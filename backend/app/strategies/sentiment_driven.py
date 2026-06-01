"""Sentiment-Driven: buy when Reddit sentiment surges with high mention velocity."""
from typing import Dict
from app.strategies.base import BaseStrategy, Signal


class SentimentDrivenStrategy(BaseStrategy):
    name = "sentiment_driven"
    description = "Buy on positive sentiment surge (FinBERT score > 0.4) with high mention activity."

    max_positions = 2
    MIN_AVG_SENTIMENT = 0.4
    MIN_MENTIONS_24H = 5
    STOP_LOSS_ATR_MULT = 2.0
    TARGET_ATR_MULT = 4.0

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        ind = context.get("indicators", {})
        sent = context.get("sentiment", {})
        last_price = ind.get("last_price")
        atr = ind.get("atr")

        if last_price is None or atr is None:
            return Signal.hold()
        if context.get("current_position"):
            return Signal.hold()

        avg_sent = sent.get("avg_sentiment", 0.0)
        mentions = sent.get("mention_count", 0)
        velocity = sent.get("mention_velocity", 0.0)

        if avg_sent < self.MIN_AVG_SENTIMENT or mentions < self.MIN_MENTIONS_24H:
            return Signal.hold()

        # Confidence scales with sentiment strength + activity
        confidence = min(1.0, avg_sent * 0.6 + min(velocity / 10.0, 0.4))

        stop_loss = round(last_price - atr * self.STOP_LOSS_ATR_MULT, 2)
        target = round(last_price + atr * self.TARGET_ATR_MULT, 2)
        return Signal(
            action="buy",
            confidence=round(confidence, 3),
            entry_price=last_price,
            stop_loss=stop_loss,
            target=target,
            reasoning=[
                f"Sentiment {avg_sent:+.2f}",
                f"{mentions} mentions/24h",
                f"velocity {velocity:.1f}/hr",
            ],
        )

    def should_close(self, trade, context: Dict):
        reason = super().should_close(trade, context)
        if reason:
            return reason

        # Exit if sentiment turns negative
        avg_sent = context.get("sentiment", {}).get("avg_sentiment", 0.0)
        if avg_sent < -0.2:
            return f"sentiment_flip_{avg_sent:.2f}"
        return None
