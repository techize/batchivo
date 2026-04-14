"""Unit tests for ShopifySyncService._build_product_payload and
EtsySyncService._build_etsy_listing_data.

Both methods are pure product-data transformation: no DB access, no HTTP calls.
We construct minimal SimpleNamespace product objects and verify the payload dicts.
"""

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.shopify_sync import ShopifySyncService
from app.services.etsy_sync import EtsySyncService


# ---------------------------------------------------------------------------
# Helpers — build lightweight product-like SimpleNamespace objects
# ---------------------------------------------------------------------------


def make_pricing(list_price, is_active=True, platform_type="shopify"):
    channel = SimpleNamespace(platform_type=platform_type)
    return SimpleNamespace(
        list_price=Decimal(str(list_price)), is_active=is_active, sales_channel=channel
    )


def make_variant(
    size="M",
    sku=None,
    is_active=True,
    display_order=0,
    price_adjustment_pence=0,
    fulfilment_type="stock",
    units_in_stock=10,
):
    return SimpleNamespace(
        size=size,
        sku=sku,
        is_active=is_active,
        display_order=display_order,
        price_adjustment_pence=price_adjustment_pence,
        fulfilment_type=fulfilment_type,
        units_in_stock=units_in_stock,
    )


def make_image(image_url, is_primary=False, display_order=0, alt_text=None):
    return SimpleNamespace(
        image_url=image_url,
        is_primary=is_primary,
        display_order=display_order,
        alt_text=alt_text,
    )


def make_product(**kwargs):
    defaults = dict(
        id=uuid4(),
        sku="SKU-001",
        name="Test Product",
        feature_title=None,
        description=None,
        shop_description=None,
        backstory=None,
        weight_grams=None,
        size_cm=None,
        print_time_hours=None,
        units_in_stock=5,
        print_to_order=False,
        shop_visible=True,
        pricing=[],
        variants=[],
        images=[],
        categories=[],
        tags=None,
        product_type=None,
        seo_title=None,
        seo_description=None,
        seo_slug=None,
    )
    return SimpleNamespace(**{**defaults, **kwargs})


def shopify_service():
    """Return a minimal ShopifySyncService-like object for calling unbound methods."""
    return SimpleNamespace()


def etsy_service():
    """Return a minimal EtsySyncService-like object for calling unbound methods."""
    return SimpleNamespace()


# ---------------------------------------------------------------------------
# ShopifySyncService._build_product_payload
# ---------------------------------------------------------------------------


