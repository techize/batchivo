"""Customer authentication API endpoints.

Handles customer registration, login, password reset, and email verification.
These endpoints are public (no admin auth required) but require tenant context.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.customer_dependencies import (
    CUSTOMER_ACCESS_TOKEN_EXPIRE_MINUTES,
    CurrentCustomer,
    create_customer_access_token,
    create_customer_refresh_token,
    decode_customer_token,
    verify_customer_token_type,
)
from app.auth.dependencies import ShopTenant
from app.database import get_db
from app.models.customer import Customer
from app.models.tenant import Tenant
from app.schemas.customer import (
    CustomerChangePassword,
    CustomerForgotPassword,
    CustomerLogin,
    CustomerRefreshToken,
    CustomerRegister,
    CustomerResetPassword,
    CustomerResponse,
    CustomerTokenResponse,
    CustomerVerifyEmail,
)
from app.services.email_service import get_email_service

router = APIRouter()


@router.post("/register", response_model=CustomerTokenResponse, status_code=201)
async def register_customer(
    data: CustomerRegister,
    tenant: ShopTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new customer account.

    Creates a customer account for the specified shop.
    Tenant is resolved from X-Shop-Hostname header.
    Returns access and refresh tokens for immediate login.
    """

    # Check if email already exists for this tenant
    existing = await db.execute(
        select(Customer).where(
            Customer.tenant_id == tenant.id,
            func.lower(Customer.email) == data.email.lower(),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    # Create customer
    customer = Customer(
        tenant_id=tenant.id,
        email=data.email.lower(),
        full_name=data.full_name,
        phone=data.phone,
        marketing_consent=data.marketing_consent,
        marketing_consent_at=datetime.now(timezone.utc) if data.marketing_consent else None,
    )
    customer.set_password(data.password)

    # Generate email verification token
    verification_token = customer.generate_verification_token()
    customer.email_verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    # Send welcome/verification email
    email_service = get_email_service()
    if email_service.is_configured:
        email_service.send_customer_welcome(
            to_email=customer.email,
            customer_name=customer.full_name,
            verification_token=verification_token,
            shop_name=tenant.name,
        )

    # Generate tokens
    access_token = create_customer_access_token(
        customer_id=customer.id,
        tenant_id=tenant.id,
        email=customer.email,
    )
    refresh_token = create_customer_refresh_token(
        customer_id=customer.id,
        tenant_id=tenant.id,
        email=customer.email,
    )

    return CustomerTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=CUSTOMER_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        customer=CustomerResponse.model_validate(customer),
    )


@router.post("/login", response_model=CustomerTokenResponse)
async def login_customer(
    data: CustomerLogin,
    tenant: ShopTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email and password.

    Tenant is resolved from X-Shop-Hostname header.
    Returns access and refresh tokens.
    """

    # Find customer
    result = await db.execute(
        select(Customer).where(
            Customer.tenant_id == tenant.id,
            func.lower(Customer.email) == data.email.lower(),
        )
    )
    customer = result.scalar_one_or_none()

    if not customer or not customer.verify_password(data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated",
        )

    # Update last login
    customer.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Generate tokens
    access_token = create_customer_access_token(
        customer_id=customer.id,
        tenant_id=tenant.id,
        email=customer.email,
    )
    refresh_token = create_customer_refresh_token(
        customer_id=customer.id,
        tenant_id=tenant.id,
        email=customer.email,
    )

    return CustomerTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=CUSTOMER_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        customer=CustomerResponse.model_validate(customer),
    )


@router.post("/refresh", response_model=CustomerTokenResponse)
async def refresh_token(
    data: CustomerRefreshToken,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Returns new access and refresh tokens.
    """
    # Verify refresh token type
    if not verify_customer_token_type(data.refresh_token, "customer_refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Decode token
    token_data = decode_customer_token(data.refresh_token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Verify customer exists and is active
    result = await db.execute(
        select(Customer).where(
            Customer.id == token_data.customer_id,
            Customer.tenant_id == token_data.tenant_id,
        )
    )
    customer = result.scalar_one_or_none()

    if not customer or not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer not found or inactive",
        )

    # Generate new tokens
    access_token = create_customer_access_token(
        customer_id=customer.id,
        tenant_id=customer.tenant_id,
        email=customer.email,
    )
    refresh_token = create_customer_refresh_token(
        customer_id=customer.id,
        tenant_id=customer.tenant_id,
        email=customer.email,
    )

    return CustomerTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=CUSTOMER_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        customer=CustomerResponse.model_validate(customer),
    )


@router.post("/forgot-password", status_code=200)
async def forgot_password(
    data: CustomerForgotPassword,
    tenant: ShopTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset email.

    Tenant is resolved from X-Shop-Hostname header.
    Always returns success to prevent email enumeration.
    """

    # Find customer
    result = await db.execute(
        select(Customer).where(
            Customer.tenant_id == tenant.id,
            func.lower(Customer.email) == data.email.lower(),
        )
    )
    customer = result.scalar_one_or_none()

    if customer and customer.is_active:
        # Generate reset token
        reset_token = customer.generate_reset_token()
        customer.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.commit()

        # Send reset email
        email_service = get_email_service()
        if email_service.is_configured:
            email_service.send_customer_password_reset(
                to_email=customer.email,
                customer_name=customer.full_name,
                reset_token=reset_token,
                shop_name=tenant.name,
            )

    # Always return success to prevent email enumeration
    return {
        "message": "If an account exists with this email, you will receive a password reset link."
    }


@router.post("/reset-password", status_code=200)
async def reset_password(
    data: CustomerResetPassword,
    tenant: ShopTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using token from email.

    Tenant is resolved from X-Shop-Hostname header.
    """

    # Find customer with valid reset token
    result = await db.execute(
        select(Customer).where(
            Customer.tenant_id == tenant.id,
            Customer.reset_token == data.token,
        )
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Check token expiry
    if (
        customer.reset_token_expires is None
        or datetime.now(timezone.utc) > customer.reset_token_expires
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    # Update password
    customer.set_password(data.password)
    customer.reset_token = None
    customer.reset_token_expires = None
    await db.commit()

    return {
        "message": "Password has been reset successfully. You can now login with your new password."
    }


@router.post("/verify-email", status_code=200)
async def verify_email(
    data: CustomerVerifyEmail,
    tenant: ShopTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify email address using token from email.

    Tenant is resolved from X-Shop-Hostname header.
    """

    # Find customer with valid verification token
    result = await db.execute(
        select(Customer).where(
            Customer.tenant_id == tenant.id,
            Customer.email_verification_token == data.token,
        )
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    # Check if already verified
    if customer.email_verified:
        return {"message": "Email already verified"}

    # Check token expiry
    if (
        customer.email_verification_expires is None
        or datetime.now(timezone.utc) > customer.email_verification_expires
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired",
        )

    # Mark as verified
    customer.email_verified = True
    customer.email_verified_at = datetime.now(timezone.utc)
    customer.email_verification_token = None
    customer.email_verification_expires = None
    await db.commit()

    return {"message": "Email verified successfully"}


@router.post("/resend-verification", status_code=200)
async def resend_verification(
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """
    Resend email verification (requires authentication).
    """
    if customer.email_verified:
        return {"message": "Email already verified"}

    # Get tenant
    result = await db.execute(select(Tenant).where(Tenant.id == customer.tenant_id))
    tenant = result.scalar_one()

    # Generate new verification token
    verification_token = customer.generate_verification_token()
    customer.email_verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    await db.commit()

    # Send verification email
    email_service = get_email_service()
    if email_service.is_configured:
        email_service.send_customer_verification(
            to_email=customer.email,
            customer_name=customer.full_name,
            verification_token=verification_token,
            shop_name=tenant.name,
        )

    return {"message": "Verification email sent"}


@router.post("/change-password", status_code=200)
async def change_password(
    data: CustomerChangePassword,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """
    Change password (requires authentication).
    """
    # Verify current password
    if not customer.verify_password(data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    customer.set_password(data.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}
