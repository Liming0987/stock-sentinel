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

    # yfinance exchange codes for US-listed securities
    _US_EXCHANGES = {
        "NMS", "NGM", "NCM",  # NASDAQ tiers
        "NYQ",                 # NYSE
        "ASE",                 # NYSE American (AMEX)
        "BTS", "PCX",          # CBOE / NYSE Arca
        "PNK", "OBB",          # OTC markets
    }

    def get_stock_info(self, ticker: str) -> Dict:
        """Get basic stock info. Returns {} for non-US, non-equity, or unresolvable symbols."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Reject non-USD securities (filters out UK, EU, etc. listings)
            if info.get("currency") != "USD":
                return {}

            # Accept only equities and ETFs; reject indices, FX, crypto, etc.
            if info.get("quoteType") not in ("EQUITY", "ETF"):
                return {}

            # Require a recognisable name — catches symbols yfinance "finds" but has no data for
            name = info.get("longName") or info.get("shortName") or ""
            if not name:
                return {}

            # Reject delisted / non-traded securities (zero average volume)
            if not info.get("averageVolume", 0):
                return {}

            return {
                "name": name,
                "sector": info.get("sector", ""),
                "market_cap": info.get("marketCap", 0),
                "avg_volume": info.get("averageVolume", 0),
            }
        except Exception as e:
            print(f"Error fetching info for {ticker}: {e}")
            return {}

    def get_short_interest(self, ticker: str) -> Dict:
        """
        Return short interest metrics + size qualification for a ticker.

        Qualification rules (show = True when any is met):
          - market_cap < $2B           (small-cap or below)
          - float_shares < 50M         (tight float)
          - pct_float_shorted >= 10%   (high short interest — squeeze risk regardless of size)

        squeeze_candidate = small_cap AND tight_float.
        """
        _EMPTY = {
            "show": False,
            "market_cap": None,
            "market_cap_category": None,
            "float_shares": None,
            "shares_outstanding": None,
            "pct_float_shorted": None,
            "days_to_cover": None,
            "tight_float": False,
            "small_cap": False,
            "squeeze_candidate": False,
            "note": None,
        }
        try:
            info = yf.Ticker(ticker).info
            market_cap = info.get("marketCap")
            float_shares = info.get("floatShares")
            shares_out = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
            pct_shorted = info.get("shortPercentOfFloat")
            days_to_cover = info.get("shortRatio")

            def _cap_label(mc):
                if mc is None: return None
                if mc >= 200e9: return "Mega-cap"
                if mc >= 10e9:  return "Large-cap"
                if mc >= 2e9:   return "Mid-cap"
                if mc >= 300e6: return "Small-cap"
                if mc >= 50e6:  return "Micro-cap"
                return "Nano-cap"

            small_cap = bool(market_cap and market_cap < 2e9)
            tight_float = bool(float_shares and float_shares < 50e6)
            high_short = bool(pct_shorted and pct_shorted >= 0.10)
            show = small_cap or tight_float or high_short
            squeeze = small_cap and tight_float

            if squeeze:
                note = "Small-cap + tight float — short squeeze dynamics can be violent"
            elif tight_float:
                note = "Tight float (<50M shares) — squeeze-susceptible despite larger market cap"
            elif small_cap and high_short:
                note = f"Small-cap with {pct_shorted*100:.1f}% float shorted — elevated squeeze risk"
            elif high_short:
                note = f"{pct_shorted*100:.1f}% of float is short — significant short interest"
            elif small_cap:
                note = "Small-cap — elevated volatility on volume spikes"
            else:
                note = None

            return {
                "show": show,
                "market_cap": market_cap,
                "market_cap_category": _cap_label(market_cap),
                "float_shares": float_shares,
                "shares_outstanding": shares_out,
                "pct_float_shorted": pct_shorted,
                "days_to_cover": days_to_cover,
                "tight_float": tight_float,
                "small_cap": small_cap,
                "squeeze_candidate": squeeze,
                "note": note,
            }
        except Exception:
            return _EMPTY

    def update_all(self) -> int:
        """Fetch latest prices for every Stock row and update last_price + updated_at.

        Returns the number of stocks successfully updated.
        Bootstraps a default universe if the table is empty.
        """
        from decimal import Decimal
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from app.config import settings
        from app.models.stock import Stock

        BOOTSTRAP_TICKERS = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "META", "GOOG", "AMZN", "PLTR", "SOFI"]

        sync_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
        engine = create_engine(sync_url)
        updated = 0

        with Session(engine) as session:
            stocks = session.execute(select(Stock)).scalars().all()

            # Bootstrap if empty
            if not stocks:
                for ticker in BOOTSTRAP_TICKERS:
                    info = self.get_stock_info(ticker)
                    if not info.get("name"):
                        continue
                    session.add(Stock(
                        ticker=ticker,
                        name=info.get("name", ticker),
                        sector=info.get("sector"),
                        market_cap=info.get("market_cap"),
                        avg_volume=info.get("avg_volume"),
                    ))
                session.commit()
                stocks = session.execute(select(Stock)).scalars().all()

            for stock in stocks:
                try:
                    df = self.get_price_data(stock.ticker, period="5d", interval="1d")
                    if df is None or df.empty:
                        continue
                    last_price = float(df["Close"].iloc[-1])
                    prev_price = float(df["Close"].iloc[-2]) if len(df) >= 2 else last_price
                    stock.prev_close = Decimal(str(round(prev_price, 2)))
                    stock.last_price = Decimal(str(round(last_price, 2)))
                    session.add(stock)
                    updated += 1
                except Exception as e:
                    print(f"update_all: error for {stock.ticker}: {e}")

            session.commit()

        engine.dispose()
        return updated

    def compute_intraday_indicators(self, df: pd.DataFrame) -> Dict:
        """Compute intraday indicators from a 5-min bar DataFrame (period='1d', interval='5m')."""
        if df is None or df.empty:
            return {}

        result: Dict = {}

        # VWAP from all bars since open
        typical = (df["High"] + df["Low"] + df["Close"]) / 3
        cum_vol = df["Volume"].cumsum()
        cum_tp_vol = (typical * df["Volume"]).cumsum()
        vwap_series = cum_tp_vol / cum_vol.replace(0, float("nan"))
        result["vwap"] = round(float(vwap_series.iloc[-1]), 4) if not vwap_series.empty else None

        # Opening Range: first 6 bars = 30 min
        orb_bars = 6
        orb_slice = df.iloc[:orb_bars] if len(df) >= orb_bars else df
        result["orb_high"] = round(float(orb_slice["High"].max()), 4)
        result["orb_low"] = round(float(orb_slice["Low"].min()), 4)

        # Current and previous bar closes
        result["current_price"] = round(float(df["Close"].iloc[-1]), 4)
        result["prev_bar_close"] = round(float(df["Close"].iloc[-2]), 4) if len(df) >= 2 else None
        result["open_price"] = round(float(df["Open"].iloc[0]), 4)
        result["bars_elapsed"] = len(df)

        # Intraday volume ratio: current bar vs avg bar
        avg_bar_vol = df["Volume"].mean()
        cur_bar_vol = df["Volume"].iloc[-1]
        result["intraday_volume_ratio"] = round(float(cur_bar_vol / avg_bar_vol), 2) if avg_bar_vol > 0 else 0.0

        # Intraday ATR (5-min, last 14 bars if available)
        atr_series = _atr(df["High"], df["Low"], df["Close"], length=min(14, len(df) - 1))
        if not atr_series.empty and not pd.isna(atr_series.iloc[-1]):
            result["intraday_atr"] = round(float(atr_series.iloc[-1]), 4)
        else:
            # Fallback: use half the daily range as a rough intraday ATR proxy
            result["intraday_atr"] = round(float((df["High"] - df["Low"]).mean()), 4)

        return result

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
