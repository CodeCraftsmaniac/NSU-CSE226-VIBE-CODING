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

try:
    from app.api.router import api_router
    app.include_router(api_router)
except Exception:
    pass
