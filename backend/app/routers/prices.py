from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/{ticker}")
async def get_price_data(
    ticker: str,
    period: str = Query(default="1M", regex="^(1D|5D|1M|3M|6M|1Y|5Y)$"),
    interval: str = Query(default="1d", regex="^(5m|15m|1h|1d|1wk)$"),
):
    """Get OHLCV price data with technical indicators."""
    # TODO: Implement with yfinance
    return {
        "ticker": ticker.upper(),
        "period": period,
        "interval": interval,
        "candles": [],
        "indicators": {
            "rsi": None,
            "macd": None,
            "bollinger": None,
        },
    }
