"""Tests for Shopify webhook ingest endpoint.

The test environment has SHOPIFY_WEBHOOK_SECRET unset (defaults to ""),
so HMAC validation is skipped for all HTTP endpoint tests.
Signature validation logic is unit-tested directly.
"""

import base64
import hashlib
import hmac
import json
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.api.v1.shopify_webhooks import verify_shopify_hmac
from app.models.order import Order, OrderStatus
from app.models.tenant import Tenant


SHOPIFY_SECRET = "test-shopify-secret-for-unit-tests"

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

# Headers with no HMAC — works in test env where secret defaults to ""
NO_HMAC_HEADERS = {
    "x-shopify-hmac-sha256": "",
    "content-type": "application/json",
}


class TestVerifyShopifyHmac:
    """Unit tests for the HMAC signature verification function."""

    def test_valid_signature(self):
        body = b'{"id": 123}'
        digest = hmac.new(SHOPIFY_SECRET.encode(), body, hashlib.sha256).digest()  # type: ignore[attr-defined]
        sig = base64.b64encode(digest).decode()
        assert verify_shopify_hmac(body, sig, SHOPIFY_SECRET) is True

    def test_invalid_signature_rejected(self):
        body = b'{"id": 123}'
        assert verify_shopify_hmac(body, "invalidsig==", SHOPIFY_SECRET) is False

    def test_empty_secret_returns_false(self):
        body = b'{"id": 123}'
        assert verify_shopify_hmac(body, "anysig==", "") is False

    def test_empty_signature_returns_false(self):
        body = b'{"id": 123}'
        assert verify_shopify_hmac(body, "", SHOPIFY_SECRET) is False

    def test_tampered_body_rejected(self):
        original_body = b'{"id": 123}'
        tampered_body = b'{"id": 456}'
        digest = hmac.new(SHOPIFY_SECRET.encode(), original_body, hashlib.sha256).digest()  # type: ignore[attr-defined]
        sig = base64.b64encode(digest).decode()
        assert verify_shopify_hmac(tampered_body, sig, SHOPIFY_SECRET) is False


class TestShopifyOrderCreate:
    """orders/create webhook integration tests."""

    @pytest.mark.asyncio
    async def test_creates_order_in_batchivo(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        db_session,
    ):
        """Shopify orders/create should produce a new Order record."""
        from sqlalchemy import select

        body = json.dumps(SAMPLE_ORDER_PAYLOAD).encode()
        response = await async_client.post(
            f"/api/v1/shopify/webhooks/{test_tenant.slug}",
            content=body,
            headers={**NO_HMAC_HEADERS, "x-shopify-topic": "orders/create"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "created"
        assert response.json()["order_number"] == "SHOP-1001"

        # Verify order persisted with correct field mapping
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
        assert order.items[0].quantity == 1

    @pytest.mark.asyncio
    async def test_unknown_tenant_returns_404(
        self,
        async_client: AsyncClient,
    ):
        """Webhook for non-existent tenant slug should return 404."""
        body = json.dumps(SAMPLE_ORDER_PAYLOAD).encode()
        response = await async_client.post(
            "/api/v1/shopify/webhooks/nonexistent-tenant-xyz",
            content=body,
            headers={**NO_HMAC_HEADERS, "x-shopify-topic": "orders/create"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_ignored_topic_returns_ignored(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
    ):
        """Unsupported Shopify topics should be acknowledged but skipped."""
        body = json.dumps({"id": 123}).encode()
        response = await async_client.post(
            f"/api/v1/shopify/webhooks/{test_tenant.slug}",
            content=body,
            headers={**NO_HMAC_HEADERS, "x-shopify-topic": "products/update"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_duplicate_create_returns_updated(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        db_session,
    ):
        """Sending orders/create twice for same Shopify ID returns 'updated'."""
        body = json.dumps(SAMPLE_ORDER_PAYLOAD).encode()
        for topic in ("orders/create", "orders/create"):
            response = await async_client.post(
                f"/api/v1/shopify/webhooks/{test_tenant.slug}",
                content=body,
                headers={**NO_HMAC_HEADERS, "x-shopify-topic": topic},
            )
            assert response.status_code == 200

        assert response.json()["status"] == "updated"


class TestShopifyOrderUpdate:
    """orders/updated webhook tests."""

    @pytest.mark.asyncio
    async def test_updates_existing_order_with_tracking(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        db_session,
    ):
        """orders/updated with fulfillment data should update tracking + status."""
        from sqlalchemy import select

        # Create the order first
        body = json.dumps(SAMPLE_ORDER_PAYLOAD).encode()
        r = await async_client.post(
            f"/api/v1/shopify/webhooks/{test_tenant.slug}",
            content=body,
            headers={**NO_HMAC_HEADERS, "x-shopify-topic": "orders/create"},
        )
        assert r.json()["status"] == "created"

        # Update with fulfilment + tracking
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
            headers={**NO_HMAC_HEADERS, "x-shopify-topic": "orders/updated"},
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
