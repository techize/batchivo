"""Admin product review moderation API endpoints.

Handles review approval, rejection, and management.
Public review submission and display is in shop.py.
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.product import Product
from app.models.review import Review
from app.schemas.review import (
    ReviewAdminListResponse,
    ReviewAdminResponse,
    ReviewReject,
    ReviewUpdate,
)

router = APIRouter()


def _build_admin_review_response(review: Review) -> ReviewAdminResponse:
    """Build admin review response with product info."""
    return ReviewAdminResponse(
        id=review.id,
        tenant_id=review.tenant_id,
        product_id=review.product_id,
        customer_id=review.customer_id,
        customer_email=review.customer_email,
        customer_name=review.customer_name,
        rating=review.rating,
        title=review.title,
        body=review.body,
        is_verified_purchase=review.is_verified_purchase,
        order_id=review.order_id,
        is_approved=review.is_approved,
        approved_at=review.approved_at,
        approved_by=review.approved_by,
        rejection_reason=review.rejection_reason,
        helpful_count=review.helpful_count,
        created_at=review.created_at,
        updated_at=review.updated_at,
        product_name=review.product.name if review.product else None,
        product_sku=review.product.sku if review.product else None,
    )


async def _update_product_review_stats(db: AsyncSession, product_id: UUID, tenant_id: UUID) -> None:
    """Update cached review statistics on a product."""
    # Calculate stats from approved reviews only
    stats_query = select(
        func.count(Review.id).label("count"),
        func.avg(Review.rating).label("avg_rating"),
    ).where(
        Review.product_id == product_id,
        Review.tenant_id == tenant_id,
        Review.is_approved.is_(True),
    )

    result = await db.execute(stats_query)
    row = result.one()

    # Update product
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )
    )
    product = product_result.scalar_one_or_none()

    if product:
        product.review_count = row.count or 0
        product.average_rating = round(row.avg_rating, 2) if row.avg_rating else None


@router.get("", response_model=ReviewAdminListResponse)
async def list_reviews(
    status_filter: Literal["all", "pending", "approved", "rejected"] = Query(
        "all", alias="status", description="Filter by approval status"
    ),
    product_id: UUID | None = Query(None, description="Filter by product"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all reviews for moderation.

    Filters:
    - status: all, pending (not approved and no rejection), approved, rejected
    - product_id: Filter to specific product
    """
    # Base query
    query = (
        select(Review).where(Review.tenant_id == tenant.id).options(selectinload(Review.product))
    )

    # Apply status filter
    if status_filter == "pending":
        query = query.where(
            Review.is_approved.is_(False),
            Review.rejection_reason.is_(None),
        )
    elif status_filter == "approved":
        query = query.where(Review.is_approved.is_(True))
    elif status_filter == "rejected":
        query = query.where(
            Review.is_approved.is_(False),
            Review.rejection_reason.isnot(None),
        )

    # Filter by product
    if product_id:
        query = query.where(Review.product_id == product_id)

    # Count total
    count_query = select(func.count(Review.id)).where(Review.tenant_id == tenant.id)
    if status_filter == "pending":
        count_query = count_query.where(
            Review.is_approved.is_(False),
            Review.rejection_reason.is_(None),
        )
    elif status_filter == "approved":
        count_query = count_query.where(Review.is_approved.is_(True))
    elif status_filter == "rejected":
        count_query = count_query.where(
            Review.is_approved.is_(False),
            Review.rejection_reason.isnot(None),
        )
    if product_id:
        count_query = count_query.where(Review.product_id == product_id)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    query = query.order_by(desc(Review.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    reviews = result.scalars().all()

    return ReviewAdminListResponse(
        items=[_build_admin_review_response(r) for r in reviews],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{review_id}", response_model=ReviewAdminResponse)
async def get_review(
    review_id: UUID,
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific review by ID."""
    result = await db.execute(
        select(Review)
        .where(
            Review.id == review_id,
            Review.tenant_id == tenant.id,
        )
        .options(selectinload(Review.product))
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    return _build_admin_review_response(review)


@router.put("/{review_id}", response_model=ReviewAdminResponse)
async def update_review(
    review_id: UUID,
    data: ReviewUpdate,
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Update a review (admin edit)."""
    result = await db.execute(
        select(Review)
        .where(
            Review.id == review_id,
            Review.tenant_id == tenant.id,
        )
        .options(selectinload(Review.product))
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    # Track if approval status changed
    was_approved = review.is_approved

    # Update fields
    if data.title is not None:
        review.title = data.title
    if data.body is not None:
        review.body = data.body
    if data.is_approved is not None:
        if data.is_approved and not review.is_approved:
            # Approving
            review.is_approved = True
            review.approved_at = datetime.now(timezone.utc)
            review.approved_by = user.id
            review.rejection_reason = None
        elif not data.is_approved:
            review.is_approved = False
            review.approved_at = None
            review.approved_by = None
    if data.rejection_reason is not None:
        review.rejection_reason = data.rejection_reason

    review.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(review)

    # Update product stats if approval status changed
    if was_approved != review.is_approved:
        await _update_product_review_stats(db, review.product_id, tenant.id)
        await db.commit()

    return _build_admin_review_response(review)


@router.post("/{review_id}/approve", response_model=ReviewAdminResponse)
async def approve_review(
    review_id: UUID,
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Approve a review for public display."""
    result = await db.execute(
        select(Review)
        .where(
            Review.id == review_id,
            Review.tenant_id == tenant.id,
        )
        .options(selectinload(Review.product))
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    if review.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review is already approved",
        )

    review.is_approved = True
    review.approved_at = datetime.now(timezone.utc)
    review.approved_by = user.id
    review.rejection_reason = None
    review.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(review)

    # Update product review stats
    await _update_product_review_stats(db, review.product_id, tenant.id)
    await db.commit()

    return _build_admin_review_response(review)


@router.post("/{review_id}/reject", response_model=ReviewAdminResponse)
async def reject_review(
    review_id: UUID,
    data: ReviewReject,
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Reject a review."""
    result = await db.execute(
        select(Review)
        .where(
            Review.id == review_id,
            Review.tenant_id == tenant.id,
        )
        .options(selectinload(Review.product))
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    was_approved = review.is_approved

    review.is_approved = False
    review.approved_at = None
    review.approved_by = None
    review.rejection_reason = data.reason
    review.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(review)

    # Update product review stats if was previously approved
    if was_approved:
        await _update_product_review_stats(db, review.product_id, tenant.id)
        await db.commit()

    return _build_admin_review_response(review)


@router.delete("/{review_id}", status_code=204)
async def delete_review(
    review_id: UUID,
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Delete a review permanently."""
    result = await db.execute(
        select(Review).where(
            Review.id == review_id,
            Review.tenant_id == tenant.id,
        )
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    product_id = review.product_id
    was_approved = review.is_approved

    await db.delete(review)
    await db.commit()

    # Update product review stats if was approved
    if was_approved:
        await _update_product_review_stats(db, product_id, tenant.id)
        await db.commit()
