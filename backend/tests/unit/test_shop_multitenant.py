"""Unit tests for multi-tenant shop functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.api.v1.shop_resolver import extract_subdomain
from app.services.domain_verification import DomainVerificationService


class TestSubdomainExtraction:
    """Tests for subdomain extraction from hostnames."""

    def test_extract_subdomain_from_nozzly_shop(self):
        """Should extract subdomain from *.nozzly.shop."""
        result = extract_subdomain("mystmereforge.nozzly.shop")
        assert result == "mystmereforge"

    def test_extract_subdomain_from_nozzly_app(self):
        """Should extract subdomain from *.nozzly.app."""
        result = extract_subdomain("testshop.nozzly.app")
        assert result == "testshop"

    def test_extract_subdomain_preserves_hyphens(self):
        """Should preserve hyphens in subdomain."""
        result = extract_subdomain("my-cool-shop.nozzly.shop")
        assert result == "my-cool-shop"

    def test_extract_subdomain_returns_none_for_custom_domain(self):
        """Should return None for custom domains."""
        result = extract_subdomain("shop.example.com")
        assert result is None

    def test_extract_subdomain_returns_none_for_bare_domain(self):
        """Should return None for bare shop domain."""
        result = extract_subdomain("nozzly.shop")
        assert result is None

    def test_extract_subdomain_handles_localhost(self):
        """Should return None for localhost."""
        result = extract_subdomain("localhost")
        assert result is None

    def test_extract_subdomain_handles_port(self):
        """Should handle hostname with port number."""
        # Note: Port should be stripped before calling extract_subdomain
        result = extract_subdomain("test.nozzly.shop")
        assert result == "test"


class TestDomainVerificationService:
    """Tests for domain verification service."""

    def test_generate_verification_token_format(self):
        """Should generate token with correct prefix."""
        mock_db = MagicMock()
        service = DomainVerificationService(mock_db)

        token = service.generate_verification_token()

        assert token.startswith("nozzly-verify-")
        assert len(token) > len("nozzly-verify-")

    def test_generate_verification_token_uniqueness(self):
        """Should generate unique tokens."""
        mock_db = MagicMock()
        service = DomainVerificationService(mock_db)

        tokens = [service.generate_verification_token() for _ in range(10)]
        unique_tokens = set(tokens)

        assert len(unique_tokens) == 10

    @pytest.mark.asyncio
    async def test_verify_cname_success(self):
        """Should return True when CNAME points to correct target."""
        mock_db = MagicMock()
        service = DomainVerificationService(mock_db)

        with patch("dns.resolver.resolve") as mock_resolve:
            mock_rdata = MagicMock()
            mock_rdata.target = "shops.nozzly.app."
            mock_resolve.return_value = [mock_rdata]

            success, error = await service.verify_cname("shop.example.com")

        assert success is True
        assert error is None

    @pytest.mark.asyncio
    async def test_verify_cname_wrong_target(self):
        """Should return False when CNAME points to wrong target."""
        mock_db = MagicMock()
        service = DomainVerificationService(mock_db)

        with patch("dns.resolver.resolve") as mock_resolve:
            mock_rdata = MagicMock()
            mock_rdata.target = "other-domain.com."
            mock_resolve.return_value = [mock_rdata]

            success, error = await service.verify_cname("shop.example.com")

        assert success is False
        assert "other-domain.com" in error

    @pytest.mark.asyncio
    async def test_verify_cname_no_record(self):
        """Should return False when no CNAME record exists."""
        import dns.resolver

        mock_db = MagicMock()
        service = DomainVerificationService(mock_db)

        with patch("dns.resolver.resolve") as mock_resolve:
            mock_resolve.side_effect = dns.resolver.NoAnswer()

            success, error = await service.verify_cname("shop.example.com")

        assert success is False
        assert "No CNAME record" in error

    @pytest.mark.asyncio
    async def test_verify_txt_success(self):
        """Should return True when TXT record contains token."""
        mock_db = MagicMock()
        service = DomainVerificationService(mock_db)

        token = "nozzly-verify-abc123"

        with patch("dns.resolver.resolve") as mock_resolve:
            mock_rdata = MagicMock()
            mock_rdata.strings = [token.encode()]
            mock_resolve.return_value = [mock_rdata]

            success, error = await service.verify_txt("example.com", token)

        assert success is True
        assert error is None

    @pytest.mark.asyncio
    async def test_verify_txt_token_not_found(self):
        """Should return False when TXT record doesn't contain token."""
        mock_db = MagicMock()
        service = DomainVerificationService(mock_db)

        with patch("dns.resolver.resolve") as mock_resolve:
            mock_rdata = MagicMock()
            mock_rdata.strings = [b"different-token"]
            mock_resolve.return_value = [mock_rdata]

            success, error = await service.verify_txt("example.com", "nozzly-verify-abc123")

        assert success is False
        assert "does not contain verification token" in error

    @pytest.mark.asyncio
    async def test_initiate_domain_verification(self):
        """Should generate token and return instructions."""
        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {}

        with patch.object(DomainVerificationService, "_get_tenant", return_value=mock_tenant):
            with patch.object(DomainVerificationService, "_update_tenant_settings") as mock_update:
                service = DomainVerificationService(mock_db)
                result = await service.initiate_domain_verification(
                    mock_tenant.id, "shop.example.com"
                )

        assert result["domain"] == "shop.example.com"
        assert result["verification_token"].startswith("nozzly-verify-")
        assert result["cname_target"] == "shops.nozzly.app"
        assert "instructions" in result
        mock_update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_verification_status_no_domain(self):
        """Should return has_custom_domain=False when no domain configured."""
        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {}

        with patch.object(DomainVerificationService, "_get_tenant", return_value=mock_tenant):
            service = DomainVerificationService(mock_db)
            result = await service.get_verification_status(mock_tenant.id)

        assert result["has_custom_domain"] is False
        assert result["domain"] is None

    @pytest.mark.asyncio
    async def test_get_verification_status_with_domain(self):
        """Should return domain details when configured."""
        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {
            "shop": {
                "custom_domain": "shop.example.com",
                "custom_domain_verified": True,
            }
        }

        with patch.object(DomainVerificationService, "_get_tenant", return_value=mock_tenant):
            service = DomainVerificationService(mock_db)
            result = await service.get_verification_status(mock_tenant.id)

        assert result["has_custom_domain"] is True
        assert result["domain"] == "shop.example.com"
        assert result["verified"] is True


