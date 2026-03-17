"""Shopify webhook ingest endpoint.

Receives Shopify orders/create and orders/updated webhook events and
creates or updates corresponding Order records in Batchivo.

Public endpoint — authenticated via HMAC-SHA256 signature validation
using the Shopify API secret (or per-tenant configured secret).

Endpoint: POST /api/v1/shopify/webhooks/{tenant_slug}
"""

import base64
import hashlib
import hmac
import json
import logging
from decimal import Decimal
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.shop_resolver import resolve_tenant_by_slug
from app.config import get_settings
from app.database import get_db
from app.models.order import Order, OrderItem, OrderStatus
from app.models.sales_channel import SalesChannel

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


def verify_shopify_hmac(body: bytes, signature_b64: str, secret: str) -> bool:
    """Verify Shopify HMAC-SHA256 webhook signature.

    Shopify signs the raw request body with HMAC-SHA256 using the
    webhook secret and encodes the result as base64.

    Args:
        body: Raw request body bytes
        signature_b64: Base64-encoded HMAC from X-Shopify-Hmac-Sha256 header
        secret: Shopify webhook secret (API secret key)

    Returns:
        True if signature is valid, False otherwise
    """
    if not secret or not signature_b64:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature_b64)


def _map_shopify_status(financial_status: str, fulfillment_status: Optional[str]) -> str:
    """Map Shopify financial + fulfillment status to Batchivo OrderStatus."""
    if financial_status in ("refunded", "voided"):
        return OrderStatus.REFUNDED
    if financial_status == "cancelled" or fulfillment_status == "cancelled":
        return OrderStatus.CANCELLED
    if fulfillment_status in ("fulfilled", "partial"):
        return OrderStatus.SHIPPED
    if financial_status == "paid":
        return OrderStatus.PENDING
    return OrderStatus.PENDING


def _extract_order_data(payload: dict) -> dict:
    """Extract and normalise fields from a Shopify order webhook payload."""
    shipping_addr = payload.get("shipping_address") or {}
    billing_addr = payload.get("billing_address") or {}
    customer = payload.get("customer") or {}

    # Resolve customer name: prefer shipping_address.name, fall back to customer fields
    customer_name = (
        shipping_addr.get("name")
        or f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        or "Unknown"
    )

    # Resolve email: order email takes precedence
    customer_email = payload.get("email") or customer.get("email") or ""

    # Resolve shipping address
    addr1 = shipping_addr.get("address1") or billing_addr.get("address1") or ""
    addr2 = shipping_addr.get("address2") or billing_addr.get("address2")
    city = shipping_addr.get("city") or billing_addr.get("city") or ""
    county = shipping_addr.get("province") or billing_addr.get("province")
    postcode = shipping_addr.get("zip") or billing_addr.get("zip") or ""
    country = shipping_addr.get("country") or billing_addr.get("country") or "United Kingdom"
    phone = shipping_addr.get("phone") or customer.get("phone") or payload.get("phone")

    # Shipping method
    shipping_lines = payload.get("shipping_lines") or []
    shipping_method = shipping_lines[0].get("title") if shipping_lines else "Standard"
    shipping_cost = Decimal(
        str(
            payload.get("total_shipping_price_set", {}).get("shop_money", {}).get("amount", "0")
            or shipping_lines[0].get("price", "0")
            if shipping_lines
            else "0"
        )
    )

    # Financials
    subtotal = Decimal(str(payload.get("subtotal_price") or "0"))
    total = Decimal(str(payload.get("total_price") or "0"))
    currency = payload.get("currency") or "GBP"

    # Discount
    discount_codes = payload.get("discount_codes") or []
    discount_code = discount_codes[0].get("code") if discount_codes else None
    discount_amount = (
        Decimal(str(discount_codes[0].get("amount", "0"))) if discount_codes else Decimal("0")
    )

    # Payment
    payment_gateway = payload.get("payment_gateway") or "shopify"

    # Notes
    customer_notes = payload.get("note")

    # Financial / fulfillment status
    financial_status = payload.get("financial_status") or "pending"
    fulfillment_status = payload.get("fulfillment_status")

    return {
        "customer_email": customer_email,
        "customer_name": customer_name,
        "customer_phone": phone,
        "shipping_address_line1": addr1,
        "shipping_address_line2": addr2,
        "shipping_city": city,
        "shipping_county": county,
        "shipping_postcode": postcode,
        "shipping_country": country,
        "shipping_method": shipping_method,
        "shipping_cost": shipping_cost,
        "subtotal": subtotal,
        "total": total,
        "currency": currency,
        "discount_code": discount_code,
        "discount_amount": discount_amount,
        "payment_provider": payment_gateway,
        "customer_notes": customer_notes,
        "status": _map_shopify_status(financial_status, fulfillment_status),
    }


