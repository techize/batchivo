"""Webhook management API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant
from app.database import get_db
from app.models.tenant import Tenant
from app.models.webhook import DeliveryStatus
from app.schemas.webhook import (
    WebhookDeliveryDetail,
    WebhookDeliveryList,
    WebhookDeliveryResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionList,
    WebhookSubscriptionResponse,
    WebhookSubscriptionUpdate,
    WebhookSubscriptionWithSecret,
    WebhookTestPayload,
    WebhookTestResult,
)
from app.services.webhook_service import WebhookService

router = APIRouter(tags=["Webhooks"])


# ==================== Subscription Endpoints ====================


@router.post(
    "/subscriptions",
    response_model=WebhookSubscriptionWithSecret,
    status_code=status.HTTP_201_CREATED,
    summary="Create a webhook subscription",
    description="Create a new webhook subscription. The secret is only shown once on creation.",
)
async def create_subscription(
    data: WebhookSubscriptionCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Create a new webhook subscription."""
    service = WebhookService(db)
    subscription, secret = await service.create_subscription(
        tenant_id=tenant.id,
        name=data.name,
        url=str(data.url),
        events=data.events,
        custom_headers=data.custom_headers,
    )

    return WebhookSubscriptionWithSecret(
        id=subscription.id,
        name=subscription.name,
        url=subscription.url,
        events=subscription.events,
        is_active=subscription.is_active,
        failure_count=subscription.failure_count,
        last_triggered_at=subscription.last_triggered_at,
        last_success_at=subscription.last_success_at,
        custom_headers=subscription.custom_headers,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
        secret=secret,
    )


