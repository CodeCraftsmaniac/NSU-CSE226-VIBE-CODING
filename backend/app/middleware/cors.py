"""
CORS Configuration
==================
Cross-Origin Resource Sharing middleware configuration.
"""
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings

settings = get_settings()


def get_cors_config() -> dict:
    """Get CORS middleware configuration."""
    return {
        "allow_origins": settings.CORS_ORIGINS,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }


def setup_cors(app):
    """Add CORS middleware to FastAPI app."""
    app.add_middleware(CORSMiddleware, **get_cors_config())
