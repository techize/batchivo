"""Self-service tenant onboarding API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database import get_db
from app.schemas.onboarding import (
    EmailVerificationRequest,
    EmailVerificationResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    TenantRegistrationRequest,
    TenantRegistrationResponse,
)
from app.services.onboarding_service import (
    EmailAlreadyRegisteredError,
    InvalidTokenError,
    get_onboarding_service,
)

router = APIRouter()

# Rate limits for registration endpoints
REGISTER_RATE_LIMIT = "5/minute"
VERIFY_RATE_LIMIT = "10/minute"
RESEND_RATE_LIMIT = "3/minute"


@router.post(
    "/register",
    response_model=TenantRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new tenant",
    description="Start the tenant registration process. Sends verification email.",
)
@limiter.limit(REGISTER_RATE_LIMIT)
async def register_tenant(
    request: Request,
    registration: TenantRegistrationRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantRegistrationResponse:
    """
    Register a new tenant with email verification.

    This endpoint:
    1. Validates the registration request
    2. Creates a verification token
    3. Sends verification email
    4. Returns success message (tenant/user created on verification)

    Rate limited to prevent abuse.
    """
    service = get_onboarding_service(db)

    try:
        return await service.register_tenant(registration)
    except EmailAlreadyRegisteredError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again later.",
        )


@router.post(
    "/verify-email",
    response_model=EmailVerificationResponse,
    summary="Verify email and complete registration",
    description="Verify email address and complete tenant/user creation.",
)
@limiter.limit(VERIFY_RATE_LIMIT)
async def verify_email(
    request: Request,
    verification: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> EmailVerificationResponse:
    """
    Verify email and complete registration.

    This endpoint:
    1. Validates the verification token
    2. Creates the tenant with appropriate settings
    3. Creates the user as tenant owner
    4. Returns JWT tokens for immediate login

    The token is single-use and expires after 24 hours.
    """
    service = get_onboarding_service(db)

    try:
        return await service.verify_email(verification.token)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except EmailAlreadyRegisteredError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed. Please try again.",
        )


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    summary="Resend verification email",
    description="Resend verification email for pending registration.",
)
@limiter.limit(RESEND_RATE_LIMIT)
async def resend_verification(
    request: Request,
    resend_request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> ResendVerificationResponse:
    """
    Resend verification email.

    This endpoint is rate-limited and always returns success to prevent
    email enumeration attacks.

    If an unverified registration exists:
    - Old token is invalidated
    - New verification email is sent

    If no pending registration or email is already verified:
    - Returns success (doesn't reveal email status)
    """
    service = get_onboarding_service(db)

    await service.resend_verification(resend_request.email)

    return ResendVerificationResponse(
        message="If an unverified account exists for this email, a verification link has been sent."
    )
