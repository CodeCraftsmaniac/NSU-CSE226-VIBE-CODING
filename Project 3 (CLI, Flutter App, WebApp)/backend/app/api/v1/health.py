"""
Health Check Endpoints
======================
Liveness and readiness probes for container orchestration.
Premium health endpoint with detailed system info (FastAPI endpoint).
"""
import os
import sys
import platform
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

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
        # Add backend directory for local imports
        backend_path = str(Path(__file__).parent.parent.parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from database import check_db_connection as _check_db
        return _check_db()
    except Exception:
        return False


# Knowledge base path
KB_PATH = Path(__file__).parent.parent.parent.parent / 'knowledge_base.md'


@router.get("/health")
async def health_check():
    """
    Premium health endpoint with detailed system info.
    
    Returns comprehensive health status including:
    - OCR engine availability
    - Database connection status
    - System information
    - Analysis capabilities
    """
    settings = get_settings_safe()
    
    # OCR API keys status
    google_key = getattr(settings, 'GOOGLE_VISION_API_KEY', '') if settings else os.getenv('GOOGLE_VISION_API_KEY', '')
    ocrspace_key = getattr(settings, 'OCR_SPACE_API_KEY', '') if settings else os.getenv('OCR_SPACE_API_KEY', '')
    
    # System info
    uptime_info = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'timezone': 'UTC'
    }
    
    # OCR limits info (no key preview for security)
    ocr_info = {
        'google_vision': {
            'configured': bool(google_key),
            'free_tier': '1,000 requests/month',
            'rate_limit': '1,800 requests/minute',
            'max_file_size': '20 MB',
            'supported_formats': ['PDF', 'PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'WEBP', 'TIFF']
        },
        'ocr_space': {
            'configured': bool(ocrspace_key),
            'free_tier': '25,000 requests/month',
            'rate_limit': '500 requests/day (free)',
            'max_file_size': '1 MB (free) / 5 MB (pro)',
            'supported_formats': ['PDF', 'PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'TIFF']
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
    
    # Database status
    db_connected = check_db_connection()
    
    # Build response
    return {
        'status': 'healthy',
        'service': 'NSU Degree Audit API',
        'version': '2.4.0',
        'framework': 'FastAPI',
        'uptime': uptime_info,
        'ocr_engines': ocr_info,
        'server': server_info,
        'environment': env_info,
        'knowledge_base': kb_info,
        'analysis_capabilities': capabilities,
        'endpoints': {
            'root': '/',
            'health': '/health',
            'upload': '/api/upload (POST)',
            'auth': '/auth/*',
            'history': '/api/history',
            'docs': '/docs'
        },
        'database': {
            'enabled': True,
            'connected': db_connected,
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
    # Check database connection
    db_ready = check_db_connection()
    
    # In production, DB is optional (graceful degradation)
    if not db_ready:
        return {
            "status": "ready",
            "database": "unavailable",
            "note": "Running without database persistence"
        }
    
    return {"status": "ready"}
