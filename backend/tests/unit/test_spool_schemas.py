"""
Tests for Spool Pydantic schemas.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.spool import SpoolBase, SpoolCreate, SpoolUpdate


def valid_spool(**kwargs) -> dict:
    defaults = {
        "spool_id": "SPOOL-001",
        "filament_type_id": uuid4(),
        "initial_weight": 1000.0,
        "current_weight": 750.0,
    }
    defaults.update(kwargs)
    return defaults


class TestSpoolBase:
    def test_valid_minimal(self):
        s = SpoolBase(**valid_spool())
        assert s.spool_id == "SPOOL-001"
        assert s.is_active is True
        assert s.is_labeled is False

    def test_spool_id_empty_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(spool_id=""))

    def test_spool_id_too_long_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(spool_id="S" * 51))

    # --- filament_type_id ---
    def test_filament_type_id_required(self):
        data = valid_spool()
        del data["filament_type_id"]
        with pytest.raises(ValidationError):
            SpoolCreate(**data)

    # --- is_labeled ---
    def test_is_labeled_defaults_false(self):
        """DATA-05: is_labeled defaults to False for new spools."""
        s = SpoolBase(**valid_spool())
        assert s.is_labeled is False

    def test_is_labeled_can_be_set_true(self):
        s = SpoolBase(**valid_spool(is_labeled=True))
        assert s.is_labeled is True

    # --- Weight ---
    def test_initial_weight_zero_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(initial_weight=0))

    def test_initial_weight_negative_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(initial_weight=-100))

    def test_current_weight_zero_accepted(self):
        s = SpoolBase(**valid_spool(current_weight=0))
        assert s.current_weight == 0

    def test_current_weight_negative_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(current_weight=-1))

    def test_purchase_price_zero_accepted(self):
        s = SpoolBase(**valid_spool(purchase_price=0))
        assert s.purchase_price == 0

    def test_purchase_price_negative_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(purchase_price=-1.0))


class TestSpoolCreate:
    def test_inherits_from_base(self):
        s = SpoolCreate(**valid_spool())
        assert s.spool_id == "SPOOL-001"

    def test_filament_type_id_present(self):
        ft_id = uuid4()
        s = SpoolCreate(**valid_spool(filament_type_id=ft_id))
        assert s.filament_type_id == ft_id


class TestSpoolUpdate:
    def test_all_optional(self):
        u = SpoolUpdate()
        assert u.filament_type_id is None
        assert u.current_weight is None
        assert u.is_active is None

    def test_partial_update(self):
        u = SpoolUpdate(current_weight=500.0, is_active=False)
        assert u.current_weight == 500.0
        assert u.is_active is False

    def test_current_weight_negative_raises(self):
        with pytest.raises(ValidationError):
            SpoolUpdate(current_weight=-1.0)

    def test_spool_id_empty_raises(self):
        with pytest.raises(ValidationError):
            SpoolUpdate(spool_id="")

    def test_is_labeled_update(self):
        u = SpoolUpdate(is_labeled=True)
        assert u.is_labeled is True
