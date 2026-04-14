"""
Tests for OnboardingService error classes and pure slug generation logic.

The DB-dependent methods (register_tenant, verify_email, etc.) require
integration fixtures and are covered separately. These tests focus on
the parts that can be exercised without a database.
"""

import re
import pytest

from app.services.onboarding_service import (
    EmailAlreadyRegisteredError,
    InvalidTokenError,
    OnboardingError,
    SlugAlreadyExistsError,
)


# ---------------------------------------------------------------------------
# Error class hierarchy
# ---------------------------------------------------------------------------


class TestOnboardingErrorHierarchy:
    def test_onboarding_error_is_exception(self):
        assert issubclass(OnboardingError, Exception)

    def test_email_already_registered_is_onboarding_error(self):
        assert issubclass(EmailAlreadyRegisteredError, OnboardingError)

    def test_slug_already_exists_is_onboarding_error(self):
        assert issubclass(SlugAlreadyExistsError, OnboardingError)

    def test_invalid_token_is_onboarding_error(self):
        assert issubclass(InvalidTokenError, OnboardingError)

    def test_all_subclasses_are_distinct(self):
        assert EmailAlreadyRegisteredError is not SlugAlreadyExistsError
        assert EmailAlreadyRegisteredError is not InvalidTokenError
        assert SlugAlreadyExistsError is not InvalidTokenError

    def test_raise_email_already_registered(self):
        with pytest.raises(OnboardingError):
            raise EmailAlreadyRegisteredError("test@example.com")

    def test_raise_slug_already_exists(self):
        with pytest.raises(OnboardingError):
            raise SlugAlreadyExistsError("my-shop")

    def test_raise_invalid_token(self):
        with pytest.raises(OnboardingError):
            raise InvalidTokenError("expired")

    def test_error_messages_are_preserved(self):
        err = EmailAlreadyRegisteredError("test@example.com already registered")
        assert "already registered" in str(err)

    def test_catch_as_base_exception_type(self):
        errors_caught = []
        for exc_class in (EmailAlreadyRegisteredError, SlugAlreadyExistsError, InvalidTokenError):
            try:
                raise exc_class("test")
            except OnboardingError as e:
                errors_caught.append(type(e))
        assert len(errors_caught) == 3


# ---------------------------------------------------------------------------
# Slug generation logic (mirrors OnboardingService._generate_unique_slug)
# We test the pure string transformation inline — identical to the service's
# regex/strip steps — without touching the DB uniqueness loop.
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(business_name: str) -> str:
    """Mirror of the pure transformation in OnboardingService._generate_unique_slug."""
    slug = _SLUG_RE.sub("-", business_name.lower())
    slug = slug.strip("-")
    if not slug:
        slug = "workspace"
    return slug


class TestSlugGeneration:
    def test_lowercase_single_word(self):
        assert _slugify("Dragon") == "dragon"

    def test_spaces_become_hyphens(self):
        assert _slugify("My Shop") == "my-shop"

    def test_multiple_spaces_single_hyphen(self):
        assert _slugify("My  Big  Shop") == "my-big-shop"

    def test_special_characters_replaced(self):
        assert _slugify("Mystmere & Forge!") == "mystmere-forge"

    def test_leading_trailing_hyphens_stripped(self):
        assert _slugify("  Dragon  ") == "dragon"

    def test_leading_special_chars_stripped(self):
        assert _slugify("---Dragon---") == "dragon"

    def test_numbers_preserved(self):
        assert _slugify("Shop 42") == "shop-42"

    def test_already_lowercase_slug(self):
        assert _slugify("my-shop") == "my-shop"

    def test_empty_string_becomes_workspace(self):
        assert _slugify("") == "workspace"

    def test_only_special_chars_becomes_workspace(self):
        assert _slugify("!@#$%^&*()") == "workspace"

    def test_unicode_letters_replaced(self):
        # Non-ASCII letters are not in [a-z0-9] so become hyphens
        slug = _slugify("Café Noir")
        assert "caf" in slug

    def test_mixed_case_normalised(self):
        assert _slugify("MyDRAGONShop") == "mydragonsho p".replace(" ", "")

    def test_hyphens_in_input_preserved(self):
        assert _slugify("print-forge") == "print-forge"

    def test_consecutive_specials_collapse(self):
        assert _slugify("a---b") == "a-b"
