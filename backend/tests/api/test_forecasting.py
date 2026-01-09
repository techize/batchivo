"""Tests for inventory forecasting API endpoints."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product


class TestForecastingEndpoints:
    """Tests for forecasting API endpoints."""

    @pytest.fixture
    async def product_with_sales(self, test_tenant, db_session):
        """Create a product with sales history."""
        # Create product
        product = Product(
            tenant_id=test_tenant.id,
            sku="FORECAST-001",
            name="Forecast Test Product",
            shop_visible=True,
            is_active=True,
            units_in_stock=50,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Create orders over past 30 days
        now = datetime.now(timezone.utc)
        for i in range(30):
            order_date = now - timedelta(days=i)
            order = Order(
                tenant_id=test_tenant.id,
                order_number=f"ORD-FC-{i:03d}",
                status=OrderStatus.DELIVERED,
                customer_email="forecast@example.com",
                customer_name="Forecast Customer",
                shipping_address_line1="123 Forecast St",
                shipping_city="London",
                shipping_postcode="SW1A 1AA",
                shipping_country="GB",
                shipping_method="Royal Mail 2nd Class",
                subtotal=25.00,
                shipping_cost=5.00,
                total=30.00,
                created_at=order_date,
            )
            db_session.add(order)
            await db_session.flush()

            # Vary quantity (1-3 per day)
            qty = (i % 3) + 1
            order_item = OrderItem(
                tenant_id=test_tenant.id,
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                quantity=qty,
                unit_price=25.00,
                total_price=25.00 * qty,
            )
            db_session.add(order_item)

        await db_session.commit()
        return product

    @pytest.fixture
    async def product_no_sales(self, test_tenant, db_session):
        """Create a product with no sales."""
        product = Product(
            tenant_id=test_tenant.id,
            sku="FORECAST-002",
            name="No Sales Product",
            shop_visible=True,
            is_active=True,
            units_in_stock=100,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product

    @pytest.fixture
    async def low_stock_product(self, test_tenant, db_session):
        """Create a product with low stock and high demand."""
        product = Product(
            tenant_id=test_tenant.id,
            sku="FORECAST-003",
            name="Low Stock Product",
            shop_visible=True,
            is_active=True,
            units_in_stock=5,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Create consistent high demand (5 per day)
        now = datetime.now(timezone.utc)
        for i in range(30):
            order_date = now - timedelta(days=i)
            order = Order(
                tenant_id=test_tenant.id,
                order_number=f"ORD-LS-{i:03d}",
                status=OrderStatus.DELIVERED,
                customer_email="lowstock@example.com",
                customer_name="Low Stock Customer",
                shipping_address_line1="456 Low St",
                shipping_city="London",
                shipping_postcode="EC1A 1BB",
                shipping_country="GB",
                shipping_method="Royal Mail 2nd Class",
                subtotal=50.00,
                shipping_cost=5.00,
                total=55.00,
                created_at=order_date,
            )
            db_session.add(order)
            await db_session.flush()

            order_item = OrderItem(
                tenant_id=test_tenant.id,
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                quantity=5,
                unit_price=50.00,
                total_price=250.00,
            )
            db_session.add(order_item)

        await db_session.commit()
        return product

    @pytest.mark.asyncio
    async def test_get_demand_forecast(
        self,
        client: AsyncClient,
        product_with_sales,
    ):
        """Test getting demand forecast for a product."""
        response = await client.get(f"/api/v1/forecasting/demand/{product_with_sales.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == str(product_with_sales.id)
        assert data["product_sku"] == "FORECAST-001"
        assert data["current_stock"] == 50
        assert data["total_sold"] > 0
        assert data["avg_daily_demand"] > 0
        assert data["predicted_demand"] > 0
        assert data["confidence_level"] in ["high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_get_demand_forecast_custom_params(
        self,
        client: AsyncClient,
        product_with_sales,
    ):
        """Test demand forecast with custom parameters."""
        response = await client.get(
            f"/api/v1/forecasting/demand/{product_with_sales.id}",
            params={"forecast_days": 60, "analysis_days": 30},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["forecast_days"] == 60
        assert data["days_analyzed"] == 30

    @pytest.mark.asyncio
    async def test_get_demand_forecast_no_sales(
        self,
        client: AsyncClient,
        product_no_sales,
    ):
        """Test demand forecast for product with no sales history."""
        response = await client.get(f"/api/v1/forecasting/demand/{product_no_sales.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total_sold"] == 0
        assert data["avg_daily_demand"] == 0
        assert data["predicted_demand"] == 0
        assert data["days_of_stock"] is None
        assert data["confidence_level"] == "low"

    @pytest.mark.asyncio
    async def test_get_demand_forecast_not_found(
        self,
        client: AsyncClient,
    ):
        """Test demand forecast for non-existent product."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/forecasting/demand/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_reorder_recommendation(
        self,
        client: AsyncClient,
        product_with_sales,
    ):
        """Test getting reorder recommendation for a product."""
        response = await client.get(f"/api/v1/forecasting/reorder/{product_with_sales.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == str(product_with_sales.id)
        assert data["reorder_point"] >= 0
        assert data["safety_stock"] >= 0
        assert data["recommended_order_qty"] >= 0
        assert data["urgency"] in ["critical", "soon", "ok"]
        assert data["lead_time_days"] == 7  # Default

    @pytest.mark.asyncio
    async def test_get_reorder_recommendation_custom_lead_time(
        self,
        client: AsyncClient,
        product_with_sales,
    ):
        """Test reorder recommendation with custom lead time."""
        response = await client.get(
            f"/api/v1/forecasting/reorder/{product_with_sales.id}",
            params={"lead_time_days": 14},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["lead_time_days"] == 14

    @pytest.mark.asyncio
    async def test_get_reorder_recommendation_low_stock(
        self,
        client: AsyncClient,
        low_stock_product,
    ):
        """Test reorder recommendation for low stock product."""
        response = await client.get(f"/api/v1/forecasting/reorder/{low_stock_product.id}")

        assert response.status_code == 200
        data = response.json()
        # High demand (5/day) with only 5 units should be critical or soon
        assert data["urgency"] in ["critical", "soon"]

    @pytest.mark.asyncio
    async def test_get_reorder_recommendations_list(
        self,
        client: AsyncClient,
        product_with_sales,
        low_stock_product,
    ):
        """Test getting reorder recommendations for all products."""
        response = await client.get("/api/v1/forecasting/reorder-recommendations")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "critical_count" in data
        assert "soon_count" in data
        # Low stock product should appear
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_stock_health(
        self,
        client: AsyncClient,
        product_with_sales,
        product_no_sales,
        low_stock_product,
    ):
        """Test getting stock health overview."""
        response = await client.get("/api/v1/forecasting/stock-health")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "summary" in data
        assert data["total"] >= 3  # At least our 3 test products

        # Check summary has expected keys
        summary = data["summary"]
        assert "critical" in summary
        assert "low" in summary
        assert "adequate" in summary
        assert "overstocked" in summary
        assert "no_sales" in summary

    @pytest.mark.asyncio
    async def test_stock_health_includes_status(
        self,
        client: AsyncClient,
        product_no_sales,
    ):
        """Test stock health correctly identifies no_sales status."""
        response = await client.get("/api/v1/forecasting/stock-health")

        assert response.status_code == 200
        data = response.json()

        # Find our no-sales product
        no_sales_item = next(
            (item for item in data["items"] if item["product_sku"] == "FORECAST-002"), None
        )
        assert no_sales_item is not None
        assert no_sales_item["status"] == "no_sales"
        assert no_sales_item["avg_daily_demand"] == 0

    @pytest.mark.asyncio
    async def test_stock_health_low_stock_status(
        self,
        client: AsyncClient,
        low_stock_product,
    ):
        """Test stock health correctly identifies low/critical status."""
        response = await client.get("/api/v1/forecasting/stock-health")

        assert response.status_code == 200
        data = response.json()

        # Find our low-stock product
        low_stock_item = next(
            (item for item in data["items"] if item["product_sku"] == "FORECAST-003"), None
        )
        assert low_stock_item is not None
        # With 5 units and ~5/day demand, should be critical or low
        assert low_stock_item["status"] in ["critical", "low"]
