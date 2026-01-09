"""Comprehensive integration tests for Models API - all fields and operations."""

import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.models.model import Model


class TestModelsBasicCRUD:
    """Test basic CRUD operations for Models."""

    @pytest.mark.asyncio
    async def test_create_model_minimal(self, client: AsyncClient, auth_headers: dict):
        """Test creating a model with minimal required fields."""
        response = await client.post(
            "/api/v1/models",
            headers=auth_headers,
            json={
                "sku": f"MOD-{uuid4().hex[:8].upper()}",
                "name": "Minimal Test Model",
            },
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "Minimal Test Model"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_model_all_fields(self, client: AsyncClient, auth_headers: dict):
        """Test creating a model with all fields populated."""
        sku = f"FULL-{uuid4().hex[:8].upper()}"
        response = await client.post(
            "/api/v1/models",
            headers=auth_headers,
            json={
                "sku": sku,
                "name": "Full Featured Model",
                "description": "A model with all fields populated for testing",
                "category": "Models",
                "image_url": "https://example.com/model.jpg",
                "labor_hours": "2.5",
                "labor_rate_override": "15.00",
                "overhead_percentage": "10",
                "is_active": True,
                "designer": "Test Designer",
                "source": "Patreon",
                "print_time_minutes": 180,
                "prints_per_plate": 4,
                "machine": "Bambulabs A1 Mini",
                "units_in_stock": 5,
            },
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["sku"] == sku
        assert data["name"] == "Full Featured Model"
        assert data["description"] == "A model with all fields populated for testing"
        assert data["category"] == "Models"
        assert data["image_url"] == "https://example.com/model.jpg"
        assert float(data["labor_hours"]) == 2.5
        assert float(data["labor_rate_override"]) == 15.00
        assert float(data["overhead_percentage"]) == 10
        assert data["is_active"] is True
        assert data["designer"] == "Test Designer"
        assert data["source"] == "Patreon"
        assert data["print_time_minutes"] == 180
        assert data["prints_per_plate"] == 4
        assert data["machine"] == "Bambulabs A1 Mini"
        assert data["units_in_stock"] == 5

    @pytest.mark.asyncio
    async def test_get_model(self, client: AsyncClient, auth_headers: dict, test_model: Model):
        """Test retrieving a model by ID."""
        response = await client.get(f"/api/v1/models/{test_model.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_model.id)
        assert data["name"] == test_model.name

    @pytest.mark.asyncio
    async def test_list_models(self, client: AsyncClient, auth_headers: dict, test_model: Model):
        """Test listing models."""
        response = await client.get("/api/v1/models", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) >= 1

    @pytest.mark.asyncio
    async def test_update_model(self, client: AsyncClient, auth_headers: dict, test_model: Model):
        """Test updating a model."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={
                "name": "Updated Model Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Model Name"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_model(self, client: AsyncClient, auth_headers: dict, test_model: Model):
        """Test deleting a model (soft delete - sets is_active to false)."""
        response = await client.delete(f"/api/v1/models/{test_model.id}", headers=auth_headers)
        assert response.status_code in [200, 204]

        # Verify model is soft-deleted (is_active = false)
        response = await client.get(f"/api/v1/models/{test_model.id}", headers=auth_headers)
        # Model should still be fetchable but marked as inactive
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False


class TestModelsAllFieldsPersistence:
    """Test that all model fields persist correctly through update and fetch."""

    @pytest.mark.asyncio
    async def test_all_fields_persist_after_update(
        self, client: AsyncClient, auth_headers: dict, test_model: Model
    ):
        """Test that ALL model fields persist after update and refetch."""
        # Update with all fields
        update_response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={
                "name": "Persistence Test Model",
                "description": "Testing field persistence",
                "category": "TestCategory",
                "image_url": "https://example.com/test.png",
                "labor_hours": "3.25",
                "labor_rate_override": "12.50",
                "overhead_percentage": "15",
                "is_active": True,
                "designer": "Persistence Designer",
                "source": "Thangs.com",
                "print_time_minutes": 240,
                "prints_per_plate": 2,
                "machine": "Ender 3 v2",
                "units_in_stock": 10,
            },
        )
        assert update_response.status_code == 200

        # Fetch and verify all fields
        get_response = await client.get(f"/api/v1/models/{test_model.id}", headers=auth_headers)
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["name"] == "Persistence Test Model"
        assert data["description"] == "Testing field persistence"
        assert data["category"] == "TestCategory"
        assert data["image_url"] == "https://example.com/test.png"
        assert float(data["labor_hours"]) == 3.25
        assert float(data["labor_rate_override"]) == 12.50
        assert float(data["overhead_percentage"]) == 15
        assert data["is_active"] is True
        assert data["designer"] == "Persistence Designer"
        assert data["source"] == "Thangs.com"
        assert data["print_time_minutes"] == 240
        assert data["prints_per_plate"] == 2
        assert data["machine"] == "Ender 3 v2"
        assert data["units_in_stock"] == 10

    @pytest.mark.asyncio
    async def test_partial_update_preserves_other_fields(
        self, client: AsyncClient, auth_headers: dict, test_model: Model
    ):
        """Test that partial update preserves fields not included in the update."""
        # First set all fields
        await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={
                "name": "Original Name",
                "description": "Original Description",
                "designer": "Original Designer",
                "source": "Original Source",
            },
        )

        # Now update only name
        update_response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={"name": "New Name Only"},
        )
        assert update_response.status_code == 200

        # Verify other fields are preserved
        get_response = await client.get(f"/api/v1/models/{test_model.id}", headers=auth_headers)
        data = get_response.json()
        assert data["name"] == "New Name Only"
        # Other fields should be preserved
        assert data["description"] == "Original Description"
        assert data["designer"] == "Original Designer"
        assert data["source"] == "Original Source"


class TestModelsMetadataFields:
    """Test metadata fields specifically (designer, source, machine, print settings)."""

    @pytest.mark.asyncio
    async def test_designer_field(self, client: AsyncClient, auth_headers: dict, test_model: Model):
        """Test designer field updates and persists."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={"designer": "Cinderwings"},
        )
        assert response.status_code == 200
        assert response.json()["designer"] == "Cinderwings"

        # Verify persistence
        get_response = await client.get(f"/api/v1/models/{test_model.id}", headers=auth_headers)
        assert get_response.json()["designer"] == "Cinderwings"

    @pytest.mark.asyncio
    async def test_source_field(self, client: AsyncClient, auth_headers: dict, test_model: Model):
        """Test source field updates and persists."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={"source": "Makerworld"},
        )
        assert response.status_code == 200
        assert response.json()["source"] == "Makerworld"

    @pytest.mark.asyncio
    async def test_machine_field(self, client: AsyncClient, auth_headers: dict, test_model: Model):
        """Test machine field updates and persists."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={"machine": "Bambulabs P2S"},
        )
        assert response.status_code == 200
        assert response.json()["machine"] == "Bambulabs P2S"

    @pytest.mark.asyncio
    async def test_print_settings_fields(
        self, client: AsyncClient, auth_headers: dict, test_model: Model
    ):
        """Test print time and prints per plate fields."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={
                "print_time_minutes": 360,
                "prints_per_plate": 6,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["print_time_minutes"] == 360
        assert data["prints_per_plate"] == 6


class TestModelsCostFields:
    """Test cost-related fields (labor, overhead)."""

    @pytest.mark.asyncio
    async def test_labor_hours(self, client: AsyncClient, auth_headers: dict, test_model: Model):
        """Test labor hours field."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={"labor_hours": "4.5"},
        )
        assert response.status_code == 200
        assert float(response.json()["labor_hours"]) == 4.5

    @pytest.mark.asyncio
    async def test_labor_rate_override(
        self, client: AsyncClient, auth_headers: dict, test_model: Model
    ):
        """Test labor rate override field."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={"labor_rate_override": "20.00"},
        )
        assert response.status_code == 200
        assert float(response.json()["labor_rate_override"]) == 20.00

    @pytest.mark.asyncio
    async def test_overhead_percentage(
        self, client: AsyncClient, auth_headers: dict, test_model: Model
    ):
        """Test overhead percentage field."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={"overhead_percentage": "25"},
        )
        assert response.status_code == 200
        assert float(response.json()["overhead_percentage"]) == 25


