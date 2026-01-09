"""Consumables module for 3D print tenants."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class ConsumablesModule(BaseModule):
    """
    Consumables management module.

    Provides functionality for:
    - Tracking consumable items (nozzles, build plates, etc.)
    - Usage tracking and replacement schedules
    - Cost tracking for consumables
    """

    name = "consumables"
    display_name = "Consumables"
    icon = "wrench"
    description = "Track printer consumables and maintenance items"

    # Only for 3D print tenants
    tenant_types = [TenantType.THREE_D_PRINT, TenantType.GENERIC]

    def register_routes(self, router: APIRouter) -> None:
        """Register consumable management routes."""
        from app.api.v1 import consumables

        # Include all routes from the existing consumables router
        for route in consumables.router.routes:
            router.routes.append(route)
