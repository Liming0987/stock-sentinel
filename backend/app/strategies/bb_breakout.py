"""Bollinger Band Breakout: buy when price breaks above upper BB with volume and RSI in healthy range."""
from typing import Dict
from app.strategies.base import BaseStrategy, Signal


class BBBreakoutStrategy(BaseStrategy):
    name = "bb_breakout"
    description = "Buy when price breaks above upper Bollinger Band with volume surge (RSI 45–70)."

    max_positions = 2
    RSI_MIN = 45
    RSI_MAX = 70
    MIN_VOL_RATIO = 1.5
    TARGET_ATR_MULT = 3.0

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        ind = context.get("indicators", {})
        last_price = ind.get("last_price")
        bb_upper = ind.get("bb_upper")
        bb_middle = ind.get("bb_middle")
        rsi = ind.get("rsi")
        atr = ind.get("atr")
        vol_ratio = ind.get("volume_ratio", 0)

        if not all(v is not None for v in (last_price, bb_upper, bb_middle, rsi, atr)):
            return Signal.hold()

        if context.get("current_position"):
            return Signal.hold()

        if last_price <= bb_upper:
            return Signal.hold()
        if not (self.RSI_MIN <= rsi <= self.RSI_MAX):
            return Signal.hold()
        if vol_ratio < self.MIN_VOL_RATIO:
            return Signal.hold()

        score = 0.5
        reasoning = [f"Price ${last_price:.2f} broke BB upper ${bb_upper:.2f}"]

        if rsi >= 55:
            score += 0.2
            reasoning.append(f"RSI={rsi:.1f} bullish momentum")
        if vol_ratio >= 2.0:
            score += 0.2
            reasoning.append(f"Volume {vol_ratio:.1f}x avg")
        elif vol_ratio >= 1.5:
            score += 0.1
            reasoning.append(f"Volume {vol_ratio:.1f}x avg")

        # Solid break (not just touching)
        if last_price > bb_upper * 1.005:
            score += 0.1

        # Stop at BB middle; target using ATR from breakout point
        stop_loss = round(bb_middle, 2)
        target = round(last_price + atr * self.TARGET_ATR_MULT, 2)

        return Signal(
            action="buy",
            confidence=round(min(score, 1.0), 3),
            entry_price=last_price,
            stop_loss=stop_loss,
            target=target,
            reasoning=reasoning,
        )

    def should_close(self, trade, context: Dict):
        reason = super().should_close(trade, context)
        if reason:
            return reason

        ind = context.get("indicators", {})
        last_price = ind.get("last_price")
        bb_middle = ind.get("bb_middle")

        if last_price and bb_middle and last_price < bb_middle:
            return "price_below_bb_middle"

        return None
