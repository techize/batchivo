"""Audit logging service.

Provides centralized audit logging for tracking user actions across the platform.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog
from app.models.customer import Customer
from app.models.user import User
from app.schemas.audit import AuditLogFilters


class AuditService:
    """Service for creating and querying audit logs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        tenant_id: UUID,
        action: AuditAction,
        entity_type: str,
        entity_id: Optional[UUID] = None,
        user: Optional[User] = None,
        customer: Optional[Customer] = None,
        changes: Optional[dict] = None,
        description: Optional[str] = None,
        request: Optional[Request] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            tenant_id: The tenant this log belongs to
            action: The type of action being logged
            entity_type: Type of entity affected (e.g., "order", "product")
            entity_id: ID of the affected entity (if applicable)
            user: Admin user who performed the action
            customer: Customer who performed the action
            changes: Dictionary of changes for UPDATE actions
            description: Human-readable description
            request: FastAPI request object for IP/user-agent extraction
            metadata: Additional context data

        Returns:
            The created AuditLog entry
        """
        # Extract request context
        ip_address = None
        user_agent = None

        if request:
            # Get real IP (handle proxies)
            ip_address = request.headers.get(
                "X-Forwarded-For", request.client.host if request.client else None
            )
            if ip_address and "," in ip_address:
                ip_address = ip_address.split(",")[0].strip()

            user_agent = request.headers.get("User-Agent")

        # Create the log entry
        log_entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user.id if user else None,
            customer_id=customer.id if customer else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=metadata,
        )

        self.db.add(log_entry)
        await self.db.flush()

        return log_entry

    async def log_create(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        user: Optional[User] = None,
        customer: Optional[Customer] = None,
        request: Optional[Request] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """Log a CREATE action."""
        return await self.log(
            tenant_id=tenant_id,
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            user=user,
            customer=customer,
            description=f"Created {entity_type}",
            request=request,
            metadata=metadata,
        )

    async def log_update(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        changes: dict,
        user: Optional[User] = None,
        customer: Optional[Customer] = None,
        request: Optional[Request] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """Log an UPDATE action with changes."""
        return await self.log(
            tenant_id=tenant_id,
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            user=user,
            customer=customer,
            changes=changes,
            description=f"Updated {entity_type}",
            request=request,
            metadata=metadata,
        )

    async def log_delete(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        user: Optional[User] = None,
        customer: Optional[Customer] = None,
        request: Optional[Request] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """Log a DELETE action."""
        return await self.log(
            tenant_id=tenant_id,
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            user=user,
            customer=customer,
            description=f"Deleted {entity_type}",
            request=request,
            metadata=metadata,
        )

    async def log_login(
        self,
        tenant_id: UUID,
        user: Optional[User] = None,
        customer: Optional[Customer] = None,
        success: bool = True,
        request: Optional[Request] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """Log a login attempt."""
        action = AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED
        entity_type = "user" if user else "customer"

        return await self.log(
            tenant_id=tenant_id,
            action=action,
            entity_type=entity_type,
            entity_id=user.id if user else (customer.id if customer else None),
            user=user if success else None,
            customer=customer if success else None,
            description=f"{'Successful' if success else 'Failed'} login",
            request=request,
            metadata=metadata,
        )

    async def get_logs(
        self,
        tenant_id: UUID,
        filters: Optional[AuditLogFilters] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """
        Get audit logs with optional filtering and pagination.

        Returns:
            Tuple of (logs, total_count)
        """
        query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        # Apply filters
        if filters:
            if filters.action:
                query = query.where(AuditLog.action == filters.action)
            if filters.entity_type:
                query = query.where(AuditLog.entity_type == filters.entity_type)
            if filters.entity_id:
                query = query.where(AuditLog.entity_id == filters.entity_id)
            if filters.user_id:
                query = query.where(AuditLog.user_id == filters.user_id)
            if filters.customer_id:
                query = query.where(AuditLog.customer_id == filters.customer_id)
            if filters.start_date:
                query = query.where(AuditLog.created_at >= filters.start_date)
            if filters.end_date:
                query = query.where(AuditLog.created_at <= filters.end_date)
            if filters.ip_address:
                query = query.where(AuditLog.ip_address == filters.ip_address)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = (
            query.order_by(desc(AuditLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    async def get_entity_history(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
    ) -> list[AuditLog]:
        """Get all audit logs for a specific entity."""
        query = (
            select(AuditLog)
            .where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(desc(AuditLog.created_at))
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_activity(
        self,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get recent activity for a specific user."""
        query = (
            select(AuditLog)
            .where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.user_id == user_id,
            )
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_summary(
        self,
        tenant_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get summary statistics for audit logs."""
        from datetime import timedelta

        cutoff = None
        if days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)

        base_query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
        if cutoff:
            base_query = base_query.where(AuditLog.created_at >= cutoff)

        # Total count
        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar() or 0

        # Actions breakdown
        actions_query = (
            select(AuditLog.action, func.count().label("count"))
            .where(AuditLog.tenant_id == tenant_id)
            .group_by(AuditLog.action)
        )
        if cutoff:
            actions_query = actions_query.where(AuditLog.created_at >= cutoff)

        actions_result = await self.db.execute(actions_query)
        actions_breakdown = {row.action.value: row.count for row in actions_result.all()}

        # Entity types breakdown
        entities_query = (
            select(AuditLog.entity_type, func.count().label("count"))
            .where(AuditLog.tenant_id == tenant_id)
            .group_by(AuditLog.entity_type)
        )
        if cutoff:
            entities_query = entities_query.where(AuditLog.created_at >= cutoff)

        entities_result = await self.db.execute(entities_query)
        entities_breakdown = {row.entity_type: row.count for row in entities_result.all()}

        # Recent activity
        recent_query = (
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(desc(AuditLog.created_at))
            .limit(10)
        )
        recent_result = await self.db.execute(recent_query)
        recent_logs = list(recent_result.scalars().all())

        return {
            "total_entries": total,
            "actions_breakdown": actions_breakdown,
            "entity_types_breakdown": entities_breakdown,
            "recent_activity": recent_logs,
        }


def calculate_changes(old_obj: Any, new_data: dict) -> dict:
    """
    Calculate changes between an existing object and new data.

    Args:
        old_obj: The existing SQLAlchemy model instance
        new_data: Dictionary of new values

    Returns:
        Dictionary of changes: {field: {"old": old_value, "new": new_value}}
    """
    changes = {}

    for field, new_value in new_data.items():
        if hasattr(old_obj, field):
            old_value = getattr(old_obj, field)
            if old_value != new_value:
                # Handle special types
                if hasattr(old_value, "isoformat"):
                    old_value = old_value.isoformat()
                if hasattr(new_value, "isoformat"):
                    new_value = new_value.isoformat()
                if isinstance(old_value, UUID):
                    old_value = str(old_value)
                if isinstance(new_value, UUID):
                    new_value = str(new_value)

                changes[field] = {"old": old_value, "new": new_value}

    return changes
