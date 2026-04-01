"""
NSU Degree Audit - Authentication Module
=========================================
Handles Supabase Auth integration with Google OAuth.
"""

import os
import logging
from functools import wraps
from typing import Optional, Dict, Any

from flask import request, jsonify, g

logger = logging.getLogger(__name__)

# Load configuration from centralized settings
try:
    from app.config import get_settings
    _settings = get_settings()
    SUPABASE_URL = _settings.SUPABASE_URL
    SUPABASE_KEY = _settings.SUPABASE_ANON_KEY
    SUPABASE_SERVICE_ROLE_KEY = _settings.SUPABASE_SERVICE_ROLE_KEY
    logger.info("Auth module: Loaded settings from config")
except Exception as e:
    # Fail with clear error message - no hardcoded fallbacks
    logger.critical(f"Auth module: Failed to load settings: {e}")
    logger.critical("Ensure all required environment variables are set (see .env.example)")
    raise RuntimeError(f"Missing required configuration: {e}")

_supabase_client = None


def get_supabase():
    """Get Supabase client with service role key for backend operations."""
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
            # Use service role key for backend operations (bypasses RLS)
            key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
            if not key:
                logger.error("No Supabase key available in auth module")
                return None
            _supabase_client = create_client(SUPABASE_URL, key)
            logger.info("Auth module: Supabase client created")
        except Exception as e:
            logger.error(f"Supabase client error: {e}")
            return None
    return _supabase_client


def verify_supabase_token(access_token: str) -> Optional[Dict[str, Any]]:
    """Verify Supabase access token and return user data."""
    supabase = get_supabase()
    if not supabase:
        logger.error("verify_supabase_token: Supabase client not available")
        return None
    
    try:
        # Get user from Supabase Auth
        user_response = supabase.auth.get_user(access_token)
        if user_response and user_response.user:
            user = user_response.user
            return {
                'id': user.id,
                'email': user.email,
                'name': user.user_metadata.get('full_name') or user.user_metadata.get('name', ''),
                'avatar_url': user.user_metadata.get('avatar_url', ''),
                'provider': user.app_metadata.get('provider', 'google'),
                'created_at': str(user.created_at) if user.created_at else None
            }
    except Exception as e:
        logger.error(f"Token verification error: {e}")
    
    return None


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current user from Authorization header.
    
    Supports two token types:
    1. Supabase JWT tokens (from web app Google OAuth)
    2. CLI tokens (simple hash tokens from /auth/google)
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Try Supabase token verification first (web app Google OAuth)
    user = verify_supabase_token(token)
    if user:
        # Sync user to our database
        sync_user_to_db(user)
        return user
    
    # Try CLI token verification (from /auth/google endpoint)
    user = verify_cli_token(token)
    if user:
        return user
    
    return None


def verify_cli_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify CLI token (self-contained JWT-like token)."""
    import hashlib
    import hmac
    import base64
    import json
    import time
    
    try:
        # Token format: base64_payload.signature
        if '.' not in token:
            return None
        
        parts = token.split('.', 1)
        if len(parts) != 2:
            return None
        
        payload_b64, signature = parts
        
        # Verify signature
        SECRET_KEY = SUPABASE_SERVICE_ROLE_KEY[:32] if SUPABASE_SERVICE_ROLE_KEY else 'fallback-secret-key'
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            logger.debug("CLI token: signature mismatch")
            return None
        
        # Decode payload
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        
        # Check expiry
        if payload.get('exp', 0) < time.time():
            logger.debug("CLI token: expired")
            return None
        
        # Get user from database to get full info
        try:
            from database import get_user_by_id
            db_user = get_user_by_id(payload['user_id'])
            if db_user:
                return {
                    'id': db_user['id'],
                    'db_id': db_user['id'],
                    'email': db_user['email'],
                    'name': db_user.get('name', ''),
                    'avatar_url': db_user.get('avatar_url', ''),
                    'provider': db_user.get('provider', 'cli'),
                    'created_at': db_user.get('created_at')
                }
        except Exception as e:
            logger.debug(f"CLI token: db lookup failed: {e}")
        
        # Fallback: return info from token payload
        return {
            'id': payload['user_id'],
            'db_id': payload['user_id'],
            'email': payload['email'],
            'name': '',
            'avatar_url': '',
            'provider': 'cli',
            'created_at': None
        }
        
    except Exception as e:
        logger.debug(f"CLI token verification error: {e}")
    return None


def sync_user_to_db(user: Dict[str, Any]) -> Optional[Dict]:
    """Sync authenticated user to cse226_ocr_users table."""
    try:
        from database import create_user
        db_user = create_user(
            email=user['email'],
            name=user.get('name', ''),
            provider=user.get('provider', 'google')
        )
        if db_user:
            user['db_id'] = db_user['id']
            logger.info(f"User synced to DB: {user['email']} -> {db_user['id']}")
        else:
            logger.warning(f"Failed to sync user to DB: {user['email']}")
        return db_user
    except Exception as e:
        logger.error(f"User sync error: {e}")
        return None


def require_auth(f):
    """Decorator requiring valid authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
        g.user = user
        return f(*args, **kwargs)
    return decorated


def optional_auth(f):
    """Decorator that optionally captures auth info."""
    @wraps(f)
    def decorated(*args, **kwargs):
        g.user = get_current_user()
        return f(*args, **kwargs)
    return decorated


def get_auth_config() -> Dict[str, Any]:
    """Get auth configuration for frontend."""
    # Get Google Client ID from settings
    try:
        from app.config import get_settings
        settings = get_settings()
        google_client_id = settings.GOOGLE_CLIENT_ID
    except Exception:
        google_client_id = os.getenv('GOOGLE_CLIENT_ID', '')
    
    # Clean up if secret was accidentally concatenated
    if ' ' in google_client_id:
        google_client_id = google_client_id.split(' ')[0]
    
    return {
        'supabase_url': SUPABASE_URL,
        'supabase_key': SUPABASE_KEY,  # Send anon key to frontend
        'google_client_id': google_client_id,
        'callback_url': f"{SUPABASE_URL}/auth/v1/callback"
    }
