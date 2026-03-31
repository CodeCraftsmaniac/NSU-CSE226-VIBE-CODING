"""
Debug OCR extraction to find CGPA discrepancy.
Shows detailed extraction results and calculates CGPA step-by-step.
"""

import sys
from backend.ocr_web import WebOCR
from backend.core import GRADE_POINTS, resolve_retakes

def main():
    pdf_path = "694300494-nsu.pdf"
    
    print("\n" + "="*100)
    print("OCR EXTRACTION DEBUG - CGPA DISCREPANCY ANALYSIS")
    print("="*100)
    
    # Extract
    print("\n[STEP 1] Extracting courses from PDF...")
    ocr = WebOCR()
    result = ocr.extract(pdf_path)
    
    if not result.success:
        print(f"ERROR: {result.error}")
        sys.exit(1)
    
    print(f"  ✓ Extracted {len(result.courses)} courses using {result.engine_used}")
    print(f"  ✓ PDF shows official CGPA: 3.18")
    
    # Convert to dict format
    courses_raw = [
        {
            'course_code': c.course_code,
            'credits': c.credits,
            'grade': c.grade,
            'semester': c.semester
        }
        for c in result.courses
    ]
    
    # Resolve retakes
    print("\n[STEP 2] Resolving retakes...")
    resolved, retake_info = resolve_retakes(courses_raw)
    print(f"  ✓ {len(resolved)} unique courses after retake resolution")
    
    if retake_info:
        print(f"  ✓ Found {len(retake_info)} retaken courses:")
        for code, grades in retake_info.items():
            best = [r for r in resolved if r['course_code'] == code][0]['grade']
            print(f"      {code}: {' → '.join(grades)} (using {best})")
    
    # Calculate CGPA manually
    print("\n[STEP 3] Calculating CGPA...")
    print("-" * 100)
    print(f"{'Course':<12} {'Credits':<10} {'Grade':<8} {'GP':<8} {'QP':<10} {'Status':<15}")
    print("-" * 100)
    
    total_qp = 0.0
    gpa_credits = 0.0
    earned_credits = 0.0
    
    for r in resolved:
        code = r['course_code']
        credits = r['credits']
        grade = r['grade']
        
        # Determine status
        if grade in ('W', 'I'):
            status = 'EXCLUDED'
            gp = 0
            qp = 0
        elif grade in ('P', 'TR'):
            status = 'TRANSFER'
            gp = 0
            qp = 0
            earned_credits += credits
        elif grade in GRADE_POINTS:
            gp = GRADE_POINTS[grade]
            qp = gp * credits
            total_qp += qp
            gpa_credits += credits
            if grade != 'F':
                earned_credits += credits
            status = 'EARNED' if grade != 'F' else 'FAILED'
        else:
            status = 'UNKNOWN'
            gp = 0
            qp = 0
        
        print(f"{code:<12} {credits:<10.1f} {grade:<8} {gp:<8.2f} {qp:<10.2f} {status:<15}")
    
    print("-" * 100)
    print(f"{'TOTALS':<12} {'':<10} {'':<8} {'':<8} {total_qp:<10.2f}")
    print("-" * 100)
    
    cgpa = total_qp / gpa_credits if gpa_credits > 0 else 0.0
    
    print(f"\n[STEP 4] Final Calculation:")
    print(f"  Total Quality Points: {total_qp:.2f}")
    print(f"  Total GPA Credits: {gpa_credits:.1f}")
    print(f"  Calculated CGPA: {total_qp:.2f} ÷ {gpa_credits:.1f} = {cgpa:.2f}")
    print(f"  Official CGPA (from PDF): 3.18")
    print(f"  Difference: {abs(3.18 - cgpa):.2f} ({abs(3.18 - cgpa) / 3.18 * 100:.1f}% error)")
    
    print("\n[ANALYSIS]")
    if cgpa < 3.18:
        missing_qp = (3.18 * gpa_credits) - total_qp
        print(f"  Your calculated CGPA is LOWER by 0.07")
        print(f"  Missing Quality Points: {missing_qp:.2f}")
        print(f"  This suggests:")
        print(f"    • Missing courses with good grades (A/A-)")
        print(f"    • Grades misread as lower (A- read as B+)")
        print(f"    • Credits misread as lower (4.0 read as 3.0)")
        print(f"\n  To fix: Compare the course list above with your PDF")
        print(f"  Look for missing courses or incorrect grades in semesters with high performance")
    
    print("\n" + "="*100)

if __name__ == "__main__":
    main()
