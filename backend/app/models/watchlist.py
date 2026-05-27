from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from app.models.database import Base


class Watchlist(Base):
    """Personal watchlist — single-user, no auth required."""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), unique=True, index=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
