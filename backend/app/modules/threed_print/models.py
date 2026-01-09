"""3D Models module for print job management."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class ModelsModule(BaseModule):
    """
    3D Model management module.

    Provides functionality for:
    - Storing and organizing 3D model files
    - Tracking print settings per model
    - Designer attribution and royalties
    - Model-to-product linking
    """

    name = "models"
    display_name = "3D Models"
    icon = "cube"
    description = "Manage 3D model files and print configurations"

    # Only for 3D printing tenants
    tenant_types = [TenantType.THREE_D_PRINT]

    def register_routes(self, router: APIRouter) -> None:
        """Register 3D model management routes."""
        from app.api.v1 import models

        # Include all routes from the existing models router
        for route in models.router.routes:
            router.routes.append(route)
