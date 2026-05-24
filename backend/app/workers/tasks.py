from app.workers.celery_app import celery_app


@celery_app.task
def scrape_reddit():
    """Scrape configured subreddits for stock mentions."""
    from app.scrapers.reddit_scraper import RedditScraper

    scraper = RedditScraper()
    results = scraper.scrape_all()
    return {"posts_scraped": len(results)}


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
