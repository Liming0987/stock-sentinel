"""Trading strategy framework.

Each strategy is a class inheriting from BaseStrategy. The strategy runner
iterates a universe of tickers, asks each strategy to evaluate, and opens
or closes paper trades accordingly.
"""
from app.strategies.base import BaseStrategy, Signal
# Swing strategies (daily bars, multi-day holds) live in strategies/swing/;
# intraday strategies (5-min bars, same-day) live in strategies/intraday/.
from app.strategies.swing.rsi_meanreversion import RSIMeanReversionStrategy
from app.strategies.swing.momentum import MomentumStrategy
from app.strategies.swing.bb_breakout import BBBreakoutStrategy
from app.strategies.swing.macd_histogram import MACDHistogramStrategy
from app.strategies.intraday.opening_range_breakout import OpeningRangeBreakoutStrategy
from app.strategies.intraday.vwap_cross import VWAPCrossStrategy
from app.strategies.swing.fib_retracement import FibRetracementStrategy
from app.strategies.swing.elliott_fib import ElliottFibStrategy
from app.strategies.swing.vcp import VCPStrategy

# Registry of available strategies. Add new ones here.
STRATEGY_REGISTRY = {
    "rsi_meanreversion": RSIMeanReversionStrategy,
    "momentum": MomentumStrategy,
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
    "BBBreakoutStrategy",
    "MACDHistogramStrategy",
    "OpeningRangeBreakoutStrategy",
    "VWAPCrossStrategy",
    "FibRetracementStrategy",
    "ElliottFibStrategy",
    "VCPStrategy",
]
