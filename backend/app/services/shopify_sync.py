"""Shopify product sync service.

Pushes Batchivo products to Shopify Admin REST API 2024-01.
Batchivo is always the source of truth — sync overwrites Shopify data.

Usage:
    sync_service = ShopifySyncService(db, tenant_id)
    success, message, listing = await sync_service.sync_product(product)
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.external_listing import ExternalListing
from app.models.product import Product

logger = logging.getLogger(__name__)

SHOPIFY_API_VERSION = "2024-01"


class ShopifySyncError(Exception):
    """Raised when Shopify sync fails."""


class ShopifyNotConfiguredError(ShopifySyncError):
    """Raised when Shopify credentials are not configured."""


class ShopifySyncService:
    """
    Synchronises a Batchivo product to Shopify.

    Creates a new Shopify product if no listing record exists.
    Updates the existing Shopify product if one does.

    The ``external_listings`` table tracks the mapping:
      product_id ↔ Shopify product_id (stored as external_id, platform='shopify')
    """

    PLATFORM = "shopify"

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Credentials & HTTP
    # ------------------------------------------------------------------

    def _get_credentials(self) -> tuple[str, str]:
        """Return (store_domain, access_token) from app settings."""
        domain = self._settings.shopify_store_domain
        token = self._settings.shopify_access_token
        if not domain or not token:
            raise ShopifyNotConfiguredError(
                "SHOPIFY_STORE_DOMAIN and SHOPIFY_ACCESS_TOKEN must be configured"
            )
        return domain, token

    def _base_url(self, domain: str) -> str:
        return f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}"

    def _headers(self, token: str) -> dict:
        return {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json",
        }

    async def _shopify_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        headers: dict,
        json: dict,
        max_retries: int = 3,
    ) -> httpx.Response:
        """Make a Shopify API request with automatic 429 retry.

        Respects the ``Retry-After`` response header when present,
        falling back to exponential backoff (2s, 4s, 8s).
        """
        for attempt in range(max_retries):
            resp = await client.request(method, url, headers=headers, json=json)
            if resp.status_code != 429:
                return resp
            retry_after = float(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
            logger.warning(
                "Shopify rate limit hit (attempt %d/%d), retrying after %.1fs",
                attempt + 1,
                max_retries,
                retry_after,
            )
            await asyncio.sleep(retry_after)
        # Final attempt — return whatever we get
        return await client.request(method, url, headers=headers, json=json)

    # ------------------------------------------------------------------
    # External listing helpers
    # ------------------------------------------------------------------

    async def get_listing_for_product(self, product_id: UUID) -> Optional[ExternalListing]:
        """Return the Shopify ExternalListing for a product, if one exists."""
        result = await self.db.execute(
            select(ExternalListing).where(
                ExternalListing.product_id == product_id,
                ExternalListing.platform == self.PLATFORM,
                ExternalListing.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def _upsert_listing(
        self,
        product: Product,
        shopify_product_id: str,
        shopify_handle: str,
        status: str = "synced",
        error: Optional[str] = None,
    ) -> ExternalListing:
        """Create or update the ExternalListing record."""
        listing = await self.get_listing_for_product(product.id)
        external_url = f"https://{self._settings.shopify_store_domain}/products/{shopify_handle}"
        if listing is None:
            listing = ExternalListing(
                tenant_id=self.tenant_id,
                product_id=product.id,
                platform=self.PLATFORM,
                external_id=shopify_product_id,
                external_url=external_url,
                sync_status=status,
                last_synced_at=datetime.now(timezone.utc) if status == "synced" else None,
                last_sync_error=error,
            )
            self.db.add(listing)
        else:
            listing.external_id = shopify_product_id
            listing.external_url = external_url
            listing.sync_status = status
            listing.last_sync_error = error
            if status == "synced":
                listing.last_synced_at = datetime.now(timezone.utc)
        return listing

    # ------------------------------------------------------------------
    # Payload construction
    # ------------------------------------------------------------------

    def _build_product_payload(self, product: Product) -> dict:
        """
        Build the Shopify product payload.

        Maps Batchivo fields to Shopify REST API product fields.
        Reference: https://shopify.dev/docs/api/admin-rest/2024-01/resources/product
        """
        # Display description: shop_description > description > name
        body_html = (
            getattr(product, "shop_description", None) or product.description or product.name
        )

        # Tags: merge product.tags (new field) with category slugs
        tags_list: list[str] = list(getattr(product, "tags", None) or [])
        for cat in getattr(product, "categories", []):
            if cat.slug and cat.slug not in tags_list:
                tags_list.append(cat.slug)
        tags_str = ", ".join(tags_list)

        product_type = getattr(product, "product_type", None) or "3D Print"

        # Build variants
        base_price_pence: int = 0
        if product.pricing:
            active = [p for p in product.pricing if p.is_active]
            if active:
                base_price_pence = int(Decimal(str(active[0].list_price)) * 100)

        active_variants = sorted(
            [v for v in getattr(product, "variants", []) if v.is_active],
            key=lambda v: v.display_order,
        )

        if active_variants:
            # Multi-size product — one Shopify variant per Batchivo variant
            shopify_variants = []
            for v in active_variants:
                price_pence = base_price_pence + v.price_adjustment_pence
                price_str = f"{price_pence / 100:.2f}"
                inventory_policy = "continue" if v.fulfilment_type == "print_to_order" else "deny"
                shopify_variants.append(
                    {
                        "option1": v.size,
                        "sku": v.sku or f"{product.sku}-{v.size}",
                        "price": price_str,
                        "inventory_management": "shopify",
                        "inventory_policy": inventory_policy,
                        "inventory_quantity": (
                            v.units_in_stock if v.fulfilment_type == "stock" else 0
                        ),
                        "requires_shipping": True,
                        "weight": product.weight_grams or 0,
                        "weight_unit": "g",
                    }
                )
            options = [{"name": "Size", "values": [v.size for v in active_variants]}]
        else:
            # Single variant (no sizing)
            price_str = f"{base_price_pence / 100:.2f}"
            inventory_policy = "continue" if product.print_to_order else "deny"
            shopify_variants = [
                {
                    "option1": "Default Title",
                    "sku": product.sku or "",
                    "price": price_str,
                    "inventory_management": "shopify",
                    "inventory_policy": inventory_policy,
                    "inventory_quantity": (0 if product.print_to_order else product.units_in_stock),
                    "requires_shipping": True,
                    "weight": product.weight_grams or 0,
                    "weight_unit": "g",
                }
            ]
            options = [{"name": "Title", "values": ["Default Title"]}]

        # Build images list (only URL-based; Shopify downloads them)
        image_objects = []
        for img in sorted(
            getattr(product, "images", []), key=lambda i: (not i.is_primary, i.display_order)
        ):
            if img.image_url:
                # Convert relative paths to absolute API URLs
                url = img.image_url
                if url.startswith("/uploads/products/"):
                    url = url.replace(
                        "/uploads/products/",
                        "https://api.batchivo.com/api/v1/shop/images/",
                    )
                elif url.startswith("/api/v1/shop/images/"):
                    url = f"https://api.batchivo.com{url}"
                image_objects.append({"src": url, "alt": img.alt_text or product.name})

        seo_title = getattr(product, "seo_title", None) or product.name
        seo_desc = getattr(product, "seo_description", None) or ""

        payload: dict = {
            "product": {
                "title": product.feature_title or product.name,
                "body_html": body_html,
                "vendor": "Mystmere Forge",
                "product_type": product_type,
                "tags": tags_str,
                "status": "active" if product.shop_visible else "draft",
                "variants": shopify_variants,
                "options": options,
                "metafields_global_title_tag": seo_title[:70],
                "metafields_global_description_tag": seo_desc[:320],
            }
        }
        if image_objects:
            payload["product"]["images"] = image_objects

        return payload

    # ------------------------------------------------------------------
    # Core sync logic
    # ------------------------------------------------------------------

    async def sync_product(
        self, product: Product, force: bool = False
    ) -> tuple[bool, str, Optional[ExternalListing]]:
        """
        Sync a product to Shopify. Returns (success, message, listing).

        If a listing already exists and force=False, re-syncs only if the
        product was updated after the last sync.
        """
        domain, token = self._get_credentials()
        base_url = self._base_url(domain)
        headers = self._headers(token)

        existing_listing = await self.get_listing_for_product(product.id)

        if (
            existing_listing
            and not force
            and existing_listing.last_synced_at
            and product.updated_at
            and product.updated_at.replace(tzinfo=None)
            <= existing_listing.last_synced_at.replace(tzinfo=None)
        ):
            return (
                True,
                f"Product already up-to-date on Shopify (listing {existing_listing.external_id})",
                existing_listing,
            )

        payload = self._build_product_payload(product)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if existing_listing and existing_listing.external_id:
                    # UPDATE existing Shopify product
                    shopify_id = existing_listing.external_id
                    resp = await self._shopify_request(
                        client,
                        "PUT",
                        f"{base_url}/products/{shopify_id}.json",
                        headers=headers,
                        json=payload,
                    )
                    action = "updated"
                else:
                    # CREATE new Shopify product
                    resp = await self._shopify_request(
                        client,
                        "POST",
                        f"{base_url}/products.json",
                        headers=headers,
                        json=payload,
                    )
                    action = "created"

                if resp.status_code not in (200, 201):
                    error_body = resp.text[:500]
                    logger.error(
                        "Shopify sync failed for product %s: %s %s",
                        product.id,
                        resp.status_code,
                        error_body,
                    )
                    listing = await self._upsert_listing(
                        product,
                        existing_listing.external_id if existing_listing else "unknown",
                        "",
                        status="error",
                        error=f"HTTP {resp.status_code}: {error_body}",
                    )
                    return False, f"Shopify API error {resp.status_code}: {error_body}", listing

                data = resp.json()
                shopify_product = data["product"]
                shopify_id = str(shopify_product["id"])
                shopify_handle = shopify_product.get("handle", "")

                listing = await self._upsert_listing(
                    product, shopify_id, shopify_handle, status="synced"
                )

                logger.info(
                    "Shopify sync %s product %s → Shopify ID %s",
                    action,
                    product.id,
                    shopify_id,
                )
                return (
                    True,
                    f"Product {action} on Shopify (ID {shopify_id})",
                    listing,
                )

        except httpx.HTTPError as exc:
            error_msg = f"HTTP error syncing to Shopify: {exc}"
            logger.exception(error_msg)
            listing = await self._upsert_listing(
                product,
                existing_listing.external_id if existing_listing else "unknown",
                "",
                status="error",
                error=error_msg,
            )
            raise ShopifySyncError(error_msg) from exc
