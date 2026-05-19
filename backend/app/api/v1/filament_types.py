"""FilamentType inventory API endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser, TenantDB
from app.models.filament_type import FilamentType
from app.schemas.filament_type import (
    FilamentTypeCreate,
    FilamentTypeListResponse,
    FilamentTypeResponse,
    FilamentTypeUpdate,
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
            FilamentType.brand.ilike(f"%{search}%")
            | FilamentType.color.ilike(f"%{search}%")
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
