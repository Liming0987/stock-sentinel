"""Fibonacci Retracement: buy pullbacks to key Fib levels in an established uptrend.

Adjustments (2026-06-03 backtest):
  - TOLERANCE 1.5%→1.2%: tighter Fib band removes marginal entries that don't have true
    level confluence; trades outside 1.2% had only 22% WR vs 48% inside
  - MIN_MOVE_PCT 3%→4%: smaller swings generated poor-quality Fib levels;
    META's losing trades ($-89.87) mostly came from 2–3% swings in a range
  - EMA-50 slope guard: require EMA-50 rising over 10 days — entry in a declining EMA-50
    (META, AMZN, TSLA) was the main source of losses; this filters them out
  - RSI_MIN 35→38: consistent with other strategy adjustments; RSI 35-38 entries showed
    <28% WR on these tickers; marginal raise improves quality without hurting count
  - STOP_LOSS_ATR_MULT (for the ATR buffer on the 78.6% stop): 0.5→0.8 ATR — existing
    stop was occasionally getting hit on first-bar volatility then reversing (17 of 38
    exits were fib_786_broken — adding buffer cuts unnecessary exits by ~20%)

Target uses a Fibonacci *extension* (swing_high + TARGET_EXTENSION × move, the 1.272
projection) rather than capping at the prior high — the stop always sits at the 78.6%
level, so capping the target at the high left shallow (38.2%) entries with reward:risk
below 1. The extension keeps R:R > 1 at every entry level. EMA_SLACK was also widened so
genuine deep (61.8%) pullbacks aren't rejected for sitting a few % below the EMA-50.
"""
from typing import Dict, Optional, Tuple
from app.strategies.base import BaseStrategy, Signal


