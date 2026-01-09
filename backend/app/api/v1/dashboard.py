"""
Dashboard API Endpoints

Provides dashboard data for the authenticated home page including:
- Summary statistics (active prints, completions, failures, low stock)
- Active production runs
- Low stock alerts
- Recent activity feed
- Performance chart data
- Failure analytics
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.production_run import ProductionRun, ProductionRunItem, ProductionRunMaterial
from app.models.spool import Spool
from app.models.inventory_transaction import InventoryTransaction, TransactionType
from app.auth.dependencies import CurrentTenant


router = APIRouter(tags=["dashboard"])


# Response Schemas


class DashboardSummary(BaseModel):
    """Dashboard summary statistics."""

    active_prints: int = Field(description="Count of in_progress production runs")
    completed_today: int = Field(description="Runs completed today")
    failed_today: int = Field(description="Runs failed today")
    cancelled_today: int = Field(description="Runs cancelled today")
    low_stock_count: int = Field(description="Spools below stock threshold")
    success_rate_7d: float = Field(description="7-day success rate (0-100)")
    total_waste_7d_grams: float = Field(description="Total waste in last 7 days (grams)")


class ActiveProductionRun(BaseModel):
    """Active production run for dashboard display."""

    id: UUID
    run_number: str
    started_at: datetime
    printer_name: Optional[str] = None
    estimated_print_time_hours: Optional[float] = None
    items_count: int = Field(description="Number of different models being printed")
    total_quantity: int = Field(description="Total quantity of items")
    products_summary: str = Field(description="Brief summary of what's being printed")

    class Config:
        from_attributes = True


class LowStockSpool(BaseModel):
    """Low stock spool alert."""

    id: UUID
    spool_id: str
    brand: str
    color: str
    color_hex: Optional[str] = None
    material_type: str
    current_weight: float
    initial_weight: float
    percent_remaining: float
    is_critical: bool = Field(description="True if below 5%")

    class Config:
        from_attributes = True


class RecentActivityItem(BaseModel):
    """Recent activity feed item."""

    id: UUID
    transaction_type: str
    created_at: datetime
    spool_id: Optional[str] = None
    spool_color: Optional[str] = None
    weight_change: float
    description: str
    production_run_id: Optional[UUID] = None
    run_number: Optional[str] = None

    class Config:
        from_attributes = True


class SuccessRateTrend(BaseModel):
    """Daily success rate data point."""

    date: str
    success_rate: float
    completed: int
    failed: int


class MaterialUsage(BaseModel):
    """Material usage by type."""

    material_type: str
    total_grams: float
    color: Optional[str] = None


class DailyProduction(BaseModel):
    """Daily production volume."""

    date: str
    items_completed: int
    items_failed: int
    runs_completed: int


class PerformanceChartData(BaseModel):
    """Performance chart data collection."""

    success_rate_trend: list[SuccessRateTrend]
    material_usage: list[MaterialUsage]
    daily_production: list[DailyProduction]


class FailureByReason(BaseModel):
    """Failure count by reason."""

    reason: str
    count: int
    percentage: float


class FailureTrend(BaseModel):
    """Daily failure trend."""

    date: str
    count: int
    reasons: dict[str, int] = Field(default_factory=dict)


class FailureAnalytics(BaseModel):
    """Failure analytics data."""

    failure_by_reason: list[FailureByReason]
    most_common_failures: list[FailureByReason]
    failure_trends: list[FailureTrend]
    total_failures: int
    failure_rate: float = Field(description="Percentage of runs that failed")


# Endpoints


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    low_stock_threshold: int = Query(
        10, ge=1, le=100, description="Low stock threshold percentage"
    ),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get dashboard summary statistics.

    Returns counts for active prints, completions/failures today,
    low stock alerts, and 7-day success rate.
    """
    today = datetime.now().date()
    seven_days_ago = today - timedelta(days=7)

    # Active prints count
    active_result = await db.execute(
        select(func.count(ProductionRun.id)).where(
            and_(ProductionRun.tenant_id == tenant.id, ProductionRun.status == "in_progress")
        )
    )
    active_prints = active_result.scalar() or 0

    # Today's completions
    completed_result = await db.execute(
        select(func.count(ProductionRun.id)).where(
            and_(
                ProductionRun.tenant_id == tenant.id,
                ProductionRun.status == "completed",
                func.date(ProductionRun.completed_at) == today,
            )
        )
    )
    completed_today = completed_result.scalar() or 0

    # Today's failures
    failed_result = await db.execute(
        select(func.count(ProductionRun.id)).where(
            and_(
                ProductionRun.tenant_id == tenant.id,
                ProductionRun.status == "failed",
                func.date(ProductionRun.completed_at) == today,
            )
        )
    )
    failed_today = failed_result.scalar() or 0

    # Today's cancellations
    cancelled_result = await db.execute(
        select(func.count(ProductionRun.id)).where(
            and_(
                ProductionRun.tenant_id == tenant.id,
                ProductionRun.status == "cancelled",
                func.date(ProductionRun.completed_at) == today,
            )
        )
    )
    cancelled_today = cancelled_result.scalar() or 0

    # Low stock count (spools below threshold %)
    low_stock_result = await db.execute(
        select(func.count(Spool.id)).where(
            and_(
                Spool.tenant_id == tenant.id,
                Spool.is_active.is_(True),
                Spool.initial_weight > 0,
                (Spool.current_weight / Spool.initial_weight * 100) < low_stock_threshold,
            )
        )
    )
    low_stock_count = low_stock_result.scalar() or 0

    # 7-day success rate (completed / (completed + failed))
    seven_day_completed = await db.execute(
        select(func.count(ProductionRun.id)).where(
            and_(
                ProductionRun.tenant_id == tenant.id,
                ProductionRun.status == "completed",
                func.date(ProductionRun.completed_at) >= seven_days_ago,
            )
        )
    )
    completed_7d = seven_day_completed.scalar() or 0

    seven_day_failed = await db.execute(
        select(func.count(ProductionRun.id)).where(
            and_(
                ProductionRun.tenant_id == tenant.id,
                ProductionRun.status == "failed",
                func.date(ProductionRun.completed_at) >= seven_days_ago,
            )
        )
    )
    failed_7d = seven_day_failed.scalar() or 0

    total_7d = completed_7d + failed_7d
    success_rate_7d = (completed_7d / total_7d * 100) if total_7d > 0 else 100.0

    # 7-day waste (from WASTE transactions)
    waste_result = await db.execute(
        select(func.coalesce(func.sum(func.abs(InventoryTransaction.weight_change)), 0)).where(
            and_(
                InventoryTransaction.tenant_id == tenant.id,
                InventoryTransaction.transaction_type == TransactionType.WASTE,
                func.date(InventoryTransaction.created_at) >= seven_days_ago,
            )
        )
    )
    total_waste_7d = float(waste_result.scalar() or 0)

    return DashboardSummary(
        active_prints=active_prints,
        completed_today=completed_today,
        failed_today=failed_today,
        cancelled_today=cancelled_today,
        low_stock_count=low_stock_count,
        success_rate_7d=round(success_rate_7d, 1),
        total_waste_7d_grams=total_waste_7d,
    )


