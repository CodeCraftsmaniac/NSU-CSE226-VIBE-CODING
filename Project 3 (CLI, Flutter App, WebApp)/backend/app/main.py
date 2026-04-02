"""
NSU Degree Audit API - FastAPI Application
==========================================
High-performance async backend for OCR-based degree auditing.
"""
import os
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# CORS allowed origins - load from config or use defaults
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [
    "https://ocr.nsunexus.app",
    "https://ocrapi.nsunexus.app",
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5000",
]

# Create app
app = FastAPI(
    title="NSU Degree Audit API",
    version="2.5.0",
    description="NSU Degree Audit Engine - OCR-based transcript analysis API",
)

# Middleware - GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS - Use specific origins (not wildcard) for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


# Global exception handler - prevent stack trace leaks
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return generic error."""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


@app.get("/")
def root():
    return {
        "name": "NSU Degree Audit API",
        "version": "2.5.0",
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
    
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        return JSONResponse(status_code=429, content={"error": "Too many requests"})
except ImportError:
    pass

# Load API router
try:
    from app.api.router import api_router
    app.include_router(api_router)
    logger.info("✅ API router loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load API router: {e}")
