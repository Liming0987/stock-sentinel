"""Strategy runner: evaluates each registered strategy on the universe and
opens/closes paper trades, tracks per-strategy performance.

Designed to be called from a Celery task (sync SQLAlchemy session).
"""
import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, List
from uuid import uuid4

from sqlalchemy import create_engine, select, and_, func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.stock import Stock
from app.models.trade import Strategy as StrategyRow, Trade
from app.models.strategy_signal import StrategySignal
from app.services.price_service import PriceService
from app.services.alpaca_service import AlpacaService
from app.services.universe_builder import UniverseBuilder
from app.services.fundamentals_service import FundamentalsService
from app.strategies import STRATEGY_REGISTRY, BaseStrategy
from app.models.trade_event import TradeEvent

logger = logging.getLogger(__name__)

POSITION_SIZE_USD = 100.0  # fixed dollar notional per trade (per-trade cap)
MAX_TOTAL_DEPLOYED_USD = 500.0  # hard cap on total capital deployed across ALL open trades
MAX_PER_TICKER_PER_STRATEGY_USD = 100.0  # cap on capital ONE strategy can deploy in a single ticker
MIN_POSITION_USD = 1.0  # skip an entry when less than this much capital room remains
UNIVERSE_SIZE     = 20     # stocks evaluated per run


class CapitalCapReached(RuntimeError):
    """Raised when opening a new position would exceed MAX_TOTAL_DEPLOYED_USD."""


class MissingExitError(RuntimeError):
    """Raised when a buy signal has neither stop_loss nor target — the trade would
    have no exit condition (should_close could never fire), so we refuse to open it."""


def _sync_db_url() -> str:
    return settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")


def _is_market_open() -> bool:
    """Return True only when the NYSE is in a regular trading session right now."""
    try:
        import pandas_market_calendars as mcal
        import pandas as pd
        import pytz
        from datetime import time as dt_time

        et = pytz.timezone("America/New_York")
        now = datetime.now(et)

        # Weekends are never open
        if now.weekday() >= 5:
            return False

        # Check NYSE calendar for today — handles all holidays (Good Friday,
        # Juneteenth, early closes on Christmas Eve, etc.)
        nyse = mcal.get_calendar("NYSE")
        today = now.date().isoformat()
        schedule = nyse.schedule(start_date=today, end_date=today)
        if schedule.empty:
            return False  # market holiday

        market_open = schedule.iloc[0]["market_open"].to_pydatetime()
        market_close = schedule.iloc[0]["market_close"].to_pydatetime()
        now_utc = datetime.now(timezone.utc)
        return market_open <= now_utc <= market_close

    except Exception:
        # Fall back to simple clock check if library unavailable
        try:
            import pytz
            from datetime import time as dt_time
            et = pytz.timezone("America/New_York")
            now = datetime.now(et)
            return now.weekday() < 5 and dt_time(9, 30) <= now.time() <= dt_time(16, 0)
        except Exception:
            return True


def _is_near_close(window_min: int = 20) -> bool:
    """True if the NYSE is open right now AND within the last `window_min` minutes
    before today's close — the window in which run_eod fires (~3:55 PM ET) to place
    near-close limit orders that fill in the same session.

    Uses the NYSE calendar's actual close, so it also returns False on early-close
    half-days once past the 1 PM close (run_eod simply skips those days).
    """
    try:
        import pandas_market_calendars as mcal
        import pytz
        et = pytz.timezone("America/New_York")
        now_et = datetime.now(et)
        if now_et.weekday() >= 5:
            return False
        nyse = mcal.get_calendar("NYSE")
        today = now_et.date().isoformat()
        schedule = nyse.schedule(start_date=today, end_date=today)
        if schedule.empty:
            return False
        market_open = schedule.iloc[0]["market_open"].to_pydatetime()
        market_close = schedule.iloc[0]["market_close"].to_pydatetime()
        now_utc = datetime.now(timezone.utc)
        return (
            market_open <= now_utc <= market_close
            and (market_close - now_utc) <= timedelta(minutes=window_min)
        )
    except Exception:
        # Fallback clock check: 3:40–4:00 PM ET on a weekday
        try:
            import pytz
            from datetime import time as dt_time
            et = pytz.timezone("America/New_York")
            now = datetime.now(et)
            return now.weekday() < 5 and dt_time(15, 40) <= now.time() <= dt_time(16, 0)
        except Exception:
            return False


