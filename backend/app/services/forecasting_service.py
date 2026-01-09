"""Inventory forecasting service for demand prediction and reorder recommendations.

Uses Simple Moving Average with safety stock calculations for inventory planning.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product


@dataclass
class DailyDemand:
    """Daily demand data point."""

    date: datetime
    quantity: int


@dataclass
class DemandForecast:
    """Demand forecast for a product."""

    product_id: UUID
    product_name: str
    product_sku: str
    current_stock: int
    # Historical metrics (last 90 days)
    total_sold: int
    days_analyzed: int
    avg_daily_demand: float
    std_deviation: float
    # Forecast
    forecast_days: int
    predicted_demand: int
    # Stock projections
    days_of_stock: Optional[int]  # None if no demand
    stockout_date: Optional[datetime]
    confidence_level: str  # "high", "medium", "low" based on data quality


@dataclass
class ReorderRecommendation:
    """Reorder recommendation for a product."""

    product_id: UUID
    product_name: str
    product_sku: str
    current_stock: int
    reorder_point: int
    safety_stock: int
    avg_daily_demand: float
    lead_time_days: int
    recommended_order_qty: int
    urgency: str  # "critical", "soon", "ok"
    days_until_stockout: Optional[int]


@dataclass
class StockHealthItem:
    """Stock health status for a product."""

    product_id: UUID
    product_name: str
    product_sku: str
    current_stock: int
    avg_daily_demand: float
    days_of_stock: Optional[int]
    reorder_point: int
    status: str  # "critical", "low", "adequate", "overstocked", "no_sales"
    last_sale_date: Optional[datetime]


class ForecastingService:
    """Service for inventory demand forecasting and reorder planning."""

    # Configuration
    DEFAULT_ANALYSIS_DAYS = 90
    DEFAULT_FORECAST_DAYS = 30
    DEFAULT_LEAD_TIME_DAYS = 7
    SAFETY_FACTOR = 1.65  # ~95% service level

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_sales_history(
        self,
        product_id: UUID,
        tenant_id: UUID,
        days: int = DEFAULT_ANALYSIS_DAYS,
    ) -> list[DailyDemand]:
        """Get daily sales history for a product."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Query completed orders with this product
        result = await self.db.execute(
            select(
                func.date(Order.created_at).label("sale_date"),
                func.sum(OrderItem.quantity).label("total_qty"),
            )
            .join(OrderItem, Order.id == OrderItem.order_id)
            .where(
                Order.tenant_id == tenant_id,
                OrderItem.product_id == product_id,
                Order.created_at >= cutoff_date,
                Order.status.in_(
                    [
                        OrderStatus.PENDING,
                        OrderStatus.PROCESSING,
                        OrderStatus.SHIPPED,
                        OrderStatus.DELIVERED,
                    ]
                ),
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )

        rows = result.all()
        demands = []
        for row in rows:
            # Handle both date objects (PostgreSQL) and strings (SQLite)
            sale_date = row.sale_date
            if isinstance(sale_date, str):
                sale_date = datetime.strptime(sale_date, "%Y-%m-%d").date()
            demands.append(
                DailyDemand(
                    date=datetime.combine(sale_date, datetime.min.time()),
                    quantity=int(row.total_qty),
                )
            )
        return demands

    def _calculate_statistics(
        self, sales_history: list[DailyDemand], analysis_days: int
    ) -> tuple[float, float, int]:
        """Calculate average daily demand and standard deviation.

        Returns (avg_daily, std_dev, total_sold).
        """
        if not sales_history:
            return 0.0, 0.0, 0

        total_sold = sum(d.quantity for d in sales_history)
        avg_daily = total_sold / analysis_days

        if len(sales_history) < 2:
            return avg_daily, 0.0, total_sold

        # Calculate std deviation of daily sales
        # Include zero-sale days in calculation
        daily_quantities = {d.date.date(): d.quantity for d in sales_history}

        # Create full range of days
        all_days = []
        start_date = datetime.now(timezone.utc) - timedelta(days=analysis_days)
        for i in range(analysis_days):
            day = (start_date + timedelta(days=i)).date()
            all_days.append(daily_quantities.get(day, 0))

        # Calculate standard deviation
        mean = sum(all_days) / len(all_days)
        variance = sum((x - mean) ** 2 for x in all_days) / len(all_days)
        std_dev = math.sqrt(variance)

        return avg_daily, std_dev, total_sold

    def _get_confidence_level(self, sales_history: list[DailyDemand], analysis_days: int) -> str:
        """Determine forecast confidence based on data quality."""
        if not sales_history:
            return "low"

        days_with_sales = len(sales_history)
        coverage = days_with_sales / analysis_days

        if coverage >= 0.3 and days_with_sales >= 10:
            return "high"
        elif coverage >= 0.1 and days_with_sales >= 5:
            return "medium"
        return "low"

    async def predict_demand(
        self,
        product_id: UUID,
        tenant_id: UUID,
        forecast_days: int = DEFAULT_FORECAST_DAYS,
        analysis_days: int = DEFAULT_ANALYSIS_DAYS,
    ) -> Optional[DemandForecast]:
        """Predict demand for a product over the forecast period."""
        # Get product info
        product_result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
            )
        )
        product = product_result.scalar_one_or_none()

        if not product:
            return None

        # Get sales history
        sales_history = await self.get_sales_history(product_id, tenant_id, analysis_days)

        # Calculate statistics
        avg_daily, std_dev, total_sold = self._calculate_statistics(sales_history, analysis_days)

        # Forecast demand
        predicted_demand = round(avg_daily * forecast_days)

        # Calculate days of stock
        days_of_stock = None
        stockout_date = None
        if avg_daily > 0:
            days_of_stock = int(product.units_in_stock / avg_daily)
            stockout_date = datetime.now(timezone.utc) + timedelta(days=days_of_stock)

        return DemandForecast(
            product_id=product.id,
            product_name=product.name,
            product_sku=product.sku,
            current_stock=product.units_in_stock,
            total_sold=total_sold,
            days_analyzed=analysis_days,
            avg_daily_demand=round(avg_daily, 2),
            std_deviation=round(std_dev, 2),
            forecast_days=forecast_days,
            predicted_demand=predicted_demand,
            days_of_stock=days_of_stock,
            stockout_date=stockout_date,
            confidence_level=self._get_confidence_level(sales_history, analysis_days),
        )

    async def calculate_reorder_point(
        self,
        product_id: UUID,
        tenant_id: UUID,
        lead_time_days: int = DEFAULT_LEAD_TIME_DAYS,
    ) -> Optional[ReorderRecommendation]:
        """Calculate reorder point and recommendation for a product."""
        # Get demand forecast first
        forecast = await self.predict_demand(product_id, tenant_id)
        if not forecast:
            return None

        avg_daily = forecast.avg_daily_demand
        std_dev = forecast.std_deviation

        # Calculate safety stock (covers variability during lead time)
        # Safety stock = Z * σ * √(lead_time)
        safety_stock = int(self.SAFETY_FACTOR * std_dev * math.sqrt(lead_time_days))

        # Reorder point = (avg_daily * lead_time) + safety_stock
        reorder_point = int(avg_daily * lead_time_days) + safety_stock

        # Economic Order Quantity (simplified)
        # Recommend ordering ~30 days of stock
        recommended_qty = max(int(avg_daily * 30), 1) if avg_daily > 0 else 0

        # Determine urgency
        if forecast.current_stock <= 0:
            urgency = "critical"
        elif forecast.current_stock <= reorder_point:
            urgency = "soon"
        else:
            urgency = "ok"

        return ReorderRecommendation(
            product_id=forecast.product_id,
            product_name=forecast.product_name,
            product_sku=forecast.product_sku,
            current_stock=forecast.current_stock,
            reorder_point=reorder_point,
            safety_stock=safety_stock,
            avg_daily_demand=avg_daily,
            lead_time_days=lead_time_days,
            recommended_order_qty=recommended_qty,
            urgency=urgency,
            days_until_stockout=forecast.days_of_stock,
        )

    async def get_reorder_recommendations(
        self,
        tenant_id: UUID,
        lead_time_days: int = DEFAULT_LEAD_TIME_DAYS,
    ) -> list[ReorderRecommendation]:
        """Get reorder recommendations for all products that need attention."""
        # Get all active products
        products_result = await self.db.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.is_active.is_(True),
            )
        )
        products = products_result.scalars().all()

        recommendations = []
        for product in products:
            rec = await self.calculate_reorder_point(product.id, tenant_id, lead_time_days)
            if rec and rec.urgency in ["critical", "soon"]:
                recommendations.append(rec)

        # Sort by urgency (critical first) then by days until stockout
        urgency_order = {"critical": 0, "soon": 1, "ok": 2}
        recommendations.sort(
            key=lambda r: (
                urgency_order.get(r.urgency, 99),
                r.days_until_stockout or 0,
            )
        )

        return recommendations

    async def get_stock_health(self, tenant_id: UUID) -> list[StockHealthItem]:
        """Get stock health status for all products."""
        # Get all active products
        products_result = await self.db.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.is_active.is_(True),
            )
        )
        products = products_result.scalars().all()

        health_items = []
        for product in products:
            forecast = await self.predict_demand(product.id, tenant_id)
            if not forecast:
                continue

            reorder_point = await self.calculate_reorder_point(product.id, tenant_id)

            # Determine status
            if forecast.avg_daily_demand == 0:
                # Check if there were any sales ever
                last_sale = await self._get_last_sale_date(product.id, tenant_id)
                status = "no_sales"
            elif forecast.current_stock <= 0:
                status = "critical"
                last_sale = await self._get_last_sale_date(product.id, tenant_id)
            elif reorder_point and forecast.current_stock <= reorder_point.reorder_point:
                status = "low"
                last_sale = await self._get_last_sale_date(product.id, tenant_id)
            elif forecast.days_of_stock and forecast.days_of_stock > 180:
                status = "overstocked"
                last_sale = await self._get_last_sale_date(product.id, tenant_id)
            else:
                status = "adequate"
                last_sale = await self._get_last_sale_date(product.id, tenant_id)

            health_items.append(
                StockHealthItem(
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    current_stock=product.units_in_stock,
                    avg_daily_demand=forecast.avg_daily_demand,
                    days_of_stock=forecast.days_of_stock,
                    reorder_point=reorder_point.reorder_point if reorder_point else 0,
                    status=status,
                    last_sale_date=last_sale,
                )
            )

        # Sort by status severity
        status_order = {
            "critical": 0,
            "low": 1,
            "no_sales": 2,
            "adequate": 3,
            "overstocked": 4,
        }
        health_items.sort(key=lambda h: status_order.get(h.status, 99))

        return health_items

    async def _get_last_sale_date(self, product_id: UUID, tenant_id: UUID) -> Optional[datetime]:
        """Get the date of the last sale for a product."""
        result = await self.db.execute(
            select(func.max(Order.created_at))
            .join(OrderItem, Order.id == OrderItem.order_id)
            .where(
                Order.tenant_id == tenant_id,
                OrderItem.product_id == product_id,
                Order.status.in_(
                    [
                        OrderStatus.PENDING,
                        OrderStatus.PROCESSING,
                        OrderStatus.SHIPPED,
                        OrderStatus.DELIVERED,
                    ]
                ),
            )
        )
        return result.scalar()
