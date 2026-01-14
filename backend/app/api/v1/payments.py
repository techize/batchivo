"""Payment processing API endpoints for multi-tenant shops."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import ShopContext
from app.config import get_settings
from app.database import get_db
from app.models.order import Order as OrderModel, OrderItem as OrderItemModel, OrderStatus
from app.models.product import Product
from app.schemas.payment import PaymentRequest, PaymentResponse, PaymentError
from app.services.square_payment import get_payment_service
from app.services.email_service import get_email_service

router = APIRouter()
settings = get_settings()


class PaymentConfigResponse(BaseModel):
    """Response with payment configuration (for frontend)."""

    enabled: bool
    environment: str
    app_id: str | None = None
    location_id: str | None = None


@router.get("/config", response_model=PaymentConfigResponse)
async def get_payment_config() -> PaymentConfigResponse:
    """
    Get payment configuration for Square Web Payments SDK.

    Returns app_id, location_id, and environment needed by the frontend
    to initialize the Square Web Payments SDK. The access_token is NOT
    exposed as it's only needed server-side.

    This endpoint is public - no auth required.
    """
    enabled = bool(settings.square_access_token and settings.square_location_id)
    return PaymentConfigResponse(
        enabled=enabled,
        environment=settings.square_environment,
        app_id=settings.square_app_id if enabled else None,
        location_id=settings.square_location_id if enabled else None,
    )


@router.post("/process", response_model=PaymentResponse)
async def process_payment(
    request: PaymentRequest,
    shop_context: ShopContext,
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """
    Process a payment using a Square Web Payments SDK token.

    This endpoint receives the tokenized card details from the frontend
    and processes the actual payment through Square's API.

    Uses order_number as idempotency key to prevent duplicate charges.
    Tenant resolved from X-Shop-Hostname header.
    """
    import logging

    logger = logging.getLogger(__name__)
    shop_tenant, channel = shop_context

    # Validate configuration
    if not settings.square_access_token or not settings.square_location_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    # Validate amount matches items + shipping
    items_total = sum(item.price * item.quantity for item in request.items)
    expected_total = items_total + request.shipping_cost

    if request.amount != expected_total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount mismatch: received {request.amount}, expected {expected_total}",
        )

    # Generate order_number BEFORE payment to use as idempotency key
    # This ensures retries don't create duplicate charges (Square 24-hour window)
    # Get order prefix from tenant settings, fallback to uppercase slug
    tenant_settings = shop_tenant.settings or {}
    shop_settings = tenant_settings.get("shop", {})
    order_prefix = shop_settings.get("order_prefix") or shop_tenant.slug.upper()[:4]

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    order_count_result = await db.execute(
        select(OrderModel).where(
            OrderModel.tenant_id == shop_tenant.id,
            OrderModel.order_number.like(f"{order_prefix}-{today}-%"),
        )
    )
    existing_orders = order_count_result.scalars().all()
    order_seq = len(existing_orders) + 1
    order_number = f"{order_prefix}-{today}-{order_seq:03d}"

    # Use order_number as idempotency key (or client-provided key if given)
    idempotency_key = request.idempotency_key or order_number
    request.idempotency_key = idempotency_key

    logger.info(
        f"Processing payment for order {order_number} with idempotency_key={idempotency_key}"
    )

    # Process the payment
    payment_service = get_payment_service()
    result = payment_service.process_payment(request)

    if isinstance(result, PaymentError):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error_code": result.error_code,
                "error_message": result.error_message,
                "detail": result.detail,
            },
        )

    # Create order record in database
    try:
        # Channel already resolved from ShopContext

        # Build customer name from shipping address
        customer_name = (
            f"{request.shipping_address.first_name} {request.shipping_address.last_name}"
        )

        # Create order using resolved tenant
        db_order = OrderModel(
            tenant_id=shop_tenant.id,
            sales_channel_id=channel.id,
            order_number=order_number,
            status=OrderStatus.PENDING,
            customer_email=request.customer.email,
            customer_name=customer_name,
            customer_phone=request.customer.phone,
            shipping_address_line1=request.shipping_address.address_line1,
            shipping_address_line2=request.shipping_address.address_line2,
            shipping_city=request.shipping_address.city,
            shipping_county=request.shipping_address.county,
            shipping_postcode=request.shipping_address.postcode,
            shipping_country=request.shipping_address.country,
            shipping_method=request.shipping_method,
            shipping_cost=request.shipping_cost / 100,  # Convert pence to pounds
            subtotal=items_total / 100,  # Convert pence to pounds
            total=request.amount / 100,  # Convert pence to pounds
            currency=request.currency,
            payment_provider="square",
            payment_id=result.payment_id,
            payment_status=result.status,
        )
        db.add(db_order)
        await db.flush()  # Get the order ID

        # Create order items
        # Look up each product to get its real SKU and link properly
        for item in request.items:
            # Try to find product in Batchivo DB by product ID
            # SECURITY: Must filter by tenant_id to prevent cross-tenant data leakage
            product_result = await db.execute(
                select(Product).where(
                    Product.id == item.product_id,
                    Product.tenant_id == shop_tenant.id,  # Enforce tenant isolation
                )
            )
            product = product_result.scalar_one_or_none()

            if product:
                # Product exists in Batchivo - use real SKU and link
                db_item = OrderItemModel(
                    tenant_id=shop_tenant.id,
                    order_id=db_order.id,
                    product_id=product.id,
                    product_sku=product.sku,
                    product_name=item.name,
                    quantity=item.quantity,
                    unit_price=item.price / 100,  # Convert pence to pounds
                    total_price=(item.price * item.quantity) / 100,  # Convert pence to pounds
                )
            else:
                # Product not found - store ID as reference (fallback)
                db_item = OrderItemModel(
                    tenant_id=shop_tenant.id,
                    order_id=db_order.id,
                    product_id=None,
                    product_sku=str(item.product_id),
                    product_name=item.name,
                    quantity=item.quantity,
                    unit_price=item.price / 100,  # Convert pence to pounds
                    total_price=(item.price * item.quantity) / 100,  # Convert pence to pounds
                )
            db.add(db_item)

        await db.commit()

        # Update result with actual order number
        result.order_id = order_number

        # Send confirmation email and track result
        email_service = get_email_service()
        email_sent = email_service.send_order_confirmation(
            to_email=request.customer.email,
            customer_name=customer_name,
            order_number=order_number,
            order_items=[
                {
                    "name": item.name,
                    "quantity": item.quantity,
                    "price": item.price / 100,  # Convert pence to pounds
                }
                for item in request.items
            ],
            subtotal=items_total / 100,
            shipping_cost=request.shipping_cost / 100,
            total=request.amount / 100,
            shipping_address={
                "address_line1": request.shipping_address.address_line1,
                "address_line2": request.shipping_address.address_line2,
                "city": request.shipping_address.city,
                "county": request.shipping_address.county,
                "postcode": request.shipping_address.postcode,
                "country": request.shipping_address.country,
            },
            receipt_url=result.receipt_url,
        )

        # Update order with email status
        db_order.confirmation_email_sent = email_sent
        if email_sent:
            db_order.confirmation_email_sent_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception as e:
        # Log error but don't fail the payment - it already succeeded
        import logging

        logging.error(f"Failed to create order record: {e}")
        # The payment was successful, so we still return success
        # Order can be reconciled from Square dashboard if needed

    return result


@router.get("/status/{payment_id}")
async def get_payment_status(payment_id: str) -> dict:
    """
    Get the status of a payment by ID.

    This can be used to verify payment status after processing.
    """
    if not settings.square_access_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    payment_service = get_payment_service()
    payment = payment_service.get_payment(payment_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    return {
        "payment_id": payment.get("id"),
        "status": payment.get("status"),
        "amount": payment.get("amount_money", {}).get("amount"),
        "currency": payment.get("amount_money", {}).get("currency"),
        "receipt_url": payment.get("receipt_url"),
    }


# ============================================
# Webhook Endpoints
# ============================================


class WebhookResponse(BaseModel):
    """Response for webhook endpoint."""

    status: str = "received"


@router.post("/webhooks/square", response_model=WebhookResponse)
async def square_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """
    Handle Square webhook events.

    Square sends webhooks for payment events like payment.completed,
    payment.updated, refund.created, etc.

    Validates signature and processes events asynchronously.
    Returns 200 immediately to acknowledge receipt.
    """
    import hashlib
    import hmac
    import logging

    logger = logging.getLogger(__name__)

    # Get request body and signature
    body = await request.body()
    signature = request.headers.get("x-square-hmacsha256-signature", "")
    notification_url = str(request.url)

    # Validate signature if webhook key is configured
    if settings.square_webhook_signature_key:
        # Square uses HMAC-SHA256 with the notification URL + body
        # https://developer.squareup.com/docs/webhooks/validate-notifications
        string_to_sign = notification_url + body.decode("utf-8")
        expected_signature = hmac.new(
            settings.square_webhook_signature_key.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        import base64

        expected_signature_b64 = base64.b64encode(expected_signature).decode("utf-8")

        if not hmac.compare_digest(signature, expected_signature_b64):
            logger.warning("Invalid Square webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse webhook event
    try:
        import json

        event = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook body")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("type", "")
    event_data = event.get("data", {}).get("object", {})

    logger.info(f"Received Square webhook: type={event_type}")

    # Process different event types
    try:
        if event_type == "payment.created":
            await _handle_payment_created(event_data, db, logger)
        elif event_type == "payment.updated":
            await _handle_payment_updated(event_data, db, logger)
        elif event_type == "refund.created":
            await _handle_refund_created(event_data, db, logger)
        elif event_type == "refund.updated":
            await _handle_refund_updated(event_data, db, logger)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
    except Exception as e:
        # Log but don't fail - we've received the webhook
        logger.error(f"Error processing webhook: {e}")

    # Always return 200 to acknowledge receipt
    return WebhookResponse(status="received")


async def _handle_payment_created(payment: dict, db: AsyncSession, logger) -> None:
    """Handle payment.created webhook event."""
    payment_id = payment.get("payment", {}).get("id")
    status = payment.get("payment", {}).get("status")
    logger.info(f"Payment created: payment_id={payment_id} status={status}")
    # Payment is typically already recorded during checkout
    # This is mainly for logging/auditing


async def _handle_payment_updated(payment: dict, db: AsyncSession, logger) -> None:
    """Handle payment.updated webhook event."""
    payment_data = payment.get("payment", {})
    payment_id = payment_data.get("id")
    new_status = payment_data.get("status")

    logger.info(f"Payment updated: payment_id={payment_id} status={new_status}")

    # Find and update order payment status
    result = await db.execute(select(OrderModel).where(OrderModel.payment_id == payment_id))
    order = result.scalar_one_or_none()

    if order:
        order.payment_status = new_status
        order.updated_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(f"Updated order {order.order_number} payment_status to {new_status}")
    else:
        logger.warning(f"No order found for payment_id={payment_id}")


async def _handle_refund_created(refund: dict, db: AsyncSession, logger) -> None:
    """Handle refund.created webhook event."""
    refund_data = refund.get("refund", {})
    refund_id = refund_data.get("id")
    payment_id = refund_data.get("payment_id")
    status = refund_data.get("status")
    amount = refund_data.get("amount_money", {}).get("amount", 0)

    logger.info(
        f"Refund created: refund_id={refund_id} payment_id={payment_id} "
        f"status={status} amount={amount}"
    )

    # Find and update order status to refunded
    result = await db.execute(select(OrderModel).where(OrderModel.payment_id == payment_id))
    order = result.scalar_one_or_none()

    if order and status == "COMPLETED":
        order.status = OrderStatus.REFUNDED
        order.payment_status = "REFUNDED"
        order.updated_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(f"Updated order {order.order_number} to REFUNDED status")
    elif order:
        logger.info(f"Refund pending for order {order.order_number}: status={status}")
    else:
        logger.warning(f"No order found for payment_id={payment_id}")


async def _handle_refund_updated(refund: dict, db: AsyncSession, logger) -> None:
    """Handle refund.updated webhook event."""
    refund_data = refund.get("refund", {})
    refund_id = refund_data.get("id")
    payment_id = refund_data.get("payment_id")
    status = refund_data.get("status")

    logger.info(f"Refund updated: refund_id={refund_id} status={status}")

    if status == "COMPLETED":
        # Find and update order status
        result = await db.execute(select(OrderModel).where(OrderModel.payment_id == payment_id))
        order = result.scalar_one_or_none()

        if order:
            order.status = OrderStatus.REFUNDED
            order.payment_status = "REFUNDED"
            order.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"Updated order {order.order_number} to REFUNDED status")
