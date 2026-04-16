"""
Upload & OCR Endpoints
======================
Handle transcript file uploads and OCR processing.
FastAPI upload and OCR endpoints.
"""
import sys
import csv
import os
import time
import tempfile
import logging
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from pydantic import BaseModel

from app.middleware.rate_limit import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy settings loading
_settings = None

def get_settings_safe():
    """Get settings with fallback for missing config."""
    global _settings
    if _settings is None:
        try:
            from app.config import get_settings
            _settings = get_settings()
        except Exception as e:
            logger.warning(f"Could not load settings: {e}")
            # Return a minimal settings object
            class MinimalSettings:
                MAX_UPLOAD_SIZE_MB = 16
            _settings = MinimalSettings()
    return _settings

# Add backend directory for local imports
backend_path = str(Path(__file__).parent.parent.parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Lazy import functions for OCR and analysis
OCR_AVAILABLE = None
TranscriptOCR = None
ANALYSIS_AVAILABLE = None
run_full_analysis = None

def get_ocr_engine():
    """Lazy load OCR engine."""
    global OCR_AVAILABLE, TranscriptOCR
    if OCR_AVAILABLE is None:
        try:
            from ocr_web import WebOCR as _TranscriptOCR
            TranscriptOCR = _TranscriptOCR
            OCR_AVAILABLE = True
        except Exception:
            try:
                from ocr_engine import TranscriptOCR as _TranscriptOCR
                TranscriptOCR = _TranscriptOCR
                OCR_AVAILABLE = True
            except Exception:
                OCR_AVAILABLE = False
                TranscriptOCR = None
    return OCR_AVAILABLE, TranscriptOCR

def get_analysis_engine():
    """Lazy load analysis engine."""
    global ANALYSIS_AVAILABLE, run_full_analysis
    if ANALYSIS_AVAILABLE is None:
        try:
            from core import run_full_analysis as _run_full_analysis
            run_full_analysis = _run_full_analysis
            ANALYSIS_AVAILABLE = True
        except Exception:
            ANALYSIS_AVAILABLE = False
            run_full_analysis = None
    return ANALYSIS_AVAILABLE, run_full_analysis

# Lazy import for dependencies
def get_dependencies():
    """Lazy load dependency functions."""
    try:
        from app.dependencies import get_current_user_optional, get_db_user_id, DB_MODULE_AVAILABLE
        return get_current_user_optional, get_db_user_id, DB_MODULE_AVAILABLE
    except Exception:
        async def _get_current_user_optional(authorization: Optional[str] = None):
            return None
        async def _get_db_user_id(user):
            return None
        return _get_current_user_optional, _get_db_user_id, False

# Lazy import for database functions
def get_db_functions():
    """Lazy load database functions."""
    try:
        from database import save_scan, get_user_by_email, create_user
        return save_scan, get_user_by_email, create_user
    except Exception:
        return None, None, None

# WebSocket progress helper
async def broadcast_progress(job_id: str, stage: str, progress: int, message: str, error: str = None):
    """Broadcast progress to WebSocket clients if available."""
    try:
        from app.main import update_ocr_progress
        await update_ocr_progress(job_id, stage, progress, message, error)
    except Exception as e:
        # WebSocket not critical - log and continue
        logger.debug(f"Could not broadcast progress: {e}")

# Knowledge base path
KB_PATH = Path(__file__).parent.parent.parent.parent / 'knowledge_base.md'

# Allowed file types and MIME types
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.csv'}
ALLOWED_MIME_TYPES = {
    'application/pdf': '.pdf',
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/jpg': '.jpg',
    'text/csv': '.csv',
    'application/csv': '.csv',
    'text/plain': '.csv',  # Some systems report CSV as text/plain
}
MAGIC_SIGNATURES = {
    '.pdf': (b'%PDF-',),
    '.png': (b'\x89PNG\r\n\x1a\n',),
    '.jpg': (b'\xff\xd8\xff',),
    '.jpeg': (b'\xff\xd8\xff',),
}

def validate_upload_file(file: UploadFile) -> str:
    """
    Validate uploaded file for security.
    
    Args:
        file: The uploaded file
        
    Returns:
        Sanitized filename
        
    Raises:
        HTTPException: If file is invalid
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Sanitize filename - extract just the filename, no path components
    filename = Path(file.filename).name
    
    # Prevent path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Check filename length
    if len(filename) > 255:
        raise HTTPException(status_code=400, detail="Filename too long")
    
    # Get file extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validate MIME type if provided
    if file.content_type:
        mime = file.content_type.lower()
        if mime not in ALLOWED_MIME_TYPES and not mime.startswith('image/') and mime != 'application/octet-stream':
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {mime}"
            )
    
    return filename


def validate_upload_contents(filename: str, content: bytes) -> None:
    """Validate that uploaded bytes actually match the declared file type."""
    ext = Path(filename).suffix.lower()

    if ext in MAGIC_SIGNATURES:
        signatures = MAGIC_SIGNATURES[ext]
        if not any(content.startswith(signature) for signature in signatures):
            raise HTTPException(
                status_code=400,
                detail=f"File contents do not match the declared {ext} type",
            )
        return

    if ext == '.csv':
        if not content:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        if b'\x00' in content:
            raise HTTPException(status_code=400, detail="CSV file contains invalid binary data")
        try:
            content.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                content.decode('latin-1')
            except UnicodeDecodeError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="CSV file must be valid text data",
                ) from exc


def get_analysis_courses(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract the canonical course list from an analysis payload."""
    courses = analysis.get('courses')
    if isinstance(courses, list):
        return courses
    level1 = analysis.get('level1', {})
    valid_entries = level1.get('valid_entries') if isinstance(level1, dict) else None
    return valid_entries if isinstance(valid_entries, list) else []


def get_scan_metrics(analysis: Dict[str, Any]) -> Tuple[int, float, float]:
    """Build consistent scan summary fields for history persistence."""
    courses = get_analysis_courses(analysis)
    level1 = analysis.get('level1', {}) if isinstance(analysis.get('level1', {}), dict) else {}
    level2 = analysis.get('level2', {}) if isinstance(analysis.get('level2', {}), dict) else {}

    total_courses = len(courses)
    total_credits = float(
        level1.get('earned_credits')
        or level1.get('total_credits_attempted')
        or level2.get('gpa_credits')
        or 0
    )
    cgpa = float(level2.get('cgpa') or 0)
    return total_courses, total_credits, cgpa


# ═══════════════════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class UploadResponse(BaseModel):
    """Upload endpoint response model."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    job_id: Optional[str] = None  # For WebSocket progress tracking
    
    class Config:
        from_attributes = True


class ValidateResponse(BaseModel):
    """Validate endpoint response model."""
    valid: bool
    filename: Optional[str] = None
    type: Optional[str] = None
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# CSV Parser for Direct Course Import
# ═══════════════════════════════════════════════════════════════════════════════

def parse_csv_transcript(content: bytes) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """
    Parse CSV content with course data.
    
    Expected CSV format (header optional):
    Course_Code,Credits,Grade,Semester
    CSE115,3,A,Fall 2022
    MAT120,3,B+,Fall 2022
    
    Also supports variations:
    - course_code,credit,grade,semester
    - Code,Credits,Grade,Term
    
    Returns:
        tuple: (list of course dicts, error message or None)
    """
    courses = []
    
    try:
        # Decode content
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content.decode('latin-1')
        
        # Parse CSV
        lines = text.splitlines()
        if not lines:
            return None, "Empty CSV file"
        
        # Try to detect dialect
        sample = '\n'.join(lines[:10])
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        
        # Check if has header
        try:
            has_header = csv.Sniffer().has_header(sample)
        except csv.Error:
            has_header = True  # Assume header if can't detect
        
        reader = csv.reader(lines, dialect)
        
        # Column mapping
        col_map = {'code': 0, 'credits': 1, 'grade': 2, 'semester': 3}
        
        for i, row in enumerate(reader):
            if not row or all(not cell.strip() for cell in row):
                continue
            
            # Handle header row
            if i == 0 and has_header:
                header_lower = [h.lower().strip() for h in row]
                for j, h in enumerate(header_lower):
                    if 'code' in h or 'course' in h:
                        col_map['code'] = j
                    elif 'credit' in h:
                        col_map['credits'] = j
                    elif 'grade' in h:
                        col_map['grade'] = j
                    elif 'sem' in h or 'term' in h:
                        col_map['semester'] = j
                continue
            
            # Parse data row
            if len(row) < 4:
                continue
            
            try:
                course_code = row[col_map['code']].strip().upper()
                credits_str = row[col_map['credits']].strip()
                grade = row[col_map['grade']].strip().upper()
                semester = row[col_map['semester']].strip()
                
                # Validate course code (2-4 letters + 3 digits)
                if not (len(course_code) >= 5 and course_code[:2].isalpha()):
                    continue
                
                # Parse credits
                try:
                    credits = float(credits_str)
                    if credits <= 0 or credits > 6:
                        continue
                except ValueError:
                    continue
                
                # Validate grade
                valid_grades = {'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 
                               'D+', 'D', 'F', 'W', 'I', 'P', 'TR', 'S', 'U'}
                if grade not in valid_grades:
                    continue
                
                courses.append({
                    'course_code': course_code,
                    'credits': credits,
                    'grade': grade,
                    'semester': semester
                })
            except (IndexError, ValueError):
                continue
        
        if not courses:
            return None, "No valid course data found in CSV. Expected format: Course_Code,Credits,Grade,Semester"
        
        logger.info(f"CSV parsed: {len(courses)} courses found")
        return courses, None
        
    except Exception as e:
        return None, f"Error parsing CSV: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# Upload Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/upload", response_model=UploadResponse)
@limiter.limit("10/minute")
async def upload_transcript(
    request: Request,
    file: UploadFile = File(...),
    source: str = Form(default="web"),
    ocr_engine: str = Form(default="auto"),
    authorization: Optional[str] = None
):
    """
    Upload and process a transcript file (PDF, CSV, or image).
    
    Accepts:
    - PDF files (will be processed with OCR if needed)
    - CSV files (direct parsing)
    - Image files (PNG, JPG, JPEG - OCR processing)
    
    Args:
        file: The file to upload
        source: Source of upload ('web', 'cli', 'api')
        ocr_engine: OCR engine selection ('auto', 'google_vision', 'azure')
    
    Returns processed transcript data with courses and audit results.
    Standard response format for backward compatibility.
    """
    # Get dependencies lazily
    get_current_user_optional, get_db_user_id, DB_MODULE_AVAILABLE = get_dependencies()
    settings = get_settings_safe()
    
    # Validate file security (path traversal, extension, MIME type)
    safe_filename = validate_upload_file(file)
    
    # Validate OCR engine selection
    valid_engines = {'auto', 'google_vision', 'azure'}
    if ocr_engine.lower() not in valid_engines:
        ocr_engine = 'auto'
    
    # Get user from auth header
    user = None
    auth_header = request.headers.get('Authorization')
    if auth_header:
        user = await get_current_user_optional(auth_header)
    
    # Log auth status
    if user:
        logger.info(f"Upload request from authenticated user: {user.get('email')}")
    else:
        logger.info("Upload request from unauthenticated user (guest mode)")
    
    # Get file extension
    ext = Path(safe_filename).suffix.lower().lstrip('.')
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB."
        )
    validate_upload_contents(safe_filename, content)
    
    # Generate job ID for WebSocket progress tracking
    job_id = str(uuid.uuid4())[:8]
    
    logger.info(f"File uploaded: {safe_filename}, size: {len(content)} bytes, job: {job_id}")
    
    # Broadcast initial progress
    await broadcast_progress(job_id, "upload", 10, "File received, validating...")
    
    # Check if required modules are available
    analysis_available, run_analysis = get_analysis_engine()
    if not analysis_available:
        await broadcast_progress(job_id, "error", 0, "Analysis engine not available", "Analysis engine not available")
        raise HTTPException(
            status_code=503,
            detail="Analysis engine not available"
        )
    
    try:
        result: Dict[str, Any] = {}
        courses: List[Dict] = []
        
        # Handle CSV files directly (no OCR needed)
        if ext == 'csv':
            await broadcast_progress(job_id, "parse", 30, "Parsing CSV file...")
            
            courses, csv_error = parse_csv_transcript(content)
            
            if csv_error:
                await broadcast_progress(job_id, "error", 0, csv_error, csv_error)
                return UploadResponse(success=False, error=csv_error, job_id=job_id)
            
            if not courses:
                await broadcast_progress(job_id, "error", 0, "No valid courses found", "No valid courses found in CSV")
                return UploadResponse(success=False, error="No valid courses found in CSV", job_id=job_id)
            
            await broadcast_progress(job_id, "analyze", 60, "Running degree audit analysis...")
            
            # Run analysis on parsed courses
            result = run_analysis(courses, kb_path=str(KB_PATH))
            
            # Add CSV info (similar to OCR info)
            result['ocr_info'] = {
                'engine': 'CSV Parser (Direct Import)',
                'confidence': 100.0,
                'raw_text_count': len(courses),
                'student_name': None,
                'student_id': None,
                'cgpa_from_pdf': 0,
                'total_credits_from_pdf': sum(c.get('credits', 0) for c in courses)
            }
        else:
            # OCR Processing for PDF/images
            await broadcast_progress(job_id, "ocr", 25, "Starting OCR processing...")
            
            ocr_available, OCRClass = get_ocr_engine()
            if not ocr_available:
                await broadcast_progress(job_id, "error", 0, "OCR engine not available", "OCR engine not available")
                raise HTTPException(
                    status_code=503,
                    detail="OCR engine not available"
                )
            
            # Save temporarily for OCR processing
            runtime_root = Path(tempfile.gettempdir()) / 'nsu-audit-api' / 'uploads'
            runtime_root.mkdir(parents=True, exist_ok=True)
            
            # Secure filename
            safe_filename = f"upload_{int(time.time())}_{file.filename or 'file'}"
            safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in '._-')
            if not safe_filename.endswith(f'.{ext}'):
                safe_filename = f"{safe_filename}.{ext}"
            
            filepath = runtime_root / safe_filename
            
            try:
                # Write file
                filepath.write_bytes(content)
                
                await broadcast_progress(job_id, "ocr", 40, f"Running OCR with {ocr_engine} engine...")
                
                # OCR Processing with selected engine
                ocr = OCRClass(engine=ocr_engine)
                ocr_result = ocr.extract(str(filepath))
                
                if not ocr_result.success:
                    logger.error(f"OCR failed: {ocr_result.error}")
                    await broadcast_progress(job_id, "error", 0, f"OCR failed: {ocr_result.error}", ocr_result.error)
                    return UploadResponse(
                        success=False, 
                        error=ocr_result.error or 'OCR extraction failed',
                        job_id=job_id
                    )
                
                await broadcast_progress(job_id, "ocr", 60, f"Found {ocr_result.course_count} courses")
                
                if ocr_result.course_count == 0:
                    await broadcast_progress(job_id, "error", 0, "No courses found", "No courses found in document")
                    return UploadResponse(
                        success=False, 
                        error="No courses found in document",
                        job_id=job_id
                    )
                
                # Check for valid department from student ID
                if ocr_result.student_id and not getattr(ocr_result, 'department_valid', True):
                    try:
                        from ocr_web import detect_department_from_id
                        dept_check = detect_department_from_id(ocr_result.student_id)
                        if not dept_check.get('valid', False):
                            error_msg = (
                                "This transcript is not from a supported NSU department. "
                                "Only CSE (42), EEE (43), and BBA (30) transcripts are accepted."
                            )
                            if dept_check.get('department_code'):
                                error_msg += f" (Detected code: {dept_check.get('department_code')})"
                            logger.warning(f"Invalid department detected: {ocr_result.student_id}")
                            await broadcast_progress(job_id, "error", 0, "Invalid department", error_msg)
                            return UploadResponse(success=False, error=error_msg, job_id=job_id)
                    except ImportError:
                        pass  # Skip department check if function not available
                
                await broadcast_progress(job_id, "analyze", 70, "Running degree audit analysis...")
                
                # Prepare courses data
                courses = [
                    {
                        'course_code': c.course_code,
                        'credits': c.credits,
                        'grade': c.grade,
                        'semester': c.semester
                    }
                    for c in ocr_result.courses
                ]
                
                # Run analysis with student_id for curriculum versioning
                result = run_analysis(
                    courses, 
                    kb_path=str(KB_PATH),
                    student_id=ocr_result.student_id
                )
                
                # Add OCR info with department and validation data
                result['ocr_info'] = {
                    'engine': ocr_result.engine_used,
                    'confidence': round(ocr_result.confidence_score * 100, 1),
                    'raw_text_count': len(ocr_result.raw_text),
                    'student_name': ocr_result.student_name,
                    'student_id': ocr_result.student_id,
                    'department_code': getattr(ocr_result, 'department_code', None),
                    'department_name': getattr(ocr_result, 'department_name', None),
                    'department_full_name': getattr(ocr_result, 'department_full_name', None),
                    'department_valid': getattr(ocr_result, 'department_valid', True),
                    'unknown_courses': getattr(ocr_result, 'unknown_courses', []),
                }
            finally:
                # Cleanup temp file
                try:
                    filepath.unlink(missing_ok=True)
                except Exception:
                    pass
        
        # Save to history if user is authenticated
        scan_id = None
        save_scan, _, _ = get_db_functions()
        if user and DB_MODULE_AVAILABLE and save_scan:
            logger.info(f"Attempting to save scan for user: {user.get('email')}")
            try:
                db_user_id = await get_db_user_id(user)
                
                if db_user_id:
                    total_courses, total_credits, cgpa = get_scan_metrics(result)
                    logger.info(
                        f"Saving scan: {file.filename}, courses: {total_courses}, cgpa: {cgpa}"
                    )
                    scan_record = save_scan(
                        user_id=db_user_id,
                        filename=file.filename or 'uploaded_file',
                        total_courses=total_courses,
                        total_credits=total_credits,
                        cgpa=cgpa,
                        analysis_data=result,
                        source=source
                    )
                    if scan_record:
                        scan_id = scan_record['id']
                        result['scan_id'] = scan_id
                        logger.info(f"✓ Scan saved to history: {scan_id}")
                    else:
                        logger.error("save_scan returned None")
                else:
                    logger.error("Could not get db_user_id")
            except Exception as e:
                logger.exception(f"Failed to save to history: {e}")
        elif not user:
            logger.info("No user authenticated, skipping history save")
        elif not DB_MODULE_AVAILABLE:
            logger.warning("Database not available, skipping history save")
        
        await broadcast_progress(job_id, "complete", 100, f"Analysis complete! {len(courses)} courses processed")
        
        logger.info(f"Analysis complete: {len(courses)} courses processed")
        return UploadResponse(success=True, data=result, job_id=job_id)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing upload: {str(e)}")
        await broadcast_progress(job_id, "error", 0, "Processing error", str(e))
        raise HTTPException(
            status_code=500,
            detail="Error processing file. Please try again."
        )


@router.post("/upload/validate", response_model=ValidateResponse)
@limiter.limit("20/minute")
async def validate_file(
    request: Request,
    file: UploadFile = File(...)
):
    """
    Validate a file without processing it.
    
    Quick check to verify file type and size before full upload.
    """
    settings = get_settings_safe()
    
    allowed = {'pdf', 'csv', 'png', 'jpg', 'jpeg'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if file.filename and '.' in file.filename else ''
    
    if ext not in allowed:
        return ValidateResponse(
            valid=False,
            error=f"Invalid file type. Allowed: {', '.join(allowed)}"
        )
    
    # Check file size without reading entire file
    content = await file.read()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    if len(content) > max_size:
        return ValidateResponse(
            valid=False,
            error=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB."
        )
    validate_upload_contents(file.filename or "upload.csv", content)
    
    return ValidateResponse(
        valid=True,
        filename=file.filename,
        type=ext
    )


# ═══════════════════════════════════════════════════════════════════════════════
# NEW FEATURES: Export, GPA Predictor
# ═══════════════════════════════════════════════════════════════════════════════

class ExportRequest(BaseModel):
    """Export format options."""
    format: str = "json"  # json, csv

class GPAPredictorRequest(BaseModel):
    """GPA prediction request."""
    current_cgpa: float
    current_credits: int
    planned_courses: List[Dict[str, Any]]  # [{credits: 3, expected_grade: "A"}]

class GPAPredictorResponse(BaseModel):
    """GPA prediction response."""
    current_cgpa: float
    predicted_cgpa: float
    scenarios: List[Dict[str, Any]]
    credits_after: int


@router.get("/export/{scan_id}")
@limiter.limit("10/minute")
async def export_scan(
    request: Request,
    scan_id: str,
    format: str = "json",
    authorization: Optional[str] = None
):
    """
    Export a scan result in various formats.
    
    Formats:
    - json: Full JSON data
    - csv: Course list as CSV
    - excel: Excel workbook with multiple sheets
    - pdf: PDF report with summary
    """
    get_current_user_optional, get_db_user_id, DB_MODULE_AVAILABLE = get_dependencies()
    
    if not DB_MODULE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Get user from Authorization header
    user = None
    auth_header = request.headers.get('Authorization')
    if auth_header:
        user = await get_current_user_optional(auth_header)
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get scan from database
    try:
        from database import get_scan_by_id
        db_user_id = await get_db_user_id(user)
        scan = get_scan_by_id(scan_id)  # Only pass scan_id
        
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        # Verify ownership
        if scan.get('user_id') != db_user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        analysis_data = scan.get('analysis_data', {})
        
        # Handle case where analysis_data is a JSON string
        import json as json_module
        if isinstance(analysis_data, str):
            try:
                analysis_data = json_module.loads(analysis_data)
            except json_module.JSONDecodeError:
                logger.error(f"Failed to parse analysis_data for scan {scan_id}")
                analysis_data = {}
        
        format = format.lower().strip()
        if format not in {"json", "csv", "excel", "pdf"}:
            raise HTTPException(status_code=400, detail="Unsupported export format")

        level1 = analysis_data.get('level1', {}) if isinstance(analysis_data.get('level1', {}), dict) else {}
        level2 = analysis_data.get('level2', {}) if isinstance(analysis_data.get('level2', {}), dict) else {}
        level3 = analysis_data.get('level3', {}) if isinstance(analysis_data.get('level3', {}), dict) else {}
        courses = get_analysis_courses(analysis_data)
        waiver = level2.get('waiver', {}) if isinstance(level2.get('waiver', {}), dict) else {}
        
        from fastapi.responses import Response
        import io
        
        if format == "csv":
            # Generate CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow(['Course Code', 'Credits', 'Grade', 'Quality Points', 'Semester'])
            
            for course in courses:
                writer.writerow([
                    course.get('code', ''),
                    course.get('credits', 0),
                    course.get('grade', ''),
                    course.get('quality_points', 0),
                    course.get('semester', '')
                ])
            
            # Summary row
            writer.writerow([])
            writer.writerow(['Summary'])
            writer.writerow(['Total Credits', level2.get('gpa_credits', 0)])
            writer.writerow(['CGPA', level2.get('cgpa', 0)])
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=transcript_{scan_id}.csv"}
            )
        
        elif format == "excel":
            # Generate Excel with openpyxl
            try:
                from openpyxl import Workbook
                from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
                from openpyxl.utils import get_column_letter
            except ImportError:
                raise HTTPException(status_code=503, detail="Excel export not available")
            
            wb = Workbook()
            
            # Sheet 1: Summary
            ws_summary = wb.active
            ws_summary.title = "Summary"
            
            # Styles
            header_font = Font(bold=True, size=14)
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_font_white = Font(bold=True, size=12, color="FFFFFF")
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Title
            ws_summary['A1'] = "NSU Degree Audit Report"
            ws_summary['A1'].font = Font(bold=True, size=18)
            ws_summary.merge_cells('A1:D1')
            
            # Summary data
            summary_data = [
                ("", ""),  # Empty row
                ("File", scan.get('filename', 'N/A')),
                ("Date", scan.get('created_at', 'N/A')),
                ("", ""),
                ("Academic Summary", ""),
                ("Total Credits", level2.get('gpa_credits', 0)),
                ("Quality Points", level2.get('total_quality_points', 0)),
                ("CGPA", level2.get('cgpa', 0)),
                ("", ""),
                ("Waiver Status", waiver.get('name', 'N/A')),
                ("Waiver Percentage", waiver.get('level', '0%')),
            ]
            
            for idx, (label, value) in enumerate(summary_data, start=2):
                ws_summary[f'A{idx}'] = label
                ws_summary[f'B{idx}'] = value
                if label:
                    ws_summary[f'A{idx}'].font = Font(bold=True)
            
            ws_summary.column_dimensions['A'].width = 25
            ws_summary.column_dimensions['B'].width = 40
            
            # Sheet 2: Courses
            ws_courses = wb.create_sheet("Courses")
            
            # Header
            headers = ['Course Code', 'Course Name', 'Credits', 'Grade', 'Quality Points', 'Semester']
            for col, header in enumerate(headers, start=1):
                cell = ws_courses.cell(row=1, column=col, value=header)
                cell.font = header_font_white
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
                cell.border = thin_border
            
            # Data rows
            for row_idx, course in enumerate(courses, start=2):
                ws_courses.cell(row=row_idx, column=1, value=course.get('code', ''))
                ws_courses.cell(row=row_idx, column=2, value=course.get('name', ''))
                ws_courses.cell(row=row_idx, column=3, value=course.get('credits', 0))
                ws_courses.cell(row=row_idx, column=4, value=course.get('grade', ''))
                ws_courses.cell(row=row_idx, column=5, value=course.get('quality_points', 0))
                ws_courses.cell(row=row_idx, column=6, value=course.get('semester', ''))
                
                for col in range(1, 7):
                    ws_courses.cell(row=row_idx, column=col).border = thin_border
            
            # Auto-adjust column widths
            for col in range(1, 7):
                ws_courses.column_dimensions[get_column_letter(col)].width = 15
            
            # Save to bytes
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            return Response(
                content=output.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=transcript_{scan_id}.xlsx"}
            )
        
        elif format == "pdf":
            # Generate PDF with reportlab
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            except ImportError:
                raise HTTPException(status_code=503, detail="PDF export not available")
            
            output = io.BytesIO()
            doc = SimpleDocTemplate(output, pagesize=letter, topMargin=0.5*inch)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                alignment=1,  # Center
                spaceAfter=20
            )
            elements.append(Paragraph("NSU Degree Audit Report", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Summary section
            elements.append(Paragraph("Academic Summary", styles['Heading2']))
            summary_data = [
                ["Metric", "Value"],
                ["Filename", scan.get('filename', 'N/A')],
                ["Total Credits", str(level2.get('gpa_credits', 0))],
                ["Quality Points", str(level2.get('total_quality_points', 0))],
                ["CGPA", str(level2.get('cgpa', 0))],
                ["Waiver Status", waiver.get('name', 'N/A')],
            ]
            
            summary_table = Table(summary_data, colWidths=[2.5*inch, 3*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E7E6E6')),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Courses section
            elements.append(Paragraph("Course Details", styles['Heading2']))
            
            course_data = [["Course Code", "Credits", "Grade", "Quality Pts"]]
            for course in courses[:50]:  # Limit to 50 courses for PDF
                course_data.append([
                    course.get('code', ''),
                    str(course.get('credits', 0)),
                    course.get('grade', ''),
                    str(course.get('quality_points', 0))
                ])
            
            if len(courses) > 50:
                course_data.append(["...", f"+{len(courses)-50} more", "", ""])
            
            course_table = Table(course_data, colWidths=[2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
            course_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
            ]))
            elements.append(course_table)
            
            # Build PDF
            doc.build(elements)
            output.seek(0)
            
            return Response(
                content=output.getvalue(),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=transcript_{scan_id}.pdf"}
            )
        
        # Default: JSON
        return {
            "success": True,
            "scan_id": scan_id,
            "filename": scan.get('filename'),
            "created_at": scan.get('created_at'),
            "analysis": analysis_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="Export failed")


@router.post("/predict-gpa", response_model=GPAPredictorResponse)
@limiter.limit("30/minute")
async def predict_gpa(
    request: Request,
    data: GPAPredictorRequest
):
    """
    Predict future CGPA based on planned courses and expected grades.
    
    Provides multiple scenarios (optimistic, realistic, conservative).
    """
    # Grade points mapping
    grade_points = {
        'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0, 'C-': 1.7,
        'D+': 1.3, 'D': 1.0,
        'F': 0.0
    }
    
    current_quality_points = data.current_cgpa * data.current_credits
    
    # Calculate for planned courses
    planned_credits = 0
    planned_points = 0
    
    for course in data.planned_courses:
        credits = course.get('credits', 3)
        grade = course.get('expected_grade', 'B').upper()
        points = grade_points.get(grade, 3.0)
        
        planned_credits += credits
        planned_points += credits * points
    
    total_credits = data.current_credits + planned_credits
    total_points = current_quality_points + planned_points
    predicted_cgpa = total_points / total_credits if total_credits > 0 else 0
    
    # Generate scenarios
    scenarios = []
    
    # Optimistic (all A/A-)
    opt_points = current_quality_points + (planned_credits * 3.85)
    scenarios.append({
        "name": "Optimistic (All A/A-)",
        "cgpa": round(opt_points / total_credits, 2),
        "description": "Best case scenario with all A and A- grades"
    })
    
    # Realistic (as predicted)
    scenarios.append({
        "name": "Realistic (As Expected)",
        "cgpa": round(predicted_cgpa, 2),
        "description": "Based on your expected grades"
    })
    
    # Conservative (all B/B-)
    cons_points = current_quality_points + (planned_credits * 2.85)
    scenarios.append({
        "name": "Conservative (All B/B-)",
        "cgpa": round(cons_points / total_credits, 2),
        "description": "Conservative estimate with B-range grades"
    })
    
    return GPAPredictorResponse(
        current_cgpa=data.current_cgpa,
        predicted_cgpa=round(predicted_cgpa, 2),
        scenarios=scenarios,
        credits_after=total_credits
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH UPLOAD: Process multiple transcripts at once
# ═══════════════════════════════════════════════════════════════════════════════

class BatchUploadResultItem(BaseModel):
    """Individual file result in batch upload."""
    filename: str
    success: bool
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class BatchUploadResponse(BaseModel):
    """Batch upload response with all results."""
    success: bool
    total_files: int
    processed: int
    failed: int
    results: List[BatchUploadResultItem]


@router.post("/upload/batch", response_model=BatchUploadResponse)
@limiter.limit("5/minute")
async def batch_upload_transcripts(
    request: Request,
    files: List[UploadFile] = File(...),
    ocr_engine: Optional[str] = Form(None),
    authorization: Optional[str] = None
):
    """
    Upload and process multiple transcript files in a single request.
    
    Supports up to 10 files at once.
    Each file is processed independently - failures don't affect other files.
    
    Parameters:
    - files: List of transcript files (PDF, PNG, JPG, JPEG, CSV)
    - ocr_engine: OCR engine to use (auto, google_vision, azure)
    
    Returns results for each file with success/failure status.
    """
    MAX_BATCH_SIZE = 10
    
    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_BATCH_SIZE} files allowed per batch"
        )
    
    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail="No files provided"
        )
    
    # Get auth and settings
    get_current_user_optional, get_db_user_id, DB_MODULE_AVAILABLE = get_dependencies()
    settings = get_settings_safe()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    # Get user if authenticated
    user = None
    db_user_id = None
    auth_header = request.headers.get('Authorization')
    if auth_header:
        user = await get_current_user_optional(auth_header)
        if user and DB_MODULE_AVAILABLE:
            db_user_id = await get_db_user_id(user)
    
    results = []
    processed = 0
    failed = 0
    
    for file in files:
        try:
            # Validate file
            if not file.filename:
                results.append(BatchUploadResultItem(
                    filename="unknown",
                    success=False,
                    error="No filename provided"
                ))
                failed += 1
                continue
            
            try:
                safe_filename = validate_upload_file(file)
            except HTTPException as exc:
                results.append(BatchUploadResultItem(
                    filename=file.filename,
                    success=False,
                    error=str(exc.detail),
                ))
                failed += 1
                continue

            ext = Path(safe_filename).suffix.lower()
            
            # Read content
            content = await file.read()
            if len(content) > max_size:
                results.append(BatchUploadResultItem(
                    filename=file.filename,
                    success=False,
                    error=f"File too large (max {settings.MAX_UPLOAD_SIZE_MB}MB)"
                ))
                failed += 1
                continue
            try:
                validate_upload_contents(safe_filename, content)
            except HTTPException as exc:
                results.append(BatchUploadResultItem(
                    filename=file.filename,
                    success=False,
                    error=str(exc.detail),
                ))
                failed += 1
                continue
            
            # Process CSV directly
            if ext == '.csv':
                ANALYSIS_AVAILABLE, run_analysis = get_analysis_engine()
                
                if ANALYSIS_AVAILABLE and run_analysis:
                    course_rows, csv_error = parse_csv_transcript(content)
                    if csv_error or not course_rows:
                        results.append(BatchUploadResultItem(
                            filename=file.filename,
                            success=False,
                            error=csv_error or "No valid courses found in CSV",
                        ))
                        failed += 1
                        continue

                    analysis = run_analysis(course_rows, kb_path=str(KB_PATH))
                    analysis['ocr_info'] = {
                        'engine': 'CSV Parser (Direct Import)',
                        'confidence': 100.0,
                        'source': 'batch_upload',
                    }
                    
                    # Save to history if authenticated
                    if db_user_id and DB_MODULE_AVAILABLE:
                        save_scan, _, _ = get_db_functions()
                        if save_scan:
                            try:
                                total_courses, total_credits, cgpa = get_scan_metrics(analysis)
                                save_scan(
                                    user_id=db_user_id,
                                    filename=file.filename,
                                    total_courses=total_courses,
                                    total_credits=total_credits,
                                    cgpa=cgpa,
                                    analysis_data=analysis,
                                    source='batch_upload',
                                )
                            except Exception as e:
                                logger.warning(f"Batch save_scan failed: {e}")
                    
                    results.append(BatchUploadResultItem(
                        filename=file.filename,
                        success=True,
                        data=analysis
                    ))
                    processed += 1
                else:
                    results.append(BatchUploadResultItem(
                        filename=file.filename,
                        success=False,
                        error="Analysis engine not available"
                    ))
                    failed += 1
                continue
            
            # Process PDF/Image with OCR
            OCR_AVAILABLE, OCRClass = get_ocr_engine()
            if not OCR_AVAILABLE or not OCRClass:
                results.append(BatchUploadResultItem(
                    filename=file.filename,
                    success=False,
                    error="OCR engine not available"
                ))
                failed += 1
                continue
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            
            try:
                # Run OCR with engine selection
                ocr = OCRClass(engine=ocr_engine) if ocr_engine else OCRClass()
                ocr_result = ocr.extract(tmp_path)
                
                if not ocr_result.success:
                    results.append(BatchUploadResultItem(
                        filename=file.filename,
                        success=False,
                        error=f"OCR failed: {ocr_result.error}"
                    ))
                    failed += 1
                    continue
                
                # Get analysis
                ANALYSIS_AVAILABLE, run_analysis = get_analysis_engine()
                if ANALYSIS_AVAILABLE and run_analysis:
                    course_rows = [
                        {
                            'course_code': course.course_code,
                            'credits': course.credits,
                            'grade': course.grade,
                            'semester': course.semester,
                        }
                        for course in ocr_result.courses
                    ]
                    analysis = run_analysis(
                        course_rows,
                        kb_path=str(KB_PATH),
                        student_id=getattr(ocr_result, 'student_id', None),
                    )
                    
                    # Add OCR info
                    analysis['ocr_info'] = {
                        'engine': ocr_result.engine_used,
                        'confidence': round(ocr_result.confidence_score * 100, 1),
                        'source': 'batch_upload',
                        'student_name': getattr(ocr_result, 'student_name', ''),
                        'student_id': getattr(ocr_result, 'student_id', ''),
                        'department_code': getattr(ocr_result, 'department_code', None),
                        'department_name': getattr(ocr_result, 'department_name', None),
                        'department_full_name': getattr(ocr_result, 'department_full_name', None),
                        'department_valid': getattr(ocr_result, 'department_valid', True),
                        'unknown_courses': getattr(ocr_result, 'unknown_courses', []),
                    }
                    
                    # Save to history if authenticated
                    if db_user_id and DB_MODULE_AVAILABLE:
                        save_scan, _, _ = get_db_functions()
                        if save_scan:
                            try:
                                total_courses, total_credits, cgpa = get_scan_metrics(analysis)
                                save_scan(
                                    user_id=db_user_id,
                                    filename=file.filename,
                                    total_courses=total_courses,
                                    total_credits=total_credits,
                                    cgpa=cgpa,
                                    analysis_data=analysis,
                                    source='batch_upload',
                                )
                            except Exception as e:
                                logger.warning(f"Batch save_scan failed: {e}")
                    
                    results.append(BatchUploadResultItem(
                        filename=file.filename,
                        success=True,
                        data=analysis
                    ))
                    processed += 1
                else:
                    results.append(BatchUploadResultItem(
                        filename=file.filename,
                        success=False,
                        error="Analysis engine not available"
                    ))
                    failed += 1
                    
            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.exception(f"Batch upload error for {file.filename}: {e}")
            results.append(BatchUploadResultItem(
                filename=file.filename if file.filename else "unknown",
                success=False,
                error=str(e)
            ))
            failed += 1
    
    return BatchUploadResponse(
        success=processed > 0,
        total_files=len(files),
        processed=processed,
        failed=failed,
        results=results
    )
