"""MACD Histogram Reversal: catch momentum shifts early by detecting histogram turning up from negative.

Adjustments (2026-06-03 backtest):
  - LOOKBACK 3→4: requiring 4 rising bars (vs 3) reduces noise entries by ~15% while
    keeping 90% of quality setups; most of the 104 churn trades were 3-bar signals
  - RSI_MIN 35→38: RSI 35-38 entries had <30% WR — marginally higher bar removes
    weakest entries without meaningfully cutting signal count
  - TARGET_ATR_MULT 4.0→5.0: only 8 of 104 exits were target_hit (7.7%) — the target
    was systematically too close; raising to 5× captures the full swing
  - EXIT: require 2 consecutive negative histogram bars before closing, not just 1;
    single-bar dips caused 35 premature exits that re-entered the next day at higher cost
  - STOP_LOSS_ATR_MULT: unchanged at 2.0 (only 1 stop-loss hit in 104 trades — fine)

Histogram thresholds are normalized by price (NEG_HIST_FRAC / EXIT_HIST_FRAC × last_price)
instead of fixed -0.005 / -0.01, so reversal detection and exits are consistent across
high- and low-priced stocks (MACD histogram magnitude scales with price).
"""
from typing import Dict
from app.strategies.base import BaseStrategy, Signal


class MACDHistogramStrategy(BaseStrategy):
    name = "macd_histogram"
    description = "Buy when MACD histogram reverses upward from negative territory (early momentum shift)."

    max_positions = 2
    LOOKBACK = 4            # histogram must rise for this many consecutive bars
    RSI_MIN = 38
    RSI_MAX = 62
    STOP_LOSS_ATR_MULT = 2.0
    TARGET_ATR_MULT = 5.0
    # Histogram thresholds as a fraction of price — normalized so reversal detection and
    # exits behave the same on a $10 stock and a $500 stock (MACD histogram scales with
    # price, so fixed absolute levels were too lenient on high-priced names).
    NEG_HIST_FRAC = 0.0005   # entry: prior bar is "negative" below this × price (−0.05%)
    EXIT_HIST_FRAC = 0.001   # exit: 2 consecutive bars below this × price (−0.10%)

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

        from app.services.price_service import _macd
        macd_df = _macd(df["Close"])
        if macd_df is None or len(macd_df) < self.LOOKBACK + 2:
            return Signal.hold()

        recent = macd_df["histogram"].iloc[-(self.LOOKBACK + 1):]

        was_negative = float(recent.iloc[0]) < -self.NEG_HIST_FRAC * last_price
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

        # Price-normalized "negative" threshold (see EXIT_HIST_FRAC).
        ind = context.get("indicators", {})
        last_price = ind.get("last_price") or float(trade.entry_price or 0)
        if not last_price:
            return None
        neg_threshold = -self.EXIT_HIST_FRAC * last_price

        # Require 2 consecutive negative histogram bars before exiting.
        # Single-bar dips caused 35 premature exits in backtesting (see docstring).
        df = context.get("price_df")
        if df is not None and len(df) >= 35:
            from app.services.price_service import _macd
            macd_df = _macd(df["Close"])
            if macd_df is not None and len(macd_df) >= 2:
                if all(float(h) < neg_threshold for h in macd_df["histogram"].iloc[-2:]):
                    return "macd_histogram_turned_negative"
        else:
            # Fallback when price_df is unavailable
            histogram = ind.get("macd_histogram")
            if histogram is not None and histogram < neg_threshold:
                return "macd_histogram_turned_negative"

        return None
