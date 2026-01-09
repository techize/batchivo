"""create_rls_policies

Revision ID: 8c3c671816d9
Revises: cffc14267961
Create Date: 2025-12-30 13:30:00.000000

This migration creates Row-Level Security (RLS) policies for all tenant-scoped
tables. Each table gets 4 policies for complete CRUD coverage:

1. SELECT policy: Controls which rows can be read
2. INSERT policy: Controls which rows can be inserted (WITH CHECK)
3. UPDATE policy: Controls which rows can be modified
4. DELETE policy: Controls which rows can be deleted

Policies use the PostgreSQL session variable `app.current_tenant_id` which must
be set by the application before any database operations. The middleware sets
this via: SET app.current_tenant_id = '{tenant_id}'

Security Model:
- If app.current_tenant_id is not set, queries return empty results (safe default)
- If app.current_tenant_id doesn't match row's tenant_id, access is denied
- Superusers bypass RLS (used for migrations), app_user does not
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "8c3c671816d9"
down_revision: Union[str, Sequence[str], None] = "cffc14267961"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All tables with tenant_id column that need RLS policies
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


def create_policy(table: str, operation: str, policy_type: str) -> str:
    """
    Generate SQL for creating an RLS policy.

    Args:
        table: Table name
        operation: SQL operation (SELECT, INSERT, UPDATE, DELETE)
        policy_type: Either 'USING' (for SELECT/UPDATE/DELETE) or 'WITH CHECK' (for INSERT)

    The current_setting function with 'true' as second parameter returns NULL
    if the setting doesn't exist, rather than raising an error. This ensures
    queries don't fail if middleware hasn't set the tenant context yet -
    they just return no rows (safe default).
    """
    policy_name = f"tenant_isolation_{operation.lower()}"

    if policy_type == "WITH CHECK":
        # INSERT uses WITH CHECK to validate new rows
        return f"""
            CREATE POLICY {policy_name} ON {table}
            FOR {operation}
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
        """
    else:
        # SELECT, UPDATE, DELETE use USING to filter existing rows
        return f"""
            CREATE POLICY {policy_name} ON {table}
            FOR {operation}
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
        """


def upgrade() -> None:
    """
    Create RLS policies for all tenant-scoped tables.

    Each table gets 4 policies:
    - tenant_isolation_select: Filter rows by tenant_id on SELECT
    - tenant_isolation_insert: Validate tenant_id on INSERT
    - tenant_isolation_update: Filter and validate on UPDATE
    - tenant_isolation_delete: Filter rows by tenant_id on DELETE

    Note: UPDATE needs both USING (filter existing) and WITH CHECK (validate new).
    We create it with just USING for simplicity since tenant_id shouldn't change.
    """
    for table in TENANT_SCOPED_TABLES:
        # SELECT policy - filter which rows can be read
        op.execute(text(create_policy(table, "SELECT", "USING")))

        # INSERT policy - validate tenant_id on new rows
        op.execute(text(create_policy(table, "INSERT", "WITH CHECK")))

        # UPDATE policy - filter which rows can be modified
        # Note: If tenant_id could be modified, we'd also need WITH CHECK
        # But tenant_id should never change, so USING alone is sufficient
        op.execute(text(create_policy(table, "UPDATE", "USING")))

        # DELETE policy - filter which rows can be deleted
        op.execute(text(create_policy(table, "DELETE", "USING")))


def downgrade() -> None:
    """
    Drop all RLS policies from tenant-scoped tables.

    Warning: This removes tenant isolation at the policy level.
    The tables will still have RLS enabled but with no policies,
    meaning NO ACCESS for non-superusers until the previous migration
    is also rolled back.
    """
    for table in TENANT_SCOPED_TABLES:
        # Drop all 4 policies
        op.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_select ON {table}"))
        op.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_insert ON {table}"))
        op.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_update ON {table}"))
        op.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_delete ON {table}"))
