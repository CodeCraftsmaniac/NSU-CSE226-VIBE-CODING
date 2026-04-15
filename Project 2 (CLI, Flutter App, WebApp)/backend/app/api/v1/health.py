"""
Health Check Endpoints
======================
Liveness and readiness probes for container orchestration.
Premium health endpoint with detailed system info.
Real-time health monitoring for dashboard.
"""
import os
import sys
import time
import platform
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Startup time tracking for accurate uptime
# ═══════════════════════════════════════════════════════════════════════════════
_STARTUP_TIME = time.monotonic()
_STARTUP_TIMESTAMP = datetime.now(timezone.utc)
_REQUEST_COUNT = 0
_ERROR_COUNT = 0

def increment_request_count():
    """Called from middleware to track request count."""
    global _REQUEST_COUNT
    _REQUEST_COUNT += 1

def increment_error_count():
    """Called from middleware to track error count."""
    global _ERROR_COUNT
    _ERROR_COUNT += 1

# Lazy settings loading
_settings = None

def get_settings_safe():
    """Get settings with fallback for missing config."""
    global _settings
    if _settings is None:
        try:
            _settings = get_settings()
        except Exception as e:
            logger.warning(f"Could not load settings: {e}")
            _settings = None
    return _settings

# Database check function - lazy loaded
def check_db_connection():
    """Check database connection with lazy import."""
    try:
        backend_path = str(Path(__file__).parent.parent.parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        from database import check_db_connection as _check_db
        return _check_db()
    except Exception:
        return False

def _measure_db_latency():
    """Measure database round-trip latency in ms."""
    try:
        backend_path = str(Path(__file__).parent.parent.parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        from database import get_supabase
        supabase = get_supabase()
        if not supabase:
            return -1
        start = time.monotonic()
        supabase.table('cse226_ocr_users').select('id').limit(1).execute()
        return round((time.monotonic() - start) * 1000, 1)
    except Exception:
        return -1

def _format_uptime(seconds):
    """Format seconds into human-readable uptime string."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


# Knowledge base path
KB_PATH = Path(__file__).parent.parent.parent.parent / 'knowledge_base.md'


# ═══════════════════════════════════════════════════════════════════════════════
# Real-time Health (lightweight, for frequent polling)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/health/realtime")
async def health_realtime():
    """
    Lightweight real-time health metrics for dashboard polling.
    
    Designed to be called every 2-3 seconds by the frontend dashboard.
    Includes uptime, latency, request counts — no heavy computations.
    """
    now = time.monotonic()
    uptime_seconds = now - _STARTUP_TIME
    
    # Measure API response latency (time for this request itself)
    request_start = time.monotonic()
    
    # Quick DB check (cached result to avoid hammering DB)
    db_connected = check_db_connection()
    db_latency = _measure_db_latency() if db_connected else -1
    
    api_latency = round((time.monotonic() - request_start) * 1000, 1)
    
    return {
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'uptime': {
            'seconds': round(uptime_seconds, 1),
            'formatted': _format_uptime(uptime_seconds),
            'started_at': _STARTUP_TIMESTAMP.isoformat(),
        },
        'latency': {
            'api_ms': api_latency,
            'db_ms': db_latency,
        },
        'metrics': {
            'total_requests': _REQUEST_COUNT,
            'total_errors': _ERROR_COUNT,
            'error_rate': round(_ERROR_COUNT / max(_REQUEST_COUNT, 1) * 100, 2),
        },
        'database': {
            'connected': db_connected,
            'provider': 'Supabase',
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Full Health (detailed, for initial load)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    """
    Premium health endpoint with comprehensive system info.
    
    Returns detailed status including OCR engines, DB, system info,
    analysis capabilities, grading scale, and waiver thresholds.
    """
    settings = get_settings_safe()
    uptime_seconds = time.monotonic() - _STARTUP_TIME
    
    # OCR API keys status
    google_key = getattr(settings, 'GOOGLE_VISION_API_KEY', '') if settings else os.getenv('GOOGLE_VISION_API_KEY', '')
    azure_key = getattr(settings, 'AZURE_DOC_INTELLIGENCE_KEY', '') if settings else os.getenv('AZURE_DOC_INTELLIGENCE_KEY', '')
    
    # Measure latencies
    db_connected = check_db_connection()
    db_latency = _measure_db_latency() if db_connected else -1
    
    # Uptime info
    uptime_info = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'timezone': 'UTC',
        'started_at': _STARTUP_TIMESTAMP.isoformat(),
        'uptime_seconds': round(uptime_seconds, 1),
        'uptime_formatted': _format_uptime(uptime_seconds),
    }
    
    # OCR limits info
    ocr_info = {
        'google_vision': {
            'configured': bool(google_key),
            'free_tier': '1,000 requests/month',
            'rate_limit': '1,800 requests/minute',
            'max_file_size': '20 MB',
            'supported_formats': ['PDF', 'PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'WEBP', 'TIFF']
        },
        'azure_doc_intelligence': {
            'configured': bool(azure_key),
            'accuracy': '99%+',
            'free_tier': '500 pages/month',
            'max_file_size': '50 MB',
            'supported_formats': ['PDF', 'PNG', 'JPG', 'JPEG', 'TIFF', 'BMP']
        }
    }
    
    # Server info
    server_info = {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'python_version': platform.python_version(),
        'architecture': platform.machine(),
        'processor': platform.processor() or 'Cloud Run',
        'hostname': platform.node()
    }
    
    # Environment
    env_info = {
        'environment': getattr(settings, 'ENVIRONMENT', 'production') if settings else 'production',
        'log_level': getattr(settings, 'LOG_LEVEL', 'INFO') if settings else 'INFO',
        'max_upload_mb': getattr(settings, 'MAX_UPLOAD_SIZE_MB', 16) if settings else 16,
        'port': os.getenv('PORT', '8080')
    }
    
    # Knowledge base status
    kb_info = {
        'path': str(KB_PATH),
        'exists': KB_PATH.exists(),
        'size_kb': round(KB_PATH.stat().st_size / 1024, 2) if KB_PATH.exists() else 0
    }
    
    # Analysis capabilities
    capabilities = {
        'level_1': {
            'name': 'Credit Tally',
            'features': ['Total credits', 'Earned credits', 'Failed credits', 'Retake detection']
        },
        'level_2': {
            'name': 'CGPA Analysis',
            'features': ['CGPA calculation', 'Academic standing', 'Grade distribution', 'Waiver eligibility']
        },
        'level_3': {
            'name': 'Degree Audit',
            'features': ['Program detection', 'Mandatory course check', 'Elective requirements', 'Graduation readiness']
        }
    }
    
    # Build response
    return {
        'status': 'healthy',
        'service': 'NSU Degree Audit API',
        'version': '2.5.0',
        'framework': 'FastAPI',
        'uptime': uptime_info,
        'latency': {
            'db_ms': db_latency,
        },
        'metrics': {
            'total_requests': _REQUEST_COUNT,
            'total_errors': _ERROR_COUNT,
            'error_rate': round(_ERROR_COUNT / max(_REQUEST_COUNT, 1) * 100, 2),
        },
        'ocr_engines': ocr_info,
        'server': server_info,
        'environment': env_info,
        'knowledge_base': kb_info,
        'analysis_capabilities': capabilities,
        'endpoints': {
            'root': '/',
            'health': '/health',
            'health_realtime': '/health/realtime',
            'upload': '/api/upload (POST)',
            'auth': '/auth/*',
            'history': '/api/history',
            'docs': '/docs',
        },
        'database': {
            'enabled': True,
            'connected': db_connected,
            'latency_ms': db_latency,
            'provider': 'Supabase',
            'features': ['user_auth', 'scan_history', 'api_keys'] if db_connected else []
        },
        'grading_scale': {
            'A': 4.00, 'A-': 3.70,
            'B+': 3.30, 'B': 3.00, 'B-': 2.70,
            'C+': 2.30, 'C': 2.00, 'C-': 1.70,
            'D+': 1.30, 'D': 1.00,
            'F': 0.00
        },
        'waivers': {
            'chancellors_award': {'cgpa': 3.97, 'waiver': '100%'},
            'vc_scholarship': {'cgpa': 3.75, 'waiver': '50%'},
            'deans_scholarship': {'cgpa': 3.50, 'waiver': '25%'}
        }
    }


@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe - is the service running?"""
    response = JSONResponse(content={"status": "live"})
    response.headers["Cache-Control"] = "no-cache, max-age=0"
    return response


@router.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe - is the service ready to accept traffic?"""
    db_ready = check_db_connection()
    
    if not db_ready:
        return {
            "status": "ready",
            "database": "unavailable",
            "note": "Running without database persistence"
        }
    
    return {"status": "ready"}
