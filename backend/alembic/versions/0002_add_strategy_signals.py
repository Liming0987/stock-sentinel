"""add strategy_signals table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-07

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "strategy_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("entry_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("stop_loss", sa.Numeric(12, 4), nullable=True),
        sa.Column("target", sa.Numeric(12, 4), nullable=True),
        sa.Column("reasoning", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("executed", sa.Boolean(), nullable=False),
        sa.Column("trade_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"]),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"]),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategy_signals_strategy_id", "strategy_signals", ["strategy_id"])
    op.create_index("ix_strategy_signals_ticker", "strategy_signals", ["ticker"])
    op.create_index("ix_strategy_signals_created_at", "strategy_signals", ["created_at"])
    op.create_index(
        "ix_strategy_signals_strategy_created",
        "strategy_signals",
        ["strategy_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("strategy_signals")
