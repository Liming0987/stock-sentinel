from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.get("")
async def get_trending_stocks(
    limit: int = Query(default=20, le=50),
    timeframe: str = Query(default="24h", regex="^(1h|6h|24h|7d)$"),
    sector: Optional[str] = None,
):
    """Get top trending stocks ranked by composite score."""
    # TODO: Implement with real data from DB
    return {
        "timeframe": timeframe,
        "stocks": [],
        "updated_at": None,
    }


@router.get("/{ticker}")
async def get_trending_detail(ticker: str):
    """Get detailed trending data for a specific stock."""
    # TODO: Implement
    return {
        "ticker": ticker.upper(),
        "mention_count": 0,
        "mention_velocity": 0.0,
        "avg_sentiment": 0.0,
        "trend_score": 0.0,
        "sources": [],
    }
