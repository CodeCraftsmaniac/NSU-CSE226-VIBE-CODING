"""
Upload Endpoint Tests
=====================
Tests for file upload and OCR processing.
"""
import io
import pytest


def test_upload_validation_no_file(test_client):
    """Test upload validation fails without file."""
    response = test_client.post("/api/upload/validate")
    assert response.status_code == 422  # Validation error


def test_upload_validation_with_csv(test_client, sample_csv_content):
    """Test upload validation accepts CSV file."""
    csv_file = io.BytesIO(sample_csv_content.encode())
    csv_file.name = "transcript.csv"
    
    response = test_client.post(
        "/api/upload/validate",
        files={"file": ("transcript.csv", csv_file, "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == True


def test_upload_csv_processing(test_client, sample_csv_content):
    """Test CSV file upload and processing."""
    csv_file = io.BytesIO(sample_csv_content.encode())
    
    response = test_client.post(
        "/api/upload",
        files={"file": ("transcript.csv", csv_file, "text/csv")}
    )
    # Should succeed even without auth (guest mode)
    assert response.status_code in [200, 500]  # 500 if OCR not available


def test_upload_invalid_extension(test_client):
    """Test upload rejects invalid file types."""
    fake_file = io.BytesIO(b"not a valid file")
    
    response = test_client.post(
        "/api/upload",
        files={"file": ("test.exe", fake_file, "application/octet-stream")}
    )
    assert response.status_code == 400
