"""
ocr_web.py  —  Lightweight Web-based OCR for NSU Transcript Extraction
=======================================================================
Uses FREE OCR.space API (500 requests/month) for fast, reliable extraction.
No heavy model downloads. No GPU required. Works immediately.

OCR.space Free Tier:
- 500 requests/month (plenty for 20-30 scans)
- 1MB file size limit (we compress images)
- Supports PDF and images

Fallback: PyMuPDF text extraction for digital PDFs

Usage:
    from ocr_web import WebOCR
    ocr = WebOCR()
    result = ocr.extract("transcript.pdf")
    print(result.csv_data)
"""

import os
import re
import io
import base64
import tempfile
import warnings
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from pathlib import Path

warnings.filterwarnings('ignore')

# OCR.space Free API Key (free tier - 500 requests/month)
# Get your own key at: https://ocr.space/ocrapi/freekey
OCR_SPACE_API_KEY = "K85483682688957"  # Free demo key

VALID_GRADES = {'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F', 'W', 'I', 'P', 'TR'}
COURSE_PATTERN = re.compile(r'^([A-Z]{2,4})(\d{3}[A-Z]?)$')
SEMESTER_PATTERN = re.compile(r'(Spring|Summer|Fall)\s*(\d{4})', re.IGNORECASE)

NSU_COURSE_PREFIXES = {
    'CSE', 'EEE', 'ECE', 'MAT', 'PHY', 'CHE', 'ENG', 'BEN', 'BIO',
    'ENV', 'ECO', 'BUS', 'ACT', 'FIN', 'MKT', 'MGT', 'MIS', 'HRM',
    'SOC', 'POL', 'HIS', 'PHI', 'ANT', 'PSY', 'ARC', 'LAW', 'ESL',
    'GEN', 'COM', 'MED', 'PHA', 'PUB', 'MPH', 'STA', 'IST', 'LIN',
    'JMS', 'CIS', 'MSC', 'NST'
}

# Common OCR corrections
OCR_CORRECTIONS = {
    '8+': 'B+', '8-': 'B-', '8': 'B',
    'A+': 'A', 'A1': 'A-', 'Al': 'A-',
    'C1': 'C-', 'D1': 'D+', '0': 'D', 'O': 'D',
    'Bt': 'B+', 'B1': 'B-', 'Ct': 'C+', 'Dt': 'D+',
}


@dataclass
class CourseRecord:
    """Represents a single course entry."""
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

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "error": self.error,
            "student_name": self.student_name,
            "student_id": self.student_id,
            "cgpa": self.cgpa,
            "total_credits": self.total_credits,
            "course_count": self.course_count,
            "engine_used": self.engine_used,
            "confidence_score": self.confidence_score,
            "courses": [
                {
                    "course_code": c.course_code,
                    "credits": c.credits,
                    "grade": c.grade,
                    "semester": c.semester
                }
                for c in self.courses
            ],
            "csv_data": self.csv_data
        }


