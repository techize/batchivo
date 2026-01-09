"""
Production Run API Endpoints

Provides CRUD operations for production runs, including:
- Creating new production runs with items and materials
- Listing production runs with filtering
- Getting production run details
- Updating production runs (status, actuals, quality ratings)
- Managing production run items and materials
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.production_run import ProductionRun, ProductionRunItem, ProductionRunMaterial
from app.models.model import Model
from app.models.model_material import ModelMaterial
from app.models.spool import Spool
from app.auth.dependencies import CurrentTenant, CurrentUser, RequireAdmin
from app.schemas.production_run import (
    ProductionRunCreateRequest,
    ProductionRunUpdate,
    ProductionRunDetailResponse,
    ProductionRunListResponse,
    ProductionRunItemCreate,
    ProductionRunItemUpdate,
    ProductionRunItemResponse,
    ProductionRunMaterialCreate,
    ProductionRunMaterialUpdate,
    ProductionRunMaterialResponse,
    CancelProductionRunRequest,
    FailProductionRunRequest,
    FAILURE_REASONS,
)
from app.schemas.production_run_plate import (
    ProductionRunPlateCreate,
    ProductionRunPlateUpdate,
    ProductionRunPlateResponse,
    ProductionRunPlateListResponse,
    MarkPlateCompleteRequest,
)
from app.services.production_run import ProductionRunService
from app.services.production_run_plate_service import ProductionRunPlateService

router = APIRouter(tags=["production-runs"])


@router.post("", response_model=ProductionRunDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_production_run(
    request: ProductionRunCreateRequest,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Create a new production run.

    Args:
        request: Production run creation request with items and materials
        db: Database session
        tenant: Current authenticated tenant

    Returns:
        Created production run with items and materials

    Raises:
        HTTPException: If validation fails or referenced entities don't exist
    """
    # Set started_at to now if not provided
    if not request.started_at:
        request.started_at = datetime.now()

    # Generate run number if not provided
    if not request.run_number:
        # Format: YYYYMMDD-NNN
        today = datetime.now().strftime("%Y%m%d")

        # Get count of runs today for this tenant
        result = await db.execute(
            select(func.count(ProductionRun.id)).where(
                and_(
                    ProductionRun.tenant_id == tenant.id,
                    func.date(ProductionRun.created_at) == datetime.now().date(),
                )
            )
        )
        count = result.scalar() or 0
        request.run_number = f"{today}-{count + 1:03d}"

    # Create production run
    db_production_run = ProductionRun(
        tenant_id=tenant.id,
        **request.model_dump(exclude={"items", "materials"}, exclude_unset=True),
    )
    db.add(db_production_run)
    await db.flush()

    # Create items
    for item_data in request.items:
        # Verify model exists and belongs to tenant
        model_result = await db.execute(
            select(Model).where(and_(Model.id == item_data.model_id, Model.tenant_id == tenant.id))
        )
        model = model_result.scalar_one_or_none()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {item_data.model_id} not found",
            )

        db_item = ProductionRunItem(
            production_run_id=db_production_run.id, **item_data.model_dump()
        )
        db.add(db_item)

    # Create materials
    for material_data in request.materials:
        # Verify spool exists and belongs to tenant
        spool_result = await db.execute(
            select(Spool).where(
                and_(Spool.id == material_data.spool_id, Spool.tenant_id == tenant.id)
            )
        )
        spool = spool_result.scalar_one_or_none()
        if not spool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spool {material_data.spool_id} not found",
            )

        # Check sufficient inventory (sum of model + flushed + tower)
        estimated_usage = (
            material_data.estimated_model_weight_grams
            + material_data.estimated_flushed_grams
            + material_data.estimated_tower_grams
        )
        if spool.current_weight < estimated_usage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient inventory in spool {spool.spool_id}. Available: {spool.current_weight}g, Required: {estimated_usage}g",
            )

        db_material = ProductionRunMaterial(
            production_run_id=db_production_run.id, **material_data.model_dump()
        )
        db.add(db_material)

    await db.commit()

    # Reload with relationships (including nested model and spool details)
    result = await db.execute(
        select(ProductionRun)
        .options(
            selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
            selectinload(ProductionRun.materials)
            .selectinload(ProductionRunMaterial.spool)
            .selectinload(Spool.material_type),
        )
        .where(ProductionRun.id == db_production_run.id)
    )
    created_run = result.scalar_one()

    return created_run


