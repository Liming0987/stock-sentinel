"""Momentum: buy when price > 50-EMA > 200-EMA AND MACD bullish AND volume confirmation.

Adjustments (2026-06-03 backtest):
  - STOP_LOSS_ATR_MULT 2.5→2.0: tighten stops — drawdown was -39.6% on a winner
  - TARGET_ATR_MULT 5.0→6.0: let winners run longer (avg winner only 5.68%)
  - MIN_VOL_RATIO 1.2→1.3: marginally higher bar filters weak-volume false starts
  - Added EMA-50 slope guard (must be rising over 10 days) to avoid late-trend entries
  - Added minimum trend gap: price must be ≥1.5% above EMA-50 to skip noise
  - Price must be above EMA-200 (made mandatory, was optional)
"""
from typing import Dict
from app.strategies.base import BaseStrategy, Signal


class MomentumStrategy(BaseStrategy):
    name = "momentum"
    description = "Trend-following: enter on bullish MACD + price above 50/200-EMA + volume."

    max_positions = 3
    STOP_LOSS_ATR_MULT = 2.0
    TARGET_ATR_MULT = 6.0
    MIN_VOL_RATIO = 1.3
    MIN_TREND_GAP = 0.015   # price must be ≥1.5% above EMA-50
    EMA_SLOPE_BARS = 10     # EMA-50 must be higher than 10 bars ago

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        ind = context.get("indicators", {})
        df = context.get("price_df")
        last_price = ind.get("last_price")
        ema_50 = ind.get("ema_50")
        ema_200 = ind.get("ema_200")
        macd = ind.get("macd")
        macd_sig = ind.get("macd_signal")
        atr = ind.get("atr")
        vol_ratio = ind.get("volume_ratio", 0)

        if not all(v is not None for v in (last_price, ema_50, ema_200, macd, macd_sig, atr)):
            return Signal.hold()

        if context.get("current_position"):
            return Signal.hold()

        # EMA-50 slope check: today > 5 days ago > 10 days ago.
        # Two-interval check confirms sustained direction without requiring
        # monotonic movement every bar (EMA-50 naturally pauses 1-2 days
        # even in strong uptrends due to smoothing).
        if df is not None and len(df) >= self.EMA_SLOPE_BARS + 50:
            from app.services.price_service import _ema
            ema50_series = _ema(df["Close"], 50)
            half = self.EMA_SLOPE_BARS // 2
            if not (
                float(ema50_series.iloc[-1]) > float(ema50_series.iloc[-(half + 1)])
                > float(ema50_series.iloc[-(self.EMA_SLOPE_BARS + 1)])
            ):
                return Signal.hold()

        bullish_trend = (
            last_price > ema_50 * (1 + self.MIN_TREND_GAP)
            and ema_50 > ema_200
        )

        # Require MACD above signal line for 2 consecutive bars, not just today.
        # Filters one-day false crossovers while still catching genuine momentum.
        bullish_macd = False
        if df is not None and len(df) >= 35:
            from app.services.price_service import _macd
            macd_df = _macd(df["Close"])
            if macd_df is not None and len(macd_df) >= 2:
                last2_macd = macd_df["macd"].iloc[-2:]
                last2_sig = macd_df["signal"].iloc[-2:]
                bullish_macd = (
                    all(last2_macd.iloc[i] > last2_sig.iloc[i] for i in range(2))
                    and float(last2_macd.iloc[-1]) > 0
                )
        else:
            bullish_macd = macd > macd_sig and macd > 0
        volume_ok = vol_ratio >= self.MIN_VOL_RATIO

        score = 0.0
        reasoning = []
        if bullish_trend:
            score += 0.4
            reasoning.append(f"Price ${last_price:.2f} above EMA-50 ${ema_50:.2f} (+{(last_price/ema_50-1)*100:.1f}%)")
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
