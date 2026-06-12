"""Add trade_events audit table and performance indexes.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------ #
    # a) Create trade_events append-only audit table                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "trade_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "trade_id",
            sa.Integer(),
            sa.ForeignKey("trades.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("strategy_name", sa.String(100), nullable=True),
        sa.Column("side", sa.String(4), nullable=True),
        sa.Column("qty", sa.Numeric(12, 6), nullable=True),
        sa.Column("price", sa.Numeric(12, 4), nullable=True),
        sa.Column("pnl", sa.Numeric(14, 2), nullable=True),
        sa.Column("alpaca_order_id", sa.String(100), nullable=True),
        sa.Column("alpaca_position_id", sa.String(100), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------ #
    # b) Indexes on trade_events                                          #
    # ------------------------------------------------------------------ #
    op.create_index("ix_trade_events_trade_id", "trade_events", ["trade_id"])
    op.create_index("ix_trade_events_ticker", "trade_events", ["ticker"])
    op.create_index("ix_trade_events_event_type", "trade_events", ["event_type"])
    op.create_index("ix_trade_events_created_at", "trade_events", ["created_at"])

    # ------------------------------------------------------------------ #
    # c) Performance indexes on existing tables                           #
    # ------------------------------------------------------------------ #

    # Composite index for strategy runner open-position queries
    op.create_index("ix_trades_strategy_status", "trades", ["strategy_id", "status"])

    # Composite index for dedup checks
    op.create_index("ix_trades_ticker_status", "trades", ["ticker", "status"])

    # Partial index: only rows where alpaca_order_id is not NULL
    op.create_index(
        "ix_trades_alpaca_order_id",
        "trades",
        ["alpaca_order_id"],
        postgresql_where=sa.text("alpaca_order_id IS NOT NULL"),
    )

    # Index for daily report queries on strategy_signals
    op.create_index(
        "ix_strategy_signals_action_created",
        "strategy_signals",
        ["action", "created_at"],
    )

    # Primary lookup index on stocks.ticker (IF NOT EXISTS guard via try/except
    # is not available in Alembic, so we rely on the standard index creation;
    # the migration is idempotent via downgrade/upgrade cycle)
    op.create_index("ix_stocks_ticker", "stocks", ["ticker"])


def downgrade():
    # Drop in reverse order

    # c) Existing-table indexes
    op.drop_index("ix_stocks_ticker", table_name="stocks")
    op.drop_index("ix_strategy_signals_action_created", table_name="strategy_signals")
    op.drop_index("ix_trades_alpaca_order_id", table_name="trades")
    op.drop_index("ix_trades_ticker_status", table_name="trades")
    op.drop_index("ix_trades_strategy_status", table_name="trades")

    # b) trade_events indexes
    op.drop_index("ix_trade_events_created_at", table_name="trade_events")
    op.drop_index("ix_trade_events_event_type", table_name="trade_events")
    op.drop_index("ix_trade_events_ticker", table_name="trade_events")
    op.drop_index("ix_trade_events_trade_id", table_name="trade_events")

    # a) trade_events table
    op.drop_table("trade_events")
