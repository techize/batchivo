"""Pydantic schemas for payment processing."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ShippingAddress(BaseModel):
    """Customer shipping address."""

    first_name: str
    last_name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    county: Optional[str] = None
    postcode: str
    country: str = "GB"


class CustomerDetails(BaseModel):
    """Customer contact details."""

    email: str
    phone: Optional[str] = None


class CartItem(BaseModel):
    """Item in the shopping cart."""

    product_id: UUID
    name: str
    quantity: int = Field(ge=1)
    price: int = Field(ge=0, description="Price in pence")


class PaymentRequest(BaseModel):
    """Request to process a payment."""

    payment_token: str = Field(..., description="Token from Square Web Payments SDK")
    amount: int = Field(ge=1, description="Total amount in pence")
    currency: str = Field(default="GBP", pattern="^[A-Z]{3}$")
    customer: CustomerDetails
    shipping_address: ShippingAddress
    shipping_method: str
    shipping_cost: int = Field(ge=0, description="Shipping cost in pence")
    items: list[CartItem]
    idempotency_key: Optional[str] = Field(
        None, description="Client-provided idempotency key for duplicate prevention"
    )


class PaymentResponse(BaseModel):
    """Response after successful payment."""

    success: bool
    order_id: str
    payment_id: str
    amount: int
    currency: str
    status: str
    receipt_url: Optional[str] = None
    created_at: datetime


class PaymentError(BaseModel):
    """Error response for failed payments."""

    success: bool = False
    error_code: str
    error_message: str
    detail: Optional[str] = None
