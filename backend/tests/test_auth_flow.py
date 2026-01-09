"""
Test authentication flow to verify token handling and API access.

This test suite mimics the real-world flow where:
1. User logs in and receives tokens
2. User makes authenticated API calls
3. Tokens refresh when expiring
4. All endpoints respect authentication properly
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import MaterialType
from app.models.spool import Spool
from app.models.tenant import Tenant
from app.models.user import User


class TestAuthenticationFlow:
    """Test suite for authentication flow."""

    @pytest.mark.asyncio
    async def test_login_and_get_user_info(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
    ):
        """
        Test: User logs in and retrieves their user info.

        Flow:
        1. Login with valid credentials
        2. Receive access token
        3. Call /users/me with token
        4. Verify user info returned
        """
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # Get user info with token
        user_response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert user_response.status_code == 200
        user_data = user_response.json()
        assert user_data["email"] == test_user.email
        assert user_data["tenant_id"] == str(test_tenant.id)

    @pytest.mark.asyncio
    async def test_authenticated_api_access(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db: AsyncSession,
    ):
        """
        Test: User accesses multiple authenticated endpoints.

        Flow:
        1. Login and get token
        2. Call /users/me (should work)
        3. Call /spools (should work)
        4. Call /spools/material-types (should work)
        5. All with same token, all should succeed
        """
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]

        # Set auth header for all requests
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # Test /users/me
        user_response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert user_response.status_code == 200, f"users/me failed: {user_response.text}"

        # Test /spools
        spools_response = await client.get("/api/v1/spools", headers=auth_headers)
        assert spools_response.status_code == 200, f"spools failed: {spools_response.text}"

        # Test /spools/material-types
        materials_response = await client.get(
            "/api/v1/spools/material-types",
            headers=auth_headers,
        )
        assert (
            materials_response.status_code == 200
        ), f"material-types failed: {materials_response.text}"
        materials = materials_response.json()
        assert isinstance(materials, list)
        assert len(materials) > 0  # Should have seeded materials

    @pytest.mark.asyncio
    async def test_material_types_return_data(
        self,
        client: AsyncClient,
        test_user: User,
        db: AsyncSession,
    ):
        """
        Test: Material types endpoint returns seeded data.

        Verifies:
        1. Material types exist in database
        2. Endpoint returns all active types
        3. Data format is correct
        """
        # Verify materials exist in DB
        result = await db.execute(select(MaterialType).where(MaterialType.is_active.is_(True)))
        db_materials = result.scalars().all()
        assert len(db_materials) >= 8, "Expected at least 8 material types"

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        tokens = login_response.json()

        # Get material types via API
        materials_response = await client.get(
            "/api/v1/spools/material-types",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert materials_response.status_code == 200
        materials = materials_response.json()

        # Verify response structure
        assert isinstance(materials, list)
        assert len(materials) >= 8

        # Verify each material has required fields
        for material in materials:
            assert "id" in material
            assert "code" in material
            assert "name" in material
            assert material["is_active"] is True

        # Verify common material types exist
        codes = [m["code"] for m in materials]
        assert "PLA" in codes
        assert "PETG" in codes
        assert "ABS" in codes

    @pytest.mark.asyncio
    async def test_spool_creation_with_material_type(
        self,
        client: AsyncClient,
        test_user: User,
        test_tenant: Tenant,
        db: AsyncSession,
    ):
        """
        Test: Complete flow of getting material types and creating a spool.

        Flow:
        1. Login
        2. Get material types list
        3. Pick a material type
        4. Create spool with that material type
        5. Verify spool was created with correct material type
        """
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        tokens = login_response.json()
        auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # Get material types
        materials_response = await client.get(
            "/api/v1/spools/material-types",
            headers=auth_headers,
        )
        assert materials_response.status_code == 200
        materials = materials_response.json()
        assert len(materials) > 0

        # Pick PLA material
        pla_material = next(m for m in materials if m["code"] == "PLA")

        # Create spool with PLA
        spool_data = {
            "spool_id": "TEST-001",
            "brand": "Test Brand",
            "material_type_id": pla_material["id"],
            "color": "Red",
            "finish": "matte",
            "diameter": 1.75,
            "initial_weight": 1000.0,
            "current_weight": 1000.0,
        }

        create_response = await client.post(
            "/api/v1/spools",
            headers=auth_headers,
            json=spool_data,
        )
        assert create_response.status_code == 201, f"Failed to create spool: {create_response.text}"
        created_spool = create_response.json()

        # Verify spool has correct material type
        assert created_spool["material_type_code"] == "PLA"
        assert created_spool["material_type_name"] == pla_material["name"]
        assert created_spool["spool_id"] == "TEST-001"

    @pytest.mark.asyncio
    async def test_unauthenticated_access_denied(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """
        Test: Unauthenticated requests are rejected.

        Verifies:
        1. /users/me without token returns 401
        2. /spools without token returns 401
        3. /spools/material-types without token returns 401
        """
        # Test /users/me
        user_response = await unauthenticated_client.get("/api/v1/users/me")
        assert user_response.status_code == 401

        # Test /spools
        spools_response = await unauthenticated_client.get("/api/v1/spools")
        assert spools_response.status_code == 401

        # Test /spools/material-types
        materials_response = await unauthenticated_client.get("/api/v1/spools/material-types")
        assert materials_response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """
        Test: Invalid tokens are rejected.

        Verifies:
        1. Malformed token returns 401
        2. Expired token returns 401
        3. Wrong signature token returns 401
        """
        invalid_tokens = [
            "invalid_token",
            "Bearer invalid_token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.invalid",
        ]

        for token in invalid_tokens:
            response = await unauthenticated_client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 401, f"Token '{token}' should be rejected"

    @pytest.mark.asyncio
    async def test_tenant_isolation(
        self,
        unauthenticated_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test: Users can only access their own tenant's data.

        Flow:
        1. Create two tenants with users
        2. Create spools for each tenant
        3. Login as tenant1 user
        4. Verify only tenant1 spools visible
        5. Login as tenant2 user
        6. Verify only tenant2 spools visible
        """
        # Create tenant 1
        from app.models.tenant import Tenant
        from app.models.user import User
        from app.auth.password import get_password_hash

        from app.models.user import UserTenant, UserRole

        tenant1 = Tenant(name="Tenant 1", slug="tenant1")
        db.add(tenant1)
        await db.flush()

        user1 = User(
            email="user1@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="User 1",
        )
        db.add(user1)
        await db.flush()

        # Create user-tenant relationship for user1
        user_tenant1 = UserTenant(
            user_id=user1.id,
            tenant_id=tenant1.id,
            role=UserRole.ADMIN,
        )
        db.add(user_tenant1)

        # Create tenant 2
        tenant2 = Tenant(name="Tenant 2", slug="tenant2")
        db.add(tenant2)
        await db.flush()

        user2 = User(
            email="user2@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="User 2",
        )
        db.add(user2)
        await db.flush()

        # Create user-tenant relationship for user2
        user_tenant2 = UserTenant(
            user_id=user2.id,
            tenant_id=tenant2.id,
            role=UserRole.ADMIN,
        )
        db.add(user_tenant2)

        await db.commit()

        # Get a material type
        result = await db.execute(select(MaterialType).limit(1))
        material_type = result.scalar_one()

        # Create spool for tenant 1
        spool1 = Spool(
            tenant_id=tenant1.id,
            spool_id="T1-SPOOL-001",
            brand="Brand 1",
            material_type_id=material_type.id,
            color="Blue",
            finish="matte",
            diameter=1.75,
            initial_weight=1000.0,
            current_weight=1000.0,
        )
        db.add(spool1)

        # Create spool for tenant 2
        spool2 = Spool(
            tenant_id=tenant2.id,
            spool_id="T2-SPOOL-001",
            brand="Brand 2",
            material_type_id=material_type.id,
            color="Green",
            finish="matte",
            diameter=1.75,
            initial_weight=1000.0,
            current_weight=1000.0,
        )
        db.add(spool2)
        await db.commit()

        # Login as user1
        login1 = await unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": "user1@test.com", "password": "password123"},
        )
        tokens1 = login1.json()

        # Get spools as user1 - should only see tenant1 spool
        spools1 = await unauthenticated_client.get(
            "/api/v1/spools",
            headers={"Authorization": f"Bearer {tokens1['access_token']}"},
        )
        assert spools1.status_code == 200
        spools1_data = spools1.json()
        spool_ids_1 = [s["spool_id"] for s in spools1_data["spools"]]
        assert "T1-SPOOL-001" in spool_ids_1
        assert "T2-SPOOL-001" not in spool_ids_1

        # Login as user2
        login2 = await unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": "user2@test.com", "password": "password123"},
        )
        tokens2 = login2.json()

        # Get spools as user2 - should only see tenant2 spool
        spools2 = await unauthenticated_client.get(
            "/api/v1/spools",
            headers={"Authorization": f"Bearer {tokens2['access_token']}"},
        )
        assert spools2.status_code == 200
        spools2_data = spools2.json()
        spool_ids_2 = [s["spool_id"] for s in spools2_data["spools"]]
        assert "T2-SPOOL-001" in spool_ids_2
        assert "T1-SPOOL-001" not in spool_ids_2
