"""FilamentType inventory API endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import case, func, select, text
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import CurrentTenant, CurrentUser, TenantDB
from app.config import get_settings

settings = get_settings()
from app.models.filament_type import FilamentType
from app.models.material import MaterialType
from app.models.spool import Spool
from app.schemas.filament_type import (
    BatchCreateRequest,
    BatchCreateResponse,
    BulkCreateRequest,
    BulkCreateResponse,
    FilamentTypeAggregatedListResponse,
    FilamentTypeAggregatedResponse,
    FilamentTypeCreate,
    FilamentTypeListResponse,
    FilamentTypeResponse,
    FilamentTypeUpdate,
    SpoolInSheetResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def filament_type_to_response(ft: FilamentType) -> dict:
    """Convert FilamentType model to response dict."""
    return {
        **ft.__dict__,
        "material_type_code": ft.material_type.code if ft.material_type else "UNKNOWN",
        "material_type_name": ft.material_type.name if ft.material_type else "Unknown",
    }


async def _next_spool_ids(db, tenant_id: UUID, count: int) -> list[str]:
    """Return `count` sequential FIL-NNN spool IDs. Must be called within an open transaction."""
    max_query = select(func.max(Spool.spool_id)).where(
        Spool.tenant_id == tenant_id,
        Spool.spool_id.like("FIL-%"),
    )
    max_result = await db.execute(max_query)
    max_spool_id = max_result.scalar_one_or_none()
    current_num = 0
    if max_spool_id:
        try:
            current_num = int(max_spool_id.split("-")[1])
        except (ValueError, IndexError):
            current_num = 0
    return [f"FIL-{current_num + i + 1:03d}" for i in range(count)]


async def _find_or_create_filament_type(db, tenant_id: UUID, data) -> FilamentType:
    """Find existing FilamentType by (tenant_id, brand, color, material_type_id) or create new one."""
    stmt = select(FilamentType).where(
        FilamentType.tenant_id == tenant_id,
        FilamentType.brand == data.brand,
        FilamentType.color == data.color,
        FilamentType.material_type_id == data.material_type_id,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        optional_fields = [
            "color_hex",
            "finish",
            "pattern",
            "spool_type",
            "notes",
            "density",
            "extruder_temp",
            "bed_temp",
        ]
        for field in optional_fields:
            incoming_value = getattr(data, field, None)
            if getattr(existing, field) is None and incoming_value is not None:
                setattr(existing, field, incoming_value)
                db.add(existing)
        return existing
    exclude_fields = {"quantity", "initial_weight"}
    ft = FilamentType(
        tenant_id=tenant_id,
        has_sample=False,
        **data.model_dump(exclude=exclude_fields),
    )
    db.add(ft)
    await db.flush()
    await db.refresh(ft)
    return ft


@router.post("", response_model=FilamentTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_filament_type(
    data: FilamentTypeCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> FilamentTypeResponse:
    """
    Create a new filament type definition.

    Requires authentication.
    FilamentType will be associated with current tenant.
    """
    ft = FilamentType(
        tenant_id=tenant.id,
        **data.model_dump(),
    )

    db.add(ft)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid foreign key reference — check material_type_id exists.",
        )
    await db.refresh(ft)

    logger.info(f"Created FilamentType {ft.id} for tenant {tenant.id}")
    return FilamentTypeResponse(**filament_type_to_response(ft))


@router.get("", response_model=FilamentTypeListResponse)
async def list_filament_types(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by brand or colour"),
    material_type_id: Optional[UUID] = Query(None, description="Filter by material type"),
) -> FilamentTypeListResponse:
    """
    List all filament types for current tenant with pagination.

    Supports:
    - Pagination (page, page_size)
    - Search (brand, colour)
    - Filter by material type
    """
    query = select(FilamentType).where(FilamentType.tenant_id == tenant.id)

    if search:
        query = query.where(
            FilamentType.brand.ilike(f"%{search}%") | FilamentType.color.ilike(f"%{search}%")
        )

    if material_type_id:
        query = query.where(FilamentType.material_type_id == material_type_id)

    # Count total (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(FilamentType.created_at.desc())

    result = await db.execute(query)
    filament_types = result.scalars().all()

    responses = [FilamentTypeResponse(**filament_type_to_response(ft)) for ft in filament_types]

    return FilamentTypeListResponse(
        total=total,
        filament_types=responses,
        page=page,
        page_size=page_size,
    )


@router.get("/aggregated", response_model=FilamentTypeAggregatedListResponse)
async def list_filament_types_aggregated(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    brand: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    material_type_id: Optional[UUID] = Query(None),
    needs_labels: Optional[bool] = Query(None),
    needs_sample: Optional[bool] = Query(None),
) -> FilamentTypeAggregatedListResponse:
    """Aggregated FilamentType list with spool/labeled counts for the list view."""
    query = (
        select(
            FilamentType.id,
            FilamentType.brand,
            FilamentType.color,
            FilamentType.color_hex,
            FilamentType.has_sample,
            MaterialType.name.label("material_type_name"),
            MaterialType.code.label("material_type_code"),
            func.count(Spool.id).label("spool_count"),
            func.count(case((Spool.is_labeled == True, Spool.id))).label("labeled_count"),  # noqa: E712
        )
        .outerjoin(
            Spool, (Spool.filament_type_id == FilamentType.id) & (Spool.tenant_id == tenant.id)
        )
        .outerjoin(MaterialType, MaterialType.id == FilamentType.material_type_id)
        .where(FilamentType.tenant_id == tenant.id)
        .group_by(
            FilamentType.id,
            FilamentType.brand,
            FilamentType.color,
            FilamentType.color_hex,
            FilamentType.has_sample,
            MaterialType.name,
            MaterialType.code,
        )
    )

    if brand:
        query = query.where(FilamentType.brand.ilike(f"%{brand}%"))
    if color:
        query = query.where(FilamentType.color.ilike(f"%{color}%"))
    if material_type_id:
        query = query.where(FilamentType.material_type_id == material_type_id)
    if needs_sample is True:
        query = query.where(FilamentType.has_sample == False)  # noqa: E712
    if needs_labels is True:
        query = query.having(func.count(case((Spool.is_labeled == False, Spool.id))) > 0)  # noqa: E712

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(FilamentType.brand, FilamentType.color)

    result = await db.execute(query)
    rows = result.mappings().all()

    logger.info(f"Listed {total} filament types aggregated for tenant {tenant.id}")
    return FilamentTypeAggregatedListResponse(
        total=total,
        filament_types=[FilamentTypeAggregatedResponse(**dict(row)) for row in rows],
        page=page,
        page_size=page_size,
    )


@router.post("/bulk-create", response_model=BulkCreateResponse, status_code=status.HTTP_201_CREATED)
async def bulk_create(
    data: BulkCreateRequest,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> BulkCreateResponse:
    """Create multiple identical spools, auto-generating sequential FIL-NNN IDs."""
    ft = await _find_or_create_filament_type(db, tenant.id, data)
    spool_ids = await _next_spool_ids(db, tenant.id, data.quantity)
    spools = [
        Spool(
            tenant_id=tenant.id,
            spool_id=sid,
            filament_type_id=ft.id,
            initial_weight=data.initial_weight,
            current_weight=data.initial_weight,
            is_active=True,
            is_labeled=False,
        )
        for sid in spool_ids
    ]
    db.add_all(spools)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Re-establish RLS context — SET LOCAL is transaction-scoped and is cleared by rollback.
        if settings.rls_enabled:
            await db.execute(
                text("SET LOCAL app.current_tenant_id = :tenant_id"),
                {"tenant_id": str(tenant.id)},
            )
        ft = await _find_or_create_filament_type(db, tenant.id, data)
        spool_ids = await _next_spool_ids(db, tenant.id, data.quantity)
        spools = [
            Spool(
                tenant_id=tenant.id,
                spool_id=sid,
                filament_type_id=ft.id,
                initial_weight=data.initial_weight,
                current_weight=data.initial_weight,
                is_active=True,
                is_labeled=False,
            )
            for sid in spool_ids
        ]
        db.add_all(spools)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Spool ID collision — please retry.",
            )
    logger.info(
        "bulk_create: created %d spools for FilamentType %s (tenant %s)",
        data.quantity,
        ft.id,
        tenant.id,
    )
    return BulkCreateResponse(filament_type_id=ft.id, spool_ids=spool_ids)


@router.post(
    "/batch-create", response_model=BatchCreateResponse, status_code=status.HTTP_201_CREATED
)
async def batch_create(
    data: BatchCreateRequest,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> BatchCreateResponse:
    """Create one spool per entry, supporting multiple color variants in one call."""
    all_spool_ids = await _next_spool_ids(db, tenant.id, len(data.entries))
    results = []
    for i, entry in enumerate(data.entries):
        ft = await _find_or_create_filament_type(db, tenant.id, entry)
        db.add(
            Spool(
                tenant_id=tenant.id,
                spool_id=all_spool_ids[i],
                filament_type_id=ft.id,
                initial_weight=data.initial_weight,
                current_weight=data.initial_weight,
                is_active=True,
                is_labeled=False,
            )
        )
        results.append({"filament_type_id": str(ft.id), "spool_id": all_spool_ids[i]})
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Re-establish RLS context — SET LOCAL is transaction-scoped and is cleared by rollback.
        if settings.rls_enabled:
            await db.execute(
                text("SET LOCAL app.current_tenant_id = :tenant_id"),
                {"tenant_id": str(tenant.id)},
            )
        all_spool_ids = await _next_spool_ids(db, tenant.id, len(data.entries))
        results = []
        for i, entry in enumerate(data.entries):
            ft = await _find_or_create_filament_type(db, tenant.id, entry)
            db.add(
                Spool(
                    tenant_id=tenant.id,
                    spool_id=all_spool_ids[i],
                    filament_type_id=ft.id,
                    initial_weight=data.initial_weight,
                    current_weight=data.initial_weight,
                    is_active=True,
                    is_labeled=False,
                )
            )
            results.append({"filament_type_id": str(ft.id), "spool_id": all_spool_ids[i]})
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Spool ID collision — please retry.",
            )
    logger.info("batch_create: created %d spools for tenant %s", len(data.entries), tenant.id)
    return BatchCreateResponse(results=results)


@router.get("/{filament_type_id}/spools", response_model=list[SpoolInSheetResponse])
async def list_spools_for_filament_type(
    filament_type_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> list[SpoolInSheetResponse]:
    """List child spools for a FilamentType. Used by the read-only spool drill-down sheet."""
    # Check FilamentType exists and belongs to tenant
    ft_result = await db.execute(
        select(FilamentType).where(
            FilamentType.id == filament_type_id,
            FilamentType.tenant_id == tenant.id,
        )
    )
    ft = ft_result.scalar_one_or_none()
    if not ft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FilamentType {filament_type_id} not found",
        )

    result = await db.execute(
        select(Spool)
        .where(Spool.filament_type_id == filament_type_id, Spool.tenant_id == tenant.id)
        .order_by(Spool.spool_id)
    )
    spools = result.scalars().all()

    logger.info(f"Listed {len(spools)} spools for FilamentType {filament_type_id}")
    return [SpoolInSheetResponse.model_validate(s) for s in spools]


@router.get("/{filament_type_id}", response_model=FilamentTypeResponse)
async def get_filament_type(
    filament_type_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> FilamentTypeResponse:
    """
    Get a specific filament type by ID.

    Requires authentication.
    Only returns filament types belonging to current tenant.
    """
    result = await db.execute(
        select(FilamentType).where(
            FilamentType.id == filament_type_id,
            FilamentType.tenant_id == tenant.id,
        )
    )
    ft = result.scalar_one_or_none()

    if not ft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FilamentType {filament_type_id} not found",
        )

    return FilamentTypeResponse(**filament_type_to_response(ft))


@router.put("/{filament_type_id}", response_model=FilamentTypeResponse)
async def update_filament_type(
    filament_type_id: UUID,
    data: FilamentTypeUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> FilamentTypeResponse:
    """
    Update a filament type.

    Requires authentication.
    Only updates filament types belonging to current tenant.
    All fields are optional.
    """
    result = await db.execute(
        select(FilamentType).where(
            FilamentType.id == filament_type_id,
            FilamentType.tenant_id == tenant.id,
        )
    )
    ft = result.scalar_one_or_none()

    if not ft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FilamentType {filament_type_id} not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ft, field, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid foreign key reference — check material_type_id exists.",
        )
    await db.refresh(ft)

    logger.info(f"Updated FilamentType {filament_type_id} for tenant {tenant.id}")
    return FilamentTypeResponse(**filament_type_to_response(ft))


@router.delete("/{filament_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filament_type(
    filament_type_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> None:
    """
    Delete a filament type.

    Requires authentication.
    Only deletes filament types belonging to current tenant.
    """
    result = await db.execute(
        select(FilamentType).where(
            FilamentType.id == filament_type_id,
            FilamentType.tenant_id == tenant.id,
        )
    )
    ft = result.scalar_one_or_none()

    if not ft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FilamentType {filament_type_id} not found",
        )

    await db.delete(ft)
    await db.commit()

    logger.info(f"Deleted FilamentType {filament_type_id} for tenant {tenant.id}")