@router.get("", response_model=ProductionRunListResponse)
async def list_production_runs(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (inclusive)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    List production runs with optional filtering and pagination.

    Args:
        status_filter: Filter by status (in_progress, completed, failed, cancelled)
        start_date: Filter runs started on or after this date
        end_date: Filter runs started on or before this date
        skip: Pagination offset
        limit: Maximum results per page
        db: Database session
        tenant: Current authenticated tenant

    Returns:
        Paginated list of production runs
    """
    # Build base query with filters
    base_query = select(ProductionRun).where(ProductionRun.tenant_id == tenant.id)

    if status_filter:
        base_query = base_query.where(ProductionRun.status == status_filter)

    if start_date:
        base_query = base_query.where(ProductionRun.started_at >= start_date)

    if end_date:
        base_query = base_query.where(ProductionRun.started_at <= end_date)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results with eager loading for items_summary
    query = (
        base_query.options(
            selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
            selectinload(ProductionRun.product),
        )
        .order_by(ProductionRun.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    runs = result.scalars().all()

    return ProductionRunListResponse(runs=runs, total=total, skip=skip, limit=limit)


@router.get("/failure-reasons", response_model=list)
async def get_failure_reasons():
    """
    Get the list of predefined failure reasons for UI dropdowns.

    Returns:
        List of failure reason options with value, label, and description
    """
    return [reason.model_dump() for reason in FAILURE_REASONS]


@router.get("/{run_id}", response_model=ProductionRunDetailResponse)
async def get_production_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get detailed information about a specific production run.

    Args:
        run_id: Production run ID
        db: Database session
        tenant: Current authenticated tenant

    Returns:
        Production run details with items and materials

    Raises:
        HTTPException: If production run not found
    """
    result = await db.execute(
        select(ProductionRun)
        .options(
            selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
            selectinload(ProductionRun.materials)
            .selectinload(ProductionRunMaterial.spool)
            .selectinload(Spool.material_type),
        )
        .where(and_(ProductionRun.id == run_id, ProductionRun.tenant_id == tenant.id))
    )
    production_run = result.scalar_one_or_none()

    if not production_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Production run {run_id} not found"
        )

    return production_run


