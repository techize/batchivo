"""Spool inventory API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser, TenantDB
from app.models.filament_type import FilamentType
from app.models.material import MaterialType
from app.models.spool import Spool
from app.schemas.material import MaterialTypeCreate, MaterialTypeResponse
from app.schemas.spool import SpoolCreate, SpoolListResponse, SpoolResponse, SpoolUpdate

router = APIRouter()


# Helper function to convert Spool model to response schema
def spool_to_response(spool: Spool) -> dict:
    """Convert Spool model to response dict."""
    return {
        **spool.__dict__,
        "remaining_weight": spool.remaining_weight,
        "remaining_percentage": spool.remaining_percentage,
        "filament_type": spool.filament_type,
    }


async def ensure_material_type_exists(db: AsyncSession, material_type_id: UUID) -> None:
    """Validate that a material type exists before writing a spool FK."""
    result = await db.execute(select(MaterialType.id).where(MaterialType.id == material_type_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid foreign key reference - check material_type_id exists.",
        )


async def ensure_filament_type_exists(db: AsyncSession, filament_type_id: UUID) -> None:
    """Validate that a filament type exists before writing a spool FK."""
    result = await db.execute(select(FilamentType.id).where(FilamentType.id == filament_type_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid foreign key reference - check filament_type_id exists.",
        )


@router.post("", response_model=SpoolResponse, status_code=status.HTTP_201_CREATED)
async def create_spool(
    spool_data: SpoolCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> SpoolResponse:
    """
    Create a new filament spool.

    Requires authentication.
    Spool will be associated with current tenant.
    """
    # Create spool instance (filament_type_id validated by IntegrityError on commit)
    spool = Spool(
        tenant_id=tenant.id,
        **spool_data.model_dump(),
    )

    db.add(spool)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid foreign key reference - check filament_type_id exists.",
        )
    await db.refresh(spool)

    return SpoolResponse(**spool_to_response(spool))


@router.get("", response_model=SpoolListResponse)
async def list_spools(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by spool_id, brand, or color"),
    material_type_id: Optional[UUID] = Query(None, description="Filter by material type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    low_stock_only: bool = Query(False, description="Show only low stock spools (<20%)"),
) -> SpoolListResponse:
    """
    List all spools for current tenant with pagination and filtering.

    Supports:
    - Pagination (page, page_size)
    - Search (spool_id, brand, color)
    - Filter by material type (via FilamentType)
    - Filter by active status
    - Filter by low stock
    """
    # Base query for current tenant — join FilamentType for search/filter
    query = select(Spool).join(Spool.filament_type).where(Spool.tenant_id == tenant.id)

    # Apply filters
    if search:
        search_filter = or_(
            Spool.spool_id.ilike(f"%{search}%"),
            FilamentType.brand.ilike(f"%{search}%"),
            FilamentType.color.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if material_type_id:
        query = query.where(FilamentType.material_type_id == material_type_id)

    if is_active is not None:
        query = query.where(Spool.is_active == is_active)

    # Count total (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Spool.created_at.desc())

    # Execute query
    result = await db.execute(query)
    spools = result.scalars().all()

    # Convert to response format
    spool_responses = []
    for spool in spools:
        # Apply low stock filter if requested
        if low_stock_only and not spool.is_low_stock():
            continue
        spool_responses.append(SpoolResponse(**spool_to_response(spool)))

    return SpoolListResponse(
        total=total,
        spools=spool_responses,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# Material Types Endpoints
# ============================================================================
# NOTE: These must be defined BEFORE /{spool_id} to avoid route conflicts


@router.get("/material-types", response_model=list[MaterialTypeResponse])
async def list_material_types(
    user: CurrentUser,
    db: TenantDB,
) -> list[MaterialTypeResponse]:
    """
    List all available material types.

    Material types are global (not tenant-scoped).
    Returns all active material types sorted by code.
    """
    result = await db.execute(
        select(MaterialType).where(MaterialType.is_active.is_(True)).order_by(MaterialType.code)
    )
    materials = result.scalars().all()

    return [
        MaterialTypeResponse(
            id=str(mat.id),
            code=mat.code,
            name=mat.name,
            description=mat.description,
            typical_density=mat.typical_density,
            typical_cost_per_kg=mat.typical_cost_per_kg,
            min_temp=mat.min_temp,
            max_temp=mat.max_temp,
            bed_temp=mat.bed_temp,
            is_active=mat.is_active,
        )
        for mat in materials
    ]


@router.post(
    "/material-types", response_model=MaterialTypeResponse, status_code=status.HTTP_201_CREATED
)
async def create_material_type(
    material_data: MaterialTypeCreate,
    user: CurrentUser,
    db: TenantDB,
) -> MaterialTypeResponse:
    """
    Create a new material type.

    Requires authentication.
    Material types are global and can be used by all tenants.
    """
    # Check if code already exists
    result = await db.execute(
        select(MaterialType).where(MaterialType.code == material_data.code.upper())
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Material type with code '{material_data.code}' already exists",
        )

    # Create material type
    material = MaterialType(
        code=material_data.code.upper(),
        name=material_data.name,
        description=material_data.description,
        typical_density=material_data.typical_density,
        typical_cost_per_kg=material_data.typical_cost_per_kg,
        min_temp=material_data.min_temp,
        max_temp=material_data.max_temp,
        bed_temp=material_data.bed_temp,
        is_active=material_data.is_active,
    )

    db.add(material)
    await db.commit()
    await db.refresh(material)

    return MaterialTypeResponse(
        id=str(material.id),
        code=material.code,
        name=material.name,
        description=material.description,
        typical_density=material.typical_density,
        typical_cost_per_kg=material.typical_cost_per_kg,
        min_temp=material.min_temp,
        max_temp=material.max_temp,
        bed_temp=material.bed_temp,
        is_active=material.is_active,
    )


# ============================================================================
# Spool-specific Endpoints (must come AFTER /material-types)
# ============================================================================


@router.get("/{spool_id}", response_model=SpoolResponse)
async def get_spool(
    spool_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> SpoolResponse:
    """
    Get a specific spool by ID.

    Requires authentication.
    Only returns spools belonging to current tenant.
    """
    query = select(Spool).where(
        Spool.id == spool_id,
        Spool.tenant_id == tenant.id,
    )

    result = await db.execute(query)
    spool = result.scalar_one_or_none()

    if not spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spool {spool_id} not found",
        )

    return SpoolResponse(**spool_to_response(spool))


@router.put("/{spool_id}", response_model=SpoolResponse)
async def update_spool(
    spool_id: UUID,
    spool_data: SpoolUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> SpoolResponse:
    """
    Update a spool.

    Requires authentication.
    Only updates spools belonging to current tenant.
    All fields are optional.
    """
    # Get existing spool
    query = select(Spool).where(
        Spool.id == spool_id,
        Spool.tenant_id == tenant.id,
    )

    result = await db.execute(query)
    spool = result.scalar_one_or_none()

    if not spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spool {spool_id} not found",
        )

    # Update fields (only if provided)
    update_data = spool_data.model_dump(exclude_unset=True)
    if "filament_type_id" in update_data:
        await ensure_filament_type_exists(db, update_data["filament_type_id"])

    for field, value in update_data.items():
        setattr(spool, field, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid foreign key reference - check filament_type_id exists.",
        )
    await db.refresh(spool)

    return SpoolResponse(**spool_to_response(spool))


@router.delete("/{spool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spool(
    spool_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> None:
    """
    Delete a spool.

    Requires authentication.
    Only deletes spools belonging to current tenant.
    """
    # Get existing spool
    query = select(Spool).where(
        Spool.id == spool_id,
        Spool.tenant_id == tenant.id,
    )

    result = await db.execute(query)
    spool = result.scalar_one_or_none()

    if not spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spool {spool_id} not found",
        )

    await db.delete(spool)
    await db.commit()


# export/import removed in Phase 1 (stale field names from pre-migration model)


@router.post(
    "/{spool_id}/duplicate", response_model=SpoolResponse, status_code=status.HTTP_201_CREATED
)
async def duplicate_spool(
    spool_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> SpoolResponse:
    """
    Duplicate a spool.

    Creates a copy of the spool with a new auto-generated spool_id.
    Copies filament_type_id and physical spool fields.
    New spool has is_labeled=False (new physical spool needs a new label).
    Returns the new spool for immediate editing.
    """
    # Get source spool
    query = select(Spool).where(
        Spool.id == spool_id,
        Spool.tenant_id == tenant.id,
    )

    result = await db.execute(query)
    source_spool = result.scalar_one_or_none()

    if not source_spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spool {spool_id} not found",
        )

    # Generate new spool_id by finding max and incrementing
    max_query = select(func.max(Spool.spool_id)).where(
        Spool.tenant_id == tenant.id,
        Spool.spool_id.like("FIL-%"),
    )
    max_result = await db.execute(max_query)
    max_spool_id = max_result.scalar_one_or_none()

    if max_spool_id:
        # Extract number and increment
        try:
            current_num = int(max_spool_id.replace("FIL-", ""))
            new_spool_id = f"FIL-{current_num + 1:03d}"
        except ValueError:
            new_spool_id = "FIL-001"
    else:
        new_spool_id = "FIL-001"

    # Create duplicate spool — copy filament_type_id and physical spool fields
    new_spool = Spool(
        tenant_id=tenant.id,
        spool_id=new_spool_id,
        filament_type_id=source_spool.filament_type_id,
        initial_weight=source_spool.initial_weight,
        current_weight=source_spool.initial_weight,  # Reset to full weight for new spool
        empty_spool_weight=source_spool.empty_spool_weight,
        purchase_date=source_spool.purchase_date,
        purchase_price=source_spool.purchase_price,
        supplier=source_spool.supplier,
        storage_location=source_spool.storage_location,
        is_active=True,
        is_labeled=False,  # New physical spool needs a new label
    )

    db.add(new_spool)
    await db.commit()
    await db.refresh(new_spool)

    return SpoolResponse(**spool_to_response(new_spool))
