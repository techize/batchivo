"""
Tests for payment processing Pydantic schemas.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.payment import (
    CartItem,
    CustomerDetails,
    PaymentError,
    PaymentRequest,
    PaymentResponse,
    ShippingAddress,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestShippingAddress:
    def _valid(self, **kwargs) -> dict:
        defaults = {
            "first_name": "Jane",
            "last_name": "Doe",
            "address_line1": "123 Main Street",
            "city": "London",
            "postcode": "SW1A 1AA",
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        a = ShippingAddress(**self._valid())
        assert a.country == "GB"
        assert a.address_line2 is None
        assert a.county is None

    def test_full_address(self):
        a = ShippingAddress(
            **self._valid(
                address_line2="Flat 2",
                county="Greater London",
                country="GB",
            )
        )
        assert a.address_line2 == "Flat 2"
        assert a.county == "Greater London"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            ShippingAddress(first_name="Jane", last_name="Doe")


class TestCustomerDetails:
    def test_valid_minimal(self):
        c = CustomerDetails(email="jane@example.com")
        assert c.email == "jane@example.com"
        assert c.phone is None

    def test_with_phone(self):
        c = CustomerDetails(email="jane@example.com", phone="+44 7700 900000")
        assert c.phone == "+44 7700 900000"

    def test_email_required(self):
        with pytest.raises(ValidationError):
            CustomerDetails()


class TestCartItem:
    def test_valid(self):
        item = CartItem(product_id=uuid4(), name="Dragon Mini", quantity=2, price=1299)
        assert item.quantity == 2
        assert item.price == 1299

    def test_quantity_minimum_1(self):
        with pytest.raises(ValidationError):
            CartItem(product_id=uuid4(), name="Test", quantity=0, price=100)

    def test_price_zero_accepted(self):
        item = CartItem(product_id=uuid4(), name="Free Item", quantity=1, price=0)
        assert item.price == 0

    def test_price_negative_raises(self):
        with pytest.raises(ValidationError):
            CartItem(product_id=uuid4(), name="Test", quantity=1, price=-1)


class TestPaymentRequest:
    def _shipping_address(self) -> ShippingAddress:
        return ShippingAddress(
            first_name="Jane",
            last_name="Doe",
            address_line1="123 Main St",
            city="London",
            postcode="SW1A 1AA",
        )

    def _customer(self) -> CustomerDetails:
        return CustomerDetails(email="jane@example.com")

    def _cart_item(self) -> CartItem:
        return CartItem(product_id=uuid4(), name="Dragon Mini", quantity=1, price=1299)

    def _valid(self, **kwargs) -> dict:
        defaults = {
            "payment_token": "tok_sandbox_abc123",
            "amount": 1499,
            "customer": self._customer(),
            "shipping_address": self._shipping_address(),
            "shipping_method": "royal-mail-2nd",
            "shipping_cost": 199,
            "items": [self._cart_item()],
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        r = PaymentRequest(**self._valid())
        assert r.currency == "GBP"
        assert r.idempotency_key is None

    def test_amount_minimum_1(self):
        with pytest.raises(ValidationError):
            PaymentRequest(**self._valid(amount=0))

    def test_shipping_cost_zero_accepted(self):
        r = PaymentRequest(**self._valid(shipping_cost=0))
        assert r.shipping_cost == 0

    def test_shipping_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            PaymentRequest(**self._valid(shipping_cost=-1))

    def test_currency_pattern(self):
        r = PaymentRequest(**self._valid(currency="USD"))
        assert r.currency == "USD"

    def test_invalid_currency_raises(self):
        with pytest.raises(ValidationError):
            PaymentRequest(**self._valid(currency="usd"))

    def test_with_idempotency_key(self):
        r = PaymentRequest(**self._valid(idempotency_key="unique-key-001"))
        assert r.idempotency_key == "unique-key-001"

    def test_empty_items_accepted(self):
        r = PaymentRequest(**self._valid(items=[]))
        assert r.items == []


class TestPaymentResponse:
    def test_valid(self):
        r = PaymentResponse(
            success=True,
            order_id="MYS-20251231-001",
            payment_id="sq-pay-abc123",
            amount=1499,
            currency="GBP",
            status="COMPLETED",
            created_at=_now(),
        )
        assert r.success is True
        assert r.receipt_url is None

    def test_with_receipt_url(self):
        r = PaymentResponse(
            success=True,
            order_id="MYS-001",
            payment_id="sq-abc",
            amount=999,
            currency="GBP",
            status="COMPLETED",
            receipt_url="https://squareup.com/receipt/abc",
            created_at=_now(),
        )
        assert r.receipt_url == "https://squareup.com/receipt/abc"


class TestPaymentError:
    def test_valid(self):
        e = PaymentError(error_code="CARD_DECLINED", error_message="Card was declined")
        assert e.success is False
        assert e.detail is None

    def test_with_detail(self):
        e = PaymentError(
            error_code="GENERIC_DECLINE",
            error_message="Payment failed",
            detail="Insufficient funds",
        )
        assert e.detail == "Insufficient funds"
