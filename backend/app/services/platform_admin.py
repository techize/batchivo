"""Platform admin service for cross-tenant operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.order import Order, OrderStatus
from app.models.platform_admin import PlatformAdminAuditLog, PlatformSetting
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User, UserTenant


class PlatformAdminService:
    """
    Business logic service for platform admin operations.

    Handles cross-tenant queries, impersonation, audit logging,
    and platform-wide statistics.
    """

    def __init__(self, db: AsyncSession, admin_user: User, request_info: dict | None = None):
        """
        Initialize the platform admin service.

        Args:
            db: Database session (should bypass RLS for cross-tenant access)
            admin_user: The platform admin user performing actions
            request_info: Optional dict with ip_address, user_agent for audit logging
        """
        self.db = db
        self.admin_user = admin_user
        self.request_info = request_info or {}

    async def get_all_tenants(
        self,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Tenant], int]:
        """
        Get all tenants with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            search: Optional search string for name/slug
            is_active: Optional filter for active status

        Returns:
            Tuple of (tenants list, total count)
        """
        query = select(Tenant)

        # Apply filters
        if search:
            query = query.where(
                (Tenant.name.ilike(f"%{search}%")) | (Tenant.slug.ilike(f"%{search}%"))
            )
        if is_active is not None:
            query = query.where(Tenant.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Apply pagination
        query = query.order_by(Tenant.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        tenants = list(result.scalars().all())

        return tenants, total

    async def get_tenant_by_id(self, tenant_id: UUID) -> Tenant | None:
        """Get a tenant by ID."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_tenant_statistics(self, tenant_id: UUID) -> dict[str, Any]:
        """
        Calculate comprehensive statistics for a tenant.

        Returns:
            Dict with user_count, product_count, order_count, total_revenue
        """
        # Count users in tenant
        user_count = (
            await self.db.scalar(
                select(func.count(UserTenant.id)).where(UserTenant.tenant_id == tenant_id)
            )
            or 0
        )

        # Count products
        product_count = (
            await self.db.scalar(
                select(func.count(Product.id)).where(Product.tenant_id == tenant_id)
            )
            or 0
        )

        # Count orders and sum revenue (shipped/delivered orders count as completed)
        order_stats = await self.db.execute(
            select(
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(Order.total), 0).label("total_revenue"),
            ).where(
                Order.tenant_id == tenant_id,
                Order.status.in_([OrderStatus.SHIPPED, OrderStatus.DELIVERED]),
            )
        )
        stats_row = order_stats.one()

        return {
            "user_count": user_count,
            "product_count": product_count,
            "order_count": stats_row.order_count or 0,
            "total_revenue": float(stats_row.total_revenue or 0),
        }

    async def create_impersonation_token(self, tenant_id: UUID) -> str:
        """
        Generate JWT token for impersonating into a tenant.

        The token includes special claims to identify it as an impersonation:
        - impersonating: True
        - original_admin_id: The platform admin's user ID

        Args:
            tenant_id: The tenant to impersonate into

        Returns:
            JWT access token for impersonation
        """
        # Verify tenant exists
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Create impersonation token
        token = create_access_token(
            {
                "user_id": str(self.admin_user.id),
                "email": self.admin_user.email,
                "tenant_id": str(tenant_id),
                "is_platform_admin": True,
                "impersonating": True,
                "original_admin_id": str(self.admin_user.id),
            }
        )

        # Log the impersonation
        await self._log_audit(
            action="impersonate",
            target_type="tenant",
            target_id=tenant_id,
            metadata={"tenant_name": tenant.name, "tenant_slug": tenant.slug},
        )

        return token

    async def deactivate_tenant(self, tenant_id: UUID) -> Tenant:
        """
        Deactivate a tenant.

        Args:
            tenant_id: The tenant to deactivate

        Returns:
            The updated tenant
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        tenant.is_active = False
        await self.db.flush()

        await self._log_audit(
            action="deactivate_tenant",
            target_type="tenant",
            target_id=tenant_id,
            metadata={"tenant_name": tenant.name},
        )

        return tenant

    async def reactivate_tenant(self, tenant_id: UUID) -> Tenant:
        """
        Reactivate a tenant.

        Args:
            tenant_id: The tenant to reactivate

        Returns:
            The updated tenant
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        tenant.is_active = True
        await self.db.flush()

        await self._log_audit(
            action="reactivate_tenant",
            target_type="tenant",
            target_id=tenant_id,
            metadata={"tenant_name": tenant.name},
        )

        return tenant

    async def search_users(
        self,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[User], int]:
        """
        Search users across all tenants.

        Args:
            search: Optional search string for email/name
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (users list, total count)
        """
        query = select(User)

        if search:
            query = query.where(
                (User.email.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%"))
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Apply pagination
        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def get_platform_setting(self, key: str) -> Any | None:
        """Get a platform setting value by key."""
        result = await self.db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting else None

    async def update_platform_setting(
        self, key: str, value: Any, description: str | None = None
    ) -> PlatformSetting:
        """
        Update a platform setting.

        Args:
            key: Setting key
            value: New value (will be stored as JSON)
            description: Optional description update

        Returns:
            The updated setting
        """
        result = await self.db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        setting = result.scalar_one_or_none()

        if setting:
            old_value = setting.value
            setting.value = value
            setting.updated_by = self.admin_user.id
            setting.updated_at = datetime.utcnow()
            if description is not None:
                setting.description = description
        else:
            old_value = None
            setting = PlatformSetting(
                key=key,
                value=value,
                description=description,
                updated_by=self.admin_user.id,
            )
            self.db.add(setting)

        await self.db.flush()

        await self._log_audit(
            action="update_setting",
            target_type="setting",
            target_id=None,
            metadata={"key": key, "old_value": old_value, "new_value": value},
        )

        return setting

    async def get_audit_logs(
        self,
        skip: int = 0,
        limit: int = 50,
        action: str | None = None,
    ) -> tuple[list[PlatformAdminAuditLog], int]:
        """
        Get platform admin audit logs.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            action: Optional filter by action type

        Returns:
            Tuple of (audit logs list, total count)
        """
        query = select(PlatformAdminAuditLog)

        if action:
            query = query.where(PlatformAdminAuditLog.action == action)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Apply pagination, newest first
        query = query.order_by(PlatformAdminAuditLog.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    async def _log_audit(
        self,
        action: str,
        target_type: str | None,
        target_id: UUID | None,
        metadata: dict | None = None,
    ) -> PlatformAdminAuditLog:
        """
        Log a platform admin action to the audit table.

        Args:
            action: Action type (impersonate, deactivate_tenant, etc.)
            target_type: Type of target (tenant, user, setting)
            target_id: ID of the target entity
            metadata: Additional context

        Returns:
            The created audit log entry
        """
        log = PlatformAdminAuditLog(
            admin_user_id=self.admin_user.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            action_metadata=metadata,
            ip_address=self.request_info.get("ip_address"),
            user_agent=self.request_info.get("user_agent"),
        )
        self.db.add(log)
        await self.db.flush()
        return log
