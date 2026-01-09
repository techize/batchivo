"""Pydantic schemas for webhook endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.models.webhook import WebhookEventType


class WebhookSubscriptionCreate(BaseModel):
    """Schema for creating a webhook subscription."""

    name: str = Field(..., min_length=1, max_length=100)
    url: HttpUrl
    events: list[WebhookEventType] = Field(..., min_length=1)
    custom_headers: Optional[dict[str, str]] = None

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list) -> list:
        """Ensure events list is unique."""
        unique_events = list(set(v))
        if len(unique_events) != len(v):
            return unique_events
        return v


class WebhookSubscriptionUpdate(BaseModel):
    """Schema for updating a webhook subscription."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[HttpUrl] = None
    events: Optional[list[WebhookEventType]] = Field(None, min_length=1)
    is_active: Optional[bool] = None
    custom_headers: Optional[dict[str, str]] = None


class WebhookSubscriptionResponse(BaseModel):
    """Schema for webhook subscription response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    events: list[str]
    is_active: bool
    failure_count: int
    last_triggered_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    custom_headers: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class WebhookSubscriptionWithSecret(WebhookSubscriptionResponse):
    """Response including secret (only shown on creation)."""

    secret: str


class WebhookDeliveryResponse(BaseModel):
    """Schema for webhook delivery response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subscription_id: UUID
    event_type: str
    event_id: str
    status: str
    response_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    attempts: int
    next_retry_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class WebhookDeliveryDetail(WebhookDeliveryResponse):
    """Detailed delivery response including payload."""

    payload: dict
    response_body: Optional[str] = None


class WebhookDeliveryList(BaseModel):
    """Paginated list of webhook deliveries."""

    deliveries: list[WebhookDeliveryResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class WebhookSubscriptionList(BaseModel):
    """List of webhook subscriptions."""

    subscriptions: list[WebhookSubscriptionResponse]
    total: int


class WebhookTestPayload(BaseModel):
    """Test payload for webhook testing."""

    event_type: WebhookEventType = WebhookEventType.ORDER_CREATED
    test_data: Optional[dict] = None


class WebhookTestResult(BaseModel):
    """Result of webhook test."""

    success: bool
    response_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None


class WebhookEventPayload(BaseModel):
    """Standard webhook payload structure."""

    event_id: str
    event_type: str
    timestamp: datetime
    tenant_id: str
    data: dict


# Event-specific payload schemas
class OrderEventData(BaseModel):
    """Data included in order events."""

    order_id: str
    order_number: str
    status: str
    total_amount: float
    currency: str = "GBP"
    customer_email: str
    items_count: int
    created_at: datetime


class PaymentEventData(BaseModel):
    """Data included in payment events."""

    payment_id: str
    order_id: str
    amount: float
    currency: str = "GBP"
    status: str
    payment_method: Optional[str] = None


class InventoryEventData(BaseModel):
    """Data included in inventory events."""

    product_id: str
    product_sku: str
    product_name: str
    current_stock: int
    threshold: Optional[int] = None


class ProductEventData(BaseModel):
    """Data included in product events."""

    product_id: str
    sku: str
    name: str
    is_active: bool
    shop_visible: bool
    price: Optional[float] = None


class ReviewEventData(BaseModel):
    """Data included in review events."""

    review_id: str
    product_id: str
    customer_email: str
    rating: int
    title: Optional[str] = None


class CustomerEventData(BaseModel):
    """Data included in customer events."""

    customer_id: str
    email: str
    full_name: str


class ReturnEventData(BaseModel):
    """Data included in return events."""

    return_id: str
    rma_number: str
    order_id: str
    status: str
    reason: str