class TestShopifyBuildProductPayload:
    def _build(self, product):
        return ShopifySyncService._build_product_payload(shopify_service(), product)

    def test_title_uses_feature_title_when_set(self):
        product = make_product(feature_title="Dragon - Limited Edition", name="Dragon")
        payload = self._build(product)
        assert payload["product"]["title"] == "Dragon - Limited Edition"

    def test_title_falls_back_to_name(self):
        product = make_product(feature_title=None, name="Dragon")
        payload = self._build(product)
        assert payload["product"]["title"] == "Dragon"

    def test_status_active_when_shop_visible(self):
        product = make_product(shop_visible=True)
        payload = self._build(product)
        assert payload["product"]["status"] == "active"

    def test_status_draft_when_not_shop_visible(self):
        product = make_product(shop_visible=False)
        payload = self._build(product)
        assert payload["product"]["status"] == "draft"

    def test_single_variant_default_title(self):
        product = make_product(variants=[])
        payload = self._build(product)
        variants = payload["product"]["variants"]
        assert len(variants) == 1
        assert variants[0]["option1"] == "Default Title"

    def test_single_variant_price_from_pricing(self):
        pricing = [make_pricing(12.50)]
        product = make_product(pricing=pricing)
        payload = self._build(product)
        assert payload["product"]["variants"][0]["price"] == "12.50"

    def test_single_variant_zero_price_when_no_pricing(self):
        product = make_product(pricing=[])
        payload = self._build(product)
        assert payload["product"]["variants"][0]["price"] == "0.00"

    def test_single_variant_inventory_policy_deny_for_stock(self):
        product = make_product(print_to_order=False)
        payload = self._build(product)
        assert payload["product"]["variants"][0]["inventory_policy"] == "deny"

    def test_single_variant_inventory_policy_continue_for_print_to_order(self):
        product = make_product(print_to_order=True)
        payload = self._build(product)
        assert payload["product"]["variants"][0]["inventory_policy"] == "continue"

    def test_multi_variant_one_shopify_variant_per_batchivo_variant(self):
        variants = [
            make_variant(size="S", display_order=0, price_adjustment_pence=0),
            make_variant(size="L", display_order=1, price_adjustment_pence=500),
        ]
        pricing = [make_pricing(10.00)]
        product = make_product(variants=variants, pricing=pricing)
        payload = self._build(product)
        shopify_variants = payload["product"]["variants"]
        assert len(shopify_variants) == 2
        assert shopify_variants[0]["option1"] == "S"
        assert shopify_variants[1]["option1"] == "L"

    def test_multi_variant_price_adjustment_applied(self):
        variants = [make_variant(size="XL", price_adjustment_pence=200)]
        pricing = [make_pricing(10.00)]
        product = make_product(variants=variants, pricing=pricing)
        payload = self._build(product)
        # 10.00 + 2.00 = 12.00
        assert payload["product"]["variants"][0]["price"] == "12.00"

    def test_multi_variant_sorted_by_display_order(self):
        variants = [
            make_variant(size="L", display_order=2),
            make_variant(size="S", display_order=0),
            make_variant(size="M", display_order=1),
        ]
        product = make_product(variants=variants)
        payload = self._build(product)
        sizes = [v["option1"] for v in payload["product"]["variants"]]
        assert sizes == ["S", "M", "L"]

    def test_inactive_variants_excluded(self):
        variants = [
            make_variant(size="S", is_active=True, display_order=0),
            make_variant(size="XL", is_active=False, display_order=1),
        ]
        product = make_product(variants=variants)
        payload = self._build(product)
        sizes = [v["option1"] for v in payload["product"]["variants"]]
        assert "XL" not in sizes
        assert "S" in sizes

    def test_tags_from_category_slugs(self):
        cat = SimpleNamespace(slug="dragons")
        product = make_product(categories=[cat])
        payload = self._build(product)
        assert "dragons" in payload["product"]["tags"]

    def test_tags_merged_with_product_tags(self):
        cat = SimpleNamespace(slug="fantasy")
        product = make_product(tags=["new-arrival"], categories=[cat])
        payload = self._build(product)
        tags = payload["product"]["tags"]
        assert "new-arrival" in tags
        assert "fantasy" in tags

    def test_seo_slug_sets_handle(self):
        product = make_product(seo_slug="my-cool-dragon")
        payload = self._build(product)
        assert payload["product"]["handle"] == "my-cool-dragon"

    def test_no_seo_slug_no_handle_key(self):
        product = make_product(seo_slug=None)
        payload = self._build(product)
        assert "handle" not in payload["product"]

    def test_images_included_in_payload(self):
        images = [make_image("https://example.com/img.jpg", is_primary=True)]
        product = make_product(images=images)
        payload = self._build(product)
        assert "images" in payload["product"]
        assert payload["product"]["images"][0]["src"] == "https://example.com/img.jpg"

    def test_relative_upload_path_converted_to_absolute(self):
        images = [make_image("/uploads/products/test.jpg")]
        product = make_product(images=images)
        payload = self._build(product)
        src = payload["product"]["images"][0]["src"]
        assert src.startswith("https://api.batchivo.com/api/v1/shop/images/")

    def test_relative_api_path_converted_to_absolute(self):
        images = [make_image("/api/v1/shop/images/test.jpg")]
        product = make_product(images=images)
        payload = self._build(product)
        src = payload["product"]["images"][0]["src"]
        assert src == "https://api.batchivo.com/api/v1/shop/images/test.jpg"

    def test_body_html_uses_shop_description_first(self):
        product = make_product(shop_description="Shop desc", description="Fallback desc")
        payload = self._build(product)
        assert payload["product"]["body_html"] == "Shop desc"

    def test_body_html_falls_back_to_description(self):
        product = make_product(shop_description=None, description="Fallback desc")
        payload = self._build(product)
        assert payload["product"]["body_html"] == "Fallback desc"

    def test_seo_title_truncated_to_70_chars(self):
        long_title = "A" * 100
        product = make_product(seo_title=long_title)
        payload = self._build(product)
        assert len(payload["product"]["metafields_global_title_tag"]) == 70

    def test_seo_description_truncated_to_320_chars(self):
        long_desc = "B" * 400
        product = make_product(seo_description=long_desc)
        payload = self._build(product)
        assert len(payload["product"]["metafields_global_description_tag"]) == 320

    def test_print_to_order_variant_inventory_quantity_zero(self):
        variants = [make_variant(size="S", fulfilment_type="print_to_order", units_in_stock=99)]
        product = make_product(variants=variants)
        payload = self._build(product)
        assert payload["product"]["variants"][0]["inventory_quantity"] == 0

    def test_stock_variant_uses_actual_stock(self):
        variants = [make_variant(size="S", fulfilment_type="stock", units_in_stock=42)]
        product = make_product(variants=variants)
        payload = self._build(product)
        assert payload["product"]["variants"][0]["inventory_quantity"] == 42

    def test_variant_sku_falls_back_to_product_sku_and_size(self):
        variants = [make_variant(size="M", sku=None)]
        product = make_product(sku="PROD-001", variants=variants)
        payload = self._build(product)
        assert payload["product"]["variants"][0]["sku"] == "PROD-001-M"


