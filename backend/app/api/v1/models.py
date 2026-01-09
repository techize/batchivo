"""Model catalog API endpoints (printed items with BOM)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.model import Model
from app.models.model_component import ModelComponent
from app.models.model_material import ModelMaterial
from app.models.spool import Spool
from app.schemas.model import (
    BOMSpoolSuggestion,
    ModelComponentCreate,
    ModelComponentResponse,
    ModelCreate,
    ModelDetailResponse,
    ModelListResponse,
    ModelMaterialCreate,
    ModelMaterialResponse,
    ModelProductionDefaults,
    ModelResponse,
    ModelUpdate,
)
from app.services.costing import CostingService
from app.utils.csv_handler import (
    CSVImportError,
    generate_csv_export,
    parse_csv_file,
    parse_date,
    parse_print_time,
)

router = APIRouter()


# Helper function to calculate and attach cost breakdown
async def model_with_cost(model: Model) -> dict:
    """Convert Model to response dict with cost breakdown."""
    # Calculate cost (using default tenant rates - in production, fetch from tenant settings)
    cost_breakdown = CostingService.calculate_model_cost(model)

    return {
        **model.__dict__,
        "cost_breakdown": cost_breakdown,
    }


@router.post("", response_model=ModelDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    model_data: ModelCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ModelDetailResponse:
    """
    Create a new model (printed item).

    Requires authentication.
    Model will be associated with current tenant.
    SKU must be unique per tenant.
    """
    # Check if SKU already exists for this tenant
    existing = await db.execute(
        select(Model).where(
            Model.tenant_id == tenant.id,
            Model.sku == model_data.sku,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model with SKU '{model_data.sku}' already exists",
        )

    # Create model instance
    model = Model(
        tenant_id=tenant.id,
        **model_data.model_dump(),
    )

    db.add(model)
    await db.commit()
    await db.refresh(model)

    return ModelDetailResponse(**await model_with_cost(model))


@router.get("", response_model=ModelListResponse)
async def list_models(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max items to return"),
    search: Optional[str] = Query(None, description="Search by SKU or name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> ModelListResponse:
    """
    List all models for current tenant with pagination and filtering.

    Supports:
    - Pagination (skip, limit)
    - Search (SKU, name)
    - Filter by category
    - Filter by active status

    Returns total_cost for each model (computed from materials and components).
    """
    # Build query
    query = select(Model).where(Model.tenant_id == tenant.id)

    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Model.sku.ilike(search_pattern),
                Model.name.ilike(search_pattern),
            )
        )

    if category:
        query = query.where(Model.category == category)

    if is_active is not None:
        query = query.where(Model.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination and fetch with materials/components for cost calculation
    query = (
        query.options(
            selectinload(Model.materials),
            selectinload(Model.components),
        )
        .order_by(Model.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    models = result.scalars().all()

    # Calculate total_cost for each model
    model_responses = []
    for m in models:
        cost_breakdown = CostingService.calculate_model_cost(m)
        model_dict = {
            **m.__dict__,
            "total_cost": cost_breakdown.total_cost,
        }
        # Remove SQLAlchemy internal state
        model_dict.pop("_sa_instance_state", None)
        model_responses.append(ModelResponse.model_validate(model_dict))

    return ModelListResponse(
        models=model_responses,
        total=total or 0,
        skip=skip,
        limit=limit,
    )


@router.get("/{model_id}", response_model=ModelDetailResponse)
async def get_model(
    model_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ModelDetailResponse:
    """
    Get model detail with BOM, components, and cost breakdown.

    Requires authentication.
    Model must belong to current tenant.
    """
    # Fetch model with relationships
    query = (
        select(Model)
        .where(
            Model.id == model_id,
            Model.tenant_id == tenant.id,
        )
        .options(
            selectinload(Model.materials).selectinload(ModelMaterial.spool),
            selectinload(Model.components),
        )
    )

    result = await db.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    return ModelDetailResponse(**await model_with_cost(model))


@router.get("/{model_id}/production-defaults", response_model=ModelProductionDefaults)
async def get_model_production_defaults(
    model_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ModelProductionDefaults:
    """
    Get production defaults for a model (BOM materials with inventory, printer, print time).

    Used to auto-populate production run creation wizard with suggested materials and settings.

    Returns:
    - Model basic info (id, sku, name)
    - Suggested printer/machine
    - Print time and prints per plate
    - BOM materials with current spool inventory info

    Requires authentication.
    Model must belong to current tenant.
    """
    # Fetch model with BOM materials (and spool + material_type relationships)
    query = (
        select(Model)
        .where(
            Model.id == model_id,
            Model.tenant_id == tenant.id,
        )
        .options(
            selectinload(Model.materials)
            .selectinload(ModelMaterial.spool)
            .selectinload(Spool.material_type)
        )
    )

    result = await db.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Build BOM material suggestions with current spool inventory
    bom_suggestions = []
    for model_material in model.materials:
        spool = model_material.spool
        material_type = spool.material_type

        # Create spool name: "Brand - Material - Color"
        spool_name = f"{spool.brand} - {material_type.code} - {spool.color}"

        bom_suggestion = BOMSpoolSuggestion(
            spool_id=spool.id,
            spool_name=spool_name,
            material_type_code=material_type.code,
            color=spool.color,
            color_hex=spool.color_hex,
            weight_grams=model_material.weight_grams,
            cost_per_gram=model_material.cost_per_gram,
            current_weight=spool.current_weight,
            is_active=spool.is_active,
        )
        bom_suggestions.append(bom_suggestion)

    # Build production defaults response
    return ModelProductionDefaults(
        model_id=model.id,
        sku=model.sku,
        name=model.name,
        machine=model.machine,
        print_time_minutes=model.print_time_minutes,
        prints_per_plate=model.prints_per_plate,
        bom_materials=bom_suggestions,
    )


@router.put("/{model_id}", response_model=ModelDetailResponse)
async def update_model(
    model_id: UUID,
    model_data: ModelUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ModelDetailResponse:
    """
    Update an existing model.

    Requires authentication.
    Model must belong to current tenant.
    """
    # Fetch model
    query = (
        select(Model)
        .where(
            Model.id == model_id,
            Model.tenant_id == tenant.id,
        )
        .options(
            selectinload(Model.materials),
            selectinload(Model.components),
        )
    )

    result = await db.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check SKU uniqueness if changing
    if model_data.sku and model_data.sku != model.sku:
        existing = await db.execute(
            select(Model).where(
                Model.tenant_id == tenant.id,
                Model.sku == model_data.sku,
                Model.id != model_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model with SKU '{model_data.sku}' already exists",
            )

    # Update fields
    update_data = model_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model, field, value)

    await db.commit()
    await db.refresh(model)

    return ModelDetailResponse(**await model_with_cost(model))


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a model (soft delete by setting is_active=False).

    Requires authentication.
    Model must belong to current tenant.
    """
    # Fetch model
    query = select(Model).where(
        Model.id == model_id,
        Model.tenant_id == tenant.id,
    )

    result = await db.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Soft delete
    model.is_active = False
    await db.commit()


