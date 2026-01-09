"""SpoolmanDB API endpoints.

Provides access to community-maintained filament database.
Data is synced from https://github.com/Donkie/SpoolmanDB
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.spoolmandb import SpoolmanDBFilament, SpoolmanDBManufacturer
from app.schemas.spoolmandb import (
    SpoolmanDBFilamentListResponse,
    SpoolmanDBFilamentWithManufacturer,
    SpoolmanDBManufacturerListResponse,
    SpoolmanDBManufacturerWithCount,
    SpoolmanDBStatsResponse,
    SpoolmanDBSyncResponse,
)
from app.services.spoolmandb_sync import SpoolmanDBSyncService

router = APIRouter()


@router.get("/stats", response_model=SpoolmanDBStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
) -> SpoolmanDBStatsResponse:
    """
    Get statistics about the SpoolmanDB data.

    Returns counts of manufacturers, filaments, and available materials.
    """
    service = SpoolmanDBSyncService(db)
    stats = await service.get_stats()

    return SpoolmanDBStatsResponse(**stats)


@router.post("/sync", response_model=SpoolmanDBSyncResponse)
async def sync_database(
    db: AsyncSession = Depends(get_db),
) -> SpoolmanDBSyncResponse:
    """
    Trigger a sync from SpoolmanDB.

    Fetches latest filament data from the community database
    and updates local tables.
    """
    try:
        service = SpoolmanDBSyncService(db)
        stats = await service.sync()

        return SpoolmanDBSyncResponse(
            success=True,
            manufacturers_added=stats["manufacturers_added"],
            manufacturers_updated=stats["manufacturers_updated"],
            filaments_added=stats["filaments_added"],
            filaments_updated=stats["filaments_updated"],
            message="Sync completed successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


@router.get("/manufacturers", response_model=SpoolmanDBManufacturerListResponse)
async def list_manufacturers(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search manufacturer name"),
) -> SpoolmanDBManufacturerListResponse:
    """
    List all manufacturers in SpoolmanDB.

    Returns manufacturers with their filament counts.
    """
    # Build query with filament count
    query = (
        select(
            SpoolmanDBManufacturer,
            func.count(SpoolmanDBFilament.id).label("filament_count"),
        )
        .outerjoin(SpoolmanDBFilament)
        .where(SpoolmanDBManufacturer.is_active.is_(True))
        .group_by(SpoolmanDBManufacturer.id)
        .order_by(SpoolmanDBManufacturer.name)
    )

    if search:
        query = query.where(SpoolmanDBManufacturer.name.ilike(f"%{search}%"))

    result = await db.execute(query)
    rows = result.all()

    manufacturers = [
        SpoolmanDBManufacturerWithCount(
            id=row[0].id,
            name=row[0].name,
            is_active=row[0].is_active,
            created_at=row[0].created_at,
            updated_at=row[0].updated_at,
            filament_count=row[1],
        )
        for row in rows
    ]

    return SpoolmanDBManufacturerListResponse(
        manufacturers=manufacturers,
        total=len(manufacturers),
    )


@router.get("/filaments", response_model=SpoolmanDBFilamentListResponse)
async def list_filaments(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    manufacturer_id: Optional[UUID] = Query(None, description="Filter by manufacturer"),
    manufacturer_name: Optional[str] = Query(None, description="Filter by manufacturer name"),
    material: Optional[str] = Query(None, description="Filter by material type (e.g., PLA, PETG)"),
    search: Optional[str] = Query(None, description="Search name or colour"),
    diameter: Optional[float] = Query(None, description="Filter by diameter (1.75 or 2.85)"),
) -> SpoolmanDBFilamentListResponse:
    """
    List filaments from SpoolmanDB with filtering.

    Supports filtering by manufacturer, material type, and search.
    """
    # Base query with manufacturer join
    query = (
        select(SpoolmanDBFilament)
        .join(SpoolmanDBManufacturer)
        .where(SpoolmanDBFilament.is_active.is_(True))
        .options(selectinload(SpoolmanDBFilament.manufacturer))
    )

    # Apply filters
    if manufacturer_id:
        query = query.where(SpoolmanDBFilament.manufacturer_id == manufacturer_id)

    if manufacturer_name:
        query = query.where(SpoolmanDBManufacturer.name.ilike(f"%{manufacturer_name}%"))

    if material:
        query = query.where(SpoolmanDBFilament.material.ilike(f"%{material}%"))

    if diameter:
        query = query.where(SpoolmanDBFilament.diameter == diameter)

    if search:
        query = query.where(
            or_(
                SpoolmanDBFilament.name.ilike(f"%{search}%"),
                SpoolmanDBFilament.color_name.ilike(f"%{search}%"),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination and ordering
    query = (
        query.order_by(
            SpoolmanDBManufacturer.name, SpoolmanDBFilament.material, SpoolmanDBFilament.name
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    filaments = result.scalars().all()

    # Convert to response
    filament_responses = [
        SpoolmanDBFilamentWithManufacturer(
            id=f.id,
            external_id=f.external_id,
            manufacturer_id=f.manufacturer_id,
            manufacturer_name=f.manufacturer.name,
            name=f.name,
            material=f.material,
            density=f.density,
            diameter=f.diameter,
            weight=f.weight,
            spool_weight=f.spool_weight,
            spool_type=f.spool_type,
            color_name=f.color_name,
            color_hex=f.color_hex,
            extruder_temp=f.extruder_temp,
            bed_temp=f.bed_temp,
            finish=f.finish,
            translucent=f.translucent,
            glow=f.glow,
            pattern=f.pattern,
            multi_color_direction=f.multi_color_direction,
            color_hexes=f.color_hexes,
            is_active=f.is_active,
            created_at=f.created_at,
            updated_at=f.updated_at,
        )
        for f in filaments
    ]

    return SpoolmanDBFilamentListResponse(
        filaments=filament_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/filaments/{filament_id}", response_model=SpoolmanDBFilamentWithManufacturer)
async def get_filament(
    filament_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SpoolmanDBFilamentWithManufacturer:
    """
    Get a specific filament by ID.
    """
    query = (
        select(SpoolmanDBFilament)
        .where(SpoolmanDBFilament.id == filament_id)
        .options(selectinload(SpoolmanDBFilament.manufacturer))
    )

    result = await db.execute(query)
    filament = result.scalar_one_or_none()

    if not filament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filament not found",
        )

    return SpoolmanDBFilamentWithManufacturer(
        id=filament.id,
        external_id=filament.external_id,
        manufacturer_id=filament.manufacturer_id,
        manufacturer_name=filament.manufacturer.name,
        name=filament.name,
        material=filament.material,
        density=filament.density,
        diameter=filament.diameter,
        weight=filament.weight,
        spool_weight=filament.spool_weight,
        spool_type=filament.spool_type,
        color_name=filament.color_name,
        color_hex=filament.color_hex,
        extruder_temp=filament.extruder_temp,
        bed_temp=filament.bed_temp,
        finish=filament.finish,
        translucent=filament.translucent,
        glow=filament.glow,
        pattern=filament.pattern,
        multi_color_direction=filament.multi_color_direction,
        color_hexes=filament.color_hexes,
        is_active=filament.is_active,
        created_at=filament.created_at,
        updated_at=filament.updated_at,
    )


@router.get("/materials")
async def list_materials(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get list of unique material types from SpoolmanDB filaments.
    """
    query = (
        select(
            SpoolmanDBFilament.material,
            func.count(SpoolmanDBFilament.id).label("count"),
        )
        .where(SpoolmanDBFilament.is_active.is_(True))
        .group_by(SpoolmanDBFilament.material)
        .order_by(SpoolmanDBFilament.material)
    )

    result = await db.execute(query)
    rows = result.all()

    materials = [{"material": row[0], "count": row[1]} for row in rows]

    return {
        "materials": materials,
        "total": len(materials),
    }
