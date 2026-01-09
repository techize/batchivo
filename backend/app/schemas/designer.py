"""Pydantic schemas for licensed designers."""

import re
from datetime import date, datetime
from decimal import Decimal
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


class DesignerBase(BaseModel):
    """Base schema for designer."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Designer display name (e.g., PrintyJay, CinderWings)",
    )
    description: Optional[str] = Field(None, description="Designer bio/description")
    logo_url: Optional[str] = Field(
        None,
        max_length=500,
        description="URL to designer logo image",
    )
    website_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Designer website or store URL",
    )
    social_links: Optional[dict] = Field(
        None,
        description="Social media links as JSON (e.g., {instagram: url, youtube: url})",
    )
    is_active: bool = Field(
        default=True, description="Whether designer is currently active/licensed"
    )


class DesignerCreate(DesignerBase):
    """Schema for creating a designer."""

    slug: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="URL-friendly identifier (auto-generated from name if not provided)",
    )
    # Membership tracking (internal use)
    membership_cost: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Annual/monthly membership cost",
    )
    membership_start_date: Optional[date] = Field(
        None,
        description="When membership started",
    )
    membership_renewal_date: Optional[date] = Field(
        None,
        description="Next renewal date for membership",
    )
    notes: Optional[str] = Field(None, description="Internal notes about designer/membership")

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug_if_empty(cls, v: Optional[str]) -> Optional[str]:
        """Auto-generate slug from name if not provided."""
        if v:
            return slugify(v)
        return v


class DesignerUpdate(BaseModel):
    """Schema for updating a designer."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=500)
    social_links: Optional[dict] = None
    membership_cost: Optional[Decimal] = Field(None, ge=0)
    membership_start_date: Optional[date] = None
    membership_renewal_date: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("slug", mode="before")
    @classmethod
    def slugify_if_provided(cls, v: Optional[str]) -> Optional[str]:
        """Slugify if provided."""
        if v:
            return slugify(v)
        return v


class DesignerResponse(BaseModel):
    """Response schema for designer (full details, internal use)."""

    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    social_links: Optional[dict] = None
    membership_cost: Optional[Decimal] = None
    membership_start_date: Optional[date] = None
    membership_renewal_date: Optional[date] = None
    is_active: bool
    notes: Optional[str] = None
    product_count: int = Field(default=0, description="Number of products from this designer")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DesignerListResponse(BaseModel):
    """Response schema for list of designers."""

    designers: list[DesignerResponse]
    total: int


class DesignerSimple(BaseModel):
    """Simplified designer for embedding in product responses (public)."""

    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    website_url: Optional[str] = None

    model_config = {"from_attributes": True}


class DesignerPublic(BaseModel):
    """Public designer info for shop (excludes membership details)."""

    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    social_links: Optional[dict] = None
    product_count: int = Field(default=0)

    model_config = {"from_attributes": True}
