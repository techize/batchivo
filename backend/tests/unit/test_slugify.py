"""Unit tests for the slugify utility function and slug-generating schema validators.

The same slugify implementation exists in page.py, category.py, and designer.py.
We test all three and the schema validators that call them.
"""

import pytest

from app.schemas.category import CategoryCreate, slugify as category_slugify
from app.schemas.designer import DesignerCreate, slugify as designer_slugify
from app.schemas.page import PageCreate, slugify as page_slugify


# ---------------------------------------------------------------------------
# slugify — shared behaviour (same impl in all three modules)
# ---------------------------------------------------------------------------


class TestSlugify:
    @pytest.mark.parametrize("slugify_fn", [page_slugify, category_slugify, designer_slugify])
    def test_lowercases_input(self, slugify_fn):
        assert slugify_fn("Hello World") == "hello-world"

    @pytest.mark.parametrize("slugify_fn", [page_slugify, category_slugify, designer_slugify])
    def test_replaces_spaces_with_hyphens(self, slugify_fn):
        assert slugify_fn("my page title") == "my-page-title"

    @pytest.mark.parametrize("slugify_fn", [page_slugify, category_slugify, designer_slugify])
    def test_strips_leading_trailing_whitespace(self, slugify_fn):
        assert slugify_fn("  trimmed  ") == "trimmed"

    @pytest.mark.parametrize("slugify_fn", [page_slugify, category_slugify, designer_slugify])
    def test_removes_special_characters(self, slugify_fn):
        assert slugify_fn("Hello! World?") == "hello-world"

    @pytest.mark.parametrize("slugify_fn", [page_slugify, category_slugify, designer_slugify])
    def test_collapses_multiple_hyphens(self, slugify_fn):
        assert slugify_fn("hello---world") == "hello-world"

    @pytest.mark.parametrize("slugify_fn", [page_slugify, category_slugify, designer_slugify])
    def test_strips_leading_trailing_hyphens(self, slugify_fn):
        assert slugify_fn("-hello-") == "hello"

    @pytest.mark.parametrize("slugify_fn", [page_slugify, category_slugify, designer_slugify])
    def test_already_valid_slug_unchanged(self, slugify_fn):
        assert slugify_fn("already-a-slug") == "already-a-slug"

    @pytest.mark.parametrize("slugify_fn", [page_slugify, category_slugify, designer_slugify])
    def test_underscores_replaced_with_hyphens(self, slugify_fn):
        assert slugify_fn("snake_case_name") == "snake-case-name"

    @pytest.mark.parametrize("slugify_fn", [page_slugify, category_slugify, designer_slugify])
    def test_numbers_preserved(self, slugify_fn):
        assert slugify_fn("page 42") == "page-42"

    @pytest.mark.parametrize("slugify_fn", [page_slugify, category_slugify, designer_slugify])
    def test_single_word(self, slugify_fn):
        assert slugify_fn("Dragons") == "dragons"


# ---------------------------------------------------------------------------
# CategoryCreate — slug auto-generated from name
# ---------------------------------------------------------------------------


class TestCategoryCreateSlug:
    def _make(self, **kwargs):
        base = dict(name="My Category", is_active=True)
        return CategoryCreate(**{**base, **kwargs})

    def test_no_slug_provided_returns_none(self):
        # Auto-generation from name happens in the API endpoint, not the schema
        cat = self._make(name="My Category")
        assert cat.slug is None

    def test_explicit_slug_is_slugified(self):
        cat = self._make(slug="Custom Slug!")
        assert cat.slug == "custom-slug"

    def test_already_valid_slug_unchanged(self):
        cat = self._make(slug="my-category")
        assert cat.slug == "my-category"


# ---------------------------------------------------------------------------
# PageCreate — slug auto-generated if not provided, slugified if provided
# ---------------------------------------------------------------------------


class TestPageCreateSlug:
    def _make(self, **kwargs):
        from app.schemas.page import PageType

        base = dict(title="My Page", page_type=PageType.POLICY)
        return PageCreate(**{**base, **kwargs})

    def test_slug_passthrough_when_already_valid(self):
        page = self._make(slug="returns-policy")
        assert page.slug == "returns-policy"

    def test_slug_slugified_when_provided_with_spaces(self):
        page = self._make(slug="Returns Policy")
        assert page.slug == "returns-policy"

    def test_none_slug_stays_none(self):
        page = self._make(slug=None)
        assert page.slug is None


# ---------------------------------------------------------------------------
# DesignerCreate — slug auto-generated from name if not provided
# ---------------------------------------------------------------------------


class TestDesignerCreateSlug:
    def _make(self, **kwargs):
        base = dict(name="Cool Designer", membership_cost=0)
        return DesignerCreate(**{**base, **kwargs})

    def test_no_slug_provided_returns_none(self):
        # Auto-generation from name happens in the API endpoint, not the schema
        d = self._make(name="Cool Designer")
        assert d.slug is None

    def test_explicit_slug_is_slugified(self):
        d = self._make(slug="My Designer!")
        assert d.slug == "my-designer"

    def test_none_slug_returns_none(self):
        d = self._make(slug=None)
        assert d.slug is None
