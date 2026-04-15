"""
Tests for platform admin Pydantic schemas.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.platform_admin import (
    AuditLogResponse,
    ImpersonationResponse,
    PaginatedAuditLogsResponse,
    PaginatedTenantsResponse,
    PaginatedUsersResponse,
    PlatformSettingResponse,
    PlatformSettingUpdate,
    PlatformSettingsResponse,
    TenantActionResponse,
    TenantDetailResponse,
    TenantModuleActionResponse,
    TenantModuleStatus,
    TenantModuleUpdate,
    TenantModulesResetResponse,
    TenantModulesResponse,
    TenantResponse,
    UserResponse,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestTenantResponse:
    def _base(self, **kwargs) -> dict:
        defaults = {
            "id": uuid4(),
            "name": "Test Tenant",
            "slug": "test-tenant",
            "tenant_type": "three_d_print",
            "is_active": True,
            "created_at": _now(),
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        t = TenantResponse(**self._base())
        assert t.name == "Test Tenant"
        assert t.settings is None

    def test_with_settings(self):
        t = TenantResponse(**self._base(settings={"theme": "dark"}))
        assert t.settings == {"theme": "dark"}

    def test_inactive(self):
        t = TenantResponse(**self._base(is_active=False))
        assert t.is_active is False


class TestTenantDetailResponse:
    def _base(self, **kwargs) -> dict:
        defaults = {
            "id": uuid4(),
            "name": "Big Shop",
            "slug": "big-shop",
            "tenant_type": "three_d_print",
            "is_active": True,
            "created_at": _now(),
        }
        defaults.update(kwargs)
        return defaults

    def test_defaults(self):
        t = TenantDetailResponse(**self._base())
        assert t.user_count == 0
        assert t.product_count == 0
        assert t.order_count == 0
        assert t.total_revenue == 0.0

    def test_with_stats(self):
        t = TenantDetailResponse(
            **self._base(user_count=5, product_count=50, order_count=200, total_revenue=9999.99)
        )
        assert t.user_count == 5
        assert t.total_revenue == 9999.99


class TestPaginatedTenantsResponse:
    def test_empty(self):
        r = PaginatedTenantsResponse(items=[], total=0, skip=0, limit=20)
        assert r.total == 0

    def test_with_values(self):
        r = PaginatedTenantsResponse(items=[], total=100, skip=40, limit=20)
        assert r.skip == 40
        assert r.limit == 20


class TestUserResponse:
    def test_valid(self):
        u = UserResponse(
            id=uuid4(),
            email="admin@example.com",
            full_name="Admin User",
            is_active=True,
            is_platform_admin=True,
            created_at=_now(),
        )
        assert u.is_platform_admin is True
        assert u.full_name == "Admin User"

    def test_no_full_name(self):
        u = UserResponse(
            id=uuid4(),
            email="user@example.com",
            full_name=None,
            is_active=True,
            is_platform_admin=False,
            created_at=_now(),
        )
        assert u.full_name is None


class TestPaginatedUsersResponse:
    def test_empty(self):
        r = PaginatedUsersResponse(items=[], total=0, skip=0, limit=50)
        assert r.total == 0


class TestImpersonationResponse:
    def test_valid(self):
        r = ImpersonationResponse(
            access_token="tok123",
            tenant_id=uuid4(),
            tenant_name="Test Shop",
        )
        assert r.token_type == "bearer"
        assert r.access_token == "tok123"

    def test_custom_token_type(self):
        r = ImpersonationResponse(
            access_token="tok",
            token_type="JWT",
            tenant_id=uuid4(),
            tenant_name="Shop",
        )
        assert r.token_type == "JWT"


class TestPlatformSettingResponse:
    def test_valid(self):
        s = PlatformSettingResponse(
            key="maintenance_mode",
            value=False,
            description="Enable maintenance mode",
            updated_at=_now(),
            updated_by=None,
        )
        assert s.key == "maintenance_mode"
        assert s.description is not None

    def test_complex_value(self):
        s = PlatformSettingResponse(
            key="feature_flags",
            value={"seo": True, "analytics": False},
            description=None,
            updated_at=_now(),
            updated_by=uuid4(),
        )
        assert s.value["seo"] is True


class TestPlatformSettingUpdate:
    def test_valid(self):
        u = PlatformSettingUpdate(value=True)
        assert u.value is True
        assert u.description is None

    def test_with_description(self):
        u = PlatformSettingUpdate(value=42, description="New description")
        assert u.value == 42

    def test_value_required(self):
        with pytest.raises(ValidationError):
            PlatformSettingUpdate()


class TestPlatformSettingsResponse:
    def test_empty(self):
        r = PlatformSettingsResponse(items=[])
        assert r.items == []


class TestAuditLogResponse:
    def test_valid(self):
        r = AuditLogResponse(
            id=uuid4(),
            admin_user_id=uuid4(),
            action="impersonate_tenant",
            target_type="tenant",
            target_id=uuid4(),
            action_metadata={"reason": "Support request"},
            ip_address="192.168.1.1",
            created_at=_now(),
        )
        assert r.action == "impersonate_tenant"

    def test_optional_fields(self):
        r = AuditLogResponse(
            id=uuid4(),
            admin_user_id=uuid4(),
            action="list_tenants",
            target_type=None,
            target_id=None,
            action_metadata=None,
            ip_address=None,
            created_at=_now(),
        )
        assert r.target_type is None
        assert r.action_metadata is None


class TestPaginatedAuditLogsResponse:
    def test_valid(self):
        r = PaginatedAuditLogsResponse(items=[], total=500, skip=100, limit=50)
        assert r.total == 500


class TestTenantActionResponse:
    def test_activate(self):
        r = TenantActionResponse(
            id=uuid4(),
            name="My Shop",
            is_active=True,
            message="Tenant activated successfully",
        )
        assert r.is_active is True

    def test_deactivate(self):
        r = TenantActionResponse(
            id=uuid4(),
            name="My Shop",
            is_active=False,
            message="Tenant deactivated",
        )
        assert r.is_active is False


class TestTenantModuleStatus:
    def test_valid(self):
        s = TenantModuleStatus(
            module_name="analytics",
            enabled=True,
            is_default=True,
            configured=False,
        )
        assert s.module_name == "analytics"
        assert s.enabled_by_user_id is None
        assert s.updated_at is None

    def test_configured(self):
        s = TenantModuleStatus(
            module_name="seo",
            enabled=False,
            is_default=False,
            configured=True,
            enabled_by_user_id=uuid4(),
            updated_at=_now(),
        )
        assert s.configured is True


class TestTenantModulesResponse:
    def test_valid(self):
        r = TenantModulesResponse(
            tenant_id=uuid4(),
            tenant_type="three_d_print",
            modules=[],
        )
        assert r.modules == []


class TestTenantModuleUpdate:
    def test_enable(self):
        u = TenantModuleUpdate(enabled=True)
        assert u.enabled is True

    def test_disable(self):
        u = TenantModuleUpdate(enabled=False)
        assert u.enabled is False

    def test_required(self):
        with pytest.raises(ValidationError):
            TenantModuleUpdate()


class TestTenantModuleActionResponse:
    def test_valid(self):
        r = TenantModuleActionResponse(
            module_name="analytics", enabled=True, message="Module enabled"
        )
        assert r.enabled is True


class TestTenantModulesResetResponse:
    def test_valid(self):
        r = TenantModulesResetResponse(
            tenant_id=uuid4(),
            tenant_type="three_d_print",
            modules_reset=5,
            message="Reset complete",
        )
        assert r.modules_reset == 5
