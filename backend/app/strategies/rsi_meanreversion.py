"""RSI Mean-Reversion: buy oversold (RSI<30), sell overbought (RSI>70)."""
from typing import Dict
from app.strategies.base import BaseStrategy, Signal


class RSIMeanReversionStrategy(BaseStrategy):
    name = "rsi_meanreversion"
    description = "Buy when RSI < 30 (oversold), close at RSI > 60 or stop-loss/target."

    max_positions = 2
    RSI_BUY_THRESHOLD = 30
    RSI_EXIT_THRESHOLD = 60
    STOP_LOSS_ATR_MULT = 2.0
    TARGET_ATR_MULT = 3.0

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        ind = context.get("indicators", {})
        rsi = ind.get("rsi")
        last_price = ind.get("last_price")
        atr = ind.get("atr")

        if rsi is None or last_price is None or atr is None:
            return Signal.hold()

        # Already in a position? Don't add.
        if context.get("current_position"):
            return Signal.hold()

        if rsi < self.RSI_BUY_THRESHOLD:
            stop_loss = round(last_price - atr * self.STOP_LOSS_ATR_MULT, 2)
            target = round(last_price + atr * self.TARGET_ATR_MULT, 2)
            confidence = min(1.0, (self.RSI_BUY_THRESHOLD - rsi) / 30 + 0.5)
            return Signal(
                action="buy",
                confidence=round(confidence, 3),
                entry_price=last_price,
                stop_loss=stop_loss,
                target=target,
                reasoning=[f"RSI={rsi:.1f} oversold (<{self.RSI_BUY_THRESHOLD})"],
                qty=1.0,
            )

        return Signal.hold()

    def should_close(self, trade, context: Dict):
        # Default stop/target check first
        reason = super().should_close(trade, context)
        if reason:
            return reason

        # Also exit if RSI returns to neutral/overbought
        rsi = context.get("indicators", {}).get("rsi")
        if rsi is not None and rsi > self.RSI_EXIT_THRESHOLD:
            return f"rsi_exit_{rsi:.0f}"
        return None
