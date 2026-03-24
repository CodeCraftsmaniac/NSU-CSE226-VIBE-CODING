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

# API Keys
GOOGLE_VISION_API_KEY = os.environ.get('GOOGLE_VISION_API_KEY', '')
OCR_SPACE_API_KEY = os.environ.get('OCR_SPACE_API_KEY', 'K85483682688957')

VALID_GRADES = {'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F', 'W', 'I', 'P', 'TR'}
COURSE_PATTERN = re.compile(r'^([A-Z]{2,4})(\d{3}[A-Z]?)$')
SEMESTER_PATTERN = re.compile(r'(Spring|Summer|Fall)\s*(\d{4})', re.IGNORECASE)

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

# OCR corrections for common misreads
OCR_CORRECTIONS = {
    '8+': 'B+', '8-': 'B-', '8': 'B',
    'A+': 'A', 'A1': 'A-', 'Al': 'A-', 'A|': 'A-',
    'C1': 'C-', 'D1': 'D+', '0': 'D', 'O': 'D',
    'Bt': 'B+', 'B1': 'B-', 'Ct': 'C+', 'Dt': 'D+',
    'At': 'A-', 'A~': 'A-', 'B~': 'B-', 'C~': 'C-',
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

        Strategy:
        1. Find course codes (XXX123 format)
        2. Look for credits and grades nearby
        3. Track semester context
        4. Handle table format (Course | Credits | Grade)
        """
        courses = []
        student_name = ""
        student_id = ""
        cgpa = 0.0
        current_semester = ""
        seen_courses = set()

        lines = text.replace('\r', '\n').split('\n')

        # First pass: extract metadata
        for line in lines:
            line_clean = line.strip()

            # Student ID (10+ digit number)
            if not student_id:
                id_match = re.search(r'\b(\d{10,})\b', line_clean)
                if id_match:
                    student_id = id_match.group(1)

            # CGPA
            if 'CGPA' in line_clean.upper() or 'Cumulative' in line_clean:
                cgpa_match = re.search(r'(\d+\.\d{1,2})', line_clean)
                if cgpa_match:
                    try:
                        cgpa = float(cgpa_match.group(1))
                    except:
                        pass

        # Second pass: extract courses
        for i, line in enumerate(lines):
            line_clean = line.strip()

            # Semester detection
            sem_match = SEMESTER_PATTERN.search(line_clean)
            if sem_match:
                current_semester = f"{sem_match.group(1)} {sem_match.group(2)}"
                continue

            # Look for course patterns in the line
            # Pattern 1: Line-based format (course code on same line as credits/grade)
            # Example: "CSE115 3 A" or "CSE 115   3.0   A-"

            # Find all potential course codes in this line
            course_matches = list(re.finditer(r'\b([A-Z]{2,4})[\s-]?(\d{3}[A-Z]?)\b', line_clean))

            for match in course_matches:
                prefix = match.group(1)
                number = match.group(2)
                course_code = prefix + number

                # Skip if already seen
                if course_code in seen_courses:
                    continue

                # Look for credits and grade after the course code
                after_course = line_clean[match.end():]

                # Try to find credits (1-4 digit number, possibly with decimal)
                credits = 0.0
                credit_match = re.search(r'\b(\d{1,2}(?:\.\d)?)\b', after_course)
                if credit_match:
                    try:
                        val = float(credit_match.group(1))
                        if 0 <= val <= 10:
                            credits = val
                    except:
                        pass

                # Try to find grade
                grade = ""
                for g in VALID_GRADES:
                    if re.search(r'\b' + re.escape(g) + r'\b', after_course):
                        grade = g
                        break

                # Also check for OCR-misread grades
                if not grade:
                    for wrong, correct in OCR_CORRECTIONS.items():
                        if re.search(r'\b' + re.escape(wrong) + r'\b', after_course):
                            grade = correct
                            break

                # If no grade found on same line, check next few lines
                if not grade and i + 1 < len(lines):
                    for j in range(i + 1, min(i + 4, len(lines))):
                        next_line = lines[j].strip()

                        # Stop if we hit another course
                        if re.search(r'\b[A-Z]{2,4}\d{3}[A-Z]?\b', next_line):
                            break

                        for g in VALID_GRADES:
                            if re.search(r'\b' + re.escape(g) + r'\b', next_line):
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
                        semester=current_semester
                    ))

        # Build raw text list for frontend display
        raw_text = [w for w in text.split() if w.strip()][:100]

        return OCRResult(
            success=True,
            courses=courses,
            raw_text=raw_text,
            student_name=student_name,
            student_id=student_id,
            cgpa=cgpa
        )


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
