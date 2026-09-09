# Momentum Strategy

**File:** `backend/app/strategies/swing/momentum.py`
**Type:** Swing (daily bars)
**Max positions:** 3

## Overview

Trend-following strategy that only buys stocks already in a confirmed uptrend with active bullish momentum. Unlike the other strategies which try to catch turning points, Momentum enters late — after the trend is established — and rides it as long as MACD stays bullish. The philosophy: strong stocks tend to keep going strong.

## Entry conditions

**Hard requirements (all must pass):**
- EMA-50 is rising: today > 5 days ago > 10 days ago (slope check, not just level)
- Price ≥ 1.5% above EMA-50 (not just barely above — meaningful lead required)
- EMA-50 > EMA-200 (medium-term stronger than long-term)
- MACD line above signal line for 2 consecutive bars (filters one-day false crossovers)
- MACD line itself > 0 (short-term momentum genuinely stronger than long-term)

**Confidence:**
- Volume < 1.3× average → 0.75
- Volume ≥ 1.3× average → 0.90 (only booster; volume is not a gate)

## Exit conditions

- **Stop:** `entry − 2 × ATR`
- **Target:** `entry + 6 × ATR`
- **Indicator exit:** MACD < signal line AND MACD < 0 (both required — same strictness as entry)

## Parameters

| Parameter       | Value  | Rationale |
|-----------------|--------|-----------|
| STOP_LOSS_ATR   | 2.0×   | Tightened from 2.5× — one winner had a −39.6% drawdown before recovering |
| TARGET_ATR      | 6.0×   | Raised from 5.0× — avg winner only reached 5.68%; was leaving gains on the table |
| MIN_VOL_RATIO   | 1.3    | Raised from 1.2× — weak-volume entries were false starts |
| MIN_TREND_GAP   | 1.5%   | Price must be ≥1.5% above EMA-50; sitting right at the average is ambiguous |
| EMA_SLOPE_BARS  | 10     | Two-interval check (today > 5d ago > 10d ago) confirms sustained direction without requiring monotonic movement every bar |

## Backtest findings (Jun 2026)

- **EMA-50 slope guard** was added to avoid late-trend entries. A stock can have EMA-50 > EMA-200 but still be rolling over; the slope check catches this.
- **MIN_TREND_GAP 1.5%** filters noise at the EMA-50 boundary — stocks hovering right at the average can go either way.
- **EMA-200 made mandatory** (was optional). Entering below EMA-200 caused the bulk of losses.
- **Two-bar MACD confirmation** prevents acting on single-day crossover noise.
- **STOP tightened 2.5→2.0**: −39.6% drawdown on one winner was unacceptable even though the trade eventually recovered.
- **TARGET raised 5→6**: only 7.7% of exits were hitting the old target; winners routinely ran further.

## Rejected alternatives

- **Volume as a hard gate**: rejected — good trend entries occasionally happen on moderate volume; volume is a quality signal, not a precondition
- **Single-bar MACD confirmation**: too many false crossovers in choppy conditions
- **STOP at 2.5×ATR**: one trade hit −39.6% drawdown; the risk wasn't justified

## Known limitations

- Enters late in the trend — less upside remaining compared to reversal strategies
- Fires often in bull markets, rarely in choppy or bear markets (by design)
- The wide 6× ATR target means the MACD bearish exit will often fire before the target is reached
