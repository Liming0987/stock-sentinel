"""Add alpaca_close_order_id to trades for EOD exit price correction.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("trades", sa.Column("alpaca_close_order_id", sa.String(50), nullable=True))


def downgrade():
    op.drop_column("trades", "alpaca_close_order_id")