@router.patch("/{run_id}", response_model=ProductionRunDetailResponse)
async def update_production_run(
    run_id: UUID,
    updates: ProductionRunUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Update a production run.

    Args:
        run_id: Production run ID
        updates: Fields to update
        db: Database session
        tenant: Current authenticated tenant

    Returns:
        Updated production run

    Raises:
        HTTPException: If production run not found or validation fails
    """
    # Get existing production run
    result = await db.execute(
        select(ProductionRun)
        .options(
            selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
            selectinload(ProductionRun.materials)
            .selectinload(ProductionRunMaterial.spool)
            .selectinload(Spool.material_type),
        )
        .where(and_(ProductionRun.id == run_id, ProductionRun.tenant_id == tenant.id))
    )
    production_run = result.scalar_one_or_none()

    if not production_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Production run {run_id} not found"
        )

    # Status-based validation: restrict edits for completed/failed/cancelled runs
    immutable_statuses = ["completed", "failed", "cancelled"]
    if production_run.status in immutable_statuses:
        # Only allow updating notes field for completed/failed/cancelled runs
        update_data = updates.model_dump(exclude_unset=True)
        restricted_fields = [field for field in update_data.keys() if field != "notes"]

        if restricted_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify {', '.join(restricted_fields)} for {production_run.status} production runs. Only 'notes' can be updated.",
            )

    # Update fields
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(production_run, field, value)

    # Auto-calculate duration if completed_at is set
    if updates.completed_at and production_run.started_at:
        # Ensure started_at is timezone-aware (SQLite returns naive datetimes)
        started_at = production_run.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        duration = updates.completed_at - started_at
        production_run.duration_hours = Decimal(str(duration.total_seconds() / 3600))

    await db.commit()

    # Reload with relationships for response
    result = await db.execute(
        select(ProductionRun)
        .options(
            selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
            selectinload(ProductionRun.materials)
            .selectinload(ProductionRunMaterial.spool)
            .selectinload(Spool.material_type),
        )
        .where(ProductionRun.id == run_id)
    )
    production_run = result.scalar_one()

    return production_run


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    _: RequireAdmin = None,
):
    """
    Delete a production run.

    Args:
        run_id: Production run ID
        db: Database session
        tenant: Current authenticated tenant

    Raises:
        HTTPException: If production run not found or cannot be deleted
    """
    result = await db.execute(
        select(ProductionRun).where(
            and_(ProductionRun.id == run_id, ProductionRun.tenant_id == tenant.id)
        )
    )
    production_run = result.scalar_one_or_none()

    if not production_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Production run {run_id} not found"
        )

    # Only allow deletion of non-completed runs
    if production_run.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete completed production runs",
        )

    await db.delete(production_run)
    await db.commit()


# Production Run Items Endpoints


@router.post(
    "/{run_id}/items", response_model=ProductionRunItemResponse, status_code=status.HTTP_201_CREATED
)
async def add_production_run_item(
    run_id: UUID,
    item: ProductionRunItemCreate,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Add an item to a production run.

    Args:
        run_id: Production run ID
        item: Item data
        db: Database session
        tenant: Current authenticated tenant

    Returns:
        Created production run item

    Raises:
        HTTPException: If production run not found or validation fails
    """
    # Verify production run exists
    run_result = await db.execute(
        select(ProductionRun).where(
            and_(ProductionRun.id == run_id, ProductionRun.tenant_id == tenant.id)
        )
    )
    production_run = run_result.scalar_one_or_none()
    if not production_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Production run {run_id} not found"
        )

    # Verify model exists
    model_result = await db.execute(
        select(Model).where(and_(Model.id == item.model_id, Model.tenant_id == tenant.id))
    )
    model = model_result.scalar_one_or_none()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Model {item.model_id} not found"
        )

    # Create item
    db_item = ProductionRunItem(production_run_id=run_id, **item.model_dump())
    db.add(db_item)
    await db.commit()

    # Reload with model relationship
    result = await db.execute(
        select(ProductionRunItem)
        .options(selectinload(ProductionRunItem.model))
        .where(ProductionRunItem.id == db_item.id)
    )
    db_item = result.scalar_one()

    return db_item


