"""
Pytest Configuration and Fixtures
=================================
Shared fixtures for all tests.
"""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Set test environment variables before importing app
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only")
os.environ.setdefault("GOOGLE_VISION_API_KEY", "test-google-vision-key")
os.environ.setdefault("AZURE_DOC_INTELLIGENCE_KEY", "")
os.environ.setdefault("AZURE_DOC_INTELLIGENCE_ENDPOINT", "")


@pytest.fixture(scope="session")
def test_client():
    """Create a test client for the FastAPI app."""
    from app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_csv_content():
    """Sample CSV data for testing."""
    return """Course Code,Course Title,Credits,Grade,Semester
ENG101,English Composition,3,A,Fall 2020
MAT120,Basic Mathematics,3,A-,Fall 2020
CSE115,Programming Language I,3,A,Spring 2021
PHY107,Physics I,3,B+,Spring 2021
CSE173,Discrete Mathematics,3,A,Summer 2021
"""


@pytest.fixture
def sample_transcript_data():
    """Sample transcript data for testing."""
    return {
        "student_name": "Test Student",
        "student_id": "0920402 S 42",
        "department": "CSE",
        "cgpa": 3.75,
        "total_credits": 130,
        "courses": [
            {"code": "ENG101", "credits": 3, "grade": "A", "semester": "Fall 2020"},
            {"code": "MAT120", "credits": 3, "grade": "A-", "semester": "Fall 2020"},
            {"code": "CSE115", "credits": 3, "grade": "A", "semester": "Spring 2021"},
        ]
    }


@pytest.fixture
def auth_headers():
    """Mock authorization headers."""
    return {"Authorization": "Bearer test-token"}
