# Opening Range Breakout (ORB) Strategy

**File:** `backend/app/strategies/intraday/opening_range_breakout.py`
**Type:** Intraday (5-minute bars)
**Max positions:** 2
**Holds overnight:** No — all positions closed by 3:45 PM ET

## Overview

The first 30 minutes of trading (9:30–10:00 AM) establish a range as buyers and sellers fight to set the day's direction. ORB buys when price breaks decisively above that range's high with heavy volume — betting the morning buyers won the opening battle and the stock will continue higher. Entry window closes at 11:00 AM; the opening momentum thesis doesn't apply to afternoon breaks.

## Opening range

- First 6 five-minute bars (9:30–10:00 AM)
- `ORB_HIGH` = highest high of those 6 bars
- `ORB_LOW` = lowest low of those 6 bars
- Fixed for the rest of the day — does not update

## Entry conditions

**Hard requirements (all must pass):**
- Bars elapsed ≥ 6 (full ORB has formed)
- Bars elapsed ≤ 18 (within 60 min of ORB forming — 10:00–11:00 AM only)
- `current_price > ORB_HIGH` (price above the range)
- Volume ≥ 2× today's per-bar average

**Confidence scoring:**
| Condition | Points |
|-----------|--------|
| Base | 0.60 |
| Volume 2–3× average | +0.10 |
| Volume ≥ 3× average | +0.20 |
| Price > ORB_HIGH × 1.005 (solid break) | +0.10 |
| Daily MACD bullish | +0.10 |

## Exit conditions

- **Stop:** `ORB_HIGH − ORB_RANGE × 0.5` (midpoint of the opening range)
- **Risk** = `entry − stop`
- **Target** = `entry + risk × 2.0` (2:1 R:R)
- **Indicator exit:** `price < ORB_HIGH × 0.998` (fell back into the range — breakout failed)
- **EOD exits:** bar 75 (3:45 PM) or wall-clock 3:45 PM ET — whichever fires first

## Stop design note

Stop is anchored to the ORB midpoint, not ATR. If price falls back to the middle of the opening range, buyers couldn't hold even half the range above the low — the breakout has clearly failed structurally. This makes the stop self-sizing: wider opening ranges produce wider stops, which is appropriate since a wide range reflects more volatile conditions.

## Parameters

| Parameter          | Value  | Rationale |
|--------------------|--------|-----------|
| ORB_BARS           | 6      | 6 × 5 min = 30 min; standard ORB window |
| ENTRY_WINDOW_BARS  | 12     | 12 × 5 min = 60 min after ORB; breakouts after 11 AM don't carry the same morning momentum thesis |
| MIN_VOL_RATIO      | 2.0×   | Higher bar than VWAP Cross (1.5×) — ORB is a one-shot bet on the day's direction, needs stronger conviction |
| STOP_LOSS_ATR_MULT | 1.5×   | Used only for intraday ATR reference; actual stop is the ORB midpoint |

## ORB vs VWAP Cross

| | ORB | VWAP Cross |
|---|---|---|
| Reference level | Fixed at 10:00 AM | Updates every 5 min all day |
| Entry window | 10:00–11:00 AM only | 10:00 AM–3:30 PM |
| Volume threshold | ≥ 2× | ≥ 1.5× |
| Stop anchor | ORB midpoint | VWAP − 0.5×ATR |
| One-shot? | Yes — misses if no 11AM break | No — can cross VWAP multiple times |

## Known limitations

- One-shot per day per ticker — if no breakout by 11 AM, strategy is idle for the rest of the day
- Late breakouts (10:45–11:00 AM) have less morning momentum behind them
- Wide opening ranges (volatile open) produce large stops and far targets — the 2:1 R:R holds but the absolute dollar risk per trade grows
- Same feed mismatch as VWAP Cross: live Alpaca price vs delayed yfinance ORB levels
