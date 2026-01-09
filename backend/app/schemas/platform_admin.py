"""Pydantic schemas for platform admin API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# Tenant schemas
class TenantResponse(BaseModel):
    """Schema for tenant in list response."""

    id: UUID
    name: str
    slug: str
    tenant_type: str
    is_active: bool
    created_at: datetime
    settings: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class TenantDetailResponse(TenantResponse):
    """Schema for tenant detail with statistics."""

    user_count: int = 0
    product_count: int = 0
    order_count: int = 0
    total_revenue: float = 0.0


class PaginatedTenantsResponse(BaseModel):
    """Paginated list of tenants."""

    items: list[TenantResponse]
    total: int
    skip: int
    limit: int


# User schemas for platform admin
class UserResponse(BaseModel):
    """Schema for user in platform admin context."""

    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    is_platform_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedUsersResponse(BaseModel):
    """Paginated list of users."""

    items: list[UserResponse]
    total: int
    skip: int
    limit: int


# Impersonation
class ImpersonationResponse(BaseModel):
    """Response for impersonation request."""

    access_token: str
    token_type: str = "bearer"
    tenant_id: UUID
    tenant_name: str


# Platform settings
class PlatformSettingResponse(BaseModel):
    """Schema for platform setting."""

    key: str
    value: Any
    description: str | None
    updated_at: datetime
    updated_by: UUID | None

    class Config:
        from_attributes = True


class PlatformSettingUpdate(BaseModel):
    """Schema for updating a platform setting."""

    value: Any = Field(..., description="New value for the setting")
    description: str | None = Field(None, description="Optional description update")


class PlatformSettingsResponse(BaseModel):
    """List of platform settings."""

    items: list[PlatformSettingResponse]


# Audit logs
class AuditLogResponse(BaseModel):
    """Schema for audit log entry."""

    id: UUID
    admin_user_id: UUID
    action: str
    target_type: str | None
    target_id: UUID | None
    action_metadata: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedAuditLogsResponse(BaseModel):
    """Paginated list of audit logs."""

    items: list[AuditLogResponse]
    total: int
    skip: int
    limit: int


# Tenant actions
class TenantActionResponse(BaseModel):
    """Response for tenant action (activate/deactivate)."""

    id: UUID
    name: str
    is_active: bool
    message: str
