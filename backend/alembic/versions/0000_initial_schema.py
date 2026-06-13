"""initial schema — all base tables before any incremental migrations

Revision ID: 0000
Revises:
Create Date: 2026-06-13

This migration creates the base tables that earlier migrations assume exist.
Every op.create_table call is guarded by an existence check so it is safe
to run against a database that was bootstrapped via SQLAlchemy create_all.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    conn = op.get_bind()
    return conn.dialect.has_table(conn, name)


def upgrade() -> None:
    if not _table_exists("stocks"):
        op.create_table(
            "stocks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("ticker", sa.String(10), unique=True, nullable=False),
            sa.Column("name", sa.String(255)),
            sa.Column("sector", sa.String(100)),
            sa.Column("market_cap", sa.BigInteger()),
            sa.Column("avg_volume", sa.BigInteger()),
            sa.Column("last_price", sa.Numeric(10, 2)),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_stocks_ticker", "stocks", ["ticker"], unique=True)

    if not _table_exists("strategies"):
        op.create_table(
            "strategies",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(50), unique=True, nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("enabled", sa.Boolean(), default=True),
            sa.Column("paper", sa.Boolean(), default=True),
            sa.Column("total_trades", sa.Integer(), default=0),
            sa.Column("winning_trades", sa.Integer(), default=0),
            sa.Column("losing_trades", sa.Integer(), default=0),
            sa.Column("total_pnl", sa.Numeric(14, 2), default=0),
            sa.Column("unrealized_pnl", sa.Numeric(14, 2), default=0),
            sa.Column("win_rate", sa.Numeric(5, 4), default=0),
            sa.Column("avg_return_pct", sa.Numeric(8, 4), default=0),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("last_run_at", sa.DateTime(timezone=True)),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_strategies_name", "strategies", ["name"], unique=True)

    if not _table_exists("trades"):
        op.create_table(
            "trades",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("strategies.id"), nullable=False),
            sa.Column("stock_id", sa.Integer(), sa.ForeignKey("stocks.id"), nullable=False),
            sa.Column("ticker", sa.String(10)),
            sa.Column("side", sa.String(10)),
            sa.Column("qty", sa.Numeric(12, 4)),
            sa.Column("entry_price", sa.Numeric(12, 4)),
            sa.Column("exit_price", sa.Numeric(12, 4)),
            sa.Column("stop_loss", sa.Numeric(12, 4)),
            sa.Column("target", sa.Numeric(12, 4)),
            sa.Column("status", sa.String(20)),
            sa.Column("pnl", sa.Numeric(14, 2)),
            sa.Column("return_pct", sa.Numeric(8, 4)),
            sa.Column("alpaca_order_id", sa.String(50)),
            sa.Column("alpaca_client_order_id", sa.String(50)),
            sa.Column("reasoning", sa.Text()),
            sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("closed_at", sa.DateTime(timezone=True)),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_trades_strategy_id", "trades", ["strategy_id"])
        op.create_index("ix_trades_stock_id", "trades", ["stock_id"])
        op.create_index("ix_trades_ticker", "trades", ["ticker"])
        op.create_index("ix_trades_status", "trades", ["status"])
        op.create_index("ix_trades_opened_at", "trades", ["opened_at"])

    if not _table_exists("mentions"):
        op.create_table(
            "mentions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("stock_id", sa.Integer(), sa.ForeignKey("stocks.id")),
            sa.Column("source_type", sa.String(20)),
            sa.Column("source_id", sa.Integer()),
            sa.Column("sentiment_score", sa.Numeric(4, 3)),
            sa.Column("confidence", sa.Numeric(4, 3)),
            sa.Column("model_used", sa.String(20)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_mentions_stock_id", "mentions", ["stock_id"])
        op.create_index("ix_mentions_created_at", "mentions", ["created_at"])

    if not _table_exists("reddit_posts"):
        op.create_table(
            "reddit_posts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("external_id", sa.String(20), unique=True),
            sa.Column("subreddit", sa.String(50)),
            sa.Column("title", sa.Text()),
            sa.Column("body", sa.Text()),
            sa.Column("author", sa.String(50)),
            sa.Column("score", sa.Integer(), default=0),
            sa.Column("num_comments", sa.Integer(), default=0),
            sa.Column("url", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_reddit_posts_subreddit", "reddit_posts", ["subreddit"])

    if not _table_exists("stocktwits_messages"):
        op.create_table(
            "stocktwits_messages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("external_id", sa.String(20), unique=True),
            sa.Column("body", sa.Text()),
            sa.Column("author", sa.String(50)),
            sa.Column("sentiment_tag", sa.String(10)),
            sa.Column("likes", sa.Integer(), default=0),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("signals"):
        op.create_table(
            "signals",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("stock_id", sa.Integer(), sa.ForeignKey("stocks.id")),
            sa.Column("signal_type", sa.String(10)),
            sa.Column("confidence", sa.Numeric(4, 3)),
            sa.Column("entry_low", sa.Numeric(10, 2)),
            sa.Column("entry_high", sa.Numeric(10, 2)),
            sa.Column("stop_loss", sa.Numeric(10, 2)),
            sa.Column("target", sa.Numeric(10, 2)),
            sa.Column("reasoning", postgresql.JSONB()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("expires_at", sa.DateTime(timezone=True)),
            sa.Column("outcome", sa.String(10)),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_signals_stock_id", "signals", ["stock_id"])

    if not _table_exists("trending_snapshots"):
        op.create_table(
            "trending_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("stock_id", sa.Integer(), sa.ForeignKey("stocks.id")),
            sa.Column("mention_count", sa.Integer(), default=0),
            sa.Column("mention_velocity", sa.Numeric(8, 2)),
            sa.Column("avg_sentiment", sa.Numeric(4, 3)),
            sa.Column("trend_score", sa.Numeric(6, 3)),
            sa.Column("rank", sa.Integer()),
            sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_trending_snapshots_stock_id", "trending_snapshots", ["stock_id"])

    if not _table_exists("watchlist"):
        op.create_table(
            "watchlist",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("stock_id", sa.Integer(), sa.ForeignKey("stocks.id"), unique=True),
            sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_watchlist_stock_id", "watchlist", ["stock_id"])

    if not _table_exists("app_settings"):
        op.create_table(
            "app_settings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("key", sa.String(100), unique=True, nullable=False),
            sa.Column("value", sa.Text()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_app_settings_key", "app_settings", ["key"], unique=True)

    if not _table_exists("stock_fundamentals"):
        op.create_table(
            "stock_fundamentals",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("stock_id", sa.Integer(), sa.ForeignKey("stocks.id"), unique=True, nullable=False),
            sa.Column("raw_metrics", postgresql.JSONB()),
            sa.Column("score", sa.Numeric(5, 4)),
            sa.Column("grade", sa.String(2)),
            sa.Column("pillars", postgresql.JSONB()),
            sa.Column("flags", postgresql.JSONB()),
            sa.Column("next_earnings", sa.DateTime(timezone=True)),
            sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_stock_fundamentals_stock_id", "stock_fundamentals", ["stock_id"])


def downgrade() -> None:
    for table in [
        "stock_fundamentals", "app_settings", "watchlist", "trending_snapshots",
        "signals", "stocktwits_messages", "reddit_posts", "mentions",
        "trades", "strategies", "stocks",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
