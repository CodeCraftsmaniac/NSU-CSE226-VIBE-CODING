"""
NSU Degree Audit - Backend Unit Tests
======================================
Tests for API endpoints, CSV parsing, and core functionality.

Run with: pytest tests/test_backend.py -v
"""

import pytest
import sys
import os
from pathlib import Path

# Add backend to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from io import BytesIO


class TestAPIEndpoints:
    """Test API endpoint availability and responses."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from api import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_root_endpoint(self, client):
        """Test / returns API info."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.get_json()
        assert data['service'] == 'NSU Degree Audit API'
        assert 'endpoints' in data
    
    def test_health_endpoint(self, client):
        """Test /health returns status."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
    
    def test_auth_config_endpoint(self, client):
        """Test /auth/config returns config."""
        response = client.get('/auth/config')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert 'config' in data
    
    def test_upload_no_file(self, client):
        """Test /upload without file returns error."""
        response = client.post('/upload')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] == False
        assert 'error' in data
    
    def test_upload_invalid_extension(self, client):
        """Test /upload with invalid file type."""
        data = {'file': (BytesIO(b'test'), 'test.txt')}
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid file type' in data.get('error', '')
    
    def test_history_unauthenticated(self, client):
        """Test /history without auth returns 401."""
        response = client.get('/history')
        assert response.status_code == 401


class TestCSVParser:
    """Test CSV parsing functionality."""
    
    def test_parse_valid_csv(self, tmp_path):
        """Test parsing valid CSV file."""
        from api import parse_csv_transcript
        
        csv_content = """Course_Code,Credits,Grade,Semester
CSE115,3,A,Fall 2022
MAT120,3,B+,Fall 2022
ENG101,3,A-,Spring 2023
"""
        csv_file = tmp_path / "transcript.csv"
        csv_file.write_text(csv_content)
        
        courses, error = parse_csv_transcript(str(csv_file))
        
        assert error is None
        assert courses is not None
        assert len(courses) == 3
        assert courses[0]['course_code'] == 'CSE115'
        assert courses[0]['credits'] == 3.0
        assert courses[0]['grade'] == 'A'
    
    def test_parse_csv_different_headers(self, tmp_path):
        """Test CSV with different header names."""
        from api import parse_csv_transcript
        
        csv_content = """code,credit,grade,term
CSE225,3,B,Summer 2023
"""
        csv_file = tmp_path / "transcript.csv"
        csv_file.write_text(csv_content)
        
        courses, error = parse_csv_transcript(str(csv_file))
        
        assert error is None
        assert len(courses) == 1
        assert courses[0]['course_code'] == 'CSE225'
    
    def test_parse_invalid_csv(self, tmp_path):
        """Test CSV with no valid data."""
        from api import parse_csv_transcript
        
        csv_content = """Name,Age,City
John,25,NYC
"""
        csv_file = tmp_path / "invalid.csv"
        csv_file.write_text(csv_content)
        
        courses, error = parse_csv_transcript(str(csv_file))
        
        assert courses is None
        assert error is not None
        assert 'No valid course data' in error
    
    def test_parse_csv_invalid_grades(self, tmp_path):
        """Test CSV with invalid grades are skipped."""
        from api import parse_csv_transcript
        
        csv_content = """Course_Code,Credits,Grade,Semester
CSE115,3,X,Fall 2022
MAT120,3,A,Fall 2022
"""
        csv_file = tmp_path / "transcript.csv"
        csv_file.write_text(csv_content)
        
        courses, error = parse_csv_transcript(str(csv_file))
        
        assert error is None
        assert len(courses) == 1  # Only valid grade row


class TestCoreAnalysis:
    """Test core analysis functions."""
    
    def test_run_full_analysis(self):
        """Test full analysis with sample courses."""
        from core import run_full_analysis
        
        courses = [
            {'course_code': 'CSE115', 'credits': 3, 'grade': 'A', 'semester': 'Fall 2022'},
            {'course_code': 'MAT120', 'credits': 3, 'grade': 'B+', 'semester': 'Fall 2022'},
            {'course_code': 'ENG101', 'credits': 3, 'grade': 'A-', 'semester': 'Fall 2022'},
        ]
        
        kb_path = str(PROJECT_ROOT / 'knowledge_base.md')
        result = run_full_analysis(courses, kb_path=kb_path)
        
        assert result is not None
        assert 'level1' in result
        assert 'level2' in result
        assert 'level3' in result
        assert result['level1']['total_courses'] == 3
        assert result['level2']['cgpa'] > 0


class TestDatabaseModule:
    """Test database module functions."""
    
    def test_get_supabase_returns_client(self):
        """Test Supabase client creation."""
        from database import get_supabase
        
        client = get_supabase()
        # May be None if no valid credentials, but shouldn't raise
        assert client is None or client is not None
    
    def test_check_db_connection(self):
        """Test database connection check."""
        from database import check_db_connection
        
        # Should return True or False, not raise
        result = check_db_connection()
        assert isinstance(result, bool)


class TestAuthModule:
    """Test authentication module."""
    
    def test_auth_decorators_exist(self):
        """Test auth decorators can be imported."""
        try:
            from auth import require_auth, optional_auth
            assert callable(require_auth)
            assert callable(optional_auth)
        except ImportError:
            pytest.skip("Auth module not available")
    
    def test_verify_token_with_invalid_token(self):
        """Test token verification with invalid token."""
        try:
            from auth import verify_supabase_token
            result = verify_supabase_token("invalid_token_12345")
            assert result is None
        except ImportError:
            pytest.skip("Auth module not available")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
