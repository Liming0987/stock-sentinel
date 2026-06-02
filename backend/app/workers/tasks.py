import logging
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select
from app.config import settings
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Default retry policy shared across all tasks:
#   - up to 3 retries
#   - exponential back-off: 60s → 120s → 240s
#   - any Exception triggers a retry (SoftTimeLimitExceeded included)
_RETRY_DEFAULTS = dict(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)


@celery_app.task(**_RETRY_DEFAULTS, name="app.workers.tasks.scrape_reddit")
def scrape_reddit(self: Task):
    """Scrape subreddits, extract tickers, score sentiment, persist to DB."""
    from decimal import Decimal
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.config import settings
    from app.scrapers.reddit_scraper import RedditScraper
    # Process-level singleton — FinBERT loads once when the worker boots
    from app.services.sentiment_service import get_sentiment_service
    from app.services.price_service import PriceService
    from app.models.stock import Stock
    from app.models.mention import RedditPost, Mention

    try:
        from app.models.watchlist import Watchlist

        scraper = RedditScraper()
        sentiment = get_sentiment_service(use_finbert=True)
        price_service = PriceService()

        results = scraper.scrape_all()
        sync_db_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
        engine = create_engine(sync_db_url)

        # Pull watchlist tickers and do a targeted search so watchlisted stocks
        # always get recent Reddit coverage even when not trending.
        with Session(engine) as tmp:
            watchlist_tickers = tmp.execute(
                select(Stock.ticker).join(Watchlist, Watchlist.stock_id == Stock.id)
            ).scalars().all()
        watchlist_tickers = list(watchlist_tickers)

        if watchlist_tickers:
            seen_ids = {r["external_id"] for r in results}
            targeted = scraper.scrape_for_tickers(watchlist_tickers)
            for r in targeted:
                if r["external_id"] not in seen_ids:
                    results.append(r)
                    seen_ids.add(r["external_id"])

        posts_saved = 0
        mentions_saved = 0
        # Cache ticker→info per run to avoid redundant yfinance calls
        ticker_info_cache: dict = {}

        with Session(engine) as session:
            for item in results:
                existing = session.execute(
                    select(RedditPost).where(RedditPost.external_id == item["external_id"])
                ).scalar_one_or_none()
                if existing:
                    continue

                post = RedditPost(
                    external_id=item["external_id"],
                    subreddit=item["subreddit"],
                    title=item["title"],
                    body=item["body"],
                    author=item["author"],
                    score=item["score"],
                    num_comments=item["num_comments"],
                    url=item["url"],
                    created_at=item["created_at"],
                )
                session.add(post)
                session.flush()
                posts_saved += 1

                text = f"{item['title']} {item['body'] or ''}"
                sent = sentiment.analyze(text, method="auto")

                for ticker in item["tickers"]:
                    # Always validate — even existing stocks may become delisted
                    if ticker not in ticker_info_cache:
                        ticker_info_cache[ticker] = price_service.get_stock_info(ticker)
                    info = ticker_info_cache[ticker]
                    if not info.get("name"):
                        continue

                    stock = session.execute(
                        select(Stock).where(Stock.ticker == ticker)
                    ).scalar_one_or_none()

                    if not stock:
                        stock = Stock(
                            ticker=ticker,
                            name=info.get("name", ticker),
                            sector=info.get("sector"),
                            market_cap=info.get("market_cap"),
                            avg_volume=info.get("avg_volume"),
                        )
                        session.add(stock)
                        session.flush()

                    mention = Mention(
                        stock_id=stock.id,
                        source_type="reddit",
                        source_id=post.id,
                        sentiment_score=Decimal(str(sent["score"])),
                        confidence=Decimal(str(sent["confidence"])),
                        model_used=sent["model_used"],
                        created_at=item["created_at"],
                    )
                    session.add(mention)
                    mentions_saved += 1

            session.commit()

        engine.dispose()
        return {"posts_scraped": len(results), "posts_saved": posts_saved, "mentions_saved": mentions_saved}

    except SoftTimeLimitExceeded:
        logger.warning("scrape_reddit hit soft time limit — aborting cleanly")
        raise


