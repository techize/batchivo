"""Platform admin API endpoints for managing tenants and platform settings."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.auth.dependencies import PlatformAdmin, PlatformAdminDB
from app.schemas.platform_admin import (
    AuditLogResponse,
    ImpersonationResponse,
    PaginatedAuditLogsResponse,
    PaginatedTenantsResponse,
    TenantActionResponse,
    TenantDetailResponse,
    TenantResponse,
)
from app.services.platform_admin import PlatformAdminService

router = APIRouter(prefix="/platform", tags=["Platform Admin"])


def _get_request_info(request: Request) -> dict:
    """Extract request info for audit logging."""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


@router.get("/tenants", response_model=PaginatedTenantsResponse)
async def list_tenants(
    request: Request,
    admin: PlatformAdmin,
    db: PlatformAdminDB,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    search: str | None = Query(None, description="Search by name or slug"),
    is_active: bool | None = Query(None, description="Filter by active status"),
):
    """
    List all tenants with pagination and filters.

    Requires platform admin access.

    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (1-100)
    - **search**: Optional search string for tenant name or slug
    - **is_active**: Optional filter for active/inactive tenants
    """
    service = PlatformAdminService(db, admin, _get_request_info(request))
    tenants, total = await service.get_all_tenants(
        skip=skip,
        limit=limit,
        search=search,
        is_active=is_active,
    )

    return PaginatedTenantsResponse(
        items=[TenantResponse.model_validate(t) for t in tenants],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant_detail(
    request: Request,
    tenant_id: UUID,
    admin: PlatformAdmin,
    db: PlatformAdminDB,
):
    """
    Get detailed tenant information with statistics.

    Requires platform admin access.

    Returns tenant details including:
    - Basic tenant information (name, slug, type, status)
    - User count
    - Product count
    - Order count (confirmed + fulfilled)
    - Total revenue
    """
    service = PlatformAdminService(db, admin, _get_request_info(request))
    tenant = await service.get_tenant_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )

    # Get statistics for the tenant
    stats = await service.get_tenant_statistics(tenant_id)

    # Build response with tenant data and statistics
    return TenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        tenant_type=tenant.tenant_type,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        settings=tenant.settings,
        user_count=stats["user_count"],
        product_count=stats["product_count"],
        order_count=stats["order_count"],
        total_revenue=stats["total_revenue"],
    )


@router.post("/tenants/{tenant_id}/impersonate", response_model=ImpersonationResponse)
async def impersonate_tenant(
    request: Request,
    tenant_id: UUID,
    admin: PlatformAdmin,
    db: PlatformAdminDB,
):
    """
    Generate an impersonation JWT token for accessing a tenant.

    Requires platform admin access.

    The generated token:
    - Allows access to the specified tenant's data
    - Includes `impersonating: true` claim
    - Includes `original_admin_id` for audit trail
    - Can be used like a normal access token

    Use this for debugging, support, or administrative access to tenant data.
    All impersonation actions are logged to the audit trail.
    """
    service = PlatformAdminService(db, admin, _get_request_info(request))
    tenant = await service.get_tenant_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot impersonate inactive tenant",
        )

    # Generate impersonation token (this also logs the action)
    token = await service.create_impersonation_token(tenant_id)

    return ImpersonationResponse(
        access_token=token,
        token_type="bearer",
        tenant_id=tenant_id,
        tenant_name=tenant.name,
    )


@router.post("/tenants/{tenant_id}/deactivate", response_model=TenantActionResponse)
async def deactivate_tenant(
    request: Request,
    tenant_id: UUID,
    admin: PlatformAdmin,
    db: PlatformAdminDB,
):
    """
    Deactivate a tenant (soft delete).

    Requires platform admin access.

    Deactivation:
    - Sets is_active=false on the tenant
    - Prevents users from logging into the tenant
    - Prevents impersonation into the tenant
    - Does NOT delete any data

    Use POST /tenants/{id}/reactivate to restore access.
    """
    service = PlatformAdminService(db, admin, _get_request_info(request))

    try:
        tenant = await service.deactivate_tenant(tenant_id)
        return TenantActionResponse(
            id=tenant.id,
            name=tenant.name,
            is_active=tenant.is_active,
            message=f"Tenant '{tenant.name}' has been deactivated",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/tenants/{tenant_id}/reactivate", response_model=TenantActionResponse)
async def reactivate_tenant(
    request: Request,
    tenant_id: UUID,
    admin: PlatformAdmin,
    db: PlatformAdminDB,
):
    """
    Reactivate a previously deactivated tenant.

    Requires platform admin access.

    Reactivation:
    - Sets is_active=true on the tenant
    - Restores user access to the tenant
    - Allows impersonation again
    """
    service = PlatformAdminService(db, admin, _get_request_info(request))

    try:
        tenant = await service.reactivate_tenant(tenant_id)
        return TenantActionResponse(
            id=tenant.id,
            name=tenant.name,
            is_active=tenant.is_active,
            message=f"Tenant '{tenant.name}' has been reactivated",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/audit", response_model=PaginatedAuditLogsResponse)
async def list_audit_logs(
    request: Request,
    admin: PlatformAdmin,
    db: PlatformAdminDB,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    action: str | None = Query(None, description="Filter by action type"),
):
    """
    List platform admin audit logs.

    Requires platform admin access.

    Returns a paginated list of all platform admin actions including:
    - Impersonations
    - Tenant activations/deactivations
    - Settings changes
    - User searches

    Filter by action type to see specific activities.
    """
    service = PlatformAdminService(db, admin, _get_request_info(request))
    logs, total = await service.get_audit_logs(
        skip=skip,
        limit=limit,
        action=action,
    )

    return PaginatedAuditLogsResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )
