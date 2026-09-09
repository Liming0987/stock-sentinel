# RSI Mean Reversion Strategy

**File:** `backend/app/strategies/swing/rsi_meanreversion.py`
**Type:** Swing (daily bars)
**Max positions:** 2

## Overview

Buys the bounce out of an oversold condition — specifically when RSI crosses back *above* 30 rather than when it first dips below. The key design choice is waiting for the crossover back up, confirming the selling pressure has exhausted itself and buyers are already stepping in. Requires a macro uptrend (above EMA-200) to avoid catching falling knives.

## Entry conditions

**Hard requirements (all must pass):**
- Price above EMA-200 (no oversold buys in a macro downtrend)
- RSI crossed from below 30 to above 30: `prev_rsi < 30 <= curr_rsi`
  - Both conditions must be true simultaneously — already above 30 yesterday means no signal

**Confidence:** scales with depth of the recent oversold dip (lowest RSI in last 6 bars):
```
confidence = (30 − trough_rsi) / 30 + 0.5
```

| Trough RSI | Confidence |
|-----------|-----------|
| 25        | 0.67       |
| 20        | 0.83       |
| 15        | 1.00 (cap) |

Deeper dip → more exhausted sellers → stronger expected snap-back.

## Exit conditions

- **Stop:** `entry − 2 × ATR`
- **Target:** `entry + 3 × ATR`
- **Indicator exit:** RSI > 60 (stock has recovered to neutral; bounce play is done)
- **Failsafe:** max holding 60 days (base class)

## Parameters

| Parameter          | Value | Rationale |
|--------------------|-------|-----------|
| RSI_BUY_THRESHOLD  | 30    | Standard oversold level; not tuned |
| RSI_EXIT_THRESHOLD | 60    | Neutral/recovering — edge of the bounce play is gone |
| STOP_LOSS_ATR      | 2.0×  | Only 1 stop-loss hit in backtest — fine as-is |
| TARGET_ATR         | 3.0×  | Shorter hold than trend strategies; catching a bounce back to normal, not riding a trend |
| TROUGH_LOOKBACK    | 6     | 6 bars (~1.5 weeks) to find the depth of the recent dip |

## Regime note

This strategy fires infrequently in persistent bull markets — stocks rarely get genuinely oversold when the trend is strong. Designed for range-bound / choppy markets where oversold bounces are reliable. The Jun 2025–Jun 2026 backtest (tech bull market) confirmed low signal count by design.

## Rejected alternatives

- **Buy on first dip below 30**: catches falling knives — RSI can keep falling to 20, 15, or lower. Waiting for the crossover back above confirms the selling is done.
- **EMA-200 as optional**: entering oversold positions in downtrends (below EMA-200) is the classic falling-knife failure mode; made mandatory.

## Known limitations

- Very low signal frequency in strong bull markets (by design)
- No volume filter — an oversold bounce can happen on thin volume
- Target of 3× ATR may be too conservative in some cases; the RSI > 60 exit will often fire first anyway
