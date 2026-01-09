"""Audit log API endpoints.

Admin-only endpoints for viewing and searching audit logs.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.audit_log import AuditAction
from app.schemas.audit import (
    AuditLogFilters,
    AuditLogListResponse,
    AuditLogResponse,
    AuditLogSummary,
)
from app.services.audit_service import AuditService

router = APIRouter()


def _log_to_response(log) -> AuditLogResponse:
    """Convert AuditLog model to response schema."""
    return AuditLogResponse(
        id=log.id,
        created_at=log.created_at,
        user_id=log.user_id,
        user_email=log.user.email if log.user else None,
        customer_id=log.customer_id,
        customer_email=log.customer.email if log.customer else None,
        action=log.action,
        description=log.description,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        changes=log.changes,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        extra_data=log.extra_data,
    )


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[UUID] = Query(None, description="Filter by entity ID"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    customer_id: Optional[UUID] = Query(None, description="Filter by customer ID"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List audit logs with optional filtering.

    Supports filtering by action type, entity, user, date range, and IP address.
    Results are ordered by most recent first.
    """
    service = AuditService(db)

    filters = AuditLogFilters(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        customer_id=customer_id,
        start_date=start_date,
        end_date=end_date,
        ip_address=ip_address,
    )

    logs, total = await service.get_logs(
        tenant_id=tenant.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return AuditLogListResponse(
        items=[_log_to_response(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/summary", response_model=AuditLogSummary)
async def get_audit_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary statistics for audit logs.

    Returns action counts, entity type counts, and recent activity.
    """
    service = AuditService(db)
    summary = await service.get_summary(tenant_id=tenant.id, days=days)

    return AuditLogSummary(
        total_entries=summary["total_entries"],
        actions_breakdown=summary["actions_breakdown"],
        entity_types_breakdown=summary["entity_types_breakdown"],
        recent_activity=[_log_to_response(log) for log in summary["recent_activity"]],
    )


@router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_history(
    entity_type: str,
    entity_id: UUID,
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get audit history for a specific entity.

    Useful for viewing all changes to a particular order, product, etc.
    """
    service = AuditService(db)
    logs = await service.get_entity_history(
        tenant_id=tenant.id,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "history": [_log_to_response(log) for log in logs],
        "total": len(logs),
    }


@router.get("/user/{user_id}")
async def get_user_activity(
    user_id: UUID,
    limit: int = Query(100, ge=1, le=500, description="Maximum entries to return"),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent activity for a specific admin user.

    Useful for reviewing what actions a team member has taken.
    """
    service = AuditService(db)
    logs = await service.get_user_activity(
        tenant_id=tenant.id,
        user_id=user_id,
        limit=limit,
    )

    return {
        "user_id": user_id,
        "activity": [_log_to_response(log) for log in logs],
        "total": len(logs),
    }


@router.get("/actions")
async def list_action_types():
    """
    List all available audit action types.

    Useful for populating filter dropdowns in the UI.
    """
    return {
        "actions": [
            {"value": action.value, "label": action.name.replace("_", " ").title()}
            for action in AuditAction
        ]
    }
