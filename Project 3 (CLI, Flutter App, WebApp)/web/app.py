"""
NSU Degree Audit Web Application
================================
Premium web interface with real-time OCR scanning display.
Upload PDF/Image -> Watch OCR extract text -> View 3-level analysis.

Run: python app.py
Access: http://localhost:5000
"""

import os
import sys
import json
import time
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flask import Flask, render_template, request, jsonify, send_from_directory, Response, stream_with_context
from werkzeug.utils import secure_filename

# Import our modules - using lightweight web-based OCR (no heavy model downloads!)
try:
    from src.ocr_web import WebOCR as TranscriptOCR  # Fast, free OCR.space API
except ImportError:
    from src.ocr_engine import TranscriptOCR  # Fallback to heavy OCR

from src.core import resolve_retakes, GRADE_POINTS, get_academic_standing, parse_knowledge_base

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

# Knowledge base path
KB_PATH = Path(__file__).parent.parent / 'knowledge_base.md'

# Only PDF and images
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and OCR extraction."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type. Only PDF, PNG, JPG allowed.'})

    filename = secure_filename(file.filename)
    filepath = app.config['UPLOAD_FOLDER'] / filename

    try:
        file.save(str(filepath))

        # OCR extraction
        ocr = TranscriptOCR()
        ocr_result = ocr.extract(str(filepath))

        # Cleanup immediately
        filepath.unlink(missing_ok=True)

        if not ocr_result.success:
            return jsonify({'success': False, 'error': ocr_result.error or 'OCR extraction failed'})

        if ocr_result.course_count == 0:
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
            'student_id': ocr_result.student_id
        }

        # Add raw extracted texts for display
        result['extracted_texts'] = ocr_result.raw_text[:100]  # First 100 texts

        return jsonify({'success': True, 'data': result})

    except Exception as e:
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

    if KB_PATH.exists():
        try:
            programs = parse_knowledge_base(str(KB_PATH))

            # Detect program from courses
            completed_codes = {c['code'] for c in course_details}
            detected_program = None

            for prog_key, prog_data in programs.items():
                mandatory = set(prog_data.get('mandatory', []))
                overlap = len(completed_codes & mandatory)
                if overlap > 3:  # At least 3 matching mandatory courses
                    detected_program = prog_key
                    break

            if detected_program and detected_program in programs:
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

    # ═══════════════════════════════════════════════════════════════════════════
    # Semester-grouped courses for display
    # ═══════════════════════════════════════════════════════════════════════════
    semesters = {}
    for c in course_details:
        sem = c['semester'] or 'Unknown'
        if sem not in semesters:
            semesters[sem] = []
        semesters[sem].append(c)

    # Sort semesters chronologically
    semester_order = {'Spring': 0, 'Summer': 1, 'Fall': 2}

    def sem_sort_key(sem_name):
        if sem_name == 'Unknown':
            return (9999, 9)
        parts = sem_name.split()
        if len(parts) == 2:
            return (int(parts[1]), semester_order.get(parts[0], 3))
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
    return send_from_directory('static', filename)


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  NSU Degree Audit - Premium Web Application")
    print("=" * 60)
    print(f"\n  Server: http://localhost:5000")
    print("  Press Ctrl+C to stop\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
