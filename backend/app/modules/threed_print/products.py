"""Products module for all tenant types."""

from fastapi import APIRouter

from app.modules.base import BaseModule


class ProductsModule(BaseModule):
    """
    Product catalog management module.

    Provides functionality for:
    - Creating and managing sellable products
    - Product variants and pricing
    - Product images and descriptions
    - Linking products to models (for 3D print tenants)
    """

    name = "products"
    display_name = "Products"
    icon = "package"
    description = "Manage your product catalog"

    # Available for all tenant types (core module)
    tenant_types = []  # Empty = all tenant types
    is_core = True

    def register_routes(self, router: APIRouter) -> None:
        """Register product management routes."""
        from app.api.v1 import products

        # Include all routes from the existing products router
        for route in products.router.routes:
            router.routes.append(route)
