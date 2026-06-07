"""Strategy signal history API — per-signal detail for educational review."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.trade import Strategy as StrategyRow
from app.models.strategy_signal import StrategySignal

router = APIRouter()


def _serialize(sig: StrategySignal, strategy_name: str) -> dict:
    return {
        "id": sig.id,
        "strategy_name": strategy_name,
        "ticker": sig.ticker,
        "action": sig.action,
        "confidence": float(sig.confidence) if sig.confidence is not None else None,
        "entry_price": float(sig.entry_price) if sig.entry_price is not None else None,
        "stop_loss": float(sig.stop_loss) if sig.stop_loss is not None else None,
        "target": float(sig.target) if sig.target is not None else None,
        "reasoning": sig.reasoning if isinstance(sig.reasoning, list) else [],
        "executed": sig.executed,
        "trade_id": sig.trade_id,
        "created_at": sig.created_at.isoformat() if sig.created_at else None,
    }


@router.get("/strategies/{name}/signals")
async def get_strategy_signals(
    name: str,
    action: str = Query(default="all", pattern="^(all|buy|sell|hold)$"),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    strat = await db.execute(select(StrategyRow).where(StrategyRow.name == name))
    strat_row = strat.scalar_one_or_none()
    if not strat_row:
        return {"strategy": name, "signals": []}

    query = (
        select(StrategySignal)
        .where(StrategySignal.strategy_id == strat_row.id)
        .order_by(desc(StrategySignal.created_at))
        .limit(limit)
    )
    if action != "all":
        query = query.where(StrategySignal.action == action)

    result = await db.execute(query)
    signals = result.scalars().all()

    return {
        "strategy": name,
        "signals": [_serialize(s, name) for s in signals],
    }


@router.get("/strategy-signals")
async def list_strategy_signals(
    strategy: str = Query(default=""),
    action: str = Query(default="all", pattern="^(all|buy|sell|hold)$"),
    ticker: str = Query(default=""),
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    strats_result = await db.execute(select(StrategyRow))
    strats_by_id = {s.id: s.name for s in strats_result.scalars().all()}

    if action != "all":
        filters = [StrategySignal.action == action]
    else:
        filters = []

    if strategy:
        strat_row = await db.execute(select(StrategyRow).where(StrategyRow.name == strategy))
        strat_row = strat_row.scalar_one_or_none()
        if strat_row:
            filters.append(StrategySignal.strategy_id == strat_row.id)
        else:
            return {"signals": [], "total": 0}

    if ticker:
        filters.append(StrategySignal.ticker == ticker.upper())

    query = (
        select(StrategySignal)
        .order_by(desc(StrategySignal.created_at))
        .limit(limit)
    )
    if filters:
        query = query.where(and_(*filters))

    result = await db.execute(query)
    signals = result.scalars().all()

    return {
        "signals": [_serialize(s, strats_by_id.get(s.strategy_id, "unknown")) for s in signals],
        "total": len(signals),
    }
