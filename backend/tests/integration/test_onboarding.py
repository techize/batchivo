"""Integration tests for tenant onboarding and registration flow."""

import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, MagicMock

from app.models.email_verification import EmailVerificationToken, VerificationTokenType
from app.models.tenant import Tenant
from app.models.user import User


class TestTenantRegistration:
    """Test tenant registration flow."""

    @pytest.mark.asyncio
    async def test_register_tenant_success(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test successful tenant registration sends verification email."""
        with patch("app.services.onboarding_service.get_email_service") as mock_email:
            mock_email.return_value.is_configured = True
            mock_email.return_value.send_customer_welcome = MagicMock(return_value=True)

            response = await unauthenticated_client.post(
                "/api/v1/onboarding/register",
                json={
                    "email": "newuser@example.com",
                    "password": "SecurePass123",
                    "full_name": "New User",
                    "business_name": "My 3D Print Shop",
                    "tenant_type": "three_d_print",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "check your email" in data["message"].lower()

        # Verify token was created
        result = await db_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.email == "newuser@example.com"
            )
        )
        token = result.scalar_one_or_none()
        assert token is not None
        assert token.token_type == VerificationTokenType.EMAIL_VERIFICATION.value

    @pytest.mark.asyncio
    async def test_register_tenant_weak_password(self, unauthenticated_client: AsyncClient):
        """Test registration with weak password fails."""
        response = await unauthenticated_client.post(
            "/api/v1/onboarding/register",
            json={
                "email": "newuser@example.com",
                "password": "weak",  # Too short, no uppercase, no digits
                "full_name": "New User",
                "business_name": "My Shop",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_tenant_invalid_email(self, unauthenticated_client: AsyncClient):
        """Test registration with invalid email fails."""
        response = await unauthenticated_client.post(
            "/api/v1/onboarding/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123",
                "full_name": "New User",
                "business_name": "My Shop",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(
        self, unauthenticated_client: AsyncClient, test_user: User
    ):
        """Test registration with already registered email fails."""
        response = await unauthenticated_client.post(
            "/api/v1/onboarding/register",
            json={
                "email": test_user.email,  # Already exists
                "password": "SecurePass123",
                "full_name": "Another User",
                "business_name": "Another Shop",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_creates_pending_token(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that registration creates a pending verification token."""
        with patch("app.services.onboarding_service.get_email_service") as mock_email:
            mock_email.return_value.is_configured = True
            mock_email.return_value.send_customer_welcome = MagicMock(return_value=True)

            await unauthenticated_client.post(
                "/api/v1/onboarding/register",
                json={
                    "email": "pending@example.com",
                    "password": "SecurePass123",
                    "full_name": "Pending User",
                    "business_name": "Pending Shop",
                    "tenant_type": "hand_knitting",
                },
            )

        # Verify token contains registration data
        result = await db_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.email == "pending@example.com"
            )
        )
        token = result.scalar_one()
        reg_data = json.loads(token.registration_data)

        assert reg_data["email"] == "pending@example.com"
        assert reg_data["business_name"] == "Pending Shop"
        assert reg_data["tenant_type"] == "hand_knitting"
        assert "password_hash" in reg_data  # Password should be hashed


