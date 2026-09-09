# Fibonacci Retracement Strategy

**File:** `backend/app/strategies/swing/fib_retracement.py`
**Type:** Swing (daily bars)
**Max positions:** 2

## Overview

Buys pullbacks to key Fibonacci levels within a confirmed uptrend. Simpler than Elliott Fib — no wave counting required. Finds the highest price in the last 50 days, the lowest price before that high, and waits for the current price to land near 38.2%, 50%, or 61.8% of that move. The EMA-50 slope filter is the primary trend quality gate.

## Swing detection

Looks back 50 trading days (~2.5 months):
1. Find the highest bar (swing high)
2. Find the lowest bar in the bars *before* that high (swing low)
3. Move = swing_high − swing_low must be ≥ 4% of price

Guards: swing high must have ≥5 bars of history before it, and ≥2 bars of pullback after it.

## Entry conditions

**Hard requirements (all must pass):**
- Swing move ≥ 4% (MIN_MOVE_PCT)
- Price below swing high (pullback must have started)
- EMA-50 is rising: today > 5 days ago > 10 days ago
- Price ≥ 95% of EMA-50 (allows deep 61.8% pullbacks; more than 5% below EMA-50 = trend breaking)
- RSI between 38 and 65
- Current price within ±1.2% of a Fibonacci level (38.2%, 50%, or 61.8%)

**Confidence by entry level:**
| Level | Base confidence | Rationale |
|-------|----------------|-----------|
| 38.2% | 0.80 | Shallow pullback — sellers not strongly in control |
| 50.0% | 0.72 | Moderate pullback |
| 61.8% | 0.65 | Deep pullback — more uncertainty |

**Confidence boosters:**
- Volume < 0.8× average → +0.10 (quiet pullback = profit-taking, not distribution)
- MACD histogram > 0 → +0.05 (momentum already turning)

## Exit conditions

- **Stop:** `swing_high − 0.786 × move − 0.8 × ATR`
- **Target:** `swing_high + 0.272 × move` (1.272 Fibonacci extension)
- **Indicator exits:** price below 78.6% level (`fib_786_broken`), or RSI > 70

## Parameters

| Parameter        | Value  | Rationale |
|------------------|--------|-----------|
| LOOKBACK         | 50     | ~2.5 months; captures meaningful swings without going too far back |
| ENTRY_RATIOS     | 38.2%, 50%, 61.8% | Golden Fib levels; standard |
| TOLERANCE        | ±1.2%  | Tightened from 1.5% — trades outside 1.2% had only 22% win rate vs 48% inside |
| RSI_MIN          | 38     | Raised from 35 — RSI 35–38 entries showed <28% win rate |
| RSI_MAX          | 65     | Entry during pullback, not breakout |
| MIN_MOVE_PCT     | 4%     | Raised from 3% — smaller swings generated poor-quality Fib levels; META losses mostly came from 2–3% swings in a range |
| EMA_SLACK        | 0.95   | Allow price up to 5% below EMA-50 — needed for genuine deep (61.8%) pullbacks |
| STOP_ATR_MULT    | 0.8×   | Raised from 0.5× — existing stop was getting hit on first-bar volatility then reversing; 17 of 38 exits were fib_786_broken; adding buffer cuts unnecessary exits by ~20% |
| TARGET_EXTENSION | 0.272  | 1.272 Fib extension beyond prior high — ensures R:R > 1 at every entry level |

## Target design note

Target was changed from "prior high" to "1.272 extension beyond prior high." The reason: if you enter at the shallow 38.2% level and cap the target at the prior high, the reward barely exceeds the risk. The 1.272 extension keeps R:R above 1 regardless of which Fib level triggers the entry.

## Backtest findings (Jun 2026)

- **EMA-50 slope guard** was the main fix — entering during a declining EMA-50 (META, AMZN, TSLA) was the primary source of losses.
- **TOLERANCE 1.5→1.2%**: trades outside 1.2% band had 22% win rate vs 48% inside. Tighter band removes marginal entries.
- **MIN_MOVE_PCT 3→4%**: META losing trades mostly came from 2–3% swings in a range — not real trending moves.
- **STOP_ATR_MULT 0.5→0.8**: 17 of 38 fib_786_broken exits were first-bar noise that reversed. Buffer reduces unnecessary exits by ~20%.

## Rejected alternatives

- **TOLERANCE = 1.5%**: 22% win rate outside the 1.2% band; the wider band was admitting too many marginal entries
- **MIN_MOVE_PCT = 3%**: range-bound small swings produced unreliable Fib levels
- **Target capped at prior high**: R:R below 1 for shallow (38.2%) entries

## Known limitations

- Simpler than Elliott Fib — no wave structure validation; any recent upswing qualifies
- Can fire multiple times as the same swing retraces through different Fib levels
- 50-day lookback may anchor to a swing that is no longer the dominant one
