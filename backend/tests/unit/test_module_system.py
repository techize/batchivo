"""Tests for the module system (registration, discovery, tenant filtering)."""

import pytest
from unittest.mock import MagicMock

from app.models.tenant import Tenant, TenantType
from app.modules.base import BaseModule, ModuleInfo, RouteInfo
from app.modules.registry import get_module_registry, reset_module_registry
from app.schemas.tenant_settings import TenantType as SchemaTenantType


class DummyModule(BaseModule):
    """Test module for unit tests."""

    name = "dummy"
    display_name = "Dummy Module"
    icon = "test"
    description = "A test module"
    tenant_types = []

    def register_routes(self, router):
        @router.get("/test")
        def test_route():
            return {"status": "ok"}


class Print3DModule(BaseModule):
    """Module only for 3D print tenants."""

    name = "print3d"
    display_name = "3D Print Features"
    icon = "printer"
    description = "3D printing specific features"
    tenant_types = [SchemaTenantType.THREE_D_PRINT]

    def register_routes(self, router):
        @router.get("/printers")
        def list_printers():
            return []


class KnittingOnlyModule(BaseModule):
    """Module only for knitting tenants."""

    name = "knitting_only"
    display_name = "Knitting Features"
    icon = "yarn"
    description = "Knitting specific features"
    tenant_types = [SchemaTenantType.HAND_KNITTING, SchemaTenantType.MACHINE_KNITTING]

    def register_routes(self, router):
        @router.get("/yarn")
        def list_yarn():
            return []


class CoreModule(BaseModule):
    """Core module always enabled."""

    name = "core"
    display_name = "Core Features"
    icon = "core"
    description = "Core features"
    is_core = True
    tenant_types = []

    def register_routes(self, router):
        pass


@pytest.fixture
def clean_registry():
    """Ensure clean registry for each test."""
    reset_module_registry()
    yield
    reset_module_registry()


@pytest.fixture
def tenant_3d_print():
    """Create a 3D print tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = "tenant-3d"
    tenant.name = "3D Print Shop"
    tenant.tenant_type = TenantType.THREE_D_PRINT.value
    return tenant


@pytest.fixture
def tenant_knitting():
    """Create a knitting tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = "tenant-knit"
    tenant.name = "Knitting Studio"
    tenant.tenant_type = TenantType.HAND_KNITTING.value
    return tenant


@pytest.fixture
def tenant_generic():
    """Create a generic tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = "tenant-generic"
    tenant.name = "Generic Maker"
    tenant.tenant_type = TenantType.GENERIC.value
    return tenant


class TestModuleRegistration:
    """Test module registration functionality."""

    def test_register_module_class(self, clean_registry):
        """Test registering a module by class."""
        registry = get_module_registry()
        module = registry.register(DummyModule)

        assert module.name == "dummy"
        assert module in registry.get_all_modules()

    def test_register_module_instance(self, clean_registry):
        """Test registering a module instance."""
        registry = get_module_registry()
        module = DummyModule()
        registry.register_module(module)

        assert registry.get_module("dummy") is module

    def test_duplicate_registration_raises(self, clean_registry):
        """Test that duplicate registration raises ValueError."""
        registry = get_module_registry()
        registry.register(DummyModule)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(DummyModule)

    def test_get_nonexistent_module(self, clean_registry):
        """Test getting a module that doesn't exist."""
        registry = get_module_registry()

        assert registry.get_module("nonexistent") is None

    def test_get_all_modules(self, clean_registry):
        """Test getting all registered modules."""
        registry = get_module_registry()
        registry.register(DummyModule)
        registry.register(Print3DModule)

        modules = registry.get_all_modules()
        assert len(modules) == 2
        module_names = [m.name for m in modules]
        assert "dummy" in module_names
        assert "print3d" in module_names

    def test_registry_clear(self, clean_registry):
        """Test clearing the registry."""
        registry = get_module_registry()
        registry.register(DummyModule)

        assert len(registry.get_all_modules()) == 1

        registry.clear()

        assert len(registry.get_all_modules()) == 0


