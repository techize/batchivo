"""Module registry for managing feature modules."""

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from fastapi import APIRouter

from app.modules.base import BaseModule, ModuleInfo

if TYPE_CHECKING:
    from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """
    Singleton registry for managing feature modules.

    The registry handles:
    - Module registration and discovery
    - Tenant-specific module filtering
    - Route registration with FastAPI
    """

    _instance: Optional["ModuleRegistry"] = None
    _modules: Dict[str, BaseModule]

    def __new__(cls) -> "ModuleRegistry":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._modules = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, module_class: Type[BaseModule]) -> BaseModule:
        """
        Register a module with the registry.

        Args:
            module_class: The module class to register

        Returns:
            The instantiated module

        Raises:
            ValueError: If module with same name already registered
        """
        module = module_class()

        if module.name in self._modules:
            raise ValueError(f"Module '{module.name}' is already registered")

        self._modules[module.name] = module
        logger.info(f"Registered module: {module.name} ({module.display_name})")

        return module

    def register_module(self, module: BaseModule) -> None:
        """
        Register an already-instantiated module.

        Args:
            module: The module instance to register

        Raises:
            ValueError: If module with same name already registered
        """
        if module.name in self._modules:
            raise ValueError(f"Module '{module.name}' is already registered")

        self._modules[module.name] = module
        logger.info(f"Registered module: {module.name} ({module.display_name})")

    def get_module(self, name: str) -> Optional[BaseModule]:
        """
        Get a module by name.

        Args:
            name: The module name

        Returns:
            The module or None if not found
        """
        return self._modules.get(name)

    def get_all_modules(self) -> List[BaseModule]:
        """
        Get all registered modules.

        Returns:
            List of all registered modules
        """
        return list(self._modules.values())

    def get_modules_for_tenant(self, tenant: "Tenant") -> List[BaseModule]:
        """
        Get modules enabled for a specific tenant.

        Args:
            tenant: The tenant to check

        Returns:
            List of modules enabled for this tenant
        """
        return [module for module in self._modules.values() if module.is_enabled_for_tenant(tenant)]

    def get_module_info_for_tenant(
        self, tenant: "Tenant", include_disabled: bool = False
    ) -> List[ModuleInfo]:
        """
        Get module information for a tenant (for API response).

        Args:
            tenant: The tenant to check
            include_disabled: Whether to include disabled modules

        Returns:
            List of module info dictionaries
        """
        result = []

        for module in self._modules.values():
            enabled = module.is_enabled_for_tenant(tenant)

            if enabled or include_disabled:
                result.append(module.get_info(enabled=enabled))

        return result

    def discover_modules(self) -> int:
        """
        Auto-discover and register modules from the modules package.

        Returns:
            Number of modules discovered
        """
        # Import module packages to trigger registration
        from app.modules import threed_print, knitting

        # Register modules from each package
        count = 0

        # 3D printing modules
        for module in threed_print.get_modules():
            try:
                self.register_module(module)
                count += 1
            except ValueError:
                # Already registered, skip
                pass

        # Knitting modules
        for module in knitting.get_modules():
            try:
                self.register_module(module)
                count += 1
            except ValueError:
                # Already registered, skip
                pass

        logger.info(f"Discovered {count} new modules")
        return count

    def register_routes(self, app_router: APIRouter, prefix: str = "") -> None:
        """
        Register all module routes with the application router.

        Args:
            app_router: The main application router
            prefix: URL prefix for all module routes
        """
        for module in self._modules.values():
            module_prefix = f"{prefix}/{module.name}" if prefix else f"/{module.name}"
            app_router.include_router(
                module.router,
                prefix=module_prefix,
                tags=[module.name],
            )
            logger.info(f"Registered routes for module: {module.name} at {module_prefix}")

    def clear(self) -> None:
        """Clear all registered modules (for testing)."""
        self._modules.clear()
        self._initialized = False
        logger.info("Module registry cleared")


# Global registry instance
_registry: Optional[ModuleRegistry] = None


def get_module_registry() -> ModuleRegistry:
    """
    Get the global module registry instance.

    Returns:
        The module registry singleton
    """
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry


def reset_module_registry() -> None:
    """Reset the global module registry (for testing)."""
    global _registry
    if _registry is not None:
        _registry.clear()
    _registry = None
