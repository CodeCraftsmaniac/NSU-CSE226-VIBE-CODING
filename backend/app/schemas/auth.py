"""
Authentication Schemas
======================
Request/response models for authentication endpoints.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """Login request body."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")
    
    class Config:
        from_attributes = True


class SignupRequest(BaseModel):
    """Signup request body."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 chars)")
    confirm_password: str = Field(..., description="Password confirmation")
    name: Optional[str] = Field(None, max_length=100, description="Display name")
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Authentication token response."""
    success: bool = True
    message: Optional[str] = None
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    
    class Config:
        from_attributes = True


class UserInfo(BaseModel):
    """User information response."""
    id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    name: Optional[str] = Field(None, description="Display name")
    email_verified: bool = Field(False, description="Email verification status")
    created_at: Optional[datetime] = Field(None, description="Account creation time")
    last_login: Optional[datetime] = Field(None, description="Last login time")
    
    class Config:
        from_attributes = True


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr = Field(..., description="Email address for reset")
    
    class Config:
        from_attributes = True


class PasswordChangeRequest(BaseModel):
    """Password change request (authenticated)."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")
    
    class Config:
        from_attributes = True
