#!/usr/bin/env python3
"""Migration script to populate Mystmere Forge tenant with proper shop settings.

This script updates the existing Mystmereforge tenant with the complete
shop and branding settings needed for the multi-tenant white-label shop system.

Run with: poetry run python scripts/migrate_mystmereforge_settings.py

This script is idempotent - it can be run multiple times safely.
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session_maker
from app.models.tenant import Tenant


# Mystmere Forge brand colors (from existing shop)
MYSTMERE_FORGE_SETTINGS = {
    "tenant_type": "three_d_print",
    "shop": {
        "enabled": True,
        "shop_name": "Mystmere Forge",
        "shop_url_slug": "mystmereforge",
        "custom_domain": "www.mystmereforge.co.uk",
        "custom_domain_verified": True,  # Already verified and working
        "order_prefix": "MF",
        "tagline": "Handcrafted dragons, toys, and collectables - each one unique",
        "about_text": (
            "Welcome to Mystmere Forge! Each piece is lovingly crafted in our "
            "home workshop using premium materials. Our articulated dragons are "
            "each unique - named and given their own personality and backstory. "
            "Every purchase supports a small family business dedicated to bringing "
            "a little magic into your life."
        ),
        "contact_email": "shop@mystmereforge.co.uk",
        "social_links": {
            "instagram": "https://instagram.com/mystmereforge",
            "etsy": "https://www.etsy.com/uk/shop/MystmereForge",
        },
        "shipping_info": (
            "UK Shipping: Royal Mail tracked delivery. Most orders dispatched within "
            "2-3 business days. Free shipping on orders over £50."
        ),
        "return_policy": (
            "We want you to love your purchase! If you're not completely satisfied, "
            "please contact us within 14 days of delivery. Custom/personalized items "
            "are non-refundable unless faulty."
        ),
    },
    "branding": {
        "logo_url": "/uploads/branding/mystmereforge/logo.png",
        "favicon_url": "/uploads/branding/mystmereforge/favicon.ico",
        "primary_color": "#6B21A8",  # Purple - matches Mystmere Forge brand
        "accent_color": "#F59E0B",  # Amber/Gold - dragon fire
        "font_family": "Inter, system-ui, sans-serif",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    "localization": {
        "currency": "GBP",
        "currency_symbol": "£",
        "timezone": "Europe/London",
        "locale": "en-GB",
        "date_format": "DD/MM/YYYY",
        "weight_unit": "g",
        "length_unit": "mm",
    },
    "labels": {
        "material_singular": "Spool",
        "material_plural": "Spools",
        "material_type_singular": "Filament",
        "material_type_plural": "Filaments",
        "equipment_singular": "Printer",
        "equipment_plural": "Printers",
        "production_singular": "Print",
        "production_plural": "Prints",
        "production_run_singular": "Production Run",
        "production_run_plural": "Production Runs",
        "design_singular": "Model",
        "design_plural": "Models",
    },
    "features": {
        "inventory_tracking": True,
        "consumption_tracking": True,
        "low_stock_alerts": True,
        "production_runs": True,
        "time_tracking": False,
        "cost_calculation": True,
        "equipment_management": True,
        "equipment_connections": True,  # Bambu Lab integration
        "online_shop": True,
        "customer_accounts": True,
        "order_management": True,
        "reviews": True,
        "pattern_library": False,
        "project_tracking": False,
        "needle_inventory": False,
        "gauge_tracking": False,
        "analytics_dashboard": True,
        "export_data": True,
    },
    # Legacy fields for backward compatibility
    "default_labor_rate": 20.0,
    "currency": "GBP",
}


async def migrate_mystmereforge():
    """Update Mystmereforge tenant with complete shop settings."""
    async with async_session_maker() as session:
        # Find the tenant
        result = await session.execute(select(Tenant).where(Tenant.slug == "mystmereforge"))
        tenant = result.scalar_one_or_none()

        if not tenant:
            print("ERROR: Mystmereforge tenant not found!")
            print("Run seed_mystmereforge.py first to create the tenant.")
            return False

        print(f"Found tenant: {tenant.name} ({tenant.id})")
        settings_keys = list(tenant.settings.keys()) if tenant.settings else "None"
        print(f"Current settings keys: {settings_keys}")

        # Merge new settings with any existing settings
        existing_settings = dict(tenant.settings) if tenant.settings else {}

        # Deep merge - preserve existing values where they exist
        merged_settings = {}
        for key, value in MYSTMERE_FORGE_SETTINGS.items():
            if key in existing_settings and isinstance(value, dict):
                # Merge sub-dictionaries
                existing_sub = existing_settings.get(key, {})
                if isinstance(existing_sub, dict):
                    merged_sub = {**value, **existing_sub}
                    merged_settings[key] = merged_sub
                    print(f"  Merged {key}: {len(value)} defaults + {len(existing_sub)} existing")
                else:
                    merged_settings[key] = value
                    print(f"  Set {key}: {type(value).__name__}")
            elif key in existing_settings:
                # Keep existing non-dict value
                merged_settings[key] = existing_settings[key]
                print(f"  Kept existing {key}: {existing_settings[key]}")
            else:
                # Add new setting
                merged_settings[key] = value
                print(f"  Added {key}: {type(value).__name__}")

        # Add any existing settings not in our template
        for key, value in existing_settings.items():
            if key not in merged_settings:
                merged_settings[key] = value
                print(f"  Preserved {key}: {type(value).__name__}")

        # Update the tenant
        tenant.settings = merged_settings
        tenant.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(tenant)

        print("\n✓ Settings migration complete!")
        print(f"  Shop name: {merged_settings.get('shop', {}).get('shop_name')}")
        print(f"  Order prefix: {merged_settings.get('shop', {}).get('order_prefix')}")
        print(f"  Custom domain: {merged_settings.get('shop', {}).get('custom_domain')}")
        print(f"  Domain verified: {merged_settings.get('shop', {}).get('custom_domain_verified')}")
        print(f"  Primary color: {merged_settings.get('branding', {}).get('primary_color')}")

        return True


async def verify_settings():
    """Verify the settings were applied correctly."""
    async with async_session_maker() as session:
        result = await session.execute(select(Tenant).where(Tenant.slug == "mystmereforge"))
        tenant = result.scalar_one_or_none()

        if not tenant:
            print("ERROR: Tenant not found!")
            return False

        settings = tenant.settings or {}
        shop = settings.get("shop", {})
        branding = settings.get("branding", {})

        print("\n=== Verification ===")
        print(f"Tenant: {tenant.name}")

        checks = [
            ("Shop enabled", shop.get("enabled") is True),
            ("Order prefix set", shop.get("order_prefix") == "MF"),
            ("Custom domain set", shop.get("custom_domain") == "www.mystmereforge.co.uk"),
            ("Domain verified", shop.get("custom_domain_verified") is True),
            ("Primary color set", branding.get("primary_color") is not None),
        ]

        all_passed = True
        for name, passed in checks:
            status = "✓" if passed else "✗"
            print(f"  {status} {name}")
            if not passed:
                all_passed = False

        return all_passed


if __name__ == "__main__":
    print("=== Mystmere Forge Settings Migration ===\n")

    success = asyncio.run(migrate_mystmereforge())

    if success:
        print("\n" + "=" * 40)
        asyncio.run(verify_settings())
        print("\nMigration complete! Mystmere Forge is ready for the white-label shop system.")
    else:
        print("\nMigration failed. Please check the errors above.")
        exit(1)
