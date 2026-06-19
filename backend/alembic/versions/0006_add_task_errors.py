"""Add task_errors table for surfacing Celery task failures in the UI.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "task_errors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_name", sa.String(100), nullable=False, index=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            index=True,
        ),
    )


def downgrade():
    op.drop_table("task_errors")
