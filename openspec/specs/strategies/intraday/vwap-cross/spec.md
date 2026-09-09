# VWAP Cross Strategy

**File:** `backend/app/strategies/intraday/vwap_cross.py`
**Type:** Intraday (5-minute bars)
**Max positions:** 2
**Holds overnight:** No — all positions closed by 3:45 PM ET

## Overview

Buys when price crosses above VWAP (Volume Weighted Average Price) with a volume surge. VWAP is the market's "fair price" for the day — professional traders use it as their benchmark. When price crosses above it with conviction, buyers have taken control of the day. The strategy bets the move continues.

VWAP resets to zero at 9:30 AM every morning. Everything in this strategy is intraday-only.

## Entry conditions

**Hard requirements (all must pass):**
- Between bar 6 (10:00 AM) and bar 72 (3:30 PM) — VWAP needs 30 min to build meaningful history
- Previous bar closed below its own VWAP; current price is at or above today's VWAP (true crossover)
- Volume ≥ 1.5× today's per-bar average (excluding the current bar and the high-volume open)

**Confidence scoring:**
| Condition | Points |
|-----------|--------|
| Base | 0.50 |
| Volume 1.5–2× average | +0.10 |
| Volume ≥ 2× average | +0.20 |
| Daily price above EMA-50 | +0.20 |
| Daily MACD bullish | +0.10 |

## Exit conditions

- **Stop:** `VWAP − 0.5 × intraday_ATR`
- **Target:** `entry + 2 × (entry − stop)` (2:1 R:R)
- **Indicator exit:** last completed bar close < VWAP × 0.999 (fell back below VWAP)
- **EOD exits:** bar 75 (3:45 PM) or wall-clock 3:45 PM ET — whichever fires first

## Implementation notes (Sep 2026 fixes)

Several correctness issues were fixed:

1. **VWAP daily reset**: `compute_intraday_indicators` now filters the yfinance frame to today's ET date before computing VWAP. yfinance's `period="1d"` can return prior-session bars; without filtering, VWAP ran across the day boundary silently.

2. **Crossover detection**: uses per-bar VWAP (`prev_bar_vwap`) rather than comparing the prior bar's close to the current bar's cumulative VWAP. Avoids apples-to-oranges comparison when VWAP shifts on high-volume bars.

3. **Volume ratio denominator**: changed from `df["Volume"].mean()` (all bars including current) to `df["Volume"].iloc[:-1].mean()` (prior bars only). The opening bar's high volume was inflating the average and understating mid-session surges.

4. **EOD bar-count exit**: fixed from bar 78 (4:00 PM) to bar 75 (3:45 PM) — consistent with ORB and the wall-clock cutoff.

5. **Exit feed mismatch**: `should_close` now uses the last completed bar close (not the live Alpaca quote) for the below-VWAP check, preventing whipsaws from quote spikes against a delayed VWAP level.

## Known limitations

- Celery polls every 5 minutes — a VWAP cross that happens mid-bar may be 0–5 minutes stale by the time the strategy runs
- `current_price` is a live Alpaca quote; VWAP and volume are from the last completed yfinance bar — these feeds can disagree
- The 3:45 PM EOD exit is best-effort: relies on a Celery beat tick landing in the 15-minute window before market close
