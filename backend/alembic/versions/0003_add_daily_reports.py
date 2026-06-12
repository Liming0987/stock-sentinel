"""add daily_reports table

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("total_pnl", sa.Numeric(12, 4), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(12, 4), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(12, 4), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=True),
        sa.Column("winning_trades", sa.Integer(), nullable=True),
        sa.Column("signals_generated", sa.Integer(), nullable=True),
        sa.Column("best_strategy", sa.String(length=100), nullable=True),
        sa.Column("worst_strategy", sa.String(length=100), nullable=True),
        sa.Column("top_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("strategy_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_date"),
    )
    op.create_index("ix_daily_reports_date", "daily_reports", ["report_date"])


def downgrade() -> None:
    op.drop_table("daily_reports")
