"""Spool inventory API endpoints."""

import csv
import io
import json
from typing import Optional
from uuid import UUID

import yaml
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
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
        "material_type_code": spool.material_type.code if spool.material_type else "UNKNOWN",
        "material_type_name": spool.material_type.name if spool.material_type else "Unknown",
    }


@router.post("", response_model=SpoolResponse, status_code=status.HTTP_201_CREATED)
async def create_spool(
    spool_data: SpoolCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> SpoolResponse:
    """
    Create a new filament spool.

    Requires authentication.
    Spool will be associated with current tenant.
    """
    # Create spool instance
    spool = Spool(
        tenant_id=tenant.id,
        **spool_data.model_dump(),
    )

    db.add(spool)
    await db.commit()
    await db.refresh(spool)

    return SpoolResponse(**spool_to_response(spool))


@router.get("", response_model=SpoolListResponse)
async def list_spools(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
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
    - Filter by material type
    - Filter by active status
    - Filter by low stock
    """
    # Base query for current tenant
    query = select(Spool).where(Spool.tenant_id == tenant.id)

    # Apply filters
    if search:
        search_filter = or_(
            Spool.spool_id.ilike(f"%{search}%"),
            Spool.brand.ilike(f"%{search}%"),
            Spool.color.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if material_type_id:
        query = query.where(Spool.material_type_id == material_type_id)

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
    db: AsyncSession = Depends(get_db),
) -> list[MaterialTypeResponse]:
    """
    List all available material types.

    Material types are global (not tenant-scoped).
    Returns all active material types sorted by code.
    """
    result = await db.execute(
        select(MaterialType)
        .where(MaterialType.is_active.is_(True))  # noqa: E712
        .order_by(MaterialType.code)
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    for field, value in update_data.items():
        setattr(spool, field, value)

    await db.commit()
    await db.refresh(spool)

    return SpoolResponse(**spool_to_response(spool))


@router.delete("/{spool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spool(
    spool_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
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


@router.post(
    "/{spool_id}/duplicate", response_model=SpoolResponse, status_code=status.HTTP_201_CREATED
)
async def duplicate_spool(
    spool_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> SpoolResponse:
    """
    Duplicate a spool.

    Creates a copy of the spool with a new auto-generated spool_id.
    Preserves all fields except id, spool_id, and timestamps.
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

    # Create duplicate spool
    new_spool = Spool(
        tenant_id=tenant.id,
        spool_id=new_spool_id,
        material_type_id=source_spool.material_type_id,
        brand=source_spool.brand,
        color=source_spool.color,
        finish=source_spool.finish,
        initial_weight=source_spool.initial_weight,
        current_weight=source_spool.initial_weight,  # Reset to full weight for new spool
        empty_spool_weight=source_spool.empty_spool_weight,
        purchase_date=source_spool.purchase_date,
        purchase_price=source_spool.purchase_price,
        supplier=source_spool.supplier,
        purchased_quantity=source_spool.purchased_quantity,
        spools_remaining=source_spool.spools_remaining,
        storage_location=source_spool.storage_location,
        notes=source_spool.notes,
        is_active=True,
    )

    db.add(new_spool)
    await db.commit()
    await db.refresh(new_spool)

    return SpoolResponse(**spool_to_response(new_spool))


@router.get("/export", status_code=status.HTTP_200_OK)
async def export_spools(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    format: str = Query("csv", regex="^(csv|json|yaml)$", description="Export format"),
) -> StreamingResponse:
    """
    Export all spools for current tenant.

    Supported formats: csv, json, yaml
    """
    # Get all spools for tenant
    query = select(Spool).where(Spool.tenant_id == tenant.id).order_by(Spool.created_at.asc())
    result = await db.execute(query)
    spools = result.scalars().all()

    # Convert to dict format
    spools_data = []
    for spool in spools:
        spool_dict = {
            "spool_id": spool.spool_id,
            "brand": spool.brand,
            "material_type_id": str(spool.material_type_id),
            "color": spool.color,
            "finish": spool.finish,
            "diameter_mm": float(spool.diameter_mm),
            "initial_weight_g": float(spool.initial_weight_g),
            "current_weight_g": float(spool.current_weight_g),
            "cost_per_kg": float(spool.cost_per_kg) if spool.cost_per_kg else None,
            "purchase_date": spool.purchase_date.isoformat() if spool.purchase_date else None,
            "supplier": spool.supplier,
            "location": spool.location,
            "notes": spool.notes,
            "is_active": spool.is_active,
        }
        spools_data.append(spool_dict)

    # Generate file content based on format
    if format == "csv":
        output = io.StringIO()
        if spools_data:
            writer = csv.DictWriter(output, fieldnames=spools_data[0].keys())
            writer.writeheader()
            writer.writerows(spools_data)
        content = output.getvalue()
        media_type = "text/csv"
        filename = f"spools_export_{tenant.slug}.csv"

    elif format == "json":
        content = json.dumps(spools_data, indent=2)
        media_type = "application/json"
        filename = f"spools_export_{tenant.slug}.json"

    else:  # yaml
        content = yaml.dump(spools_data, default_flow_style=False, allow_unicode=True)
        media_type = "application/x-yaml"
        filename = f"spools_export_{tenant.slug}.yaml"

    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/import", status_code=status.HTTP_200_OK)
async def import_spools(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> dict:
    """
    Import spools from CSV, JSON, or YAML file.

    File format is detected from extension (.csv, .json, .yaml/.yml)

    Returns summary of imported spools and any errors.
    """
    # Read file content
    content = await file.read()

    # Detect format from filename
    filename_lower = file.filename.lower() if file.filename else ""

    try:
        if filename_lower.endswith(".csv"):
            # Parse CSV
            csv_content = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(csv_content))
            spools_data = list(reader)

        elif filename_lower.endswith(".json"):
            # Parse JSON
            spools_data = json.loads(content.decode("utf-8"))
            if not isinstance(spools_data, list):
                raise ValueError("JSON must contain an array of spools")

        elif filename_lower.endswith((".yaml", ".yml")):
            # Parse YAML
            spools_data = yaml.safe_load(content.decode("utf-8"))
            if not isinstance(spools_data, list):
                raise ValueError("YAML must contain an array of spools")

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Use .csv, .json, or .yaml/.yml",
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}",
        )

    # Validate and import spools
    imported_count = 0
    errors = []

    for idx, spool_dict in enumerate(spools_data):
        try:
            # Create spool data (exclude id if present)
            spool_create = SpoolCreate(
                spool_id=spool_dict.get("spool_id"),
                brand=spool_dict.get("brand"),
                material_type_id=UUID(spool_dict.get("material_type_id")),
                color=spool_dict.get("color"),
                finish=spool_dict.get("finish", "matte"),
                diameter_mm=float(spool_dict.get("diameter_mm")),
                initial_weight_g=float(spool_dict.get("initial_weight_g")),
                current_weight_g=float(spool_dict.get("current_weight_g")),
                cost_per_kg=float(spool_dict["cost_per_kg"])
                if spool_dict.get("cost_per_kg")
                else None,
                purchase_date=spool_dict.get("purchase_date"),
                supplier=spool_dict.get("supplier"),
                location=spool_dict.get("location"),
                notes=spool_dict.get("notes"),
                is_active=bool(spool_dict.get("is_active", True)),
            )

            # Create spool
            spool = Spool(
                tenant_id=tenant.id,
                **spool_create.model_dump(),
            )

            db.add(spool)
            imported_count += 1

        except Exception as e:
            errors.append(
                {
                    "row": idx + 1,
                    "spool_id": spool_dict.get("spool_id", "unknown"),
                    "error": str(e),
                }
            )

    # Commit all successful imports
    if imported_count > 0:
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save spools: {str(e)}",
            )

    return {
        "imported": imported_count,
        "errors": errors,
        "total": len(spools_data),
    }
