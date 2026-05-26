"""Trading strategy comparison API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.trade import Strategy as StrategyRow, Trade
from app.strategies import STRATEGY_REGISTRY

router = APIRouter()


@router.get("")
async def list_strategies(db: AsyncSession = Depends(get_db)):
    """Get all registered strategies and their current performance metrics."""
    result = await db.execute(select(StrategyRow).order_by(desc(StrategyRow.total_pnl)))
    rows = result.scalars().all()

    # Make sure registry strategies are returned even if they haven't run yet
    seen = {r.name for r in rows}
    extra = []
    for name, cls in STRATEGY_REGISTRY.items():
        if name not in seen:
            extra.append({
                "name": name,
                "description": cls.description,
                "enabled": True,
                "paper": True,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "unrealized_pnl": 0,
                "avg_return_pct": 0,
                "last_run_at": None,
            })

    strategies = [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "enabled": r.enabled,
            "paper": r.paper,
            "total_trades": r.total_trades,
            "winning_trades": r.winning_trades,
            "losing_trades": r.losing_trades,
            "win_rate": float(r.win_rate or 0),
            "total_pnl": float(r.total_pnl or 0),
            "unrealized_pnl": float(r.unrealized_pnl or 0),
            "avg_return_pct": float(r.avg_return_pct or 0),
            "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
        }
        for r in rows
    ] + extra

    return {"strategies": strategies}


@router.get("/{name}/trades")
async def get_strategy_trades(
    name: str,
    status: str = Query(default="all", regex="^(all|open|closed)$"),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get trades for a specific strategy."""
    strat = await db.execute(select(StrategyRow).where(StrategyRow.name == name))
    strat = strat.scalar_one_or_none()
    if not strat:
        return {"strategy": name, "trades": []}

    query = (
        select(Trade)
        .where(Trade.strategy_id == strat.id)
        .order_by(desc(Trade.opened_at))
        .limit(limit)
    )
    if status != "all":
        query = query.where(Trade.status == status)

    result = await db.execute(query)
    trades = result.scalars().all()

    return {
        "strategy": name,
        "trades": [
            {
                "id": t.id,
                "ticker": t.ticker,
                "side": t.side,
                "qty": float(t.qty) if t.qty else 0,
                "entry_price": float(t.entry_price) if t.entry_price else 0,
                "exit_price": float(t.exit_price) if t.exit_price else None,
                "stop_loss": float(t.stop_loss) if t.stop_loss else None,
                "target": float(t.target) if t.target else None,
                "status": t.status,
                "pnl": float(t.pnl) if t.pnl else None,
                "return_pct": float(t.return_pct) if t.return_pct else None,
                "reasoning": t.reasoning,
                "opened_at": t.opened_at.isoformat() if t.opened_at else None,
                "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            }
            for t in trades
        ],
    }


@router.post("/run")
async def trigger_strategy_run(submit_to_alpaca: bool = False):
    """Manually run all strategies once (synchronously)."""
    import asyncio
    from app.services.strategy_runner import StrategyRunner

    def _run():
        return StrategyRunner(submit_to_alpaca=submit_to_alpaca).run()

    loop = asyncio.get_event_loop()
    summary = await loop.run_in_executor(None, _run)
    return summary


@router.get("/alpaca/account")
async def alpaca_account():
    """Return Alpaca paper account snapshot (cash, equity, positions)."""
    import asyncio
    from app.services.alpaca_service import AlpacaService

    def _fetch():
        svc = AlpacaService()
        if not svc.is_configured:
            return {"configured": False, "message": "Alpaca credentials not set"}
        acc = svc.get_account()
        positions = []
        try:
            for p in svc.get_positions():
                positions.append({
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "avg_entry_price": float(p.avg_entry_price),
                    "current_price": float(p.current_price) if p.current_price else None,
                    "unrealized_pl": float(p.unrealized_pl) if p.unrealized_pl else 0,
                })
        except Exception as e:
            positions = [{"error": str(e)}]
        acc["positions"] = positions
        return acc

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch)
