"""Pydantic schemas for audit logging."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.audit_log import AuditAction


class AuditLogResponse(BaseModel):
    """Response for a single audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime

    # Actor
    user_id: Optional[UUID] = None
    user_email: Optional[str] = Field(
        default=None, description="Email of admin user who performed action"
    )
    customer_id: Optional[UUID] = None
    customer_email: Optional[str] = Field(
        default=None, description="Email of customer who performed action"
    )

    # Action
    action: AuditAction
    description: Optional[str] = None

    # Entity
    entity_type: str
    entity_id: Optional[UUID] = None

    # Changes (for UPDATE actions)
    changes: Optional[dict] = None

    # Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    extra_data: Optional[dict] = None


class AuditLogListResponse(BaseModel):
    """Paginated list of audit logs."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditLogFilters(BaseModel):
    """Filters for querying audit logs."""

    action: Optional[AuditAction] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ip_address: Optional[str] = None


class AuditLogSummary(BaseModel):
    """Summary statistics for audit logs."""

    total_entries: int
    actions_breakdown: dict[str, int] = Field(description="Count of entries by action type")
    entity_types_breakdown: dict[str, int] = Field(description="Count of entries by entity type")
    recent_activity: list[AuditLogResponse] = Field(description="Most recent 10 audit entries")
