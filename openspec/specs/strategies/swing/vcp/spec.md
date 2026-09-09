# VCP (Volatility Contraction Pattern) Strategy

**File:** `backend/app/strategies/swing/vcp.py`
**Type:** Swing (daily bars)
**Max positions:** 3
**Minimum history required:** 200 trading days (~10 months)

## Overview

Minervini-style pivot breakout. Finds stocks that have made a significant prior advance, consolidated in a series of progressively tighter pullbacks (the "coiling spring"), and then broken above the tightest pullback's high on a volume surge. The most data-intensive and selective strategy in the system — requires Stage 2 uptrend confirmation plus 2–4 valid contractions before it fires.

## Stage 2 uptrend (hard requirement)

All four must be true:
1. `price > EMA-50 > EMA-150 > EMA-200` (full EMA stack in order)
2. EMA-200 is rising over the last 50 bars
3. Price within 25% of its 52-week high (near the best, not recovering from a breakdown)
4. Prior advance ≥ 20% in the 100 bars before the base started (real institutional demand behind the move)

## Contraction detection

Within the last 150 bars, finds 2–4 swing high→low contractions that satisfy all of:

| Rule | Why |
|------|-----|
| Depth decreasing each contraction | The coil is genuinely tightening |
| Each high lower than the prior high | No new highs during consolidation |
| Each low higher than the prior low | Sellers losing power |
| Average volume decreasing each contraction | Supply drying up |
| Each contraction completes within 50 bars | Not a drawn-out slog |
| Gap between contractions ≤ 30 bars | Genuinely consecutive, not separated by a new trend |

Minimum depth per contraction: 1.5%. Keeps the most recent 4 if more are found.

## Entry conditions

- VCP detected with Stage 2 confirmed
- `price > pivot × 1.01` (≥1% above the high of the last contraction)
- Volume ≥ 1.4× average on the breakout bar

**Pivot** = high of the last (tightest) contraction.

## Exit conditions

- **Stop:** `max(last_contraction_low × 0.99, entry × 0.92)` — tighter of: just under last contraction low, or 8% below entry
- **Risk** = `entry − stop_loss`
- **Target** = `entry + risk × 2.5` (always 2.5× risk, fixed)

## Confidence

| Condition | Points |
|-----------|--------|
| Base | 0.45 |
| Per contraction (up to 4) | +0.05 each |
| Most contractions had quiet volume (vol_dry) | +0.15 |
| Breakout volume ≥ 1.5× | +0.10 |
| Stage 2 confirmed | +0.10 |
| Hard cap | 0.92 |

## Parameters

| Parameter          | Value | Rationale |
|--------------------|-------|-----------|
| MIN_BARS           | 200   | Need full EMA-200 stack; below 200 bars the 150- and 200-span EMAs collapse together |
| _STOP_PCT          | 8%    | Minervini standard stop; hard maximum loss cap |
| _TARGET_MULT       | 2.5×  | Fixed R:R; Minervini methodology |
| _MIN_VOL_RATIO     | 1.4×  | 40%+ above average — decisive break, not a drift |
| _BREAKOUT_BUFFER   | 1.01  | Must clear pivot by ≥1%; razor-thin touches are noise |
| MAX_CONTRACTION    | 50 bars | Per-contraction time limit |
| MAX_GAP            | 30 bars | Between-contraction recovery time limit |

## Known limitations

- Requires 200 days of history — newest stocks never qualify
- Most selective strategy in the system — long quiet periods are normal
- Stage 2 prior advance check (≥20%) can exclude stocks that ran up quietly without a clean low before the base
- The 2.5× fixed target means the position exits mechanically regardless of how strong the trend looks
