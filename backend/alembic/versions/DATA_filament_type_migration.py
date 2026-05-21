"""Create filament_types table and migrate spools to two-tier structure.

Revision ID: data_filament_type_migration
Revises: merge_filament_type_heads
Create Date: 2026-05-19

This migration:
1. Creates the filament_types table (D-01 fields)
2. Deduplicates existing spool data into FilamentType records (DISTINCT ON brand+color+material_type_id)
3. Backfills filament_type_id on every spool
4. Removes all D-01 fields from spools (brand, color, color_hex, etc.)
5. Adds is_labeled column to spools
6. Enables Row-Level Security on filament_types

Abort condition: Any spool with NULL brand or NULL color causes RuntimeError before any schema changes.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "data_filament_type_migration"
down_revision: Union[str, Sequence[str], None] = "merge_filament_type_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migrate spools to two-tier FilamentType + Spool structure.

    Steps:
    1. Fail-fast: abort if any spool has NULL brand or color (D-06)
    2. Create filament_types table
    3. Insert deduplicated FilamentType records via DISTINCT ON
    4. Add filament_type_id to spools (nullable)
    5. Backfill filament_type_id on every spool
    6. Make filament_type_id NOT NULL
    7. Add FK from spools.filament_type_id → filament_types.id
    8. Add is_labeled column
    9. Drop FK for material_type_id + its index
    10. Drop all deprecated D-01 columns from spools
    11. Enable RLS on filament_types
    """
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1: FAIL FAST — abort if any spool has NULL brand or NULL color
    # ------------------------------------------------------------------
    result = conn.execute(sa.text("SELECT id FROM spools WHERE brand IS NULL OR color IS NULL"))
    bad_rows = result.fetchall()
    if bad_rows:
        bad_ids = [str(row[0]) for row in bad_rows]
        raise RuntimeError(
            f"Migration aborted: {len(bad_ids)} spool(s) have NULL brand or NULL color. "
            f"Fix these rows before migrating. IDs: {', '.join(bad_ids)}"
        )

    # ------------------------------------------------------------------
    # Step 2: Create filament_types table
    # ------------------------------------------------------------------
    op.create_table(
        "filament_types",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
            comment="Tenant ID for multi-tenant isolation",
        ),
        sa.Column(
            "material_type_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "brand",
            sa.String(100),
            nullable=False,
        ),
        sa.Column(
            "color",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "color_hex",
            sa.String(9),
            nullable=True,
        ),
        sa.Column(
            "finish",
            sa.String(50),
            nullable=True,
        ),
        sa.Column(
            "diameter",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="1.75",
        ),
        sa.Column(
            "density",
            sa.Numeric(5, 3),
            nullable=True,
        ),
        sa.Column(
            "extruder_temp",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "bed_temp",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "translucent",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "glow",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "pattern",
            sa.String(50),
            nullable=True,
        ),
        sa.Column(
            "spool_type",
            sa.String(50),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "has_sample",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["material_type_id"],
            ["material_types.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_filament_types_tenant_id"),
        "filament_types",
        ["tenant_id"],
    )
    op.create_index(
        op.f("ix_filament_types_material_type_id"),
        "filament_types",
        ["material_type_id"],
    )

    # ------------------------------------------------------------------
    # Step 3: Insert deduplicated FilamentType records (DISTINCT ON)
    #   One FilamentType per (tenant_id, brand, color, material_type_id).
    #   Values taken from the oldest spool in each group (created_at ASC).
    # ------------------------------------------------------------------
    conn.execute(
        sa.text(
            """
            INSERT INTO filament_types (
                id, tenant_id, material_type_id, brand, color, color_hex, finish,
                diameter, density, extruder_temp, bed_temp,
                translucent, glow, pattern, spool_type, notes,
                has_sample, created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                tenant_id,
                material_type_id,
                brand,
                color,
                color_hex,
                finish,
                COALESCE(diameter, 1.75),
                density,
                extruder_temp,
                bed_temp,
                COALESCE(translucent, false),
                COALESCE(glow, false),
                pattern,
                spool_type,
                notes,
                false,
                now(),
                now()
            FROM (
                SELECT DISTINCT ON (tenant_id, brand, color, material_type_id)
                    tenant_id, material_type_id, brand, color, color_hex, finish,
                    diameter, density, extruder_temp, bed_temp,
                    translucent, glow, pattern, spool_type, notes
                FROM spools
                ORDER BY tenant_id, brand, color, material_type_id, created_at ASC
            ) oldest_spool
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 4: Add filament_type_id to spools as nullable UUID
    # ------------------------------------------------------------------
    op.add_column(
        "spools",
        sa.Column("filament_type_id", sa.UUID(), nullable=True),
    )

    # ------------------------------------------------------------------
    # Step 5: Backfill filament_type_id on every spool
    # ------------------------------------------------------------------
    conn.execute(
        sa.text(
            """
            UPDATE spools s
            SET filament_type_id = ft.id
            FROM filament_types ft
            WHERE s.tenant_id = ft.tenant_id
              AND s.brand = ft.brand
              AND s.color = ft.color
              AND s.material_type_id = ft.material_type_id
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 6: Make filament_type_id NOT NULL
    # ------------------------------------------------------------------
    op.alter_column("spools", "filament_type_id", nullable=False)

    # ------------------------------------------------------------------
    # Step 7: Add FK from spools.filament_type_id → filament_types.id
    # ------------------------------------------------------------------
    op.create_foreign_key(
        "fk_spools_filament_type_id",
        "spools",
        "filament_types",
        ["filament_type_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------
    # Step 8: Add is_labeled column to spools (default false)
    # ------------------------------------------------------------------
    op.add_column(
        "spools",
        sa.Column(
            "is_labeled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # ------------------------------------------------------------------
    # Step 9: Drop FK constraint and index for material_type_id on spools
    #   The FK was created without an explicit name in d80bf772b461;
    #   PostgreSQL auto-named it spools_material_type_id_fkey.
    # ------------------------------------------------------------------
    op.drop_index(op.f("ix_spools_material_type_id"), table_name="spools")
    op.drop_constraint("spools_material_type_id_fkey", "spools", type_="foreignkey")

    # ------------------------------------------------------------------
    # Step 10: Drop all deprecated D-01 columns from spools
    # ------------------------------------------------------------------
    op.drop_column("spools", "brand")
    op.drop_column("spools", "color")
    op.drop_column("spools", "color_hex")
    op.drop_column("spools", "finish")
    op.drop_column("spools", "diameter")
    op.drop_column("spools", "density")
    op.drop_column("spools", "extruder_temp")
    op.drop_column("spools", "bed_temp")
    op.drop_column("spools", "translucent")
    op.drop_column("spools", "glow")
    op.drop_column("spools", "pattern")
    op.drop_column("spools", "spool_type")
    op.drop_column("spools", "notes")
    op.drop_column("spools", "material_type_id")
    op.drop_column("spools", "purchased_quantity")
    op.drop_column("spools", "spools_remaining")

    # ------------------------------------------------------------------
    # Step 11: Enable Row-Level Security on filament_types
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TABLE filament_types ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE filament_types FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            "CREATE POLICY tenant_isolation_select ON filament_types "
            "FOR SELECT "
            "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
        )
    )
    op.execute(
        sa.text(
            "CREATE POLICY tenant_isolation_insert ON filament_types "
            "FOR INSERT "
            "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
        )
    )
    op.execute(
        sa.text(
            "CREATE POLICY tenant_isolation_update ON filament_types "
            "FOR UPDATE "
            "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
        )
    )
    op.execute(
        sa.text(
            "CREATE POLICY tenant_isolation_delete ON filament_types "
            "FOR DELETE "
            "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
        )
    )


def downgrade() -> None:
    """
    Reverse the filament_types migration.

    Steps (reverse of upgrade):
    1. Restore 16 removed spool columns as nullable (D-08: NULL-filled is acceptable)
    2. Drop fk_spools_filament_type_id, filament_type_id column, and is_labeled column
    3. Drop RLS policies from filament_types
    4. Drop indexes and filament_types table
    """
    # ------------------------------------------------------------------
    # Step 1: Restore removed spool columns as nullable (NULL-filled, D-08)
    # ------------------------------------------------------------------
    op.add_column("spools", sa.Column("brand", sa.String(100), nullable=True))
    op.add_column("spools", sa.Column("color", sa.String(50), nullable=True))
    op.add_column("spools", sa.Column("color_hex", sa.String(9), nullable=True))
    op.add_column("spools", sa.Column("finish", sa.String(50), nullable=True))
    op.add_column("spools", sa.Column("diameter", sa.Numeric(4, 2), nullable=True))
    op.add_column("spools", sa.Column("density", sa.Numeric(5, 3), nullable=True))
    op.add_column("spools", sa.Column("extruder_temp", sa.Integer(), nullable=True))
    op.add_column("spools", sa.Column("bed_temp", sa.Integer(), nullable=True))
    op.add_column("spools", sa.Column("translucent", sa.Boolean(), nullable=True))
    op.add_column("spools", sa.Column("glow", sa.Boolean(), nullable=True))
    op.add_column("spools", sa.Column("pattern", sa.String(50), nullable=True))
    op.add_column("spools", sa.Column("spool_type", sa.String(50), nullable=True))
    op.add_column("spools", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("spools", sa.Column("material_type_id", sa.UUID(), nullable=True))
    op.add_column("spools", sa.Column("purchased_quantity", sa.Integer(), nullable=True))
    op.add_column("spools", sa.Column("spools_remaining", sa.Integer(), nullable=True))

    # ------------------------------------------------------------------
    # Step 2: Drop FK and columns added in upgrade
    # ------------------------------------------------------------------
    op.drop_constraint("fk_spools_filament_type_id", "spools", type_="foreignkey")
    op.drop_column("spools", "filament_type_id")
    op.drop_column("spools", "is_labeled")

    # ------------------------------------------------------------------
    # Step 3: Drop RLS policies from filament_types before dropping table
    # ------------------------------------------------------------------
    op.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation_select ON filament_types"))
    op.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation_insert ON filament_types"))
    op.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation_update ON filament_types"))
    op.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation_delete ON filament_types"))

    # ------------------------------------------------------------------
    # Step 4: Drop indexes and filament_types table
    # ------------------------------------------------------------------
    op.drop_index(
        op.f("ix_filament_types_material_type_id"),
        table_name="filament_types",
    )
    op.drop_index(
        op.f("ix_filament_types_tenant_id"),
        table_name="filament_types",
    )
    op.drop_table("filament_types")
