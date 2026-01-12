"""OpenTelemetry metrics and Prometheus exporter setup."""

from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from prometheus_client import start_http_server

from app.config import get_settings

settings = get_settings()


def setup_metrics(prometheus_port: int = 9090) -> None:
    """
    Set up OpenTelemetry metrics with Prometheus exporter.

    Exposes metrics on /metrics endpoint for Prometheus scraping.

    Args:
        prometheus_port: Port to expose Prometheus metrics (default: 9090)
    """
    if not settings.enable_metrics:
        print("⏭️  Metrics disabled (ENABLE_METRICS=false)")
        return

    # Create resource with service information
    resource = Resource.create(
        attributes={
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.otel_environment,
        }
    )

    # Set up Prometheus exporter
    try:
        prometheus_reader = PrometheusMetricReader()
        meter_provider = MeterProvider(resource=resource, metric_readers=[prometheus_reader])
        metrics.set_meter_provider(meter_provider)

        # Start Prometheus HTTP server
        start_http_server(port=prometheus_port, addr="0.0.0.0")
        print(f"✓ Prometheus metrics server started on port {prometheus_port}")
        print(f"  Metrics available at http://0.0.0.0:{prometheus_port}/metrics")

    except Exception as e:
        print(f"⚠️  Failed to configure Prometheus exporter: {e}")
        print("   Continuing without metrics export...")


# Global meter for creating instruments
meter = metrics.get_meter(__name__)

# HTTP Request Metrics
http_request_counter = meter.create_counter(
    name="batchivo.http.requests",
    description="Total HTTP requests",
    unit="1",
)

http_request_duration = meter.create_histogram(
    name="batchivo.http.request.duration",
    description="HTTP request duration in seconds",
    unit="s",
)

# Inventory Operation Metrics
inventory_operation_counter = meter.create_counter(
    name="batchivo.inventory.operations",
    description="Inventory operations by type",
    unit="1",
)

spool_weight_updated_counter = meter.create_counter(
    name="batchivo.inventory.spool_weight_updates",
    description="Spool weight update operations",
    unit="1",
)

# Production Run Metrics
production_runs_completed_counter = meter.create_counter(
    name="batchivo.production.runs_completed",
    description="Completed production runs",
    unit="1",
)

production_run_duration = meter.create_histogram(
    name="batchivo.production.run_duration",
    description="Production run duration from creation to completion",
    unit="s",
)

material_cost_calculated = meter.create_histogram(
    name="batchivo.production.material_cost",
    description="Material cost per production run",
    unit="USD",
)

# Order Metrics
order_created_counter = meter.create_counter(
    name="batchivo.orders.created",
    description="Orders created",
    unit="1",
)

order_total_amount = meter.create_histogram(
    name="batchivo.orders.total_amount",
    description="Order total amount",
    unit="USD",
)

payment_processed_counter = meter.create_counter(
    name="batchivo.payments.processed",
    description="Payment transactions processed",
    unit="1",
)

# Error Metrics
error_counter = meter.create_counter(
    name="batchivo.errors",
    description="Application errors by type",
    unit="1",
)

# Active Users Gauge
active_users_gauge = meter.create_up_down_counter(
    name="batchivo.users.active",
    description="Currently active users",
    unit="1",
)


def record_http_request(endpoint: str, method: str, status_code: int, duration: float) -> None:
    """
    Record HTTP request metrics.

    Args:
        endpoint: API endpoint path
        method: HTTP method (GET, POST, etc.)
        status_code: HTTP response status code
        duration: Request duration in seconds
    """
    http_request_counter.add(
        1,
        attributes={
            "http.endpoint": endpoint,
            "http.method": method,
            "http.status_code": status_code,
        },
    )

    http_request_duration.record(
        duration,
        attributes={
            "http.endpoint": endpoint,
            "http.method": method,
        },
    )


def record_inventory_operation(operation_type: str, tenant_id: str, success: bool = True) -> None:
    """
    Record inventory operation.

    Args:
        operation_type: Type of operation (add, update, delete, weight_update)
        tenant_id: Tenant UUID
        success: Whether operation succeeded
    """
    inventory_operation_counter.add(
        1,
        attributes={
            "operation": operation_type,
            "tenant_id": tenant_id,
            "success": str(success),
        },
    )


def record_production_run_completed(
    tenant_id: str, duration_seconds: float, material_cost: float
) -> None:
    """
    Record production run completion.

    Args:
        tenant_id: Tenant UUID
        duration_seconds: Time from creation to completion
        material_cost: Total material cost
    """
    production_runs_completed_counter.add(1, attributes={"tenant_id": tenant_id})

    production_run_duration.record(duration_seconds, attributes={"tenant_id": tenant_id})

    material_cost_calculated.record(material_cost, attributes={"tenant_id": tenant_id})


def record_order_created(tenant_id: str, total_amount: float, channel: str) -> None:
    """
    Record order creation.

    Args:
        tenant_id: Tenant UUID
        total_amount: Order total in USD
        channel: Sales channel name
    """
    order_created_counter.add(
        1,
        attributes={
            "tenant_id": tenant_id,
            "channel": channel,
        },
    )

    order_total_amount.record(
        total_amount,
        attributes={
            "tenant_id": tenant_id,
            "channel": channel,
        },
    )


def record_payment_processed(
    tenant_id: str, amount: float, status: str, provider: str = "square"
) -> None:
    """
    Record payment processing.

    Args:
        tenant_id: Tenant UUID
        amount: Payment amount in USD
        status: Payment status (success, failed, pending)
        provider: Payment provider name
    """
    payment_processed_counter.add(
        1,
        attributes={
            "tenant_id": tenant_id,
            "status": status,
            "provider": provider,
        },
    )


def record_error(error_type: str, endpoint: str = "", tenant_id: str = "") -> None:
    """
    Record application error.

    Args:
        error_type: Type/class of error
        endpoint: API endpoint where error occurred
        tenant_id: Tenant UUID (if applicable)
    """
    error_counter.add(
        1,
        attributes={
            "error_type": error_type,
            "endpoint": endpoint,
            "tenant_id": tenant_id,
        },
    )


def increment_active_users(tenant_id: str) -> None:
    """Increment active users count."""
    active_users_gauge.add(1, attributes={"tenant_id": tenant_id})


def decrement_active_users(tenant_id: str) -> None:
    """Decrement active users count."""
    active_users_gauge.add(-1, attributes={"tenant_id": tenant_id})