@router.patch("/{run_id}/items/{item_id}", response_model=ProductionRunItemResponse)
async def update_production_run_item(
    run_id: UUID,
    item_id: UUID,
    updates: ProductionRunItemUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Update a production run item.

    Args:
        run_id: Production run ID
        item_id: Item ID
        updates: Fields to update
        db: Database session
        tenant: Current authenticated tenant

    Returns:
        Updated production run item

    Raises:
        HTTPException: If item not found or validation fails
    """
    # Get item with tenant check via production run
    result = await db.execute(
        select(ProductionRunItem, ProductionRun.status)
        .join(ProductionRun)
        .options(selectinload(ProductionRunItem.model))
        .where(
            and_(
                ProductionRunItem.id == item_id,
                ProductionRunItem.production_run_id == run_id,
                ProductionRun.tenant_id == tenant.id,
            )
        )
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Production run item {item_id} not found"
        )

    item, run_status = row

    # Status-based validation: prevent editing items for completed/failed/cancelled runs
    immutable_statuses = ["completed", "failed", "cancelled"]
    if run_status in immutable_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify items for {run_status} production runs",
        )

    # Update fields
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()

    # Reload with model relationship
    result = await db.execute(
        select(ProductionRunItem)
        .options(selectinload(ProductionRunItem.model))
        .where(ProductionRunItem.id == item.id)
    )
    item = result.scalar_one()

    return item


@router.delete("/{run_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production_run_item(
    run_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    _: RequireAdmin = None,
):
    """
    Delete a production run item.

    Args:
        run_id: Production run ID
        item_id: Item ID
        db: Database session
        tenant: Current authenticated tenant

    Raises:
        HTTPException: If item not found
    """
    result = await db.execute(
        select(ProductionRunItem)
        .join(ProductionRun)
        .where(
            and_(
                ProductionRunItem.id == item_id,
                ProductionRunItem.production_run_id == run_id,
                ProductionRun.tenant_id == tenant.id,
            )
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Production run item {item_id} not found"
        )

    await db.delete(item)
    await db.commit()


# Production Run Materials Endpoints


@router.post(
    "/{run_id}/materials",
    response_model=ProductionRunMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_production_run_material(
    run_id: UUID,
    material: ProductionRunMaterialCreate,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Add a material/spool to a production run.

    Args:
        run_id: Production run ID
        material: Material data
        db: Database session
        tenant: Current authenticated tenant

    Returns:
        Created production run material

    Raises:
        HTTPException: If production run or spool not found or insufficient inventory
    """
    # Verify production run exists
    run_result = await db.execute(
        select(ProductionRun).where(
            and_(ProductionRun.id == run_id, ProductionRun.tenant_id == tenant.id)
        )
    )
    production_run = run_result.scalar_one_or_none()
    if not production_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Production run {run_id} not found"
        )

    # Verify spool exists and has sufficient inventory
    spool_result = await db.execute(
        select(Spool).where(and_(Spool.id == material.spool_id, Spool.tenant_id == tenant.id))
    )
    spool = spool_result.scalar_one_or_none()
    if not spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Spool {material.spool_id} not found"
        )

    estimated_usage = (
        material.estimated_model_weight_grams
        + material.estimated_flushed_grams
        + material.estimated_tower_grams
    )
    if spool.current_weight < estimated_usage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient inventory in spool {spool.spool_id}. Available: {spool.current_weight}g, Required: {estimated_usage}g",
        )

    # Create material
    db_material = ProductionRunMaterial(production_run_id=run_id, **material.model_dump())
    db.add(db_material)
    await db.commit()

    # Reload with spool relationship
    result = await db.execute(
        select(ProductionRunMaterial)
        .options(selectinload(ProductionRunMaterial.spool).selectinload(Spool.material_type))
        .where(ProductionRunMaterial.id == db_material.id)
    )
    db_material = result.scalar_one()

    return db_material


