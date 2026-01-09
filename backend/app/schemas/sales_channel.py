"""Pydantic schemas for Sales Channel API."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SalesChannelBase(BaseModel):
    """Base sales channel schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Channel name")
    platform_type: str = Field(
        ..., description="Platform type: fair, online_shop, shopify, ebay, etsy, amazon, other"
    )
    fee_percentage: Decimal = Field(
        Decimal("0"), ge=0, le=100, description="Platform percentage fee"
    )
    fee_fixed: Decimal = Field(Decimal("0"), ge=0, description="Fixed fee per transaction")
    monthly_cost: Decimal = Field(Decimal("0"), ge=0, description="Monthly subscription/booth fee")
    is_active: bool = Field(True, description="Whether channel is active")


class SalesChannelCreate(SalesChannelBase):
    """Schema for creating a sales channel."""

    pass


class SalesChannelUpdate(BaseModel):
    """Schema for updating a sales channel."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    platform_type: Optional[str] = None
    fee_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    fee_fixed: Optional[Decimal] = Field(None, ge=0)
    monthly_cost: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class SalesChannelResponse(SalesChannelBase):
    """Schema for sales channel response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesChannelListResponse(BaseModel):
    """Schema for paginated sales channel list."""

    channels: list[SalesChannelResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)
