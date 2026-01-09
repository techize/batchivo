"""enable_rls_on_tenant_tables

Revision ID: cffc14267961
Revises: ecce200bf082
Create Date: 2025-12-30 13:28:21.135172

This migration enables PostgreSQL Row-Level Security (RLS) on all tenant-scoped
tables. RLS provides database-level tenant isolation, ensuring that even if
application code has bugs, data cannot leak between tenants.

Tables with tenant_id column that need RLS:
- Core: categories, products, models, orders, customers, customer_addresses
- Inventory: spools, consumable_types, consumable_purchases, consumable_usage,
             inventory_transactions
- Printers: printers, printer_connections, ams_slot_mappings
- Shop: sales_channels, product_images, pages, reviews, designers
- Discounts: discount_codes, discount_usages
- Production: production_runs
- Webhooks: webhook_subscriptions
- Users: user_tenants (tenant membership)
- Audit: audit_logs, return_requests

Tables WITHOUT tenant_id (global/shared):
- tenants: Root tenant table
- users: Users can belong to multiple tenants
- material_types: Shared reference data
- payment_logs: Linked via order_id, not direct tenant_id
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "cffc14267961"
down_revision: Union[str, Sequence[str], None] = "ecce200bf082"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All tables with tenant_id column that need RLS enabled
TENANT_SCOPED_TABLES = [
    # Core business tables
    "categories",
    "products",
    "models",
    "orders",
    "customers",
    "customer_addresses",
    # Inventory management
    "spools",
    "consumable_types",
    "consumable_purchases",
    "consumable_usage",
    "inventory_transactions",
    # Printer management
    "printers",
    "printer_connections",
    "ams_slot_mappings",
    # Shop/storefront
    "sales_channels",
    "product_images",
    "pages",
    "reviews",
    "designers",
    # Discounts
    "discount_codes",
    "discount_usages",
    # Production
    "production_runs",
    # Webhooks
    "webhook_subscriptions",
    # User-tenant membership
    "user_tenants",
    # Audit/returns
    "audit_logs",
    "return_requests",
]


def upgrade() -> None:
    """
    Enable Row-Level Security on all tenant-scoped tables.

    RLS must be enabled before policies can be created. This migration only
    enables RLS; policies will be created in the next migration (80.3).

    Note: Enabling RLS without policies will BLOCK ALL ACCESS for non-superusers
    until policies are created. This is by design - we want to ensure policies
    exist before any data access is allowed.
    """
    for table in TENANT_SCOPED_TABLES:
        # Enable RLS on the table
        # FORCE ensures RLS applies to table owner too (belt and suspenders)
        op.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))

        # Also set FORCE ROW LEVEL SECURITY to ensure policies apply to table owner
        # This prevents bypassing RLS even if connected as the table owner
        op.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    """
    Disable Row-Level Security on all tenant-scoped tables.

    Warning: This removes tenant isolation at the database level.
    Only run this if you're certain you want to remove RLS protection.
    """
    for table in TENANT_SCOPED_TABLES:
        # Remove FORCE first
        op.execute(text(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY"))

        # Then disable RLS entirely
        op.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
