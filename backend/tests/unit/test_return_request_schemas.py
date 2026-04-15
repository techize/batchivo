"""
Tests for return request (RMA) Pydantic schemas.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.return_request import ReturnAction, ReturnReason, ReturnStatus
from app.schemas.return_request import (
    ReturnItemCreate,
    ReturnLookupRequest,
    ReturnRequestApprove,
    ReturnRequestComplete,
    ReturnRequestCreate,
    ReturnRequestReject,
    ReturnRequestUpdate,
)


class TestReturnItemCreate:
    def test_valid_item(self):
        item = ReturnItemCreate(order_item_id=uuid4(), quantity=2)
        assert item.quantity == 2
        assert item.reason is None

    def test_quantity_zero_raises(self):
        with pytest.raises(ValidationError):
            ReturnItemCreate(order_item_id=uuid4(), quantity=0)

    def test_quantity_negative_raises(self):
        with pytest.raises(ValidationError):
            ReturnItemCreate(order_item_id=uuid4(), quantity=-1)

    def test_quantity_minimum_one(self):
        item = ReturnItemCreate(order_item_id=uuid4(), quantity=1)
        assert item.quantity == 1

    def test_with_reason(self):
        item = ReturnItemCreate(
            order_item_id=uuid4(),
            quantity=1,
            reason="Wing broke on arrival",
        )
        assert item.reason == "Wing broke on arrival"

    def test_reason_too_long_raises(self):
        with pytest.raises(ValidationError):
            ReturnItemCreate(order_item_id=uuid4(), quantity=1, reason="r" * 501)

    def test_reason_exactly_500(self):
        item = ReturnItemCreate(order_item_id=uuid4(), quantity=1, reason="r" * 500)
        assert len(item.reason) == 500


class TestReturnRequestCreate:
    def _valid(self, **kwargs) -> dict:
        defaults = {
            "reason": ReturnReason.DEFECTIVE,
            "items": [{"order_item_id": str(uuid4()), "quantity": 1}],
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        r = ReturnRequestCreate(**self._valid())
        assert r.reason == ReturnReason.DEFECTIVE
        assert r.requested_action == ReturnAction.REFUND  # default

    def test_reason_details_optional(self):
        r = ReturnRequestCreate(**self._valid())
        assert r.reason_details is None

    def test_reason_details_max_2000(self):
        r = ReturnRequestCreate(**self._valid(reason_details="d" * 2000))
        assert len(r.reason_details) == 2000

    def test_reason_details_too_long_raises(self):
        with pytest.raises(ValidationError):
            ReturnRequestCreate(**self._valid(reason_details="d" * 2001))

    def test_empty_items_raises(self):
        with pytest.raises(ValidationError):
            ReturnRequestCreate(reason=ReturnReason.DEFECTIVE, items=[])

    def test_custom_action(self):
        r = ReturnRequestCreate(**self._valid(requested_action=ReturnAction.REPLACEMENT))
        assert r.requested_action == ReturnAction.REPLACEMENT

    def test_customer_email_optional(self):
        r = ReturnRequestCreate(**self._valid())
        assert r.customer_email is None

    def test_customer_email_validated(self):
        with pytest.raises(ValidationError):
            ReturnRequestCreate(**self._valid(customer_email="not-an-email"))

    def test_customer_name_max_255(self):
        r = ReturnRequestCreate(**self._valid(customer_name="A" * 255))
        assert len(r.customer_name) == 255

    def test_customer_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            ReturnRequestCreate(**self._valid(customer_name="A" * 256))

    def test_all_return_reasons_accepted(self):
        for reason in ReturnReason:
            r = ReturnRequestCreate(**self._valid(reason=reason))
            assert r.reason == reason

    def test_all_return_actions_accepted(self):
        for action in ReturnAction:
            r = ReturnRequestCreate(**self._valid(requested_action=action))
            assert r.requested_action == action


class TestReturnRequestReject:
    def test_valid_rejection(self):
        r = ReturnRequestReject(rejection_reason="Outside 30-day window")
        assert r.rejection_reason == "Outside 30-day window"

    def test_empty_reason_raises(self):
        with pytest.raises(ValidationError):
            ReturnRequestReject(rejection_reason="")

    def test_reason_too_long_raises(self):
        with pytest.raises(ValidationError):
            ReturnRequestReject(rejection_reason="r" * 501)

    def test_reason_exactly_500(self):
        r = ReturnRequestReject(rejection_reason="r" * 500)
        assert len(r.rejection_reason) == 500

    def test_admin_notes_optional(self):
        r = ReturnRequestReject(rejection_reason="Valid reason")
        assert r.admin_notes is None

    def test_admin_notes_accepted(self):
        r = ReturnRequestReject(rejection_reason="Valid reason", admin_notes="Internal note")
        assert r.admin_notes == "Internal note"


class TestReturnRequestComplete:
    def test_all_optional(self):
        r = ReturnRequestComplete()
        assert r.refund_amount is None
        assert r.refund_reference is None
        assert r.admin_notes is None
        assert r.replacement_order_id is None

    def test_refund_amount_zero_accepted(self):
        r = ReturnRequestComplete(refund_amount=Decimal("0"))
        assert r.refund_amount == Decimal("0")

    def test_refund_amount_negative_raises(self):
        with pytest.raises(ValidationError):
            ReturnRequestComplete(refund_amount=Decimal("-1"))

    def test_positive_refund(self):
        r = ReturnRequestComplete(refund_amount=Decimal("19.99"))
        assert r.refund_amount == Decimal("19.99")

    def test_replacement_order_id(self):
        oid = uuid4()
        r = ReturnRequestComplete(replacement_order_id=oid)
        assert r.replacement_order_id == oid


class TestReturnRequestApprove:
    def test_all_optional(self):
        r = ReturnRequestApprove()
        assert r.admin_notes is None
        assert r.return_label_url is None


class TestReturnRequestUpdate:
    def test_all_optional(self):
        u = ReturnRequestUpdate()
        assert u.admin_notes is None
        assert u.return_tracking_number is None
        assert u.return_label_url is None


class TestReturnLookupRequest:
    def test_valid(self):
        r = ReturnLookupRequest(rma_number="RMA-12345", email="customer@example.com")
        assert r.rma_number == "RMA-12345"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            ReturnLookupRequest(rma_number="RMA-001", email="not-an-email")


class TestReturnEnums:
    def test_return_status_values(self):
        statuses = {s.value for s in ReturnStatus}
        assert "requested" in statuses
        assert "approved" in statuses
        assert "completed" in statuses
        assert "rejected" in statuses

    def test_return_reason_values(self):
        reasons = {r.value for r in ReturnReason}
        assert "defective" in reasons
        assert "changed_mind" in reasons
        assert "wrong_item" in reasons

    def test_return_action_values(self):
        actions = {a.value for a in ReturnAction}
        assert "refund" in actions
        assert "replacement" in actions
        assert "store_credit" in actions
