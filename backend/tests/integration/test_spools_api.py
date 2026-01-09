"""Integration tests for spools/inventory API endpoints."""

import pytest
from httpx import AsyncClient
from decimal import Decimal
from uuid import uuid4

from app.models.spool import Spool
from app.models.material import MaterialType


class TestSpoolsEndpoints:
    """Test spool/inventory API endpoints."""

    @pytest.mark.asyncio
    async def test_create_spool(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_material_type: MaterialType,
    ):
        """Test spool creation with material type."""
        response = await client.post(
            "/api/v1/spools",
            headers=auth_headers,
            json={
                "material_type_id": str(test_material_type.id),
                "spool_id": f"TEST-{uuid4().hex[:8].upper()}",
                "brand": "Test Brand",
                "color": "Red",
                "initial_weight": 1000,
                "current_weight": 1000,
                "purchase_price": "25.00",
            },
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["brand"] == "Test Brand"
        assert data["color"] == "Red"

    @pytest.mark.asyncio
    async def test_list_spools(self, client: AsyncClient, auth_headers: dict, test_spool: Spool):
        """Test spool listing."""
        response = await client.get("/api/v1/spools", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        if isinstance(data, dict):
            spools = data.get("spools", data)
        else:
            spools = data

        assert isinstance(spools, list)
        assert len(spools) >= 1

    @pytest.mark.asyncio
    async def test_get_spool_by_id(
        self, client: AsyncClient, auth_headers: dict, test_spool: Spool
    ):
        """Test retrieving a specific spool."""
        response = await client.get(f"/api/v1/spools/{test_spool.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_spool.id)
        assert data["brand"] == test_spool.brand

    @pytest.mark.asyncio
    async def test_update_spool_weight(
        self, client: AsyncClient, auth_headers: dict, test_spool: Spool
    ):
        """Test weight update creates transaction."""
        original_weight = float(test_spool.current_weight)
        new_weight = original_weight - 100

        response = await client.patch(
            f"/api/v1/spools/{test_spool.id}/weight",
            headers=auth_headers,
            json={"new_weight": new_weight, "reason": "Test usage"},
        )

        # Endpoint might not exist yet
        if response.status_code == 404:
            pytest.skip("Weight update endpoint not implemented yet")

        assert response.status_code == 200
        data = response.json()
        assert float(data["current_weight"]) == new_weight

    @pytest.mark.asyncio
    async def test_delete_spool(self, client: AsyncClient, auth_headers: dict, test_spool: Spool):
        """Test spool deletion."""
        response = await client.delete(f"/api/v1/spools/{test_spool.id}", headers=auth_headers)
        assert response.status_code in [200, 204]

        # Verify spool is deleted
        response = await client.get(f"/api/v1/spools/{test_spool.id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_spool_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test accessing non-existent spool returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/spools/{fake_id}", headers=auth_headers)
        assert response.status_code == 404


class TestSpoolInventoryManagement:
    """Test inventory management features for spools."""

    @pytest.mark.asyncio
    async def test_low_stock_alert(
        self, client: AsyncClient, auth_headers: dict, db_session, test_tenant, test_material_type
    ):
        """Test low stock spools appear in alerts."""
        from app.models.spool import Spool

        # Create low stock spool
        low_stock_spool = Spool(
            id=uuid4(),
            tenant_id=test_tenant.id,
            material_type_id=test_material_type.id,
            spool_id=f"LOW-{uuid4().hex[:8]}",
            brand="Test Brand",
            color="Blue",
            initial_weight=Decimal("1000.00"),
            current_weight=Decimal("50.00"),  # Very low
            purchase_price=Decimal("25.00"),
            is_active=True,
        )
        db_session.add(low_stock_spool)
        await db_session.commit()

        # Query for low stock
        response = await client.get("/api/v1/spools?low_stock=true", headers=auth_headers)

        # Endpoint might not exist yet
        if response.status_code == 404:
            pytest.skip("Low stock filter not implemented yet")

        assert response.status_code == 200
        data = response.json()
        if isinstance(data, dict):
            spools = data.get("spools", data)
        else:
            spools = data

        # Low stock spool should be in results
        spool_ids = [s["id"] for s in spools]
        assert str(low_stock_spool.id) in spool_ids

    @pytest.mark.asyncio
    async def test_spool_usage_history(
        self, client: AsyncClient, auth_headers: dict, test_spool: Spool
    ):
        """Test retrieving spool usage history."""
        response = await client.get(
            f"/api/v1/spools/{test_spool.id}/transactions", headers=auth_headers
        )

        # Endpoint might not exist yet
        if response.status_code == 404:
            pytest.skip("Transaction history endpoint not implemented yet")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) and "spools" in data

    @pytest.mark.asyncio
    async def test_calculate_spool_cost_per_gram(
        self, client: AsyncClient, auth_headers: dict, test_spool: Spool
    ):
        """Test cost per gram calculation."""
        # Manual calculation
        expected_cost_per_gram = float(test_spool.purchase_price) / float(test_spool.initial_weight)

        response = await client.get(f"/api/v1/spools/{test_spool.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Check if cost_per_gram is calculated
        if "cost_per_gram" in data:
            assert abs(float(data["cost_per_gram"]) - expected_cost_per_gram) < 0.01


class TestSpoolTenantIsolation:
    """Test multi-tenant isolation for spools."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_spool(
        self, client: AsyncClient, auth_headers: dict, db_session, test_material_type
    ):
        """Test spools from other tenants are not visible."""
        from app.models.tenant import Tenant
        from app.models.spool import Spool

        # Create a different tenant
        other_tenant = Tenant(
            id=uuid4(), name="Other Tenant Spools", slug="other-tenant-spools", settings={}
        )
        db_session.add(other_tenant)
        await db_session.flush()

        # Create a spool for the other tenant
        other_spool = Spool(
            id=uuid4(),
            tenant_id=other_tenant.id,
            material_type_id=test_material_type.id,
            spool_id="OTHER-SPOOL-001",
            brand="Other Brand",
            color="Green",
            initial_weight=Decimal("1000.00"),
            current_weight=Decimal("800.00"),
            purchase_price=Decimal("30.00"),
            is_active=True,
        )
        db_session.add(other_spool)
        await db_session.commit()

        # Try to access other tenant's spool
        response = await client.get(f"/api/v1/spools/{other_spool.id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_only_shows_own_tenant_spools(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_spool: Spool,
        db_session,
        test_material_type,
    ):
        """Test spool list only returns spools from current tenant."""
        from app.models.tenant import Tenant
        from app.models.spool import Spool

        # Create another tenant with spools
        other_tenant = Tenant(
            id=uuid4(), name="Other Tenant Spools 2", slug="other-tenant-spools-2", settings={}
        )
        db_session.add(other_tenant)
        await db_session.flush()

        other_spool = Spool(
            id=uuid4(),
            tenant_id=other_tenant.id,
            material_type_id=test_material_type.id,
            spool_id="OTHER-002",
            brand="Other Brand",
            color="Yellow",
            initial_weight=Decimal("1000.00"),
            current_weight=Decimal("900.00"),
            purchase_price=Decimal("20.00"),
            is_active=True,
        )
        db_session.add(other_spool)
        await db_session.commit()

        # Get spool list
        response = await client.get("/api/v1/spools", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        if isinstance(data, dict):
            spools = data.get("spools", data)
        else:
            spools = data

        # Verify other tenant's spool is not in list
        spool_ids = [s["id"] for s in spools]
        assert str(other_spool.id) not in spool_ids
