"""Unit tests for tenant settings service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.tenant_settings import TenantSettingsService
from app.schemas.tenant_settings import SquareSettingsUpdate
from app.core.encryption import encrypt_value


class TestTenantSettingsServiceSquare:
    """Tests for Square settings methods."""

    @pytest.mark.asyncio
    async def test_get_square_settings_default(self):
        """Should return default settings when tenant has no Square config."""
        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.settings = {}
        mock_tenant.id = uuid4()

        with patch.object(TenantSettingsService, "_get_tenant", return_value=mock_tenant):
            service = TenantSettingsService(mock_db)
            result = await service.get_square_settings(mock_tenant.id)

        assert result.enabled is False
        assert result.environment == "sandbox"
        assert result.is_configured is False
        assert result.access_token_masked is None

    @pytest.mark.asyncio
    async def test_get_square_settings_configured(self):
        """Should return settings with masked credentials when configured."""
        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {
            "square": {
                "enabled": True,
                "environment": "production",
                "access_token_encrypted": encrypt_value("sq0atp-XXXXX12345"),
                "location_id_encrypted": encrypt_value("LXXX1234"),
                "app_id": "sq0idp-test",
            }
        }

        with patch.object(TenantSettingsService, "_get_tenant", return_value=mock_tenant):
            service = TenantSettingsService(mock_db)
            result = await service.get_square_settings(mock_tenant.id)

        assert result.enabled is True
        assert result.environment == "production"
        assert result.is_configured is True
        assert result.access_token_masked == "...2345"
        assert result.location_id_masked == "...1234"
        assert result.app_id == "sq0idp-test"

    @pytest.mark.asyncio
    async def test_update_square_settings_enabled(self):
        """Should update the enabled flag."""
        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {"square": {"enabled": False}}

        with patch.object(TenantSettingsService, "_get_tenant", return_value=mock_tenant):
            with patch.object(TenantSettingsService, "_update_tenant_settings") as mock_update:
                service = TenantSettingsService(mock_db)

                update = SquareSettingsUpdate(enabled=True)
                await service.update_square_settings(mock_tenant.id, update)

                # Check the settings dict was updated
                mock_update.assert_awaited_once()
                call_args = mock_update.call_args[0]
                assert call_args[1]["square"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_update_square_settings_encrypts_credentials(self):
        """Should encrypt credentials before storing."""
        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.settings = {}

        with patch.object(TenantSettingsService, "_get_tenant", return_value=mock_tenant):
            with patch.object(TenantSettingsService, "_update_tenant_settings") as mock_update:
                service = TenantSettingsService(mock_db)

                update = SquareSettingsUpdate(
                    access_token="sq0atp-secret",
                    location_id="LTEST123",
                )
                await service.update_square_settings(mock_tenant.id, update)

                # Check credentials were encrypted
                call_args = mock_update.call_args[0]
                square_config = call_args[1]["square"]

                # Fernet tokens start with 'gAAAAA'
                assert square_config["access_token_encrypted"].startswith("gAAAAA")
                assert square_config["location_id_encrypted"].startswith("gAAAAA")


class TestTenantSettingsServiceTenant:
    """Tests for tenant details methods.

    Note: update_tenant tests are in integration tests since they require
    actual database operations (SQLAlchemy update statements).
    """

    @pytest.mark.asyncio
    async def test_get_tenant_returns_response(self):
        """Should return tenant details as response schema."""
        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.name = "Test Tenant"
        mock_tenant.slug = "test-tenant"
        mock_tenant.description = "A test tenant"
        mock_tenant.tenant_type = "three_d_print"
        mock_tenant.is_active = True
        mock_tenant.settings = {}
        mock_tenant.created_at = "2025-01-01T00:00:00Z"
        mock_tenant.updated_at = "2025-01-01T00:00:00Z"

        with patch.object(TenantSettingsService, "_get_tenant", return_value=mock_tenant):
            service = TenantSettingsService(mock_db)
            result = await service.get_tenant(mock_tenant.id)

        assert str(result.id) == str(mock_tenant.id)
        assert result.name == "Test Tenant"
        assert result.slug == "test-tenant"
        assert result.description == "A test tenant"
        assert result.tenant_type.value == "three_d_print"
        assert result.is_active is True


class TestSquareCredentialsForPayment:
    """Tests for get_square_credentials_for_payment method."""

    def test_returns_none_when_disabled(self):
        """Should return None when Square is disabled."""
        mock_db = MagicMock()
        service = TenantSettingsService(mock_db)

        settings = {"square": {"enabled": False}}
        result = service.get_square_credentials_for_payment(settings)

        assert result is None

    def test_returns_none_when_not_configured(self):
        """Should return None when credentials are missing."""
        mock_db = MagicMock()
        service = TenantSettingsService(mock_db)

        settings = {"square": {"enabled": True}}
        result = service.get_square_credentials_for_payment(settings)

        assert result is None

    def test_returns_credentials_when_configured(self):
        """Should return decrypted credentials when properly configured."""
        mock_db = MagicMock()
        service = TenantSettingsService(mock_db)

        settings = {
            "square": {
                "enabled": True,
                "environment": "sandbox",
                "access_token_encrypted": encrypt_value("sq0atp-test-token"),
                "location_id_encrypted": encrypt_value("LTEST123"),
            }
        }
        result = service.get_square_credentials_for_payment(settings)

        assert result is not None
        access_token, location_id, environment = result
        assert access_token == "sq0atp-test-token"
        assert location_id == "LTEST123"
        assert environment == "sandbox"
