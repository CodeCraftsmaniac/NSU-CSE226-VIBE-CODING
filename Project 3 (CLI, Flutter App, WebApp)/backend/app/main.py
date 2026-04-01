"""
NSU Degree Audit API - FastAPI Application
==========================================
High-performance async backend for OCR-based degree auditing.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create app with minimal config
app = FastAPI(
    title="NSU Degree Audit API",
    version="2.4.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": "NSU Degree Audit API",
        "version": "2.4.0",
        "framework": "FastAPI",
        "status": "running",
    }


@app.get("/health")
@app.get("/health/live")
@app.get("/health/ready")
def health():
    return {"status": "healthy"}


# Load additional routes only if dependencies are available
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from fastapi.responses import JSONResponse
    
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        return JSONResponse(status_code=429, content={"error": "Too many requests"})
except ImportError:
    pass

import logging
import sys

# Configure logging to show at startup
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Track router loading status
_router_loaded = False
_router_error = None

try:
    from app.api.router import api_router
    app.include_router(api_router)
    _router_loaded = True
    logger.info("✅ API router loaded successfully")
    print("✅ API router loaded successfully", file=sys.stderr)
except Exception as e:
    _router_error = str(e)
    logger.error(f"❌ Failed to load API router: {e}")
    print(f"❌ Failed to load API router: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()


@app.get("/debug/status")
def debug_status():
    """Debug endpoint to check router loading status."""
    return {
        "router_loaded": _router_loaded,
        "router_error": _router_error,
        "python_version": sys.version,
        "python_path": sys.path[:5]  # First 5 entries
    }
