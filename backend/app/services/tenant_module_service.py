"""TenantModule service for managing per-tenant module access control."""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantType
from app.models.tenant_module import TenantModule
from app.models.user import User

logger = logging.getLogger(__name__)


# Default modules enabled per tenant type
DEFAULT_MODULES_BY_TYPE: Dict[str, List[str]] = {
    TenantType.THREE_D_PRINT.value: [
        "spools",
        "models",
        "printers",
        "production",
        "products",
        "orders",
        "categories",
    ],
    TenantType.HAND_KNITTING.value: [
        "products",
        "orders",
        "categories",
    ],
    TenantType.MACHINE_KNITTING.value: [
        "products",
        "orders",
        "categories",
    ],
    TenantType.GENERIC.value: [
        "products",
        "orders",
        "categories",
    ],
}

# All available modules in the system
ALL_MODULES = [
    "spools",
    "models",
    "printers",
    "production",
    "products",
    "orders",
    "categories",
]


class TenantModuleService:
    """
    Service for managing tenant module access control.

    Handles enabling/disabling modules per tenant, getting module status,
    and resetting to default configurations.
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant: Optional[Tenant] = None,
        user: Optional[User] = None,
    ):
        """
        Initialize the tenant module service.

        Args:
            db: AsyncSession instance for database operations
            tenant: Optional tenant context (for non-platform-admin operations)
            user: Current user performing actions (for audit trail)
        """
        self.db = db
        self.tenant = tenant
        self.user = user

    async def get_tenant_modules(self, tenant_id: UUID) -> List[TenantModule]:
        """
        Get all module configurations for a tenant.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            List of TenantModule instances
        """
        result = await self.db.execute(
            select(TenantModule)
            .where(TenantModule.tenant_id == tenant_id)
            .order_by(TenantModule.module_name)
        )
        return list(result.scalars().all())

    async def get_enabled_modules(self, tenant_id: UUID) -> List[str]:
        """
        Get list of enabled module names for a tenant.

        Falls back to defaults if no configuration exists.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            List of enabled module names
        """
        modules = await self.get_tenant_modules(tenant_id)

        if not modules:
            # No configuration - return defaults based on tenant type
            tenant = await self._get_tenant(tenant_id)
            if tenant:
                return DEFAULT_MODULES_BY_TYPE.get(
                    tenant.tenant_type,
                    DEFAULT_MODULES_BY_TYPE[TenantType.GENERIC.value],
                )
            return DEFAULT_MODULES_BY_TYPE[TenantType.GENERIC.value]

        return [m.module_name for m in modules if m.enabled]

    async def is_module_enabled(self, tenant_id: UUID, module_name: str) -> bool:
        """
        Check if a specific module is enabled for a tenant.

        Args:
            tenant_id: UUID of the tenant
            module_name: Name of the module to check

        Returns:
            True if enabled, False otherwise
        """
        enabled_modules = await self.get_enabled_modules(tenant_id)
        return module_name in enabled_modules

    async def set_module_enabled(
        self,
        tenant_id: UUID,
        module_name: str,
        enabled: bool,
    ) -> TenantModule:
        """
        Enable or disable a module for a tenant.

        Creates the configuration if it doesn't exist.

        Args:
            tenant_id: UUID of the tenant
            module_name: Name of the module
            enabled: Whether to enable or disable

        Returns:
            Updated TenantModule instance
        """
        # Validate module name
        if module_name not in ALL_MODULES:
            raise ValueError(f"Unknown module: {module_name}")

        # Get or create the module configuration
        result = await self.db.execute(
            select(TenantModule)
            .where(TenantModule.tenant_id == tenant_id)
            .where(TenantModule.module_name == module_name)
        )
        tenant_module = result.scalar_one_or_none()

        if tenant_module:
            tenant_module.enabled = enabled
            tenant_module.enabled_by_user_id = self.user.id if self.user else None
        else:
            tenant_module = TenantModule(
                tenant_id=tenant_id,
                module_name=module_name,
                enabled=enabled,
                enabled_by_user_id=self.user.id if self.user else None,
            )
            self.db.add(tenant_module)

        await self.db.commit()
        await self.db.refresh(tenant_module)

        logger.info(
            f"Module '{module_name}' {'enabled' if enabled else 'disabled'} "
            f"for tenant {tenant_id} by user {self.user.id if self.user else 'system'}"
        )
        return tenant_module

    async def reset_to_defaults(self, tenant_id: UUID) -> List[TenantModule]:
        """
        Reset a tenant's module configuration to defaults based on tenant type.

        Deletes existing configuration and creates fresh defaults.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            List of new TenantModule instances
        """
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")

        # Delete existing configurations
        existing = await self.get_tenant_modules(tenant_id)
        for module in existing:
            await self.db.delete(module)

        # Get default modules for this tenant type
        default_modules = DEFAULT_MODULES_BY_TYPE.get(
            tenant.tenant_type,
            DEFAULT_MODULES_BY_TYPE[TenantType.GENERIC.value],
        )

        # Create new configurations for all modules
        new_modules = []
        for module_name in ALL_MODULES:
            tenant_module = TenantModule(
                tenant_id=tenant_id,
                module_name=module_name,
                enabled=module_name in default_modules,
                enabled_by_user_id=self.user.id if self.user else None,
            )
            self.db.add(tenant_module)
            new_modules.append(tenant_module)

        await self.db.commit()

        # Refresh all modules
        for module in new_modules:
            await self.db.refresh(module)

        logger.info(
            f"Reset modules to defaults for tenant {tenant_id} "
            f"(type: {tenant.tenant_type}) by user {self.user.id if self.user else 'system'}"
        )
        return new_modules

    async def initialize_tenant_modules(self, tenant_id: UUID) -> List[TenantModule]:
        """
        Initialize module configuration for a new tenant.

        Called when a tenant is created. Sets up default modules based on tenant type.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            List of created TenantModule instances
        """
        # Check if already initialized
        existing = await self.get_tenant_modules(tenant_id)
        if existing:
            logger.debug(f"Tenant {tenant_id} already has module configuration")
            return existing

        # Create default configuration
        return await self.reset_to_defaults(tenant_id)

    async def get_module_status(
        self,
        tenant_id: UUID,
    ) -> Dict[str, Dict]:
        """
        Get full module status for a tenant including metadata.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Dict mapping module names to their status and metadata
        """
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")

        modules = await self.get_tenant_modules(tenant_id)
        modules_by_name = {m.module_name: m for m in modules}

        # Get defaults for this tenant type
        default_modules = DEFAULT_MODULES_BY_TYPE.get(
            tenant.tenant_type,
            DEFAULT_MODULES_BY_TYPE[TenantType.GENERIC.value],
        )

        result = {}
        for module_name in ALL_MODULES:
            if module_name in modules_by_name:
                m = modules_by_name[module_name]
                result[module_name] = {
                    "enabled": m.enabled,
                    "is_default": m.enabled == (module_name in default_modules),
                    "configured": True,
                    "enabled_by_user_id": str(m.enabled_by_user_id)
                    if m.enabled_by_user_id
                    else None,
                    "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                }
            else:
                # Not configured - use default
                result[module_name] = {
                    "enabled": module_name in default_modules,
                    "is_default": True,
                    "configured": False,
                    "enabled_by_user_id": None,
                    "updated_at": None,
                }

        return result

    async def _get_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()
