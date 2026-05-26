from app.workers.celery_app import celery_app


@celery_app.task
def scrape_reddit():
    """Scrape configured subreddits, extract tickers, analyze sentiment, persist to DB."""
    from decimal import Decimal
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.config import settings
    from app.scrapers.reddit_scraper import RedditScraper
    from app.services.sentiment_service import SentimentService
    from app.services.price_service import PriceService
    from app.models.stock import Stock
    from app.models.mention import RedditPost, Mention

    scraper = RedditScraper()
    # Use FinBERT for finance-tuned sentiment (falls back to VADER if load fails)
    sentiment = SentimentService(use_finbert=True)
    price_service = PriceService()

    results = scraper.scrape_all()
    sync_db_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
    engine = create_engine(sync_db_url)

    posts_saved = 0
    mentions_saved = 0

    with Session(engine) as session:
        for item in results:
            # Skip if post already exists
            existing = session.execute(
                select(RedditPost).where(RedditPost.external_id == item["external_id"])
            ).scalar_one_or_none()
            if existing:
                continue

            # Save RedditPost
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
            session.flush()  # get post.id
            posts_saved += 1

            # Analyze sentiment once per post
            text = f"{item['title']} {item['body'] or ''}"
            sent = sentiment.analyze(text, method="auto")

            # Create one Mention per (post, ticker)
            for ticker in item["tickers"]:
                stock = session.execute(
                    select(Stock).where(Stock.ticker == ticker)
                ).scalar_one_or_none()

                if not stock:
                    # Bootstrap stock from yfinance
                    info = price_service.get_stock_info(ticker)
                    if not info.get("name"):
                        continue  # invalid ticker
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


@celery_app.task
def scrape_stocktwits():
    """Scrape StockTwits for trending stock messages."""
    from app.scrapers.stocktwits_scraper import StockTwitsScraper

    scraper = StockTwitsScraper()
    results = scraper.scrape_trending()
    return {"messages_scraped": len(results)}


@celery_app.task
def update_prices():
    """Update price data for tracked stocks."""
    from app.services.price_service import PriceService

    service = PriceService()
    updated = service.update_all()
    return {"stocks_updated": updated}


@celery_app.task
def compute_trending():
    """Compute trending scores for all stocks with recent mentions."""
    from app.services.trending_service import TrendingService

    service = TrendingService()
    rankings = service.compute_rankings()
    return {"stocks_ranked": len(rankings)}


@celery_app.task
def generate_signals():
    """Generate buy/hold/avoid signals based on multi-factor model."""
    from app.services.signal_service import SignalService

    service = SignalService()
    signals = service.generate()
    return {"signals_generated": len(signals)}


@celery_app.task
def cleanup_expired_signals():
    """Mark expired signals and compute outcomes."""
    from app.services.signal_service import SignalService

    service = SignalService()
    cleaned = service.cleanup_expired()
    return {"signals_expired": cleaned}
