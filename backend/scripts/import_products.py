#!/usr/bin/env python3
"""Product import script for Mystmereforge shop.

Imports products from CSV file with optional image upload from folders.

Usage:
    # Validate CSV only (dry run)
    poetry run python scripts/import_products.py products.csv --validate

    # Dry run (show what would be imported)
    poetry run python scripts/import_products.py products.csv --dry-run

    # Import products (no images)
    poetry run python scripts/import_products.py products.csv

    # Import products with images from folder
    poetry run python scripts/import_products.py products.csv --images ./product_images

CSV Format:
    sku,name,category,description,price,units_in_stock,is_featured,feature_title,backstory,image_folder
    DRG-001,Ember the Crystal Dragon,dragons,"A majestic dragon...",45.00,1,true,Ember the Ancient,"Born in...",dragons/ember
"""

import argparse
import asyncio
import csv
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session_maker
from app.models.category import Category
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_pricing import ProductPricing
from app.models.sales_channel import SalesChannel
from app.models.tenant import Tenant


# =============================================================================
# Configuration
# =============================================================================

TENANT_SLUG = "mystmereforge"
CHANNEL_NAME = "Mystmereforge Shop"

REQUIRED_COLUMNS = ["sku", "name", "category", "price"]
OPTIONAL_COLUMNS = [
    "description",
    "shop_description",
    "units_in_stock",
    "is_featured",
    "feature_title",
    "backstory",
    "image_folder",
]

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


# =============================================================================
# Validation
# =============================================================================


class ValidationError:
    """Validation error with row context."""

    def __init__(self, row: int, field: str, message: str):
        self.row = row
        self.field = field
        self.message = message

    def __str__(self):
        return f"Row {self.row}: [{self.field}] {self.message}"


def validate_csv(csv_path: Path, images_path: Optional[Path] = None) -> list[ValidationError]:
    """Validate CSV file and return list of errors."""
    errors: list[ValidationError] = []

    if not csv_path.exists():
        errors.append(ValidationError(0, "file", f"CSV file not found: {csv_path}"))
        return errors

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Check required columns
            if reader.fieldnames is None:
                errors.append(ValidationError(0, "header", "CSV file is empty"))
                return errors

            missing_cols = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
            if missing_cols:
                errors.append(
                    ValidationError(
                        0, "header", f"Missing required columns: {', '.join(missing_cols)}"
                    )
                )
                return errors

            skus_seen: set[str] = set()

            for idx, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                # Check required fields
                for col in REQUIRED_COLUMNS:
                    value = row.get(col, "").strip()
                    if not value:
                        errors.append(ValidationError(idx, col, f"Required field '{col}' is empty"))

                # Validate SKU uniqueness
                sku = row.get("sku", "").strip()
                if sku:
                    if sku in skus_seen:
                        errors.append(ValidationError(idx, "sku", f"Duplicate SKU: {sku}"))
                    skus_seen.add(sku)

                # Validate price
                price_str = row.get("price", "").strip()
                if price_str:
                    try:
                        price = Decimal(price_str)
                        if price <= 0:
                            errors.append(ValidationError(idx, "price", "Price must be positive"))
                    except InvalidOperation:
                        errors.append(
                            ValidationError(idx, "price", f"Invalid price format: {price_str}")
                        )

                # Validate units_in_stock
                stock_str = row.get("units_in_stock", "").strip()
                if stock_str:
                    try:
                        stock = int(stock_str)
                        if stock < 0:
                            errors.append(
                                ValidationError(idx, "units_in_stock", "Stock cannot be negative")
                            )
                    except ValueError:
                        errors.append(
                            ValidationError(
                                idx, "units_in_stock", f"Invalid stock format: {stock_str}"
                            )
                        )

                # Validate is_featured
                featured_str = row.get("is_featured", "").strip().lower()
                if featured_str and featured_str not in (
                    "true",
                    "false",
                    "yes",
                    "no",
                    "1",
                    "0",
                    "",
                ):
                    errors.append(
                        ValidationError(
                            idx,
                            "is_featured",
                            f"Invalid boolean value: {featured_str} (use true/false)",
                        )
                    )

                # Validate image folder if images path provided
                if images_path:
                    image_folder = row.get("image_folder", "").strip()
                    if image_folder:
                        folder_path = images_path / image_folder
                        if not folder_path.exists():
                            errors.append(
                                ValidationError(
                                    idx, "image_folder", f"Image folder not found: {folder_path}"
                                )
                            )
                        elif not folder_path.is_dir():
                            errors.append(
                                ValidationError(
                                    idx, "image_folder", f"Path is not a directory: {folder_path}"
                                )
                            )
                        else:
                            # Check for valid images
                            image_files = [
                                f
                                for f in folder_path.iterdir()
                                if f.is_file() and f.suffix.lower() in VALID_IMAGE_EXTENSIONS
                            ]
                            if not image_files:
                                errors.append(
                                    ValidationError(
                                        idx,
                                        "image_folder",
                                        f"No valid images in folder: {folder_path}",
                                    )
                                )

    except csv.Error as e:
        errors.append(ValidationError(0, "file", f"CSV parsing error: {e}"))

    return errors


