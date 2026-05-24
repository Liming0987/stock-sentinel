import yfinance as yf
import pandas_ta as ta
import pandas as pd
from typing import Dict, List, Optional


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
        rsi = ta.rsi(df["Close"], length=14)
        if rsi is not None and not rsi.empty:
            indicators["rsi"] = round(rsi.iloc[-1], 2)

        # MACD (12, 26, 9)
        macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
        if macd is not None and not macd.empty:
            indicators["macd"] = round(macd.iloc[-1, 0], 4)
            indicators["macd_signal"] = round(macd.iloc[-1, 1], 4)
            indicators["macd_histogram"] = round(macd.iloc[-1, 2], 4)

        # Bollinger Bands (20, 2)
        bbands = ta.bbands(df["Close"], length=20, std=2)
        if bbands is not None and not bbands.empty:
            indicators["bb_upper"] = round(bbands.iloc[-1, 0], 2)
            indicators["bb_middle"] = round(bbands.iloc[-1, 1], 2)
            indicators["bb_lower"] = round(bbands.iloc[-1, 2], 2)

        # EMAs
        ema_50 = ta.ema(df["Close"], length=50)
        if ema_50 is not None and not ema_50.empty:
            indicators["ema_50"] = round(ema_50.iloc[-1], 2)

        ema_200 = ta.ema(df["Close"], length=200)
        if ema_200 is not None and not ema_200.empty:
            indicators["ema_200"] = round(ema_200.iloc[-1], 2)

        # ATR (14-period)
        atr = ta.atr(df["High"], df["Low"], df["Close"], length=14)
        if atr is not None and not atr.empty:
            indicators["atr"] = round(atr.iloc[-1], 2)

        # Volume analysis
        avg_volume_20 = df["Volume"].tail(20).mean()
        current_volume = df["Volume"].iloc[-1]
        indicators["avg_volume_20d"] = int(avg_volume_20)
        indicators["volume_ratio"] = round(current_volume / avg_volume_20, 2) if avg_volume_20 > 0 else 0

        # Current price
        indicators["last_price"] = round(df["Close"].iloc[-1], 2)

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
