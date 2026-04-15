"""
Tests for shipping rate Pydantic schemas.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.shipping import (
    PostcodeValidationResponse,
    ShippingOption,
    ShippingRateRequest,
    ShippingRatesResponse,
)


class TestShippingOption:
    def _valid(self, **kwargs) -> dict:
        defaults = {
            "id": "royal-mail-2nd",
            "name": "Royal Mail 2nd Class",
            "carrier": "Royal Mail",
            "description": "2nd Class Letter/Large Letter",
            "price_pence": 199,
            "estimated_days_min": 2,
            "estimated_days_max": 3,
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        o = ShippingOption(**self._valid())
        assert o.id == "royal-mail-2nd"
        assert o.is_tracked is False
        assert o.is_signed is False

    def test_price_pounds_property(self):
        o = ShippingOption(**self._valid(price_pence=399))
        assert o.price_pounds == Decimal("3.99")

    def test_price_pounds_zero(self):
        o = ShippingOption(**self._valid(price_pence=0))
        assert o.price_pounds == Decimal("0")

    def test_estimated_days_display_range(self):
        o = ShippingOption(**self._valid(estimated_days_min=2, estimated_days_max=3))
        assert o.estimated_days_display == "2-3 days"

    def test_estimated_days_display_single(self):
        o = ShippingOption(**self._valid(estimated_days_min=1, estimated_days_max=1))
        assert o.estimated_days_display == "1 day"

    def test_estimated_days_display_plural_same(self):
        o = ShippingOption(**self._valid(estimated_days_min=3, estimated_days_max=3))
        assert o.estimated_days_display == "3 days"

    def test_tracked_and_signed(self):
        o = ShippingOption(**self._valid(is_tracked=True, is_signed=True))
        assert o.is_tracked is True
        assert o.is_signed is True


class TestShippingRateRequest:
    def test_valid_minimal(self):
        r = ShippingRateRequest(postcode="SW1A 1AA")
        assert r.postcode == "SW1A 1AA"
        assert r.weight_grams is None
        assert r.cart_total_pence is None

    def test_with_weight_and_cart_total(self):
        r = ShippingRateRequest(
            postcode="EC1A 1BB",
            weight_grams=500,
            cart_total_pence=2500,
        )
        assert r.weight_grams == 500
        assert r.cart_total_pence == 2500

    def test_postcode_required(self):
        with pytest.raises(ValidationError):
            ShippingRateRequest()


class TestShippingRatesResponse:
    def _option(self) -> ShippingOption:
        return ShippingOption(
            id="std",
            name="Standard",
            carrier="Royal Mail",
            description="Standard delivery",
            price_pence=299,
            estimated_days_min=3,
            estimated_days_max=5,
        )

    def test_valid_minimal(self):
        r = ShippingRatesResponse(options=[], postcode_valid=True)
        assert r.qualifies_for_free_shipping is False
        assert r.free_shipping_threshold_pence is None

    def test_with_options(self):
        r = ShippingRatesResponse(
            options=[self._option()],
            postcode_valid=True,
            free_shipping_threshold_pence=5000,
            qualifies_for_free_shipping=True,
        )
        assert len(r.options) == 1
        assert r.free_shipping_threshold_pence == 5000
        assert r.qualifies_for_free_shipping is True

    def test_invalid_postcode(self):
        r = ShippingRatesResponse(options=[], postcode_valid=False)
        assert r.postcode_valid is False


class TestPostcodeValidationResponse:
    def test_valid_uk_postcode(self):
        r = PostcodeValidationResponse(
            valid=True,
            postcode="SW1A 1AA",
            area="SW",
            region="London",
        )
        assert r.valid is True
        assert r.is_highland_island is False

    def test_invalid_postcode(self):
        r = PostcodeValidationResponse(valid=False, postcode="INVALID")
        assert r.valid is False
        assert r.area is None
        assert r.region is None

    def test_highland_island(self):
        r = PostcodeValidationResponse(
            valid=True,
            postcode="HS1 2AB",
            area="HS",
            region="Scotland",
            is_highland_island=True,
        )
        assert r.is_highland_island is True
