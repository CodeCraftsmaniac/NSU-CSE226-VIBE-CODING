"""
Compare OCR-extracted courses with PDF to find CGPA discrepancy.

Usage: python compare_cgpa.py 694300494-nsu.pdf
"""

import sys
from backend.ocr_web import WebOCR
from backend.core import run_full_analysis

def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_cgpa.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print("\n" + "="*80)
    print("CGPA COMPARISON TOOL")
    print("="*80)
    
    # Extract with OCR
    print("\n[1/3] Extracting courses from PDF...")
    ocr = WebOCR()
    result = ocr.extract(pdf_path)
    
    if not result.success:
        print(f"ERROR: {result.error}")
        sys.exit(1)
    
    print(f"  ✓ Extracted {len(result.courses)} courses")
    print(f"  ✓ Engine: {result.engine_used}")
    print(f"  ✓ PDF CGPA: {result.cgpa}")
    
    # Run analysis
    print("\n[2/3] Running CGPA calculation...")
    courses_raw = [
        {
            'course_code': c.course_code,
            'credits': c.credits,
            'grade': c.grade,
            'semester': c.semester
        }
        for c in result.courses
    ]
    
    analysis = run_full_analysis(courses_raw)
    calculated_cgpa = analysis['level2']['cgpa']
    
    print(f"  ✓ Calculated CGPA: {calculated_cgpa}")
    print(f"  ✓ Difference: {abs(result.cgpa - calculated_cgpa):.2f}")
    
    # Show all courses
    print("\n[3/3] Extracted Courses:")
    print("-" * 80)
    print(f"{'Course':<12} {'Credits':<10} {'Grade':<8} {'Semester':<20}")
    print("-" * 80)
    
    for c in result.courses:
        print(f"{c.course_code:<12} {c.credits:<10.1f} {c.grade:<8} {c.semester:<20}")
    
    print("-" * 80)
    print(f"\nTotal courses: {len(result.courses)}")
    print(f"PDF CGPA: {result.cgpa}")
    print(f"Calculated CGPA: {calculated_cgpa}")
    print(f"Difference: {abs(result.cgpa - calculated_cgpa):.2f}")
    
    if abs(result.cgpa - calculated_cgpa) > 0.05:
        print("\n⚠ SIGNIFICANT DIFFERENCE DETECTED")
        print("Compare this list with your PDF to find:")
        print("  • Missing courses (especially with A/A- grades)")
        print("  • Incorrect grades (B instead of A-, etc.)")
        print("  • Incorrect credits (3.0 instead of 4.0)")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
