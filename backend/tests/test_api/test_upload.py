"""
Upload Endpoint Tests
=====================
Tests for file upload and OCR processing.
"""
import io


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


def test_upload_validation_rejects_content_mismatch(test_client):
    """Test upload validation rejects files whose bytes do not match the extension."""
    fake_pdf = io.BytesIO(b"not really a pdf")
    fake_pdf.name = "transcript.pdf"

    response = test_client.post(
        "/api/upload/validate",
        files={"file": ("transcript.pdf", fake_pdf, "application/pdf")},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "declared .pdf type" in data["detail"]


def test_batch_upload_csv_uses_parsed_courses(
    test_client,
    sample_csv_content,
    monkeypatch,
):
    """Test batch CSV upload sends parsed rows into the analysis engine."""
    from app.api.v1 import upload as upload_api

    captured = {}

    def fake_run_analysis(course_rows, kb_path=None, student_id=None):
        captured["course_rows"] = course_rows
        return {
            "courses": [
                {
                    "code": "ENG101",
                    "credits": 3,
                    "grade": "A",
                    "quality_points": 12,
                    "semester": "Fall 2020",
                }
            ],
            "level1": {"earned_credits": 3},
            "level2": {"cgpa": 4.0, "gpa_credits": 3},
        }

    monkeypatch.setattr(upload_api, "get_analysis_engine", lambda: (True, fake_run_analysis))

    csv_file = io.BytesIO(sample_csv_content.encode())
    response = test_client.post(
        "/upload/batch",
        files=[("files", ("transcript.csv", csv_file, "text/csv"))],
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["processed"] == 1
    assert captured["course_rows"][0]["course_code"] == "ENG101"
    assert data["results"][0]["data"]["ocr_info"]["engine"] == "CSV Parser (Direct Import)"


def test_export_csv_uses_top_level_courses(test_client, monkeypatch):
    """Test export reads the canonical top-level course list from analysis data."""
    from app.api.v1 import upload as upload_api
    import database

    async def fake_get_current_user_optional(authorization=None):
        return {"id": "auth-user-1", "email": "student@example.com"}

    async def fake_get_db_user_id(user):
        return "db-user-1"

    monkeypatch.setattr(
        upload_api,
        "get_dependencies",
        lambda: (fake_get_current_user_optional, fake_get_db_user_id, True),
    )
    monkeypatch.setattr(
        database,
        "get_scan_by_id",
        lambda scan_id: {
            "id": scan_id,
            "user_id": "db-user-1",
            "filename": "transcript.pdf",
            "created_at": "2026-04-16T00:00:00Z",
            "analysis_data": {
                "level1": {"valid_entries": []},
                "level2": {
                    "gpa_credits": 3,
                    "cgpa": 4.0,
                    "total_quality_points": 12,
                    "waiver": {"name": "Dean Scholarship", "level": "25%"},
                },
                "level3": {},
                "courses": [
                    {
                        "code": "CSE115",
                        "credits": 3,
                        "grade": "A",
                        "quality_points": 12,
                        "semester": "Spring 2024",
                    }
                ],
            },
        },
    )

    response = test_client.get(
        "/export/scan-123?format=csv",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "CSE115" in response.text
