"""Add local file reference support to model_files

Revision ID: local_file_refs_01
Revises: cost_analysis_02
Create Date: 2026-01-19 16:30:00.000000

Adds support for storing local filesystem path references instead of uploading files.
Useful for OrcaSlicer project files and other large files that exist locally.

New fields:
- file_location: enum ('uploaded', 'local_reference') - where file is stored
- local_path: optional string - filesystem path for local references

Modified fields:
- file_url: now nullable (not needed for local references)
- file_size: now nullable (may not be known for local references)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "local_file_refs_01"
down_revision: Union[str, Sequence[str], None] = "cost_analysis_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add local file reference support."""
    # Add file_location column with default 'uploaded' for existing rows
    op.add_column(
        "model_files",
        sa.Column(
            "file_location",
            sa.String(20),
            nullable=False,
            server_default="uploaded",
            comment="Where file is stored: 'uploaded' (in storage) or 'local_reference' (filesystem path)",
        ),
    )

    # Add local_path column for local file references
    op.add_column(
        "model_files",
        sa.Column(
            "local_path",
            sa.String(1000),
            nullable=True,
            comment="Local filesystem path (for local_reference files)",
        ),
    )

    # Make file_url nullable (not needed for local references)
    op.alter_column(
        "model_files",
        "file_url",
        existing_type=sa.String(500),
        nullable=True,
    )

    # Make file_size nullable (may not be known for local references)
    op.alter_column(
        "model_files",
        "file_size",
        existing_type=sa.BigInteger(),
        nullable=True,
    )


def downgrade() -> None:
    """Remove local file reference support."""
    # Make file_size required again (set nulls to 0 first)
    op.execute("UPDATE model_files SET file_size = 0 WHERE file_size IS NULL")
    op.alter_column(
        "model_files",
        "file_size",
        existing_type=sa.BigInteger(),
        nullable=False,
    )

    # Make file_url required again (set nulls to empty string first)
    op.execute("UPDATE model_files SET file_url = '' WHERE file_url IS NULL")
    op.alter_column(
        "model_files",
        "file_url",
        existing_type=sa.String(500),
        nullable=False,
    )

    # Drop the new columns
    op.drop_column("model_files", "local_path")
    op.drop_column("model_files", "file_location")
