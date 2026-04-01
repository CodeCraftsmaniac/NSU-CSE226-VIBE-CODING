"""
NSU Degree Audit - Backend API
==============================
Pure REST API backend for OCR processing and degree analysis.
NO UI - only JSON endpoints for CLI, Web, and Flutter apps.
Version: 2.3.1 - Auth and scan history fully integrated

Endpoints:
  GET  /health        - Service health, OCR limits, system info
  POST /upload        - Upload transcript PDF/image for OCR + analysis
  GET  /              - API info (JSON)
  
Auth Endpoints:
  GET  /auth/config   - Get auth configuration for frontend
  GET  /auth/user     - Get current user info
  GET  /auth/callback - OAuth callback handler
  
History Endpoints:
  GET  /history       - Get user's scan history
  GET  /history/<id>  - Get specific scan
  DELETE /history/<id> - Delete a scan
"""

import os
import sys
import time
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

from flask import Flask, request, jsonify, g, redirect

# Enable CORS for all frontends
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

# Auth module
try:
    from auth import (
        require_auth, optional_auth, get_current_user,
        get_auth_config, verify_supabase_token
    )
    AUTH_AVAILABLE = True
except Exception as e:
    AUTH_AVAILABLE = False
    print(f"Auth module not available: {e}")
    # Fallback decorators
    def require_auth(f):
        from functools import wraps
        @wraps(f)
        def decorated(*args, **kwargs):
            return jsonify({'error': 'Auth not available'}), 503
        return decorated
    def optional_auth(f):
        from functools import wraps
        @wraps(f)
        def decorated(*args, **kwargs):
            g.user = None
            return f(*args, **kwargs)
        return decorated

