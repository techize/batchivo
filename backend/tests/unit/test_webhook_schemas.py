"""
Tests for webhook Pydantic schemas.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.webhook import WebhookEventType
from app.schemas.webhook import (
    CustomerEventData,
    InventoryEventData,
    OrderEventData,
    PaymentEventData,
    ProductEventData,
    ReturnEventData,
    ReviewEventData,
    WebhookDeliveryDetail,
    WebhookDeliveryList,
    WebhookDeliveryResponse,
    WebhookEventPayload,
    WebhookSubscriptionCreate,
    WebhookSubscriptionList,
    WebhookSubscriptionUpdate,
    WebhookSubscriptionWithSecret,
    WebhookTestPayload,
    WebhookTestResult,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestWebhookEventType:
    def test_order_events(self):
        assert WebhookEventType.ORDER_CREATED == "order.created"
        assert WebhookEventType.ORDER_PAID == "order.paid"
        assert WebhookEventType.ORDER_SHIPPED == "order.shipped"
        assert WebhookEventType.ORDER_CANCELLED == "order.cancelled"

    def test_payment_events(self):
        assert WebhookEventType.PAYMENT_COMPLETED == "payment.completed"
        assert WebhookEventType.PAYMENT_REFUNDED == "payment.refunded"
        assert WebhookEventType.PAYMENT_FAILED == "payment.failed"

    def test_inventory_events(self):
        assert WebhookEventType.INVENTORY_LOW_STOCK == "inventory.low_stock"
        assert WebhookEventType.INVENTORY_OUT_OF_STOCK == "inventory.out_of_stock"

    def test_product_events(self):
        assert WebhookEventType.PRODUCT_CREATED == "product.created"
        assert WebhookEventType.PRODUCT_UPDATED == "product.updated"
        assert WebhookEventType.PRODUCT_DELETED == "product.deleted"

    def test_review_events(self):
        assert WebhookEventType.REVIEW_SUBMITTED == "review.submitted"
        assert WebhookEventType.REVIEW_APPROVED == "review.approved"

    def test_customer_events(self):
        assert WebhookEventType.CUSTOMER_REGISTERED == "customer.registered"
        assert WebhookEventType.CUSTOMER_UPDATED == "customer.updated"

    def test_return_events(self):
        assert WebhookEventType.RETURN_REQUESTED == "return.requested"
        assert WebhookEventType.RETURN_APPROVED == "return.approved"
        assert WebhookEventType.RETURN_COMPLETED == "return.completed"


class TestWebhookSubscriptionCreate:
    def test_valid(self):
        s = WebhookSubscriptionCreate(
            name="My Webhook",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )
        assert s.name == "My Webhook"

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(
                name="",
                url="https://example.com/hook",
                events=[WebhookEventType.ORDER_CREATED],
            )

    def test_name_max_100(self):
        s = WebhookSubscriptionCreate(
            name="N" * 100,
            url="https://example.com/hook",
            events=[WebhookEventType.ORDER_PAID],
        )
        assert len(s.name) == 100

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(
                name="N" * 101,
                url="https://example.com/hook",
                events=[WebhookEventType.ORDER_PAID],
            )

    def test_empty_events_raises(self):
        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(
                name="Hook",
                url="https://example.com/hook",
                events=[],
            )

    def test_duplicate_events_deduplicated(self):
        s = WebhookSubscriptionCreate(
            name="Hook",
            url="https://example.com/hook",
            events=[WebhookEventType.ORDER_CREATED, WebhookEventType.ORDER_CREATED],
        )
        assert len(s.events) == 1

    def test_multiple_events(self):
        s = WebhookSubscriptionCreate(
            name="Multi-event Hook",
            url="https://example.com/hook",
            events=[
                WebhookEventType.ORDER_CREATED,
                WebhookEventType.ORDER_PAID,
                WebhookEventType.ORDER_SHIPPED,
            ],
        )
        assert len(s.events) == 3

    def test_with_custom_headers(self):
        s = WebhookSubscriptionCreate(
            name="Secure Hook",
            url="https://example.com/hook",
            events=[WebhookEventType.PRODUCT_CREATED],
            custom_headers={"X-Secret": "abc123"},
        )
        assert s.custom_headers["X-Secret"] == "abc123"


class TestWebhookSubscriptionUpdate:
    def test_all_optional(self):
        u = WebhookSubscriptionUpdate()
        assert u.name is None
        assert u.url is None
        assert u.events is None
        assert u.is_active is None

    def test_partial_update(self):
        u = WebhookSubscriptionUpdate(is_active=False)
        assert u.is_active is False

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            WebhookSubscriptionUpdate(name="")


class TestWebhookSubscriptionWithSecret:
    def _base(self, **kwargs) -> dict:
        now = _now()
        defaults = {
            "id": uuid4(),
            "name": "My Hook",
            "url": "https://example.com/hook",
            "events": ["order.created"],
            "is_active": True,
            "failure_count": 0,
            "created_at": now,
            "updated_at": now,
            "secret": "whsec_abc123xyz",
        }
        defaults.update(kwargs)
        return defaults

    def test_includes_secret(self):
        s = WebhookSubscriptionWithSecret(**self._base())
        assert s.secret == "whsec_abc123xyz"


class TestWebhookDeliveryResponse:
    def _base(self, **kwargs) -> dict:
        now = _now()
        defaults = {
            "id": uuid4(),
            "subscription_id": uuid4(),
            "event_type": "order.created",
            "event_id": "evt_123",
            "status": "success",
            "attempts": 1,
            "created_at": now,
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        r = WebhookDeliveryResponse(**self._base())
        assert r.status == "success"
        assert r.response_code is None
        assert r.error_message is None

    def test_with_response_info(self):
        r = WebhookDeliveryResponse(
            **self._base(response_code=200, response_time_ms=145, completed_at=_now())
        )
        assert r.response_code == 200
        assert r.response_time_ms == 145

    def test_failed_delivery(self):
        r = WebhookDeliveryResponse(
            **self._base(status="failed", error_message="Connection refused", attempts=3)
        )
        assert r.status == "failed"
        assert r.attempts == 3


class TestWebhookDeliveryDetail:
    def test_includes_payload(self):
        now = _now()
        r = WebhookDeliveryDetail(
            id=uuid4(),
            subscription_id=uuid4(),
            event_type="order.paid",
            event_id="evt_456",
            status="success",
            response_code=200,
            attempts=1,
            created_at=now,
            payload={"order_id": "MYS-001", "amount": 2999},
            response_body='{"ok": true}',
        )
        assert r.payload["order_id"] == "MYS-001"
        assert r.response_body == '{"ok": true}'


class TestWebhookDeliveryList:
    def test_empty(self):
        r = WebhookDeliveryList(deliveries=[], total=0, page=1, limit=20, has_more=False)
        assert r.total == 0
        assert r.has_more is False

    def test_paginated(self):
        r = WebhookDeliveryList(deliveries=[], total=50, page=2, limit=20, has_more=True)
        assert r.has_more is True


class TestWebhookSubscriptionList:
    def test_empty(self):
        r = WebhookSubscriptionList(subscriptions=[], total=0)
        assert r.total == 0


class TestWebhookTestPayload:
    def test_default(self):
        p = WebhookTestPayload()
        assert p.event_type == WebhookEventType.ORDER_CREATED
        assert p.test_data is None

    def test_custom_event(self):
        p = WebhookTestPayload(
            event_type=WebhookEventType.PAYMENT_COMPLETED,
            test_data={"amount": 1000},
        )
        assert p.event_type == WebhookEventType.PAYMENT_COMPLETED
        assert p.test_data["amount"] == 1000


class TestWebhookTestResult:
    def test_success(self):
        r = WebhookTestResult(success=True, response_code=200, response_time_ms=80)
        assert r.success is True
        assert r.error_message is None

    def test_failure(self):
        r = WebhookTestResult(success=False, error_message="Timeout after 30s")
        assert r.success is False


class TestWebhookEventPayload:
    def test_valid(self):
        p = WebhookEventPayload(
            event_id="evt_abc123",
            event_type="order.created",
            timestamp=_now(),
            tenant_id=str(uuid4()),
            data={"order_number": "MYS-001"},
        )
        assert p.event_type == "order.created"
        assert p.data["order_number"] == "MYS-001"


class TestEventDataSchemas:
    def test_order_event_data(self):
        d = OrderEventData(
            order_id="ord-1",
            order_number="MYS-0001",
            status="confirmed",
            total_amount=29.99,
            customer_email="jane@example.com",
            items_count=2,
            created_at=_now(),
        )
        assert d.currency == "GBP"
        assert d.items_count == 2

    def test_payment_event_data(self):
        d = PaymentEventData(
            payment_id="pay-1",
            order_id="ord-1",
            amount=29.99,
            status="COMPLETED",
        )
        assert d.currency == "GBP"
        assert d.payment_method is None

    def test_inventory_event_data(self):
        d = InventoryEventData(
            product_id="prod-1",
            product_sku="DRG-001",
            product_name="Dragon Mini",
            current_stock=2,
            threshold=5,
        )
        assert d.current_stock == 2

    def test_product_event_data(self):
        d = ProductEventData(
            product_id="prod-1",
            sku="DRG-001",
            name="Dragon Mini",
            is_active=True,
            shop_visible=True,
            price=12.99,
        )
        assert d.is_active is True

    def test_review_event_data(self):
        d = ReviewEventData(
            review_id="rev-1",
            product_id="prod-1",
            customer_email="jane@example.com",
            rating=5,
            title="Amazing!",
        )
        assert d.rating == 5

    def test_customer_event_data(self):
        d = CustomerEventData(
            customer_id="cust-1",
            email="jane@example.com",
            full_name="Jane Doe",
        )
        assert d.full_name == "Jane Doe"

    def test_return_event_data(self):
        d = ReturnEventData(
            return_id="ret-1",
            rma_number="RMA-001",
            order_id="ord-1",
            status="requested",
            reason="Wrong size",
        )
        assert d.status == "requested"
