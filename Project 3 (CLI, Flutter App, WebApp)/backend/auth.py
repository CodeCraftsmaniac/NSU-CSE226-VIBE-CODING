"""
NSU Degree Audit - Authentication Module
=========================================
Handles Supabase Auth integration with Google OAuth.
"""

import os
from functools import wraps
from typing import Optional, Dict, Any

from flask import request, jsonify, g

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://kmbltplmjdkjlbungbbh.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')  # Anon key for frontend
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')  # Service role for backend

_supabase_client = None


def get_supabase():
    """Get Supabase client with service role key for backend operations."""
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
            # Use service role key for backend operations (bypasses RLS)
            key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
            _supabase_client = create_client(SUPABASE_URL, key)
        except Exception as e:
            print(f"Supabase client error: {e}")
            return None
    return _supabase_client


def verify_supabase_token(access_token: str) -> Optional[Dict[str, Any]]:
    """Verify Supabase access token and return user data."""
    supabase = get_supabase()
    if not supabase:
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
        print(f"Token verification error: {e}")
    
    return None


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current user from Authorization header."""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Try Supabase token verification
    user = verify_supabase_token(token)
    if user:
        # Sync user to our database
        sync_user_to_db(user)
        return user
    
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
        return db_user
    except Exception as e:
        print(f"User sync error: {e}")
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
    return {
        'supabase_url': SUPABASE_URL,
        'supabase_key': SUPABASE_KEY,  # Send anon key to frontend
        'google_client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
        'callback_url': f"{SUPABASE_URL}/auth/v1/callback"
    }
