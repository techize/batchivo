"""Needle inventory module for knitting/crochet tenants."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class NeedleModule(BaseModule):
    """
    Needle and crochet hook inventory management module.

    Provides functionality for:
    - Tracking knitting needles (straight, circular, DPN, interchangeable)
    - Tracking crochet hooks (inline, tapered, ergonomic, Tunisian)
    - Size conversion (metric, US, UK)
    - Material tracking (bamboo, metal, wood, etc.)
    - Interchangeable set management
    - Size gap analysis
    """

    name = "needles"
    display_name = "Needles & Hooks"
    icon = "needle"
    description = "Track and manage knitting needles and crochet hooks"

    # Available for knitting tenants only
    tenant_types = [TenantType.HAND_KNITTING, TenantType.MACHINE_KNITTING]

    def register_routes(self, router: APIRouter) -> None:
        """Register needle inventory management routes."""
        from app.api.v1 import needle

        # Include all routes from the needle router
        for route in needle.router.routes:
            router.routes.append(route)
