"""Designers module for 3D print tenants."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class DesignersModule(BaseModule):
    """
    Designer management module.

    Provides functionality for:
    - Tracking model designers/creators
    - Designer attribution on products
    - Designer profiles and links
    """

    name = "designers"
    display_name = "Designers"
    icon = "brush"
    description = "Manage 3D model designers"

    # Only for 3D print tenants
    tenant_types = [TenantType.THREE_D_PRINT, TenantType.GENERIC]

    def register_routes(self, router: APIRouter) -> None:
        """Register designer management routes."""
        from app.api.v1 import designers

        # Include all routes from the existing designers router
        for route in designers.router.routes:
            router.routes.append(route)