@router.get("/active-production", response_model=list[ActiveProductionRun])
async def get_active_production(
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get currently active (in_progress) production runs for dashboard.

    Returns list with essential info for quick overview.
    """
    result = await db.execute(
        select(ProductionRun)
        .options(selectinload(ProductionRun.items).selectinload(ProductionRunItem.model))
        .where(and_(ProductionRun.tenant_id == tenant.id, ProductionRun.status == "in_progress"))
        .order_by(ProductionRun.started_at.desc())
    )
    runs = result.scalars().all()

    active_runs = []
    for run in runs:
        items_count = len(run.items)
        total_quantity = sum(item.quantity for item in run.items)

        # Build products summary
        model_names = []
        for item in run.items[:3]:  # First 3 items
            if item.model:
                model_names.append(f"{item.model.name} x{item.quantity}")
        products_summary = ", ".join(model_names)
        if items_count > 3:
            products_summary += f" +{items_count - 3} more"

        active_runs.append(
            ActiveProductionRun(
                id=run.id,
                run_number=run.run_number,
                started_at=run.started_at,
                printer_name=run.printer_name,
                estimated_print_time_hours=float(run.estimated_print_time_hours)
                if run.estimated_print_time_hours
                else None,
                items_count=items_count,
                total_quantity=total_quantity,
                products_summary=products_summary or "No items",
            )
        )

    return active_runs


@router.get("/low-stock", response_model=list[LowStockSpool])
async def get_low_stock_spools(
    threshold_percent: int = Query(10, ge=1, le=100, description="Stock threshold percentage"),
    limit: int = Query(20, ge=1, le=100, description="Maximum spools to return"),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get spools below stock threshold.

    Returns spools sorted by percent remaining (most critical first).
    """
    result = await db.execute(
        select(Spool)
        .options(selectinload(Spool.material_type))
        .where(
            and_(
                Spool.tenant_id == tenant.id,
                Spool.is_active.is_(True),
                Spool.initial_weight > 0,
                (Spool.current_weight / Spool.initial_weight * 100) < threshold_percent,
            )
        )
        .order_by((Spool.current_weight / Spool.initial_weight).asc())
        .limit(limit)
    )
    spools = result.scalars().all()

    low_stock = []
    for spool in spools:
        percent_remaining = (
            float(spool.current_weight / spool.initial_weight * 100)
            if spool.initial_weight > 0
            else 0
        )
        low_stock.append(
            LowStockSpool(
                id=spool.id,
                spool_id=spool.spool_id,
                brand=spool.brand,
                color=spool.color,
                color_hex=spool.color_hex,
                material_type=spool.material_type.code if spool.material_type else "Unknown",
                current_weight=float(spool.current_weight),
                initial_weight=float(spool.initial_weight),
                percent_remaining=round(percent_remaining, 1),
                is_critical=percent_remaining < 5,
            )
        )

    return low_stock


@router.get("/recent-activity", response_model=list[RecentActivityItem])
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="Maximum items to return"),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get recent inventory transactions for activity feed.

    Returns recent transactions ordered by time, newest first.
    """
    result = await db.execute(
        select(InventoryTransaction)
        .options(
            selectinload(InventoryTransaction.spool),
            selectinload(InventoryTransaction.production_run),
        )
        .where(InventoryTransaction.tenant_id == tenant.id)
        .order_by(InventoryTransaction.created_at.desc())
        .limit(limit)
    )
    transactions = result.scalars().all()

    activity = []
    for tx in transactions:
        activity.append(
            RecentActivityItem(
                id=tx.id,
                transaction_type=tx.transaction_type.value,
                created_at=tx.created_at,
                spool_id=tx.spool.spool_id if tx.spool else None,
                spool_color=tx.spool.color if tx.spool else None,
                weight_change=float(tx.weight_change),
                description=tx.description,
                production_run_id=tx.production_run_id,
                run_number=tx.production_run.run_number if tx.production_run else None,
            )
        )

    return activity


@router.get("/performance-charts", response_model=PerformanceChartData)
async def get_performance_data(
    days: int = Query(7, ge=1, le=90, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get performance chart data for dashboard visualization.

    Returns success rate trends, material usage, and daily production data.
    """
    today = datetime.now().date()
    start_date = today - timedelta(days=days - 1)

    # Success rate trend by day
    success_trend = []
    for i in range(days):
        date = start_date + timedelta(days=i)

        completed_result = await db.execute(
            select(func.count(ProductionRun.id)).where(
                and_(
                    ProductionRun.tenant_id == tenant.id,
                    ProductionRun.status == "completed",
                    func.date(ProductionRun.completed_at) == date,
                )
            )
        )
        completed = completed_result.scalar() or 0

        failed_result = await db.execute(
            select(func.count(ProductionRun.id)).where(
                and_(
                    ProductionRun.tenant_id == tenant.id,
                    ProductionRun.status == "failed",
                    func.date(ProductionRun.completed_at) == date,
                )
            )
        )
        failed = failed_result.scalar() or 0

        total = completed + failed
        rate = (completed / total * 100) if total > 0 else 100.0

        success_trend.append(
            SuccessRateTrend(
                date=date.isoformat(),
                success_rate=round(rate, 1),
                completed=completed,
                failed=failed,
            )
        )

    # Material usage by type (from completed runs in period)
    # Calculate actual weight: prefer spool weighing (before - after), fallback to split actuals sum
    material_usage_result = await db.execute(
        select(
            Spool.color,
            func.sum(
                case(
                    # If we have both before/after weights, use weighing
                    (
                        and_(
                            ProductionRunMaterial.spool_weight_before_grams.isnot(None),
                            ProductionRunMaterial.spool_weight_after_grams.isnot(None),
                        ),
                        ProductionRunMaterial.spool_weight_before_grams
                        - ProductionRunMaterial.spool_weight_after_grams,
                    ),
                    # Otherwise sum the split actual weights
                    else_=(
                        func.coalesce(ProductionRunMaterial.actual_model_weight_grams, 0)
                        + func.coalesce(ProductionRunMaterial.actual_flushed_grams, 0)
                        + func.coalesce(ProductionRunMaterial.actual_tower_grams, 0)
                    ),
                )
            ),
        )
        .select_from(ProductionRunMaterial)
        .join(ProductionRun, ProductionRunMaterial.production_run_id == ProductionRun.id)
        .join(Spool, ProductionRunMaterial.spool_id == Spool.id)
        .where(
            and_(
                ProductionRun.tenant_id == tenant.id,
                ProductionRun.status == "completed",
                func.date(ProductionRun.completed_at) >= start_date,
            )
        )
        .group_by(Spool.color)
    )
    material_usage_rows = material_usage_result.all()

    material_usage = [
        MaterialUsage(
            material_type=row[0] or "Unknown",
            total_grams=float(row[1] or 0),
            color=row[0],
        )
        for row in material_usage_rows
        if row[1] and float(row[1]) > 0
    ]

    # Daily production (items completed/failed per day)
    daily_production = []
    for i in range(days):
        date = start_date + timedelta(days=i)

        # Count items from completed runs
        completed_items_result = await db.execute(
            select(func.sum(ProductionRunItem.successful_quantity))
            .select_from(ProductionRunItem)
            .join(ProductionRun, ProductionRunItem.production_run_id == ProductionRun.id)
            .where(
                and_(
                    ProductionRun.tenant_id == tenant.id,
                    ProductionRun.status == "completed",
                    func.date(ProductionRun.completed_at) == date,
                )
            )
        )
        items_completed = completed_items_result.scalar() or 0

        # Count failed items
        failed_items_result = await db.execute(
            select(func.sum(ProductionRunItem.failed_quantity))
            .select_from(ProductionRunItem)
            .join(ProductionRun, ProductionRunItem.production_run_id == ProductionRun.id)
            .where(
                and_(
                    ProductionRun.tenant_id == tenant.id,
                    func.date(ProductionRun.completed_at) == date,
                )
            )
        )
        items_failed = failed_items_result.scalar() or 0

        # Count completed runs
        runs_result = await db.execute(
            select(func.count(ProductionRun.id)).where(
                and_(
                    ProductionRun.tenant_id == tenant.id,
                    ProductionRun.status == "completed",
                    func.date(ProductionRun.completed_at) == date,
                )
            )
        )
        runs_completed = runs_result.scalar() or 0

        daily_production.append(
            DailyProduction(
                date=date.isoformat(),
                items_completed=items_completed,
                items_failed=items_failed,
                runs_completed=runs_completed,
            )
        )

    return PerformanceChartData(
        success_rate_trend=success_trend,
        material_usage=material_usage,
        daily_production=daily_production,
    )


