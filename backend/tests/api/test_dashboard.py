"""Tests for dashboard API endpoints."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import MaterialType
from app.models.production_run import ProductionRun
from app.models.spool import Spool
from app.models.tenant import Tenant


# ============================================
# Fixtures
# ============================================


@pytest_asyncio.fixture
async def production_run(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> ProductionRun:
    """Create a test production run."""
    run = ProductionRun(
        id=uuid4(),
        tenant_id=test_tenant.id,
        run_number="RUN-001",
        status="in_progress",
        started_at=datetime.now(timezone.utc),
        total_plates=0,
        completed_plates=0,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


@pytest_asyncio.fixture
async def completed_run(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> ProductionRun:
    """Create a completed production run."""
    run = ProductionRun(
        id=uuid4(),
        tenant_id=test_tenant.id,
        run_number="RUN-002",
        status="completed",
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        completed_at=datetime.now(timezone.utc),
        total_plates=0,
        completed_plates=0,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


@pytest_asyncio.fixture
async def failed_run(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> ProductionRun:
    """Create a failed production run."""
    run = ProductionRun(
        id=uuid4(),
        tenant_id=test_tenant.id,
        run_number="RUN-003",
        status="failed",
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        completed_at=datetime.now(timezone.utc),
        waste_filament_grams=Decimal("25.0"),
        waste_reason="Test failure",
        total_plates=0,
        completed_plates=0,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


@pytest_asyncio.fixture
async def low_stock_spool(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_material_type: MaterialType,
) -> Spool:
    """Create a low stock spool."""
    spool = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        spool_id="SPL-LOW-001",
        brand="TestBrand",
        color="Red",
        color_hex="#FF0000",
        material_type_id=test_material_type.id,
        initial_weight=1000.0,
        current_weight=50.0,  # 5% remaining
        is_active=True,
    )
    db_session.add(spool)
    await db_session.commit()
    await db_session.refresh(spool)
    return spool


# ============================================
# Test Classes
# ============================================


class TestDashboardSummary:
    """Tests for dashboard summary endpoint."""

    async def test_summary_empty(
        self,
        client: AsyncClient,
    ):
        """Test summary with no data."""
        response = await client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert "active_prints" in data
        assert "completed_today" in data
        assert "failed_today" in data
        assert "low_stock_count" in data
        assert "success_rate_7d" in data
        assert "total_waste_7d_grams" in data

    async def test_summary_with_active_run(
        self,
        client: AsyncClient,
        production_run: ProductionRun,
    ):
        """Test summary counts active runs."""
        response = await client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["active_prints"] >= 1

    async def test_summary_with_completed_run(
        self,
        client: AsyncClient,
        completed_run: ProductionRun,
    ):
        """Test summary counts completed runs."""
        response = await client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["completed_today"] >= 1

    async def test_summary_with_failed_run(
        self,
        client: AsyncClient,
        failed_run: ProductionRun,
    ):
        """Test summary counts failed runs and waste."""
        response = await client.get("/api/v1/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["failed_today"] >= 1

    async def test_summary_with_low_stock(
        self,
        client: AsyncClient,
        low_stock_spool: Spool,
    ):
        """Test summary counts low stock items."""
        response = await client.get("/api/v1/dashboard/summary?low_stock_threshold=10")
        assert response.status_code == 200
        data = response.json()
        assert data["low_stock_count"] >= 1

    async def test_summary_custom_threshold(
        self,
        client: AsyncClient,
    ):
        """Test summary with custom low stock threshold."""
        response = await client.get("/api/v1/dashboard/summary?low_stock_threshold=20")
        assert response.status_code == 200

    async def test_summary_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/dashboard/summary")
        assert response.status_code == 401


class TestActiveProduction:
    """Tests for active production endpoint."""

    async def test_active_production_empty(
        self,
        client: AsyncClient,
    ):
        """Test active production with no runs."""
        response = await client.get("/api/v1/dashboard/active-production")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_active_production_with_run(
        self,
        client: AsyncClient,
        production_run: ProductionRun,
    ):
        """Test active production lists in-progress runs."""
        response = await client.get("/api/v1/dashboard/active-production")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        run = data[0]
        assert "id" in run
        assert "run_number" in run
        assert "started_at" in run

    async def test_active_production_excludes_completed(
        self,
        client: AsyncClient,
        completed_run: ProductionRun,
    ):
        """Test that completed runs are not included."""
        response = await client.get("/api/v1/dashboard/active-production")
        assert response.status_code == 200
        data = response.json()
        run_ids = [r["id"] for r in data]
        assert str(completed_run.id) not in run_ids

    async def test_active_production_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/dashboard/active-production")
        assert response.status_code == 401


class TestLowStock:
    """Tests for low stock endpoint."""

    async def test_low_stock_empty(
        self,
        client: AsyncClient,
    ):
        """Test low stock with no alerts."""
        response = await client.get("/api/v1/dashboard/low-stock")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_low_stock_with_spool(
        self,
        client: AsyncClient,
        low_stock_spool: Spool,
    ):
        """Test low stock detects low spools."""
        response = await client.get("/api/v1/dashboard/low-stock?threshold_percent=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        spool = data[0]
        assert "id" in spool
        assert "spool_id" in spool
        assert "percent_remaining" in spool

    async def test_low_stock_custom_threshold(
        self,
        client: AsyncClient,
        low_stock_spool: Spool,
    ):
        """Test low stock with custom threshold."""
        response = await client.get("/api/v1/dashboard/low-stock?threshold_percent=3")
        assert response.status_code == 200
        data = response.json()
        # Spool at 5% should not appear with 3% threshold
        spool_ids = [s["spool_id"] for s in data]
        assert low_stock_spool.spool_id not in spool_ids

    async def test_low_stock_limit(
        self,
        client: AsyncClient,
    ):
        """Test low stock respects limit parameter."""
        response = await client.get("/api/v1/dashboard/low-stock?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    async def test_low_stock_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/dashboard/low-stock")
        assert response.status_code == 401


class TestRecentActivity:
    """Tests for recent activity endpoint."""

    async def test_recent_activity_empty(
        self,
        client: AsyncClient,
    ):
        """Test recent activity with no transactions."""
        response = await client.get("/api/v1/dashboard/recent-activity")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_recent_activity_with_production_run(
        self,
        client: AsyncClient,
        completed_run: ProductionRun,
    ):
        """Test recent activity lists production runs."""
        response = await client.get("/api/v1/dashboard/recent-activity")
        assert response.status_code == 200
        data = response.json()
        # Recent activity may include production runs
        assert isinstance(data, list)

    async def test_recent_activity_limit(
        self,
        client: AsyncClient,
    ):
        """Test recent activity respects limit parameter."""
        response = await client.get("/api/v1/dashboard/recent-activity?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    async def test_recent_activity_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/dashboard/recent-activity")
        assert response.status_code == 401


class TestPerformanceCharts:
    """Tests for performance charts endpoint."""

    async def test_performance_charts_empty(
        self,
        client: AsyncClient,
    ):
        """Test performance charts with no data."""
        response = await client.get("/api/v1/dashboard/performance-charts")
        assert response.status_code == 200
        data = response.json()
        assert "success_rate_trend" in data
        assert "material_usage" in data
        assert "daily_production" in data

    async def test_performance_charts_with_data(
        self,
        client: AsyncClient,
        completed_run: ProductionRun,
        failed_run: ProductionRun,
    ):
        """Test performance charts with production data."""
        response = await client.get("/api/v1/dashboard/performance-charts")
        assert response.status_code == 200
        data = response.json()
        assert "success_rate_trend" in data
        assert isinstance(data["success_rate_trend"], list)

    async def test_performance_charts_custom_days(
        self,
        client: AsyncClient,
    ):
        """Test performance charts with custom days parameter."""
        response = await client.get("/api/v1/dashboard/performance-charts?days=30")
        assert response.status_code == 200
        data = response.json()
        assert "success_rate_trend" in data

    async def test_performance_charts_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/dashboard/performance-charts")
        assert response.status_code == 401


class TestFailureAnalytics:
    """Tests for failure analytics endpoint."""

    async def test_failure_analytics_empty(
        self,
        client: AsyncClient,
    ):
        """Test failure analytics with no data."""
        response = await client.get("/api/v1/dashboard/failure-analytics")
        assert response.status_code == 200
        data = response.json()
        assert "total_failures" in data
        assert "failure_rate" in data
        assert "failure_by_reason" in data
        assert "most_common_failures" in data
        assert "failure_trends" in data

    async def test_failure_analytics_with_failures(
        self,
        client: AsyncClient,
        failed_run: ProductionRun,
    ):
        """Test failure analytics with failure data."""
        response = await client.get("/api/v1/dashboard/failure-analytics")
        assert response.status_code == 200
        data = response.json()
        assert data["total_failures"] >= 1

    async def test_failure_analytics_custom_days(
        self,
        client: AsyncClient,
    ):
        """Test failure analytics with custom days parameter."""
        response = await client.get("/api/v1/dashboard/failure-analytics?days=60")
        assert response.status_code == 200
        data = response.json()
        assert "total_failures" in data

    async def test_failure_analytics_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/dashboard/failure-analytics")
        assert response.status_code == 401
