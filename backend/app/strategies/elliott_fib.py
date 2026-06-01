"""Elliott Wave + Fibonacci: trade W2 and W4 pullbacks inside a 5-wave impulse.

Elliott Wave rules enforced:
  - Wave 2 never retraces past Wave 1 start (100% retrace → invalid count)
  - Wave 3 is never shorter than Wave 1
  - Wave 4 never closes inside Wave 1 price territory

Fibonacci confluence:
  - Wave 2 entries at 38.2 %, 50 %, or 61.8 % of Wave 1
  - Wave 4 entries at 23.6 %, 38.2 %, or 50 % of Wave 3
  - Targets are standard EW projections (W3 = 1.618×W1; W5 ≈ W1)

Design decisions:
  - PIVOT_N=3 so pivots are confirmed after only 3 bars — faster than the
    standard 5-bar method, accepting slightly more noise in exchange for
    catching setups that resolve quickly.
  - Always scan the most-recent valid pattern first (reverse iteration).
  - No RSI filter — EW structure + Fib confluence is the confirmation.
  - Exit on stop-loss or target only; no indicator-based exits.
"""
from typing import Dict, List, Optional, Tuple
from app.strategies.base import BaseStrategy, Signal

PIVOT_N  = 3    # bars on each side to confirm a pivot (faster than default 5)
LOOKBACK = 180  # bars to search for pivots
FIB_TOL  = 0.018  # ±1.8 % band around each Fib level

W2_LEVELS = [0.382, 0.500, 0.618]   # W2 can retrace anywhere in this range
W4_LEVELS = [0.236, 0.382, 0.500]   # W4 is shallower; 50 % is the deepest valid

# EW structural rules
W2_MAX_RETRACE = 0.99   # W2 must not fully erase W1
W3_MIN_RATIO   = 1.00   # W3 ≥ W1 (never the shortest wave)
W4_MAX_RETRACE = 0.50   # W4 stays above the 50 % level of W3
W3_MIN_PCT     = 0.04   # W3 must be a ≥ 4 % move to be worth trading
W1_MIN_PCT     = 0.05   # W1 must be a ≥ 5 % move for W2 entries


def _find_pivots(df) -> List[Tuple[int, float, str]]:
    """
    Alternating swing highs ('H') / lows ('L') over the last LOOKBACK bars.
    Each run of the same type keeps only the most extreme pivot.
    """
    window = df.iloc[-LOOKBACK:] if len(df) > LOOKBACK else df
    offset = len(df) - len(window)
    n      = PIVOT_N
    highs  = window["High"].values
    lows   = window["Low"].values

    raw: List[Tuple[int, float, str]] = []
    for i in range(n, len(window) - n):
        if highs[i] == max(highs[i - n: i + n + 1]):
            raw.append((offset + i, float(highs[i]), 'H'))
        elif lows[i] == min(lows[i - n: i + n + 1]):
            raw.append((offset + i, float(lows[i]), 'L'))

    zz: List[Tuple[int, float, str]] = []
    for p in raw:
        if not zz:
            zz.append(p)
        elif p[2] == zz[-1][2]:
            if (p[2] == 'H' and p[1] > zz[-1][1]) or \
               (p[2] == 'L' and p[1] < zz[-1][1]):
                zz[-1] = p
        else:
            zz.append(p)
    return zz


def _w4_signal(pivots, last_price, atr, ind) -> Optional[Signal]:
    """
    Scan for a confirmed L-H-L-H structure and enter when current price
    is at a W4 Fib retracement level (23.6 %, 38.2 %, or 50 % of W3).

    Scans newest-to-oldest so the most recent valid pattern is used.
    Volume filter: reject only if volume is more than 2× average (clear
    distribution), not merely above average.
    """
    vol_ratio = ind.get("volume_ratio", 1.0)

    for i in range(len(pivots) - 4, -1, -1):   # newest → oldest
        p0, p1, p2, p3 = pivots[i], pivots[i+1], pivots[i+2], pivots[i+3]
        if not (p0[2]=='L' and p1[2]=='H' and p2[2]=='L' and p3[2]=='H'):
            continue

        w1 = p1[1] - p0[1]
        w2 = p1[1] - p2[1]
        w3 = p3[1] - p2[1]
        if w1 <= 0 or w3 <= 0:
            continue

        # ── Elliott structural rules ──────────────────────────────────────
        if p2[1] <= p0[1]:                    # W2 fully erased W1
            continue
        if w2 / w1 > W2_MAX_RETRACE:
            continue
        if w3 < W3_MIN_RATIO * w1:            # W3 shortest → invalid count
            continue
        if w3 / p3[1] < W3_MIN_PCT:           # W3 too small to trade
            continue
        if last_price >= p3[1]:               # no pullback yet
            continue
        if last_price <= p1[1]:               # W4 entered W1 territory → invalid
            continue

        w4_retrace = (p3[1] - last_price) / w3
        if not (0.10 <= w4_retrace <= W4_MAX_RETRACE):
            continue

        # ── Fib confluence ────────────────────────────────────────────────
        hit = None
        for r in W4_LEVELS:
            level = p3[1] - r * w3
            if abs(last_price - level) / level <= FIB_TOL:
                hit = (r, level)
                break
        if hit is None:
            continue

        # Reject only on clear distribution (heavy selling into the pullback)
        if vol_ratio > 2.0:
            continue

        ratio, level_price = hit

        # W5 target: W3 top + W1 (conservative); extend when W3 was strong
        w5_factor = 1.618 if w3 >= 1.618 * w1 else 1.0
        target = round(p3[1] + w5_factor * w1, 2)

        # Stop just below W1 top — Elliott invalidation level with ATR buffer
        stop = round(p1[1] - atr * 1.0, 2)

        conf = {0.236: 0.82, 0.382: 0.76, 0.500: 0.68}[ratio]
        if w3 >= 1.618 * w1:
            conf = min(1.0, conf + 0.08)

        return Signal(
            action="buy",
            confidence=round(conf, 3),
            entry_price=last_price,
            stop_loss=stop,
            target=target,
            reasoning=[
                f"Elliott W4 at Fib {ratio*100:.1f}% of W3 (${level_price:.2f})",
                f"W1={w1:.1f}  W3={w3:.1f} ({w3/w1:.2f}×)  W2-retrace={w2/w1*100:.0f}%",
                f"W5 target=${target:.2f}  stop=${stop:.2f}",
            ],
        )
    return None


