"""Tests for Shopify webhook ingest endpoint."""

import base64
import hashlib
import hmac
import json
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.models.order import Order, OrderStatus
from app.models.tenant import Tenant


def make_signature(body: bytes, secret: str) -> str:
    """Generate a valid Shopify HMAC-SHA256 signature."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()  # type: ignore[attr-defined]
    return base64.b64encode(digest).decode("utf-8")


SHOPIFY_SECRET = "test-shopify-secret"

SAMPLE_ORDER_PAYLOAD = {
    "id": 5001000001,
    "order_number": 1001,
    "name": "#1001",
    "email": "jane@example.com",
    "phone": "+447700900001",
    "financial_status": "paid",
    "fulfillment_status": None,
    "currency": "GBP",
    "subtotal_price": "29.99",
    "total_price": "32.99",
    "total_shipping_price_set": {
        "shop_money": {"amount": "3.00", "currency_code": "GBP"}
    },
    "payment_gateway": "shopify_payments",
    "note": "Please pack carefully",
    "discount_codes": [{"code": "WELCOME10", "amount": "3.00", "type": "fixed_amount"}],
    "shipping_address": {
        "name": "Jane Smith",
        "address1": "42 Dragon Lane",
        "address2": "Flat 3",
        "city": "London",
        "province": "England",
        "zip": "E1 1AA",
        "country": "United Kingdom",
        "phone": "+447700900001",
    },
    "shipping_lines": [{"title": "Royal Mail 2nd Class", "price": "3.00"}],
    "line_items": [
        {
            "id": 9001,
            "title": "Rosyra the Dragon",
            "sku": "DRG-ROSYRA-001",
            "quantity": 1,
            "price": "29.99",
        }
    ],
    "customer": {
        "email": "jane@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "phone": "+447700900001",
    },
}


def _make_webhook_headers(body: bytes, topic: str = "orders/create") -> dict:
    sig = make_signature(body, SHOPIFY_SECRET)
    return {
        "x-shopify-topic": topic,
        "x-shopify-hmac-sha256": sig,
        "content-type": "application/json",
    }


class TestShopifyWebhookSignature:
    """Signature validation tests."""

    @pytest.mark.asyncio
    async def test_missing_signature_rejected_when_secret_configured(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        monkeypatch,
    ):
        """Requests without a valid HMAC should return 401 when secret is set."""
        from app.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "shopify_webhook_secret", SHOPIFY_SECRET)

        body = json.dumps(SAMPLE_ORDER_PAYLOAD).encode()
        response = await async_client.post(
            f"/api/v1/shopify/webhooks/{test_tenant.slug}",
            content=body,
            headers={
                "x-shopify-topic": "orders/create",
                "x-shopify-hmac-sha256": "invalidsignature==",
                "content-type": "application/json",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_signature_accepted(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        monkeypatch,
        db_session,
    ):
        """Valid HMAC signature should result in order creation."""
        from app.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "shopify_webhook_secret", SHOPIFY_SECRET)

        body = json.dumps(SAMPLE_ORDER_PAYLOAD).encode()
        headers = _make_webhook_headers(body)

        response = await async_client.post(
            f"/api/v1/shopify/webhooks/{test_tenant.slug}",
            content=body,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert "SHOP-1001" in data["order_number"]


class TestShopifyOrderCreate:
    """orders/create webhook tests."""

    @pytest.mark.asyncio
    async def test_creates_order_in_batchivo(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        monkeypatch,
        db_session,
    ):
        """Shopify orders/create should produce a new Order record."""
        from app.config import get_settings
        from sqlalchemy import select

        settings = get_settings()
        monkeypatch.setattr(settings, "shopify_webhook_secret", "")  # skip HMAC in this test

        body = json.dumps(SAMPLE_ORDER_PAYLOAD).encode()
        response = await async_client.post(
            f"/api/v1/shopify/webhooks/{test_tenant.slug}",
            content=body,
            headers={
                "x-shopify-topic": "orders/create",
                "x-shopify-hmac-sha256": "",
                "content-type": "application/json",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "created"

        # Verify order persisted
        result = await db_session.execute(
            select(Order).where(
                Order.tenant_id == test_tenant.id,
                Order.order_number == "SHOP-1001",
            )
        )
        order = result.scalar_one_or_none()
        assert order is not None
        assert order.customer_email == "jane@example.com"
        assert order.customer_name == "Jane Smith"
        assert order.shipping_city == "London"
        assert order.shipping_postcode == "E1 1AA"
        assert order.payment_id == "5001000001"
        assert order.payment_provider == "shopify_payments"
        assert order.status == OrderStatus.PENDING
        assert order.discount_code == "WELCOME10"
        assert order.total == Decimal("32.99")
        assert len(order.items) == 1
        assert order.items[0].product_sku == "DRG-ROSYRA-001"

    @pytest.mark.asyncio
    async def test_unknown_tenant_returns_404(
        self,
        async_client: AsyncClient,
        monkeypatch,
    ):
        """Webhook for non-existent tenant slug should return 404."""
        from app.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "shopify_webhook_secret", "")

        body = json.dumps(SAMPLE_ORDER_PAYLOAD).encode()
        response = await async_client.post(
            "/api/v1/shopify/webhooks/nonexistent-tenant-xyz",
            content=body,
            headers={
                "x-shopify-topic": "orders/create",
                "x-shopify-hmac-sha256": "",
                "content-type": "application/json",
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_ignored_topic_returns_ignored(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        monkeypatch,
    ):
        """Unsupported Shopify topics should be acknowledged but ignored."""
        from app.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "shopify_webhook_secret", "")

        body = json.dumps({"id": 123}).encode()
        response = await async_client.post(
            f"/api/v1/shopify/webhooks/{test_tenant.slug}",
            content=body,
            headers={
                "x-shopify-topic": "products/update",
                "x-shopify-hmac-sha256": "",
                "content-type": "application/json",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"


class TestShopifyOrderUpdate:
    """orders/updated webhook tests."""

    @pytest.mark.asyncio
    async def test_updates_existing_order(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        monkeypatch,
        db_session,
    ):
        """orders/updated should update a previously imported order."""
        from app.config import get_settings
        from sqlalchemy import select

        settings = get_settings()
        monkeypatch.setattr(settings, "shopify_webhook_secret", "")

        # First create
        body = json.dumps(SAMPLE_ORDER_PAYLOAD).encode()
        r = await async_client.post(
            f"/api/v1/shopify/webhooks/{test_tenant.slug}",
            content=body,
            headers={
                "x-shopify-topic": "orders/create",
                "x-shopify-hmac-sha256": "",
                "content-type": "application/json",
            },
        )
        assert r.json()["status"] == "created"

        # Now update — mark as fulfilled with tracking
        updated_payload = dict(SAMPLE_ORDER_PAYLOAD)
        updated_payload["fulfillment_status"] = "fulfilled"
        updated_payload["fulfillments"] = [
            {
                "id": 9999,
                "tracking_number": "JD000000000GB",
                "tracking_url": "https://track.royalmail.com/JD000000000GB",
                "created_at": "2026-03-14T10:00:00Z",
            }
        ]
        body2 = json.dumps(updated_payload).encode()
        r2 = await async_client.post(
            f"/api/v1/shopify/webhooks/{test_tenant.slug}",
            content=body2,
            headers={
                "x-shopify-topic": "orders/updated",
                "x-shopify-hmac-sha256": "",
                "content-type": "application/json",
            },
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "updated"

        result = await db_session.execute(
            select(Order).where(
                Order.tenant_id == test_tenant.id,
                Order.order_number == "SHOP-1001",
            )
        )
        order = result.scalar_one_or_none()
        assert order is not None
        assert order.status == OrderStatus.SHIPPED
        assert order.tracking_number == "JD000000000GB"
