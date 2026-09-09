from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, func
from app.models.database import Base


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
