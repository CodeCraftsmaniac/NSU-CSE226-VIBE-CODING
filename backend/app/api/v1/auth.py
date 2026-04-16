"""
Authentication Endpoints
========================
User authentication via Supabase Auth and device code flow for CLI.
FastAPI authentication endpoints.
"""
import sys
import os
import time
import secrets
import string
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel, EmailStr, Field

from app.middleware.rate_limit import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

# Add backend directory for local imports
backend_path = str(Path(__file__).parent.parent.parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Lazy settings loading
_settings = None

def get_settings_safe():
    """Get settings with fallback for missing config."""
    global _settings
    if _settings is None:
        try:
            from app.config import get_settings
            _settings = get_settings()
        except Exception as e:
            logger.warning(f"Could not load settings: {e}")
            class MinimalSettings:
                SUPABASE_URL = os.getenv('SUPABASE_URL', '')
                SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
                GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
                JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', '')
            _settings = MinimalSettings()
    return _settings


# Lazy imports for dependencies
def get_dependencies():
    """Lazy load dependency functions."""
    try:
        from app.dependencies import (
            get_current_user, get_current_user_optional, 
            get_db_user_id, DB_MODULE_AVAILABLE, AUTH_MODULE_AVAILABLE
        )
        return get_current_user, get_current_user_optional, get_db_user_id, DB_MODULE_AVAILABLE, AUTH_MODULE_AVAILABLE
    except Exception as e:
        logger.warning(f"Could not load dependencies: {e}")
        async def _get_current_user(authorization = None):
            raise HTTPException(401, "Auth not available")
        async def _get_current_user_optional(authorization = None):
            return None
        async def _get_db_user_id(user):
            return None
        return _get_current_user, _get_current_user_optional, _get_db_user_id, False, False


def get_auth_functions():
    """Lazy load auth functions."""
    try:
        from auth import get_auth_config as _get_auth_config, SUPABASE_SERVICE_ROLE_KEY
        return _get_auth_config, SUPABASE_SERVICE_ROLE_KEY
    except Exception:
        return None, None


def get_db_functions():
    """Lazy load database functions."""
    try:
        from database import (
            create_user, get_user_by_email, get_user_by_id, 
            get_user_stats, get_supabase
        )
        return create_user, get_user_by_email, get_user_by_id, get_user_stats, get_supabase
    except Exception:
        return None, None, None, None, None


def get_device_code_store_functions():
    """Lazy load persistent device-code helpers when the database is available."""
    try:
        from database import (
            save_device_code,
            get_device_code,
            consume_device_code,
            count_pending_device_codes,
            cleanup_expired_device_codes,
        )
        return (
            save_device_code,
            get_device_code,
            consume_device_code,
            count_pending_device_codes,
            cleanup_expired_device_codes,
        )
    except Exception:
        return None, None, None, None, None


# ═══════════════════════════════════════════════════════════════════════════════
# In-memory store for device codes (use Redis in production)
# ═══════════════════════════════════════════════════════════════════════════════

_DEVICE_CODE_TTL_SECONDS = 600
_MAX_PENDING_DEVICE_CODES = 1000
_DEVICE_CODE_BASE_URL = os.getenv("CLI_AUTH_WEB_URL", "https://ocr.nsunexus.app").rstrip("/")
_device_codes: Dict[str, Dict[str, Any]] = {}
_device_code_lock = threading.Lock()


def _cleanup_expired_device_codes(now: Optional[float] = None) -> None:
    """Remove expired device codes to keep the in-memory store bounded."""
    cutoff = now or time.time()
    expired_codes = [
        code
        for code, data in _device_codes.items()
        if cutoff > float(data.get("expires_at", 0))
    ]
    for code in expired_codes:
        _device_codes.pop(code, None)


def _upsert_device_code(device_code: str, payload: Dict[str, Any]) -> None:
    """Store or update a device code record after cleaning up expired entries."""
    with _device_code_lock:
        _cleanup_expired_device_codes()
        _device_codes[device_code] = payload


def _get_device_code(device_code: str) -> Optional[Dict[str, Any]]:
    """Fetch a non-expired device code record."""
    with _device_code_lock:
        _cleanup_expired_device_codes()
        record = _device_codes.get(device_code)
        return dict(record) if record else None


def _pop_device_code(device_code: str) -> Optional[Dict[str, Any]]:
    """Atomically consume a device code record."""
    with _device_code_lock:
        _cleanup_expired_device_codes()
        record = _device_codes.pop(device_code, None)
        return dict(record) if record else None


def _coerce_timestamp(value: Any) -> float:
    """Normalize database or in-memory timestamps to unix seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _normalize_device_code_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a persistent device-code record into the in-memory payload shape."""
    user_data = record.get("user_data")
    if not isinstance(user_data, dict):
        user_data = {}

    return {
        "status": record.get("status", "pending"),
        "created_at": _coerce_timestamp(record.get("created_at")) or time.time(),
        "expires_at": _coerce_timestamp(record.get("expires_at")),
        "token": record.get("token"),
        "user": user_data or None,
    }


def _count_pending_device_code_records() -> int:
    """Count pending device codes across persistent and fallback in-memory stores."""
    _, _, _, count_pending_device_codes, cleanup_device_codes = get_device_code_store_functions()
    db_count = 0
    if cleanup_device_codes:
        cleanup_device_codes()
    if count_pending_device_codes:
        db_count = count_pending_device_codes()

    with _device_code_lock:
        _cleanup_expired_device_codes()
        memory_count = len(_device_codes)

    return max(db_count, memory_count)


def _store_device_code_record(device_code: str, payload: Dict[str, Any]) -> None:
    """Persist a device code in the database when possible, else keep it in memory."""
    save_device_code, _, _, _, cleanup_device_codes = get_device_code_store_functions()
    if cleanup_device_codes:
        cleanup_device_codes()
    if save_device_code and save_device_code(
        device_code=device_code,
        status=payload.get("status", "pending"),
        token=payload.get("token"),
        user_data=payload.get("user"),
        created_at=payload.get("created_at"),
        expires_at=payload.get("expires_at"),
    ):
        return

    _upsert_device_code(device_code, payload)


def _load_device_code_record(device_code: str) -> Optional[Dict[str, Any]]:
    """Read a device code from persistent storage or the in-memory fallback."""
    _, get_device_code, _, _, cleanup_device_codes = get_device_code_store_functions()
    if cleanup_device_codes:
        cleanup_device_codes()
    if get_device_code:
        record = get_device_code(device_code)
        if record:
            payload = _normalize_device_code_record(record)
            if time.time() > payload.get("expires_at", 0):
                return None
            return payload

    return _get_device_code(device_code)


def _consume_device_code_record(device_code: str) -> Optional[Dict[str, Any]]:
    """Consume a completed device code from persistent storage or in-memory fallback."""
    _, _, consume_device_code, _, cleanup_device_codes = get_device_code_store_functions()
    if cleanup_device_codes:
        cleanup_device_codes()
    if consume_device_code:
        record = consume_device_code(device_code)
        if record:
            payload = _normalize_device_code_record(record)
            if time.time() > payload.get("expires_at", 0):
                return None
            return payload

    return _pop_device_code(device_code)


def verify_supabase_access_token(access_token: str) -> Optional[Dict[str, Any]]:
    """Verify an incoming Supabase access token without leaking backend internals."""
    try:
        from auth import verify_supabase_token
    except Exception as exc:
        logger.warning("Supabase token verifier unavailable: %s", exc)
        return None

    try:
        return verify_supabase_token(access_token)
    except Exception as exc:
        logger.warning("Supabase token verification failed: %s", exc)
        return None


def generate_device_code() -> str:
    """Generate a short, user-friendly device code."""
    # 8 character alphanumeric code (easy to type)
    chars = string.ascii_uppercase + string.digits
    # Remove confusing characters
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '').replace('L', '')
    return ''.join(secrets.choice(chars) for _ in range(8))