def _w2_signal(pivots, last_price, atr, ind) -> Optional[Signal]:
    """
    Scan for an L-H pattern (W1) and enter at 38.2 %, 50 %, or 61.8 % Fib
    retracement of W1.

    Two key differences from W4:
    - Less structural confirmation, so requires EMA-50 AND EMA-200 alignment
      (both long- and medium-term trend must be bullish).
    - Stop uses the 78.6 % retracement level (deepest valid W2) OR 2× ATR
      below entry, whichever is tighter — this caps the dollar loss per trade
      without relying on the W1 start which can be many ATRs away.

    Scans newest-to-oldest so the most recent W1 is prioritised.
    """
    ema_50  = ind.get("ema_50")
    ema_200 = ind.get("ema_200")

    for i in range(len(pivots) - 2, -1, -1):   # newest → oldest
        p0, p1 = pivots[i], pivots[i+1]
        if not (p0[2] == 'L' and p1[2] == 'H'):
            continue

        w1 = p1[1] - p0[1]
        if w1 <= 0 or w1 / p1[1] < W1_MIN_PCT:   # W1 too small
            continue
        if last_price >= p1[1] or last_price <= p0[1]:
            continue   # not in the pullback zone

        w2_retrace = (p1[1] - last_price) / w1
        if w2_retrace > W2_MAX_RETRACE:
            continue

        # Dual trend filter: medium- and long-term trend must be bullish
        if ema_50  is not None and last_price < ema_50  * 0.985:
            continue
        if ema_200 is not None and last_price < ema_200:
            continue

        # Fib confluence
        hit = None
        for r in W2_LEVELS:
            level = p1[1] - r * w1
            if abs(last_price - level) / level <= FIB_TOL:
                hit = (r, level)
                break
        if hit is None:
            continue

        ratio, level_price = hit

        # Stop: tighter of 78.6 % retrace level or 2× ATR below entry.
        # This caps the per-trade loss regardless of how large W1 was.
        stop_786 = p1[1] - 0.786 * w1 - atr * 0.3
        stop_atr = last_price - atr * 2.0
        stop = round(max(stop_786, stop_atr), 2)   # max = closer to entry = tighter

        # W3 projection: W1 top + 1.618 × W1
        target = round(p1[1] + 1.618 * w1, 2)

        conf = {0.382: 0.65, 0.500: 0.70, 0.618: 0.75}[ratio]

        return Signal(
            action="buy",
            confidence=round(conf, 3),
            entry_price=last_price,
            stop_loss=stop,
            target=target,
            reasoning=[
                f"Elliott W2 at Fib {ratio*100:.1f}% of W1 (${level_price:.2f})",
                f"W1: ${p0[1]:.2f} → ${p1[1]:.2f}  ({w1/p1[1]*100:.1f}%)",
                f"W3 target=${target:.2f}  stop=${stop:.2f}",
            ],
        )
    return None


class ElliottFibStrategy(BaseStrategy):
    name = "elliott_fib"
    description = (
        "Elliott 5-wave + Fibonacci. Enters at Wave 4 pullbacks (23.6/38.2/50 % of W3) "
        "or Wave 2 pullbacks (38.2/50/61.8 % of W1). "
        "Targets W3 and W5 Fibonacci projections; stops at Elliott invalidation levels."
    )
    max_positions = 2

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        df         = context.get("price_df")
        ind        = context.get("indicators", {})
        last_price = ind.get("last_price")
        atr        = ind.get("atr")

        if df is None or len(df) < LOOKBACK // 3:
            return Signal.hold()
        if last_price is None or atr is None:
            return Signal.hold()
        if context.get("current_position"):
            return Signal.hold()

        pivots = _find_pivots(df)
        if len(pivots) < 2:
            return Signal.hold()

        # W4 first — more structural confirmation
        sig = _w4_signal(pivots, last_price, atr, ind)
        if sig is not None:
            return sig

        # W2 fallback — earlier entry, less confirmed
        sig = _w2_signal(pivots, last_price, atr, ind)
        if sig is not None:
            return sig

        return Signal.hold()

    def should_close(self, trade, context: Dict) -> Optional[str]:
        return super().should_close(trade, context)
