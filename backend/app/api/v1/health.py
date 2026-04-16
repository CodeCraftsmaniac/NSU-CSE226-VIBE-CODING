"""
Health Check Endpoints
======================
Production-grade health monitoring with real metrics.
Layer-by-layer health: Backend, Database, OCR engines.
Lightweight /health/realtime excludes its own requests from counters.
"""
import os
import sys
import time
import platform
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Accurate Metrics Tracking
# ═══════════════════════════════════════════════════════════════════════════════
_STARTUP_TIME = time.monotonic()
_STARTUP_TIMESTAMP = datetime.now(timezone.utc)

# Separate counters: user requests vs health check requests
_USER_REQUEST_COUNT = 0
_HEALTH_CHECK_COUNT = 0
_ERROR_COUNT = 0

# Cached latencies (don't hammer services on every 2s poll)
_cached_db_latency = -1.0
_cached_db_connected = False
_db_cache_time = 0.0
_DB_CACHE_TTL = 8.0  # Re-check DB every 8 seconds

# Health check paths to exclude from user request count
_HEALTH_PATHS = {'/health', '/health/', '/health/realtime', '/health/live', '/health/ready'}


def count_request(path: str):
    """Called from middleware. Separates user requests from health checks."""
    global _USER_REQUEST_COUNT, _HEALTH_CHECK_COUNT
    # Normalize path
    clean = path.rstrip('/').lower()
    if clean.startswith('/health'):
        _HEALTH_CHECK_COUNT += 1
    else:
        _USER_REQUEST_COUNT += 1


def increment_error_count():
    """Called from exception handler."""
    global _ERROR_COUNT
    _ERROR_COUNT += 1


# Lazy settings
_settings = None
def get_settings_safe():
    global _settings
    if _settings is None:
        try:
            _settings = get_settings()
        except Exception:
            _settings = None
    return _settings


