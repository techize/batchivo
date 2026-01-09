"""Add model_files table for 3D model file tracking.

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-01-04 16:16:00.000000

This migration adds model_files table to track 3MF, STL, slicer project,
and gcode files associated with 3D models. Supports multiple files per
model (multi-part), versioning, and file type categorization.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "j4k5l6m7n8o9"
down_revision = "i3j4k5l6m7n8"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table_name)"
        ),
        {"table_name": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Create model_files table."""
    # Skip if already exists
    if table_exists("model_files"):
        return

    op.create_table(
        "model_files",
        # Primary key (UUIDMixin)
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Timestamps (TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        # Tenant isolation
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant this file belongs to",
        ),
        # Model reference
        sa.Column(
            "model_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="3D model this file is associated with",
        ),
        # File type categorization
        sa.Column(
            "file_type",
            sa.String(30),
            nullable=False,
            comment="File type: source_stl, source_3mf, slicer_project, gcode, plate_layout",
        ),
        # File storage
        sa.Column(
            "file_url",
            sa.String(500),
            nullable=False,
            comment="URL or path to the stored file",
        ),
        sa.Column(
            "original_filename",
            sa.String(255),
            nullable=False,
            comment="Original filename as uploaded",
        ),
        sa.Column(
            "file_size",
            sa.BigInteger(),
            nullable=False,
            comment="File size in bytes",
        ),
        sa.Column(
            "content_type",
            sa.String(100),
            nullable=True,
            comment="MIME content type (e.g., model/stl, model/3mf)",
        ),
        # Multi-part model support
        sa.Column(
            "part_name",
            sa.String(100),
            nullable=True,
            comment="Part name for multi-part models (e.g., 'body', 'wings', 'base')",
        ),
        # Versioning
        sa.Column(
            "version",
            sa.String(50),
            nullable=True,
            comment="Version identifier (e.g., 'v2.1', '2024-01-15')",
        ),
        # Primary file flag
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether this is the primary/default file for the model",
        ),
        # Notes
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="User notes about the file (e.g., slicer settings, print tips)",
        ),
        # Audit trail
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="When the file was uploaded",
        ),
        sa.Column(
            "uploaded_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="User who uploaded the file",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["models.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        comment="3D model files (STL, 3MF, gcode, slicer projects)",
    )

    # Create indexes for common queries
    op.create_index("ix_model_files_tenant_id", "model_files", ["tenant_id"])
    op.create_index("ix_model_files_model_id", "model_files", ["model_id"])
    op.create_index("ix_model_files_file_type", "model_files", ["file_type"])
    op.create_index("ix_model_files_is_primary", "model_files", ["is_primary"])
    # Composite index for common query pattern
    op.create_index(
        "ix_model_files_model_type",
        "model_files",
        ["model_id", "file_type"],
    )


def downgrade() -> None:
    """Drop model_files table."""
    if not table_exists("model_files"):
        return

    # Drop indexes
    op.drop_index("ix_model_files_model_type", table_name="model_files")
    op.drop_index("ix_model_files_is_primary", table_name="model_files")
    op.drop_index("ix_model_files_file_type", table_name="model_files")
    op.drop_index("ix_model_files_model_id", table_name="model_files")
    op.drop_index("ix_model_files_tenant_id", table_name="model_files")
    # Drop table
    op.drop_table("model_files")