# ═══════════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class GoogleAuthRequest(BaseModel):
    """Google OAuth sign-in request from mobile/CLI apps."""
    email: EmailStr = Field(..., description="User email from Google OAuth")
    name: str = Field(default="", description="User display name")
    avatar_url: str = Field(default="", description="User avatar URL")
    provider: str = Field(default="google", description="Auth provider (google, cli)")
    access_token: Optional[str] = Field(
        default=None,
        description="Verified Supabase access token from a completed OAuth flow",
    )


class DeviceCodeResponse(BaseModel):
    """Device code creation response."""
    success: bool = True
    device_code: str
    user_code: str
    verification_url: str
    expires_in: int = 600
    interval: int = 2


class DevicePollRequest(BaseModel):
    """Device code polling request."""
    device_code: str


class DeviceVerifyRequest(BaseModel):
    """Device code verification request from web."""
    device_code: str
    access_token: str
    user: Dict[str, Any]


class AuthConfigResponse(BaseModel):
    """Auth configuration response."""
    success: bool = True
    config: Dict[str, str]
    auth_available: bool
    db_available: bool


class UserResponse(BaseModel):
    """User info response."""
    success: bool = True
    user: Dict[str, Any]


class TokenResponse(BaseModel):
    """Token response for successful authentication."""
    success: bool = True
    user: Dict[str, Any]
    token: str


