"""Tests for spool API endpoints."""

from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.filament_type import FilamentType
from app.models.material import MaterialType
from app.models.spool import Spool
from app.models.tenant import Tenant


# ============================================
# Fixtures
# ============================================


@pytest_asyncio.fixture
async def second_spool(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_material_type: MaterialType,
) -> Spool:
    """Create a second test spool."""
    ft = FilamentType(
        id=uuid4(),
        tenant_id=test_tenant.id,
        material_type_id=test_material_type.id,
        brand="Second Brand",
        color="Blue",
        color_hex="#0000FF",
        diameter=1.75,
        has_sample=False,
        translucent=False,
        glow=False,
    )
    db_session.add(ft)
    await db_session.flush()
    spool = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        filament_type_id=ft.id,
        spool_id="FIL-002",
        initial_weight=1000.0,
        current_weight=500.0,
        is_active=True,
    )
    db_session.add(spool)
    await db_session.commit()
    await db_session.refresh(spool)
    return spool


@pytest_asyncio.fixture
async def inactive_spool(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_material_type: MaterialType,
) -> Spool:
    """Create an inactive spool."""
    ft = FilamentType(
        id=uuid4(),
        tenant_id=test_tenant.id,
        material_type_id=test_material_type.id,
        brand="Inactive Brand",
        color="Green",
        diameter=1.75,
        has_sample=False,
        translucent=False,
        glow=False,
    )
    db_session.add(ft)
    await db_session.flush()
    spool = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        filament_type_id=ft.id,
        spool_id="FIL-003",
        initial_weight=1000.0,
        current_weight=0.0,
        is_active=False,
    )
    db_session.add(spool)
    await db_session.commit()
    await db_session.refresh(spool)
    return spool


@pytest_asyncio.fixture
async def low_stock_spool(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_material_type: MaterialType,
) -> Spool:
    """Create a low stock spool (<20% remaining)."""
    ft = FilamentType(
        id=uuid4(),
        tenant_id=test_tenant.id,
        material_type_id=test_material_type.id,
        brand="Low Stock Brand",
        color="Yellow",
        diameter=1.75,
        has_sample=False,
        translucent=False,
        glow=False,
    )
    db_session.add(ft)
    await db_session.flush()
    spool = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        filament_type_id=ft.id,
        spool_id="FIL-004",
        initial_weight=1000.0,
        current_weight=100.0,  # 10% remaining
        is_active=True,
    )
    db_session.add(spool)
    await db_session.commit()
    await db_session.refresh(spool)
    return spool


@pytest_asyncio.fixture
async def petg_material_type(
    db_session: AsyncSession,
    seed_material_types,
) -> MaterialType:
    """Get PETG material type from seeded data."""
    from sqlalchemy import select

    result = await db_session.execute(select(MaterialType).where(MaterialType.code == "PETG"))
    return result.scalar_one()


# ============================================
# Test Classes
# ============================================


