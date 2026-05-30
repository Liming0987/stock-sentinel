"""VWAP Cross: buy when price crosses above intraday VWAP with momentum confirmation."""
from typing import Dict
from app.strategies.base import BaseStrategy, Signal


class VWAPCrossStrategy(BaseStrategy):
    name = "vwap_cross"
    description = "Intraday: buy when price crosses above VWAP with volume and daily-trend confirmation."

    max_positions = 2
    MIN_BARS = 6        # at least 30 min for VWAP to be meaningful
    EOD_BAR = 72        # don't open new positions after 3:30 PM (72/78 bars)
    MIN_VOL_RATIO = 1.5

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        intraday = context.get("intraday") or {}
        if not intraday:
            return Signal.hold()

        if context.get("current_position"):
            return Signal.hold()

        vwap = intraday.get("vwap")
        current_price = intraday.get("current_price")
        prev_close = intraday.get("prev_bar_close")
        bars_elapsed = intraday.get("bars_elapsed", 0)
        vol_ratio = intraday.get("intraday_volume_ratio", 0)
        intraday_atr = intraday.get("intraday_atr")

        if not all(v is not None for v in (vwap, current_price, prev_close, intraday_atr)):
            return Signal.hold()

        if bars_elapsed < self.MIN_BARS or bars_elapsed >= self.EOD_BAR:
            return Signal.hold()

        # Cross: previous bar was below VWAP, current bar is above
        crossed_above = prev_close < vwap <= current_price
        if not crossed_above:
            return Signal.hold()

        if vol_ratio < self.MIN_VOL_RATIO:
            return Signal.hold()

        score = 0.5
        reasoning = [f"Price ${current_price:.2f} crossed above VWAP ${vwap:.2f}"]

        if vol_ratio >= 2.0:
            score += 0.2
            reasoning.append(f"Volume {vol_ratio:.1f}x avg")
        elif vol_ratio >= 1.5:
            score += 0.1
            reasoning.append(f"Volume {vol_ratio:.1f}x avg")

        # Bonus: daily trend aligned (price above 50-EMA)
        ind = context.get("indicators", {})
        ema_50 = ind.get("ema_50")
        daily_price = ind.get("last_price")
        if ema_50 and daily_price and daily_price > ema_50:
            score += 0.2
            reasoning.append("Daily trend bullish (above 50-EMA)")

        # Bonus: MACD on daily bullish
        if ind.get("macd", 0) > ind.get("macd_signal", 0):
            score += 0.1

        # Stop just below VWAP; target 2:1 R:R using intraday ATR
        stop_loss = round(vwap - intraday_atr * 0.5, 2)
        target = round(current_price + (current_price - stop_loss) * 2.0, 2)

        return Signal(
            action="buy",
            confidence=round(min(score, 1.0), 3),
            entry_price=current_price,
            stop_loss=stop_loss,
            target=target,
            reasoning=reasoning,
        )

    def should_close(self, trade, context: Dict):
        reason = super().should_close(trade, context)
        if reason:
            return reason

        intraday = context.get("intraday") or {}
        if not intraday:
            return None

        if intraday.get("bars_elapsed", 0) >= 78:
            return "end_of_day"

        current_price = intraday.get("current_price")
        vwap = intraday.get("vwap")
        if current_price and vwap and current_price < vwap * 0.999:
            return "price_dropped_below_vwap"

        return None
