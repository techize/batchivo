"""Orders module for all tenant types."""

from fastapi import APIRouter

from app.modules.base import BaseModule


class OrdersModule(BaseModule):
    """
    Order management module.

    Provides functionality for:
    - Order processing and status tracking
    - Customer order history
    - Integration with sales channels
    - Order fulfillment workflows
    """

    name = "orders"
    display_name = "Orders"
    icon = "shopping-bag"
    description = "Manage customer orders"

    # Available for all tenant types (core module)
    tenant_types = []  # Empty = all tenant types
    is_core = True

    def register_routes(self, router: APIRouter) -> None:
        """Register order management routes."""
        from app.api.v1 import orders

        # Include all routes from the existing orders router
        for route in orders.router.routes:
            router.routes.append(route)
