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


# ═══════════════════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class UploadResponse(BaseModel):
    """Upload endpoint response model."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
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
    authorization: Optional[str] = None
):
    """
    Upload and process a transcript file (PDF, CSV, or image).
    
    Accepts:
    - PDF files (will be processed with OCR if needed)
    - CSV files (direct parsing)
    - Image files (PNG, JPG, JPEG - OCR processing)
    
    Returns processed transcript data with courses and audit results.
    Standard response format for backward compatibility.
    """
    # Get dependencies lazily
    get_current_user_optional, get_db_user_id, DB_MODULE_AVAILABLE = get_dependencies()
    settings = get_settings_safe()
    
    # Validate file security (path traversal, extension, MIME type)
    safe_filename = validate_upload_file(file)
    
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
    
    logger.info(f"File uploaded: {safe_filename}, size: {len(content)} bytes")
    
    # Check if required modules are available
    analysis_available, run_analysis = get_analysis_engine()
    if not analysis_available:
        raise HTTPException(
            status_code=503,
            detail="Analysis engine not available"
        )
    
    try:
        result: Dict[str, Any] = {}
        courses: List[Dict] = []
        
        # Handle CSV files directly (no OCR needed)
        if ext == 'csv':
            courses, csv_error = parse_csv_transcript(content)
            
            if csv_error:
                return UploadResponse(success=False, error=csv_error)
            
            if not courses:
                return UploadResponse(success=False, error="No valid courses found in CSV")
            
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
            ocr_available, OCRClass = get_ocr_engine()
            if not ocr_available:
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
                
                # OCR Processing
                ocr = OCRClass()
                ocr_result = ocr.extract(str(filepath))
                
                if not ocr_result.success:
                    logger.error(f"OCR failed: {ocr_result.error}")
                    return UploadResponse(
                        success=False, 
                        error=ocr_result.error or 'OCR extraction failed'
                    )
                
                if ocr_result.course_count == 0:
                    return UploadResponse(
                        success=False, 
                        error="No courses found in document"
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
                            return UploadResponse(success=False, error=error_msg)
                    except ImportError:
                        pass  # Skip department check if function not available
                
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
                    level2 = result.get('level2', {})
                    logger.info(f"Saving scan: {file.filename}, courses: {len(courses)}, cgpa: {level2.get('cgpa', 0)}")
                    scan_record = save_scan(
                        user_id=db_user_id,
                        filename=file.filename or 'uploaded_file',
                        total_courses=len(courses),
                        total_credits=level2.get('gpa_credits', 0),
                        cgpa=level2.get('cgpa', 0),
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
        
        logger.info(f"Analysis complete: {len(courses)} courses processed")
        return UploadResponse(success=True, data=result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing upload: {str(e)}")
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
    
    return ValidateResponse(
        valid=True,
        filename=file.filename,
        type=ext
    )
