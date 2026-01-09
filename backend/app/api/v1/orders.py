"""Orders API endpoints for managing customer orders."""

from datetime import datetime, timezone, date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.order import Order, OrderStatus
from app.auth.dependencies import CurrentTenant, RequireAdmin

router = APIRouter()


# ============================================
# Schemas
# ============================================


class OrderItemResponse(BaseModel):
    """Order item response."""

    id: str
    product_id: Optional[str] = None
    product_sku: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Order response."""

    id: str
    order_number: str
    status: str
    customer_email: str
    customer_name: str
    customer_phone: Optional[str] = None
    shipping_address_line1: str
    shipping_address_line2: Optional[str] = None
    shipping_city: str
    shipping_county: Optional[str] = None
    shipping_postcode: str
    shipping_country: str
    shipping_method: str
    shipping_cost: float
    subtotal: float
    total: float
    currency: str
    payment_provider: str
    payment_id: Optional[str] = None
    payment_status: str
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    customer_notes: Optional[str] = None
    internal_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Paginated order list response."""

    data: list[OrderResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class UpdateOrderRequest(BaseModel):
    """Request to update an order."""

    status: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    internal_notes: Optional[str] = None


class ShipOrderRequest(BaseModel):
    """Request to mark an order as shipped."""

    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None


class OrderCountsResponse(BaseModel):
    """Order counts by status."""

    pending: int
    processing: int
    shipped: int
    delivered: int
    cancelled: int
    refunded: int
    total: int


# ============================================
# Endpoints
# ============================================


@router.get("", response_model=OrderListResponse)
async def list_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(
        None, description="Search by order number, customer name, or email"
    ),
    date_from: Optional[date] = Query(None, description="Filter orders from this date (inclusive)"),
    date_to: Optional[date] = Query(None, description="Filter orders to this date (inclusive)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """List all orders for the current tenant with filtering options."""
    # Build base query
    query = (
        select(Order)
        .where(Order.tenant_id == tenant.id)
        .options(selectinload(Order.items))
        .order_by(desc(Order.created_at))
    )

    # Build count query with same filters
    count_query = select(func.count(Order.id)).where(Order.tenant_id == tenant.id)

    # Apply status filter
    if status:
        query = query.where(Order.status == status)
        count_query = count_query.where(Order.status == status)

    # Apply search filter (case-insensitive)
    if search:
        search_term = f"%{search.lower()}%"
        search_filter = or_(
            func.lower(Order.order_number).like(search_term),
            func.lower(Order.customer_name).like(search_term),
            func.lower(Order.customer_email).like(search_term),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Apply date range filter
    if date_from:
        from_datetime = datetime.combine(date_from, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        query = query.where(Order.created_at >= from_datetime)
        count_query = count_query.where(Order.created_at >= from_datetime)

    if date_to:
        to_datetime = datetime.combine(date_to, datetime.max.time()).replace(tzinfo=timezone.utc)
        query = query.where(Order.created_at <= to_datetime)
        count_query = count_query.where(Order.created_at <= to_datetime)

    # Get total count with filters applied
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)

    # Execute query
    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        data=[
            OrderResponse(
                id=str(order.id),
                order_number=order.order_number,
                status=order.status,
                customer_email=order.customer_email,
                customer_name=order.customer_name,
                customer_phone=order.customer_phone,
                shipping_address_line1=order.shipping_address_line1,
                shipping_address_line2=order.shipping_address_line2,
                shipping_city=order.shipping_city,
                shipping_county=order.shipping_county,
                shipping_postcode=order.shipping_postcode,
                shipping_country=order.shipping_country,
                shipping_method=order.shipping_method,
                shipping_cost=float(order.shipping_cost),
                subtotal=float(order.subtotal),
                total=float(order.total),
                currency=order.currency,
                payment_provider=order.payment_provider,
                payment_id=order.payment_id,
                payment_status=order.payment_status,
                tracking_number=order.tracking_number,
                tracking_url=order.tracking_url,
                shipped_at=order.shipped_at,
                delivered_at=order.delivered_at,
                fulfilled_at=order.fulfilled_at,
                customer_notes=order.customer_notes,
                internal_notes=order.internal_notes,
                created_at=order.created_at,
                updated_at=order.updated_at,
                items=[
                    OrderItemResponse(
                        id=str(item.id),
                        product_id=str(item.product_id) if item.product_id else None,
                        product_sku=item.product_sku,
                        product_name=item.product_name,
                        quantity=item.quantity,
                        unit_price=float(item.unit_price),
                        total_price=float(item.total_price),
                    )
                    for item in order.items
                ],
            )
            for order in orders
        ],
        total=total,
        page=page,
        limit=limit,
        has_more=page * limit < total,
    )


@router.get("/counts", response_model=OrderCountsResponse)
async def get_order_counts(
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """Get order counts by status for the current tenant."""
    counts = {}
    for status in [
        OrderStatus.PENDING,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
    ]:
        result = await db.execute(
            select(func.count(Order.id)).where(
                Order.tenant_id == tenant.id,
                Order.status == status,
            )
        )
        counts[status] = result.scalar() or 0

    return OrderCountsResponse(
        pending=counts[OrderStatus.PENDING],
        processing=counts[OrderStatus.PROCESSING],
        shipped=counts[OrderStatus.SHIPPED],
        delivered=counts[OrderStatus.DELIVERED],
        cancelled=counts[OrderStatus.CANCELLED],
        refunded=counts[OrderStatus.REFUNDED],
        total=sum(counts.values()),
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """Get a specific order by ID."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tenant.id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderResponse(
        id=str(order.id),
        order_number=order.order_number,
        status=order.status,
        customer_email=order.customer_email,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        shipping_address_line1=order.shipping_address_line1,
        shipping_address_line2=order.shipping_address_line2,
        shipping_city=order.shipping_city,
        shipping_county=order.shipping_county,
        shipping_postcode=order.shipping_postcode,
        shipping_country=order.shipping_country,
        shipping_method=order.shipping_method,
        shipping_cost=float(order.shipping_cost),
        subtotal=float(order.subtotal),
        total=float(order.total),
        currency=order.currency,
        payment_provider=order.payment_provider,
        payment_id=order.payment_id,
        payment_status=order.payment_status,
        tracking_number=order.tracking_number,
        tracking_url=order.tracking_url,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
        fulfilled_at=order.fulfilled_at,
        customer_notes=order.customer_notes,
        internal_notes=order.internal_notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[
            OrderItemResponse(
                id=str(item.id),
                product_id=str(item.product_id) if item.product_id else None,
                product_sku=item.product_sku,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                total_price=float(item.total_price),
            )
            for item in order.items
        ],
    )


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: UUID,
    request: UpdateOrderRequest,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """Update an order (status, tracking, notes)."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tenant.id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Update fields
    if request.status is not None:
        valid_statuses = [
            OrderStatus.PENDING,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED,
        ]
        if request.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
        order.status = request.status

    if request.tracking_number is not None:
        order.tracking_number = request.tracking_number

    if request.tracking_url is not None:
        order.tracking_url = request.tracking_url

    if request.internal_notes is not None:
        order.internal_notes = request.internal_notes

    order.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(order)

    return OrderResponse(
        id=str(order.id),
        order_number=order.order_number,
        status=order.status,
        customer_email=order.customer_email,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        shipping_address_line1=order.shipping_address_line1,
        shipping_address_line2=order.shipping_address_line2,
        shipping_city=order.shipping_city,
        shipping_county=order.shipping_county,
        shipping_postcode=order.shipping_postcode,
        shipping_country=order.shipping_country,
        shipping_method=order.shipping_method,
        shipping_cost=float(order.shipping_cost),
        subtotal=float(order.subtotal),
        total=float(order.total),
        currency=order.currency,
        payment_provider=order.payment_provider,
        payment_id=order.payment_id,
        payment_status=order.payment_status,
        tracking_number=order.tracking_number,
        tracking_url=order.tracking_url,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
        fulfilled_at=order.fulfilled_at,
        customer_notes=order.customer_notes,
        internal_notes=order.internal_notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[
            OrderItemResponse(
                id=str(item.id),
                product_id=str(item.product_id) if item.product_id else None,
                product_sku=item.product_sku,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                total_price=float(item.total_price),
            )
            for item in order.items
        ],
    )


@router.post("/{order_id}/ship")
async def ship_order(
    order_id: UUID,
    request: ShipOrderRequest,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Mark an order as shipped with optional tracking info.

    Auto-fulfills the order (deducts inventory) if not already fulfilled.
    Sends a shipped notification email to the customer.
    """
    from app.services.order_fulfillment import OrderFulfillmentService
    from app.services.email_service import get_email_service
    import logging

    logger = logging.getLogger(__name__)

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tenant.id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
        raise HTTPException(
            status_code=400, detail=f"Cannot ship order with status: {order.status}"
        )

    # Auto-fulfill if not already fulfilled
    if not order.fulfilled_at:
        service = OrderFulfillmentService(db, tenant)

        # Validate and deduct inventory
        validation = await service.validate_inventory(order)
        if not validation.success:
            items_detail = ", ".join(
                f"{item.product_sku} (need {item.required}, have {item.available})"
                for item in validation.insufficient_items
            )
            raise HTTPException(
                status_code=400,
                detail=f"Cannot ship - insufficient inventory: {items_detail}",
            )

        fulfillment_result = await service.deduct_inventory(order)
        if not fulfillment_result.success:
            items_detail = ", ".join(
                f"{item.product_sku} (need {item.required}, have {item.available})"
                for item in fulfillment_result.insufficient_items
            )
            raise HTTPException(
                status_code=400,
                detail=f"Cannot ship - failed to deduct inventory: {items_detail}",
            )

    order.status = OrderStatus.SHIPPED
    order.shipped_at = datetime.now(timezone.utc)
    if request.tracking_number:
        order.tracking_number = request.tracking_number
    if request.tracking_url:
        order.tracking_url = request.tracking_url
    order.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Send shipped notification email
    try:
        email_service = get_email_service()
        email_sent = email_service.send_order_shipped(
            to_email=order.customer_email,
            customer_name=order.customer_name,
            order_number=order.order_number,
            tracking_number=order.tracking_number,
            tracking_url=order.tracking_url,
            shipping_method=order.shipping_method,
        )
        if email_sent:
            order.shipped_email_sent = True
            order.shipped_email_sent_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"Shipped email sent for order {order.order_number}")
        else:
            logger.warning(f"Failed to send shipped email for order {order.order_number}")
    except Exception as e:
        logger.error(f"Error sending shipped email for order {order.order_number}: {e}")

    return {"message": f"Order {order.order_number} marked as shipped"}


