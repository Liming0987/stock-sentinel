"""Trading strategy comparison API."""
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.stock import Stock
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
                "sharpe_ratio": None,
                "max_drawdown": None,
                "avg_hold_days": None,
                "consecutive_wins": 0,
                "consecutive_losses": 0,
                "best_trade_pct": None,
                "worst_trade_pct": None,
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
            "sharpe_ratio": float(r.sharpe_ratio) if r.sharpe_ratio is not None else None,
            "max_drawdown": float(r.max_drawdown) if r.max_drawdown is not None else None,
            "avg_hold_days": float(r.avg_hold_days) if r.avg_hold_days is not None else None,
            "consecutive_wins": r.consecutive_wins or 0,
            "consecutive_losses": r.consecutive_losses or 0,
            "best_trade_pct": float(r.best_trade_pct) if r.best_trade_pct is not None else None,
            "worst_trade_pct": float(r.worst_trade_pct) if r.worst_trade_pct is not None else None,
        }
        for r in rows
    ] + extra

    return {"strategies": strategies}


@router.patch("/{name}/enabled")
async def set_strategy_enabled(
    name: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a strategy. Body: { "enabled": true | false }"""
    enabled = body.get("enabled")
    if not isinstance(enabled, bool):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="'enabled' must be a boolean")

    row = await db.execute(select(StrategyRow).where(StrategyRow.name == name))
    row = row.scalar_one_or_none()

    if row is None:
        # Strategy exists in registry but hasn't run yet — create the row
        from app.strategies import STRATEGY_REGISTRY
        cls = STRATEGY_REGISTRY.get(name)
        if cls is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
        row = StrategyRow(name=name, description=cls.description, paper=True, enabled=enabled)
        db.add(row)
    else:
        row.enabled = enabled
        db.add(row)

    await db.commit()
    return {"name": name, "enabled": enabled}


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
                "total_cost": round(float(t.entry_price) * float(t.qty), 2) if t.entry_price and t.qty else None,
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


@router.post("/reset")
async def reset_positions(db: AsyncSession = Depends(get_db)):
    """Close all Alpaca positions and cancel all open DB trades so both are in sync."""
    import asyncio
    from datetime import datetime, timezone
    from app.services.alpaca_service import AlpacaService

    def _close_alpaca_positions():
        svc = AlpacaService()
        if not svc.is_configured:
            return [], "Alpaca not configured"
        positions = svc.get_positions()
        closed = []
        errors = []
        for p in positions:
            fill = svc.close_position(p.symbol)
            if fill:
                closed.append({"symbol": p.symbol, "fill_price": fill})
            else:
                errors.append(p.symbol)
        return closed, errors

    loop = asyncio.get_event_loop()
    alpaca_closed, errors = await loop.run_in_executor(None, _close_alpaca_positions)

    # Cancel all open trades in DB
    open_trades_result = await db.execute(
        select(Trade).where(Trade.status == "open")
    )
    open_trades = open_trades_result.scalars().all()
    now = datetime.now(timezone.utc)
    for trade in open_trades:
        trade.status = "cancelled"
        trade.closed_at = now
        trade.reasoning = (trade.reasoning or "") + " | reset: positions cleared for sync"
        db.add(trade)

    # Zero unrealized P&L on all strategies
    strats_result = await db.execute(select(StrategyRow))
    for strat in strats_result.scalars().all():
        strat.unrealized_pnl = 0
        db.add(strat)

    await db.commit()

    return {
        "alpaca_positions_closed": alpaca_closed,
        "alpaca_close_errors": errors,
        "db_trades_cancelled": len(open_trades),
        "message": "All positions closed and DB synced. Ready for fresh start.",
    }


@router.post("/sync-alpaca")
async def sync_alpaca_positions(db: AsyncSession = Depends(get_db)):
    """Reconcile Alpaca order history with the DB.

    Syncs at the ORDER level, not the position level, so each strategy
    execution gets its own Trade row with the correct timestamp and fill
    price — even when Alpaca aggregates multiple fills into one position.

    Two passes:
    1. BUY orders: for each filled buy order not yet in DB (dedup by
       alpaca_order_id), create a Trade row using the order's own
       filled_qty, filled_avg_price, and filled_at.
    2. Orphan close: DB open trades whose ticker has no Alpaca position
       are closed at the last known price (the position was closed
       externally — stop-loss, manual, etc.).
    """
    import asyncio
    from datetime import datetime, timezone

    strategy_names = list(STRATEGY_REGISTRY.keys())

    def _fetch_alpaca_data():
        from app.services.alpaca_service import AlpacaService
        svc = AlpacaService()
        if not svc.is_configured:
            return [], []
        positions = svc.get_positions()
        buy_orders = svc.get_all_filled_orders(limit=500)
        buy_orders = [o for o in buy_orders if str(getattr(o.side, 'value', o.side)) == "buy"]
        return positions, buy_orders

    loop = asyncio.get_event_loop()
    alpaca_positions, buy_orders = await loop.run_in_executor(None, _fetch_alpaca_data)

    alpaca_symbols = {p.symbol for p in alpaca_positions}
    now = datetime.now(timezone.utc)

    # ── Load all open DB trades (for orphan detection) ───────────────────────
    open_result = await db.execute(select(Trade).where(Trade.status == "open"))
    open_trades_list = open_result.scalars().all()

    # Idempotency keys must span ALL trades (open + closed), not just open.
    # A buy order whose position was already closed would otherwise pass the
    # dedup check and be re-imported as a ghost "open" trade.
    all_ids_result = await db.execute(
        select(Trade.alpaca_order_id, Trade.alpaca_client_order_id)
    )
    tracked_order_ids: set = set()
    tracked_client_ids: set = set()
    for order_id, client_id in all_ids_result.all():
        if order_id:
            tracked_order_ids.add(order_id)
        if client_id:
            tracked_client_ids.add(client_id)

    # ── Pass 1: Close orphaned DB trades ─────────────────────────────────────
    orphan_trades = [t for t in open_trades_list if t.ticker not in alpaca_symbols]
    orphan_tickers = list({t.ticker for t in orphan_trades})
    orphan_prices: dict = {}
    if orphan_tickers:
        def _fetch_orphan_prices():
            prices = {}
            try:
                from app.services.alpaca_service import AlpacaService
                svc = AlpacaService()
                if svc.is_configured:
                    prices = svc.get_latest_prices(orphan_tickers)
            except Exception:
                pass
            missing = [t for t in orphan_tickers if t not in prices]
            if missing:
                try:
                    import yfinance as yf
                    for sym in missing:
                        fi = yf.Ticker(sym).fast_info
                        p = getattr(fi, "last_price", None)
                        if p:
                            prices[sym] = float(p)
                except Exception:
                    pass
            return prices
        orphan_prices = await loop.run_in_executor(None, _fetch_orphan_prices)

    orphan_closed = []
    for t in orphan_trades:
        last_price = orphan_prices.get(t.ticker) or float(t.entry_price)
        entry = float(t.entry_price)
        qty = float(t.qty or 0)
        pnl = round((last_price - entry) * qty, 2)
        ret_pct = round((last_price - entry) / entry, 4) if entry else 0
        t.status = "closed"
        t.exit_price = Decimal(str(round(last_price, 4)))
        t.pnl = Decimal(str(pnl))
        t.return_pct = Decimal(str(ret_pct))
        t.closed_at = now
        t.reasoning = (t.reasoning or "") + " | sync-closed: no matching Alpaca position"
        db.add(t)
        orphan_closed.append({"symbol": t.ticker, "pnl": pnl, "exit_price": last_price})

    if not buy_orders:
        await db.commit()
        return {
            "orders_synced": 0,
            "orders_skipped": 0,
            "orphans_closed": len(orphan_closed),
            "orphans": orphan_closed,
            "message": (
                f"No filled buy orders found in Alpaca. "
                f"Closed {len(orphan_closed)} orphaned DB trade(s)."
                if orphan_closed else "No filled buy orders and no orphaned DB trades."
            ),
        }

    # ── Load strategy and stock rows ──────────────────────────────────────────
    strats_result = await db.execute(select(StrategyRow))
    strats_by_name = {s.name: s for s in strats_result.scalars().all()}

    stocks_result = await db.execute(select(Stock))
    stocks_by_ticker = {s.ticker: s for s in stocks_result.scalars().all()}

    synced = []
    skipped = []

    # ── Pass 2: Create one Trade per untracked filled buy order ───────────────
    for order in buy_orders:
        order_id = str(order.id)
        client_id = order.client_order_id or ""

        if order_id in tracked_order_ids or (client_id and client_id in tracked_client_ids):
            skipped.append({"order_id": order_id, "symbol": order.symbol, "reason": "already in DB"})
            continue

        symbol = order.symbol

        # Skip orders for positions no longer open in Alpaca — the position
        # was bought and already closed. Importing these as "open" would
        # create ghost trades with no corresponding Alpaca position.
        if symbol not in alpaca_symbols:
            skipped.append({"order_id": order_id, "symbol": symbol, "reason": "position already closed in Alpaca"})
            continue

        filled_qty = float(order.filled_qty or order.qty or 0)
        fill_price = float(order.filled_avg_price or 0)
        filled_at = order.filled_at  # actual fill timestamp — preserved per order

        if not filled_qty or not fill_price:
            skipped.append({"order_id": order_id, "symbol": symbol, "reason": "missing fill data"})
            continue

        # Parse strategy from client_order_id (format: {strategy_name}-{ticker}-{uuid8})
        strat_name = "untracked"
        if client_id:
            for name in strategy_names:
                if client_id.startswith(f"{name}-"):
                    strat_name = name
                    break

        strat_row = strats_by_name.get(strat_name)
        if strat_row is None:
            strat_row = StrategyRow(
                name=strat_name,
                description="Positions opened outside the strategy runner" if strat_name == "untracked" else None,
                enabled=strat_name != "untracked",
                paper=True,
            )
            db.add(strat_row)
            await db.flush()
            strats_by_name[strat_name] = strat_row

        # Each strategy may hold at most one open position per ticker.
        existing_open = await db.execute(
            select(Trade).where(
                and_(
                    Trade.strategy_id == strat_row.id,
                    Trade.ticker == symbol,
                    Trade.status == "open",
                )
            )
        )
        if existing_open.scalar_one_or_none() is not None:
            skipped.append({"order_id": order_id, "symbol": symbol, "reason": f"{strat_name} already has an open position for {symbol}"})
            continue

        stock = stocks_by_ticker.get(symbol)
        if stock is None:
            stock = Stock(ticker=symbol, name=symbol)
            db.add(stock)
            await db.flush()
            stocks_by_ticker[symbol] = stock

        trade = Trade(
            strategy_id=strat_row.id,
            stock_id=stock.id,
            ticker=symbol,
            side="buy",
            qty=Decimal(str(round(filled_qty, 6))),
            entry_price=Decimal(str(round(fill_price, 4))),
            status="open",
            alpaca_order_id=order_id,
            alpaca_client_order_id=client_id or None,
            opened_at=filled_at,
            reasoning=f"order-synced from Alpaca | order_id={order_id} strategy={strat_name}",
        )
        db.add(trade)
        tracked_order_ids.add(order_id)
        synced.append({
            "order_id": order_id,
            "symbol": symbol,
            "strategy": strat_name,
            "filled_qty": filled_qty,
            "fill_price": fill_price,
            "filled_at": filled_at.isoformat() if filled_at else None,
        })

    await db.commit()
    return {
        "orders_synced": len(synced),
        "orders_skipped": len(skipped),
        "orphans_closed": len(orphan_closed),
        "orders_synced_detail": synced,
        "orphans": orphan_closed,
        "message": (
            f"Synced {len(synced)} order(s) into DB; "
            f"closed {len(orphan_closed)} orphaned trade(s) no longer in Alpaca."
        ),
    }


@router.post("/run")
async def trigger_strategy_run():
    """Manually run all strategies once (synchronously)."""
    import asyncio
    from app.services.strategy_runner import StrategyRunner

    loop = asyncio.get_event_loop()
    summary = await loop.run_in_executor(None, lambda: StrategyRunner().run())
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
    """Open positions with real-time prices — poll every few seconds for live P&L.

    Merges two sources of truth:
    - DB open Trade records (have strategy attribution, stop/target levels)
    - Alpaca open positions (authoritative for what's actually held in the account)
    Any Alpaca position without a matching DB record is surfaced as 'untracked'.
    Use POST /sync-alpaca to reconcile and give untracked positions proper attribution.
    """
    import asyncio
    from datetime import datetime, timezone

    result = await db.execute(select(StrategyRow))
    strats = {s.id: s.name for s in result.scalars().all()}

    trades_result = await db.execute(
        select(Trade).where(Trade.status == "open").order_by(Trade.opened_at)
    )
    open_trades = trades_result.scalars().all()

    def _is_market_open() -> bool:
        from app.services.strategy_runner import _is_market_open as _check
        return _check()

    market_open = _is_market_open()

    db_tickers = list({t.ticker for t in open_trades})

    def _fetch_alpaca_and_prices() -> tuple:
        alpaca_positions = []
        prices: dict = {}
        try:
            from app.services.alpaca_service import AlpacaService
            svc = AlpacaService()
            if svc.is_configured:
                alpaca_positions = svc.get_positions()
                all_tickers = list(set(db_tickers + [p.symbol for p in alpaca_positions]))
                if all_tickers:
                    prices = svc.get_latest_prices(all_tickers)
        except Exception:
            pass

        missing = [t for t in db_tickers if t not in prices]
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
        return prices, alpaca_positions

    loop = asyncio.get_event_loop()
    prices, alpaca_positions = await loop.run_in_executor(None, _fetch_alpaca_and_prices)

    # Today's realized P&L per strategy (closed trades since midnight UTC)
    from datetime import date as _date
    today_start = datetime.combine(_date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    closed_today_result = await db.execute(
        select(Trade).where(
            and_(Trade.status == "closed", Trade.closed_at >= today_start)
        )
    )
    realized_by_strategy: dict = {}
    for t in closed_today_result.scalars().all():
        sname = strats.get(t.strategy_id, "unknown")
        realized_by_strategy[sname] = realized_by_strategy.get(sname, 0.0) + float(t.pnl or 0)

    positions = []
    by_strategy: dict = {}
    tracked_tickers: set = set()

    # DB-tracked positions (have strategy attribution, stop/target)
    for t in open_trades:
        strat_name = strats.get(t.strategy_id, "unknown")
        entry = float(t.entry_price) if t.entry_price else 0.0
        qty = float(t.qty) if t.qty else 0.0
        current = prices.get(t.ticker, entry)
        upnl = (current - entry) * qty
        ret_pct = (current - entry) / entry if entry else 0.0

        tracked_tickers.add(t.ticker)

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
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            "source": "db",
        })

        if strat_name not in by_strategy:
            by_strategy[strat_name] = {"unrealized_pnl": 0.0, "position_count": 0}
        by_strategy[strat_name]["unrealized_pnl"] = round(
            by_strategy[strat_name]["unrealized_pnl"] + upnl, 2
        )
        by_strategy[strat_name]["position_count"] += 1

    # Alpaca positions not yet in DB — shown as "untracked"
    for ap in alpaca_positions:
        if ap.symbol in tracked_tickers:
            continue
        entry = float(ap.avg_entry_price) if ap.avg_entry_price else 0.0
        qty = float(ap.qty) if ap.qty else 0.0
        current = prices.get(ap.symbol) or (float(ap.current_price) if ap.current_price else entry)
        upnl = float(ap.unrealized_pl) if ap.unrealized_pl else (current - entry) * qty
        ret_pct = float(ap.unrealized_plpc) if ap.unrealized_plpc else (
            (current - entry) / entry if entry else 0.0
        )

        positions.append({
            "strategy": "untracked",
            "ticker": ap.symbol,
            "qty": round(qty, 6),
            "entry_price": round(entry, 4),
            "current_price": round(current, 4),
            "stop_loss": None,
            "target": None,
            "unrealized_pnl": round(upnl, 2),
            "return_pct": round(ret_pct, 4),
            "source": "alpaca",
        })

        by_strategy.setdefault("untracked", {"unrealized_pnl": 0.0, "position_count": 0})
        by_strategy["untracked"]["unrealized_pnl"] = round(
            by_strategy["untracked"]["unrealized_pnl"] + upnl, 2
        )
        by_strategy["untracked"]["position_count"] += 1

    # Merge realized P&L into by_strategy (and surface strategies with only realized P&L today)
    for sname, rpnl in realized_by_strategy.items():
        if sname not in by_strategy:
            by_strategy[sname] = {"unrealized_pnl": 0.0, "position_count": 0}
        by_strategy[sname]["realized_pnl"] = round(rpnl, 2)
    for sname in by_strategy:
        by_strategy[sname].setdefault("realized_pnl", 0.0)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "positions": positions,
        "by_strategy": by_strategy,
        "market_open": market_open,
    }


@router.post("/reconcile")
async def reconcile_positions(db: AsyncSession = Depends(get_db)):
    """
    Trigger a reconciliation pass: compare DB open trades vs live Alpaca positions.
    Closes untracked Alpaca positions and marks stale DB trades as closed.
    Returns a summary of actions taken.
    IMPORTANT: Aborts if Alpaca API is unreachable — never modifies DB without Alpaca data.
    """
    import asyncio
    from app.services.position_reconciler import PositionReconciler
    try:
        reconciler = PositionReconciler()
        # Run in thread pool since reconciler uses sync SQLAlchemy
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, reconciler.reconcile)
        return result
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


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
