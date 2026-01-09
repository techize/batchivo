"""Consumables inventory API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.consumable import ConsumablePurchase, ConsumableType, ConsumableUsage
from app.schemas.consumable import (
    ConsumablePurchaseCreate,
    ConsumablePurchaseListResponse,
    ConsumablePurchaseResponse,
    ConsumablePurchaseWithType,
    ConsumableTypeCreate,
    ConsumableTypeListResponse,
    ConsumableTypeResponse,
    ConsumableTypeUpdate,
    ConsumableUsageCreate,
    ConsumableUsageListResponse,
    ConsumableUsageResponse,
    ConsumableUsageWithDetails,
    LowStockAlert,
    StockAdjustment,
)

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================


def consumable_type_to_response(consumable: ConsumableType) -> dict:
    """Convert ConsumableType model to response dict."""
    return {
        **{k: v for k, v in consumable.__dict__.items() if not k.startswith("_")},
        "is_low_stock": consumable.is_low_stock,
        "stock_value": consumable.stock_value,
    }


def purchase_to_response(purchase: ConsumablePurchase) -> dict:
    """Convert ConsumablePurchase model to response dict."""
    return {k: v for k, v in purchase.__dict__.items() if not k.startswith("_")}


def usage_to_response(usage: ConsumableUsage) -> dict:
    """Convert ConsumableUsage model to response dict."""
    return {
        **{k: v for k, v in usage.__dict__.items() if not k.startswith("_")},
        "total_cost": usage.total_cost,
    }


# =============================================================================
# ConsumableType Endpoints
# =============================================================================


@router.post("/types", response_model=ConsumableTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_consumable_type(
    consumable_data: ConsumableTypeCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ConsumableTypeResponse:
    """Create a new consumable type."""
    # Check for duplicate SKU
    existing = await db.execute(
        select(ConsumableType).where(
            ConsumableType.tenant_id == tenant.id,
            ConsumableType.sku == consumable_data.sku.upper(),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Consumable with SKU '{consumable_data.sku}' already exists",
        )

    # Create consumable type
    consumable = ConsumableType(
        tenant_id=tenant.id,
        sku=consumable_data.sku.upper(),
        name=consumable_data.name,
        description=consumable_data.description,
        category=consumable_data.category,
        unit_of_measure=consumable_data.unit_of_measure,
        current_cost_per_unit=consumable_data.current_cost_per_unit,
        quantity_on_hand=consumable_data.quantity_on_hand,
        reorder_point=consumable_data.reorder_point,
        reorder_quantity=consumable_data.reorder_quantity,
        preferred_supplier=consumable_data.preferred_supplier,
        supplier_sku=consumable_data.supplier_sku,
        supplier_url=consumable_data.supplier_url,
        typical_lead_days=consumable_data.typical_lead_days,
        is_active=consumable_data.is_active,
    )

    db.add(consumable)
    await db.commit()
    await db.refresh(consumable)

    return ConsumableTypeResponse(**consumable_type_to_response(consumable))


@router.get("/types", response_model=ConsumableTypeListResponse)
async def list_consumable_types(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by SKU or name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    low_stock_only: bool = Query(False, description="Show only low stock items"),
) -> ConsumableTypeListResponse:
    """List all consumable types for current tenant."""
    # Base query
    query = select(ConsumableType).where(ConsumableType.tenant_id == tenant.id)

    # Apply filters
    if search:
        search_filter = or_(
            ConsumableType.sku.ilike(f"%{search}%"),
            ConsumableType.name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if category:
        query = query.where(ConsumableType.category == category)

    if is_active is not None:
        query = query.where(ConsumableType.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(ConsumableType.sku)

    # Execute
    result = await db.execute(query)
    consumables = result.scalars().all()

    # Apply low_stock filter and convert to response
    responses = []
    for consumable in consumables:
        if low_stock_only and not consumable.is_low_stock:
            continue
        responses.append(ConsumableTypeResponse(**consumable_type_to_response(consumable)))

    return ConsumableTypeListResponse(
        total=total,
        consumables=responses,
        page=page,
        page_size=page_size,
    )


@router.get("/types/{consumable_id}", response_model=ConsumableTypeResponse)
async def get_consumable_type(
    consumable_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ConsumableTypeResponse:
    """Get a specific consumable type by ID."""
    result = await db.execute(
        select(ConsumableType).where(
            ConsumableType.id == consumable_id,
            ConsumableType.tenant_id == tenant.id,
        )
    )
    consumable = result.scalar_one_or_none()

    if not consumable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consumable type {consumable_id} not found",
        )

    return ConsumableTypeResponse(**consumable_type_to_response(consumable))


@router.put("/types/{consumable_id}", response_model=ConsumableTypeResponse)
async def update_consumable_type(
    consumable_id: UUID,
    consumable_data: ConsumableTypeUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ConsumableTypeResponse:
    """Update a consumable type."""
    # Get existing
    result = await db.execute(
        select(ConsumableType).where(
            ConsumableType.id == consumable_id,
            ConsumableType.tenant_id == tenant.id,
        )
    )
    consumable = result.scalar_one_or_none()

    if not consumable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consumable type {consumable_id} not found",
        )

    # Update fields
    update_data = consumable_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "sku" and value:
            value = value.upper()
        setattr(consumable, field, value)

    await db.commit()
    await db.refresh(consumable)

    return ConsumableTypeResponse(**consumable_type_to_response(consumable))


@router.delete("/types/{consumable_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_consumable_type(
    consumable_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a consumable type."""
    result = await db.execute(
        select(ConsumableType).where(
            ConsumableType.id == consumable_id,
            ConsumableType.tenant_id == tenant.id,
        )
    )
    consumable = result.scalar_one_or_none()

    if not consumable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consumable type {consumable_id} not found",
        )

    await db.delete(consumable)
    await db.commit()