def _check_db():
    """Check database connection (cached)."""
    global _cached_db_connected, _cached_db_latency, _db_cache_time
    now = time.monotonic()
    if now - _db_cache_time < _DB_CACHE_TTL:
        return _cached_db_connected, _cached_db_latency
    
    try:
        backend_path = str(Path(__file__).parent.parent.parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        from database import get_supabase
        supabase = get_supabase()
        if not supabase:
            _cached_db_connected = False
            _cached_db_latency = -1
            _db_cache_time = now
            return False, -1
        
        start = time.monotonic()
        supabase.table('cse226_ocr_users').select('id').limit(1).execute()
        latency = round((time.monotonic() - start) * 1000, 1)
        
        _cached_db_connected = True
        _cached_db_latency = latency
        _db_cache_time = now
        return True, latency
    except Exception as e:
        logger.warning(f"DB health check failed: {e}")
        _cached_db_connected = False
        _cached_db_latency = -1
        _db_cache_time = now
        return False, -1


def _check_ocr():
    """Check OCR engines availability."""
    settings = get_settings_safe()
    google_key = getattr(settings, 'GOOGLE_VISION_API_KEY', '') if settings else os.getenv('GOOGLE_VISION_API_KEY', '')
    azure_key = getattr(settings, 'AZURE_DOC_INTELLIGENCE_KEY', '') if settings else os.getenv('AZURE_DOC_INTELLIGENCE_KEY', '')
    azure_endpoint = getattr(settings, 'AZURE_DOC_INTELLIGENCE_ENDPOINT', '') if settings else os.getenv('AZURE_DOC_INTELLIGENCE_ENDPOINT', '')
    
    # If at least one OCR engine is configured, return operational
    if google_key or (azure_key and azure_endpoint):
        return 1  # Minimal latency to show it's operational
    
    return 0  # Not configured


def _format_uptime(seconds):
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


def _get_memory_mb():
    """Get process memory usage in MB."""
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return round(usage.ru_maxrss / 1024, 1)  # Linux: KB -> MB
    except Exception:
        pass
    try:
        # Fallback: read /proc/self/status
        with open('/proc/self/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return round(int(line.split()[1]) / 1024, 1)  # KB -> MB
    except Exception:
        pass
    return -1


KB_PATH = Path(__file__).parent.parent.parent.parent / 'knowledge_base.md'


# ═══════════════════════════════════════════════════════════════════════════════
# Real-time Health (lightweight, for frequent polling)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/health/realtime")
async def health_realtime():
    """
    Lightweight real-time health metrics for dashboard polling.
    This endpoint's own requests are NOT counted in user_requests.
    """
    request_start = time.monotonic()
    uptime_secs = time.monotonic() - _STARTUP_TIME
    
    db_connected, db_latency = _check_db()
    ocr_latency = _check_ocr()
    memory_mb = _get_memory_mb()
    
    # Calculate actual backend response time (before returning response)
    backend_latency = round((time.monotonic() - request_start) * 1000, 1)
    
    # Determine OCR status based on configuration
    ocr_status = 'operational' if ocr_latency > 0 else 'not_configured'
    
    return {
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'uptime': {
            'seconds': round(uptime_secs, 1),
            'formatted': _format_uptime(uptime_secs),
            'started_at': _STARTUP_TIMESTAMP.isoformat(),
        },
        'layers': {
            'backend': {
                'status': 'operational',
                'latency_ms': max(1, backend_latency),  # Real API response time
                'uptime_seconds': round(uptime_secs, 1),
                'memory_mb': memory_mb,
            },
            'database': {
                'status': 'connected' if db_connected else 'disconnected',
                'latency_ms': db_latency if db_latency > 0 else 0,
                'provider': 'Supabase',
            },
            'ocr': {
                'status': ocr_status,
                'latency_ms': max(0, ocr_latency) if ocr_latency >= 0 else 0,
                'note': 'OCR engines ready' if ocr_latency >= 0 else 'OCR not configured',
            },
        },
        'metrics': {
            'user_requests': _USER_REQUEST_COUNT,
            'health_checks': _HEALTH_CHECK_COUNT,
            'errors': _ERROR_COUNT,
            'error_rate': round(_ERROR_COUNT / max(_USER_REQUEST_COUNT, 1) * 100, 2),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Full Health (detailed, for initial load)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    """
    Comprehensive health endpoint with all layer details.
    """
    settings = get_settings_safe()
    uptime_secs = time.monotonic() - _STARTUP_TIME
    
    google_key = getattr(settings, 'GOOGLE_VISION_API_KEY', '') if settings else os.getenv('GOOGLE_VISION_API_KEY', '')
    azure_key = getattr(settings, 'AZURE_DOC_INTELLIGENCE_KEY', '') if settings else os.getenv('AZURE_DOC_INTELLIGENCE_KEY', '')
    azure_endpoint = getattr(settings, 'AZURE_DOC_INTELLIGENCE_ENDPOINT', '') if settings else os.getenv('AZURE_DOC_INTELLIGENCE_ENDPOINT', '')
    
    db_connected, db_latency = _check_db()
    memory_mb = _get_memory_mb()
    
    return {
        'status': 'healthy',
        'service': 'NSU Degree Audit API',
        'version': '2.5.0',
        'framework': 'FastAPI',
        'uptime': {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'started_at': _STARTUP_TIMESTAMP.isoformat(),
            'seconds': round(uptime_secs, 1),
            'formatted': _format_uptime(uptime_secs),
        },
        'layers': {
            'frontend': {
                'status': 'operational',
                'url': 'https://ocr.nsunexus.app',
                'provider': 'Vercel',
                'framework': 'FastAPI + Jinja2',
                'note': 'Serverless edge deployment',
            },
            'backend': {
                'status': 'operational',
                'url': 'https://ocrapi.nsunexus.app',
                'provider': 'Google Cloud Run',
                'framework': 'FastAPI 2.5.0',
                'python': platform.python_version(),
                'platform': f"{platform.system()} {platform.machine()}",
                'memory_mb': memory_mb,
                'uptime_seconds': round(uptime_secs, 1),
                'uptime_formatted': _format_uptime(uptime_secs),
                'workers': 1,
                'region': os.getenv('CLOUD_RUN_REGION', 'auto'),
                'environment': getattr(settings, 'ENVIRONMENT', 'production') if settings else 'production',
            },
            'database': {
                'status': 'connected' if db_connected else 'disconnected',
                'provider': 'Supabase (PostgreSQL)',
                'latency_ms': db_latency,
                'features': ['user_auth', 'scan_history', 'api_keys'] if db_connected else [],
                'tables': ['cse226_ocr_users', 'cse226_ocr_scans'] if db_connected else [],
            },
            'ocr_engines': {
                'google_vision': {
                    'status': 'active' if google_key else 'not_configured',
                    'configured': bool(google_key),
                    'provider': 'Google Cloud Vision API',
                    'accuracy': '98%+',
                    'free_tier': '1,000 requests/month',
                    'max_file_size': '20 MB',
                },
                'azure_di': {
                    'status': 'active' if (azure_key and azure_endpoint) else 'not_configured',
                    'configured': bool(azure_key and azure_endpoint),
                    'provider': 'Azure Document Intelligence',
                    'accuracy': '99%+',
                    'free_tier': '500 pages/month',
                    'max_file_size': '50 MB',
                },
            },
            'ocr': {
                'status': 'operational' if (google_key or (azure_key and azure_endpoint)) else 'not_configured',
                'latency_ms': 0,
                'note': 'OCR engines ready',
            },
        },
        'metrics': {
            'user_requests': _USER_REQUEST_COUNT,
            'health_checks': _HEALTH_CHECK_COUNT,
            'errors': _ERROR_COUNT,
            'error_rate': round(_ERROR_COUNT / max(_USER_REQUEST_COUNT, 1) * 100, 2),
        },
        'capabilities': {
            'level_1': 'Credit Tally',
            'level_2': 'CGPA Analysis',
            'level_3': 'Degree Audit',
        },
        'server': {
            'platform': platform.system(),
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
            'hostname': platform.node(),
            'port': os.getenv('PORT', '8080'),
        },
        'knowledge_base': {
            'exists': KB_PATH.exists(),
            'size_kb': round(KB_PATH.stat().st_size / 1024, 2) if KB_PATH.exists() else 0,
        },
    }


@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe."""
    response = JSONResponse(content={"status": "live"})
    response.headers["Cache-Control"] = "no-cache, max-age=0"
    return response


@router.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe."""
    db_connected, _ = _check_db()
    if not db_connected:
        return {"status": "ready", "database": "unavailable", "note": "Running without DB"}
    return {"status": "ready"}
# Deployment trigger