@router.patch("/{run_id}/materials/{material_id}", response_model=ProductionRunMaterialResponse)
async def update_production_run_material(
    run_id: UUID,
    material_id: UUID,
    updates: ProductionRunMaterialUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Update a production run material.

    Args:
        run_id: Production run ID
        material_id: Material ID
        updates: Fields to update
        db: Database session
        tenant: Current authenticated tenant

    Returns:
        Updated production run material

    Raises:
        HTTPException: If material not found or validation fails
    """
    # Get material with tenant check via production run
    result = await db.execute(
        select(ProductionRunMaterial, ProductionRun.status)
        .join(ProductionRun)
        .options(selectinload(ProductionRunMaterial.spool).selectinload(Spool.material_type))
        .where(
            and_(
                ProductionRunMaterial.id == material_id,
                ProductionRunMaterial.production_run_id == run_id,
                ProductionRun.tenant_id == tenant.id,
            )
        )
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production run material {material_id} not found",
        )

    material, run_status = row

    # Status-based validation: prevent editing materials for completed/failed/cancelled runs
    immutable_statuses = ["completed", "failed", "cancelled"]
    if run_status in immutable_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify materials for {run_status} production runs",
        )

    # Update fields
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(material, field, value)

    await db.commit()

    # Reload with spool relationship
    result = await db.execute(
        select(ProductionRunMaterial)
        .options(selectinload(ProductionRunMaterial.spool).selectinload(Spool.material_type))
        .where(ProductionRunMaterial.id == material.id)
    )
    material = result.scalar_one()

    return material


@router.delete("/{run_id}/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production_run_material(
    run_id: UUID,
    material_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    _: RequireAdmin = None,
):
    """
    Delete a production run material.

    Args:
        run_id: Production run ID
        material_id: Material ID
        db: Database session
        tenant: Current authenticated tenant

    Raises:
        HTTPException: If material not found
    """
    result = await db.execute(
        select(ProductionRunMaterial)
        .join(ProductionRun)
        .where(
            and_(
                ProductionRunMaterial.id == material_id,
                ProductionRunMaterial.production_run_id == run_id,
                ProductionRun.tenant_id == tenant.id,
            )
        )
    )
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production run material {material_id} not found",
        )

    await db.delete(material)
    await db.commit()


# Special Endpoint: Complete Production Run with Inventory Deduction


@router.post("/{run_id}/complete", response_model=ProductionRunDetailResponse)
async def complete_production_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Mark a production run as completed and deduct inventory from spools.

    This endpoint:
    1. Validates that all materials have actual usage recorded
    2. Deducts actual usage from spool inventory
    3. Updates production run status to 'completed'
    4. Sets completed_at timestamp and calculates duration

    Args:
        run_id: Production run ID
        db: Database session
        tenant: Current authenticated tenant

    Returns:
        Completed production run with updated inventory

    Raises:
        HTTPException: If validation fails or insufficient inventory
    """
    # Get production run with materials
    result = await db.execute(
        select(ProductionRun)
        .options(
            selectinload(ProductionRun.items),
            selectinload(ProductionRun.materials)
            .selectinload(ProductionRunMaterial.spool)
            .selectinload(Spool.material_type),
        )
        .where(and_(ProductionRun.id == run_id, ProductionRun.tenant_id == tenant.id))
    )
    production_run = result.scalar_one_or_none()

    if not production_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Production run {run_id} not found"
        )

    if production_run.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Production run is already completed"
        )

    # Validate all materials have actual usage recorded
    # Must have either weighing data (before/after) or manual actual weights
    for material in production_run.materials:
        has_weighing = (
            material.spool_weight_before_grams is not None
            and material.spool_weight_after_grams is not None
        )
        has_manual = material.actual_model_weight_grams is not None
        if not has_weighing and not has_manual:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Material {material.id} does not have actual usage recorded. Please weigh spools or enter manual usage.",
            )

    # Deduct inventory from spools
    total_deducted = Decimal("0")
    for material in production_run.materials:
        spool = material.spool
        actual_usage = material.actual_total_weight

        # Check sufficient inventory
        if spool.current_weight < actual_usage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient inventory in spool {spool.spool_id}. Available: {spool.current_weight}g, Required: {actual_usage}g",
            )

        # Deduct from spool
        spool.current_weight -= actual_usage
        total_deducted += actual_usage

    # Update production run status
    production_run.status = "completed"
    production_run.completed_at = datetime.now(timezone.utc)

    # Calculate duration
    if production_run.started_at:
        # Ensure started_at is timezone-aware (SQLite returns naive datetimes)
        started_at = production_run.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        duration = production_run.completed_at - started_at
        production_run.duration_hours = Decimal(str(duration.total_seconds() / 3600))

    # Calculate totals from materials
    production_run.actual_total_filament_grams = sum(
        material.actual_total_weight for material in production_run.materials
    )

    # Calculate cost analysis (distributes waste across successful items)
    total_material_cost = Decimal("0")
    for material in production_run.materials:
        if material.cost_per_gram:
            total_material_cost += material.actual_total_weight * material.cost_per_gram

    successful_weight = Decimal("0")

    # Handle multi-plate runs
    if production_run.is_multi_plate and production_run.plates:
        for plate in production_run.plates:
            if plate.successful_prints > 0:
                # Get model weight from BOM
                bom_result = await db.execute(
                    select(func.sum(ModelMaterial.weight_grams)).where(
                        ModelMaterial.model_id == plate.model_id
                    )
                )
                model_weight = bom_result.scalar() or Decimal("0")
                plate.model_weight_grams = model_weight
                successful_weight += Decimal(str(plate.successful_prints)) * model_weight

    # Handle legacy item-based runs
    elif production_run.items:
        for item in production_run.items:
            if item.successful_quantity > 0:
                # Get model weight from BOM
                bom_result = await db.execute(
                    select(func.sum(ModelMaterial.weight_grams)).where(
                        ModelMaterial.model_id == item.model_id
                    )
                )
                model_weight = bom_result.scalar() or Decimal("0")
                item.model_weight_grams = model_weight
                successful_weight += Decimal(str(item.successful_quantity)) * model_weight

    # Calculate cost per gram and per-unit costs
    if successful_weight > 0:
        cost_per_gram = total_material_cost / successful_weight
        production_run.cost_per_gram_actual = cost_per_gram
        production_run.successful_weight_grams = successful_weight

        # Calculate per-item/plate costs
        if production_run.is_multi_plate and production_run.plates:
            for plate in production_run.plates:
                if plate.model_weight_grams:
                    plate.actual_cost_per_unit = plate.model_weight_grams * cost_per_gram
        elif production_run.items:
            for item in production_run.items:
                if item.model_weight_grams:
                    item.actual_cost_per_unit = item.model_weight_grams * cost_per_gram

    await db.commit()

    # Reload with all relationships for response
    result = await db.execute(
        select(ProductionRun)
        .options(
            selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
            selectinload(ProductionRun.materials)
            .selectinload(ProductionRunMaterial.spool)
            .selectinload(Spool.material_type),
        )
        .where(ProductionRun.id == run_id)
    )
    production_run = result.scalar_one()

    # Record production run completion metrics
    try:
        from app.observability.metrics import record_production_run_completed

        duration_seconds = float(production_run.duration_hours or 0) * 3600
        material_cost = float(production_run.actual_total_cost or 0)

        record_production_run_completed(
            tenant_id=str(tenant.id),
            duration_seconds=duration_seconds,
            material_cost=material_cost,
        )
    except Exception:
        # Don't fail request if metrics recording fails
        pass

    return production_run


