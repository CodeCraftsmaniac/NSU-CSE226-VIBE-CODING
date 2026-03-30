"""
NSU Degree Audit Web Application
================================
Premium web interface with real-time OCR scanning display.
Upload PDF/Image -> Watch OCR extract text -> View 3-level analysis.

Development: python app.py
Production:  waitress-serve --host=0.0.0.0 --port=5000 app:app
             OR gunicorn -w 4 -b 0.0.0.0:5000 app:app (Linux/Mac)
"""

import os
import sys
import re
import json
import logging
import tempfile
from pathlib import Path
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass  # dotenv not installed, use system env vars

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flask import Flask, render_template, request, jsonify, send_from_directory

# Enable CORS for Flutter/mobile app access
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# Application Configuration
# ═══════════════════════════════════════════════════════════════════════════════

def create_app():
    """Application factory for Flask app."""
    app = Flask(__name__)
    
    # Enable CORS for all routes (allows Flutter/mobile access)
    if CORS_AVAILABLE:
        CORS(app, origins="*", supports_credentials=True)

    project_root = Path(__file__).parent.parent
    runtime_root = Path(tempfile.gettempdir()) / 'nsu-degree-audit' if os.getenv('VERCEL') else project_root

    # Load configuration from environment
    app.config['ENV'] = os.getenv('FLASK_ENV', 'production')
    app.config['DEBUG'] = os.getenv('DEBUG', 'false').lower() == 'true'
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'nsu-audit-default-key-change-in-prod')

    # File upload configuration
    max_mb = int(os.getenv('MAX_CONTENT_LENGTH_MB', '16'))
    app.config['MAX_CONTENT_LENGTH'] = max_mb * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = runtime_root / 'uploads'
    app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)

    # Create logs directory
    logs_dir = runtime_root / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Configure logging
    log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    log_file = logs_dir / 'app.log'

    # Create handlers
    handlers = [logging.StreamHandler()]
    try:
        handlers.append(logging.FileHandler(str(log_file)))
    except Exception:
        pass  # Skip file logging if can't create

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=handlers
    )

    return app

app = create_app()
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Import modules after app creation
# ═══════════════════════════════════════════════════════════════════════════════

from werkzeug.utils import secure_filename

try:
    from src.ocr_web import WebOCR as TranscriptOCR
except ImportError:
    from src.ocr_engine import TranscriptOCR

from src.core import resolve_retakes, GRADE_POINTS, get_academic_standing, parse_knowledge_base, compute_cgpa, validate_grade, detect_program, run_full_analysis

# Knowledge base path
KB_PATH = Path(__file__).parent.parent / 'knowledge_base.md'

# Allowed file extensions
ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'pdf,png,jpg,jpeg').split(','))


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# detect_program() and run_full_analysis() are imported from src.core
# Single source of truth — same logic for CLI, Web, and Flutter


# ═══════════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint for production monitoring."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.1.0'
    })


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and OCR extraction."""
    if 'file' not in request.files:
        logger.warning('Upload attempted without file')
        return jsonify({'success': False, 'error': 'No file provided'})

    file = request.files['file']
    
    if file.filename == '':
        logger.warning('Upload attempted with empty filename')
        return jsonify({'success': False, 'error': 'No file selected'})

    if not allowed_file(file.filename):
        logger.warning(f'Invalid file type attempted: {file.filename}')
        return jsonify({'success': False, 'error': 'Invalid file type. Only PDF, PNG, JPG allowed.'})

    filename = secure_filename(file.filename)
    filepath = app.config['UPLOAD_FOLDER'] / filename

    try:
        file.save(str(filepath))
        logger.info(f'File uploaded: {filename}, size: {filepath.stat().st_size} bytes')

        # OCR extraction
        ocr = TranscriptOCR()
        ocr_result = ocr.extract(str(filepath))

        # Cleanup immediately
        filepath.unlink(missing_ok=True)

        if not ocr_result.success:
            logger.error(f'OCR failed: {ocr_result.error}')
            return jsonify({'success': False, 'error': ocr_result.error or 'OCR extraction failed'})

        if ocr_result.course_count == 0:
            logger.warning('No courses found in uploaded file')
            return jsonify({'success': False, 'error': 'No courses found. Please upload a clear transcript image/PDF.'})

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
        
        logger.debug(f"First 3 courses being sent: {courses[:3]}")

        # Run all 3 levels of analysis (from src.core — single source of truth)
        result = run_full_analysis(courses, kb_path=str(KB_PATH))

        # Add OCR info
        result['ocr_info'] = {
            'engine': ocr_result.engine_used,
            'confidence': round(ocr_result.confidence_score * 100, 1),
            'raw_text_count': len(ocr_result.raw_text),
            'student_name': ocr_result.student_name,
            'student_id': ocr_result.student_id,
            'cgpa_from_pdf': ocr_result.cgpa,
            'total_credits_from_pdf': getattr(ocr_result, 'total_credits', 0)
        }

        # CGPA verification: compare PDF vs calculated
        if ocr_result.cgpa > 0 and result.get('level2'):
            calculated_cgpa = result['level2']['cgpa']
            if abs(calculated_cgpa - ocr_result.cgpa) > 0.05:
                result['cgpa_warning'] = {
                    'message': f'CGPA mismatch detected',
                    'pdf_value': ocr_result.cgpa,
                    'calculated_value': calculated_cgpa,
                    'difference': round(abs(calculated_cgpa - ocr_result.cgpa), 2)
                }

        # Add raw extracted texts for display
        result['extracted_texts'] = ocr_result.raw_text[:100]

        logger.info(f'Analysis complete: {len(courses)} courses processed')
        return jsonify({'success': True, 'data': result})

    except Exception as e:
        logger.exception(f'Error processing upload: {str(e)}')
        if filepath.exists():
            filepath.unlink(missing_ok=True)
        return jsonify({'success': False, 'error': str(e)})


# run_full_analysis() is imported from src.core — zero duplication


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('static', filename)


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logger.exception('Server error')
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(413)
def file_too_large(e):
    """Handle file too large errors."""
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413


# ═══════════════════════════════════════════════════════════════════════════════
# Production Server Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def get_local_ip():
    """Get local IP address for network access."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == '__main__':
    import sys
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    local_ip = get_local_ip()

    # Check OCR API configuration
    ocr_key = os.getenv('OCR_SPACE_API_KEY', '')
    google_key = os.getenv('GOOGLE_CLOUD_VISION_KEY', '')

    # Print startup banner
    print("\n" + "=" * 60)
    print("  NSU Degree Audit - Web Application")
    print("=" * 60)
    print(f"\n  Mode        : {app.config['ENV'].upper()}")
    print(f"\n  Local       : http://localhost:{port}")
    print(f"  Network     : http://{local_ip}:{port}")
    print(f"\n  OCR.space   : {'Configured' if ocr_key else 'Not configured'}")
    print(f"  Google OCR  : {'Configured' if google_key else 'Not configured'}")

    if not ocr_key and not google_key:
        print("\n  [WARNING] No OCR API keys configured!")

    print("\n  Press Ctrl+C to stop\n")
    print("=" * 60)
    sys.stdout.flush()

    if app.config['ENV'] == 'production' and not debug:
        try:
            from waitress import serve
            import logging as wlog
            wlog.getLogger('waitress').setLevel(wlog.ERROR)
            serve(app, host=host, port=port)
        except ImportError:
            app.run(debug=False, host=host, port=port)
    else:
        app.run(debug=debug, host=host, port=port)


# Vercel serverless handler (required for Vercel deployment)
# This exposes the Flask app as a handler for Vercel
handler = app
