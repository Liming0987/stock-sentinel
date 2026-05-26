"""Trading strategy framework.

Each strategy is a class inheriting from BaseStrategy. The strategy runner
iterates a universe of tickers, asks each strategy to evaluate, and opens
or closes paper trades accordingly.
"""
from app.strategies.base import BaseStrategy, Signal
from app.strategies.rsi_meanreversion import RSIMeanReversionStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.sentiment_driven import SentimentDrivenStrategy

# Registry of available strategies. Add new ones here.
STRATEGY_REGISTRY = {
    "rsi_meanreversion": RSIMeanReversionStrategy,
    "momentum": MomentumStrategy,
    "sentiment_driven": SentimentDrivenStrategy,
}

__all__ = [
    "BaseStrategy",
    "Signal",
    "STRATEGY_REGISTRY",
    "RSIMeanReversionStrategy",
    "MomentumStrategy",
    "SentimentDrivenStrategy",
]
