"""Dynamic universe builder for strategy evaluation.

Combines three candidate pools — S&P 100, watchlist, and trending stocks from
the sentiment DB — then scores every candidate on technical criteria and returns
the top N so all sources compete on equal footing.

Technical score (0–1):
  RSI fit     30%  — peak at RSI=55, drops toward extremes
  Volume      25%  — log-scaled volume ratio vs 20-day avg
  Trend       25%  — price above 50-day EMA
  Momentum    20%  — 5-day price return, normalised to 5% = full score

Liquidity gate (applied before scoring):
  avg daily volume >= 500,000
  last price >= $5
"""
import logging
import math
from typing import List, Optional

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

logger = logging.getLogger(__name__)

# S&P 100 components — broad, liquid universe to screen from
SP100 = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOG", "META", "TSLA", "UNH", "XOM",
    "JPM", "V",    "LLY",  "JNJ",  "AVGO", "MA",   "PG",   "HD",  "COST",
    "MRK",  "ABBV","CVX",  "CRM",  "NFLX", "BAC",  "PEP",  "ORCL","TMO",
    "KO",   "WMT", "CSCO", "ACN",  "ABT",  "MCD",  "DHR",  "ADBE","LIN",
    "TXN",  "NKE", "QCOM", "CAT",  "INTU", "VZ",   "UNP",  "CMCSA","GE",
    "IBM",  "AXP", "AMGN", "NEE",  "DIS",  "PM",   "HON",  "LOW", "MDT",
    "BMY",  "SBUX","RTX",  "GS",   "C",    "BLK",  "DE",   "BKNG","MMC",
    "GILD", "SYK", "MO",   "CVS",  "CI",   "TJX",  "ADI",  "ISRG","MS",
    "SO",   "DUK", "ADP",  "CB",   "REGN", "ETN",  "BSX",  "VRTX","PNC",
    "ITW",  "EMR", "TGT",  "WFC",  "ZTS",  "HCA",  "F",    "GM",  "USB",
    "OXY",  "FDX", "AMD",  "PLTR", "SOFI", "PYPL", "SNAP", "UBER","LYFT",
    "ABNB", "SHOP",
]

LIQUIDITY_MIN_VOLUME = 500_000
LIQUIDITY_MIN_PRICE  = 5.0


class UniverseBuilder:

    def build(
        self,
        session: Session,
        target: int = 20,
    ) -> List[str]:
        """Return up to `target` tickers, all competing on equal technical criteria."""
        pool = self._assemble_pool(session)
        logger.info(f"UniverseBuilder: scoring {len(pool)} candidates")

        scores = self._score_all(pool)
        if not scores:
            logger.warning("UniverseBuilder: no candidates passed scoring — falling back to SP100 head")
            return SP100[:target]

        scores.sort(key=lambda x: x[1], reverse=True)
        selected = [ticker for ticker, _ in scores[:target]]
        logger.info(f"UniverseBuilder: selected {selected}")
        return selected

    # ── Pool assembly ───────────────────────────────────────────────────────

    def _assemble_pool(self, session: Session) -> List[str]:
        pool = set(SP100)

        # Watchlist
        try:
            from app.models.stock import Stock
            from app.models.watchlist import Watchlist
            rows = session.execute(
                select(Stock.ticker).join(Watchlist, Watchlist.stock_id == Stock.id)
            ).scalars().all()
            pool.update(rows)
        except Exception as e:
            logger.warning(f"UniverseBuilder: could not load watchlist: {e}")

        # Top trending from sentiment DB (last snapshot)
        try:
            from app.models.stock import Stock as StockModel
            from app.models.signal import TrendingSnapshot
            rows = session.execute(
                select(StockModel.ticker)
                .join(TrendingSnapshot, TrendingSnapshot.stock_id == StockModel.id)
                .order_by(desc(TrendingSnapshot.trend_score))
                .limit(20)
            ).scalars().all()
            pool.update(rows)
        except Exception as e:
            logger.warning(f"UniverseBuilder: could not load trending: {e}")

        return list(pool)

    # ── Scoring ─────────────────────────────────────────────────────────────

    def _score_all(self, tickers: List[str]) -> List[tuple]:
        """Batch-download 3-month OHLCV for all tickers, score each."""
        try:
            raw = yf.download(
                tickers,
                period="3mo",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
        except Exception as e:
            logger.error(f"UniverseBuilder: yfinance batch download failed: {e}")
            return []

        # yfinance returns flat columns for a single ticker, MultiIndex for many
        multi = isinstance(raw.columns, pd.MultiIndex)

        results = []
        for ticker in tickers:
            try:
                df = self._extract(raw, ticker, multi)
                score = self._score_ticker(ticker, df)
                if score is not None:
                    results.append((ticker, score))
            except Exception as e:
                logger.debug(f"UniverseBuilder: skipping {ticker}: {e}")

        return results

    def _extract(self, raw: pd.DataFrame, ticker: str, multi: bool) -> pd.DataFrame:
        if multi:
            df = raw.xs(ticker, axis=1, level=1).dropna(how="all")
        else:
            df = raw.dropna(how="all")
        if df.empty or len(df) < 20:
            raise ValueError("insufficient data")
        return df

    def _score_ticker(self, ticker: str, df: pd.DataFrame) -> Optional[float]:
        close = df["Close"]
        volume = df["Volume"]

        last_price = float(close.iloc[-1])
        avg_vol = float(volume.tail(20).mean())

        # Liquidity gate
        if avg_vol < LIQUIDITY_MIN_VOLUME or last_price < LIQUIDITY_MIN_PRICE:
            return None

        # RSI (14-period EWM)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / 14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1 / 14, min_periods=14).mean()
        rs = avg_gain / avg_loss
        rsi = float((100 - 100 / (1 + rs)).iloc[-1])

        # EMA 50
        ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])

        # Volume ratio vs 20-day avg
        vol_ratio = float(volume.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0

        # 5-day momentum
        mom = (last_price - float(close.iloc[-5])) / float(close.iloc[-5]) if len(df) >= 5 else 0.0

        # ── Component scores ─────────────────────────────────
        # RSI: peak at 55, linear drop to 0 at extremes (25 and 85)
        rsi_score = max(0.0, 1.0 - abs(rsi - 55) / 30.0)

        # Volume: log-scale surplus above 1× avg
        vol_score = min(math.log1p(max(vol_ratio - 1.0, 0.0)), 1.0)

        # Trend: binary — price above 50-day EMA
        trend_score = 1.0 if last_price > ema50 else 0.0

        # Momentum: 5% move = full score; negative momentum → 0
        mom_score = max(0.0, min(mom / 0.05, 1.0))

        composite = (
            0.30 * rsi_score
            + 0.25 * vol_score
            + 0.25 * trend_score
            + 0.20 * mom_score
        )
        return round(composite, 4)
