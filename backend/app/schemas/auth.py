"""Pydantic schemas for authentication."""

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class UserRegister(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    full_name: str | None = Field(None, description="User's full name")
    tenant_name: str | None = Field(
        None, description="Workspace/tenant name (optional, defaults to email)"
    )


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str = Field(..., description="JWT refresh token")


class TokenData(BaseModel):
    """Schema for JWT token payload data."""

    user_id: UUID = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    tenant_id: UUID | None = Field(None, description="Current tenant UUID")
    is_platform_admin: bool = Field(default=False, description="Whether user is platform admin")


class UserResponse(BaseModel):
    """Schema for user response (without password)."""

    id: str
    email: str
    name: str
    tenant_id: str | None
    tenant_name: str | None
    is_platform_admin: bool = False

    class Config:
        from_attributes = True


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")
