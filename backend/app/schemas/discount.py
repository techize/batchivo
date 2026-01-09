"""Pydantic schemas for Discount Code API."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.discount import DiscountType


class DiscountCodeBase(BaseModel):
    """Base schema for discount codes."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Discount code (will be uppercased)",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name for the discount",
    )
    description: Optional[str] = Field(
        None,
        description="Internal description",
    )
    discount_type: DiscountType = Field(
        ...,
        description="Type of discount: percentage or fixed_amount",
    )
    amount: Decimal = Field(
        ...,
        gt=0,
        description="Discount amount (percentage 0-100 or fixed amount in GBP)",
    )
    min_order_amount: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Minimum order subtotal required",
    )
    max_discount_amount: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Maximum discount amount (caps percentage discounts)",
    )
    max_uses: Optional[int] = Field(
        None,
        gt=0,
        description="Maximum total uses (null = unlimited)",
    )
    max_uses_per_customer: Optional[int] = Field(
        None,
        gt=0,
        description="Maximum uses per customer email (null = unlimited)",
    )
    valid_from: datetime = Field(
        ...,
        description="Start of validity period",
    )
    valid_to: Optional[datetime] = Field(
        None,
        description="End of validity period (null = no expiry)",
    )
    is_active: bool = Field(
        True,
        description="Whether the discount is currently active",
    )

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        """Convert code to uppercase."""
        return v.upper().strip()

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal, info) -> Decimal:
        """Validate amount based on discount type."""
        # Note: full validation with discount_type requires model_validator
        # For now, just ensure it's positive
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v


class DiscountCodeCreate(DiscountCodeBase):
    """Schema for creating a discount code."""

    pass


class DiscountCodeUpdate(BaseModel):
    """Schema for updating a discount code."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    discount_type: Optional[DiscountType] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    min_order_amount: Optional[Decimal] = Field(None, ge=0)
    max_discount_amount: Optional[Decimal] = Field(None, ge=0)
    max_uses: Optional[int] = Field(None, gt=0)
    max_uses_per_customer: Optional[int] = Field(None, gt=0)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_active: Optional[bool] = None


class DiscountCodeResponse(DiscountCodeBase):
    """Schema for discount code response."""

    id: UUID
    tenant_id: UUID
    current_uses: int = Field(
        description="Current number of times this code has been used",
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscountCodeListResponse(BaseModel):
    """Schema for paginated list of discount codes."""

    items: list[DiscountCodeResponse]
    total: int
    skip: int
    limit: int


# Validation schemas for checkout
class DiscountValidationRequest(BaseModel):
    """Schema for validating a discount code."""

    code: str = Field(..., description="Discount code to validate")
    subtotal: Decimal = Field(..., ge=0, description="Order subtotal")
    customer_email: Optional[str] = Field(
        None,
        description="Customer email for per-customer limit check",
    )

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        """Convert code to uppercase."""
        return v.upper().strip()


class DiscountValidationResponse(BaseModel):
    """Schema for discount validation response."""

    valid: bool = Field(description="Whether the discount code is valid")
    code: str = Field(description="The discount code")
    discount_type: Optional[DiscountType] = Field(
        None,
        description="Type of discount",
    )
    discount_amount: Optional[Decimal] = Field(
        None,
        description="Calculated discount amount for this order",
    )
    message: Optional[str] = Field(
        None,
        description="Validation message (reason if invalid)",
    )


# Usage tracking
class DiscountUsageResponse(BaseModel):
    """Schema for discount usage record."""

    id: UUID
    discount_code_id: UUID
    order_id: UUID
    customer_email: str
    discount_amount: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
