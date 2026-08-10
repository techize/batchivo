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


class CheckoutBaseRequest(BaseModel):
    """Shared customer/cart fields for checkout payment flows."""

    amount: int = Field(ge=1, description="Total amount in pence")
    currency: str = Field(default="GBP", pattern="^[A-Z]{3}$")
    customer: CustomerDetails
    shipping_address: ShippingAddress
    shipping_method: str
    shipping_cost: int = Field(ge=0, description="Shipping cost in pence")
    items: list[CartItem]
    discount_code: Optional[str] = None
    discount_amount: int = Field(default=0, ge=0, description="Discount amount in pence")
    idempotency_key: Optional[str] = Field(
        None, description="Client-provided idempotency key for duplicate prevention"
    )


class PaymentRequest(CheckoutBaseRequest):
    """Request to process an embedded Square card payment."""

    payment_token: str = Field(..., description="Token from Square Web Payments SDK")
    verification_token: Optional[str] = Field(
        None, description="Buyer verification token from Square Web Payments SDK"
    )


class HostedCheckoutRequest(CheckoutBaseRequest):
    """Request to create a Square-hosted checkout link."""

    redirect_url: Optional[str] = Field(
        None, description="Storefront URL Square should redirect to after payment"
    )


class HostedCheckoutResponse(BaseModel):
    """Response containing a Square-hosted checkout URL."""

    success: bool = True
    order_id: str
    payment_link_id: str
    checkout_url: str


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
