"""
NSU Degree Audit - Backend API
==============================
Pure REST API backend for OCR processing and degree analysis.
NO UI - only JSON endpoints for CLI, Web, and Flutter apps.

Endpoints:
  GET  /health     - Service health, OCR limits, system info
  POST /upload     - Upload transcript PDF/image for OCR + analysis
  GET  /           - API info (JSON)
"""

import os
import sys
import logging
import tempfile
import platform
from pathlib import Path
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

# Add backend directory for local imports
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify

# Enable CORS for all frontends
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# Application Factory
# ═══════════════════════════════════════════════════════════════════════════════

def create_app():
    """Create Flask API application."""
    app = Flask(__name__)
    
    # Enable CORS for all origins (CLI, Web, Flutter)
    if CORS_AVAILABLE:
        CORS(app, origins="*", supports_credentials=True)

    project_root = Path(__file__).parent.parent
    runtime_root = Path(tempfile.gettempdir()) / 'nsu-audit-api'

    # Configuration
    app.config['ENV'] = os.getenv('FLASK_ENV', 'production')
    app.config['DEBUG'] = os.getenv('DEBUG', 'false').lower() == 'true'
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'nsu-audit-api-key')
    
    # File upload
    max_mb = int(os.getenv('MAX_CONTENT_LENGTH_MB', '16'))
    app.config['MAX_CONTENT_LENGTH'] = max_mb * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = runtime_root / 'uploads'
    app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)

    # Logging
    log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler()]
    )

    return app

app = create_app()
logger = logging.getLogger(__name__)

# Knowledge base path
KB_PATH = Path(__file__).parent.parent / 'knowledge_base.md'

# ═══════════════════════════════════════════════════════════════════════════════
# Import OCR and Analysis Engines
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from ocr_web import WebOCR as TranscriptOCR
except ImportError:
    from ocr_engine import TranscriptOCR

from core import run_full_analysis

# ═══════════════════════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """API root - service info."""
    return jsonify({
        'service': 'NSU Degree Audit API',
        'version': '2.0.0',
        'project': 'CSE226 Project 3',
        'endpoints': {
            'GET /': 'This info',
            'GET /health': 'Health check with OCR limits and system info',
            'POST /upload': 'Upload transcript for OCR + analysis'
        },
        'docs': 'https://github.com/your-repo/nsu-degree-audit',
        'status': 'operational'
    })


