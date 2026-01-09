"""Base module class for the modular feature system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from fastapi import APIRouter

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.schemas.tenant_settings import TenantType


@dataclass
class RouteInfo:
    """Information about a module route for discovery."""

    path: str
    method: str
    description: str
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """Public information about a module for the API."""

    name: str
    display_name: str
    description: str
    icon: str
    routes: List[RouteInfo] = field(default_factory=list)
    enabled: bool = True


class BaseModule(ABC):
    """
    Abstract base class for feature modules.

    Modules encapsulate related functionality (routes, services, models)
    that can be enabled/disabled based on tenant type.

    Example usage:
        class SpoolsModule(BaseModule):
            name = "spools"
            display_name = "Filament Spools"
            icon = "cylinder"
            description = "Track and manage 3D printing filament inventory"
            tenant_types = [TenantType.THREE_D_PRINT, TenantType.GENERIC]

            def register_routes(self, router: APIRouter) -> None:
                from app.api.v1 import spools
                router.include_router(spools.router, prefix="/spools", tags=["spools"])
    """

    # Module metadata (must be set by subclasses)
    name: str = ""
    display_name: str = ""
    icon: str = "puzzle"  # Default icon
    description: str = ""

    # List of tenant types this module supports
    # Empty list means available to all tenant types
    tenant_types: List["TenantType"] = []

    # Module dependencies (other module names that must be enabled)
    dependencies: List[str] = []

    # Whether this module is a core module (always enabled)
    is_core: bool = False

    def __init__(self):
        """Initialize the module."""
        self._router: Optional[APIRouter] = None
        self._routes: List[RouteInfo] = []

    @property
    def router(self) -> APIRouter:
        """Get or create the module's router."""
        if self._router is None:
            self._router = APIRouter()
            self.register_routes(self._router)
            self._extract_route_info()
        return self._router

    @abstractmethod
    def register_routes(self, router: APIRouter) -> None:
        """
        Register all routes for this module.

        Args:
            router: FastAPI router to add routes to
        """
        pass

    def is_enabled_for_tenant(self, tenant: "Tenant") -> bool:
        """
        Check if this module is enabled for the given tenant.

        Args:
            tenant: The tenant to check

        Returns:
            True if the module is enabled for this tenant
        """
        from app.schemas.tenant_settings import TenantType

        # Core modules are always enabled
        if self.is_core:
            return True

        # Empty tenant_types means available to all
        if not self.tenant_types:
            return True

        # Check if tenant type matches
        tenant_type = TenantType(tenant.tenant_type)
        return tenant_type in self.tenant_types

    def get_info(self, enabled: bool = True) -> ModuleInfo:
        """
        Get public information about this module.

        Args:
            enabled: Whether the module is enabled for the current tenant

        Returns:
            Module information for API response
        """
        # Ensure routes are extracted
        if not self._routes and self._router is None:
            _ = self.router  # Trigger route registration

        return ModuleInfo(
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            routes=self._routes,
            enabled=enabled,
        )

    def _extract_route_info(self) -> None:
        """Extract route information from the registered router."""
        if self._router is None:
            return

        self._routes = []
        for route in self._router.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    if method in ("HEAD", "OPTIONS"):
                        continue
                    self._routes.append(
                        RouteInfo(
                            path=route.path,
                            method=method,
                            description=getattr(route, "description", "") or "",
                            summary=getattr(route, "summary", None),
                            tags=list(getattr(route, "tags", [])),
                        )
                    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"
