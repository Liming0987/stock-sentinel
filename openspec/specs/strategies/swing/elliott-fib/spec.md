# Elliott Wave + Fibonacci Strategy

**File:** `backend/app/strategies/swing/elliott_fib.py`
**Type:** Swing (daily bars)
**Max positions:** 2

## Overview

Trades Wave 4 pullbacks inside a confirmed 5-wave Elliott impulse. Requires 4 alternating swing pivots (Low→High→Low→High) that satisfy Elliott's structural rules, then enters when the current price lands at a Fibonacci retracement level of Wave 3. More selective and structurally confirmed than Fib Retracement — no wave counting required there; here it's mandatory.

> **Note (Sep 2026):** Wave 2 entries were removed. Only Wave 4 entries remain. W2 had less structural confirmation and required dual EMA alignment; the W4 setup is higher quality and the focus going forward.

## Pivot detection

- **Lookback:** 180 trading days (~9 months)
- **Window:** `PIVOT_N = 3` bars each side — a bar is a swing high if it's the highest of 7 consecutive bars (3 before + itself + 3 after). Same for lows.
- Consecutive same-type pivots are merged (keep only the most extreme).
- Result: a strictly alternating L→H→L→H→... list.

PIVOT_N=3 is deliberately faster than the standard 5-bar method — catches setups that resolve quickly, accepts slightly more noise.

## Wave 4 entry conditions

**Structural requirements (L→H→L→H pattern = W1 start, W1 peak, W2 low, W3 peak):**
- W2 did not fully erase W1: `p2 > p0`
- W3 ≥ W1 in size (W3 is never the shortest wave)
- W3 ≥ 5% of price (W3_MIN_PCT) — too-small W3 produces targets barely beyond the stop
- Current price has pulled back from W3 peak but not below W1 peak (W4 in valid territory)
- W4 retrace between 10% and 50% of W3
- Volume not >2× average (clear distribution = reject; healthy pullback = allow)

**Fibonacci confluence:** price within ±1.8% of 23.6%, 38.2%, or 50% of W3

**Volatility filter:** skip if daily ATR > 7% of price (hyper-volatile tickers produce wave counts that look valid but are noise — PLTR cost −$76.59 before this filter)

**Confidence by Fib level:**
| Level | Base | W3 extended bonus |
|-------|------|-------------------|
| 23.6% | 0.82 | +0.08 if W3 ≥ 1.618×W1 |
| 38.2% | 0.76 | +0.08 if W3 ≥ 1.618×W1 |
| 50.0% | 0.68 | +0.08 if W3 ≥ 1.618×W1 |

## Exit conditions

- **Target:** `W3 peak + W1` (conservative W5 projection)
  - Extended to `W3 peak + 1.618×W1` when W3 ≥ 1.618×W1 (strong trend = further W5)
- **Stop:** `W1 peak − 1×ATR` (Elliott invalidation level — if price falls here, the wave count is broken)
- Standard stop/target hit (base class)

## Parameters

| Parameter      | Value  | Rationale |
|----------------|--------|-----------|
| PIVOT_N        | 3      | Faster than standard 5-bar — catches quicker setups at the cost of slightly more noise |
| LOOKBACK       | 180    | ~9 months of history to find the L→H→L→H pattern |
| FIB_TOL        | ±1.8%  | Tolerance band around each Fib level |
| W4_LEVELS      | 23.6%, 38.2%, 50% | W4 is shallower than W2; 50% is the deepest valid W4 |
| W3_MIN_PCT     | 5%     | Raised from 4% — 4% W3s on NVDA produced targets too shallow (< ATR from entry) |
| W3_MIN_RATIO   | 1.0×W1 | W3 must be at least as large as W1 (core Elliott rule) |
| W4_MAX_RETRACE | 50%    | W4 cannot retrace more than 50% of W3 |
| MAX_ATR_PCT    | 7%     | Skip if daily ATR > 7% of price — noisy wave counts |

## Backtest findings (Jun 2026)

- **MAX_ATR_PCT = 7%**: PLTR's 5–12% daily ATR created wave counts that looked valid but were noise. −$76.59 loss. Capping at 7% filters these while keeping quality patterns.
- **W3_MIN_PCT 4→5%**: 4% W3s on NVDA produced targets barely beyond the stop distance — unfavorable R:R.
- **W2 entries removed (Sep 2026)**: less structural confirmation required a dual EMA filter (50+200) to compensate. W4 entries are higher quality; W2 was removed to focus on the better setup.

## Rejected alternatives

- **PIVOT_N = 5** (standard): too slow — misses setups that resolve quickly
- **W3_MIN_PCT = 4%**: targets too shallow on NVDA
- **MAX_ATR_PCT removed**: PLTR losses demonstrated it's necessary
- **W2 entries**: lower win rate, required more filters to compensate; removed Sep 2026

## Known limitations

- Requires 180 days of price history — won't fire on newer stocks
- Wave counting is approximate (3-bar pivots can be noisy)
- No RSI filter — structural rules + Fib confluence are the sole confirmation
- Scans newest-to-oldest, so only the most recent valid pattern is used; older patterns are ignored even if stronger
