"""Middleware for automatic HTTP metrics recording."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically record HTTP request metrics.

    Records:
    - Request count by endpoint, method, and status code
    - Request duration histogram
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and record metrics.

        Args:
            request: FastAPI Request object
            call_next: Next middleware/handler in chain

        Returns:
            Response from the handler
        """
        # Skip metrics for certain paths
        if not settings.enable_metrics or request.url.path in [
            "/metrics",
            "/health",
            "/health/live",
            "/health/ready",
        ]:
            return await call_next(request)

        # Import here to avoid circular dependency
        from app.observability.metrics import record_http_request

        # Record start time
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Record error metrics
            status_code = 500
            from app.observability.metrics import record_error

            record_error(
                error_type=type(e).__name__,
                endpoint=request.url.path,
                tenant_id="",
            )
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Record HTTP metrics
            record_http_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=status_code,
                duration=duration,
            )

        return response
