import os
import shutil
import fitz  # PyMuPDF

# Step 1: Delete the data folder
data_folder = "./data"
if os.path.exists(data_folder):
    try:
        shutil.rmtree(data_folder)
        print("✓ Data folder deleted successfully\n")
    except Exception as e:
        print(f"✗ Error deleting data folder: {e}\n")
else:
    print("Data folder not found\n")

# Step 2: Extract text from PDF
print("=" * 70)
print("EXTRACTING PDF CONTENT")
print("=" * 70 + "\n")

try:
    doc = fitz.open(r"Transcript PDF.pdf")
    print(f"PDF has {len(doc)} pages\n")

    for i, page in enumerate(doc):
        print(f"=== PAGE {i+1} ===")
        
        # Try text extraction first
        text = page.get_text()
        if text.strip():
            print("TEXT CONTENT:")
            print(text)
        else:
            print("No selectable text - this is a scanned image")
        
        # Check for images
        images = page.get_images(full=True)
        print(f"\nImages on page: {len(images)}")
        print("-" * 70)

    doc.close()
    print("\n✓ PDF extraction complete")
    
except Exception as e:
    print(f"\n✗ Error reading PDF: {e}")