@router.post("/{order_id}/deliver")
async def deliver_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Mark an order as delivered.

    Sends a delivered notification email to the customer.
    """
    from app.services.email_service import get_email_service
    import logging

    logger = logging.getLogger(__name__)

    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant.id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.SHIPPED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mark as delivered - order is not shipped (status: {order.status})",
        )

    order.status = OrderStatus.DELIVERED
    order.delivered_at = datetime.now(timezone.utc)
    order.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Send delivered notification email
    try:
        email_service = get_email_service()
        email_sent = email_service.send_order_delivered(
            to_email=order.customer_email,
            customer_name=order.customer_name,
            order_number=order.order_number,
        )
        if email_sent:
            order.delivered_email_sent = True
            order.delivered_email_sent_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"Delivered email sent for order {order.order_number}")
        else:
            logger.warning(f"Failed to send delivered email for order {order.order_number}")
    except Exception as e:
        logger.error(f"Error sending delivered email for order {order.order_number}: {e}")

    return {"message": f"Order {order.order_number} marked as delivered"}


class FulfillOrderResponse(BaseModel):
    """Response for fulfill order endpoint."""

    message: str
    low_stock_alerts: list[dict] = []


@router.post("/{order_id}/fulfill", response_model=FulfillOrderResponse)
async def fulfill_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Fulfill an order by deducting inventory for all items.

    This should be called before shipping to ensure inventory is properly allocated.
    Returns 400 if insufficient inventory is available.
    """
    from app.services.order_fulfillment import OrderFulfillmentService

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tenant.id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only pending/processing orders can be fulfilled
    if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot fulfill order with status: {order.status}",
        )

    # Check if already fulfilled
    if order.fulfilled_at:
        raise HTTPException(
            status_code=400,
            detail="Order has already been fulfilled",
        )

    # Use fulfillment service
    service = OrderFulfillmentService(db, tenant)

    # First validate inventory
    validation = await service.validate_inventory(order)
    if not validation.success:
        items_detail = ", ".join(
            f"{item.product_sku} (need {item.required}, have {item.available})"
            for item in validation.insufficient_items
        )
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient inventory: {items_detail}",
        )

    # Deduct inventory
    fulfillment_result = await service.deduct_inventory(order)
    if not fulfillment_result.success:
        items_detail = ", ".join(
            f"{item.product_sku} (need {item.required}, have {item.available})"
            for item in fulfillment_result.insufficient_items
        )
        raise HTTPException(
            status_code=400,
            detail=f"Failed to deduct inventory: {items_detail}",
        )

    # Check for low stock alerts
    low_stock_alerts = await service.check_low_stock_alerts(order)

    await db.commit()

    return FulfillOrderResponse(
        message=f"Order {order.order_number} has been fulfilled",
        low_stock_alerts=low_stock_alerts,
    )


