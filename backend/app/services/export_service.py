"""
CSV Export Service for Shopify-compatible exports.

Generates CSV files for products, orders, and inventory in formats
compatible with Shopify's import system.
"""

import csv
import io
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class ExportService:
    """Service for generating CSV exports in Shopify-compatible format."""

    def __init__(self, db: AsyncSession, tenant: Tenant):
        """
        Initialize export service.

        Args:
            db: Database session
            tenant: Current tenant for data isolation
        """
        self.db = db
        self.tenant = tenant

    # ============================================
    # Product Export (Shopify Product CSV Format)
    # ============================================

    async def export_products_csv(self) -> str:
        """
        Export all products in Shopify CSV format.

        Returns:
            CSV string ready for Shopify import
        """
        # Shopify product CSV columns
        fieldnames = [
            "Handle",
            "Title",
            "Body (HTML)",
            "Vendor",
            "Product Category",
            "Type",
            "Tags",
            "Published",
            "Option1 Name",
            "Option1 Value",
            "Option2 Name",
            "Option2 Value",
            "Option3 Name",
            "Option3 Value",
            "Variant SKU",
            "Variant Grams",
            "Variant Inventory Tracker",
            "Variant Inventory Qty",
            "Variant Inventory Policy",
            "Variant Fulfillment Service",
            "Variant Price",
            "Variant Compare At Price",
            "Variant Requires Shipping",
            "Variant Taxable",
            "Variant Barcode",
            "Image Src",
            "Image Position",
            "Image Alt Text",
            "Gift Card",
            "SEO Title",
            "SEO Description",
            "Variant Image",
            "Variant Weight Unit",
            "Cost per item",
            "Status",
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        # Fetch all products with related data
        result = await self.db.execute(
            select(Product)
            .where(Product.tenant_id == self.tenant.id)
            .options(
                selectinload(Product.pricing),
                selectinload(Product.images),
                selectinload(Product.categories),
            )
            .order_by(Product.created_at.desc())
        )
        products = result.scalars().all()

        for product in products:
            # Generate handle from SKU or name
            handle = self._generate_handle(product.sku or product.name)

            # Get price from first pricing entry
            price = Decimal("0")
            compare_at_price = ""
            if product.pricing:
                price = product.pricing[0].list_price or Decimal("0")

            # Get primary image
            image_src = ""
            image_alt = ""
            if product.images:
                for img in product.images:
                    if img.is_primary:
                        image_src = img.image_url
                        image_alt = img.alt_text or ""
                        break
                if not image_src and product.images:
                    image_src = product.images[0].image_url
                    image_alt = product.images[0].alt_text or ""

            # Get categories as tags
            tags = (
                ",".join(cat.name for cat in product.categories if cat.is_active)
                if product.categories
                else ""
            )

            # Determine product type from categories
            product_type = ""
            if product.categories:
                for cat in product.categories:
                    if cat.is_active:
                        product_type = cat.name
                        break

            # Calculate weight in grams (default to 100g if not set)
            weight_grams = 100
            if hasattr(product, "weight") and product.weight:
                weight_grams = int(product.weight * 1000)  # kg to grams

            row = {
                "Handle": handle,
                "Title": product.name,
                "Body (HTML)": product.description or "",
                "Vendor": "Mystmereforge",
                "Product Category": "",
                "Type": product_type,
                "Tags": tags,
                "Published": "TRUE" if product.is_active and product.shop_visible else "FALSE",
                "Option1 Name": "Title",
                "Option1 Value": "Default Title",
                "Option2 Name": "",
                "Option2 Value": "",
                "Option3 Name": "",
                "Option3 Value": "",
                "Variant SKU": product.sku or "",
                "Variant Grams": str(weight_grams),
                "Variant Inventory Tracker": "shopify",
                "Variant Inventory Qty": str(product.units_in_stock or 0),
                "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual",
                "Variant Price": str(price),
                "Variant Compare At Price": compare_at_price,
                "Variant Requires Shipping": "TRUE",
                "Variant Taxable": "TRUE",
                "Variant Barcode": "",
                "Image Src": image_src,
                "Image Position": "1" if image_src else "",
                "Image Alt Text": image_alt,
                "Gift Card": "FALSE",
                "SEO Title": product.name,
                "SEO Description": (product.description or "")[:160],
                "Variant Image": "",
                "Variant Weight Unit": "g",
                "Cost per item": "",
                "Status": "active" if product.is_active else "draft",
            }
            writer.writerow(row)

            # Write additional images as separate rows
            if product.images and len(product.images) > 1:
                for idx, img in enumerate(product.images[1:], start=2):
                    img_row = {key: "" for key in fieldnames}
                    img_row["Handle"] = handle
                    img_row["Image Src"] = img.image_url
                    img_row["Image Position"] = str(idx)
                    img_row["Image Alt Text"] = img.alt_text or ""
                    writer.writerow(img_row)

        return output.getvalue()

    # ============================================
    # Inventory Export (Shopify Inventory CSV Format)
    # ============================================

    async def export_inventory_csv(self, location: str = "Default") -> str:
        """
        Export inventory in Shopify CSV format.

        Args:
            location: Inventory location name

        Returns:
            CSV string ready for Shopify inventory import
        """
        # Shopify inventory CSV columns
        fieldnames = [
            "Handle",
            "Title",
            "Option1 Name",
            "Option1 Value",
            "Option2 Name",
            "Option2 Value",
            "Option3 Name",
            "Option3 Value",
            "SKU",
            "HS Code",
            "COO",
            location,  # Location column with quantity
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        # Fetch all products
        result = await self.db.execute(
            select(Product).where(Product.tenant_id == self.tenant.id).order_by(Product.sku)
        )
        products = result.scalars().all()

        for product in products:
            handle = self._generate_handle(product.sku or product.name)

            row = {
                "Handle": handle,
                "Title": product.name,
                "Option1 Name": "Title",
                "Option1 Value": "Default Title",
                "Option2 Name": "",
                "Option2 Value": "",
                "Option3 Name": "",
                "Option3 Value": "",
                "SKU": product.sku or "",
                "HS Code": "",
                "COO": "GB",  # Country of Origin - UK
                location: str(product.units_in_stock or 0),
            }
            writer.writerow(row)

        return output.getvalue()

    # ============================================
    # Order Export (Shopify Order CSV Format)
    # ============================================

    async def export_orders_csv(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
    ) -> str:
        """
        Export orders in Shopify CSV format.

        Args:
            start_date: Filter orders from this date (inclusive)
            end_date: Filter orders to this date (inclusive)
            status: Filter by order status

        Returns:
            CSV string in Shopify order format
        """
        # Shopify order CSV columns
        fieldnames = [
            "Name",
            "Email",
            "Financial Status",
            "Paid at",
            "Fulfillment Status",
            "Fulfilled at",
            "Accepts Marketing",
            "Currency",
            "Subtotal",
            "Shipping",
            "Taxes",
            "Total",
            "Discount Code",
            "Discount Amount",
            "Shipping Method",
            "Created at",
            "Lineitem quantity",
            "Lineitem name",
            "Lineitem price",
            "Lineitem compare at price",
            "Lineitem sku",
            "Lineitem requires shipping",
            "Lineitem taxable",
            "Lineitem fulfillment status",
            "Billing Name",
            "Billing Street",
            "Billing Address1",
            "Billing Address2",
            "Billing Company",
            "Billing City",
            "Billing Zip",
            "Billing Province",
            "Billing Country",
            "Billing Phone",
            "Shipping Name",
            "Shipping Street",
            "Shipping Address1",
            "Shipping Address2",
            "Shipping Company",
            "Shipping City",
            "Shipping Zip",
            "Shipping Province",
            "Shipping Country",
            "Shipping Phone",
            "Notes",
            "Note Attributes",
            "Cancelled at",
            "Payment Method",
            "Payment Reference",
            "Refunded Amount",
            "Vendor",
            "Id",
            "Tags",
            "Risk Level",
            "Source",
            "Phone",
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        # Build query
        query = (
            select(Order)
            .where(Order.tenant_id == self.tenant.id)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
        )

        # Apply filters
        if start_date:
            from datetime import timezone

            start_datetime = datetime.combine(start_date, datetime.min.time()).replace(
                tzinfo=timezone.utc
            )
            query = query.where(Order.created_at >= start_datetime)

        if end_date:
            from datetime import timezone

            end_datetime = datetime.combine(end_date, datetime.max.time()).replace(
                tzinfo=timezone.utc
            )
            query = query.where(Order.created_at <= end_datetime)

        if status:
            query = query.where(Order.status == status)

        result = await self.db.execute(query)
        orders = result.scalars().all()

        for order in orders:
            # Map our status to Shopify financial status
            financial_status = self._map_financial_status(order.status, order.payment_status)
            fulfillment_status = self._map_fulfillment_status(order.status)

            # Format dates
            created_at = (
                order.created_at.strftime("%Y-%m-%d %H:%M:%S %z") if order.created_at else ""
            )
            paid_at = created_at if order.payment_status == "completed" else ""
            fulfilled_at = (
                order.shipped_at.strftime("%Y-%m-%d %H:%M:%S %z") if order.shipped_at else ""
            )
            cancelled_at = ""
            if order.status == OrderStatus.CANCELLED:
                cancelled_at = (
                    order.updated_at.strftime("%Y-%m-%d %H:%M:%S %z") if order.updated_at else ""
                )

            # Calculate taxes (assuming 20% VAT included in price)
            taxes = Decimal("0")  # We include VAT in prices

            # Write a row for each line item
            for idx, item in enumerate(order.items):
                is_first_item = idx == 0

                row = {
                    "Name": order.order_number,
                    "Email": order.customer_email if is_first_item else "",
                    "Financial Status": financial_status if is_first_item else "",
                    "Paid at": paid_at if is_first_item else "",
                    "Fulfillment Status": fulfillment_status if is_first_item else "",
                    "Fulfilled at": fulfilled_at if is_first_item else "",
                    "Accepts Marketing": "no",
                    "Currency": order.currency if is_first_item else "",
                    "Subtotal": str(order.subtotal) if is_first_item else "",
                    "Shipping": str(order.shipping_cost) if is_first_item else "",
                    "Taxes": str(taxes) if is_first_item else "",
                    "Total": str(order.total) if is_first_item else "",
                    "Discount Code": order.discount_code or "" if is_first_item else "",
                    "Discount Amount": str(order.discount_amount)
                    if is_first_item and order.discount_amount
                    else "",
                    "Shipping Method": order.shipping_method if is_first_item else "",
                    "Created at": created_at if is_first_item else "",
                    "Lineitem quantity": str(item.quantity),
                    "Lineitem name": item.product_name,
                    "Lineitem price": str(item.unit_price),
                    "Lineitem compare at price": "",
                    "Lineitem sku": item.product_sku,
                    "Lineitem requires shipping": "true",
                    "Lineitem taxable": "true",
                    "Lineitem fulfillment status": fulfillment_status.lower()
                    if fulfillment_status
                    else "",
                    "Billing Name": order.customer_name if is_first_item else "",
                    "Billing Street": "",
                    "Billing Address1": order.shipping_address_line1 if is_first_item else "",
                    "Billing Address2": order.shipping_address_line2 or "" if is_first_item else "",
                    "Billing Company": "",
                    "Billing City": order.shipping_city if is_first_item else "",
                    "Billing Zip": order.shipping_postcode if is_first_item else "",
                    "Billing Province": order.shipping_county or "" if is_first_item else "",
                    "Billing Country": order.shipping_country if is_first_item else "",
                    "Billing Phone": order.customer_phone or "" if is_first_item else "",
                    "Shipping Name": order.customer_name if is_first_item else "",
                    "Shipping Street": "",
                    "Shipping Address1": order.shipping_address_line1 if is_first_item else "",
                    "Shipping Address2": order.shipping_address_line2 or ""
                    if is_first_item
                    else "",
                    "Shipping Company": "",
                    "Shipping City": order.shipping_city if is_first_item else "",
                    "Shipping Zip": order.shipping_postcode if is_first_item else "",
                    "Shipping Province": order.shipping_county or "" if is_first_item else "",
                    "Shipping Country": order.shipping_country if is_first_item else "",
                    "Shipping Phone": order.customer_phone or "" if is_first_item else "",
                    "Notes": order.customer_notes or "" if is_first_item else "",
                    "Note Attributes": "",
                    "Cancelled at": cancelled_at if is_first_item else "",
                    "Payment Method": order.payment_provider if is_first_item else "",
                    "Payment Reference": order.payment_id or "" if is_first_item else "",
                    "Refunded Amount": str(order.total)
                    if is_first_item and order.status == OrderStatus.REFUNDED
                    else "",
                    "Vendor": "Mystmereforge",
                    "Id": str(order.id) if is_first_item else "",
                    "Tags": "",
                    "Risk Level": "Low",
                    "Source": "web",
                    "Phone": order.customer_phone or "" if is_first_item else "",
                }
                writer.writerow(row)

        return output.getvalue()

    # ============================================
    # Accounting Export (Simple format for bookkeeping)
    # ============================================

    async def export_orders_accounting_csv(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> str:
        """
        Export orders in a simple accounting format.

        Useful for importing into accounting software like Xero, QuickBooks.

        Args:
            start_date: Filter orders from this date
            end_date: Filter orders to this date

        Returns:
            CSV string for accounting import
        """
        fieldnames = [
            "Date",
            "Invoice Number",
            "Customer Name",
            "Customer Email",
            "Description",
            "Quantity",
            "Unit Price",
            "Line Total",
            "Subtotal",
            "Shipping",
            "Discount",
            "Total",
            "Payment Status",
            "Payment Method",
            "Payment Reference",
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        # Build query
        query = (
            select(Order)
            .where(Order.tenant_id == self.tenant.id)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
        )

        if start_date:
            from datetime import timezone

            start_datetime = datetime.combine(start_date, datetime.min.time()).replace(
                tzinfo=timezone.utc
            )
            query = query.where(Order.created_at >= start_datetime)

        if end_date:
            from datetime import timezone

            end_datetime = datetime.combine(end_date, datetime.max.time()).replace(
                tzinfo=timezone.utc
            )
            query = query.where(Order.created_at <= end_datetime)

        # Exclude cancelled orders for accounting
        query = query.where(Order.status != OrderStatus.CANCELLED)

        result = await self.db.execute(query)
        orders = result.scalars().all()

        for order in orders:
            order_date = order.created_at.strftime("%Y-%m-%d") if order.created_at else ""

            for idx, item in enumerate(order.items):
                is_first_item = idx == 0

                row = {
                    "Date": order_date if is_first_item else "",
                    "Invoice Number": order.order_number if is_first_item else "",
                    "Customer Name": order.customer_name if is_first_item else "",
                    "Customer Email": order.customer_email if is_first_item else "",
                    "Description": item.product_name,
                    "Quantity": str(item.quantity),
                    "Unit Price": str(item.unit_price),
                    "Line Total": str(item.total_price),
                    "Subtotal": str(order.subtotal) if is_first_item else "",
                    "Shipping": str(order.shipping_cost) if is_first_item else "",
                    "Discount": str(order.discount_amount) if is_first_item else "",
                    "Total": str(order.total) if is_first_item else "",
                    "Payment Status": order.payment_status if is_first_item else "",
                    "Payment Method": order.payment_provider if is_first_item else "",
                    "Payment Reference": order.payment_id or "" if is_first_item else "",
                }
                writer.writerow(row)

        return output.getvalue()

    # ============================================
    # Helper Methods
    # ============================================

    def _generate_handle(self, text: str) -> str:
        """Generate a URL-friendly handle from text."""
        import re

        handle = text.lower()
        handle = re.sub(r"[^a-z0-9]+", "-", handle)
        handle = handle.strip("-")
        return handle

    def _map_financial_status(self, order_status: str, payment_status: str) -> str:
        """Map our order status to Shopify financial status."""
        if order_status == OrderStatus.REFUNDED:
            return "refunded"
        if payment_status == "completed":
            return "paid"
        if payment_status == "pending":
            return "pending"
        return "paid"  # Default

    def _map_fulfillment_status(self, order_status: str) -> str:
        """Map our order status to Shopify fulfillment status."""
        status_map = {
            OrderStatus.PENDING: "",
            OrderStatus.PROCESSING: "",
            OrderStatus.SHIPPED: "fulfilled",
            OrderStatus.DELIVERED: "fulfilled",
            OrderStatus.CANCELLED: "",
            OrderStatus.REFUNDED: "",
        }
        return status_map.get(order_status, "")


def get_export_service(db: AsyncSession, tenant: Tenant) -> ExportService:
    """
    Create export service instance.

    Use in FastAPI endpoint:
        service = get_export_service(db, tenant)
    """
    return ExportService(db, tenant)
