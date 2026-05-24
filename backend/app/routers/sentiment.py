from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/{ticker}")
async def get_sentiment(
    ticker: str,
    period: str = Query(default="7d", regex="^(24h|7d|30d|90d)$"),
):
    """Get current and historical sentiment for a ticker."""
    # TODO: Implement
    return {
        "ticker": ticker.upper(),
        "current_score": 0.0,
        "period": period,
        "history": [],
    }


@router.get("/{ticker}/posts")
async def get_sentiment_posts(
    ticker: str,
    limit: int = Query(default=20, le=100),
    source: str = Query(default="all", regex="^(all|reddit|stocktwits|news)$"),
):
    """Get recent posts/comments mentioning this ticker with sentiment scores."""
    # TODO: Implement
    return {
        "ticker": ticker.upper(),
        "posts": [],
    }
