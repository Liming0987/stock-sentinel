"""VCP (Volatility Contraction Pattern) detection — Minervini methodology."""
import numpy as np
import pandas as pd
from typing import List, Optional


def _get_date(df: pd.DataFrame, idx: int) -> str:
    row_idx = df.index[idx]
    if hasattr(row_idx, "date"):
        return str(row_idx.date())
    return str(row_idx)[:10]


def _swing_highs(highs: pd.Series, window: int) -> List[int]:
    arr = highs.values
    result = []
    for i in range(window, len(arr) - window):
        if arr[i] == arr[i - window : i + window + 1].max():
            result.append(i)
    return result


def _swing_lows(lows: pd.Series, window: int) -> List[int]:
    arr = lows.values
    result = []
    for i in range(window, len(arr) - window):
        if arr[i] == arr[i - window : i + window + 1].min():
            result.append(i)
    return result


def detect_vcp(df: pd.DataFrame) -> dict:
    """
    Detect Volatility Contraction Pattern in OHLCV DataFrame.

    Criteria (Minervini):
      1. Stage 2 uptrend: price > 50 EMA > 150 EMA > 200 EMA, 200 EMA rising
      2. 2–4 contractions of decreasing depth within the base
      3. Volume drying up at each contraction low
      4. Pivot = high of the tightest (last) contraction

    Returns a dict suitable for JSON serialisation.
    """
    EMPTY: dict = {
        "detected": False,
        "stage2": False,
        "pivot": None,
        "contractions": [],
        "base_start_date": None,
        "status": "not_detected",
        "note": "Insufficient data.",
    }

    if len(df) < 40:
        return EMPTY

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    n = len(df)

    # ── Stage 2 uptrend ──────────────────────────────────────────────────────
    ema_200 = close.ewm(span=min(200, n), adjust=False).mean()
    ema_150 = close.ewm(span=min(150, n), adjust=False).mean()
    ema_50 = close.ewm(span=min(50, n), adjust=False).mean()

    last_close = float(close.iloc[-1])
    e50 = float(ema_50.iloc[-1])
    e150 = float(ema_150.iloc[-1])
    e200 = float(ema_200.iloc[-1])

    slope_bars = min(50, n - 1)
    ema200_rising = float(ema_200.iloc[-1]) > float(ema_200.iloc[-slope_bars])
    near_52w_high = last_close >= float(high.iloc[-min(252, n):].max()) * 0.75

    stage2 = (
        last_close > e50 > e150 > e200
        and ema200_rising
        and near_52w_high
    )

    # ── Swing detection in last ~90 bars (the "base") ────────────────────────
    base_len = min(90, n)
    base_df = df.iloc[-base_len:]
    base_high = base_df["High"]
    base_low = base_df["Low"]
    base_vol = base_df["Volume"]

    avg_vol = base_vol.rolling(30, min_periods=5).mean()
    swing_w = max(3, base_len // 18)  # adaptive ≈5% of base length

    sh_idx = _swing_highs(base_high, swing_w)
    sl_idx = _swing_lows(base_low, swing_w)

    if len(sh_idx) < 2 or len(sl_idx) < 2:
        return {**EMPTY, "stage2": stage2, "note": "Too few swing points in base window."}

    # ── Build (high → next low) contraction candidates ───────────────────────
    candidates = []
    for h_i in sh_idx:
        h_val = float(base_high.iloc[h_i])
        following = [l for l in sl_idx if l > h_i]
        if not following:
            continue
        l_i = following[0]
        l_val = float(base_low.iloc[l_i])
        depth = (h_val - l_val) / h_val * 100
        if depth < 1.5:
            continue
        avg_at_l = float(avg_vol.iloc[l_i]) if not np.isnan(avg_vol.iloc[l_i]) else 1
        vol_dry = float(base_vol.iloc[l_i]) < avg_at_l * 0.85
        candidates.append({
            "high": round(h_val, 2),
            "low": round(l_val, 2),
            "_h_i": h_i,
            "_l_i": l_i,
            "high_date": _get_date(base_df, h_i),
            "low_date": _get_date(base_df, l_i),
            "depth_pct": round(depth, 1),
            "vol_dry": vol_dry,
        })

    candidates.sort(key=lambda x: x["_h_i"])

    # ── Filter: non-overlapping, strictly decreasing depth ───────────────────
    valid = []
    last_end = -1
    for c in candidates:
        if c["_h_i"] <= last_end:
            continue
        if valid and c["depth_pct"] >= valid[-1]["depth_pct"]:
            continue
        valid.append(c)
        last_end = c["_l_i"]

    if len(valid) < 2:
        return {
            **EMPTY,
            "stage2": stage2,
            "note": f"Only {len(valid)} valid contraction(s) — need ≥2 with decreasing depth.",
        }

    valid = valid[-4:]  # keep most recent 4
    contractions = [{k: v for k, v in c.items() if not k.startswith("_")} for c in valid]

    pivot = valid[-1]["high"]
    if last_close > pivot * 1.01:
        status = "breaking_out"
    elif last_close >= pivot * 0.97:
        status = "ready"
    else:
        status = "forming"

    depths = " → ".join(f"{c['depth_pct']:.1f}%" for c in valid)
    vol_dry_n = sum(1 for c in valid if c["vol_dry"])
    note = (
        f"{len(valid)} contractions: {depths}. "
        f"Volume drying in {vol_dry_n}/{len(valid)} pullbacks. "
        f"Pivot ${pivot:.2f}."
    )
    if not stage2:
        note = "Stage 2 conditions not fully met. " + note

    return {
        "detected": True,
        "stage2": stage2,
        "pivot": round(pivot, 2),
        "contractions": contractions,
        "base_start_date": valid[0]["high_date"],
        "status": status,
        "note": note,
    }
