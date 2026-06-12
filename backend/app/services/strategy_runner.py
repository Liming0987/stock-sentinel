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
from app.models.mention import Mention
from app.models.trade import Strategy as StrategyRow, Trade
from app.models.strategy_signal import StrategySignal
from app.services.price_service import PriceService
from app.services.alpaca_service import AlpacaService
from app.services.universe_builder import UniverseBuilder
from app.services.fundamentals_service import FundamentalsService
from app.strategies import STRATEGY_REGISTRY, BaseStrategy
from app.models.trade_event import TradeEvent

logger = logging.getLogger(__name__)

POSITION_SIZE_USD = 500.0  # fixed dollar amount to risk per trade
UNIVERSE_SIZE     = 20     # stocks evaluated per run


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
        df = self.price_service.get_price_data(stock.ticker, period="3mo")
        if df is None or df.empty:
            return {}
        indicators = self.price_service.compute_indicators(df)

        # Sentiment from mentions table (last 24h)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        mentions = session.execute(
            select(Mention).where(
                and_(Mention.stock_id == stock.id, Mention.created_at >= cutoff)
            )
        ).scalars().all()

        if mentions:
            scores = [float(m.sentiment_score) for m in mentions if m.sentiment_score is not None]
            avg_sentiment = sum(scores) / len(scores) if scores else 0.0
            velocity = len(mentions) / 24.0
        else:
            avg_sentiment = 0.0
            velocity = 0.0

        fundamentals = self.fundamentals_service.get(stock.ticker, session)

        return {
            "price_df": df,
            "indicators": indicators,
            "sentiment": {
                "avg_sentiment": avg_sentiment,
                "mention_count": len(mentions),
                "mention_velocity": velocity,
            },
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

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        mentions = session.execute(
            select(Mention).where(
                and_(Mention.stock_id == stock.id, Mention.created_at >= cutoff)
            )
        ).scalars().all()

        scores = [float(m.sentiment_score) for m in mentions if m.sentiment_score is not None]
        avg_sentiment = sum(scores) / len(scores) if scores else 0.0
        velocity = len(mentions) / 24.0

        # 5-min bars for intraday strategies (ORB, VWAP)
        intraday: Dict = {}
        try:
            df_5m = self.price_service.get_price_data(stock.ticker, period="1d", interval="5m")
            if df_5m is not None and not df_5m.empty:
                intraday = self.price_service.compute_intraday_indicators(df_5m)
                # Override current_price with real-time Alpaca quote
                if rt_price:
                    intraday["current_price"] = rt_price
        except Exception as e:
            logger.debug(f"Intraday bars unavailable for {stock.ticker}: {e}")

        fundamentals = self.fundamentals_service.get(stock.ticker, session, allow_fetch=False)

        return {
            "price_df": df,
            "indicators": indicators,
            "sentiment": {
                "avg_sentiment": avg_sentiment,
                "mention_count": len(mentions),
                "mention_velocity": velocity,
            },
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
        )
        session.add(row)

    def _open_position(
        self, session: Session, strat_row: StrategyRow, stock: Stock, signal, ticker: str
    ) -> Trade:
        """Submit a buy order to Alpaca (if configured) and record the trade using the real fill price."""
        client_order_id = f"{strat_row.name}-{ticker}-{uuid4().hex[:8]}"
        alpaca_order_id = None

        # Size position to a fixed dollar amount; use fractional shares
        signal_price = signal.entry_price or 1.0
        qty = round(POSITION_SIZE_USD / signal_price, 6)
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

    def _close_position(self, session: Session, trade: Trade, exit_price: float, reason: str):
        """Close an open trade via Alpaca and record the fill price.

        Falls back to the last_price passed by the caller when Alpaca returns no fill
        (e.g. position already closed on Alpaca side, partial fill, API hiccup).
        This ensures the DB is always updated to 'closed' — never left stuck as 'open'.
        """
        fill_price = self.alpaca.close_position(trade.ticker)
        if fill_price:
            exit_price = fill_price
            logger.info(f"Alpaca close fill {trade.ticker} @ {fill_price}")
        else:
            logger.warning(
                f"Alpaca close_position({trade.ticker}) returned no fill — "
                f"recording exit at last price {exit_price:.4f}"
            )

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

    def _recompute_metrics(self, session: Session, strat_row: StrategyRow):
        """Recompute aggregate metrics for a strategy."""
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

        # Unrealized P&L on open trades using current price
        unrealized = 0.0
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

    # ── Main entry ─────────────────────────────────────────────────────────
    def run(self) -> Dict:
        """Run all enabled strategies once. Returns summary dict."""
        if not _is_market_open():
            logger.info("Market closed — skipping strategy run")
            return {"skipped": "market_closed"}

        engine = create_engine(_sync_db_url())
        summary = {"strategies": {}, "trades_opened": 0, "trades_closed": 0}

        with Session(engine) as session:
            universe = self._build_universe(session)
            # Build context per ticker (one expensive yfinance fetch per ticker)
            stocks_ctx: Dict[str, Dict] = {}
            for ticker in universe:
                try:
                    stock = self._ensure_stock(session, ticker)
                    ctx = self._build_context(session, stock)
                    if ctx:
                        stocks_ctx[ticker] = {"stock": stock, "ctx": ctx}
                except Exception as e:
                    logger.warning(f"Skipping {ticker}: {e}")
            session.commit()

            # Run each strategy
            for strat_name, strat_cls in STRATEGY_REGISTRY.items():
                strat: BaseStrategy = strat_cls()
                strat_row = self._ensure_strategy_row(session, strat)
                if not strat_row.enabled:
                    continue

                opened = closed = 0

                # Count currently open positions for this strategy
                open_count = session.execute(
                    select(func.count()).select_from(Trade).where(and_(
                        Trade.strategy_id == strat_row.id,
                        Trade.status == "open",
                    ))
                ).scalar() or 0

                # Collect buy signals so we can rank by confidence and respect max_positions
                buy_candidates = []

                for ticker, payload in stocks_ctx.items():
                    stock: Stock = payload["stock"]
                    ctx = dict(payload["ctx"])  # copy

                    # Inject current open position for this strategy+ticker
                    open_trade = session.execute(
                        select(Trade).where(and_(
                            Trade.strategy_id == strat_row.id,
                            Trade.stock_id == stock.id,
                            Trade.status == "open",
                        ))
                    ).scalar_one_or_none()
                    ctx["current_position"] = open_trade

                    # 1) Manage open positions
                    if open_trade:
                        close_reason = strat.should_close(open_trade, ctx)
                        if close_reason:
                            last_price = ctx["indicators"].get("last_price")
                            close_price = float(last_price) if last_price else float(open_trade.entry_price)
                            self._close_position(session, open_trade, close_price, close_reason)
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
                            continue

                    # 2) Collect entry signals — only where no existing position
                    if not open_trade:
                        sig = strat.apply_fundamental_modifier(strat.evaluate(ticker, ctx), ctx)
                        if sig.action == "buy":
                            buy_candidates.append((sig.confidence, ticker, payload["stock"], sig))
                        else:
                            self._record_signal(session, strat_row, stock, sig, executed=False)

                # Open highest-confidence entries up to max_positions cap
                buy_candidates.sort(key=lambda x: x[0], reverse=True)
                slots_available = max(0, strat.max_positions - open_count)
                executed_tickers = {t for _, t, _, _ in buy_candidates[:slots_available]}
                for _, ticker, stock, sig in buy_candidates:
                    will_execute = ticker in executed_tickers
                    if will_execute:
                        try:
                            trade = self._open_position(session, strat_row, stock, sig, ticker)
                            self._record_signal(session, strat_row, stock, sig, executed=True, trade_id=trade.id)
                            opened += 1
                        except Exception as e:
                            logger.error(f"[{strat_row.name}] Failed to open position for {ticker}: {e}")
                            self._record_signal(session, strat_row, stock, sig, executed=False)
                    else:
                        self._record_signal(session, strat_row, stock, sig, executed=False)

                # Update aggregate metrics
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
                    ).scalar_one_or_none()
                    ctx["current_position"] = open_trade

                    if open_trade:
                        close_reason = strat.should_close(open_trade, ctx)
                        if close_reason:
                            last_price = ctx["indicators"].get("last_price")
                            close_price = float(last_price) if last_price else float(open_trade.entry_price)
                            self._close_position(session, open_trade, close_price, close_reason)
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
                            continue

                    if not open_trade:
                        sig = strat.apply_fundamental_modifier(strat.evaluate(ticker, ctx), ctx)
                        if sig.action == "buy":
                            buy_candidates.append((sig.confidence, ticker, stock, sig))
                        elif sig.action == "sell":
                            self._record_signal(session, strat_row, stock, sig, executed=False)
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
                        except Exception as e:
                            logger.error(f"[{strat_row.name}] Failed to open position for {ticker}: {e}")
                            self._record_signal(session, strat_row, stock, sig, executed=False)
                    else:
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
                        self._record_signal(session, strat_row, stock, sig, executed=False)

                self._recompute_metrics(session, strat_row)
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
