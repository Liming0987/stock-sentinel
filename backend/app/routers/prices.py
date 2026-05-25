from fastapi import APIRouter, Query

from app.services.price_service import PriceService

router = APIRouter()
price_service = PriceService()

PERIOD_MAP = {"1D": "1d", "5D": "5d", "1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y"}


@router.get("/{ticker}")
async def get_price_data(
    ticker: str,
    period: str = Query(default="1M", regex="^(1D|5D|1M|3M|6M|1Y|5Y)$"),
    interval: str = Query(default="1d", regex="^(5m|15m|1h|1d|1wk)$"),
):
    """Get OHLCV price data with technical indicators."""
    yf_period = PERIOD_MAP.get(period, "1mo")
    df = price_service.get_price_data(ticker, period=yf_period, interval=interval)

    if df is None or df.empty:
        return {"ticker": ticker.upper(), "period": period, "interval": interval, "candles": [], "indicators": {}}

    candles = []
    for idx, row in df.iterrows():
        candles.append({
            "date": idx.strftime("%Y-%m-%d") if interval in ("1d", "1wk") else idx.strftime("%Y-%m-%d %H:%M"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })

    indicators = price_service.compute_indicators(df)
    info = price_service.get_stock_info(ticker)

    return {
        "ticker": ticker.upper(),
        "name": info.get("name", ""),
        "sector": info.get("sector", ""),
        "period": period,
        "interval": interval,
        "candles": candles,
        "indicators": indicators,
    }