@celery_app.task(**_RETRY_DEFAULTS, name="app.workers.tasks.scrape_stocktwits")
def scrape_stocktwits(self: Task):
    """Scrape StockTwits trending messages, score sentiment, persist to DB."""
    from decimal import Decimal
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.config import settings
    from app.scrapers.stocktwits_scraper import StockTwitsScraper
    from app.services.sentiment_service import get_sentiment_service
    from app.services.price_service import PriceService
    from app.models.stock import Stock
    from app.models.mention import StocktwitsMessage, Mention

    try:
        scraper = StockTwitsScraper()
        # VADER for StockTwits — fast, no model overhead for short messages
        sentiment_svc = get_sentiment_service(use_finbert=False)
        price_service = PriceService()

        results = scraper.scrape_trending()
        sync_db_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
        engine = create_engine(sync_db_url)

        msgs_saved = 0
        mentions_saved = 0
        # Cache ticker→info per run to avoid redundant yfinance calls
        ticker_info_cache: dict = {}

        with Session(engine) as session:
            for item in results:
                existing = session.execute(
                    select(StocktwitsMessage).where(StocktwitsMessage.external_id == item["external_id"])
                ).scalar_one_or_none()
                if existing:
                    continue

                created_at = datetime.now(timezone.utc)
                if item.get("created_at"):
                    try:
                        created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                    except Exception:
                        pass

                msg = StocktwitsMessage(
                    external_id=item["external_id"],
                    body=item["body"],
                    author=item["author"],
                    sentiment_tag=item["sentiment_tag"],
                    likes=item["likes"],
                    created_at=created_at,
                )
                session.add(msg)
                session.flush()
                msgs_saved += 1

                ticker = item["ticker"].upper()

                # Always validate — even existing stocks may become delisted
                if ticker not in ticker_info_cache:
                    ticker_info_cache[ticker] = price_service.get_stock_info(ticker)
                info = ticker_info_cache[ticker]
                if not info.get("name"):
                    continue

                stock = session.execute(
                    select(Stock).where(Stock.ticker == ticker)
                ).scalar_one_or_none()

                if not stock:
                    stock = Stock(
                        ticker=ticker,
                        name=info.get("name", ticker),
                        sector=info.get("sector"),
                        market_cap=info.get("market_cap"),
                        avg_volume=info.get("avg_volume"),
                    )
                    session.add(stock)
                    session.flush()

                sent = sentiment_svc.analyze(item["body"] or "", method="vader")
                mention = Mention(
                    stock_id=stock.id,
                    source_type="stocktwits",
                    source_id=msg.id,
                    sentiment_score=Decimal(str(sent["score"])),
                    confidence=Decimal(str(sent["confidence"])),
                    model_used=sent["model_used"],
                    created_at=created_at,
                )
                session.add(mention)
                mentions_saved += 1

            session.commit()

        engine.dispose()
        return {"messages_scraped": len(results), "messages_saved": msgs_saved, "mentions_saved": mentions_saved}

    except SoftTimeLimitExceeded:
        logger.warning("scrape_stocktwits hit soft time limit — aborting cleanly")
        raise


@celery_app.task(**_RETRY_DEFAULTS, name="app.workers.tasks.update_prices")
def update_prices(self: Task):
    """Update price data for tracked stocks."""
    from app.services.price_service import PriceService
    service = PriceService()
    updated = service.update_all()
    return {"stocks_updated": updated}


@celery_app.task(**_RETRY_DEFAULTS, name="app.workers.tasks.compute_trending")
def compute_trending(self: Task):
    """Compute trending scores for all stocks with recent mentions."""
    from app.services.trending_service import TrendingService
    service = TrendingService()
    rankings = service.compute_rankings()
    return {"stocks_ranked": len(rankings)}


