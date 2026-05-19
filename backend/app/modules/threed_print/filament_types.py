"""FilamentType module for 3D print tenants."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class FilamentTypesModule(BaseModule):
    """
    FilamentType management module.

    Provides functionality for:
    - Defining shared filament type definitions (brand + colour + material)
    - Deduplication key for physical spool records
    - Sample benchy tracking per filament type
    """

    name = "filament_types"
    display_name = "Filament Types"
    icon = "layers"
    description = "Manage filament type definitions for 3D printing"

    # Available for 3D print and generic tenants
    tenant_types = [TenantType.THREE_D_PRINT, TenantType.GENERIC]

    def register_routes(self, router: APIRouter) -> None:
        """Register filament type management routes."""
        from app.api.v1 import filament_types

        for route in filament_types.router.routes:
            router.routes.append(route)