async def _get_or_create_shopify_channel(db: AsyncSession, tenant_id, slug: str) -> Optional[str]:
    """Return the Shopify sales channel ID for the tenant, creating if needed."""
    result = await db.execute(
        select(SalesChannel).where(
            SalesChannel.tenant_id == tenant_id,
            SalesChannel.platform_type == "shopify",
            SalesChannel.is_active.is_(True),
        )
    )
    channel = result.scalar_one_or_none()
    if channel:
        return channel.id

    # Create a Shopify channel
    channel = SalesChannel(
        tenant_id=tenant_id,
        name="Shopify",
        platform_type="shopify",
        is_active=True,
    )
    db.add(channel)
    await db.flush()
    return channel.id


@router.post("/webhooks/{tenant_slug}")
async def shopify_webhook(
    tenant_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive and process a Shopify webhook event.

    Validates the HMAC-SHA256 signature from Shopify, then creates or
    updates the corresponding Batchivo order.

    Shopify requires a 200 response within 5 seconds. Processing is
    synchronous but kept lightweight — no external calls other than DB.

    Headers expected:
        X-Shopify-Hmac-Sha256: base64(HMAC-SHA256(secret, body))
        X-Shopify-Topic:        orders/create | orders/updated
    """
    body = await request.body()
    topic = request.headers.get("x-shopify-topic", "")
    signature = request.headers.get("x-shopify-hmac-sha256", "")

    # Verify signature (skip in dev if no secret configured)
    if settings.shopify_webhook_secret:
        if not verify_shopify_hmac(body, signature, settings.shopify_webhook_secret):
            logger.warning(
                f"Invalid Shopify webhook signature for tenant={tenant_slug} topic={topic}"
            )
            raise HTTPException(status_code=401, detail="Invalid signature")
    else:
        logger.warning("shopify_webhook_secret not set — skipping HMAC validation")

    # Resolve tenant
    tenant = await resolve_tenant_by_slug(db, tenant_slug)
    if not tenant:
        logger.warning(f"Shopify webhook received for unknown tenant slug: {tenant_slug}")
        raise HTTPException(status_code=404, detail="Tenant not found")

    if topic not in ("orders/create", "orders/updated"):
        logger.info(f"Ignoring Shopify topic: {topic}")
        return {"status": "ignored", "topic": topic}

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    shopify_order_id = str(payload.get("id", ""))
    shopify_order_number = payload.get("order_number") or payload.get("name") or shopify_order_id
    batchivo_order_number = f"SHOP-{shopify_order_number}"

    logger.info(
        f"Processing Shopify {topic} for tenant={tenant_slug} "
        f"shopify_id={shopify_order_id} order_number={shopify_order_number}"
    )

    # Look up existing order by payment_id (Shopify order ID stored there)
    existing_result = await db.execute(
        select(Order).where(
            Order.tenant_id == tenant.id,
            Order.payment_id == shopify_order_id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    data = _extract_order_data(payload)

    if existing:
        # Update existing order
        if topic == "orders/updated":
            for field, value in data.items():
                setattr(existing, field, value)

            # Handle fulfillment: if Shopify says fulfilled, update tracking
            fulfillments = payload.get("fulfillments") or []
            if fulfillments:
                latest = fulfillments[-1]
                if latest.get("tracking_number"):
                    existing.tracking_number = latest["tracking_number"]
                if latest.get("tracking_url"):
                    existing.tracking_url = latest["tracking_url"]
                if latest.get("created_at") and not existing.shipped_at:
                    existing.shipped_at = datetime.now(timezone.utc)

            existing.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"Updated Batchivo order {existing.order_number} from Shopify {topic}")
        return {"status": "updated", "order_number": existing.order_number}

    # Create new order
    if topic == "orders/updated" and not existing:
        # Treat as create if we haven't seen this order before
        logger.info(
            f"orders/updated received for unseen Shopify order {shopify_order_id} — creating"
        )

    sales_channel_id = await _get_or_create_shopify_channel(db, tenant.id, tenant_slug)

    order = Order(
        tenant_id=tenant.id,
        order_number=batchivo_order_number,
        sales_channel_id=sales_channel_id,
        payment_id=shopify_order_id,
        **data,
    )
    db.add(order)

    # Add line items
    line_items = payload.get("line_items") or []
    for item in line_items:
        unit_price = Decimal(str(item.get("price") or "0"))
        qty = int(item.get("quantity") or 1)
        order_item = OrderItem(
            tenant_id=tenant.id,
            product_sku=item.get("sku") or item.get("variant_title") or "UNKNOWN",
            product_name=item.get("title") or "Unknown Product",
            quantity=qty,
            unit_price=unit_price,
            total_price=unit_price * qty,
        )
        order.items.append(order_item)

    await db.commit()
    logger.info(
        f"Created Batchivo order {batchivo_order_number} from Shopify {topic} "
        f"(shopify_id={shopify_order_id})"
    )
    return {"status": "created", "order_number": batchivo_order_number}
