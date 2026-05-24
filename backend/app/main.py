from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import trending, sentiment, prices, signals, watchlist, auth

app = FastAPI(
    title="Stock Sentinel API",
    description="Reddit & Social Sentiment-Driven Stock Monitor",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", settings.frontend_url],
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


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "stock-sentinel"}
