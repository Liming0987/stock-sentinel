"""VCP (Volatility Contraction Pattern) — Minervini-style pivot breakout strategy.

Entry  : price breaks above pivot (high of last contraction) with ≥40% volume surge
Stop   : 7–8% below entry OR just under last contraction low — whichever is tighter
Target : 2.5× risk above entry
Filter : skip if broader market is in downtrend (EMA-50 below EMA-200 on SPY, handled
         by market filter in strategy runner) or if fundamental score is poor
"""
from typing import Dict

from app.strategies.base import BaseStrategy, Signal
from app.services.vcp_service import detect_vcp

_STOP_PCT = 0.08
_TARGET_MULT = 2.5
_MIN_VOL_RATIO = 1.40   # 40%+ above average volume on breakout day


class VCPStrategy(BaseStrategy):
    name = "vcp"
    description = (
        "Volatility Contraction Pattern: enter on a volume-confirmed pivot breakout "
        "after 2–4 contracting pullbacks in a Stage 2 uptrend."
    )
    max_positions = 3
    requires_intraday = False

    def evaluate(self, ticker: str, context: Dict) -> Signal:
        df = context.get("price_df")
        ind = context.get("indicators", {})
        current_position = context.get("current_position")

        if df is None or len(df) < 40:
            return Signal.hold()

        vcp = detect_vcp(df)

        # ── Manage open position ──────────────────────────────────────────────
        if current_position:
            last_price = float(df["Close"].iloc[-1])
            entry = float(current_position.entry_price or 0)
            target_price = float(current_position.target or 0)

            if entry > 0 and last_price <= entry * (1 - _STOP_PCT):
                return Signal(
                    action="sell",
                    confidence=0.95,
                    entry_price=last_price,
                    reasoning=["VCP stop: price down 8%+ from entry"],
                )
            if target_price > 0 and last_price >= target_price:
                return Signal(
                    action="sell",
                    confidence=0.80,
                    entry_price=last_price,
                    reasoning=["VCP target reached"],
                )
            return Signal.hold()

        # ── No position — look for entry ──────────────────────────────────────
        # Stage 2 uptrend is a hard requirement per Minervini — no stage 2, no trade.
        if not vcp["detected"] or not vcp["stage2"] or vcp["pivot"] is None:
            return Signal.hold()

        last_price = float(df["Close"].iloc[-1])
        pivot = float(vcp["pivot"])
        vol_ratio = float(ind.get("volume_ratio") or 0)
        contractions = vcp["contractions"]

        breaking_out = last_price > pivot and vol_ratio >= _MIN_VOL_RATIO

        if not breaking_out:
            return Signal.hold()

        n_c = len(contractions)
        vol_dry_n = sum(1 for c in contractions if c["vol_dry"])

        # Confidence: base 0.45 + bonuses
        conf = 0.45
        conf += 0.05 * n_c                           # +0.05 per contraction (max +0.20)
        if vol_dry_n >= n_c - 1:
            conf += 0.15                             # most lows had quiet volume
        if vol_ratio >= 1.5:
            conf += 0.10
        if vcp["stage2"]:
            conf += 0.10
        conf = max(0.30, min(0.92, conf))

        entry_price = last_price
        # Tighter of 8% stop or just under last contraction low
        contraction_stop = contractions[-1]["low"] * 0.99
        pct_stop = entry_price * (1 - _STOP_PCT)
        stop_loss = max(contraction_stop, pct_stop)   # max = tighter (higher price)
        risk = entry_price - stop_loss
        target = entry_price + risk * _TARGET_MULT

        reasoning = [
            f"VCP: {n_c} contractions ({' → '.join(str(c['depth_pct'])+'%' for c in contractions)})",
            f"Pivot ${pivot:.2f}",
            f"Volume dry in {vol_dry_n}/{n_c} pullbacks",
        ]
        reasoning.append(f"Breaking out — volume {vol_ratio:.1f}×")
        if vcp["stage2"]:
            reasoning.append("Stage 2 uptrend confirmed")

        signal = Signal(
            action="buy",
            confidence=conf,
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            target=round(target, 2),
            reasoning=reasoning,
        )
        return self.apply_fundamental_modifier(signal, context)