@app.route('/health')
def health():
    """Premium health endpoint with detailed system info."""
    
    # OCR API keys status
    google_key = os.getenv('GOOGLE_CLOUD_VISION_KEY', '')
    ocrspace_key = os.getenv('OCR_SPACE_API_KEY', '')
    
    # System info
    uptime_info = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'timezone': 'UTC'
    }
    
    # OCR limits info
    ocr_info = {
        'google_vision': {
            'configured': bool(google_key),
            'key_preview': f"{google_key[:8]}...{google_key[-4:]}" if len(google_key) > 12 else 'Not set',
            'free_tier': '1,000 requests/month',
            'rate_limit': '1,800 requests/minute',
            'max_file_size': '20 MB',
            'supported_formats': ['PDF', 'PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'WEBP', 'TIFF']
        },
        'ocr_space': {
            'configured': bool(ocrspace_key),
            'key_preview': f"{ocrspace_key[:4]}...{ocrspace_key[-4:]}" if len(ocrspace_key) > 8 else 'Not set',
            'free_tier': '25,000 requests/month',
            'rate_limit': '500 requests/day (free)',
            'max_file_size': '1 MB (free) / 5 MB (pro)',
            'supported_formats': ['PDF', 'PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'TIFF']
        }
    }
    
    # Server info
    server_info = {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'python_version': platform.python_version(),
        'architecture': platform.machine(),
        'processor': platform.processor() or 'Cloud Run',
        'hostname': platform.node()
    }
    
    # Environment
    env_info = {
        'flask_env': os.getenv('FLASK_ENV', 'production'),
        'debug_mode': os.getenv('DEBUG', 'false'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'max_upload_mb': int(os.getenv('MAX_CONTENT_LENGTH_MB', '16')),
        'port': os.getenv('PORT', '8080')
    }
    
    # Knowledge base status
    kb_info = {
        'path': str(KB_PATH),
        'exists': KB_PATH.exists(),
        'size_kb': round(KB_PATH.stat().st_size / 1024, 2) if KB_PATH.exists() else 0
    }
    
    # Analysis capabilities
    capabilities = {
        'level_1': {
            'name': 'Credit Tally',
            'features': ['Total credits', 'Earned credits', 'Failed credits', 'Retake detection']
        },
        'level_2': {
            'name': 'CGPA Analysis',
            'features': ['CGPA calculation', 'Academic standing', 'Grade distribution', 'Waiver eligibility']
        },
        'level_3': {
            'name': 'Degree Audit',
            'features': ['Program detection', 'Mandatory course check', 'Elective requirements', 'Graduation readiness']
        }
    }
    
    # Build response
    return jsonify({
        'status': 'healthy',
        'service': 'NSU Degree Audit API',
        'version': '2.0.0',
        'uptime': uptime_info,
        'ocr_engines': ocr_info,
        'server': server_info,
        'environment': env_info,
        'knowledge_base': kb_info,
        'analysis_capabilities': capabilities,
        'endpoints': {
            'root': '/',
            'health': '/health',
            'upload': '/upload (POST)'
        },
        'cors': {
            'enabled': CORS_AVAILABLE,
            'origins': '*'
        },
        'grading_scale': {
            'A': 4.00, 'A-': 3.70,
            'B+': 3.30, 'B': 3.00, 'B-': 2.70,
            'C+': 2.30, 'C': 2.00, 'C-': 1.70,
            'D+': 1.30, 'D': 1.00,
            'F': 0.00
        },
        'waivers': {
            'chancellors_award': {'cgpa': 3.97, 'waiver': '100%'},
            'vc_scholarship': {'cgpa': 3.75, 'waiver': '50%'},
            'deans_scholarship': {'cgpa': 3.50, 'waiver': '25%'}
        }
    })


@app.route('/upload', methods=['POST'])
def upload():
    """Process transcript upload via OCR and return analysis."""
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    # Validate extension
    allowed = {'pdf', 'png', 'jpg', 'jpeg'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed:
        return jsonify({'success': False, 'error': f'Invalid file type. Allowed: {", ".join(allowed)}'}), 400

    try:
        # Save temporarily
        filepath = Path(app.config['UPLOAD_FOLDER']) / file.filename
        file.save(str(filepath))
        file_size = filepath.stat().st_size
        
        logger.info(f"File uploaded: {file.filename}, size: {file_size} bytes")

        # OCR Processing
        ocr = TranscriptOCR()
        ocr_result = ocr.extract(str(filepath))

        # Cleanup
        filepath.unlink(missing_ok=True)

        if not ocr_result.success:
            logger.error(f"OCR failed: {ocr_result.error}")
            return jsonify({'success': False, 'error': ocr_result.error or 'OCR extraction failed'}), 500

        if ocr_result.course_count == 0:
            return jsonify({'success': False, 'error': 'No courses found in document'}), 400

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

        # Run analysis
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

        # CGPA verification
        if ocr_result.cgpa > 0 and result.get('level2'):
            calculated_cgpa = result['level2']['cgpa']
            if abs(calculated_cgpa - ocr_result.cgpa) > 0.05:
                result['cgpa_warning'] = {
                    'message': 'CGPA mismatch detected',
                    'pdf_value': ocr_result.cgpa,
                    'calculated_value': calculated_cgpa,
                    'difference': round(abs(calculated_cgpa - ocr_result.cgpa), 2)
                }

        logger.info(f"Analysis complete: {len(courses)} courses processed")
        return jsonify({'success': True, 'data': result})

    except Exception as e:
        logger.exception(f"Error processing upload: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Error Handlers
# ═══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found', 'status': 404}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error', 'status': 500}), 500

@app.errorhandler(413)
def file_too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.', 'status': 413}), 413


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    print(f"\n{'='*60}")
    print("  NSU Degree Audit - Backend API")
    print(f"{'='*60}")
    print(f"\n  URL: http://localhost:{port}")
    print(f"  Health: http://localhost:{port}/health")
    print(f"\n  Press Ctrl+C to stop")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
