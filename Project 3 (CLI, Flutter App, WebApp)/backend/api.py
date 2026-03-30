"""
NSU Degree Audit - Backend API
==============================
Pure REST API backend for OCR processing and degree analysis.
NO UI - only JSON endpoints for CLI, Web, and Flutter apps.

Endpoints:
  GET  /health        - Service health, OCR limits, system info
  POST /upload        - Upload transcript PDF/image for OCR + analysis
  GET  /              - API info (JSON)
  
Auth Endpoints:
  POST /auth/google   - Google OAuth sign-in
  GET  /auth/user     - Get current user info
  
History Endpoints:
  GET  /history       - Get user's scan history
  GET  /history/<id>  - Get specific scan
  DELETE /history/<id> - Delete a scan
"""

import os
import sys
import logging
import tempfile
import platform
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from functools import wraps

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

# Add backend directory for local imports
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify, g

# Enable CORS for all frontends
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

# Database module
try:
    from database import (
        create_user, get_user_by_email, get_user_by_id,
        save_scan, get_user_scans, get_scan_by_id, delete_scan,
        get_user_stats, check_db_connection
    )
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    print(f"Database not available: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# Application Factory
# ═══════════════════════════════════════════════════════════════════════════════

def create_app():
    """Create Flask API application."""
    app = Flask(__name__)
    
    # CORS - Allow all origins for mobile/Flutter app compatibility
    if CORS_AVAILABLE:
        CORS(app, resources={r"/*": {"origins": "*"}})

    project_root = Path(__file__).parent.parent
    runtime_root = Path(tempfile.gettempdir()) / 'nsu-audit-api'

    # Configuration
    app.config['ENV'] = os.getenv('FLASK_ENV', 'production')
    app.config['DEBUG'] = os.getenv('DEBUG', 'false').lower() == 'true'
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
    
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
# Authentication Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def get_current_user():
    """Get current user from Authorization header (Bearer token or API key)."""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        return None
    
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        # For simplicity, token is email:hash format for session tokens
        # In production, use proper JWT validation
        try:
            email = token.split(':')[0]
            if DB_AVAILABLE:
                return get_user_by_email(email)
        except Exception:
            pass
    
    return None


def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        g.user = user
        return f(*args, **kwargs)
    return decorated


def optional_auth(f):
    """Decorator to optionally capture auth info."""
    @wraps(f)
    def decorated(*args, **kwargs):
        g.user = get_current_user()
        return f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """API root - service info."""
    return jsonify({
        'service': 'NSU Degree Audit API',
        'version': '2.1.0',
        'project': 'CSE226 Project 3',
        'endpoints': {
            'GET /': 'This info',
            'GET /health': 'Health check with OCR limits and system info',
            'POST /upload': 'Upload transcript for OCR + analysis',
            'POST /auth/google': 'Google OAuth sign-in',
            'GET /auth/user': 'Get current user info',
            'GET /history': 'Get scan history (requires auth)',
            'DELETE /history/<id>': 'Delete scan (requires auth)'
        },
        'docs': 'https://github.com/your-repo/nsu-degree-audit',
        'status': 'operational',
        'database': 'connected' if DB_AVAILABLE else 'unavailable'
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
    
    # OCR limits info (no key preview for security)
    ocr_info = {
        'google_vision': {
            'configured': bool(google_key),
            'free_tier': '1,000 requests/month',
            'rate_limit': '1,800 requests/minute',
            'max_file_size': '20 MB',
            'supported_formats': ['PDF', 'PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'WEBP', 'TIFF']
        },
        'ocr_space': {
            'configured': bool(ocrspace_key),
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
        'database': {
            'enabled': DB_AVAILABLE,
            'connected': check_db_connection() if DB_AVAILABLE else False,
            'provider': 'Supabase',
            'features': ['user_auth', 'scan_history', 'api_keys'] if DB_AVAILABLE else []
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
@optional_auth
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

    # Get source from request
    source = request.form.get('source', 'web')

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

        # Save to history if user is authenticated
        scan_id = None
        if g.user and DB_AVAILABLE:
            try:
                level2 = result.get('level2', {})
                scan_record = save_scan(
                    user_id=g.user['id'],
                    filename=file.filename,
                    total_courses=len(courses),
                    total_credits=level2.get('total_credits', 0),
                    cgpa=level2.get('cgpa', 0),
                    analysis_data=result,
                    source=source
                )
                if scan_record:
                    scan_id = scan_record['id']
                    result['scan_id'] = scan_id
            except Exception as e:
                logger.warning(f"Failed to save to history: {e}")

        logger.info(f"Analysis complete: {len(courses)} courses processed")
        return jsonify({'success': True, 'data': result})

    except Exception as e:
        logger.exception(f"Error processing upload: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Authentication Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/auth/google', methods=['POST'])
def auth_google():
    """Handle Google OAuth sign-in."""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email')
    name = data.get('name', '')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    try:
        # Create or get user
        user = create_user(email=email, name=name, provider='google')
        
        if not user:
            return jsonify({'error': 'Failed to create user'}), 500
        
        # Generate session token (email:random_hash)
        token_hash = hashlib.sha256(f"{email}{secrets.token_hex(16)}".encode()).hexdigest()[:32]
        session_token = f"{email}:{token_hash}"
        
        # Get user stats
        stats = get_user_stats(user['id'])
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'provider': user.get('provider', 'google'),
                'created_at': user.get('created_at'),
                'stats': stats
            },
            'token': session_token
        })
    
    except Exception as e:
        logger.exception(f"Auth error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/auth/user')
@require_auth
def get_user():
    """Get current user info."""
    user = g.user
    stats = get_user_stats(user['id']) if DB_AVAILABLE else {}
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'provider': user.get('provider', 'google'),
            'created_at': user.get('created_at'),
            'stats': stats
        }
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Scan History Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/history')
@require_auth
def get_history():
    """Get user's scan history."""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    user = g.user
    limit = request.args.get('limit', 50, type=int)
    
    scans = get_user_scans(user['id'], limit=min(limit, 100))
    
    # Simplify scan data for listing
    history = []
    for scan in scans:
        history.append({
            'id': scan['id'],
            'filename': scan['filename'],
            'total_courses': scan['total_courses'],
            'total_credits': float(scan['total_credits']),
            'cgpa': float(scan['cgpa']),
            'source': scan['source'],
            'created_at': scan['created_at']
        })
    
    return jsonify({
        'success': True,
        'count': len(history),
        'history': history
    })


@app.route('/history/<scan_id>')
@require_auth
def get_history_detail(scan_id):
    """Get detailed scan result."""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    scan = get_scan_by_id(scan_id)
    
    if not scan:
        return jsonify({'error': 'Scan not found'}), 404
    
    # Verify ownership
    if scan['user_id'] != g.user['id']:
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({
        'success': True,
        'scan': scan
    })


@app.route('/history/<scan_id>', methods=['DELETE'])
@require_auth
def delete_history(scan_id):
    """Delete a scan from history."""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    success = delete_scan(scan_id, g.user['id'])
    
    if not success:
        return jsonify({'error': 'Scan not found or access denied'}), 404
    
    return jsonify({'success': True, 'message': 'Scan deleted'})


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
