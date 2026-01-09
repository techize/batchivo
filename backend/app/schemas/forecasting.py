"""Pydantic schemas for inventory forecasting."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DemandForecastResponse(BaseModel):
    """Demand forecast response for a product."""

    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    product_name: str
    product_sku: str
    current_stock: int

    # Historical metrics
    total_sold: int = Field(description="Total units sold in analysis period")
    days_analyzed: int = Field(description="Number of days analyzed")
    avg_daily_demand: float = Field(description="Average daily demand")
    std_deviation: float = Field(description="Standard deviation of daily demand")

    # Forecast
    forecast_days: int = Field(description="Number of days forecasted")
    predicted_demand: int = Field(description="Predicted demand for forecast period")

    # Stock projections
    days_of_stock: Optional[int] = Field(None, description="Days until stockout at current rate")
    stockout_date: Optional[datetime] = Field(None, description="Estimated stockout date")
    confidence_level: str = Field(description="Forecast confidence: high, medium, or low")


class ReorderRecommendationResponse(BaseModel):
    """Reorder recommendation for a product."""

    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    product_name: str
    product_sku: str
    current_stock: int
    reorder_point: int = Field(description="Stock level at which to reorder")
    safety_stock: int = Field(description="Buffer stock for demand variability")
    avg_daily_demand: float
    lead_time_days: int = Field(description="Expected lead time for restocking")
    recommended_order_qty: int = Field(description="Suggested order quantity")
    urgency: str = Field(description="Urgency level: critical, soon, or ok")
    days_until_stockout: Optional[int] = Field(None, description="Days until stockout")


class ReorderRecommendationsListResponse(BaseModel):
    """List of products needing reorder."""

    items: list[ReorderRecommendationResponse]
    total: int
    critical_count: int = Field(description="Products with critical stock levels")
    soon_count: int = Field(description="Products needing reorder soon")


class StockHealthItemResponse(BaseModel):
    """Stock health status for a product."""

    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    product_name: str
    product_sku: str
    current_stock: int
    avg_daily_demand: float
    days_of_stock: Optional[int]
    reorder_point: int
    status: str = Field(description="Status: critical, low, adequate, overstocked, or no_sales")
    last_sale_date: Optional[datetime]


class StockHealthResponse(BaseModel):
    """Stock health overview for all products."""

    items: list[StockHealthItemResponse]
    total: int
    summary: dict = Field(
        description="Count of products by status",
        default_factory=dict,
    )


class ForecastSettingsRequest(BaseModel):
    """Optional settings for forecast calculations."""

    lead_time_days: int = Field(
        default=7,
        ge=1,
        le=90,
        description="Lead time for restocking in days",
    )
    analysis_days: int = Field(
        default=90,
        ge=7,
        le=365,
        description="Number of days of history to analyze",
    )
    forecast_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to forecast",
    )
