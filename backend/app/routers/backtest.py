"""Backtest API — run a strategy against historical data."""
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.strategies import STRATEGY_REGISTRY

router = APIRouter()


class BacktestRequest(BaseModel):
    strategy: str
    tickers: List[str]
    start_date: date
    end_date: date

    @field_validator("strategy")
    @classmethod
    def strategy_must_exist(cls, v):
        if v not in STRATEGY_REGISTRY:
            raise ValueError(f"Unknown strategy '{v}'. Valid: {list(STRATEGY_REGISTRY)}")
        return v

    @field_validator("tickers")
    @classmethod
    def tickers_not_empty(cls, v):
        tickers = [t.strip().upper() for t in v if t.strip()]
        if not tickers:
            raise ValueError("At least one ticker is required")
        if len(tickers) > 20:
            raise ValueError("Maximum 20 tickers per backtest")
        return tickers

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        if v > date.today():
            raise ValueError("end_date cannot be in the future")
        return v

    @field_validator("start_date")
    @classmethod
    def start_not_too_old(cls, v):
        if v < date.today() - timedelta(days=365 * 5):
            raise ValueError("start_date cannot be more than 5 years ago")
        return v


@router.get("/strategies")
async def list_strategies():
    """List available strategies for the backtest UI."""
    return {
        "strategies": [
            {"name": name, "description": cls.description}
            for name, cls in STRATEGY_REGISTRY.items()
        ]
    }


@router.post("/run")
async def run_backtest(req: BacktestRequest):
    """Run a backtest. Returns trades, equity curve and metrics."""
    import asyncio
    from app.services.backtest_runner import BacktestRunner

    def _run():
        runner = BacktestRunner()
        return runner.run(
            strategy_name=req.strategy,
            tickers=req.tickers,
            start_date=req.start_date,
            end_date=req.end_date,
        )

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {e}")

    return {
        "strategy": result.strategy,
        "tickers": result.tickers,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "metrics": result.metrics,
        "equity_curve": result.equity_curve,
        "trades": [
            {
                "ticker": t.ticker,
                "entry_date": t.entry_date,
                "exit_date": t.exit_date,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "qty": t.qty,
                "pnl": t.pnl,
                "return_pct": t.return_pct,
                "exit_reason": t.exit_reason,
                "reasoning": t.reasoning,
            }
            for t in result.trades
        ],
    }
