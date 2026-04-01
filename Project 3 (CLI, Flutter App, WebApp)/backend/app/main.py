"""
NSU Degree Audit API - FastAPI Application
==========================================
High-performance async backend for OCR-based degree auditing.
"""
import os
import sys
import logging
from contextlib import asynccontextmanager

print("DEBUG: Starting app import...", file=sys.stderr)
print(f"DEBUG: PYTHONPATH={os.environ.get('PYTHONPATH', 'not set')}", file=sys.stderr)
print(f"DEBUG: Current dir={os.getcwd()}", file=sys.stderr)
print(f"DEBUG: sys.path={sys.path[:5]}", file=sys.stderr)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

print("DEBUG: FastAPI imported", file=sys.stderr)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default CORS origins
DEFAULT_CORS_ORIGINS = [
    "https://ocr.nsunexus.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "*"  # Allow all for Cloud Run health checks
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    logger.info("Starting NSU Degree Audit API...")
    logger.info(f"PORT: {os.environ.get('PORT', '8080')}")
    print(f"DEBUG: App starting on PORT={os.environ.get('PORT', '8080')}", file=sys.stderr)
    yield
    logger.info("Shutting down...")


# Create FastAPI app first (before any imports that might fail)
app = FastAPI(
    title="NSU Degree Audit API",
    description="OCR-based degree audit system for North South University transcripts",
    version="2.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

print("DEBUG: FastAPI app created", file=sys.stderr)

# Add CORS middleware (must be done before routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEFAULT_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint (always available)
@app.get("/")
async def root():
    return {
        "name": "NSU Degree Audit API",
        "version": "2.4.0",
        "framework": "FastAPI",
        "status": "running",
        "docs": "/docs"
    }


# Simple health endpoint (always available)
@app.get("/health")
@app.get("/health/live")
async def health():
    return {"status": "healthy", "version": "2.4.0"}


@app.get("/health/ready")
async def ready():
    return {"status": "ready"}

print("DEBUG: Basic routes added", file=sys.stderr)

# Try to load additional routes - if they fail, app still starts
try:
    from slowapi.errors import RateLimitExceeded
    from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    logger.info("Rate limiting configured")
    print("DEBUG: Rate limiting configured", file=sys.stderr)
except Exception as e:
    logger.warning(f"Rate limiting not available: {e}")
    print(f"DEBUG: Rate limiting failed: {e}", file=sys.stderr)

try:
    from app.api.router import api_router
    app.include_router(api_router)
    logger.info("API routes loaded")
    print("DEBUG: API routes loaded", file=sys.stderr)
except Exception as e:
    logger.error(f"Failed to load API routes: {e}")
    print(f"DEBUG: API routes failed: {e}", file=sys.stderr)
    # Add a fallback error route
    @app.get("/api/{path:path}")
    async def api_fallback(path: str):
        return {"error": "API routes not available", "path": path}

print("DEBUG: App module loading complete", file=sys.stderr)
