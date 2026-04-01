"""
NSU Degree Audit API - FastAPI Application
==========================================
High-performance async backend for OCR-based degree auditing.
"""
import os
import sys
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Create app
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


# Load rate limiting
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

# Track router loading status (for debugging)
_router_loaded = False
_router_error = None

# Load API router
try:
    from app.api.router import api_router
    app.include_router(api_router)
    _router_loaded = True
    logger.info("✅ API router loaded successfully")
except Exception as e:
    _router_error = str(e)
    logger.error(f"❌ Failed to load API router: {e}")
    import traceback
    traceback.print_exc()


@app.get("/debug/status", include_in_schema=False)
def debug_status():
    """Debug endpoint to check router loading status (hidden from docs)."""
    return {
        "router_loaded": _router_loaded,
        "router_error": _router_error,
        "python_version": sys.version,
    }