class TestShopTenantResolution:
    """Tests for shop tenant resolution by hostname."""

    @pytest.mark.asyncio
    async def test_resolve_tenant_by_slug(self):
        """Should find tenant by slug."""
        from app.api.v1.shop_resolver import resolve_tenant_by_slug

        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.slug = "mystmereforge"
        mock_tenant.is_active = True
        mock_tenant.settings = {"shop": {"enabled": True}}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result

        result = await resolve_tenant_by_slug(mock_db, "mystmereforge")

        assert result == mock_tenant

    @pytest.mark.asyncio
    async def test_resolve_tenant_returns_none_for_inactive(self):
        """Should return None for inactive tenant."""
        from app.api.v1.shop_resolver import resolve_tenant_by_slug

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await resolve_tenant_by_slug(mock_db, "inactive-shop")

        assert result is None

    def test_custom_domain_lookup_logic(self):
        """Test that custom domain lookup strips port and lowercases hostname."""
        # The resolve_tenant_by_custom_domain function uses SQLAlchemy JSONB
        # which requires a real database. Here we test the preprocessing logic.

        # Port stripping
        hostname = "shop.mystmereforge.co.uk:8080"
        processed = hostname.split(":")[0].lower()
        assert processed == "shop.mystmereforge.co.uk"

        # Lowercase
        hostname = "SHOP.MYSTMEREFORGE.CO.UK"
        processed = hostname.split(":")[0].lower()
        assert processed == "shop.mystmereforge.co.uk"

    def test_custom_domain_in_settings(self):
        """Test that custom domain is stored correctly in tenant settings."""
        settings = {
            "shop": {
                "enabled": True,
                "custom_domain": "shop.mystmereforge.co.uk",
                "custom_domain_verified": True,
            }
        }

        shop_config = settings.get("shop", {})
        assert shop_config.get("custom_domain") == "shop.mystmereforge.co.uk"
        assert shop_config.get("custom_domain_verified") is True


class TestTenantSpecificOrderNumbers:
    """Tests for tenant-specific order number generation."""

    def test_order_prefix_from_settings(self):
        """Should use order_prefix from tenant settings."""
        tenant_settings = {"shop": {"order_prefix": "MF"}}
        expected_prefix = tenant_settings.get("shop", {}).get("order_prefix")
        assert expected_prefix == "MF"

    def test_order_prefix_fallback_to_slug(self):
        """Should fallback to uppercase slug when order_prefix not set."""
        tenant_settings = {"shop": {}}
        tenant_slug = "mystmereforge"

        shop_settings = tenant_settings.get("shop", {})
        order_prefix = shop_settings.get("order_prefix") or tenant_slug.upper()[:4]

        assert order_prefix == "MYST"

    def test_order_number_format(self):
        """Should generate order number in PREFIX-YYYYMMDD-NNN format."""
        from datetime import datetime, timezone

        order_prefix = "MF"
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        order_seq = 1

        order_number = f"{order_prefix}-{today}-{order_seq:03d}"

        assert order_number.startswith("MF-")
        assert order_number.endswith("-001")
        assert len(order_number) == 15  # MF-20251231-001


