"""Pydantic schemas for product categories."""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug


class CategoryBase(BaseModel):
    """Base schema for category."""

    name: str = Field(..., min_length=1, max_length=100, description="Category display name")
    description: Optional[str] = Field(None, description="Category description")
    display_order: int = Field(default=0, ge=0, description="Sort order (lower = first)")
    is_active: bool = Field(default=True, description="Whether category is visible in shop")


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""

    slug: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="URL-friendly identifier (auto-generated from name if not provided)",
    )

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug_if_empty(cls, v: Optional[str], info) -> str:
        """Auto-generate slug from name if not provided."""
        if v:
            return slugify(v)
        # Will be generated in endpoint from name
        return v


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

    @field_validator("slug", mode="before")
    @classmethod
    def slugify_if_provided(cls, v: Optional[str]) -> Optional[str]:
        """Slugify if provided."""
        if v:
            return slugify(v)
        return v


class CategoryResponse(CategoryBase):
    """Response schema for category."""

    id: UUID
    slug: str
    product_count: int = Field(default=0, description="Number of products in this category")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CategoryListResponse(BaseModel):
    """Response schema for list of categories."""

    categories: list[CategoryResponse]
    total: int


class CategorySimple(BaseModel):
    """Simplified category for embedding in product responses."""

    id: UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}
