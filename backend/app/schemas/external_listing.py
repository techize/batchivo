"""Pydantic schemas for External Listing API (marketplace integrations)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExternalListingBase(BaseModel):
    """Base schema for external listing."""

    platform: str = Field(..., description="Platform name: etsy, ebay, amazon, shopify")
    external_id: str = Field(..., description="Listing ID on the external platform")
    external_url: Optional[str] = Field(None, description="URL to the listing")


class ExternalListingCreate(BaseModel):
    """Schema for creating an external listing (usually from sync response)."""

    platform: str = Field(..., description="Platform name")
    external_id: str = Field(..., description="Listing ID on the external platform")
    external_url: Optional[str] = Field(None, description="URL to the listing")


class ExternalListingResponse(ExternalListingBase):
    """Schema for external listing in API response."""

    id: UUID
    product_id: UUID
    sync_status: str = Field(..., description="Sync status: synced, pending, error")
    last_synced_at: Optional[datetime] = Field(None, description="Last sync timestamp")
    last_sync_error: Optional[str] = Field(None, description="Last sync error message")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SyncToEtsyRequest(BaseModel):
    """Request schema for syncing a product to Etsy."""

    force: bool = Field(False, description="Force sync even if already synced")


class SyncToEtsyResponse(BaseModel):
    """Response schema for sync operation."""

    success: bool
    message: str
    listing: Optional[ExternalListingResponse] = None
    etsy_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
