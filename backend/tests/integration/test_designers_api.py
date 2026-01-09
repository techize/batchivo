"""Comprehensive integration tests for Designers API - all fields and operations."""

import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestDesignersBasicCRUD:
    """Test basic CRUD operations for Designers."""

    @pytest.mark.asyncio
    async def test_create_designer_minimal(self, client: AsyncClient, auth_headers: dict):
        """Test creating a designer with minimal required fields."""
        response = await client.post(
            "/api/v1/designers",
            headers=auth_headers,
            json={"name": "Minimal Designer"},
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "Minimal Designer"
        assert data["slug"] == "minimal-designer"  # Auto-generated
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_designer_all_fields(self, client: AsyncClient, auth_headers: dict):
        """Test creating a designer with all fields populated."""
        response = await client.post(
            "/api/v1/designers",
            headers=auth_headers,
            json={
                "name": "Full Featured Designer",
                "slug": "full-featured-designer",
                "description": "A designer with all fields for testing",
                "logo_url": "https://example.com/logo.png",
                "website_url": "https://example.com",
                "social_links": {"instagram": "@designer", "youtube": "youtube.com/designer"},
                "membership_cost": "12.99",
                "membership_start_date": "2024-01-01",
                "membership_renewal_date": "2025-01-01",
                "is_active": True,
                "notes": "Internal notes about this designer",
            },
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "Full Featured Designer"
        assert data["slug"] == "full-featured-designer"
        assert data["description"] == "A designer with all fields for testing"
        assert data["logo_url"] == "https://example.com/logo.png"
        assert data["website_url"] == "https://example.com"
        assert data["social_links"]["instagram"] == "@designer"
        assert float(data["membership_cost"]) == 12.99
        assert data["membership_start_date"] == "2024-01-01"
        assert data["membership_renewal_date"] == "2025-01-01"
        assert data["is_active"] is True
        assert data["notes"] == "Internal notes about this designer"

    @pytest.mark.asyncio
    async def test_get_designer(self, client: AsyncClient, auth_headers: dict, test_designer):
        """Test retrieving a designer by ID."""
        response = await client.get(f"/api/v1/designers/{test_designer.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_designer.id)
        assert data["name"] == test_designer.name

    @pytest.mark.asyncio
    async def test_list_designers(self, client: AsyncClient, auth_headers: dict, test_designer):
        """Test listing designers."""
        response = await client.get("/api/v1/designers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "designers" in data
        assert isinstance(data["designers"], list)
        assert len(data["designers"]) >= 1

    @pytest.mark.asyncio
    async def test_update_designer(self, client: AsyncClient, auth_headers: dict, test_designer):
        """Test updating a designer."""
        response = await client.patch(
            f"/api/v1/designers/{test_designer.id}",
            headers=auth_headers,
            json={
                "name": "Updated Designer Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Designer Name"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_designer(self, client: AsyncClient, auth_headers: dict, test_designer):
        """Test deleting a designer (hard delete)."""
        response = await client.delete(
            f"/api/v1/designers/{test_designer.id}", headers=auth_headers
        )
        assert response.status_code in [200, 204]

        # Verify designer is actually deleted (hard delete)
        response = await client.get(f"/api/v1/designers/{test_designer.id}", headers=auth_headers)
        assert response.status_code == 404


class TestDesignersAllFieldsPersistence:
    """Test that all designer fields persist correctly."""

    @pytest.mark.asyncio
    async def test_all_fields_persist_after_update(
        self, client: AsyncClient, auth_headers: dict, test_designer
    ):
        """Test that ALL designer fields persist after update and refetch."""
        update_data = {
            "name": "Persistence Test Designer",
            "slug": "persistence-test",
            "description": "Testing field persistence",
            "logo_url": "https://example.com/persistence.png",
            "website_url": "https://persistence.example.com",
            "social_links": {"twitter": "@persisttest", "patreon": "patreon.com/test"},
            "membership_cost": "25.50",
            "membership_start_date": "2024-06-01",
            "membership_renewal_date": "2025-06-01",
            "is_active": True,
            "notes": "Updated notes for persistence test",
        }

        update_response = await client.patch(
            f"/api/v1/designers/{test_designer.id}",
            headers=auth_headers,
            json=update_data,
        )
        assert update_response.status_code == 200

        # Fetch and verify all fields
        get_response = await client.get(
            f"/api/v1/designers/{test_designer.id}", headers=auth_headers
        )
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["name"] == "Persistence Test Designer"
        assert data["slug"] == "persistence-test"
        assert data["description"] == "Testing field persistence"
        assert data["logo_url"] == "https://example.com/persistence.png"
        assert data["website_url"] == "https://persistence.example.com"
        assert data["social_links"]["twitter"] == "@persisttest"
        assert float(data["membership_cost"]) == 25.50
        assert data["membership_start_date"] == "2024-06-01"
        assert data["membership_renewal_date"] == "2025-06-01"
        assert data["is_active"] is True
        assert data["notes"] == "Updated notes for persistence test"


class TestDesignersMembershipFields:
    """Test membership tracking fields specifically."""

    @pytest.mark.asyncio
    async def test_membership_cost(self, client: AsyncClient, auth_headers: dict, test_designer):
        """Test membership cost field."""
        response = await client.patch(
            f"/api/v1/designers/{test_designer.id}",
            headers=auth_headers,
            json={"membership_cost": "19.99"},
        )
        assert response.status_code == 200
        assert float(response.json()["membership_cost"]) == 19.99

    @pytest.mark.asyncio
    async def test_membership_dates(self, client: AsyncClient, auth_headers: dict, test_designer):
        """Test membership date fields."""
        response = await client.patch(
            f"/api/v1/designers/{test_designer.id}",
            headers=auth_headers,
            json={
                "membership_start_date": "2024-03-15",
                "membership_renewal_date": "2025-03-15",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["membership_start_date"] == "2024-03-15"
        assert data["membership_renewal_date"] == "2025-03-15"


class TestDesignersSocialFields:
    """Test social media and URL fields."""

    @pytest.mark.asyncio
    async def test_website_url(self, client: AsyncClient, auth_headers: dict, test_designer):
        """Test website URL field."""
        response = await client.patch(
            f"/api/v1/designers/{test_designer.id}",
            headers=auth_headers,
            json={"website_url": "https://newsite.example.com"},
        )
        assert response.status_code == 200
        assert response.json()["website_url"] == "https://newsite.example.com"

    @pytest.mark.asyncio
    async def test_logo_url(self, client: AsyncClient, auth_headers: dict, test_designer):
        """Test logo URL field."""
        response = await client.patch(
            f"/api/v1/designers/{test_designer.id}",
            headers=auth_headers,
            json={"logo_url": "https://example.com/new-logo.png"},
        )
        assert response.status_code == 200
        assert response.json()["logo_url"] == "https://example.com/new-logo.png"

    @pytest.mark.asyncio
    async def test_social_links(self, client: AsyncClient, auth_headers: dict, test_designer):
        """Test social links JSON field."""
        social_data = {
            "instagram": "@newhandle",
            "youtube": "youtube.com/newchannel",
            "patreon": "patreon.com/designer",
        }
        response = await client.patch(
            f"/api/v1/designers/{test_designer.id}",
            headers=auth_headers,
            json={"social_links": social_data},
        )
        assert response.status_code == 200
        assert response.json()["social_links"] == social_data


class TestDesignersSlugGeneration:
    """Test automatic slug generation."""

    @pytest.mark.asyncio
    async def test_auto_slug_from_name(self, client: AsyncClient, auth_headers: dict):
        """Test that slug is auto-generated from name."""
        response = await client.post(
            "/api/v1/designers",
            headers=auth_headers,
            json={"name": "Test Designer With Spaces"},
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["slug"] == "test-designer-with-spaces"

    @pytest.mark.asyncio
    async def test_custom_slug_preserved(self, client: AsyncClient, auth_headers: dict):
        """Test that custom slug is preserved."""
        response = await client.post(
            "/api/v1/designers",
            headers=auth_headers,
            json={"name": "Some Designer", "slug": "custom-slug"},
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["slug"] == "custom-slug"


class TestDesignersValidation:
    """Test validation rules for designer fields."""

    @pytest.mark.asyncio
    async def test_designer_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test accessing non-existent designer returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/designers/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_name_rejected(self, client: AsyncClient, auth_headers: dict):
        """Test that empty name is rejected."""
        response = await client.post(
            "/api/v1/designers",
            headers=auth_headers,
            json={"name": ""},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_membership_cost_rejected(self, client: AsyncClient, auth_headers: dict):
        """Test that negative membership cost is rejected."""
        response = await client.post(
            "/api/v1/designers",
            headers=auth_headers,
            json={"name": "Test Designer", "membership_cost": "-10.00"},
        )
        assert response.status_code == 422