# ═══════════════════════════════════════════════════════════════════════════════
# Auth Configuration
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/config", response_model=AuthConfigResponse)
@limiter.limit("30/minute")
async def auth_config(request: Request):
    """
    Get auth configuration for frontend apps.
    
    Returns Supabase and Google OAuth configuration needed for client-side auth.
    """
    _get_auth_config, _ = get_auth_functions()
    _, _, _, DB_MODULE_AVAILABLE, AUTH_MODULE_AVAILABLE = get_dependencies()
    settings = get_settings_safe()
    
    if _get_auth_config and AUTH_MODULE_AVAILABLE:
        config = _get_auth_config()
    else:
        config = {
            'supabase_url': getattr(settings, 'SUPABASE_URL', ''),
            'supabase_key': getattr(settings, 'SUPABASE_ANON_KEY', ''),
            'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', '')
        }
    
    return AuthConfigResponse(
        config=config,
        auth_available=AUTH_MODULE_AVAILABLE,
        db_available=DB_MODULE_AVAILABLE
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Google OAuth (Mobile/CLI Apps)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/google", response_model=TokenResponse)
@limiter.limit("5/minute")
async def auth_google(request: Request, auth_data: GoogleAuthRequest):
    """
    Handle Google OAuth sign-in from mobile apps and CLI.
    
    Mobile apps use Google Sign-In SDK, then send user info here.
    We create/get user in our database and return a session token.
    """
    create_user, _, _, _, get_supabase = get_db_functions()
    _, _, _, DB_MODULE_AVAILABLE, _ = get_dependencies()
    
    if not DB_MODULE_AVAILABLE or not create_user:
        logger.error("auth_google: DB_MODULE_AVAILABLE is False")
        raise HTTPException(
            status_code=503,
            detail="Database module not available"
        )
    
    if not auth_data.access_token:
        raise HTTPException(
            status_code=400,
            detail=(
                "Direct email login has been disabled. "
                "Use a verified Supabase/Google access token or the CLI device code flow."
            ),
        )

    verified_user = verify_supabase_access_token(auth_data.access_token)
    if not verified_user:
        raise HTTPException(status_code=401, detail="Invalid access token")

    verified_email = (verified_user.get("email") or "").strip().lower()
    requested_email = auth_data.email.strip().lower()
    if requested_email and verified_email and requested_email != verified_email:
        raise HTTPException(
            status_code=403,
            detail="Authenticated email does not match the requested account",
        )

    user_name = verified_user.get("name") or auth_data.name
    avatar_url = verified_user.get("avatar_url") or auth_data.avatar_url
    provider = verified_user.get("provider") or auth_data.provider or "google"

    logger.info(
        "auth_google: Processing verified login for %s (provider: %s)",
        verified_email or requested_email,
        provider,
    )
    
    try:
        # Create or get user
        db_user = create_user(
            email=verified_email or requested_email,
            name=user_name,
            provider=provider,
        )
        
        if not db_user:
            logger.error(
                "auth_google: create_user returned None for %s",
                verified_email or requested_email,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to create user - database connection issue"
            )
        
        logger.info(f"auth_google: User created/found: {db_user['id']}")
        
        # Update avatar if provided
        if auth_data.avatar_url and get_supabase:
            try:
                supabase = get_supabase()
                if supabase:
                    supabase.table('cse226_ocr_users').update({
                        'avatar_url': avatar_url
                    }).eq('id', db_user['id']).execute()
            except Exception:
                pass  # Avatar update is not critical
        
        return TokenResponse(
            user={
                'id': db_user['id'],
                'email': db_user['email'],
                'name': db_user.get('name', user_name),
                'avatar_url': avatar_url or db_user.get('avatar_url', ''),
                'provider': provider,
            },
            token=auth_data.access_token,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Verified Google auth error for %s", verified_email or requested_email)
        raise HTTPException(
            status_code=500,
            detail="Authentication failed"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Current User Info
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/user", response_model=UserResponse)
@limiter.limit("30/minute")
async def get_user_info(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Get current user info and create user in database if doesn't exist.
    
    Requires valid authentication token.
    """
    get_current_user, _, get_db_user_id, DB_MODULE_AVAILABLE, _ = get_dependencies()
    _, _, _, get_user_stats, _ = get_db_functions()
    
    # Get user from auth
    user = await get_current_user(authorization)
    
    # Get or create db_id for history queries
    db_user_id = await get_db_user_id(user)
    
    stats = {}
    if DB_MODULE_AVAILABLE and db_user_id and get_user_stats:
        stats = get_user_stats(db_user_id)
    
    return UserResponse(
        user={
            'id': user.get('id'),
            'db_id': db_user_id,
            'email': user.get('email'),
            'name': user.get('name', ''),
            'avatar_url': user.get('avatar_url', ''),
            'provider': user.get('provider', 'google'),
            'created_at': user.get('created_at'),
            'stats': stats
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Logout
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/logout")
@limiter.limit("10/minute")
async def logout(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Logout current user session.
    
    For stateless JWT tokens, this is primarily a client-side operation.
    Server-side can be used to invalidate tokens if using a blocklist.
    """
    _, get_current_user_optional, _, _, _ = get_dependencies()
    user = await get_current_user_optional(authorization)
    
    if user:
        logger.info(f"User logged out: {user.get('email')}")
    
    return {
        "success": True,
        "message": "Logged out successfully"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Device Code Flow for CLI Authentication
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/device/code", response_model=DeviceCodeResponse)
@limiter.limit("10/minute")
async def create_device_code_endpoint(request: Request):
    """
    Step 1: CLI requests a device code.
    
    Returns a code that user will enter on web to authenticate.
    Similar to: gh auth login, supabase login
    """
    if _count_pending_device_code_records() >= _MAX_PENDING_DEVICE_CODES:
        raise HTTPException(
            status_code=503,
            detail="Device sign-in is temporarily busy. Please try again in a minute.",
        )

    device_code = generate_device_code()
    user_code = f"{device_code[:4]}-{device_code[4:]}"  # Format: XXXX-XXXX
    
    # Store code with expiration (10 minutes)
    _store_device_code_record(device_code, {
        'status': 'pending',
        'created_at': time.time(),
        'expires_at': time.time() + _DEVICE_CODE_TTL_SECONDS,
        'token': None,
        'user': None
    })
    
    # Build verification URL
    verification_url = f"{_DEVICE_CODE_BASE_URL}/cli-auth?code={device_code}"
    
    return DeviceCodeResponse(
        device_code=device_code,
        user_code=user_code,
        verification_url=verification_url
    )


@router.post("/device/poll")
@limiter.limit("60/minute")
async def poll_device_code(request: Request, poll_data: DevicePollRequest):
    """
    Step 2: CLI polls this endpoint to check if user has authenticated.
    
    Returns pending, expired, or the token.
    """
    device_code = poll_data.device_code.replace('-', '').upper()
    
    code_data = _load_device_code_record(device_code) if device_code else None
    if not code_data:
        raise HTTPException(status_code=400, detail="Invalid device code")
    
    # Check if authenticated
    if code_data['status'] == 'complete':
        completed_record = _consume_device_code_record(device_code)
        if not completed_record:
            raise HTTPException(status_code=410, detail="Device code expired")

        token = completed_record['token']
        user = completed_record['user']
        return {
            'status': 'complete',
            'success': True,
            'token': token,
            'user': user
        }
    
    # Still pending
    return {
        'status': 'pending',
        'message': 'Waiting for user to authenticate...'
    }


@router.post("/device/verify")
@limiter.limit("10/minute")
async def verify_device_code(request: Request, verify_data: DeviceVerifyRequest):
    """
    Step 3: Web app calls this after user authenticates via Google.
    
    Links the device code to the authenticated user.
    """
    create_user, _, _, _, _ = get_db_functions()
    _, _, _, DB_MODULE_AVAILABLE, _ = get_dependencies()
    
    device_code = verify_data.device_code.replace('-', '').upper()
    
    code_data = _load_device_code_record(device_code) if device_code else None
    if not code_data:
        raise HTTPException(status_code=400, detail="Invalid or expired device code")
    
    if not verify_data.access_token or not verify_data.user:
        raise HTTPException(status_code=400, detail="Missing token or user data")
    
    # Verify Supabase access token before accepting device verification.
    verified_user = verify_supabase_access_token(verify_data.access_token)

    if not verified_user:
        raise HTTPException(status_code=401, detail="Invalid access token")

    raw_user = verify_data.user if isinstance(verify_data.user, dict) else {}
    user_metadata = raw_user.get('user_metadata', {}) if isinstance(raw_user.get('user_metadata', {}), dict) else {}

    email = verified_user.get('email') or raw_user.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="User email is missing")

    name = (
        verified_user.get('name')
        or user_metadata.get('full_name', '')
        or user_metadata.get('name', '')
    )
    avatar_url = (
        verified_user.get('avatar_url')
        or user_metadata.get('avatar_url', '')
        or user_metadata.get('picture', '')
    )

    db_user_id = None
    if DB_MODULE_AVAILABLE and create_user:
        db_user = create_user(email=email, name=name, provider='google')
        if db_user:
            db_user_id = db_user.get('id')

    # Mark code as complete. We return the verified Supabase access token so
    # mobile/CLI use the same auth token type as the web app.
    _store_device_code_record(device_code, {
        'status': 'complete',
        'token': verify_data.access_token,
        'user': {
            'id': verified_user.get('id') or raw_user.get('id'),
            'db_id': db_user_id,
            'email': email,
            'name': name,
            'avatar_url': avatar_url,
            'provider': verified_user.get('provider', 'google')
        },
        'created_at': code_data.get('created_at', time.time()),
        'expires_at': code_data['expires_at']
    })
    
    return {
        'success': True,
        'message': 'Device authenticated successfully'
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Legacy endpoints for backward compatibility
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/me")
@limiter.limit("30/minute")
async def get_current_user_me(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Alias for /user endpoint for compatibility.
    
    Returns current authenticated user info.
    """
    get_current_user, _, get_db_user_id, DB_MODULE_AVAILABLE, _ = get_dependencies()
    _, _, _, get_user_stats, _ = get_db_functions()
    
    user = await get_current_user(authorization)
    db_user_id = await get_db_user_id(user)
    
    stats = {}
    if DB_MODULE_AVAILABLE and db_user_id and get_user_stats:
        stats = get_user_stats(db_user_id)
    
    return {
        "success": True,
        "user": {
            'id': user.get('id'),
            'db_id': db_user_id,
            'email': user.get('email'),
            'name': user.get('name', ''),
            'avatar_url': user.get('avatar_url', ''),
            'provider': user.get('provider', 'google'),
            'created_at': user.get('created_at'),
            'stats': stats
        }
    }
