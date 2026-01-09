"""3D Printing feature modules."""

from typing import List

from app.modules.base import BaseModule
from app.modules.threed_print.spools import SpoolsModule
from app.modules.threed_print.models import ModelsModule
from app.modules.threed_print.printers import PrintersModule
from app.modules.threed_print.production import ProductionModule
from app.modules.threed_print.products import ProductsModule
from app.modules.threed_print.orders import OrdersModule
from app.modules.threed_print.categories import CategoriesModule
from app.modules.threed_print.designers import DesignersModule
from app.modules.threed_print.consumables import ConsumablesModule
from app.modules.threed_print.sales_channels import SalesChannelsModule


def get_modules() -> List[BaseModule]:
    """
    Get all 3D printing modules.

    Returns:
        List of module instances
    """
    return [
        SpoolsModule(),
        ModelsModule(),
        PrintersModule(),
        ProductionModule(),
        ProductsModule(),
        OrdersModule(),
        CategoriesModule(),
        DesignersModule(),
        ConsumablesModule(),
        SalesChannelsModule(),
    ]


__all__ = [
    "SpoolsModule",
    "ModelsModule",
    "PrintersModule",
    "ProductionModule",
    "ProductsModule",
    "OrdersModule",
    "CategoriesModule",
    "DesignersModule",
    "ConsumablesModule",
    "SalesChannelsModule",
    "get_modules",
]
