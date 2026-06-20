import logging
import sys
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_init

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "stock_sentinel",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution limits — prevent runaway tasks from blocking workers
    task_time_limit=300,       # hard kill after 5 min
    task_soft_time_limit=240,  # raises SoftTimeLimitExceeded after 4 min

    # Acknowledge tasks only after completion so a crashed worker re-queues them
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Recycle worker processes after this many tasks to avoid memory leaks
    worker_max_tasks_per_child=50,

    # Single worker thread per container (set in compose command; this is a
    # safety default so in-process invocations also respect it)
    worker_concurrency=1,

    # Rate-limit for the whole worker — at most 1 task per second globally
    worker_prefetch_multiplier=1,

    # Retry result backend errors so beat keeps scheduling even if Redis blips
    result_backend_transport_options={"retry_policy": {"timeout": 5.0}},
)

celery_app.conf.beat_schedule = {
    "scrape-reddit": {
        "task": "app.workers.tasks.scrape_reddit",
        "schedule": 600.0,
    },
    "scrape-stocktwits": {
        "task": "app.workers.tasks.scrape_stocktwits",
        "schedule": 900.0,
    },
    "update-prices": {
        "task": "app.workers.tasks.update_prices",
        "schedule": 300.0,
    },
    "compute-trending": {
        "task": "app.workers.tasks.compute_trending",
        "schedule": 1800.0,
    },
    "generate-signals": {
        "task": "app.workers.tasks.generate_signals",
        "schedule": 3600.0,
    },
    "cleanup-expired": {
        "task": "app.workers.tasks.cleanup_expired_signals",
        "schedule": crontab(hour=0, minute=0),
    },
    "cleanup-strategy-signals": {
        "task": "app.workers.tasks.cleanup_strategy_signals",
        "schedule": crontab(hour=2, minute=0),
    },
    "refresh-fundamentals": {
        "task": "app.workers.tasks.refresh_fundamentals",
        "schedule": crontab(hour=1, minute=0),
    },
    # Daily-candle strategies: run once at market open using yesterday's closes
    # for all indicators (MACD, EMA, RSI) + today's live Alpaca price.
    # 14:35 UTC = 10:35 AM EDT / 9:35 AM EST — inside market hours year-round
    # without DST gymnastics. Running every 30 min was wasteful: daily indicators
    # don't change until 4pm, so all intermediate runs produced identical signals.
    "run-strategies": {
        "task": "app.workers.tasks.run_strategies",
        "schedule": crontab(hour=14, minute=35),
    },
    "run-strategies-intraday": {
        "task": "app.workers.tasks.run_strategies_intraday",
        "schedule": 60.0,  # every minute, task itself skips if market closed
    },
    "generate-daily-report": {
        "task": "tasks.generate_daily_report",
        "schedule": crontab(hour=21, minute=0),  # 21:00 UTC = 5pm ET
    },
    "reconcile-positions": {
        "task": "tasks.reconcile_positions",
        "schedule": crontab(hour=13, minute=30),  # 13:30 UTC = 9:30am ET (market open)
    },
}


@worker_init.connect
def _verify_db_on_startup(sender, **kwargs):
    """
    Pre-flight DB check: if the database is unreachable or the schema is missing
    required columns, exit the worker immediately with a non-zero code.

    Docker will then apply the restart policy (on-failure with delay) rather than
    spinning in a tight crash-load-crash cycle.
    """
    import time
    from sqlalchemy import create_engine, text

    sync_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
    engine = create_engine(sync_url, pool_pre_ping=True)

    for attempt in range(1, 6):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                # Verify critical columns exist before accepting any tasks
                result = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='stocks' AND column_name='prev_close'"
                ))
                if not result.fetchone():
                    logger.error(
                        "Schema not ready: stocks.prev_close missing. "
                        "Run: docker compose exec backend alembic upgrade head"
                    )
                    sys.exit(1)
            logger.info("Worker pre-flight DB check passed")
            engine.dispose()
            return
        except Exception as exc:
            logger.warning("DB not ready (attempt %d/5): %s", attempt, exc)
            if attempt < 5:
                time.sleep(10 * attempt)  # 10s, 20s, 30s, 40s back-off

    logger.error("DB unreachable after 5 attempts — worker refusing to start")
    sys.exit(1)
