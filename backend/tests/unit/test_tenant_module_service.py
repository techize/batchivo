"""Unit tests for TenantModuleService."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.tenant import Tenant, TenantType
from app.models.tenant_module import TenantModule
from app.models.user import User
from app.services.tenant_module_service import (
    TenantModuleService,
    ALL_MODULES,
    DEFAULT_MODULES_BY_TYPE,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "admin@example.com"
    return user


@pytest.fixture
def mock_tenant_3d_print():
    """Create a mock 3D print tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = uuid4()
    tenant.name = "3D Print Shop"
    tenant.tenant_type = TenantType.THREE_D_PRINT.value
    return tenant


@pytest.fixture
def mock_tenant_knitting():
    """Create a mock hand knitting tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = uuid4()
    tenant.name = "Knitting Studio"
    tenant.tenant_type = TenantType.HAND_KNITTING.value
    return tenant


@pytest.fixture
def mock_tenant_generic():
    """Create a mock generic tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = uuid4()
    tenant.name = "Generic Maker"
    tenant.tenant_type = TenantType.GENERIC.value
    return tenant


def create_mock_tenant_module(
    tenant_id, module_name, enabled=True, enabled_by_user_id=None, updated_at=None
):
    """Helper to create mock TenantModule."""
    module = MagicMock(spec=TenantModule)
    module.id = uuid4()
    module.tenant_id = tenant_id
    module.module_name = module_name
    module.enabled = enabled
    module.enabled_by_user_id = enabled_by_user_id
    module.updated_at = updated_at
    return module


# =============================================================================
# Test: get_tenant_modules
# =============================================================================


class TestGetTenantModules:
    """Tests for get_tenant_modules method."""

    @pytest.mark.asyncio
    async def test_returns_all_modules_for_tenant(self, mock_db, mock_tenant_3d_print):
        """Test that get_tenant_modules returns all configured modules."""
        tenant_id = mock_tenant_3d_print.id

        # Create mock modules
        modules = [
            create_mock_tenant_module(tenant_id, "spools", True),
            create_mock_tenant_module(tenant_id, "models", True),
            create_mock_tenant_module(tenant_id, "printers", False),
        ]

        # Setup mock to return modules
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = modules
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db)
        result = await service.get_tenant_modules(tenant_id)

        assert len(result) == 3
        assert all(isinstance(m, MagicMock) for m in result)

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_unconfigured_tenant(self, mock_db):
        """Test that get_tenant_modules returns empty list when no config exists."""
        tenant_id = uuid4()

        # Setup mock to return empty list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db)
        result = await service.get_tenant_modules(tenant_id)

        assert result == []


# =============================================================================
# Test: get_enabled_modules
# =============================================================================


class TestGetEnabledModules:
    """Tests for get_enabled_modules method."""

    @pytest.mark.asyncio
    async def test_returns_only_enabled_modules(self, mock_db, mock_tenant_3d_print):
        """Test that only enabled modules are returned."""
        tenant_id = mock_tenant_3d_print.id

        modules = [
            create_mock_tenant_module(tenant_id, "spools", True),
            create_mock_tenant_module(tenant_id, "models", True),
            create_mock_tenant_module(tenant_id, "printers", False),
            create_mock_tenant_module(tenant_id, "production", True),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = modules
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db)
        result = await service.get_enabled_modules(tenant_id)

        assert "spools" in result
        assert "models" in result
        assert "production" in result
        assert "printers" not in result  # Disabled

    @pytest.mark.asyncio
    async def test_returns_defaults_when_no_config_exists(
        self, mock_db, mock_tenant_3d_print
    ):
        """Test that defaults are returned when tenant has no module config."""
        tenant_id = mock_tenant_3d_print.id

        # First call returns empty modules list
        mock_result1 = MagicMock()
        mock_result1.scalars.return_value.all.return_value = []

        # Second call returns the tenant
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_tenant_3d_print

        mock_db.execute.side_effect = [mock_result1, mock_result2]

        service = TenantModuleService(db=mock_db)
        result = await service.get_enabled_modules(tenant_id)

        # Should return 3D print defaults
        expected = DEFAULT_MODULES_BY_TYPE[TenantType.THREE_D_PRINT.value]
        assert result == expected

    @pytest.mark.asyncio
    async def test_returns_generic_defaults_when_tenant_not_found(self, mock_db):
        """Test that generic defaults are returned when tenant not found."""
        tenant_id = uuid4()

        # First call returns empty modules list
        mock_result1 = MagicMock()
        mock_result1.scalars.return_value.all.return_value = []

        # Second call returns None (tenant not found)
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [mock_result1, mock_result2]

        service = TenantModuleService(db=mock_db)
        result = await service.get_enabled_modules(tenant_id)

        # Should return generic defaults
        expected = DEFAULT_MODULES_BY_TYPE[TenantType.GENERIC.value]
        assert result == expected


