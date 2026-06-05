"""Financial state and outbox trace fields.

Revision ID: 0002_financial_state_and_outbox_trace
Revises: 0001_initial
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_financial_state_and_outbox_trace"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notification_outbox", sa.Column("correlation_id", sa.String(length=80), nullable=True))
    op.create_index("ix_notification_outbox_correlation_id", "notification_outbox", ["correlation_id"])
    op.alter_column("reconciliation_records", "company_id", existing_type=sa.String(length=36), nullable=True)

    # Existing demo databases may contain historical rows without source_event_id.
    op.execute("UPDATE ledger_entries SET source_event_id = 'legacy-missing-source' WHERE source_event_id IS NULL")
    op.alter_column("ledger_entries", "source_event_id", existing_type=sa.String(length=36), nullable=False)


def downgrade() -> None:
    op.alter_column("ledger_entries", "source_event_id", existing_type=sa.String(length=36), nullable=True)
    op.alter_column("reconciliation_records", "company_id", existing_type=sa.String(length=36), nullable=False)
    op.drop_index("ix_notification_outbox_correlation_id", table_name="notification_outbox")
    op.drop_column("notification_outbox", "correlation_id")
