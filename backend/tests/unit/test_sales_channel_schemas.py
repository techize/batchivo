"""
Tests for SalesChannel Pydantic schemas.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.sales_channel import SalesChannelBase, SalesChannelCreate, SalesChannelUpdate


def valid_channel(**kwargs) -> dict:
    defaults = {
        "name": "My Etsy Shop",
        "platform_type": "etsy",
    }
    defaults.update(kwargs)
    return defaults


class TestSalesChannelBase:
    def test_valid_minimal(self):
        c = SalesChannelBase(**valid_channel())
        assert c.name == "My Etsy Shop"
        assert c.fee_percentage == Decimal("0")
        assert c.fee_fixed == Decimal("0")
        assert c.monthly_cost == Decimal("0")
        assert c.is_active is True

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            SalesChannelBase(**valid_channel(name=""))

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            SalesChannelBase(**valid_channel(name="N" * 101))

    def test_fee_percentage_zero_accepted(self):
        c = SalesChannelBase(**valid_channel(fee_percentage=Decimal("0")))
        assert c.fee_percentage == Decimal("0")

    def test_fee_percentage_max_100(self):
        c = SalesChannelBase(**valid_channel(fee_percentage=Decimal("100")))
        assert c.fee_percentage == Decimal("100")

    def test_fee_percentage_above_100_raises(self):
        with pytest.raises(ValidationError):
            SalesChannelBase(**valid_channel(fee_percentage=Decimal("100.01")))

    def test_fee_percentage_negative_raises(self):
        with pytest.raises(ValidationError):
            SalesChannelBase(**valid_channel(fee_percentage=Decimal("-1")))

    def test_fee_fixed_zero_accepted(self):
        c = SalesChannelBase(**valid_channel(fee_fixed=Decimal("0")))
        assert c.fee_fixed == Decimal("0")

    def test_fee_fixed_negative_raises(self):
        with pytest.raises(ValidationError):
            SalesChannelBase(**valid_channel(fee_fixed=Decimal("-0.01")))

    def test_monthly_cost_zero_accepted(self):
        c = SalesChannelBase(**valid_channel(monthly_cost=Decimal("0")))
        assert c.monthly_cost == Decimal("0")

    def test_monthly_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            SalesChannelBase(**valid_channel(monthly_cost=Decimal("-5")))

    def test_realistic_etsy_fees(self):
        c = SalesChannelBase(
            **valid_channel(
                fee_percentage=Decimal("6.5"),
                fee_fixed=Decimal("0.20"),
                monthly_cost=Decimal("0"),
            )
        )
        assert c.fee_percentage == Decimal("6.5")

    def test_is_active_default_true(self):
        c = SalesChannelBase(**valid_channel())
        assert c.is_active is True

    def test_is_active_false(self):
        c = SalesChannelBase(**valid_channel(is_active=False))
        assert c.is_active is False


class TestSalesChannelCreate:
    def test_inherits_from_base(self):
        c = SalesChannelCreate(**valid_channel())
        assert c.name == "My Etsy Shop"


class TestSalesChannelUpdate:
    def test_all_optional(self):
        u = SalesChannelUpdate()
        assert u.name is None
        assert u.fee_percentage is None
        assert u.is_active is None

    def test_partial_update(self):
        u = SalesChannelUpdate(fee_percentage=Decimal("5.0"), is_active=False)
        assert u.fee_percentage == Decimal("5.0")

    def test_fee_percentage_above_100_raises(self):
        with pytest.raises(ValidationError):
            SalesChannelUpdate(fee_percentage=Decimal("101"))

    def test_fee_fixed_negative_raises(self):
        with pytest.raises(ValidationError):
            SalesChannelUpdate(fee_fixed=Decimal("-1"))

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            SalesChannelUpdate(name="")
