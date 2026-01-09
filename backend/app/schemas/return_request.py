"""Pydantic schemas for return requests (RMA)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.return_request import ReturnAction, ReturnReason, ReturnStatus


# ============================================
# Return Item Schemas
# ============================================


class ReturnItemCreate(BaseModel):
    """Schema for adding an item to a return request."""

    order_item_id: UUID = Field(..., description="Order item to return")
    quantity: int = Field(..., ge=1, description="Quantity to return")
    reason: Optional[str] = Field(None, max_length=500, description="Item-specific reason")


class ReturnItemResponse(BaseModel):
    """Return item response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_item_id: UUID
    quantity: int
    reason: Optional[str]
    condition_notes: Optional[str]
    is_restockable: bool

    # From order_item relationship
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    unit_price: Optional[Decimal] = None


# ============================================
# Customer Return Request Schemas
# ============================================


class ReturnRequestCreate(BaseModel):
    """Schema for customer creating a return request."""

    reason: ReturnReason = Field(..., description="Reason for return")
    reason_details: Optional[str] = Field(None, max_length=2000, description="Additional details")
    requested_action: ReturnAction = Field(ReturnAction.REFUND, description="Desired resolution")
    items: list[ReturnItemCreate] = Field(..., min_length=1, description="Items to return")

    # Customer info (for guest checkouts)
    customer_email: Optional[EmailStr] = None
    customer_name: Optional[str] = Field(None, max_length=255)


class CustomerReturnResponse(BaseModel):
    """Return request response for customer view."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rma_number: str
    status: ReturnStatus
    reason: ReturnReason
    reason_details: Optional[str]
    requested_action: ReturnAction
    created_at: datetime
    approved_at: Optional[datetime]
    received_at: Optional[datetime]
    completed_at: Optional[datetime]
    refund_amount: Optional[Decimal]
    return_tracking_number: Optional[str]
    return_label_url: Optional[str]
    items: list[ReturnItemResponse]

    # Order info
    order_number: Optional[str] = None


class CustomerReturnListResponse(BaseModel):
    """List of return requests for customer."""

    items: list[CustomerReturnResponse]
    total: int


# ============================================
# Admin Return Request Schemas
# ============================================


class ReturnRequestAdminResponse(BaseModel):
    """Full return request response for admin."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    rma_number: str
    order_id: UUID
    customer_id: Optional[UUID]
    customer_email: str
    customer_name: str
    status: ReturnStatus
    reason: ReturnReason
    reason_details: Optional[str]
    requested_action: ReturnAction
    admin_notes: Optional[str]
    rejection_reason: Optional[str]
    approved_at: Optional[datetime]
    approved_by: Optional[UUID]
    received_at: Optional[datetime]
    received_by: Optional[UUID]
    completed_at: Optional[datetime]
    completed_by: Optional[UUID]
    refund_amount: Optional[Decimal]
    refund_reference: Optional[str]
    replacement_order_id: Optional[UUID]
    return_tracking_number: Optional[str]
    return_label_url: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    items: list[ReturnItemResponse]

    # Nested info
    order_number: Optional[str] = None
    order_total: Optional[Decimal] = None


class ReturnRequestAdminListResponse(BaseModel):
    """Paginated list of return requests for admin."""

    items: list[ReturnRequestAdminResponse]
    total: int
    skip: int
    limit: int


class ReturnRequestApprove(BaseModel):
    """Schema for approving a return request."""

    admin_notes: Optional[str] = Field(None, max_length=2000)
    return_label_url: Optional[str] = Field(None, max_length=500)


class ReturnRequestReceive(BaseModel):
    """Schema for marking items as received."""

    admin_notes: Optional[str] = Field(None, max_length=2000)
    item_conditions: Optional[list[dict]] = Field(
        None, description="List of {item_id, condition_notes, is_restockable}"
    )


class ReturnRequestComplete(BaseModel):
    """Schema for completing a return request."""

    refund_amount: Optional[Decimal] = Field(None, ge=0, description="Amount to refund")
    refund_reference: Optional[str] = Field(None, max_length=255)
    admin_notes: Optional[str] = Field(None, max_length=2000)
    # For replacements
    replacement_order_id: Optional[UUID] = None


class ReturnRequestReject(BaseModel):
    """Schema for rejecting a return request."""

    rejection_reason: str = Field(..., min_length=1, max_length=500)
    admin_notes: Optional[str] = Field(None, max_length=2000)


class ReturnRequestUpdate(BaseModel):
    """Schema for admin updating a return request."""

    admin_notes: Optional[str] = Field(None, max_length=2000)
    return_tracking_number: Optional[str] = Field(None, max_length=100)
    return_label_url: Optional[str] = Field(None, max_length=500)


# ============================================
# Public Return Lookup
# ============================================


class ReturnLookupRequest(BaseModel):
    """Schema for looking up a return by RMA number and email."""

    rma_number: str = Field(..., description="RMA number")
    email: EmailStr = Field(..., description="Customer email")


class ReturnLookupResponse(BaseModel):
    """Public return status response."""

    rma_number: str
    status: ReturnStatus
    reason: ReturnReason
    requested_action: ReturnAction
    created_at: datetime
    approved_at: Optional[datetime]
    received_at: Optional[datetime]
    completed_at: Optional[datetime]
    refund_amount: Optional[Decimal]
    return_tracking_number: Optional[str]
