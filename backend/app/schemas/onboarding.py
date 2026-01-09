"""Pydantic schemas for tenant onboarding and registration."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.tenant_settings import TenantType


class TenantRegistrationRequest(BaseModel):
    """Schema for new tenant registration request."""

    # User details
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    full_name: str = Field(..., min_length=1, max_length=255, description="User's full name")

    # Business details
    business_name: str = Field(
        ..., min_length=2, max_length=100, description="Business/workspace name"
    )
    tenant_type: TenantType = Field(
        default=TenantType.GENERIC,
        description="Type of business (determines features)",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class TenantRegistrationResponse(BaseModel):
    """Schema for registration response (before email verification)."""

    message: str = Field(
        default="Registration successful. Please check your email to verify your account.",
        description="Success message",
    )
    email: str = Field(..., description="Email address verification was sent to")


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request."""

    token: str = Field(..., min_length=1, description="Email verification token")


class EmailVerificationResponse(BaseModel):
    """Schema for successful email verification."""

    model_config = ConfigDict(from_attributes=True)

    message: str = Field(default="Email verified successfully", description="Success message")
    tenant_id: UUID = Field(..., description="Created tenant ID")
    tenant_name: str = Field(..., description="Tenant name")
    tenant_slug: str = Field(..., description="Tenant URL slug")
    user_id: UUID = Field(..., description="Created user ID")
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class ResendVerificationRequest(BaseModel):
    """Schema for resending verification email."""

    email: EmailStr = Field(..., description="Email address to resend verification to")


class ResendVerificationResponse(BaseModel):
    """Schema for resend verification response."""

    message: str = Field(
        default="If an unverified account exists for this email, a verification link has been sent.",
        description="Response message",
    )


class RegistrationStatusResponse(BaseModel):
    """Schema for checking registration status."""

    email: str = Field(..., description="Email address")
    is_registered: bool = Field(..., description="Whether email is registered")
    is_verified: bool = Field(..., description="Whether email is verified")
    tenant_name: Optional[str] = Field(None, description="Tenant name if registered")


class OnboardingUserResponse(BaseModel):
    """User details in onboarding response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User's full name")
    is_active: bool = Field(..., description="Whether user is active")


class OnboardingTenantResponse(BaseModel):
    """Tenant details in onboarding response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., description="Tenant name")
    slug: str = Field(..., description="Tenant URL slug")
    tenant_type: str = Field(..., description="Tenant type")
    is_active: bool = Field(..., description="Whether tenant is active")
    created_at: datetime = Field(..., description="Creation timestamp")
