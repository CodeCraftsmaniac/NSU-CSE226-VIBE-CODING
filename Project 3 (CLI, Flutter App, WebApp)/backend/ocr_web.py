"""
ocr_web.py  —  Web-based OCR for NSU Transcript Extraction
=====================================================================
VERSION: 2.1.0 - Production Release

Features:
1. Google Cloud Vision API (1000 free/month) - Most accurate
2. OCR.space API (500 free/month) - Good fallback
3. Native PDF text extraction - For digital PDFs
4. Improved table parsing logic
"""

__version__ = "2.1.0"

import os
import re
import io
import sys
import base64
import json
import tempfile
import warnings
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from pathlib import Path
from urllib import request as urllib_request
from urllib import parse as urllib_parse
from urllib.error import URLError, HTTPError

warnings.filterwarnings('ignore')

# Configuration constants
API_TIMEOUT = 30
OCR_CONFIDENCE_THRESHOLD = 0.7
MAX_CGPA = 4.0
MAX_CREDITS_PER_COURSE = 6
MAX_TOTAL_CREDITS = 200

# Setup logging
_logger = logging.getLogger(__name__)

# Load environment variables if dotenv is available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    pass

# API Keys - Load from environment
GOOGLE_VISION_API_KEY = os.environ.get('GOOGLE_CLOUD_VISION_KEY') or os.environ.get('GOOGLE_VISION_API_KEY', '')
OCR_SPACE_API_KEY = os.environ.get('OCR_SPACE_API_KEY', '')

VALID_GRADES = {'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F', 'W', 'I', 'P', 'TR'}
COURSE_PATTERN = re.compile(r'^([A-Z]{2,4})(\d{3}[A-Z]?)$')
SEMESTER_PATTERN = re.compile(r'(Spring|Summer|Fall)\s*(\d{4})', re.IGNORECASE)

# Full-line pattern: matches "CSE115 3 A-" or "CSE 115  3.0  B+" format
# Note: Don't use \b at end because +/- are not word characters
FULL_LINE_PATTERN = re.compile(
    r'\b([A-Z]{2,4})\s*(\d{3}[A-Z]?)\s+(\d(?:\.\d)?)\s+([ABCDF][+-]?|W|I|P|TR)(?:\s|$)',
    re.IGNORECASE
)

# Table header detection patterns
TABLE_HEADER_PATTERNS = [
    re.compile(r'Course\s*(?:Code)?.*Credit.*Grade', re.IGNORECASE),
    re.compile(r'Subject.*(?:Credit|Cr\.?).*Grade', re.IGNORECASE),
]

# Extended course prefixes for any department
ALL_COURSE_PREFIXES = {
    'CSE', 'EEE', 'ECE', 'MAT', 'PHY', 'CHE', 'ENG', 'BEN', 'BIO',
    'ENV', 'ECO', 'BUS', 'ACT', 'FIN', 'MKT', 'MGT', 'MIS', 'HRM',
    'SOC', 'POL', 'HIS', 'PHI', 'ANT', 'PSY', 'ARC', 'LAW', 'ESL',
    'GEN', 'COM', 'MED', 'PHA', 'PUB', 'MPH', 'STA', 'IST', 'LIN',
    'JMS', 'CIS', 'MSC', 'NST', 'ART', 'MUS', 'THE', 'REL', 'GEO',
    'CHI', 'JPN', 'FRE', 'GER', 'SPA', 'ARA', 'BAN', 'URD', 'HIN',
    'ACC', 'MNS', 'BME', 'CEE', 'IPE', 'TEX', 'AER', 'NFS', 'PAD',  # PAD = Public Administration
}

# OCR corrections for common misreads (extended list)
OCR_CORRECTIONS = {
    # Number/letter confusion
    '8+': 'B+', '8-': 'B-', '8': 'B',
    '0': 'D', 'O': 'D', '6': 'B',
    # Plus/minus symbol issues
    'A+': 'A', 'A1': 'A-', 'Al': 'A-', 'A|': 'A-', 'At': 'A-', 'A~': 'A-', 'A.': 'A',
    'Bt': 'B+', 'B1': 'B-', 'B~': 'B-', 'B.': 'B',
    'C1': 'C-', 'Ct': 'C+', 'C~': 'C-', 'C.': 'C',
    'D1': 'D+', 'Dt': 'D+', 'D.': 'D',
    # Transfer/special grades
    'T8': 'TR', 'TR.': 'TR', 'T R': 'TR', 'ТR': 'TR',  # Cyrillic T
    'P+': 'P', 'P.': 'P',
    # Common OCR errors
    'E': 'F', 'S': 'B',  # S often misread for B
    # Course code corrections
    'CSEIS': 'CSE15', 'MAT1I6': 'MAT116', 'MAT12O': 'MAT120',
    'PHY1O7': 'PHY107', 'ENG1O2': 'ENG102',
}


