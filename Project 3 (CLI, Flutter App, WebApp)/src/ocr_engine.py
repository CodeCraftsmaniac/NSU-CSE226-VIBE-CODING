"""
ocr_engine.py — Unified OCR Module for NSU Transcript Extraction
===================================================================
Cross-platform OCR engine with MULTIPLE FALLBACK ENGINES for maximum accuracy.
Works with Terminal, Web, and Flutter applications.

OCR Engine Priority:
  1. PaddleOCR (primary) - Fast and accurate
  2. EasyOCR (fallback) - Good for complex layouts
  3. Cross-validation for confidence scoring

Supported Inputs:
  - PDF files (scanned or digital)
  - Images (PNG, JPG, JPEG, BMP, TIFF)

Output Format:
  - CSV data: Course_Code,Credits,Grade,Semester

Dependencies:
  - paddleocr (pip install paddleocr)
  - easyocr (pip install easyocr)
  - PyMuPDF (pip install pymupdf)
  - Pillow (pip install Pillow)
  - opencv-python (pip install opencv-python)

Usage:
  from ocr_engine import TranscriptOCR

  ocr = TranscriptOCR()
  result = ocr.extract("transcript.pdf")
  print(result.csv_data)
"""

import os
import re
import io
import warnings
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Callable
from pathlib import Path

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VALID_GRADES = {'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F', 'W', 'I', 'P', 'TR'}
COURSE_PATTERN = re.compile(r'^([A-Z]{2,4})(\d{3}[A-Z]?)$')
SEMESTER_PATTERN = re.compile(r'(Spring|Summer|Fall)\s*(\d{4})', re.IGNORECASE)
CREDIT_PATTERN = re.compile(r'^(\d+\.?\d*)$')

# Known NSU course prefixes for validation
NSU_COURSE_PREFIXES = {
    'CSE', 'EEE', 'ECE', 'MAT', 'PHY', 'CHE', 'ENG', 'BEN', 'BIO',
    'ENV', 'ECO', 'BUS', 'ACT', 'FIN', 'MKT', 'MGT', 'MIS', 'HRM',
    'SOC', 'POL', 'HIS', 'PHI', 'ANT', 'PSY', 'ARC', 'LAW', 'ESL',
    'GEN', 'COM', 'MED', 'PHA', 'PUB', 'MPH', 'STA', 'IST', 'LIN',
    'JMS', 'CIS', 'MSC', 'NST'
}

# Common OCR misreadings and corrections
OCR_CORRECTIONS = {
    # Grade corrections
    '8+': 'B+', '8-': 'B-', '8': 'B',
    'A+': 'A', 'A1': 'A-', 'Al': 'A-',
    'C1': 'C-', 'D1': 'D+',
    '0': 'D', 'O': 'D',
    'Bt': 'B+', 'B1': 'B-',
    'Ct': 'C+', 'Dt': 'D+',
    # Course code corrections
    'CSEIS': 'CSE15', 'CSEI': 'CSE1',
    'MATI': 'MAT1', 'MAT1I6': 'MAT116',
    'EEEIII': 'EEE111', 'EEE14I': 'EEE141',
    'PHYI07': 'PHY107', 'PHYI08': 'PHY108',
    'CHEI01': 'CHE101',
    # Common letter substitutions in course codes
    'CSEII5': 'CSE115', 'CSEII5L': 'CSE115L',
    'ENGI02': 'ENG102', 'ENGI03': 'ENG103',
    'HISI03': 'HIS103', 'HISI02': 'HIS102',
    'PHII04': 'PHI104',
    'MAT1I6': 'MAT116', 'MATI20': 'MAT120', 'MATI25': 'MAT125',
    'MATI30': 'MAT130', 'MAT25O': 'MAT250',
    'ECOI01': 'ECO101', 'POLI01': 'POL101', 'SOCI01': 'SOC101',
    'BENI05': 'BEN205', 'BEN2O5': 'BEN205',
    'CSEZ26': 'CSE226', 'CSE2I5': 'CSE215', 'CSE2I5L': 'CSE215L',
    'CSE22S': 'CSE225', 'CSE22SL': 'CSE225L',
    'CSE23I': 'CSE231', 'CSE23IL': 'CSE231L',
}


