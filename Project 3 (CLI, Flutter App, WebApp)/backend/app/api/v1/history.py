"""
History Endpoints
=================
User audit history management.
FastAPI history endpoints.
"""
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Request, Query, Depends, Header
from pydantic import BaseModel, Field

from app.middleware.rate_limit import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

# Add backend directory for local imports
backend_path = str(Path(__file__).parent.parent.parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# Lazy loading functions
def get_dependencies():
    """Lazy load dependency functions."""
    try:
        from app.dependencies import (
            get_current_user_optional, get_db_user_id, 
            DB_MODULE_AVAILABLE
        )
        
        async def require_auth(authorization):
            """Wrapper to require authentication."""
            user = await get_current_user_optional(authorization)
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return user
        
        def require_db():
            """Wrapper to require database."""
            if not DB_MODULE_AVAILABLE:
                raise HTTPException(503, "Database not available")
        
        return require_auth, get_db_user_id, DB_MODULE_AVAILABLE, require_db
    except Exception as e:
        logger.warning(f"Could not load dependencies: {e}")
        async def _require_auth(authorization = None):
            raise HTTPException(401, "Auth not available")
        async def _get_db_user_id(user):
            return None
        def _require_db():
            raise HTTPException(503, "Database not available")
        return _require_auth, _get_db_user_id, False, _require_db


def get_db_functions():
    """Lazy load database functions."""
    try:
        from database import (
            get_user_scans, get_scan_by_id, delete_scan, get_user_by_email
        )
        return get_user_scans, get_scan_by_id, delete_scan, get_user_by_email
    except Exception:
        return None, None, None, None


# ═══════════════════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class ScanSummary(BaseModel):
    """Summary of a scan for listing."""
    id: str
    filename: str
    total_courses: int
    total_credits: float
    cgpa: float
    source: str = "web"
    created_at: str
    
    class Config:
        from_attributes = True


class HistoryListResponse(BaseModel):
    """History list response."""
    success: bool = True
    count: int
    history: List[ScanSummary]


class ScanDetailResponse(BaseModel):
    """Scan detail response."""
    success: bool = True
    scan: Dict[str, Any]


class DeleteResponse(BaseModel):
    """Delete operation response."""
    success: bool = True
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# History Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/history", response_model=HistoryListResponse)
@limiter.limit("30/minute")
async def get_history(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items to return"),
    authorization: Optional[str] = Header(None)
):
    """
    Get user's scan history.
    
    Returns a list of previous transcript scans.
    Requires authentication.
    """
    get_current_user, get_db_user_id, DB_MODULE_AVAILABLE, require_db = get_dependencies()
    get_user_scans, _, _, _ = get_db_functions()
    
    # Require DB
    require_db()
    
    # Get user
    user = await get_current_user(authorization)
    logger.info(f"History request for user: {user.get('email')}")
    
    if not get_user_scans:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Get db_id for queries
    db_user_id = await get_db_user_id(user)
    logger.info(f"User db_id: {db_user_id}")
    
    if not db_user_id:
        logger.warning(f"Could not get db_user_id for {user.get('email')}")
        return HistoryListResponse(count=0, history=[])
    
    scans = get_user_scans(db_user_id, limit=min(limit, 100))
    logger.info(f"Found {len(scans)} scans for user {db_user_id}")
    
    # Simplify scan data for listing
    history = []
    for scan in scans:
        history.append(ScanSummary(
            id=scan['id'],
            filename=scan['filename'],
            total_courses=scan['total_courses'],
            total_credits=float(scan['total_credits']) if scan.get('total_credits') else 0,
            cgpa=float(scan['cgpa']) if scan.get('cgpa') else 0,
            source=scan.get('source', 'web'),
            created_at=scan['created_at']
        ))
    
    return HistoryListResponse(count=len(history), history=history)


@router.get("/history/{scan_id}", response_model=ScanDetailResponse)
@limiter.limit("30/minute")
async def get_history_detail(
    request: Request,
    scan_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get detailed scan result.
    
    Returns full audit results including courses and requirements.
    Requires authentication and ownership of the scan.
    """
    import json
    
    get_current_user, get_db_user_id, _, require_db = get_dependencies()
    _, get_scan_by_id, _, _ = get_db_functions()
    
    # Require DB
    require_db()
    
    # Get user
    user = await get_current_user(authorization)
    
    if not get_scan_by_id:
        raise HTTPException(status_code=503, detail="Database not available")
    
    scan = get_scan_by_id(scan_id)
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Get db_id for ownership check
    db_user_id = await get_db_user_id(user)
    
    # Verify ownership
    if scan['user_id'] != db_user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Ensure analysis_data is properly parsed (handle if it's a JSON string)
    if isinstance(scan.get('analysis_data'), str):
        try:
            scan['analysis_data'] = json.loads(scan['analysis_data'])
        except json.JSONDecodeError:
            logger.error(f"Failed to parse analysis_data for scan {scan_id}")
    
    return ScanDetailResponse(scan=scan)


@router.delete("/history/{scan_id}", response_model=DeleteResponse)
@limiter.limit("10/minute")
async def delete_history_item(
    request: Request,
    scan_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Delete a scan from history.
    
    Permanently removes the scan record. Cannot be undone.
    Requires authentication and ownership of the scan.
    """
    get_current_user, get_db_user_id, _, require_db = get_dependencies()
    _, _, delete_scan, _ = get_db_functions()
    
    # Require DB
    require_db()
    
    # Get user
    user = await get_current_user(authorization)
    
    if not delete_scan:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Get db_id
    db_user_id = await get_db_user_id(user)
    
    if not db_user_id:
        raise HTTPException(status_code=404, detail="User not found")
    
    success = delete_scan(scan_id, db_user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Scan not found or access denied")
    
    return DeleteResponse(message="Scan deleted")


@router.delete("/history", response_model=DeleteResponse)
@limiter.limit("3/minute")
async def clear_history(
    request: Request,
    confirm: bool = Query(False, description="Must be true to confirm deletion"),
    authorization: Optional[str] = Header(None)
):
    """
    Clear all audit history.
    
    Permanently removes all audit records. Cannot be undone.
    Requires confirmation parameter set to true.
    """
    get_current_user, get_db_user_id, _, require_db = get_dependencies()
    get_user_scans, _, delete_scan, _ = get_db_functions()
    
    # Require DB
    require_db()
    
    # Get user
    user = await get_current_user(authorization)
    
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Must provide confirm=true query parameter to delete all history"
        )
    
    if not get_user_scans or not delete_scan:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Get db_id
    db_user_id = await get_db_user_id(user)
    
    if not db_user_id:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Batch delete all scans for user (performance optimization)
    try:
        from database import get_supabase
        supabase = get_supabase()
        if supabase:
            result = supabase.table('cse226_ocr_scans').delete().eq('user_id', db_user_id).execute()
            deleted_count = len(result.data) if result.data else 0
        else:
            # Fallback to individual deletes if direct access not available
            scans = get_user_scans(db_user_id, limit=1000)
            deleted_count = 0
            for scan in scans:
                if delete_scan(scan['id'], db_user_id):
                    deleted_count += 1
    except Exception as e:
        logger.error(f"Batch delete error: {e}")
        # Fallback to individual deletes
        scans = get_user_scans(db_user_id, limit=1000)
        deleted_count = 0
        for scan in scans:
            if delete_scan(scan['id'], db_user_id):
                deleted_count += 1
    
    logger.info(f"Cleared {deleted_count} scans for user {user.get('email')}")
    
    return DeleteResponse(message=f"Deleted {deleted_count} scans")