# Database module
try:
    from database import (
        create_user, get_user_by_email, get_user_by_id,
        save_scan, get_user_scans, get_scan_by_id, delete_scan,
        get_user_stats, check_db_connection, save_user_token
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
logger.info("NSU Degree Audit API initialized")

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
# CSV Parser for Direct Course Import
# ═══════════════════════════════════════════════════════════════════════════════

def parse_csv_transcript(filepath: str):
    """
    Parse CSV file with course data.
    
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
    import csv
    
    courses = []
    
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            # Try to detect dialect
            sample = f.read(2048)
            f.seek(0)
            
            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error:
                dialect = csv.excel
            
            # Check if has header
            has_header = csv.Sniffer().has_header(sample)
            f.seek(0)
            
            reader = csv.reader(f, dialect)
            
            # Column mapping
            col_map = {'code': 0, 'credits': 1, 'grade': 2, 'semester': 3}
            
            for i, row in enumerate(reader):
                if not row or all(not cell.strip() for cell in row):
                    continue
                
                # Handle header row
                if i == 0 and has_header:
                    # Try to map columns from header
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
        
    except UnicodeDecodeError:
        return None, "Could not read CSV file. Please ensure it's UTF-8 encoded."
    except Exception as e:
        return None, f"Error parsing CSV: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """API root - service info."""
    return jsonify({
        'service': 'NSU Degree Audit API',
        'version': '2.3.1',
        'project': 'CSE226 Project 3',
        'endpoints': {
            'GET /': 'This info',
            'GET /health': 'Health check with OCR limits and system info',
            'POST /upload': 'Upload transcript (PDF, PNG, JPG, CSV) for analysis',
            'POST /auth/google': 'Google OAuth sign-in',
            'GET /auth/user': 'Get current user info',
            'GET /history': 'Get scan history (requires auth)',
            'GET /history/<id>': 'Get specific scan (requires auth)',
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
        'version': '2.3.1',
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
    
    # Log auth status
    if g.user:
        logger.info(f"Upload request from authenticated user: {g.user.get('email')}")
    else:
        logger.info("Upload request from unauthenticated user (guest mode)")
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    # Validate extension
    allowed = {'pdf', 'png', 'jpg', 'jpeg', 'csv'}
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

        # Handle CSV files directly (no OCR needed)
        if ext == 'csv':
            courses, csv_error = parse_csv_transcript(str(filepath))
            filepath.unlink(missing_ok=True)
            
            if csv_error:
                return jsonify({'success': False, 'error': csv_error}), 400
            
            if not courses:
                return jsonify({'success': False, 'error': 'No valid courses found in CSV'}), 400
            
            # Run analysis on parsed courses
            result = run_full_analysis(courses, kb_path=str(KB_PATH))
            
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
            }

            # Note: CGPA and total_credits are NOT extracted from PDF
            # They are calculated by the analysis engine based on extracted courses

        # Save to history if user is authenticated
        scan_id = None
        if g.user and DB_AVAILABLE:
            logger.info(f"Attempting to save scan for user: {g.user.get('email')}")
            try:
                # Get db_id for database operations
                db_user_id = g.user.get('db_id')
                if not db_user_id:
                    logger.info(f"No db_id in g.user, fetching from database by email: {g.user['email']}")
                    # Try to get from database by email
                    db_user = get_user_by_email(g.user['email'])
                    if not db_user:
                        logger.info(f"User not found in database, creating: {g.user['email']}")
                        # Create user if doesn't exist
                        db_user = create_user(
                            email=g.user['email'],
                            name=g.user.get('name', ''),
                            provider=g.user.get('provider', 'google')
                        )
                    if db_user:
                        db_user_id = db_user['id']
                        logger.info(f"Got db_user_id: {db_user_id}")
                
                if db_user_id:
                    level2 = result.get('level2', {})
                    logger.info(f"Saving scan: {file.filename}, courses: {len(courses)}, cgpa: {level2.get('cgpa', 0)}")
                    scan_record = save_scan(
                        user_id=db_user_id,
                        filename=file.filename,
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
        elif not g.user:
            logger.info("No user in g.user, skipping history save")
        elif not DB_AVAILABLE:
            logger.warning("Database not available, skipping history save")

        logger.info(f"Analysis complete: {len(courses)} courses processed")
        return jsonify({'success': True, 'data': result})

    except Exception as e:
        logger.exception(f"Error processing upload: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Authentication Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/auth/config')
def auth_config():
    """Get auth configuration for frontend apps."""
    if AUTH_AVAILABLE:
        config = get_auth_config()
    else:
        config = {
            'supabase_url': os.getenv('SUPABASE_URL', ''),
            'supabase_key': os.getenv('SUPABASE_KEY', ''),
            'google_client_id': os.getenv('GOOGLE_CLIENT_ID', '')
        }
    
    return jsonify({
        'success': True,
        'config': config,
        'auth_available': AUTH_AVAILABLE,
        'db_available': DB_AVAILABLE
    })


@app.route('/auth/google', methods=['POST'])
def auth_google():
    """Handle Google OAuth sign-in from mobile apps and CLI.
    
    Mobile apps use Google Sign-In SDK, then send user info here.
    We create/get user in our database and return a session token.
    """
    if not DB_AVAILABLE:
        logger.error("auth_google: DB_AVAILABLE is False")
        return jsonify({'error': 'Database module not available', 'code': 'DB_MODULE_MISSING'}), 503
    
    data = request.get_json() or {}
    email = data.get('email')
    name = data.get('name', '')
    avatar_url = data.get('avatar_url', '')
    provider = data.get('provider', 'google')  # 'cli' for CLI app
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    logger.info(f"auth_google: Processing login for {email} (provider: {provider})")
    
    try:
        # Create or get user
        db_user = create_user(email=email, name=name, provider=provider)
        
        if not db_user:
            logger.error(f"auth_google: create_user returned None for {email}")
            return jsonify({
                'error': 'Failed to create user - database connection issue',
                'code': 'USER_CREATE_FAILED'
            }), 500
        
        logger.info(f"auth_google: User created/found: {db_user['id']}")
        
        # Update avatar if provided
        if avatar_url and DB_AVAILABLE:
            try:
                from database import get_supabase
                supabase = get_supabase()
                if supabase:
                    supabase.table('cse226_ocr_users').update({
                        'avatar_url': avatar_url
                    }).eq('id', db_user['id']).execute()
            except Exception:
                pass  # Avatar update is not critical
        
        # Generate a verifiable session token (JWT-like but simpler)
        import hashlib
        import hmac
        import base64
        import json as token_json
        import time as token_time
        
        # Secret key for signing - use hardcoded fallback for Cloud Run
        from auth import SUPABASE_SERVICE_ROLE_KEY as AUTH_SERVICE_KEY
        SECRET_KEY = AUTH_SERVICE_KEY[:32] if AUTH_SERVICE_KEY else 'fallback-secret-key'[:32]
        
        # Token payload
        payload = {
            'user_id': db_user['id'],
            'email': db_user['email'],
            'exp': int(token_time.time()) + (30 * 24 * 60 * 60)  # 30 days expiry
        }
        payload_b64 = base64.urlsafe_b64encode(token_json.dumps(payload).encode()).decode()
        
        # Sign the payload
        signature = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        token = f"{payload_b64}.{signature}"
        
        return jsonify({
            'success': True,
            'user': {
                'id': db_user['id'],
                'email': db_user['email'],
                'name': db_user.get('name', name),
                'avatar_url': avatar_url or db_user.get('avatar_url', ''),
                'provider': provider
            },
            'token': token
        })
    except Exception as e:
        logger.exception(f"Google auth error for {email}: {e}")
        return jsonify({'error': str(e), 'code': 'AUTH_ERROR'}), 500


@app.route('/auth/user')
@require_auth
def get_user():
    """Get current user info and create user in database if doesn't exist."""
    user = g.user
    
    # Get or create db_id for history queries
    db_user_id = user.get('db_id')
    if not db_user_id and DB_AVAILABLE:
        db_user = get_user_by_email(user['email'])
        if not db_user:
            # Create user in database if doesn't exist
            db_user = create_user(
                email=user['email'],
                name=user.get('name', ''),
                provider=user.get('provider', 'google')
            )
        if db_user:
            db_user_id = db_user['id']
    
    stats = get_user_stats(db_user_id) if DB_AVAILABLE and db_user_id else {}
    
    return jsonify({
        'success': True,
        'user': {
            'id': user.get('id'),
            'db_id': db_user_id,
            'email': user.get('email'),
            'name': user.get('name', ''),
            'avatar_url': user.get('avatar_url', ''),
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
    
    # Get db_id for queries
    db_user_id = user.get('db_id')
    if not db_user_id:
        db_user = get_user_by_email(user['email'])
        if db_user:
            db_user_id = db_user['id']
    
    if not db_user_id:
        return jsonify({'success': True, 'count': 0, 'history': []})
    
    scans = get_user_scans(db_user_id, limit=min(limit, 100))
    
    # Simplify scan data for listing
    history = []
    for scan in scans:
        history.append({
            'id': scan['id'],
            'filename': scan['filename'],
            'total_courses': scan['total_courses'],
            'total_credits': float(scan['total_credits']) if scan.get('total_credits') else 0,
            'cgpa': float(scan['cgpa']) if scan.get('cgpa') else 0,
            'source': scan.get('source', 'web'),
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
    
    # Get db_id for ownership check
    user = g.user
    db_user_id = user.get('db_id')
    if not db_user_id:
        db_user = get_user_by_email(user['email'])
        if db_user:
            db_user_id = db_user['id']
    
    # Verify ownership
    if scan['user_id'] != db_user_id:
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
    
    # Get db_id
    user = g.user
    db_user_id = user.get('db_id')
    if not db_user_id:
        db_user = get_user_by_email(user['email'])
        if db_user:
            db_user_id = db_user['id']
    
    if not db_user_id:
        return jsonify({'error': 'User not found'}), 404
    
    success = delete_scan(scan_id, db_user_id)
    
    if not success:
        return jsonify({'error': 'Scan not found or access denied'}), 404
    
    return jsonify({'success': True, 'message': 'Scan deleted'})


# ═══════════════════════════════════════════════════════════════════════════════
# Device Code Flow for CLI Authentication (like GitHub CLI / Supabase CLI)
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory store for device codes (use Redis in production)
_device_codes = {}

import secrets
import string

def generate_device_code():
    """Generate a short, user-friendly device code."""
    # 8 character alphanumeric code (easy to type)
    chars = string.ascii_uppercase + string.digits
    # Remove confusing characters
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '').replace('L', '')
    return ''.join(secrets.choice(chars) for _ in range(8))


@app.route('/auth/device/code', methods=['POST'])
def create_device_code():
    """
    Step 1: CLI requests a device code.
    Returns a code that user will enter on web to authenticate.
    Similar to: gh auth login, supabase login
    """
    device_code = generate_device_code()
    user_code = f"{device_code[:4]}-{device_code[4:]}"  # Format: XXXX-XXXX
    
    # Store code with expiration (10 minutes)
    _device_codes[device_code] = {
        'status': 'pending',
        'created_at': time.time(),
        'expires_at': time.time() + 600,  # 10 minutes
        'token': None,
        'user': None
    }
    
    verification_url = f"https://ocr.nsunexus.app/cli-auth?code={device_code}"
    
    return jsonify({
        'success': True,
        'device_code': device_code,
        'user_code': user_code,
        'verification_url': verification_url,
        'expires_in': 600,
        'interval': 2  # Poll every 2 seconds
    })


@app.route('/auth/device/poll', methods=['POST'])
def poll_device_code():
    """
    Step 2: CLI polls this endpoint to check if user has authenticated.
    Returns pending, expired, or the token.
    """
    data = request.get_json() or {}
    device_code = data.get('device_code', '').replace('-', '').upper()
    
    if not device_code or device_code not in _device_codes:
        return jsonify({'error': 'Invalid device code'}), 400
    
    code_data = _device_codes[device_code]
    
    # Check expiration
    if time.time() > code_data['expires_at']:
        del _device_codes[device_code]
        return jsonify({'status': 'expired', 'error': 'Device code expired'}), 410
    
    # Check if authenticated
    if code_data['status'] == 'complete':
        token = code_data['token']
        user = code_data['user']
        del _device_codes[device_code]  # One-time use
        return jsonify({
            'status': 'complete',
            'success': True,
            'token': token,
            'user': user
        })
    
    # Still pending
    return jsonify({
        'status': 'pending',
        'message': 'Waiting for user to authenticate...'
    })


@app.route('/auth/device/verify', methods=['POST'])
def verify_device_code():
    """
    Step 3: Web app calls this after user authenticates via Google.
    Links the device code to the authenticated user.
    """
    data = request.get_json() or {}
    device_code = data.get('device_code', '').replace('-', '').upper()
    access_token = data.get('access_token')
    user_data = data.get('user')
    
    if not device_code or device_code not in _device_codes:
        return jsonify({'error': 'Invalid or expired device code'}), 400
    
    code_data = _device_codes[device_code]
    
    if time.time() > code_data['expires_at']:
        del _device_codes[device_code]
        return jsonify({'error': 'Device code expired'}), 410
    
    if not access_token or not user_data:
        return jsonify({'error': 'Missing token or user data'}), 400
    
    # Get or create user in our database
    email = user_data.get('email')
    name = user_data.get('user_metadata', {}).get('full_name', '') or user_data.get('user_metadata', {}).get('name', '')
    
    if DB_AVAILABLE and email:
        db_user = create_user(email=email, name=name, provider='google')
        if db_user:
            user_data['db_id'] = db_user['id']
    
    # Generate our own token for CLI
    import hashlib
    import hmac
    import base64
    import json as token_json
    
    from auth import SUPABASE_SERVICE_ROLE_KEY as AUTH_SERVICE_KEY
    SECRET_KEY = AUTH_SERVICE_KEY[:32] if AUTH_SERVICE_KEY else 'cli-device-auth-key'[:32]
    
    payload = {
        'user_id': user_data.get('db_id') or user_data.get('id'),
        'email': email,
        'exp': int(time.time()) + (30 * 24 * 3600)  # 30 days
    }
    
    payload_bytes = base64.urlsafe_b64encode(token_json.dumps(payload).encode()).decode()
    signature = hmac.new(SECRET_KEY.encode(), payload_bytes.encode(), hashlib.sha256).hexdigest()[:16]
    cli_token = f"{payload_bytes}.{signature}"
    
    # Mark code as complete
    _device_codes[device_code] = {
        'status': 'complete',
        'token': cli_token,
        'user': {
            'id': user_data.get('id'),
            'db_id': user_data.get('db_id'),
            'email': email,
            'name': name,
            'avatar_url': user_data.get('user_metadata', {}).get('avatar_url', ''),
            'provider': 'google'
        },
        'expires_at': code_data['expires_at']
    }
    
    return jsonify({
        'success': True,
        'message': 'Device authenticated successfully'
    })


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
