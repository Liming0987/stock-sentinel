from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.stock import Stock
from app.models.mention import Mention
from app.models.signal import TrendingSnapshot
from app.services.price_service import PriceService

router = APIRouter()
price_service = PriceService()


def _change_pct(stock: Stock) -> float:
    if stock.last_price and stock.prev_close and float(stock.prev_close) > 0:
        return round((float(stock.last_price) - float(stock.prev_close)) / float(stock.prev_close) * 100, 2)
    return 0.0

# Popular tickers to show when DB has no mention data yet (bootstrap)
BOOTSTRAP_TICKERS = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "AMZN", "META", "GOOG", "PLTR", "SOFI"]


@router.get("")
async def get_trending_stocks(
    limit: int = Query(default=20, le=50),
    timeframe: str = Query(default="24h", regex="^(1h|6h|24h|7d)$"),
    sector: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get top trending stocks ranked by composite score."""
    # Subquery: most recent snapshot timestamp per stock
    latest_subq = (
        select(
            TrendingSnapshot.stock_id,
            func.max(TrendingSnapshot.snapshot_at).label("latest_at"),
        )
        .group_by(TrendingSnapshot.stock_id)
        .subquery()
    )
    result = await db.execute(
        select(TrendingSnapshot)
        .join(
            latest_subq,
            and_(
                TrendingSnapshot.stock_id == latest_subq.c.stock_id,
                TrendingSnapshot.snapshot_at == latest_subq.c.latest_at,
            ),
        )
        .join(Stock, TrendingSnapshot.stock_id == Stock.id)
        .order_by(desc(TrendingSnapshot.trend_score))
        .limit(limit)
    )
    snapshots = result.scalars().all()

    if snapshots:
        stocks = []
        for snap in snapshots:
            stock = await db.get(Stock, snap.stock_id)
            if not stock:
                continue
            stocks.append({
                "ticker": stock.ticker,
                "name": stock.name or stock.ticker,
                "price": float(stock.last_price) if stock.last_price else 0,
                "change_pct": _change_pct(stock),
                "mention_count": snap.mention_count,
                "mention_velocity": float(snap.mention_velocity) if snap.mention_velocity else 0,
                "sentiment_score": float(snap.avg_sentiment) if snap.avg_sentiment else 0,
                "trend_score": float(snap.trend_score) if snap.trend_score else 0,
                "volume_ratio": 1.0,
                "sources": ["reddit"],
            })
        return {"timeframe": timeframe, "stocks": stocks, "updated_at": datetime.now(timezone.utc).isoformat()}

    # Bootstrap: show real price data for popular tickers when no sentiment data exists yet
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
async def get_trending_detail(ticker: str, db: AsyncSession = Depends(get_db)):
    """Get detailed trending data for a specific stock."""
    ticker = ticker.upper()
    df = price_service.get_price_data(ticker, period="1mo", interval="1d")
    info = price_service.get_stock_info(ticker)
    indicators = price_service.compute_indicators(df) if df is not None and len(df) >= 20 else {}

    last_close = float(df["Close"].iloc[-1]) if df is not None and not df.empty else 0
    prev_close = float(df["Close"].iloc[-2]) if df is not None and len(df) >= 2 else last_close
    change_pct = round((last_close - prev_close) / prev_close * 100, 2) if prev_close else 0

    # Fetch stock and real sentiment/mention data from DB
    stock_result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = stock_result.scalar_one_or_none()

    mention_count = 0
    mention_velocity = 0.0
    avg_sentiment = 0.0
    sources = []

    if stock:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        prev_cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

        mentions_result = await db.execute(
            select(Mention).where(
                and_(Mention.stock_id == stock.id, Mention.created_at >= cutoff)
            )
        )
        mentions = mentions_result.scalars().all()

        prev_result = await db.execute(
            select(Mention).where(
                and_(
                    Mention.stock_id == stock.id,
                    Mention.created_at >= prev_cutoff,
                    Mention.created_at < cutoff,
                )
            )
        )
        prev_mentions = prev_result.scalars().all()

        mention_count = len(mentions)
        prev_count = len(prev_mentions)
        mention_velocity = (mention_count - prev_count) / 24.0

        scores = [float(m.sentiment_score) for m in mentions if m.sentiment_score is not None]
        avg_sentiment = round(sum(scores) / len(scores), 3) if scores else 0.0
        sources = list({m.source_type for m in mentions})

    return {
        "ticker": ticker,
        "name": info.get("name", ticker),
        "price": round(last_close, 2),
        "change_pct": change_pct,
        "mention_count": mention_count,
        "mention_velocity": round(mention_velocity, 2),
        "sentiment_score": avg_sentiment,
        "trend_score": 0.0,
        "volume_ratio": indicators.get("volume_ratio", 1.0),
        "indicators": indicators,
        "sources": sources,
    }
