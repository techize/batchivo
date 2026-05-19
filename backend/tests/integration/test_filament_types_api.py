"""Integration tests for FilamentType API endpoints."""

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
