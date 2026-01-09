"""SKU generation API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant
from app.database import get_db
from app.services.sku_generator import EntityType, SKUGeneratorService

router = APIRouter()


class NextSKUResponse(BaseModel):
    """Response for next SKU generation."""

    entity_type: str
    next_sku: str
    highest_existing: int


class SKUAvailabilityResponse(BaseModel):
    """Response for SKU availability check."""

    sku: str
    available: bool


@router.get("/next/{entity_type}", response_model=NextSKUResponse)
async def get_next_sku(
    entity_type: str,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> NextSKUResponse:
    """
    Get the next available SKU for an entity type.

    Entity types:
    - PROD: Products
    - MOD: Models (3D printed parts)
    - COM: Consumables
    - FIL: Filament spools

    Returns the next sequential SKU (e.g., if PROD-042 exists, returns PROD-043).
    """
    # Validate entity type
    try:
        entity = EntityType(entity_type.upper())
    except ValueError:
        valid_types = [e.value for e in EntityType if e != EntityType.RUN]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity type '{entity_type}'. Valid types: {', '.join(valid_types)}",
        )

    # Don't support RUN via this endpoint (has different format)
    if entity == EntityType.RUN:
        raise HTTPException(
            status_code=400,
            detail="Production run numbers are auto-generated with date format. Use the production runs API.",
        )

    highest = await SKUGeneratorService.get_highest_sku_number(db, str(tenant.id), entity)
    next_sku = await SKUGeneratorService.generate_next_sku(db, str(tenant.id), entity)

    return NextSKUResponse(
        entity_type=entity.value,
        next_sku=next_sku,
        highest_existing=highest,
    )


@router.get("/check/{entity_type}/{sku}", response_model=SKUAvailabilityResponse)
async def check_sku_availability(
    entity_type: str,
    sku: str,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> SKUAvailabilityResponse:
    """
    Check if a specific SKU is available for use.

    Useful for validating user-entered SKUs before creating entities.
    """
    # Validate entity type
    try:
        entity = EntityType(entity_type.upper())
    except ValueError:
        valid_types = [e.value for e in EntityType if e != EntityType.RUN]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity type '{entity_type}'. Valid types: {', '.join(valid_types)}",
        )

    if entity == EntityType.RUN:
        raise HTTPException(
            status_code=400,
            detail="Production run numbers are auto-generated. Use the production runs API.",
        )

    available = await SKUGeneratorService.is_sku_available(db, str(tenant.id), entity, sku)

    return SKUAvailabilityResponse(sku=sku, available=available)
