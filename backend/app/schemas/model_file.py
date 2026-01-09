"""Pydantic schemas for ModelFile API (3D model files)."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelFileType(str, Enum):
    """Types of 3D model files."""

    SOURCE_STL = "source_stl"
    SOURCE_3MF = "source_3mf"
    SLICER_PROJECT = "slicer_project"
    GCODE = "gcode"
    PLATE_LAYOUT = "plate_layout"


class ModelFileBase(BaseModel):
    """Base schema for model files."""

    file_type: ModelFileType = Field(..., description="Type of file")
    part_name: Optional[str] = Field(
        None, max_length=100, description="Part name for multi-part models"
    )
    version: Optional[str] = Field(None, max_length=50, description="Version identifier")
    is_primary: bool = Field(False, description="Whether this is the primary file")
    notes: Optional[str] = Field(None, description="User notes about the file")


class ModelFileCreate(BaseModel):
    """Schema for file upload metadata (file content sent separately as multipart)."""

    file_type: ModelFileType = Field(..., description="Type of file")
    part_name: Optional[str] = Field(
        None, max_length=100, description="Part name for multi-part models"
    )
    version: Optional[str] = Field(None, max_length=50, description="Version identifier")
    is_primary: bool = Field(False, description="Whether this is the primary file")
    notes: Optional[str] = Field(None, description="User notes about the file")


class ModelFileUpdate(BaseModel):
    """Schema for updating file metadata."""

    part_name: Optional[str] = Field(
        None, max_length=100, description="Part name for multi-part models"
    )
    version: Optional[str] = Field(None, max_length=50, description="Version identifier")
    is_primary: Optional[bool] = Field(None, description="Whether this is the primary file")
    notes: Optional[str] = Field(None, description="User notes about the file")


class ModelFileResponse(BaseModel):
    """Schema for file response."""

    id: UUID
    model_id: UUID
    file_type: str = Field(..., description="Type of file")
    file_url: str = Field(..., description="URL to download the file")
    original_filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME content type")
    part_name: Optional[str] = Field(None, description="Part name for multi-part models")
    version: Optional[str] = Field(None, description="Version identifier")
    is_primary: bool = Field(..., description="Whether this is the primary file")
    notes: Optional[str] = Field(None, description="User notes")
    uploaded_at: datetime = Field(..., description="When the file was uploaded")
    uploaded_by_user_id: Optional[UUID] = Field(None, description="User who uploaded")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelFileListResponse(BaseModel):
    """Response for listing model files."""

    files: List[ModelFileResponse] = Field(..., description="List of files")
    total: int = Field(..., description="Total number of files")


class ModelFileUploadResponse(BaseModel):
    """Response after successful file upload."""

    file: ModelFileResponse = Field(..., description="Uploaded file details")
    message: str = Field("File uploaded successfully", description="Success message")
