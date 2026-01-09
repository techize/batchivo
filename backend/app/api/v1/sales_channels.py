"""Sales Channels API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.sales_channel import SalesChannel
from app.schemas.sales_channel import (
    SalesChannelCreate,
    SalesChannelListResponse,
    SalesChannelResponse,
    SalesChannelUpdate,
)

router = APIRouter()


@router.post("", response_model=SalesChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_channel(
    channel_data: SalesChannelCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> SalesChannelResponse:
    """
    Create a new sales channel.

    Requires authentication.
    Channel will be associated with current tenant.
    Name must be unique per tenant.
    """
    # Check if name already exists for this tenant
    existing = await db.execute(
        select(SalesChannel).where(
            SalesChannel.tenant_id == tenant.id,
            SalesChannel.name == channel_data.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sales channel with name '{channel_data.name}' already exists",
        )

    # Validate platform type
    valid_platforms = ["fair", "online_shop", "shopify", "ebay", "etsy", "amazon", "other"]
    if channel_data.platform_type not in valid_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform type. Must be one of: {', '.join(valid_platforms)}",
        )

    # Create channel instance
    channel = SalesChannel(
        tenant_id=tenant.id,
        **channel_data.model_dump(),
    )

    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    return SalesChannelResponse.model_validate(channel)


@router.get("", response_model=SalesChannelListResponse)
async def list_sales_channels(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max items to return"),
    search: Optional[str] = Query(None, description="Search by name"),
    platform_type: Optional[str] = Query(None, description="Filter by platform type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> SalesChannelListResponse:
    """
    List all sales channels for current tenant with pagination and filtering.
    """
    # Build query
    query = select(SalesChannel).where(SalesChannel.tenant_id == tenant.id)

    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.where(SalesChannel.name.ilike(search_pattern))

    if platform_type:
        query = query.where(SalesChannel.platform_type == platform_type)

    if is_active is not None:
        query = query.where(SalesChannel.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination and fetch
    query = query.order_by(SalesChannel.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    channels = result.scalars().all()

    return SalesChannelListResponse(
        channels=[SalesChannelResponse.model_validate(c) for c in channels],
        total=total or 0,
    )


@router.get("/{channel_id}", response_model=SalesChannelResponse)
async def get_sales_channel(
    channel_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> SalesChannelResponse:
    """
    Get sales channel detail.

    Requires authentication.
    Channel must belong to current tenant.
    """
    query = select(SalesChannel).where(
        SalesChannel.id == channel_id,
        SalesChannel.tenant_id == tenant.id,
    )

    result = await db.execute(query)
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales channel not found",
        )

    return SalesChannelResponse.model_validate(channel)


@router.put("/{channel_id}", response_model=SalesChannelResponse)
async def update_sales_channel(
    channel_id: UUID,
    channel_data: SalesChannelUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> SalesChannelResponse:
    """
    Update an existing sales channel.

    Requires authentication.
    Channel must belong to current tenant.
    """
    # Fetch channel
    query = select(SalesChannel).where(
        SalesChannel.id == channel_id,
        SalesChannel.tenant_id == tenant.id,
    )

    result = await db.execute(query)
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales channel not found",
        )

    # Check name uniqueness if changing
    if channel_data.name and channel_data.name != channel.name:
        existing = await db.execute(
            select(SalesChannel).where(
                SalesChannel.tenant_id == tenant.id,
                SalesChannel.name == channel_data.name,
                SalesChannel.id != channel_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sales channel with name '{channel_data.name}' already exists",
            )

    # Validate platform type if provided
    if channel_data.platform_type:
        valid_platforms = ["fair", "online_shop", "shopify", "ebay", "etsy", "amazon", "other"]
        if channel_data.platform_type not in valid_platforms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid platform type. Must be one of: {', '.join(valid_platforms)}",
            )

    # Update fields
    update_data = channel_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    await db.commit()
    await db.refresh(channel)

    return SalesChannelResponse.model_validate(channel)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sales_channel(
    channel_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    permanent: bool = Query(False, description="Permanently delete instead of soft delete"),
):
    """
    Delete a sales channel.

    By default, performs a soft delete (sets is_active=False).
    Use ?permanent=true to permanently remove the channel from the database.

    Requires authentication.
    Channel must belong to current tenant.
    """
    query = select(SalesChannel).where(
        SalesChannel.id == channel_id,
        SalesChannel.tenant_id == tenant.id,
    )

    result = await db.execute(query)
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales channel not found",
        )

    if permanent:
        # Hard delete - permanently remove from database
        await db.delete(channel)
    else:
        # Soft delete - just mark as inactive
        channel.is_active = False
    await db.commit()
