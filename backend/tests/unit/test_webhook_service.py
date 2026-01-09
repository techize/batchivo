"""Unit tests for the webhook service."""

import hashlib
import hmac
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

import httpx

from app.models.webhook import DeliveryStatus, WebhookEventType
from app.services.webhook_service import WebhookService

pytestmark = pytest.mark.anyio


class TestWebhookServiceSubscriptions:
    """Tests for webhook subscription management."""

    async def test_create_subscription(self, db_session, test_tenant):
        """Test creating a webhook subscription."""
        service = WebhookService(db_session)

        subscription, secret = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test Webhook",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED, WebhookEventType.ORDER_SHIPPED],
        )

        assert subscription.name == "Test Webhook"
        assert subscription.url == "https://example.com/webhook"
        assert WebhookEventType.ORDER_CREATED.value in subscription.events
        assert subscription.is_active is True
        assert len(secret) == 64  # 32 bytes hex encoded

    async def test_create_subscription_with_custom_headers(self, db_session, test_tenant):
        """Test creating subscription with custom headers."""
        service = WebhookService(db_session)

        custom_headers = {"X-Custom-Header": "custom-value"}
        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
            custom_headers=custom_headers,
        )

        assert subscription.custom_headers == custom_headers

    async def test_get_subscription(self, db_session, test_tenant):
        """Test getting a subscription by ID."""
        service = WebhookService(db_session)

        # Create subscription
        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        # Get it
        retrieved = await service.get_subscription(subscription.id, test_tenant.id)
        assert retrieved is not None
        assert retrieved.id == subscription.id

    async def test_get_subscription_wrong_tenant(self, db_session, test_tenant):
        """Test that subscription is not returned for wrong tenant."""
        service = WebhookService(db_session)

        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        # Try to get with wrong tenant ID
        wrong_tenant_id = uuid4()
        retrieved = await service.get_subscription(subscription.id, wrong_tenant_id)
        assert retrieved is None

    async def test_list_subscriptions(self, db_session, test_tenant):
        """Test listing subscriptions."""
        service = WebhookService(db_session)

        # Create multiple subscriptions
        await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Webhook 1",
            url="https://example.com/webhook1",
            events=[WebhookEventType.ORDER_CREATED],
        )
        await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Webhook 2",
            url="https://example.com/webhook2",
            events=[WebhookEventType.ORDER_SHIPPED],
        )

        subscriptions = await service.list_subscriptions(test_tenant.id)
        assert len(subscriptions) == 2

    async def test_list_subscriptions_excludes_inactive(self, db_session, test_tenant):
        """Test that inactive subscriptions are excluded by default."""
        service = WebhookService(db_session)

        # Create active subscription
        await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Active",
            url="https://example.com/webhook1",
            events=[WebhookEventType.ORDER_CREATED],
        )

        # Create and disable subscription
        inactive, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Inactive",
            url="https://example.com/webhook2",
            events=[WebhookEventType.ORDER_CREATED],
        )
        await service.update_subscription(inactive.id, test_tenant.id, is_active=False)

        # List without inactive
        subscriptions = await service.list_subscriptions(test_tenant.id)
        assert len(subscriptions) == 1
        assert subscriptions[0].name == "Active"

        # List with inactive
        all_subscriptions = await service.list_subscriptions(test_tenant.id, include_inactive=True)
        assert len(all_subscriptions) == 2

    async def test_update_subscription(self, db_session, test_tenant):
        """Test updating a subscription."""
        service = WebhookService(db_session)

        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Original",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        updated = await service.update_subscription(
            subscription.id,
            test_tenant.id,
            name="Updated",
            events=[WebhookEventType.ORDER_SHIPPED],
        )

        assert updated.name == "Updated"
        assert WebhookEventType.ORDER_SHIPPED.value in updated.events

    async def test_delete_subscription(self, db_session, test_tenant):
        """Test deleting a subscription."""
        service = WebhookService(db_session)

        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="To Delete",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        deleted = await service.delete_subscription(subscription.id, test_tenant.id)
        assert deleted is True

        # Verify deleted
        retrieved = await service.get_subscription(subscription.id, test_tenant.id)
        assert retrieved is None

    async def test_regenerate_secret(self, db_session, test_tenant):
        """Test regenerating secret."""
        service = WebhookService(db_session)

        subscription, original_secret = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        new_secret = await service.regenerate_secret(subscription.id, test_tenant.id)
        assert new_secret is not None
        assert new_secret != original_secret
        assert len(new_secret) == 64