@router.post("/types/{consumable_id}/adjust-stock", response_model=ConsumableTypeResponse)
async def adjust_stock(
    consumable_id: UUID,
    adjustment: StockAdjustment,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ConsumableTypeResponse:
    """Adjust stock level for a consumable type."""
    result = await db.execute(
        select(ConsumableType).where(
            ConsumableType.id == consumable_id,
            ConsumableType.tenant_id == tenant.id,
        )
    )
    consumable = result.scalar_one_or_none()

    if not consumable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consumable type {consumable_id} not found",
        )

    # Calculate new quantity
    new_quantity = consumable.quantity_on_hand + adjustment.quantity_adjustment
    if new_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reduce stock below 0. Current: {consumable.quantity_on_hand}, Adjustment: {adjustment.quantity_adjustment}",
        )

    # Update stock
    consumable.quantity_on_hand = new_quantity

    # Create usage log for audit trail
    usage = ConsumableUsage(
        tenant_id=tenant.id,
        consumable_type_id=consumable_id,
        quantity_used=abs(adjustment.quantity_adjustment)
        if adjustment.quantity_adjustment < 0
        else -adjustment.quantity_adjustment,
        cost_at_use=consumable.current_cost_per_unit,
        usage_type="adjustment",
        notes=f"{adjustment.reason}. {adjustment.notes or ''}".strip(),
    )
    db.add(usage)

    await db.commit()
    await db.refresh(consumable)

    return ConsumableTypeResponse(**consumable_type_to_response(consumable))


# =============================================================================
# Low Stock Alerts
# =============================================================================