class TestModelsInventoryFields:
    """Test inventory-related fields."""

    @pytest.mark.asyncio
    async def test_units_in_stock(self, client: AsyncClient, auth_headers: dict, test_model: Model):
        """Test units in stock field."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={"units_in_stock": 50},
        )
        assert response.status_code == 200
        assert response.json()["units_in_stock"] == 50

    @pytest.mark.asyncio
    async def test_is_active_toggle(
        self, client: AsyncClient, auth_headers: dict, test_model: Model
    ):
        """Test toggling is_active field."""
        # Set to inactive
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

        # Set back to active
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            headers=auth_headers,
            json={"is_active": True},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True


class TestModelsTenantIsolation:
    """Test multi-tenant isolation for models."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_model(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        """Test models from other tenants are not visible."""
        from app.models.tenant import Tenant

        # Create a different tenant
        other_tenant = Tenant(
            id=uuid4(), name="Other Tenant", slug="other-tenant-model", settings={}
        )
        db_session.add(other_tenant)
        await db_session.flush()

        # Create a model for the other tenant
        other_model = Model(
            id=uuid4(),
            tenant_id=other_tenant.id,
            sku="OTHER-MOD-001",
            name="Other Tenant Model",
            description="Should not be visible",
        )
        db_session.add(other_model)
        await db_session.commit()

        # Try to access other tenant's model
        response = await client.get(f"/api/v1/models/{other_model.id}", headers=auth_headers)
        assert response.status_code == 404


class TestModelsValidation:
    """Test validation rules for model fields."""

    @pytest.mark.asyncio
    async def test_duplicate_sku_rejected(
        self, client: AsyncClient, auth_headers: dict, test_model: Model
    ):
        """Test that duplicate SKU is rejected."""
        response = await client.post(
            "/api/v1/models",
            headers=auth_headers,
            json={
                "sku": test_model.sku,  # Duplicate
                "name": "Duplicate SKU Model",
            },
        )
        assert response.status_code in [400, 409]

    @pytest.mark.asyncio
    async def test_model_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test accessing non-existent model returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/models/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_overhead_percentage(self, client: AsyncClient, auth_headers: dict):
        """Test that overhead percentage > 100 is rejected."""
        response = await client.post(
            "/api/v1/models",
            headers=auth_headers,
            json={
                "sku": f"INVALID-{uuid4().hex[:8].upper()}",
                "name": "Invalid Overhead Model",
                "overhead_percentage": "150",  # Invalid - should be 0-100
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_labor_hours_rejected(self, client: AsyncClient, auth_headers: dict):
        """Test that negative labor hours is rejected."""
        response = await client.post(
            "/api/v1/models",
            headers=auth_headers,
            json={
                "sku": f"NEG-{uuid4().hex[:8].upper()}",
                "name": "Negative Labor Model",
                "labor_hours": "-1",
            },
        )
        assert response.status_code == 422