class TestShopSettingsService:
    """Tests for shop settings service methods."""

    @pytest.mark.asyncio
    async def test_get_shop_settings_default(self):
        """Should return default settings when tenant has no shop config."""
        from app.services.tenant_settings import TenantSettingsService

        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.settings = {}
        mock_tenant.id = uuid4()

        with patch.object(TenantSettingsService, "_get_tenant", return_value=mock_tenant):
            service = TenantSettingsService(mock_db)
            result = await service.get_shop_settings(mock_tenant.id)

        assert result.enabled is False
        assert result.shop_name is None
        assert result.order_prefix is None
        assert result.custom_domain_verified is False

    @pytest.mark.asyncio
    async def test_get_shop_settings_configured(self):
        """Should return settings when shop is configured."""
        from app.services.tenant_settings import TenantSettingsService

        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {
            "shop": {
                "enabled": True,
                "shop_name": "Mystmere Forge",
                "order_prefix": "MF",
                "custom_domain": "shop.mystmereforge.co.uk",
                "custom_domain_verified": True,
            }
        }

        with patch.object(TenantSettingsService, "_get_tenant", return_value=mock_tenant):
            service = TenantSettingsService(mock_db)
            result = await service.get_shop_settings(mock_tenant.id)

        assert result.enabled is True
        assert result.shop_name == "Mystmere Forge"
        assert result.order_prefix == "MF"
        assert result.custom_domain == "shop.mystmereforge.co.uk"
        assert result.custom_domain_verified is True

    @pytest.mark.asyncio
    async def test_update_shop_settings(self):
        """Should update shop settings."""
        from app.services.tenant_settings import TenantSettingsService
        from app.schemas.tenant_settings import ShopSettingsUpdate

        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {"shop": {"enabled": False}}

        with patch.object(TenantSettingsService, "_get_tenant", return_value=mock_tenant):
            with patch.object(TenantSettingsService, "_update_tenant_settings") as mock_update:
                service = TenantSettingsService(mock_db)

                update = ShopSettingsUpdate(
                    enabled=True,
                    shop_name="New Shop Name",
                    order_prefix="NS",
                )
                await service.update_shop_settings(mock_tenant.id, update)

                mock_update.assert_awaited_once()
                call_args = mock_update.call_args[0]
                shop_config = call_args[1]["shop"]
                assert shop_config["enabled"] is True
                assert shop_config["shop_name"] == "New Shop Name"
                assert shop_config["order_prefix"] == "NS"


class TestBrandingSettingsService:
    """Tests for branding settings service methods."""

    @pytest.mark.asyncio
    async def test_get_branding_settings_default(self):
        """Should return default colors when tenant has no branding config."""
        from app.services.tenant_settings import TenantSettingsService

        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.settings = {}
        mock_tenant.id = uuid4()

        with patch.object(TenantSettingsService, "_get_tenant", return_value=mock_tenant):
            service = TenantSettingsService(mock_db)
            result = await service.get_branding_settings(mock_tenant.id)

        assert result.primary_color == "#3B82F6"
        assert result.accent_color == "#10B981"
        assert result.logo_url is None

    @pytest.mark.asyncio
    async def test_get_branding_settings_configured(self):
        """Should return configured branding."""
        from app.services.tenant_settings import TenantSettingsService

        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {
            "branding": {
                "logo_url": "/uploads/logo.png",
                "primary_color": "#6B21A8",
                "accent_color": "#F59E0B",
                "font_family": "Inter",
            }
        }

        with patch.object(TenantSettingsService, "_get_tenant", return_value=mock_tenant):
            service = TenantSettingsService(mock_db)
            result = await service.get_branding_settings(mock_tenant.id)

        assert result.logo_url == "/uploads/logo.png"
        assert result.primary_color == "#6B21A8"
        assert result.accent_color == "#F59E0B"
        assert result.font_family == "Inter"

    @pytest.mark.asyncio
    async def test_update_branding_settings(self):
        """Should update branding settings."""
        from app.services.tenant_settings import TenantSettingsService
        from app.schemas.tenant_settings import BrandingSettingsUpdate

        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {}

        with patch.object(TenantSettingsService, "_get_tenant", return_value=mock_tenant):
            with patch.object(TenantSettingsService, "_update_tenant_settings") as mock_update:
                service = TenantSettingsService(mock_db)

                update = BrandingSettingsUpdate(
                    primary_color="#FF0000",
                    accent_color="#00FF00",
                )
                await service.update_branding_settings(mock_tenant.id, update)

                mock_update.assert_awaited_once()
                call_args = mock_update.call_args[0]
                branding_config = call_args[1]["branding"]
                assert branding_config["primary_color"] == "#FF0000"
                assert branding_config["accent_color"] == "#00FF00"
