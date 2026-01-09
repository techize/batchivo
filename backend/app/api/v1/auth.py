"""Authentication API endpoints."""

import logging
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter, AUTH_RATE_LIMIT, FORGOT_PASSWORD_RATE_LIMIT
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
)
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserTenant, UserRole
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    TokenRefresh,
    PasswordResetRequest,
    PasswordResetConfirm,
)

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_RATE_LIMIT)
async def register(
    request: Request, user_data: UserRegister, db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Register a new user and create their personal workspace.

    This endpoint:
    1. Creates a new user account
    2. Creates a personal tenant/workspace for the user
    3. Links the user to their workspace with OWNER role
    4. Returns JWT tokens for immediate login
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    new_user = User(email=user_data.email, full_name=user_data.full_name, is_active=True)
    new_user.set_password(user_data.password)

    db.add(new_user)
    await db.flush()  # Get user ID

    # Create personal tenant/workspace
    tenant_name = user_data.tenant_name or f"{user_data.email}'s Workspace"
    tenant_slug = user_data.email.split("@")[0].lower().replace(".", "-")

    new_tenant = Tenant(name=tenant_name, slug=tenant_slug, is_active=True, settings={})
    db.add(new_tenant)
    await db.flush()  # Get tenant ID

    # Link user to tenant with OWNER role
    user_tenant = UserTenant(user_id=new_user.id, tenant_id=new_tenant.id, role=UserRole.OWNER)
    db.add(user_tenant)
    await db.commit()

    # Create tokens
    token_data = {
        "user_id": str(new_user.id),
        "email": new_user.email,
        "tenant_id": str(new_tenant.id),
        "is_platform_admin": new_user.is_platform_admin,
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=Token)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: Request, credentials: UserLogin, db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Authenticate a user and return JWT tokens.

    Returns access and refresh tokens for the user's primary workspace.
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not user.verify_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    # Get user's primary tenant (first one, or could be configurable)
    result = await db.execute(select(UserTenant).where(UserTenant.user_id == user.id).limit(1))
    user_tenant = result.scalar_one_or_none()

    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no associated workspace",
        )

    # Create tokens
    token_data = {
        "user_id": str(user.id),
        "email": user.email,
        "tenant_id": str(user_tenant.tenant_id),
        "is_platform_admin": user.is_platform_admin,
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh, db: AsyncSession = Depends(get_db)) -> Token:
    """
    Refresh an access token using a refresh token.

    Returns a new access token (and optionally a new refresh token).
    """
    # Verify it's a refresh token
    if not verify_token_type(token_data.refresh_token, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode the refresh token
    decoded = decode_token(token_data.refresh_token)
    if not decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == decoded.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    # Create new tokens (fetch fresh is_platform_admin from user)
    new_token_data = {
        "user_id": str(decoded.user_id),
        "email": decoded.email,
        "tenant_id": str(decoded.tenant_id) if decoded.tenant_id else None,
        "is_platform_admin": user.is_platform_admin,
    }

    access_token = create_access_token(new_token_data)
    new_refresh_token = create_refresh_token(new_token_data)

    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout")
async def logout():
    """
    Logout current user.

    For JWT-based auth, logout is handled client-side by discarding tokens.
    Server-side revocation could be added in the future with a token blacklist.
    """
    return {"message": "Logged out successfully. Please discard your tokens client-side."}


@router.post("/forgot-password")
@limiter.limit(FORGOT_PASSWORD_RATE_LIMIT)
async def forgot_password(
    request: Request, request_data: PasswordResetRequest, db: AsyncSession = Depends(get_db)
):
    """
    Request a password reset token.

    Generates a secure reset token and stores it with 1-hour expiration.
    In production, this would send an email with a reset link.
    For now, returns success even if email doesn't exist (security best practice).
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == request_data.email))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    # Only generate token if user actually exists
    if user:
        # Generate secure random token
        reset_token = secrets.token_urlsafe(32)

        # Set expiration to 1 hour from now (Unix timestamp)
        expiration = int(time.time()) + 3600

        # Store token and expiration
        user.reset_token = reset_token
        user.reset_token_expires = expiration

        await db.commit()

        # Send password reset email
        email_service = get_email_service()
        email_sent = email_service.send_admin_password_reset(
            to_email=user.email,
            user_name=user.full_name or user.email.split("@")[0],
            reset_token=reset_token,
        )
        if not email_sent:
            logger.warning(f"Failed to send password reset email to {user.email}")

    return {
        "message": "If that email address exists in our system, we've sent a password reset link to it."
    }


@router.post("/reset-password")
@limiter.limit(AUTH_RATE_LIMIT)
async def reset_password(
    request: Request, reset_data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
):
    """
    Reset password using a valid reset token.

    Validates the token and expiration, then updates the user's password.
    """
    # Find user with matching reset token
    result = await db.execute(select(User).where(User.reset_token == reset_data.token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        )

    # Check if token has expired
    current_time = int(time.time())
    if not user.reset_token_expires or user.reset_token_expires < current_time:
        # Clean up expired token
        user.reset_token = None
        user.reset_token_expires = None
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        )

    # Update password
    user.set_password(reset_data.new_password)

    # Clear reset token
    user.reset_token = None
    user.reset_token_expires = None

    await db.commit()

    return {"message": "Password reset successfully. You can now log in with your new password."}
