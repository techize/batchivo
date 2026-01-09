"""Yarn inventory module for knitting/crochet tenants."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class YarnModule(BaseModule):
    """
    Yarn inventory management module.

    Provides functionality for:
    - Tracking yarn skeins (brand, color, weight class, fiber content)
    - Yardage and usage tracking
    - Dye lot management
    - Cost calculations per yard
    - Low stock alerts
    """

    name = "yarn"
    display_name = "Yarn Inventory"
    icon = "circle"  # Ball of yarn
    description = "Track and manage yarn inventory for knitting and crochet"

    # Available for knitting tenants only
    tenant_types = [TenantType.HAND_KNITTING, TenantType.MACHINE_KNITTING]

    def register_routes(self, router: APIRouter) -> None:
        """Register yarn inventory management routes."""
        from app.api.v1 import yarn

        # Include all routes from the yarn router
        for route in yarn.router.routes:
            router.routes.append(route)
