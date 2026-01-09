"""Comprehensive integration tests for Consumables API - all fields and operations."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.consumable import ConsumableType, ConsumablePurchase
from app.models.tenant import Tenant


@pytest_asyncio.fixture
async def test_consumable_type(db_session: AsyncSession, test_tenant: Tenant) -> ConsumableType:
    """Create a test consumable type."""
    consumable = ConsumableType(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="TEST-MAGNET-001",
        name="Test 6mm Magnets",
        description="Test magnets for unit tests",
        category="magnets",
        unit_of_measure="pack",
        current_cost_per_unit=5.99,
        quantity_on_hand=100,
        reorder_point=20,
        reorder_quantity=50,
        preferred_supplier="Test Supplier",
        supplier_sku="MAG-6MM-100",
        supplier_url="https://example.com/magnets",
        typical_lead_days=3,
        is_active=True,
    )
    db_session.add(consumable)
    await db_session.commit()
    await db_session.refresh(consumable)
    return consumable


@pytest_asyncio.fixture
async def test_consumable_purchase(
    db_session: AsyncSession, test_tenant: Tenant, test_consumable_type: ConsumableType
) -> ConsumablePurchase:
    """Create a test consumable purchase."""
    purchase = ConsumablePurchase(
        id=uuid4(),
        tenant_id=test_tenant.id,
        consumable_type_id=test_consumable_type.id,
        quantity_purchased=100,
        total_cost=599.00,
        cost_per_unit=5.99,  # Required field
        quantity_remaining=100,  # Required field
        supplier="Test Supplier",
        order_reference="ORD-12345",
        purchase_url="https://example.com/order/12345",
        purchase_date=date.today(),
        notes="Test purchase",
    )
    db_session.add(purchase)
    await db_session.commit()
    await db_session.refresh(purchase)
    return purchase


class TestConsumableTypesBasicCRUD:
    """Test basic CRUD operations for Consumable Types."""

    @pytest.mark.asyncio
    async def test_create_consumable_type_minimal(self, client: AsyncClient, auth_headers: dict):
        """Test creating a consumable type with minimal required fields."""
        response = await client.post(
            "/api/v1/consumables/types",
            headers=auth_headers,
            json={
                "sku": f"MIN-{uuid4().hex[:8].upper()}",
                "name": "Minimal Consumable",
            },
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "Minimal Consumable"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_consumable_type_all_fields(self, client: AsyncClient, auth_headers: dict):
        """Test creating a consumable type with all fields populated."""
        sku = f"FULL-{uuid4().hex[:8].upper()}"
        response = await client.post(
            "/api/v1/consumables/types",
            headers=auth_headers,
            json={
                "sku": sku,
                "name": "Full Featured Consumable",
                "description": "A consumable with all fields for testing",
                "category": "hardware",
                "unit_of_measure": "each",
                "current_cost_per_unit": 2.50,
                "quantity_on_hand": 200,
                "reorder_point": 50,
                "reorder_quantity": 100,
                "preferred_supplier": "Hardware Supplier",
                "supplier_sku": "HW-12345",
                "supplier_url": "https://supplier.com/hw-12345",
                "typical_lead_days": 5,
                "is_active": True,
            },
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["sku"] == sku
        assert data["name"] == "Full Featured Consumable"
        assert data["description"] == "A consumable with all fields for testing"
        assert data["category"] == "hardware"
        assert data["unit_of_measure"] == "each"
        assert data["current_cost_per_unit"] == 2.50
        assert data["quantity_on_hand"] == 200
        assert data["reorder_point"] == 50
        assert data["reorder_quantity"] == 100
        assert data["preferred_supplier"] == "Hardware Supplier"
        assert data["supplier_sku"] == "HW-12345"
        assert data["supplier_url"] == "https://supplier.com/hw-12345"
        assert data["typical_lead_days"] == 5
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_consumable_type(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test retrieving a consumable type by ID."""
        response = await client.get(
            f"/api/v1/consumables/types/{test_consumable_type.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_consumable_type.id)
        assert data["name"] == test_consumable_type.name

    @pytest.mark.asyncio
    async def test_list_consumable_types(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test listing consumable types."""
        response = await client.get("/api/v1/consumables/types", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "consumables" in data
        assert isinstance(data["consumables"], list)
        assert len(data["consumables"]) >= 1

    @pytest.mark.asyncio
    async def test_update_consumable_type(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test updating a consumable type."""
        response = await client.put(
            f"/api/v1/consumables/types/{test_consumable_type.id}",
            headers=auth_headers,
            json={
                "name": "Updated Consumable Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Consumable Name"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_consumable_type(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test deleting a consumable type."""
        response = await client.delete(
            f"/api/v1/consumables/types/{test_consumable_type.id}", headers=auth_headers
        )
        assert response.status_code in [200, 204]

        # Verify consumable type is deleted
        response = await client.get(
            f"/api/v1/consumables/types/{test_consumable_type.id}", headers=auth_headers
        )
        assert response.status_code == 404


class TestConsumableTypesAllFieldsPersistence:
    """Test that all consumable type fields persist correctly."""

    @pytest.mark.asyncio
    async def test_all_fields_persist_after_update(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test that ALL consumable type fields persist after update and refetch."""
        update_data = {
            "name": "Persistence Test Consumable",
            "description": "Testing field persistence",
            "category": "finishing",
            "unit_of_measure": "ml",
            "current_cost_per_unit": 15.99,
            "quantity_on_hand": 500,
            "reorder_point": 100,
            "reorder_quantity": 200,
            "preferred_supplier": "Persistence Supplier",
            "supplier_sku": "PERS-SKU-001",
            "supplier_url": "https://persistence.example.com",
            "typical_lead_days": 7,
            "is_active": True,
        }

        update_response = await client.put(
            f"/api/v1/consumables/types/{test_consumable_type.id}",
            headers=auth_headers,
            json=update_data,
        )
        assert update_response.status_code == 200

        # Fetch and verify all fields
        get_response = await client.get(
            f"/api/v1/consumables/types/{test_consumable_type.id}", headers=auth_headers
        )
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["name"] == "Persistence Test Consumable"
        assert data["description"] == "Testing field persistence"
        assert data["category"] == "finishing"
        assert data["unit_of_measure"] == "ml"
        assert data["current_cost_per_unit"] == 15.99
        assert data["quantity_on_hand"] == 500
        assert data["reorder_point"] == 100
        assert data["reorder_quantity"] == 200
        assert data["preferred_supplier"] == "Persistence Supplier"
        assert data["supplier_sku"] == "PERS-SKU-001"
        assert data["supplier_url"] == "https://persistence.example.com"
        assert data["typical_lead_days"] == 7
        assert data["is_active"] is True


class TestConsumableTypesStockManagement:
    """Test stock management fields and operations."""

    @pytest.mark.asyncio
    async def test_stock_adjustment(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test adjusting stock levels."""
        initial_qty = test_consumable_type.quantity_on_hand

        response = await client.post(
            f"/api/v1/consumables/types/{test_consumable_type.id}/adjust-stock",
            headers=auth_headers,
            json={
                "quantity_adjustment": 50,
                "reason": "Received shipment",
                "notes": "Order #12345",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantity_on_hand"] == initial_qty + 50

    @pytest.mark.asyncio
    async def test_stock_adjustment_negative(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test reducing stock levels."""
        initial_qty = test_consumable_type.quantity_on_hand

        response = await client.post(
            f"/api/v1/consumables/types/{test_consumable_type.id}/adjust-stock",
            headers=auth_headers,
            json={
                "quantity_adjustment": -20,
                "reason": "Damaged items",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantity_on_hand"] == initial_qty - 20

    @pytest.mark.asyncio
    async def test_low_stock_alerts(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_tenant: Tenant
    ):
        """Test low stock alerts endpoint."""
        # Create a consumable with low stock
        low_stock = ConsumableType(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku=f"LOW-{uuid4().hex[:8].upper()}",
            name="Low Stock Item",
            quantity_on_hand=5,
            reorder_point=20,
            is_active=True,
        )
        db_session.add(low_stock)
        await db_session.commit()

        response = await client.get("/api/v1/consumables/alerts/low-stock", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include our low stock item
        low_stock_ids = [item["consumable_id"] for item in data]
        assert str(low_stock.id) in low_stock_ids


class TestConsumableTypesSupplierFields:
    """Test supplier-related fields."""

    @pytest.mark.asyncio
    async def test_supplier_fields_update(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test updating supplier fields."""
        response = await client.put(
            f"/api/v1/consumables/types/{test_consumable_type.id}",
            headers=auth_headers,
            json={
                "preferred_supplier": "New Supplier Inc",
                "supplier_sku": "NEW-SKU-999",
                "supplier_url": "https://newsupplier.com/product",
                "typical_lead_days": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preferred_supplier"] == "New Supplier Inc"
        assert data["supplier_sku"] == "NEW-SKU-999"
        assert data["supplier_url"] == "https://newsupplier.com/product"
        assert data["typical_lead_days"] == 10


class TestConsumableTypesCategories:
    """Test category-related functionality."""

    @pytest.mark.asyncio
    async def test_get_categories(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test getting list of categories."""
        response = await client.get("/api/v1/consumables/categories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Our test consumable has category "magnets"
        assert "magnets" in data


class TestConsumablePurchasesCRUD:
    """Test CRUD operations for consumable purchases."""

    @pytest.mark.asyncio
    async def test_create_purchase(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test creating a consumable purchase."""
        response = await client.post(
            "/api/v1/consumables/purchases",
            headers=auth_headers,
            json={
                "consumable_type_id": str(test_consumable_type.id),
                "quantity_purchased": 50,
                "total_cost": 299.50,
                "supplier": "Test Supplier",
                "order_reference": "ORD-TEST-001",
                "purchase_url": "https://example.com/order",
                "purchase_date": "2024-12-01",
                "notes": "Test purchase notes",
            },
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["quantity_purchased"] == 50
        assert data["total_cost"] == 299.50
        assert data["supplier"] == "Test Supplier"

    @pytest.mark.asyncio
    async def test_list_purchases(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_consumable_purchase: ConsumablePurchase,
    ):
        """Test listing consumable purchases."""
        response = await client.get("/api/v1/consumables/purchases", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "purchases" in data
        assert isinstance(data["purchases"], list)
        assert len(data["purchases"]) >= 1

    @pytest.mark.asyncio
    async def test_get_purchase(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_consumable_purchase: ConsumablePurchase,
    ):
        """Test getting a single purchase."""
        response = await client.get(
            f"/api/v1/consumables/purchases/{test_consumable_purchase.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_consumable_purchase.id)
        assert data["quantity_purchased"] == test_consumable_purchase.quantity_purchased

    @pytest.mark.asyncio
    async def test_delete_purchase(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_consumable_purchase: ConsumablePurchase,
    ):
        """Test deleting a purchase."""
        response = await client.delete(
            f"/api/v1/consumables/purchases/{test_consumable_purchase.id}",
            headers=auth_headers,
        )
        assert response.status_code in [200, 204]

        # Verify purchase is deleted
        response = await client.get(
            f"/api/v1/consumables/purchases/{test_consumable_purchase.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestConsumableUsage:
    """Test consumable usage tracking."""

    @pytest.mark.asyncio
    async def test_list_usage(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test listing usage records."""
        response = await client.get("/api/v1/consumables/usage", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "usage" in data
        assert isinstance(data["usage"], list)


class TestConsumableTypesValidation:
    """Test validation rules for consumable types."""

    @pytest.mark.asyncio
    async def test_consumable_type_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test accessing non-existent consumable type returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/consumables/types/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_duplicate_sku_rejected(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test that duplicate SKU is rejected."""
        response = await client.post(
            "/api/v1/consumables/types",
            headers=auth_headers,
            json={
                "sku": test_consumable_type.sku,  # Duplicate
                "name": "Duplicate SKU Consumable",
            },
        )
        assert response.status_code in [400, 409]

    @pytest.mark.asyncio
    async def test_negative_quantity_rejected(self, client: AsyncClient, auth_headers: dict):
        """Test that negative quantity_on_hand is rejected."""
        response = await client.post(
            "/api/v1/consumables/types",
            headers=auth_headers,
            json={
                "sku": f"NEG-{uuid4().hex[:8].upper()}",
                "name": "Negative Quantity",
                "quantity_on_hand": -10,
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_cost_rejected(self, client: AsyncClient, auth_headers: dict):
        """Test that negative cost is rejected."""
        response = await client.post(
            "/api/v1/consumables/types",
            headers=auth_headers,
            json={
                "sku": f"NEGCOST-{uuid4().hex[:8].upper()}",
                "name": "Negative Cost",
                "current_cost_per_unit": -5.00,
            },
        )
        assert response.status_code == 422


class TestConsumableTypesTenantIsolation:
    """Test multi-tenant isolation for consumable types."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_consumable(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test consumable types from other tenants are not visible."""
        # Create a different tenant
        other_tenant = Tenant(
            id=uuid4(), name="Other Tenant", slug="other-tenant-consumable", settings={}
        )
        db_session.add(other_tenant)
        await db_session.flush()

        # Create a consumable for the other tenant
        other_consumable = ConsumableType(
            id=uuid4(),
            tenant_id=other_tenant.id,
            sku="OTHER-CONS-001",
            name="Other Tenant Consumable",
            is_active=True,
        )
        db_session.add(other_consumable)
        await db_session.commit()

        # Try to access other tenant's consumable
        response = await client.get(
            f"/api/v1/consumables/types/{other_consumable.id}", headers=auth_headers
        )
        assert response.status_code == 404


class TestConsumableTypesComputedFields:
    """Test computed fields in responses."""

    @pytest.mark.asyncio
    async def test_is_low_stock_field(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_tenant: Tenant
    ):
        """Test is_low_stock computed field."""
        # Create consumable with low stock
        low_stock = ConsumableType(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku=f"LOW-COMP-{uuid4().hex[:8].upper()}",
            name="Low Stock Computed",
            quantity_on_hand=5,
            reorder_point=20,
            is_active=True,
        )
        db_session.add(low_stock)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/consumables/types/{low_stock.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_low_stock"] is True

    @pytest.mark.asyncio
    async def test_stock_value_field(
        self, client: AsyncClient, auth_headers: dict, test_consumable_type: ConsumableType
    ):
        """Test stock_value computed field."""
        response = await client.get(
            f"/api/v1/consumables/types/{test_consumable_type.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # stock_value = quantity_on_hand * current_cost_per_unit
        expected_value = test_consumable_type.quantity_on_hand * (
            test_consumable_type.current_cost_per_unit or 0
        )
        assert data["stock_value"] == expected_value
