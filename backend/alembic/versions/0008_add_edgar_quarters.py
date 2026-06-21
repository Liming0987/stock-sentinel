"""Add edgar_quarters JSONB column to stock_fundamentals.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("stock_fundamentals", sa.Column("edgar_quarters", JSONB, nullable=True))


def downgrade():
    op.drop_column("stock_fundamentals", "edgar_quarters")
