"""Integration tests for FilamentType API endpoints."""

import re

import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.models.filament_type import FilamentType
from app.models.material import MaterialType


# Minimum valid payload for FilamentType creation
def _valid_payload(test_material_type: MaterialType) -> dict:
    return {
        "material_type_id": str(test_material_type.id),
        "brand": "Bambu Lab",
        "color": "Jade White",
        "diameter": 1.75,
    }


class TestFilamentTypesEndpoints:
    """Integration tests for /api/v1/filament-types endpoints."""

    # ============================================
    # POST /api/v1/filament-types
    # ============================================

    @pytest.mark.asyncio
    async def test_create_filament_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_material_type: MaterialType,
    ):
        """Test filament type creation returns 201 with expected fields."""
        response = await client.post(
            "/api/v1/filament-types",
            headers=auth_headers,
            json=_valid_payload(test_material_type),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["brand"] == "Bambu Lab"
        assert data["color"] == "Jade White"
        assert data["has_sample"] is False
        assert "material_type_code" in data
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_requires_auth(
        self,
        unauthenticated_client: AsyncClient,
        test_material_type: MaterialType,
    ):
        """Test filament type creation without auth returns 401."""
        response = await unauthenticated_client.post(
            "/api/v1/filament-types",
            json=_valid_payload(test_material_type),
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_validation_error(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_material_type: MaterialType,
    ):
        """Test filament type creation with empty brand returns 422."""
        payload = _valid_payload(test_material_type)
        payload["brand"] = ""  # violates min_length=1
        response = await client.post(
            "/api/v1/filament-types",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 422

    # ============================================
    # GET /api/v1/filament-types
    # ============================================

    @pytest.mark.asyncio
    async def test_list_filament_types(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_filament_type: FilamentType,
    ):
        """Test listing filament types returns 200 with paginated response."""
        response = await client.get("/api/v1/filament-types", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "filament_types" in data
        assert isinstance(data["filament_types"], list)
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, unauthenticated_client: AsyncClient):
        """Test listing filament types without auth returns 401."""
        response = await unauthenticated_client.get("/api/v1/filament-types")
        assert response.status_code in [401, 403]

    # ============================================
    # GET /api/v1/filament-types/{id}
    # ============================================

    @pytest.mark.asyncio
    async def test_get_filament_type_by_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_filament_type: FilamentType,
    ):
        """Test retrieving a specific filament type by ID returns 200."""
        response = await client.get(
            f"/api/v1/filament-types/{test_filament_type.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_filament_type.id)

    @pytest.mark.asyncio
    async def test_get_filament_type_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test retrieving a non-existent filament type returns 404."""
        fake_id = uuid4()
        response = await client.get(
            f"/api/v1/filament-types/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    # ============================================
    # PUT /api/v1/filament-types/{id}
    # ============================================

    @pytest.mark.asyncio
    async def test_update_filament_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_filament_type: FilamentType,
    ):
        """Test updating a filament type returns 200 with updated field."""
        response = await client.put(
            f"/api/v1/filament-types/{test_filament_type.id}",
            headers=auth_headers,
            json={"has_sample": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_sample"] is True

    # ============================================
    # DELETE /api/v1/filament-types/{id}
    # ============================================

    @pytest.mark.asyncio
    async def test_delete_filament_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_material_type: MaterialType,
    ):
        """Test deleting a filament type returns 204."""
        # Create a separate filament type to delete (avoid invalidating other fixtures)
        create_resp = await client.post(
            "/api/v1/filament-types",
            headers=auth_headers,
            json=_valid_payload(test_material_type),
        )
        assert create_resp.status_code == 201
        ft_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/filament-types/{ft_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test deleting a non-existent filament type returns 404."""
        fake_id = uuid4()
        response = await client.delete(
            f"/api/v1/filament-types/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    # ============================================
    # Multi-tenant RLS isolation
    # ============================================

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_filament_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_material_type: MaterialType,
    ):
        """Test filament types from another tenant are not visible (RLS isolation)."""
        from app.models.tenant import Tenant

        # Create a different tenant
        other_tenant = Tenant(
            id=uuid4(),
            name="Other Tenant FT",
            slug=f"other-tenant-ft-{uuid4().hex[:8]}",
            settings={},
        )
        db_session.add(other_tenant)
        await db_session.flush()

        # Directly insert a FilamentType for the other tenant into the DB
        other_ft = FilamentType(
            id=uuid4(),
            tenant_id=other_tenant.id,
            material_type_id=test_material_type.id,
            brand="Other Brand",
            color="Other Color",
            diameter=1.75,
            has_sample=False,
            translucent=False,
            glow=False,
        )
        db_session.add(other_ft)
        await db_session.commit()

        # Try to access other tenant's filament type using current tenant's auth
        response = await client.get(
            f"/api/v1/filament-types/{other_ft.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


# ============================================
# Aggregated endpoints — Wave 0 stubs (Plan 07 fills in real bodies)
# ============================================


class TestFilamentTypeAggregatedEndpoints:
    """Integration tests for aggregated FilamentType list and spool sub-resource endpoints.

    NOTE: Stubs created in Wave 0 (Plan 00). Real test bodies filled in by Plan 07.
    Phase 1 prerequisite: verify Spool.filament_type_id FK is non-null for migrated spools
    before running these tests against a production-migrated database.
    """

    # ============================================
    # GET /api/v1/filament-types/aggregated
    # ============================================

    @pytest.mark.asyncio
    async def test_aggregated_list_returns_200_with_counts(
        self, client: AsyncClient, auth_headers: dict, test_filament_type, test_spool
    ):
        """Aggregated list returns 200 with spool_count and labeled_count per row."""
        response = await client.get("/api/v1/filament-types/aggregated", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "filament_types" in data
        assert data["total"] >= 1
        rows = data["filament_types"]
        row = next((r for r in rows if r["id"] == str(test_filament_type.id)), None)
        assert row is not None
        assert "spool_count" in row
        assert row["spool_count"] >= 1
        assert "labeled_count" in row
        assert "material_type_name" in row
        assert "material_type_code" in row
        assert "has_sample" in row

    @pytest.mark.asyncio
    async def test_aggregated_list_labeled_count_accuracy(
        self, client: AsyncClient, auth_headers: dict, test_filament_type, test_spool
    ):
        """labeled_count == 0 when test_spool.is_labeled is False."""
        # test_spool.is_labeled is False per conftest fixture
        response = await client.get("/api/v1/filament-types/aggregated", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        row = next((r for r in data["filament_types"] if r["id"] == str(test_filament_type.id)), None)
        assert row is not None
        assert row["labeled_count"] == 0  # test_spool is unlabeled
        assert row["spool_count"] == 1    # only one spool linked to this type

    @pytest.mark.asyncio
    async def test_aggregated_filter_needs_labels(
        self, client: AsyncClient, auth_headers: dict, test_filament_type, test_spool
    ):
        """needs_labels=true filter returns only types with unlabeled spools."""
        response = await client.get(
            "/api/v1/filament-types/aggregated?needs_labels=true", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        ids = [r["id"] for r in data["filament_types"]]
        assert str(test_filament_type.id) in ids  # test spool is unlabeled so type shows up

    @pytest.mark.asyncio
    async def test_aggregated_filter_needs_sample(
        self, client: AsyncClient, auth_headers: dict, test_filament_type, test_spool
    ):
        """needs_sample=true filter returns only types without a sample."""
        # test_filament_type.has_sample is False per conftest fixture
        response = await client.get(
            "/api/v1/filament-types/aggregated?needs_sample=true", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # All returned rows should have has_sample == False
        for row in data["filament_types"]:
            assert row["has_sample"] is False
        ids = [r["id"] for r in data["filament_types"]]
        assert str(test_filament_type.id) in ids  # has_sample=False means it needs a sample

    @pytest.mark.asyncio
    async def test_aggregated_requires_auth(self, unauthenticated_client: AsyncClient):
        """Aggregated list without auth returns 401 or 403."""
        response = await unauthenticated_client.get("/api/v1/filament-types/aggregated")
        assert response.status_code in [401, 403]

    # ============================================
    # GET /api/v1/filament-types/{id}/spools
    # ============================================

    @pytest.mark.asyncio
    async def test_spools_sub_resource_returns_child_spools(
        self, client: AsyncClient, auth_headers: dict, test_filament_type, test_spool
    ):
        """Spools sub-resource returns list of spools with correct fields."""
        response = await client.get(
            f"/api/v1/filament-types/{test_filament_type.id}/spools", headers=auth_headers
        )
        assert response.status_code == 200
        spools = response.json()
        assert isinstance(spools, list)
        assert len(spools) >= 1
        spool = spools[0]
        assert "id" in spool
        assert "spool_id" in spool
        assert "current_weight" in spool
        assert "initial_weight" in spool
        assert "is_labeled" in spool
        assert "is_active" in spool
        assert spool["spool_id"] == "TEST-SPOOL-001"
        assert spool["is_labeled"] is False

    @pytest.mark.asyncio
    async def test_spools_sub_resource_requires_auth(
        self, unauthenticated_client: AsyncClient, test_filament_type
    ):
        """Spools sub-resource without auth returns 401 or 403."""
        response = await unauthenticated_client.get(
            f"/api/v1/filament-types/{test_filament_type.id}/spools"
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_spools_sub_resource_404_for_nonexistent(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Spools sub-resource returns 404 for a random UUID not in this tenant."""
        response = await client.get(
            "/api/v1/filament-types/00000000-0000-0000-0000-000000000000/spools",
            headers=auth_headers,
        )
        assert response.status_code == 404


# ============================================
# Bulk / Batch add workflow helpers
# ============================================


def _bulk_payload(test_material_type, quantity=3):
    return {
        "material_type_id": str(test_material_type.id),
        "brand": "Test Brand",
        "color": "Ocean Blue",
        "quantity": quantity,
        "initial_weight": 1000.0,
    }


def _batch_payload(test_material_type, entries=None):
    return {
        "entries": entries
        or [
            {
                "material_type_id": str(test_material_type.id),
                "brand": "Test Brand",
                "color": "Forest Green",
            }
        ],
        "initial_weight": 1000.0,
    }


# ============================================
# POST /api/v1/filament-types/bulk-create
# ============================================


class TestBulkCreate:
    """Integration tests for POST /api/v1/filament-types/bulk-create."""

    @pytest.mark.asyncio
    async def test_bulk_create_returns_201_with_spool_ids(
        self, client: AsyncClient, auth_headers: dict, test_material_type
    ):
        response = await client.post(
            "/api/v1/filament-types/bulk-create",
            json=_bulk_payload(test_material_type, quantity=3),
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "filament_type_id" in data
        assert "spool_ids" in data
        assert len(data["spool_ids"]) == 3

    @pytest.mark.asyncio
    async def test_bulk_create_quantity_1_creates_one_spool(
        self, client: AsyncClient, auth_headers: dict, test_material_type
    ):
        response = await client.post(
            "/api/v1/filament-types/bulk-create",
            json=_bulk_payload(test_material_type, quantity=1),
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["spool_ids"]) == 1

    @pytest.mark.asyncio
    async def test_bulk_create_spool_id_format(
        self, client: AsyncClient, auth_headers: dict, test_material_type
    ):
        response = await client.post(
            "/api/v1/filament-types/bulk-create",
            json=_bulk_payload(test_material_type, quantity=2),
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        for spool_id in data["spool_ids"]:
            assert re.match(r"^FIL-\d{3,}$", spool_id), (
                f"Spool ID {spool_id!r} does not match FIL-NNN format"
            )

    @pytest.mark.asyncio
    async def test_bulk_create_spools_are_unlabeled(
        self, client: AsyncClient, auth_headers: dict, test_material_type, db_session
    ):
        response = await client.post(
            "/api/v1/filament-types/bulk-create",
            json=_bulk_payload(test_material_type, quantity=2),
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        ft_id = data["filament_type_id"]
        spools_response = await client.get(
            f"/api/v1/filament-types/{ft_id}/spools", headers=auth_headers
        )
        assert spools_response.status_code == 200
        spools = spools_response.json()
        created_spool_ids = set(data["spool_ids"])
        created_spools = [s for s in spools if s["spool_id"] in created_spool_ids]
        assert len(created_spools) == 2
        assert all(s["is_labeled"] is False for s in created_spools)

    @pytest.mark.asyncio
    async def test_bulk_create_requires_auth(
        self, unauthenticated_client: AsyncClient, test_material_type
    ):
        response = await unauthenticated_client.post(
            "/api/v1/filament-types/bulk-create",
            json=_bulk_payload(test_material_type),
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_bulk_create_quantity_zero_rejected(
        self, client: AsyncClient, auth_headers: dict, test_material_type
    ):
        payload = _bulk_payload(test_material_type, quantity=3)
        payload["quantity"] = 0
        response = await client.post(
            "/api/v1/filament-types/bulk-create",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_bulk_create_quantity_over_limit_rejected(
        self, client: AsyncClient, auth_headers: dict, test_material_type
    ):
        payload = _bulk_payload(test_material_type, quantity=3)
        payload["quantity"] = 21
        response = await client.post(
            "/api/v1/filament-types/bulk-create",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_bulk_create_finds_existing_filament_type(
        self, client: AsyncClient, auth_headers: dict, test_material_type
    ):
        payload = {
            "material_type_id": str(test_material_type.id),
            "brand": "DuplicateBrand",
            "color": "SameColor",
            "quantity": 3,
            "initial_weight": 1000.0,
        }
        response1 = await client.post(
            "/api/v1/filament-types/bulk-create",
            json=payload,
            headers=auth_headers,
        )
        response2 = await client.post(
            "/api/v1/filament-types/bulk-create",
            json=payload,
            headers=auth_headers,
        )
        assert response1.status_code == 201
        assert response2.status_code == 201
        assert response1.json()["filament_type_id"] == response2.json()["filament_type_id"], (
            "Duplicate FilamentType should be reused"
        )


# ============================================
# POST /api/v1/filament-types/batch-create
# ============================================


class TestBatchCreate:
    """Integration tests for POST /api/v1/filament-types/batch-create."""

    @pytest.mark.asyncio
    async def test_batch_create_returns_201_with_results(
        self, client: AsyncClient, auth_headers: dict, test_material_type
    ):
        response = await client.post(
            "/api/v1/filament-types/batch-create",
            json=_batch_payload(test_material_type),
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert "filament_type_id" in data["results"][0]
        assert "spool_id" in data["results"][0]

    @pytest.mark.asyncio
    async def test_batch_create_multiple_entries(
        self, client: AsyncClient, auth_headers: dict, test_material_type
    ):
        payload = _batch_payload(
            test_material_type,
            entries=[
                {"material_type_id": str(test_material_type.id), "brand": "JAYO", "color": "Red"},
                {"material_type_id": str(test_material_type.id), "brand": "JAYO", "color": "Blue"},
                {"material_type_id": str(test_material_type.id), "brand": "JAYO", "color": "Green"},
            ],
        )
        response = await client.post(
            "/api/v1/filament-types/batch-create",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["results"]) == 3

    @pytest.mark.asyncio
    async def test_batch_create_spools_are_unlabeled(
        self, client: AsyncClient, auth_headers: dict, test_material_type
    ):
        payload = _batch_payload(
            test_material_type,
            entries=[
                {"material_type_id": str(test_material_type.id), "brand": "JAYO", "color": "Purple"},
                {"material_type_id": str(test_material_type.id), "brand": "JAYO", "color": "Yellow"},
            ],
        )
        response = await client.post(
            "/api/v1/filament-types/batch-create",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        # Verify spools are unlabeled via spool_id format assertions
        for result in data["results"]:
            assert re.match(r"^FIL-\d{3,}$", result["spool_id"])

    @pytest.mark.asyncio
    async def test_batch_create_reuses_existing_filament_type(
        self, client: AsyncClient, auth_headers: dict, test_material_type
    ):
        payload = _batch_payload(
            test_material_type,
            entries=[
                {
                    "material_type_id": str(test_material_type.id),
                    "brand": "SameBrand",
                    "color": "SameColor2",
                },
                {
                    "material_type_id": str(test_material_type.id),
                    "brand": "SameBrand",
                    "color": "SameColor2",
                },
            ],
        )
        response = await client.post(
            "/api/v1/filament-types/batch-create",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["results"][0]["filament_type_id"] == data["results"][1]["filament_type_id"]

    @pytest.mark.asyncio
    async def test_batch_create_requires_auth(
        self, unauthenticated_client: AsyncClient, test_material_type
    ):
        response = await unauthenticated_client.post(
            "/api/v1/filament-types/batch-create",
            json=_batch_payload(test_material_type),
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_batch_create_empty_entries_rejected(
        self, client: AsyncClient, auth_headers: dict, test_material_type
    ):
        payload = {"entries": [], "initial_weight": 1000.0}
        response = await client.post(
            "/api/v1/filament-types/batch-create",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 422
