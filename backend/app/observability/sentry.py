"""Sentry error monitoring integration for Batchivo backend.

Provides centralized error tracking, performance monitoring, and release tracking
with Sentry. Integrates with FastAPI ASGI middleware for automatic request tracing.
"""

import logging
import subprocess

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.config import get_settings

logger = logging.getLogger(__name__)


def get_git_release() -> str | None:
    """Get the current git commit hash for release tracking."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return f"batchivo-backend@{result.stdout.strip()}"
    except Exception:
        pass
    return None


def init_sentry() -> bool:
    """
    Initialize Sentry SDK for error monitoring.

    Returns:
        bool: True if Sentry was initialized successfully, False otherwise.
    """
    settings = get_settings()

    # Check if Sentry DSN is configured
    sentry_dsn = getattr(settings, "sentry_dsn", None)
    if not sentry_dsn:
        logger.info("Sentry DSN not configured, skipping initialization")
        return False

    # Get release version from git or settings
    release = get_git_release()

    # Configure sample rates based on environment
    traces_sample_rate = 0.1  # 10% in production
    profiles_sample_rate = 0.1

    if settings.environment == "development":
        traces_sample_rate = 1.0  # 100% in development
        profiles_sample_rate = 1.0
    elif settings.environment == "staging":
        traces_sample_rate = 0.5  # 50% in staging
        profiles_sample_rate = 0.5

    try:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.environment,
            release=release,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            # Send PII only in development for debugging
            send_default_pii=settings.is_development,
            # Attach request data to events
            request_bodies="medium",
            # Enable performance monitoring
            enable_tracing=True,
            # Integrations
            integrations=[
                # FastAPI and Starlette for request/response tracing
                StarletteIntegration(
                    transaction_style="endpoint",
                ),
                FastApiIntegration(
                    transaction_style="endpoint",
                ),
                # SQLAlchemy for database query tracing
                SqlalchemyIntegration(),
                # Redis for cache operation tracing
                RedisIntegration(),
                # Celery for background job tracing
                CeleryIntegration(),
                # Logging integration - capture errors from logging
                LoggingIntegration(
                    level=logging.INFO,  # Capture INFO and above
                    event_level=logging.ERROR,  # Only send ERROR and above as events
                ),
            ],
            # Filter out health check endpoints from performance data
            traces_sampler=traces_sampler,
            # Add custom tags
            before_send=before_send,
        )

        logger.info(f"Sentry initialized (env={settings.environment}, release={release})")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def traces_sampler(sampling_context: dict) -> float:
    """
    Custom traces sampler to filter out noisy endpoints.

    Args:
        sampling_context: Context about the transaction being sampled.

    Returns:
        Sample rate (0.0 to 1.0) or None to use default rate.
    """
    settings = get_settings()

    # Get transaction name if available
    transaction_context = sampling_context.get("transaction_context", {})
    name = transaction_context.get("name", "")

    # Never trace health check endpoints
    if any(path in name for path in ["/health", "/ready", "/live", "/metrics"]):
        return 0.0

    # Lower sample rate for high-volume endpoints
    if "/api/v1/dashboard" in name or "/api/v1/analytics" in name:
        return 0.05  # 5% for dashboard/analytics

    # Use environment-based defaults
    if settings.environment == "development":
        return 1.0
    elif settings.environment == "staging":
        return 0.5
    else:
        return 0.1


def before_send(event: dict, hint: dict) -> dict | None:
    """
    Process events before sending to Sentry.

    Can be used to filter, modify, or enrich events.

    Args:
        event: The Sentry event dictionary.
        hint: Additional context about the event.

    Returns:
        Modified event dict, or None to drop the event.
    """
    # Don't send events for expected/handled exceptions
    if "exc_info" in hint:
        exc_type, exc_value, exc_tb = hint["exc_info"]

        # Don't report 404s or rate limit errors as Sentry issues
        from fastapi import HTTPException
        from slowapi.errors import RateLimitExceeded

        if isinstance(exc_value, HTTPException):
            if exc_value.status_code in [404, 401, 403, 429]:
                return None

        if isinstance(exc_value, RateLimitExceeded):
            return None

    # Add custom context
    settings = get_settings()
    event.setdefault("tags", {})
    event["tags"]["app.name"] = settings.app_name
    event["tags"]["storage.type"] = settings.storage_type

    return event


def capture_exception(error: Exception, **extra) -> str | None:
    """
    Manually capture an exception and send to Sentry.

    Args:
        error: The exception to capture.
        **extra: Additional context to attach to the event.

    Returns:
        Event ID if captured, None otherwise.
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in extra.items():
            scope.set_extra(key, value)
        return sentry_sdk.capture_exception(error)


def capture_message(message: str, level: str = "info", **extra) -> str | None:
    """
    Capture a message and send to Sentry.

    Args:
        message: The message to capture.
        level: Severity level (debug, info, warning, error, fatal).
        **extra: Additional context to attach to the event.

    Returns:
        Event ID if captured, None otherwise.
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in extra.items():
            scope.set_extra(key, value)
        return sentry_sdk.capture_message(message, level=level)


def set_user(user_id: str | None, email: str | None = None, **extra) -> None:
    """
    Set user context for Sentry events.

    Call this when a user is authenticated to associate errors with users.

    Args:
        user_id: The user's unique identifier.
        email: The user's email address.
        **extra: Additional user attributes.
    """
    user_data = {"id": user_id}
    if email:
        user_data["email"] = email
    user_data.update(extra)
    sentry_sdk.set_user(user_data)


def set_tenant(tenant_id: str, tenant_name: str | None = None) -> None:
    """
    Set tenant context for Sentry events.

    Call this when tenant context is established to associate errors with tenants.

    Args:
        tenant_id: The tenant's unique identifier.
        tenant_name: The tenant's display name.
    """
    sentry_sdk.set_tag("tenant.id", tenant_id)
    if tenant_name:
        sentry_sdk.set_tag("tenant.name", tenant_name)
