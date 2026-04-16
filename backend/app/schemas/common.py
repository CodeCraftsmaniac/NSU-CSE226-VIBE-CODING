"""
Common Schemas
==============
Shared response models used across the API.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Generic, TypeVar, List
from datetime import datetime

T = TypeVar('T')


class BaseResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    message: Optional[str] = None
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    
    class Config:
        from_attributes = True


class PaginationInfo(BaseModel):
    """Pagination metadata."""
    page: int = Field(ge=1, description="Current page number")
    limit: int = Field(ge=1, le=100, description="Items per page")
    total: int = Field(ge=0, description="Total number of items")
    pages: int = Field(ge=0, description="Total number of pages")
    
    @classmethod
    def calculate(cls, page: int, limit: int, total: int) -> "PaginationInfo":
        """Calculate pagination info from parameters."""
        pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(page=page, limit=limit, total=total, pages=pages)


class PaginatedResponse(BaseModel):
    """Paginated list response."""
    success: bool = True
    data: List[Any] = []
    pagination: PaginationInfo
    
    class Config:
        from_attributes = True


class TimestampMixin(BaseModel):
    """Mixin for models with timestamps."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
