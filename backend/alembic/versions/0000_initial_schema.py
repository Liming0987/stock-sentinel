"""Initial schema — squashed baseline built from the ORM models.

Replaces the former 0000–0012 chain. On a fresh database `alembic upgrade head` runs
only this migration, which creates the full current schema via SQLAlchemy's
Base.metadata.create_all — so the models are the single source of truth and stay in
sync with the create_all the app runs at startup.

All indexes that used to live only in migrations (composite/partial indexes and the
partial-unique "one open trade per strategy+stock" index) are now defined on the models
(trade.py / strategy_signal.py / trade_event.py), so create_all reproduces them exactly.

NOTE: this is a squash for a fresh start. It is NOT safe to apply on a database whose
alembic_version is already past 0000; those databases were torn down.

Revision ID: 0000
Revises: (base)
Create Date: 2026-09-04
"""
from alembic import op

# Import every model module so Base.metadata is fully populated before create_all.
from app.models.database import Base
from app.models import (  # noqa: F401
    stock, mention, signal, trade, watchlist, settings,
    fundamentals, strategy_signal, daily_report, task_error, trade_event,
)

revision = "0000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
