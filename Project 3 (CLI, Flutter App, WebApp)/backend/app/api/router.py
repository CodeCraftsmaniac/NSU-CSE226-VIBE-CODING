"""
Main API Router
===============
Aggregates all API routes from versioned modules.
"""
from fastapi import APIRouter
from app.api.v1 import health, upload, auth, history

api_router = APIRouter()

# Health endpoints (no prefix)
api_router.include_router(health.router, tags=["Health"])

# API v1 endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(upload.router, prefix="/api", tags=["Upload & OCR"])
api_router.include_router(history.router, prefix="/api", tags=["History"])
