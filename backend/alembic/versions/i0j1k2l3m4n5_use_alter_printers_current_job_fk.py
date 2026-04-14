"""Name printers.current_job_id FK so use_alter can defer it during DROP

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-04-14 00:00:00.000000

The printers ↔ print_jobs relationship is circular:
  printers.current_job_id  → print_jobs.id
  print_jobs.assigned_printer_id → printers.id

SQLAlchemy cannot resolve drop order for circular FKs unless at least one
constraint is deferred with use_alter=True.  Adding use_alter also requires a
stable constraint name so Alembic can emit the matching ALTER TABLE … DROP
CONSTRAINT in the downgrade path.

If the existing FK is already unnamed (Postgres auto-names it), this migration
drops and re-creates it with the canonical name so the model and DB stay in
sync.
"""

from alembic import op


revision = "i0j1k2l3m4n5"
down_revision = "h9i0j1k2l3m4"
branch_labels = None
depends_on = None

_TABLE = "printers"
_COLUMN = "current_job_id"
_REF_TABLE = "print_jobs"
_CONSTRAINT = "fk_printers_current_job_id"


def upgrade() -> None:
    # Drop the FK if it exists (name may vary), then recreate with canonical name.
    # Use IF EXISTS to handle both fresh installs and upgrades from older schemas.
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}")
    op.create_foreign_key(
        _CONSTRAINT,
        _TABLE,
        _REF_TABLE,
        [_COLUMN],
        ["id"],
        ondelete="SET NULL",
        use_alter=True,
    )


def downgrade() -> None:
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.drop_constraint(_CONSTRAINT, type_="foreignkey")
        batch_op.create_foreign_key(
            None,
            _REF_TABLE,
            [_COLUMN],
            ["id"],
            ondelete="SET NULL",
        )
