"""Spools/Filament inventory module for 3D printing."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class SpoolsModule(BaseModule):
    """
    Filament spool inventory management module.

    Provides functionality for:
    - Tracking filament spools (brand, color, material, weight)
    - Usage tracking and weight updates
    - Low stock alerts
    - Integration with SpoolmanDB
    """

    name = "spools"
    display_name = "Filament Inventory"
    icon = "cylinder"
    description = "Track and manage 3D printing filament spools"

    # Available for 3D printing and generic tenants
    tenant_types = [TenantType.THREE_D_PRINT, TenantType.GENERIC]

    def register_routes(self, router: APIRouter) -> None:
        """Register spool management routes."""
        from app.api.v1 import spools

        # Include all routes from the existing spools router
        for route in spools.router.routes:
            router.routes.append(route)
