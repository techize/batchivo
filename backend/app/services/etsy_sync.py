"""
Etsy Sync Service

Handles syncing products from Batchivo to Etsy marketplace.
Batchivo is ALWAYS the source of truth - sync overwrites Etsy, never merges.

Uses etsyv3 library for Etsy API v3 integration.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import safe_decrypt
from app.models.external_listing import ExternalListing
from app.models.product import Product
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class EtsySyncError(Exception):
    """Custom exception for Etsy sync errors."""

    pass


class EtsyNotConfiguredError(EtsySyncError):
    """Raised when Etsy credentials are not configured."""

    pass


class EtsySyncService:
    """Service for syncing products to Etsy."""

    PLATFORM = "etsy"

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self._etsy_credentials: Optional[dict] = None
        self._api = None

    async def _get_etsy_credentials(self) -> dict:
        """Get Etsy credentials from tenant settings."""
        if self._etsy_credentials is not None:
            return self._etsy_credentials

        # Get tenant from database
        result = await self.db.execute(select(Tenant).where(Tenant.id == self.tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise EtsySyncError(f"Tenant not found: {self.tenant_id}")

        etsy_config = tenant.settings.get("etsy", {})

        if not etsy_config.get("enabled", False):
            raise EtsyNotConfiguredError("Etsy integration is not enabled")

        api_key = safe_decrypt(etsy_config.get("api_key_encrypted", ""))
        access_token = safe_decrypt(etsy_config.get("access_token_encrypted", ""))
        refresh_token = safe_decrypt(etsy_config.get("refresh_token_encrypted", ""))
        shop_id = etsy_config.get("shop_id")

        if not api_key or not access_token:
            raise EtsyNotConfiguredError("Etsy API credentials are not configured")

        if not shop_id:
            raise EtsyNotConfiguredError("Etsy shop ID is not configured")

        self._etsy_credentials = {
            "api_key": api_key,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "shop_id": shop_id,
        }

        return self._etsy_credentials

    def _get_etsy_api(self):
        """Get or create Etsy API client."""
        if self._api is not None:
            return self._api

        # This should only be called after _get_etsy_credentials
        if self._etsy_credentials is None:
            raise EtsySyncError("Must call _get_etsy_credentials first")

        from etsyv3 import EtsyAPI

        self._api = EtsyAPI(
            keystring=self._etsy_credentials["api_key"],
            token=self._etsy_credentials["access_token"],
            refresh_token=self._etsy_credentials.get("refresh_token"),
            expiry=None,  # We handle token refresh separately
        )

        return self._api

    async def get_listing_for_product(self, product_id: UUID) -> Optional[ExternalListing]:
        """Get existing Etsy listing for a product."""
        result = await self.db.execute(
            select(ExternalListing).where(
                ExternalListing.product_id == product_id,
                ExternalListing.platform == self.PLATFORM,
                ExternalListing.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def sync_product(
        self, product: Product, force: bool = False
    ) -> tuple[bool, str, Optional[ExternalListing]]:
        """
        Sync a product to Etsy.

        Args:
            product: The product to sync
            force: If True, sync even if already synced recently

        Returns:
            Tuple of (success, message, listing)
        """
        try:
            # Get Etsy credentials first
            await self._get_etsy_credentials()

            # Check if we have an existing listing
            existing_listing = await self.get_listing_for_product(product.id)

            if existing_listing and existing_listing.external_id.startswith("placeholder_"):
                # This was a placeholder from Phase 1, treat as new listing
                existing_listing = None

            if existing_listing:
                # Update existing listing
                return await self._update_etsy_listing(product, existing_listing, force)
            else:
                # Create new listing
                return await self._create_etsy_listing(product)

        except EtsyNotConfiguredError as e:
            logger.warning(f"Etsy not configured for tenant {self.tenant_id}: {e}")
            return False, str(e), None
        except Exception as e:
            logger.exception(f"Error syncing product {product.id} to Etsy")
            return False, f"Sync failed: {str(e)}", None

    async def _create_etsy_listing(
        self, product: Product
    ) -> tuple[bool, str, Optional[ExternalListing]]:
        """Create a new Etsy listing for a product."""
        try:
            api = self._get_etsy_api()
            shop_id = int(self._etsy_credentials["shop_id"])
            listing_data = self._build_etsy_listing_data(product)

            # Validate required data
            if not listing_data["price"]:
                raise EtsySyncError("Product has no price configured")

            if not listing_data["title"]:
                raise EtsySyncError("Product has no title")

            # Create draft listing using etsyv3
            from etsyv3.models.listing_request import (
                CreateDraftListingRequest,
                UpdateListingInventoryRequest,
            )
            from etsyv3.models.product import Product as EtsyProduct

            # Create the draft listing first (without price/quantity)
            create_request = CreateDraftListingRequest(
                quantity=1,  # Initial quantity, will be set via inventory
                title=listing_data["title"][:140],  # Etsy title limit
                description=listing_data["description"][:5000],  # Etsy description limit
                who_made=listing_data["who_made"],
                when_made=listing_data["when_made"],
                taxonomy_id=listing_data["taxonomy_id"] or 2078,  # Default: Art & Collectibles
                is_supply=listing_data["is_supply"],
            )

            # Create the listing on Etsy
            etsy_listing = api.create_draft_listing(shop_id, create_request)

            if not etsy_listing:
                raise EtsySyncError("Failed to create listing - no response from Etsy")

            # Extract listing ID and URL
            listing_id = (
                str(etsy_listing.listing_id) if hasattr(etsy_listing, "listing_id") else None
            )
            if not listing_id:
                raise EtsySyncError("Failed to get listing ID from Etsy response")

            etsy_url = f"https://www.etsy.com/listing/{listing_id}"

            # Update inventory with price, quantity, and SKU
            # Etsy requires inventory to be updated separately
            price_in_cents = int(listing_data["price"] * 100)  # Convert to cents
            etsy_product = EtsyProduct(
                sku=listing_data["sku"] or "",
                property_values=[],
                offerings=[
                    {
                        "price": price_in_cents,
                        "quantity": listing_data["quantity"] or 1,
                        "is_enabled": True,
                    }
                ],
            )

            inventory_request = UpdateListingInventoryRequest(
                products=[etsy_product],
            )

            try:
                api.update_listing_inventory(int(listing_id), inventory_request)
            except Exception as inv_err:
                logger.warning(f"Could not update inventory for listing {listing_id}: {inv_err}")

            # Delete any existing placeholder listing
            existing = await self.get_listing_for_product(product.id)
            if existing:
                await self.db.delete(existing)

            # Create external listing record
            listing = ExternalListing(
                tenant_id=self.tenant_id,
                product_id=product.id,
                platform=self.PLATFORM,
                external_id=listing_id,
                external_url=etsy_url,
                sync_status="synced",
                last_synced_at=datetime.now(timezone.utc),
                last_sync_error=None,
            )

            self.db.add(listing)
            await self.db.flush()
            await self.db.refresh(listing)

            logger.info(f"Created Etsy listing {listing_id} for product {product.sku}")

            return (
                True,
                f"Successfully created Etsy listing. View at: {etsy_url}",
                listing,
            )

        except EtsySyncError:
            raise
        except Exception as e:
            logger.exception(f"Error creating Etsy listing for product {product.id}")
            raise EtsySyncError(f"Failed to create listing: {str(e)}")

    async def _update_etsy_listing(
        self, product: Product, listing: ExternalListing, force: bool
    ) -> tuple[bool, str, Optional[ExternalListing]]:
        """Update an existing Etsy listing."""
        try:
            # Check if sync is needed
            if not force and listing.sync_status == "synced" and listing.last_synced_at:
                last_sync = listing.last_synced_at
                if last_sync.tzinfo is None:
                    last_sync = last_sync.replace(tzinfo=timezone.utc)
                time_since_sync = datetime.now(timezone.utc) - last_sync
                if time_since_sync.total_seconds() < 300:  # 5 minutes
                    return (
                        True,
                        f"Listing already synced {int(time_since_sync.total_seconds())} seconds ago. Use force=true to re-sync.",
                        listing,
                    )

            api = self._get_etsy_api()
            shop_id = int(self._etsy_credentials["shop_id"])
            listing_id = int(listing.external_id)
            listing_data = self._build_etsy_listing_data(product)

            # Update listing using etsyv3
            from etsyv3.models.listing_request import (
                UpdateListingRequest,
                UpdateListingInventoryRequest,
            )
            from etsyv3.models.product import Product as EtsyProduct

            # Update the listing metadata
            update_request = UpdateListingRequest(
                title=listing_data["title"][:140],
                description=listing_data["description"][:5000],
            )

            # Update the listing on Etsy
            api.update_listing(shop_id, listing_id, update_request)

            # Update inventory (price, quantity, SKU)
            if listing_data["price"]:
                price_in_cents = int(listing_data["price"] * 100)
                etsy_product = EtsyProduct(
                    sku=listing_data["sku"] or "",
                    property_values=[],
                    offerings=[
                        {
                            "price": price_in_cents,
                            "quantity": listing_data["quantity"] or 1,
                            "is_enabled": True,
                        }
                    ],
                )

                inventory_request = UpdateListingInventoryRequest(
                    products=[etsy_product],
                )

                try:
                    api.update_listing_inventory(listing_id, inventory_request)
                except Exception as inv_err:
                    logger.warning(
                        f"Could not update inventory for listing {listing_id}: {inv_err}"
                    )

            # Update our record
            listing.last_synced_at = datetime.now(timezone.utc)
            listing.sync_status = "synced"
            listing.last_sync_error = None
            listing.external_url = f"https://www.etsy.com/listing/{listing_id}"

            await self.db.flush()
            await self.db.refresh(listing)

            logger.info(f"Updated Etsy listing {listing_id} for product {product.sku}")

            return (
                True,
                f"Successfully updated Etsy listing. View at: {listing.external_url}",
                listing,
            )

        except Exception as e:
            logger.exception(f"Error updating Etsy listing for product {product.id}")
            listing.sync_status = "error"
            listing.last_sync_error = str(e)
            listing.last_synced_at = datetime.now(timezone.utc)
            await self.db.flush()
            raise EtsySyncError(f"Failed to update listing: {str(e)}")

    def _build_etsy_listing_data(self, product: Product) -> dict:
        """
        Build the data payload for Etsy API.

        This prepares all the product data that will be sent to Etsy.
        """
        # Build description including backstory and specs
        description_parts = []

        if product.shop_description:
            description_parts.append(product.shop_description)
        elif product.description:
            description_parts.append(product.description)

        if product.backstory:
            description_parts.append(f"\n\n{product.backstory}")

        # Add specifications
        specs = []
        if product.weight_grams:
            specs.append(f"Weight: {product.weight_grams}g")
        if product.size_cm:
            specs.append(f"Size: {product.size_cm}cm")
        if product.print_time_hours:
            specs.append(f"Print time: {product.print_time_hours} hours")

        if specs:
            description_parts.append("\n\nSpecifications:\n" + "\n".join(f"• {s}" for s in specs))

        # Get primary image URL
        primary_image_url = None
        if product.images:
            primary_images = [img for img in product.images if img.is_primary]
            if primary_images:
                primary_image_url = primary_images[0].image_url
            elif product.images:
                primary_image_url = product.images[0].image_url

        # Get price from first active pricing (Etsy channel preferred)
        price = None
        if product.pricing:
            etsy_pricing = [
                p
                for p in product.pricing
                if p.is_active and p.sales_channel.platform_type == "etsy"
            ]
            if etsy_pricing:
                price = float(etsy_pricing[0].list_price)
            elif product.pricing:
                # Fall back to first active pricing
                active_pricing = [p for p in product.pricing if p.is_active]
                if active_pricing:
                    price = float(active_pricing[0].list_price)

        return {
            "title": product.feature_title or product.name,
            "description": "\n".join(description_parts) if description_parts else product.name,
            "price": price,
            "quantity": product.units_in_stock,
            "sku": product.sku,
            "primary_image_url": primary_image_url,
            "image_urls": [img.image_url for img in product.images] if product.images else [],
            # Etsy-specific fields
            "who_made": "i_did",
            "when_made": "made_to_order" if product.print_to_order else "2020_2025",
            "is_supply": False,
            "shipping_profile_id": None,  # To be configured per tenant
            "taxonomy_id": None,  # To be configured per product/category
        }
