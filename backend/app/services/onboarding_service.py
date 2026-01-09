"""Onboarding service for self-service tenant registration."""

import json
import logging
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import get_password_hash
from app.core.security import create_access_token, create_refresh_token
from app.models.email_verification import (
    EmailVerificationToken,
    VerificationTokenType,
)
from app.models.tenant import Tenant, TenantType
from app.models.user import User, UserRole, UserTenant
from app.schemas.onboarding import (
    EmailVerificationResponse,
    TenantRegistrationRequest,
    TenantRegistrationResponse,
)
from app.schemas.tenant_settings import TenantSettings
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)


class OnboardingError(Exception):
    """Base exception for onboarding errors."""

    pass


class EmailAlreadyRegisteredError(OnboardingError):
    """Email is already registered."""

    pass


class SlugAlreadyExistsError(OnboardingError):
    """Tenant slug already exists."""

    pass


class InvalidTokenError(OnboardingError):
    """Token is invalid, expired, or already used."""

    pass


class OnboardingService:
    """
    Service for self-service tenant registration and onboarding.

    Flow:
    1. User submits registration form (email, password, business_name)
    2. System creates verification token and sends email
    3. User clicks verification link
    4. System creates tenant, user, and user_tenant relationship
    5. Returns JWT tokens for immediate login
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.email_service = get_email_service()

    async def register_tenant(
        self, request: TenantRegistrationRequest
    ) -> TenantRegistrationResponse:
        """
        Start tenant registration process.

        Creates a verification token and sends email. Does not create tenant
        or user until email is verified.

        Args:
            request: Registration details

        Returns:
            Registration response with instructions

        Raises:
            EmailAlreadyRegisteredError: If email is already registered
        """
        email = request.email.lower()

        # Check if email is already registered
        existing_user = await self._get_user_by_email(email)
        if existing_user:
            raise EmailAlreadyRegisteredError(
                f"Email {email} is already registered. Please log in or reset your password."
            )

        # Check if there's a pending registration for this email
        existing_token = await self._get_pending_token(email)
        if existing_token:
            # Invalidate old token
            existing_token.mark_as_used()

        # Generate unique slug
        slug = await self._generate_unique_slug(request.business_name)

        # Store registration data in token (completed on verification)
        registration_data = {
            "email": email,
            "password_hash": get_password_hash(request.password),
            "full_name": request.full_name,
            "business_name": request.business_name,
            "tenant_type": request.tenant_type.value,
            "slug": slug,
        }

        # Create verification token
        token = EmailVerificationToken.create_email_verification(
            email=email,
            registration_data=json.dumps(registration_data),
            expires_hours=24,
        )
        self.db.add(token)
        await self.db.commit()

        # Send verification email
        await self._send_verification_email(
            email=email,
            name=request.full_name,
            token=token.token,
            business_name=request.business_name,
        )

        logger.info(f"Registration initiated for {email} (tenant: {request.business_name})")

        return TenantRegistrationResponse(
            message="Registration successful. Please check your email to verify your account.",
            email=email,
        )

    async def verify_email(self, token_str: str) -> EmailVerificationResponse:
        """
        Verify email and complete registration.

        Creates tenant, user, and user_tenant on successful verification.

        Args:
            token_str: Verification token from email link

        Returns:
            Verification response with JWT tokens

        Raises:
            InvalidTokenError: If token is invalid, expired, or used
        """
        # Find token
        result = await self.db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token == token_str,
                EmailVerificationToken.token_type == VerificationTokenType.EMAIL_VERIFICATION.value,
            )
        )
        token = result.scalar_one_or_none()

        if not token:
            raise InvalidTokenError("Invalid verification token")

        if not token.is_valid:
            if token.is_expired:
                raise InvalidTokenError("Verification token has expired. Please register again.")
            if token.is_used:
                raise InvalidTokenError("Verification token has already been used.")
            raise InvalidTokenError("Invalid verification token")

        # Parse registration data
        if not token.registration_data:
            raise InvalidTokenError("Token missing registration data")

        reg_data = json.loads(token.registration_data)

        # Double-check email isn't registered (race condition protection)
        existing_user = await self._get_user_by_email(reg_data["email"])
        if existing_user:
            token.mark_as_used()
            await self.db.commit()
            raise EmailAlreadyRegisteredError("Email is already registered")

        # Create tenant
        tenant_type = TenantType(reg_data["tenant_type"])
        default_settings = TenantSettings.for_tenant_type(tenant_type)

        tenant = Tenant(
            name=reg_data["business_name"],
            slug=reg_data["slug"],
            tenant_type=tenant_type.value,
            settings=default_settings.model_dump(),
            is_active=True,
        )
        self.db.add(tenant)
        await self.db.flush()  # Get tenant.id

        # Create user
        user = User(
            email=reg_data["email"],
            full_name=reg_data["full_name"],
            hashed_password=reg_data["password_hash"],
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()  # Get user.id

        # Create owner relationship
        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=tenant.id,
            role=UserRole.OWNER,
        )
        self.db.add(user_tenant)

        # Mark token as used
        token.mark_as_used()

        await self.db.commit()
        await self.db.refresh(tenant)
        await self.db.refresh(user)

        # Generate JWT tokens
        access_token = create_access_token(
            data={
                "user_id": str(user.id),
                "email": user.email,
                "tenant_id": str(tenant.id),
            }
        )
        refresh_token = create_refresh_token(
            data={
                "user_id": str(user.id),
                "email": user.email,
            }
        )

        logger.info(
            f"Registration completed for {user.email}: "
            f"tenant={tenant.name} ({tenant.slug}), user_id={user.id}"
        )

        return EmailVerificationResponse(
            message="Email verified successfully. Welcome to Nozzly!",
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            tenant_slug=tenant.slug,
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def resend_verification(self, email: str) -> bool:
        """
        Resend verification email for pending registration.

        Args:
            email: Email address to resend to

        Returns:
            True if email was sent (or would have been sent)
        """
        email = email.lower()

        # Check if already registered
        existing_user = await self._get_user_by_email(email)
        if existing_user:
            # Don't reveal that email is registered
            logger.info(f"Resend verification attempted for registered email: {email}")
            return True

        # Find pending token
        token = await self._get_pending_token(email)
        if not token:
            # Don't reveal that no pending registration exists
            logger.info(f"Resend verification attempted for unknown email: {email}")
            return True

        # Parse registration data for name
        reg_data = json.loads(token.registration_data) if token.registration_data else {}
        name = reg_data.get("full_name", "there")
        business_name = reg_data.get("business_name", "your business")

        # Invalidate old token and create new one
        token.mark_as_used()

        new_token = EmailVerificationToken.create_email_verification(
            email=email,
            registration_data=token.registration_data,
            expires_hours=24,
        )
        self.db.add(new_token)
        await self.db.commit()

        # Send new verification email
        await self._send_verification_email(
            email=email,
            name=name,
            token=new_token.token,
            business_name=business_name,
        )

        logger.info(f"Verification email resent to {email}")
        return True

    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def _get_pending_token(self, email: str) -> Optional[EmailVerificationToken]:
        """Get pending verification token for email."""
        result = await self.db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.email == email.lower(),
                EmailVerificationToken.token_type == VerificationTokenType.EMAIL_VERIFICATION.value,
                EmailVerificationToken.used_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _generate_unique_slug(self, business_name: str) -> str:
        """
        Generate a unique URL slug from business name.

        Args:
            business_name: Business name to slugify

        Returns:
            Unique slug
        """
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", business_name.lower())
        slug = slug.strip("-")

        # Ensure slug isn't empty
        if not slug:
            slug = "workspace"

        # Check for uniqueness
        base_slug = slug
        counter = 1
        while True:
            result = await self.db.execute(select(Tenant).where(Tenant.slug == slug))
            existing = result.scalar_one_or_none()
            if not existing:
                return slug
            slug = f"{base_slug}-{counter}"
            counter += 1
            if counter > 100:
                # Fallback: use random suffix
                import secrets

                return f"{base_slug}-{secrets.token_hex(4)}"

    async def _send_verification_email(
        self,
        email: str,
        name: str,
        token: str,
        business_name: str,
    ) -> bool:
        """
        Send verification email to new user.

        Args:
            email: Recipient email
            name: User's name
            token: Verification token
            business_name: Business name for personalization

        Returns:
            True if email sent successfully
        """
        if not self.email_service.is_configured:
            logger.warning(f"Email service not configured. Verification token for {email}: {token}")
            return False

        # For now, use the existing customer welcome email method
        # In production, you might want a separate tenant registration email
        return self.email_service.send_customer_welcome(
            to_email=email,
            customer_name=name,
            verification_token=token,
            shop_name="Nozzly",
        )


def get_onboarding_service(db: AsyncSession) -> OnboardingService:
    """Get onboarding service instance."""
    return OnboardingService(db)
