"""
Shared Dependencies
===================
Common dependencies for FastAPI dependency injection.
Integrates with existing auth.py module for token verification.
"""
import os
import sys
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import Header, HTTPException, Depends

from app.config import get_settings

# Add backend directory for importing existing modules
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

settings = get_settings()
logger = logging.getLogger(__name__)

# Import existing auth functions
try:
    from auth import verify_supabase_token, verify_cli_token, sync_user_to_db
    AUTH_MODULE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Auth module not available: {e}")
    AUTH_MODULE_AVAILABLE = False
    
    # Fallback implementations
    def verify_supabase_token(token: str) -> Optional[Dict]:
        return None
    
    def verify_cli_token(token: str) -> Optional[Dict]:
        return None
    
    def sync_user_to_db(user: Dict) -> Optional[Dict]:
        return None

# Import database functions
try:
    from database import (
        get_user_by_email, create_user, get_user_by_id,
        check_db_connection
    )
    DB_MODULE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Database module not available: {e}")
    DB_MODULE_AVAILABLE = False
    
    def get_user_by_email(email: str) -> Optional[Dict]:
        return None
    
    def create_user(email: str, name: str, provider: str = 'google') -> Optional[Dict]:
        return None
    
    def get_user_by_id(user_id: str) -> Optional[Dict]:
        return None
    
    def check_db_connection() -> bool:
        return False


async def get_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """Extract API key from header if present."""
    return x_api_key


async def verify_api_key(api_key: Optional[str] = Depends(get_api_key)) -> str:
    """Verify that a valid API key was provided against database."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required"
        )
    
    # Validate API key against database
    if DB_MODULE_AVAILABLE:
        try:
            from database import get_supabase
            supabase = get_supabase()
            if supabase:
                result = supabase.table('cse226_ocr_api_keys').select('*').eq('key', api_key).eq('revoked', False).execute()
                if result.data:
                    return api_key
        except Exception:
            pass
    
    # If no database or key not found, check against env var as fallback
    valid_keys = os.environ.get('API_KEYS', '').split(',')
    if api_key in valid_keys and api_key:
        return api_key
    
    raise HTTPException(
        status_code=401,
        detail="Invalid or revoked API key"
    )


async def get_current_user_optional(
    authorization: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    Extract and verify user from Authorization header.
    
    Supports two token types:
    1. Supabase JWT tokens (from web app Google OAuth)
    2. CLI tokens (simple hash tokens from /auth/google)
    
    Returns None if no valid auth, does not raise exception.
    """
    if not authorization:
        return None
    
    # Handle both "Bearer token" and raw token formats
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    if not token:
        return None
    
    # Try Supabase token verification first (web app Google OAuth)
    user = verify_supabase_token(token)
    if user:
        # Sync user to our database
        if DB_MODULE_AVAILABLE:
            sync_user_to_db(user)
        return user
    
    # Try CLI token verification (from /auth/google endpoint)
    user = verify_cli_token(token)
    if user:
        return user
    
    return None


async def get_current_user(
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Require authenticated user.
    
    Raises HTTPException 401 if not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def get_db_user_id(user: Dict[str, Any]) -> Optional[str]:
    """
    Get the database user ID for the authenticated user.
    
    This handles the case where user comes from Supabase (has 'id')
    vs from our database (has 'db_id').
    """
    # First check if we already have db_id
    db_user_id = user.get('db_id')
    if db_user_id:
        return db_user_id
    
    # Try to get from database by email
    if DB_MODULE_AVAILABLE and user.get('email'):
        db_user = get_user_by_email(user['email'])
        if not db_user:
            # Create user in database if doesn't exist
            db_user = create_user(
                email=user['email'],
                name=user.get('name', ''),
                provider=user.get('provider', 'google')
            )
        if db_user:
            return db_user['id']
    
    return None


def require_db():
    """Dependency that requires database to be available."""
    if not DB_MODULE_AVAILABLE or not check_db_connection():
        raise HTTPException(
            status_code=503,
            detail="Database not available"
        )
    return True


def require_auth_module():
    """Dependency that requires auth module to be available."""
    if not AUTH_MODULE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Authentication module not available"
        )
    return True
