# MACD Histogram Strategy

**File:** `backend/app/strategies/swing/macd_histogram.py`
**Type:** Swing (daily bars)
**Max positions:** 2

## Overview

Catches early momentum shifts by detecting the MACD histogram turning upward from clearly negative territory. Buys while the stock is still technically weak — before the recovery is obvious — betting that 4 consecutive rising histogram bars from a negative starting point signals a real turn, not a one-day wobble. The earliest-entry strategy in the system.

## Entry conditions

**Hard requirements (all must pass):**
- RSI between 38 and 62
- Histogram bar 5 days ago was clearly negative (< −0.05% of price)
- Every bar since has been higher than the one before (4 consecutive rises, no exceptions)

**"Clearly negative" threshold is price-normalized:** `−NEG_HIST_FRAC × last_price` (= −0.05% of price). This keeps reversal detection consistent across high- and low-priced stocks — a fixed −0.005 threshold was too lenient on high-priced names.

**Confidence scoring:**
| Condition | Points |
|-----------|--------|
| Base | 0.45 |
| Histogram crossed above zero | +0.25 |
| RSI ≥ 45 (momentum recovering) | +0.15 |
| Volume ≥ 1.3× average | +0.10 |
| MACD line > signal line | +0.05 |

## Exit conditions

- **Stop:** `entry − 2 × ATR`
- **Target:** `entry + 5 × ATR`
- **Indicator exit:** 2 consecutive histogram bars below −0.10% of price (EXIT_HIST_FRAC)
  - Single bar required before Jun 2026 fix — caused 35 premature exits that reversed next day

## Parameters

| Parameter       | Value   | Rationale |
|-----------------|---------|-----------|
| LOOKBACK        | 4 bars  | Raised from 3 — requiring 4 rising bars reduces noise entries by ~15% while keeping 90% of quality setups; most of the 104 churn trades were 3-bar signals |
| RSI_MIN         | 38      | Raised from 35 — RSI 35–38 entries had <30% win rate |
| RSI_MAX         | 62      | Ceiling — if RSI is already high, this isn't a dip recovery |
| TARGET_ATR_MULT | 5.0×    | Raised from 4.0× — only 7.7% of exits were hitting the old target; winners ran further |
| STOP_ATR_MULT   | 2.0×    | Unchanged — only 1 stop-loss hit in 104 backtest trades |
| NEG_HIST_FRAC   | 0.0005  | Entry: histogram must be below −0.05% of price to count as "negative" |
| EXIT_HIST_FRAC  | 0.001   | Exit: 2 consecutive bars below −0.10% of price |

## Backtest findings (Jun 2026)

- **LOOKBACK 3→4**: 104 churn trades at 3-bar setting; most were low-quality. 4 bars cuts noise while keeping quality setups.
- **Two-bar exit requirement**: single negative bar caused 35 premature exits that re-entered the next day at higher cost. Now requires 2 consecutive bars.
- **Price-normalized thresholds**: fixed absolute thresholds (−0.005, −0.01) were inconsistent — too lenient on high-priced stocks. Normalizing by price fixes this.
- **TARGET 4→5×**: same pattern as other strategies — old target too close, winners routinely ran past it.

## Rejected alternatives

- **3-bar LOOKBACK**: 104 churn trades, mostly noise
- **Single negative bar exit**: 35 premature exits reversed next day — too sensitive to one-day wobbles
- **Fixed absolute histogram thresholds**: inconsistent across price ranges

## Known limitations

- Earliest entry in the system — buys while histogram is still negative, so the stock looks weak at entry
- No trend filter (no EMA check) — can fire in downtrends if the histogram turns up temporarily
- RSI range (38–62) is the only directional filter beyond the histogram pattern itself
