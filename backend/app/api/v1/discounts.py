"""Discount Codes API endpoints for managing promotional pricing."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant
from app.database import get_db
from app.models.discount import DiscountCode, DiscountType, DiscountUsage
from app.schemas.discount import (
    DiscountCodeCreate,
    DiscountCodeListResponse,
    DiscountCodeResponse,
    DiscountCodeUpdate,
    DiscountValidationRequest,
    DiscountValidationResponse,
)

router = APIRouter()


# ============================================
# Admin Endpoints (CRUD)
# ============================================


@router.get("", response_model=DiscountCodeListResponse)
async def list_discount_codes(
    search: Optional[str] = Query(None, description="Search by code or name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """List all discount codes for the current tenant."""
    # Build base query
    query = (
        select(DiscountCode)
        .where(DiscountCode.tenant_id == tenant.id)
        .order_by(desc(DiscountCode.created_at))
    )

    # Build count query
    count_query = select(func.count(DiscountCode.id)).where(DiscountCode.tenant_id == tenant.id)

    # Apply filters
    if search:
        search_term = f"%{search.upper()}%"
        search_filter = func.upper(DiscountCode.code).like(search_term) | func.upper(
            DiscountCode.name
        ).like(search_term)
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if is_active is not None:
        query = query.where(DiscountCode.is_active == is_active)
        count_query = count_query.where(DiscountCode.is_active == is_active)

    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    discount_codes = result.scalars().all()

    return DiscountCodeListResponse(
        items=[DiscountCodeResponse.model_validate(dc) for dc in discount_codes],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{discount_id}", response_model=DiscountCodeResponse)
async def get_discount_code(
    discount_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """Get a specific discount code by ID."""
    result = await db.execute(
        select(DiscountCode).where(
            DiscountCode.id == discount_id, DiscountCode.tenant_id == tenant.id
        )
    )
    discount_code = result.scalar_one_or_none()

    if not discount_code:
        raise HTTPException(status_code=404, detail="Discount code not found")

    return DiscountCodeResponse.model_validate(discount_code)


@router.post("", response_model=DiscountCodeResponse, status_code=201)
async def create_discount_code(
    data: DiscountCodeCreate,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """Create a new discount code."""
    # Check for duplicate code
    existing = await db.execute(
        select(DiscountCode).where(
            DiscountCode.tenant_id == tenant.id,
            DiscountCode.code == data.code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Discount code '{data.code}' already exists")

    # Validate percentage is 0-100
    if data.discount_type == DiscountType.PERCENTAGE and data.amount > 100:
        raise HTTPException(status_code=400, detail="Percentage discount cannot exceed 100%")

    # Validate dates
    if data.valid_to and data.valid_to < data.valid_from:
        raise HTTPException(status_code=400, detail="valid_to must be after valid_from")

    discount_code = DiscountCode(
        tenant_id=tenant.id,
        code=data.code,
        name=data.name,
        description=data.description,
        discount_type=data.discount_type.value,
        amount=data.amount,
        min_order_amount=data.min_order_amount,
        max_discount_amount=data.max_discount_amount,
        max_uses=data.max_uses,
        max_uses_per_customer=data.max_uses_per_customer,
        valid_from=data.valid_from,
        valid_to=data.valid_to,
        is_active=data.is_active,
        current_uses=0,
    )

    db.add(discount_code)
    await db.commit()
    await db.refresh(discount_code)

    return DiscountCodeResponse.model_validate(discount_code)


@router.patch("/{discount_id}", response_model=DiscountCodeResponse)
async def update_discount_code(
    discount_id: UUID,
    data: DiscountCodeUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """Update a discount code."""
    result = await db.execute(
        select(DiscountCode).where(
            DiscountCode.id == discount_id, DiscountCode.tenant_id == tenant.id
        )
    )
    discount_code = result.scalar_one_or_none()

    if not discount_code:
        raise HTTPException(status_code=404, detail="Discount code not found")

    # Update fields if provided
    if data.name is not None:
        discount_code.name = data.name
    if data.description is not None:
        discount_code.description = data.description
    if data.discount_type is not None:
        discount_code.discount_type = data.discount_type.value
    if data.amount is not None:
        # Validate percentage
        if (
            data.discount_type == DiscountType.PERCENTAGE
            or discount_code.discount_type == DiscountType.PERCENTAGE.value
        ) and data.amount > 100:
            raise HTTPException(status_code=400, detail="Percentage discount cannot exceed 100%")
        discount_code.amount = data.amount
    if data.min_order_amount is not None:
        discount_code.min_order_amount = data.min_order_amount
    if data.max_discount_amount is not None:
        discount_code.max_discount_amount = data.max_discount_amount
    if data.max_uses is not None:
        discount_code.max_uses = data.max_uses
    if data.max_uses_per_customer is not None:
        discount_code.max_uses_per_customer = data.max_uses_per_customer
    if data.valid_from is not None:
        discount_code.valid_from = data.valid_from
    if data.valid_to is not None:
        discount_code.valid_to = data.valid_to
    if data.is_active is not None:
        discount_code.is_active = data.is_active

    # Validate dates
    if discount_code.valid_to and discount_code.valid_to < discount_code.valid_from:
        raise HTTPException(status_code=400, detail="valid_to must be after valid_from")

    discount_code.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(discount_code)

    return DiscountCodeResponse.model_validate(discount_code)


@router.delete("/{discount_id}", status_code=204)
async def delete_discount_code(
    discount_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """Delete a discount code."""
    result = await db.execute(
        select(DiscountCode).where(
            DiscountCode.id == discount_id, DiscountCode.tenant_id == tenant.id
        )
    )
    discount_code = result.scalar_one_or_none()

    if not discount_code:
        raise HTTPException(status_code=404, detail="Discount code not found")

    await db.delete(discount_code)
    await db.commit()


# ============================================
# Validation Endpoint (Public - for checkout)
# ============================================


@router.post("/validate", response_model=DiscountValidationResponse)
async def validate_discount_code(
    data: DiscountValidationRequest,
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Validate a discount code for checkout.

    Returns whether the code is valid and the calculated discount amount.
    """
    # Find the discount code
    result = await db.execute(
        select(DiscountCode).where(
            DiscountCode.tenant_id == tenant.id,
            DiscountCode.code == data.code,
        )
    )
    discount_code = result.scalar_one_or_none()

    if not discount_code:
        return DiscountValidationResponse(
            valid=False,
            code=data.code,
            message="Invalid discount code",
        )

    # Check if active
    if not discount_code.is_active:
        return DiscountValidationResponse(
            valid=False,
            code=data.code,
            message="This discount code is no longer active",
        )

    # Check validity period
    now = datetime.now(timezone.utc)
    # Handle both timezone-aware and naive datetimes for comparison
    valid_from = discount_code.valid_from
    if valid_from.tzinfo is None:
        valid_from = valid_from.replace(tzinfo=timezone.utc)
    if now < valid_from:
        return DiscountValidationResponse(
            valid=False,
            code=data.code,
            message="This discount code is not yet valid",
        )
    valid_to = discount_code.valid_to
    if valid_to and valid_to.tzinfo is None:
        valid_to = valid_to.replace(tzinfo=timezone.utc)
    if valid_to and now > valid_to:
        return DiscountValidationResponse(
            valid=False,
            code=data.code,
            message="This discount code has expired",
        )

    # Check max uses
    if discount_code.max_uses is not None and discount_code.current_uses >= discount_code.max_uses:
        return DiscountValidationResponse(
            valid=False,
            code=data.code,
            message="This discount code has reached its usage limit",
        )

    # Check per-customer limit
    if discount_code.max_uses_per_customer is not None and data.customer_email:
        usage_count_result = await db.execute(
            select(func.count(DiscountUsage.id)).where(
                DiscountUsage.discount_code_id == discount_code.id,
                func.lower(DiscountUsage.customer_email) == data.customer_email.lower(),
            )
        )
        customer_uses = usage_count_result.scalar() or 0
        if customer_uses >= discount_code.max_uses_per_customer:
            return DiscountValidationResponse(
                valid=False,
                code=data.code,
                message="You have already used this discount code the maximum number of times",
            )

    # Check minimum order amount
    if (
        discount_code.min_order_amount is not None
        and data.subtotal < discount_code.min_order_amount
    ):
        return DiscountValidationResponse(
            valid=False,
            code=data.code,
            message=f"Minimum order amount of £{discount_code.min_order_amount:.2f} required",
        )

    # Calculate discount amount
    if discount_code.discount_type == DiscountType.PERCENTAGE.value:
        discount_amount = data.subtotal * (discount_code.amount / Decimal("100"))
    else:
        discount_amount = discount_code.amount

    # Apply max discount cap
    if discount_code.max_discount_amount is not None:
        discount_amount = min(discount_amount, discount_code.max_discount_amount)

    # Ensure discount doesn't exceed subtotal
    discount_amount = min(discount_amount, data.subtotal)

    return DiscountValidationResponse(
        valid=True,
        code=data.code,
        discount_type=DiscountType(discount_code.discount_type),
        discount_amount=discount_amount,
        message=f"Discount applied: £{discount_amount:.2f} off",
    )


