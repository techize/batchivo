"""Pydantic schemas for product reviews."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ============================================
# Review Submission (Public)
# ============================================


class ReviewCreate(BaseModel):
    """Schema for creating a new review (public submission)."""

    rating: int = Field(..., ge=1, le=5, description="Star rating (1-5)")
    title: Optional[str] = Field(None, max_length=200, description="Review title")
    body: str = Field(..., min_length=10, max_length=5000, description="Review text")
    customer_name: str = Field(..., min_length=1, max_length=255, description="Display name")
    customer_email: EmailStr = Field(..., description="Email for verification")


class ReviewResponse(BaseModel):
    """Public review response (approved reviews only)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rating: int
    title: Optional[str]
    body: str
    customer_name: str
    is_verified_purchase: bool
    helpful_count: int
    created_at: datetime


class ReviewListResponse(BaseModel):
    """Paginated list of public reviews."""

    items: list[ReviewResponse]
    total: int
    average_rating: Optional[Decimal] = None
    rating_distribution: Optional[dict[int, int]] = None  # {1: 5, 2: 10, ...}


# ============================================
# Review Moderation (Admin)
# ============================================


class ReviewAdminResponse(BaseModel):
    """Full review response for admin moderation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    product_id: UUID
    customer_id: Optional[UUID]
    customer_email: str
    customer_name: str
    rating: int
    title: Optional[str]
    body: str
    is_verified_purchase: bool
    order_id: Optional[UUID]
    is_approved: bool
    approved_at: Optional[datetime]
    approved_by: Optional[UUID]
    rejection_reason: Optional[str]
    helpful_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    # Nested info
    product_name: Optional[str] = None
    product_sku: Optional[str] = None


class ReviewAdminListResponse(BaseModel):
    """Paginated list of reviews for admin."""

    items: list[ReviewAdminResponse]
    total: int
    skip: int
    limit: int


class ReviewApprove(BaseModel):
    """Schema for approving a review."""

    pass  # No additional data needed


class ReviewReject(BaseModel):
    """Schema for rejecting a review."""

    reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection")


class ReviewUpdate(BaseModel):
    """Schema for admin editing a review (limited)."""

    title: Optional[str] = Field(None, max_length=200)
    body: Optional[str] = Field(None, min_length=10, max_length=5000)
    is_approved: Optional[bool] = None
    rejection_reason: Optional[str] = Field(None, max_length=500)


# ============================================
# Helpful Vote
# ============================================


class ReviewHelpfulVote(BaseModel):
    """Schema for marking a review as helpful."""

    pass  # No additional data needed


class ReviewHelpfulResponse(BaseModel):
    """Response after voting helpful."""

    review_id: UUID
    helpful_count: int


# ============================================
# Product Review Stats (for product responses)
# ============================================


class ProductReviewStats(BaseModel):
    """Review statistics for a product."""

    average_rating: Optional[Decimal] = None
    review_count: int = 0
    rating_distribution: Optional[dict[int, int]] = None
