"""Pydantic schemas for request/response validation."""
from app.schemas.common import BaseResponse, ErrorResponse, PaginatedResponse
from app.schemas.upload import UploadResponse, OCRResult, CourseData
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserInfo

__all__ = [
    "BaseResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "UploadResponse",
    "OCRResult",
    "CourseData",
    "LoginRequest",
    "SignupRequest",
    "TokenResponse",
    "UserInfo",
]
