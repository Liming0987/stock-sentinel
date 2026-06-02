# Stock Sentinel — Claude Code Guide

## Project purpose
Algorithmic paper-trading platform: monitor social sentiment, surface buy signals, execute trades via Alpaca.

## Stack
| Layer | Tech |
|-------|------|
| Backend | FastAPI (Python 3.12) + Celery + PostgreSQL (TimescaleDB) + Redis |
| Frontend | Next.js 14 (App Router) + Recharts |
| Data | yfinance (OHLCV), Alpaca paper trading, Reddit + StockTwits scrapers |
| Sentiment | FinBERT + VADER ensemble |
| Infra | AWS EC2 (single host), Docker Compose, GitHub Actions CI |
| Secrets | AWS Secrets Manager — no .env fallbacks in production |

## Key directories
```
backend/app/
  strategies/   ← trading logic (all extend BaseStrategy)
  services/     ← PriceService, AlpacaService, SentimentService, StrategyRunner, SignalService
  routers/      ← FastAPI route handlers
  workers/      ← Celery tasks (tasks.py) + celery_app.py
  models/       ← SQLAlchemy ORM models
  scrapers/     ← Reddit + StockTwits

frontend/src/
  app/          ← Next.js pages (backtesting/, strategies/, signals/, watchlist/, settings/)
  components/   ← shared UI (dashboard/, layout/, ui/)
```

## Strategy conventions (MUST follow when adding strategies)
- Extend `BaseStrategy` in `backend/app/strategies/base.py`
- Implement `evaluate(self, ticker: str, context: Dict) -> Signal`
- `Signal` dataclass fields: `action` ("buy"/"sell"/"hold"), `confidence` (0–1), `entry_price`, `stop_loss`, `target`, `reasoning: list[str]`
- `context` keys: `price_df` (OHLCV DataFrame), `indicators` (dict from PriceService), `sentiment` (dict), `current_position` (Trade ORM row | None)
- **`Signal` in base.py is a dataclass — not the ORM `Signal` model in `models/signal.py`**
- Register new strategy in **two places**:
  1. `backend/app/strategies/__init__.py` → `STRATEGY_REGISTRY`
  2. `backend/app/workers/tasks.py` → strategy list used by Celery
- Existing strategies: Momentum, RSI MeanReversion, Sentiment-Driven, BB Breakout, VWAP Cross, MACD Histogram, Opening Range Breakout, Fibonacci Retracement, Elliott Wave+Fib

## Current strategies (quick reference)
| Strategy | Entry signal | Exit |
|----------|-------------|------|
| Momentum | price > 50EMA > 200EMA, bullish MACD, volume spike | MACD turns bearish |
| RSI MeanReversion | RSI < 30 oversold, price near lower Bollinger Band | RSI > 70 or target/stop |
| Sentiment-Driven | high mention velocity + positive sentiment + price confirmation | sentiment reversal |
| BB Breakout | close breaks above upper Bollinger Band with volume | price falls below middle band |
| VWAP Cross | price crosses above VWAP with momentum | price falls below VWAP |
| MACD Histogram | histogram turns positive from negative territory | histogram turns negative |
| Opening Range Breakout | breaks above first 30-min high | stop at OR low |
| Fib Retracement | bounces off 0.618 fib with volume | target at prior high |
| Elliott Wave+Fib | wave count + fib confluence | wave structure break |

## Development commands (local)
```bash
# Backend (from backend/)
DATABASE_URL=postgresql+asyncpg://sentinel:sentinel_dev_pass@localhost:5432/stock_sentinel \
REDIS_URL=redis://localhost:6379/0 AWS_REGION=us-east-1 \
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# Frontend (from frontend/)
NEXT_PUBLIC_API_URL="http://127.0.0.1:8001" npm run dev

# Type-check backend
python3 -m py_compile backend/app/strategies/<file>.py

# Type-check frontend
cd frontend && npx tsc --noEmit
```

## Multi-agent workflow
Use `/trade-feature` to build new features or strategies through a 3-agent pipeline:
**Analyst → Builder → Evaluator**

See `.claude/commands/trade-feature.md` for details.
