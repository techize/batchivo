"""Tenant context middleware for multi-tenant Row-Level Security."""

import logging
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract tenant context for PostgreSQL Row-Level Security.

    This middleware runs early in the request lifecycle and extracts the
    tenant_id from the JWT token (or X-Tenant-ID header). It stores this
    in request.state.tenant_id for use by the RLS database dependency.

    The actual RLS session variable is set by get_tenant_db dependency,
    not by this middleware, because:
    1. Each database session needs SET LOCAL executed on it
    2. Dependencies have access to the same session used by route handlers
    3. This separation keeps middleware fast and non-blocking

    Flow:
    1. TenantContextMiddleware extracts tenant_id -> request.state.tenant_id
    2. Route handler uses get_tenant_db dependency
    3. get_tenant_db reads request.state.tenant_id and sets SET LOCAL
    4. All queries in that session are RLS-filtered
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """
        Extract tenant context from request and store in request.state.

        Priority:
        1. X-Tenant-ID header (explicit tenant selection)
        2. tenant_id from JWT token (default tenant)
        3. None (unauthenticated/public endpoints)
        """
        tenant_id: Optional[UUID] = None

        # Try to extract tenant_id from JWT token
        authorization = request.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            tenant_id = self._extract_tenant_from_token(token)

        # X-Tenant-ID header can override (if user has access - validated by dependency)
        x_tenant_id = request.headers.get("x-tenant-id")
        if x_tenant_id:
            try:
                tenant_id = UUID(x_tenant_id)
            except ValueError:
                # Invalid UUID in header - ignore and use token tenant_id
                logger.warning(f"Invalid X-Tenant-ID header: {x_tenant_id}")

        # Store in request state for use by get_tenant_db dependency
        request.state.tenant_id = tenant_id

        if tenant_id and settings.debug:
            logger.debug(f"Tenant context extracted: {tenant_id}")

        response = await call_next(request)
        return response

    def _extract_tenant_from_token(self, token: str) -> Optional[UUID]:
        """
        Extract tenant_id from JWT token without full validation.

        This is a lightweight extraction for middleware. Full token validation
        happens in get_current_user dependency.
        """
        try:
            # Import here to avoid circular imports
            from app.core.security import decode_token

            token_data = decode_token(token)
            if token_data and token_data.tenant_id:
                return token_data.tenant_id
        except Exception as e:
            # Don't fail the request - just log and continue
            # Full auth validation happens in dependencies
            logger.debug(f"Could not extract tenant from token: {e}")

        return None
