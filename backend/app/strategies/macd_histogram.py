"""MACD Histogram Reversal: catch momentum shifts early by detecting histogram turning up from negative."""
from typing import Dict
from app.strategies.base import BaseStrategy, Signal


class MACDHistogramStrategy(BaseStrategy):
    name = "macd_histogram"
    description = "Buy when MACD histogram reverses upward from negative territory (early momentum shift)."

    max_positions = 2
    LOOKBACK = 3        # histogram must rise for this many consecutive bars
    RSI_MIN = 35
    RSI_MAX = 62
    STOP_LOSS_ATR_MULT = 2.0
    TARGET_ATR_MULT = 4.0

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        ind = context.get("indicators", {})
        df = context.get("price_df")
        last_price = ind.get("last_price")
        rsi = ind.get("rsi")
        atr = ind.get("atr")

        if not all(v is not None for v in (last_price, rsi, atr)):
            return Signal.hold()

        if context.get("current_position"):
            return Signal.hold()

        if df is None or len(df) < 35:
            return Signal.hold()

        if not (self.RSI_MIN <= rsi <= self.RSI_MAX):
            return Signal.hold()

        # Compute MACD histogram from price history
        from app.services.price_service import _macd
        macd_df = _macd(df["Close"])
        if macd_df is None or len(macd_df) < self.LOOKBACK + 2:
            return Signal.hold()

        recent = macd_df["histogram"].iloc[-(self.LOOKBACK + 1):]

        # Must have started negative and been rising each bar
        was_negative = recent.iloc[0] < -0.005
        is_rising = all(
            recent.iloc[i] > recent.iloc[i - 1]
            for i in range(1, len(recent))
        )
        current_hist = float(recent.iloc[-1])

        if not (was_negative and is_rising):
            return Signal.hold()

        score = 0.45
        reasoning = [
            f"MACD histogram rising {recent.iloc[0]:.4f} → {current_hist:.4f}",
        ]

        if current_hist >= 0:
            score += 0.25
            reasoning.append("Histogram crossed above zero")
        if rsi >= 45:
            score += 0.15
            reasoning.append(f"RSI={rsi:.1f} recovering")
        if ind.get("volume_ratio", 0) >= 1.3:
            score += 0.1
            reasoning.append(f"Volume {ind.get('volume_ratio'):.1f}x avg")
        if ind.get("macd", 0) > ind.get("macd_signal", 0):
            score += 0.05

        stop_loss = round(last_price - atr * self.STOP_LOSS_ATR_MULT, 2)
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

        histogram = context.get("indicators", {}).get("macd_histogram")
        if histogram is not None and histogram < -0.01:
            return "macd_histogram_turned_negative"

        return None
