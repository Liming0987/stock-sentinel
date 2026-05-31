"""Backtest engine: replay a strategy against historical OHLCV data.

Deliberately isolated from Alpaca and the live DB — pure simulation.
Uses the same strategy.evaluate() / should_close() methods as the live
runner, so results reflect the real signal logic.

Design choices to avoid look-ahead bias:
  - Data up to day D (inclusive) is the only data visible when making a
    decision on day D.
  - Entry and exit prices are the closing price of the decision day.
  - Indicators require at least 50 bars of history before any signal is
    generated (same as live runtime minimum).
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from app.services.price_service import PriceService
from app.strategies import STRATEGY_REGISTRY, BaseStrategy

logger = logging.getLogger(__name__)

POSITION_SIZE_USD = 100.0
MIN_BARS = 50  # minimum history needed before evaluating signals


@dataclass
class BacktestTrade:
    ticker: str
    entry_date: str
    exit_date: Optional[str]
    entry_price: float
    exit_price: Optional[float]
    qty: float
    pnl: float
    return_pct: float
    exit_reason: str
    reasoning: str


@dataclass
class BacktestResult:
    strategy: str
    tickers: List[str]
    start_date: str
    end_date: str
    trades: List[BacktestTrade]
    equity_curve: List[Dict]   # [{date, equity}]
    metrics: Dict


class BacktestRunner:
    def __init__(self):
        self.price_service = PriceService()

    def run(
        self,
        strategy_name: str,
        tickers: List[str],
        start_date: date,
        end_date: date,
    ) -> BacktestResult:
        if strategy_name not in STRATEGY_REGISTRY:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        strat: BaseStrategy = STRATEGY_REGISTRY[strategy_name]()

        # Download historical data — fetch extra history before start_date
        # so indicators are warm on the first signal day.
        fetch_start = start_date - timedelta(days=MIN_BARS * 2)
        logger.info(f"Backtest: downloading {tickers} from {fetch_start} to {end_date}")

        raw = yf.download(
            tickers,
            start=fetch_start.isoformat(),
            end=(end_date + timedelta(days=1)).isoformat(),
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if raw.empty:
            raise ValueError("No price data returned for the selected tickers/period")

        multi = isinstance(raw.columns, pd.MultiIndex)
        ticker_dfs: Dict[str, pd.DataFrame] = {}
        for t in tickers:
            try:
                df = raw.xs(t, axis=1, level=1).dropna(how="all") if multi else raw.dropna(how="all")
                if len(df) >= MIN_BARS:
                    ticker_dfs[t] = df
            except Exception:
                logger.debug(f"Backtest: no data for {t}")

        if not ticker_dfs:
            raise ValueError("No usable price data — all tickers had insufficient history")

        # Trading days within the requested window
        trading_days = sorted([
            d for d in raw.index
            if start_date <= d.date() <= end_date
        ])

        trades: List[BacktestTrade] = []
        open_positions: Dict[str, Dict] = {}  # ticker → {entry_price, qty, entry_date, reasoning}
        cumulative_pnl = 0.0
        equity_curve = []

        for day in trading_days:
            day_pnl = 0.0

            # 1. Manage open positions first
            for ticker in list(open_positions.keys()):
                df = ticker_dfs.get(ticker)
                if df is None or day not in df.index:
                    continue
                df_so_far = df.loc[:day]
                if len(df_so_far) < MIN_BARS:
                    continue

                ind = self.price_service.compute_indicators(df_so_far)
                ctx = {
                    "price_df": df_so_far,
                    "indicators": ind,
                    "sentiment": {"avg_sentiment": 0.0, "mention_count": 0, "mention_velocity": 0.0},
                    "intraday": {},
                    "current_position": True,  # signal we have a position
                }
                reason = strat.should_close(open_positions[ticker]["mock_trade"], ctx)
                if reason:
                    pos = open_positions.pop(ticker)
                    exit_price = float(df_so_far["Close"].iloc[-1])
                    entry_price = pos["entry_price"]
                    qty = pos["qty"]
                    pnl = (exit_price - entry_price) * qty
                    ret = (exit_price - entry_price) / entry_price if entry_price else 0
                    day_pnl += pnl
                    trades.append(BacktestTrade(
                        ticker=ticker,
                        entry_date=pos["entry_date"],
                        exit_date=day.strftime("%Y-%m-%d"),
                        entry_price=round(entry_price, 4),
                        exit_price=round(exit_price, 4),
                        qty=round(qty, 6),
                        pnl=round(pnl, 2),
                        return_pct=round(ret, 4),
                        exit_reason=reason,
                        reasoning=pos["reasoning"],
                    ))

            # 2. Collect entry signals for tickers without an open position
            buy_candidates = []
            open_count = len(open_positions)
            for ticker, df in ticker_dfs.items():
                if ticker in open_positions:
                    continue
                if day not in df.index:
                    continue
                df_so_far = df.loc[:day]
                if len(df_so_far) < MIN_BARS:
                    continue

                ind = self.price_service.compute_indicators(df_so_far)
                ctx = {
                    "price_df": df_so_far,
                    "indicators": ind,
                    "sentiment": {"avg_sentiment": 0.0, "mention_count": 0, "mention_velocity": 0.0},
                    "intraday": {},
                    "current_position": None,
                }
                sig = strat.evaluate(ticker, ctx)
                if sig.action == "buy":
                    buy_candidates.append((sig.confidence, ticker, sig, ind))

            # Open highest-confidence entries up to max_positions
            buy_candidates.sort(key=lambda x: x[0], reverse=True)
            slots = max(0, strat.max_positions - open_count)
            for _, ticker, sig, ind in buy_candidates[:slots]:
                entry_price = float(ind.get("last_price") or sig.entry_price or 0)
                if entry_price <= 0:
                    continue
                qty = round(POSITION_SIZE_USD / entry_price, 6)
                # Create a minimal trade-like object for should_close()
                mock_trade = _MockTrade(
                    ticker=ticker,
                    entry_price=entry_price,
                    stop_loss=float(sig.stop_loss) if sig.stop_loss else None,
                    target=float(sig.target) if sig.target else None,
                )
                open_positions[ticker] = {
                    "entry_price": entry_price,
                    "qty": qty,
                    "entry_date": day.strftime("%Y-%m-%d"),
                    "reasoning": " | ".join(sig.reasoning),
                    "mock_trade": mock_trade,
                }

            cumulative_pnl += day_pnl
            equity_curve.append({
                "date": day.strftime("%Y-%m-%d"),
                "equity": round(cumulative_pnl, 2),
            })

        # Force-close any remaining positions at last available price
        for ticker, pos in open_positions.items():
            df = ticker_dfs.get(ticker)
            if df is None:
                continue
            last_row = df[df.index <= trading_days[-1]] if trading_days else df
            if last_row.empty:
                continue
            exit_price = float(last_row["Close"].iloc[-1])
            entry_price = pos["entry_price"]
            qty = pos["qty"]
            pnl = (exit_price - entry_price) * qty
            ret = (exit_price - entry_price) / entry_price if entry_price else 0
            trades.append(BacktestTrade(
                ticker=ticker,
                entry_date=pos["entry_date"],
                exit_date=trading_days[-1].strftime("%Y-%m-%d") if trading_days else None,
                entry_price=round(entry_price, 4),
                exit_price=round(exit_price, 4),
                qty=round(qty, 6),
                pnl=round(pnl, 2),
                return_pct=round(ret, 4),
                exit_reason="period_end",
                reasoning=pos["reasoning"],
            ))

        metrics = self._compute_metrics(trades, equity_curve)
        return BacktestResult(
            strategy=strategy_name,
            tickers=tickers,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            trades=trades,
            equity_curve=equity_curve,
            metrics=metrics,
        )

    def _compute_metrics(self, trades: List[BacktestTrade], equity_curve: List[Dict]) -> Dict:
        if not trades:
            return {
                "total_pnl": 0, "total_return_pct": 0, "num_trades": 0,
                "win_rate": 0, "max_drawdown": 0, "sharpe_ratio": None,
                "avg_win": 0, "avg_loss": 0, "profit_factor": 0,
            }

        closed = [t for t in trades]
        wins = [t for t in closed if t.pnl > 0]
        losses = [t for t in closed if t.pnl <= 0]
        total_pnl = sum(t.pnl for t in closed)
        win_rate = len(wins) / len(closed) if closed else 0
        avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None

        # Max drawdown from equity curve
        equities = [p["equity"] for p in equity_curve]
        max_drawdown = 0.0
        if equities:
            peak = equities[0]
            for e in equities:
                peak = max(peak, e)
                dd = (e - peak) / abs(peak) if peak != 0 else 0
                max_drawdown = min(max_drawdown, dd)

        # Daily returns for Sharpe
        sharpe = None
        if len(equities) > 30:
            daily_returns = pd.Series(equities).diff().dropna()
            if daily_returns.std() > 0:
                sharpe = round(float((daily_returns.mean() / daily_returns.std()) * math.sqrt(252)), 2)

        # Total invested capital (sum of position sizes opened)
        total_invested = len(closed) * POSITION_SIZE_USD
        total_return_pct = total_pnl / total_invested if total_invested > 0 else 0

        return {
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_return_pct, 4),
            "num_trades": len(closed),
            "win_rate": round(win_rate, 4),
            "max_drawdown": round(max_drawdown, 4),
            "sharpe_ratio": sharpe,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        }


class _MockTrade:
    """Minimal object satisfying the trade interface used by should_close()."""
    def __init__(self, ticker, entry_price, stop_loss, target):
        self.ticker = ticker
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.target = target
        self.strategy_id = None
        self.id = None
