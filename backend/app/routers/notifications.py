"""Recent activity feed: buy signals, trade opens, trade closes, task errors."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.stock import Stock
from app.models.signal import Signal
from app.models.trade import Strategy as StrategyRow, Trade
from app.models.task_error import TaskError

router = APIRouter()


@router.get("")
async def get_notifications(
    limit: int = Query(default=30, le=100),
    hours: int = Query(default=48),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    notifications = []

    # ── Buy signals ────────────────────────────────────────────────────────
    sig_result = await db.execute(
        select(Signal, Stock)
        .join(Stock, Signal.stock_id == Stock.id)
        .where(and_(Signal.signal_type == "buy", Signal.created_at >= cutoff))
        .order_by(desc(Signal.created_at))
        .limit(limit)
    )
    for sig, stock in sig_result.all():
        reasoning = ""
        if sig.reasoning:
            reasons = sig.reasoning if isinstance(sig.reasoning, list) else []
            reasoning = reasons[0] if reasons else ""
        notifications.append({
            "id": f"signal-{sig.id}",
            "type": "signal",
            "ticker": stock.ticker,
            "message": f"Buy signal for ${stock.ticker} — {int((sig.confidence or 0) * 100)}% confidence. {reasoning}".strip(),
            "timestamp": sig.created_at.isoformat(),
            "meta": {"confidence": float(sig.confidence or 0)},
        })

    # ── Trade opens ────────────────────────────────────────────────────────
    strats_result = await db.execute(select(StrategyRow))
    strats = {s.id: s.name for s in strats_result.scalars().all()}

    open_result = await db.execute(
        select(Trade)
        .where(Trade.opened_at >= cutoff)
        .order_by(desc(Trade.opened_at))
        .limit(limit)
    )
    for trade in open_result.scalars().all():
        strat_name = strats.get(trade.strategy_id, "strategy")
        notifications.append({
            "id": f"trade-open-{trade.id}",
            "type": "trade_open",
            "ticker": trade.ticker,
            "message": f"[{strat_name}] Opened ${trade.ticker} @ ${float(trade.entry_price or 0):.2f}",
            "timestamp": trade.opened_at.isoformat(),
            "meta": {"entry_price": float(trade.entry_price or 0), "strategy": strat_name},
        })

    # ── Trade closes ───────────────────────────────────────────────────────
    close_result = await db.execute(
        select(Trade)
        .where(and_(Trade.status == "closed", Trade.closed_at >= cutoff))
        .order_by(desc(Trade.closed_at))
        .limit(limit)
    )
    for trade in close_result.scalars().all():
        strat_name = strats.get(trade.strategy_id, "strategy")
        pnl = float(trade.pnl or 0)
        sign = "+" if pnl >= 0 else ""
        notifications.append({
            "id": f"trade-close-{trade.id}",
            "type": "trade_close",
            "ticker": trade.ticker,
            "message": f"[{strat_name}] Closed ${trade.ticker} @ ${float(trade.exit_price or 0):.2f} | P&L {sign}${pnl:.2f}",
            "timestamp": trade.closed_at.isoformat(),
            "meta": {"pnl": pnl, "strategy": strat_name},
        })

    # ── Task errors ────────────────────────────────────────────────────────
    error_result = await db.execute(
        select(TaskError)
        .where(TaskError.created_at >= cutoff)
        .order_by(desc(TaskError.created_at))
        .limit(limit)
    )
    for err in error_result.scalars().all():
        notifications.append({
            "id": f"task-error-{err.id}",
            "type": "task_error",
            "ticker": None,
            "message": f"[{err.task_name}] {err.error_message}",
            "timestamp": err.created_at.isoformat(),
            "meta": {"task_name": err.task_name},
        })

    notifications.sort(key=lambda n: n["timestamp"], reverse=True)
    return {"notifications": notifications[:limit]}
