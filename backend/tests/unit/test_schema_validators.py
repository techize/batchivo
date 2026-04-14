"""Unit tests for Pydantic schema field validators.

Tests validate_password (TenantRegistrationRequest),
discount code validators, and printer connection IP validation.
All tests exercise pure validation logic with no DB interaction.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.onboarding import TenantRegistrationRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def valid_registration(**overrides) -> dict:
    """Return a valid registration payload."""
    base = dict(
        email="user@example.com",
        password="Passw0rd",
        full_name="Test User",
        business_name="My Business",
    )
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# TenantRegistrationRequest.validate_password
# ---------------------------------------------------------------------------


class TestTenantRegistrationPasswordValidator:
    def test_valid_password_accepted(self):
        req = TenantRegistrationRequest(**valid_registration(password="Secure1!"))
        assert req.password == "Secure1!"

    def test_too_short_raises(self):
        with pytest.raises(ValidationError, match="least 8 characters"):
            TenantRegistrationRequest(**valid_registration(password="Ab1"))

    def test_no_uppercase_raises(self):
        with pytest.raises(ValidationError, match="uppercase"):
            TenantRegistrationRequest(**valid_registration(password="passw0rd"))

    def test_no_lowercase_raises(self):
        with pytest.raises(ValidationError, match="lowercase"):
            TenantRegistrationRequest(**valid_registration(password="PASSW0RD"))

    def test_no_digit_raises(self):
        with pytest.raises(ValidationError, match="digit"):
            TenantRegistrationRequest(**valid_registration(password="Password"))

    def test_exactly_8_chars_with_all_requirements_accepted(self):
        req = TenantRegistrationRequest(**valid_registration(password="Passw0rd"))
        assert req.password == "Passw0rd"

    def test_special_chars_accepted(self):
        req = TenantRegistrationRequest(**valid_registration(password="P@ssw0rd!"))
        assert req.password == "P@ssw0rd!"

    def test_long_password_accepted(self):
        pwd = "Longpassword123secure"
        req = TenantRegistrationRequest(**valid_registration(password=pwd))
        assert req.password == pwd


# ---------------------------------------------------------------------------
# TenantRegistrationRequest — other field constraints
# ---------------------------------------------------------------------------


class TestTenantRegistrationFieldConstraints:
    def test_business_name_too_short_raises(self):
        with pytest.raises(ValidationError):
            TenantRegistrationRequest(**valid_registration(business_name="X"))

    def test_business_name_min_length_accepted(self):
        req = TenantRegistrationRequest(**valid_registration(business_name="AB"))
        assert req.business_name == "AB"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            TenantRegistrationRequest(**valid_registration(email="not-an-email"))

    def test_full_name_empty_raises(self):
        with pytest.raises(ValidationError):
            TenantRegistrationRequest(**valid_registration(full_name=""))


# ---------------------------------------------------------------------------
# Discount code validators (uppercase + positive amount)
# ---------------------------------------------------------------------------


class TestDiscountCodeValidators:
    """Tests for DiscountCodeBase field validators."""

    def _make_discount(self, **overrides):
        from app.schemas.discount import DiscountCodeCreate
        from app.models.discount import DiscountType

        base = dict(
            code="sale10",
            name="10% Sale",
            discount_type=DiscountType.PERCENTAGE,
            amount=Decimal("10.00"),
            valid_from=datetime.now(timezone.utc),
        )
        return DiscountCodeCreate(**{**base, **overrides})

    def test_code_is_uppercased(self):
        d = self._make_discount(code="summer10")
        assert d.code == "SUMMER10"

    def test_code_is_stripped_and_uppercased(self):
        d = self._make_discount(code="  promo20  ")
        assert d.code == "PROMO20"

    def test_already_uppercase_unchanged(self):
        d = self._make_discount(code="WINTER")
        assert d.code == "WINTER"

    def test_zero_amount_raises(self):
        from app.schemas.discount import DiscountCodeCreate
        from app.models.discount import DiscountType

        with pytest.raises(ValidationError):
            DiscountCodeCreate(
                code="BAD",
                name="Bad",
                discount_type=DiscountType.PERCENTAGE,
                amount=Decimal("0"),
                valid_from=datetime.now(timezone.utc),
            )

    def test_negative_amount_raises(self):
        from app.schemas.discount import DiscountCodeCreate
        from app.models.discount import DiscountType

        with pytest.raises(ValidationError):
            DiscountCodeCreate(
                code="NEG",
                name="Negative",
                discount_type=DiscountType.FIXED_AMOUNT,
                amount=Decimal("-5.00"),
                valid_from=datetime.now(timezone.utc),
            )

    def test_positive_amount_accepted(self):
        d = self._make_discount(amount=Decimal("0.01"))
        assert d.amount == Decimal("0.01")


# ---------------------------------------------------------------------------
# PrinterConnectionBase IP address validator
# ---------------------------------------------------------------------------


class TestPrinterConnectionIpValidator:
    """Tests for the validate_ip_address field validator."""

    def _make_connection(self, **overrides):
        from app.schemas.printer_connection import PrinterConnectionCreate
        from app.models.printer_connection import ConnectionType

        base = dict(
            connection_type=ConnectionType.MOONRAKER,
            name="Test Printer",
            ip_address=None,
        )
        return PrinterConnectionCreate(**{**base, **overrides})

    def test_none_ip_accepted(self):
        conn = self._make_connection(ip_address=None)
        assert conn.ip_address is None

    def test_valid_ipv4_accepted(self):
        conn = self._make_connection(ip_address="192.168.1.100")
        assert conn.ip_address == "192.168.1.100"

    def test_localhost_accepted(self):
        conn = self._make_connection(ip_address="127.0.0.1")
        assert conn.ip_address == "127.0.0.1"

    def test_boundary_octets_accepted(self):
        conn = self._make_connection(ip_address="0.0.0.0")
        assert conn.ip_address == "0.0.0.0"

    def test_max_octets_accepted(self):
        conn = self._make_connection(ip_address="255.255.255.255")
        assert conn.ip_address == "255.255.255.255"

    def test_hostname_passthrough(self):
        # Hostnames are allowed to pass through the validator
        conn = self._make_connection(ip_address="printer.local")
        assert conn.ip_address == "printer.local"


# ---------------------------------------------------------------------------
# PrinterConnectionResponse — access_code and cloud_token masking
# ---------------------------------------------------------------------------


class TestPrinterConnectionResponseMasking:
    """Tests for sensitive field masking validators in response schema."""

    def _make_response(self, **overrides):
        import uuid
        from datetime import datetime, timezone
        from app.schemas.printer_connection import PrinterConnectionResponse
        from app.models.printer_connection import ConnectionType

        base = dict(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            printer_id=uuid.uuid4(),
            connection_type=ConnectionType.MOONRAKER,
            name="Test",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return PrinterConnectionResponse(**{**base, **overrides})

    def test_access_code_masked(self):
        resp = self._make_response(access_code="mysecretcode")
        assert resp.access_code == "****code"

    def test_access_code_short_fully_masked(self):
        resp = self._make_response(access_code="ab")
        assert resp.access_code == "****"

    def test_access_code_none_stays_none(self):
        resp = self._make_response(access_code=None)
        assert resp.access_code is None

    def test_cloud_token_masked_to_stars(self):
        resp = self._make_response(cloud_token="very-long-secret-token")
        assert resp.cloud_token == "****"

    def test_cloud_token_none_stays_none(self):
        resp = self._make_response(cloud_token=None)
        assert resp.cloud_token is None
