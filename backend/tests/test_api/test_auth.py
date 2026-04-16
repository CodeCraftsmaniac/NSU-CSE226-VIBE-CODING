"""
Authentication Endpoint Tests
=============================
Tests for auth endpoints.
"""


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


def test_auth_google_requires_verified_access_token(test_client):
    """Test /auth/google refuses legacy direct email-only login."""
    response = test_client.post(
        "/auth/google",
        json={
            "email": "student@example.com",
            "name": "Student",
            "provider": "cli",
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "disabled" in data["detail"].lower()


def test_auth_google_rejects_email_mismatch(test_client, monkeypatch):
    """Test /auth/google enforces the verified token identity."""
    from app.api.v1 import auth as auth_api

    monkeypatch.setattr(
        auth_api,
        "get_dependencies",
        lambda: (None, None, None, True, True),
    )
    monkeypatch.setattr(
        auth_api,
        "get_db_functions",
        lambda: (
            lambda email, name, provider="google": {
                "id": "db-user-1",
                "email": email,
                "name": name,
                "provider": provider,
            },
            None,
            None,
            None,
            None,
        ),
    )
    monkeypatch.setattr(
        auth_api,
        "verify_supabase_access_token",
        lambda token: {
            "id": "supabase-user-1",
            "email": "verified@example.com",
            "name": "Verified User",
            "provider": "google",
        },
    )

    response = test_client.post(
        "/auth/google",
        json={
            "email": "other@example.com",
            "name": "Client User",
            "provider": "cli",
            "access_token": "verified-token",
        },
    )
    assert response.status_code == 403
    data = response.json()
    assert "does not match" in data["detail"].lower()


def test_auth_google_uses_verified_identity(test_client, monkeypatch):
    """Test /auth/google returns the verified user and preserves the access token."""
    from app.api.v1 import auth as auth_api

    captured = {}

    def fake_create_user(email, name, provider="google"):
        captured.update({
            "email": email,
            "name": name,
            "provider": provider,
        })
        return {
            "id": "db-user-1",
            "email": email,
            "name": name,
            "provider": provider,
            "avatar_url": "",
        }

    monkeypatch.setattr(
        auth_api,
        "get_dependencies",
        lambda: (None, None, None, True, True),
    )
    monkeypatch.setattr(
        auth_api,
        "get_db_functions",
        lambda: (fake_create_user, None, None, None, None),
    )
    monkeypatch.setattr(
        auth_api,
        "verify_supabase_access_token",
        lambda token: {
            "id": "supabase-user-1",
            "email": "verified@example.com",
            "name": "Verified User",
            "avatar_url": "https://example.com/avatar.png",
            "provider": "google",
        },
    )

    response = test_client.post(
        "/auth/google",
        json={
            "email": "verified@example.com",
            "name": "Client User",
            "avatar_url": "https://example.com/client.png",
            "provider": "cli",
            "access_token": "verified-token",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["token"] == "verified-token"
    assert data["user"]["email"] == "verified@example.com"
    assert data["user"]["name"] == "Verified User"
    assert data["user"]["avatar_url"] == "https://example.com/avatar.png"
    assert captured == {
        "email": "verified@example.com",
        "name": "Verified User",
        "provider": "google",
    }