@celery_app.task(**_RETRY_DEFAULTS, name="app.workers.tasks.generate_signals")
def generate_signals(self: Task):
    """Generate buy/hold/avoid signals based on multi-factor model."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.services.signal_service import SignalService
    from app.models.watchlist import Watchlist

    service = SignalService()
    signals = service.generate()

    # SMS: notify for any new buy signal on a watchlisted stock
    try:
        from app.services.notification_service import NotificationService
        from app.models.stock import Stock
        sync_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
        engine = create_engine(sync_url)
        with Session(engine) as s:
            watchlist_tickers = {
                row[0] for row in s.execute(
                    select(Stock.ticker).join(Watchlist, Watchlist.stock_id == Stock.id)
                ).all()
            }
        engine.dispose()

        svc = NotificationService(sync_url)
        for sig in signals:
            ticker = sig.get("ticker", "")
            if sig.get("signal_type") == "buy" and ticker in watchlist_tickers:
                reasoning = sig.get("reasoning", [])
                svc.notify_signal(
                    ticker=ticker,
                    action="buy",
                    confidence=sig.get("confidence", 0),
                    reasoning=reasoning[0] if reasoning else "",
                )
    except Exception as e:
        logger.warning(f"Signal notification failed: {e}")

    return {"signals_generated": len(signals)}


@celery_app.task(**_RETRY_DEFAULTS, name="app.workers.tasks.cleanup_expired_signals")
def cleanup_expired_signals(self: Task):
    """Mark expired signals and compute outcomes."""
    from app.services.signal_service import SignalService
    service = SignalService()
    cleaned = service.cleanup_expired()
    return {"signals_expired": cleaned}


@celery_app.task(**_RETRY_DEFAULTS, name="app.workers.tasks.run_strategies")
def run_strategies(self: Task):
    """Evaluate every registered strategy and open/close paper trades."""
    from app.services.strategy_runner import StrategyRunner
    from app.services.notification_service import NotificationService
    try:
        runner = StrategyRunner()
        return runner.run()
    except Exception as exc:
        msg = str(exc)
        logger.error(f"run_strategies failed: {msg}")
        try:
            sync_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
            NotificationService(sync_url).notify_error("run_strategies", msg)
        except Exception:
            pass
        raise


@celery_app.task(**_RETRY_DEFAULTS, name="app.workers.tasks.refresh_fundamentals")
def refresh_fundamentals(self: Task):
    """Refresh fundamental analysis for all tracked stocks."""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.models.stock import Stock
    from app.services.fundamentals_service import FundamentalsService

    sync_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
    engine = create_engine(sync_url)
    try:
        with Session(engine) as session:
            tickers = session.execute(select(Stock.ticker)).scalars().all()
        with Session(engine) as session:
            FundamentalsService().refresh_all(list(tickers), session)
    finally:
        engine.dispose()
    return {"tickers_refreshed": len(list(tickers))}


@celery_app.task(
    bind=True, name="app.workers.tasks.run_strategies_intraday",
    max_retries=0, time_limit=55, soft_time_limit=50,
    autoretry_for=(), task_acks_late=True,
)
def run_strategies_intraday(self: Task):
    """Run strategies every minute during market hours using real-time Alpaca prices."""
    from app.services.strategy_runner import StrategyRunner
    from app.services.notification_service import NotificationService
    try:
        runner = StrategyRunner()
        return runner.run_intraday()
    except SoftTimeLimitExceeded:
        logger.warning("run_strategies_intraday hit soft time limit — aborting")
        raise
    except Exception as exc:
        msg = str(exc)
        logger.error(f"run_strategies_intraday failed: {msg}")
        try:
            sync_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
            NotificationService(sync_url).notify_error("run_strategies_intraday", msg)
        except Exception:
            pass
        raise
