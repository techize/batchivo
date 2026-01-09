"""Project tracking module for knitting/crochet tenants."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class ProjectModule(BaseModule):
    """
    Knitting project tracking management module.

    Provides functionality for:
    - Project lifecycle management (queued → in progress → finished/frogged)
    - Time tracking with per-session entries
    - Yarn and needle usage tracking
    - Cost calculation (materials + labor)
    - Product linking for items made for sale
    """

    name = "projects"
    display_name = "Project Tracking"
    icon = "clipboard"
    description = "Track knitting and crochet projects with time and materials"

    # Available for knitting tenants only
    tenant_types = [TenantType.HAND_KNITTING, TenantType.MACHINE_KNITTING]

    def register_routes(self, router: APIRouter) -> None:
        """Register project tracking management routes."""
        from app.api.v1 import projects

        # Include all routes from the projects router
        for route in projects.router.routes:
            router.routes.append(route)
