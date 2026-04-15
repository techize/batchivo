"""
Tests for InventoryTransaction Pydantic schemas.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.inventory_transaction import TransactionType
from app.schemas.inventory_transaction import (
    InventoryTransactionCreate,
    InventoryTransactionListResponse,
    InventoryTransactionSummary,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestTransactionType:
    def test_all_values(self):
        assert TransactionType.PURCHASE == "purchase"
        assert TransactionType.USAGE == "usage"
        assert TransactionType.ADJUSTMENT == "adjustment"
        assert TransactionType.TRANSFER == "transfer"
        assert TransactionType.RETURN == "return"
        assert TransactionType.WASTE == "waste"
        assert TransactionType.COUNT == "count"


class TestInventoryTransactionCreate:
    def test_valid(self):
        t = InventoryTransactionCreate(
            spool_id=uuid4(),
            new_weight=Decimal("750.0"),
            reason="Physical count correction",
        )
        assert t.new_weight == Decimal("750.0")
        assert t.notes is None

    def test_new_weight_zero_accepted(self):
        t = InventoryTransactionCreate(
            spool_id=uuid4(),
            new_weight=Decimal("0"),
            reason="Spool exhausted",
        )
        assert t.new_weight == Decimal("0")

    def test_new_weight_negative_raises(self):
        with pytest.raises(ValidationError):
            InventoryTransactionCreate(
                spool_id=uuid4(),
                new_weight=Decimal("-1"),
                reason="Bad data",
            )

    def test_reason_max_200(self):
        t = InventoryTransactionCreate(
            spool_id=uuid4(),
            new_weight=Decimal("500"),
            reason="R" * 200,
        )
        assert len(t.reason) == 200

    def test_reason_too_long_raises(self):
        with pytest.raises(ValidationError):
            InventoryTransactionCreate(
                spool_id=uuid4(),
                new_weight=Decimal("500"),
                reason="R" * 201,
            )

    def test_with_notes(self):
        t = InventoryTransactionCreate(
            spool_id=uuid4(),
            new_weight=Decimal("300"),
            reason="Count adjustment",
            notes="Measured with scale #2",
        )
        assert t.notes == "Measured with scale #2"


class TestInventoryTransactionListResponse:
    def test_empty(self):
        r = InventoryTransactionListResponse(transactions=[], total=0, page=1, page_size=20)
        assert r.total == 0
        assert r.page == 1
        assert r.page_size == 20

    def test_with_pagination(self):
        r = InventoryTransactionListResponse(transactions=[], total=150, page=3, page_size=50)
        assert r.total == 150
        assert r.page == 3


class TestInventoryTransactionSummary:
    def test_valid(self):
        s = InventoryTransactionSummary(
            spool_id="SPOOL-001",
            total_transactions=10,
            by_type={"usage": 6, "adjustment": 2, "return": 2},
            total_used=250.0,
            total_returned=50.0,
            total_adjusted=10.0,
        )
        assert s.total_transactions == 10
        assert s.total_used == 250.0
        assert s.by_type["usage"] == 6

    def test_zero_summary(self):
        s = InventoryTransactionSummary(
            spool_id="SPOOL-002",
            total_transactions=0,
            by_type={},
            total_used=0.0,
            total_returned=0.0,
            total_adjusted=0.0,
        )
        assert s.total_transactions == 0
        assert s.by_type == {}