# Cancel and Fail Endpoints


@router.post("/{run_id}/cancel", response_model=ProductionRunDetailResponse)
async def cancel_production_run_endpoint(
    run_id: UUID,
    request: CancelProductionRunRequest,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
):
    """
    Cancel a production run with options for handling materials.

    Cancel modes:
    - "full_reversal": Simply cancel without deducting any materials (as if run never started)
    - "record_partial": Deduct actual usage recorded before cancellation

    Args:
        run_id: Production run ID
        request: Cancel request with mode and optional partial usage data
        db: Database session
        tenant: Current authenticated tenant
        user: Current authenticated user

    Returns:
        Cancelled production run

    Raises:
        HTTPException: If run not found, not in_progress, or validation fails
    """
    service = ProductionRunService(db, tenant, user)

    # Convert partial_usage list to dict
    partial_usage = None
    if request.cancel_mode == "record_partial" and request.partial_usage:
        partial_usage = {entry.spool_id: entry.grams for entry in request.partial_usage}

    try:
        result = await service.cancel_production_run(
            run_id=run_id,
            cancel_mode=request.cancel_mode,
            partial_usage=partial_usage,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Production run {run_id} not found"
            )

        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{run_id}/fail", response_model=ProductionRunDetailResponse)
async def fail_production_run_endpoint(
    run_id: UUID,
    request: FailProductionRunRequest,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
):
    """
    Mark a production run as failed and record waste materials.

    This endpoint:
    1. Records waste materials as WASTE transaction type
    2. Deducts waste from spool inventory
    3. Updates run status to 'failed' with failure reason

    Args:
        run_id: Production run ID
        request: Fail request with waste materials and failure reason
        db: Database session
        tenant: Current authenticated tenant
        user: Current authenticated user

    Returns:
        Failed production run with waste recorded

    Raises:
        HTTPException: If run not found, not in_progress, or validation fails
    """
    service = ProductionRunService(db, tenant, user)

    # Convert waste_materials list to dict
    waste_grams = {entry.spool_id: entry.grams for entry in request.waste_materials}

    try:
        result = await service.fail_production_run(
            run_id=run_id,
            waste_grams=waste_grams,
            failure_reason=request.failure_reason,
            notes=request.notes,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Production run {run_id} not found"
            )

        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Production Run Plates Endpoints


