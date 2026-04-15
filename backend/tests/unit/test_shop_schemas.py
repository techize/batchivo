"""
Tests for Shop (public storefront) Pydantic schemas.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.shop import (
    ShopCategoryListResponse,
    ShopCategoryResponse,
    ShopCategorySummary,
    ShopProductDetail,
    ShopProductFilters,
    ShopProductImageResponse,
    ShopProductListResponse,
    ShopProductSummary,
)


class TestShopProductImageResponse:
    def test_defaults(self):
        img = ShopProductImageResponse(id=uuid4(), url="https://cdn.example.com/img.jpg")
        assert img.alt == ""
        assert img.is_primary is False
        assert img.order == 0
        assert img.thumbnail_url is None

    def test_primary_image(self):
        img = ShopProductImageResponse(
            id=uuid4(),
            url="https://cdn.example.com/img.jpg",
            thumbnail_url="https://cdn.example.com/thumb.jpg",
            alt="Dragon miniature",
            is_primary=True,
            order=0,
        )
        assert img.is_primary is True
        assert img.alt == "Dragon miniature"


class TestShopProductSummary:
    def _valid(self, **kwargs) -> dict:
        defaults = {
            "id": uuid4(),
            "sku": "DRG-001",
            "name": "Dragon Mini",
            "price": Decimal("12.99"),
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        p = ShopProductSummary(**self._valid())
        assert p.is_sold is False
        assert p.is_featured is False
        assert p.free_shipping is False
        assert p.category_slugs == []
        assert p.primary_image_url is None

    def test_with_images_and_categories(self):
        p = ShopProductSummary(
            **self._valid(
                primary_image_url="https://cdn.example.com/img.jpg",
                primary_image_thumbnail="https://cdn.example.com/thumb.jpg",
                is_sold=True,
                is_featured=True,
                free_shipping=True,
                category_slugs=["dragons", "miniatures"],
            )
        )
        assert p.is_sold is True
        assert p.category_slugs == ["dragons", "miniatures"]


class TestShopProductDetail:
    def _valid(self, **kwargs) -> dict:
        defaults = {
            "id": uuid4(),
            "sku": "DRG-002",
            "name": "Fire Drake",
            "price": Decimal("24.99"),
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        p = ShopProductDetail(**self._valid())
        assert p.shop_description is None
        assert p.description is None
        assert p.images == []
        assert p.categories == []
        assert p.related_products == []

    def test_with_details(self):
        p = ShopProductDetail(
            **self._valid(
                shop_description="<p>A fierce fire drake</p>",
                feature_title="Ignarath the Destroyer",
                backstory="Forged in the depths of Mount Doom...",
            )
        )
        assert p.feature_title == "Ignarath the Destroyer"
        assert p.backstory is not None


class TestShopCategorySummary:
    def test_valid(self):
        c = ShopCategorySummary(id=uuid4(), name="Dragons", slug="dragons")
        assert c.name == "Dragons"
        assert c.slug == "dragons"


class TestShopCategoryResponse:
    def test_valid_minimal(self):
        c = ShopCategoryResponse(id=uuid4(), name="Miniatures", slug="miniatures")
        assert c.product_count == 0
        assert c.display_order == 0
        assert c.description is None
        assert c.image_url is None

    def test_with_all_fields(self):
        c = ShopCategoryResponse(
            id=uuid4(),
            name="Dragons",
            slug="dragons",
            description="All our dragon miniatures",
            image_url="https://cdn.example.com/dragons.jpg",
            product_count=15,
            display_order=1,
        )
        assert c.product_count == 15
        assert c.display_order == 1


class TestShopProductListResponse:
    def test_empty(self):
        r = ShopProductListResponse(data=[], total=0)
        assert r.total == 0
        assert r.page == 1
        assert r.limit == 24
        assert r.has_more is False

    def test_paginated(self):
        r = ShopProductListResponse(data=[], total=100, page=2, limit=24, has_more=True)
        assert r.has_more is True
        assert r.page == 2


class TestShopCategoryListResponse:
    def test_empty(self):
        r = ShopCategoryListResponse(data=[], total=0)
        assert r.total == 0


class TestShopProductFilters:
    def test_defaults(self):
        f = ShopProductFilters()
        assert f.category is None
        assert f.sort == "newest"
        assert f.page == 1
        assert f.limit == 24
        assert f.include_sold is True

    def test_custom_filters(self):
        f = ShopProductFilters(category="dragons", sort="price_asc", page=2, limit=12)
        assert f.category == "dragons"
        assert f.limit == 12

    def test_page_minimum_1(self):
        with pytest.raises(ValidationError):
            ShopProductFilters(page=0)

    def test_limit_minimum_1(self):
        with pytest.raises(ValidationError):
            ShopProductFilters(limit=0)

    def test_limit_maximum_100(self):
        f = ShopProductFilters(limit=100)
        assert f.limit == 100

    def test_limit_above_max_raises(self):
        with pytest.raises(ValidationError):
            ShopProductFilters(limit=101)
