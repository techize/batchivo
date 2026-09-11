"""Explicit storefront reporting channel; never choose an arbitrary active row."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.models.sales_channel import SalesChannel


async def commerce_sales_channel(db, tenant_id, environment, isolated):
    configured = environment.get("COMMERCE_SALES_CHANNEL_ID")
    if not configured and isolated:
        return None  # Compatibility for historical isolated fixtures only.
    try:
        channel_id = UUID(configured or "")
    except ValueError:
        raise HTTPException(503, "Commerce sales channel configuration is required") from None
    channel = await db.scalar(
        select(SalesChannel).where(
            SalesChannel.id == channel_id,
            SalesChannel.tenant_id == tenant_id,
            SalesChannel.platform_type == "online_shop",
            SalesChannel.is_active.is_(True),
        )
    )
    if not channel:
        raise HTTPException(503, "Commerce sales channel is unavailable")
    return channel.id
