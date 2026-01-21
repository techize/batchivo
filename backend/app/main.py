"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response

logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.core.rate_limit import limiter
from app.database import close_db, init_db
from app.middleware.security import SecurityHeadersMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager (startup and shutdown)."""
    # Startup
    print(f"🚀 Starting {settings.app_name} ({settings.environment})")

    # Initialize Sentry error monitoring (before other services)
    from app.observability.sentry import init_sentry

    if init_sentry():
        print("✓ Sentry error monitoring enabled")

    # Initialize database
    await init_db()
    print("✓ Database initialized")

    # Set up OpenTelemetry (if enabled)
    if settings.enable_tracing:
        from app.observability.tracing import instrument_app, setup_tracing

        setup_tracing()
        from app.database import engine

        instrument_app(app, engine)
        print("✓ OpenTelemetry tracing enabled")

    # Set up OpenTelemetry Metrics (if enabled)
    if settings.enable_metrics:
        from app.observability.metrics import setup_metrics

        setup_metrics(prometheus_port=9090)
        print("✓ OpenTelemetry metrics enabled")

    yield

    # Shutdown
    print("👋 Shutting down...")
    await close_db()
    print("✓ Database connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="3D Print Business Management Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,  # Disable in production
    redoc_url="/redoc" if settings.is_development else None,
    redirect_slashes=False,  # Don't auto-redirect trailing slashes (causes CORS issues)
)

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-ID", "X-Shop-Hostname"],
)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Metrics middleware (before tenant context to track all requests)
if settings.enable_metrics:
    from app.middleware.metrics import MetricsMiddleware

    app.add_middleware(MetricsMiddleware)

# Add tenant context middleware
from app.auth.middleware import TenantContextMiddleware

app.add_middleware(TenantContextMiddleware)


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "environment": settings.environment,
        "docs": "/docs" if settings.is_development else "disabled",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
    }


@app.get("/health/ready")
async def ready():
    """Readiness check (for Kubernetes) - verifies database connectivity."""
    from sqlalchemy import text
    from app.database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=200,
            content={"status": "ready", "database": "connected"},
        )
    except Exception as e:
        # Log the actual error for debugging, but don't expose it in the response
        logger.error(f"Health check failed: database connection error: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "disconnected"},
        )


@app.get("/health/live")
async def live():
    """Liveness check (for Kubernetes)."""
    return JSONResponse(
        status_code=200,
        content={"status": "live"},
    )


# Include API routers
from app.api.v1 import (
    analytics,
    audit,
    auth,
    categories,
    consumables,
    customer_account,
    customer_auth,
    dashboard,
    designers,
    discounts,
    exports,
    forecasting,
    model_files,
    models,
    modules,
    newsletter,
    onboarding,
    orders,
    pages,
    payments,
    platform,
    print_queue,
    printer_bambu,
    printers,
    products,
    production_runs,
    returns,
    reviews,
    sales_channels,
    settings as settings_api,
    shipping,
    shop,
    shop_resolver,
    sku,
    spoolmandb,
    spools,
    tenant_members,
    test,
    users,
    webhooks,
)

app.include_router(auth.router, prefix=f"{settings.api_v1_prefix}/auth", tags=["auth"])
app.include_router(
    onboarding.router,
    prefix=f"{settings.api_v1_prefix}/onboarding",
    tags=["onboarding"],
)
app.include_router(users.router, prefix=f"{settings.api_v1_prefix}/users", tags=["users"])
app.include_router(test.router, prefix=f"{settings.api_v1_prefix}/test", tags=["test"])
app.include_router(spools.router, prefix=f"{settings.api_v1_prefix}/spools", tags=["spools"])
app.include_router(
    consumables.router, prefix=f"{settings.api_v1_prefix}/consumables", tags=["consumables"]
)
app.include_router(models.router, prefix=f"{settings.api_v1_prefix}/models", tags=["models"])
app.include_router(
    model_files.router, prefix=f"{settings.api_v1_prefix}/models", tags=["model-files"]
)
app.include_router(modules.router, prefix=f"{settings.api_v1_prefix}/modules", tags=["modules"])
app.include_router(printers.router, prefix=f"{settings.api_v1_prefix}/printers", tags=["printers"])
app.include_router(
    printer_bambu.router,
    prefix=f"{settings.api_v1_prefix}/printers",
    tags=["printers-bambu"],
)
app.include_router(
    print_queue.router,
    prefix=settings.api_v1_prefix,
    tags=["print-queue"],
)
app.include_router(products.router, prefix=f"{settings.api_v1_prefix}/products", tags=["products"])
app.include_router(
    categories.router, prefix=f"{settings.api_v1_prefix}/categories", tags=["categories"]
)
app.include_router(
    sales_channels.router,
    prefix=f"{settings.api_v1_prefix}/sales-channels",
    tags=["sales-channels"],
)
app.include_router(
    production_runs.router,
    prefix=f"{settings.api_v1_prefix}/production-runs",
    tags=["production-runs"],
)
app.include_router(orders.router, prefix=f"{settings.api_v1_prefix}/orders", tags=["orders"])
app.include_router(
    discounts.router, prefix=f"{settings.api_v1_prefix}/discounts", tags=["discounts"]
)
app.include_router(exports.router, prefix=f"{settings.api_v1_prefix}/exports", tags=["exports"])
app.include_router(pages.router, prefix=f"{settings.api_v1_prefix}/pages", tags=["pages"])
app.include_router(
    spoolmandb.router, prefix=f"{settings.api_v1_prefix}/spoolmandb", tags=["spoolmandb"]
)
app.include_router(sku.router, prefix=f"{settings.api_v1_prefix}/sku", tags=["sku"])
app.include_router(
    dashboard.router, prefix=f"{settings.api_v1_prefix}/dashboard", tags=["dashboard"]
)
app.include_router(
    analytics.router, prefix=f"{settings.api_v1_prefix}/analytics", tags=["analytics"]
)
app.include_router(payments.router, prefix=f"{settings.api_v1_prefix}/payments", tags=["payments"])
app.include_router(shop.router, prefix=f"{settings.api_v1_prefix}/shop", tags=["shop"])
app.include_router(
    shop_resolver.router,
    prefix=f"{settings.api_v1_prefix}/shop-resolver",
    tags=["shop-resolver"],
)
app.include_router(
    designers.router, prefix=f"{settings.api_v1_prefix}/designers", tags=["designers"]
)
app.include_router(
    settings_api.router, prefix=f"{settings.api_v1_prefix}/settings", tags=["settings"]
)
app.include_router(
    tenant_members.router,
    prefix=f"{settings.api_v1_prefix}/tenant/members",
    tags=["tenant-members"],
)
app.include_router(
    customer_auth.router,
    prefix=f"{settings.api_v1_prefix}/customer/auth",
    tags=["customer-auth"],
)
app.include_router(
    customer_account.router,
    prefix=f"{settings.api_v1_prefix}/customer/account",
    tags=["customer-account"],
)
app.include_router(
    reviews.router,
    prefix=f"{settings.api_v1_prefix}/reviews",
    tags=["reviews"],
)
app.include_router(
    returns.router,
    prefix=f"{settings.api_v1_prefix}/returns",
    tags=["returns"],
)
app.include_router(
    forecasting.router,
    prefix=f"{settings.api_v1_prefix}/forecasting",
    tags=["forecasting"],
)
app.include_router(
    shipping.router,
    prefix=f"{settings.api_v1_prefix}/shipping",
    tags=["shipping"],
)
app.include_router(
    audit.router,
    prefix=f"{settings.api_v1_prefix}/audit",
    tags=["audit"],
)
app.include_router(
    webhooks.router,
    prefix=f"{settings.api_v1_prefix}/webhooks",
    tags=["webhooks"],
)
app.include_router(
    newsletter.router,
    prefix=f"{settings.api_v1_prefix}/newsletter",
    tags=["newsletter"],
)

# Platform admin routes (cross-tenant operations)
app.include_router(
    platform.router,
    prefix=settings.api_v1_prefix,
    tags=["platform-admin"],
)


# Dynamic image serving endpoint (works with both local and S3 storage)
@app.get("/uploads/products/{product_id}/{filename}")
async def serve_uploaded_image(product_id: str, filename: str):
    """
    Serve product images from storage (local or S3/MinIO).

    This endpoint handles /uploads/products/{product_id}/{filename} requests
    and works with both local filesystem and S3/MinIO storage backends.
    """
    from app.services.image_storage import get_image_storage, ImageStorageError

    storage = get_image_storage()
    image_url = f"/uploads/products/{product_id}/{filename}"

    try:
        content, content_type = await storage.get_image(image_url)
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
    except ImageStorageError:
        raise HTTPException(status_code=404, detail="Image not found")


# TODO: Include feature routers in future phases
# app.include_router(orders.router, prefix=settings.api_v1_prefix, tags=["orders"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level="debug" if settings.debug else "info",
    )
