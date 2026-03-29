"""
Dump raw OCR text to a file for analysis.
Run: python scripts/debug_ocr.py
Output: ocr_dump.txt in project root
"""
import sys
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.join(base_dir, 'src'))

import fitz  # PyMuPDF

def dump_ocr():
    pdf_path = os.path.join(base_dir, "Transcript PDF.pdf")
    output_file = os.path.join(base_dir, "ocr_dump.txt")
    
    print(f"PDF: {pdf_path}")
    
    from src.ocr_web import WebOCR
    ocr = WebOCR()
    print(f"Google API: {'OK' if ocr.google_api_key else 'MISSING'}")
    print(f"OCR.space: {'OK' if ocr.ocr_space_key else 'MISSING'}")
    
    doc = fitz.open(pdf_path)
    all_text = []
    
    for page_num, page in enumerate(doc):
        print(f"Processing page {page_num + 1}...")
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        text, error = ocr._google_vision_ocr(img_data)
        if error or not text:
            text, error = ocr._ocr_space_ocr(img_data, f"page{page_num}.png")
        
        if text:
            all_text.append(f"\n{'='*60}\nPAGE {page_num + 1}\n{'='*60}\n")
            all_text.append(text)
            print(f"  Page {page_num + 1}: {len(text)} chars extracted")
        else:
            print(f"  Page {page_num + 1}: ERROR - {error}")
    
    doc.close()
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_text))
    
    print(f"\n*** RAW OCR TEXT SAVED TO: {output_file} ***")
    
    # Now test the parser
    full_text = '\n'.join(all_text)
    print(f"\n{'='*60}")
    print("TESTING PARSER:")
    print("="*60)
    
    result = ocr._parse_transcript_text(full_text)
    print(f"\nCourses found: {len(result.courses)}")
    print(f"Student: {result.student_name}")
    print(f"ID: {result.student_id}")
    print(f"CGPA: {result.cgpa}")
    
    print(f"\n{'='*60}")
    print("COURSES BY SEMESTER:")
    print("="*60)
    
    current_sem = ""
    for course in result.courses:
        if course.semester != current_sem:
            current_sem = course.semester
            print(f"\n--- {current_sem or 'Unknown Semester'} ---")
        print(f"  {course.course_code}: {course.grade} ({course.credits} cr)")
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(result.courses)} courses")
    print("="*60)

if __name__ == "__main__":
    dump_ocr()