class WebOCR:
    """
    Lightweight OCR using OCR.space free API.

    Benefits:
    - No heavy model downloads (works immediately)
    - Free tier: 500 requests/month
    - Fast response times
    - Reliable service
    """

    def __init__(self, api_key: str = None, progress_callback=None):
        self.api_key = api_key or OCR_SPACE_API_KEY
        self.progress_callback = progress_callback

    def _report_progress(self, stage: str, progress: float, text: str = ""):
        if self.progress_callback:
            self.progress_callback(stage, progress, text)

    def extract(self, file_path: str) -> OCRResult:
        """Extract transcript data from PDF or image."""
        path = Path(file_path)

        if not path.exists():
            return OCRResult(success=False, error=f"File not found: {file_path}")

        ext = path.suffix.lower()

        try:
            self._report_progress("init", 5, "Initializing OCR...")

            if ext == '.pdf':
                return self._extract_from_pdf(path)
            elif ext in {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}:
                return self._extract_from_image(path)
            else:
                return OCRResult(success=False, error=f"Unsupported file type: {ext}")
        except Exception as e:
            return OCRResult(success=False, error=str(e))

    def _extract_from_pdf(self, path: Path) -> OCRResult:
        """Extract from PDF - try native text first, then OCR."""
        import fitz  # PyMuPDF

        self._report_progress("pdf", 10, "Opening PDF...")

        doc = fitz.open(str(path))
        all_text = []
        total_pages = len(doc)

        # First, try to extract native text (for digital PDFs)
        self._report_progress("text", 20, "Extracting embedded text...")

        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                all_text.extend(text.split())

        # If we got good text, parse it
        if len(all_text) > 50:  # Likely has readable text
            doc.close()
            self._report_progress("parse", 70, "Parsing transcript...")
            result = self._parse_transcript(all_text)
            result.engine_used = "PyMuPDF (native text)"
            result.confidence_score = 0.95
            result.raw_text = all_text[:100]
            self._report_progress("complete", 100, "Complete!")
            return result

        # Otherwise, OCR each page as image
        self._report_progress("ocr", 30, "Running OCR on scanned pages...")
        all_text = []

        for page_num in range(total_pages):
            progress = 30 + (page_num / total_pages) * 50
            self._report_progress("page", progress, f"OCR page {page_num + 1}/{total_pages}...")

            page = doc[page_num]

            # Render page to image
            mat = fitz.Matrix(2.0, 2.0)  # 2x scale for better OCR
            pix = page.get_pixmap(matrix=mat)

            # Compress to JPEG if too large (OCR.space limit: 1MB)
            img_data = pix.tobytes("jpeg")

            # If still too large, reduce quality
            if len(img_data) > 900000:
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_data = pix.tobytes("jpeg")

            # OCR the image
            page_text = self._ocr_via_api(img_data, "page.jpg")
            if page_text:
                all_text.extend(page_text.split())

        doc.close()

        self._report_progress("parse", 85, "Parsing transcript data...")
        result = self._parse_transcript(all_text)
        result.engine_used = "OCR.space API"
        result.confidence_score = 0.85
        result.raw_text = all_text[:100]

        self._report_progress("complete", 100, "Extraction complete!")
        return result

    def _extract_from_image(self, path: Path) -> OCRResult:
        """Extract from image using OCR.space API."""
        self._report_progress("image", 20, "Reading image...")

        # Read and possibly compress image
        with open(path, 'rb') as f:
            img_data = f.read()

        # Compress if too large
        if len(img_data) > 900000:
            self._report_progress("compress", 30, "Compressing image...")
            img_data = self._compress_image(img_data, path.suffix)

        self._report_progress("ocr", 40, "Running OCR...")

        text = self._ocr_via_api(img_data, path.name)

        if not text:
            return OCRResult(success=False, error="OCR extraction returned no text")

        all_text = text.split()

        self._report_progress("parse", 80, "Parsing transcript...")
        result = self._parse_transcript(all_text)
        result.engine_used = "OCR.space API"
        result.confidence_score = 0.85
        result.raw_text = all_text[:100]

        self._report_progress("complete", 100, "Complete!")
        return result

    def _compress_image(self, data: bytes, suffix: str) -> bytes:
        """Compress image to fit OCR.space 1MB limit."""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data))

            # Convert to RGB if needed
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Resize if very large
            max_dim = 2000
            if img.width > max_dim or img.height > max_dim:
                ratio = min(max_dim / img.width, max_dim / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)

            # Save as JPEG with compression
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=80, optimize=True)
            return output.getvalue()
        except Exception:
            return data

    def _ocr_via_api(self, img_data: bytes, filename: str) -> str:
        """Call OCR.space API for text extraction."""
        import urllib.request
        import urllib.parse
        import json

        try:
            # Encode image as base64
            b64_image = base64.b64encode(img_data).decode('utf-8')

            # Determine file type
            if filename.lower().endswith('.pdf'):
                filetype = "PDF"
                data_prefix = "data:application/pdf;base64,"
            elif filename.lower().endswith('.png'):
                filetype = "PNG"
                data_prefix = "data:image/png;base64,"
            else:
                filetype = "JPG"
                data_prefix = "data:image/jpeg;base64,"

            # Prepare API request
            payload = {
                'apikey': self.api_key,
                'base64Image': data_prefix + b64_image,
                'language': 'eng',
                'isOverlayRequired': 'false',
                'detectOrientation': 'true',
                'scale': 'true',
                'isTable': 'true',
                'OCREngine': '2',  # Engine 2 is better for tables
            }

            data = urllib.parse.urlencode(payload).encode('utf-8')

            req = urllib.request.Request(
                'https://api.ocr.space/parse/image',
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))

            if result.get('IsErroredOnProcessing'):
                error_msg = result.get('ErrorMessage', ['Unknown error'])
                if isinstance(error_msg, list):
                    error_msg = error_msg[0] if error_msg else 'Unknown error'
                raise Exception(f"OCR API error: {error_msg}")

            parsed_results = result.get('ParsedResults', [])
            if not parsed_results:
                return ""

            # Combine text from all parsed results
            all_text = []
            for pr in parsed_results:
                text = pr.get('ParsedText', '')
                if text:
                    all_text.append(text)

            return '\n'.join(all_text)

        except Exception as e:
            print(f"OCR API error: {e}")
            return ""

    def _apply_corrections(self, text: str) -> str:
        """Apply common OCR error corrections."""
        corrected = text.strip()
        if corrected in OCR_CORRECTIONS:
            return OCR_CORRECTIONS[corrected]

        # Fix I -> 1 in course codes
        if re.match(r'^[A-Z]{2,4}I\d{2}$', corrected):
            corrected = corrected.replace('I', '1', 1)

        # Fix O -> 0 in course codes
        if re.match(r'^[A-Z]{2,4}O\d{2}$', corrected):
            corrected = corrected.replace('O', '0', 1)

        return corrected

    def _parse_transcript(self, raw_text: list) -> OCRResult:
        """Parse raw OCR text into structured course data."""
        courses = []
        current_semester = ""
        student_name = ""
        student_id = ""
        cgpa = 0.0
        seen_courses = set()

        # Apply corrections
        corrected_text = [self._apply_corrections(t) for t in raw_text]

        for i, text in enumerate(corrected_text):
            text = text.strip()

            # Extract student info
            if "Name" in text and i + 1 < len(corrected_text):
                name_candidate = corrected_text[i + 1].strip()
                if not any(kw in name_candidate for kw in ['Student', 'ID', 'Date', ':']):
                    student_name = name_candidate

            if "ID" in text:
                id_match = re.search(r'(\d{10,})', text)
                if id_match:
                    student_id = id_match.group(1)
                elif i + 1 < len(corrected_text):
                    id_match = re.search(r'(\d{10,})', corrected_text[i + 1])
                    if id_match:
                        student_id = id_match.group(1)

            # Extract CGPA
            if "CGPA" in text.upper() or "Cumulative" in text:
                cgpa_match = re.search(r'(\d+\.\d+)', text)
                if cgpa_match:
                    try:
                        cgpa = float(cgpa_match.group(1))
                    except:
                        pass

            # Detect semester
            sem_match = SEMESTER_PATTERN.search(text)
            if sem_match:
                current_semester = f"{sem_match.group(1)} {sem_match.group(2)}"

            # Detect course code
            course_match = COURSE_PATTERN.match(text)
            if course_match:
                course_code = text

                if course_code in seen_courses:
                    continue

                # Look ahead for credits and grade
                credits = 0.0
                grade = ""

                for j in range(i + 1, min(i + 10, len(corrected_text))):
                    next_text = corrected_text[j].strip()

                    # Check for credit value
                    if credits == 0.0:
                        credit_match = re.match(r'^(\d+\.?\d*)$', next_text)
                        if credit_match:
                            try:
                                val = float(credit_match.group(1))
                                if 0 < val <= 10:
                                    credits = val
                            except:
                                pass

                    # Check for grade
                    if not grade:
                        grade_text = next_text
                        if grade_text in OCR_CORRECTIONS:
                            grade_text = OCR_CORRECTIONS[grade_text]
                        if grade_text in VALID_GRADES:
                            grade = grade_text

                    # Stop if we find another course code
                    if COURSE_PATTERN.match(next_text):
                        break

                    if credits > 0 and grade:
                        break

                # Add course if valid
                if grade:
                    seen_courses.add(course_code)
                    courses.append(CourseRecord(
                        course_code=course_code,
                        credits=credits,
                        grade=grade,
                        semester=current_semester
                    ))

        return OCRResult(
            success=True,
            courses=courses,
            raw_text=raw_text,
            student_name=student_name,
            student_id=student_id,
            cgpa=cgpa
        )


# Alias for backward compatibility
TranscriptOCR = WebOCR


def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ocr_web.py <transcript.pdf|image.png>")
        print("\nLightweight OCR using OCR.space free API.")
        print("Free tier: 500 requests/month")
        sys.exit(1)

    file_path = sys.argv[1]
    print(f"Processing: {file_path}")

    ocr = WebOCR()
    result = ocr.extract(file_path)

    if result.success:
        print(f"\n[OK] Extraction successful!")
        print(f"  Engine: {result.engine_used}")
        print(f"  Confidence: {result.confidence_score:.1%}")
        print(f"  Courses found: {result.course_count}")
        print(f"  Student: {result.student_name or 'N/A'}")
        print(f"  ID: {result.student_id or 'N/A'}")
        print(f"\n=== CSV OUTPUT ===\n")
        print(result.csv_data)
    else:
        print(f"\n[ERROR] {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
