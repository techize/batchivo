"""Pattern library module for knitting/crochet tenants."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class PatternModule(BaseModule):
    """
    Knitting pattern library management module.

    Provides functionality for:
    - Storing and organizing knitting/crochet patterns
    - PDF and image upload for patterns
    - External link support (Ravelry, LoveCrafts, etc.)
    - Difficulty level and category classification
    - Full-text search across pattern metadata
    - Suggested materials tracking (yarn weight, needle size)
    """

    name = "patterns"
    display_name = "Pattern Library"
    icon = "book"
    description = "Store and organize knitting and crochet patterns"

    # Available for knitting tenants only
    tenant_types = [TenantType.HAND_KNITTING, TenantType.MACHINE_KNITTING]

    def register_routes(self, router: APIRouter) -> None:
        """Register pattern library management routes."""
        from app.api.v1 import patterns

        # Include all routes from the patterns router
        for route in patterns.router.routes:
            router.routes.append(route)
