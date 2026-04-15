"""
Tests for licensed designer Pydantic schemas and the slugify utility.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.designer import DesignerBase, DesignerCreate, DesignerUpdate, slugify


class TestSlugify:
    """designer.slugify is identical to category.slugify — tested here for coverage."""

    def test_basic(self):
        assert slugify("PrintyJay") == "printyjay"

    def test_spaces(self):
        assert slugify("Cinder Wings") == "cinder-wings"

    def test_special_chars_removed(self):
        assert slugify("Forge & Fire!") == "forge-fire"

    def test_trailing_hyphens(self):
        assert slugify("-designer-") == "designer"

    def test_empty(self):
        assert slugify("") == ""


class TestDesignerBase:
    def test_valid_minimal(self):
        d = DesignerBase(name="PrintyJay")
        assert d.name == "PrintyJay"
        assert d.is_active is True
        assert d.description is None

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            DesignerBase(name="")

    def test_name_max_100(self):
        d = DesignerBase(name="D" * 100)
        assert len(d.name) == 100

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            DesignerBase(name="D" * 101)

    def test_logo_url_max_500(self):
        d = DesignerBase(name="Test", logo_url="https://x.com/" + "a" * 480)
        assert d.logo_url is not None

    def test_logo_url_too_long_raises(self):
        with pytest.raises(ValidationError):
            DesignerBase(name="Test", logo_url="u" * 501)

    def test_website_url_too_long_raises(self):
        with pytest.raises(ValidationError):
            DesignerBase(name="Test", website_url="u" * 501)

    def test_social_links_dict(self):
        d = DesignerBase(
            name="Test",
            social_links={"instagram": "https://instagram.com/test"},
        )
        assert d.social_links["instagram"].startswith("https")

    def test_is_active_false(self):
        d = DesignerBase(name="Retired", is_active=False)
        assert d.is_active is False


class TestDesignerCreate:
    def test_slug_auto_slugified(self):
        d = DesignerCreate(name="Cinder Wings", slug="Cinder Wings!")
        assert d.slug == "cinder-wings"

    def test_slug_none_passes_through(self):
        d = DesignerCreate(name="Cinder Wings")
        assert d.slug is None

    def test_membership_cost_zero_accepted(self):
        d = DesignerCreate(name="Test", membership_cost=Decimal("0"))
        assert d.membership_cost == Decimal("0")

    def test_membership_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            DesignerCreate(name="Test", membership_cost=Decimal("-1"))

    def test_membership_cost_positive(self):
        d = DesignerCreate(name="Test", membership_cost=Decimal("9.99"))
        assert d.membership_cost == Decimal("9.99")

    def test_slug_too_long_raises(self):
        with pytest.raises(ValidationError):
            DesignerCreate(name="Test", slug="s" * 101)


class TestDesignerUpdate:
    def test_all_optional(self):
        u = DesignerUpdate()
        assert u.name is None
        assert u.is_active is None

    def test_partial_update(self):
        u = DesignerUpdate(is_active=False, name="Updated Name")
        assert u.is_active is False
        assert u.name == "Updated Name"

    def test_slug_slugified_when_provided(self):
        u = DesignerUpdate(slug="New Slug!")
        assert u.slug == "new-slug"

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            DesignerUpdate(name="")

    def test_membership_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            DesignerUpdate(membership_cost=Decimal("-0.01"))
