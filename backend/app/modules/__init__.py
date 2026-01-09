"""Feature module system for multi-tenant SaaS."""

from app.modules.base import BaseModule, ModuleInfo, RouteInfo
from app.modules.registry import (
    ModuleRegistry,
    get_module_registry,
    reset_module_registry,
)

__all__ = [
    "BaseModule",
    "ModuleInfo",
    "RouteInfo",
    "ModuleRegistry",
    "get_module_registry",
    "reset_module_registry",
]