# =============================================================================
# Test: is_module_enabled
# =============================================================================


class TestIsModuleEnabled:
    """Tests for is_module_enabled method."""

    @pytest.mark.asyncio
    async def test_returns_true_for_enabled_module(self, mock_db, mock_tenant_3d_print):
        """Test that True is returned for enabled modules."""
        tenant_id = mock_tenant_3d_print.id

        modules = [
            create_mock_tenant_module(tenant_id, "spools", True),
            create_mock_tenant_module(tenant_id, "models", False),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = modules
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db)

        assert await service.is_module_enabled(tenant_id, "spools") is True

    @pytest.mark.asyncio
    async def test_returns_false_for_disabled_module(self, mock_db, mock_tenant_3d_print):
        """Test that False is returned for disabled modules."""
        tenant_id = mock_tenant_3d_print.id

        modules = [
            create_mock_tenant_module(tenant_id, "spools", True),
            create_mock_tenant_module(tenant_id, "models", False),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = modules
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db)

        assert await service.is_module_enabled(tenant_id, "models") is False


# =============================================================================
# Test: set_module_enabled
# =============================================================================


class TestSetModuleEnabled:
    """Tests for set_module_enabled method."""

    @pytest.mark.asyncio
    async def test_creates_new_config_when_none_exists(self, mock_db, mock_user):
        """Test that a new TenantModule is created when none exists."""
        tenant_id = uuid4()

        # No existing module config
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db, user=mock_user)
        result = await service.set_module_enabled(tenant_id, "spools", True)

        # Verify db.add was called (new module created)
        mock_db.add.assert_called_once()

        # Verify the added object has correct attributes
        added_module = mock_db.add.call_args[0][0]
        assert added_module.tenant_id == tenant_id
        assert added_module.module_name == "spools"
        assert added_module.enabled is True
        assert added_module.enabled_by_user_id == mock_user.id

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_existing_config(self, mock_db, mock_user):
        """Test that existing TenantModule is updated."""
        tenant_id = uuid4()

        # Existing module config
        existing_module = create_mock_tenant_module(tenant_id, "spools", True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_module
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db, user=mock_user)
        result = await service.set_module_enabled(tenant_id, "spools", False)

        # Verify existing module was updated
        assert existing_module.enabled is False
        assert existing_module.enabled_by_user_id == mock_user.id
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_for_unknown_module(self, mock_db, mock_user):
        """Test that ValueError is raised for unknown module names."""
        tenant_id = uuid4()

        service = TenantModuleService(db=mock_db, user=mock_user)

        with pytest.raises(ValueError, match="Unknown module"):
            await service.set_module_enabled(tenant_id, "nonexistent_module", True)

    @pytest.mark.asyncio
    async def test_all_valid_modules_accepted(self, mock_db, mock_user):
        """Test that all modules in ALL_MODULES are valid."""
        tenant_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db, user=mock_user)

        # All modules should be accepted without raising ValueError
        for module_name in ALL_MODULES:
            # Reset mock for each call
            mock_db.add.reset_mock()
            mock_db.commit.reset_mock()
            mock_db.refresh.reset_mock()

            try:
                await service.set_module_enabled(tenant_id, module_name, True)
            except ValueError:
                pytest.fail(f"Module '{module_name}' should be valid")

            # Verify module was created
            mock_db.add.assert_called_once()


# =============================================================================
# Test: reset_to_defaults
# =============================================================================