class TestEmailVerification:
    """Test email verification flow."""

    @pytest.mark.asyncio
    async def test_verify_email_creates_tenant_and_user(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test email verification creates tenant and user."""
        # First, create a verification token manually
        registration_data = {
            "email": "verified@example.com",
            "password_hash": "$2b$12$testhashedpassword",
            "full_name": "Verified User",
            "business_name": "Verified Shop",
            "tenant_type": "three_d_print",
            "slug": "verified-shop",
        }

        token = EmailVerificationToken.create_email_verification(
            email="verified@example.com",
            registration_data=json.dumps(registration_data),
            expires_hours=24,
        )
        db_session.add(token)
        await db_session.commit()

        # Verify email
        response = await unauthenticated_client.post(
            "/api/v1/onboarding/verify-email",
            json={"token": token.token},
        )

        assert response.status_code == 200
        data = response.json()

        # Check response contains expected data
        assert data["tenant_name"] == "Verified Shop"
        assert data["tenant_slug"] == "verified-shop"
        assert "access_token" in data
        assert "refresh_token" in data

        # Verify tenant was created
        result = await db_session.execute(select(Tenant).where(Tenant.slug == "verified-shop"))
        tenant = result.scalar_one_or_none()
        assert tenant is not None
        assert tenant.name == "Verified Shop"
        assert tenant.tenant_type == "three_d_print"

        # Verify user was created
        result = await db_session.execute(select(User).where(User.email == "verified@example.com"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.full_name == "Verified User"

    @pytest.mark.asyncio
    async def test_verify_invalid_token_fails(self, unauthenticated_client: AsyncClient):
        """Test verification with invalid token fails."""
        response = await unauthenticated_client.post(
            "/api/v1/onboarding/verify-email",
            json={"token": "invalid-token-12345"},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_expired_token_fails(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test verification with expired token fails."""
        from datetime import datetime, timedelta, timezone

        # Create an expired token
        token = EmailVerificationToken.create_email_verification(
            email="expired@example.com",
            registration_data="{}",
            expires_hours=24,
        )
        # Manually set expiry to past (use timezone-aware datetime)
        token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.add(token)
        await db_session.commit()

        response = await unauthenticated_client.post(
            "/api/v1/onboarding/verify-email",
            json={"token": token.token},
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_used_token_fails(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test verification with already-used token fails."""
        # Create a used token
        token = EmailVerificationToken.create_email_verification(
            email="used@example.com",
            registration_data="{}",
            expires_hours=24,
        )
        token.mark_as_used()
        db_session.add(token)
        await db_session.commit()

        response = await unauthenticated_client.post(
            "/api/v1/onboarding/verify-email",
            json={"token": token.token},
        )

        assert response.status_code == 400
        assert (
            "used" in response.json()["detail"].lower()
            or "invalid" in response.json()["detail"].lower()
        )


class TestResendVerification:
    """Test resend verification email flow."""

    @pytest.mark.asyncio
    async def test_resend_verification_success(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test resending verification email."""
        # Create a pending token
        registration_data = {
            "email": "resend@example.com",
            "password_hash": "$2b$12$testhashedpassword",
            "full_name": "Resend User",
            "business_name": "Resend Shop",
            "tenant_type": "generic",
            "slug": "resend-shop",
        }

        token = EmailVerificationToken.create_email_verification(
            email="resend@example.com",
            registration_data=json.dumps(registration_data),
            expires_hours=24,
        )
        db_session.add(token)
        await db_session.commit()

        with patch("app.services.onboarding_service.get_email_service") as mock_email:
            mock_email.return_value.is_configured = True
            mock_email.return_value.send_customer_welcome = MagicMock(return_value=True)

            response = await unauthenticated_client.post(
                "/api/v1/onboarding/resend-verification",
                json={"email": "resend@example.com"},
            )

        assert response.status_code == 200
        # Response should not reveal if email exists
        assert "verification link has been sent" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_resend_nonexistent_email_same_response(
        self, unauthenticated_client: AsyncClient
    ):
        """Test resend for non-existent email returns same response (security)."""
        response = await unauthenticated_client.post(
            "/api/v1/onboarding/resend-verification",
            json={"email": "nonexistent@example.com"},
        )

        # Should return success to prevent email enumeration
        assert response.status_code == 200
        assert "verification link has been sent" in response.json()["message"].lower()


class TestTenantTypeSettings:
    """Test tenant type affects default settings."""

    @pytest.mark.asyncio
    async def test_3d_print_tenant_gets_correct_settings(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test 3D print tenant gets appropriate default settings."""
        registration_data = {
            "email": "3dprint@example.com",
            "password_hash": "$2b$12$testhashedpassword",
            "full_name": "3D Print User",
            "business_name": "3D Print Shop",
            "tenant_type": "three_d_print",
            "slug": "3d-print-shop",
        }

        token = EmailVerificationToken.create_email_verification(
            email="3dprint@example.com",
            registration_data=json.dumps(registration_data),
            expires_hours=24,
        )
        db_session.add(token)
        await db_session.commit()

        response = await unauthenticated_client.post(
            "/api/v1/onboarding/verify-email",
            json={"token": token.token},
        )

        assert response.status_code == 200

        # Verify tenant has correct type
        result = await db_session.execute(select(Tenant).where(Tenant.slug == "3d-print-shop"))
        tenant = result.scalar_one()
        assert tenant.tenant_type == "three_d_print"

    @pytest.mark.asyncio
    async def test_knitting_tenant_gets_correct_settings(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test knitting tenant gets appropriate default settings."""
        registration_data = {
            "email": "knitter@example.com",
            "password_hash": "$2b$12$testhashedpassword",
            "full_name": "Knitting User",
            "business_name": "Yarn Haven",
            "tenant_type": "hand_knitting",
            "slug": "yarn-haven",
        }

        token = EmailVerificationToken.create_email_verification(
            email="knitter@example.com",
            registration_data=json.dumps(registration_data),
            expires_hours=24,
        )
        db_session.add(token)
        await db_session.commit()

        response = await unauthenticated_client.post(
            "/api/v1/onboarding/verify-email",
            json={"token": token.token},
        )

        assert response.status_code == 200

        # Verify tenant has correct type
        result = await db_session.execute(select(Tenant).where(Tenant.slug == "yarn-haven"))
        tenant = result.scalar_one()
        assert tenant.tenant_type == "hand_knitting"


class TestSlugGeneration:
    """Test unique slug generation for tenants."""

    @pytest.mark.asyncio
    async def test_slug_generated_from_business_name(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test slug is generated from business name."""
        with patch("app.services.onboarding_service.get_email_service") as mock_email:
            mock_email.return_value.is_configured = True
            mock_email.return_value.send_customer_welcome = MagicMock(return_value=True)

            response = await unauthenticated_client.post(
                "/api/v1/onboarding/register",
                json={
                    "email": "slugtest@example.com",
                    "password": "SecurePass123",
                    "full_name": "Slug Test User",
                    "business_name": "My Amazing Shop!",
                },
            )

        assert response.status_code == 201

        # Check token has generated slug
        result = await db_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.email == "slugtest@example.com"
            )
        )
        token = result.scalar_one()
        reg_data = json.loads(token.registration_data)

        # Slug should be lowercase with hyphens
        assert reg_data["slug"] == "my-amazing-shop"
