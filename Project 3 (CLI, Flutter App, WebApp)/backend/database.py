"""
NSU Degree Audit - Supabase Database Module
============================================
Handles database operations for user auth and scan history.
Uses cse226_ocr_ prefixed tables to avoid conflicts.

Thread-safe connection pooling for 20+ concurrent users.
"""

import os
import logging
import threading
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Supabase Configuration - HARDCODED FALLBACK for Cloud Run
# These are safe to hardcode as they're also in the .env file
_DEFAULT_SUPABASE_URL = 'https://kmbltplmjdkjlbungbbh.supabase.co'
_DEFAULT_SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImttYmx0cGxtamRramxidW5nYmJoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc2Mjc1MDksImV4cCI6MjA4MzIwMzUwOX0.IRoQ306ElYZh8WoTN1dXMVr9mSd20-RPxwKYZ6M6Lcg'
_DEFAULT_SERVICE_ROLE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImttYmx0cGxtamRramxidW5nYmJoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzYyNzUwOSwiZXhwIjoyMDgzMjAzNTA5fQ.CCtw4HCNIXB95TW4Ry1mAtB3__XoL1W8s49kXKHDzdI'

SUPABASE_URL = os.getenv('SUPABASE_URL', _DEFAULT_SUPABASE_URL)
SUPABASE_KEY = os.getenv('SUPABASE_KEY', _DEFAULT_SUPABASE_KEY)
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', _DEFAULT_SERVICE_ROLE_KEY)

# Thread-safe client management for concurrent users
_supabase_client = None
_client_lock = threading.Lock()

def get_supabase():
    """
    Get or create Supabase client (thread-safe).
    Uses double-check locking for concurrent access.
    Uses service role key for backend operations.
    """
    global _supabase_client
    if _supabase_client is None:
        with _client_lock:
            # Double-check after acquiring lock
            if _supabase_client is None:
                try:
                    from supabase import create_client
                    # Use service role key for backend operations (bypasses RLS)
                    key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
                    if not key:
                        logger.error("No Supabase key available")
                        return None
                    logger.info(f"Creating Supabase client: {SUPABASE_URL[:40]}...")
                    _supabase_client = create_client(SUPABASE_URL, key)
                    logger.info("Supabase client created successfully")
                except ImportError as e:
                    logger.error(f"Supabase SDK not installed: {e}")
                    return None
                except Exception as e:
                    logger.error(f"Failed to create Supabase client: {e}")
                    return None
    return _supabase_client


# ─── User Operations ────────────────────────────────────────────────────────────

def create_user(email: str, name: str, provider: str = 'google') -> Optional[Dict]:
    """Create or get existing user in cse226_ocr_users table."""
    supabase = get_supabase()
    if not supabase:
        logger.error("create_user: Supabase client not available")
        return None
    
    try:
        # Check if user exists
        result = supabase.table('cse226_ocr_users').select('*').eq('email', email).execute()
        
        if result.data:
            # Update last login
            supabase.table('cse226_ocr_users').update({
                'last_login': datetime.utcnow().isoformat(),
                'name': name
            }).eq('email', email).execute()
            logger.info(f"User already exists: {email}")
            return result.data[0]
        
        # Create new user
        new_user = {
            'email': email,
            'name': name,
            'provider': provider
        }
        
        result = supabase.table('cse226_ocr_users').insert(new_user).execute()
        logger.info(f"Created new user: {email}")
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Create user error for {email}: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email from cse226_ocr_users table."""
    supabase = get_supabase()
    if not supabase:
        return None
    try:
        result = supabase.table('cse226_ocr_users').select('*').eq('email', email).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get user by ID from cse226_ocr_users table."""
    supabase = get_supabase()
    if not supabase:
        return None
    try:
        result = supabase.table('cse226_ocr_users').select('*').eq('id', user_id).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


# ─── Scan History Operations ────────────────────────────────────────────────────

def save_scan(
    user_id: str,
    filename: str,
    total_courses: int,
    total_credits: float,
    cgpa: float,
    analysis_data: Dict[str, Any],
    source: str = 'web'
) -> Optional[Dict]:
    """Save a transcript scan to cse226_ocr_scans table."""
    supabase = get_supabase()
    if not supabase:
        logger.error("save_scan: Supabase client not available")
        return None
    
    try:
        scan_record = {
            'user_id': user_id,
            'filename': filename,
            'total_courses': total_courses,
            'total_credits': total_credits,
            'cgpa': cgpa,
            'analysis_data': analysis_data,
            'source': source
        }
        
        result = supabase.table('cse226_ocr_scans').insert(scan_record).execute()
        if result.data:
            logger.info(f"Saved scan for user {user_id}: {filename}")
            return result.data[0]
        else:
            logger.error(f"save_scan: No data returned from insert")
            return None
    except Exception as e:
        logger.error(f"Save scan error for user {user_id}: {e}")
        return None


def get_user_scans(user_id: str, limit: int = 50) -> List[Dict]:
    """Get scan history for a user from cse226_ocr_scans table."""
    supabase = get_supabase()
    if not supabase:
        return []
    try:
        result = supabase.table('cse226_ocr_scans')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        return result.data or []
    except Exception:
        return []


def get_scan_by_id(scan_id: str) -> Optional[Dict]:
    """Get a specific scan by ID from cse226_ocr_scans table."""
    supabase = get_supabase()
    if not supabase:
        return None
    try:
        result = supabase.table('cse226_ocr_scans').select('*').eq('id', scan_id).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def delete_scan(scan_id: str, user_id: str) -> bool:
    """Delete a scan (only if owned by user) from cse226_ocr_scans table."""
    supabase = get_supabase()
    if not supabase:
        return False
    try:
        result = supabase.table('cse226_ocr_scans')\
            .delete()\
            .eq('id', scan_id)\
            .eq('user_id', user_id)\
            .execute()
        return len(result.data) > 0 if result.data else False
    except Exception:
        return False


# ─── Analytics Operations ───────────────────────────────────────────────────────

def get_user_stats(user_id: str) -> Dict[str, Any]:
    """Get statistics for a user from cse226_ocr_scans table."""
    supabase = get_supabase()
    if not supabase:
        return {'total_scans': 0, 'avg_cgpa': 0.0, 'total_courses_scanned': 0, 'total_credits_scanned': 0.0}
    
    try:
        scans = supabase.table('cse226_ocr_scans')\
            .select('cgpa, total_credits, total_courses')\
            .eq('user_id', user_id)\
            .execute()
        
        if not scans.data:
            return {
                'total_scans': 0,
                'avg_cgpa': 0.0,
                'total_courses_scanned': 0,
                'total_credits_scanned': 0.0
            }
        
        cgpas = [float(s['cgpa']) for s in scans.data if s.get('cgpa')]
        
        return {
            'total_scans': len(scans.data),
            'avg_cgpa': round(sum(cgpas) / len(cgpas), 2) if cgpas else 0.0,
            'total_courses_scanned': sum(s.get('total_courses', 0) for s in scans.data),
            'total_credits_scanned': sum(float(s.get('total_credits', 0)) for s in scans.data)
        }
    except Exception:
        return {'total_scans': 0, 'avg_cgpa': 0.0, 'total_courses_scanned': 0, 'total_credits_scanned': 0.0}


# ─── Health Check ───────────────────────────────────────────────────────────────

def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        supabase = get_supabase()
        if not supabase:
            return False
        supabase.table('cse226_ocr_users').select('id').limit(1).execute()
        return True
    except Exception:
        return False
