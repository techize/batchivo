"""Printers module for 3D printer management."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class PrintersModule(BaseModule):
    """
    3D Printer management module.

    Provides functionality for:
    - Printer registration and status tracking
    - Bambu Lab cloud integration
    - Print job assignment
    - Maintenance scheduling
    """

    name = "printers"
    display_name = "3D Printers"
    icon = "printer"
    description = "Manage 3D printers and print jobs"

    # Only for 3D printing tenants
    tenant_types = [TenantType.THREE_D_PRINT]

    def register_routes(self, router: APIRouter) -> None:
        """Register printer management routes."""
        from app.api.v1 import printers, printer_bambu

        # Include all routes from the printers routers
        for route in printers.router.routes:
            router.routes.append(route)

        # Include Bambu-specific routes under /bambu prefix
        bambu_router = APIRouter(prefix="/bambu", tags=["printers-bambu"])
        for route in printer_bambu.router.routes:
            bambu_router.routes.append(route)
        router.include_router(bambu_router)
