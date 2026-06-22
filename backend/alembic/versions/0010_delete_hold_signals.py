"""Delete all existing hold signals — they are not actionable and flood the log.

Going forward the strategy runners no longer write hold signals (fixed in
app/services/strategy_runner.py). This migration removes the historical rows.

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-22
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM strategy_signals WHERE action = 'hold'")


def downgrade():
    pass  # holds cannot be recovered — downgrade is a no-op