# ============================================
# Usage Tracking (Internal helper functions)
# ============================================


async def record_discount_usage(
    db: AsyncSession,
    tenant_id: UUID,
    discount_code_id: UUID,
    order_id: UUID,
    customer_email: str,
    discount_amount: Decimal,
) -> DiscountUsage:
    """Record a discount code usage and increment the counter."""
    # Get the discount code
    result = await db.execute(
        select(DiscountCode).where(
            DiscountCode.id == discount_code_id,
            DiscountCode.tenant_id == tenant_id,
        )
    )
    discount_code = result.scalar_one_or_none()

    if not discount_code:
        raise ValueError("Discount code not found")

    # Create usage record
    usage = DiscountUsage(
        tenant_id=tenant_id,
        discount_code_id=discount_code_id,
        order_id=order_id,
        customer_email=customer_email.lower(),
        discount_amount=discount_amount,
    )
    db.add(usage)

    # Increment counter
    discount_code.current_uses += 1

    return usage


async def get_discount_code_by_code(
    db: AsyncSession,
    tenant_id: UUID,
    code: str,
) -> Optional[DiscountCode]:
    """Get a discount code by its code string."""
    result = await db.execute(
        select(DiscountCode).where(
            DiscountCode.tenant_id == tenant_id,
            DiscountCode.code == code.upper().strip(),
        )
    )
    return result.scalar_one_or_none()