class TestWebhookSignature:
    """Tests for HMAC signature generation."""

    def test_signature_generation(self, db_session):
        """Test that signatures are generated correctly."""
        service = WebhookService(db_session)
        payload = b'{"test": "data"}'
        secret = "test_secret_key"

        signature = service._generate_signature(payload, secret)

        # Verify signature manually
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert signature == expected


class TestWebhookDelivery:
    """Tests for webhook delivery functionality."""

    async def test_trigger_event_creates_delivery(self, db_session, test_tenant):
        """Test that triggering an event creates delivery records."""
        service = WebhookService(db_session)

        # Create subscription
        await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        # Mock the HTTP client to avoid real requests
        with patch.object(service, "_send_webhook", new_callable=AsyncMock):
            deliveries = await service.trigger_event(
                tenant_id=test_tenant.id,
                event_type=WebhookEventType.ORDER_CREATED,
                data={"order_id": "123"},
            )

        assert len(deliveries) == 1
        assert deliveries[0].event_type == WebhookEventType.ORDER_CREATED.value
        assert deliveries[0].payload["data"]["order_id"] == "123"

    async def test_trigger_event_no_subscriptions(self, db_session, test_tenant):
        """Test triggering event with no subscribers."""
        service = WebhookService(db_session)

        deliveries = await service.trigger_event(
            tenant_id=test_tenant.id,
            event_type=WebhookEventType.ORDER_CREATED,
            data={"order_id": "123"},
        )

        assert deliveries == []

    async def test_trigger_event_filters_by_event_type(self, db_session, test_tenant):
        """Test that only subscriptions for the event type receive webhooks."""
        service = WebhookService(db_session)

        # Create subscription for different event
        await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Ship Only",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_SHIPPED],  # Not ORDER_CREATED
        )

        with patch.object(service, "_send_webhook", new_callable=AsyncMock):
            deliveries = await service.trigger_event(
                tenant_id=test_tenant.id,
                event_type=WebhookEventType.ORDER_CREATED,
                data={"order_id": "123"},
            )

        assert deliveries == []

    async def test_send_webhook_success(self, db_session, test_tenant):
        """Test successful webhook delivery."""
        service = WebhookService(db_session)

        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        delivery = await service._create_delivery(
            subscription=subscription,
            event_type=WebhookEventType.ORDER_CREATED,
            event_id="test-123",
            data={"order_id": "456"},
            tenant_id=test_tenant.id,
        )

        # Mock successful response
        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"received": true}'

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            await service._send_webhook(delivery, subscription)

        # Refresh and check status
        await db_session.refresh(delivery)
        assert delivery.status == DeliveryStatus.SUCCESS.value
        assert delivery.response_code == 200

    async def test_send_webhook_failure_schedules_retry(self, db_session, test_tenant):
        """Test that failed delivery schedules retry."""
        service = WebhookService(db_session)

        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        delivery = await service._create_delivery(
            subscription=subscription,
            event_type=WebhookEventType.ORDER_CREATED,
            event_id="test-123",
            data={"order_id": "456"},
            tenant_id=test_tenant.id,
        )

        # Mock failed response
        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            await service._send_webhook(delivery, subscription)

        # Refresh and check status
        await db_session.refresh(delivery)
        assert delivery.status == DeliveryStatus.PENDING.value
        assert delivery.attempts == 2
        assert delivery.next_retry_at is not None

    async def test_send_webhook_timeout(self, db_session, test_tenant):
        """Test handling of timeout."""
        service = WebhookService(db_session)

        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        delivery = await service._create_delivery(
            subscription=subscription,
            event_type=WebhookEventType.ORDER_CREATED,
            event_id="test-123",
            data={"order_id": "456"},
            tenant_id=test_tenant.id,
        )

        # Mock timeout
        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))
            mock_client.return_value.__aenter__.return_value = mock_instance

            await service._send_webhook(delivery, subscription)

        await db_session.refresh(delivery)
        assert delivery.error_message == "Request timed out"


