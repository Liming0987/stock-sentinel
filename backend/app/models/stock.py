from sqlalchemy import Column, Integer, String, BigInteger, Numeric, DateTime, func
from app.models.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255))
    sector = Column(String(100))
    market_cap = Column(BigInteger)
    avg_volume = Column(BigInteger)
    last_price = Column(Numeric(10, 2))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
