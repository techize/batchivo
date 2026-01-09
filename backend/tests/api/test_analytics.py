"""Tests for analytics API endpoints."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import MaterialType
from app.models.model import Model
from app.models.product import Product
from app.models.production_run import ProductionRun, ProductionRunItem, ProductionRunMaterial
from app.models.spool import Spool
from app.models.tenant import Tenant


# ============================================
# Fixtures
# ============================================


@pytest_asyncio.fixture
async def analytics_product(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> Product:
    """Create a test product for analytics."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Analytics Test Product",
        sku="ATP-001",
        description="Product for analytics testing",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def analytics_model(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> Model:
    """Create a test model for analytics."""
    model = Model(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="MDL-ANALYTICS-001",
        name="Analytics Test Model",
        print_time_minutes=120,
        is_active=True,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def analytics_spool(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_material_type: MaterialType,
) -> Spool:
    """Create a test spool for analytics."""
    spool = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        spool_id="SPL-ANALYTICS-001",
        brand="TestBrand",
        color="Blue",
        color_hex="#0000FF",
        material_type_id=test_material_type.id,
        initial_weight=1000.0,
        current_weight=800.0,
        is_active=True,
    )
    db_session.add(spool)
    await db_session.commit()
    await db_session.refresh(spool)
    return spool


@pytest_asyncio.fixture
async def completed_production_run(
    db_session: AsyncSession,
    test_tenant: Tenant,
    analytics_model: Model,
    analytics_spool: Spool,
) -> ProductionRun:
    """Create a completed production run with materials and items."""
    run = ProductionRun(
        id=uuid4(),
        tenant_id=test_tenant.id,
        run_number="RUN-ANALYTICS-001",
        status="completed",
        started_at=datetime.now(timezone.utc) - timedelta(hours=4),
        completed_at=datetime.now(timezone.utc) - timedelta(hours=1),
        total_plates=1,
        completed_plates=1,
    )
    db_session.add(run)
    await db_session.flush()

    # Add production run item
    item = ProductionRunItem(
        id=uuid4(),
        production_run_id=run.id,
        model_id=analytics_model.id,
        quantity=5,
        successful_quantity=4,
        failed_quantity=1,
    )
    db_session.add(item)

    # Add production run material
    material = ProductionRunMaterial(
        id=uuid4(),
        production_run_id=run.id,
        spool_id=analytics_spool.id,
        estimated_model_weight_grams=Decimal("50.0"),
        estimated_flushed_grams=Decimal("5.0"),
        estimated_tower_grams=Decimal("0.0"),
        actual_model_weight_grams=Decimal("60.0"),
        cost_per_gram=Decimal("0.025"),
    )
    db_session.add(material)

    await db_session.commit()
    await db_session.refresh(run)
    return run


@pytest_asyncio.fixture
async def production_run_in_progress(
    db_session: AsyncSession,
    test_tenant: Tenant,
    analytics_model: Model,
    analytics_spool: Spool,
) -> ProductionRun:
    """Create an in-progress production run."""
    run = ProductionRun(
        id=uuid4(),
        tenant_id=test_tenant.id,
        run_number="RUN-ANALYTICS-002",
        status="in_progress",
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        total_plates=1,
        completed_plates=0,
    )
    db_session.add(run)
    await db_session.flush()

    item = ProductionRunItem(
        id=uuid4(),
        production_run_id=run.id,
        model_id=analytics_model.id,
        quantity=3,
    )
    db_session.add(item)

    material = ProductionRunMaterial(
        id=uuid4(),
        production_run_id=run.id,
        spool_id=analytics_spool.id,
        estimated_model_weight_grams=Decimal("30.0"),
        estimated_flushed_grams=Decimal("3.0"),
        estimated_tower_grams=Decimal("0.0"),
        cost_per_gram=Decimal("0.025"),
    )
    db_session.add(material)

    await db_session.commit()
    await db_session.refresh(run)
    return run


# ============================================
# Test Classes
# ============================================


class TestVarianceReport:
    """Tests for variance report endpoint."""

    async def test_variance_report_empty(
        self,
        client: AsyncClient,
    ):
        """Test variance report with no data."""
        response = await client.get("/api/v1/analytics/variance-report")
        assert response.status_code == 200
        data = response.json()
        assert "by_product" in data
        assert "highest_variance_runs" in data
        assert "variance_trends" in data
        assert "summary" in data
        assert data["summary"]["total_runs_analyzed"] == 0

    async def test_variance_report_with_data(
        self,
        client: AsyncClient,
        completed_production_run: ProductionRun,
    ):
        """Test variance report with production data."""
        response = await client.get("/api/v1/analytics/variance-report")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        # Should have at least one run analyzed
        assert data["summary"]["total_runs_analyzed"] >= 1

    async def test_variance_report_custom_days(
        self,
        client: AsyncClient,
    ):
        """Test variance report with custom days parameter."""
        response = await client.get("/api/v1/analytics/variance-report?days=60")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data

    async def test_variance_report_with_threshold(
        self,
        client: AsyncClient,
        completed_production_run: ProductionRun,
    ):
        """Test variance report with variance threshold filter."""
        response = await client.get("/api/v1/analytics/variance-report?variance_threshold=5")
        assert response.status_code == 200
        data = response.json()
        # Only runs above threshold should be included
        for run in data["highest_variance_runs"]:
            assert abs(run["variance_percent"]) >= 5

    async def test_variance_report_with_product_filter(
        self,
        client: AsyncClient,
        analytics_product: Product,
    ):
        """Test variance report filtered by product."""
        response = await client.get(
            f"/api/v1/analytics/variance-report?product_id={analytics_product.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "by_product" in data

    async def test_variance_report_invalid_days(
        self,
        client: AsyncClient,
    ):
        """Test variance report with invalid days parameter."""
        response = await client.get("/api/v1/analytics/variance-report?days=0")
        assert response.status_code == 422

        response = await client.get("/api/v1/analytics/variance-report?days=500")
        assert response.status_code == 422

    async def test_variance_report_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/analytics/variance-report")
        assert response.status_code == 401


class TestProductProductionHistory:
    """Tests for product production history endpoint."""

    async def test_production_history_product_not_found(
        self,
        client: AsyncClient,
    ):
        """Test production history for non-existent product."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/analytics/products/{fake_id}/production-history")
        assert response.status_code == 404

    async def test_production_history_empty(
        self,
        client: AsyncClient,
        analytics_product: Product,
    ):
        """Test production history with no runs."""
        response = await client.get(
            f"/api/v1/analytics/products/{analytics_product.id}/production-history"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == str(analytics_product.id)
        assert data["product_name"] == analytics_product.name
        assert data["total_runs"] == 0
        assert data["production_history"] == []

    async def test_production_history_with_runs(
        self,
        client: AsyncClient,
        analytics_product: Product,
        completed_production_run: ProductionRun,
    ):
        """Test production history with production runs."""
        response = await client.get(
            f"/api/v1/analytics/products/{analytics_product.id}/production-history"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == str(analytics_product.id)
        # May or may not have runs depending on model linkage
        assert "production_history" in data
        assert "total_runs" in data
        assert "overall_success_rate" in data

    async def test_production_history_custom_days(
        self,
        client: AsyncClient,
        analytics_product: Product,
    ):
        """Test production history with custom days parameter."""
        response = await client.get(
            f"/api/v1/analytics/products/{analytics_product.id}/production-history?days=180"
        )
        assert response.status_code == 200

    async def test_production_history_with_status_filter(
        self,
        client: AsyncClient,
        analytics_product: Product,
    ):
        """Test production history with status filter."""
        response = await client.get(
            f"/api/v1/analytics/products/{analytics_product.id}/production-history?status_filter=completed"
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["production_history"]:
            assert item["status"] == "completed"

    async def test_production_history_pagination(
        self,
        client: AsyncClient,
        analytics_product: Product,
    ):
        """Test production history pagination."""
        response = await client.get(
            f"/api/v1/analytics/products/{analytics_product.id}/production-history?skip=0&limit=10"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["production_history"]) <= 10

    async def test_production_history_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        fake_id = uuid4()
        response = await unauthenticated_client.get(
            f"/api/v1/analytics/products/{fake_id}/production-history"
        )
        assert response.status_code == 401


class TestSpoolProductionUsage:
    """Tests for spool production usage endpoint."""

    async def test_spool_usage_not_found(
        self,
        client: AsyncClient,
    ):
        """Test spool usage for non-existent spool."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/analytics/spools/{fake_id}/production-usage")
        assert response.status_code == 404

    async def test_spool_usage_empty(
        self,
        client: AsyncClient,
        analytics_spool: Spool,
    ):
        """Test spool usage with no runs."""
        response = await client.get(
            f"/api/v1/analytics/spools/{analytics_spool.id}/production-usage"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["spool_id"] == str(analytics_spool.id)
        assert data["spool_code"] == analytics_spool.spool_id
        assert data["color"] == analytics_spool.color
        assert data["run_count"] == 0
        assert data["usage_history"] == []

    async def test_spool_usage_with_runs(
        self,
        client: AsyncClient,
        analytics_spool: Spool,
        completed_production_run: ProductionRun,
    ):
        """Test spool usage with production runs."""
        response = await client.get(
            f"/api/v1/analytics/spools/{analytics_spool.id}/production-usage"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["spool_id"] == str(analytics_spool.id)
        assert data["run_count"] >= 1
        assert len(data["usage_history"]) >= 1

        # Check usage item structure
        if data["usage_history"]:
            usage = data["usage_history"][0]
            assert "run_id" in usage
            assert "run_number" in usage
            assert "estimated_weight" in usage
            assert "actual_weight" in usage
            assert "variance_grams" in usage
            assert "variance_percent" in usage
            assert "products_printed" in usage

    async def test_spool_usage_custom_days(
        self,
        client: AsyncClient,
        analytics_spool: Spool,
    ):
        """Test spool usage with custom days parameter."""
        response = await client.get(
            f"/api/v1/analytics/spools/{analytics_spool.id}/production-usage?days=180"
        )
        assert response.status_code == 200

    async def test_spool_usage_pagination(
        self,
        client: AsyncClient,
        analytics_spool: Spool,
    ):
        """Test spool usage pagination."""
        response = await client.get(
            f"/api/v1/analytics/spools/{analytics_spool.id}/production-usage?skip=0&limit=10"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["usage_history"]) <= 10

    async def test_spool_usage_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        analytics_spool: Spool,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get(
            f"/api/v1/analytics/spools/{analytics_spool.id}/production-usage"
        )
        assert response.status_code == 401