# ==================== BOM (Model Materials) Management ====================


@router.post(
    "/{model_id}/materials",
    response_model=ModelMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_model_material(
    model_id: UUID,
    material_data: ModelMaterialCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ModelMaterialResponse:
    """
    Add a material to model's Bill of Materials (BOM).

    Requires authentication.
    Model and spool must belong to current tenant.
    """
    # Verify model exists and belongs to tenant
    model = await db.get(Model, model_id)
    if not model or model.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Verify spool exists and belongs to tenant
    spool = await db.get(Spool, material_data.spool_id)
    if not spool or spool.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spool not found",
        )

    # Create material entry
    material = ModelMaterial(
        model_id=model_id,
        **material_data.model_dump(),
    )

    db.add(material)
    await db.commit()
    await db.refresh(material)

    return ModelMaterialResponse.model_validate(material)


@router.delete("/{model_id}/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_model_material(
    model_id: UUID,
    material_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a material from model's BOM.

    Requires authentication.
    Model must belong to current tenant.
    """
    # Fetch material with model
    query = (
        select(ModelMaterial)
        .join(Model)
        .where(
            ModelMaterial.id == material_id,
            ModelMaterial.model_id == model_id,
            Model.tenant_id == tenant.id,
        )
    )

    result = await db.execute(query)
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )

    await db.delete(material)
    await db.commit()


# ==================== Component Management ====================


@router.post(
    "/{model_id}/components",
    response_model=ModelComponentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_model_component(
    model_id: UUID,
    component_data: ModelComponentCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ModelComponentResponse:
    """
    Add a component to model.

    Requires authentication.
    Model must belong to current tenant.
    """
    # Verify model exists and belongs to tenant
    model = await db.get(Model, model_id)
    if not model or model.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Create component entry
    component = ModelComponent(
        model_id=model_id,
        **component_data.model_dump(),
    )

    db.add(component)
    await db.commit()
    await db.refresh(component)

    return ModelComponentResponse.model_validate(component)


@router.delete("/{model_id}/components/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_model_component(
    model_id: UUID,
    component_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a component from model.

    Requires authentication.
    Model must belong to current tenant.
    """
    # Fetch component with model
    query = (
        select(ModelComponent)
        .join(Model)
        .where(
            ModelComponent.id == component_id,
            ModelComponent.model_id == model_id,
            Model.tenant_id == tenant.id,
        )
    )

    result = await db.execute(query)
    component = result.scalar_one_or_none()

    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )

    await db.delete(component)
    await db.commit()


# ==================== CSV Import/Export ====================


@router.post("/import", status_code=status.HTTP_200_OK)
async def import_models_csv(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """
    Import models from CSV file.

    Supports user's spreadsheet format with columns:
    - ID, Name, SKU, Category, Description
    - Designer, Source, Machine
    - Print Time (13h38m format or minutes)
    - Date Printed Last (DD/MM/YYYY)
    - Units (stock count)
    - Filament1-4, Weight1-4 (multi-material BOM)

    Creates new models or updates existing ones based on SKU.
    Returns summary of import results.
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )

    # Read file content
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read CSV file: {str(e)}",
        )

    # Parse CSV
    try:
        rows = parse_csv_file(csv_content)
    except CSVImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Import models
    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []

    for row in rows:
        try:
            # Check if model exists by SKU
            existing = await db.execute(
                select(Model).where(
                    Model.tenant_id == tenant.id,
                    Model.sku == row.sku,
                )
            )
            model = existing.scalar_one_or_none()

            # Parse special fields
            print_time_minutes = parse_print_time(row.print_time) if row.print_time else None
            last_printed_date = parse_date(row.last_printed_date) if row.last_printed_date else None

            if model:
                # Update existing model
                model.name = row.name
                model.category = row.category
                model.description = row.description
                model.designer = row.designer
                model.source = row.source
                model.machine = row.machine
                model.print_time_minutes = print_time_minutes
                model.last_printed_date = last_printed_date
                model.units_in_stock = row.units_in_stock or 0
                model.labor_hours = row.labor_hours
                model.overhead_percentage = row.overhead_percentage

                updated_count += 1
            else:
                # Create new model
                model = Model(
                    tenant_id=tenant.id,
                    sku=row.sku,
                    name=row.name,
                    category=row.category,
                    description=row.description,
                    designer=row.designer,
                    source=row.source,
                    machine=row.machine,
                    print_time_minutes=print_time_minutes,
                    last_printed_date=last_printed_date,
                    units_in_stock=row.units_in_stock or 0,
                    labor_hours=row.labor_hours,
                    overhead_percentage=row.overhead_percentage,
                )
                db.add(model)
                created_count += 1

        except Exception as e:
            errors.append(f"SKU '{row.sku}': {str(e)}")
            skipped_count += 1
            continue

    # Commit all changes
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save models: {str(e)}",
        )

    return {
        "success": True,
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total_rows": len(rows),
        "errors": errors if errors else None,
    }


@router.get("/export")
async def export_models_csv(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Export all models to CSV file.

    Returns CSV with columns matching import format.
    """
    # Fetch all models with relationships
    query = (
        select(Model)
        .where(
            Model.tenant_id == tenant.id,
            Model.is_active.is_(True),
        )
        .options(
            selectinload(Model.materials).selectinload(ModelMaterial.spool),
        )
        .order_by(Model.created_at.desc())
    )

    result = await db.execute(query)
    models = result.scalars().all()

    # Convert to dicts with cost breakdown
    model_dicts = []
    for model in models:
        model_dict = await model_with_cost(model)
        model_dicts.append(model_dict)

    # Generate CSV
    csv_content = generate_csv_export(model_dicts)

    # Return as downloadable file
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=models_export.csv"},
    )
