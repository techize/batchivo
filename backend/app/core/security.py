"""Security utilities for JWT token handling."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from jwt.exceptions import PyJWTError
from pydantic import ValidationError

from app.schemas.auth import TokenData
from app.config import get_settings

settings = get_settings()

# JWT Configuration from environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing user information to encode
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Dictionary containing user information to encode

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenData | None:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("user_id")
        email: str | None = payload.get("email")
        tenant_id: str | None = payload.get("tenant_id")
        is_platform_admin: bool = payload.get("is_platform_admin", False)

        if user_id is None or email is None:
            return None

        return TokenData(
            user_id=UUID(user_id),
            email=email,
            tenant_id=UUID(tenant_id) if tenant_id else None,
            is_platform_admin=is_platform_admin,
        )
    except (PyJWTError, ValidationError, ValueError) as e:
        print(f"[decode_token] Error decoding token: {type(e).__name__}: {str(e)}")
        print(f"[decode_token] Token preview: {token[:50]}...")
        return None
    except Exception as e:
        print(f"[decode_token] Unexpected error: {type(e).__name__}: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def verify_token_type(token: str, expected_type: str) -> bool:
    """
    Verify that a token is of the expected type (access/refresh).

    Args:
        token: JWT token string
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        True if token type matches, False otherwise
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        return token_type == expected_type
    except PyJWTError:
        return False
