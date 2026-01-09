"""Add print queue tables

Revision ID: a4b5c6d7e8f9
Revises: h8i9j0k1l2m3
Create Date: 2024-12-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create print_jobs table
    op.create_table(
        "print_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "tenant_id", sa.UUID(), nullable=False, comment="Tenant ID for multi-tenant isolation"
        ),
        sa.Column(
            "model_id",
            sa.UUID(),
            nullable=True,
            comment="Model to print (if printing a model directly)",
        ),
        sa.Column(
            "product_id",
            sa.UUID(),
            nullable=True,
            comment="Product to print (if printing for a product)",
        ),
        sa.Column(
            "quantity", sa.Integer(), nullable=False, default=1, comment="Number of copies to print"
        ),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            default="normal",
            comment="Job priority level",
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, default="pending", comment="Current job status"
        ),
        sa.Column(
            "assigned_printer_id", sa.UUID(), nullable=True, comment="Printer assigned to this job"
        ),
        sa.Column(
            "estimated_duration_hours",
            sa.Numeric(6, 2),
            nullable=True,
            comment="Estimated print duration in hours",
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=True, comment="When printing started"
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When printing completed",
        ),
        sa.Column("queue_position", sa.Integer(), nullable=True, comment="Position in the queue"),
        sa.Column(
            "reference",
            sa.String(100),
            nullable=True,
            comment="External reference (order ID, etc.)",
        ),
        sa.Column("notes", sa.Text(), nullable=True, comment="Additional notes for the job"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="Error message if job failed"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_printer_id"], ["printers.id"], ondelete="SET NULL"),
        comment="Print jobs queue for 3D printers",
    )

    # Create indexes for print_jobs
    op.create_index("ix_print_jobs_tenant_id", "print_jobs", ["tenant_id"])
    op.create_index("ix_print_jobs_model_id", "print_jobs", ["model_id"])
    op.create_index("ix_print_jobs_product_id", "print_jobs", ["product_id"])
    op.create_index("ix_print_jobs_assigned_printer_id", "print_jobs", ["assigned_printer_id"])
    op.create_index("ix_print_jobs_priority", "print_jobs", ["priority"])
    op.create_index("ix_print_jobs_status", "print_jobs", ["status"])
    op.create_index(
        "ix_print_jobs_queue_order",
        "print_jobs",
        ["tenant_id", "status", sa.text("priority DESC"), "created_at"],
    )
    op.create_index("ix_print_jobs_printer_status", "print_jobs", ["assigned_printer_id", "status"])

    # Add current_status column to printers table
    op.add_column(
        "printers",
        sa.Column(
            "current_status",
            sa.String(20),
            nullable=False,
            server_default="offline",
            comment="Current operational status for queue management",
        ),
    )
    op.create_index("ix_printers_current_status", "printers", ["current_status"])

    # Add current_job_id column to printers table
    op.add_column(
        "printers",
        sa.Column(
            "current_job_id", sa.UUID(), nullable=True, comment="Currently printing job (if any)"
        ),
    )
    op.create_foreign_key(
        "fk_printers_current_job_id",
        "printers",
        "print_jobs",
        ["current_job_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Enable RLS for print_jobs (PostgreSQL only)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
                ALTER TABLE print_jobs ENABLE ROW LEVEL SECURITY;

                -- Policy for tenant isolation
                DROP POLICY IF EXISTS print_jobs_tenant_isolation ON print_jobs;
                CREATE POLICY print_jobs_tenant_isolation ON print_jobs
                    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Disable RLS
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'print_jobs') THEN
                ALTER TABLE print_jobs DISABLE ROW LEVEL SECURITY;
                DROP POLICY IF EXISTS print_jobs_tenant_isolation ON print_jobs;
            END IF;
        END $$;
    """)

    # Remove current_job_id from printers
    op.drop_constraint("fk_printers_current_job_id", "printers", type_="foreignkey")
    op.drop_column("printers", "current_job_id")

    # Remove current_status from printers
    op.drop_index("ix_printers_current_status", table_name="printers")
    op.drop_column("printers", "current_status")

    # Drop print_jobs table and indexes
    op.drop_index("ix_print_jobs_printer_status", table_name="print_jobs")
    op.drop_index("ix_print_jobs_queue_order", table_name="print_jobs")
    op.drop_index("ix_print_jobs_status", table_name="print_jobs")
    op.drop_index("ix_print_jobs_priority", table_name="print_jobs")
    op.drop_index("ix_print_jobs_assigned_printer_id", table_name="print_jobs")
    op.drop_index("ix_print_jobs_product_id", table_name="print_jobs")
    op.drop_index("ix_print_jobs_model_id", table_name="print_jobs")
    op.drop_index("ix_print_jobs_tenant_id", table_name="print_jobs")
    op.drop_table("print_jobs")
