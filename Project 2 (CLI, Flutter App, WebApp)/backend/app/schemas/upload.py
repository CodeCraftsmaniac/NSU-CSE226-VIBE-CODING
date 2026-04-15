"""
Upload Schemas
==============
Request/response models for file upload and OCR processing.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    """Supported file types for upload."""
    PDF = "pdf"
    CSV = "csv"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"


class CourseData(BaseModel):
    """Parsed course information from transcript."""
    code: str = Field(..., description="Course code (e.g., CSE115)")
    name: Optional[str] = Field(None, description="Course name")
    credits: float = Field(..., ge=0, description="Credit hours")
    grade: Optional[str] = Field(None, description="Letter grade")
    grade_points: Optional[float] = Field(None, ge=0, le=4.0, description="Grade points")
    semester: Optional[str] = Field(None, description="Semester taken")
    status: Optional[str] = Field(None, description="Course status (completed, in-progress, etc.)")
    
    class Config:
        from_attributes = True


class StudentInfo(BaseModel):
    """Student information extracted from transcript."""
    student_id: Optional[str] = Field(None, description="NSU Student ID")
    name: Optional[str] = Field(None, description="Student name")
    program: Optional[str] = Field(None, description="Degree program")
    major: Optional[str] = Field(None, description="Major")
    minor: Optional[str] = Field(None, description="Minor if any")
    admission_date: Optional[str] = Field(None, description="Admission date/semester")
    
    class Config:
        from_attributes = True


class AcademicSummary(BaseModel):
    """Academic summary from transcript."""
    total_credits: float = Field(0, ge=0, description="Total credits earned")
    total_credits_attempted: float = Field(0, ge=0, description="Total credits attempted")
    cgpa: Optional[float] = Field(None, ge=0, le=4.0, description="Cumulative GPA")
    credits_required: Optional[float] = Field(None, description="Credits required for graduation")
    credits_remaining: Optional[float] = Field(None, description="Credits remaining")
    
    class Config:
        from_attributes = True


class OCRResult(BaseModel):
    """OCR processing results."""
    raw_text: Optional[str] = Field(None, description="Raw extracted text")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="OCR confidence score")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    method: Optional[str] = Field(None, description="OCR method used")
    
    class Config:
        from_attributes = True


class RequirementStatus(BaseModel):
    """Status of a degree requirement."""
    category: str = Field(..., description="Requirement category")
    required: float = Field(..., description="Credits required")
    completed: float = Field(..., description="Credits completed")
    remaining: float = Field(..., description="Credits remaining")
    courses: List[CourseData] = Field(default_factory=list, description="Courses in this category")
    
    class Config:
        from_attributes = True


class AuditResult(BaseModel):
    """Degree audit result."""
    student: Optional[StudentInfo] = None
    summary: Optional[AcademicSummary] = None
    courses: List[CourseData] = Field(default_factory=list)
    requirements: List[RequirementStatus] = Field(default_factory=list)
    is_complete: bool = Field(False, description="Whether all requirements are met")
    warnings: List[str] = Field(default_factory=list, description="Any warnings or issues")
    
    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """Response from file upload endpoint."""
    success: bool = True
    message: Optional[str] = None
    filename: Optional[str] = None
    file_type: Optional[FileType] = None
    file_size: Optional[int] = None
    ocr_result: Optional[OCRResult] = None
    audit_result: Optional[AuditResult] = None
    audit_id: Optional[str] = Field(None, description="ID of saved audit record")
    
    class Config:
        from_attributes = True
