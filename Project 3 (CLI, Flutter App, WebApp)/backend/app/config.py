"""
NSU Degree Audit - Centralized Configuration
=============================================
Pydantic Settings for secure, validated configuration.
All secrets come from environment variables - NO hardcoded defaults.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache
from typing import List, Any


class Settings(BaseSettings):
    """
    Application settings with validation.
    
    Supports multiple env var naming conventions for compatibility:
    - SUPABASE_KEY or SUPABASE_ANON_KEY
    - JWT_SECRET_KEY or SUPABASE_JWT_SECRET
    - GOOGLE_CLOUD_VISION_KEY or GOOGLE_VISION_API_KEY
    """
    
    # === REQUIRED - Supabase Configuration ===
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    
    # JWT Configuration
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 30
    
    # === OCR APIs (at least one required for OCR functionality) ===
    GOOGLE_VISION_API_KEY: str = ""  # Primary OCR engine
    # Azure Document Intelligence (premium, 99%+ accuracy)
    AZURE_DOC_INTELLIGENCE_KEY: str = ""
    AZURE_DOC_INTELLIGENCE_ENDPOINT: str = ""
    
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
    
    @model_validator(mode='before')
    @classmethod
    def resolve_aliases(cls, data: Any) -> Any:
        """Resolve alternative env var names for compatibility."""
        if isinstance(data, dict):
            # Support SUPABASE_KEY as alias for SUPABASE_ANON_KEY
            if not data.get('SUPABASE_ANON_KEY') and data.get('SUPABASE_KEY'):
                data['SUPABASE_ANON_KEY'] = data.get('SUPABASE_KEY')
            
            # Support SUPABASE_JWT_SECRET as alias for JWT_SECRET_KEY
            if not data.get('JWT_SECRET_KEY') and data.get('SUPABASE_JWT_SECRET'):
                data['JWT_SECRET_KEY'] = data.get('SUPABASE_JWT_SECRET')
            
            # Support GOOGLE_CLOUD_VISION_KEY as alias for GOOGLE_VISION_API_KEY
            if not data.get('GOOGLE_VISION_API_KEY') and data.get('GOOGLE_CLOUD_VISION_KEY'):
                data['GOOGLE_VISION_API_KEY'] = data.get('GOOGLE_CLOUD_VISION_KEY')
        
        # Also check os.environ directly for Cloud Run
        if not data.get('SUPABASE_ANON_KEY'):
            data['SUPABASE_ANON_KEY'] = os.environ.get('SUPABASE_KEY', '')
        if not data.get('JWT_SECRET_KEY'):
            data['JWT_SECRET_KEY'] = os.environ.get('SUPABASE_JWT_SECRET', '')
        if not data.get('GOOGLE_VISION_API_KEY'):
            data['GOOGLE_VISION_API_KEY'] = os.environ.get('GOOGLE_CLOUD_VISION_KEY', '')
        
        return data
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars
    
    def has_ocr_provider(self) -> bool:
        """Check if at least one OCR provider is configured."""
        return bool(self.GOOGLE_VISION_API_KEY or self.AZURE_DOC_INTELLIGENCE_KEY)
    
    def get_supabase_key(self) -> str:
        """Get the appropriate Supabase key for backend operations."""
        return self.SUPABASE_SERVICE_ROLE_KEY or self.SUPABASE_ANON_KEY


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns default settings if validation fails to allow graceful startup.
    """
    try:
        return Settings()
    except Exception:
        # Return settings with defaults for graceful degradation
        jwt_secret = os.environ.get('SUPABASE_JWT_SECRET', os.environ.get('JWT_SECRET_KEY', ''))
        if not jwt_secret:
            raise ValueError("JWT_SECRET_KEY must be set in production")
        return Settings(
            SUPABASE_URL=os.environ.get('SUPABASE_URL', ''),
            SUPABASE_ANON_KEY=os.environ.get('SUPABASE_KEY', os.environ.get('SUPABASE_ANON_KEY', '')),
            SUPABASE_SERVICE_ROLE_KEY=os.environ.get('SUPABASE_SERVICE_ROLE_KEY', ''),
            JWT_SECRET_KEY=jwt_secret,
        )


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
            errors.append("No OCR provider configured (need GOOGLE_VISION_API_KEY or AZURE_DOC_INTELLIGENCE_KEY)")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'settings': {
                'supabase_url': settings.SUPABASE_URL[:30] + '...' if settings.SUPABASE_URL else None,
                'has_google_vision': bool(settings.GOOGLE_VISION_API_KEY),
                'has_azure_doc': bool(settings.AZURE_DOC_INTELLIGENCE_KEY),
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