# =============================================================================
# Import Functions
# =============================================================================


def parse_bool(value: str) -> bool:
    """Parse boolean from string."""
    return value.strip().lower() in ("true", "yes", "1")


async def get_tenant_and_channel(
    session: AsyncSession,
) -> tuple[Optional[UUID], Optional[UUID]]:
    """Get tenant and sales channel IDs."""
    # Get tenant
    result = await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return None, None

    # Get sales channel
    result = await session.execute(
        select(SalesChannel).where(
            SalesChannel.tenant_id == tenant.id,
            SalesChannel.name == CHANNEL_NAME,
        )
    )
    channel = result.scalar_one_or_none()

    return tenant.id if tenant else None, channel.id if channel else None


async def get_category_map(session: AsyncSession, tenant_id: UUID) -> dict[str, UUID]:
    """Get mapping of category slug to ID."""
    result = await session.execute(select(Category).where(Category.tenant_id == tenant_id))
    categories = result.scalars().all()
    return {cat.slug: cat.id for cat in categories}


async def get_existing_skus(session: AsyncSession, tenant_id: UUID) -> set[str]:
    """Get set of existing product SKUs."""
    result = await session.execute(select(Product.sku).where(Product.tenant_id == tenant_id))
    return {sku for (sku,) in result.all()}


