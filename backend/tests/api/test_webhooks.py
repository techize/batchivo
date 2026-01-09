"""API tests for webhook endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.anyio


class TestWebhookSubscriptions:
    """Tests for webhook subscription management."""

    async def test_create_subscription(self, client: AsyncClient, auth_headers):
        """Test creating a webhook subscription."""
        response = await client.post(
            "/api/v1/webhooks/subscriptions",
            headers=auth_headers,
            json={
                "name": "My Webhook",
                "url": "https://example.com/webhook",
                "events": ["order.created", "order.shipped"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Webhook"
        assert data["url"] == "https://example.com/webhook"
        assert "order.created" in data["events"]
        assert "order.shipped" in data["events"]
        assert data["is_active"] is True
        assert "secret" in data  # Secret shown only on creation
        assert len(data["secret"]) == 64  # 32 bytes hex encoded

    async def test_create_subscription_requires_auth(self, unauthenticated_client: AsyncClient):
        """Creating webhook requires authentication."""
        response = await unauthenticated_client.post(
            "/api/v1/webhooks/subscriptions",
            json={
                "name": "Test",
                "url": "https://example.com/webhook",
                "events": ["order.created"],
            },
        )
        assert response.status_code == 401

    async def test_create_subscription_invalid_url(self, client: AsyncClient, auth_headers):
        """Invalid URL should be rejected."""
        response = await client.post(
            "/api/v1/webhooks/subscriptions",
            headers=auth_headers,
            json={
                "name": "Test",
                "url": "not-a-valid-url",
                "events": ["order.created"],
            },
        )
        assert response.status_code == 422

    async def test_create_subscription_empty_events(self, client: AsyncClient, auth_headers):
        """Empty events list should be rejected."""
        response = await client.post(
            "/api/v1/webhooks/subscriptions",
            headers=auth_headers,
            json={
                "name": "Test",
                "url": "https://example.com/webhook",
                "events": [],
            },
        )
        assert response.status_code == 422

    async def test_list_subscriptions(self, client: AsyncClient, auth_headers):
        """Test listing webhook subscriptions."""
        # Create a subscription first
        await client.post(
            "/api/v1/webhooks/subscriptions",
            headers=auth_headers,
            json={
                "name": "Test Webhook",
                "url": "https://example.com/webhook",
                "events": ["order.created"],
            },
        )

        response = await client.get(
            "/api/v1/webhooks/subscriptions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data
        assert "total" in data
        assert data["total"] >= 1
        # Secret should NOT be in list response
        assert "secret" not in data["subscriptions"][0]

    async def test_get_subscription(self, client: AsyncClient, auth_headers):
        """Test getting a specific subscription."""
        # Create first
        create_response = await client.post(
            "/api/v1/webhooks/subscriptions",
            headers=auth_headers,
            json={
                "name": "Test Webhook",
                "url": "https://example.com/webhook",
                "events": ["order.created"],
            },
        )
        subscription_id = create_response.json()["id"]

        # Get it
        response = await client.get(
            f"/api/v1/webhooks/subscriptions/{subscription_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == subscription_id
        assert data["name"] == "Test Webhook"
        # Secret should NOT be in get response
        assert "secret" not in data

    async def test_get_subscription_not_found(self, client: AsyncClient, auth_headers):
        """Getting non-existent subscription returns 404."""
        response = await client.get(
            "/api/v1/webhooks/subscriptions/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_update_subscription(self, client: AsyncClient, auth_headers):
        """Test updating a subscription."""
        # Create first
        create_response = await client.post(
            "/api/v1/webhooks/subscriptions",
            headers=auth_headers,
            json={
                "name": "Original Name",
                "url": "https://example.com/webhook",
                "events": ["order.created"],
            },
        )
        subscription_id = create_response.json()["id"]

        # Update
        response = await client.put(
            f"/api/v1/webhooks/subscriptions/{subscription_id}",
            headers=auth_headers,
            json={
                "name": "Updated Name",
                "events": ["order.created", "order.shipped"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert "order.shipped" in data["events"]

    async def test_update_subscription_disable(self, client: AsyncClient, auth_headers):
        """Test disabling a subscription."""
        # Create first
        create_response = await client.post(
            "/api/v1/webhooks/subscriptions",
            headers=auth_headers,
            json={
                "name": "Test",
                "url": "https://example.com/webhook",
                "events": ["order.created"],
            },
        )
        subscription_id = create_response.json()["id"]

        # Disable
        response = await client.put(
            f"/api/v1/webhooks/subscriptions/{subscription_id}",
            headers=auth_headers,
            json={"is_active": False},
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    async def test_delete_subscription(self, client: AsyncClient, auth_headers):
        """Test deleting a subscription."""
        # Create first
        create_response = await client.post(
            "/api/v1/webhooks/subscriptions",
            headers=auth_headers,
            json={
                "name": "To Delete",
                "url": "https://example.com/webhook",
                "events": ["order.created"],
            },
        )
        subscription_id = create_response.json()["id"]

        # Delete
        response = await client.delete(
            f"/api/v1/webhooks/subscriptions/{subscription_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify deletion
        get_response = await client.get(
            f"/api/v1/webhooks/subscriptions/{subscription_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    async def test_regenerate_secret(self, client: AsyncClient, auth_headers):
        """Test regenerating the webhook secret."""
        # Create first
        create_response = await client.post(
            "/api/v1/webhooks/subscriptions",
            headers=auth_headers,
            json={
                "name": "Test",
                "url": "https://example.com/webhook",
                "events": ["order.created"],
            },
        )
        subscription_id = create_response.json()["id"]
        original_secret = create_response.json()["secret"]

        # Regenerate
        response = await client.post(
            f"/api/v1/webhooks/subscriptions/{subscription_id}/regenerate-secret",
            headers=auth_headers,
        )

        assert response.status_code == 200
        new_secret = response.json()["secret"]
        assert new_secret != original_secret
        assert len(new_secret) == 64


class TestWebhookTest:
    """Tests for webhook testing endpoint."""

    async def test_test_webhook_success(self, client: AsyncClient, auth_headers):
        """Test the test webhook endpoint with successful delivery."""
        # Create subscription
        create_response = await client.post(
            "/api/v1/webhooks/subscriptions",
            headers=auth_headers,
            json={
                "name": "Test",
                "url": "https://httpbin.org/post",
                "events": ["order.created"],
            },
        )
        subscription_id = create_response.json()["id"]

        # Mock the HTTP request
        with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = '{"success": true}'
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            response = await client.post(
                f"/api/v1/webhooks/subscriptions/{subscription_id}/test",
                headers=auth_headers,
                json={"event_type": "order.created"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["response_code"] == 200

    async def test_test_webhook_not_found(self, client: AsyncClient, auth_headers):
        """Test with non-existent subscription."""
        response = await client.post(
            "/api/v1/webhooks/subscriptions/00000000-0000-0000-0000-000000000000/test",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestWebhookDeliveries:
    """Tests for webhook delivery endpoints."""

    async def test_list_deliveries_empty(self, client: AsyncClient, auth_headers):
        """Test listing deliveries when none exist."""
        response = await client.get(
            "/api/v1/webhooks/deliveries",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deliveries"] == []
        assert data["total"] == 0

    async def test_list_deliveries_pagination(self, client: AsyncClient, auth_headers):
        """Test delivery list pagination params."""
        response = await client.get(
            "/api/v1/webhooks/deliveries",
            params={"page": 1, "limit": 10},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert "limit" in data
        assert "has_more" in data


class TestWebhookEventTypes:
    """Tests for event types endpoint."""

    async def test_list_event_types(self, client: AsyncClient, auth_headers):
        """Test listing available event types."""
        response = await client.get(
            "/api/v1/webhooks/event-types",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

        # Check structure
        event = data[0]
        assert "event_type" in event
        assert "category" in event
        assert "description" in event

        # Check expected events exist
        event_types = [e["event_type"] for e in data]
        assert "order.created" in event_types
        assert "payment.completed" in event_types
        assert "inventory.low_stock" in event_types
