"""Trading strategy framework.

Each strategy is a class inheriting from BaseStrategy. The strategy runner
iterates a universe of tickers, asks each strategy to evaluate, and opens
or closes paper trades accordingly.
"""
from app.strategies.base import BaseStrategy, Signal
from app.strategies.rsi_meanreversion import RSIMeanReversionStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.sentiment_driven import SentimentDrivenStrategy
from app.strategies.bb_breakout import BBBreakoutStrategy
from app.strategies.macd_histogram import MACDHistogramStrategy
from app.strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
from app.strategies.vwap_cross import VWAPCrossStrategy
from app.strategies.fib_retracement import FibRetracementStrategy
from app.strategies.elliott_fib import ElliottFibStrategy
from app.strategies.vcp import VCPStrategy

# Registry of available strategies. Add new ones here.
STRATEGY_REGISTRY = {
    "rsi_meanreversion": RSIMeanReversionStrategy,
    "momentum": MomentumStrategy,
    "sentiment_driven": SentimentDrivenStrategy,
    "bb_breakout": BBBreakoutStrategy,
    "macd_histogram": MACDHistogramStrategy,
    "opening_range_breakout": OpeningRangeBreakoutStrategy,
    "vwap_cross": VWAPCrossStrategy,
    "fib_retracement": FibRetracementStrategy,
    "elliott_fib": ElliottFibStrategy,
    "vcp": VCPStrategy,
}

__all__ = [
    "BaseStrategy",
    "Signal",
    "STRATEGY_REGISTRY",
    "RSIMeanReversionStrategy",
    "MomentumStrategy",
    "SentimentDrivenStrategy",
    "BBBreakoutStrategy",
    "MACDHistogramStrategy",
    "OpeningRangeBreakoutStrategy",
    "VWAPCrossStrategy",
    "FibRetracementStrategy",
    "ElliottFibStrategy",
    "VCPStrategy",
]
