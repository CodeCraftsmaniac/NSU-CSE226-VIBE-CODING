"""
NSU Degree Audit - Centralized Configuration
=============================================
Pydantic Settings for secure, validated configuration.
All secrets come from environment variables - NO hardcoded defaults.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """
    Application settings with validation.
    
    Required secrets have no defaults - app will fail to start if not set.
    This is intentional to prevent accidental deployment without proper config.
    """
    
    # === REQUIRED - No defaults for secrets (app fails if not set) ===
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # JWT Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 30
    
    # === OCR APIs (at least one required for OCR functionality) ===
    GOOGLE_VISION_API_KEY: str = ""  # Optional, can use OCR.space instead
    OCR_SPACE_API_KEY: str = ""  # Optional, can use Google instead
    
    # === CORS - Specific origins only (no wildcard) ===
    CORS_ORIGINS: List[str] = [
        "https://ocr.nsunexus.app",
        "http://localhost:3000",
        "http://localhost:5173"
    ]
    
    # === Rate Limiting ===
    RATE_LIMIT_PER_MINUTE: int = 30
    
    # === Upload Configuration ===
    MAX_UPLOAD_SIZE_MB: int = 16
    UPLOAD_FOLDER: str = "uploads"
    
    # === Logging ===
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    
    # === Optional Google OAuth (for frontend) ===
    GOOGLE_CLIENT_ID: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars
    
    def has_ocr_provider(self) -> bool:
        """Check if at least one OCR provider is configured."""
        return bool(self.GOOGLE_VISION_API_KEY or self.OCR_SPACE_API_KEY)
    
    def get_supabase_key(self) -> str:
        """Get the appropriate Supabase key for backend operations."""
        return self.SUPABASE_SERVICE_ROLE_KEY or self.SUPABASE_ANON_KEY


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Raises ValidationError if required settings are missing.
    This is intentional - fail fast on misconfiguration.
    """
    return Settings()


def validate_settings_on_startup() -> dict:
    """
    Validate settings and return status dict.
    Call this at app startup to ensure all required config is present.
    
    Returns:
        dict with 'valid' bool and 'errors' list
    """
    errors = []
    
    try:
        settings = get_settings()
        
        # Check OCR providers
        if not settings.has_ocr_provider():
            errors.append("No OCR provider configured (need GOOGLE_VISION_API_KEY or OCR_SPACE_API_KEY)")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'settings': {
                'supabase_url': settings.SUPABASE_URL[:30] + '...' if settings.SUPABASE_URL else None,
                'has_google_vision': bool(settings.GOOGLE_VISION_API_KEY),
                'has_ocr_space': bool(settings.OCR_SPACE_API_KEY),
                'cors_origins': settings.CORS_ORIGINS,
                'rate_limit': settings.RATE_LIMIT_PER_MINUTE,
                'debug': settings.DEBUG
            }
        }
    except Exception as e:
        return {
            'valid': False,
            'errors': [f"Configuration error: {str(e)}"],
            'settings': None
        }