class TestWebhookTesting:
    """Tests for webhook testing functionality."""

    async def test_test_webhook_success(self, db_session, test_tenant):
        """Test the test webhook function."""
        service = WebhookService(db_session)

        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"ok": true}'

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await service.test_webhook(subscription.id, test_tenant.id)

        assert result["success"] is True
        assert result["response_code"] == 200

    async def test_test_webhook_not_found(self, db_session, test_tenant):
        """Test with non-existent subscription."""
        service = WebhookService(db_session)

        with pytest.raises(ValueError, match="Subscription not found"):
            await service.test_webhook(uuid4(), test_tenant.id)


class TestDeliveryManagement:
    """Tests for delivery listing and management."""

    async def test_list_deliveries(self, db_session, test_tenant):
        """Test listing deliveries."""
        service = WebhookService(db_session)

        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        # Create some deliveries
        await service._create_delivery(
            subscription=subscription,
            event_type=WebhookEventType.ORDER_CREATED,
            event_id="event-1",
            data={"order_id": "1"},
            tenant_id=test_tenant.id,
        )
        await service._create_delivery(
            subscription=subscription,
            event_type=WebhookEventType.ORDER_CREATED,
            event_id="event-2",
            data={"order_id": "2"},
            tenant_id=test_tenant.id,
        )

        deliveries, total = await service.list_deliveries(test_tenant.id)
        assert total == 2
        assert len(deliveries) == 2

    async def test_list_deliveries_filter_by_subscription(self, db_session, test_tenant):
        """Test filtering deliveries by subscription."""
        service = WebhookService(db_session)

        sub1, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Sub 1",
            url="https://example.com/webhook1",
            events=[WebhookEventType.ORDER_CREATED],
        )
        sub2, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Sub 2",
            url="https://example.com/webhook2",
            events=[WebhookEventType.ORDER_CREATED],
        )

        await service._create_delivery(
            subscription=sub1,
            event_type=WebhookEventType.ORDER_CREATED,
            event_id="event-1",
            data={"order_id": "1"},
            tenant_id=test_tenant.id,
        )
        await service._create_delivery(
            subscription=sub2,
            event_type=WebhookEventType.ORDER_CREATED,
            event_id="event-2",
            data={"order_id": "2"},
            tenant_id=test_tenant.id,
        )

        deliveries, total = await service.list_deliveries(test_tenant.id, subscription_id=sub1.id)
        assert total == 1
        assert deliveries[0].subscription_id == sub1.id

    async def test_retry_delivery(self, db_session, test_tenant):
        """Test manually retrying a failed delivery."""
        service = WebhookService(db_session)

        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        delivery = await service._create_delivery(
            subscription=subscription,
            event_type=WebhookEventType.ORDER_CREATED,
            event_id="event-1",
            data={"order_id": "1"},
            tenant_id=test_tenant.id,
        )

        # Mark as failed
        delivery.status = DeliveryStatus.FAILED.value
        delivery.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Mock the send
        with patch.object(service, "_send_webhook", new_callable=AsyncMock):
            retried = await service.retry_delivery(delivery.id, test_tenant.id)

        assert retried is not None
        assert retried.status == DeliveryStatus.PENDING.value
        assert retried.attempts == 1

    async def test_retry_delivery_not_failed(self, db_session, test_tenant):
        """Test that only failed deliveries can be retried."""
        service = WebhookService(db_session)

        subscription, _ = await service.create_subscription(
            tenant_id=test_tenant.id,
            name="Test",
            url="https://example.com/webhook",
            events=[WebhookEventType.ORDER_CREATED],
        )

        delivery = await service._create_delivery(
            subscription=subscription,
            event_type=WebhookEventType.ORDER_CREATED,
            event_id="event-1",
            data={"order_id": "1"},
            tenant_id=test_tenant.id,
        )

        with pytest.raises(ValueError, match="Can only retry failed deliveries"):
            await service.retry_delivery(delivery.id, test_tenant.id)
