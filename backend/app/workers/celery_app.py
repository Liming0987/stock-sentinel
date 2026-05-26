from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "stock_sentinel",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    # Scrape Reddit every 10 minutes
    "scrape-reddit": {
        "task": "app.workers.tasks.scrape_reddit",
        "schedule": 600.0,  # 10 minutes
    },
    # Scrape StockTwits every 15 minutes
    "scrape-stocktwits": {
        "task": "app.workers.tasks.scrape_stocktwits",
        "schedule": 900.0,  # 15 minutes
    },
    # Update price data every 5 minutes during market hours
    "update-prices": {
        "task": "app.workers.tasks.update_prices",
        "schedule": 300.0,  # 5 minutes
    },
    # Compute trending scores every 30 minutes
    "compute-trending": {
        "task": "app.workers.tasks.compute_trending",
        "schedule": 1800.0,  # 30 minutes
    },
    # Generate buy signals every hour
    "generate-signals": {
        "task": "app.workers.tasks.generate_signals",
        "schedule": 3600.0,  # 1 hour
    },
    # Daily cleanup of expired signals
    "cleanup-expired": {
        "task": "app.workers.tasks.cleanup_expired_signals",
        "schedule": crontab(hour=0, minute=0),
    },
    # Run trading strategies every 30 minutes
    "run-strategies": {
        "task": "app.workers.tasks.run_strategies",
        "schedule": 1800.0,  # 30 minutes
    },
}