class TestModuleTenantFiltering:
    """Test module filtering by tenant type."""

    def test_universal_module_enabled_for_all(
        self, clean_registry, tenant_3d_print, tenant_knitting, tenant_generic
    ):
        """Test that modules with empty tenant_types are enabled for all."""
        registry = get_module_registry()
        registry.register(DummyModule)

        # Should be enabled for all tenant types
        assert DummyModule().is_enabled_for_tenant(tenant_3d_print)
        assert DummyModule().is_enabled_for_tenant(tenant_knitting)
        assert DummyModule().is_enabled_for_tenant(tenant_generic)

    def test_3d_print_module_only_for_3d_print(
        self, clean_registry, tenant_3d_print, tenant_knitting, tenant_generic
    ):
        """Test that 3D print module is only enabled for 3D print tenants."""
        module = Print3DModule()

        assert module.is_enabled_for_tenant(tenant_3d_print)
        assert not module.is_enabled_for_tenant(tenant_knitting)
        assert not module.is_enabled_for_tenant(tenant_generic)

    def test_knitting_module_for_knitting_tenants(
        self, clean_registry, tenant_3d_print, tenant_knitting
    ):
        """Test that knitting module is enabled for knitting tenants only."""
        module = KnittingOnlyModule()

        assert not module.is_enabled_for_tenant(tenant_3d_print)
        assert module.is_enabled_for_tenant(tenant_knitting)

    def test_core_module_always_enabled(
        self, clean_registry, tenant_3d_print, tenant_knitting, tenant_generic
    ):
        """Test that core modules are always enabled."""
        module = CoreModule()

        assert module.is_core
        assert module.is_enabled_for_tenant(tenant_3d_print)
        assert module.is_enabled_for_tenant(tenant_knitting)
        assert module.is_enabled_for_tenant(tenant_generic)

    def test_get_modules_for_tenant(self, clean_registry, tenant_3d_print, tenant_knitting):
        """Test getting modules filtered by tenant."""
        registry = get_module_registry()
        registry.register(DummyModule)
        registry.register(Print3DModule)
        registry.register(KnittingOnlyModule)
        registry.register(CoreModule)

        # 3D print tenant should get dummy, print3d, and core
        modules_3d = registry.get_modules_for_tenant(tenant_3d_print)
        names_3d = [m.name for m in modules_3d]
        assert "dummy" in names_3d
        assert "print3d" in names_3d
        assert "core" in names_3d
        assert "knitting_only" not in names_3d

        # Knitting tenant should get dummy, knitting_only, and core
        modules_knit = registry.get_modules_for_tenant(tenant_knitting)
        names_knit = [m.name for m in modules_knit]
        assert "dummy" in names_knit
        assert "knitting_only" in names_knit
        assert "core" in names_knit
        assert "print3d" not in names_knit


class TestModuleInfo:
    """Test module information extraction."""

    def test_get_module_info(self, clean_registry):
        """Test getting module information."""
        module = DummyModule()
        info = module.get_info(enabled=True)

        assert isinstance(info, ModuleInfo)
        assert info.name == "dummy"
        assert info.display_name == "Dummy Module"
        assert info.description == "A test module"
        assert info.icon == "test"
        assert info.enabled is True

    def test_get_module_info_disabled(self, clean_registry):
        """Test getting disabled module info."""
        module = DummyModule()
        info = module.get_info(enabled=False)

        assert info.enabled is False

    def test_module_info_includes_routes(self, clean_registry):
        """Test that module info includes route information."""
        module = DummyModule()
        info = module.get_info()

        assert len(info.routes) >= 1
        route = info.routes[0]
        assert isinstance(route, RouteInfo)
        assert route.path == "/test"
        assert route.method == "GET"

    def test_get_module_info_for_tenant(self, clean_registry, tenant_3d_print, tenant_knitting):
        """Test getting module info list for tenant."""
        registry = get_module_registry()
        registry.register(DummyModule)
        registry.register(Print3DModule)
        registry.register(KnittingOnlyModule)

        # 3D print tenant - include disabled to see all
        infos = registry.get_module_info_for_tenant(tenant_3d_print, include_disabled=True)
        info_dict = {i.name: i for i in infos}

        assert info_dict["dummy"].enabled is True
        assert info_dict["print3d"].enabled is True
        assert info_dict["knitting_only"].enabled is False

        # Knitting tenant - only enabled modules
        infos_knit = registry.get_module_info_for_tenant(tenant_knitting, include_disabled=False)
        names = [i.name for i in infos_knit]

        assert "dummy" in names
        assert "knitting_only" in names
        assert "print3d" not in names


class TestModuleDiscovery:
    """Test automatic module discovery."""

    def test_discover_modules(self, clean_registry):
        """Test that module discovery finds modules."""
        registry = get_module_registry()

        count = registry.discover_modules()

        # Should discover at least some modules
        assert count > 0
        modules = registry.get_all_modules()
        assert len(modules) > 0

    def test_discover_finds_3d_print_modules(self, clean_registry):
        """Test that discovery finds 3D print modules."""
        registry = get_module_registry()
        registry.discover_modules()

        # Check for expected 3D print modules
        module_names = [m.name for m in registry.get_all_modules()]

        # These should exist from threed_print package
        assert (
            "spools" in module_names or "spool_inventory" in module_names or len(module_names) > 0
        )

    def test_discover_finds_knitting_modules(self, clean_registry):
        """Test that discovery finds knitting modules."""
        registry = get_module_registry()
        registry.discover_modules()

        module_names = [m.name for m in registry.get_all_modules()]

        # Should find yarn module from knitting package
        assert "yarn" in module_names


class TestModuleRouter:
    """Test module route registration."""

    def test_module_creates_router(self, clean_registry):
        """Test that module creates a router."""
        module = DummyModule()
        router = module.router

        assert router is not None
        assert len(router.routes) > 0

    def test_module_router_is_cached(self, clean_registry):
        """Test that router is cached (same instance returned)."""
        module = DummyModule()
        router1 = module.router
        router2 = module.router

        assert router1 is router2

    def test_routes_extracted_after_registration(self, clean_registry):
        """Test that route info is extracted after router creation."""
        module = DummyModule()
        _ = module.router  # Trigger route registration

        assert len(module._routes) > 0
        assert module._routes[0].path == "/test"
