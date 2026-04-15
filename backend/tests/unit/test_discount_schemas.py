"""
Tests for Discount Code Pydantic schemas.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.discount import DiscountType
from app.schemas.discount import (
    DiscountCodeBase,
    DiscountCodeCreate,
    DiscountCodeUpdate,
    DiscountValidationRequest,
)

VALID_FROM = datetime(2026, 1, 1, tzinfo=timezone.utc)


def base_discount(**kwargs) -> dict:
    defaults = {
        "code": "SUMMER20",
        "name": "Summer Sale 20%",
        "discount_type": DiscountType.PERCENTAGE,
        "amount": Decimal("20.00"),
        "valid_from": VALID_FROM,
    }
    defaults.update(kwargs)
    return defaults


class TestDiscountCodeBase:
    def test_valid_percentage_discount(self):
        d = DiscountCodeBase(**base_discount())
        assert d.code == "SUMMER20"
        assert d.discount_type == DiscountType.PERCENTAGE

    def test_code_uppercased(self):
        d = DiscountCodeBase(**base_discount(code="summer20"))
        assert d.code == "SUMMER20"

    def test_code_stripped(self):
        d = DiscountCodeBase(**base_discount(code="  SALE  "))
        assert d.code == "SALE"

    def test_code_empty_raises(self):
        with pytest.raises(ValidationError):
            DiscountCodeBase(**base_discount(code=""))

    def test_code_too_long_raises(self):
        with pytest.raises(ValidationError):
            DiscountCodeBase(**base_discount(code="X" * 51))

    def test_code_max_50(self):
        d = DiscountCodeBase(**base_discount(code="X" * 50))
        assert len(d.code) == 50

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            DiscountCodeBase(**base_discount(name=""))

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            DiscountCodeBase(**base_discount(name="N" * 256))

    def test_amount_zero_raises(self):
        with pytest.raises(ValidationError):
            DiscountCodeBase(**base_discount(amount=Decimal("0")))

    def test_amount_negative_raises(self):
        with pytest.raises(ValidationError):
            DiscountCodeBase(**base_discount(amount=Decimal("-5")))

    def test_amount_positive(self):
        d = DiscountCodeBase(**base_discount(amount=Decimal("15.50")))
        assert d.amount == Decimal("15.50")

    def test_is_active_defaults_true(self):
        d = DiscountCodeBase(**base_discount())
        assert d.is_active is True

    def test_optional_fields_none_by_default(self):
        d = DiscountCodeBase(**base_discount())
        assert d.description is None
        assert d.min_order_amount is None
        assert d.max_discount_amount is None
        assert d.max_uses is None
        assert d.max_uses_per_customer is None
        assert d.valid_to is None

    def test_min_order_amount_zero_accepted(self):
        d = DiscountCodeBase(**base_discount(min_order_amount=Decimal("0")))
        assert d.min_order_amount == Decimal("0")

    def test_min_order_amount_negative_raises(self):
        with pytest.raises(ValidationError):
            DiscountCodeBase(**base_discount(min_order_amount=Decimal("-1")))

    def test_max_discount_amount_zero_accepted(self):
        d = DiscountCodeBase(**base_discount(max_discount_amount=Decimal("0")))
        assert d.max_discount_amount == Decimal("0")

    def test_max_uses_zero_raises(self):
        with pytest.raises(ValidationError):
            DiscountCodeBase(**base_discount(max_uses=0))

    def test_max_uses_positive(self):
        d = DiscountCodeBase(**base_discount(max_uses=100))
        assert d.max_uses == 100

    def test_max_uses_per_customer_zero_raises(self):
        with pytest.raises(ValidationError):
            DiscountCodeBase(**base_discount(max_uses_per_customer=0))

    def test_max_uses_per_customer_positive(self):
        d = DiscountCodeBase(**base_discount(max_uses_per_customer=3))
        assert d.max_uses_per_customer == 3

    def test_fixed_amount_type(self):
        d = DiscountCodeBase(
            **base_discount(discount_type=DiscountType.FIXED_AMOUNT, amount=Decimal("5.00"))
        )
        assert d.discount_type == DiscountType.FIXED_AMOUNT


class TestDiscountCodeCreate:
    def test_inherits_from_base(self):
        d = DiscountCodeCreate(**base_discount())
        assert d.code == "SUMMER20"


class TestDiscountCodeUpdate:
    def test_all_none_by_default(self):
        u = DiscountCodeUpdate()
        assert u.name is None
        assert u.amount is None
        assert u.is_active is None

    def test_partial_update(self):
        u = DiscountCodeUpdate(is_active=False)
        assert u.is_active is False
        assert u.name is None

    def test_amount_zero_raises(self):
        with pytest.raises(ValidationError):
            DiscountCodeUpdate(amount=Decimal("0"))

    def test_max_uses_zero_raises(self):
        with pytest.raises(ValidationError):
            DiscountCodeUpdate(max_uses=0)


class TestDiscountValidationRequest:
    def test_code_uppercased(self):
        req = DiscountValidationRequest(code="summer10", subtotal=Decimal("50.00"))
        assert req.code == "SUMMER10"

    def test_code_stripped(self):
        req = DiscountValidationRequest(code="  SALE  ", subtotal=Decimal("50.00"))
        assert req.code == "SALE"

    def test_subtotal_zero_accepted(self):
        req = DiscountValidationRequest(code="FREE", subtotal=Decimal("0"))
        assert req.subtotal == Decimal("0")

    def test_subtotal_negative_raises(self):
        with pytest.raises(ValidationError):
            DiscountValidationRequest(code="PROMO", subtotal=Decimal("-1"))

    def test_customer_email_optional(self):
        req = DiscountValidationRequest(code="PROMO", subtotal=Decimal("10"))
        assert req.customer_email is None

    def test_customer_email_provided(self):
        req = DiscountValidationRequest(
            code="PROMO",
            subtotal=Decimal("10"),
            customer_email="test@example.com",
        )
        assert req.customer_email == "test@example.com"