class StrategyRunner:
    """Runs all enabled strategies against a stock universe."""

    def __init__(self):
        self.price_service = PriceService()
        self.universe_builder = UniverseBuilder()
        self.fundamentals_service = FundamentalsService()
        alpaca = AlpacaService()
        if not alpaca.is_configured:
            raise RuntimeError(
                "Alpaca credentials are not configured. "
                "All strategy trades must go through Alpaca — simulation mode is disabled."
            )
        self.alpaca = alpaca

    # ── Helpers ────────────────────────────────────────────────────────────
    def _build_universe(self, session: Session) -> List[str]:
        """Score all candidates (S&P 100 + watchlist + trending) and return top UNIVERSE_SIZE."""
        return self.universe_builder.build(session, target=UNIVERSE_SIZE)

    def _ensure_stock(self, session: Session, ticker: str) -> Stock:
        stock = session.execute(
            select(Stock).where(Stock.ticker == ticker)
        ).scalar_one_or_none()
        if stock:
            return stock
        info = self.price_service.get_stock_info(ticker)
        stock = Stock(
            ticker=ticker,
            name=info.get("name", ticker),
            sector=info.get("sector"),
            market_cap=info.get("market_cap"),
            avg_volume=info.get("avg_volume"),
        )
        session.add(stock)
        session.flush()
        return stock

    def _ensure_strategy_row(self, session: Session, strat: BaseStrategy) -> StrategyRow:
        row = session.execute(
            select(StrategyRow).where(StrategyRow.name == strat.name)
        ).scalar_one_or_none()
        if row:
            return row
        row = StrategyRow(name=strat.name, description=strat.description, paper=True, enabled=True)
        session.add(row)
        session.flush()
        return row

    def _build_context(self, session: Session, stock: Stock) -> Dict:
        # 1y of daily bars: swing strategies need a real 50/150/200-EMA stack and a
        # true 52-week high (VCP Stage 2), and Elliott needs its 180-bar pivot lookback.
        # (Intraday context stays at 3mo — it only needs recent daily indicators.)
        df = self.price_service.get_price_data(stock.ticker, period="1y")
        if df is None or df.empty:
            return {}
        indicators = self.price_service.compute_indicators(df)

        # Override last_price with live Alpaca quote when market is open so
        # stops and targets are calculated relative to the actual fill price,
        # not yesterday's close.
        if _is_market_open():
            rt_price = self.alpaca.get_latest_price(stock.ticker)
            if rt_price:
                indicators["last_price"] = rt_price

        fundamentals = self.fundamentals_service.get(stock.ticker, session)

        return {
            "price_df": df,
            "indicators": indicators,
            "fundamentals": fundamentals,
        }

    def _build_intraday_context(self, session: Session, stock: Stock, alpaca) -> Dict:
        """Build strategy context using real-time Alpaca price + cached daily indicators."""
        df = self.price_service.get_price_data(stock.ticker, period="3mo")
        if df is None or df.empty:
            return {}
        indicators = self.price_service.compute_indicators(df)

        # Override last_price with real-time Alpaca quote
        rt_price = alpaca.get_latest_price(stock.ticker)
        if rt_price:
            indicators["last_price"] = rt_price

        # 5-min bars for intraday strategies (ORB, VWAP)
        intraday: Dict = {}
        try:
            df_5m = self.price_service.get_price_data(stock.ticker, period="1d", interval="5m")
            if df_5m is not None and not df_5m.empty:
                intraday = self.price_service.compute_intraday_indicators(df_5m)
                # compute_intraday_indicators returns {} when the frame is stale (wrong day).
                if intraday and rt_price:
                    # Override current_price with the live Alpaca quote.
                    # bars_elapsed and volume_ratio are intentionally left as-is — they
                    # reflect the last completed yfinance bar and are used for bar-clock
                    # gating (entry window, EOD checks), not for price comparisons.
                    intraday["current_price"] = rt_price
        except Exception as e:
            logger.debug(f"Intraday bars unavailable for {stock.ticker}: {e}")

        fundamentals = self.fundamentals_service.get(stock.ticker, session, allow_fetch=False)

        return {
            "price_df": df,
            "indicators": indicators,
            "intraday": intraday,
            "fundamentals": fundamentals,
        }

    def _record_signal(
        self,
        session: Session,
        strat_row: StrategyRow,
        stock: Stock,
        signal,
        executed: bool,
        trade_id: int | None = None,
        not_executed_reason: str | None = None,
    ) -> None:
        row = StrategySignal(
            strategy_id=strat_row.id,
            stock_id=stock.id,
            ticker=stock.ticker,
            action=signal.action,
            confidence=Decimal(str(round(signal.confidence, 3))) if signal.confidence is not None else None,
            entry_price=Decimal(str(signal.entry_price)) if signal.entry_price else None,
            stop_loss=Decimal(str(signal.stop_loss)) if signal.stop_loss else None,
            target=Decimal(str(signal.target)) if signal.target else None,
            reasoning=signal.reasoning if isinstance(signal.reasoning, list) else [],
            executed=executed,
            trade_id=trade_id,
            not_executed_reason=not_executed_reason if not executed else None,
        )
        session.add(row)

    def _deployed_capital(self, session: Session) -> float:
        """Total dollar notional currently deployed across ALL open trades (every strategy).

        This is the global exposure used to enforce MAX_TOTAL_DEPLOYED_USD. It counts
        entry cost (qty × entry_price) of every open position, regardless of which
        strategy opened it, so the whole platform never risks more than the cap.
        """
        total = session.execute(
            select(func.coalesce(func.sum(Trade.qty * Trade.entry_price), 0)).where(
                Trade.status == "open"
            )
        ).scalar() or 0
        return float(total)

    def _deployed_capital_for_ticker_strategy(self, session: Session, ticker: str, strategy_id) -> float:
        """Dollar notional ONE strategy currently has deployed in a single ticker."""
        total = session.execute(
            select(func.coalesce(func.sum(Trade.qty * Trade.entry_price), 0)).where(
                and_(
                    Trade.status == "open",
                    Trade.ticker == ticker,
                    Trade.strategy_id == strategy_id,
                )
            )
        ).scalar() or 0
        return float(total)

    def _available_capital(self, session: Session, ticker: str, strategy_id) -> float:
        """Dollar notional available for a new position in `ticker` for `strategy_id`:
        the smallest of POSITION_SIZE_USD, the room left under the global cap
        (MAX_TOTAL_DEPLOYED_USD), the room left under this strategy's per-ticker cap
        (MAX_PER_TICKER_PER_STRATEGY_USD), and Alpaca's actual buying power.
        Clamped to >= 0.

        Alpaca buying power is the authoritative cash ceiling — without it, the DB cap
        can show room while Alpaca rejects the order with "insufficient buying power."
        """
        global_room = MAX_TOTAL_DEPLOYED_USD - self._deployed_capital(session)
        ticker_room = (
            MAX_PER_TICKER_PER_STRATEGY_USD
            - self._deployed_capital_for_ticker_strategy(session, ticker, strategy_id)
        )
        db_cap = max(0.0, min(POSITION_SIZE_USD, global_room, ticker_room))

        # Clamp to actual Alpaca buying power so we never submit an order the broker
        # will reject. Fall back to db_cap when Alpaca is not configured.
        alpaca_bp = db_cap
        if self.alpaca and self.alpaca.is_configured:
            try:
                acc = self.alpaca.get_account()
                alpaca_bp = float(acc.get("buying_power", db_cap))
            except Exception as e:
                logger.warning(f"Could not fetch Alpaca buying power: {e} — using DB cap")

        return max(0.0, min(db_cap, alpaca_bp))

    def _open_position(
        self, session: Session, strat_row: StrategyRow, stock: Stock, signal, ticker: str
    ) -> Trade:
        """Submit a buy order to Alpaca (if configured) and record the trade using the real fill price."""
        client_order_id = f"{strat_row.name}-{ticker}-{uuid4().hex[:8]}"
        alpaca_order_id = None

        # Refuse to open without an exit condition — a trade with neither stop_loss
        # nor target can never be closed by should_close (it would sit open forever).
        if signal.stop_loss is None and signal.target is None:
            raise MissingExitError(f"{ticker}: signal has no stop_loss or target — refusing to open")

        # Size to the capital room available (≤ $100) so leftover headroom under the
        # caps is used rather than skipped. Skip only if there's effectively no room.
        signal_price = signal.entry_price or 1.0
        available_usd = self._available_capital(session, ticker, strat_row.id)
        if available_usd < MIN_POSITION_USD:
            raise CapitalCapReached(
                f"{ticker}: only ${available_usd:.2f} room left (< ${MIN_POSITION_USD:.0f} min) — skipping"
            )
        qty = round(available_usd / signal_price, 6)
        qty = max(qty, 0.000001)

        order = self.alpaca.submit_order(
            symbol=ticker,
            qty=qty,
            side="buy",
            client_order_id=client_order_id,
        )
        alpaca_order_id = str(order.id)

        fill_price = self.alpaca.get_order_fill(alpaca_order_id)
        if not fill_price:
            # Cancel the pending Alpaca order to avoid a dangling open order
            try:
                self.alpaca.cancel_order(alpaca_order_id)
                logger.warning(f"[{strat_row.name}] Cancelled unfilled order {alpaca_order_id} for {ticker}")
            except Exception as cancel_err:
                logger.error(f"[{strat_row.name}] Failed to cancel order {alpaca_order_id}: {cancel_err}")

            # Write an audit event — no Trade row is created
            failed_event = TradeEvent(
                trade_id=None,
                event_type="open_failed",
                ticker=ticker,
                strategy_name=strat_row.name,
                side="buy",
                qty=Decimal(str(qty)),
                price=Decimal(str(round(signal_price, 4))),
                alpaca_order_id=alpaca_order_id,
                meta={"client_order_id": client_order_id, "signal_price": str(signal_price)},
            )
            session.add(failed_event)
            raise RuntimeError(
                f"Order {alpaca_order_id} for {ticker} did not fill within timeout; order cancelled"
            )

        entry_price = fill_price
        logger.info(f"[{strat_row.name}] Alpaca fill {ticker} @ {fill_price} (signal {signal_price})")

        trade = Trade(
            strategy_id=strat_row.id,
            stock_id=stock.id,
            ticker=ticker,
            side="buy",
            qty=Decimal(str(qty)),
            entry_price=Decimal(str(round(entry_price, 4))),
            stop_loss=Decimal(str(signal.stop_loss)) if signal.stop_loss else None,
            target=Decimal(str(signal.target)) if signal.target else None,
            status="open",
            alpaca_client_order_id=client_order_id,
            alpaca_order_id=alpaca_order_id,
            reasoning=" | ".join(signal.reasoning),
        )
        open_event = TradeEvent(
            trade_id=None,  # will be set after flush
            event_type="opened",
            ticker=ticker,
            strategy_name=strat_row.name,
            side="buy",
            qty=Decimal(str(qty)),
            price=Decimal(str(fill_price)),
            alpaca_order_id=alpaca_order_id,
            meta={"signal_price": str(signal.entry_price), "client_order_id": client_order_id},
        )
        session.add(trade)
        session.flush()  # get trade.id
        open_event.trade_id = trade.id
        session.add(open_event)
        logger.info(f"[{strat_row.name}] OPEN {ticker} @ {entry_price} qty={qty}")

        # SMS notification (fire-and-forget, never raises)
        try:
            from app.services.notification_service import NotificationService
            NotificationService(_sync_db_url()).notify_trade_open(
                strategy=strat_row.name,
                ticker=ticker,
                price=float(signal.entry_price),
                stop=float(signal.stop_loss) if signal.stop_loss else None,
                target=float(signal.target) if signal.target else None,
            )
        except Exception:
            pass

        return trade

    def _open_position_eod(
        self, session: Session, strat_row: StrategyRow, stock: Stock, signal, ticker: str
    ) -> Trade:
        """Submit a near-close BUY *limit* order and record the trade at the real fill.

        Runs while the market is still open (~3:55 PM ET), so the order fills in the
        same session near the signal price. The limit is set slightly above the signal
        price (settings.eod_limit_buffer) so it stays marketable but caps slippage.

        If the limit does not fill before the close it is cancelled. If it fills in
        the race with that cancel — or only *partially* fills — the actual filled
        quantity is recorded and stop/target are re-anchored to the real fill price,
        so the DB always matches Alpaca and the intended risk/reward is preserved.
        """
        client_order_id = f"{strat_row.name}-{ticker}-{uuid4().hex[:8]}-eod"

        # Refuse to open without an exit condition — a trade with neither stop_loss
        # nor target can never be closed by should_close (it would sit open forever).
        if signal.stop_loss is None and signal.target is None:
            raise MissingExitError(f"{ticker}: signal has no stop_loss or target — refusing to open")

        # Size to the capital room available (≤ $100) so leftover headroom under the
        # caps is used rather than skipped. Skip only if there's effectively no room.
        signal_price = signal.entry_price or 1.0
        available_usd = self._available_capital(session, ticker, strat_row.id)
        if available_usd < MIN_POSITION_USD:
            raise CapitalCapReached(
                f"{ticker}: only ${available_usd:.2f} room left (< ${MIN_POSITION_USD:.0f} min) — skipping"
            )
        intended_qty = round(available_usd / signal_price, 6)
        intended_qty = max(intended_qty, 0.000001)

        # Buy limit slightly above the signal price: marketable near the close but
        # bounds the worst-case fill.
        limit_price = round(signal_price * (1 + settings.eod_limit_buffer), 2)

        order = self.alpaca.submit_order(
            symbol=ticker,
            qty=intended_qty,
            side="buy",
            order_type="limit",
            limit_price=limit_price,
            client_order_id=client_order_id,
        )
        alpaca_order_id = str(order.id)

        # Wait for the fill (fully or partially) before touching the DB.
        details = self.alpaca.get_order_fill_details(alpaca_order_id, timeout=20)
        if details is None:
            # Poll timed out with the order still working. Cancel the remainder, then
            # re-check: the order may have filled in the race with our cancel, or a
            # partial fill may surface once the cancel terminates it. If so we record
            # it so the DB matches Alpaca instead of leaving an orphan position.
            try:
                self.alpaca.cancel_order(alpaca_order_id)
            except Exception as cancel_err:
                logger.error(f"[{strat_row.name}] Failed to cancel EOD order {alpaca_order_id}: {cancel_err}")
            details = self.alpaca.get_order_fill_details(alpaca_order_id, timeout=5)
            if details is None:
                logger.warning(f"[{strat_row.name}] EOD limit {ticker} unfilled — cancelled {alpaca_order_id}")
                failed_event = TradeEvent(
                    trade_id=None,
                    event_type="open_failed",
                    ticker=ticker,
                    strategy_name=strat_row.name,
                    side="buy",
                    qty=Decimal(str(intended_qty)),
                    price=Decimal(str(round(limit_price, 4))),
                    alpaca_order_id=alpaca_order_id,
                    meta={"client_order_id": client_order_id, "signal_price": str(signal_price),
                          "limit_price": str(limit_price), "eod": True},
                )
                session.add(failed_event)
                raise RuntimeError(
                    f"EOD limit order {alpaca_order_id} for {ticker} did not fill before close; cancelled"
                )
            logger.warning(
                f"[{strat_row.name}] EOD limit {ticker} filled in race with cancel — "
                f"recording to stay in sync with Alpaca"
            )

        filled_qty, fill_price = details
        partial = filled_qty < intended_qty * 0.999   # tolerance for float rounding

        # Anchor stop-loss / target to the ACTUAL fill so the strategy's intended
        # risk/reward *distances* are preserved relative to where we really got in.
        stop_loss_val = (
            round(fill_price - (signal_price - float(signal.stop_loss)), 2)
            if signal.stop_loss else None
        )
        target_val = (
            round(fill_price + (float(signal.target) - signal_price), 2)
            if signal.target else None
        )

        logger.info(
            f"[{strat_row.name}] EOD limit fill {ticker} @ {fill_price} "
            f"qty={filled_qty}" + (f"/{intended_qty} (PARTIAL)" if partial else "") +
            f" (signal {signal_price}, limit {limit_price})"
        )

        trade = Trade(
            strategy_id=strat_row.id,
            stock_id=stock.id,
            ticker=ticker,
            side="buy",
            qty=Decimal(str(filled_qty)),
            entry_price=Decimal(str(round(fill_price, 4))),
            stop_loss=Decimal(str(stop_loss_val)) if stop_loss_val is not None else None,
            target=Decimal(str(target_val)) if target_val is not None else None,
            status="open",
            alpaca_client_order_id=client_order_id,
            alpaca_order_id=alpaca_order_id,
            reasoning=" | ".join(signal.reasoning) + " | entry: near-close limit (EOD)"
                      + (" [partial fill]" if partial else ""),
        )
        open_event = TradeEvent(
            trade_id=None,
            event_type="opened_eod",
            ticker=ticker,
            strategy_name=strat_row.name,
            side="buy",
            qty=Decimal(str(filled_qty)),
            price=Decimal(str(fill_price)),
            alpaca_order_id=alpaca_order_id,
            meta={
                "client_order_id": client_order_id,
                "signal_price": str(signal_price),
                "limit_price": str(limit_price),
                "intended_qty": str(intended_qty),
                "filled_qty": str(filled_qty),
                "partial": partial,
                "eod": True,
            },
        )
        session.add(trade)
        session.flush()
        open_event.trade_id = trade.id
        session.add(open_event)
        logger.info(f"[{strat_row.name}] EOD OPEN {ticker} @ {fill_price} qty={filled_qty}")

        try:
            from app.services.notification_service import NotificationService
            NotificationService(_sync_db_url()).notify_trade_open(
                strategy=strat_row.name,
                ticker=ticker,
                price=float(fill_price),
                stop=stop_loss_val,
                target=target_val,
            )
        except Exception:
            pass

        return trade

    def _close_position(self, session: Session, trade: Trade, exit_price: float, reason: str) -> bool:
        """Sell an open trade via Alpaca and record it at the real fill price.

        Sells only this strategy's own qty (not the whole symbol) so it never liquidates
        another strategy's position in the same ticker. Returns True if the position was
        sold, False if the sell did not fill — in which case sell_qty_with_order_id has
        already cancelled the order and the trade is left OPEN to retry on the next run,
        rather than being marked closed at a guessed price or queued to fill overnight.
        """
        fill_price, _ = self.alpaca.sell_qty_with_order_id(trade.ticker, float(trade.qty))
        if not fill_price:
            logger.warning(
                f"[strat={trade.strategy_id}] {trade.ticker}: close did not fill — "
                f"order cancelled, leaving trade open to retry ({reason})"
            )
            return False

        exit_price = fill_price
        logger.info(f"Alpaca close fill {trade.ticker} @ {fill_price}")

        entry = float(trade.entry_price)
        qty = float(trade.qty)
        pnl = (exit_price - entry) * qty
        return_pct = (exit_price - entry) / entry if entry else 0

        trade.exit_price = Decimal(str(round(exit_price, 4)))
        trade.pnl = Decimal(str(round(pnl, 2)))
        trade.return_pct = Decimal(str(round(return_pct, 4)))
        trade.status = "closed"
        trade.closed_at = datetime.now(timezone.utc)
        trade.reasoning = (trade.reasoning or "") + f" | exit: {reason}"
        close_event = TradeEvent(
            trade_id=trade.id,
            event_type="closed",
            ticker=trade.ticker,
            strategy_name=None,
            side="sell",
            qty=trade.qty,
            price=Decimal(str(fill_price or exit_price)),
            pnl=trade.pnl,
            alpaca_order_id=trade.alpaca_order_id,
            meta={"reason": reason, "exit_price": str(exit_price)},
        )
        session.add(close_event)
        session.add(trade)
        logger.info(f"[strat={trade.strategy_id}] CLOSE {trade.ticker} @ {exit_price} pnl={pnl:.2f} ({reason})")

        # SMS notification
        try:
            from app.services.notification_service import NotificationService
            strat_name = session.get(StrategyRow, trade.strategy_id)
            strat_label = strat_name.name if strat_name else str(trade.strategy_id)
            NotificationService(_sync_db_url()).notify_trade_close(
                strategy=strat_label,
                ticker=trade.ticker,
                price=exit_price,
                pnl=pnl,
                return_pct=return_pct,
                reason=reason,
            )
        except Exception:
            pass

        return True

    def _recompute_metrics(self, session: Session, strat_row: StrategyRow, compute_unrealized: bool = True):
        """Recompute aggregate metrics for a strategy.

        compute_unrealized=False skips the per-trade yfinance fetch — used in
        run_intraday (60s cadence) to avoid hammering the API. The daily run
        always computes unrealized so the UI stays accurate.
        """
        closed = session.execute(
            select(Trade).where(
                and_(Trade.strategy_id == strat_row.id, Trade.status == "closed")
            )
        ).scalars().all()

        open_trades = session.execute(
            select(Trade).where(
                and_(Trade.strategy_id == strat_row.id, Trade.status == "open")
            )
        ).scalars().all()

        total = len(closed)
        wins = sum(1 for t in closed if t.pnl is not None and float(t.pnl) > 0)
        losses = sum(1 for t in closed if t.pnl is not None and float(t.pnl) <= 0)
        total_pnl = sum(float(t.pnl) for t in closed if t.pnl is not None)
        avg_return = (
            sum(float(t.return_pct) for t in closed if t.return_pct is not None) / total
            if total else 0.0
        )
        win_rate = wins / total if total else 0.0

        # Unrealized P&L on open trades using current price.
        # Skipped in the intraday path to avoid a yfinance call per trade per minute.
        unrealized = 0.0
        if compute_unrealized:
            for t in open_trades:
                df = self.price_service.get_price_data(t.ticker, period="5d")
                if df is not None and not df.empty:
                    last = float(df["Close"].iloc[-1])
                    unrealized += (last - float(t.entry_price)) * float(t.qty)

        strat_row.total_trades = total
        strat_row.winning_trades = wins
        strat_row.losing_trades = losses
        strat_row.total_pnl = Decimal(str(round(total_pnl, 2)))
        strat_row.unrealized_pnl = Decimal(str(round(unrealized, 2)))
        strat_row.win_rate = Decimal(str(round(win_rate, 4)))
        strat_row.avg_return_pct = Decimal(str(round(avg_return, 4)))
        strat_row.last_run_at = datetime.now(timezone.utc)
        self._compute_advanced_metrics(session, strat_row)
        session.add(strat_row)

    def _compute_advanced_metrics(self, session: Session, strat_row):
        """Compute Sharpe ratio, max drawdown, avg hold days, streaks, best/worst trade."""
        import math
        from decimal import Decimal

        closed = session.query(Trade).filter(
            Trade.strategy_id == strat_row.id,
            Trade.status == "closed",
        ).order_by(Trade.closed_at).all()

        if len(closed) < 2:
            return

        returns = [float(t.return_pct) / 100 for t in closed if t.return_pct is not None]
        if len(returns) >= 2:
            mean_r = sum(returns) / len(returns)
            variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
            std_r = math.sqrt(variance) if variance > 0 else 0
            sharpe = (math.sqrt(252) * mean_r / std_r) if std_r > 0 else 0
            strat_row.sharpe_ratio = Decimal(str(round(sharpe, 4)))

        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in closed:
            cum += float(t.pnl or 0)
            if cum > peak:
                peak = cum
            if peak > 0:
                dd = (peak - cum) / peak * 100
                if dd > max_dd:
                    max_dd = dd
        strat_row.max_drawdown = Decimal(str(round(max_dd, 4)))

        hold_days = []
        for t in closed:
            if t.opened_at and t.closed_at:
                hold_days.append((t.closed_at - t.opened_at).total_seconds() / 86400)
        if hold_days:
            strat_row.avg_hold_days = Decimal(str(round(sum(hold_days) / len(hold_days), 2)))

        ret_vals = [float(t.return_pct) for t in closed if t.return_pct is not None]
        if ret_vals:
            strat_row.best_trade_pct = Decimal(str(round(max(ret_vals), 4)))
            strat_row.worst_trade_pct = Decimal(str(round(min(ret_vals), 4)))

        wins = losses = 0
        for t in reversed(closed):
            pnl = float(t.pnl or 0)
            if pnl > 0:
                if losses > 0:
                    break
                wins += 1
            else:
                if wins > 0:
                    break
                losses += 1
        strat_row.consecutive_wins = wins
        strat_row.consecutive_losses = losses

    def run_eod(self) -> Dict:
        """Evaluate strategies near the close and enter with same-session limit orders.

        Fires ~3:55 PM ET (see beat schedule) while the market is still open, so the
        near-final closing candle drives the signal and the limit order fills in the
        same session at ~the signal price — avoiding the overnight gap of a queued
        market-on-open order. Skips outside the near-close window.
        """
        if not _is_near_close():
            logger.info("EOD run: not within the near-close window — skipping")
            return {"skipped": "not_near_close"}

        engine = create_engine(_sync_db_url())
        summary = {"strategies": {}, "trades_opened": 0, "trades_closed": 0, "eod": True}

        with Session(engine) as session:
            universe = self._build_universe(session)
            stocks_ctx: Dict[str, Dict] = {}
            for ticker in universe:
                try:
                    stock = self._ensure_stock(session, ticker)
                    ctx = self._build_context(session, stock)
                    if ctx:
                        stocks_ctx[ticker] = {"stock": stock, "ctx": ctx}
                except Exception as e:
                    logger.warning(f"EOD: skipping {ticker}: {e}")
            session.commit()

            # Fetch all live Alpaca positions once so we can guard against
            # trying to close a position that only has a pending buy order.
            alpaca_positions_now = self.alpaca.get_all_positions_dict()

            for strat_name, strat_cls in STRATEGY_REGISTRY.items():
                strat: BaseStrategy = strat_cls()
                strat_row = self._ensure_strategy_row(session, strat)
                if not strat_row.enabled:
                    continue

                opened = closed = 0

                open_count = session.execute(
                    select(func.count()).select_from(Trade).where(and_(
                        Trade.strategy_id == strat_row.id,
                        Trade.status == "open",
                    ))
                ).scalar() or 0

                buy_candidates = []

                for ticker, payload in stocks_ctx.items():
                    stock: Stock = payload["stock"]
                    ctx = dict(payload["ctx"])

                    open_trade = session.execute(
                        select(Trade).where(and_(
                            Trade.strategy_id == strat_row.id,
                            Trade.stock_id == stock.id,
                            Trade.status == "open",
                        ))
                    ).scalars().first()
                    ctx["current_position"] = open_trade

                    if open_trade:
                        close_reason = strat.should_close(open_trade, ctx)
                        if close_reason:
                            # Only close if Alpaca has a real open position.
                            # If the buy order is still pending (e.g. opened
                            # in the same EOD run), cancel the buy instead.
                            if open_trade.ticker not in alpaca_positions_now:
                                cancelled = self.alpaca.cancel_order(open_trade.alpaca_order_id or "")
                                open_trade.status = "cancelled"
                                open_trade.closed_at = datetime.now(timezone.utc)
                                open_trade.reasoning = (
                                    (open_trade.reasoning or "")
                                    + f" | eod-no-position: buy cancelled ({close_reason})"
                                )
                                session.add(open_trade)
                                logger.info(
                                    f"[{strat_row.name}] {ticker}: no Alpaca position — "
                                    f"buy order cancelled (close reason: {close_reason})"
                                )
                                closed += 1
                                open_count -= 1
                                continue

                            last_price = ctx["indicators"].get("last_price")
                            close_price = float(last_price) if last_price else float(open_trade.entry_price)
                            if self._close_position(session, open_trade, close_price, close_reason):
                                from app.strategies.base import Signal as SigDC
                                sell_sig = SigDC(
                                    action="sell",
                                    confidence=1.0,
                                    entry_price=close_price,
                                    stop_loss=float(open_trade.stop_loss) if open_trade.stop_loss else None,
                                    target=float(open_trade.target) if open_trade.target else None,
                                    reasoning=[close_reason],
                                )
                                self._record_signal(session, strat_row, stock, sell_sig, executed=True, trade_id=open_trade.id)
                                closed += 1
                                open_count -= 1
                            # whether it closed or is left open to retry, don't enter this ticker now
                            continue

                    if strat.requires_intraday:
                        continue

                    if not open_trade:
                        sig = strat.apply_exit_overrides(strat.evaluate(ticker, ctx))
                        # Fundamental modifier is a slow, quarterly-data bias — apply it
                        # only to multi-day strategies, not same-day intraday scalps.
                        if not strat.requires_intraday:
                            sig = strat.apply_fundamental_modifier(sig, ctx)
                        if sig.action == "buy":
                            buy_candidates.append((sig.confidence, ticker, payload["stock"], sig))
                        elif sig.action == "sell":
                            self._record_signal(session, strat_row, stock, sig, executed=False,
                                                not_executed_reason="no_open_position")
                        # hold signals are not recorded — not actionable, flood the log

                buy_candidates.sort(key=lambda x: x[0], reverse=True)
                slots_available = max(0, strat.max_positions - open_count)
                executed_tickers = {t for _, t, _, _ in buy_candidates[:slots_available]}
                dedup_cutoff = datetime.now(timezone.utc) - timedelta(hours=25)
                for _, ticker, stock, sig in buy_candidates:
                    will_execute = ticker in executed_tickers
                    if will_execute:
                        try:
                            trade = self._open_position_eod(session, strat_row, stock, sig, ticker)
                            self._record_signal(session, strat_row, stock, sig, executed=True, trade_id=trade.id)
                            opened += 1
                        except CapitalCapReached as e:
                            logger.info(f"[{strat_row.name}] Capital cap reached (EOD): {e}")
                            self._record_signal(session, strat_row, stock, sig, executed=False,
                                                not_executed_reason="capital_cap_reached")
                        except MissingExitError as e:
                            logger.warning(f"[{strat_row.name}] No exit condition (EOD): {e}")
                            self._record_signal(session, strat_row, stock, sig, executed=False,
                                                not_executed_reason="no_exit_condition")
                        except Exception as e:
                            logger.error(f"[{strat_row.name}] EOD failed to open {ticker}: {e}")
                            self._record_signal(session, strat_row, stock, sig, executed=False,
                                                not_executed_reason="order_fill_failed")
                    else:
                        reason = "max_positions_reached" if slots_available == 0 else "outranked"
                        existing = session.query(StrategySignal).filter(
                            StrategySignal.strategy_id == strat_row.id,
                            StrategySignal.ticker == ticker,
                            StrategySignal.action == "buy",
                            StrategySignal.executed == False,
                            StrategySignal.created_at >= dedup_cutoff,
                        ).first()
                        if not existing:
                            self._record_signal(session, strat_row, stock, sig, executed=False,
                                                not_executed_reason=reason)

                self._recompute_metrics(session, strat_row)
                session.commit()

                summary["strategies"][strat_name] = {
                    "opened": opened,
                    "closed": closed,
                    "total_trades": strat_row.total_trades,
                    "win_rate": float(strat_row.win_rate or 0),
                    "total_pnl": float(strat_row.total_pnl or 0),
                    "unrealized_pnl": float(strat_row.unrealized_pnl or 0),
                }
                summary["trades_opened"] += opened
                summary["trades_closed"] += closed

        engine.dispose()
        return summary

    def run_intraday(self) -> Dict:
        """Run strategies using real-time Alpaca prices. Market-hours-only."""
        from app.services.alpaca_service import AlpacaService

        alpaca = AlpacaService()
        if not alpaca.is_configured:
            return {"skipped": "Alpaca not configured"}
        if not alpaca.is_market_open():
            return {"skipped": "Market closed"}

        engine = create_engine(_sync_db_url())
        summary = {"strategies": {}, "trades_opened": 0, "trades_closed": 0, "intraday": True}

        with Session(engine) as session:
            universe = self._build_universe(session)
            stocks_ctx: Dict[str, Dict] = {}
            for ticker in universe:
                try:
                    stock = self._ensure_stock(session, ticker)
                    ctx = self._build_intraday_context(session, stock, alpaca)
                    if ctx:
                        stocks_ctx[ticker] = {"stock": stock, "ctx": ctx}
                except Exception as e:
                    logger.warning(f"Intraday: skipping {ticker}: {e}")
            session.commit()

            for strat_name, strat_cls in STRATEGY_REGISTRY.items():
                strat: BaseStrategy = strat_cls()
                strat_row = self._ensure_strategy_row(session, strat)
                if not strat_row.enabled:
                    continue

                opened = closed = 0

                open_count = session.execute(
                    select(func.count()).select_from(Trade).where(and_(
                        Trade.strategy_id == strat_row.id,
                        Trade.status == "open",
                    ))
                ).scalar() or 0

                buy_candidates = []

                for ticker, payload in stocks_ctx.items():
                    stock: Stock = payload["stock"]
                    ctx = dict(payload["ctx"])

                    open_trade = session.execute(
                        select(Trade).where(and_(
                            Trade.strategy_id == strat_row.id,
                            Trade.stock_id == stock.id,
                            Trade.status == "open",
                        ))
                    ).scalars().first()
                    ctx["current_position"] = open_trade

                    if open_trade:
                        close_reason = strat.should_close(open_trade, ctx)
                        if close_reason:
                            last_price = ctx["indicators"].get("last_price")
                            close_price = float(last_price) if last_price else float(open_trade.entry_price)
                            if self._close_position(session, open_trade, close_price, close_reason):
                                from app.strategies.base import Signal as SigDC
                                sell_sig = SigDC(
                                    action="sell",
                                    confidence=1.0,
                                    entry_price=close_price,
                                    stop_loss=float(open_trade.stop_loss) if open_trade.stop_loss else None,
                                    target=float(open_trade.target) if open_trade.target else None,
                                    reasoning=[close_reason],
                                )
                                self._record_signal(session, strat_row, stock, sell_sig, executed=True, trade_id=open_trade.id)
                                closed += 1
                                open_count -= 1
                            # whether it closed or is left open to retry, don't enter this ticker now
                            continue

                    # Daily strategies generate entries only via run_eod (after close).
                    # run_intraday handles exits for daily strategies and both
                    # entries + exits for intraday-only strategies (ORB, VWAP).
                    if not strat.requires_intraday:
                        continue

                    if not open_trade:
                        # Block re-entry if a trade for this ticker+strategy was already
                        # closed today (e.g. stopped out on a prior VWAP cross attempt).
                        today_start = datetime.now(timezone.utc).replace(
                            hour=0, minute=0, second=0, microsecond=0
                        )
                        already_traded = session.execute(
                            select(Trade).where(and_(
                                Trade.strategy_id == strat_row.id,
                                Trade.stock_id == stock.id,
                                Trade.status == "closed",
                                Trade.closed_at >= today_start,
                            ))
                        ).scalars().first()
                        if already_traded:
                            continue

                        sig = strat.apply_exit_overrides(strat.evaluate(ticker, ctx))
                        # Fundamental modifier is a slow, quarterly-data bias — apply it
                        # only to multi-day strategies, not same-day intraday scalps.
                        if not strat.requires_intraday:
                            sig = strat.apply_fundamental_modifier(sig, ctx)
                        if sig.action == "buy":
                            buy_candidates.append((sig.confidence, ticker, stock, sig))
                        elif sig.action == "sell":
                            self._record_signal(session, strat_row, stock, sig, executed=False,
                                                not_executed_reason="no_open_position")
                        # hold signals are skipped in the intraday path — they fire too frequently

                buy_candidates.sort(key=lambda x: x[0], reverse=True)
                slots_available = max(0, strat.max_positions - open_count)
                executed_tickers_intra = {t for _, t, _, _ in buy_candidates[:slots_available]}
                dedup_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                for _, ticker, stock, sig in buy_candidates:
                    will_execute = ticker in executed_tickers_intra
                    if will_execute:
                        try:
                            trade = self._open_position(session, strat_row, stock, sig, ticker)
                            self._record_signal(session, strat_row, stock, sig, executed=True, trade_id=trade.id)
                            opened += 1
                        except CapitalCapReached as e:
                            logger.info(f"[{strat_row.name}] Capital cap reached: {e}")
                            self._record_signal(session, strat_row, stock, sig, executed=False,
                                                not_executed_reason="capital_cap_reached")
                        except MissingExitError as e:
                            logger.warning(f"[{strat_row.name}] No exit condition: {e}")
                            self._record_signal(session, strat_row, stock, sig, executed=False,
                                                not_executed_reason="no_exit_condition")
                        except Exception as e:
                            logger.error(f"[{strat_row.name}] Failed to open position for {ticker}: {e}")
                            self._record_signal(session, strat_row, stock, sig, executed=False,
                                                not_executed_reason="order_fill_failed")
                    else:
                        reason = "max_positions_reached" if slots_available == 0 else "outranked"
                        # Dedup: skip if an identical unexecuted buy was already recorded within the last 5 min
                        existing = session.query(StrategySignal).filter(
                            StrategySignal.strategy_id == strat_row.id,
                            StrategySignal.ticker == ticker,
                            StrategySignal.action == "buy",
                            StrategySignal.executed == False,
                            StrategySignal.created_at >= dedup_cutoff,
                        ).first()
                        if existing:
                            continue
                        self._record_signal(session, strat_row, stock, sig, executed=False,
                                            not_executed_reason=reason)

                # Skip unrealized P&L fetch in the intraday path — too expensive
                # at 60s cadence (yfinance call per open trade per strategy).
                self._recompute_metrics(session, strat_row, compute_unrealized=False)
                session.commit()

                summary["strategies"][strat_name] = {
                    "opened": opened,
                    "closed": closed,
                    "total_pnl": float(strat_row.total_pnl or 0),
                }
                summary["trades_opened"] += opened
                summary["trades_closed"] += closed

        engine.dispose()
        return summary
