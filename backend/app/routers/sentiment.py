from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.stock import Stock
from app.models.mention import Mention, RedditPost, StocktwitsMessage

router = APIRouter()


@router.get("/market")
async def get_market_sentiment(
    period: str = Query(default="7d", regex="^(24h|7d|30d)$"),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate sentiment across all tracked stocks for the market overview chart."""
    period_map = {"24h": 1, "7d": 7, "30d": 30}
    days = period_map.get(period, 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(Mention).where(Mention.created_at >= cutoff).order_by(Mention.created_at)
    )
    all_mentions = result.scalars().all()

    history = []
    for d in range(days):
        day = datetime.now(timezone.utc) - timedelta(days=days - 1 - d)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_mentions = [m for m in all_mentions if m.created_at and day_start <= m.created_at < day_end]
        day_scores = [float(m.sentiment_score) for m in day_mentions if m.sentiment_score is not None]
        history.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "sentiment": round(sum(day_scores) / len(day_scores), 3) if day_scores else 0.0,
            "mentions": len(day_mentions),
        })

    return {"period": period, "history": history}


@router.get("/{ticker}")
async def get_sentiment(
    ticker: str,
    period: str = Query(default="7d", regex="^(24h|7d|30d|90d)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get current and historical sentiment for a ticker."""
    period_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = period_map.get(period, 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stock_result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = stock_result.scalar_one_or_none()

    if not stock:
        return {"ticker": ticker.upper(), "current_score": 0.0, "period": period, "history": []}

    result = await db.execute(
        select(Mention)
        .where(Mention.stock_id == stock.id, Mention.created_at >= cutoff)
        .order_by(desc(Mention.created_at))
    )
    mentions = result.scalars().all()

    current_score = 0.0
    if mentions:
        scores = [float(m.sentiment_score) for m in mentions if m.sentiment_score is not None]
        current_score = round(sum(scores) / len(scores), 3) if scores else 0.0

    # Build daily history
    history = []
    for d in range(days):
        day = datetime.now(timezone.utc) - timedelta(days=days - 1 - d)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_mentions = [m for m in mentions if m.created_at and day_start <= m.created_at < day_end]
        day_scores = [float(m.sentiment_score) for m in day_mentions if m.sentiment_score is not None]
        history.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "sentiment": round(sum(day_scores) / len(day_scores), 3) if day_scores else 0.0,
            "mentions": len(day_mentions),
        })

    return {
        "ticker": ticker.upper(),
        "current_score": current_score,
        "period": period,
        "history": history,
    }


@router.get("/{ticker}/posts")
async def get_sentiment_posts(
    ticker: str,
    limit: int = Query(default=20, le=100),
    source: str = Query(default="all", regex="^(all|reddit|stocktwits|news)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get recent posts/comments mentioning this ticker with sentiment scores."""
    stock_result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = stock_result.scalar_one_or_none()

    if not stock:
        return {"ticker": ticker.upper(), "posts": []}

    query = (
        select(Mention, RedditPost, StocktwitsMessage)
        .outerjoin(RedditPost, (Mention.source_type == "reddit") & (Mention.source_id == RedditPost.id))
        .outerjoin(StocktwitsMessage, (Mention.source_type == "stocktwits") & (Mention.source_id == StocktwitsMessage.id))
        .where(Mention.stock_id == stock.id)
        .order_by(desc(Mention.created_at))
        .limit(limit)
    )

    if source != "all":
        query = query.where(Mention.source_type == source)

    result = await db.execute(query)
    rows = result.all()

    posts = []
    for mention, reddit_post, st_msg in rows:
        if mention.source_type == "reddit" and reddit_post:
            posts.append({
                "id": mention.id,
                "source": "reddit",
                "subreddit": reddit_post.subreddit,
                "title": reddit_post.title or "",
                "body": (reddit_post.body or "")[:300],
                "author": reddit_post.author or "",
                "score": reddit_post.score or 0,
                "sentiment_score": float(mention.sentiment_score) if mention.sentiment_score else 0,
                "created_at": mention.created_at.isoformat() if mention.created_at else "",
                "url": reddit_post.url or "",
            })
        elif mention.source_type == "stocktwits" and st_msg:
            posts.append({
                "id": mention.id,
                "source": "stocktwits",
                "subreddit": None,
                "title": "",
                "body": st_msg.body or "",
                "author": st_msg.author or "",
                "score": st_msg.likes or 0,
                "sentiment_score": float(mention.sentiment_score) if mention.sentiment_score else 0,
                "created_at": mention.created_at.isoformat() if mention.created_at else "",
                "url": "",
            })

    return {"ticker": ticker.upper(), "posts": posts}


@router.post("/scrape")
async def trigger_scrape():
    """Manually trigger Reddit scrape + sentiment analysis (runs synchronously)."""
    import asyncio
    from app.workers.tasks import scrape_reddit

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, scrape_reddit)
    return result
