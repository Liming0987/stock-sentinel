"""Partial unique index: one open trade per (strategy_id, stock_id).

Prevents concurrent intraday workers from opening duplicate trades for
the same strategy+ticker when two runs overlap.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-22
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE UNIQUE INDEX uq_trades_open_strategy_stock
        ON trades (strategy_id, stock_id)
        WHERE status = 'open'
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_trades_open_strategy_stock")
