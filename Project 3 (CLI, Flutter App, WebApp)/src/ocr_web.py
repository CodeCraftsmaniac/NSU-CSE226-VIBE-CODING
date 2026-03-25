"""
ocr_web.py  —  Improved Web-based OCR for NSU Transcript Extraction
=====================================================================
Features:
1. Google Cloud Vision API (1000 free/month) - Most accurate
2. OCR.space API (500 free/month) - Good fallback
3. Native PDF text extraction - For digital PDFs
4. Improved table parsing logic

Setup Google Vision (recommended for accuracy):
1. Go to https://console.cloud.google.com/
2. Create project -> Enable Cloud Vision API
3. Create API key -> Copy the key
4. Set environment variable: GOOGLE_VISION_API_KEY=your_key

Or just use OCR.space (works without setup, 500 free/month)
"""

import os
import re
import io
import base64
import json
import tempfile
import warnings
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from pathlib import Path
from urllib import request as urllib_request
from urllib import parse as urllib_parse
from urllib.error import URLError, HTTPError

warnings.filterwarnings('ignore')

# Load environment variables if dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

# API Keys - Load from environment with fallback defaults
GOOGLE_VISION_API_KEY = os.environ.get('GOOGLE_CLOUD_VISION_KEY') or os.environ.get('GOOGLE_VISION_API_KEY', '')
OCR_SPACE_API_KEY = os.environ.get('OCR_SPACE_API_KEY', 'K85858573688957')

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
    'ACC', 'MNS', 'BME', 'CEE', 'IPE', 'TEX', 'AER', 'NFS',  # More
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
        self.google_api_key = google_api_key or GOOGLE_VISION_API_KEY
        self.ocr_space_key = ocr_space_key or OCR_SPACE_API_KEY
        self.progress_callback = progress_callback

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
        if len(full_text) > 500:
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
        for i, page in enumerate(doc):
            self._report("page", 30 + (i / len(doc)) * 50, f"OCR page {i+1}/{len(doc)}...")

            # Render page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img_data = pix.tobytes("png")

            # Try Google Vision first, then OCR.space
            page_text = self._ocr_image(img_data, "page.png")
            if page_text:
                ocr_text += page_text + "\n"

        doc.close()

        if not ocr_text.strip():
            return OCRResult(success=False, error="OCR returned no text")

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
        text = self._ocr_image(img_data, path.name)

        if not text:
            return OCRResult(success=False, error="OCR returned no text")

        self._report("parse", 80, "Parsing...")
        result = self._parse_transcript_text(text)
        result.engine_used = "Google Vision" if self.google_api_key else "OCR.space"
        result.confidence_score = 0.85

        self._report("complete", 100, "Done!")
        return result

    def _ocr_image(self, img_data: bytes, filename: str) -> str:
        """Run OCR on image data using available API."""
        # Try Google Vision first (more accurate)
        if self.google_api_key:
            text = self._google_vision_ocr(img_data)
            if text:
                return text

        # Fallback to OCR.space
        return self._ocr_space_ocr(img_data, filename)

    def _google_vision_ocr(self, img_data: bytes) -> str:
        """Google Cloud Vision API text detection."""
        if not self.google_api_key:
            return ""

        try:
            b64_image = base64.b64encode(img_data).decode('utf-8')

            payload = {
                "requests": [{
                    "image": {"content": b64_image},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]
                }]
            }

            url = f"https://vision.googleapis.com/v1/images:annotate?key={self.google_api_key}"
            req = urllib_request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )

            with urllib_request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))

            responses = result.get('responses', [])
            if responses:
                annotation = responses[0].get('fullTextAnnotation', {})
                return annotation.get('text', '')

        except Exception as e:
            print(f"Google Vision error: {e}")

        return ""

    def _ocr_space_ocr(self, img_data: bytes, filename: str) -> str:
        """OCR.space API text extraction."""
        try:
            b64_image = base64.b64encode(img_data).decode('utf-8')

            if filename.lower().endswith('.pdf'):
                data_prefix = "data:application/pdf;base64,"
            elif filename.lower().endswith('.png'):
                data_prefix = "data:image/png;base64,"
            else:
                data_prefix = "data:image/jpeg;base64,"

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

            with urllib_request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))

            if result.get('IsErroredOnProcessing'):
                return ""

            parsed = result.get('ParsedResults', [])
            texts = [pr.get('ParsedText', '') for pr in parsed]
            return '\n'.join(texts)

        except Exception as e:
            print(f"OCR.space error: {e}")

        return ""

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
        except:
            return data

    def _parse_transcript_text(self, text: str) -> OCRResult:
        """
        Parse transcript text into structured course data.

        Multi-pass Strategy:
        1. Pass 1: Extract full-line patterns (course+credits+grade on one line)
        2. Pass 2: Extract courses with grades/credits on nearby lines
        3. Pass 3: Validate and deduplicate
        """
        courses = []
        student_name = ""
        student_id = ""
        cgpa = 0.0
        total_credits_from_pdf = 0.0
        current_semester = ""
        seen_courses = set()

        lines = text.replace('\r', '\n').split('\n')

        # First pass: extract metadata and summary section
        for line in lines:
            line_clean = line.strip()

            # Student ID (10+ digit number)
            if not student_id:
                id_match = re.search(r'\b(\d{10,})\b', line_clean)
                if id_match:
                    student_id = id_match.group(1)

            # CGPA from summary section
            if 'CGPA' in line_clean.upper() or 'Cumulative' in line_clean:
                cgpa_match = re.search(r'(\d+\.\d{1,2})', line_clean)
                if cgpa_match:
                    try:
                        val = float(cgpa_match.group(1))
                        if 0 <= val <= 4.0:
                            cgpa = val
                    except:
                        pass

            # Total credits from summary
            if 'Total Credit' in line_clean or 'Credits Earned' in line_clean:
                cr_match = re.search(r'(\d+(?:\.\d)?)', line_clean)
                if cr_match:
                    try:
                        total_credits_from_pdf = float(cr_match.group(1))
                    except:
                        pass

        # Pass 1: Full-line extraction (most accurate when available)
        for i, line in enumerate(lines):
            line_clean = line.strip()

            # Update semester context
            sem_match = SEMESTER_PATTERN.search(line_clean)
            if sem_match:
                current_semester = f"{sem_match.group(1).capitalize()} {sem_match.group(2)}"
                continue

            # Try full-line pattern first (course, credits, grade on same line)
            full_matches = list(FULL_LINE_PATTERN.finditer(line_clean))
            for match in full_matches:
                prefix = match.group(1).upper()
                number = match.group(2).upper()
                credits = float(match.group(3))
                grade = match.group(4).upper()

                # Apply OCR corrections to grade
                grade = OCR_CORRECTIONS.get(grade, grade)

                course_code = prefix + number
                if course_code not in seen_courses and grade in VALID_GRADES:
                    seen_courses.add(course_code)
                    courses.append(CourseRecord(
                        course_code=course_code,
                        credits=credits,
                        grade=grade,
                        semester=current_semester,
                        confidence=0.95
                    ))

        # Pass 2: Look for courses without full-line match
        for i, line in enumerate(lines):
            line_clean = line.strip()

            # Update semester context
            sem_match = SEMESTER_PATTERN.search(line_clean)
            if sem_match:
                current_semester = f"{sem_match.group(1).capitalize()} {sem_match.group(2)}"
                continue

            # Find course codes
            course_matches = list(re.finditer(r'\b([A-Z]{2,4})[\s-]?(\d{3}[A-Z]?)\b', line_clean))

            for match in course_matches:
                prefix = match.group(1).upper()
                number = match.group(2).upper()
                course_code = prefix + number

                # Skip if already found
                if course_code in seen_courses:
                    continue

                # Look for credits and grade after the course code
                after_course = line_clean[match.end():]

                # Find credits (number 0-10, possibly with decimal)
                credits = 0.0
                credit_match = re.search(r'\b(\d{1,2}(?:\.\d)?)\b', after_course)
                if credit_match:
                    try:
                        val = float(credit_match.group(1))
                        if 0 <= val <= 10:
                            credits = val
                    except:
                        pass

                # Find grade - check for valid grades and OCR corrections
                grade = ""

                # First try valid grades
                for g in VALID_GRADES:
                    pattern = r'\b' + re.escape(g) + r'\b'
                    if re.search(pattern, after_course, re.IGNORECASE):
                        grade = g
                        break

                # Then try OCR corrections
                if not grade:
                    for wrong, correct in OCR_CORRECTIONS.items():
                        if re.search(r'\b' + re.escape(wrong) + r'\b', after_course):
                            grade = correct
                            break

                # If no grade on same line, check next few lines
                if not grade and i + 1 < len(lines):
                    for j in range(i + 1, min(i + 4, len(lines))):
                        next_line = lines[j].strip()

                        # Stop if we hit another course code
                        if re.search(r'\b[A-Z]{2,4}\s*\d{3}[A-Z]?\b', next_line):
                            break

                        # Look for grade
                        for g in VALID_GRADES:
                            if re.search(r'\b' + re.escape(g) + r'\b', next_line, re.IGNORECASE):
                                grade = g
                                break

                        if grade:
                            break

                        # Also look for credits if not found
                        if credits == 0.0:
                            cm = re.search(r'\b(\d{1,2}(?:\.\d)?)\b', next_line)
                            if cm:
                                try:
                                    val = float(cm.group(1))
                                    if 0 < val <= 10:
                                        credits = val
                                except:
                                    pass

                # Add course if we have at least a grade
                if grade:
                    seen_courses.add(course_code)
                    courses.append(CourseRecord(
                        course_code=course_code,
                        credits=credits,
                        grade=grade,
                        semester=current_semester,
                        confidence=0.85 if credits > 0 else 0.70
                    ))

        # Pass 3: Validate and sort courses
        validated_courses = []
        for course in courses:
            # Ensure grade is valid
            if course.grade in VALID_GRADES:
                validated_courses.append(course)

        # Sort by semester if available, then by course code
        def sort_key(c):
            if c.semester:
                parts = c.semester.split()
                if len(parts) == 2:
                    season_order = {'Spring': 0, 'Summer': 1, 'Fall': 2}
                    return (int(parts[1]), season_order.get(parts[0], 3), c.course_code)
            return (9999, 9, c.course_code)

        validated_courses.sort(key=sort_key)

        # Build raw text list for frontend display
        raw_text = [w for w in text.split() if w.strip()][:100]

        result = OCRResult(
            success=True,
            courses=validated_courses,
            raw_text=raw_text,
            student_name=student_name,
            student_id=student_id,
            cgpa=cgpa,
            total_credits=total_credits_from_pdf
        )

        return result


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