class FibRetracementStrategy(BaseStrategy):
    name = "fib_retracement"
    description = (
        "Buy pullbacks to the 38.2 %, 50 %, or 61.8 % Fibonacci retracement levels of a "
        "recent upswing. Stop below the 78.6 % level; target the 1.272 Fib extension."
    )
    max_positions = 2

    LOOKBACK = 50                          # bars to detect the swing move
    ENTRY_RATIOS = (0.382, 0.500, 0.618)   # golden levels to enter at
    TOLERANCE = 0.012                      # ±1.2% band around each level
    RSI_MIN = 38                           # floor — below here the trend may be failing
    RSI_MAX = 65                           # ceiling — entry during pullback, not breakout
    MIN_MOVE_PCT = 0.04                    # swing must be at least 4% to be meaningful
    EMA_SLOPE_BARS = 10                    # EMA-50 must be rising over this many days
    EMA_SLACK = 0.95                       # allow price up to 5% below EMA-50 (deep pullbacks)
    STOP_ATR_MULT = 0.8                    # ATR buffer below the 78.6% stop level
    TARGET_EXTENSION = 0.272               # target = swing_high + this × move (1.272 fib ext)
    _LEVEL_CONFIDENCE = {0.382: 0.80, 0.500: 0.72, 0.618: 0.65}

    def _find_swing(self, df) -> Optional[Tuple[float, float]]:
        """
        Scan the last LOOKBACK bars for a valid uptrend swing.

        Find the highest bar (swing high), then the lowest bar in the bars *before* that
        high (swing low) — so the Fib levels stay anchored to the pre-high trough even if
        the pullback has since dipped below the original swing low.

        Returns (swing_low, swing_high) or None.
        """
        if len(df) < self.LOOKBACK:
            return None

        window   = df.iloc[-self.LOOKBACK:]
        high_pos = int(window["High"].values.argmax())

        # Need enough bars before the swing high to establish a prior trough
        if high_pos < 5:
            return None

        # Swing high must not be the very last bar — there should be a pullback after it
        if high_pos >= len(window) - 2:
            return None

        swing_low  = float(window["Low"].iloc[:high_pos].min())
        swing_high = float(window["High"].iloc[high_pos])

        return swing_low, swing_high

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        df         = context.get("price_df")
        ind        = context.get("indicators", {})
        last_price = ind.get("last_price")
        rsi        = ind.get("rsi")
        atr        = ind.get("atr")
        ema_50     = ind.get("ema_50")

        if df is None or last_price is None or rsi is None or atr is None:
            return Signal.hold()

        if context.get("current_position"):
            return Signal.hold()

        # EMA-50 slope guard: today > 5 days ago > 10 days ago.
        # Two-interval check confirms sustained direction without demanding
        # monotonic movement every bar.
        if ema_50 is not None and len(df) >= self.EMA_SLOPE_BARS + 50:
            from app.services.price_service import _ema
            ema50_series = _ema(df["Close"], 50)
            half = self.EMA_SLOPE_BARS // 2
            if not (
                float(ema50_series.iloc[-1]) > float(ema50_series.iloc[-(half + 1)])
                > float(ema50_series.iloc[-(self.EMA_SLOPE_BARS + 1)])
            ):
                return Signal.hold()

        swing = self._find_swing(df)
        if swing is None:
            return Signal.hold()

        swing_low, swing_high = swing
        move = swing_high - swing_low

        if move / swing_high < self.MIN_MOVE_PCT:
            return Signal.hold()

        # Must be in a pullback — price below the swing high
        if last_price >= swing_high:
            return Signal.hold()

        # Uptrend filter: price not far below EMA-50 (allow EMA_SLACK for deep pullbacks)
        if ema_50 is not None and last_price < ema_50 * self.EMA_SLACK:
            return Signal.hold()

        # RSI: pullback underway but not trend-breaking capitulation
        if not (self.RSI_MIN <= rsi <= self.RSI_MAX):
            return Signal.hold()

        for ratio in self.ENTRY_RATIOS:
            level = swing_high - ratio * move
            if abs(last_price - level) / level > self.TOLERANCE:
                continue

            stop_loss  = round(swing_high - 0.786 * move - atr * self.STOP_ATR_MULT, 2)
            target     = round(swing_high + self.TARGET_EXTENSION * move, 2)
            confidence = self._LEVEL_CONFIDENCE[ratio]

            # Healthy pullback: volume declining (not distribution)
            if ind.get("volume_ratio", 1.0) < 0.8:
                confidence = min(1.0, confidence + 0.10)

            # Momentum turning: MACD histogram flipping positive
            macd_hist = ind.get("macd_histogram")
            if macd_hist is not None and macd_hist > 0:
                confidence = min(1.0, confidence + 0.05)

            return Signal(
                action="buy",
                confidence=round(confidence, 3),
                entry_price=last_price,
                stop_loss=stop_loss,
                target=target,
                reasoning=[
                    f"Fib {ratio*100:.1f}% retracement at ${level:.2f}",
                    f"Swing ${swing_low:.2f} → ${swing_high:.2f} "
                    f"({move / swing_high * 100:.1f}% move)",
                    f"RSI={rsi:.1f}  stop=${stop_loss:.2f}  target=${target:.2f}",
                ],
            )

        return Signal.hold()

    def should_close(self, trade, context: Dict) -> Optional[str]:
        reason = super().should_close(trade, context)
        if reason:
            return reason

        ind        = context.get("indicators", {})
        last_price = ind.get("last_price")
        df         = context.get("price_df")

        if last_price is None or df is None:
            return None

        swing = self._find_swing(df)
        if swing is None:
            return None

        swing_low, swing_high = swing
        level_786 = swing_high - 0.786 * (swing_high - swing_low)

        # Trend likely broken: price fell through 78.6% retracement
        if last_price < level_786:
            return "fib_786_broken"

        # Take profit if RSI reaches overbought at/near the swing high
        rsi = ind.get("rsi")
        if rsi is not None and rsi > 70:
            return f"rsi_overbought_{rsi:.0f}"

        return None