class TestCreateSpool:
    """Tests for spool creation endpoint."""

    async def test_create_spool(
        self,
        client: AsyncClient,
        test_filament_type,
    ):
        """Test creating a new spool."""
        response = await client.post(
            "/api/v1/spools",
            json={
                "spool_id": "NEW-SPOOL-001",
                "filament_type_id": str(test_filament_type.id),
                "initial_weight": 1000.0,
                "current_weight": 1000.0,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["spool_id"] == "NEW-SPOOL-001"
        assert data["filament_type"]["brand"] == "Test Brand"
        assert data["filament_type"]["color"] == "Red"
        assert data["initial_weight"] == 1000.0
        assert data["current_weight"] == 1000.0
        assert data["filament_type"]["material_type_code"] == "PLA"

    async def test_create_spool_with_all_fields(
        self,
        client: AsyncClient,
        test_filament_type,
    ):
        """Test creating spool with all optional fields."""
        response = await client.post(
            "/api/v1/spools",
            json={
                "spool_id": "FULL-SPOOL-001",
                "filament_type_id": str(test_filament_type.id),
                "initial_weight": 1000.0,
                "current_weight": 1000.0,
                "empty_spool_weight": 150.0,
                "purchase_price": 25.99,
                "supplier": "Amazon",
                "storage_location": "Shelf A",
                "is_active": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["supplier"] == "Amazon"
        assert data["storage_location"] == "Shelf A"

    async def test_create_spool_missing_required_fields(
        self,
        client: AsyncClient,
    ):
        """Test that missing required fields return 422."""
        response = await client.post(
            "/api/v1/spools",
            json={
                "brand": "Incomplete Brand",
            },
        )
        assert response.status_code == 422

    async def test_create_spool_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        from uuid import uuid4 as _uuid4

        response = await unauthenticated_client.post(
            "/api/v1/spools",
            json={
                "spool_id": "TEST",
                "filament_type_id": str(_uuid4()),
                "initial_weight": 1000,
                "current_weight": 1000,
            },
        )
        assert response.status_code == 401


class TestListSpools:
    """Tests for spool list endpoint."""

    async def test_list_spools_empty(
        self,
        client: AsyncClient,
    ):
        """Test listing spools when none exist."""
        response = await client.get("/api/v1/spools")
        assert response.status_code == 200
        data = response.json()
        assert "spools" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    async def test_list_spools(
        self,
        client: AsyncClient,
        test_spool: Spool,
    ):
        """Test listing spools."""
        response = await client.get("/api/v1/spools")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["spools"]) >= 1

    async def test_list_spools_pagination(
        self,
        client: AsyncClient,
        test_spool: Spool,
        second_spool: Spool,
    ):
        """Test spool list pagination."""
        response = await client.get("/api/v1/spools?page=1&page_size=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["spools"]) == 1
        assert data["page"] == 1
        assert data["page_size"] == 1

    async def test_list_spools_search_by_brand(
        self,
        client: AsyncClient,
        test_spool: Spool,
        second_spool: Spool,
    ):
        """Test searching spools by brand."""
        response = await client.get("/api/v1/spools?search=Second")
        assert response.status_code == 200
        data = response.json()
        assert all("Second" in s["filament_type"]["brand"] for s in data["spools"])

    async def test_list_spools_search_by_color(
        self,
        client: AsyncClient,
        test_spool: Spool,
        second_spool: Spool,
    ):
        """Test searching spools by color."""
        response = await client.get("/api/v1/spools?search=Blue")
        assert response.status_code == 200
        data = response.json()
        assert all("Blue" in s["filament_type"]["color"] for s in data["spools"])

    async def test_list_spools_filter_by_material_type(
        self,
        client: AsyncClient,
        test_spool: Spool,
        test_material_type: MaterialType,
    ):
        """Test filtering spools by material type."""
        response = await client.get(f"/api/v1/spools?material_type_id={test_material_type.id}")
        assert response.status_code == 200
        data = response.json()
        assert all(s["filament_type"]["material_type_code"] == "PLA" for s in data["spools"])

    async def test_list_spools_filter_active_only(
        self,
        client: AsyncClient,
        test_spool: Spool,
        inactive_spool: Spool,
    ):
        """Test filtering for active spools only."""
        response = await client.get("/api/v1/spools?is_active=true")
        assert response.status_code == 200
        data = response.json()
        assert all(s["is_active"] is True for s in data["spools"])

    async def test_list_spools_filter_inactive_only(
        self,
        client: AsyncClient,
        test_spool: Spool,
        inactive_spool: Spool,
    ):
        """Test filtering for inactive spools only."""
        response = await client.get("/api/v1/spools?is_active=false")
        assert response.status_code == 200
        data = response.json()
        assert all(s["is_active"] is False for s in data["spools"])

    async def test_list_spools_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/spools")
        assert response.status_code == 401


class TestGetSpool:
    """Tests for getting a specific spool."""

    async def test_get_spool(
        self,
        client: AsyncClient,
        test_spool: Spool,
    ):
        """Test getting a specific spool."""
        response = await client.get(f"/api/v1/spools/{test_spool.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_spool.id)
        assert data["spool_id"] == test_spool.spool_id
        assert data["filament_type"]["brand"] == test_spool.filament_type.brand
        assert data["filament_type"]["color"] == test_spool.filament_type.color

    async def test_get_spool_includes_computed_fields(
        self,
        client: AsyncClient,
        test_spool: Spool,
    ):
        """Test that response includes computed fields."""
        response = await client.get(f"/api/v1/spools/{test_spool.id}")
        assert response.status_code == 200
        data = response.json()
        assert "remaining_weight" in data
        assert "remaining_percentage" in data
        assert "material_type_code" in data["filament_type"]
        assert "material_type_name" in data["filament_type"]
        assert data["remaining_percentage"] == 80.0  # 800/1000 * 100

    async def test_get_spool_not_found(
        self,
        client: AsyncClient,
    ):
        """Test getting non-existent spool."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/spools/{fake_id}")
        assert response.status_code == 404

    async def test_get_spool_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_spool: Spool,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get(f"/api/v1/spools/{test_spool.id}")
        assert response.status_code == 401


class TestUpdateSpool:
    """Tests for spool update endpoint."""

    async def test_update_spool(
        self,
        client: AsyncClient,
        test_spool: Spool,
    ):
        """Test updating a spool."""
        response = await client.put(
            f"/api/v1/spools/{test_spool.id}",
            json={
                "storage_location": "Updated Location",
                "supplier": "Updated Supplier",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["storage_location"] == "Updated Location"
        assert data["supplier"] == "Updated Supplier"

    async def test_update_spool_current_weight(
        self,
        client: AsyncClient,
        test_spool: Spool,
    ):
        """Test updating spool weight."""
        response = await client.put(
            f"/api/v1/spools/{test_spool.id}",
            json={
                "current_weight": 600.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_weight"] == 600.0
        assert data["remaining_percentage"] == 60.0

    async def test_update_spool_deactivate(
        self,
        client: AsyncClient,
        test_spool: Spool,
    ):
        """Test deactivating a spool."""
        response = await client.put(
            f"/api/v1/spools/{test_spool.id}",
            json={
                "is_active": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    async def test_update_spool_not_found(
        self,
        client: AsyncClient,
    ):
        """Test updating non-existent spool."""
        fake_id = uuid4()
        response = await client.put(
            f"/api/v1/spools/{fake_id}",
            json={"supplier": "New Supplier"},
        )
        assert response.status_code == 404

    async def test_update_spool_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_spool: Spool,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.put(
            f"/api/v1/spools/{test_spool.id}",
            json={"supplier": "Updated"},
        )
        assert response.status_code == 401


class TestDeleteSpool:
    """Tests for spool deletion endpoint."""

    async def test_delete_spool(
        self,
        client: AsyncClient,
        test_spool: Spool,
    ):
        """Test deleting a spool."""
        response = await client.delete(f"/api/v1/spools/{test_spool.id}")
        assert response.status_code == 204

        # Verify spool is gone
        response = await client.get(f"/api/v1/spools/{test_spool.id}")
        assert response.status_code == 404

    async def test_delete_spool_not_found(
        self,
        client: AsyncClient,
    ):
        """Test deleting non-existent spool."""
        fake_id = uuid4()
        response = await client.delete(f"/api/v1/spools/{fake_id}")
        assert response.status_code == 404

    async def test_delete_spool_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_spool: Spool,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.delete(f"/api/v1/spools/{test_spool.id}")
        assert response.status_code == 401


@pytest_asyncio.fixture
async def spool_with_fil_prefix(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_material_type: MaterialType,
) -> Spool:
    """Create a spool with FIL- prefix for ID generation tests."""
    ft = FilamentType(
        id=uuid4(),
        tenant_id=test_tenant.id,
        material_type_id=test_material_type.id,
        brand="FIL Brand",
        color="Pink",
        diameter=1.75,
        has_sample=False,
        translucent=False,
        glow=False,
    )
    db_session.add(ft)
    await db_session.flush()
    spool = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        filament_type_id=ft.id,
        spool_id="FIL-005",
        initial_weight=1000.0,
        current_weight=1000.0,
        is_active=True,
    )
    db_session.add(spool)
    await db_session.commit()
    await db_session.refresh(spool)
    return spool


@pytest_asyncio.fixture
async def spool_with_invalid_fil_suffix(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_material_type: MaterialType,
) -> Spool:
    """Create a spool with invalid FIL- suffix for edge case testing."""
    ft = FilamentType(
        id=uuid4(),
        tenant_id=test_tenant.id,
        material_type_id=test_material_type.id,
        brand="Invalid Brand",
        color="White",
        diameter=1.75,
        has_sample=False,
        translucent=False,
        glow=False,
    )
    db_session.add(ft)
    await db_session.flush()
    spool = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        filament_type_id=ft.id,
        spool_id="FIL-ABC",  # Non-numeric suffix
        initial_weight=1000.0,
        current_weight=1000.0,
        is_active=True,
    )
    db_session.add(spool)
    await db_session.commit()
    await db_session.refresh(spool)
    return spool


class TestDuplicateSpool:
    """Tests for spool duplication endpoint."""

    async def test_duplicate_spool(
        self,
        client: AsyncClient,
        test_spool: Spool,
    ):
        """Test duplicating a spool."""
        response = await client.post(f"/api/v1/spools/{test_spool.id}/duplicate")
        assert response.status_code == 201
        data = response.json()

        # New spool should have different id and spool_id
        assert data["id"] != str(test_spool.id)
        assert data["spool_id"] != test_spool.spool_id

        # Should preserve other attributes (filament_type is shared)
        assert data["filament_type"]["brand"] == test_spool.filament_type.brand
        assert data["filament_type"]["color"] == test_spool.filament_type.color
        assert data["filament_type"]["material_type_code"] == "PLA"

        # Duplicated spool should have full weight
        assert data["current_weight"] == float(test_spool.initial_weight)
        assert data["is_active"] is True

    async def test_duplicate_spool_increments_fil_id(
        self,
        client: AsyncClient,
        spool_with_fil_prefix: Spool,
    ):
        """Test that duplicating increments FIL- IDs correctly."""
        response = await client.post(f"/api/v1/spools/{spool_with_fil_prefix.id}/duplicate")
        assert response.status_code == 201
        data = response.json()

        # New spool should have incremented FIL- ID
        assert data["spool_id"] == "FIL-006"

    async def test_duplicate_spool_first_fil_id(
        self,
        client: AsyncClient,
        test_spool: Spool,  # Has TEST-SPOOL-001 ID, not FIL-
    ):
        """Test that duplicate starts at FIL-001 when no FIL- spools exist."""
        response = await client.post(f"/api/v1/spools/{test_spool.id}/duplicate")
        assert response.status_code == 201
        data = response.json()

        # First FIL- ID should be FIL-001
        assert data["spool_id"] == "FIL-001"

    async def test_duplicate_spool_invalid_fil_suffix(
        self,
        client: AsyncClient,
        spool_with_invalid_fil_suffix: Spool,
    ):
        """Test duplicate handles invalid FIL- suffix gracefully."""
        # FIL-ABC exists, but ABC is not a valid number
        # The duplicate should fall back to FIL-001
        response = await client.post(f"/api/v1/spools/{spool_with_invalid_fil_suffix.id}/duplicate")
        assert response.status_code == 201
        data = response.json()

        # Should fall back to FIL-001 when parsing fails
        assert data["spool_id"] == "FIL-001"

    async def test_duplicate_spool_not_found(
        self,
        client: AsyncClient,
    ):
        """Test duplicating non-existent spool."""
        fake_id = uuid4()
        response = await client.post(f"/api/v1/spools/{fake_id}/duplicate")
        assert response.status_code == 404

    async def test_duplicate_spool_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_spool: Spool,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.post(f"/api/v1/spools/{test_spool.id}/duplicate")
        assert response.status_code == 401


class TestMaterialTypes:
    """Tests for material type endpoints."""

    async def test_list_material_types(
        self,
        client: AsyncClient,
    ):
        """Test listing material types."""
        response = await client.get("/api/v1/spools/material-types")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Check structure
        mat = data[0]
        assert "id" in mat
        assert "code" in mat
        assert "name" in mat

    async def test_list_material_types_includes_standard_types(
        self,
        client: AsyncClient,
    ):
        """Test that standard material types are included."""
        response = await client.get("/api/v1/spools/material-types")
        assert response.status_code == 200
        data = response.json()
        codes = [m["code"] for m in data]
        assert "PLA" in codes
        assert "PETG" in codes
        assert "ABS" in codes

    async def test_create_material_type(
        self,
        client: AsyncClient,
    ):
        """Test creating a new material type."""
        response = await client.post(
            "/api/v1/spools/material-types",
            json={
                "code": "CUSTOM",
                "name": "Custom Material",
                "description": "A custom test material",
                "typical_density": 1.25,
                "typical_cost_per_kg": 30.0,
                "min_temp": 200,
                "max_temp": 230,
                "bed_temp": 60,
                "is_active": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "CUSTOM"
        assert data["name"] == "Custom Material"

    async def test_create_material_type_duplicate_code(
        self,
        client: AsyncClient,
    ):
        """Test that duplicate material codes are rejected."""
        response = await client.post(
            "/api/v1/spools/material-types",
            json={
                "code": "PLA",  # Already exists from seed
                "name": "Duplicate PLA",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_create_material_type_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.post(
            "/api/v1/spools/material-types",
            json={
                "code": "TEST",
                "name": "Test",
            },
        )
        assert response.status_code == 401

    async def test_list_material_types_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/spools/material-types")
        assert response.status_code == 401


class TestSpoolProperties:
    """Tests for spool computed properties and edge cases."""

    async def test_spool_remaining_percentage_calculation(
        self,
        client: AsyncClient,
        test_spool: Spool,
    ):
        """Test that remaining percentage is calculated correctly."""
        response = await client.get(f"/api/v1/spools/{test_spool.id}")
        assert response.status_code == 200
        data = response.json()

        # test_spool has 800g current, 1000g initial = 80%
        expected_percentage = (800.0 / 1000.0) * 100
        assert data["remaining_percentage"] == expected_percentage

    async def test_spool_zero_initial_weight(
        self,
        client: AsyncClient,
        test_filament_type,
    ):
        """Test spool with edge case initial weight."""
        # Create spool with very small initial weight
        response = await client.post(
            "/api/v1/spools",
            json={
                "spool_id": "SMALL-SPOOL",
                "filament_type_id": str(test_filament_type.id),
                "initial_weight": 100.0,
                "current_weight": 50.0,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["remaining_percentage"] == 50.0

    async def test_spool_fully_used(
        self,
        client: AsyncClient,
        test_filament_type,
    ):
        """Test spool with zero current weight."""
        response = await client.post(
            "/api/v1/spools",
            json={
                "spool_id": "EMPTY-SPOOL",
                "filament_type_id": str(test_filament_type.id),
                "initial_weight": 1000.0,
                "current_weight": 0.0,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["remaining_percentage"] == 0.0


class TestFKConstraintErrors:
    """Regression tests for MYS-475: FK constraint violations return 400, not 500."""

    async def test_create_spool_invalid_filament_type_returns_400(
        self,
        client: AsyncClient,
    ):
        """Regression test: POSTing with a non-existent filament_type_id returns 400."""
        nonexistent_id = str(uuid4())
        response = await client.post(
            "/api/v1/spools",
            json={
                "spool_id": "FK-TEST-001",
                "filament_type_id": nonexistent_id,
                "initial_weight": 1000.0,
                "current_weight": 1000.0,
            },
        )
        assert response.status_code == 400

    async def test_update_spool_invalid_filament_type_returns_400(
        self,
        client: AsyncClient,
        test_spool: Spool,
    ):
        """Regression test: PUTting a non-existent filament_type_id returns 400."""
        nonexistent_id = str(uuid4())
        response = await client.put(
            f"/api/v1/spools/{test_spool.id}",
            json={
                "filament_type_id": nonexistent_id,
            },
        )
        assert response.status_code == 400
