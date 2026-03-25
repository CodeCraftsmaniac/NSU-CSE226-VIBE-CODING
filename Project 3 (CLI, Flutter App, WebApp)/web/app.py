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

# ═══════════════════════════════════════════════════════════════════════════════
# Application Configuration
# ═══════════════════════════════════════════════════════════════════════════════

def create_app():
    """Application factory for Flask app."""
    app = Flask(__name__)

    # Load configuration from environment
    app.config['ENV'] = os.getenv('FLASK_ENV', 'production')
    app.config['DEBUG'] = os.getenv('DEBUG', 'false').lower() == 'true'
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'nsu-audit-default-key-change-in-prod')

    # File upload configuration
    max_mb = int(os.getenv('MAX_CONTENT_LENGTH_MB', '16'))
    app.config['MAX_CONTENT_LENGTH'] = max_mb * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
    app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

    # Create logs directory
    logs_dir = Path(__file__).parent.parent / 'logs'
    logs_dir.mkdir(exist_ok=True)

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

from src.core import resolve_retakes, GRADE_POINTS, get_academic_standing, parse_knowledge_base, compute_cgpa, validate_grade

# Knowledge base path
KB_PATH = Path(__file__).parent.parent / 'knowledge_base.md'

# Allowed file extensions
ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'pdf,png,jpg,jpeg').split(','))


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_program(courses):
    """Detect academic program from course prefixes.

    Uses prefix-based detection which is more reliable than matching mandatory courses.

    Args:
        courses: List of course dicts with 'code' key

    Returns:
        Program key ('CSE', 'LLB', etc.) or None if not detected
    """
    if not courses:
        return None

    prefix_counts = {}
    for c in courses:
        code = c.get('code', '')
        prefix_match = re.match(r'^([A-Z]{2,4})', code)
        if prefix_match:
            p = prefix_match.group(1)
            prefix_counts[p] = prefix_counts.get(p, 0) + 1

    if not prefix_counts:
        return None

    # CSE detection: CSE or EEE courses present
    cse_count = prefix_counts.get('CSE', 0) + prefix_counts.get('EEE', 0)
    if cse_count >= 3:
        return 'CSE'

    # LLB detection: LAW courses present
    if prefix_counts.get('LAW', 0) >= 2:
        return 'LLB'

    # BBA/Business detection
    bba_count = sum(prefix_counts.get(p, 0) for p in ['BUS', 'ACT', 'FIN', 'MKT', 'MGT'])
    if bba_count >= 3:
        return 'BBA'

    # Fallback: return most common prefix if it has enough courses
    most_common = max(prefix_counts, key=prefix_counts.get)
    if prefix_counts[most_common] >= 3:
        return most_common

    return None


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
        'version': '2.0.0'
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
        logger.info(f'File uploaded: {filename}')

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

        # Run all 3 levels of analysis
        result = run_full_analysis(courses)

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


