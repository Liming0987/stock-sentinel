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
from app.services.price_service import PriceService
from app.services.alpaca_service import AlpacaService
from app.strategies import STRATEGY_REGISTRY, BaseStrategy

logger = logging.getLogger(__name__)


# Default universe: top liquid stocks. Extend as needed.
DEFAULT_UNIVERSE = [
    "NVDA", "TSLA", "AAPL", "MSFT", "AMD",
    "META", "GOOG", "AMZN", "PLTR", "SOFI",
]


def _sync_db_url() -> str:
    return settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")


class StrategyRunner:
    """Runs all enabled strategies against a stock universe."""

    def __init__(self, universe: List[str] = None, submit_to_alpaca: bool = False):
        self.universe = universe or DEFAULT_UNIVERSE
        self.submit_to_alpaca = submit_to_alpaca
        self.price_service = PriceService()
        # Alpaca is optional; if not configured we just simulate trades in DB
        self.alpaca = AlpacaService() if submit_to_alpaca else None

    # ── Helpers ────────────────────────────────────────────────────────────
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

        return {
            "price_df": df,
            "indicators": indicators,
            "sentiment": {
                "avg_sentiment": avg_sentiment,
                "mention_count": len(mentions),
                "mention_velocity": velocity,
            },
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

        return {
            "price_df": df,
            "indicators": indicators,
            "sentiment": {
                "avg_sentiment": avg_sentiment,
                "mention_count": len(mentions),
                "mention_velocity": velocity,
            },
        }

    def _open_position(
        self, session: Session, strat_row: StrategyRow, stock: Stock, signal, ticker: str
    ) -> Trade:
        """Open a new paper trade. Optionally submit to Alpaca."""
        client_order_id = f"{strat_row.name}-{ticker}-{uuid4().hex[:8]}"
        alpaca_order_id = None

        if self.submit_to_alpaca and self.alpaca and self.alpaca.is_configured:
            try:
                order = self.alpaca.submit_order(
                    symbol=ticker,
                    qty=signal.qty,
                    side="buy",
                    client_order_id=client_order_id,
                )
                alpaca_order_id = str(order.id)
                logger.info(f"[{strat_row.name}] Alpaca order submitted: {alpaca_order_id}")
            except Exception as e:
                logger.warning(f"[{strat_row.name}] Alpaca submit failed: {e}")

        trade = Trade(
            strategy_id=strat_row.id,
            stock_id=stock.id,
            ticker=ticker,
            side="buy",
            qty=Decimal(str(signal.qty)),
            entry_price=Decimal(str(signal.entry_price)),
            stop_loss=Decimal(str(signal.stop_loss)) if signal.stop_loss else None,
            target=Decimal(str(signal.target)) if signal.target else None,
            status="open",
            alpaca_client_order_id=client_order_id,
            alpaca_order_id=alpaca_order_id,
            reasoning=" | ".join(signal.reasoning),
        )
        session.add(trade)
        session.flush()
        logger.info(f"[{strat_row.name}] OPEN {ticker} @ {signal.entry_price} qty={signal.qty}")
        return trade

    def _close_position(self, session: Session, trade: Trade, exit_price: float, reason: str):
        """Close an open trade and compute P&L."""
        if self.submit_to_alpaca and self.alpaca and self.alpaca.is_configured:
            try:
                self.alpaca.submit_order(
                    symbol=trade.ticker,
                    qty=float(trade.qty),
                    side="sell",
                    client_order_id=f"{trade.alpaca_client_order_id}-close",
                )
            except Exception as e:
                logger.warning(f"Alpaca close failed for {trade.ticker}: {e}")

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
        session.add(trade)
        logger.info(f"[strat={trade.strategy_id}] CLOSE {trade.ticker} @ {exit_price} pnl={pnl:.2f} ({reason})")

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
        session.add(strat_row)

    # ── Main entry ─────────────────────────────────────────────────────────
    def run(self) -> Dict:
        """Run all enabled strategies once. Returns summary dict."""
        engine = create_engine(_sync_db_url())
        summary = {"strategies": {}, "trades_opened": 0, "trades_closed": 0}

        with Session(engine) as session:
            # Build context per ticker (one expensive yfinance fetch per ticker)
            stocks_ctx: Dict[str, Dict] = {}
            for ticker in self.universe:
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
                            if last_price:
                                self._close_position(session, open_trade, float(last_price), close_reason)
                                closed += 1
                                open_count -= 1
                                continue

                    # 2) Collect entry signals — only where no existing position
                    if not open_trade:
                        sig = strat.evaluate(ticker, ctx)
                        if sig.action == "buy":
                            buy_candidates.append((sig.confidence, ticker, payload["stock"], sig))

                # Open highest-confidence entries up to max_positions cap
                buy_candidates.sort(key=lambda x: x[0], reverse=True)
                slots_available = max(0, strat.max_positions - open_count)
                for _, ticker, stock, sig in buy_candidates[:slots_available]:
                    self._open_position(session, strat_row, stock, sig, ticker)
                    opened += 1

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
            stocks_ctx: Dict[str, Dict] = {}
            for ticker in self.universe:
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
                            if last_price:
                                self._close_position(session, open_trade, float(last_price), close_reason)
                                closed += 1
                                open_count -= 1
                                continue

                    if not open_trade:
                        sig = strat.evaluate(ticker, ctx)
                        if sig.action == "buy":
                            buy_candidates.append((sig.confidence, ticker, stock, sig))

                buy_candidates.sort(key=lambda x: x[0], reverse=True)
                slots_available = max(0, strat.max_positions - open_count)
                for _, ticker, stock, sig in buy_candidates[:slots_available]:
                    self._open_position(session, strat_row, stock, sig, ticker)
                    opened += 1

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
