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
from app.routers import trending, sentiment, prices, signals, watchlist, auth, strategies as strategies_router


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


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "stock-sentinel"}
