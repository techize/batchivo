"""Sales Channels module for all tenant types."""

from fastapi import APIRouter

from app.modules.base import BaseModule


class SalesChannelsModule(BaseModule):
    """
    Sales channels management module.

    Provides functionality for:
    - Managing sales platforms (Etsy, Amazon, website, etc.)
    - Channel-specific pricing and inventory
    - Order sync from external channels
    """

    name = "sales_channels"
    display_name = "Sales Channels"
    icon = "store"
    description = "Manage your sales channels and integrations"

    # Available for all tenant types (core module)
    tenant_types = []  # Empty = all tenant types
    is_core = True

    def register_routes(self, router: APIRouter) -> None:
        """Register sales channel management routes."""
        from app.api.v1 import sales_channels

        # Include all routes from the existing sales_channels router
        for route in sales_channels.router.routes:
            router.routes.append(route)
