"""Service for managing tenant settings with secure credential storage."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from square.client import Client as SquareClient

from app.core.encryption import encrypt_value, mask_credential, safe_decrypt
from app.models.tenant import Tenant
from app.schemas.tenant_settings import (
    BrandingSettingsResponse,
    BrandingSettingsUpdate,
    EtsyConnectionTest,
    EtsySettingsResponse,
    EtsySettingsUpdate,
    ShopSettingsResponse,
    ShopSettingsUpdate,
    SquareConnectionTest,
    SquareSettingsResponse,
    SquareSettingsUpdate,
    TenantResponse,
    TenantUpdate,
)


class TenantSettingsService:
    """Service for managing tenant settings."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Square Settings
    # =========================================================================

    async def get_square_settings(self, tenant_id: UUID) -> SquareSettingsResponse:
        """Get Square payment settings for a tenant (with masked credentials).

        Args:
            tenant_id: The tenant's UUID

        Returns:
            SquareSettingsResponse with masked credentials
        """
        tenant = await self._get_tenant(tenant_id)
        square_config = tenant.settings.get("square", {})

        # Decrypt and mask credentials
        access_token = safe_decrypt(square_config.get("access_token_encrypted", ""))
        location_id = safe_decrypt(square_config.get("location_id_encrypted", ""))

        # Check if configured
        is_configured = bool(access_token and location_id)

        return SquareSettingsResponse(
            enabled=square_config.get("enabled", False),
            environment=square_config.get("environment", "sandbox"),
            is_configured=is_configured,
            access_token_masked=mask_credential(access_token) if access_token else None,
            app_id=square_config.get("app_id"),
            location_id_masked=mask_credential(location_id) if location_id else None,
            updated_at=square_config.get("updated_at"),
        )

    async def update_square_settings(
        self, tenant_id: UUID, data: SquareSettingsUpdate
    ) -> SquareSettingsResponse:
        """Update Square payment settings for a tenant.

        Args:
            tenant_id: The tenant's UUID
            data: The settings update data

        Returns:
            Updated SquareSettingsResponse
        """
        tenant = await self._get_tenant(tenant_id)

        # Get existing settings or create new
        current_settings = dict(tenant.settings)
        square_config = dict(current_settings.get("square", {}))

        # Update provided fields
        if data.enabled is not None:
            square_config["enabled"] = data.enabled

        if data.environment is not None:
            square_config["environment"] = data.environment

        if data.app_id is not None:
            square_config["app_id"] = data.app_id

        # Encrypt sensitive credentials
        if data.access_token is not None:
            square_config["access_token_encrypted"] = encrypt_value(data.access_token)

        if data.location_id is not None:
            square_config["location_id_encrypted"] = encrypt_value(data.location_id)

        # Update timestamp
        square_config["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Save to database
        current_settings["square"] = square_config
        await self._update_tenant_settings(tenant_id, current_settings)

        return await self.get_square_settings(tenant_id)

    async def test_square_connection(self, tenant_id: UUID) -> SquareConnectionTest:
        """Test the Square connection using tenant's credentials.

        Args:
            tenant_id: The tenant's UUID

        Returns:
            SquareConnectionTest with result details
        """
        tenant = await self._get_tenant(tenant_id)
        square_config = tenant.settings.get("square", {})

        # Get decrypted credentials
        access_token = safe_decrypt(square_config.get("access_token_encrypted", ""))
        location_id = safe_decrypt(square_config.get("location_id_encrypted", ""))
        environment = square_config.get("environment", "sandbox")

        if not access_token or not location_id:
            return SquareConnectionTest(
                success=False,
                message="Square credentials are not configured",
                environment=environment,
            )

        try:
            # Initialize Square client
            client = SquareClient(
                access_token=access_token,
                environment=environment,
            )

            # Test by fetching the location
            result = client.locations.retrieve_location(location_id=location_id)

            if result.is_success():
                location = result.body.get("location", {})
                return SquareConnectionTest(
                    success=True,
                    message="Successfully connected to Square",
                    environment=environment,
                    location_name=location.get("name"),
                )
            else:
                errors = result.errors or []
                error_msg = errors[0].get("detail", "Unknown error") if errors else "Unknown error"
                return SquareConnectionTest(
                    success=False,
                    message=f"Square API error: {error_msg}",
                    environment=environment,
                )

        except Exception as e:
            return SquareConnectionTest(
                success=False,
                message=f"Connection failed: {str(e)}",
                environment=environment,
            )

    def get_square_credentials_for_payment(
        self, tenant_settings: dict
    ) -> tuple[str, str, str] | None:
        """Get decrypted Square credentials for payment processing.

        This method is used by the payment service to get credentials
        without an async context.

        Args:
            tenant_settings: The tenant's settings dict

        Returns:
            Tuple of (access_token, location_id, environment) or None if not configured
        """
        square_config = tenant_settings.get("square", {})

        if not square_config.get("enabled", False):
            return None

        access_token = safe_decrypt(square_config.get("access_token_encrypted", ""))
        location_id = safe_decrypt(square_config.get("location_id_encrypted", ""))
        environment = square_config.get("environment", "sandbox")

        if not access_token or not location_id:
            return None

        return (access_token, location_id, environment)

    # =========================================================================
    # Etsy Settings
    # =========================================================================

    async def get_etsy_settings(self, tenant_id: UUID) -> EtsySettingsResponse:
        """Get Etsy marketplace settings for a tenant (with masked credentials).

        Args:
            tenant_id: The tenant's UUID

        Returns:
            EtsySettingsResponse with masked credentials
        """
        tenant = await self._get_tenant(tenant_id)
        etsy_config = tenant.settings.get("etsy", {})

        # Decrypt and mask credentials
        api_key = safe_decrypt(etsy_config.get("api_key_encrypted", ""))
        shared_secret = safe_decrypt(etsy_config.get("shared_secret_encrypted", ""))
        access_token = safe_decrypt(etsy_config.get("access_token_encrypted", ""))
        refresh_token = safe_decrypt(etsy_config.get("refresh_token_encrypted", ""))

        # Check if configured (need at least api_key, access_token, and shop_id)
        shop_id = etsy_config.get("shop_id")
        is_configured = bool(api_key and access_token and shop_id)

        return EtsySettingsResponse(
            enabled=etsy_config.get("enabled", False),
            is_configured=is_configured,
            api_key_masked=mask_credential(api_key) if api_key else None,
            shared_secret_masked=mask_credential(shared_secret) if shared_secret else None,
            access_token_masked=mask_credential(access_token) if access_token else None,
            refresh_token_set=bool(refresh_token),
            shop_id=shop_id,
            shop_name=etsy_config.get("shop_name"),
            updated_at=etsy_config.get("updated_at"),
        )

    async def update_etsy_settings(
        self, tenant_id: UUID, data: EtsySettingsUpdate
    ) -> EtsySettingsResponse:
        """Update Etsy marketplace settings for a tenant.

        Args:
            tenant_id: The tenant's UUID
            data: The settings update data

        Returns:
            Updated EtsySettingsResponse
        """
        tenant = await self._get_tenant(tenant_id)

        # Get existing settings or create new
        current_settings = dict(tenant.settings)
        etsy_config = dict(current_settings.get("etsy", {}))

        # Update provided fields
        if data.enabled is not None:
            etsy_config["enabled"] = data.enabled

        if data.shop_id is not None:
            etsy_config["shop_id"] = data.shop_id

        # Encrypt sensitive credentials
        if data.api_key is not None:
            etsy_config["api_key_encrypted"] = encrypt_value(data.api_key)

        if data.shared_secret is not None:
            etsy_config["shared_secret_encrypted"] = encrypt_value(data.shared_secret)

        if data.access_token is not None:
            etsy_config["access_token_encrypted"] = encrypt_value(data.access_token)

        if data.refresh_token is not None:
            etsy_config["refresh_token_encrypted"] = encrypt_value(data.refresh_token)

        # Update timestamp
        etsy_config["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Save to database
        current_settings["etsy"] = etsy_config
        await self._update_tenant_settings(tenant_id, current_settings)

        return await self.get_etsy_settings(tenant_id)

    async def test_etsy_connection(self, tenant_id: UUID) -> EtsyConnectionTest:
        """Test the Etsy connection using tenant's credentials.

        Args:
            tenant_id: The tenant's UUID

        Returns:
            EtsyConnectionTest with result details
        """
        tenant = await self._get_tenant(tenant_id)
        etsy_config = tenant.settings.get("etsy", {})

        # Get decrypted credentials
        api_key = safe_decrypt(etsy_config.get("api_key_encrypted", ""))
        access_token = safe_decrypt(etsy_config.get("access_token_encrypted", ""))
        shop_id = etsy_config.get("shop_id")

        if not api_key or not access_token:
            return EtsyConnectionTest(
                success=False,
                message="Etsy API credentials are not configured",
            )

        if not shop_id:
            return EtsyConnectionTest(
                success=False,
                message="Etsy shop ID is not configured",
            )

        try:
            # Use etsyv3 client to test connection
            from etsyv3 import EtsyAPI

            # Create API client - etsyv3 needs keystring and token
            api = EtsyAPI(
                keystring=api_key,
                token=access_token,
                refresh_token=None,  # Not needed for connection test
                expiry=None,  # Not needed for connection test
            )

            # Get shop info to verify connection
            shop = api.get_shop(shop_id=int(shop_id))

            if shop:
                shop_name = shop.shop_name if hasattr(shop, "shop_name") else str(shop_id)
                shop_url = f"https://www.etsy.com/shop/{shop_name}"

                # Save shop name for display
                current_settings = dict(tenant.settings)
                etsy_config = dict(current_settings.get("etsy", {}))
                etsy_config["shop_name"] = shop_name
                current_settings["etsy"] = etsy_config
                await self._update_tenant_settings(tenant_id, current_settings)

                return EtsyConnectionTest(
                    success=True,
                    message="Successfully connected to Etsy",
                    shop_name=shop_name,
                    shop_url=shop_url,
                )
            else:
                return EtsyConnectionTest(
                    success=False,
                    message="Could not retrieve shop information",
                )

        except Exception as e:
            return EtsyConnectionTest(
                success=False,
                message=f"Connection failed: {str(e)}",
            )

    def get_etsy_credentials(self, tenant_settings: dict) -> dict | None:
        """Get decrypted Etsy credentials for API calls.

        This method is used by EtsySyncService to get credentials
        without an async context.

        Args:
            tenant_settings: The tenant's settings dict

        Returns:
            Dict with api_key, access_token, refresh_token, shop_id or None if not configured
        """
        etsy_config = tenant_settings.get("etsy", {})

        if not etsy_config.get("enabled", False):
            return None

        api_key = safe_decrypt(etsy_config.get("api_key_encrypted", ""))
        shared_secret = safe_decrypt(etsy_config.get("shared_secret_encrypted", ""))
        access_token = safe_decrypt(etsy_config.get("access_token_encrypted", ""))
        refresh_token = safe_decrypt(etsy_config.get("refresh_token_encrypted", ""))
        shop_id = etsy_config.get("shop_id")

        if not api_key or not access_token or not shop_id:
            return None

        return {
            "api_key": api_key,
            "shared_secret": shared_secret,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "shop_id": shop_id,
        }

    # =========================================================================
    # Shop Settings
    # =========================================================================

    async def get_shop_settings(self, tenant_id: UUID) -> ShopSettingsResponse:
        """Get shop settings for a tenant.

        Args:
            tenant_id: The tenant's UUID

        Returns:
            ShopSettingsResponse with current shop configuration
        """
        tenant = await self._get_tenant(tenant_id)
        shop_config = tenant.settings.get("shop", {})

        return ShopSettingsResponse(
            enabled=shop_config.get("enabled", False),
            shop_name=shop_config.get("shop_name"),
            shop_url_slug=shop_config.get("shop_url_slug"),
            custom_domain=shop_config.get("custom_domain"),
            custom_domain_verified=shop_config.get("custom_domain_verified", False),
            order_prefix=shop_config.get("order_prefix"),
            tagline=shop_config.get("tagline"),
            logo_url=shop_config.get("logo_url"),
            favicon_url=shop_config.get("favicon_url"),
            contact_email=shop_config.get("contact_email"),
            contact_phone=shop_config.get("contact_phone"),
            social_instagram=shop_config.get("social_instagram"),
            social_facebook=shop_config.get("social_facebook"),
            social_twitter=shop_config.get("social_twitter"),
            show_reviews=shop_config.get("show_reviews", True),
            allow_guest_checkout=shop_config.get("allow_guest_checkout", True),
            currency=shop_config.get("currency", "GBP"),
            updated_at=shop_config.get("updated_at"),
        )

    async def update_shop_settings(
        self, tenant_id: UUID, data: ShopSettingsUpdate
    ) -> ShopSettingsResponse:
        """Update shop settings for a tenant.

        Args:
            tenant_id: The tenant's UUID
            data: The settings update data

        Returns:
            Updated ShopSettingsResponse
        """
        tenant = await self._get_tenant(tenant_id)

        # Get existing settings or create new
        current_settings = dict(tenant.settings)
        shop_config = dict(current_settings.get("shop", {}))

        # Update provided fields (only non-None values)
        update_fields = [
            "enabled",
            "shop_name",
            "shop_url_slug",
            "custom_domain",
            "order_prefix",
            "tagline",
            "logo_url",
            "favicon_url",
            "contact_email",
            "contact_phone",
            "social_instagram",
            "social_facebook",
            "social_twitter",
            "show_reviews",
            "allow_guest_checkout",
            "currency",
        ]

        for field in update_fields:
            value = getattr(data, field, None)
            if value is not None:
                shop_config[field] = value

        # Update timestamp
        shop_config["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Save to database
        current_settings["shop"] = shop_config
        await self._update_tenant_settings(tenant_id, current_settings)

        return await self.get_shop_settings(tenant_id)

    # =========================================================================
    # Branding Settings
    # =========================================================================

    async def get_branding_settings(self, tenant_id: UUID) -> BrandingSettingsResponse:
        """Get branding settings for a tenant.

        Args:
            tenant_id: The tenant's UUID

        Returns:
            BrandingSettingsResponse with current branding configuration
        """
        tenant = await self._get_tenant(tenant_id)
        branding_config = tenant.settings.get("branding", {})

        return BrandingSettingsResponse(
            logo_url=branding_config.get("logo_url"),
            favicon_url=branding_config.get("favicon_url"),
            primary_color=branding_config.get("primary_color", "#3B82F6"),
            accent_color=branding_config.get("accent_color", "#10B981"),
            font_family=branding_config.get("font_family"),
            updated_at=branding_config.get("updated_at"),
        )

    async def update_branding_settings(
        self, tenant_id: UUID, data: BrandingSettingsUpdate
    ) -> BrandingSettingsResponse:
        """Update branding settings for a tenant.

        Args:
            tenant_id: The tenant's UUID
            data: The settings update data

        Returns:
            Updated BrandingSettingsResponse
        """
        tenant = await self._get_tenant(tenant_id)

        # Get existing settings or create new
        current_settings = dict(tenant.settings)
        branding_config = dict(current_settings.get("branding", {}))

        # Update provided fields (only non-None values)
        update_fields = [
            "logo_url",
            "favicon_url",
            "primary_color",
            "accent_color",
            "font_family",
        ]

        for field in update_fields:
            value = getattr(data, field, None)
            if value is not None:
                branding_config[field] = value

        # Update timestamp
        branding_config["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Save to database
        current_settings["branding"] = branding_config
        await self._update_tenant_settings(tenant_id, current_settings)

        return await self.get_branding_settings(tenant_id)

    # =========================================================================
    # Tenant Details
    # =========================================================================

    async def get_tenant(self, tenant_id: UUID) -> TenantResponse:
        """Get tenant details.

        Args:
            tenant_id: The tenant's UUID

        Returns:
            TenantResponse with tenant details
        """
        tenant = await self._get_tenant(tenant_id)
        return TenantResponse.model_validate(tenant)

    async def update_tenant(self, tenant_id: UUID, data: TenantUpdate) -> TenantResponse:
        """Update tenant details.

        Args:
            tenant_id: The tenant's UUID
            data: The update data

        Returns:
            Updated TenantResponse
        """
        tenant = await self._get_tenant(tenant_id)

        # Build update dict
        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.description is not None:
            updates["description"] = data.description

        if updates:
            updates["updated_at"] = datetime.now(timezone.utc)
            stmt = update(Tenant).where(Tenant.id == tenant_id).values(**updates)
            await self.db.execute(stmt)
            await self.db.commit()

        # Refresh and return
        await self.db.refresh(tenant)
        return TenantResponse.model_validate(tenant)

    # =========================================================================
    # Helpers
    # =========================================================================

    async def _get_tenant(self, tenant_id: UUID) -> Tenant:
        """Get a tenant by ID.

        Args:
            tenant_id: The tenant's UUID

        Returns:
            The Tenant object

        Raises:
            ValueError: If tenant not found
        """
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")

        return tenant

    async def _update_tenant_settings(self, tenant_id: UUID, settings: dict[str, Any]) -> None:
        """Update tenant settings JSON field.

        Args:
            tenant_id: The tenant's UUID
            settings: The new settings dict
        """
        stmt = (
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(settings=settings, updated_at=datetime.now(timezone.utc))
        )
        await self.db.execute(stmt)
        await self.db.commit()


# Factory function for dependency injection
async def get_tenant_settings_service(db: AsyncSession) -> TenantSettingsService:
    """Create a TenantSettingsService instance."""
    return TenantSettingsService(db)