class TestResetToDefaults:
    """Tests for reset_to_defaults method."""

    @pytest.mark.asyncio
    async def test_deletes_existing_and_creates_defaults(
        self, mock_db, mock_user, mock_tenant_3d_print
    ):
        """Test that existing config is deleted and defaults are created."""
        tenant_id = mock_tenant_3d_print.id

        # Existing modules
        existing_modules = [
            create_mock_tenant_module(tenant_id, "spools", False),
            create_mock_tenant_module(tenant_id, "models", True),
        ]

        # First call: get tenant
        mock_tenant_result = MagicMock()
        mock_tenant_result.scalar_one_or_none.return_value = mock_tenant_3d_print

        # Second call: get existing modules
        mock_modules_result = MagicMock()
        mock_modules_result.scalars.return_value.all.return_value = existing_modules

        mock_db.execute.side_effect = [mock_tenant_result, mock_modules_result]

        service = TenantModuleService(db=mock_db, user=mock_user)
        result = await service.reset_to_defaults(tenant_id)

        # Verify all existing modules were deleted
        assert mock_db.delete.await_count == len(existing_modules)

        # Verify new modules were created for ALL_MODULES
        assert mock_db.add.call_count == len(ALL_MODULES)

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_for_nonexistent_tenant(self, mock_db, mock_user):
        """Test that ValueError is raised when tenant not found."""
        tenant_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db, user=mock_user)

        with pytest.raises(ValueError, match="Tenant not found"):
            await service.reset_to_defaults(tenant_id)

    @pytest.mark.asyncio
    async def test_defaults_match_tenant_type(
        self, mock_db, mock_user, mock_tenant_knitting
    ):
        """Test that correct defaults are set based on tenant type."""
        tenant_id = mock_tenant_knitting.id

        # Tenant query
        mock_tenant_result = MagicMock()
        mock_tenant_result.scalar_one_or_none.return_value = mock_tenant_knitting

        # No existing modules
        mock_modules_result = MagicMock()
        mock_modules_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_tenant_result, mock_modules_result]

        service = TenantModuleService(db=mock_db, user=mock_user)

        created_modules = []

        def capture_add(module):
            created_modules.append(module)

        mock_db.add.side_effect = capture_add

        result = await service.reset_to_defaults(tenant_id)

        # Verify modules were created
        assert mock_db.add.call_count == len(ALL_MODULES)

        # Check that knitting defaults are applied
        knitting_defaults = DEFAULT_MODULES_BY_TYPE[TenantType.HAND_KNITTING.value]

        for module in created_modules:
            expected_enabled = module.module_name in knitting_defaults
            assert module.enabled == expected_enabled, (
                f"Module '{module.module_name}' should be "
                f"{'enabled' if expected_enabled else 'disabled'} for knitting tenant"
            )


# =============================================================================
# Test: initialize_tenant_modules
# =============================================================================


class TestInitializeTenantModules:
    """Tests for initialize_tenant_modules method."""

    @pytest.mark.asyncio
    async def test_returns_existing_if_already_initialized(
        self, mock_db, mock_tenant_3d_print
    ):
        """Test that existing config is returned if already initialized."""
        tenant_id = mock_tenant_3d_print.id

        existing_modules = [
            create_mock_tenant_module(tenant_id, "spools", True),
            create_mock_tenant_module(tenant_id, "models", True),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = existing_modules
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db)
        result = await service.initialize_tenant_modules(tenant_id)

        assert result == existing_modules
        # reset_to_defaults should NOT have been called
        mock_db.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_creates_defaults_if_not_initialized(
        self, mock_db, mock_user, mock_tenant_3d_print
    ):
        """Test that defaults are created for new tenant."""
        tenant_id = mock_tenant_3d_print.id

        # First call: check existing (none)
        mock_modules_result = MagicMock()
        mock_modules_result.scalars.return_value.all.return_value = []

        # Second call: get tenant for reset
        mock_tenant_result = MagicMock()
        mock_tenant_result.scalar_one_or_none.return_value = mock_tenant_3d_print

        # Third call: get existing for delete (none)
        mock_empty_result = MagicMock()
        mock_empty_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [
            mock_modules_result,
            mock_tenant_result,
            mock_empty_result,
        ]

        service = TenantModuleService(db=mock_db, user=mock_user)
        result = await service.initialize_tenant_modules(tenant_id)

        # Should have created modules for all ALL_MODULES
        assert mock_db.add.call_count == len(ALL_MODULES)


# =============================================================================
# Test: get_module_status
# =============================================================================


