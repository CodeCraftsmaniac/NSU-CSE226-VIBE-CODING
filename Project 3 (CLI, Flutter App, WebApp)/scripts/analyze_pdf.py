"""
Script to analyze the transcript PDF and extract all text content.
Run this to understand what's in the PDF before testing OCR.
"""
import sys
import os
import shutil

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

# Delete data folder first
data_dir = os.path.join(base_dir, "data")
if os.path.exists(data_dir):
    shutil.rmtree(data_dir)
    print(f"DELETED: {data_dir}")
else:
    print(f"Data folder doesn't exist: {data_dir}")

import fitz  # PyMuPDF

def analyze_pdf(pdf_path):
    """Analyze PDF and extract all text content."""
    doc = fitz.open(pdf_path)
    print(f"\nPDF: {pdf_path}")
    print(f"Pages: {len(doc)}")
    print("=" * 70)
    
    all_text = []
    total_images = 0
    
    for i, page in enumerate(doc):
        text = page.get_text()
        images = page.get_images(full=True)
        total_images += len(images)
        
        print(f"\n--- PAGE {i+1} ---")
        print(f"Text length: {len(text)} chars, Images: {len(images)}")
        
        if text.strip():
            print(text)
            all_text.append(text)
        else:
            print("(No extractable text - scanned image)")
    
    doc.close()
    
    print("\n" + "=" * 70)
    print(f"SUMMARY: {len(doc)} pages, {total_images} images, {sum(len(t) for t in all_text)} total chars")
    
    return '\n'.join(all_text)

if __name__ == "__main__":
    pdf_path = os.path.join(base_dir, "Transcript PDF.pdf")
    analyze_pdf(pdf_path)