@dataclass
class CourseRecord:
    """Represents a single course entry from the transcript."""
    course_code: str
    credits: float
    grade: str
    semester: str = ""
    confidence: float = 1.0

    def to_csv_row(self) -> str:
        return f"{self.course_code},{self.credits},{self.grade},{self.semester}"


@dataclass
class OCRResult:
    """Result of OCR extraction."""
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
        """Generate CSV-formatted output."""
        lines = ["Course_Code,Credits,Grade,Semester"]
        for course in self.courses:
            lines.append(course.to_csv_row())
        return "\n".join(lines)

    @property
    def course_count(self) -> int:
        return len(self.courses)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization (API responses)."""
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  IMAGE PREPROCESSING (Enhanced)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ImagePreprocessor:
    """Preprocess images for better OCR accuracy."""

    @staticmethod
    def enhance_for_ocr(image_path: str) -> str:
        """
        Apply advanced preprocessing to maximize OCR accuracy.
        Returns path to preprocessed image.
        """
        try:
            import cv2
            import numpy as np
            from PIL import Image, ImageEnhance
            import tempfile

            # Read image
            img = cv2.imread(image_path)
            if img is None:
                return image_path

            # Step 1: Upscale small images for better OCR
            height, width = img.shape[:2]
            if width < 2000:
                scale = 2000 / width
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            # Step 2: Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Step 3: Deskew - correct any rotation
            gray = ImagePreprocessor._deskew(gray)

            # Step 4: Apply CLAHE for contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # Step 5: Sharpen the image
            kernel = np.array([[-1, -1, -1],
                               [-1,  9, -1],
                               [-1, -1, -1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            # Step 6: Adaptive thresholding to handle watermarks/backgrounds
            binary = cv2.adaptiveThreshold(
                sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 15, 4
            )

            # Step 7: Denoise
            denoised = cv2.fastNlMeansDenoising(binary, None, 12, 7, 21)

            # Save preprocessed image
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                cv2.imwrite(tmp.name, denoised)
                return tmp.name

        except ImportError:
            return image_path
        except Exception:
            return image_path

    @staticmethod
    def _deskew(image):
        """Correct slight rotation/skew in scanned images."""
        try:
            import cv2
            import numpy as np

            # Detect edges
            edges = cv2.Canny(image, 50, 150, apertureSize=3)

            # Detect lines using Hough transform
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                                    minLineLength=100, maxLineGap=10)

            if lines is None or len(lines) == 0:
                return image

            # Calculate median angle of detected lines
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                if abs(angle) < 10:  # Only consider near-horizontal lines
                    angles.append(angle)

            if not angles:
                return image

            median_angle = np.median(angles)

            if abs(median_angle) < 0.5:
                return image  # Already straight

            # Rotate to correct skew
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h),
                                     flags=cv2.INTER_CUBIC,
                                     borderMode=cv2.BORDER_REPLICATE)
            return rotated
        except Exception:
            return image


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OCR ENGINE BACKENDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PaddleOCRBackend:
    """PaddleOCR backend - primary engine."""

    def __init__(self, lang: str = 'en'):
        self.lang = lang
        self._ocr = None

    def _get_ocr(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(lang=self.lang)
        return self._ocr

    def extract_text(self, image_path: str) -> List[Tuple[str, float]]:
        """Extract text with confidence scores."""
        try:
            ocr = self._get_ocr()
            result = list(ocr.predict(image_path))

            texts_with_scores = []
            if result:
                page_result = result[0]
                texts = page_result.get('rec_texts', [])
                scores = page_result.get('rec_scores', [])
                for text, score in zip(texts, scores):
                    if score > 0.3:  # Lower threshold to catch more text
                        texts_with_scores.append((text.strip(), score))

            return texts_with_scores
        except Exception as e:
            return []

    @property
    def name(self) -> str:
        return "PaddleOCR"


class EasyOCRBackend:
    """EasyOCR backend - fallback engine."""

    def __init__(self, lang: str = 'en'):
        self.lang = [lang]
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(self.lang, gpu=False, verbose=False)
        return self._reader

    def extract_text(self, image_path: str) -> List[Tuple[str, float]]:
        """Extract text with confidence scores."""
        try:
            reader = self._get_reader()
            results = reader.readtext(image_path)

            texts_with_scores = []
            for (bbox, text, confidence) in results:
                if confidence > 0.3:
                    texts_with_scores.append((text.strip(), confidence))

            return texts_with_scores
        except Exception as e:
            return []

    @property
    def name(self) -> str:
        return "EasyOCR"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN OCR ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TranscriptOCR:
    """
    NSU Transcript OCR Engine with Multiple Fallbacks

    Extracts course data from scanned or digital NSU transcripts.
    Uses multiple OCR engines for maximum accuracy.

    Engine Priority:
    1. PaddleOCR (fast, accurate)
    2. EasyOCR (good fallback)
    3. Cross-validation between engines
    """

    def __init__(self, lang: str = 'en', dpi: float = 4.0, use_fallback: bool = True,
                 progress_callback: Callable = None):
        """
        Initialize the OCR engine.

        Args:
            lang: OCR language (default: 'en' for English)
            dpi: Resolution multiplier for PDF rendering (default: 4.0 for max accuracy)
            use_fallback: Enable fallback engines (default: True)
            progress_callback: Optional callback for progress updates
        """
        self.lang = lang
        self.dpi = dpi
        self.use_fallback = use_fallback
        self.preprocessor = ImagePreprocessor()
        self.progress_callback = progress_callback

        # Initialize backends lazily
        self._paddle = None
        self._easyocr = None

    def _report_progress(self, stage: str, progress: float, text: str = ""):
        """Report progress to callback if available."""
        if self.progress_callback:
            self.progress_callback(stage, progress, text)

    def _get_paddle(self) -> PaddleOCRBackend:
        if self._paddle is None:
            self._paddle = PaddleOCRBackend(self.lang)
        return self._paddle

    def _get_easyocr(self) -> EasyOCRBackend:
        if self._easyocr is None:
            self._easyocr = EasyOCRBackend(self.lang)
        return self._easyocr

    def extract(self, file_path: str) -> OCRResult:
        """
        Extract transcript data from a file.

        Args:
            file_path: Path to PDF or image file

        Returns:
            OCRResult with extracted course data
        """
        path = Path(file_path)

        if not path.exists():
            return OCRResult(success=False, error=f"File not found: {file_path}")

        ext = path.suffix.lower()

        try:
            self._report_progress("init", 5, "Initializing OCR engine...")

            if ext == '.pdf':
                return self._extract_from_pdf(path)
            elif ext in {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}:
                return self._extract_from_image(path)
            else:
                return OCRResult(success=False, error=f"Unsupported file type: {ext}")
        except Exception as e:
            return OCRResult(success=False, error=str(e))

    def extract_from_bytes(self, data: bytes, filename: str = "upload.pdf") -> OCRResult:
        """
        Extract from raw bytes (for web/API uploads).

        Args:
            data: Raw file bytes
            filename: Original filename for type detection

        Returns:
            OCRResult with extracted course data
        """
        import tempfile

        ext = Path(filename).suffix.lower() or '.pdf'

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            result = self.extract(tmp_path)
        finally:
            os.unlink(tmp_path)

        return result

    def _extract_from_pdf(self, path: Path) -> OCRResult:
        """Extract text from PDF file with multiple engines."""
        import fitz  # PyMuPDF
        from PIL import Image
        import tempfile

        doc = fitz.open(str(path))
        all_results = []
        total_pages = len(doc)

        self._report_progress("pdf", 10, f"Opening PDF ({total_pages} pages)...")

        for page_num in range(total_pages):
            page = doc[page_num]
            page_progress = 10 + (page_num / total_pages) * 60

            self._report_progress("page", page_progress,
                                  f"Processing page {page_num + 1}/{total_pages}...")

            images = page.get_images(full=True)

            # If page has embedded images (scanned PDF)
            if images:
                for img_info in images:
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    img = Image.open(io.BytesIO(image_bytes))

                    # Save temp file for OCR
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                        img.save(tmp.name)
                        tmp_path = tmp.name

                    try:
                        page_results = self._run_ocr_with_fallback(tmp_path)
                        all_results.extend(page_results)
                    finally:
                        os.unlink(tmp_path)
            else:
                # Digital PDF - render as high-res image
                mat = fitz.Matrix(self.dpi, self.dpi)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    img.save(tmp.name)
                    tmp_path = tmp.name

                try:
                    page_results = self._run_ocr_with_fallback(tmp_path)
                    all_results.extend(page_results)
                finally:
                    os.unlink(tmp_path)

        doc.close()

        self._report_progress("parse", 75, "Parsing transcript data...")

        # Extract texts and determine engine used
        all_text = [text for text, score in all_results]
        avg_confidence = sum(score for text, score in all_results) / len(all_results) if all_results else 0

        result = self._parse_transcript(all_text)
        result.confidence_score = avg_confidence
        result.raw_text = all_text

        self._report_progress("validate", 90, "Validating extracted data...")

        # Post-validation
        result = self._validate_result(result)

        self._report_progress("complete", 100, "Extraction complete!")

        return result

    def _extract_from_image(self, path: Path) -> OCRResult:
        """Extract text from image file with multiple engines."""
        self._report_progress("image", 15, "Processing image...")

        results = self._run_ocr_with_fallback(str(path))

        self._report_progress("parse", 70, "Parsing transcript data...")

        all_text = [text for text, score in results]
        avg_confidence = sum(score for text, score in results) / len(results) if results else 0

        result = self._parse_transcript(all_text)
        result.confidence_score = avg_confidence
        result.raw_text = all_text

        self._report_progress("validate", 90, "Validating extracted data...")
        result = self._validate_result(result)

        self._report_progress("complete", 100, "Extraction complete!")

        return result

    def _run_ocr_with_fallback(self, image_path: str) -> List[Tuple[str, float]]:
        """
        Run OCR with fallback engines for maximum accuracy.

        Strategy:
        1. Try PaddleOCR first
        2. If results are poor or empty, try EasyOCR
        3. Cross-validate and merge results
        """
        # Try preprocessing first
        preprocessed_path = self.preprocessor.enhance_for_ocr(image_path)
        cleanup_preprocessed = preprocessed_path != image_path

        try:
            # Primary engine: PaddleOCR
            paddle_results = []
            engine_used = "PaddleOCR"

            try:
                paddle = self._get_paddle()
                paddle_results = paddle.extract_text(preprocessed_path)
                self._report_progress("ocr", 40, "PaddleOCR extraction complete...")
            except Exception:
                pass

            # Calculate average confidence
            paddle_confidence = (
                sum(s for _, s in paddle_results) / len(paddle_results)
                if paddle_results else 0
            )

            # Try fallback if primary results are poor
            if self.use_fallback and (len(paddle_results) < 5 or paddle_confidence < 0.7):
                try:
                    self._report_progress("ocr", 50, "Running EasyOCR fallback...")
                    easyocr = self._get_easyocr()
                    easy_results = easyocr.extract_text(preprocessed_path)

                    easy_confidence = (
                        sum(s for _, s in easy_results) / len(easy_results)
                        if easy_results else 0
                    )

                    # Use the better result, or merge if both are similar
                    if len(easy_results) > len(paddle_results) * 1.2:
                        engine_used = "EasyOCR"
                        return self._merge_results(easy_results, paddle_results, engine_used)
                    elif easy_confidence > paddle_confidence + 0.1:
                        engine_used = "EasyOCR"
                        return self._merge_results(easy_results, paddle_results, engine_used)
                    elif paddle_results:
                        return self._merge_results(paddle_results, easy_results, engine_used)
                    else:
                        engine_used = "EasyOCR" if easy_results else "None"
                        return easy_results or []

                except Exception:
                    pass

            return paddle_results

        finally:
            # Cleanup preprocessed file
            if cleanup_preprocessed and os.path.exists(preprocessed_path):
                try:
                    os.unlink(preprocessed_path)
                except Exception:
                    pass

    def _merge_results(
        self,
        primary: List[Tuple[str, float]],
        secondary: List[Tuple[str, float]],
        engine_used: str
    ) -> List[Tuple[str, float]]:
        """Merge results from multiple OCR engines."""
        # Create a set of primary texts for deduplication
        primary_texts = {text.lower() for text, _ in primary}

        merged = list(primary)

        # Add unique texts from secondary
        for text, score in secondary:
            if text.lower() not in primary_texts:
                # Apply corrections
                corrected = self._apply_corrections(text)
                merged.append((corrected, score * 0.9))  # Slightly lower confidence for secondary

        return merged

    def _apply_corrections(self, text: str) -> str:
        """Apply common OCR error corrections."""
        corrected = text.strip()

        # Apply direct corrections
        if corrected in OCR_CORRECTIONS:
            return OCR_CORRECTIONS[corrected]

        # Fix common patterns
        # I -> 1 in numbers within course codes
        if re.match(r'^[A-Z]{2,4}I\d{2}$', corrected):
            corrected = corrected.replace('I', '1', 1)

        # O -> 0 in course codes
        if re.match(r'^[A-Z]{2,4}O\d{2}$', corrected):
            corrected = corrected.replace('O', '0', 1)

        # Fix l -> 1 in course numbers
        if re.match(r'^[A-Z]{2,4}l\d{2}$', corrected):
            corrected = re.sub(r'([A-Z]{2,4})l', r'\g<1>1', corrected)

        # Fix common O/0 confusion in numbers
        if re.match(r'^[A-Z]{2,4}\d{1}O\d{1}$', corrected):
            # e.g., CSE1O3 -> CSE103
            corrected = corrected.replace('O', '0')

        return corrected

    def _validate_course_code(self, code: str) -> str:
        """Validate and correct a course code against known NSU patterns."""
        if not code:
            return code

        # Already valid
        match = COURSE_PATTERN.match(code)
        if match:
            prefix = match.group(1)
            if prefix in NSU_COURSE_PREFIXES:
                return code

        # Try corrections
        corrected = self._apply_corrections(code)
        match = COURSE_PATTERN.match(corrected)
        if match:
            prefix = match.group(1)
            if prefix in NSU_COURSE_PREFIXES:
                return corrected

        return code  # Return as-is if we can't fix it

    def _validate_result(self, result: OCRResult) -> OCRResult:
        """Post-processing validation to ensure data quality."""
        validated_courses = []

        for course in result.courses:
            # Validate course code
            course.course_code = self._validate_course_code(course.course_code)

            # Validate grade
            if course.grade not in VALID_GRADES:
                corrected_grade = OCR_CORRECTIONS.get(course.grade, course.grade)
                if corrected_grade in VALID_GRADES:
                    course.grade = corrected_grade
                else:
                    continue  # Skip invalid courses

            # Validate credits (0-6 typical range)
            if course.credits < 0 or course.credits > 10:
                continue

            # Validate course code pattern
            if not COURSE_PATTERN.match(course.course_code):
                continue

            validated_courses.append(course)

        result.courses = validated_courses
        return result

    def _parse_transcript(self, raw_text: list) -> OCRResult:
        """Parse raw OCR text into structured course data."""
        courses = []
        current_semester = ""

        # Extract metadata
        student_name = ""
        student_id = ""
        cgpa = 0.0
        total_credits = 0.0

        # Track which courses we've already added (avoid duplicates)
        seen_courses = set()

        # Apply corrections to all text first
        corrected_text = [self._apply_corrections(t) for t in raw_text]

        for i, text in enumerate(corrected_text):
            text = text.strip()

            # Extract student info
            if "Student Name" in text or "Name :" in text:
                if i + 1 < len(corrected_text):
                    name_candidate = corrected_text[i + 1].strip()
                    if not any(kw in name_candidate for kw in ['Student', 'ID', 'Date', ':']):
                        student_name = name_candidate

            if "Student ID" in text or text.startswith("ID :"):
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

            # Extract total credits
            if "Total Credits" in text:
                credits_match = re.search(r'(\d+\.?\d*)', text)
                if credits_match:
                    try:
                        total_credits = float(credits_match.group(1))
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

                # Skip if already seen (avoid duplicates from retakes)
                if course_code in seen_courses:
                    continue

                # Look ahead for credits and grade
                credits = 0.0
                grade = ""
                grade_confidence = 0.0

                for j in range(i + 1, min(i + 10, len(corrected_text))):
                    next_text = corrected_text[j].strip()

                    # Check for credit value
                    if credits == 0.0:
                        credit_match = re.match(r'^(\d+\.?\d*)$', next_text)
                        if credit_match:
                            try:
                                val = float(credit_match.group(1))
                                # Credits should be reasonable (0-6 typically)
                                if 0 < val <= 10:
                                    credits = val
                            except:
                                pass

                    # Check for grade
                    if not grade:
                        # Apply grade corrections
                        grade_text = next_text
                        if grade_text in OCR_CORRECTIONS:
                            grade_text = OCR_CORRECTIONS[grade_text]

                        if grade_text in VALID_GRADES:
                            grade = grade_text

                    # Stop if we find another course code
                    if COURSE_PATTERN.match(next_text):
                        break

                    # Stop if we have both
                    if credits > 0 and grade:
                        break

                # Only add if we have valid data
                if grade and credits > 0:
                    seen_courses.add(course_code)
                    courses.append(CourseRecord(
                        course_code=course_code,
                        credits=credits,
                        grade=grade,
                        semester=current_semester
                    ))
                elif grade and credits == 0.0:
                    # Some lab courses have 0 credits
                    seen_courses.add(course_code)
                    courses.append(CourseRecord(
                        course_code=course_code,
                        credits=0.0,
                        grade=grade,
                        semester=current_semester
                    ))

        return OCRResult(
            success=True,
            courses=courses,
            raw_text=raw_text,
            student_name=student_name,
            student_id=student_id,
            cgpa=cgpa,
            total_credits=total_credits,
            engine_used="Multi-Engine"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI INTERFACE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """CLI entry point for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ocr_engine.py <transcript.pdf|image.png>")
        print("\nExtracts course data from NSU transcripts.")
        print("\nFeatures:")
        print("  - Multiple OCR engines (PaddleOCR + EasyOCR)")
        print("  - Automatic fallback for better accuracy")
        print("  - Image preprocessing for watermarked documents")
        print("  - Cross-validation between engines")
        sys.exit(1)

    file_path = sys.argv[1]

    print(f"Processing: {file_path}")
    print("Initializing OCR engine (multi-engine mode)...")

    ocr = TranscriptOCR()
    result = ocr.extract(file_path)

    if result.success:
        print(f"\n[OK] Extraction successful!")
        print(f"  Engine: {result.engine_used}")
        print(f"  Confidence: {result.confidence_score:.1%}")
        print(f"  Courses found: {result.course_count}")
        print(f"  Student: {result.student_name or 'N/A'}")
        print(f"  ID: {result.student_id or 'N/A'}")
        print(f"  CGPA: {result.cgpa or 'N/A'}")
        print(f"\n=== CSV OUTPUT ===\n")
        print(result.csv_data)
    else:
        print(f"\n[ERROR] Extraction failed: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
