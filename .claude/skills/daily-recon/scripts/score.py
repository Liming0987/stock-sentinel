"""
score.py — 0-100 conviction scoring engine for the Daily Recon skill.

Computes three dimension scores:
  Trend Health       0-30 pts
  Fundamental Quality 0-30 pts
  Timing/Setup       0-40 pts

Usage:
  from score import compute_score, compute_rs_rating, compute_sector_momentum, fetch_earnings_days
"""

import datetime
from typing import Optional

# ── Sector → ETF mapping ───────────────────────────────────────────────────────
SECTOR_ETF = {
    "Technology":             "QQQ",
    "Communication Services": "XLC",
    "Consumer Cyclical":      "XLY",
    "Consumer Defensive":     "XLP",
    "Energy":                 "XLE",
    "Financial Services":     "XLF",
    "Healthcare":             "XLV",
    "Industrials":            "XLI",
    "Basic Materials":        "XLB",
    "Real Estate":            "XLRE",
    "Utilities":              "XLU",
}


# ── RS Rating ─────────────────────────────────────────────────────────────────

def compute_rs_rating(ticker: str, price_df, spy_df) -> int:
    """
    Approximate IBD-style Relative Strength rating (1-99).
    Weighted 12-week return vs SPY: Q1 (most recent) 40%, Q2-Q4 20% each.
    Returns 50 if insufficient data.
    """
    try:
        close = price_df["Close"]
        spy = spy_df["Close"]

        if len(close) < 60 or len(spy) < 60:
            return 50

        # Align on common dates
        import pandas as pd
        merged = pd.DataFrame({"stock": close, "spy": spy}).dropna()
        if len(merged) < 60:
            return 50

        n = len(merged)
        q = n // 4

        def _ret(df, start, end):
            if end <= start or start >= len(df):
                return 0.0
            s = float(df.iloc[start]["stock"])
            e = float(df.iloc[end - 1]["stock"])
            s_spy = float(df.iloc[start]["spy"])
            e_spy = float(df.iloc[end - 1]["spy"])
            stock_ret = (e - s) / s if s > 0 else 0.0
            spy_ret = (e_spy - s_spy) / s_spy if s_spy > 0 else 0.0
            return stock_ret - spy_ret  # excess return vs SPY

        # Most recent quarter has highest weight
        q4_ret = _ret(merged, n - q, n)
        q3_ret = _ret(merged, n - 2 * q, n - q)
        q2_ret = _ret(merged, n - 3 * q, n - 2 * q)
        q1_ret = _ret(merged, n - 4 * q, n - 3 * q)

        weighted = q4_ret * 0.40 + q3_ret * 0.20 + q2_ret * 0.20 + q1_ret * 0.20

        # Map excess return to 1-99:
        # +30%+ excess  → 99
        # -30%+ lagging → 1
        # linear between
        clamped = max(-0.30, min(0.30, weighted))
        rating = int(round(1 + (clamped + 0.30) / 0.60 * 98))
        return max(1, min(99, rating))

    except Exception:
        return 50


# ── Sector momentum ───────────────────────────────────────────────────────────

def compute_sector_momentum(sector: str) -> dict:
    """
    Returns {etf, return_4w_pct, label} for the stock's sector ETF.
    label: "strong" (> +3%), "weak" (< -3%), "neutral" otherwise.
    """
    etf = SECTOR_ETF.get(sector, "SPY")
    try:
        import yfinance as yf
        df = yf.Ticker(etf).history(period="2mo", interval="1d")
        if df is None or len(df) < 20:
            return {"etf": etf, "return_4w_pct": None, "label": "neutral"}
        close = df["Close"].dropna()
        if len(close) < 20:
            return {"etf": etf, "return_4w_pct": None, "label": "neutral"}
        ret = (float(close.iloc[-1]) - float(close.iloc[-20])) / float(close.iloc[-20]) * 100
        ret = round(ret, 1)
        import math
        if math.isnan(ret):
            return {"etf": etf, "return_4w_pct": None, "label": "neutral"}
        label = "strong" if ret > 3 else ("weak" if ret < -3 else "neutral")
        return {"etf": etf, "return_4w_pct": ret, "label": label}
    except Exception:
        return {"etf": etf, "return_4w_pct": None, "label": "neutral"}


# ── Earnings proximity ────────────────────────────────────────────────────────

def fetch_earnings_days(ticker: str, fundamentals: dict = None) -> Optional[int]:
    """
    Returns calendar days until next earnings, or None if unavailable.
    Checks fundamentals["next_earnings"] first (already fetched), then
    falls back to yfinance earningsDate.
    """
    today = datetime.date.today()

    # Prefer next_earnings from fundamentals (already fetched by the skill)
    if fundamentals:
        raw = fundamentals.get("next_earnings")
        if raw:
            try:
                if hasattr(raw, "date"):
                    target = raw.date()
                else:
                    from datetime import datetime as _dt
                    target = _dt.fromisoformat(str(raw).replace("Z", "+00:00")).date()
                diff = (target - today).days
                if diff >= 0:
                    return diff
            except Exception:
                pass

    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        raw = info.get("earningsDate") or info.get("earningsTimestamp")
        if raw is None:
            return None

        if isinstance(raw, (list, tuple)):
            raw = raw[0] if raw else None
        if raw is None:
            return None

        if isinstance(raw, (int, float)):
            target = datetime.date.fromtimestamp(raw)
        elif hasattr(raw, "date"):
            target = raw.date()
        else:
            return None

        diff = (target - today).days
        return diff if diff >= 0 else None

    except Exception:
        return None


