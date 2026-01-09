"""Pydantic schemas for customer accounts."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ============================================
# Authentication Schemas
# ============================================


class CustomerRegister(BaseModel):
    """Schema for customer registration."""

    email: EmailStr = Field(..., description="Customer email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    marketing_consent: bool = Field(False, description="Consent to marketing emails")


class CustomerLogin(BaseModel):
    """Schema for customer login."""

    email: EmailStr = Field(..., description="Customer email address")
    password: str = Field(..., description="Password")


class CustomerTokenResponse(BaseModel):
    """Response after successful login/register."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiry in seconds")
    customer: "CustomerResponse"


class CustomerRefreshToken(BaseModel):
    """Schema for token refresh."""

    refresh_token: str


class CustomerForgotPassword(BaseModel):
    """Schema for forgot password request."""

    email: EmailStr


class CustomerResetPassword(BaseModel):
    """Schema for password reset."""

    token: str = Field(..., description="Reset token from email")
    password: str = Field(..., min_length=8, description="New password")


class CustomerChangePassword(BaseModel):
    """Schema for password change (logged in user)."""

    current_password: str
    new_password: str = Field(..., min_length=8)


class CustomerVerifyEmail(BaseModel):
    """Schema for email verification."""

    token: str = Field(..., description="Verification token from email")


# ============================================
# Profile Schemas
# ============================================


class CustomerUpdate(BaseModel):
    """Schema for updating customer profile."""

    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    marketing_consent: Optional[bool] = None


class CustomerResponse(BaseModel):
    """Customer response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    phone: Optional[str]
    email_verified: bool
    email_verified_at: Optional[datetime]
    marketing_consent: bool
    last_login_at: Optional[datetime]
    is_active: bool
    created_at: datetime


class CustomerWithAddresses(CustomerResponse):
    """Customer with addresses included."""

    addresses: list["CustomerAddressResponse"] = []


# ============================================
# Address Schemas
# ============================================


class CustomerAddressCreate(BaseModel):
    """Schema for creating a customer address."""

    label: str = Field("Home", max_length=50, description="Address label")
    is_default: bool = Field(False, description="Set as default address")
    recipient_name: str = Field(..., max_length=255, description="Recipient name")
    phone: Optional[str] = Field(None, max_length=50)
    line1: str = Field(..., max_length=255, description="Address line 1")
    line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    county: Optional[str] = Field(None, max_length=100)
    postcode: str = Field(..., max_length=20)
    country: str = Field("United Kingdom", max_length=100)


class CustomerAddressUpdate(BaseModel):
    """Schema for updating a customer address."""

    label: Optional[str] = Field(None, max_length=50)
    is_default: Optional[bool] = None
    recipient_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    line1: Optional[str] = Field(None, max_length=255)
    line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    county: Optional[str] = Field(None, max_length=100)
    postcode: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)


class CustomerAddressResponse(BaseModel):
    """Customer address response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    is_default: bool
    recipient_name: str
    phone: Optional[str]
    line1: str
    line2: Optional[str]
    city: str
    county: Optional[str]
    postcode: str
    country: str
    created_at: datetime
    updated_at: datetime


class CustomerAddressListResponse(BaseModel):
    """List of customer addresses."""

    items: list[CustomerAddressResponse]
    total: int


# ============================================
# Order History Schemas (simplified view)
# ============================================


class CustomerOrderItemResponse(BaseModel):
    """Simplified order item for customer view."""

    model_config = ConfigDict(from_attributes=True)

    product_sku: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float


class CustomerOrderResponse(BaseModel):
    """Order response for customer order history."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_number: str
    status: str
    subtotal: float
    shipping_cost: float
    discount_amount: float
    total: float
    currency: str
    shipping_method: str
    tracking_number: Optional[str]
    tracking_url: Optional[str]
    created_at: datetime
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    items: list[CustomerOrderItemResponse] = []


class CustomerOrderListResponse(BaseModel):
    """Paginated list of customer orders."""

    items: list[CustomerOrderResponse]
    total: int
    skip: int
    limit: int


# Rebuild models for forward references
CustomerTokenResponse.model_rebuild()
CustomerWithAddresses.model_rebuild()
