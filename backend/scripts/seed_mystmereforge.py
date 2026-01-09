#!/usr/bin/env python3
"""Seed script to create Mystmereforge tenant, sales channel, and categories.

Run with: poetry run python scripts/seed_mystmereforge.py
"""

import asyncio
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.database import async_session_maker
from app.models.tenant import Tenant
from app.models.sales_channel import SalesChannel
from app.models.category import Category


# Shop categories for Mystmereforge
SHOP_CATEGORIES = [
    {
        "name": "Dragons",
        "slug": "dragons",
        "description": "Articulated dragons - each one unique and named with their own personality and backstory",
        "display_order": 1,
    },
    {
        "name": "Dinosaurs",
        "slug": "dinosaurs",
        "description": "Articulated dinosaurs and prehistoric creatures - from T-Rex to Triceratops",
        "display_order": 2,
    },
    {
        "name": "Wildlife",
        "slug": "wildlife",
        "description": "British wildlife scenes and dioramas - red squirrels, ermines, and winter wonderlands",
        "display_order": 3,
    },
    {
        "name": "Toys & Trinkets",
        "slug": "toys",
        "description": "Fun fidget toys, desk companions, and small collectables for everyday joy",
        "display_order": 4,
    },
    {
        "name": "Special Editions",
        "slug": "special-editions",
        "description": "Limited runs, large showcase pieces, and one-of-a-kind creations",
        "display_order": 5,
    },
]


async def seed_mystmereforge():
    """Create Mystmereforge tenant, sales channel, and categories."""
    async with async_session_maker() as session:
        # Check for existing tenant
        result = await session.execute(select(Tenant).where(Tenant.slug == "mystmereforge"))
        tenant = result.scalar_one_or_none()

        if not tenant:
            print("Creating Mystmereforge tenant...")
            tenant = Tenant(
                id=uuid4(),
                name="Mystmere Forge",
                slug="mystmereforge",
                description="Handcrafted 3D printed dragons, toys, and collectables",
                is_active=True,
            )
            session.add(tenant)
            await session.flush()
            print(f"Created tenant: {tenant.id}")
        else:
            print(f"Tenant already exists: {tenant.id}")

        # Check for existing sales channel
        result = await session.execute(
            select(SalesChannel).where(
                SalesChannel.tenant_id == tenant.id,
                SalesChannel.name == "Mystmereforge Shop",
            )
        )
        channel = result.scalar_one_or_none()

        if not channel:
            print("Creating Mystmereforge Shop sales channel...")
            channel = SalesChannel(
                id=uuid4(),
                tenant_id=tenant.id,
                name="Mystmereforge Shop",
                platform_type="online_shop",
                fee_percentage=Decimal("2.9"),  # Square payment processing
                fee_fixed=Decimal("0.30"),  # Square per-transaction fee
                monthly_cost=Decimal("0"),  # No monthly cost
                is_active=True,
            )
            session.add(channel)
            await session.flush()
            print(f"Created sales channel: {channel.id}")
        else:
            print(f"Sales channel already exists: {channel.id}")

        # Create shop categories
        print("\nCreating shop categories...")
        categories_created = 0
        for cat_data in SHOP_CATEGORIES:
            # Check if category exists
            result = await session.execute(
                select(Category).where(
                    Category.tenant_id == tenant.id,
                    Category.slug == cat_data["slug"],
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                category = Category(
                    id=uuid4(),
                    tenant_id=tenant.id,
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data["description"],
                    display_order=cat_data["display_order"],
                    is_active=True,
                )
                session.add(category)
                print(f"  Created: {cat_data['name']} ({cat_data['slug']})")
                categories_created += 1
            else:
                print(f"  Exists: {cat_data['name']} ({cat_data['slug']})")

        await session.commit()
        print(f"\nDone! Created {categories_created} new categories.")

        return tenant.id, channel.id


if __name__ == "__main__":
    tenant_id, channel_id = asyncio.run(seed_mystmereforge())
    print(f"\nTenant ID: {tenant_id}")
    print(f"Sales Channel ID: {channel_id}")
