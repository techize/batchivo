"""Unit tests for uncovered production run schema validators.

Covers:
- ProductionRunMaterialBase.validate_positive_decimals (model weight, cost_per_gram)
- ProductionRunMaterialBase.validate_non_negative_decimal (flushed/tower grams)
- ProductionRunMaterialUpdate optional-field validators
- CancelProductionRunRequest.validate_cancel_mode
- FailProductionRunRequest.validate_failure_reason (strip/lower)
- ShippingOption.price_pounds and estimated_days_display properties
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.production_run import (
    CancelProductionRunRequest,
    FailProductionRunRequest,
    ProductionRunMaterialBase,
    ProductionRunMaterialUpdate,
)
from app.schemas.shipping import ShippingOption


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_material_base(**kwargs):
    defaults = dict(
        spool_id=uuid4(),
        estimated_model_weight_grams=Decimal("10"),
        cost_per_gram=Decimal("0.05"),
    )
    return ProductionRunMaterialBase(**{**defaults, **kwargs})


def make_fail_request(**kwargs):
    from app.schemas.production_run import MaterialUsageEntry

    defaults = dict(
        failure_reason="spaghetti",
        waste_materials=[MaterialUsageEntry(spool_id=uuid4(), grams=Decimal("5"))],
    )
    return FailProductionRunRequest(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# ProductionRunMaterialBase validators
# ---------------------------------------------------------------------------


class TestMaterialBasePositiveDecimals:
    def test_valid_model_weight_accepted(self):
        m = make_material_base(estimated_model_weight_grams=Decimal("5"))
        assert m.estimated_model_weight_grams == Decimal("5")

    def test_zero_model_weight_raises(self):
        with pytest.raises(ValidationError):
            make_material_base(estimated_model_weight_grams=Decimal("0"))

    def test_negative_model_weight_raises(self):
        with pytest.raises(ValidationError):
            make_material_base(estimated_model_weight_grams=Decimal("-1"))

    def test_valid_cost_per_gram_accepted(self):
        m = make_material_base(cost_per_gram=Decimal("0.10"))
        assert m.cost_per_gram == Decimal("0.10")

    def test_zero_cost_per_gram_raises(self):
        with pytest.raises(ValidationError):
            make_material_base(cost_per_gram=Decimal("0"))

    def test_negative_cost_per_gram_raises(self):
        with pytest.raises(ValidationError):
            make_material_base(cost_per_gram=Decimal("-0.01"))


class TestMaterialBaseNonNegativeDecimals:
    def test_zero_flushed_grams_accepted(self):
        m = make_material_base(estimated_flushed_grams=Decimal("0"))
        assert m.estimated_flushed_grams == Decimal("0")

    def test_positive_flushed_grams_accepted(self):
        m = make_material_base(estimated_flushed_grams=Decimal("2.5"))
        assert m.estimated_flushed_grams == Decimal("2.5")

    def test_negative_flushed_grams_raises(self):
        with pytest.raises(ValidationError):
            make_material_base(estimated_flushed_grams=Decimal("-0.1"))

    def test_zero_tower_grams_accepted(self):
        m = make_material_base(estimated_tower_grams=Decimal("0"))
        assert m.estimated_tower_grams == Decimal("0")

    def test_negative_tower_grams_raises(self):
        with pytest.raises(ValidationError):
            make_material_base(estimated_tower_grams=Decimal("-1"))


# ---------------------------------------------------------------------------
# ProductionRunMaterialUpdate optional validators
# ---------------------------------------------------------------------------


class TestMaterialUpdateValidators:
    def test_none_values_accepted(self):
        update = ProductionRunMaterialUpdate()
        assert update.estimated_model_weight_grams is None
        assert update.cost_per_gram is None

    def test_positive_model_weight_accepted(self):
        update = ProductionRunMaterialUpdate(estimated_model_weight_grams=Decimal("3"))
        assert update.estimated_model_weight_grams == Decimal("3")

    def test_zero_model_weight_raises(self):
        with pytest.raises(ValidationError):
            ProductionRunMaterialUpdate(estimated_model_weight_grams=Decimal("0"))

    def test_positive_cost_per_gram_accepted(self):
        update = ProductionRunMaterialUpdate(cost_per_gram=Decimal("0.05"))
        assert update.cost_per_gram == Decimal("0.05")

    def test_zero_cost_per_gram_raises(self):
        with pytest.raises(ValidationError):
            ProductionRunMaterialUpdate(cost_per_gram=Decimal("0"))

    def test_zero_flushed_grams_accepted(self):
        update = ProductionRunMaterialUpdate(estimated_flushed_grams=Decimal("0"))
        assert update.estimated_flushed_grams == Decimal("0")

    def test_negative_flushed_grams_raises(self):
        with pytest.raises(ValidationError):
            ProductionRunMaterialUpdate(estimated_flushed_grams=Decimal("-1"))

    def test_negative_actual_model_weight_raises(self):
        with pytest.raises(ValidationError):
            ProductionRunMaterialUpdate(actual_model_weight_grams=Decimal("-0.1"))

    def test_zero_spool_weight_before_accepted(self):
        update = ProductionRunMaterialUpdate(spool_weight_before_grams=Decimal("0"))
        assert update.spool_weight_before_grams == Decimal("0")

    def test_negative_spool_weight_raises(self):
        with pytest.raises(ValidationError):
            ProductionRunMaterialUpdate(spool_weight_before_grams=Decimal("-5"))


# ---------------------------------------------------------------------------
# CancelProductionRunRequest.validate_cancel_mode
# ---------------------------------------------------------------------------


class TestCancelModeValidator:
    def test_full_reversal_accepted(self):
        req = CancelProductionRunRequest(cancel_mode="full_reversal")
        assert req.cancel_mode == "full_reversal"

    def test_record_partial_accepted(self):
        req = CancelProductionRunRequest(cancel_mode="record_partial")
        assert req.cancel_mode == "record_partial"

    def test_default_is_full_reversal(self):
        req = CancelProductionRunRequest()
        assert req.cancel_mode == "full_reversal"

    def test_invalid_cancel_mode_raises(self):
        with pytest.raises(ValidationError, match="cancel_mode must be one of"):
            CancelProductionRunRequest(cancel_mode="something_else")

    def test_empty_cancel_mode_raises(self):
        with pytest.raises(ValidationError):
            CancelProductionRunRequest(cancel_mode="")


# ---------------------------------------------------------------------------
# FailProductionRunRequest.validate_failure_reason
# ---------------------------------------------------------------------------


class TestFailureReasonValidator:
    def test_reason_stripped_and_lowercased(self):
        req = make_fail_request(failure_reason="  Spaghetti  ")
        assert req.failure_reason == "spaghetti"

    def test_mixed_case_lowercased(self):
        req = make_fail_request(failure_reason="Layer_Shift")
        assert req.failure_reason == "layer_shift"

    def test_already_lowercase_unchanged(self):
        req = make_fail_request(failure_reason="clog")
        assert req.failure_reason == "clog"

    def test_empty_reason_raises(self):
        with pytest.raises(ValidationError):
            make_fail_request(failure_reason="")

    def test_reason_over_100_chars_raises(self):
        with pytest.raises(ValidationError):
            make_fail_request(failure_reason="x" * 101)

    def test_waste_materials_required(self):
        with pytest.raises(ValidationError):
            FailProductionRunRequest(failure_reason="clog", waste_materials=[])


# ---------------------------------------------------------------------------
# ShippingOption properties
# ---------------------------------------------------------------------------


def make_shipping_option(**kwargs):
    defaults = dict(
        id="rm-48",
        name="Royal Mail 48",
        carrier="Royal Mail",
        description="2nd class",
        price_pence=300,
        estimated_days_min=2,
        estimated_days_max=3,
    )
    return ShippingOption(**{**defaults, **kwargs})


class TestShippingOptionPricePounds:
    def test_price_pence_converted_correctly(self):
        opt = make_shipping_option(price_pence=350)
        assert opt.price_pounds == Decimal("3.50")

    def test_round_pounds(self):
        opt = make_shipping_option(price_pence=500)
        assert opt.price_pounds == Decimal("5.00")

    def test_zero_pence(self):
        opt = make_shipping_option(price_pence=0)
        assert opt.price_pounds == Decimal("0")


class TestShippingOptionEstimatedDaysDisplay:
    def test_single_day_singular(self):
        opt = make_shipping_option(estimated_days_min=1, estimated_days_max=1)
        assert opt.estimated_days_display == "1 day"

    def test_same_day_plural(self):
        opt = make_shipping_option(estimated_days_min=3, estimated_days_max=3)
        assert opt.estimated_days_display == "3 days"

    def test_range_display(self):
        opt = make_shipping_option(estimated_days_min=2, estimated_days_max=4)
        assert opt.estimated_days_display == "2-4 days"

    def test_next_day_range(self):
        opt = make_shipping_option(estimated_days_min=1, estimated_days_max=2)
        assert opt.estimated_days_display == "1-2 days"
