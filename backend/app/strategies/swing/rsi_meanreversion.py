"""RSI Mean-Reversion: buy the bounce out of oversold, exit on recovery/stop/target.

Entry: RSI(14) crosses back ABOVE 30 (bounce confirmation — not the first dip below,
       which can keep falling) AND price is above the 200-EMA (skip oversold buys in a
       macro downtrend, the classic falling-knife failure mode).
Exit:  ATR-based stop/target, RSI recovers above 60, or the max-holding failsafe.

Regime note (Jun 2025 – Jun 2026 backtest, tech bull market): oversold dips are rare in
persistent uptrends, so this fires infrequently; it's designed for range-bound / choppy
markets where oversold bounces are reliable.
"""
from typing import Dict
from app.strategies.base import BaseStrategy, Signal


class RSIMeanReversionStrategy(BaseStrategy):
    name = "rsi_meanreversion"
    description = "Buy when RSI crosses back above 30 (oversold bounce) while above the 200-EMA; close at RSI > 60 or stop/target."

    max_positions = 2
    RSI_BUY_THRESHOLD = 30
    RSI_EXIT_THRESHOLD = 60
    STOP_LOSS_ATR_MULT = 2.0
    TARGET_ATR_MULT = 3.0
    TROUGH_LOOKBACK = 6     # bars to scan for the depth of the recent oversold dip

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        ind = context.get("indicators", {})
        df = context.get("price_df")
        last_price = ind.get("last_price")
        atr = ind.get("atr")
        ema_200 = ind.get("ema_200")

        if last_price is None or atr is None or df is None or len(df) < 20:
            return Signal.hold()

        # Already in a position? Don't add.
        if context.get("current_position"):
            return Signal.hold()

        # Downtrend guard: don't buy oversold in a macro downtrend (falling knives).
        if ema_200 is not None and last_price < ema_200:
            return Signal.hold()

        # Enter on RSI crossing back ABOVE the threshold (bounce confirmation), not on
        # the first dip below it — buying while RSI is still falling catches the knife.
        from app.services.price_service import _rsi
        rsi_series = _rsi(df["Close"], 14)
        if rsi_series is None or len(rsi_series) < 2:
            return Signal.hold()
        prev_rsi = float(rsi_series.iloc[-2])
        curr_rsi = float(rsi_series.iloc[-1])
        if not (prev_rsi < self.RSI_BUY_THRESHOLD <= curr_rsi):
            return Signal.hold()

        # Confidence scales with how deep the recent oversold dip reached — the deeper
        # the trough, the stronger the mean-reversion snap-back.
        trough_rsi = float(rsi_series.iloc[-self.TROUGH_LOOKBACK:].min())
        confidence = min(1.0, (self.RSI_BUY_THRESHOLD - trough_rsi) / self.RSI_BUY_THRESHOLD + 0.5)

        stop_loss = round(last_price - atr * self.STOP_LOSS_ATR_MULT, 2)
        target = round(last_price + atr * self.TARGET_ATR_MULT, 2)
        return Signal(
            action="buy",
            confidence=round(confidence, 3),
            entry_price=last_price,
            stop_loss=stop_loss,
            target=target,
            reasoning=[
                f"RSI crossed up through {self.RSI_BUY_THRESHOLD} "
                f"({prev_rsi:.1f}→{curr_rsi:.1f}); dip reached {trough_rsi:.1f}",
            ],
        )

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
