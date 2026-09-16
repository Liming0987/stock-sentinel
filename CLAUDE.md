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
  strategies/   ← trading logic (all extend BaseStrategy); base.py + __init__.py registry
    swing/      ← daily-bar, multi-day strategies (momentum, rsi, bb, macd, fib, elliott, vcp)
    intraday/   ← 5-min, same-day strategies (opening_range_breakout, vwap_cross)
  services/     ← PriceService, AlpacaService, SentimentService, StrategyRunner, TrendingService
  routers/      ← FastAPI route handlers
  workers/      ← Celery tasks (tasks.py) + celery_app.py
  models/       ← SQLAlchemy ORM models
  scrapers/     ← Reddit + StockTwits

frontend/src/
  app/          ← Next.js pages (backtesting/, strategies/, watchlist/, settings/)
  components/   ← shared UI (dashboard/, layout/, ui/)
```

## Strategy conventions (MUST follow when adding strategies)
- Extend `BaseStrategy` in `backend/app/strategies/base.py`
- Implement `evaluate(self, ticker: str, context: Dict) -> Signal`
- `Signal` dataclass fields: `action` ("buy"/"sell"/"hold"), `confidence` (0–1), `entry_price`, `stop_loss`, `target`, `reasoning: list[str]`
- `context` keys: `price_df` (OHLCV DataFrame), `indicators` (dict from PriceService), `fundamentals` (dict), `current_position` (Trade ORM row | None); `intraday` (dict) for intraday strategies
- **`Signal` in base.py is a dataclass — not the ORM `Signal` model in `models/signal.py`**
- Place the file in `backend/app/strategies/swing/` or `.../intraday/` (set `requires_intraday=True` for intraday)
- Register it in `backend/app/strategies/__init__.py` → import + `STRATEGY_REGISTRY` (the runner iterates the registry; no separate list in tasks.py)
- Existing strategies: Momentum, RSI MeanReversion, BB Breakout, VWAP Cross, MACD Histogram, Opening Range Breakout, Fibonacci Retracement, Elliott Wave+Fib, VCP

## Current strategies (quick reference)
| Strategy | Entry signal | Exit |
|----------|-------------|------|
| Momentum | price > rising 50EMA > 200EMA AND bullish MACD (volume boosts confidence) | MACD turns bearish |
| RSI MeanReversion | RSI crosses back above 30 (oversold bounce), price above 200-EMA | RSI > 60 or target/stop |
| BB Breakout | close breaks above upper Bollinger Band with volume | price falls below middle band |
| VWAP Cross | price crosses above VWAP with momentum | price falls below VWAP |
| MACD Histogram | histogram turns positive from negative territory | histogram turns negative |
| Opening Range Breakout | breaks above first 30-min high | stop at OR low |
| Fib Retracement | bounces off 0.618 fib with volume | target at prior high |
| Elliott Wave+Fib | wave count + fib confluence | wave structure break |
| VCP | volume-confirmed pivot breakout after 2–4 contractions in a Stage-2 uptrend | 8% stop or 2.5× risk target |

**Authoritative per-strategy specs** (entry/exit rules, every parameter + its backtest rationale, rejected alternatives) live in `openspec/specs/strategies/<swing|intraday>/<name>/spec.md`. Read the spec before changing a strategy. Elliott Wave+Fib trades Wave 4 pullbacks only (W2 entries were removed). The Sentiment-Driven strategy was removed — do NOT reintroduce it.

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

## Runtime notes & gotchas
- **Universe is dynamic** — `UniverseBuilder` (services/universe_builder.py) scores an S&P-100 pool + watchlist + trending and selects the top ~20 each run; there is no fixed ticker list. Non-equity cashtags surfaced by scrapers (FX, crypto, delisted) are filtered via the `EXCLUDED_TICKERS` denylist.
- **Secrets** — one combined secret `stock-sentinel/credentials` holds all third-party keys (Reddit + Alpaca). When `alpaca_paper: true` the service uses `alpaca_paper_api_key`/`_secret`. No env-var fallbacks; loaded via `services/secrets.py`.
- **Order sizing** — order size is clamped to Alpaca buying power. EOD limit orders size quantity on the *limit* price (signal price × buffer), not the signal price, so `qty × limit` never exceeds buying power (avoids "insufficient buying power" rejections). Caps: $100/trade, $100 per strategy per ticker, $500 total.
- **Notifications** — SMS via **AWS SNS** (services/notification_service.py, boto3 + EC2 instance role), not Twilio.
- **Signal log** — `/api/strategy-signals` (per-signal decision audit incl. `not_executed_reason`). The old advisory `/api/signals` + `SignalService` were removed.
- **Known bug** — `GET /api/prices/{ticker}` can return 500 when yfinance yields NaN candle values (JSON can't serialize NaN); the daily-recon skill works around it by pulling prices from yfinance directly.

## Multi-agent workflow
Use `/trade-feature` to build new features or strategies through a 3-agent pipeline:
**Analyst → Builder → Evaluator**

See `.claude/commands/trade-feature.md` for details.

## OpenSpec
Specs and change proposals live in `openspec/`. Use `/opsx:propose`, `/opsx:apply`, `/opsx:archive` (or `/opsx:explore` to think through an idea). Capability specs are under `openspec/specs/` — strategies under `strategies/`, tooling under `tools/` (daily-recon, daily-recon-scoring, strategy-review).
