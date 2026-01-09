"""Pydantic schemas for product images."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProductImageBase(BaseModel):
    """Base schema for product image."""

    alt_text: str = Field(default="", max_length=255, description="Alt text for accessibility")


class ProductImageCreate(ProductImageBase):
    """Schema for creating a product image (metadata only, file uploaded separately)."""

    pass


class ProductImageUpdate(BaseModel):
    """Schema for updating a product image."""

    alt_text: Optional[str] = Field(None, max_length=255)
    display_order: Optional[int] = Field(None, ge=0)


class ProductImageResponse(ProductImageBase):
    """Response schema for product image."""

    id: UUID
    product_id: UUID
    image_url: str
    thumbnail_url: Optional[str] = None
    display_order: int
    is_primary: bool
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductImageListResponse(BaseModel):
    """Response schema for list of product images."""

    images: list[ProductImageResponse]
    total: int
