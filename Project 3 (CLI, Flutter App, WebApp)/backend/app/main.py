"""
NSU Degree Audit API - FastAPI Application
==========================================
High-performance async backend for OCR-based degree auditing.
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler

logger = logging.getLogger(__name__)

# Lazy settings loading with fallback
def get_settings_safe():
    """Get settings with fallback for missing config."""
    try:
        from app.config import get_settings
        return get_settings()
    except Exception as e:
        logger.warning(f"Could not load settings: {e}")
        # Return a minimal settings-like object
        class MinimalSettings:
            CORS_ORIGINS = [
                "https://ocr.nsunexus.app",
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
            ]
            DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
        return MinimalSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    logger.info("Starting NSU Degree Audit API...")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="NSU Degree Audit API",
    description="OCR-based degree audit system for North South University transcripts",
    version="2.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS - get settings lazily
settings = get_settings_safe()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "name": "NSU Degree Audit API",
        "version": "2.4.0",
        "framework": "FastAPI",
        "status": "running",
        "docs": "/docs"
    }
