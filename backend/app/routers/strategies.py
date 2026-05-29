"""Trading strategy comparison API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, and_
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


@router.get("/equity-curve")
async def get_equity_curves(db: AsyncSession = Depends(get_db)):
    """Return daily cumulative P&L per strategy for charting."""
    from collections import defaultdict

    result = await db.execute(
        select(StrategyRow)
    )
    strats = result.scalars().all()

    curves = {}
    for strat in strats:
        trades_result = await db.execute(
            select(Trade)
            .where(and_(Trade.strategy_id == strat.id, Trade.status == "closed"))
            .order_by(Trade.closed_at)
        )
        closed_trades = trades_result.scalars().all()

        daily_pnl: dict = defaultdict(float)
        for t in closed_trades:
            if t.closed_at and t.pnl is not None:
                day = t.closed_at.strftime("%Y-%m-%d")
                daily_pnl[day] += float(t.pnl)

        cumulative = 0.0
        points = []
        for day in sorted(daily_pnl.keys()):
            cumulative += daily_pnl[day]
            points.append({"date": day, "cumulative_pnl": round(cumulative, 2), "daily_pnl": round(daily_pnl[day], 2)})

        curves[strat.name] = points

    return {"curves": curves}


@router.get("/live-positions")
async def live_positions(db: AsyncSession = Depends(get_db)):
    """Open positions with real-time prices — poll every few seconds for live P&L."""
    import asyncio
    from datetime import datetime, timezone

    result = await db.execute(select(StrategyRow))
    strats = {s.id: s.name for s in result.scalars().all()}

    trades_result = await db.execute(
        select(Trade).where(Trade.status == "open").order_by(Trade.opened_at)
    )
    open_trades = trades_result.scalars().all()

    def _is_market_open() -> bool:
        try:
            import pytz
            from datetime import time as dt_time
            et = pytz.timezone("America/New_York")
            now = datetime.now(et)
            return now.weekday() < 5 and dt_time(9, 30) <= now.time() <= dt_time(16, 0)
        except Exception:
            return True  # default open if check fails

    market_open = _is_market_open()

    if not open_trades:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "positions": [],
            "by_strategy": {},
            "market_open": market_open,
        }

    tickers = list({t.ticker for t in open_trades})

    def _fetch_prices() -> dict:
        prices: dict = {}
        try:
            from app.services.alpaca_service import AlpacaService
            svc = AlpacaService()
            if svc.is_configured:
                prices = svc.get_latest_prices(tickers)
        except Exception:
            pass

        missing = [t for t in tickers if t not in prices]
        if missing:
            try:
                import yfinance as yf
                for sym in missing:
                    fi = yf.Ticker(sym).fast_info
                    price = getattr(fi, "last_price", None)
                    if price:
                        prices[sym] = float(price)
            except Exception:
                pass
        return prices

    loop = asyncio.get_event_loop()
    prices = await loop.run_in_executor(None, _fetch_prices)

    positions = []
    by_strategy: dict = {}

    for t in open_trades:
        strat_name = strats.get(t.strategy_id, "unknown")
        entry = float(t.entry_price) if t.entry_price else 0.0
        qty = float(t.qty) if t.qty else 0.0
        current = prices.get(t.ticker, entry)
        upnl = (current - entry) * qty
        ret_pct = (current - entry) / entry if entry else 0.0

        positions.append({
            "strategy": strat_name,
            "ticker": t.ticker,
            "qty": round(qty, 6),
            "entry_price": round(entry, 4),
            "current_price": round(current, 4),
            "stop_loss": round(float(t.stop_loss), 4) if t.stop_loss else None,
            "target": round(float(t.target), 4) if t.target else None,
            "unrealized_pnl": round(upnl, 2),
            "return_pct": round(ret_pct, 4),
        })

        if strat_name not in by_strategy:
            by_strategy[strat_name] = {"unrealized_pnl": 0.0, "position_count": 0}
        by_strategy[strat_name]["unrealized_pnl"] = round(
            by_strategy[strat_name]["unrealized_pnl"] + upnl, 2
        )
        by_strategy[strat_name]["position_count"] += 1

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "positions": positions,
        "by_strategy": by_strategy,
        "market_open": market_open,
    }


@router.get("/alpaca/account")
async def alpaca_account():
    """Return Alpaca paper account snapshot (cash, equity, positions)."""
    import asyncio
    from app.services.alpaca_service import AlpacaService

    def _fetch():
        try:
            svc = AlpacaService()
        except Exception as e:
            return {"configured": False, "message": f"Failed to load Alpaca credentials: {e}"}
        if not svc.is_configured:
            return {"configured": False, "message": "Alpaca credentials not set"}
        try:
            acc = svc.get_account()
        except Exception as e:
            return {"configured": True, "error": str(e), "message": "Alpaca API call failed — check API key/secret are valid paper trading credentials"}
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