def run_full_analysis(courses_raw):
    """Run all 3 levels of analysis on extracted courses."""

    # Convert to dict format for resolve_retakes
    courses = [
        {'course_code': c['course_code'], 'credits': c['credits'],
         'grade': c['grade'], 'semester': c.get('semester', '')}
        for c in courses_raw
        if c['course_code'] and c['grade']
    ]

    # Resolve retakes
    resolved, retake_info = resolve_retakes(courses)

    # ═══════════════════════════════════════════════════════════════════════════
    # LEVEL 1: Credit Tally
    # ═══════════════════════════════════════════════════════════════════════════
    total_credits = 0
    earned_credits = 0
    gpa_credits = 0
    total_qp = 0.0
    failed_credits = 0

    course_details = []

    for r in resolved:
        code = r['course_code']
        credits = r['credits']
        grade = r['grade']
        sem = r.get('semester', '')
        gp = GRADE_POINTS.get(grade)
        status = 'earned'

        if grade in ('W', 'I'):
            status = 'excluded'
        elif grade == 'F':
            status = 'failed'
            failed_credits += credits
            if credits > 0 and gp is not None:
                total_qp += gp * credits
                gpa_credits += credits
        elif gp is not None:
            if credits > 0:
                total_qp += gp * credits
                gpa_credits += credits
                earned_credits += credits
        elif grade in ('P', 'TR'):
            earned_credits += credits if credits > 0 else 0
            status = 'transfer'

        total_credits += credits

        course_details.append({
            'code': code,
            'credits': credits,
            'grade': grade,
            'semester': sem,
            'status': status,
            'grade_points': gp,
            'quality_points': round(gp * credits, 2) if gp and credits else 0
        })

    # Retakes info
    retakes = []
    resolved_grades = {r['course_code']: r['grade'] for r in resolved}
    for code, grades_list in retake_info.items():
        if len(grades_list) > 1:
            best_grade = resolved_grades.get(code, grades_list[-1])
            retakes.append({
                'code': code,
                'attempts': len(grades_list),
                'grades': grades_list,
                'best': best_grade
            })

    level1 = {
        'total_entries': len(courses),
        'unique_courses': len(resolved),
        'total_credits_attempted': total_credits,
        'earned_credits': earned_credits,
        'failed_credits': failed_credits,
        'retakes_count': len(retakes),
        'retakes': retakes,
        'progress_130': round(earned_credits / 130 * 100, 1)
    }

    # ═══════════════════════════════════════════════════════════════════════════
    # LEVEL 2: CGPA Analysis
    # ═══════════════════════════════════════════════════════════════════════════
    cgpa = round(total_qp / gpa_credits, 2) if gpa_credits > 0 else 0.0
    standing, stars = get_academic_standing(cgpa)

    # Grade distribution
    grade_dist = {}
    for c in course_details:
        g = c['grade']
        if g not in grade_dist:
            grade_dist[g] = 0
        grade_dist[g] += 1

    # Waiver eligibility
    waiver = None
    if earned_credits >= 30:
        if cgpa >= 3.97:
            waiver = {'level': '100%', 'name': "Chancellor's Award", 'color': 'gold'}
        elif cgpa >= 3.75:
            waiver = {'level': '50%', 'name': 'VC Scholarship', 'color': 'silver'}
        elif cgpa >= 3.50:
            waiver = {'level': '25%', 'name': "Dean's Scholarship", 'color': 'bronze'}

    level2 = {
        'cgpa': cgpa,
        'gpa_credits': gpa_credits,
        'total_quality_points': round(total_qp, 2),
        'standing': standing,
        'stars': stars,
        'grade_distribution': grade_dist,
        'waiver': waiver
    }

    # ═══════════════════════════════════════════════════════════════════════════
    # LEVEL 3: Degree Audit (if knowledge base exists)
    # ═══════════════════════════════════════════════════════════════════════════
    level3 = None

    # Use prefix-based program detection first
    detected_program = detect_program(course_details)
    completed_codes = {c['code'] for c in course_details}

    if KB_PATH.exists() and detected_program:
        try:
            programs = parse_knowledge_base(str(KB_PATH))

            if detected_program in programs:
                prog = programs[detected_program]
                mandatory = prog.get('mandatory', [])
                elective_groups = prog.get('elective_groups', {})

                completed_mandatory = [c for c in mandatory if c in completed_codes]
                missing_mandatory = [c for c in mandatory if c not in completed_codes]

                # Elective analysis
                elective_status = {}
                for group_name, group_data in elective_groups.items():
                    required = group_data.get('required', 0)
                    options = group_data.get('courses', [])
                    completed_in_group = [c for c in options if c in completed_codes]
                    elective_status[group_name] = {
                        'required': required,
                        'completed': len(completed_in_group),
                        'courses': completed_in_group,
                        'satisfied': len(completed_in_group) >= required
                    }

                level3 = {
                    'program': detected_program,
                    'program_name': prog.get('full_name', detected_program),
                    'mandatory_total': len(mandatory),
                    'mandatory_completed': len(completed_mandatory),
                    'mandatory_missing': missing_mandatory,
                    'mandatory_progress': round(len(completed_mandatory) / len(mandatory) * 100, 1) if mandatory else 0,
                    'elective_status': elective_status,
                    'graduation_ready': len(missing_mandatory) == 0 and earned_credits >= 130
                }
        except Exception:
            pass

    # Fallback: show detected program even without knowledge base
    if level3 is None and detected_program:
        level3 = {
            'program': detected_program,
            'program_name': f'{detected_program} Program (detected)',
            'mandatory_total': 0,
            'mandatory_completed': 0,
            'mandatory_missing': [],
            'mandatory_progress': 0,
            'elective_status': {},
            'graduation_ready': False,
            'note': 'Knowledge base not available for detailed audit'
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # Semester-grouped courses for display
    # ═══════════════════════════════════════════════════════════════════════════
    semesters = {}
    for c in course_details:
        sem = c['semester'] or 'Not Specified'
        if sem not in semesters:
            semesters[sem] = []
        semesters[sem].append(c)

    # Sort semesters chronologically
    semester_order = {'Spring': 0, 'Summer': 1, 'Fall': 2}

    def sem_sort_key(sem_name):
        if sem_name == 'Not Specified':
            return (9999, 9)
        parts = sem_name.split()
        if len(parts) == 2:
            try:
                return (int(parts[1]), semester_order.get(parts[0], 3))
            except ValueError:
                return (9999, 9)
        return (9999, 9)

    sorted_semesters = []
    for sem_name in sorted(semesters.keys(), key=sem_sort_key):
        sorted_semesters.append({
            'name': sem_name,
            'courses': semesters[sem_name]
        })

    return {
        'level1': level1,
        'level2': level2,
        'level3': level3,
        'courses': course_details,
        'semesters': sorted_semesters
    }


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

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    print("\n" + "=" * 60)
    print("  NSU Degree Audit - Premium Web Application")
    print("=" * 60)
    print(f"\n  Environment: {app.config['ENV']}")
    print(f"  Debug: {debug}")
    print(f"  Server: http://{host}:{port}")
    print("  Press Ctrl+C to stop\n")

    if app.config['ENV'] == 'production' and not debug:
        # Use production server
        try:
            from waitress import serve
            print("  Using Waitress production server...")
            serve(app, host=host, port=port)
        except ImportError:
            print("  Waitress not installed, using Flask dev server (not recommended for production)")
            app.run(debug=False, host=host, port=port)
    else:
        # Development mode
        app.run(debug=debug, host=host, port=port)
