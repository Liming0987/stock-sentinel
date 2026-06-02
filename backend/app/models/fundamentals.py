from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from app.models.database import Base


class StockFundamentals(Base):
    __tablename__ = "stock_fundamentals"

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), unique=True, nullable=False, index=True)
    raw_metrics = Column(JSONB)
    score = Column(Numeric(5, 4), nullable=True)
    grade = Column(String(2))
    pillars = Column(JSONB)
    flags = Column(JSONB)
    next_earnings = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
