"""Tests for Shopify product sync endpoint and service.

Shopify API calls are mocked with httpx.MockTransport so no real
network traffic occurs during tests.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.product import Product
from app.models.product_pricing import ProductPricing
from app.models.sales_channel import SalesChannel


# ============================================================
# Fixtures
# ============================================================


@pytest_asyncio.fixture
async def shop_product(db_session, test_tenant):
    """A basic product ready for shop sync."""
    product = Product(
        tenant_id=test_tenant.id,
        sku="TEST-DRAGON",
        name="Test Dragon",
        description="A fearsome test dragon",
        shop_description="<p>A fearsome test dragon for unit tests.</p>",
        is_active=True,
        shop_visible=True,
        print_to_order=True,
        free_shipping=False,
        is_dragon=True,
        weight_grams=120,
        units_in_stock=0,
    )
    db_session.add(product)

    # Add a sales channel + pricing
    channel = SalesChannel(
        tenant_id=test_tenant.id,
        name="Own Shop",
        platform_type="online_shop",
        is_active=True,
    )
    db_session.add(channel)
    await db_session.flush()

    pricing = ProductPricing(
        product_id=product.id,
        sales_channel_id=channel.id,
        list_price=Decimal("29.99"),
        is_active=True,
    )
    db_session.add(pricing)
    await db_session.flush()

    product_id = product.id
    tenant_id = test_tenant.id
    return product_id, tenant_id


# ============================================================
# Unit tests — ShopifySyncService
# ============================================================


class TestShopifySyncService:
    """Unit-test the sync service in isolation (no real HTTP)."""

    @pytest.mark.asyncio
    async def test_raises_when_not_configured(self, db_session, test_tenant):
        from app.services.shopify_sync import ShopifySyncService, ShopifyNotConfiguredError

        # Patch settings so no credentials are set
        with patch("app.services.shopify_sync.get_settings") as mock_settings:
            cfg = MagicMock()
            cfg.shopify_store_domain = ""
            cfg.shopify_access_token = ""
            mock_settings.return_value = cfg

            service = ShopifySyncService(db_session, test_tenant.id)
            with pytest.raises(ShopifyNotConfiguredError):
                service._get_credentials()

    @pytest.mark.asyncio
    async def test_build_product_payload_single_variant(
        self, db_session, test_tenant, shop_product
    ):
        """Verify payload structure for a product with no size variants."""
        from app.services.shopify_sync import ShopifySyncService

        product_id, tenant_id = shop_product
        with patch("app.services.shopify_sync.get_settings") as mock_settings:
            cfg = MagicMock()
            cfg.shopify_store_domain = "mystmereforge.myshopify.com"
            cfg.shopify_access_token = "shpat_test"
            mock_settings.return_value = cfg

            service = ShopifySyncService(db_session, tenant_id)

            # Fetch fresh product with relationships
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            result = await db_session.execute(
                select(Product)
                .where(Product.id == product_id)
                .options(
                    selectinload(Product.images),
                    selectinload(Product.pricing).selectinload(ProductPricing.sales_channel),
                    selectinload(Product.variants),
                    selectinload(Product.categories),
                )
            )
            product = result.scalar_one()

            payload = service._build_product_payload(product)

        assert payload["product"]["title"] == "Test Dragon"
        assert "body_html" in payload["product"]
        assert payload["product"]["vendor"] == "Mystmere Forge"
        assert payload["product"]["status"] == "active"
        # Single-variant products use "Default Title"
        assert payload["product"]["variants"][0]["option1"] == "Default Title"
        assert payload["product"]["variants"][0]["inventory_policy"] == "continue"  # print_to_order

    @pytest.mark.asyncio
    async def test_build_product_payload_image_url_uses_api_batchivo(
        self, db_session, test_tenant, shop_product
    ):
        """Images stored as /uploads/products/... must resolve to api.batchivo.com, not the
        storefront domain (which is password-protected and inaccessible to Shopify)."""
        from app.models.product_image import ProductImage
        from app.services.shopify_sync import ShopifySyncService
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        product_id, tenant_id = shop_product

        # Add a product image with a /uploads/products/ path
        image = ProductImage(
            tenant_id=test_tenant.id,
            product_id=product_id,
            image_url="/uploads/products/abc123/photo.jpg",
            is_primary=True,
            display_order=0,
        )
        db_session.add(image)
        await db_session.flush()

        with patch("app.services.shopify_sync.get_settings") as mock_settings:
            cfg = MagicMock()
            cfg.shopify_store_domain = "mystmereforge.myshopify.com"
            cfg.shopify_access_token = "shpat_test"
            mock_settings.return_value = cfg

            service = ShopifySyncService(db_session, tenant_id)

            result = await db_session.execute(
                select(Product)
                .where(Product.id == product_id)
                .options(
                    selectinload(Product.images),
                    selectinload(Product.pricing).selectinload(ProductPricing.sales_channel),
                    selectinload(Product.variants),
                    selectinload(Product.categories),
                )
            )
            product = result.scalar_one()

            payload = service._build_product_payload(product)

        images = payload["product"]["images"]
        assert len(images) == 1
        assert images[0]["src"] == "https://api.batchivo.com/api/v1/shop/images/abc123/photo.jpg"
        assert "mystmereforge.myshopify.com" not in images[0]["src"]

    @pytest.mark.asyncio
    async def test_build_product_payload_includes_handle_when_seo_slug_set(
        self, db_session, test_tenant, shop_product
    ):
        """seo_slug must appear as handle to prevent Shopify handle oscillation."""
        from app.services.shopify_sync import ShopifySyncService
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        product_id, tenant_id = shop_product
        r0 = await db_session.execute(select(Product).where(Product.id == product_id))
        prod0 = r0.scalar_one()
        prod0.seo_slug = "test-dragon-uk"
        await db_session.flush()

        with patch("app.services.shopify_sync.get_settings") as mock_settings:
            cfg = MagicMock()
            cfg.shopify_store_domain = "mystmereforge.myshopify.com"
            cfg.shopify_access_token = "shpat_test"
            mock_settings.return_value = cfg
            service = ShopifySyncService(db_session, tenant_id)
            r1 = await db_session.execute(
                select(Product)
                .where(Product.id == product_id)
                .options(
                    selectinload(Product.images),
                    selectinload(Product.pricing).selectinload(ProductPricing.sales_channel),
                    selectinload(Product.variants),
                    selectinload(Product.categories),
                )
            )
            prod = r1.scalar_one()
            payload = service._build_product_payload(prod)

        assert payload["product"]["handle"] == "test-dragon-uk"

    @pytest.mark.asyncio
    async def test_build_product_payload_omits_handle_when_no_seo_slug(
        self, db_session, test_tenant, shop_product
    ):
        """When seo_slug is not set, handle must be absent so Shopify keeps its own value."""
        from app.services.shopify_sync import ShopifySyncService
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        product_id, tenant_id = shop_product
        with patch("app.services.shopify_sync.get_settings") as mock_settings:
            cfg = MagicMock()
            cfg.shopify_store_domain = "mystmereforge.myshopify.com"
            cfg.shopify_access_token = "shpat_test"
            mock_settings.return_value = cfg
            service = ShopifySyncService(db_session, tenant_id)
            r2 = await db_session.execute(
                select(Product)
                .where(Product.id == product_id)
                .options(
                    selectinload(Product.images),
                    selectinload(Product.pricing).selectinload(ProductPricing.sales_channel),
                    selectinload(Product.variants),
                    selectinload(Product.categories),
                )
            )
            prod = r2.scalar_one()
            payload = service._build_product_payload(prod)

        assert "handle" not in payload["product"]

    @pytest.mark.asyncio
    async def test_get_listing_for_product_returns_none_when_missing(
        self, db_session, test_tenant, shop_product
    ):
        from app.services.shopify_sync import ShopifySyncService

        product_id, tenant_id = shop_product
        with patch("app.services.shopify_sync.get_settings"):
            service = ShopifySyncService(db_session, tenant_id)
            listing = await service.get_listing_for_product(product_id)
        assert listing is None


# ============================================================
# API endpoint tests
# ============================================================


class TestShopifySyncEndpoints:
    """Integration-style tests against the API endpoints (mocked HTTP)."""

    @pytest.mark.asyncio
    async def test_sync_shopify_success(
        self, client, db_session, test_tenant, shop_product, auth_headers
    ):
        """POST /sync/shopify creates a listing when Shopify returns 201."""
        product_id, _ = shop_product

        fake_shopify_response = {
            "product": {
                "id": 9988776655,
                "handle": "test-dragon",
                "title": "Test Dragon",
                "variants": [{"id": 111, "sku": "TEST-DRAGON", "price": "29.99"}],
            }
        }

        with (
            patch("app.services.shopify_sync.get_settings") as mock_cfg,
            patch("app.services.shopify_sync.httpx.AsyncClient") as mock_client_cls,
        ):
            cfg = MagicMock()
            cfg.shopify_store_domain = "mystmereforge.myshopify.com"
            cfg.shopify_access_token = "shpat_test"
            mock_cfg.return_value = cfg

            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = fake_shopify_response

            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=None)
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_http

            resp = await client.post(
                f"/api/v1/products/{product_id}/sync/shopify",
                headers=auth_headers,
                json={"force": True},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "9988776655" in data["message"]
        assert data["shopify_url"] is not None

    @pytest.mark.asyncio
    async def test_sync_shopify_product_not_found(self, client, auth_headers):
        """POST /sync/shopify returns 404 for unknown product."""
        random_id = uuid4()
        resp = await client.post(
            f"/api/v1/products/{random_id}/sync/shopify",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_sync_shopify_not_configured(self, client, auth_headers, shop_product):
        """POST /sync/shopify returns 503 when credentials are missing."""
        product_id, _ = shop_product

        with patch("app.services.shopify_sync.get_settings") as mock_cfg:
            cfg = MagicMock()
            cfg.shopify_store_domain = ""
            cfg.shopify_access_token = ""
            mock_cfg.return_value = cfg

            resp = await client.post(
                f"/api/v1/products/{product_id}/sync/shopify",
                headers=auth_headers,
            )
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_get_sync_status_no_listings(self, client, auth_headers, shop_product):
        """GET /sync-status returns unsynced channels when no listings exist."""
        product_id, _ = shop_product
        resp = await client.get(
            f"/api/v1/products/{product_id}/sync-status",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["shop"]["synced"] is True  # shop_visible=True
        assert data["shopify"]["synced"] is False
        assert data["etsy"]["synced"] is False

    @pytest.mark.asyncio
    async def test_get_sync_status_not_found(self, client, auth_headers):
        """GET /sync-status returns 404 for unknown product."""
        random_id = uuid4()
        resp = await client.get(
            f"/api/v1/products/{random_id}/sync-status",
            headers=auth_headers,
        )
        assert resp.status_code == 404
