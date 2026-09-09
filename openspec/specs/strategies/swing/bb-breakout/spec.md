# BB Breakout Strategy

**File:** `backend/app/strategies/swing/bb_breakout.py`
**Type:** Swing (daily bars)
**Max positions:** 2

## Overview

Buys when price breaks above the upper Bollinger Band with a volume surge and healthy RSI momentum, in a stock already in a macro uptrend. The core idea: a close above the upper BB is statistically rare (~2.5% of days), so when it happens on high volume with momentum in the right range, it signals a real breakout rather than noise.

## Entry conditions

**Hard requirements (all must pass):**
- Price above EMA-200 (macro uptrend filter — mandatory since Jun 2026 backtest)
- Price above upper Bollinger Band (20-day, 2 std dev)
- RSI between 50 and 68
- Volume ≥ 2× the 30-day average

**Confidence boosters (optional):**
- RSI ≥ 55 → +0.2 confidence (strong momentum)
- Volume ≥ 3× average → +0.2 (vs +0.1 for 2–3×)
- Price > upper BB × 1.005 → +0.1 (solid break, not just touching)

**Confidence range:** 0.5 (bare minimum) to 1.0 (capped)

## Exit conditions

- **Stop:** `max(BB_middle, entry − 1.5 × ATR)` — whichever is higher (closer to price)
- **Target:** `entry + 4 × ATR`
- **Indicator exit:** price falls below BB middle band

## Parameters

| Parameter        | Value | Rationale |
|------------------|-------|-----------|
| RSI_MIN          | 50    | RSI < 50 had 20% win rate — stock still in correction zone; 50+ means upside momentum already in control |
| RSI_MAX          | 68    | RSI > 70 breakouts were extended — 80% ended as false breaks; 68 gives a small buffer |
| MIN_VOL_RATIO    | 2.0   | At 1.5×, 38% false breakout rate; at 2.0×, drops to ~18% |
| TARGET_ATR_MULT  | 4.0   | Winners consistently ran past a 3× target; raised to capture the full move |
| STOP_ATR_MULT    | 1.5   | ATR floor on the stop — prevents the BB middle from sitting too far below entry on volatile tickers |
| BB period        | 20    | Standard; not tuned |
| BB std dev       | 2.0   | Standard; not tuned |

## Backtest findings (Jun 2026)

- **EMA-200 filter** was the single biggest improvement. Entering breakouts on META and MSFT while they were below EMA-200 caused most of the −$43 loss. Made mandatory.
- **MIN_VOL_RATIO 1.5→2.0** was the key volume improvement. SOFI (−$123) triggered on 1.6× only. At 2.0×, false breakout rate nearly halved.
- **RSI_MIN 45→50**: RSI 45–49 entries had only 20% win rate — consistently entering during corrections, not breakouts.
- **RSI_MAX 70→68**: RSI > 70 breakouts were already extended; 80% reversed. Tightening to 68 filters the worst of these.
- **TARGET_ATR_MULT 3.0→4.0**: Only 7.7% of exits were hitting the old 3× target. Winners routinely ran further.

## Stop design note

The stop uses `max(BB_middle, entry − 1.5×ATR)` — the higher of the two, meaning the tighter stop. On volatile tickers (SOFI ATR = 5.6% of price), the Bollinger Bands are wide and BB_middle can sit far below entry, risking too much. The ATR floor caps the worst-case loss regardless of band width.

## Rejected alternatives

- **RSI_MIN = 45**: 20% win rate on RSI 45–49 entries — correction zone, not breakout territory
- **MIN_VOL_RATIO = 1.5**: 38% false breakout rate; the extra bar on volume is worth the missed entries
- **TARGET_ATR_MULT = 3.0**: Too close — winners consistently ran past it

## Known limitations

- Fires rarely on low-volatility stocks (bands are tight, fewer breakouts occur)
- No EMA-50 slope check — unlike Momentum and Fib Retracement, doesn't verify the medium-term trend is still rising
- Volatile tickers (high ATR) can produce wide stops even with the ATR floor