@router.get(
    "/subscriptions",
    response_model=WebhookSubscriptionList,
    summary="List webhook subscriptions",
)
async def list_subscriptions(
    include_inactive: bool = Query(False, description="Include inactive subscriptions"),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """List all webhook subscriptions for the tenant."""
    service = WebhookService(db)
    subscriptions = await service.list_subscriptions(
        tenant_id=tenant.id,
        include_inactive=include_inactive,
    )

    return WebhookSubscriptionList(
        subscriptions=[WebhookSubscriptionResponse.model_validate(s) for s in subscriptions],
        total=len(subscriptions),
    )


@router.get(
    "/subscriptions/{subscription_id}",
    response_model=WebhookSubscriptionResponse,
    summary="Get a webhook subscription",
)
async def get_subscription(
    subscription_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific webhook subscription by ID."""
    service = WebhookService(db)
    subscription = await service.get_subscription(subscription_id, tenant.id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook subscription not found",
        )

    return WebhookSubscriptionResponse.model_validate(subscription)


@router.put(
    "/subscriptions/{subscription_id}",
    response_model=WebhookSubscriptionResponse,
    summary="Update a webhook subscription",
)
async def update_subscription(
    subscription_id: UUID,
    data: WebhookSubscriptionUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Update a webhook subscription."""
    service = WebhookService(db)

    updates = data.model_dump(exclude_unset=True)
    subscription = await service.update_subscription(
        subscription_id=subscription_id,
        tenant_id=tenant.id,
        **updates,
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook subscription not found",
        )

    return WebhookSubscriptionResponse.model_validate(subscription)


@router.delete(
    "/subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook subscription",
)
async def delete_subscription(
    subscription_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Delete a webhook subscription and all its delivery history."""
    service = WebhookService(db)
    deleted = await service.delete_subscription(subscription_id, tenant.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook subscription not found",
        )


@router.post(
    "/subscriptions/{subscription_id}/regenerate-secret",
    response_model=dict,
    summary="Regenerate webhook secret",
)
async def regenerate_secret(
    subscription_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate the signing secret for a webhook subscription."""
    service = WebhookService(db)
    new_secret = await service.regenerate_secret(subscription_id, tenant.id)

    if not new_secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook subscription not found",
        )

    return {"secret": new_secret}


@router.post(
    "/subscriptions/{subscription_id}/test",
    response_model=WebhookTestResult,
    summary="Test a webhook subscription",
)
async def test_subscription(
    subscription_id: UUID,
    payload: Optional[WebhookTestPayload] = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Send a test webhook to verify the subscription configuration."""
    service = WebhookService(db)

    if payload is None:
        payload = WebhookTestPayload()

    try:
        result = await service.test_webhook(
            subscription_id=subscription_id,
            tenant_id=tenant.id,
            event_type=payload.event_type,
            test_data=payload.test_data,
        )
        return WebhookTestResult(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ==================== Delivery Endpoints ====================


@router.get(
    "/deliveries",
    response_model=WebhookDeliveryList,
    summary="List webhook deliveries",
)
async def list_deliveries(
    subscription_id: Optional[UUID] = Query(None, description="Filter by subscription"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    delivery_status: Optional[DeliveryStatus] = Query(
        None, alias="status", description="Filter by status"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """List webhook deliveries with optional filtering."""
    service = WebhookService(db)
    offset = (page - 1) * limit

    deliveries, total = await service.list_deliveries(
        tenant_id=tenant.id,
        subscription_id=subscription_id,
        event_type=event_type,
        status=delivery_status,
        limit=limit,
        offset=offset,
    )

    return WebhookDeliveryList(
        deliveries=[WebhookDeliveryResponse.model_validate(d) for d in deliveries],
        total=total,
        page=page,
        limit=limit,
        has_more=(offset + len(deliveries)) < total,
    )


@router.get(
    "/deliveries/{delivery_id}",
    response_model=WebhookDeliveryDetail,
    summary="Get delivery details",
)
async def get_delivery(
    delivery_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a webhook delivery."""
    service = WebhookService(db)
    delivery = await service.get_delivery(delivery_id, tenant.id)

    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook delivery not found",
        )

    return WebhookDeliveryDetail.model_validate(delivery)


@router.post(
    "/deliveries/{delivery_id}/retry",
    response_model=WebhookDeliveryResponse,
    summary="Retry a failed delivery",
)
async def retry_delivery(
    delivery_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Manually retry a failed webhook delivery."""
    service = WebhookService(db)

    try:
        delivery = await service.retry_delivery(delivery_id, tenant.id)
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook delivery not found",
            )
        return WebhookDeliveryResponse.model_validate(delivery)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ==================== Event Types Endpoint ====================


@router.get(
    "/event-types",
    response_model=list[dict],
    summary="List available event types",
)
async def list_event_types():
    """List all available webhook event types."""
    event_categories = {
        "order": [
            "order.created",
            "order.paid",
            "order.shipped",
            "order.delivered",
            "order.cancelled",
        ],
        "payment": ["payment.completed", "payment.refunded", "payment.failed"],
        "inventory": ["inventory.low_stock", "inventory.out_of_stock", "inventory.restocked"],
        "product": ["product.created", "product.updated", "product.deleted"],
        "review": ["review.submitted", "review.approved"],
        "customer": ["customer.registered", "customer.updated"],
        "return": ["return.requested", "return.approved", "return.completed"],
    }

    result = []
    for category, events in event_categories.items():
        for event in events:
            result.append(
                {
                    "event_type": event,
                    "category": category,
                    "description": _get_event_description(event),
                }
            )

    return result


def _get_event_description(event_type: str) -> str:
    """Get human-readable description for event type."""
    descriptions = {
        "order.created": "Triggered when a new order is created",
        "order.paid": "Triggered when an order payment is confirmed",
        "order.shipped": "Triggered when an order is marked as shipped",
        "order.delivered": "Triggered when an order is marked as delivered",
        "order.cancelled": "Triggered when an order is cancelled",
        "payment.completed": "Triggered when a payment is successfully processed",
        "payment.refunded": "Triggered when a payment is refunded",
        "payment.failed": "Triggered when a payment attempt fails",
        "inventory.low_stock": "Triggered when product stock falls below threshold",
        "inventory.out_of_stock": "Triggered when product goes out of stock",
        "inventory.restocked": "Triggered when product is restocked",
        "product.created": "Triggered when a new product is created",
        "product.updated": "Triggered when a product is updated",
        "product.deleted": "Triggered when a product is deleted",
        "review.submitted": "Triggered when a customer submits a review",
        "review.approved": "Triggered when a review is approved by admin",
        "customer.registered": "Triggered when a new customer registers",
        "customer.updated": "Triggered when customer profile is updated",
        "return.requested": "Triggered when a return request is submitted",
        "return.approved": "Triggered when a return request is approved",
        "return.completed": "Triggered when a return is completed",
    }
    return descriptions.get(event_type, f"Event: {event_type}")
