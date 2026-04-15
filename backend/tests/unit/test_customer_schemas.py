"""
Tests for customer account Pydantic schemas.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.customer import (
    CustomerAddressCreate,
    CustomerAddressListResponse,
    CustomerAddressUpdate,
    CustomerChangePassword,
    CustomerForgotPassword,
    CustomerLogin,
    CustomerOrderItemResponse,
    CustomerOrderListResponse,
    CustomerOrderResponse,
    CustomerRefreshToken,
    CustomerRegister,
    CustomerResetPassword,
    CustomerUpdate,
    CustomerVerifyEmail,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestCustomerRegister:
    def test_valid_minimal(self):
        r = CustomerRegister(
            email="user@example.com",
            password="password1",
            full_name="Jane Doe",
        )
        assert r.email == "user@example.com"
        assert r.marketing_consent is False
        assert r.phone is None

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            CustomerRegister(email="not-an-email", password="password1", full_name="Jane")

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            CustomerRegister(email="j@example.com", password="short", full_name="Jane")

    def test_password_exactly_8_accepted(self):
        r = CustomerRegister(email="j@example.com", password="12345678", full_name="Jane")
        assert len(r.password) == 8

    def test_full_name_required(self):
        with pytest.raises(ValidationError):
            CustomerRegister(email="j@example.com", password="password1")

    def test_full_name_empty_raises(self):
        with pytest.raises(ValidationError):
            CustomerRegister(email="j@example.com", password="password1", full_name="")

    def test_full_name_max_255(self):
        r = CustomerRegister(email="j@example.com", password="password1", full_name="J" * 255)
        assert len(r.full_name) == 255

    def test_full_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            CustomerRegister(email="j@example.com", password="password1", full_name="J" * 256)

    def test_phone_optional(self):
        r = CustomerRegister(
            email="j@example.com",
            password="password1",
            full_name="Jane",
            phone="+44 7700 900000",
        )
        assert r.phone == "+44 7700 900000"

    def test_phone_max_50(self):
        r = CustomerRegister(
            email="j@example.com", password="password1", full_name="Jane", phone="1" * 50
        )
        assert len(r.phone) == 50

    def test_phone_too_long_raises(self):
        with pytest.raises(ValidationError):
            CustomerRegister(
                email="j@example.com", password="password1", full_name="Jane", phone="1" * 51
            )

    def test_marketing_consent_true(self):
        r = CustomerRegister(
            email="j@example.com",
            password="password1",
            full_name="Jane",
            marketing_consent=True,
        )
        assert r.marketing_consent is True


class TestCustomerLogin:
    def test_valid(self):
        login = CustomerLogin(email="user@example.com", password="anypass")
        assert login.email == "user@example.com"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            CustomerLogin(email="not-valid", password="pass")


class TestCustomerRefreshToken:
    def test_valid(self):
        r = CustomerRefreshToken(refresh_token="tok123")
        assert r.refresh_token == "tok123"

    def test_required(self):
        with pytest.raises(ValidationError):
            CustomerRefreshToken()


class TestCustomerForgotPassword:
    def test_valid(self):
        r = CustomerForgotPassword(email="user@example.com")
        assert r.email == "user@example.com"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            CustomerForgotPassword(email="bad")


class TestCustomerResetPassword:
    def test_valid(self):
        r = CustomerResetPassword(token="reset-token", password="newpass1")
        assert r.token == "reset-token"

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            CustomerResetPassword(token="tok", password="short")

    def test_password_exactly_8_accepted(self):
        r = CustomerResetPassword(token="tok", password="12345678")
        assert len(r.password) == 8


class TestCustomerChangePassword:
    def test_valid(self):
        r = CustomerChangePassword(current_password="oldpass1", new_password="newpass1")
        assert r.current_password == "oldpass1"

    def test_new_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            CustomerChangePassword(current_password="old", new_password="short")


class TestCustomerVerifyEmail:
    def test_valid(self):
        r = CustomerVerifyEmail(token="verification-token")
        assert r.token == "verification-token"

    def test_required(self):
        with pytest.raises(ValidationError):
            CustomerVerifyEmail()


class TestCustomerUpdate:
    def test_all_optional(self):
        u = CustomerUpdate()
        assert u.full_name is None
        assert u.phone is None
        assert u.marketing_consent is None

    def test_partial_update(self):
        u = CustomerUpdate(full_name="New Name", marketing_consent=True)
        assert u.full_name == "New Name"
        assert u.marketing_consent is True

    def test_full_name_empty_raises(self):
        with pytest.raises(ValidationError):
            CustomerUpdate(full_name="")

    def test_phone_max_50(self):
        u = CustomerUpdate(phone="1" * 50)
        assert len(u.phone) == 50

    def test_phone_too_long_raises(self):
        with pytest.raises(ValidationError):
            CustomerUpdate(phone="1" * 51)


class TestCustomerAddressCreate:
    def _valid(self, **kwargs) -> dict:
        defaults = {
            "recipient_name": "Jane Doe",
            "line1": "123 Main Street",
            "city": "London",
            "postcode": "SW1A 1AA",
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        a = CustomerAddressCreate(**self._valid())
        assert a.label == "Home"
        assert a.country == "United Kingdom"
        assert a.is_default is False

    def test_custom_label(self):
        a = CustomerAddressCreate(**self._valid(label="Work"))
        assert a.label == "Work"

    def test_label_max_50(self):
        a = CustomerAddressCreate(**self._valid(label="L" * 50))
        assert len(a.label) == 50

    def test_label_too_long_raises(self):
        with pytest.raises(ValidationError):
            CustomerAddressCreate(**self._valid(label="L" * 51))

    def test_recipient_name_max_255(self):
        a = CustomerAddressCreate(**self._valid(recipient_name="N" * 255))
        assert len(a.recipient_name) == 255

    def test_recipient_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            CustomerAddressCreate(**self._valid(recipient_name="N" * 256))

    def test_line1_max_255(self):
        a = CustomerAddressCreate(**self._valid(line1="L" * 255))
        assert len(a.line1) == 255

    def test_line1_too_long_raises(self):
        with pytest.raises(ValidationError):
            CustomerAddressCreate(**self._valid(line1="L" * 256))

    def test_postcode_max_20(self):
        a = CustomerAddressCreate(**self._valid(postcode="P" * 20))
        assert len(a.postcode) == 20

    def test_postcode_too_long_raises(self):
        with pytest.raises(ValidationError):
            CustomerAddressCreate(**self._valid(postcode="P" * 21))

    def test_city_max_100(self):
        a = CustomerAddressCreate(**self._valid(city="C" * 100))
        assert len(a.city) == 100

    def test_city_too_long_raises(self):
        with pytest.raises(ValidationError):
            CustomerAddressCreate(**self._valid(city="C" * 101))

    def test_optional_fields(self):
        a = CustomerAddressCreate(
            **self._valid(
                line2="Flat 2",
                county="Greater London",
                phone="07700900000",
                country="Germany",
                is_default=True,
            )
        )
        assert a.line2 == "Flat 2"
        assert a.country == "Germany"
        assert a.is_default is True


class TestCustomerAddressUpdate:
    def test_all_optional(self):
        u = CustomerAddressUpdate()
        assert u.label is None
        assert u.line1 is None
        assert u.postcode is None

    def test_partial_update(self):
        u = CustomerAddressUpdate(city="Manchester", is_default=True)
        assert u.city == "Manchester"
        assert u.is_default is True


class TestCustomerAddressListResponse:
    def test_empty(self):
        r = CustomerAddressListResponse(items=[], total=0)
        assert r.total == 0


class TestCustomerOrderItemResponse:
    def test_valid(self):
        item = CustomerOrderItemResponse(
            product_sku="DRG-001",
            product_name="Dragon Mini",
            quantity=2,
            unit_price=12.99,
            total_price=25.98,
        )
        assert item.product_sku == "DRG-001"
        assert item.total_price == 25.98


class TestCustomerOrderResponse:
    def _base(self, **kwargs) -> dict:
        now = _now()
        defaults = {
            "id": uuid4(),
            "order_number": "MYS-0001",
            "status": "confirmed",
            "subtotal": 25.98,
            "shipping_cost": 3.99,
            "discount_amount": 0.0,
            "total": 29.97,
            "currency": "GBP",
            "shipping_method": "Standard",
            "tracking_number": None,
            "tracking_url": None,
            "created_at": now,
            "shipped_at": None,
            "delivered_at": None,
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        r = CustomerOrderResponse(**self._base())
        assert r.order_number == "MYS-0001"
        assert r.tracking_number is None
        assert r.items == []

    def test_with_tracking(self):
        r = CustomerOrderResponse(
            **self._base(
                tracking_number="JD000001234",
                tracking_url="https://track.example.com/JD000001234",
                shipped_at=_now(),
            )
        )
        assert r.tracking_number == "JD000001234"


class TestCustomerOrderListResponse:
    def test_empty(self):
        r = CustomerOrderListResponse(items=[], total=0, skip=0, limit=10)
        assert r.total == 0
        assert r.skip == 0
        assert r.limit == 10