@router.post(
    "/{run_id}/plates",
    response_model=ProductionRunPlateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_production_run_plate(
    run_id: UUID,
    plate_data: ProductionRunPlateCreate,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
):
    """
    Create a new plate within a production run.

    Args:
        run_id: Production run ID
        plate_data: Plate creation data
        db: Database session
        tenant: Current authenticated tenant
        user: Current authenticated user

    Returns:
        Created production run plate

    Raises:
        HTTPException: If production run, model, or printer not found
    """
    service = ProductionRunPlateService(db, tenant, user)

    try:
        plate = await service.create_plate(run_id, plate_data)
        return ProductionRunPlateResponse.model_validate(plate)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{run_id}/plates", response_model=ProductionRunPlateListResponse)
async def list_production_run_plates(
    run_id: UUID,
    status_filter: Optional[str] = Query(None, description="Filter by plate status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
):
    """
    List all plates for a production run.

    Args:
        run_id: Production run ID
        status_filter: Optional status filter (pending, printing, complete, failed, cancelled)
        skip: Pagination offset
        limit: Maximum results per page
        db: Database session
        tenant: Current authenticated tenant
        user: Current authenticated user

    Returns:
        Paginated list of plates
    """
    service = ProductionRunPlateService(db, tenant, user)
    return await service.list_plates_for_run(
        production_run_id=run_id, status=status_filter, skip=skip, limit=limit
    )


@router.get("/{run_id}/plates/{plate_id}", response_model=ProductionRunPlateResponse)
async def get_production_run_plate(
    run_id: UUID,
    plate_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
):
    """
    Get details of a specific plate.

    Args:
        run_id: Production run ID
        plate_id: Plate ID
        db: Database session
        tenant: Current authenticated tenant
        user: Current authenticated user

    Returns:
        Plate details

    Raises:
        HTTPException: If plate not found
    """
    service = ProductionRunPlateService(db, tenant, user)
    plate = await service.get_plate(plate_id)

    if not plate or plate.production_run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plate {plate_id} not found in production run {run_id}",
        )

    return ProductionRunPlateResponse.model_validate(plate)


@router.patch("/{run_id}/plates/{plate_id}", response_model=ProductionRunPlateResponse)
async def update_production_run_plate(
    run_id: UUID,
    plate_id: UUID,
    updates: ProductionRunPlateUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
):
    """
    Update a production run plate.

    Args:
        run_id: Production run ID
        plate_id: Plate ID
        updates: Fields to update
        db: Database session
        tenant: Current authenticated tenant
        user: Current authenticated user

    Returns:
        Updated plate

    Raises:
        HTTPException: If plate not found
    """
    service = ProductionRunPlateService(db, tenant, user)

    # Verify plate belongs to this run
    existing = await service.get_plate(plate_id)
    if not existing or existing.production_run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plate {plate_id} not found in production run {run_id}",
        )

    plate = await service.update_plate(plate_id, updates)
    return ProductionRunPlateResponse.model_validate(plate)


