"""Position reconciler: keeps the DB in sync with live Alpaca positions.

Run this:
- On application startup (via Celery beat at market open)
- On-demand via POST /api/strategies/reconcile
- After any Alpaca connectivity issue

Safety guarantees:
- Never modifies a trade row without writing a TradeEvent first
- Never closes an Alpaca position without logging the action
- Idempotent: safe to run multiple times
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import Session

from app.models.trade import Trade, Strategy as StrategyRow
from app.models.trade_event import TradeEvent
from app.services.alpaca_service import AlpacaService

logger = logging.getLogger(__name__)


def _sync_db_url() -> str:
    from app.config import settings
    return settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")


class PositionReconciler:
    """Reconciles DB open trades with live Alpaca positions."""

    def __init__(self):
        self.alpaca = AlpacaService()

    def reconcile(self) -> Dict:
        """
        Full reconciliation pass. Returns a summary dict with:
          - orphan_cancelled: Alpaca positions closed (no DB record)
          - db_orphans_closed: DB trades marked closed (no Alpaca position)
          - matched: trades that exist in both, verified
          - errors: list of error strings encountered
        """
        if not self.alpaca.is_configured:
            return {"skipped": "Alpaca not configured"}

        engine = create_engine(_sync_db_url())
        summary = {
            "orphan_cancelled": [],
            "db_orphans_closed": [],
            "matched": [],
            "errors": [],
            "run_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Fetch Alpaca positions — if this call fails, abort entirely
            # (we must not modify DB if we cannot see Alpaca state)
            alpaca_positions = self.alpaca.get_all_positions_dict()
        except Exception as e:
            msg = f"Alpaca get_all_positions_dict failed: {e} — reconciliation aborted"
            logger.error(msg)
            return {"error": msg, "aborted": True}

        with Session(engine) as session:
            # All open trades in DB
            db_trades = session.execute(
                select(Trade).where(Trade.status == "open")
            ).scalars().all()

            # Map by ticker for O(1) lookup
            db_by_ticker: Dict[str, List[Trade]] = {}
            for t in db_trades:
                db_by_ticker.setdefault(t.ticker, []).append(t)

            alpaca_tickers = set(alpaca_positions.keys())
            db_tickers = set(db_by_ticker.keys())

            # ── 1. Alpaca positions with NO DB trade ──────────────────────────
            untracked = alpaca_tickers - db_tickers
            for symbol in sorted(untracked):
                pos = alpaca_positions[symbol]
                logger.warning(
                    f"[Reconciler] Untracked Alpaca position: {symbol} "
                    f"qty={pos['qty']} avg_entry={pos['avg_entry_price']} — closing via API"
                )
                result = self.alpaca.close_position_for_reconciliation(symbol)
                event = TradeEvent(
                    trade_id=None,
                    event_type="orphan_cancelled",
                    ticker=symbol,
                    strategy_name="unknown",
                    side="sell",
                    qty=Decimal(str(pos["qty"])),
                    price=Decimal(str(result["fill_price"])) if result and result.get("fill_price") else None,
                    alpaca_order_id=result["order_id"] if result else None,
                    meta={
                        "reason": "No matching DB trade found; position closed by reconciler",
                        "alpaca_avg_entry": str(pos["avg_entry_price"]),
                        "alpaca_qty": str(pos["qty"]),
                        "close_result": result,
                    },
                )
                session.add(event)
                summary["orphan_cancelled"].append({
                    "symbol": symbol,
                    "qty": pos["qty"],
                    "close_result": result,
                })

            # ── 2. DB trades with NO Alpaca position ──────────────────────────
            # A still-working or unsettled order may not show a position yet; check
            # its order status before closing so we don't flatten a pending fill.
            db_only = db_tickers - alpaca_tickers
            for ticker in sorted(db_only):
                for trade in db_by_ticker[ticker]:
                    if trade.alpaca_order_id:
                        try:
                            from alpaca.trading.requests import GetOrderByIdRequest
                            order = self.alpaca.trading_client.get_order_by_id(
                                trade.alpaca_order_id,
                                filter=GetOrderByIdRequest(nested=False),
                            )
                            order_status = (
                                order.status.value
                                if hasattr(order.status, "value")
                                else str(order.status)
                            )
                            if order_status in ("accepted", "pending_new", "new", "held"):
                                logger.info(
                                    f"[Reconciler] Trade #{trade.id} ({ticker}) has pending order "
                                    f"{trade.alpaca_order_id} — skipping until next run"
                                )
                                continue
                            if order_status == "filled" and order.filled_avg_price:
                                # Order filled but position already closed; update entry and skip
                                trade.entry_price = Decimal(str(round(float(order.filled_avg_price), 4)))
                                session.add(trade)
                                logger.info(
                                    f"[Reconciler] Trade #{trade.id} ({ticker}) fill price updated "
                                    f"to {order.filled_avg_price}"
                                )
                                continue
                        except Exception as e:
                            logger.warning(
                                f"[Reconciler] Could not check order {trade.alpaca_order_id} for "
                                f"trade #{trade.id}: {e}"
                            )

                    logger.warning(
                        f"[Reconciler] DB trade #{trade.id} ({ticker}) has no Alpaca position — marking closed"
                    )
                    event = TradeEvent(
                        trade_id=trade.id,
                        event_type="db_orphan_closed",
                        ticker=ticker,
                        strategy_name=None,
                        side="sell",
                        qty=trade.qty,
                        price=trade.entry_price,  # use entry as best estimate
                        pnl=Decimal("0"),
                        alpaca_order_id=trade.alpaca_order_id,
                        meta={
                            "reason": "DB trade open but Alpaca position not found; closed by reconciler",
                            "original_entry": str(trade.entry_price),
                            "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
                        },
                    )
                    session.add(event)
                    trade.status = "closed"
                    trade.closed_at = datetime.now(timezone.utc)
                    trade.pnl = Decimal("0")
                    trade.return_pct = Decimal("0")
                    summary["db_orphans_closed"].append({
                        "trade_id": trade.id,
                        "ticker": ticker,
                        "alpaca_order_id": trade.alpaca_order_id,
                    })

            # ── 3. Matched positions — verify qty and sync fill price ─────────
            # A symbol may back several DB trades (different strategies each holding up
            # to the per-strategy cap), but Alpaca reports ONE aggregate position per
            # symbol. So compare Alpaca qty against the SUM of the symbol's open trades,
            # and only re-anchor entry_price from Alpaca's (blended) avg when a single
            # trade backs the symbol — otherwise the blend would corrupt per-strategy
            # entries. Stacked trades already record their own real fill at open.
            matched = db_tickers & alpaca_tickers
            for ticker in sorted(matched):
                trades_for_ticker = db_by_ticker[ticker]
                alpaca_qty = alpaca_positions[ticker]["qty"]
                alpaca_avg_entry = alpaca_positions[ticker]["avg_entry_price"]
                total_db_qty = sum(float(t.qty or 0) for t in trades_for_ticker)
                qty_match = abs(alpaca_qty - total_db_qty) < 0.01
                single_trade = len(trades_for_ticker) == 1

                for trade in trades_for_ticker:
                    db_entry = float(trade.entry_price or 0)

                    price_updated = False
                    if single_trade and abs(db_entry - alpaca_avg_entry) > 0.005:
                        trade.entry_price = Decimal(str(round(alpaca_avg_entry, 4)))
                        session.add(trade)
                        price_updated = True
                        logger.info(
                            f"[Reconciler] Trade #{trade.id} ({ticker}) entry_price updated "
                            f"{db_entry} → {alpaca_avg_entry} (actual fill)"
                        )

                    event = TradeEvent(
                        trade_id=trade.id,
                        event_type="reconciled",
                        ticker=ticker,
                        strategy_name=None,
                        side="buy",
                        qty=trade.qty,
                        price=Decimal(str(alpaca_avg_entry)),
                        meta={
                            "qty_match": qty_match,
                            "db_qty": float(trade.qty or 0),
                            "total_db_qty": total_db_qty,
                            "alpaca_qty": alpaca_qty,
                            "alpaca_unrealized_pl": alpaca_positions[ticker].get("unrealized_pl"),
                            "price_updated": price_updated,
                            "placeholder_entry": str(db_entry) if price_updated else None,
                        },
                    )
                    session.add(event)
                    summary["matched"].append({
                        "trade_id": trade.id,
                        "ticker": ticker,
                        "qty_match": qty_match,
                        "db_qty": float(trade.qty or 0),
                        "total_db_qty": total_db_qty,
                        "alpaca_qty": alpaca_qty,
                        "price_updated": price_updated,
                    })

            session.commit()

        engine.dispose()
        logger.info(
            f"[Reconciler] Done: {len(summary['orphan_cancelled'])} orphans cancelled, "
            f"{len(summary['db_orphans_closed'])} DB orphans closed, "
            f"{len(summary['matched'])} matched"
        )
        return summary
