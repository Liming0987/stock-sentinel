"""Add advanced analytics columns to strategies table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("strategies", sa.Column("sharpe_ratio", sa.Numeric(8, 4), nullable=True))
    op.add_column("strategies", sa.Column("max_drawdown", sa.Numeric(8, 4), nullable=True))
    op.add_column("strategies", sa.Column("avg_hold_days", sa.Numeric(8, 2), nullable=True))
    op.add_column("strategies", sa.Column("consecutive_wins", sa.Integer(), server_default="0"))
    op.add_column("strategies", sa.Column("consecutive_losses", sa.Integer(), server_default="0"))
    op.add_column("strategies", sa.Column("best_trade_pct", sa.Numeric(8, 4), nullable=True))
    op.add_column("strategies", sa.Column("worst_trade_pct", sa.Numeric(8, 4), nullable=True))


def downgrade():
    op.drop_column("strategies", "worst_trade_pct")
    op.drop_column("strategies", "best_trade_pct")
    op.drop_column("strategies", "consecutive_losses")
    op.drop_column("strategies", "consecutive_wins")
    op.drop_column("strategies", "avg_hold_days")
    op.drop_column("strategies", "max_drawdown")
    op.drop_column("strategies", "sharpe_ratio")
