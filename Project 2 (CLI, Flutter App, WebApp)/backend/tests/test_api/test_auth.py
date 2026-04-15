"""
Authentication Endpoint Tests
=============================
Tests for auth endpoints.
"""
import pytest


def test_auth_config(test_client):
    """Test auth config endpoint returns config."""
    response = test_client.get("/auth/config")
    assert response.status_code == 200
    data = response.json()
    # Config may be nested or at top level
    if "config" in data:
        assert "supabase_url" in data["config"]
    else:
        assert "supabaseUrl" in data or "supabase_url" in data


def test_auth_user_without_token(test_client):
    """Test /auth/user without token returns error."""
    response = test_client.get("/auth/user")
    assert response.status_code in [401, 404]


def test_auth_me_without_token(test_client):
    """Test /auth/me without token returns error."""
    response = test_client.get("/auth/me")
    assert response.status_code in [401, 404]


def test_device_code_request(test_client):
    """Test device code generation."""
    response = test_client.post("/auth/device/code")
    assert response.status_code == 200
    data = response.json()
    assert "device_code" in data
    assert "user_code" in data
    assert "verification_url" in data
    assert "expires_in" in data


def test_device_code_poll_invalid(test_client):
    """Test polling with invalid device code."""
    response = test_client.post(
        "/auth/device/poll",
        json={"device_code": "invalid-code"}
    )
    # May return 200 with error status or 400
    assert response.status_code in [200, 400]