# ---------------------------------------------------------------------------
# ShopifySyncService._base_url and _headers (simple helpers)
# ---------------------------------------------------------------------------


class TestShopifyHelpers:
    def test_base_url_format(self):
        svc = SimpleNamespace()
        url = ShopifySyncService._base_url(svc, "mystore.myshopify.com")
        assert url == "https://mystore.myshopify.com/admin/api/2024-01"

    def test_headers_contain_token(self):
        svc = SimpleNamespace()
        headers = ShopifySyncService._headers(svc, "mytoken123")
        assert headers["X-Shopify-Access-Token"] == "mytoken123"
        assert headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# EtsySyncService._build_etsy_listing_data
# ---------------------------------------------------------------------------


class TestEtsyBuildListingData:
    def _build(self, product):
        return EtsySyncService._build_etsy_listing_data(etsy_service(), product)

    def test_title_uses_feature_title(self):
        product = make_product(feature_title="The Dragon", name="Dragon")
        data = self._build(product)
        assert data["title"] == "The Dragon"

    def test_title_falls_back_to_name(self):
        product = make_product(feature_title=None, name="Dragon")
        data = self._build(product)
        assert data["title"] == "Dragon"

    def test_price_from_etsy_channel_preferred(self):
        shopify_p = make_pricing(10.00, platform_type="shopify")
        etsy_p = make_pricing(12.00, platform_type="etsy")
        product = make_product(pricing=[shopify_p, etsy_p])
        data = self._build(product)
        assert data["price"] == 12.0

    def test_price_falls_back_to_any_active_pricing(self):
        shopify_p = make_pricing(9.99, platform_type="shopify")
        product = make_product(pricing=[shopify_p])
        data = self._build(product)
        assert data["price"] == 9.99

    def test_price_none_when_no_pricing(self):
        product = make_product(pricing=[])
        data = self._build(product)
        assert data["price"] is None

    def test_description_includes_shop_description(self):
        product = make_product(shop_description="Shop only text")
        data = self._build(product)
        assert "Shop only text" in data["description"]

    def test_description_includes_backstory(self):
        product = make_product(description="Desc", backstory="A long story")
        data = self._build(product)
        assert "A long story" in data["description"]

    def test_weight_spec_appended(self):
        product = make_product(weight_grams=150, description="Test")
        data = self._build(product)
        assert "Weight: 150g" in data["description"]

    def test_primary_image_selected(self):
        images = [
            make_image("https://example.com/secondary.jpg", is_primary=False),
            make_image("https://example.com/primary.jpg", is_primary=True),
        ]
        product = make_product(images=images)
        data = self._build(product)
        assert data["primary_image_url"] == "https://example.com/primary.jpg"

    def test_first_image_fallback_when_no_primary(self):
        images = [
            make_image("https://example.com/first.jpg", is_primary=False),
            make_image("https://example.com/second.jpg", is_primary=False),
        ]
        product = make_product(images=images)
        data = self._build(product)
        assert data["primary_image_url"] == "https://example.com/first.jpg"

    def test_primary_image_none_when_no_images(self):
        product = make_product(images=[])
        data = self._build(product)
        assert data["primary_image_url"] is None

    def test_made_to_order_when_print_to_order(self):
        product = make_product(print_to_order=True)
        data = self._build(product)
        assert data["when_made"] == "made_to_order"

    def test_not_made_to_order_when_stock(self):
        product = make_product(print_to_order=False)
        data = self._build(product)
        assert data["when_made"] == "2020_2025"

    def test_variants_included(self):
        variants = [make_variant(size="S", is_active=True, display_order=0)]
        pricing = [make_pricing(10.00)]
        product = make_product(variants=variants, pricing=pricing)
        data = self._build(product)
        assert len(data["variants"]) == 1
        assert data["variants"][0]["size"] == "S"

    def test_variant_size_property_uses_etsy_size_id(self):
        variants = [make_variant(size="M", is_active=True, display_order=0)]
        product = make_product(variants=variants)
        data = self._build(product)
        prop = data["variants"][0]["property_values"][0]
        assert prop["property_id"] == 100  # ETSY_SIZE_PROPERTY_ID
        assert prop["property_name"] == "Size"

    def test_inactive_variants_excluded(self):
        variants = [
            make_variant(size="S", is_active=True, display_order=0),
            make_variant(size="XL", is_active=False, display_order=1),
        ]
        product = make_product(variants=variants)
        data = self._build(product)
        sizes = [v["size"] for v in data["variants"]]
        assert "XL" not in sizes

    def test_is_supply_always_false(self):
        product = make_product()
        data = self._build(product)
        assert data["is_supply"] is False

    def test_who_made_always_i_did(self):
        product = make_product()
        data = self._build(product)
        assert data["who_made"] == "i_did"
