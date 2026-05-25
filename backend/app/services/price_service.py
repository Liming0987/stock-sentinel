import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional


def _rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Compute RSI using pure pandas."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / length, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _ema(series: pd.Series, length: int) -> pd.Series:
    """Compute EMA using pure pandas."""
    return series.ewm(span=length, adjust=False).mean()


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Compute MACD, signal, and histogram."""
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "histogram": histogram})


def _bbands(series: pd.Series, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    """Compute Bollinger Bands."""
    middle = series.rolling(window=length).mean()
    rolling_std = series.rolling(window=length).std()
    upper = middle + std * rolling_std
    lower = middle - std * rolling_std
    return pd.DataFrame({"upper": upper, "middle": middle, "lower": lower})


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Compute Average True Range."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=length).mean()


class PriceService:
    """Fetch and compute price data + technical indicators."""

    def get_price_data(
        self, ticker: str, period: str = "1mo", interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Yahoo Finance."""
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            if df.empty:
                return None
            return df
        except Exception as e:
            print(f"Error fetching price data for {ticker}: {e}")
            return None

    def compute_indicators(self, df: pd.DataFrame) -> Dict:
        """Compute technical indicators for a price DataFrame."""
        if df is None or len(df) < 20:
            return {}

        indicators = {}

        # RSI (14-period)
        rsi = _rsi(df["Close"], length=14)
        if rsi is not None and not rsi.empty:
            indicators["rsi"] = round(float(rsi.iloc[-1]), 2)

        # MACD (12, 26, 9)
        macd = _macd(df["Close"], fast=12, slow=26, signal=9)
        if macd is not None and not macd.empty:
            indicators["macd"] = round(float(macd["macd"].iloc[-1]), 4)
            indicators["macd_signal"] = round(float(macd["signal"].iloc[-1]), 4)
            indicators["macd_histogram"] = round(float(macd["histogram"].iloc[-1]), 4)

        # Bollinger Bands (20, 2)
        bbands = _bbands(df["Close"], length=20, std=2)
        if bbands is not None and not bbands.empty:
            indicators["bb_upper"] = round(float(bbands["upper"].iloc[-1]), 2)
            indicators["bb_middle"] = round(float(bbands["middle"].iloc[-1]), 2)
            indicators["bb_lower"] = round(float(bbands["lower"].iloc[-1]), 2)

        # EMAs
        ema_50 = _ema(df["Close"], length=50)
        if ema_50 is not None and not ema_50.empty:
            indicators["ema_50"] = round(float(ema_50.iloc[-1]), 2)

        ema_200 = _ema(df["Close"], length=200)
        if ema_200 is not None and not ema_200.empty:
            indicators["ema_200"] = round(float(ema_200.iloc[-1]), 2)

        # ATR (14-period)
        atr = _atr(df["High"], df["Low"], df["Close"], length=14)
        if atr is not None and not atr.empty:
            indicators["atr"] = round(float(atr.iloc[-1]), 2)

        # Volume analysis
        avg_volume_20 = df["Volume"].tail(20).mean()
        current_volume = df["Volume"].iloc[-1]
        indicators["avg_volume_20d"] = int(avg_volume_20)
        indicators["volume_ratio"] = round(float(current_volume / avg_volume_20), 2) if avg_volume_20 > 0 else 0

        # Current price
        indicators["last_price"] = round(float(df["Close"].iloc[-1]), 2)

        return indicators

    def get_stock_info(self, ticker: str) -> Dict:
        """Get basic stock info (name, sector, market cap)."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                "name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "market_cap": info.get("marketCap", 0),
                "avg_volume": info.get("averageVolume", 0),
            }
        except Exception as e:
            print(f"Error fetching info for {ticker}: {e}")
            return {}

    def update_all(self) -> int:
        """Update prices for all tracked stocks. Returns count updated."""
        # TODO: Query DB for tracked stocks, update each
        return 0

    def is_oversold(self, indicators: Dict) -> bool:
        """Check if a stock is technically oversold."""
        rsi = indicators.get("rsi")
        last_price = indicators.get("last_price")
        bb_lower = indicators.get("bb_lower")

        if rsi and rsi < 30:
            return True
        if last_price and bb_lower and last_price < bb_lower:
            return True
        return False

    def has_volume_confirmation(self, indicators: Dict) -> bool:
        """Check if volume confirms a potential move."""
        volume_ratio = indicators.get("volume_ratio", 0)
        return volume_ratio >= 1.5
