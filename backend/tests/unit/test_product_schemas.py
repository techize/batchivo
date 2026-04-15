"""
Tests for Product Pydantic schemas.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.product_variant import FulfilmentType
from app.schemas.product import (
    ExternalListingBrief,
    ProductBase,
    ProductCategoryBrief,
    ProductCostBreakdown,
    ProductCreate,
    ProductListResponse,
    ProductModelBase,
    ProductModelCreate,
    ProductPricingBase,
    ProductPricingCreate,
    ProductPricingUpdate,
    ProductUpdate,
    ProductVariantBase,
    ProductVariantCreate,
    ProductVariantUpdate,
)


class TestFulfilmentType:
    def test_values(self):
        assert FulfilmentType.STOCK == "stock"
        assert FulfilmentType.PRINT_TO_ORDER == "print_to_order"


class TestProductModelBase:
    def test_defaults(self):
        m = ProductModelBase(model_id=uuid4())
        assert m.quantity == 1

    def test_quantity_zero_raises(self):
        with pytest.raises(ValidationError):
            ProductModelBase(model_id=uuid4(), quantity=0)

    def test_quantity_positive(self):
        m = ProductModelBase(model_id=uuid4(), quantity=4)
        assert m.quantity == 4


class TestProductModelCreate:
    def test_inherits_base(self):
        m = ProductModelCreate(model_id=uuid4())
        assert m.quantity == 1


class TestProductPricingBase:
    def test_valid(self):
        p = ProductPricingBase(sales_channel_id=uuid4(), list_price=Decimal("12.99"))
        assert p.is_active is True

    def test_list_price_zero_accepted(self):
        p = ProductPricingBase(sales_channel_id=uuid4(), list_price=Decimal("0"))
        assert p.list_price == Decimal("0")

    def test_list_price_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductPricingBase(sales_channel_id=uuid4(), list_price=Decimal("-0.01"))


class TestProductPricingCreate:
    def test_valid(self):
        c = ProductPricingCreate(sales_channel_id=uuid4(), list_price=Decimal("9.99"))
        assert c.is_active is True


class TestProductPricingUpdate:
    def test_all_optional(self):
        u = ProductPricingUpdate()
        assert u.list_price is None
        assert u.is_active is None

    def test_price_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductPricingUpdate(list_price=Decimal("-1"))


class TestProductCostBreakdown:
    def test_valid(self):
        c = ProductCostBreakdown(
            models_cost=Decimal("5.00"),
            packaging_cost=Decimal("0.50"),
            assembly_cost=Decimal("2.00"),
            total_make_cost=Decimal("7.50"),
        )
        assert c.total_make_cost == Decimal("7.50")
        assert c.child_products_cost == Decimal("0")
        assert c.models_with_actual_cost == 0
        assert c.models_total == 0


class TestProductBase:
    def _valid(self, **kwargs) -> dict:
        defaults = {"sku": "DRG-001", "name": "Dragon Mini"}
        defaults.update(kwargs)
        return defaults

    def test_defaults(self):
        p = ProductBase(**self._valid())
        assert p.units_in_stock == 0
        assert p.low_stock_threshold == 5
        assert p.packaging_cost == Decimal("0")
        assert p.packaging_quantity == 1
        assert p.assembly_minutes == 0
        assert p.is_active is True
        assert p.shop_visible is False
        assert p.is_featured is False
        assert p.tags == []
        assert p.colour_options == []

    def test_sku_empty_raises(self):
        with pytest.raises(ValidationError):
            ProductBase(sku="", name="Test")

    def test_sku_max_100(self):
        p = ProductBase(sku="S" * 100, name="Test")
        assert len(p.sku) == 100

    def test_sku_too_long_raises(self):
        with pytest.raises(ValidationError):
            ProductBase(sku="S" * 101, name="Test")

    def test_name_max_200(self):
        p = ProductBase(sku="DRG", name="N" * 200)
        assert len(p.name) == 200

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            ProductBase(sku="DRG", name="N" * 201)

    def test_units_in_stock_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductBase(**self._valid(units_in_stock=-1))

    def test_packaging_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductBase(**self._valid(packaging_cost=Decimal("-0.01")))

    def test_packaging_quantity_minimum_1(self):
        with pytest.raises(ValidationError):
            ProductBase(**self._valid(packaging_quantity=0))

    def test_assembly_minutes_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductBase(**self._valid(assembly_minutes=-1))

    def test_feature_title_max_100(self):
        p = ProductBase(**self._valid(feature_title="T" * 100))
        assert len(p.feature_title) == 100

    def test_feature_title_too_long_raises(self):
        with pytest.raises(ValidationError):
            ProductBase(**self._valid(feature_title="T" * 101))

    def test_seo_slug_max_200(self):
        p = ProductBase(**self._valid(seo_slug="s" * 200))
        assert len(p.seo_slug) == 200

    def test_seo_slug_too_long_raises(self):
        with pytest.raises(ValidationError):
            ProductBase(**self._valid(seo_slug="s" * 201))

    def test_weight_grams_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductBase(**self._valid(weight_grams=-1))

    def test_size_cm_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductBase(**self._valid(size_cm=Decimal("-0.1")))

    def test_print_time_hours_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductBase(**self._valid(print_time_hours=Decimal("-1")))

    def test_with_all_shop_fields(self):
        p = ProductBase(
            **self._valid(
                shop_visible=True,
                is_featured=True,
                is_dragon=True,
                free_shipping=True,
                print_to_order=True,
                tags=["dragon", "miniature"],
                colour_options=["White", "Black"],
            )
        )
        assert p.shop_visible is True
        assert p.tags == ["dragon", "miniature"]


class TestProductCreate:
    def test_minimal(self):
        p = ProductCreate(sku="DRG-001", name="Dragon Mini")
        assert p.models == []
        assert p.child_products == []


class TestProductUpdate:
    def test_all_optional(self):
        u = ProductUpdate()
        assert u.sku is None
        assert u.name is None
        assert u.shop_visible is None

    def test_sku_empty_raises(self):
        with pytest.raises(ValidationError):
            ProductUpdate(sku="")

    def test_partial_update(self):
        u = ProductUpdate(shop_visible=True, units_in_stock=5)
        assert u.shop_visible is True
        assert u.units_in_stock == 5

    def test_packaging_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductUpdate(packaging_cost=Decimal("-1"))


class TestProductCategoryBrief:
    def test_valid(self):
        c = ProductCategoryBrief(id=uuid4(), name="Dragons", slug="dragons")
        assert c.slug == "dragons"


class TestExternalListingBrief:
    def test_valid(self):
        b = ExternalListingBrief(
            id=uuid4(),
            platform="etsy",
            external_id="etsy-123",
            sync_status="synced",
        )
        assert b.external_url is None
        assert b.last_synced_at is None


class TestProductListResponse:
    def test_empty(self):
        r = ProductListResponse(products=[], total=0, skip=0, limit=20)
        assert r.total == 0

    def test_paginated(self):
        r = ProductListResponse(products=[], total=50, skip=20, limit=20)
        assert r.skip == 20


class TestProductVariantBase:
    def _valid(self, **kwargs) -> dict:
        defaults = {"size": "Medium"}
        defaults.update(kwargs)
        return defaults

    def test_defaults(self):
        v = ProductVariantBase(**self._valid())
        assert v.display_order == 0
        assert v.price_adjustment_pence == 0
        assert v.units_in_stock == 0
        assert v.fulfilment_type == FulfilmentType.STOCK
        assert v.is_active is True

    def test_size_empty_raises(self):
        with pytest.raises(ValidationError):
            ProductVariantBase(size="")

    def test_size_max_50(self):
        v = ProductVariantBase(size="S" * 50)
        assert len(v.size) == 50

    def test_size_too_long_raises(self):
        with pytest.raises(ValidationError):
            ProductVariantBase(size="S" * 51)

    def test_display_order_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductVariantBase(**self._valid(display_order=-1))

    def test_units_in_stock_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductVariantBase(**self._valid(units_in_stock=-1))

    def test_lead_time_days_minimum_1(self):
        with pytest.raises(ValidationError):
            ProductVariantBase(**self._valid(lead_time_days=0))

    def test_material_cost_pence_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductVariantBase(**self._valid(material_cost_pence=-1))

    def test_print_time_hours_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductVariantBase(**self._valid(print_time_hours=Decimal("-0.1")))

    def test_print_to_order_type(self):
        v = ProductVariantBase(
            size="Large",
            fulfilment_type=FulfilmentType.PRINT_TO_ORDER,
            lead_time_days=3,
        )
        assert v.fulfilment_type == FulfilmentType.PRINT_TO_ORDER


class TestProductVariantCreate:
    def test_inherits_base_defaults(self):
        v = ProductVariantCreate(size="Small")
        assert v.fulfilment_type == FulfilmentType.STOCK


class TestProductVariantUpdate:
    def test_all_optional(self):
        u = ProductVariantUpdate()
        assert u.size is None
        assert u.is_active is None

    def test_size_empty_raises(self):
        with pytest.raises(ValidationError):
            ProductVariantUpdate(size="")

    def test_partial_update(self):
        u = ProductVariantUpdate(price_adjustment_pence=200, is_active=False)
        assert u.price_adjustment_pence == 200
        assert u.is_active is False

    def test_units_in_stock_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductVariantUpdate(units_in_stock=-1)