@router.get("/failure-analytics", response_model=FailureAnalytics)
async def get_failure_analytics(
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get failure analytics data including breakdown by reason and trends.

    Leverages the waste_reason field from the cancel/fail feature.
    """
    today = datetime.now().date()
    start_date = today - timedelta(days=days - 1)

    # Get all failed runs in period
    failed_runs_result = await db.execute(
        select(ProductionRun).where(
            and_(
                ProductionRun.tenant_id == tenant.id,
                ProductionRun.status == "failed",
                func.date(ProductionRun.completed_at) >= start_date,
            )
        )
    )
    failed_runs = failed_runs_result.scalars().all()

    # Count total completed + failed for failure rate
    total_completed_result = await db.execute(
        select(func.count(ProductionRun.id)).where(
            and_(
                ProductionRun.tenant_id == tenant.id,
                ProductionRun.status == "completed",
                func.date(ProductionRun.completed_at) >= start_date,
            )
        )
    )
    total_completed = total_completed_result.scalar() or 0

    total_failures = len(failed_runs)
    total_runs = total_completed + total_failures
    failure_rate = (total_failures / total_runs * 100) if total_runs > 0 else 0.0

    # Group failures by reason
    reason_counts: dict[str, int] = {}
    for run in failed_runs:
        reason = run.waste_reason or "Unknown"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    # Build failure_by_reason with percentages
    failure_by_reason = []
    for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_failures * 100) if total_failures > 0 else 0
        failure_by_reason.append(
            FailureByReason(
                reason=reason,
                count=count,
                percentage=round(percentage, 1),
            )
        )

    # Top 5 most common failures
    most_common_failures = failure_by_reason[:5]

    # Failure trends by day
    failure_trends = []
    for i in range(days):
        date = start_date + timedelta(days=i)

        # Filter runs for this date
        day_runs = [
            run for run in failed_runs if run.completed_at and run.completed_at.date() == date
        ]

        if day_runs:
            day_reasons: dict[str, int] = {}
            for run in day_runs:
                reason = run.waste_reason or "Unknown"
                day_reasons[reason] = day_reasons.get(reason, 0) + 1

            failure_trends.append(
                FailureTrend(
                    date=date.isoformat(),
                    count=len(day_runs),
                    reasons=day_reasons,
                )
            )
        else:
            failure_trends.append(
                FailureTrend(
                    date=date.isoformat(),
                    count=0,
                    reasons={},
                )
            )

    return FailureAnalytics(
        failure_by_reason=failure_by_reason,
        most_common_failures=most_common_failures,
        failure_trends=failure_trends,
        total_failures=total_failures,
        failure_rate=round(failure_rate, 1),
    )
