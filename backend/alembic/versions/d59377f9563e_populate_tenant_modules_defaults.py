"""Populate tenant_modules defaults for existing tenants.

Revision ID: d59377f9563e
Revises: external_listings_01
Create Date: 2026-01-14 16:00:56.917180

This data migration populates tenant_modules with default enabled modules
for all existing tenants based on their tenant_type. New tenants created
after this migration will have defaults set via OnboardingService.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd59377f9563e'
down_revision: Union[str, Sequence[str], None] = 'external_listings_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default modules enabled per tenant type
DEFAULT_MODULES_BY_TYPE = {
    "three_d_print": [
        "spools",
        "models",
        "printers",
        "production",
        "products",
        "orders",
        "categories",
    ],
    "hand_knitting": [
        "products",
        "orders",
        "categories",
    ],
    "machine_knitting": [
        "products",
        "orders",
        "categories",
    ],
    "generic": [
        "products",
        "orders",
        "categories",
    ],
}

# All available modules
ALL_MODULES = [
    "spools",
    "models",
    "printers",
    "production",
    "products",
    "orders",
    "categories",
]


def upgrade() -> None:
    """Populate tenant_modules defaults for existing tenants."""
    conn = op.get_bind()

    # Get all tenants that don't have any tenant_modules entries
    tenants_without_modules = conn.execute(
        sa.text("""
            SELECT t.id, t.tenant_type
            FROM tenants t
            LEFT JOIN tenant_modules tm ON t.id = tm.tenant_id
            WHERE tm.id IS NULL
        """)
    ).fetchall()

    if not tenants_without_modules:
        print("No tenants without module configuration found.")
        return

    print(f"Populating modules for {len(tenants_without_modules)} tenants...")

    for tenant_id, tenant_type in tenants_without_modules:
        # Get default modules for this tenant type
        default_modules = DEFAULT_MODULES_BY_TYPE.get(
            tenant_type,
            DEFAULT_MODULES_BY_TYPE["generic"],
        )

        # Insert module configuration for each module
        for module_name in ALL_MODULES:
            enabled = module_name in default_modules
            conn.execute(
                sa.text("""
                    INSERT INTO tenant_modules (tenant_id, module_name, enabled)
                    VALUES (:tenant_id, :module_name, :enabled)
                    ON CONFLICT (tenant_id, module_name) DO NOTHING
                """),
                {
                    "tenant_id": tenant_id,
                    "module_name": module_name,
                    "enabled": enabled,
                },
            )

        print(f"  - Tenant {tenant_id} ({tenant_type}): configured {len(ALL_MODULES)} modules")

    print("Done populating tenant module defaults.")


def downgrade() -> None:
    """Remove auto-populated tenant_modules (only system-set ones)."""
    conn = op.get_bind()

    # Only delete entries that were system-set (no enabled_by_user_id)
    result = conn.execute(
        sa.text("""
            DELETE FROM tenant_modules
            WHERE enabled_by_user_id IS NULL
        """)
    )

    print(f"Removed {result.rowcount} system-set tenant_modules entries.")
