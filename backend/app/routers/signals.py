from fastapi import APIRouter, Query

router = APIRouter()


@router.get("")
async def get_active_signals():
    """Get all active buy/hold signals."""
    # TODO: Implement
    return {"signals": []}


@router.get("/history")
async def get_signal_history(
    limit: int = Query(default=50, le=200),
    outcome: str = Query(default="all", regex="^(all|hit_target|hit_stop|expired)$"),
):
    """Get past signals with outcomes for performance tracking."""
    # TODO: Implement
    return {"signals": [], "stats": {"total": 0, "hit_rate": 0.0}}
