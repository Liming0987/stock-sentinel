from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from app.models.database import Base


class StrategySignal(Base):
    __tablename__ = "strategy_signals"

    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    ticker = Column(String(10), nullable=False, index=True)
    action = Column(String(10), nullable=False)  # buy / sell / hold
    confidence = Column(Numeric(4, 3))
    entry_price = Column(Numeric(12, 4))
    stop_loss = Column(Numeric(12, 4))
    target = Column(Numeric(12, 4))
    reasoning = Column(JSONB)  # list[str] preserved as JSON
    executed = Column(Boolean, default=False, nullable=False)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("ix_strategy_signals_strategy_created", "strategy_id", "created_at"),
    )
