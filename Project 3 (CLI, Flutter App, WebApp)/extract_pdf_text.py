import fitz  # PyMuPDF
import sys

try:
    doc = fitz.open('694300494-nsu.pdf')
    text = ""
    for page in doc:
        text += page.get_text()
    print(text)
    doc.close()
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
