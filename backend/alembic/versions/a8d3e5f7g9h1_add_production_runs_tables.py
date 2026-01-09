"""Add production runs tables

Revision ID: a8d3e5f7g9h1
Revises: f3a4b8c9d21e
Create Date: 2025-01-13 17:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a8d3e5f7g9h1"
down_revision: Union[str, None] = "f3a4b8c9d21e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create production_runs table
    op.create_table(
        "production_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Identification
        sa.Column("run_number", sa.String(50), nullable=False),
        # Timing
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_hours", sa.Numeric(6, 2), nullable=True),
        # Slicer estimates
        sa.Column("estimated_print_time_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("estimated_total_filament_grams", sa.Numeric(10, 2), nullable=True),
        sa.Column("estimated_total_purge_grams", sa.Numeric(10, 2), nullable=True),
        # Actual usage
        sa.Column("actual_total_filament_grams", sa.Numeric(10, 2), nullable=True),
        sa.Column("actual_total_purge_grams", sa.Numeric(10, 2), nullable=True),
        # Waste tracking
        sa.Column("waste_filament_grams", sa.Numeric(10, 2), nullable=True),
        sa.Column("waste_reason", sa.Text, nullable=True),
        # Metadata
        sa.Column("slicer_software", sa.String(100), nullable=True),
        sa.Column("printer_name", sa.String(100), nullable=True),
        sa.Column("bed_temperature", sa.Integer, nullable=True),
        sa.Column("nozzle_temperature", sa.Integer, nullable=True),
        # Status
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        # Quality & failure tracking
        sa.Column("quality_rating", sa.Integer, nullable=True),
        sa.Column("quality_notes", sa.Text, nullable=True),
        # Reprint tracking
        sa.Column("original_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_reprint", sa.Boolean, nullable=False, server_default="false"),
        # Notes
        sa.Column("notes", sa.Text, nullable=True),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        # Primary key
        sa.PrimaryKeyConstraint("id"),
        # Foreign keys
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["original_run_id"], ["production_runs.id"], ondelete="SET NULL"),
        # Constraints
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'failed', 'cancelled')", name="check_status"
        ),
        sa.CheckConstraint(
            "quality_rating >= 1 AND quality_rating <= 5", name="check_quality_rating"
        ),
        sa.UniqueConstraint("tenant_id", "run_number", name="unique_run_number_per_tenant"),
    )

    # Create indexes
    op.create_index("idx_production_runs_tenant", "production_runs", ["tenant_id"])
    op.create_index("idx_production_runs_started", "production_runs", [sa.text("started_at DESC")])
    op.create_index("idx_production_runs_status", "production_runs", ["status"])
    op.create_index(
        "idx_production_runs_original",
        "production_runs",
        ["original_run_id"],
        postgresql_where=sa.text("original_run_id IS NOT NULL"),
    )

    # Enable RLS
    op.execute("ALTER TABLE production_runs ENABLE ROW LEVEL SECURITY")

    # Create RLS policy
    op.execute(
        """
        CREATE POLICY tenant_isolation_policy ON production_runs
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """
    )

    # Create production_run_items table
    op.create_table(
        "production_run_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("production_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Quantity
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("successful_quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_quantity", sa.Integer, nullable=False, server_default="0"),
        # Position tracking
        sa.Column("bed_position", sa.String(50), nullable=True),
        # Estimated costs (captured at time of print creation)
        sa.Column("estimated_material_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("estimated_component_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("estimated_labor_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("estimated_total_cost", sa.Numeric(10, 2), nullable=True),
        # Notes
        sa.Column("notes", sa.Text, nullable=True),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        # Primary key
        sa.PrimaryKeyConstraint("id"),
        # Foreign keys
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        # Constraints
        sa.CheckConstraint("quantity > 0", name="check_quantity_positive"),
    )

    # Create indexes
    op.create_index("idx_production_run_items_run", "production_run_items", ["production_run_id"])
    op.create_index("idx_production_run_items_product", "production_run_items", ["product_id"])

    # Enable RLS (inherits tenant_id from production_runs)
    op.execute("ALTER TABLE production_run_items ENABLE ROW LEVEL SECURITY")

    # Create RLS policy
    op.execute(
        """
        CREATE POLICY tenant_isolation_policy ON production_run_items
        USING (
            production_run_id IN (
                SELECT id FROM production_runs
                WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
            )
        )
    """
    )

    # Create production_run_materials table
    op.create_table(
        "production_run_materials",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("production_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("spool_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Slicer estimates
        sa.Column("estimated_weight_grams", sa.Numeric(10, 2), nullable=False),
        sa.Column("estimated_purge_grams", sa.Numeric(10, 2), server_default="0", nullable=False),
        # Spool weighing
        sa.Column("spool_weight_before_grams", sa.Numeric(10, 2), nullable=True),
        sa.Column("spool_weight_after_grams", sa.Numeric(10, 2), nullable=True),
        # Manual actual usage
        sa.Column("actual_weight_manual", sa.Numeric(10, 2), nullable=True),
        sa.Column("actual_purge_grams", sa.Numeric(10, 2), nullable=True),
        # Cost tracking
        sa.Column("cost_per_gram", sa.Numeric(10, 4), nullable=False),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        # Primary key
        sa.PrimaryKeyConstraint("id"),
        # Foreign keys
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spool_id"], ["spools.id"], ondelete="RESTRICT"),
    )

    # Create indexes
    op.create_index(
        "idx_production_run_materials_run", "production_run_materials", ["production_run_id"]
    )
    op.create_index("idx_production_run_materials_spool", "production_run_materials", ["spool_id"])

    # Enable RLS
    op.execute("ALTER TABLE production_run_materials ENABLE ROW LEVEL SECURITY")

    # Create RLS policy
    op.execute(
        """
        CREATE POLICY tenant_isolation_policy ON production_run_materials
        USING (
            production_run_id IN (
                SELECT id FROM production_runs
                WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
            )
        )
    """
    )

    # Add computed columns for production_run_materials
    # Note: PostgreSQL doesn't support GENERATED ALWAYS AS in ALTER TABLE for existing columns
    # We'll create views or use computed properties in the application layer instead


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("production_run_materials")
    op.drop_table("production_run_items")
    op.drop_table("production_runs")
