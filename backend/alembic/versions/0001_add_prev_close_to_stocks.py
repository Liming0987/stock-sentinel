"""add prev_close to stocks

Revision ID: 0001
Revises:
Create Date: 2026-05-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stocks", sa.Column("prev_close", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("stocks", "prev_close")
