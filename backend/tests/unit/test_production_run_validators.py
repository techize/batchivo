"""Unit tests for ProductionRun schema field validators.

Tests quality_rating range, completed_at temporal ordering, and
quantity positivity validators — all pure Pydantic validation logic.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.production_run import (
    ProductionRunBase,
    ProductionRunItemBase,
    ProductionRunItemUpdate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def now():
    return datetime.now(timezone.utc)


def make_run_base(**kwargs):
    """Minimal valid ProductionRunBase payload."""
    defaults = dict(
        run_number="RUN-001",
        started_at=now(),
        status="in_progress",
    )
    return ProductionRunBase(**{**defaults, **kwargs})


def make_item_base(**kwargs):
    """Minimal valid ProductionRunItemBase payload."""
    defaults = dict(model_id=uuid4(), quantity=1)
    return ProductionRunItemBase(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# ProductionRunBase.validate_quality_rating
# ---------------------------------------------------------------------------


class TestQualityRatingValidator:
    def test_none_is_accepted(self):
        run = make_run_base(quality_rating=None)
        assert run.quality_rating is None

    def test_1_is_valid(self):
        run = make_run_base(quality_rating=1)
        assert run.quality_rating == 1

    def test_5_is_valid(self):
        run = make_run_base(quality_rating=5)
        assert run.quality_rating == 5

    def test_3_is_valid(self):
        run = make_run_base(quality_rating=3)
        assert run.quality_rating == 3

    def test_0_raises(self):
        with pytest.raises(ValidationError):
            make_run_base(quality_rating=0)

    def test_6_raises(self):
        # Pydantic's le=5 field constraint fires first
        with pytest.raises(ValidationError):
            make_run_base(quality_rating=6)

    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            make_run_base(quality_rating=-1)


# ---------------------------------------------------------------------------
# ProductionRunCreate.validate_completed_at (temporal ordering)
# ---------------------------------------------------------------------------


class TestCompletedAtValidator:
    def _make_create(self, **kwargs):
        from app.schemas.production_run import ProductionRunCreate

        defaults = dict(
            run_number="RUN-001",
            started_at=now(),
            status="in_progress",
        )
        return ProductionRunCreate(**{**defaults, **kwargs})

    def test_completed_at_after_started_at_is_valid(self):
        start = now()
        end = start + timedelta(hours=2)
        run = self._make_create(started_at=start, completed_at=end)
        assert run.completed_at == end

    def test_completed_at_none_is_valid(self):
        run = self._make_create(completed_at=None)
        assert run.completed_at is None

    def test_completed_at_before_started_at_raises(self):
        start = now()
        end = start - timedelta(minutes=1)
        with pytest.raises(ValidationError, match="after started_at"):
            self._make_create(started_at=start, completed_at=end)

    def test_completed_at_equal_to_started_at_is_valid(self):
        # Validator uses strict < so equal timestamps are allowed
        start = now()
        run = self._make_create(started_at=start, completed_at=start)
        assert run.completed_at == start

    def test_completed_at_without_started_at_is_valid(self):
        # started_at=None means no comparison is made
        end = now() + timedelta(hours=1)
        run = self._make_create(started_at=None, completed_at=end)
        assert run.completed_at == end


# ---------------------------------------------------------------------------
# ProductionRunItemBase.validate_quantity
# ---------------------------------------------------------------------------


class TestItemQuantityValidator:
    def test_positive_quantity_accepted(self):
        item = make_item_base(quantity=5)
        assert item.quantity == 5

    def test_quantity_one_accepted(self):
        item = make_item_base(quantity=1)
        assert item.quantity == 1

    def test_zero_quantity_raises(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            make_item_base(quantity=0)

    def test_negative_quantity_raises(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            make_item_base(quantity=-1)


# ---------------------------------------------------------------------------
# ProductionRunItemUpdate validators (optional quantity, non-negative counts)
# ---------------------------------------------------------------------------


class TestItemUpdateValidators:
    def test_none_quantity_accepted(self):
        update = ProductionRunItemUpdate(quantity=None)
        assert update.quantity is None

    def test_positive_quantity_accepted(self):
        update = ProductionRunItemUpdate(quantity=3)
        assert update.quantity == 3

    def test_zero_quantity_raises(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            ProductionRunItemUpdate(quantity=0)

    def test_negative_successful_quantity_raises(self):
        with pytest.raises(ValidationError):
            ProductionRunItemUpdate(successful_quantity=-1)

    def test_negative_failed_quantity_raises(self):
        with pytest.raises(ValidationError):
            ProductionRunItemUpdate(failed_quantity=-1)

    def test_zero_successful_quantity_accepted(self):
        update = ProductionRunItemUpdate(successful_quantity=0)
        assert update.successful_quantity == 0

    def test_none_quantities_accepted(self):
        update = ProductionRunItemUpdate(successful_quantity=None, failed_quantity=None)
        assert update.successful_quantity is None
        assert update.failed_quantity is None
