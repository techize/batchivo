"""Integration tests for settings API endpoints."""

import pytest
from httpx import AsyncClient


class TestSquareSettingsAPI:
    """Test Square settings API endpoints."""

    @pytest.mark.asyncio
    async def test_get_square_settings_default(self, client: AsyncClient, auth_headers: dict):
        """Test getting Square settings returns defaults when not configured."""
        response = await client.get(
            "/api/v1/settings/square",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["environment"] == "sandbox"
        assert data["is_configured"] is False
        assert data["access_token_masked"] is None

    @pytest.mark.asyncio
    async def test_update_square_settings_toggle_enabled(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test toggling Square enabled state."""
        # Enable Square
        response = await client.put(
            "/api/v1/settings/square",
            headers=auth_headers,
            json={"enabled": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True

        # Verify it persisted
        response = await client.get(
            "/api/v1/settings/square",
            headers=auth_headers,
        )
        assert response.json()["enabled"] is True

    @pytest.mark.asyncio
    async def test_update_square_settings_change_environment(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test changing Square environment."""
        response = await client.put(
            "/api/v1/settings/square",
            headers=auth_headers,
            json={"environment": "production"},
        )

        assert response.status_code == 200
        assert response.json()["environment"] == "production"

    @pytest.mark.asyncio
    async def test_update_square_settings_with_credentials(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating Square with credentials masks them in response."""
        response = await client.put(
            "/api/v1/settings/square",
            headers=auth_headers,
            json={
                "access_token": "sq0atp-test-token-12345",
                "location_id": "LTEST1234",
                "app_id": "sq0idp-test-app",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_configured"] is True
        # Credentials should be masked (last 4 chars visible)
        assert data["access_token_masked"] == "...2345"
        assert data["location_id_masked"] == "...1234"
        assert data["app_id"] == "sq0idp-test-app"

    @pytest.mark.asyncio
    async def test_update_square_settings_invalid_environment(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that invalid environment is rejected."""
        response = await client.put(
            "/api/v1/settings/square",
            headers=auth_headers,
            json={"environment": "invalid"},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_test_square_connection_not_configured(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test Square connection test fails when not configured."""
        response = await client.post(
            "/api/v1/settings/square/test",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not configured" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_square_settings_requires_auth(self, unauthenticated_client: AsyncClient):
        """Test that Square settings endpoints require authentication."""
        response = await unauthenticated_client.get("/api/v1/settings/square")
        assert response.status_code == 401

        response = await unauthenticated_client.put(
            "/api/v1/settings/square",
            json={"enabled": True},
        )
        assert response.status_code == 401


class TestTenantSettingsAPI:
    """Test tenant settings API endpoints."""

    @pytest.mark.asyncio
    async def test_get_tenant(self, client: AsyncClient, auth_headers: dict):
        """Test getting tenant details."""
        response = await client.get(
            "/api/v1/settings/tenant",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "slug" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_update_tenant_name(self, client: AsyncClient, auth_headers: dict):
        """Test updating tenant name."""
        response = await client.put(
            "/api/v1/settings/tenant",
            headers=auth_headers,
            json={"name": "Updated Tenant Name"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Tenant Name"

    @pytest.mark.asyncio
    async def test_update_tenant_description(self, client: AsyncClient, auth_headers: dict):
        """Test updating tenant description."""
        response = await client.put(
            "/api/v1/settings/tenant",
            headers=auth_headers,
            json={"name": "Test Tenant", "description": "New description"},
        )

        assert response.status_code == 200
        assert response.json()["description"] == "New description"

    @pytest.mark.asyncio
    async def test_update_tenant_partial(self, client: AsyncClient, auth_headers: dict):
        """Test updating only description (partial update)."""
        response = await client.put(
            "/api/v1/settings/tenant",
            headers=auth_headers,
            json={"description": "Only description updated"},
        )

        # Partial updates are allowed
        assert response.status_code == 200
        assert response.json()["description"] == "Only description updated"

    @pytest.mark.asyncio
    async def test_tenant_settings_requires_auth(self, unauthenticated_client: AsyncClient):
        """Test that tenant settings require authentication."""
        response = await unauthenticated_client.get("/api/v1/settings/tenant")
        assert response.status_code == 401


class TestTenantMembersAPI:
    """Test tenant members API endpoints."""

    @pytest.mark.asyncio
    async def test_list_members(self, client: AsyncClient, auth_headers: dict):
        """Test listing tenant members."""
        response = await client.get(
            "/api/v1/tenant/members",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert isinstance(data["members"], list)
        # Should have at least the current user
        assert len(data["members"]) >= 1

    @pytest.mark.asyncio
    async def test_list_members_includes_current_user(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that member list includes the authenticated user."""
        response = await client.get(
            "/api/v1/tenant/members",
            headers=auth_headers,
        )

        assert response.status_code == 200
        members = response.json()["members"]

        # Find the test user in members
        emails = [m["email"] for m in members]
        assert any("test" in email for email in emails)

    @pytest.mark.asyncio
    async def test_invite_member_nonexistent_user(self, client: AsyncClient, auth_headers: dict):
        """Test inviting a non-existent user returns 404."""
        response = await client.post(
            "/api/v1/tenant/members/invite",
            headers=auth_headers,
            json={
                "email": "nonexistent@example.com",
                "role": "member",
            },
        )

        assert response.status_code == 404
        assert "no user found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invite_member_invalid_role(self, client: AsyncClient, auth_headers: dict):
        """Test inviting with invalid role is rejected."""
        response = await client.post(
            "/api/v1/tenant/members/invite",
            headers=auth_headers,
            json={
                "email": "test@example.com",
                "role": "superadmin",  # Invalid role
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_members_requires_auth(self, unauthenticated_client: AsyncClient):
        """Test that members endpoints require authentication."""
        response = await unauthenticated_client.get("/api/v1/tenant/members")
        assert response.status_code == 401
