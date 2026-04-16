"""
Main API Router
===============
Aggregates all API routes from versioned modules.
"""
from fastapi import APIRouter
from app.api.v1 import health, upload, auth, history, analysis

api_router = APIRouter()

# Health endpoints (no prefix)
api_router.include_router(health.router, tags=["Health"])

# API v1 endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Upload at both /upload and /api/upload for backward compatibility
api_router.include_router(upload.router, tags=["Upload & OCR"])  # /upload
api_router.include_router(upload.router, prefix="/api", tags=["Upload & OCR"])  # /api/upload (legacy)

# History at both /history and /api/history for backward compatibility
api_router.include_router(history.router, tags=["History"])  # /history
api_router.include_router(history.router, prefix="/api", tags=["History"])  # /api/history (legacy)

# Analysis endpoints
api_router.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])  # /api/v1/analysis
