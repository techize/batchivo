"""Pydantic schemas for shipping rates and options."""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ShippingOption(BaseModel):
    """A shipping option with pricing."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique identifier for the shipping method")
    name: str = Field(description="Display name")
    carrier: str = Field(description="Carrier name (e.g., Royal Mail)")
    description: str = Field(description="Description of service level")
    price_pence: int = Field(description="Price in pence")
    estimated_days_min: int = Field(description="Minimum estimated delivery days")
    estimated_days_max: int = Field(description="Maximum estimated delivery days")
    is_tracked: bool = Field(default=False, description="Whether shipment is tracked")
    is_signed: bool = Field(default=False, description="Whether signature required")

    @property
    def price_pounds(self) -> Decimal:
        """Price in pounds."""
        return Decimal(self.price_pence) / 100

    @property
    def estimated_days_display(self) -> str:
        """Display string for estimated days."""
        if self.estimated_days_min == self.estimated_days_max:
            return f"{self.estimated_days_min} day{'s' if self.estimated_days_min != 1 else ''}"
        return f"{self.estimated_days_min}-{self.estimated_days_max} days"


class ShippingRateRequest(BaseModel):
    """Request for shipping rates."""

    postcode: str = Field(description="UK postcode for delivery")
    weight_grams: Optional[int] = Field(default=None, description="Total weight in grams")
    cart_total_pence: Optional[int] = Field(
        default=None, description="Cart total in pence (for free shipping threshold)"
    )


class ShippingRatesResponse(BaseModel):
    """Response containing available shipping options."""

    options: list[ShippingOption]
    postcode_valid: bool = Field(description="Whether the postcode is valid")
    free_shipping_threshold_pence: Optional[int] = Field(
        default=None, description="Cart total needed for free shipping"
    )
    qualifies_for_free_shipping: bool = Field(
        default=False, description="Whether order qualifies for free shipping"
    )


class PostcodeValidationResponse(BaseModel):
    """Response for postcode validation."""

    valid: bool
    postcode: str = Field(description="Normalized postcode")
    area: Optional[str] = Field(default=None, description="Postal area")
    region: Optional[str] = Field(default=None, description="Region/country")
    is_highland_island: bool = Field(
        default=False, description="Whether this is a Highland/Island surcharge area"
    )
