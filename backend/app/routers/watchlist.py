from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_db
from app.models.stock import Stock
from app.models.mention import Mention
from app.models.signal import Signal
from app.models.watchlist import Watchlist
from app.services.volume_service import VolumeService
from app.services.price_service import PriceService
from app.services.fundamentals_service import FundamentalsService
from app.services.news_service import NewsService
from app.services.dcf_service import DCFService

router = APIRouter()
volume_service = VolumeService()
price_service = PriceService()
_fundamentals_service = FundamentalsService()
_news_service = NewsService()
_dcf_service = DCFService()

_sync_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
_sync_engine = create_engine(_sync_url, pool_size=2, max_overflow=2)


def _change_pct(stock: Stock) -> float:
    if stock.last_price and stock.prev_close and float(stock.prev_close) > 0:
        return round((float(stock.last_price) - float(stock.prev_close)) / float(stock.prev_close) * 100, 2)
    return 0.0


@router.get("")
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    """Get watchlist with current price, sentiment score, and active signal status."""
    result = await db.execute(
        select(Watchlist, Stock)
        .join(Stock, Watchlist.stock_id == Stock.id)
        .order_by(Watchlist.added_at)
    )
    rows = result.all()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    stocks = []
    for wl, stock in rows:
        mentions_result = await db.execute(
            select(Mention).where(
                and_(Mention.stock_id == stock.id, Mention.created_at >= cutoff)
            )
        )
        mentions = mentions_result.scalars().all()
        scores = [float(m.sentiment_score) for m in mentions if m.sentiment_score is not None]
        sentiment_score = round(sum(scores) / len(scores), 3) if scores else 0.0

        signal_result = await db.execute(
            select(Signal).where(
                and_(
                    Signal.stock_id == stock.id,
                    Signal.expires_at > now,
                    Signal.outcome.is_(None),
                )
            )
        )
        has_active_signal = signal_result.scalar_one_or_none() is not None

        stocks.append({
            "ticker": stock.ticker,
            "name": stock.name or stock.ticker,
            "price": float(stock.last_price) if stock.last_price else 0,
            "change_pct": _change_pct(stock),
            "sentiment_score": sentiment_score,
            "has_active_signal": has_active_signal,
        })

    return {"stocks": stocks}


@router.get("/{ticker}/volume-analysis")
async def get_volume_analysis(
    ticker: str,
    period: str = Query(default="90d", pattern="^(30d|60d|90d|6mo|1y|2y|3y)$"),
):
    ticker = ticker.upper()
    edgar_quarters: list = []
    try:
        with Session(_sync_engine) as session:
            fund = _fundamentals_service.get(ticker, session, allow_fetch=False)
            edgar_quarters = fund.get("edgar_quarters") or []
    except Exception:
        pass
    return volume_service.analyze(ticker, period, edgar_quarters=edgar_quarters)


@router.get("/{ticker}/dcf")
async def get_dcf(ticker: str):
    return _dcf_service.analyze(ticker.upper())


@router.get("/{ticker}/news")
async def get_stock_news(ticker: str, limit: int = Query(default=20, ge=1, le=50)):
    ticker = ticker.upper()
    items = _news_service.get_news(ticker, limit=limit)
    return {"ticker": ticker, "news": items}


@router.post("/{ticker}")
async def add_to_watchlist(ticker: str, db: AsyncSession = Depends(get_db)):
    """Add a stock to the watchlist."""
    ticker = ticker.upper()
    stock_result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = stock_result.scalar_one_or_none()

    if not stock:
        info = price_service.get_stock_info(ticker)
        if not info:
            raise HTTPException(status_code=404, detail=f"{ticker} is not a valid US equity symbol.")
        stock = Stock(ticker=ticker, **info)
        db.add(stock)
        await db.flush()

    existing = await db.execute(select(Watchlist).where(Watchlist.stock_id == stock.id))
    if existing.scalar_one_or_none():
        return {"message": f"{ticker} is already in your watchlist"}

    db.add(Watchlist(stock_id=stock.id))
    await db.commit()
    return {"message": f"{ticker} added to watchlist"}


@router.delete("/{ticker}")
async def remove_from_watchlist(ticker: str, db: AsyncSession = Depends(get_db)):
    """Remove a stock from the watchlist."""
    ticker = ticker.upper()
    stock_result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = stock_result.scalar_one_or_none()

    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    wl_result = await db.execute(select(Watchlist).where(Watchlist.stock_id == stock.id))
    wl = wl_result.scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=404, detail=f"{ticker} is not in your watchlist")

    await db.delete(wl)
    await db.commit()
    return {"message": f"{ticker} removed from watchlist"}
