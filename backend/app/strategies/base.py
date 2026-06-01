"""Base strategy interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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

    @abstractmethod
    def evaluate(self, ticker: str, context: Dict) -> Signal:
        """
        Evaluate a single ticker and return a Signal.

        Args:
            ticker: Stock symbol
            context: Dict with keys:
                - "price_df": pandas DataFrame of OHLCV
                - "indicators": dict from PriceService.compute_indicators
                - "sentiment": dict with avg_sentiment, mention_count, velocity
                - "current_position": Trade row if open, else None
        """
        ...

    def should_close(self, trade, context: Dict) -> Optional[str]:
        """
        Decide whether to close an open trade.

        Returns:
            None to keep open, or a reason string to close.
        """
        last_price = context.get("indicators", {}).get("last_price")
        if last_price is None:
            return None

        # Default: stop-loss / target hit
        if trade.stop_loss and float(last_price) <= float(trade.stop_loss):
            return "stop_loss_hit"
        if trade.target and float(last_price) >= float(trade.target):
            return "target_hit"
        return None
