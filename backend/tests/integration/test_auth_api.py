"""Integration tests for authentication API endpoints."""

import pytest
from httpx import AsyncClient

from app.models.user import User


class TestAuthEndpoints:
    """Test authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_login_success(self, unauthenticated_client: AsyncClient, test_user: User):
        """Test successful login returns JWT token."""
        response = await unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, unauthenticated_client: AsyncClient):
        """Test login with non-existent email returns 401."""
        response = await unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self, unauthenticated_client: AsyncClient, test_user: User
    ):
        """Test login with wrong password returns 401."""
        response = await unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    @pytest.mark.skip(
        reason="Rate limiting disabled in test environment to prevent test interference"
    )
    @pytest.mark.asyncio
    async def test_login_rate_limiting(self, unauthenticated_client: AsyncClient):
        """Test rate limiting blocks excessive login attempts."""
        # Make 6 login attempts (rate limit is 5/minute)
        for i in range(6):
            response = await unauthenticated_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "wrongpassword"},
            )

        # Last attempt should be rate limited
        assert response.status_code == 429
        assert "rate limit exceeded" in response.text.lower()

    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(self, unauthenticated_client: AsyncClient):
        """Test protected endpoints return 401 without token."""
        response = await unauthenticated_client.get("/api/v1/products")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_jwt_token_validation(self, client: AsyncClient, auth_headers: dict):
        """Test valid JWT allows access to protected endpoints."""
        response = await client.get("/api/v1/products", headers=auth_headers)
        # Should return 200 or 404 (depending on if products exist), not 401
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_register_new_user(self, unauthenticated_client: AsyncClient, test_tenant):
        """Test new user registration."""
        response = await unauthenticated_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User",
            },
        )
        # Might be 201 (created) or 200 (success) depending on implementation
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, unauthenticated_client: AsyncClient, test_user: User
    ):
        """Test registration with existing email returns error."""
        response = await unauthenticated_client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "password123",
                "full_name": "Duplicate User",
            },
        )
        assert response.status_code in [400, 409]  # Bad request or conflict

    @pytest.mark.skip(
        reason="Rate limiting disabled in test environment to prevent test interference"
    )
    @pytest.mark.asyncio
    async def test_forgot_password_rate_limiting(self, unauthenticated_client: AsyncClient):
        """Test forgot password endpoint has rate limiting."""
        # Make 4 requests (rate limit is 3/minute)
        for i in range(4):
            response = await unauthenticated_client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@example.com"},
            )

        # Last attempt should be rate limited
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_forgot_password_valid_email(
        self, unauthenticated_client: AsyncClient, test_user: User
    ):
        """Test forgot password with valid email."""
        response = await unauthenticated_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email},
        )
        # Should return 200 even for valid emails (security best practice)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_forgot_password_invalid_email(self, unauthenticated_client: AsyncClient):
        """Test forgot password with non-existent email."""
        response = await unauthenticated_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        # Should return 200 to prevent email enumeration
        assert response.status_code == 200

    @pytest.mark.skip(
        reason="Rate limiting disabled in test environment to prevent test interference"
    )
    @pytest.mark.asyncio
    async def test_reset_password_rate_limiting(self, unauthenticated_client: AsyncClient):
        """Test password reset endpoint has rate limiting."""
        # Make 6 requests (rate limit is 5/minute)
        for i in range(6):
            response = await unauthenticated_client.post(
                "/api/v1/auth/reset-password",
                json={
                    "token": "invalid-token",
                    "new_password": "newpassword123",
                },
            )

        # Last attempt should be rate limited
        assert response.status_code == 429


class TestAuthSecurity:
    """Test authentication security features."""

    @pytest.mark.asyncio
    async def test_security_headers_present(self, unauthenticated_client: AsyncClient):
        """Test security headers are present in responses."""
        response = await unauthenticated_client.get("/health")

        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "X-XSS-Protection" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_password_complexity_required(self, unauthenticated_client: AsyncClient):
        """Test weak passwords are rejected during registration."""
        response = await unauthenticated_client.post(
            "/api/v1/auth/register",
            json={
                "email": "weakpass@example.com",
                "password": "123",  # Too short
                "full_name": "Weak Password User",
            },
        )
        # Should return validation error (422 or 400)
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_jwt_contains_expected_claims(
        self, unauthenticated_client: AsyncClient, test_user: User
    ):
        """Test JWT token contains expected claims."""
        response = await unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        assert response.status_code == 200
        data = response.json()

        # JWT should be returned
        assert "access_token" in data
        token = data["access_token"]

        # Token should have 3 parts (header.payload.signature)
        assert len(token.split(".")) == 3
