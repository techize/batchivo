"""Rate limiting configuration using SlowAPI."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance with IP-based rate limiting
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations for different endpoint types
AUTH_RATE_LIMIT = "5/minute"  # Login, register, password reset attempts
FORGOT_PASSWORD_RATE_LIMIT = "3/minute"  # More restrictive for password reset requests
API_RATE_LIMIT = "100/minute"  # General API endpoints
