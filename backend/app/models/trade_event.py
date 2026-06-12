"""Append-only audit log for every trade lifecycle event.
This table is NEVER updated — only INSERT is permitted."""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from app.models.database import Base


class TradeEvent(Base):
    __tablename__ = "trade_events"

    id = Column(Integer, primary_key=True)

    # trade_id is nullable: some events (e.g., orphaned Alpaca position cancelled)
    # have no corresponding DB trade row yet
    trade_id = Column(Integer, ForeignKey("trades.id", ondelete="SET NULL"), nullable=True, index=True)

    # Event classification
    event_type = Column(String(30), nullable=False)
    # Valid values:
    #   opened          — trade successfully opened (Alpaca confirmed fill)
    #   closed          — trade successfully closed (Alpaca confirmed fill)
    #   cancelled       — trade cancelled before fill
    #   open_failed     — Alpaca order placed but fill timed out; order cancelled
    #   close_failed    — Alpaca close call failed
    #   reconciled      — DB trade synced/corrected by reconciler
    #   orphan_cancelled — Alpaca position existed with no DB record; was closed via API
    #   orphan_imported  — Alpaca position imported into DB as a legacy trade
    #   db_orphan_closed — DB trade had no matching Alpaca position; marked closed

    ticker = Column(String(10), nullable=False, index=True)
    strategy_name = Column(String(100))
    side = Column(String(4))        # buy / sell
    qty = Column(Numeric(12, 6))
    price = Column(Numeric(12, 4))  # fill price or last known price
    pnl = Column(Numeric(14, 2))    # realized PnL if applicable

    alpaca_order_id = Column(String(100))
    alpaca_position_id = Column(String(100))  # for position-level events

    # Freeform context (reason, error message, reconciler notes, etc.)
    meta = Column(JSONB, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
        index=True,
    )