@router.get("/alerts/low-stock", response_model=list[LowStockAlert])
async def get_low_stock_alerts(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> list[LowStockAlert]:
    """Get all consumables that are below their reorder point."""
    result = await db.execute(
        select(ConsumableType).where(
            ConsumableType.tenant_id == tenant.id,
            ConsumableType.is_active.is_(True),
            ConsumableType.reorder_point.isnot(None),
        )
    )
    consumables = result.scalars().all()

    alerts = []
    for consumable in consumables:
        if consumable.is_low_stock:
            alerts.append(
                LowStockAlert(
                    consumable_id=consumable.id,
                    sku=consumable.sku,
                    name=consumable.name,
                    quantity_on_hand=consumable.quantity_on_hand,
                    reorder_point=consumable.reorder_point,
                    reorder_quantity=consumable.reorder_quantity,
                    preferred_supplier=consumable.preferred_supplier,
                    stock_value=consumable.stock_value,
                )
            )

    return alerts


# =============================================================================
# ConsumablePurchase Endpoints
# =============================================================================


@router.post(
    "/purchases", response_model=ConsumablePurchaseResponse, status_code=status.HTTP_201_CREATED
)
async def create_purchase(
    purchase_data: ConsumablePurchaseCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ConsumablePurchaseResponse:
    """Record a new consumable purchase."""
    # Verify consumable type exists
    consumable_result = await db.execute(
        select(ConsumableType).where(
            ConsumableType.id == purchase_data.consumable_type_id,
            ConsumableType.tenant_id == tenant.id,
        )
    )
    consumable = consumable_result.scalar_one_or_none()

    if not consumable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consumable type {purchase_data.consumable_type_id} not found",
        )

    # Calculate cost per unit
    cost_per_unit = purchase_data.total_cost / purchase_data.quantity_purchased

    # Create purchase record
    purchase = ConsumablePurchase(
        tenant_id=tenant.id,
        consumable_type_id=purchase_data.consumable_type_id,
        quantity_purchased=purchase_data.quantity_purchased,
        total_cost=purchase_data.total_cost,
        cost_per_unit=cost_per_unit,
        supplier=purchase_data.supplier,
        order_reference=purchase_data.order_reference,
        purchase_url=purchase_data.purchase_url,
        purchase_date=purchase_data.purchase_date,
        quantity_remaining=purchase_data.quantity_purchased,
        notes=purchase_data.notes,
    )

    db.add(purchase)

    # Update consumable stock and cost
    consumable.quantity_on_hand += purchase_data.quantity_purchased
    consumable.current_cost_per_unit = cost_per_unit

    await db.commit()
    await db.refresh(purchase)

    return ConsumablePurchaseResponse(**purchase_to_response(purchase))


@router.get("/purchases", response_model=ConsumablePurchaseListResponse)
async def list_purchases(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    consumable_type_id: Optional[UUID] = Query(None, description="Filter by consumable type"),
) -> ConsumablePurchaseListResponse:
    """List all consumable purchases."""
    # Base query with join to get consumable info
    query = (
        select(ConsumablePurchase)
        .where(ConsumablePurchase.tenant_id == tenant.id)
        .join(ConsumableType)
    )

    if consumable_type_id:
        query = query.where(ConsumablePurchase.consumable_type_id == consumable_type_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(ConsumablePurchase.created_at.desc())

    # Execute
    result = await db.execute(query)
    purchases = result.scalars().all()

    # Convert to response
    responses = []
    for purchase in purchases:
        response_dict = purchase_to_response(purchase)
        response_dict["consumable_sku"] = purchase.consumable_type.sku
        response_dict["consumable_name"] = purchase.consumable_type.name
        responses.append(ConsumablePurchaseWithType(**response_dict))

    return ConsumablePurchaseListResponse(
        total=total,
        purchases=responses,
        page=page,
        page_size=page_size,
    )


@router.get("/purchases/{purchase_id}", response_model=ConsumablePurchaseWithType)
async def get_purchase(
    purchase_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ConsumablePurchaseWithType:
    """Get a specific purchase by ID."""
    result = await db.execute(
        select(ConsumablePurchase)
        .where(
            ConsumablePurchase.id == purchase_id,
            ConsumablePurchase.tenant_id == tenant.id,
        )
        .join(ConsumableType)
    )
    purchase = result.scalar_one_or_none()

    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Purchase {purchase_id} not found",
        )

    response_dict = purchase_to_response(purchase)
    response_dict["consumable_sku"] = purchase.consumable_type.sku
    response_dict["consumable_name"] = purchase.consumable_type.name

    return ConsumablePurchaseWithType(**response_dict)


@router.delete("/purchases/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase(
    purchase_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a purchase record (also reverses stock increase)."""
    result = await db.execute(
        select(ConsumablePurchase)
        .where(
            ConsumablePurchase.id == purchase_id,
            ConsumablePurchase.tenant_id == tenant.id,
        )
        .join(ConsumableType)
    )
    purchase = result.scalar_one_or_none()

    if not purchase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Purchase {purchase_id} not found",
        )

    # Reverse stock increase
    consumable = purchase.consumable_type
    new_quantity = consumable.quantity_on_hand - purchase.quantity_remaining
    if new_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete purchase: would result in negative stock",
        )

    consumable.quantity_on_hand = new_quantity

    await db.delete(purchase)
    await db.commit()


# =============================================================================
# ConsumableUsage Endpoints
# =============================================================================


@router.post("/usage", response_model=ConsumableUsageResponse, status_code=status.HTTP_201_CREATED)
async def record_usage(
    usage_data: ConsumableUsageCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ConsumableUsageResponse:
    """Record consumable usage (deduct from stock)."""
    # Verify consumable type exists
    consumable_result = await db.execute(
        select(ConsumableType).where(
            ConsumableType.id == usage_data.consumable_type_id,
            ConsumableType.tenant_id == tenant.id,
        )
    )
    consumable = consumable_result.scalar_one_or_none()

    if not consumable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consumable type {usage_data.consumable_type_id} not found",
        )

    # Check sufficient stock for usage (not returns)
    if usage_data.quantity_used > 0 and consumable.quantity_on_hand < usage_data.quantity_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {consumable.quantity_on_hand}, Requested: {usage_data.quantity_used}",
        )

    # Create usage record
    usage = ConsumableUsage(
        tenant_id=tenant.id,
        consumable_type_id=usage_data.consumable_type_id,
        production_run_id=usage_data.production_run_id,
        product_id=usage_data.product_id,
        quantity_used=usage_data.quantity_used,
        cost_at_use=consumable.current_cost_per_unit,
        usage_type=usage_data.usage_type,
        notes=usage_data.notes,
    )

    db.add(usage)

    # Update stock (positive = deduct, negative = return)
    consumable.quantity_on_hand -= usage_data.quantity_used

    await db.commit()
    await db.refresh(usage)

    return ConsumableUsageResponse(**usage_to_response(usage))


@router.get("/usage", response_model=ConsumableUsageListResponse)
async def list_usage(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    consumable_type_id: Optional[UUID] = Query(None, description="Filter by consumable type"),
    usage_type: Optional[str] = Query(None, description="Filter by usage type"),
) -> ConsumableUsageListResponse:
    """List all consumable usage records."""
    query = (
        select(ConsumableUsage).where(ConsumableUsage.tenant_id == tenant.id).join(ConsumableType)
    )

    if consumable_type_id:
        query = query.where(ConsumableUsage.consumable_type_id == consumable_type_id)

    if usage_type:
        query = query.where(ConsumableUsage.usage_type == usage_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(ConsumableUsage.created_at.desc())

    # Execute
    result = await db.execute(query)
    usages = result.scalars().all()

    # Convert to response
    responses = []
    for usage in usages:
        response_dict = usage_to_response(usage)
        response_dict["consumable_sku"] = usage.consumable_type.sku
        response_dict["consumable_name"] = usage.consumable_type.name
        responses.append(ConsumableUsageWithDetails(**response_dict))

    return ConsumableUsageListResponse(
        total=total,
        usage=responses,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Category Helpers
# =============================================================================


@router.get("/categories", response_model=list[str])
async def list_categories(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Get all unique categories used by this tenant."""
    result = await db.execute(
        select(ConsumableType.category)
        .where(
            ConsumableType.tenant_id == tenant.id,
            ConsumableType.category.isnot(None),
        )
        .distinct()
        .order_by(ConsumableType.category)
    )
    categories = result.scalars().all()
    return [c for c in categories if c]
