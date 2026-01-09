"""Pydantic schemas for content pages (policies, info pages)."""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.page import PageType


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug


class PageBase(BaseModel):
    """Base schema for content page."""

    title: str = Field(..., min_length=1, max_length=200, description="Page title")
    content: str = Field(default="", description="Page content in Markdown format")
    page_type: PageType = Field(default=PageType.POLICY, description="Page type")
    meta_description: Optional[str] = Field(
        None, max_length=300, description="SEO meta description"
    )
    is_published: bool = Field(default=False, description="Whether page is publicly visible")
    sort_order: int = Field(default=0, ge=0, description="Sort order for listings")


class PageCreate(PageBase):
    """Schema for creating a page."""

    slug: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="URL-friendly identifier (auto-generated from title if not provided)",
    )

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug_if_empty(cls, v: Optional[str]) -> Optional[str]:
        """Slugify if provided."""
        if v:
            return slugify(v)
        return v


class PageUpdate(BaseModel):
    """Schema for updating a page."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = None
    page_type: Optional[PageType] = None
    meta_description: Optional[str] = Field(None, max_length=300)
    is_published: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)

    @field_validator("slug", mode="before")
    @classmethod
    def slugify_if_provided(cls, v: Optional[str]) -> Optional[str]:
        """Slugify if provided."""
        if v:
            return slugify(v)
        return v


class PageResponse(PageBase):
    """Response schema for page."""

    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PageListResponse(BaseModel):
    """Response schema for list of pages."""

    pages: list[PageResponse]
    total: int


class PagePublicResponse(BaseModel):
    """Public response schema for page (used by shop)."""

    slug: str
    title: str
    content: str
    meta_description: Optional[str] = None
    updated_at: datetime

    model_config = {"from_attributes": True}
