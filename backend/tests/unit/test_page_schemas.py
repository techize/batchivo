"""
Tests for content page Pydantic schemas and the slugify utility.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.page import PageType
from app.schemas.page import (
    PageBase,
    PageCreate,
    PageListResponse,
    PagePublicResponse,
    PageUpdate,
    slugify,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestSlugify:
    def test_lowercase(self):
        assert slugify("Hello World") == "hello-world"

    def test_spaces_to_hyphens(self):
        assert slugify("privacy policy") == "privacy-policy"

    def test_special_chars_removed(self):
        assert slugify("Terms & Conditions!") == "terms-conditions"

    def test_underscores_to_hyphens(self):
        assert slugify("about_us") == "about-us"

    def test_trailing_hyphens_stripped(self):
        assert slugify("-terms-") == "terms"

    def test_empty(self):
        assert slugify("") == ""

    def test_numbers_preserved(self):
        assert slugify("Policy 2025") == "policy-2025"


class TestPageBase:
    def test_valid_minimal(self):
        p = PageBase(title="Privacy Policy")
        assert p.title == "Privacy Policy"
        assert p.content == ""
        assert p.page_type == PageType.POLICY
        assert p.is_published is False
        assert p.sort_order == 0

    def test_title_empty_raises(self):
        with pytest.raises(ValidationError):
            PageBase(title="")

    def test_title_max_200(self):
        p = PageBase(title="T" * 200)
        assert len(p.title) == 200

    def test_title_too_long_raises(self):
        with pytest.raises(ValidationError):
            PageBase(title="T" * 201)

    def test_meta_description_max_300(self):
        p = PageBase(title="Test", meta_description="M" * 300)
        assert len(p.meta_description) == 300

    def test_meta_description_too_long_raises(self):
        with pytest.raises(ValidationError):
            PageBase(title="Test", meta_description="M" * 301)

    def test_sort_order_zero_accepted(self):
        p = PageBase(title="Test", sort_order=0)
        assert p.sort_order == 0

    def test_sort_order_negative_raises(self):
        with pytest.raises(ValidationError):
            PageBase(title="Test", sort_order=-1)

    def test_page_type_info(self):
        p = PageBase(title="Shipping Info", page_type=PageType.INFO)
        assert p.page_type == PageType.INFO

    def test_page_type_legal(self):
        p = PageBase(title="Legal Notice", page_type=PageType.LEGAL)
        assert p.page_type == PageType.LEGAL

    def test_is_published_true(self):
        p = PageBase(title="Test", is_published=True)
        assert p.is_published is True


class TestPageCreate:
    def test_slug_auto_slugified(self):
        p = PageCreate(title="Privacy Policy", slug="Privacy Policy!")
        assert p.slug == "privacy-policy"

    def test_slug_none_passes_through(self):
        p = PageCreate(title="Privacy Policy")
        assert p.slug is None

    def test_slug_max_100(self):
        p = PageCreate(title="Test", slug="s" * 100)
        assert len(p.slug) == 100

    def test_slug_too_long_raises(self):
        with pytest.raises(ValidationError):
            PageCreate(title="Test", slug="s" * 101)

    def test_inherits_page_base_defaults(self):
        p = PageCreate(title="About Us")
        assert p.page_type == PageType.POLICY
        assert p.is_published is False


class TestPageUpdate:
    def test_all_optional(self):
        u = PageUpdate()
        assert u.title is None
        assert u.slug is None
        assert u.content is None
        assert u.page_type is None
        assert u.is_published is None

    def test_partial_update(self):
        u = PageUpdate(title="New Title", is_published=True)
        assert u.title == "New Title"
        assert u.is_published is True

    def test_slug_slugified_when_provided(self):
        u = PageUpdate(slug="New Slug With Spaces!")
        assert u.slug == "new-slug-with-spaces"

    def test_title_empty_raises(self):
        with pytest.raises(ValidationError):
            PageUpdate(title="")

    def test_meta_description_too_long_raises(self):
        with pytest.raises(ValidationError):
            PageUpdate(meta_description="M" * 301)

    def test_sort_order_negative_raises(self):
        with pytest.raises(ValidationError):
            PageUpdate(sort_order=-1)

    def test_sort_order_zero_accepted(self):
        u = PageUpdate(sort_order=0)
        assert u.sort_order == 0


class TestPageListResponse:
    def test_valid(self):
        r = PageListResponse(pages=[], total=0)
        assert r.total == 0
        assert r.pages == []

    def test_total_non_zero(self):
        r = PageListResponse(pages=[], total=42)
        assert r.total == 42


class TestPagePublicResponse:
    def test_valid_minimal(self):
        p = PagePublicResponse(
            slug="privacy-policy",
            title="Privacy Policy",
            content="Our privacy policy...",
            updated_at=_now(),
        )
        assert p.slug == "privacy-policy"
        assert p.meta_description is None

    def test_with_meta_description(self):
        p = PagePublicResponse(
            slug="about",
            title="About Us",
            content="About our shop.",
            meta_description="We make great things.",
            updated_at=_now(),
        )
        assert p.meta_description == "We make great things."
