from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean, func
from app.models.database import Base


class Strategy(Base):
    """Registered trading strategy with its current performance metrics."""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    enabled = Column(Boolean, default=True)
    paper = Column(Boolean, default=True)  # always True initially

    # Performance metrics (recomputed on each strategy run)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_pnl = Column(Numeric(14, 2), default=0)  # realized P&L in USD
    unrealized_pnl = Column(Numeric(14, 2), default=0)
    win_rate = Column(Numeric(5, 4), default=0)  # 0..1
    avg_return_pct = Column(Numeric(8, 4), default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_run_at = Column(DateTime(timezone=True))


class Trade(Base):
    """A simulated trade executed by a strategy. Tracks entry/exit and P&L."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), index=True, nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), index=True, nullable=False)
    ticker = Column(String(10), index=True)

    side = Column(String(10))  # "buy" or "sell" (we'll start with long-only)
    qty = Column(Numeric(12, 4))
    entry_price = Column(Numeric(12, 4))
    exit_price = Column(Numeric(12, 4))
    stop_loss = Column(Numeric(12, 4))
    target = Column(Numeric(12, 4))

    status = Column(String(20), index=True)  # "open", "closed", "cancelled"
    pnl = Column(Numeric(14, 2))  # realized P&L (set when closed)
    return_pct = Column(Numeric(8, 4))  # % return on this trade

    # Alpaca order tracking (for paper trading via Alpaca)
    alpaca_order_id = Column(String(50))
    alpaca_client_order_id = Column(String(50))

    reasoning = Column(Text)  # why the strategy entered

    opened_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    closed_at = Column(DateTime(timezone=True))
