"""VCP (Volatility Contraction Pattern) detection — Minervini methodology."""
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any


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
    base_len = min(150, n)
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

    # Each contraction (high → low span) must fit within 50 bars (~10 weeks).
    # The recovery rally between contractions must not exceed 30 bars (~6 weeks)
    # — enforcing that C1, C2, C3 are genuinely consecutive.
    MAX_CONTRACTION_BARS = 50
    MAX_GAP_BARS = 30

    # ── Build (high → next low) contraction candidates ───────────────────────
    candidates = []
    for h_i in sh_idx:
        h_val = float(base_high.iloc[h_i])
        following = [l for l in sl_idx if l > h_i]
        if not following:
            continue
        l_i = following[0]
        if l_i - h_i > MAX_CONTRACTION_BARS:
            continue
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

    # ── Filter: non-overlapping, consecutive, strictly decreasing depth ───────
    valid = []
    last_end = -1
    for c in candidates:
        if c["_h_i"] <= last_end:
            continue
        # Gap from previous low to this high must be within MAX_GAP_BARS.
        # A larger gap means the recovery took too long — the contractions
        # are not truly consecutive and the chain resets here.
        if valid and c["_h_i"] - valid[-1]["_l_i"] > MAX_GAP_BARS:
            continue
        if valid and c["depth_pct"] >= valid[-1]["depth_pct"]:
            continue
        if valid and c["high"] > valid[-1]["high"]:
            continue  # each contraction must start from a lower high (lower-highs pattern)
        if valid and c["low"] < valid[-1]["low"]:
            continue  # each contraction low must be higher than the previous (higher-lows = tightening range)
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


def detect_vcp_history(df: pd.DataFrame, step: int = 10) -> List[Dict[str, Any]]:
    """
    Slide a detection window across the full price history and collect each
    distinct VCP setup that was visible at the time.

    step=10 means we check every 10 bars (~2 weeks on daily data).
    Stops 20 bars from the end so the current VCP (rendered separately)
    is not duplicated.

    Returns up to 5 most-recent historical setups, oldest-first, each with:
        detection_date, pivot, base_start_date, contractions,
        broke_out (bool), breakout_date (str|None)
    """
    n = len(df)
    results: List[Dict[str, Any]] = []
    seen_base_starts: set = set()

    # Leave last 20 bars as the "current" window handled by detect_vcp()
    for end in range(50, max(50, n - 20), step):
        window = df.iloc[:end]
        vcp = detect_vcp(window)
        if not vcp["detected"] or vcp["pivot"] is None:
            continue

        base_start = vcp["base_start_date"]
        if base_start in seen_base_starts:
            continue
        seen_base_starts.add(base_start)

        pivot = float(vcp["pivot"])

        # Did price close above pivot (+1%) after this detection point?
        future = df.iloc[end:]
        broke_out = False
        breakout_date: Optional[str] = None
        if len(future) > 0:
            above = future["Close"] > pivot * 1.01
            if above.any():
                idx = future.index[int(above.values.argmax())]
                broke_out = True
                breakout_date = (
                    str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]
                )

        results.append({
            "detection_date": _get_date(df, end - 1),
            "pivot": pivot,
            "base_start_date": base_start,
            "contractions": vcp["contractions"],
            "broke_out": broke_out,
            "breakout_date": breakout_date,
        })

    # Keep the 5 most recent, sorted oldest-first for rendering order
    results.sort(key=lambda x: x["detection_date"])
    return results[-5:]
