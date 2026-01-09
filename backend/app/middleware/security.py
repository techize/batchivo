"""Security headers middleware for HTTP responses."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all HTTP responses.

    Implements OWASP recommended security headers:
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Legacy XSS protection for older browsers
    - Strict-Transport-Security: Enforce HTTPS
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Restrict browser features
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers to response."""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking - deny all framing
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection for legacy browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTP Strict Transport Security - enforce HTTPS for 1 year
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Control referrer information sent to other sites
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict browser features/permissions
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response
