"""
Analytics API Endpoints

Provides analytics and variance analysis including:
- Variance report across production runs
- Product production history
- Spool usage tracking
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.production_run import ProductionRun, ProductionRunItem, ProductionRunMaterial
from app.models.product import Product
from app.models.model import Model
from app.models.spool import Spool
from app.auth.dependencies import CurrentTenant


router = APIRouter(tags=["analytics"])


# Response Schemas


class ProductVariance(BaseModel):
    """Variance data for a specific product."""

    product_id: UUID
    product_name: str
    sku: Optional[str] = None
    run_count: int
    avg_variance_percent: float = Field(description="Average variance percentage")
    total_estimated_grams: float
    total_actual_grams: float
    min_variance_percent: float
    max_variance_percent: float

    class Config:
        from_attributes = True


class RunVariance(BaseModel):
    """Variance data for a specific run."""

    run_id: UUID
    run_number: str
    completed_at: datetime
    estimated_grams: float
    actual_grams: float
    variance_grams: float
    variance_percent: float

    class Config:
        from_attributes = True


class VarianceTrend(BaseModel):
    """Daily variance trend data."""

    date: str
    avg_variance_percent: float
    run_count: int


class VarianceReportResponse(BaseModel):
    """Comprehensive variance report."""

    by_product: list[ProductVariance]
    highest_variance_runs: list[RunVariance]
    variance_trends: list[VarianceTrend]
    summary: dict = Field(description="Overall summary statistics")


class ProductionHistoryItem(BaseModel):
    """Single production history entry for a product."""

    run_id: UUID
    run_number: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    quantity_planned: int
    quantity_successful: int
    quantity_failed: int
    success_rate: float
    estimated_cost: float
    actual_cost: Optional[float] = None
    variance_percent: Optional[float] = None

    class Config:
        from_attributes = True


class ProductProductionHistoryResponse(BaseModel):
    """Production history for a specific product."""

    product_id: UUID
    product_name: str
    total_runs: int
    total_produced: int
    total_failed: int
    overall_success_rate: float
    avg_estimated_cost: float
    avg_actual_cost: Optional[float] = None
    production_history: list[ProductionHistoryItem]


class SpoolUsageItem(BaseModel):
    """Single usage entry for a spool."""

    run_id: UUID
    run_number: str
    date: datetime
    estimated_weight: float
    actual_weight: float
    variance_grams: float
    variance_percent: float
    products_printed: list[str]

    class Config:
        from_attributes = True


class SpoolUsageResponse(BaseModel):
    """Usage history for a specific spool."""

    spool_id: UUID
    spool_code: str
    color: str
    material_type: str
    total_usage_grams: float
    avg_usage_per_run: float
    run_count: int
    usage_history: list[SpoolUsageItem]


# Endpoints


@router.get("/variance-report", response_model=VarianceReportResponse)
async def get_variance_report(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    product_id: Optional[UUID] = Query(None, description="Filter by specific product"),
    variance_threshold: Optional[float] = Query(
        None, ge=0, description="Only include runs with variance above threshold %"
    ),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get variance analysis report across production runs.

    Returns:
    - Variance breakdown by product (which products consistently over/under estimate)
    - Runs with highest variance
    - Variance trends over time
    - Summary statistics
    """
    start_date = datetime.now() - timedelta(days=days)

    # Get completed runs with materials
    query = (
        select(ProductionRun)
        .options(
            selectinload(ProductionRun.materials).selectinload(ProductionRunMaterial.spool),
            selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
        )
        .where(
            and_(
                ProductionRun.tenant_id == tenant.id,
                ProductionRun.status == "completed",
                ProductionRun.completed_at >= start_date,
            )
        )
        .order_by(ProductionRun.completed_at.desc())
    )

    result = await db.execute(query)
    runs = result.scalars().unique().all()

    # Calculate variance for each run
    run_variances = []
    product_data: dict[UUID, dict] = {}

    for run in runs:
        estimated = sum(float(m.estimated_total_weight) for m in run.materials)
        actual = sum(float(m.actual_total_weight) for m in run.materials)

        if estimated > 0:
            variance_grams = actual - estimated
            variance_percent = (variance_grams / estimated) * 100

            # Apply threshold filter
            if variance_threshold and abs(variance_percent) < variance_threshold:
                continue

            run_variances.append(
                {
                    "run": run,
                    "estimated": estimated,
                    "actual": actual,
                    "variance_grams": variance_grams,
                    "variance_percent": variance_percent,
                }
            )

            # Aggregate by product
            for item in run.items:
                if item.model:
                    # Get product for this model
                    for product_model in getattr(item.model, "products", []):
                        pid = product_model.product_id
                        if pid not in product_data:
                            product_data[pid] = {
                                "product_id": pid,
                                "product_name": "Unknown",
                                "sku": None,
                                "run_count": 0,
                                "total_estimated": 0.0,
                                "total_actual": 0.0,
                                "variances": [],
                            }
                        product_data[pid]["run_count"] += 1
                        product_data[pid]["total_estimated"] += estimated / len(run.items)
                        product_data[pid]["total_actual"] += actual / len(run.items)
                        product_data[pid]["variances"].append(variance_percent)

    # Build by_product list
    by_product = []
    for pid, data in product_data.items():
        if data["variances"]:
            avg_var = sum(data["variances"]) / len(data["variances"])
            by_product.append(
                ProductVariance(
                    product_id=data["product_id"],
                    product_name=data["product_name"],
                    sku=data["sku"],
                    run_count=data["run_count"],
                    avg_variance_percent=round(avg_var, 2),
                    total_estimated_grams=round(data["total_estimated"], 1),
                    total_actual_grams=round(data["total_actual"], 1),
                    min_variance_percent=round(min(data["variances"]), 2),
                    max_variance_percent=round(max(data["variances"]), 2),
                )
            )

    # Sort by absolute average variance
    by_product.sort(key=lambda x: abs(x.avg_variance_percent), reverse=True)

    # Highest variance runs (top 10)
    highest_variance_runs = sorted(
        run_variances, key=lambda x: abs(x["variance_percent"]), reverse=True
    )[:10]

    highest_variance_runs_response = [
        RunVariance(
            run_id=rv["run"].id,
            run_number=rv["run"].run_number,
            completed_at=rv["run"].completed_at,
            estimated_grams=rv["estimated"],
            actual_grams=rv["actual"],
            variance_grams=round(rv["variance_grams"], 1),
            variance_percent=round(rv["variance_percent"], 2),
        )
        for rv in highest_variance_runs
    ]

    # Variance trends by day
    daily_variances: dict[str, list[float]] = {}
    for rv in run_variances:
        date_str = rv["run"].completed_at.strftime("%Y-%m-%d")
        if date_str not in daily_variances:
            daily_variances[date_str] = []
        daily_variances[date_str].append(rv["variance_percent"])

    variance_trends = [
        VarianceTrend(
            date=date,
            avg_variance_percent=round(sum(variances) / len(variances), 2),
            run_count=len(variances),
        )
        for date, variances in sorted(daily_variances.items())
    ]

    # Summary statistics
    all_variances = [rv["variance_percent"] for rv in run_variances]
    summary = {
        "total_runs_analyzed": len(run_variances),
        "avg_variance_percent": round(sum(all_variances) / len(all_variances), 2)
        if all_variances
        else 0,
        "runs_over_estimate": len([v for v in all_variances if v > 0]),
        "runs_under_estimate": len([v for v in all_variances if v < 0]),
        "runs_above_10_percent": len([v for v in all_variances if abs(v) > 10]),
    }

    return VarianceReportResponse(
        by_product=by_product[:20],  # Top 20 products
        highest_variance_runs=highest_variance_runs_response,
        variance_trends=variance_trends,
        summary=summary,
    )


