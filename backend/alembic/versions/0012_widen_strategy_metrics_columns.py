"""widen strategy metrics columns to NUMERIC(14,4)

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "strategies", "sharpe_ratio",
        type_=sa.Numeric(14, 4), existing_nullable=True
    )
    op.alter_column(
        "strategies", "max_drawdown",
        type_=sa.Numeric(14, 4), existing_nullable=True
    )
    op.alter_column(
        "strategies", "best_trade_pct",
        type_=sa.Numeric(14, 4), existing_nullable=True
    )
    op.alter_column(
        "strategies", "worst_trade_pct",
        type_=sa.Numeric(14, 4), existing_nullable=True
    )


def downgrade():
    op.alter_column(
        "strategies", "sharpe_ratio",
        type_=sa.Numeric(8, 4), existing_nullable=True
    )
    op.alter_column(
        "strategies", "max_drawdown",
        type_=sa.Numeric(8, 4), existing_nullable=True
    )
    op.alter_column(
        "strategies", "best_trade_pct",
        type_=sa.Numeric(8, 4), existing_nullable=True
    )
    op.alter_column(
        "strategies", "worst_trade_pct",
        type_=sa.Numeric(8, 4), existing_nullable=True
    )
