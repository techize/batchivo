"""
Tests for category Pydantic schemas and the slugify utility.
"""

import pytest
from pydantic import ValidationError

from app.schemas.category import CategoryBase, CategoryCreate, CategoryUpdate, slugify


class TestSlugify:
    def test_basic_lowercase(self):
        assert slugify("Dragons") == "dragons"

    def test_spaces_to_hyphens(self):
        assert slugify("My Category") == "my-category"

    def test_multiple_spaces_collapsed(self):
        assert slugify("a  b") == "a-b"

    def test_underscores_to_hyphens(self):
        assert slugify("my_category") == "my-category"

    def test_leading_trailing_stripped(self):
        assert slugify("  dragons  ") == "dragons"

    def test_leading_trailing_hyphens_stripped(self):
        assert slugify("-dragons-") == "dragons"

    def test_special_chars_removed(self):
        assert slugify("Cats & Dogs!") == "cats-dogs"

    def test_numbers_preserved(self):
        assert slugify("Category 1") == "category-1"

    def test_consecutive_separators_collapsed(self):
        # multiple spaces, underscore, hyphen → single hyphen
        assert slugify("a _ b - c") == "a-b-c"

    def test_already_slug(self):
        assert slugify("already-slug") == "already-slug"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_only_special_chars(self):
        assert slugify("!@#") == ""


class TestCategoryBase:
    def test_valid_minimal(self):
        c = CategoryBase(name="Dragons")
        assert c.name == "Dragons"
        assert c.display_order == 0
        assert c.is_active is True

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            CategoryBase(name="")

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            CategoryBase(name="N" * 101)

    def test_name_max_100(self):
        c = CategoryBase(name="N" * 100)
        assert len(c.name) == 100

    def test_display_order_negative_raises(self):
        with pytest.raises(ValidationError):
            CategoryBase(name="Test", display_order=-1)

    def test_display_order_zero_accepted(self):
        c = CategoryBase(name="Test", display_order=0)
        assert c.display_order == 0

    def test_description_optional(self):
        c = CategoryBase(name="Test")
        assert c.description is None

    def test_is_active_default_true(self):
        c = CategoryBase(name="Test")
        assert c.is_active is True

    def test_is_active_false(self):
        c = CategoryBase(name="Test", is_active=False)
        assert c.is_active is False


class TestCategoryCreate:
    def test_slug_none_passes_through(self):
        c = CategoryCreate(name="Dragons")
        assert c.slug is None

    def test_slug_auto_slugified(self):
        c = CategoryCreate(name="Dragons", slug="My Category!")
        # The validator slugifies whatever value is passed
        assert c.slug == "my-category"

    def test_slug_too_long_raises(self):
        with pytest.raises(ValidationError):
            CategoryCreate(name="Test", slug="s" * 101)

    def test_slug_min_length_empty_raises(self):
        # min_length=1 on slug field; empty string raises
        with pytest.raises(ValidationError):
            CategoryCreate(name="Test", slug="")


class TestCategoryUpdate:
    def test_all_optional(self):
        u = CategoryUpdate()
        assert u.name is None
        assert u.slug is None
        assert u.is_active is None

    def test_partial_update(self):
        u = CategoryUpdate(is_active=False)
        assert u.is_active is False
        assert u.name is None

    def test_slug_slugified_when_provided(self):
        u = CategoryUpdate(slug="My Updated Slug!")
        assert u.slug == "my-updated-slug"

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            CategoryUpdate(name="")

    def test_display_order_negative_raises(self):
        with pytest.raises(ValidationError):
            CategoryUpdate(display_order=-5)