@router.post("/{run_id}/plates/{plate_id}/start", response_model=ProductionRunPlateResponse)
async def start_production_run_plate(
    run_id: UUID,
    plate_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
):
    """
    Start printing a plate (transition from pending to printing).

    Args:
        run_id: Production run ID
        plate_id: Plate ID
        db: Database session
        tenant: Current authenticated tenant
        user: Current authenticated user

    Returns:
        Updated plate with printing status

    Raises:
        HTTPException: If plate not found or invalid status transition
    """
    service = ProductionRunPlateService(db, tenant, user)

    # Verify plate belongs to this run
    existing = await service.get_plate(plate_id)
    if not existing or existing.production_run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plate {plate_id} not found in production run {run_id}",
        )

    try:
        plate = await service.start_plate(plate_id)
        return ProductionRunPlateResponse.model_validate(plate)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{run_id}/plates/{plate_id}/complete", response_model=ProductionRunPlateResponse)
async def complete_production_run_plate(
    run_id: UUID,
    plate_id: UUID,
    request: MarkPlateCompleteRequest,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
):
    """
    Mark a plate as complete with print results.

    Args:
        run_id: Production run ID
        plate_id: Plate ID
        request: Completion data with successful/failed print counts
        db: Database session
        tenant: Current authenticated tenant
        user: Current authenticated user

    Returns:
        Updated plate with complete status

    Raises:
        HTTPException: If plate not found or invalid status transition
    """
    service = ProductionRunPlateService(db, tenant, user)

    # Verify plate belongs to this run
    existing = await service.get_plate(plate_id)
    if not existing or existing.production_run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plate {plate_id} not found in production run {run_id}",
        )

    try:
        plate = await service.complete_plate(plate_id, request)
        return ProductionRunPlateResponse.model_validate(plate)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{run_id}/plates/{plate_id}/fail", response_model=ProductionRunPlateResponse)
async def fail_production_run_plate(
    run_id: UUID,
    plate_id: UUID,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
):
    """
    Mark a plate as failed.

    Args:
        run_id: Production run ID
        plate_id: Plate ID
        notes: Optional failure notes
        db: Database session
        tenant: Current authenticated tenant
        user: Current authenticated user

    Returns:
        Updated plate with failed status

    Raises:
        HTTPException: If plate not found or invalid status transition
    """
    service = ProductionRunPlateService(db, tenant, user)

    # Verify plate belongs to this run
    existing = await service.get_plate(plate_id)
    if not existing or existing.production_run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plate {plate_id} not found in production run {run_id}",
        )

    try:
        plate = await service.fail_plate(plate_id, notes)
        return ProductionRunPlateResponse.model_validate(plate)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{run_id}/plates/{plate_id}/cancel", response_model=ProductionRunPlateResponse)
async def cancel_production_run_plate(
    run_id: UUID,
    plate_id: UUID,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
):
    """
    Cancel a plate.

    Args:
        run_id: Production run ID
        plate_id: Plate ID
        notes: Optional cancellation notes
        db: Database session
        tenant: Current authenticated tenant
        user: Current authenticated user

    Returns:
        Updated plate with cancelled status

    Raises:
        HTTPException: If plate not found or invalid status transition
    """
    service = ProductionRunPlateService(db, tenant, user)

    # Verify plate belongs to this run
    existing = await service.get_plate(plate_id)
    if not existing or existing.production_run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plate {plate_id} not found in production run {run_id}",
        )

    try:
        plate = await service.cancel_plate(plate_id, notes)
        return ProductionRunPlateResponse.model_validate(plate)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{run_id}/plates/{plate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production_run_plate(
    run_id: UUID,
    plate_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    _: RequireAdmin = None,
):
    """
    Delete a plate from a production run.

    Args:
        run_id: Production run ID
        plate_id: Plate ID
        db: Database session
        tenant: Current authenticated tenant
        user: Current authenticated user

    Raises:
        HTTPException: If plate not found
    """
    service = ProductionRunPlateService(db, tenant, user)

    # Verify plate belongs to this run
    existing = await service.get_plate(plate_id)
    if not existing or existing.production_run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plate {plate_id} not found in production run {run_id}",
        )

    result = await service.delete_plate(plate_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Plate {plate_id} not found"
        )