async def import_products(
    csv_path: Path,
    images_path: Optional[Path] = None,
    dry_run: bool = False,
) -> tuple[int, int, list[str]]:
    """
    Import products from CSV.

    Returns:
        Tuple of (imported_count, skipped_count, error_messages)
    """
    imported = 0
    skipped = 0
    messages: list[str] = []

    async with async_session_maker() as session:
        # Get tenant and channel
        tenant_id, channel_id = await get_tenant_and_channel(session)
        if not tenant_id:
            messages.append(
                f"ERROR: Tenant '{TENANT_SLUG}' not found. Run seed_mystmereforge.py first."
            )
            return 0, 0, messages
        if not channel_id:
            messages.append(
                f"ERROR: Sales channel '{CHANNEL_NAME}' not found. Run seed_mystmereforge.py first."
            )
            return 0, 0, messages

        # Get category mapping
        category_map = await get_category_map(session, tenant_id)
        if not category_map:
            messages.append("WARNING: No categories found. Products won't be categorized.")

        # Get existing SKUs
        existing_skus = await get_existing_skus(session, tenant_id)

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for idx, row in enumerate(reader, start=2):
                sku = row.get("sku", "").strip()
                name = row.get("name", "").strip()
                category_slug = row.get("category", "").strip()

                # Skip existing products
                if sku in existing_skus:
                    skipped += 1
                    messages.append(f"SKIP: Row {idx} - SKU '{sku}' already exists")
                    continue

                # Get category ID
                category_id = category_map.get(category_slug)
                if category_slug and not category_id:
                    messages.append(
                        f"WARNING: Row {idx} - Category '{category_slug}' not found, skipping category assignment"
                    )

                # Parse fields
                description = row.get("description", "").strip() or None
                shop_description = row.get("shop_description", "").strip() or None
                units_in_stock = int(row.get("units_in_stock", "0").strip() or "0")
                is_featured = parse_bool(row.get("is_featured", ""))
                feature_title = row.get("feature_title", "").strip() or None
                backstory = row.get("backstory", "").strip() or None
                price = Decimal(row.get("price", "0").strip())

                if dry_run:
                    cat_info = f" [{category_slug}]" if category_slug else ""
                    feat_info = " (FEATURED)" if is_featured else ""
                    messages.append(f"WOULD IMPORT: {sku} - {name}{cat_info} @ £{price}{feat_info}")
                    imported += 1
                    continue

                # Create product
                product = Product(
                    tenant_id=tenant_id,
                    sku=sku,
                    name=name,
                    description=description,
                    shop_description=shop_description,
                    units_in_stock=units_in_stock,
                    is_active=True,
                    shop_visible=True,  # Importing means it should be visible
                    is_featured=is_featured,
                    feature_title=feature_title,
                    backstory=backstory,
                )
                session.add(product)
                await session.flush()  # Get product ID

                # Add category via junction table
                if category_id:
                    from sqlalchemy import insert
                    from app.models.category import product_categories

                    await session.execute(
                        insert(product_categories).values(
                            product_id=product.id,
                            category_id=category_id,
                        )
                    )

                # Add pricing
                pricing = ProductPricing(
                    product_id=product.id,
                    sales_channel_id=channel_id,
                    list_price=float(price),
                    is_active=True,
                )
                session.add(pricing)

                # Upload images if folder specified
                image_folder = row.get("image_folder", "").strip()
                if images_path and image_folder:
                    folder_path = images_path / image_folder
                    if folder_path.exists() and folder_path.is_dir():
                        image_files = sorted(
                            [
                                f
                                for f in folder_path.iterdir()
                                if f.is_file() and f.suffix.lower() in VALID_IMAGE_EXTENSIONS
                            ]
                        )

                        for order, img_file in enumerate(image_files):
                            # For now, we'll store a relative path - in production
                            # this would upload to S3/MinIO and store the URL
                            image_url = f"/uploads/products/{product.id}/{img_file.name}"

                            image = ProductImage(
                                product_id=product.id,
                                image_url=image_url,
                                alt_text=f"{name} - Image {order + 1}",
                                display_order=order,
                                is_primary=(order == 0),
                            )
                            session.add(image)

                        messages.append(f"  → Added {len(image_files)} images from {image_folder}")

                imported += 1
                cat_info = f" [{category_slug}]" if category_slug else ""
                feat_info = " (FEATURED)" if is_featured else ""
                messages.append(f"IMPORTED: {sku} - {name}{cat_info} @ £{price}{feat_info}")

        if not dry_run:
            await session.commit()
            messages.append(f"\n✓ Committed {imported} products to database")

    return imported, skipped, messages


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Import products from CSV for Mystmereforge shop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CSV Columns:
  Required: sku, name, category, price
  Optional: description, shop_description, units_in_stock, is_featured,
            feature_title, backstory, image_folder

Examples:
  # Validate CSV
  python scripts/import_products.py products.csv --validate

  # Dry run
  python scripts/import_products.py products.csv --dry-run

  # Import with images
  python scripts/import_products.py products.csv --images ./product_images
        """,
    )
    parser.add_argument("csv_file", type=Path, help="Path to CSV file")
    parser.add_argument(
        "--images",
        type=Path,
        default=None,
        help="Base path for image folders (referenced in image_folder column)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only validate CSV, don't import",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without making changes",
    )

    args = parser.parse_args()

    # Validate first
    print(f"Validating {args.csv_file}...")
    errors = validate_csv(args.csv_file, args.images)

    if errors:
        print(f"\n❌ Found {len(errors)} validation errors:\n")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)

    print("✓ CSV validation passed\n")

    if args.validate:
        print("Validation only mode - exiting.")
        sys.exit(0)

    # Import
    mode = "DRY RUN" if args.dry_run else "IMPORT"
    print(f"Starting {mode}...\n")

    imported, skipped, messages = asyncio.run(
        import_products(args.csv_file, args.images, args.dry_run)
    )

    for msg in messages:
        print(msg)

    print(f"\n{'=' * 50}")
    print(f"Results: {imported} imported, {skipped} skipped")

    if args.dry_run:
        print("\nThis was a dry run. Run without --dry-run to actually import.")


if __name__ == "__main__":
    main()
