from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
from app.models.database import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True)
    report_date = Column(Date, unique=True, nullable=False)
    total_pnl = Column(Numeric(12, 4))
    realized_pnl = Column(Numeric(12, 4))
    unrealized_pnl = Column(Numeric(12, 4))
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    signals_generated = Column(Integer, default=0)
    best_strategy = Column(String(100))
    worst_strategy = Column(String(100))
    top_signals = Column(JSONB, default=list)
    strategy_breakdown = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
