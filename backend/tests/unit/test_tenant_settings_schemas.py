"""
Tests for tenant settings Pydantic schemas.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.tenant_settings import (
    BrandingSettings,
    BrandingSettingsUpdate,
    CustomDomainRequest,
    CustomDomainVerifyResponse,
    DynamicLabels,
    EtsyConnectionTest,
    EtsySettingsResponse,
    EtsySettingsUpdate,
    LocalizationSettings,
    ShopSettings,
    ShopSettingsUpdate,
    SquareConnectionTest,
    SquareSettingsResponse,
    SquareSettingsUpdate,
    TenantFeatures,
    TenantMemberInvite,
    TenantMemberListResponse,
    TenantMemberRoleUpdate,
    TenantSettings,
    TenantType,
    TenantUpdate,
    UserRole,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestUserRole:
    def test_all_values(self):
        assert UserRole.OWNER == "owner"
        assert UserRole.ADMIN == "admin"
        assert UserRole.MEMBER == "member"
        assert UserRole.VIEWER == "viewer"


class TestTenantType:
    def test_all_values(self):
        assert TenantType.THREE_D_PRINT == "three_d_print"
        assert TenantType.HAND_KNITTING == "hand_knitting"
        assert TenantType.MACHINE_KNITTING == "machine_knitting"
        assert TenantType.GENERIC == "generic"


class TestBrandingSettings:
    def test_defaults(self):
        b = BrandingSettings()
        assert b.primary_color == "#3B82F6"
        assert b.accent_color == "#10B981"
        assert b.logo_url is None
        assert b.favicon_url is None

    def test_with_values(self):
        b = BrandingSettings(logo_url="https://cdn.example.com/logo.png", primary_color="#FF0000")
        assert b.logo_url == "https://cdn.example.com/logo.png"
        assert b.primary_color == "#FF0000"

    def test_extra_fields_ignored(self):
        b = BrandingSettings(unknown_field="ignored")
        assert not hasattr(b, "unknown_field")


class TestLocalizationSettings:
    def test_defaults(self):
        loc = LocalizationSettings()
        assert loc.currency == "GBP"
        assert loc.currency_symbol == "£"
        assert loc.timezone == "Europe/London"
        assert loc.locale == "en-GB"
        assert loc.weight_unit == "g"
        assert loc.length_unit == "mm"

    def test_weight_unit_literals(self):
        for unit in ("g", "kg", "oz", "lb"):
            loc = LocalizationSettings(weight_unit=unit)
            assert loc.weight_unit == unit

    def test_invalid_weight_unit_raises(self):
        with pytest.raises(ValidationError):
            LocalizationSettings(weight_unit="lbs")

    def test_length_unit_literals(self):
        for unit in ("mm", "cm", "m", "in", "ft"):
            loc = LocalizationSettings(length_unit=unit)
            assert loc.length_unit == unit

    def test_invalid_length_unit_raises(self):
        with pytest.raises(ValidationError):
            LocalizationSettings(length_unit="yards")


class TestDynamicLabels:
    def test_3d_print_defaults(self):
        d = DynamicLabels()
        assert d.material_singular == "Spool"
        assert d.material_plural == "Spools"
        assert d.equipment_singular == "Printer"
        assert d.design_singular == "Model"

    def test_knitting_overrides(self):
        d = DynamicLabels(
            material_singular="Skein",
            material_plural="Skeins",
            equipment_singular="Needle Set",
            design_singular="Pattern",
        )
        assert d.material_singular == "Skein"
        assert d.design_singular == "Pattern"


class TestTenantFeatures:
    def test_defaults(self):
        f = TenantFeatures()
        assert f.inventory_tracking is True
        assert f.online_shop is True
        assert f.pattern_library is False
        assert f.equipment_connections is False
        assert f.time_tracking is False

    def test_enable_knitting_features(self):
        f = TenantFeatures(pattern_library=True, project_tracking=True, needle_inventory=True)
        assert f.pattern_library is True
        assert f.needle_inventory is True


class TestShopSettings:
    def test_defaults(self):
        s = ShopSettings()
        assert s.enabled is False
        assert s.shop_name is None
        assert s.social_links == {}

    def test_with_values(self):
        s = ShopSettings(
            enabled=True,
            shop_name="Mystmereforge",
            shop_url_slug="mystmereforge",
            social_links={"instagram": "https://instagram.com/mystmereforge"},
        )
        assert s.enabled is True
        assert s.social_links["instagram"] == "https://instagram.com/mystmereforge"


class TestTenantSettings:
    def test_defaults(self):
        t = TenantSettings()
        assert t.tenant_type == TenantType.THREE_D_PRINT
        assert t.default_labor_rate == 20.0
        assert t.currency == "GBP"
        assert isinstance(t.branding, BrandingSettings)
        assert isinstance(t.features, TenantFeatures)

    def test_for_tenant_type_3d_print(self):
        t = TenantSettings.for_tenant_type(TenantType.THREE_D_PRINT)
        assert t.tenant_type == TenantType.THREE_D_PRINT
        assert t.labels.material_singular == "Spool"
        assert t.features.equipment_connections is True
        assert t.features.pattern_library is False

    def test_for_tenant_type_hand_knitting(self):
        t = TenantSettings.for_tenant_type(TenantType.HAND_KNITTING)
        assert t.tenant_type == TenantType.HAND_KNITTING
        assert t.labels.material_singular == "Skein"
        assert t.features.pattern_library is True
        assert t.features.equipment_connections is False

    def test_for_tenant_type_machine_knitting(self):
        t = TenantSettings.for_tenant_type(TenantType.MACHINE_KNITTING)
        assert t.labels.material_singular == "Cone"
        assert t.features.production_runs is True

    def test_for_tenant_type_generic(self):
        t = TenantSettings.for_tenant_type(TenantType.GENERIC)
        assert t.labels.design_singular == "Design"
        assert t.features.pattern_library is True


class TestTenantUpdate:
    def test_all_optional(self):
        u = TenantUpdate()
        assert u.name is None
        assert u.description is None
        assert u.tenant_type is None

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            TenantUpdate(name="")

    def test_name_max_100(self):
        u = TenantUpdate(name="N" * 100)
        assert len(u.name) == 100

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            TenantUpdate(name="N" * 101)

    def test_description_max_500(self):
        u = TenantUpdate(description="D" * 500)
        assert len(u.description) == 500

    def test_description_too_long_raises(self):
        with pytest.raises(ValidationError):
            TenantUpdate(description="D" * 501)


class TestShopSettingsUpdate:
    def test_all_optional(self):
        u = ShopSettingsUpdate()
        assert u.enabled is None
        assert u.shop_name is None

    def test_shop_url_slug_pattern(self):
        u = ShopSettingsUpdate(shop_url_slug="my-shop-123")
        assert u.shop_url_slug == "my-shop-123"

    def test_shop_url_slug_invalid_raises(self):
        with pytest.raises(ValidationError):
            ShopSettingsUpdate(shop_url_slug="My Shop!")

    def test_order_prefix_pattern(self):
        u = ShopSettingsUpdate(order_prefix="MF")
        assert u.order_prefix == "MF"

    def test_order_prefix_lowercase_raises(self):
        with pytest.raises(ValidationError):
            ShopSettingsUpdate(order_prefix="mf")

    def test_shop_name_max_100(self):
        u = ShopSettingsUpdate(shop_name="N" * 100)
        assert len(u.shop_name) == 100

    def test_shop_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            ShopSettingsUpdate(shop_name="N" * 101)

    def test_about_text_max_5000(self):
        u = ShopSettingsUpdate(about_text="A" * 5000)
        assert len(u.about_text) == 5000

    def test_about_text_too_long_raises(self):
        with pytest.raises(ValidationError):
            ShopSettingsUpdate(about_text="A" * 5001)


class TestCustomDomainRequest:
    def test_valid(self):
        r = CustomDomainRequest(domain="shop.example.com")
        assert r.domain == "shop.example.com"

    def test_invalid_uppercase_raises(self):
        with pytest.raises(ValidationError):
            CustomDomainRequest(domain="Shop.Example.COM")

    def test_too_short_raises(self):
        with pytest.raises(ValidationError):
            CustomDomainRequest(domain="x.y")

    def test_subdomain_valid(self):
        r = CustomDomainRequest(domain="my-shop.mystmereforge.co.uk")
        assert r.domain == "my-shop.mystmereforge.co.uk"


class TestCustomDomainVerifyResponse:
    def test_success(self):
        r = CustomDomainVerifyResponse(
            success=True, cname_verified=True, txt_verified=True, domain="shop.example.com"
        )
        assert r.success is True
        assert r.error is None

    def test_failure(self):
        r = CustomDomainVerifyResponse(success=False, message="CNAME not set")
        assert r.success is False
        assert r.cname_verified is False


class TestBrandingSettingsUpdate:
    def test_all_optional(self):
        u = BrandingSettingsUpdate()
        assert u.primary_color is None

    def test_valid_hex_color(self):
        u = BrandingSettingsUpdate(primary_color="#3B82F6", accent_color="#10B981")
        assert u.primary_color == "#3B82F6"

    def test_invalid_hex_raises(self):
        with pytest.raises(ValidationError):
            BrandingSettingsUpdate(primary_color="blue")

    def test_invalid_hex_short_raises(self):
        with pytest.raises(ValidationError):
            BrandingSettingsUpdate(primary_color="#FFF")

    def test_logo_url_max_500(self):
        u = BrandingSettingsUpdate(logo_url="https://x.com/" + "a" * 480)
        assert u.logo_url is not None

    def test_logo_url_too_long_raises(self):
        with pytest.raises(ValidationError):
            BrandingSettingsUpdate(logo_url="u" * 501)


class TestEtsySettingsUpdate:
    def test_all_optional(self):
        u = EtsySettingsUpdate()
        assert u.enabled is None
        assert u.api_key is None

    def test_api_key_empty_raises(self):
        with pytest.raises(ValidationError):
            EtsySettingsUpdate(api_key="")

    def test_with_credentials(self):
        u = EtsySettingsUpdate(
            enabled=True,
            api_key="abc123",
            shared_secret="secret",
            access_token="token",
            shop_id="myshop",
        )
        assert u.enabled is True
        assert u.api_key == "abc123"


class TestEtsySettingsResponse:
    def test_defaults(self):
        r = EtsySettingsResponse()
        assert r.enabled is False
        assert r.is_configured is False
        assert r.refresh_token_set is False

    def test_configured(self):
        r = EtsySettingsResponse(
            enabled=True,
            is_configured=True,
            api_key_masked="****5678",
            shop_id="myshop",
            shop_name="My Etsy Shop",
        )
        assert r.is_configured is True
        assert r.shop_name == "My Etsy Shop"


class TestEtsyConnectionTest:
    def test_success(self):
        r = EtsyConnectionTest(success=True, message="Connected", shop_name="My Shop")
        assert r.success is True

    def test_failure(self):
        r = EtsyConnectionTest(success=False, message="Invalid API key")
        assert r.success is False
        assert r.shop_name is None


class TestSquareSettingsUpdate:
    def test_all_optional(self):
        u = SquareSettingsUpdate()
        assert u.enabled is None
        assert u.environment is None

    def test_sandbox_environment(self):
        u = SquareSettingsUpdate(environment="sandbox")
        assert u.environment == "sandbox"

    def test_production_environment(self):
        u = SquareSettingsUpdate(environment="production")
        assert u.environment == "production"

    def test_invalid_environment_raises(self):
        with pytest.raises(ValidationError):
            SquareSettingsUpdate(environment="staging")

    def test_access_token_empty_raises(self):
        with pytest.raises(ValidationError):
            SquareSettingsUpdate(access_token="")


class TestSquareSettingsResponse:
    def test_defaults(self):
        r = SquareSettingsResponse()
        assert r.enabled is False
        assert r.environment == "sandbox"
        assert r.is_configured is False

    def test_configured(self):
        r = SquareSettingsResponse(
            enabled=True,
            environment="production",
            is_configured=True,
            access_token_masked="****abcd",
            app_id="sq0idp-xxx",
        )
        assert r.environment == "production"
        assert r.is_configured is True


class TestSquareConnectionTest:
    def test_success(self):
        r = SquareConnectionTest(
            success=True,
            message="OK",
            environment="sandbox",
            location_name="My Location",
        )
        assert r.success is True
        assert r.location_name == "My Location"

    def test_failure(self):
        r = SquareConnectionTest(success=False, message="Unauthorized")
        assert r.success is False


class TestTenantMemberInvite:
    def test_valid(self):
        i = TenantMemberInvite(email="member@example.com")
        assert i.role == UserRole.MEMBER

    def test_custom_role(self):
        i = TenantMemberInvite(email="admin@example.com", role=UserRole.ADMIN)
        assert i.role == UserRole.ADMIN

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            TenantMemberInvite(email="not-an-email")


class TestTenantMemberRoleUpdate:
    def test_valid(self):
        u = TenantMemberRoleUpdate(role=UserRole.VIEWER)
        assert u.role == UserRole.VIEWER

    def test_required(self):
        with pytest.raises(ValidationError):
            TenantMemberRoleUpdate()


class TestTenantMemberListResponse:
    def test_empty(self):
        r = TenantMemberListResponse(members=[], total=0)
        assert r.total == 0
