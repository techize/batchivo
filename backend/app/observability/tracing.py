"""OpenTelemetry tracing and instrumentation setup."""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import get_settings

settings = get_settings()


def setup_tracing() -> None:
    """
    Set up OpenTelemetry tracing for the application.

    Instruments:
    - FastAPI (HTTP requests)
    - SQLAlchemy (database queries)

    Exports traces to OTLP endpoint (Tempo via Grafana Agent).
    """
    if not settings.enable_tracing:
        print("⏭️  Tracing disabled (ENABLE_TRACING=false)")
        return

    # Create resource with service information
    resource = Resource.create(
        attributes={
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.otel_environment,
        }
    )

    # Set up tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter (sends to Tempo)
    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=True,  # Use insecure for local development
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        print(f"✓ OTLP exporter configured: {settings.otel_exporter_otlp_endpoint}")
    except Exception as e:
        print(f"⚠️  Failed to configure OTLP exporter: {e}")
        print("   Continuing without tracing export...")

    # Set global tracer provider
    trace.set_tracer_provider(provider)
    print(f"✓ OpenTelemetry tracer initialized: {settings.otel_service_name}")


def instrument_app(app, engine) -> None:
    """
    Instrument FastAPI app and SQLAlchemy engine.

    Args:
        app: FastAPI application instance
        engine: SQLAlchemy async engine
    """
    if not settings.enable_tracing:
        return

    # Instrument FastAPI
    try:
        FastAPIInstrumentor.instrument_app(app)
        print("✓ FastAPI instrumentation enabled")
    except Exception as e:
        print(f"⚠️  FastAPI instrumentation failed: {e}")

    # Instrument SQLAlchemy
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        print("✓ SQLAlchemy instrumentation enabled")
    except Exception as e:
        print(f"⚠️  SQLAlchemy instrumentation failed: {e}")