@dataclass
class CourseRecord:
    """A single course entry."""
    course_code: str
    credits: float
    grade: str
    semester: str = ""
    confidence: float = 1.0

    def to_csv_row(self) -> str:
        return f"{self.course_code},{self.credits},{self.grade},{self.semester}"


@dataclass
class OCRResult:
    """OCR extraction result."""
    success: bool
    courses: list = field(default_factory=list)
    raw_text: list = field(default_factory=list)
    error: Optional[str] = None
    student_name: str = ""
    student_id: str = ""
    cgpa: float = 0.0
    total_credits: float = 0.0
    engine_used: str = ""
    confidence_score: float = 0.0

    @property
    def csv_data(self) -> str:
        lines = ["Course_Code,Credits,Grade,Semester"]
        for course in self.courses:
            lines.append(course.to_csv_row())
        return "\n".join(lines)

    @property
    def course_count(self) -> int:
        return len(self.courses)


class WebOCR:
    """
    Improved OCR with multiple engines and better parsing.

    Priority:
    1. Native PDF text (for digital PDFs)
    2. Google Vision API (most accurate, 1000 free/month)
    3. OCR.space API (good fallback, 500 free/month)
    """

    def __init__(self, google_api_key: str = None, ocr_space_key: str = None,
                 progress_callback=None):
        # Use module-level constants as fallback (loaded from .env at import time)
        # Also check environment directly for runtime flexibility
        self.google_api_key = google_api_key or GOOGLE_VISION_API_KEY or os.environ.get('GOOGLE_CLOUD_VISION_KEY') or os.environ.get('GOOGLE_VISION_API_KEY', '')
        self.ocr_space_key = ocr_space_key or OCR_SPACE_API_KEY or os.environ.get('OCR_SPACE_API_KEY', '')
        self.progress_callback = progress_callback
        
        _logger.info(f"WebOCR initialized - Google API key: {'present' if self.google_api_key else 'missing'}, OCR.space key: {'present' if self.ocr_space_key else 'missing'}")

    def _report(self, stage: str, progress: float, text: str = ""):
        if self.progress_callback:
            self.progress_callback(stage, progress, text)

    def extract(self, file_path: str) -> OCRResult:
        """Extract transcript data from PDF or image."""
        path = Path(file_path)
        if not path.exists():
            return OCRResult(success=False, error=f"File not found: {file_path}")

        ext = path.suffix.lower()
        try:
            self._report("init", 5, "Starting extraction...")

            if ext == '.pdf':
                return self._extract_pdf(path)
            elif ext in {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}:
                return self._extract_image(path)
            else:
                return OCRResult(success=False, error=f"Unsupported: {ext}")
        except Exception as e:
            _logger.exception(f"OCR extraction error: {e}")
            return OCRResult(success=False, error=str(e))

    def _extract_pdf(self, path: Path) -> OCRResult:
        """Extract from PDF."""
        import fitz

        self._report("pdf", 10, "Opening PDF...")
        doc = fitz.open(str(path))

        # Try native text extraction first (for digital PDFs)
        all_text = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                all_text.append(text)

        full_text = "\n".join(all_text)

        # If we got substantial text, parse it directly
        if len(full_text) > 50:
            doc.close()
            self._report("parse", 50, "Parsing digital PDF...")
            result = self._parse_transcript_text(full_text)
            result.engine_used = "PyMuPDF (Native Text)"
            result.confidence_score = 0.98
            self._report("complete", 100, "Done!")
            return result

        # Otherwise, need OCR for scanned PDF
        self._report("ocr", 30, "Running OCR on scanned PDF...")

        ocr_text = ""
        last_error = None
        pages_processed = 0

        for i, page in enumerate(doc):
            self._report("page", 30 + (i / len(doc)) * 50, f"OCR page {i+1}/{len(doc)}...")

            # Render page to image at higher resolution for better OCR
            pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
            img_data = pix.tobytes("png")

            # Compress if too large for OCR API (free tier limit ~1MB)
            if len(img_data) > 900000:
                img_data = self._compress_image(img_data)

            # Try Google Vision first, then OCR.space
            page_text, error = self._ocr_image(img_data, "page.png")
            pages_processed += 1

            if page_text:
                ocr_text += page_text + "\n"
            if error:
                last_error = error
                _logger.warning(f"Page {i+1} OCR error: {error}")

        doc.close()

        if not ocr_text.strip():
            if last_error:
                error_msg = f"OCR failed on {pages_processed} page(s): {last_error}"
            else:
                error_msg = f"OCR processed {pages_processed} page(s) but found no text. APIs configured: Google={bool(self.google_api_key)}, OCR.space={bool(self.ocr_space_key)}"
            return OCRResult(success=False, error=error_msg)

        self._report("parse", 85, "Parsing extracted text...")
        result = self._parse_transcript_text(ocr_text)
        result.engine_used = "Google Vision" if self.google_api_key else "OCR.space"
        result.confidence_score = 0.85

        self._report("complete", 100, "Done!")
        return result

    def _extract_image(self, path: Path) -> OCRResult:
        """Extract from image file."""
        self._report("image", 20, "Reading image...")

        with open(path, 'rb') as f:
            img_data = f.read()

        # Compress if too large
        if len(img_data) > 900000:
            self._report("compress", 30, "Compressing...")
            img_data = self._compress_image(img_data)

        self._report("ocr", 40, "Running OCR...")
        text, error = self._ocr_image(img_data, path.name)

        if not text:
            if error:
                error_msg = f"OCR failed: {error}"
            else:
                error_msg = f"OCR found no text. APIs configured: Google={bool(self.google_api_key)}, OCR.space={bool(self.ocr_space_key)}"
            return OCRResult(success=False, error=error_msg)

        self._report("parse", 80, "Parsing...")
        result = self._parse_transcript_text(text)
        result.engine_used = "Google Vision" if self.google_api_key else "OCR.space"
        result.confidence_score = 0.85

        self._report("complete", 100, "Done!")
        return result

    def _ocr_image(self, img_data: bytes, filename: str) -> tuple:
        """Run OCR on image data using available API.

        Returns:
            tuple: (text, error) - text is the extracted text, error is the error message if any
        """
        google_error = None
        ocr_space_error = None
        google_tried = False
        ocr_space_tried = False

        # Try Google Vision first (more accurate)
        if self.google_api_key:
            google_tried = True
            text, google_error = self._google_vision_ocr(img_data)
            if text:
                return text, None

        # Fallback to OCR.space
        if self.ocr_space_key:
            ocr_space_tried = True
            text, ocr_space_error = self._ocr_space_ocr(img_data, filename)
            if text:
                return text, None

        # Build error message
        error_msg = ""
        if google_tried and ocr_space_tried:
            if google_error and ocr_space_error:
                error_msg = f"Both OCR APIs failed - Google: {google_error}; OCR.space: {ocr_space_error}"
            elif google_error:
                error_msg = f"Google Vision failed ({google_error}), OCR.space found no text"
            elif ocr_space_error:
                error_msg = f"OCR.space failed ({ocr_space_error}), Google Vision found no text"
            else:
                error_msg = "Both OCR APIs processed OK but found no text."
        elif google_tried:
            error_msg = google_error or "Google Vision API processed but found no text"
        elif ocr_space_tried:
            error_msg = ocr_space_error or "OCR.space API processed but found no text"
        else:
            error_msg = "No OCR API keys configured. Set GOOGLE_CLOUD_VISION_KEY or OCR_SPACE_API_KEY in .env"
        
        return "", error_msg

    def _google_vision_ocr(self, img_data: bytes) -> tuple:
        """Google Cloud Vision API text detection."""
        if not self.google_api_key:
            return "", None

        try:
            b64_image = base64.b64encode(img_data).decode('utf-8')

            payload = {
                "requests": [{
                    "image": {"content": b64_image},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]
                }]
            }

            req = urllib_request.Request(
                "https://vision.googleapis.com/v1/images:annotate",
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'x-goog-api-key': self.google_api_key
                }
            )

            with urllib_request.urlopen(req, timeout=API_TIMEOUT) as response:
                result = json.loads(response.read().decode('utf-8'))

            responses = result.get('responses', [])
            if responses:
                if 'error' in responses[0]:
                    error_msg = responses[0]['error'].get('message', 'Unknown error')
                    return "", f"API error: {error_msg}"
                annotation = responses[0].get('fullTextAnnotation', {})
                text = annotation.get('text', '')
                if text:
                    return text, None
                return "", None
            else:
                return "", "No response from API"

        except HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
                error_json = json.loads(error_body)
                error_msg = error_json.get('error', {}).get('message', str(e.reason))
            except (json.JSONDecodeError, AttributeError):
                error_msg = str(e.reason)
            return "", f"HTTP {e.code}: {error_msg}"
        except URLError as e:
            return "", f"Network error: {e.reason}"
        except Exception as e:
            return "", f"Error: {str(e)}"

    def _ocr_space_ocr(self, img_data: bytes, filename: str) -> tuple:
        """OCR.space API text extraction."""
        if not self.ocr_space_key:
            return "", "OCR.space API key not configured"

        if filename.lower().endswith('.pdf'):
            data_prefix = "data:application/pdf;base64,"
        elif filename.lower().endswith('.png'):
            data_prefix = "data:image/png;base64,"
        else:
            data_prefix = "data:image/jpeg;base64,"

        b64_image = base64.b64encode(img_data).decode('utf-8')
        engine2_error = None
        
        # Try Engine 2 first (better for documents)
        try:
            payload = {
                'apikey': self.ocr_space_key,
                'base64Image': data_prefix + b64_image,
                'language': 'eng',
                'isOverlayRequired': 'false',
                'detectOrientation': 'true',
                'scale': 'true',
                'isTable': 'true',
                'OCREngine': '2',
            }

            data = urllib_parse.urlencode(payload).encode('utf-8')
            req = urllib_request.Request(
                'https://api.ocr.space/parse/image',
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            with urllib_request.urlopen(req, timeout=API_TIMEOUT) as response:
                result = json.loads(response.read().decode('utf-8'))

            if result.get('IsErroredOnProcessing'):
                error_msg = result.get('ErrorMessage', ['Unknown OCR error'])
                if isinstance(error_msg, list):
                    error_msg = '; '.join(error_msg)
                engine2_error = f"Engine 2: {error_msg}"
            else:
                parsed = result.get('ParsedResults', [])
                if parsed:
                    texts = [pr.get('ParsedText', '') for pr in parsed]
                    text = '\n'.join(texts)
                    if text.strip():
                        return text, None
                    engine2_error = "Engine 2 returned empty text"
                else:
                    engine2_error = "Engine 2 returned no results"

        except HTTPError as e:
            engine2_error = f"Engine 2 HTTP error {e.code}"
        except URLError as e:
            return "", f"Network error: {e.reason}"
        except json.JSONDecodeError as e:
            engine2_error = f"Engine 2 JSON decode error: {str(e)}"
        except Exception as e:
            engine2_error = f"Engine 2 error: {str(e)}"

        # Retry with Engine 1 as fallback
        try:
            payload_e1 = {
                'apikey': self.ocr_space_key,
                'base64Image': data_prefix + b64_image,
                'language': 'eng',
                'isOverlayRequired': 'false',
                'detectOrientation': 'true',
                'scale': 'true',
                'isTable': 'true',
                'OCREngine': '1',
            }
            data_e1 = urllib_parse.urlencode(payload_e1).encode('utf-8')
            req_e1 = urllib_request.Request(
                'https://api.ocr.space/parse/image',
                data=data_e1,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            with urllib_request.urlopen(req_e1, timeout=API_TIMEOUT) as response_e1:
                result_e1 = json.loads(response_e1.read().decode('utf-8'))

            if result_e1.get('IsErroredOnProcessing'):
                error_msg = result_e1.get('ErrorMessage', ['Unknown OCR error'])
                if isinstance(error_msg, list):
                    error_msg = '; '.join(error_msg)
                return "", f"Both engines failed - {engine2_error}; Engine 1: {error_msg}"

            parsed_e1 = result_e1.get('ParsedResults', [])
            if parsed_e1:
                texts_e1 = [pr.get('ParsedText', '') for pr in parsed_e1]
                fallback_text = '\n'.join(texts_e1)
                if fallback_text.strip():
                    return fallback_text, None

            return "", f"Both OCR engines returned empty text. {engine2_error}"

        except HTTPError as e:
            return "", f"OCR HTTP error: {e.code}"
        except URLError as e:
            return "", f"Network error: {e.reason}"
        except json.JSONDecodeError as e:
            return "", f"OCR JSON decode error: {str(e)}"
        except Exception as e2:
            return "", f"OCR error: {str(e2)}"

    def _compress_image(self, data: bytes) -> bytes:
        """Compress image for API limits."""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            max_dim = 2000
            if img.width > max_dim or img.height > max_dim:
                ratio = min(max_dim / img.width, max_dim / img.height)
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)

            output = io.BytesIO()
            img.save(output, format='JPEG', quality=80, optimize=True)
            return output.getvalue()
        except ImportError as e:
            _logger.warning(f"PIL not available for image compression: {e}")
            return data
        except Exception as e:
            _logger.warning(f"Image compression failed: {e}")
            return data

    def _parse_transcript_text(self, text: str) -> OCRResult:
        """
        Parse transcript text using SIMPLE SEQUENTIAL MATCHING.
        
        Strategy:
        1. Find ALL course codes with line positions
        2. Find ALL grades with line positions
        3. Sort both by line number
        4. For each course, find the nearest grade AFTER it (within reasonable distance)
        
        This is simpler and more reliable than semester-scoped matching.
        """
        courses = []
        student_name = ""
        student_id = ""
        cgpa = 0.0
        total_credits_from_pdf = 0.0

        lines = text.replace('\r', '\n').split('\n')
        
        # ===== METADATA EXTRACTION =====
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Student ID
            if not student_id:
                id_match = re.search(r'\b(\d{10,})\b', line_clean)
                if id_match:
                    student_id = id_match.group(1)
                id_match2 = re.search(r':\s*(\d{7})\s*(\d)\s*(\d{2})', line_clean)
                if id_match2:
                    student_id = id_match2.group(1) + id_match2.group(2) + id_match2.group(3)
            
            # Student Name
            if 'Student Name' in line_clean:
                for j in range(i + 1, min(i + 10, len(lines))):
                    potential_name = lines[j].strip()
                    if potential_name and len(potential_name) >= 8:
                        if re.match(r'^[A-Za-z\s]{8,}$', potential_name):
                            if potential_name not in ['Student ID', 'Date of Birth', 'Degree Conferred', 
                                                      'Official Transcript', 'Course Title']:
                                student_name = potential_name
                                break
            
            # CGPA
            if 'Cumulative Grade Point Average' in line_clean:
                cgpa_match = re.search(r':\s*(\d+\.\d{1,2})', line_clean)
                if cgpa_match:
                    cgpa = float(cgpa_match.group(1))
            
            # Total Credits
            if 'Total Credits' in line_clean:
                cr_match = re.search(r':\s*(\d+(?:\.\d)?)', line_clean)
                if cr_match:
                    total_credits_from_pdf = float(cr_match.group(1))

        # ===== PASS 1: COLLECT ALL DATA =====
        
        # Course code pattern
        course_code_pattern = re.compile(r'\b([A-Z]{2,4})\s?(\d{3}[A-Z]?)\b')
        
        # Grade patterns (multiple formats)
        grade_patterns = [
            re.compile(r'([123456])\.0\s+([ABCDF][+-]?)\s+\d+\.\d+\s+\d+\.\d+'),  # "3.0 A- 3.0 3.0"
            re.compile(r'^([ABCDF][+-]?)\s+\d+\.\d+\s+\d+\.\d+'),  # "A- 3.0 3.0" at start
            re.compile(r'([123456])\.0\s+([ABCDF][+-]?)(?:\s*$|\s+[A-Z])'),  # "3.0 A-" or "2.0 A"
            re.compile(r'^([ABCDF][+-]?)\s*$'),  # Just "A" or "B+" (standalone)
            re.compile(r'([ABCDF][+-]?)\s+0\.0\s+0\.0'),  # "C 0.0 0.0" (failed)
            re.compile(r'\s([ABCDF][+-]?)\s+\d+\.\d+\s+\d+\.\d+'),  # Grade with CC CP anywhere
            re.compile(r'^\s*([123456])\.0\s+([ABCDF][+-]?)\s*'),  # Simpler: "3.0 A" at line start
            re.compile(r'\b([ABCDF][+-]?)\s+\d+\.\d+\s+\d+\.\d+\b'),  # Grade CC CP anywhere in line
        ]
        
        # Find ALL semester headers with their line numbers
        # Also track TGPA/CGPA lines as block delimiters
        semester_headers = []  # [(line_num, semester), ...]
        block_ends = []  # Line numbers where semester blocks end (TGPA/CGPA lines)
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            sem_match = re.search(r'(Spring|Summer|Fall)\s+(\d{4})', line_clean, re.IGNORECASE)
            if sem_match:
                semester = f"{sem_match.group(1).capitalize()} {sem_match.group(2)}"
                semester_headers.append((i, semester))
            
            # TGPA/CGPA lines mark end of semester data
            if re.search(r'TGPA|CGPA|Semester Credit', line_clean):
                block_ends.append(i)
        
        _logger.debug(f"Found {len(semester_headers)} semester headers")
        
        # Sort semester headers by line number
        semester_headers.sort(key=lambda x: x[0])
        
        # Build semester ranges: each semester header is valid until the next one
        # or until a TGPA/CGPA line, whichever comes first
        semester_ranges = []  # [(start, end, semester), ...]
        
        for idx, (sem_line, semester) in enumerate(semester_headers):
            start = sem_line
            
            # End is either next semester header, or end of file
            if idx + 1 < len(semester_headers):
                end = semester_headers[idx + 1][0] - 1
            else:
                end = len(lines)
            
            semester_ranges.append((start, end, semester))
        
        # For each course, find which semester range it falls into
        def get_semester_for_line(line_num):
            for start, end, semester in semester_ranges:
                if start <= line_num <= end:
                    return semester
            
            # Fallback: find most recent header before this line
            best = ""
            for sem_line, semester in semester_headers:
                if sem_line <= line_num:
                    best = semester
            return best
        
        # Collect ALL course codes
        all_courses = []  # [(code, line_num, semester), ...]
        seen_code_in_line = {}  # Track course codes per line to avoid duplicates
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            
            # Skip summary stats lines (but NOT lines that just happen to be near "Summary")
            if 'Total Credits Counted' in line_clean and ':' in line_clean:
                continue
            if 'Total Credits Passed' in line_clean and ':' in line_clean:
                continue
            if 'Total Grade Points' in line_clean and ':' in line_clean:
                continue
            
            for match in course_code_pattern.finditer(line_clean):
                prefix = match.group(1).upper()
                number = match.group(2).upper()
                
                if prefix not in ALL_COURSE_PREFIXES:
                    continue
                
                code = prefix + number
                
                # Skip if we already found this code in this line
                line_key = (code, i)
                if line_key in seen_code_in_line:
                    continue
                seen_code_in_line[line_key] = True
                
                semester = get_semester_for_line(i)
                all_courses.append((code, i, semester))
                if not semester:
                    _logger.debug(f"Course {code} at line {i} has no semester")
        
        _logger.info(f"Found {len(all_courses)} course codes in OCR")
        
        # Collect ALL grades
        all_grades = []  # [(grade, credits, line_num, is_failed), ...]
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            
            # Check for failed pattern "C 0.0 0.0" or "D+ 0.0 0.0"
            is_failed = bool(re.search(r'0\.0\s+0\.0', line_clean))
            
            grade_found = None
            credits_found = 3.0
            
            # Try pattern 5: Failed pattern "C 0.0 0.0"
            match = grade_patterns[4].search(line_clean)
            if match:
                grade_found = match.group(1).upper()
                is_failed = True
                # Look back for credits
                for j in range(max(0, i-8), i):
                    cr_match = re.search(r'\b([123456])\.0\b', lines[j])
                    if cr_match:
                        credits_found = float(cr_match.group(1))
                        break
            
            # Try pattern 1: "3.0 A- 3.0 3.0"
            if not grade_found:
                match = grade_patterns[0].search(line_clean)
                if match:
                    credits_found = float(match.group(1))
                    grade_found = match.group(2).upper()
            
            # Try pattern 2: "A- 3.0 3.0"
            if not grade_found:
                match = grade_patterns[1].match(line_clean)
                if match:
                    grade_found = match.group(1).upper()
                    # Look back for credits
                    for j in range(max(0, i-8), i):
                        cr_match = re.search(r'\b([123456])\.0\b', lines[j])
                        if cr_match:
                            credits_found = float(cr_match.group(1))
                            break
            
            # Try pattern 3: "3.0 A-"
            if not grade_found:
                match = grade_patterns[2].search(line_clean)
                if match:
                    credits_found = float(match.group(1))
                    grade_found = match.group(2).upper()
            
            # Try pattern 4: Just "A", "B+", "C-" (single grade letter)
            if not grade_found:
                match = grade_patterns[3].match(line_clean)
                if match:
                    grade_found = match.group(1).upper()
                    # Look back for credits
                    for j in range(max(0, i-8), i):
                        cr_match = re.search(r'\b([123456])\.0\b', lines[j])
                        if cr_match:
                            credits_found = float(cr_match.group(1))
                            break
            
            # Try pattern 6: Grade anywhere in line (with CC CP format)
            if not grade_found:
                match = grade_patterns[5].search(line_clean)
                if match:
                    grade_found = match.group(1).upper()
                    # Look back for credits
                    for j in range(max(0, i-8), i):
                        cr_match = re.search(r'\b([123456])\.0\b', lines[j])
                        if cr_match:
                            credits_found = float(cr_match.group(1))
                            break
            
            # Try pattern 7: Simple "3.0 A" at line start (last resort)
            if not grade_found:
                match = grade_patterns[6].match(line_clean)
                if match:
                    credits_found = float(match.group(1))
                    grade_found = match.group(2).upper()
            
            # Try pattern 8: Grade CC CP anywhere in line (broadest match)
            if not grade_found:
                match = grade_patterns[7].search(line_clean)
                if match:
                    grade_found = match.group(1).upper()
                    # Look back for credits
                    for j in range(max(0, i-8), i):
                        cr_match = re.search(r'\b([123456])\.0\b', lines[j])
                        if cr_match:
                            credits_found = float(cr_match.group(1))
                            break
            
            if grade_found:
                all_grades.append((grade_found, credits_found, i, is_failed))
        
        _logger.info(f"Found {len(all_grades)} grades in OCR")
        
        # ===== PASS 2: SEQUENTIAL LINE-ORDER MATCHING =====
        # Strategy: Process courses in line order, assign grades in line order
        # This ensures clustered courses get sequential grades
        
        all_courses.sort(key=lambda x: x[1])  # Sort by line number
        all_grades.sort(key=lambda x: x[2])   # Sort by line number
        
        used_grades = set()
        matched = []
        
        # Track next expected grade index for sequential matching
        next_grade_idx = 0
        
        # FIRST PASS: Sequential matching - each course gets the next available grade within range
        remaining_courses = []
        for code, code_line, semester in all_courses:
            best_grade = None
            best_grade_idx = -1
            best_distance = float('inf')
            
            # Start searching from next_grade_idx to maintain sequence
            for g_idx in range(len(all_grades)):
                if g_idx in used_grades:
                    continue
                    
                grade, credits, grade_line, is_failed = all_grades[g_idx]
                
                # Grade must be within reasonable range (15 lines before to 20 lines after)
                if grade_line < code_line - 15:
                    continue
                if grade_line > code_line + 20:
                    break  # Grades are sorted, stop looking
                
                distance = abs(grade_line - code_line)
                if distance < best_distance:
                    best_grade = (grade, credits, is_failed)
                    best_grade_idx = g_idx
                    best_distance = distance
            
            if best_grade:
                grade, credits, is_failed = best_grade
                used_grades.add(best_grade_idx)
                matched.append((code, credits, grade, semester, code_line, is_failed))
                _logger.debug(f"TIGHT matched: {code} (line {code_line}) -> {grade} ({credits} cr)")
            else:
                remaining_courses.append((code, code_line, semester))
        
        _logger.info(f"After tight pass: {len(matched)} matched, {len(remaining_courses)} remaining")
        
        # SECOND PASS: Medium window (within 60 lines)
        still_remaining = []
        for code, code_line, semester in remaining_courses:
            best_grade = None
            best_grade_idx = -1
            best_distance = float('inf')
            
            for g_idx, (grade, credits, grade_line, is_failed) in enumerate(all_grades):
                if g_idx in used_grades:
                    continue
                
                # Grade can be up to 30 lines before, 60 lines after
                if grade_line < code_line - 30:
                    continue
                    
                distance = abs(grade_line - code_line)
                if distance <= 60 and distance < best_distance:
                    best_grade = (grade, credits, is_failed)
                    best_grade_idx = g_idx
                    best_distance = distance
            
            if best_grade:
                grade, credits, is_failed = best_grade
                used_grades.add(best_grade_idx)
                matched.append((code, credits, grade, semester, code_line, is_failed))
                _logger.debug(f"MEDIUM matched: {code} (line {code_line}) -> {grade} ({credits} cr)")
            else:
                still_remaining.append((code, code_line, semester))
        
        unmatched_courses = still_remaining
        _logger.info(f"After medium pass: {len(matched)} matched, {len(unmatched_courses)} remaining")
        
        # FALLBACK PASS: Try wider window for unmatched
        if unmatched_courses:
            _logger.info(f"FALLBACK: Trying to match {len(unmatched_courses)} unmatched courses")
            still_unmatched = []
            for code, code_line, semester in unmatched_courses:
                best_grade = None
                best_grade_idx = -1
                best_distance = float('inf')
                
                for g_idx, (grade, credits, grade_line, is_failed) in enumerate(all_grades):
                    if g_idx in used_grades:
                        continue
                    
                    # Allow MUCH wider window - 150 lines forward, 50 lines back
                    distance = abs(grade_line - code_line)
                    if grade_line >= code_line - 50 and distance <= 150:
                        if distance < best_distance:
                            best_grade = (grade, credits, is_failed)
                            best_grade_idx = g_idx
                            best_distance = distance
                
                if best_grade:
                    grade, credits, is_failed = best_grade
                    used_grades.add(best_grade_idx)
                    matched.append((code, credits, grade, semester, code_line, is_failed))
                    _logger.debug(f"FALLBACK matched: {code} -> {grade}")
                else:
                    still_unmatched.append((code, code_line, semester))
            
            # LAST RESORT: Assign ANY remaining unused grade to unmatched courses
            if still_unmatched:
                _logger.info(f"LAST RESORT: {len(still_unmatched)} courses still need grades")
                final_unmatched = []
                
                # Get all unused grades
                unused_grades = [(g_idx, g) for g_idx, g in enumerate(all_grades) if g_idx not in used_grades]
                unused_idx = 0
                
                for code, code_line, semester in still_unmatched:
                    if unused_idx < len(unused_grades):
                        g_idx, (grade, credits, grade_line, is_failed) = unused_grades[unused_idx]
                        used_grades.add(g_idx)
                        matched.append((code, credits, grade, semester, code_line, is_failed))
                        _logger.debug(f"LAST RESORT matched: {code} -> {grade} ({credits} cr)")
                        unused_idx += 1
                    else:
                        # ULTRA FALLBACK: Scan the course's own line and nearby lines for ANY grade letter
                        found_grade = None
                        search_range = range(max(0, code_line - 5), min(len(lines), code_line + 10))
                        for scan_line in search_range:
                            line_text = lines[scan_line].strip()
                            # Look for standalone grade letters
                            grade_match = re.search(r'\b([ABCDF][+-]?)\b', line_text)
                            if grade_match:
                                potential_grade = grade_match.group(1)
                                # Verify it's a valid grade (not part of course code like "EEE")
                                if potential_grade not in ('E', 'EE', 'EEE'):
                                    found_grade = potential_grade
                                    _logger.debug(f"ULTRA FALLBACK: Found {code} -> {found_grade} at line {scan_line}")
                                    break
                        
                        if found_grade:
                            matched.append((code, 3.0, found_grade, semester, code_line, False))
                        else:
                            final_unmatched.append((code, code_line, semester))
                
                still_unmatched = final_unmatched
            
            if still_unmatched:
                _logger.warning(f"Still unmatched after fallback: {[c[0] for c in still_unmatched]}")
        
        _logger.info(f"Matched {len(matched)} courses total")
        
        # Build final course list
        for code, credits, grade, semester, line_num, is_failed in matched:
            courses.append(CourseRecord(
                course_code=code,
                credits=credits,
                grade=grade,
                semester=semester,
                confidence=0.90 if not is_failed else 0.85
            ))
        
        # SORT CHRONOLOGICALLY by semester (year, then Spring->Summer->Fall)
        def semester_sort_key(course):
            sem = course.semester
            if sem:
                parts = sem.split()
                if len(parts) == 2:
                    season_order = {'Spring': 0, 'Summer': 1, 'Fall': 2}
                    try:
                        year = int(parts[1])
                        season = season_order.get(parts[0], 3)
                        return (year, season, course.course_code)
                    except ValueError:
                        pass
            return (9999, 9, course.course_code)
        
        courses.sort(key=semester_sort_key)
        
        # Log unmatched
        unmatched_count = len(all_courses) - len(matched)
        if unmatched_count > 0:
            _logger.warning(f"Could not match {unmatched_count} courses to grades")

        raw_text = [w for w in text.split() if w.strip()][:100]

        return OCRResult(
            success=True,
            courses=courses,
            raw_text=raw_text,
            student_name=student_name,
            student_id=student_id,
            cgpa=cgpa,
            total_credits=total_credits_from_pdf
        )
    
    def _is_watermark_only(self, line: str) -> bool:
        """Check if line contains only watermark text."""
        if not line or len(line) < 3:
            return True
        
        line_upper = line.upper().strip()
        
        # Pure watermark patterns
        watermarks = [
            'NORTH SOUTH', 'UNIVERSITY', 'NIVERSITY', 'IVERSITY', 'VERSITY',
            'ERSITY', 'RTH SO', 'ORTH SC', 'TH SOUTH', 'SOUTH UNIV',
            'NORTH S', 'RTH SOUTH', 'OUTH UNIV', 'UNIVER', 'IVERSIT'
        ]
        
        # If the line is short and matches watermark, skip it
        if len(line_upper) < 25:
            for w in watermarks:
                if w in line_upper:
                    # But don't skip if it has a course code
                    if re.search(r'[A-Z]{3}\s?\d{3}', line_upper):
                        return False
                    return True
        
        return False


# Alias for compatibility
TranscriptOCR = WebOCR


def main():
    """Test CLI."""
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ocr_web.py <file.pdf|image.png>")
        print("\nOCR Engines:")
        print(f"  Google Vision: {'Configured' if GOOGLE_VISION_API_KEY else 'Not configured'}")
        print(f"  OCR.space: Available (free tier)")
        print("\nTo use Google Vision (most accurate):")
        print("  set GOOGLE_VISION_API_KEY=your_key")
        sys.exit(1)

    ocr = WebOCR()
    result = ocr.extract(sys.argv[1])

    if result.success:
        print(f"\n[OK] Extracted {result.course_count} courses")
        print(f"  Engine: {result.engine_used}")
        print(f"  Student ID: {result.student_id or 'N/A'}")
        print(f"  CGPA: {result.cgpa or 'N/A'}")
        print("\nCSV Output:")
        print(result.csv_data)
    else:
        print(f"[ERROR] {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
