# Stock Sentinel

Reddit & Social Sentiment-Driven Stock Monitor with Buy-Point Recommendations.

## Features

- **Social Scraping**: Reddit (r/wallstreetbets, r/stocks, etc.) + StockTwits
- **NLP Sentiment**: FinBERT + VADER ensemble scoring
- **Trending Rankings**: Multi-factor stock ranking by mention velocity, sentiment, engagement
- **Price Monitoring**: Real-time OHLCV + technical indicators (RSI, MACD, Bollinger Bands)
- **Buy Signals**: Multi-factor recommendation engine with entry zones + stop-losses
- **Pump Detection**: Flags suspicious mention patterns from few authors
- **Alerts**: Dashboard notifications + email for watchlist stocks

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Reddit API credentials ([create app here](https://www.reddit.com/prefs/apps))
- (Optional) Finnhub API key ([free tier](https://finnhub.io/))

### Setup

```bash
# Clone and navigate
cd stock-sentinel

# Copy environment file and fill in credentials
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head
```

### Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Architecture

```
Frontend (Next.js :3000)
    ↕ REST API
Backend (FastAPI :8000)
    ↕
Workers (Celery) ─── Redis (broker)
    ↕
PostgreSQL + TimescaleDB
```

## Data Sources

| Source | Type | Cost |
|--------|------|------|
| Reddit (PRAW) | Social sentiment | Free |
| StockTwits | Social sentiment | Free |
| Google Trends | Search interest | Free |
| Yahoo Finance | Price data | Free |
| Finnhub | News + real-time quotes | Free tier |
| Financial Modeling Prep | Fundamentals | Free tier |
| FRED | Macro indicators | Free |

## Project Structure

```
stock-sentinel/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app
│   │   ├── config.py          # Settings
│   │   ├── models/            # SQLAlchemy models
│   │   ├── routers/           # API endpoints
│   │   ├── scrapers/          # Reddit, StockTwits scrapers
│   │   ├── services/          # Business logic
│   │   └── workers/           # Celery tasks + scheduler
│   ├── alembic/               # DB migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  # Next.js app (TBD)
├── docker-compose.yml
├── SPEC.md                    # Full design specification
└── README.md
```

## AWS Deployment

See `SPEC.md` Section 10 for detailed AWS deployment options:
- **Option A**: Single EC2 t3.small + Docker Compose (~$30-50/mo)
- **Option B**: ECS Fargate + RDS + ElastiCache (~$80-120/mo)

## Disclaimer

This tool is for **informational purposes only** and does not constitute financial advice. Past signal performance does not guarantee future results.
