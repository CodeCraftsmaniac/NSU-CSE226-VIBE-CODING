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
import hashlib
import hmac
import base64
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Depends, Body, Header
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


# ═══════════════════════════════════════════════════════════════════════════════
# In-memory store for device codes (use Redis in production)
# ═══════════════════════════════════════════════════════════════════════════════

_device_codes: Dict[str, Dict[str, Any]] = {}


def generate_device_code() -> str:
    """Generate a short, user-friendly device code."""
    # 8 character alphanumeric code (easy to type)
    chars = string.ascii_uppercase + string.digits
    # Remove confusing characters
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '').replace('L', '')
    return ''.join(secrets.choice(chars) for _ in range(8))


def get_secret_key() -> bytes:
    """Get secret key for token signing (SHA256 hash of service key)."""
    _, SUPABASE_SERVICE_ROLE_KEY = get_auth_functions()
    settings = get_settings_safe()
    if SUPABASE_SERVICE_ROLE_KEY:
        return hashlib.sha256(SUPABASE_SERVICE_ROLE_KEY.encode()).digest()
    jwt_key = getattr(settings, 'JWT_SECRET_KEY', None)
    if not jwt_key:
        raise HTTPException(status_code=503, detail="JWT secret not configured")
    return hashlib.sha256(jwt_key.encode()).digest()


# ═══════════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class GoogleAuthRequest(BaseModel):
    """Google OAuth sign-in request from mobile/CLI apps."""
    email: EmailStr = Field(..., description="User email from Google OAuth")
    name: str = Field(default="", description="User display name")
    avatar_url: str = Field(default="", description="User avatar URL")
    provider: str = Field(default="google", description="Auth provider (google, cli)")


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
    
    logger.info(f"auth_google: Processing login for {auth_data.email} (provider: {auth_data.provider})")
    
    try:
        # Create or get user
        db_user = create_user(
            email=auth_data.email, 
            name=auth_data.name, 
            provider=auth_data.provider
        )
        
        if not db_user:
            logger.error(f"auth_google: create_user returned None for {auth_data.email}")
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
                        'avatar_url': auth_data.avatar_url
                    }).eq('id', db_user['id']).execute()
            except Exception:
                pass  # Avatar update is not critical
        
        # Generate a verifiable session token
        SECRET_KEY = get_secret_key()
        
        payload = {
            'user_id': db_user['id'],
            'email': db_user['email'],
            'exp': int(time.time()) + (30 * 24 * 60 * 60)  # 30 days expiry
        }
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        
        # Sign the payload with SHA256 hash of secret
        signature = hmac.new(SECRET_KEY, payload_b64.encode(), hashlib.sha256).hexdigest()
        token = f"{payload_b64}.{signature}"
        
        return TokenResponse(
            user={
                'id': db_user['id'],
                'email': db_user['email'],
                'name': db_user.get('name', auth_data.name),
                'avatar_url': auth_data.avatar_url or db_user.get('avatar_url', ''),
                'provider': auth_data.provider
            },
            token=token
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Google auth error for {auth_data.email}: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
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
    device_code = generate_device_code()
    user_code = f"{device_code[:4]}-{device_code[4:]}"  # Format: XXXX-XXXX
    
    # Store code with expiration (10 minutes)
    _device_codes[device_code] = {
        'status': 'pending',
        'created_at': time.time(),
        'expires_at': time.time() + 600,  # 10 minutes
        'token': None,
        'user': None
    }
    
    # Build verification URL
    base_url = "https://ocr.nsunexus.app"
    verification_url = f"{base_url}/cli-auth?code={device_code}"
    
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
    
    if not device_code or device_code not in _device_codes:
        raise HTTPException(status_code=400, detail="Invalid device code")
    
    code_data = _device_codes[device_code]
    
    # Check expiration
    if time.time() > code_data['expires_at']:
        del _device_codes[device_code]
        raise HTTPException(status_code=410, detail="Device code expired")
    
    # Check if authenticated
    if code_data['status'] == 'complete':
        token = code_data['token']
        user = code_data['user']
        del _device_codes[device_code]  # One-time use
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
    
    if not device_code or device_code not in _device_codes:
        raise HTTPException(status_code=400, detail="Invalid or expired device code")
    
    code_data = _device_codes[device_code]
    
    if time.time() > code_data['expires_at']:
        del _device_codes[device_code]
        raise HTTPException(status_code=410, detail="Device code expired")
    
    if not verify_data.access_token or not verify_data.user:
        raise HTTPException(status_code=400, detail="Missing token or user data")
    
    # Verify Supabase access token before accepting device verification.
    try:
        from auth import verify_supabase_token
        verified_user = verify_supabase_token(verify_data.access_token)
    except Exception as e:
        logger.warning(f"Device verify: token verification import failed: {e}")
        verified_user = None

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
    _device_codes[device_code] = {
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
        'expires_at': code_data['expires_at']
    }
    
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
