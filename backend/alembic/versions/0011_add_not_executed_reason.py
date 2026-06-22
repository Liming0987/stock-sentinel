"""Add not_executed_reason to strategy_signals.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "strategy_signals",
        sa.Column("not_executed_reason", sa.String(50), nullable=True),
    )


def downgrade():
    op.drop_column("strategy_signals", "not_executed_reason")
