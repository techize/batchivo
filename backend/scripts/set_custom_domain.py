#!/usr/bin/env python3
"""Set custom domain for a tenant.

Run with: poetry run python scripts/set_custom_domain.py mystmereforge mystmereforge.co.uk
"""

import asyncio
import sys

from sqlalchemy import select

from app.database import async_session_maker
from app.models.tenant import Tenant


async def set_custom_domain(slug: str, custom_domain: str):
    """Set custom domain in tenant settings."""
    async with async_session_maker() as session:
        # Find tenant
        result = await session.execute(select(Tenant).where(Tenant.slug == slug))
        tenant = result.scalar_one_or_none()

        if not tenant:
            print(f"Tenant not found: {slug}")
            return False

        # Update settings
        settings = tenant.settings or {}
        if "shop" not in settings:
            settings["shop"] = {}
        settings["shop"]["custom_domain"] = custom_domain

        tenant.settings = settings
        await session.commit()

        print(f"Updated tenant '{slug}' with custom domain: {custom_domain}")
        return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/set_custom_domain.py <tenant_slug> <custom_domain>")
        print("Example: python scripts/set_custom_domain.py mystmereforge mystmereforge.co.uk")
        sys.exit(1)

    slug = sys.argv[1]
    domain = sys.argv[2]
    asyncio.run(set_custom_domain(slug, domain))
