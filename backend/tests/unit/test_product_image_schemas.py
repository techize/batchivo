"""
Tests for ProductImage Pydantic schemas.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.product_image import (
    ImportImageFromUrlRequest,
    ProductImageBase,
    ProductImageCreate,
    ProductImageListResponse,
    ProductImageResponse,
    ProductImageUpdate,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestProductImageBase:
    def test_defaults(self):
        img = ProductImageBase()
        assert img.alt_text == ""

    def test_alt_text_provided(self):
        img = ProductImageBase(alt_text="A red dragon model")
        assert img.alt_text == "A red dragon model"

    def test_alt_text_max_255(self):
        img = ProductImageBase(alt_text="A" * 255)
        assert len(img.alt_text) == 255

    def test_alt_text_too_long_raises(self):
        with pytest.raises(ValidationError):
            ProductImageBase(alt_text="A" * 256)


class TestProductImageCreate:
    def test_inherits_base_defaults(self):
        img = ProductImageCreate()
        assert img.alt_text == ""

    def test_with_alt_text(self):
        img = ProductImageCreate(alt_text="Front view")
        assert img.alt_text == "Front view"


class TestProductImageUpdate:
    def test_all_optional(self):
        u = ProductImageUpdate()
        assert u.alt_text is None
        assert u.display_order is None

    def test_alt_text_update(self):
        u = ProductImageUpdate(alt_text="New alt text")
        assert u.alt_text == "New alt text"

    def test_display_order_zero(self):
        u = ProductImageUpdate(display_order=0)
        assert u.display_order == 0

    def test_display_order_negative_raises(self):
        with pytest.raises(ValidationError):
            ProductImageUpdate(display_order=-1)

    def test_alt_text_max_255(self):
        u = ProductImageUpdate(alt_text="A" * 255)
        assert len(u.alt_text) == 255

    def test_alt_text_too_long_raises(self):
        with pytest.raises(ValidationError):
            ProductImageUpdate(alt_text="A" * 256)


class TestProductImageResponse:
    def _base(self, **kwargs) -> dict:
        now = _now()
        defaults = {
            "id": uuid4(),
            "product_id": uuid4(),
            "image_url": "https://cdn.example.com/image.jpg",
            "display_order": 0,
            "is_primary": False,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        r = ProductImageResponse(**self._base())
        assert r.thumbnail_url is None
        assert r.original_filename is None
        assert r.file_size is None
        assert r.content_type is None

    def test_primary_image(self):
        r = ProductImageResponse(**self._base(is_primary=True, display_order=0))
        assert r.is_primary is True

    def test_with_all_fields(self):
        r = ProductImageResponse(
            **self._base(
                thumbnail_url="https://cdn.example.com/thumb.jpg",
                original_filename="photo.jpg",
                file_size=204800,
                content_type="image/jpeg",
            )
        )
        assert r.thumbnail_url == "https://cdn.example.com/thumb.jpg"
        assert r.file_size == 204800
        assert r.content_type == "image/jpeg"


class TestProductImageListResponse:
    def test_empty(self):
        r = ProductImageListResponse(images=[], total=0)
        assert r.total == 0

    def test_with_total(self):
        r = ProductImageListResponse(images=[], total=5)
        assert r.total == 5


class TestImportImageFromUrlRequest:
    def test_valid_minimal(self):
        r = ImportImageFromUrlRequest(url="https://example.com/img.jpg")
        assert r.url == "https://example.com/img.jpg"
        assert r.alt_text == ""
        assert r.is_primary is False

    def test_url_required(self):
        with pytest.raises(ValidationError):
            ImportImageFromUrlRequest()

    def test_with_alt_text_and_primary(self):
        r = ImportImageFromUrlRequest(
            url="https://example.com/img.jpg",
            alt_text="Dragon mini",
            is_primary=True,
        )
        assert r.alt_text == "Dragon mini"
        assert r.is_primary is True

    def test_alt_text_max_255(self):
        r = ImportImageFromUrlRequest(url="https://x.com/i.jpg", alt_text="A" * 255)
        assert len(r.alt_text) == 255

    def test_alt_text_too_long_raises(self):
        with pytest.raises(ValidationError):
            ImportImageFromUrlRequest(url="https://x.com/i.jpg", alt_text="A" * 256)