@router.get(
    "/products/{product_id}/production-history", response_model=ProductProductionHistoryResponse
)
async def get_product_production_history(
    product_id: UUID,
    days: int = Query(90, ge=1, le=365, description="Number of days to include"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get production history for a specific product.

    Returns all production runs that included this product with:
    - Quantities planned vs successful vs failed
    - Success rates
    - Cost estimates vs actuals
    """
    # First verify product exists
    product_result = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.tenant_id == tenant.id,
            )
        )
    )
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found"
        )

    start_date = datetime.now() - timedelta(days=days)

    # Get runs that contain models from this product
    query = (
        select(ProductionRun)
        .join(ProductionRunItem)
        .join(Model, ProductionRunItem.model_id == Model.id)
        .where(
            and_(
                ProductionRun.tenant_id == tenant.id,
                ProductionRun.started_at >= start_date,
            )
        )
        .options(
            selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
            selectinload(ProductionRun.materials),
        )
        .distinct()
        .order_by(ProductionRun.started_at.desc())
    )

    if status_filter:
        query = query.where(ProductionRun.status == status_filter)

    result = await db.execute(query.offset(skip).limit(limit))
    runs = result.scalars().unique().all()

    # Build history items
    history_items = []
    total_produced = 0
    total_failed = 0
    estimated_costs = []
    actual_costs = []

    for run in runs:
        # Find items for this product's models
        run_quantity_planned = 0
        run_quantity_successful = 0
        run_quantity_failed = 0

        for item in run.items:
            run_quantity_planned += item.quantity
            run_quantity_successful += item.successful_quantity or 0
            run_quantity_failed += item.failed_quantity or 0

        success_rate = (
            (run_quantity_successful / run_quantity_planned * 100)
            if run_quantity_planned > 0
            else 0
        )

        # Calculate costs
        estimated_cost = sum(
            float(m.estimated_total_weight * m.cost_per_gram) for m in run.materials
        )
        actual_cost = None
        variance_percent = None

        if run.status == "completed":
            actual_cost = sum(float(m.actual_total_weight * m.cost_per_gram) for m in run.materials)
            if estimated_cost > 0:
                variance_percent = ((actual_cost - estimated_cost) / estimated_cost) * 100

        history_items.append(
            ProductionHistoryItem(
                run_id=run.id,
                run_number=run.run_number,
                started_at=run.started_at,
                completed_at=run.completed_at,
                status=run.status,
                quantity_planned=run_quantity_planned,
                quantity_successful=run_quantity_successful,
                quantity_failed=run_quantity_failed,
                success_rate=round(success_rate, 1),
                estimated_cost=round(estimated_cost, 2),
                actual_cost=round(actual_cost, 2) if actual_cost else None,
                variance_percent=round(variance_percent, 2) if variance_percent else None,
            )
        )

        total_produced += run_quantity_successful
        total_failed += run_quantity_failed
        estimated_costs.append(estimated_cost)
        if actual_cost:
            actual_costs.append(actual_cost)

    overall_success_rate = (
        (total_produced / (total_produced + total_failed) * 100)
        if (total_produced + total_failed) > 0
        else 100
    )

    return ProductProductionHistoryResponse(
        product_id=product.id,
        product_name=product.name,
        total_runs=len(runs),
        total_produced=total_produced,
        total_failed=total_failed,
        overall_success_rate=round(overall_success_rate, 1),
        avg_estimated_cost=round(sum(estimated_costs) / len(estimated_costs), 2)
        if estimated_costs
        else 0,
        avg_actual_cost=round(sum(actual_costs) / len(actual_costs), 2) if actual_costs else None,
        production_history=history_items,
    )


@router.get("/spools/{spool_id}/production-usage", response_model=SpoolUsageResponse)
async def get_spool_production_usage(
    spool_id: UUID,
    days: int = Query(90, ge=1, le=365, description="Number of days to include"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get production usage history for a specific spool.

    Returns all production runs that used this spool with:
    - Estimated vs actual weights
    - Variance tracking
    - Products produced in each run
    """
    # Verify spool exists
    spool_result = await db.execute(
        select(Spool)
        .options(selectinload(Spool.material_type))
        .where(
            and_(
                Spool.id == spool_id,
                Spool.tenant_id == tenant.id,
            )
        )
    )
    spool = spool_result.scalar_one_or_none()

    if not spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Spool {spool_id} not found"
        )

    start_date = datetime.now() - timedelta(days=days)

    # Get runs that used this spool
    query = (
        select(ProductionRun)
        .join(ProductionRunMaterial)
        .where(
            and_(
                ProductionRun.tenant_id == tenant.id,
                ProductionRunMaterial.spool_id == spool_id,
                ProductionRun.started_at >= start_date,
            )
        )
        .options(
            selectinload(ProductionRun.materials),
            selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
        )
        .order_by(ProductionRun.started_at.desc())
    )

    result = await db.execute(query.offset(skip).limit(limit))
    runs = result.scalars().unique().all()

    # Build usage items
    usage_items = []
    total_usage = 0.0

    for run in runs:
        # Find the material record for this spool
        material = next((m for m in run.materials if m.spool_id == spool_id), None)

        if material:
            estimated = float(material.estimated_total_weight)
            actual = float(material.actual_total_weight)
            variance_grams = actual - estimated
            variance_percent = (variance_grams / estimated * 100) if estimated > 0 else 0

            # Get product names
            products_printed = [item.model.name if item.model else "Unknown" for item in run.items]

            usage_items.append(
                SpoolUsageItem(
                    run_id=run.id,
                    run_number=run.run_number,
                    date=run.started_at,
                    estimated_weight=round(estimated, 1),
                    actual_weight=round(actual, 1),
                    variance_grams=round(variance_grams, 1),
                    variance_percent=round(variance_percent, 2),
                    products_printed=products_printed,
                )
            )

            total_usage += actual

    avg_usage = total_usage / len(usage_items) if usage_items else 0

    return SpoolUsageResponse(
        spool_id=spool.id,
        spool_code=spool.spool_id,
        color=spool.color,
        material_type=spool.material_type.code if spool.material_type else "Unknown",
        total_usage_grams=round(total_usage, 1),
        avg_usage_per_run=round(avg_usage, 1),
        run_count=len(usage_items),
        usage_history=usage_items,
    )
