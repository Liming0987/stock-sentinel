from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.stock import Stock
from app.models.signal import Signal

router = APIRouter()


@router.get("")
async def get_active_signals(db: AsyncSession = Depends(get_db)):
    """Get all active buy/hold signals."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Signal, Stock)
        .join(Stock, Signal.stock_id == Stock.id)
        .where(Signal.expires_at > now, Signal.outcome.is_(None))
        .order_by(desc(Signal.confidence))
    )
    rows = result.all()

    signals = []
    for signal, stock in rows:
        signals.append({
            "id": signal.id,
            "ticker": stock.ticker,
            "name": stock.name or stock.ticker,
            "signal_type": signal.signal_type,
            "confidence": float(signal.confidence) if signal.confidence else 0,
            "entry_low": float(signal.entry_low) if signal.entry_low else 0,
            "entry_high": float(signal.entry_high) if signal.entry_high else 0,
            "stop_loss": float(signal.stop_loss) if signal.stop_loss else 0,
            "target": float(signal.target) if signal.target else 0,
            "reasoning": signal.reasoning or [],
            "created_at": signal.created_at.isoformat() if signal.created_at else "",
            "expires_at": signal.expires_at.isoformat() if signal.expires_at else "",
        })

    return {"signals": signals}


@router.get("/history")
async def get_signal_history(
    limit: int = Query(default=50, le=200),
    outcome: str = Query(default="all", regex="^(all|hit_target|hit_stop|expired)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get past signals with outcomes for performance tracking."""
    query = (
        select(Signal, Stock)
        .join(Stock, Signal.stock_id == Stock.id)
        .where(Signal.outcome.isnot(None))
        .order_by(desc(Signal.created_at))
        .limit(limit)
    )

    if outcome != "all":
        query = query.where(Signal.outcome == outcome)

    result = await db.execute(query)
    rows = result.all()

    signals = []
    for signal, stock in rows:
        signals.append({
            "id": signal.id,
            "ticker": stock.ticker,
            "name": stock.name or stock.ticker,
            "signal_type": signal.signal_type,
            "confidence": float(signal.confidence) if signal.confidence else 0,
            "outcome": signal.outcome,
            "created_at": signal.created_at.isoformat() if signal.created_at else "",
        })

    total = len(signals)
    hits = sum(1 for s in signals if s["outcome"] == "hit_target")
    hit_rate = round(hits / total, 2) if total > 0 else 0.0

    return {"signals": signals, "stats": {"total": total, "hit_rate": hit_rate}}


@router.post("/generate")
async def trigger_signal_generation():
    """Manually trigger signal generation (runs synchronously)."""
    import asyncio
    from app.services.signal_service import SignalService

    service = SignalService()
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, service.generate)
    return {"signals_generated": len(results), "signals": results}