class CancelOrderRequest(BaseModel):
    """Request to cancel an order."""

    reason: Optional[str] = None


class RefundOrderRequest(BaseModel):
    """Request to refund an order."""

    reason: Optional[str] = None
    amount: Optional[float] = None  # Optional partial refund amount in pounds


class RefundOrderResponse(BaseModel):
    """Response for refund order endpoint."""

    message: str
    refund_id: Optional[str] = None
    refund_status: Optional[str] = None
    refund_amount: Optional[float] = None


class ResendEmailRequest(BaseModel):
    """Request to resend an order email."""

    email_type: str  # "confirmation", "shipped", "delivered"


class ResendEmailResponse(BaseModel):
    """Response for resend email endpoint."""

    message: str
    email_sent: bool


@router.post("/{order_id}/refund", response_model=RefundOrderResponse)
async def refund_order(
    order_id: UUID,
    request: RefundOrderRequest,
    tenant: CurrentTenant,
    _: RequireAdmin,
    db: AsyncSession = Depends(get_db),
):
    """
    Refund an order through Square.

    Processes a full or partial refund through Square's API, updates the order status,
    and restores inventory if the order was fulfilled.

    Sends a refund confirmation email to the customer.
    """
    from app.services.order_fulfillment import OrderFulfillmentService
    from app.services.square_payment import get_payment_service
    from app.services.email_service import get_email_service
    import logging

    logger = logging.getLogger(__name__)

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tenant.id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Validate order can be refunded
    if order.status == OrderStatus.REFUNDED:
        raise HTTPException(status_code=400, detail="Order has already been refunded")

    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot refund a cancelled order")

    if not order.payment_id:
        raise HTTPException(
            status_code=400,
            detail="No payment ID found - cannot process refund",
        )

    if order.payment_provider != "square":
        raise HTTPException(
            status_code=400,
            detail=f"Refunds only supported for Square payments (provider: {order.payment_provider})",
        )

    # Calculate refund amount (in pence)
    if request.amount:
        # Partial refund
        refund_amount_pence = int(request.amount * 100)
        if refund_amount_pence > int(order.total * 100):
            raise HTTPException(
                status_code=400,
                detail=f"Refund amount £{request.amount} exceeds order total £{order.total}",
            )
    else:
        # Full refund
        refund_amount_pence = int(order.total * 100)

    logger.info(
        f"Processing refund for order {order.order_number}: "
        f"amount={refund_amount_pence} pence, payment_id={order.payment_id}"
    )

    # Process refund through Square
    payment_service = get_payment_service()
    refund_result = payment_service.refund_payment(
        payment_id=order.payment_id,
        amount=refund_amount_pence,
        currency=order.currency,
        reason=request.reason or f"Refund for order {order.order_number}",
        idempotency_key=f"refund-{order.order_number}",
    )

    if not refund_result.get("success"):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": refund_result.get("error_code"),
                "error_message": refund_result.get("error_message"),
                "detail": refund_result.get("detail"),
            },
        )

    # Revert inventory if order was fulfilled
    inventory_reverted = False
    if order.fulfilled_at:
        service = OrderFulfillmentService(db, tenant)
        revert_result = await service.revert_inventory(order)
        inventory_reverted = revert_result.success
        if inventory_reverted:
            logger.info(f"Inventory reverted for order {order.order_number}")
        else:
            logger.warning(f"Failed to revert inventory for order {order.order_number}")

    # Update order status
    order.status = OrderStatus.REFUNDED
    order.payment_status = "REFUNDED"
    if request.reason:
        if order.internal_notes:
            order.internal_notes = f"{order.internal_notes}\n\n[Refunded] {request.reason}"
        else:
            order.internal_notes = f"[Refunded] {request.reason}"
    order.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Send refund confirmation email
    try:
        email_service = get_email_service()
        email_service.send_refund_confirmation(
            to_email=order.customer_email,
            customer_name=order.customer_name,
            order_number=order.order_number,
            refund_amount=refund_amount_pence / 100,
            currency=order.currency,
            reason=request.reason,
        )
    except Exception as e:
        logger.error(f"Failed to send refund confirmation email: {e}")
        # Don't fail the request - refund was successful

    message = f"Order {order.order_number} has been refunded (£{refund_amount_pence / 100:.2f})"
    if inventory_reverted:
        message += " and inventory restored"

    return RefundOrderResponse(
        message=message,
        refund_id=refund_result.get("refund_id"),
        refund_status=refund_result.get("status"),
        refund_amount=refund_amount_pence / 100,
    )


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: UUID,
    request: CancelOrderRequest,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Cancel an order with optional reason.

    If the order was fulfilled (inventory deducted), the inventory
    will be restored automatically.
    """
    from app.services.order_fulfillment import OrderFulfillmentService

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tenant.id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only pending/processing orders can be cancelled
    if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order with status: {order.status}",
        )

    # Revert inventory if order was fulfilled
    inventory_reverted = False
    if order.fulfilled_at:
        service = OrderFulfillmentService(db, tenant)
        revert_result = await service.revert_inventory(order)
        inventory_reverted = revert_result.success

    order.status = OrderStatus.CANCELLED
    if request.reason:
        # Append cancellation reason to internal notes
        if order.internal_notes:
            order.internal_notes = f"{order.internal_notes}\n\n[Cancelled] {request.reason}"
        else:
            order.internal_notes = f"[Cancelled] {request.reason}"
    order.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Send cancellation notification email
    try:
        from app.services.email_service import get_email_service

        email_service = get_email_service()
        email_service.send_order_cancelled(
            to_email=order.customer_email,
            customer_name=order.customer_name,
            order_number=order.order_number,
            reason=request.reason,
        )
    except Exception as e:
        # Log but don't fail cancellation for email errors
        import logging

        logging.getLogger(__name__).error(f"Failed to send cancellation email: {e}")

    message = f"Order {order.order_number} has been cancelled"
    if inventory_reverted:
        message += " (inventory restored)"
    return {"message": message}


@router.post("/{order_id}/resend-email", response_model=ResendEmailResponse)
async def resend_order_email(
    order_id: UUID,
    request: ResendEmailRequest,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Resend an order notification email.

    Supported email types: confirmation, shipped, delivered
    """
    from app.services.email_service import get_email_service

    # Validate email_type
    valid_types = ["confirmation", "shipped", "delivered"]
    if request.email_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid email_type. Must be one of: {', '.join(valid_types)}",
        )

    # Fetch order with items for confirmation email
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tenant.id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    email_service = get_email_service()
    email_sent = False

    try:
        if request.email_type == "confirmation":
            # Re-send order confirmation
            email_sent = email_service.send_order_confirmation(
                to_email=order.customer_email,
                customer_name=order.customer_name,
                order_number=order.order_number,
                order_items=[
                    {
                        "name": item.product_name,
                        "quantity": item.quantity,
                        "price": float(item.unit_price) / 100,
                    }
                    for item in order.items
                ],
                subtotal=float(order.subtotal) / 100 if order.subtotal else 0,
                shipping_cost=float(order.shipping_cost) / 100 if order.shipping_cost else 0,
                total=float(order.total) / 100 if order.total else 0,
                shipping_address={
                    "address_line1": order.shipping_address_line1 or "",
                    "address_line2": order.shipping_address_line2 or "",
                    "city": order.shipping_city or "",
                    "county": order.shipping_county or "",
                    "postcode": order.shipping_postcode or "",
                    "country": order.shipping_country or "United Kingdom",
                },
            )
            if email_sent:
                order.confirmation_email_sent = True
                order.confirmation_email_sent_at = datetime.now(timezone.utc)
                await db.commit()

        elif request.email_type == "shipped":
            # Re-send shipped notification
            if order.status not in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
                raise HTTPException(
                    status_code=400,
                    detail="Order has not been shipped yet",
                )
            email_sent = email_service.send_order_shipped(
                to_email=order.customer_email,
                customer_name=order.customer_name,
                order_number=order.order_number,
                tracking_number=order.tracking_number,
                tracking_url=order.tracking_url,
                shipping_method=order.shipping_method or "Royal Mail",
            )
            if email_sent:
                order.shipped_email_sent = True
                order.shipped_email_sent_at = datetime.now(timezone.utc)
                await db.commit()

        elif request.email_type == "delivered":
            # Re-send delivered notification
            if order.status != OrderStatus.DELIVERED:
                raise HTTPException(
                    status_code=400,
                    detail="Order has not been delivered yet",
                )
            email_sent = email_service.send_order_delivered(
                to_email=order.customer_email,
                customer_name=order.customer_name,
                order_number=order.order_number,
            )
            if email_sent:
                order.delivered_email_sent = True
                order.delivered_email_sent_at = datetime.now(timezone.utc)
                await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Failed to resend {request.email_type} email: {e}")
        return ResendEmailResponse(
            message=f"Failed to send {request.email_type} email",
            email_sent=False,
        )

    if email_sent:
        return ResendEmailResponse(
            message=f"{request.email_type.capitalize()} email sent successfully to {order.customer_email}",
            email_sent=True,
        )
    else:
        return ResendEmailResponse(
            message=f"Failed to send {request.email_type} email (email service may not be configured)",
            email_sent=False,
        )
