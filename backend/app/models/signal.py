from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from app.models.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), index=True)
    signal_type = Column(String(10))  # BUY, HOLD, AVOID
    confidence = Column(Numeric(4, 3))
    entry_low = Column(Numeric(10, 2))
    entry_high = Column(Numeric(10, 2))
    stop_loss = Column(Numeric(10, 2))
    target = Column(Numeric(10, 2))
    reasoning = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    outcome = Column(String(10))  # hit_target, hit_stop, expired


class TrendingSnapshot(Base):
    __tablename__ = "trending_snapshots"

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), index=True)
    mention_count = Column(Integer, default=0)
    mention_velocity = Column(Numeric(8, 2))
    avg_sentiment = Column(Numeric(4, 3))
    trend_score = Column(Numeric(6, 3))
    rank = Column(Integer)
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now())