class TestGetModuleStatus:
    """Tests for get_module_status method."""

    @pytest.mark.asyncio
    async def test_returns_status_for_all_modules(
        self, mock_db, mock_tenant_3d_print
    ):
        """Test that status is returned for all modules."""
        tenant_id = mock_tenant_3d_print.id

        # Tenant query
        mock_tenant_result = MagicMock()
        mock_tenant_result.scalar_one_or_none.return_value = mock_tenant_3d_print

        # Some configured modules
        configured_modules = [
            create_mock_tenant_module(tenant_id, "spools", True),
            create_mock_tenant_module(tenant_id, "models", False),
        ]

        mock_modules_result = MagicMock()
        mock_modules_result.scalars.return_value.all.return_value = configured_modules

        mock_db.execute.side_effect = [mock_tenant_result, mock_modules_result]

        service = TenantModuleService(db=mock_db)
        result = await service.get_module_status(tenant_id)

        # Should have status for all modules
        assert len(result) == len(ALL_MODULES)

        # Configured modules should show configured=True
        assert result["spools"]["configured"] is True
        assert result["spools"]["enabled"] is True

        assert result["models"]["configured"] is True
        assert result["models"]["enabled"] is False

        # Non-configured modules should use defaults
        for module_name in ALL_MODULES:
            if module_name not in ["spools", "models"]:
                assert result[module_name]["configured"] is False

    @pytest.mark.asyncio
    async def test_raises_for_nonexistent_tenant(self, mock_db):
        """Test that ValueError is raised when tenant not found."""
        tenant_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db)

        with pytest.raises(ValueError, match="Tenant not found"):
            await service.get_module_status(tenant_id)

    @pytest.mark.asyncio
    async def test_is_default_flag_accurate(self, mock_db, mock_tenant_3d_print):
        """Test that is_default flag correctly identifies default status."""
        tenant_id = mock_tenant_3d_print.id
        defaults = DEFAULT_MODULES_BY_TYPE[TenantType.THREE_D_PRINT.value]

        # Tenant query
        mock_tenant_result = MagicMock()
        mock_tenant_result.scalar_one_or_none.return_value = mock_tenant_3d_print

        # spools is default-enabled for 3D print, but we'll disable it
        # models is also default-enabled, we'll leave it enabled
        configured_modules = [
            create_mock_tenant_module(tenant_id, "spools", False),  # Changed from default
            create_mock_tenant_module(tenant_id, "models", True),   # Same as default
        ]

        mock_modules_result = MagicMock()
        mock_modules_result.scalars.return_value.all.return_value = configured_modules

        mock_db.execute.side_effect = [mock_tenant_result, mock_modules_result]

        service = TenantModuleService(db=mock_db)
        result = await service.get_module_status(tenant_id)

        # spools is disabled but default is enabled -> is_default=False
        assert result["spools"]["is_default"] is False

        # models is enabled and default is enabled -> is_default=True
        assert result["models"]["is_default"] is True


# =============================================================================
# Test: Default Module Configurations
# =============================================================================


class TestDefaultModuleConfigurations:
    """Tests for default module configurations."""

    def test_all_modules_list_contains_expected_modules(self):
        """Test that ALL_MODULES contains expected modules."""
        expected = ["spools", "models", "printers", "production", "products", "orders", "categories"]
        for module in expected:
            assert module in ALL_MODULES, f"Expected module '{module}' in ALL_MODULES"

    def test_3d_print_defaults_contain_expected_modules(self):
        """Test 3D print tenant type has expected default modules."""
        defaults = DEFAULT_MODULES_BY_TYPE[TenantType.THREE_D_PRINT.value]

        # 3D print should have manufacturing modules
        assert "spools" in defaults
        assert "models" in defaults
        assert "printers" in defaults
        assert "production" in defaults

    def test_knitting_defaults_are_minimal(self):
        """Test knitting tenant types have minimal modules."""
        hand_knitting_defaults = DEFAULT_MODULES_BY_TYPE[TenantType.HAND_KNITTING.value]

        # Knitting should NOT have 3D print specific modules
        assert "spools" not in hand_knitting_defaults
        assert "printers" not in hand_knitting_defaults

        # Should have common modules
        assert "products" in hand_knitting_defaults
        assert "orders" in hand_knitting_defaults

    def test_generic_defaults_are_minimal(self):
        """Test generic tenant type has minimal modules."""
        generic_defaults = DEFAULT_MODULES_BY_TYPE[TenantType.GENERIC.value]

        # Generic should have basic modules only
        assert "products" in generic_defaults
        assert "orders" in generic_defaults
        assert "categories" in generic_defaults

        # Should NOT have specialized modules
        assert "spools" not in generic_defaults
        assert "printers" not in generic_defaults


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in tenant module management."""

    @pytest.mark.asyncio
    async def test_service_works_without_user(self, mock_db, mock_tenant_3d_print):
        """Test that service works when no user is provided (system operations)."""
        tenant_id = mock_tenant_3d_print.id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Create service without user
        service = TenantModuleService(db=mock_db)  # No user

        await service.set_module_enabled(tenant_id, "spools", True)

        # Verify db.add was called (new module created)
        mock_db.add.assert_called_once()

        # Should set enabled_by_user_id to None since no user was provided
        added_module = mock_db.add.call_args[0][0]
        assert added_module.enabled_by_user_id is None

    @pytest.mark.asyncio
    async def test_empty_tenant_modules_list(self, mock_db):
        """Test handling of tenant with no modules configured."""
        tenant_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = TenantModuleService(db=mock_db)
        result = await service.get_tenant_modules(tenant_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_module_name_case_sensitivity(self, mock_db, mock_user):
        """Test that module names are case sensitive."""
        tenant_id = uuid4()

        service = TenantModuleService(db=mock_db, user=mock_user)

        # "SPOOLS" (uppercase) should be rejected since ALL_MODULES has "spools"
        with pytest.raises(ValueError, match="Unknown module"):
            await service.set_module_enabled(tenant_id, "SPOOLS", True)
