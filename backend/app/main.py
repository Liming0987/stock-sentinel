from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.models.database import engine, Base
from app.models.stock import Stock
from app.models.mention import RedditPost, StocktwitsMessage, Mention
from app.models.signal import Signal, TrendingSnapshot
from app.models.trade import Strategy, Trade
from app.models.watchlist import Watchlist
from app.models.settings import AppSetting  # noqa: F401 — registers table with Base
from app.models.fundamentals import StockFundamentals  # noqa: F401 — registers table with Base
from app.models.strategy_signal import StrategySignal  # noqa: F401 — registers table with Base
from app.models.daily_report import DailyReport  # noqa: F401 — registers table with Base
from app.routers import trending, sentiment, prices, signals, watchlist, auth, strategies as strategies_router
from app.routers import settings as settings_router
from app.routers import notifications as notifications_router
from app.routers import backtest as backtest_router
from app.routers import fundamentals as fundamentals_router
from app.routers import strategy_signals as strategy_signals_router
from app.routers.reports import router as reports_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Enable TimescaleDB extension if available
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        except Exception:
            pass  # Regular PostgreSQL without TimescaleDB
    yield
    await engine.dispose()


app = FastAPI(
    title="Stock Sentinel API",
    description="Reddit & Social Sentiment-Driven Stock Monitor",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(trending.router, prefix="/api/trending", tags=["trending"])
app.include_router(sentiment.router, prefix="/api/sentiment", tags=["sentiment"])
app.include_router(prices.router, prefix="/api/prices", tags=["prices"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(strategies_router.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])
app.include_router(notifications_router.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(backtest_router.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(fundamentals_router.router, prefix="/api/fundamentals", tags=["fundamentals"])
app.include_router(strategy_signals_router.router, prefix="/api", tags=["strategy-signals"])
app.include_router(reports_router, prefix="/api", tags=["reports"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "stock-sentinel"}
