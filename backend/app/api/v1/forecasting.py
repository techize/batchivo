"""Inventory forecasting API endpoints.

Provides demand prediction, reorder recommendations, and stock health analysis.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.schemas.forecasting import (
    DemandForecastResponse,
    ReorderRecommendationResponse,
    ReorderRecommendationsListResponse,
    StockHealthItemResponse,
    StockHealthResponse,
)
from app.services.forecasting_service import ForecastingService

router = APIRouter()


@router.get("/demand/{product_id}", response_model=DemandForecastResponse)
async def get_demand_forecast(
    product_id: UUID,
    forecast_days: int = Query(30, ge=1, le=365, description="Number of days to forecast"),
    analysis_days: int = Query(90, ge=7, le=365, description="Days of history to analyze"),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get demand forecast for a specific product.

    Uses historical sales data to predict future demand and estimate stockout dates.

    - **forecast_days**: How far ahead to predict (default: 30 days)
    - **analysis_days**: How much history to analyze (default: 90 days)
    """
    service = ForecastingService(db)
    forecast = await service.predict_demand(
        product_id=product_id,
        tenant_id=tenant.id,
        forecast_days=forecast_days,
        analysis_days=analysis_days,
    )

    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return DemandForecastResponse(
        product_id=forecast.product_id,
        product_name=forecast.product_name,
        product_sku=forecast.product_sku,
        current_stock=forecast.current_stock,
        total_sold=forecast.total_sold,
        days_analyzed=forecast.days_analyzed,
        avg_daily_demand=forecast.avg_daily_demand,
        std_deviation=forecast.std_deviation,
        forecast_days=forecast.forecast_days,
        predicted_demand=forecast.predicted_demand,
        days_of_stock=forecast.days_of_stock,
        stockout_date=forecast.stockout_date,
        confidence_level=forecast.confidence_level,
    )


@router.get("/reorder/{product_id}", response_model=ReorderRecommendationResponse)
async def get_product_reorder_recommendation(
    product_id: UUID,
    lead_time_days: int = Query(7, ge=1, le=90, description="Expected lead time for restocking"),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get reorder recommendation for a specific product.

    Calculates optimal reorder point and suggested order quantity based on
    demand patterns and lead time.
    """
    service = ForecastingService(db)
    recommendation = await service.calculate_reorder_point(
        product_id=product_id,
        tenant_id=tenant.id,
        lead_time_days=lead_time_days,
    )

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return ReorderRecommendationResponse(
        product_id=recommendation.product_id,
        product_name=recommendation.product_name,
        product_sku=recommendation.product_sku,
        current_stock=recommendation.current_stock,
        reorder_point=recommendation.reorder_point,
        safety_stock=recommendation.safety_stock,
        avg_daily_demand=recommendation.avg_daily_demand,
        lead_time_days=recommendation.lead_time_days,
        recommended_order_qty=recommendation.recommended_order_qty,
        urgency=recommendation.urgency,
        days_until_stockout=recommendation.days_until_stockout,
    )


@router.get("/reorder-recommendations", response_model=ReorderRecommendationsListResponse)
async def get_reorder_recommendations(
    lead_time_days: int = Query(7, ge=1, le=90, description="Expected lead time for restocking"),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get reorder recommendations for all products needing attention.

    Returns products with 'critical' or 'soon' urgency levels, sorted by
    urgency and days until stockout.
    """
    service = ForecastingService(db)
    recommendations = await service.get_reorder_recommendations(
        tenant_id=tenant.id,
        lead_time_days=lead_time_days,
    )

    critical_count = sum(1 for r in recommendations if r.urgency == "critical")
    soon_count = sum(1 for r in recommendations if r.urgency == "soon")

    return ReorderRecommendationsListResponse(
        items=[
            ReorderRecommendationResponse(
                product_id=r.product_id,
                product_name=r.product_name,
                product_sku=r.product_sku,
                current_stock=r.current_stock,
                reorder_point=r.reorder_point,
                safety_stock=r.safety_stock,
                avg_daily_demand=r.avg_daily_demand,
                lead_time_days=r.lead_time_days,
                recommended_order_qty=r.recommended_order_qty,
                urgency=r.urgency,
                days_until_stockout=r.days_until_stockout,
            )
            for r in recommendations
        ],
        total=len(recommendations),
        critical_count=critical_count,
        soon_count=soon_count,
    )


@router.get("/stock-health", response_model=StockHealthResponse)
async def get_stock_health(
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get stock health overview for all products.

    Returns stock status for each product categorized as:
    - **critical**: Out of stock or below safety level
    - **low**: Below reorder point
    - **adequate**: Healthy stock levels
    - **overstocked**: More than 180 days of stock
    - **no_sales**: No sales history to analyze
    """
    service = ForecastingService(db)
    health_items = await service.get_stock_health(tenant_id=tenant.id)

    # Build summary
    summary = {
        "critical": 0,
        "low": 0,
        "adequate": 0,
        "overstocked": 0,
        "no_sales": 0,
    }
    for item in health_items:
        if item.status in summary:
            summary[item.status] += 1

    return StockHealthResponse(
        items=[
            StockHealthItemResponse(
                product_id=item.product_id,
                product_name=item.product_name,
                product_sku=item.product_sku,
                current_stock=item.current_stock,
                avg_daily_demand=item.avg_daily_demand,
                days_of_stock=item.days_of_stock,
                reorder_point=item.reorder_point,
                status=item.status,
                last_sale_date=item.last_sale_date,
            )
            for item in health_items
        ],
        total=len(health_items),
        summary=summary,
    )
