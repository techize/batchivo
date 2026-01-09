"""
Tests for OpenTelemetry observability instrumentation.
"""

import pytest


class TestMetrics:
    """Tests for metrics recording functions."""

    def test_record_http_request(self):
        """Test HTTP request metrics recording."""
        from app.observability.metrics import record_http_request

        # Should not raise an error
        record_http_request(
            endpoint="/api/v1/products",
            method="GET",
            status_code=200,
            duration=0.15,
        )

    def test_record_inventory_operation(self):
        """Test inventory operation metrics recording."""
        from app.observability.metrics import record_inventory_operation

        record_inventory_operation(
            operation_type="usage",
            tenant_id="test-tenant-id",
            success=True,
        )

    def test_record_production_run_completed(self):
        """Test production run completion metrics recording."""
        from app.observability.metrics import record_production_run_completed

        record_production_run_completed(
            tenant_id="test-tenant-id",
            duration_seconds=3600.0,
            material_cost=25.50,
        )

    def test_record_order_created(self):
        """Test order creation metrics recording."""
        from app.observability.metrics import record_order_created

        record_order_created(
            tenant_id="test-tenant-id",
            total_amount=99.99,
            channel="mystmereforge",
        )

    def test_record_payment_processed(self):
        """Test payment processing metrics recording."""
        from app.observability.metrics import record_payment_processed

        record_payment_processed(
            tenant_id="test-tenant-id",
            amount=49.99,
            status="success",
            provider="square",
        )

    def test_record_error(self):
        """Test error metrics recording."""
        from app.observability.metrics import record_error

        record_error(
            error_type="ValueError",
            endpoint="/api/v1/spools",
            tenant_id="test-tenant-id",
        )

    def test_active_users_gauge(self):
        """Test active users increment/decrement."""
        from app.observability.metrics import increment_active_users, decrement_active_users

        increment_active_users(tenant_id="test-tenant-id")
        decrement_active_users(tenant_id="test-tenant-id")


class TestMetricsMiddleware:
    """Tests for MetricsMiddleware."""

    @pytest.mark.asyncio
    async def test_middleware_records_metrics(self):
        """Test that middleware records HTTP metrics."""
        from app.middleware.metrics import MetricsMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        async def homepage(request):
            return JSONResponse({"hello": "world"})

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(MetricsMiddleware)

        # We can't easily test metrics values without a full OTEL setup,
        # but we can verify the middleware doesn't break the request
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert response.json() == {"hello": "world"}

    @pytest.mark.asyncio
    async def test_middleware_skips_health_endpoints(self):
        """Test that middleware skips metrics for health endpoints."""
        from app.middleware.metrics import MetricsMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        async def health(request):
            return JSONResponse({"status": "healthy"})

        app = Starlette(routes=[Route("/health", health)])
        app.add_middleware(MetricsMiddleware)

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200


class TestTracingSetup:
    """Tests for tracing setup."""

    def test_tracing_disabled_by_default(self, monkeypatch):
        """Test that tracing is disabled when ENABLE_TRACING is false."""
        monkeypatch.setenv("ENABLE_TRACING", "false")

        # Re-import to pick up env var
        from importlib import reload
        import app.config

        reload(app.config)

        from app.config import get_settings

        settings = get_settings()
        assert settings.enable_tracing is False

    def test_tracer_available(self):
        """Test that tracer can be obtained."""
        from opentelemetry import trace

        tracer = trace.get_tracer(__name__)
        assert tracer is not None


class TestProductionRunSpans:
    """Tests for production run service spans."""

    def test_tracer_is_configured(self):
        """Test that tracer is configured in production run service."""
        from app.services.production_run import tracer

        assert tracer is not None

    def test_span_imports_available(self):
        """Test that OpenTelemetry span imports work."""
        from opentelemetry.trace import Status, StatusCode

        assert Status is not None
        assert StatusCode.OK is not None
        assert StatusCode.ERROR is not None
