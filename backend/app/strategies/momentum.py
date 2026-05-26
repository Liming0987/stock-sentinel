"""Momentum: buy when price > 50-EMA > 200-EMA AND MACD bullish AND volume confirmation."""
from typing import Dict
from app.strategies.base import BaseStrategy, Signal


class MomentumStrategy(BaseStrategy):
    name = "momentum"
    description = "Trend-following: enter on bullish MACD + price above 50/200-EMA + volume."

    STOP_LOSS_ATR_MULT = 2.5
    TARGET_ATR_MULT = 5.0
    MIN_VOL_RATIO = 1.2

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        ind = context.get("indicators", {})
        last_price = ind.get("last_price")
        ema_50 = ind.get("ema_50")
        ema_200 = ind.get("ema_200")
        macd = ind.get("macd")
        macd_sig = ind.get("macd_signal")
        atr = ind.get("atr")
        vol_ratio = ind.get("volume_ratio", 0)

        if not all(v is not None for v in (last_price, ema_50, macd, macd_sig, atr)):
            return Signal.hold()

        if context.get("current_position"):
            return Signal.hold()

        bullish_trend = last_price > ema_50 and (ema_200 is None or ema_50 > ema_200)
        bullish_macd = macd > macd_sig and macd > 0
        volume_ok = vol_ratio >= self.MIN_VOL_RATIO

        score = 0.0
        reasoning = []
        if bullish_trend:
            score += 0.4
            reasoning.append("Price above 50-EMA")
        if bullish_macd:
            score += 0.4
            reasoning.append(f"MACD bullish ({macd:.3f}>{macd_sig:.3f})")
        if volume_ok:
            score += 0.2
            reasoning.append(f"Volume {vol_ratio:.1f}x avg")

        if score < 0.6:
            return Signal.hold()

        stop_loss = round(last_price - atr * self.STOP_LOSS_ATR_MULT, 2)
        target = round(last_price + atr * self.TARGET_ATR_MULT, 2)
        return Signal(
            action="buy",
            confidence=round(score, 3),
            entry_price=last_price,
            stop_loss=stop_loss,
            target=target,
            reasoning=reasoning,
            qty=1.0,
        )

    def should_close(self, trade, context: Dict):
        reason = super().should_close(trade, context)
        if reason:
            return reason

        # Exit if MACD turns bearish
        ind = context.get("indicators", {})
        macd, sig = ind.get("macd"), ind.get("macd_signal")
        if macd is not None and sig is not None and macd < sig and macd < 0:
            return "macd_bearish_exit"
        return None
