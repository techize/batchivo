"""Production runs module for batch manufacturing."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class ProductionModule(BaseModule):
    """
    Production run management module.

    Provides functionality for:
    - Batch production tracking
    - Filament usage per run
    - Quality control logging
    - Production analytics
    """

    name = "production"
    display_name = "Production Runs"
    icon = "factory"
    description = "Track batch production runs and manufacturing"

    # Only for 3D printing tenants
    tenant_types = [TenantType.THREE_D_PRINT]

    def register_routes(self, router: APIRouter) -> None:
        """Register production run management routes."""
        from app.api.v1 import production_runs

        # Include all routes from the production_runs router
        for route in production_runs.router.routes:
            router.routes.append(route)
