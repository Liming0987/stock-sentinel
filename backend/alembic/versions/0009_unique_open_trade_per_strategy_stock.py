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
    # Remove duplicate open trades first — keep the oldest (lowest id) per
    # (strategy_id, stock_id) pair, close the rest as 'cancelled'.
    # This handles rows created by the concurrent-worker race condition.
    op.execute("""
        UPDATE trades
        SET status = 'cancelled'
        WHERE status = 'open'
          AND id NOT IN (
              SELECT MIN(id)
              FROM trades
              WHERE status = 'open'
              GROUP BY strategy_id, stock_id
          )
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_trades_open_strategy_stock
        ON trades (strategy_id, stock_id)
        WHERE status = 'open'
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_trades_open_strategy_stock")
