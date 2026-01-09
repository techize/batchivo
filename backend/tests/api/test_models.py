"""Tests for model catalog API endpoints."""

from decimal import Decimal
from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model import Model
from app.models.model_component import ModelComponent
from app.models.model_material import ModelMaterial
from app.models.spool import Spool
from app.models.tenant import Tenant


# ============================================
# Fixtures
# ============================================


@pytest_asyncio.fixture
async def second_model(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> Model:
    """Create a second test model."""
    model = Model(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="MODEL-002",
        name="Second Model",
        category="Category A",
        print_time_minutes=90,
        is_active=True,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def inactive_model(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> Model:
    """Create an inactive model."""
    model = Model(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="MODEL-INACTIVE",
        name="Inactive Model",
        is_active=False,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def model_with_materials(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_spool: Spool,
) -> Model:
    """Create a model with BOM materials."""
    model = Model(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="MODEL-BOM",
        name="Model with BOM",
        print_time_minutes=60,
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()

    material = ModelMaterial(
        id=uuid4(),
        model_id=model.id,
        spool_id=test_spool.id,
        weight_grams=Decimal("50.0"),
        cost_per_gram=Decimal("0.025"),
    )
    db_session.add(material)

    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def model_with_components(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> Model:
    """Create a model with components."""
    model = Model(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="MODEL-COMP",
        name="Model with Components",
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()

    component = ModelComponent(
        id=uuid4(),
        model_id=model.id,
        component_name="Test Component",
        quantity=2,
        unit_cost=Decimal("1.50"),
        supplier="Test Supplier",
    )
    db_session.add(component)

    await db_session.commit()
    await db_session.refresh(model)
    return model


# ============================================
# Test Classes
# ============================================


class TestCreateModel:
    """Tests for model creation endpoint."""

    async def test_create_model(
        self,
        client: AsyncClient,
    ):
        """Test creating a new model."""
        response = await client.post(
            "/api/v1/models",
            json={
                "sku": "NEW-MODEL-001",
                "name": "New Test Model",
                "description": "A test model",
                "category": "Test Category",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "NEW-MODEL-001"
        assert data["name"] == "New Test Model"
        assert data["is_active"] is True
        assert "cost_breakdown" in data

    async def test_create_model_with_all_fields(
        self,
        client: AsyncClient,
    ):
        """Test creating model with all optional fields."""
        response = await client.post(
            "/api/v1/models",
            json={
                "sku": "FULL-MODEL-001",
                "name": "Full Model",
                "description": "Complete model",
                "category": "Category A",
                "labor_hours": 0.5,
                "overhead_percentage": 10.0,
                "designer": "Test Designer",
                "source": "Thangs",
                "print_time_minutes": 120,
                "prints_per_plate": 3,
                "machine": "Bambu A1 Mini",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["labor_hours"] == "0.50"  # Decimal(10,2) formatting
        assert data["designer"] == "Test Designer"
        assert data["print_time_minutes"] == 120
        assert data["prints_per_plate"] == 3

    async def test_create_model_duplicate_sku(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test that duplicate SKU is rejected."""
        response = await client.post(
            "/api/v1/models",
            json={
                "sku": test_model.sku,  # Duplicate
                "name": "Duplicate Model",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_create_model_missing_required_fields(
        self,
        client: AsyncClient,
    ):
        """Test that missing required fields return 422."""
        response = await client.post(
            "/api/v1/models",
            json={
                "name": "No SKU Model",
            },
        )
        assert response.status_code == 422

    async def test_create_model_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.post(
            "/api/v1/models",
            json={
                "sku": "TEST",
                "name": "Test",
            },
        )
        assert response.status_code == 401


class TestListModels:
    """Tests for model list endpoint."""

    async def test_list_models_empty(
        self,
        client: AsyncClient,
    ):
        """Test listing models when none exist."""
        response = await client.get("/api/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data

    async def test_list_models(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test listing models."""
        response = await client.get("/api/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["models"]) >= 1

    async def test_list_models_pagination(
        self,
        client: AsyncClient,
        test_model,
        second_model,
    ):
        """Test model list pagination."""
        response = await client.get("/api/v1/models?skip=0&limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["models"]) == 1
        assert data["skip"] == 0
        assert data["limit"] == 1

    async def test_list_models_search_by_sku(
        self,
        client: AsyncClient,
        test_model,
        second_model,
    ):
        """Test searching models by SKU."""
        response = await client.get(f"/api/v1/models?search={test_model.sku}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(m["sku"] == test_model.sku for m in data["models"])

    async def test_list_models_search_by_name(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test searching models by name."""
        response = await client.get("/api/v1/models?search=Test")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_list_models_filter_by_category(
        self,
        client: AsyncClient,
        second_model,
    ):
        """Test filtering models by category."""
        response = await client.get("/api/v1/models?category=Category A")
        assert response.status_code == 200
        data = response.json()
        assert all(m["category"] == "Category A" for m in data["models"])

    async def test_list_models_filter_active_only(
        self,
        client: AsyncClient,
        test_model,
        inactive_model,
    ):
        """Test filtering for active models only."""
        response = await client.get("/api/v1/models?is_active=true")
        assert response.status_code == 200
        data = response.json()
        assert all(m["is_active"] is True for m in data["models"])

    async def test_list_models_filter_inactive(
        self,
        client: AsyncClient,
        inactive_model,
    ):
        """Test filtering for inactive models."""
        response = await client.get("/api/v1/models?is_active=false")
        assert response.status_code == 200
        data = response.json()
        assert all(m["is_active"] is False for m in data["models"])

    async def test_list_models_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/models")
        assert response.status_code == 401


class TestGetModel:
    """Tests for getting a specific model."""

    async def test_get_model(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test getting a specific model."""
        response = await client.get(f"/api/v1/models/{test_model.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_model.id)
        assert data["sku"] == test_model.sku
        assert data["name"] == test_model.name

    async def test_get_model_includes_cost_breakdown(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test that response includes cost breakdown."""
        response = await client.get(f"/api/v1/models/{test_model.id}")
        assert response.status_code == 200
        data = response.json()
        assert "cost_breakdown" in data
        cost = data["cost_breakdown"]
        assert "material_cost" in cost
        assert "component_cost" in cost
        assert "labor_cost" in cost
        assert "overhead_cost" in cost
        assert "total_cost" in cost

    async def test_get_model_not_found(
        self,
        client: AsyncClient,
    ):
        """Test getting non-existent model."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/models/{fake_id}")
        assert response.status_code == 404

    async def test_get_model_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_model,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get(f"/api/v1/models/{test_model.id}")
        assert response.status_code == 401


class TestGetProductionDefaults:
    """Tests for model production defaults endpoint."""

    async def test_get_production_defaults(
        self,
        client: AsyncClient,
        model_with_materials,
    ):
        """Test getting production defaults for a model."""
        response = await client.get(f"/api/v1/models/{model_with_materials.id}/production-defaults")
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == str(model_with_materials.id)
        assert data["sku"] == model_with_materials.sku
        assert data["name"] == model_with_materials.name
        assert "bom_materials" in data
        assert len(data["bom_materials"]) >= 1

    async def test_get_production_defaults_bom_structure(
        self,
        client: AsyncClient,
        model_with_materials,
    ):
        """Test production defaults BOM structure."""
        response = await client.get(f"/api/v1/models/{model_with_materials.id}/production-defaults")
        assert response.status_code == 200
        data = response.json()
        bom = data["bom_materials"][0]
        assert "spool_id" in bom
        assert "spool_name" in bom
        assert "material_type_code" in bom
        assert "color" in bom
        assert "weight_grams" in bom
        assert "current_weight" in bom
        assert "is_active" in bom

    async def test_get_production_defaults_not_found(
        self,
        client: AsyncClient,
    ):
        """Test getting production defaults for non-existent model."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/models/{fake_id}/production-defaults")
        assert response.status_code == 404

    async def test_get_production_defaults_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        model_with_materials,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get(
            f"/api/v1/models/{model_with_materials.id}/production-defaults"
        )
        assert response.status_code == 401


class TestUpdateModel:
    """Tests for model update endpoint."""

    async def test_update_model(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test updating a model."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            json={
                "name": "Updated Model Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Model Name"
        assert data["description"] == "Updated description"

    async def test_update_model_sku(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test updating model SKU."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            json={
                "sku": "UPDATED-SKU-001",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sku"] == "UPDATED-SKU-001"

    async def test_update_model_duplicate_sku(
        self,
        client: AsyncClient,
        test_model,
        second_model,
    ):
        """Test that updating to duplicate SKU is rejected."""
        response = await client.put(
            f"/api/v1/models/{test_model.id}",
            json={
                "sku": second_model.sku,  # Duplicate
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_update_model_not_found(
        self,
        client: AsyncClient,
    ):
        """Test updating non-existent model."""
        fake_id = uuid4()
        response = await client.put(
            f"/api/v1/models/{fake_id}",
            json={"name": "New Name"},
        )
        assert response.status_code == 404

    async def test_update_model_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_model,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.put(
            f"/api/v1/models/{test_model.id}",
            json={"name": "Updated"},
        )
        assert response.status_code == 401


class TestDeleteModel:
    """Tests for model deletion endpoint."""

    async def test_delete_model(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test deleting (soft delete) a model."""
        response = await client.delete(f"/api/v1/models/{test_model.id}")
        assert response.status_code == 204

        # Verify model is soft deleted (inactive)
        response = await client.get(f"/api/v1/models/{test_model.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    async def test_delete_model_not_found(
        self,
        client: AsyncClient,
    ):
        """Test deleting non-existent model."""
        fake_id = uuid4()
        response = await client.delete(f"/api/v1/models/{fake_id}")
        assert response.status_code == 404

    async def test_delete_model_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_model,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.delete(f"/api/v1/models/{test_model.id}")
        assert response.status_code == 401


class TestModelMaterials:
    """Tests for model materials (BOM) endpoints."""

    async def test_add_material(
        self,
        client: AsyncClient,
        test_model,
        test_spool,
    ):
        """Test adding material to model BOM."""
        response = await client.post(
            f"/api/v1/models/{test_model.id}/materials",
            json={
                "spool_id": str(test_spool.id),
                "weight_grams": 25.0,
                "cost_per_gram": 0.03,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["spool_id"] == str(test_spool.id)
        assert data["weight_grams"] == "25.00"  # Decimal formatting
        assert data["cost_per_gram"] == "0.0300"  # Decimal(10,4) formatting

    async def test_add_material_model_not_found(
        self,
        client: AsyncClient,
        test_spool,
    ):
        """Test adding material to non-existent model."""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/models/{fake_id}/materials",
            json={
                "spool_id": str(test_spool.id),
                "weight_grams": 25.0,
                "cost_per_gram": 0.03,
            },
        )
        assert response.status_code == 404

    async def test_add_material_spool_not_found(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test adding material with non-existent spool."""
        fake_spool_id = uuid4()
        response = await client.post(
            f"/api/v1/models/{test_model.id}/materials",
            json={
                "spool_id": str(fake_spool_id),
                "weight_grams": 25.0,
                "cost_per_gram": 0.03,
            },
        )
        assert response.status_code == 404

    async def test_remove_material(
        self,
        client: AsyncClient,
        model_with_materials: Model,
        db_session: AsyncSession,
    ):
        """Test removing material from model BOM."""
        from sqlalchemy import select

        # Get the material ID
        result = await db_session.execute(
            select(ModelMaterial).where(ModelMaterial.model_id == model_with_materials.id)
        )
        material = result.scalar_one()

        response = await client.delete(
            f"/api/v1/models/{model_with_materials.id}/materials/{material.id}"
        )
        assert response.status_code == 204

    async def test_remove_material_not_found(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test removing non-existent material."""
        fake_material_id = uuid4()
        response = await client.delete(
            f"/api/v1/models/{test_model.id}/materials/{fake_material_id}"
        )
        assert response.status_code == 404

    async def test_add_material_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_model,
        test_spool,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.post(
            f"/api/v1/models/{test_model.id}/materials",
            json={
                "spool_id": str(test_spool.id),
                "weight_grams": 25.0,
                "cost_per_gram": 0.03,
            },
        )
        assert response.status_code == 401


class TestModelComponents:
    """Tests for model components endpoints."""

    async def test_add_component(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test adding component to model."""
        response = await client.post(
            f"/api/v1/models/{test_model.id}/components",
            json={
                "component_name": "New Component",
                "quantity": 3,
                "unit_cost": 2.50,
                "supplier": "Test Supplier",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["component_name"] == "New Component"
        assert data["quantity"] == 3
        assert data["unit_cost"] == "2.50"
        assert data["supplier"] == "Test Supplier"

    async def test_add_component_model_not_found(
        self,
        client: AsyncClient,
    ):
        """Test adding component to non-existent model."""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/models/{fake_id}/components",
            json={
                "component_name": "Component",
                "quantity": 1,
                "unit_cost": 1.00,
            },
        )
        assert response.status_code == 404

    async def test_remove_component(
        self,
        client: AsyncClient,
        model_with_components: Model,
        db_session: AsyncSession,
    ):
        """Test removing component from model."""
        from sqlalchemy import select

        # Get the component ID
        result = await db_session.execute(
            select(ModelComponent).where(ModelComponent.model_id == model_with_components.id)
        )
        component = result.scalar_one()

        response = await client.delete(
            f"/api/v1/models/{model_with_components.id}/components/{component.id}"
        )
        assert response.status_code == 204

    async def test_remove_component_not_found(
        self,
        client: AsyncClient,
        test_model,
    ):
        """Test removing non-existent component."""
        fake_component_id = uuid4()
        response = await client.delete(
            f"/api/v1/models/{test_model.id}/components/{fake_component_id}"
        )
        assert response.status_code == 404

    async def test_add_component_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_model,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.post(
            f"/api/v1/models/{test_model.id}/components",
            json={
                "component_name": "Component",
                "quantity": 1,
                "unit_cost": 1.00,
            },
        )
        assert response.status_code == 401