def fetch_sector(ticker: str, fundamentals: dict = None) -> str:
    """Returns the stock's sector string, falling back to yfinance if not in fundamentals."""
    if fundamentals:
        sector = (fundamentals.get("metrics") or {}).get("sector")
        if sector:
            return sector
    try:
        import yfinance as yf
        return yf.Ticker(ticker).info.get("sector", "") or ""
    except Exception:
        return ""


# ── Scoring engine ────────────────────────────────────────────────────────────

def compute_score(
    indicators: dict,
    wyckoff: dict,
    vcp: dict,
    fundamentals: dict,
    dcf: dict,
    signals: list,
    rs_rating: int,
    earnings_days: Optional[int],
) -> dict:
    """
    Returns {total, trend_health, fundamental_quality, timing_setup, stance, earnings_flag}.
    """

    # ── Trend Health (0-30) ────────────────────────────────────────────────
    trend = 0

    ema_50 = indicators.get("ema_50")
    ema_200 = indicators.get("ema_200")
    last_price = indicators.get("last_price")

    # EMA stack: price > EMA-50 > EMA-200
    if ema_50 and ema_200 and last_price:
        if last_price > ema_50 > ema_200:
            trend += 10
        elif last_price > ema_200:
            trend += 4

    # EMA-50 slope (use wyckoff bias as proxy when slope not directly available)
    wyckoff_bias = (wyckoff or {}).get("bias", "neutral")
    if wyckoff_bias == "bullish":
        trend += 5
    elif wyckoff_bias == "neutral" and ema_50 and ema_200 and ema_50 > ema_200:
        trend += 2

    # RS Rating
    if rs_rating >= 80:
        trend += 10
    elif rs_rating >= 70:
        trend += 8
    elif rs_rating >= 50:
        trend += 5
    elif rs_rating >= 30:
        trend += 2

    # 52-week high proximity (use VCP stage2 as proxy)
    if (vcp or {}).get("stage2"):
        trend += 5
    elif wyckoff_bias != "bearish":
        trend += 2

    trend = min(30, trend)

    # ── Fundamental Quality (0-30) ────────────────────────────────────────
    fundamental = 0

    grade = (fundamentals or {}).get("grade", "")
    score_val = (fundamentals or {}).get("score", 0) or 0
    flags = (fundamentals or {}).get("flags", [])

    if grade.startswith("A"):
        fundamental += 15
    elif grade.startswith("B"):
        fundamental += 10
    elif grade.startswith("C"):
        fundamental += 5

    dcf_feasible = (dcf or {}).get("feasible", False)
    upside = (dcf or {}).get("upside_pct")
    if dcf_feasible and upside is not None:
        if upside > 25:
            fundamental += 10
        elif upside > 15:
            fundamental += 8
        elif upside > 5:
            fundamental += 5
        elif upside > 0:
            fundamental += 2

    if not flags:
        fundamental += 5

    fundamental = min(30, fundamental)

    # ── Timing/Setup (0-40) ───────────────────────────────────────────────
    timing = 0

    # VCP
    vcp_detected = (vcp or {}).get("detected", False)
    vcp_stage2 = (vcp or {}).get("stage2", False)
    if vcp_detected and vcp_stage2:
        timing += 15
    elif vcp_detected:
        timing += 7

    # Wyckoff bullish signals
    wyckoff_signals = (wyckoff or {}).get("signals", [])
    sos_detected = any(s.get("name") in ("SOS", "LPS") and s.get("detected") for s in wyckoff_signals)
    any_bullish = wyckoff_bias == "bullish"
    if sos_detected:
        timing += 10
    elif any_bullish:
        timing += 5

    # Volume drying up (use VCP volume dry as proxy)
    contractions = (vcp or {}).get("contractions", [])
    vol_dry_count = sum(1 for c in contractions if c.get("vol_dry"))
    if contractions and vol_dry_count >= len(contractions) - 1:
        timing += 5
    elif vol_dry_count > 0:
        timing += 2

    # Strategy signals (today or last 3 days)
    today_str = datetime.date.today().isoformat()
    cutoff = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
    recent_signals = [
        s for s in (signals or [])
        if s.get("action") == "buy" and (s.get("created_at") or "") >= cutoff
    ]
    if any(s.get("created_at", "") >= today_str for s in recent_signals):
        timing += 10
    elif recent_signals:
        timing += 5

    timing = min(40, timing)

    # ── Total & stance ────────────────────────────────────────────────────
    total = trend + fundamental + timing

    if total >= 75:
        stance = "accumulate"
    elif total >= 50:
        stance = "watch"
    elif total >= 35:
        stance = "caution"
    else:
        stance = "avoid"

    # ── Earnings override ─────────────────────────────────────────────────
    earnings_flag = None
    if earnings_days is not None:
        if earnings_days <= 5:
            earnings_flag = "earnings_risk"
            if stance == "accumulate":
                stance = "watch"
        elif earnings_days <= 14:
            earnings_flag = "catalyst_opportunity"

    return {
        "total": total,
        "trend_health": trend,
        "fundamental_quality": fundamental,
        "timing_setup": timing,
        "stance": stance,
        "earnings_flag": earnings_flag,
    }
