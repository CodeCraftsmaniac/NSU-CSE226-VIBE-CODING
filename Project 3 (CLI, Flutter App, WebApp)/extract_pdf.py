import fitz
import sys

pdf_path = r"D:\Future projects\CSE226 VIBE CODING\Project 3 (CLI, Flutter App, WebApp)\Transcript PDF.pdf"

doc = fitz.open(pdf_path)
print(f"PDF has {len(doc)} pages")
print("="*60)

all_text = []
for i, page in enumerate(doc):
    text = page.get_text()
    if text.strip():
        all_text.append(f"--- PAGE {i+1} ---")
        all_text.append(text)
    else:
        all_text.append(f"--- PAGE {i+1} (NO TEXT - likely scanned image) ---")
        # Try to get images
        images = page.get_images(full=True)
        all_text.append(f"  Contains {len(images)} embedded image(s)")

doc.close()

for line in all_text:
    print(line)
