"""Tests for platform admin API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_admin import PlatformAdminAuditLog
from app.models.tenant import Tenant
from app.models.user import User, UserTenant, UserRole


class TestPlatformAdminEndpoints:
    """Tests for platform admin API endpoints."""

    @pytest_asyncio.fixture
    async def platform_admin_user(self, db_session: AsyncSession, test_tenant: Tenant) -> User:
        """Create a platform admin user."""
        from app.auth.password import get_password_hash

        user = User(
            id=uuid4(),
            email="admin@platform.com",
            full_name="Platform Admin",
            hashed_password=get_password_hash("adminpassword123"),
            is_active=True,
            is_platform_admin=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Create user-tenant relationship
        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=test_tenant.id,
            role=UserRole.ADMIN,
        )
        db_session.add(user_tenant)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def regular_user(self, db_session: AsyncSession, test_tenant: Tenant) -> User:
        """Create a regular (non-admin) user."""
        from app.auth.password import get_password_hash

        user = User(
            id=uuid4(),
            email="regular@example.com",
            full_name="Regular User",
            hashed_password=get_password_hash("regularpassword123"),
            is_active=True,
            is_platform_admin=False,
        )
        db_session.add(user)
        await db_session.flush()

        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=test_tenant.id,
            role=UserRole.MEMBER,
        )
        db_session.add(user_tenant)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def platform_admin_client(
        self,
        db_session: AsyncSession,
        seed_material_types,
        platform_admin_user: User,
        test_tenant: Tenant,
    ):
        """Create a test HTTP client authenticated as platform admin."""
        from app.auth.dependencies import (
            get_current_user,
            get_current_tenant,
            get_platform_admin,
            get_platform_admin_db,
        )
        from app.database import get_db
        from app.main import app

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return platform_admin_user

        async def override_get_platform_admin():
            return platform_admin_user

        async def override_get_current_tenant():
            return test_tenant

        async def override_get_platform_admin_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_platform_admin] = override_get_platform_admin
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant
        app.dependency_overrides[get_platform_admin_db] = override_get_platform_admin_db

        app.state.limiter.enabled = False

        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

        app.state.limiter.enabled = True
        app.dependency_overrides.clear()

    @pytest_asyncio.fixture
    async def regular_user_client(
        self,
        db_session: AsyncSession,
        seed_material_types,
        regular_user: User,
        test_tenant: Tenant,
    ):
        """Create a test HTTP client authenticated as regular user (non-admin)."""
        from app.auth.dependencies import get_current_user, get_current_tenant
        from app.database import get_db
        from app.main import app

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return regular_user

        async def override_get_current_tenant():
            return test_tenant

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant

        app.state.limiter.enabled = False

        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

        app.state.limiter.enabled = True
        app.dependency_overrides.clear()

    @pytest_asyncio.fixture
    async def additional_tenants(self, db_session: AsyncSession) -> list[Tenant]:
        """Create additional tenants for testing."""
        tenants = []
        for i in range(3):
            tenant = Tenant(
                id=uuid4(),
                name=f"Test Tenant {i + 1}",
                slug=f"test-tenant-{i + 1}",
                is_active=i != 2,  # Third tenant is inactive
                settings={"test_setting": f"value_{i}"},
            )
            db_session.add(tenant)
            tenants.append(tenant)
        await db_session.commit()
        for t in tenants:
            await db_session.refresh(t)
        return tenants

    # =========================================================================
    # List Tenants Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_tenants_as_admin(
        self,
        platform_admin_client: AsyncClient,
        test_tenant: Tenant,
    ):
        """Test listing tenants as platform admin."""
        response = await platform_admin_client.get("/api/v1/platform/tenants")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_tenants_forbidden_for_non_admin(
        self,
        regular_user_client: AsyncClient,
    ):
        """Test that regular users cannot list tenants."""
        response = await regular_user_client.get("/api/v1/platform/tenants")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_tenants_pagination(
        self,
        platform_admin_client: AsyncClient,
        additional_tenants: list[Tenant],
    ):
        """Test tenant list pagination."""
        response = await platform_admin_client.get(
            "/api/v1/platform/tenants",
            params={"skip": 0, "limit": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["skip"] == 0
        assert data["limit"] == 2

    @pytest.mark.asyncio
    async def test_list_tenants_search(
        self,
        platform_admin_client: AsyncClient,
        additional_tenants: list[Tenant],
    ):
        """Test tenant list search."""
        response = await platform_admin_client.get(
            "/api/v1/platform/tenants",
            params={"search": "Tenant 1"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should find tenants with "Tenant 1" in name
        for item in data["items"]:
            assert "1" in item["name"] or "1" in item["slug"]

    @pytest.mark.asyncio
    async def test_list_tenants_filter_active(
        self,
        platform_admin_client: AsyncClient,
        additional_tenants: list[Tenant],
    ):
        """Test filtering tenants by active status."""
        # Filter for active tenants
        response = await platform_admin_client.get(
            "/api/v1/platform/tenants",
            params={"is_active": True},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["is_active"] is True

        # Filter for inactive tenants
        response = await platform_admin_client.get(
            "/api/v1/platform/tenants",
            params={"is_active": False},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["is_active"] is False

    # =========================================================================
    # Get Tenant Detail Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_tenant_detail(
        self,
        platform_admin_client: AsyncClient,
        test_tenant: Tenant,
    ):
        """Test getting tenant detail with statistics."""
        response = await platform_admin_client.get(f"/api/v1/platform/tenants/{test_tenant.id}")

        # Debug output
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.text}")

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["id"] == str(test_tenant.id)
        assert data["name"] == test_tenant.name
        assert data["slug"] == test_tenant.slug
        assert "user_count" in data
        assert "product_count" in data
        assert "order_count" in data
        assert "total_revenue" in data

    @pytest.mark.asyncio
    async def test_get_tenant_detail_not_found(
        self,
        platform_admin_client: AsyncClient,
    ):
        """Test getting non-existent tenant returns 404."""
        fake_id = uuid4()
        response = await platform_admin_client.get(f"/api/v1/platform/tenants/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_tenant_detail_forbidden_for_non_admin(
        self,
        regular_user_client: AsyncClient,
        test_tenant: Tenant,
    ):
        """Test that regular users cannot get tenant details."""
        response = await regular_user_client.get(f"/api/v1/platform/tenants/{test_tenant.id}")
        assert response.status_code == 403

    # =========================================================================
    # Impersonation Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_impersonate_tenant(
        self,
        platform_admin_client: AsyncClient,
        test_tenant: Tenant,
    ):
        """Test impersonating a tenant."""
        response = await platform_admin_client.post(
            f"/api/v1/platform/tenants/{test_tenant.id}/impersonate"
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["tenant_id"] == str(test_tenant.id)
        assert data["tenant_name"] == test_tenant.name

    @pytest.mark.asyncio
    async def test_impersonate_inactive_tenant_fails(
        self,
        platform_admin_client: AsyncClient,
        additional_tenants: list[Tenant],
    ):
        """Test that impersonating inactive tenant fails."""
        inactive_tenant = additional_tenants[2]  # Third tenant is inactive
        response = await platform_admin_client.post(
            f"/api/v1/platform/tenants/{inactive_tenant.id}/impersonate"
        )

        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_impersonate_nonexistent_tenant_fails(
        self,
        platform_admin_client: AsyncClient,
    ):
        """Test that impersonating non-existent tenant fails."""
        fake_id = uuid4()
        response = await platform_admin_client.post(
            f"/api/v1/platform/tenants/{fake_id}/impersonate"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_impersonate_forbidden_for_non_admin(
        self,
        regular_user_client: AsyncClient,
        test_tenant: Tenant,
    ):
        """Test that regular users cannot impersonate."""
        response = await regular_user_client.post(
            f"/api/v1/platform/tenants/{test_tenant.id}/impersonate"
        )
        assert response.status_code == 403

    # =========================================================================
    # Deactivate/Reactivate Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_deactivate_tenant(
        self,
        platform_admin_client: AsyncClient,
        additional_tenants: list[Tenant],
    ):
        """Test deactivating a tenant."""
        active_tenant = additional_tenants[0]
        response = await platform_admin_client.post(
            f"/api/v1/platform/tenants/{active_tenant.id}/deactivate"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(active_tenant.id)
        assert data["is_active"] is False
        assert "deactivated" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_deactivate_nonexistent_tenant_fails(
        self,
        platform_admin_client: AsyncClient,
    ):
        """Test that deactivating non-existent tenant fails."""
        fake_id = uuid4()
        response = await platform_admin_client.post(
            f"/api/v1/platform/tenants/{fake_id}/deactivate"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_reactivate_tenant(
        self,
        platform_admin_client: AsyncClient,
        additional_tenants: list[Tenant],
    ):
        """Test reactivating a tenant."""
        inactive_tenant = additional_tenants[2]  # Third tenant is inactive
        response = await platform_admin_client.post(
            f"/api/v1/platform/tenants/{inactive_tenant.id}/reactivate"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(inactive_tenant.id)
        assert data["is_active"] is True
        assert "reactivated" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_deactivate_forbidden_for_non_admin(
        self,
        regular_user_client: AsyncClient,
        test_tenant: Tenant,
    ):
        """Test that regular users cannot deactivate tenants."""
        response = await regular_user_client.post(
            f"/api/v1/platform/tenants/{test_tenant.id}/deactivate"
        )
        assert response.status_code == 403

    # =========================================================================
    # Audit Log Tests
    # =========================================================================

    @pytest_asyncio.fixture
    async def platform_audit_logs(
        self,
        db_session: AsyncSession,
        platform_admin_user: User,
        test_tenant: Tenant,
    ) -> list[PlatformAdminAuditLog]:
        """Create sample platform admin audit log entries."""
        logs = []
        actions = ["impersonate", "deactivate_tenant", "reactivate_tenant", "update_setting"]

        for i, action in enumerate(actions):
            log = PlatformAdminAuditLog(
                id=uuid4(),
                admin_user_id=platform_admin_user.id,
                action=action,
                target_type="tenant",
                target_id=test_tenant.id,
                action_metadata={"test": f"value_{i}"},
                ip_address="192.168.1.100",
            )
            db_session.add(log)
            logs.append(log)

        await db_session.commit()
        return logs

    @pytest.mark.asyncio
    async def test_list_audit_logs(
        self,
        platform_admin_client: AsyncClient,
        platform_audit_logs: list[PlatformAdminAuditLog],
    ):
        """Test listing platform admin audit logs."""
        response = await platform_admin_client.get("/api/v1/platform/audit")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= len(platform_audit_logs)

    @pytest.mark.asyncio
    async def test_list_audit_logs_filter_by_action(
        self,
        platform_admin_client: AsyncClient,
        platform_audit_logs: list[PlatformAdminAuditLog],
    ):
        """Test filtering audit logs by action type."""
        response = await platform_admin_client.get(
            "/api/v1/platform/audit",
            params={"action": "impersonate"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["action"] == "impersonate"

    @pytest.mark.asyncio
    async def test_list_audit_logs_pagination(
        self,
        platform_admin_client: AsyncClient,
        platform_audit_logs: list[PlatformAdminAuditLog],
    ):
        """Test audit log pagination."""
        response = await platform_admin_client.get(
            "/api/v1/platform/audit",
            params={"skip": 0, "limit": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["skip"] == 0
        assert data["limit"] == 2

    @pytest.mark.asyncio
    async def test_list_audit_logs_forbidden_for_non_admin(
        self,
        regular_user_client: AsyncClient,
    ):
        """Test that regular users cannot list audit logs."""
        response = await regular_user_client.get("/api/v1/platform/audit")
        assert response.status_code == 403


class TestImpersonationToken:
    """Tests for impersonation token validation."""

    @pytest_asyncio.fixture
    async def platform_admin_user(self, db_session: AsyncSession, test_tenant: Tenant) -> User:
        """Create a platform admin user."""
        from app.auth.password import get_password_hash

        user = User(
            id=uuid4(),
            email="admin@platform.com",
            full_name="Platform Admin",
            hashed_password=get_password_hash("adminpassword123"),
            is_active=True,
            is_platform_admin=True,
        )
        db_session.add(user)
        await db_session.flush()

        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=test_tenant.id,
            role=UserRole.ADMIN,
        )
        db_session.add(user_tenant)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def platform_admin_client(
        self,
        db_session: AsyncSession,
        seed_material_types,
        platform_admin_user: User,
        test_tenant: Tenant,
    ):
        """Create a test HTTP client authenticated as platform admin."""
        from app.auth.dependencies import (
            get_current_user,
            get_current_tenant,
            get_platform_admin,
            get_platform_admin_db,
        )
        from app.database import get_db
        from app.main import app

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return platform_admin_user

        async def override_get_platform_admin():
            return platform_admin_user

        async def override_get_current_tenant():
            return test_tenant

        async def override_get_platform_admin_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_platform_admin] = override_get_platform_admin
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant
        app.dependency_overrides[get_platform_admin_db] = override_get_platform_admin_db

        app.state.limiter.enabled = False

        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

        app.state.limiter.enabled = True
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_impersonation_token_contains_correct_claims(
        self,
        platform_admin_client: AsyncClient,
        platform_admin_user: User,
        test_tenant: Tenant,
    ):
        """Test that impersonation token contains required claims."""
        from app.core.security import decode_token

        response = await platform_admin_client.post(
            f"/api/v1/platform/tenants/{test_tenant.id}/impersonate"
        )

        assert response.status_code == 200
        token = response.json()["access_token"]

        # Decode and verify claims
        token_data = decode_token(token)
        assert token_data is not None
        assert str(token_data.user_id) == str(platform_admin_user.id)
        assert str(token_data.tenant_id) == str(test_tenant.id)
        assert token_data.is_platform_admin is True
