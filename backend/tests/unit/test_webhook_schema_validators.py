"""Unit tests for WebhookSubscriptionCreate.validate_events validator.

Tests the deduplication behaviour of the events list validator.
"""

import pytest
from pydantic import ValidationError

from app.models.webhook import WebhookEventType
from app.schemas.webhook import WebhookSubscriptionCreate


def make_webhook(**kwargs):
    base = dict(
        name="Test Webhook",
        url="https://example.com/webhook",
        events=[WebhookEventType.ORDER_CREATED],
    )
    return WebhookSubscriptionCreate(**{**base, **kwargs})


class TestWebhookEventsValidator:
    def test_unique_events_accepted_unchanged(self):
        wh = make_webhook(events=[WebhookEventType.ORDER_CREATED, WebhookEventType.ORDER_SHIPPED])
        assert len(wh.events) == 2

    def test_duplicate_events_deduplicated(self):
        wh = make_webhook(
            events=[
                WebhookEventType.ORDER_CREATED,
                WebhookEventType.ORDER_CREATED,
                WebhookEventType.ORDER_SHIPPED,
            ]
        )
        assert len(wh.events) == 2
        assert WebhookEventType.ORDER_CREATED in wh.events
        assert WebhookEventType.ORDER_SHIPPED in wh.events

    def test_all_duplicates_deduplicated(self):
        wh = make_webhook(
            events=[WebhookEventType.PAYMENT_COMPLETED, WebhookEventType.PAYMENT_COMPLETED]
        )
        assert len(wh.events) == 1

    def test_single_event_accepted(self):
        wh = make_webhook(events=[WebhookEventType.INVENTORY_LOW_STOCK])
        assert len(wh.events) == 1

    def test_empty_events_raises(self):
        with pytest.raises(ValidationError):
            make_webhook(events=[])

    def test_many_distinct_events_accepted(self):
        events = [
            WebhookEventType.ORDER_CREATED,
            WebhookEventType.ORDER_PAID,
            WebhookEventType.ORDER_SHIPPED,
            WebhookEventType.PAYMENT_COMPLETED,
            WebhookEventType.INVENTORY_LOW_STOCK,
        ]
        wh = make_webhook(events=events)
        assert len(wh.events) == 5
