"""
Health Endpoint Tests
=====================
Tests for health check endpoints.
"""
import pytest


def test_root_endpoint(test_client):
    """Test root endpoint returns API info."""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "NSU Degree Audit API"
    assert data["framework"] == "FastAPI"
    assert data["status"] == "running"


def test_health_live(test_client):
    """Test liveness endpoint."""
    response = test_client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "live"]


def test_health_ready(test_client):
    """Test readiness endpoint."""
    response = test_client.get("/health/ready")
    # May return 200 or 503 depending on DB status
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data

