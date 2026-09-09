"""Base strategy interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict


@dataclass
class Signal:
    """Output of a strategy.evaluate() call."""
    action: str  # "buy", "sell", "hold"
    confidence: float = 0.0  # 0..1
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    reasoning: List[str] = field(default_factory=list)

    @classmethod
    def hold(cls) -> "Signal":
        return cls(action="hold")


class BaseStrategy(ABC):
    """Abstract base for all trading strategies."""

    # Subclasses override these
    name: str = "base"
    description: str = ""
    max_positions: int = 2  # max concurrent open trades across the whole universe
    FUNDAMENTAL_WEIGHT: float = 0.30
    requires_intraday: bool = False  # True for strategies that need 5-min bars (ORB, VWAP)
    MAX_HOLDING_DAYS: int = 60  # time-based failsafe: force-close a live trade older than this

    @abstractmethod
    def evaluate(self, ticker: str, context: Dict) -> Signal:
        """
        Evaluate a single ticker and return a Signal.

        Args:
            ticker: Stock symbol
            context: Dict with keys:
                - "price_df": pandas DataFrame of OHLCV
                - "indicators": dict from PriceService.compute_indicators
                - "current_position": Trade row if open, else None
        """
        ...

    def apply_fundamental_modifier(self, signal: Signal, context: Dict) -> Signal:
        if signal.action != "buy":
            return signal
        fundamentals = context.get("fundamentals")
        if not fundamentals:
            return signal
        score = fundamentals.get("score")
        if score is None:
            return signal
        grade = fundamentals.get("grade", "N/A")
        flags = fundamentals.get("flags", [])

        if flags and score < 0.35:
            signal.action = "hold"
            signal.reasoning.append(f"Fundamental veto: {flags[0]}")
            return signal

        mult = 1 + self.FUNDAMENTAL_WEIGHT * (score - 0.5) * 2
        signal.confidence = round(min(1.0, max(0.0, signal.confidence * mult)), 3)
        signal.reasoning.append(f"Fundamentals {grade} ({score:.0%}) ×{mult:.2f}")
        return signal

    def apply_exit_overrides(self, signal: Signal) -> Signal:
        """Optionally replace stop_loss/target with fixed-percentage levels around the
        entry price when settings.exit_mode == 'percent'
        (target = entry × (1 + target_pct), stop = entry × (1 - stop_pct)).

        Applies to swing strategies only — intraday scalps (ORB/VWAP) keep their native
        stops/targets, since a ±5% band is too wide for a same-day trade. The default
        'atr' mode leaves every strategy's own ATR/structure-based levels untouched.
        Applied centrally by the runner/backtester to every buy signal.
        """
        from app.config import settings
        if signal.action != "buy" or not signal.entry_price:
            return signal
        if self.requires_intraday:
            return signal  # intraday scalps keep their native ORB/VWAP stops & targets
        if getattr(settings, "exit_mode", "atr") != "percent":
            return signal
        entry = float(signal.entry_price)
        signal.stop_loss = round(entry * (1 - settings.stop_pct), 2)
        signal.target = round(entry * (1 + settings.target_pct), 2)
        signal.reasoning.append(
            f"Exit %-mode: target +{settings.target_pct:.0%} / stop -{settings.stop_pct:.0%}"
        )
        return signal

    def should_close(self, trade, context: Dict) -> Optional[str]:
        """
        Decide whether to close an open trade.

        Returns:
            None to keep open, or a reason string to close.
        """
        # Time-based failsafe: never hold a live position longer than MAX_HOLDING_DAYS.
        # Backstops indicator-only exits that might never trigger. Checked first so it
        # fires even when last_price is unavailable. Skipped when opened_at is absent
        # (e.g. backtest mock trades) so it can't misfire on historical replays.
        opened_at = getattr(trade, "opened_at", None)
        if self.MAX_HOLDING_DAYS and opened_at is not None:
            if opened_at.tzinfo is None:
                opened_at = opened_at.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - opened_at).days >= self.MAX_HOLDING_DAYS:
                return f"max_holding_{self.MAX_HOLDING_DAYS}d"

        last_price = context.get("indicators", {}).get("last_price")
        if last_price is None:
            return None

        # Default: stop-loss / target hit
        if trade.stop_loss and float(last_price) <= float(trade.stop_loss):
            return "stop_loss_hit"
        if trade.target and float(last_price) >= float(trade.target):
            return "target_hit"
        return None
