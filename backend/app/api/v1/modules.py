"""Module discovery and information API endpoints."""

from typing import Annotated, List, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant
from app.database import get_db
from app.models.tenant import Tenant
from app.modules import get_module_registry
from app.services.tenant_module_service import TenantModuleService

router = APIRouter()


# Module status matching frontend expectations
ModuleStatus = Literal["active", "disabled", "coming_soon"]

# Tenant type matching frontend expectations
TenantType = Literal["three_d_print", "hand_knitting", "machine_knitting", "generic"]


class NavigationRouteResponse(BaseModel):
    """Navigation route for frontend sidebar."""

    path: str = Field(..., description="Route path for navigation")
    label: str = Field(..., description="Display label for navigation")
    icon: str | None = Field(None, description="Optional icon override")
    exact: bool = Field(False, description="Whether path must match exactly")
    badge: int | None = Field(None, description="Optional badge count")


class ModuleInfoResponse(BaseModel):
    """Information about a feature module."""

    name: str = Field(..., description="Module identifier")
    display_name: str = Field(..., description="Human-readable module name")
    description: str = Field(..., description="Module description")
    icon: str = Field(..., description="Icon identifier for UI")
    status: ModuleStatus = Field(..., description="Module status: active, disabled, or coming_soon")
    order: int = Field(..., description="Display order in navigation")
    routes: List[NavigationRouteResponse] = Field(
        default_factory=list, description="Navigation routes for this module"
    )


class ModulesResponse(BaseModel):
    """Response containing available modules."""

    tenant_type: TenantType = Field(..., description="Current tenant type")
    modules: List[ModuleInfoResponse] = Field(..., description="List of modules")


# Type alias for authenticated tenant
CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]


# Navigation routes for each module (frontend sidebar)
# These define the actual navigation items shown in the UI
MODULE_NAVIGATION: dict[str, list[dict]] = {
    "products": [
        {"path": "/products", "label": "Products", "icon": "package", "exact": False},
    ],
    "models": [
        {"path": "/models", "label": "Models", "icon": "layers", "exact": False},
    ],
    "designers": [
        {"path": "/designers", "label": "Designers", "icon": "brush", "exact": False},
    ],
    "categories": [
        {"path": "/categories", "label": "Categories", "icon": "folder-open", "exact": False},
    ],
    "production": [
        {"path": "/production-runs", "label": "Runs", "icon": "play", "exact": False},
    ],
    "spools": [
        {"path": "/inventory", "label": "Inventory", "icon": "box", "exact": True},
        {"path": "/filaments", "label": "Filaments", "icon": "box", "exact": False},
    ],
    "printers": [
        {"path": "/printers", "label": "Printers", "icon": "printer", "exact": False},
    ],
    "consumables": [
        {"path": "/consumables", "label": "Consumables", "icon": "wrench", "exact": False},
    ],
    "sales_channels": [
        {"path": "/sales-channels", "label": "Channels", "icon": "store", "exact": False},
    ],
    "orders": [
        {"path": "/orders", "label": "Orders", "icon": "shopping-bag", "exact": False},
    ],
}

# Module display order
MODULE_ORDER: dict[str, int] = {
    "products": 1,
    "models": 2,
    "designers": 3,
    "categories": 4,
    "production": 5,
    "spools": 6,
    "printers": 7,
    "consumables": 8,
    "sales_channels": 9,
    "orders": 10,
}


@router.get(
    "",
    response_model=ModulesResponse,
    summary="List available modules",
    description="Get all feature modules available for the current tenant.",
)
async def list_modules(
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    include_disabled: bool = Query(
        False, description="Include modules not enabled for this tenant"
    ),
) -> ModulesResponse:
    """
    List available feature modules for the current tenant.

    Returns modules filtered by tenant_modules table configuration.
    Falls back to tenant_type defaults if no configuration exists.
    Use include_disabled=true to see all modules regardless of status.
    """
    registry = get_module_registry()

    # Initialize modules if not already done
    if not registry.get_all_modules():
        registry.discover_modules()

    # Get enabled modules from tenant_modules table (with fallback to defaults)
    module_service = TenantModuleService(db=db, tenant=tenant)
    enabled_module_names = await module_service.get_enabled_modules(tenant.id)

    # Get tenant type from model
    tenant_type: TenantType = tenant.tenant_type or "three_d_print"

    # Build module list from registry
    modules = []
    for module in registry.get_all_modules():
        enabled = module.name in enabled_module_names

        # Skip disabled modules unless include_disabled is True
        if not enabled and not include_disabled:
            continue

        info = module.get_info(enabled=enabled)
        modules.append(
            ModuleInfoResponse(
                name=info.name,
                display_name=info.display_name,
                description=info.description,
                icon=info.icon,
                status="active" if enabled else "disabled",
                order=MODULE_ORDER.get(info.name, 99),
                routes=[
                    NavigationRouteResponse(
                        path=nav["path"],
                        label=nav["label"],
                        icon=nav.get("icon"),
                        exact=nav.get("exact", False),
                        badge=nav.get("badge"),
                    )
                    for nav in MODULE_NAVIGATION.get(info.name, [])
                ],
            )
        )

    # Sort by order
    modules.sort(key=lambda m: m.order)

    return ModulesResponse(
        tenant_type=tenant_type,
        modules=modules,
    )


@router.get(
    "/{module_name}",
    response_model=ModuleInfoResponse,
    summary="Get module details",
    description="Get detailed information about a specific module.",
)
async def get_module(
    module_name: str,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ModuleInfoResponse:
    """
    Get detailed information about a specific module.

    Returns module info including whether it's enabled for the current tenant
    based on tenant_modules configuration.
    """
    from fastapi import HTTPException, status

    registry = get_module_registry()

    # Initialize modules if not already done
    if not registry.get_all_modules():
        registry.discover_modules()

    module = registry.get_module(module_name)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_name}' not found",
        )

    # Check enabled status from tenant_modules table
    module_service = TenantModuleService(db=db, tenant=tenant)
    enabled = await module_service.is_module_enabled(tenant.id, module_name)
    info = module.get_info(enabled=enabled)

    return ModuleInfoResponse(
        name=info.name,
        display_name=info.display_name,
        description=info.description,
        icon=info.icon,
        status="active" if enabled else "disabled",
        order=MODULE_ORDER.get(info.name, 99),
        routes=[
            NavigationRouteResponse(
                path=nav["path"],
                label=nav["label"],
                icon=nav.get("icon"),
                exact=nav.get("exact", False),
                badge=nav.get("badge"),
            )
            for nav in MODULE_NAVIGATION.get(info.name, [])
        ],
    )
