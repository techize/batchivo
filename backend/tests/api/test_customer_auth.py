"""Tests for customer authentication API endpoints."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.models.customer import Customer


class TestCustomerRegistration:
    """Tests for customer registration."""

    @pytest.mark.asyncio
    async def test_register_customer_success(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test successful customer registration."""
        with patch("app.api.v1.customer_auth.get_email_service") as mock_email:
            mock_email.return_value.is_configured = False

            response = await unauthenticated_client.post(
                "/api/v1/customer/auth/register",
                json={
                    "email": "newcustomer@example.com",
                    "password": "testpassword123",
                    "full_name": "Test Customer",
                    "phone": "07700900000",
                    "marketing_consent": True,
                },
                headers={"X-Shop-Hostname": f"{test_tenant.slug}.batchivo.com"},
            )

        assert response.status_code == 201
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["customer"]["email"] == "newcustomer@example.com"
        assert data["customer"]["full_name"] == "Test Customer"
        assert data["customer"]["marketing_consent"] is True

    @pytest.mark.asyncio
    async def test_register_customer_duplicate_email(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test registration fails with duplicate email."""
        # Create existing customer
        customer = Customer(
            tenant_id=test_tenant.id,
            email="existing@example.com",
            full_name="Existing Customer",
        )
        customer.set_password("password123")
        db_session.add(customer)
        await db_session.commit()

        response = await unauthenticated_client.post(
            "/api/v1/customer/auth/register",
            json={
                "email": "existing@example.com",
                "password": "newpassword123",
                "full_name": "Duplicate Customer",
            },
            headers={"X-Shop-Hostname": f"{test_tenant.slug}.batchivo.com"},
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_customer_invalid_tenant(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test registration fails with invalid tenant."""
        response = await unauthenticated_client.post(
            "/api/v1/customer/auth/register",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
                "full_name": "Test Customer",
            },
            headers={"X-Shop-Hostname": "nonexistent.batchivo.com"},
        )

        assert response.status_code == 404
        assert "Shop not found" in response.json()["detail"]


class TestCustomerLogin:
    """Tests for customer login."""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test successful customer login."""
        # Create customer
        customer = Customer(
            tenant_id=test_tenant.id,
            email="login@example.com",
            full_name="Login Test",
        )
        customer.set_password("correctpassword")
        db_session.add(customer)
        await db_session.commit()

        response = await unauthenticated_client.post(
            "/api/v1/customer/auth/login",
            json={
                "email": "login@example.com",
                "password": "correctpassword",
            },
            headers={"X-Shop-Hostname": f"{test_tenant.slug}.batchivo.com"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["customer"]["email"] == "login@example.com"

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test login fails with wrong password."""
        # Create customer
        customer = Customer(
            tenant_id=test_tenant.id,
            email="wrongpw@example.com",
            full_name="Wrong PW Test",
        )
        customer.set_password("correctpassword")
        db_session.add(customer)
        await db_session.commit()

        response = await unauthenticated_client.post(
            "/api/v1/customer/auth/login",
            json={
                "email": "wrongpw@example.com",
                "password": "wrongpassword",
            },
            headers={"X-Shop-Hostname": f"{test_tenant.slug}.batchivo.com"},
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
    ):
        """Test login fails with nonexistent email."""
        response = await unauthenticated_client.post(
            "/api/v1/customer/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "somepassword",
            },
            headers={"X-Shop-Hostname": f"{test_tenant.slug}.batchivo.com"},
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_inactive_account(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test login fails for inactive account."""
        # Create inactive customer
        customer = Customer(
            tenant_id=test_tenant.id,
            email="inactive@example.com",
            full_name="Inactive Test",
            is_active=False,
        )
        customer.set_password("password123")
        db_session.add(customer)
        await db_session.commit()

        response = await unauthenticated_client.post(
            "/api/v1/customer/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "password123",
            },
            headers={"X-Shop-Hostname": f"{test_tenant.slug}.batchivo.com"},
        )

        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"]


class TestCustomerTokenRefresh:
    """Tests for token refresh."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test successful token refresh."""
        # Create and login customer
        customer = Customer(
            tenant_id=test_tenant.id,
            email="refresh@example.com",
            full_name="Refresh Test",
        )
        customer.set_password("password123")
        db_session.add(customer)
        await db_session.commit()

        # Login to get tokens
        login_response = await unauthenticated_client.post(
            "/api/v1/customer/auth/login",
            json={
                "email": "refresh@example.com",
                "password": "password123",
            },
            headers={"X-Shop-Hostname": f"{test_tenant.slug}.batchivo.com"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = await unauthenticated_client.post(
            "/api/v1/customer/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data


class TestCustomerForgotPassword:
    """Tests for forgot password."""

    @pytest.mark.asyncio
    async def test_forgot_password_success(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test forgot password request."""
        # Create customer
        customer = Customer(
            tenant_id=test_tenant.id,
            email="forgot@example.com",
            full_name="Forgot Test",
        )
        customer.set_password("password123")
        db_session.add(customer)
        await db_session.commit()

        with patch("app.api.v1.customer_auth.get_email_service") as mock_email:
            mock_email.return_value.is_configured = False

            response = await unauthenticated_client.post(
                "/api/v1/customer/auth/forgot-password",
                json={"email": "forgot@example.com"},
                headers={"X-Shop-Hostname": f"{test_tenant.slug}.batchivo.com"},
            )

        assert response.status_code == 200
        # Should always return success to prevent email enumeration
        assert "receive a password reset link" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
    ):
        """Test forgot password with nonexistent email still returns success."""
        response = await unauthenticated_client.post(
            "/api/v1/customer/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
            headers={"X-Shop-Hostname": f"{test_tenant.slug}.batchivo.com"},
        )

        # Should still return success to prevent email enumeration
        assert response.status_code == 200
