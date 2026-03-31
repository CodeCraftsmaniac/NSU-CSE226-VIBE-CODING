import sys
sys.path.insert(0, 'backend')

from ocr_web import WebOCR

# Process the PDF
ocr = WebOCR()
result = ocr.extract('694300494-nsu.pdf')

if result.success:
    print(f"Student: {result.student_name}")
    print(f"ID: {result.student_id}")
    print(f"CGPA from PDF: {result.cgpa}")
    print(f"Total Credits from PDF: {result.total_credits}")
    print(f"Courses found: {result.course_count}")
    print(f"\nFirst 10 courses:")
    for i, course in enumerate(result.courses[:10]):
        print(f"  {course.course_code} - {course.credits} credits - Grade: {course.grade}")
    
    # Now run analysis
    from core import run_full_analysis
    courses = [
        {
            'course_code': c.course_code,
            'credits': c.credits,
            'grade': c.grade,
            'semester': c.semester
        }
        for c in result.courses
    ]
    
    analysis = run_full_analysis(courses, kb_path='knowledge_base.md')
    
    print(f"\n=== COMPARISON ===")
    print(f"PDF CGPA: {result.cgpa}")
    print(f"Calculated CGPA: {analysis['level2']['cgpa']}")
    print(f"Difference: {abs(result.cgpa - analysis['level2']['cgpa']):.2f}")
    print(f"\nPDF Total Credits: {result.total_credits}")
    print(f"Calculated Total Credits: {analysis['level1']['total_credits_attempted']}")
    print(f"Calculated Earned Credits: {analysis['level1']['earned_credits']}")
else:
    print(f"OCR failed: {result.error}")
