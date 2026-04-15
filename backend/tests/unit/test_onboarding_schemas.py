"""
Tests for tenant onboarding Pydantic schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.onboarding import (
    EmailVerificationRequest,
    ResendVerificationRequest,
    TenantRegistrationRequest,
    TenantRegistrationResponse,
)
from app.schemas.tenant_settings import TenantType


def valid_reg(**kwargs) -> dict:
    defaults = {
        "email": "owner@example.com",
        "password": "SecurePass1",
        "full_name": "Jane Smith",
        "business_name": "Dragon Forge",
    }
    defaults.update(kwargs)
    return defaults


class TestTenantRegistrationRequest:
    def test_valid_minimal(self):
        r = TenantRegistrationRequest(**valid_reg())
        assert r.email == "owner@example.com"
        assert r.tenant_type == TenantType.GENERIC

    # --- Email ---
    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            TenantRegistrationRequest(**valid_reg(email="not-an-email"))

    # --- Password length ---
    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            TenantRegistrationRequest(**valid_reg(password="Ab1"))

    def test_password_exactly_8_chars_valid(self):
        r = TenantRegistrationRequest(**valid_reg(password="Abcdef1!"))
        assert len(r.password) == 8

    def test_password_too_long_raises(self):
        with pytest.raises(ValidationError):
            TenantRegistrationRequest(**valid_reg(password="A" * 129))

    # --- Password strength ---
    def test_password_no_uppercase_raises(self):
        with pytest.raises(ValidationError, match="uppercase"):
            TenantRegistrationRequest(**valid_reg(password="nouppercase1"))

    def test_password_no_lowercase_raises(self):
        with pytest.raises(ValidationError, match="lowercase"):
            TenantRegistrationRequest(**valid_reg(password="NOLOWERCASE1"))

    def test_password_no_digit_raises(self):
        with pytest.raises(ValidationError, match="digit"):
            TenantRegistrationRequest(**valid_reg(password="NoDigitHere"))

    def test_strong_password_accepted(self):
        r = TenantRegistrationRequest(**valid_reg(password="GoodPass99!"))
        assert r.password == "GoodPass99!"

    # --- Full name ---
    def test_full_name_empty_raises(self):
        with pytest.raises(ValidationError):
            TenantRegistrationRequest(**valid_reg(full_name=""))

    def test_full_name_max_255(self):
        r = TenantRegistrationRequest(**valid_reg(full_name="A" * 255))
        assert len(r.full_name) == 255

    def test_full_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            TenantRegistrationRequest(**valid_reg(full_name="A" * 256))

    # --- Business name ---
    def test_business_name_too_short_raises(self):
        with pytest.raises(ValidationError):
            TenantRegistrationRequest(**valid_reg(business_name="A"))

    def test_business_name_exactly_2_chars(self):
        r = TenantRegistrationRequest(**valid_reg(business_name="AB"))
        assert r.business_name == "AB"

    def test_business_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            TenantRegistrationRequest(**valid_reg(business_name="B" * 101))

    def test_business_name_max_100(self):
        r = TenantRegistrationRequest(**valid_reg(business_name="B" * 100))
        assert len(r.business_name) == 100

    # --- Tenant type ---
    def test_default_tenant_type_is_generic(self):
        r = TenantRegistrationRequest(**valid_reg())
        assert r.tenant_type == TenantType.GENERIC

    def test_custom_tenant_type(self):
        r = TenantRegistrationRequest(**valid_reg(tenant_type=TenantType.THREE_D_PRINT))
        assert r.tenant_type == TenantType.THREE_D_PRINT


class TestTenantRegistrationResponse:
    def test_default_message(self):
        r = TenantRegistrationResponse(email="owner@example.com")
        assert "verify your account" in r.message

    def test_custom_message(self):
        r = TenantRegistrationResponse(email="owner@example.com", message="Done!")
        assert r.message == "Done!"

    def test_email_preserved(self):
        r = TenantRegistrationResponse(email="shop@example.com")
        assert r.email == "shop@example.com"


class TestEmailVerificationRequest:
    def test_valid_token(self):
        r = EmailVerificationRequest(token="abc123xyz")
        assert r.token == "abc123xyz"

    def test_empty_token_raises(self):
        with pytest.raises(ValidationError):
            EmailVerificationRequest(token="")


class TestResendVerificationRequest:
    def test_valid_email(self):
        r = ResendVerificationRequest(email="user@example.com")
        assert r.email == "user@example.com"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            ResendVerificationRequest(email="not-an-email")
