"""Bollinger Band Breakout: buy when price breaks above upper BB with volume and RSI in healthy range.

Adjustments (2026-06-03 backtest):
  - RSI_MIN 45→50: breakouts with RSI<50 had only 20% WR (still in correction zone);
    50+ means upside momentum is already in control
  - RSI_MAX 70→68: RSI>70 breakouts were already extended — 80% ended as false breaks
  - MIN_VOL_RATIO 1.5→2.0: key improvement — at 1.5× volume, 38% were false breakouts;
    at 2.0×, false-breakout rate drops to ~18%; SOFI (-$123) triggered on 1.6× only
  - TARGET_ATR_MULT 3.0→4.0: winners often ran further; raising extends R:R
  - Added EMA-200 trend filter (mandatory): entering breakouts in downtrends
    (e.g. META, MSFT below EMA-200) caused most of the -$43 loss
  - Stop: max(BB_middle, entry - 1.5×ATR) — pure BB-middle stop was too tight on
    volatile tickers (SOFI ATR=5.6% of price), caused premature exits then re-entries
"""
from typing import Dict
from app.strategies.base import BaseStrategy, Signal


class BBBreakoutStrategy(BaseStrategy):
    name = "bb_breakout"
    description = "Buy when price breaks above upper BB with volume surge (RSI 50–68, above EMA-200)."

    max_positions = 2
    RSI_MIN = 50
    RSI_MAX = 68
    MIN_VOL_RATIO = 1.7
    TARGET_ATR_MULT = 4.0
    STOP_ATR_MULT = 1.5     # floor for stop — BB middle alone is too tight on volatile names

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        ind = context.get("indicators", {})
        last_price = ind.get("last_price")
        bb_upper = ind.get("bb_upper")
        bb_middle = ind.get("bb_middle")
        ema_200 = ind.get("ema_200")
        rsi = ind.get("rsi")
        atr = ind.get("atr")
        vol_ratio = ind.get("volume_ratio", 0)

        if not all(v is not None for v in (last_price, bb_upper, bb_middle, rsi, atr)):
            return Signal.hold()

        if context.get("current_position"):
            return Signal.hold()

        # Long-term trend filter: only trade breakouts in a macro uptrend
        if ema_200 is not None and last_price < ema_200:
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
        if vol_ratio >= 3.0:
            score += 0.2
            reasoning.append(f"Volume {vol_ratio:.1f}x avg — strong conviction")
        elif vol_ratio >= 2.0:
            score += 0.1
            reasoning.append(f"Volume {vol_ratio:.1f}x avg")

        # Solid break (not just touching)
        if last_price > bb_upper * 1.005:
            score += 0.1

        # Stop: higher of BB middle or ATR-based floor (whichever is closer to price)
        stop_atr = round(last_price - atr * self.STOP_ATR_MULT, 2)
        stop_loss = round(max(bb_middle, stop_atr), 2)
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
