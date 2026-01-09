"""Categories module for all tenant types."""

from fastapi import APIRouter

from app.modules.base import BaseModule


class CategoriesModule(BaseModule):
    """
    Category management module.

    Provides functionality for:
    - Product categorization
    - Hierarchical category structures
    - Category-based navigation
    """

    name = "categories"
    display_name = "Categories"
    icon = "folder-open"
    description = "Organize products with categories"

    # Available for all tenant types (core module)
    tenant_types = []  # Empty = all tenant types
    is_core = True

    def register_routes(self, router: APIRouter) -> None:
        """Register category management routes."""
        from app.api.v1 import categories

        # Include all routes from the existing categories router
        for route in categories.router.routes:
            router.routes.append(route)
