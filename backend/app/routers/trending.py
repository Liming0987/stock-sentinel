from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.stock import Stock
from app.models.mention import Mention
from app.models.signal import TrendingSnapshot
from app.services.price_service import PriceService

router = APIRouter()
price_service = PriceService()

# Popular tickers to show when DB is empty (bootstrap)
BOOTSTRAP_TICKERS = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "AMZN", "META", "GOOG", "PLTR", "SOFI"]


@router.get("")
async def get_trending_stocks(
    limit: int = Query(default=20, le=50),
    timeframe: str = Query(default="24h", regex="^(1h|6h|24h|7d)$"),
    sector: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get top trending stocks ranked by composite score."""
    # Try DB first
    result = await db.execute(
        select(TrendingSnapshot)
        .join(Stock, TrendingSnapshot.stock_id == Stock.id)
        .order_by(desc(TrendingSnapshot.trend_score))
        .limit(limit)
    )
    snapshots = result.scalars().all()

    if snapshots:
        stocks = []
        for snap in snapshots:
            stock = await db.get(Stock, snap.stock_id)
            stocks.append({
                "ticker": stock.ticker,
                "name": stock.name or stock.ticker,
                "price": float(stock.last_price) if stock.last_price else 0,
                "change_pct": 0,
                "mention_count": snap.mention_count,
                "mention_velocity": float(snap.mention_velocity) if snap.mention_velocity else 0,
                "sentiment_score": float(snap.avg_sentiment) if snap.avg_sentiment else 0,
                "trend_score": float(snap.trend_score) if snap.trend_score else 0,
                "volume_ratio": 1.0,
                "sources": ["reddit"],
            })
        return {"timeframe": timeframe, "stocks": stocks, "updated_at": datetime.now(timezone.utc).isoformat()}

    # Bootstrap: fetch live data from yfinance for popular tickers
    stocks = []
    for ticker in BOOTSTRAP_TICKERS[:limit]:
        try:
            df = price_service.get_price_data(ticker, period="5d", interval="1d")
            if df is None or len(df) < 2:
                continue
            info = price_service.get_stock_info(ticker)
            last_close = float(df["Close"].iloc[-1])
            prev_close = float(df["Close"].iloc[-2])
            change_pct = round((last_close - prev_close) / prev_close * 100, 2)
            indicators = price_service.compute_indicators(df) if len(df) >= 20 else {}

            stocks.append({
                "ticker": ticker,
                "name": info.get("name", ticker),
                "price": round(last_close, 2),
                "change_pct": change_pct,
                "mention_count": 0,
                "mention_velocity": 0,
                "sentiment_score": 0,
                "trend_score": 0,
                "volume_ratio": indicators.get("volume_ratio", 1.0),
                "sources": [],
            })
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")

    return {"timeframe": timeframe, "stocks": stocks, "updated_at": datetime.now(timezone.utc).isoformat()}


@router.get("/{ticker}")
async def get_trending_detail(ticker: str):
    """Get detailed trending data for a specific stock."""
    df = price_service.get_price_data(ticker.upper(), period="1mo", interval="1d")
    info = price_service.get_stock_info(ticker.upper())
    indicators = price_service.compute_indicators(df) if df is not None and len(df) >= 20 else {}

    last_close = float(df["Close"].iloc[-1]) if df is not None and not df.empty else 0
    prev_close = float(df["Close"].iloc[-2]) if df is not None and len(df) >= 2 else last_close
    change_pct = round((last_close - prev_close) / prev_close * 100, 2) if prev_close else 0

    return {
        "ticker": ticker.upper(),
        "name": info.get("name", ticker.upper()),
        "price": round(last_close, 2),
        "change_pct": change_pct,
        "mention_count": 0,
        "mention_velocity": 0.0,
        "avg_sentiment": 0.0,
        "trend_score": 0.0,
        "volume_ratio": indicators.get("volume_ratio", 1.0),
        "indicators": indicators,
        "sources": [],
    }
