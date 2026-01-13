"""
Etsy Sync Service

Handles syncing products from Batchivo to Etsy marketplace.
Batchivo is ALWAYS the source of truth - sync overwrites Etsy, never merges.

Phase 1: Manual sync with stub implementation (stores listing data)
Phase 2: Real Etsy API integration with OAuth
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external_listing import ExternalListing
from app.models.product import Product

logger = logging.getLogger(__name__)


class EtsySyncError(Exception):
    """Custom exception for Etsy sync errors."""

    pass


class EtsySyncService:
    """Service for syncing products to Etsy."""

    PLATFORM = "etsy"

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

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
            # Check if we have an existing listing
            existing_listing = await self.get_listing_for_product(product.id)

            if existing_listing:
                # Update existing listing
                return await self._update_etsy_listing(product, existing_listing, force)
            else:
                # Create new listing
                return await self._create_etsy_listing(product)

        except Exception as e:
            logger.exception(f"Error syncing product {product.id} to Etsy")
            return False, f"Sync failed: {str(e)}", None

    async def _create_etsy_listing(
        self, product: Product
    ) -> tuple[bool, str, Optional[ExternalListing]]:
        """Create a new Etsy listing for a product."""
        try:
            # TODO: Phase 2 - Real Etsy API call
            # For now, we'll create a stub listing that can be updated later
            # when Etsy API integration is added

            # Generate a placeholder external ID (in real implementation, this comes from Etsy API)
            # Format: etsy_placeholder_{product_sku}_{timestamp}
            placeholder_id = f"placeholder_{product.sku}_{int(datetime.now().timestamp())}"

            # Create external listing record
            listing = ExternalListing(
                tenant_id=self.tenant_id,
                product_id=product.id,
                platform=self.PLATFORM,
                external_id=placeholder_id,
                external_url=None,  # Will be populated when real Etsy API is integrated
                sync_status="pending",  # Pending until real API integration
                last_synced_at=datetime.now(timezone.utc),
                last_sync_error="Etsy API integration pending - listing prepared for sync",
            )

            self.db.add(listing)
            await self.db.flush()
            await self.db.refresh(listing)

            logger.info(f"Created Etsy listing placeholder for product {product.sku}")

            return (
                True,
                "Listing prepared for Etsy sync. API integration pending.",
                listing,
            )

        except Exception as e:
            logger.exception(f"Error creating Etsy listing for product {product.id}")
            raise EtsySyncError(f"Failed to create listing: {str(e)}")

    async def _update_etsy_listing(
        self, product: Product, listing: ExternalListing, force: bool
    ) -> tuple[bool, str, Optional[ExternalListing]]:
        """Update an existing Etsy listing."""
        try:
            # Check if sync is needed
            if not force and listing.sync_status == "synced":
                time_since_sync = datetime.now(timezone.utc) - listing.last_synced_at.replace(
                    tzinfo=timezone.utc
                )
                if time_since_sync.total_seconds() < 300:  # 5 minutes
                    return (
                        True,
                        f"Listing already synced {int(time_since_sync.total_seconds())} seconds ago. Use force=true to re-sync.",
                        listing,
                    )

            # TODO: Phase 2 - Real Etsy API call to update listing
            # For now, just update the timestamp and status

            listing.last_synced_at = datetime.now(timezone.utc)
            listing.sync_status = "pending"  # Still pending until real API
            listing.last_sync_error = "Etsy API integration pending - listing updated"

            await self.db.flush()
            await self.db.refresh(listing)

            logger.info(f"Updated Etsy listing for product {product.sku}")

            return (
                True,
                "Listing updated for Etsy sync. API integration pending.",
                listing,
            )

        except Exception as e:
            logger.exception(f"Error updating Etsy listing for product {product.id}")
            listing.sync_status = "error"
            listing.last_sync_error = str(e)
            await self.db.flush()
            raise EtsySyncError(f"Failed to update listing: {str(e)}")

    def _build_etsy_listing_data(self, product: Product) -> dict:
        """
        Build the data payload for Etsy API.

        This prepares all the product data that will be sent to Etsy.
        Currently returns the structure, will be used in Phase 2.
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
                p for p in product.pricing if p.is_active and p.sales_channel.platform_type == "etsy"
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
            "description": "\n".join(description_parts),
            "price": price,
            "quantity": product.units_in_stock,
            "sku": product.sku,
            "primary_image_url": primary_image_url,
            "image_urls": [img.image_url for img in product.images] if product.images else [],
            # Etsy-specific fields (to be used with real API)
            "who_made": "i_did",
            "when_made": "made_to_order" if product.print_to_order else "2020_2025",
            "is_supply": False,
            "shipping_profile_id": None,  # To be configured per tenant
            "taxonomy_id": None,  # To be configured per product/category
        }
