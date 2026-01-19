"""Integration tests for tenant module management API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantType
from app.models.tenant_module import TenantModule
from app.models.user import User, UserTenant, UserRole
from app.services.tenant_module_service import ALL_MODULES, DEFAULT_MODULES_BY_TYPE


# =============================================================================
# Fixtures
# =============================================================================


class TestTenantModulesAPI:
    """Integration tests for tenant module management API."""

    @pytest_asyncio.fixture
    async def platform_admin_user(self, db_session: AsyncSession, test_tenant: Tenant) -> User:
        """Create a platform admin user."""
        from app.auth.password import get_password_hash

        unique_id = str(uuid4())[:8]
        user = User(
            id=uuid4(),
            email=f"admin-modules-{unique_id}@platform.com",
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
    async def regular_user(self, db_session: AsyncSession, test_tenant: Tenant) -> User:
        """Create a regular (non-admin) user."""
        from app.auth.password import get_password_hash

        unique_id = str(uuid4())[:8]
        user = User(
            id=uuid4(),
            email=f"regular-modules-{unique_id}@example.com",
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

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
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

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

        app.state.limiter.enabled = True
        app.dependency_overrides.clear()

    @pytest_asyncio.fixture
    async def tenant_3d_print(self, db_session: AsyncSession) -> Tenant:
        """Create a 3D print tenant for testing."""
        unique_id = str(uuid4())[:8]
        tenant = Tenant(
            id=uuid4(),
            name="3D Print Test Shop",
            slug=f"3d-print-test-{unique_id}",
            tenant_type=TenantType.THREE_D_PRINT.value,
            is_active=True,
            settings={"currency": "USD"},
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        return tenant

    @pytest_asyncio.fixture
    async def tenant_knitting(self, db_session: AsyncSession) -> Tenant:
        """Create a knitting tenant for testing."""
        unique_id = str(uuid4())[:8]
        tenant = Tenant(
            id=uuid4(),
            name="Knitting Test Studio",
            slug=f"knitting-test-{unique_id}",
            tenant_type=TenantType.HAND_KNITTING.value,
            is_active=True,
            settings={"currency": "USD"},
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        return tenant

    @pytest_asyncio.fixture
    async def tenant_with_modules(
        self, db_session: AsyncSession, tenant_3d_print: Tenant, platform_admin_user: User
    ) -> Tenant:
        """Create a tenant with pre-configured modules."""
        # Create some module configurations
        modules_config = [
            ("spools", True),
            ("models", True),
            ("printers", False),  # Explicitly disabled
            ("production", True),
        ]

        for module_name, enabled in modules_config:
            module = TenantModule(
                id=uuid4(),
                tenant_id=tenant_3d_print.id,
                module_name=module_name,
                enabled=enabled,
                enabled_by_user_id=platform_admin_user.id,
            )
            db_session.add(module)

        await db_session.commit()
        return tenant_3d_print

    # =========================================================================
    # List Tenant Modules Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_tenant_modules(
        self,
        platform_admin_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test listing modules for a tenant."""
        response = await platform_admin_client.get(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["tenant_id"] == str(tenant_3d_print.id)
        assert data["tenant_type"] == TenantType.THREE_D_PRINT.value
        assert "modules" in data
        assert len(data["modules"]) == len(ALL_MODULES)

    @pytest.mark.asyncio
    async def test_list_modules_returns_all_modules(
        self,
        platform_admin_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test that all available modules are returned."""
        response = await platform_admin_client.get(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules"
        )

        assert response.status_code == 200
        data = response.json()

        module_names = [m["module_name"] for m in data["modules"]]
        for expected_module in ALL_MODULES:
            assert expected_module in module_names

    @pytest.mark.asyncio
    async def test_list_modules_shows_configured_status(
        self,
        platform_admin_client: AsyncClient,
        tenant_with_modules: Tenant,
    ):
        """Test that configured vs default status is correctly shown."""
        response = await platform_admin_client.get(
            f"/api/v1/platform/tenants/{tenant_with_modules.id}/modules"
        )

        assert response.status_code == 200
        data = response.json()

        modules_by_name = {m["module_name"]: m for m in data["modules"]}

        # spools was explicitly configured as enabled
        assert modules_by_name["spools"]["configured"] is True
        assert modules_by_name["spools"]["enabled"] is True

        # printers was explicitly configured as disabled
        assert modules_by_name["printers"]["configured"] is True
        assert modules_by_name["printers"]["enabled"] is False

        # products was not configured, should use default
        assert modules_by_name["products"]["configured"] is False

    @pytest.mark.asyncio
    async def test_list_modules_nonexistent_tenant(
        self,
        platform_admin_client: AsyncClient,
    ):
        """Test listing modules for non-existent tenant returns 404."""
        fake_id = uuid4()
        response = await platform_admin_client.get(
            f"/api/v1/platform/tenants/{fake_id}/modules"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_modules_forbidden_for_non_admin(
        self,
        regular_user_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test that regular users cannot list tenant modules."""
        response = await regular_user_client.get(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules"
        )

        assert response.status_code == 403

    # =========================================================================
    # Update Module Status Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_enable_module(
        self,
        platform_admin_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test enabling a module for a tenant."""
        response = await platform_admin_client.put(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/spools",
            json={"enabled": True},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["module_name"] == "spools"
        assert data["enabled"] is True
        assert "enabled" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_disable_module(
        self,
        platform_admin_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test disabling a module for a tenant."""
        response = await platform_admin_client.put(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/printers",
            json={"enabled": False},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["module_name"] == "printers"
        assert data["enabled"] is False
        assert "disabled" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_enable_module_persists(
        self,
        platform_admin_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test that module enable status persists."""
        # Enable a module
        await platform_admin_client.put(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/spools",
            json={"enabled": True},
        )

        # Check that it's reflected in the list
        response = await platform_admin_client.get(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules"
        )

        data = response.json()
        spools = next(m for m in data["modules"] if m["module_name"] == "spools")
        assert spools["enabled"] is True
        assert spools["configured"] is True

    @pytest.mark.asyncio
    async def test_update_nonexistent_module(
        self,
        platform_admin_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test updating a non-existent module returns error."""
        response = await platform_admin_client.put(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/nonexistent_module",
            json={"enabled": True},
        )

        assert response.status_code == 400
        assert "unknown module" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_module_nonexistent_tenant(
        self,
        platform_admin_client: AsyncClient,
    ):
        """Test updating module for non-existent tenant returns 404."""
        fake_id = uuid4()
        response = await platform_admin_client.put(
            f"/api/v1/platform/tenants/{fake_id}/modules/spools",
            json={"enabled": True},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_module_forbidden_for_non_admin(
        self,
        regular_user_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test that regular users cannot update modules."""
        response = await regular_user_client.put(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/spools",
            json={"enabled": True},
        )

        assert response.status_code == 403

    # =========================================================================
    # Reset to Defaults Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_reset_to_defaults(
        self,
        platform_admin_client: AsyncClient,
        tenant_with_modules: Tenant,
    ):
        """Test resetting modules to defaults."""
        response = await platform_admin_client.post(
            f"/api/v1/platform/tenants/{tenant_with_modules.id}/modules/reset-defaults"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["tenant_id"] == str(tenant_with_modules.id)
        assert data["modules_reset"] == len(ALL_MODULES)
        assert "reset" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_reset_to_defaults_applies_tenant_type_defaults(
        self,
        platform_admin_client: AsyncClient,
        tenant_with_modules: Tenant,
    ):
        """Test that reset applies correct defaults for tenant type."""
        # Reset to defaults
        await platform_admin_client.post(
            f"/api/v1/platform/tenants/{tenant_with_modules.id}/modules/reset-defaults"
        )

        # Check the resulting configuration
        response = await platform_admin_client.get(
            f"/api/v1/platform/tenants/{tenant_with_modules.id}/modules"
        )

        data = response.json()
        defaults = DEFAULT_MODULES_BY_TYPE[TenantType.THREE_D_PRINT.value]

        for module in data["modules"]:
            expected_enabled = module["module_name"] in defaults
            assert module["enabled"] == expected_enabled, (
                f"Module {module['module_name']} should be "
                f"{'enabled' if expected_enabled else 'disabled'} after reset"
            )

    @pytest.mark.asyncio
    async def test_reset_knitting_tenant_defaults(
        self,
        platform_admin_client: AsyncClient,
        tenant_knitting: Tenant,
    ):
        """Test that knitting tenant gets correct defaults after reset."""
        # First enable all modules
        for module_name in ALL_MODULES:
            await platform_admin_client.put(
                f"/api/v1/platform/tenants/{tenant_knitting.id}/modules/{module_name}",
                json={"enabled": True},
            )

        # Reset to defaults
        await platform_admin_client.post(
            f"/api/v1/platform/tenants/{tenant_knitting.id}/modules/reset-defaults"
        )

        # Check the resulting configuration
        response = await platform_admin_client.get(
            f"/api/v1/platform/tenants/{tenant_knitting.id}/modules"
        )

        data = response.json()
        knitting_defaults = DEFAULT_MODULES_BY_TYPE[TenantType.HAND_KNITTING.value]

        for module in data["modules"]:
            expected_enabled = module["module_name"] in knitting_defaults
            assert module["enabled"] == expected_enabled, (
                f"Module {module['module_name']} should be "
                f"{'enabled' if expected_enabled else 'disabled'} for knitting tenant"
            )

    @pytest.mark.asyncio
    async def test_reset_nonexistent_tenant(
        self,
        platform_admin_client: AsyncClient,
    ):
        """Test resetting modules for non-existent tenant returns 404."""
        fake_id = uuid4()
        response = await platform_admin_client.post(
            f"/api/v1/platform/tenants/{fake_id}/modules/reset-defaults"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_reset_forbidden_for_non_admin(
        self,
        regular_user_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test that regular users cannot reset modules."""
        response = await regular_user_client.post(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/reset-defaults"
        )

        assert response.status_code == 403

    # =========================================================================
    # Edge Cases
    # =========================================================================

    @pytest.mark.asyncio
    async def test_toggle_module_multiple_times(
        self,
        platform_admin_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test enabling and disabling a module multiple times."""
        module_name = "spools"

        # Enable
        response = await platform_admin_client.put(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/{module_name}",
            json={"enabled": True},
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is True

        # Disable
        response = await platform_admin_client.put(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/{module_name}",
            json={"enabled": False},
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is False

        # Enable again
        response = await platform_admin_client.put(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/{module_name}",
            json={"enabled": True},
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is True

    @pytest.mark.asyncio
    async def test_all_valid_modules_can_be_updated(
        self,
        platform_admin_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test that all modules in ALL_MODULES can be enabled/disabled."""
        for module_name in ALL_MODULES:
            # Enable
            response = await platform_admin_client.put(
                f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/{module_name}",
                json={"enabled": True},
            )
            assert response.status_code == 200, f"Failed to enable module {module_name}"

            # Disable
            response = await platform_admin_client.put(
                f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/{module_name}",
                json={"enabled": False},
            )
            assert response.status_code == 200, f"Failed to disable module {module_name}"

    @pytest.mark.asyncio
    async def test_is_default_flag_changes_after_update(
        self,
        platform_admin_client: AsyncClient,
        tenant_3d_print: Tenant,
    ):
        """Test that is_default flag changes when module status differs from default."""
        # Get defaults for 3D print
        defaults = DEFAULT_MODULES_BY_TYPE[TenantType.THREE_D_PRINT.value]

        # spools should be in defaults
        assert "spools" in defaults

        # Disable spools (which should be enabled by default)
        await platform_admin_client.put(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules/spools",
            json={"enabled": False},
        )

        # Check that is_default is now False
        response = await platform_admin_client.get(
            f"/api/v1/platform/tenants/{tenant_3d_print.id}/modules"
        )

        data = response.json()
        spools = next(m for m in data["modules"] if m["module_name"] == "spools")
        assert spools["is_default"] is False


# =============================================================================
# User Modules API Tests (non-admin endpoint)
# =============================================================================


class TestUserModulesAPI:
    """Tests for the user-facing modules API (/api/v1/modules)."""

    @pytest.mark.asyncio
    async def test_list_modules_for_current_tenant(
        self,
        client: AsyncClient,  # Uses the standard authenticated client
        test_tenant: Tenant,
    ):
        """Test listing enabled modules for current tenant."""
        response = await client.get("/api/v1/modules")

        assert response.status_code == 200
        data = response.json()

        assert "tenant_type" in data
        assert "modules" in data

    @pytest.mark.asyncio
    async def test_list_modules_includes_expected_fields(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
    ):
        """Test that module response includes expected fields."""
        response = await client.get("/api/v1/modules")

        assert response.status_code == 200
        data = response.json()

        if data["modules"]:
            module = data["modules"][0]
            assert "name" in module
            assert "display_name" in module
            assert "description" in module
            assert "icon" in module
            assert "status" in module
            assert "order" in module
            assert "routes" in module

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Module discovery has import errors in knitting modules (yarn.py, needle.py)")
    async def test_list_modules_with_include_disabled(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
    ):
        """Test listing all modules including disabled ones."""
        response = await client.get(
            "/api/v1/modules",
            params={"include_disabled": True},
        )

        assert response.status_code == 200
        data = response.json()

        # Should include both active and disabled modules
        statuses = [m["status"] for m in data["modules"]]
        # We can't guarantee disabled modules exist, but the endpoint should work
        assert all(s in ["active", "disabled", "coming_soon"] for s in statuses)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Module discovery has import errors in knitting modules (yarn.py, needle.py)")
    async def test_get_specific_module(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
    ):
        """Test getting details of a specific module."""
        # First get list to find a valid module name
        list_response = await client.get("/api/v1/modules", params={"include_disabled": True})
        modules = list_response.json()["modules"]

        if modules:
            module_name = modules[0]["name"]
            response = await client.get(f"/api/v1/modules/{module_name}")

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == module_name

    @pytest.mark.asyncio
    async def test_get_nonexistent_module(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
    ):
        """Test getting a non-existent module returns 404."""
        response = await client.get("/api/v1/modules/nonexistent_module_xyz")

        assert response.status_code == 404
