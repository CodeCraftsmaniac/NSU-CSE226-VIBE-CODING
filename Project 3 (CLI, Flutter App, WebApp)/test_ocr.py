#!/usr/bin/env python3
"""
Test script to verify OCR functionality
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env', override=True)

print("=" * 60)
print("OCR API Key Test")
print("=" * 60)

# Check environment variables
google_key = os.environ.get('GOOGLE_CLOUD_VISION_KEY', '')
ocr_space_key = os.environ.get('OCR_SPACE_API_KEY', '')

print(f"GOOGLE_CLOUD_VISION_KEY: {'Present (' + google_key[:20] + '...)' if google_key else 'MISSING!'}")
print(f"OCR_SPACE_API_KEY: {'Present (' + ocr_space_key[:10] + '...)' if ocr_space_key else 'MISSING!'}")

# Test WebOCR import
print("\nTesting WebOCR import...")
try:
    from ocr_web import WebOCR, OCR_SPACE_API_KEY, GOOGLE_VISION_API_KEY
    print(f"  Module-level GOOGLE_VISION_API_KEY: {'Present' if GOOGLE_VISION_API_KEY else 'MISSING!'}")
    print(f"  Module-level OCR_SPACE_API_KEY: {'Present' if OCR_SPACE_API_KEY else 'MISSING!'}")
    
    ocr = WebOCR()
    print(f"  Instance google_api_key: {'Present' if ocr.google_api_key else 'MISSING!'}")
    print(f"  Instance ocr_space_key: {'Present' if ocr.ocr_space_key else 'MISSING!'}")
    print("  WebOCR import: SUCCESS")
except Exception as e:
    print(f"  WebOCR import: FAILED - {e}")

# Test with the actual transcript if it exists
transcript_path = Path(__file__).parent / 'Transcript PDF.pdf'
if transcript_path.exists():
    print(f"\nTesting OCR on: {transcript_path}")
    print("This may take a moment...")
    
    try:
        result = ocr.extract(str(transcript_path))
        print(f"\n  Success: {result.success}")
        if result.success:
            print(f"  Engine used: {result.engine_used}")
            print(f"  Courses found: {result.course_count}")
            print(f"  Confidence: {result.confidence_score:.2%}")
            if result.courses:
                print(f"  First 3 courses: {[c.course_code for c in result.courses[:3]]}")
        else:
            print(f"  Error: {result.error}")
    except Exception as e:
        print(f"  OCR extraction failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"\nNo test file found at: {transcript_path}")

print("\n" + "=" * 60)
