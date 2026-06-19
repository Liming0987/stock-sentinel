"""Opening Range Breakout (ORB): buy when price breaks above the first-30-min high with volume."""
from datetime import datetime, time as dt_time
from typing import Dict, Optional
from app.strategies.base import BaseStrategy, Signal


class OpeningRangeBreakoutStrategy(BaseStrategy):
    name = "opening_range_breakout"
    description = "Intraday: buy breakout above the first 30-min high with volume surge. EOD close."

    max_positions = 2
    requires_intraday = True
    ORB_BARS = 6            # 6 × 5 min = 30 min opening range
    ENTRY_WINDOW_BARS = 12  # only enter within 60 min after ORB forms
    MIN_VOL_RATIO = 2.0
    STOP_LOSS_ATR_MULT = 1.5

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        intraday = context.get("intraday") or {}
        if not intraday:
            return Signal.hold()

        if context.get("current_position"):
            return Signal.hold()

        orb_high = intraday.get("orb_high")
        orb_low = intraday.get("orb_low")
        current_price = intraday.get("current_price")
        bars_elapsed = intraday.get("bars_elapsed", 0)
        vol_ratio = intraday.get("intraday_volume_ratio", 0)
        intraday_atr = intraday.get("intraday_atr")

        if not all(v is not None for v in (orb_high, orb_low, current_price, intraday_atr)):
            return Signal.hold()

        # Need full ORB before trading
        if bars_elapsed < self.ORB_BARS:
            return Signal.hold()

        # Entry window: ORB forms at bar 6, only enter up to bar 18 (60 min after)
        if bars_elapsed > self.ORB_BARS + self.ENTRY_WINDOW_BARS:
            return Signal.hold()

        if current_price <= orb_high:
            return Signal.hold()

        if vol_ratio < self.MIN_VOL_RATIO:
            return Signal.hold()

        orb_range = orb_high - orb_low
        # Stop at ORB midpoint; target at 2:1 R:R above entry
        stop_loss = round(orb_high - orb_range * 0.5, 2)
        risk = current_price - stop_loss
        target = round(current_price + risk * 2.0, 2)

        score = 0.6
        reasoning = [
            f"ORB breakout: ${current_price:.2f} > high ${orb_high:.2f}",
            f"Opening range ${orb_low:.2f}–${orb_high:.2f} ({orb_range:.2f} wide)",
        ]

        if vol_ratio >= 3.0:
            score += 0.2
            reasoning.append(f"Volume {vol_ratio:.1f}x avg — strong")
        elif vol_ratio >= 2.0:
            score += 0.1
            reasoning.append(f"Volume {vol_ratio:.1f}x avg")

        # Solid break, not just touching
        if current_price > orb_high * 1.005:
            score += 0.1
            reasoning.append("Clean break above ORB high")

        # Bonus: daily trend in same direction
        ind = context.get("indicators", {})
        if ind.get("macd", 0) > ind.get("macd_signal", 0):
            score += 0.1

        return Signal(
            action="buy",
            confidence=round(min(score, 1.0), 3),
            entry_price=current_price,
            stop_loss=stop_loss,
            target=target,
            reasoning=reasoning,
        )

    def should_close(self, trade, context: Dict) -> Optional[str]:
        reason = super().should_close(trade, context)
        if reason:
            return reason

        # Wall-clock EOD safety net: close any open ORB position after 3:45 ET
        # regardless of intraday context availability (e.g. when run_strategies
        # calls should_close after the intraday runner has stopped for the day).
        try:
            import pytz
            et = pytz.timezone("America/New_York")
            if datetime.now(et).time() >= dt_time(15, 45):
                return "end_of_day"
        except Exception:
            pass

        intraday = context.get("intraday") or {}
        if not intraday:
            return None

        # Force close at bar 75 (3:45 PM with 5-min bars)
        if intraday.get("bars_elapsed", 0) >= 75:
            return "end_of_day"

        current_price = intraday.get("current_price")
        orb_high = intraday.get("orb_high")
        if current_price and orb_high and current_price < orb_high * 0.998:
            return "failed_breakout_below_orb"

        return None
