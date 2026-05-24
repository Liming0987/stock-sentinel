# Stock Sentinel — Design Specification

> Reddit & Social Sentiment-Driven Stock Monitor with Buy-Point Recommendations

## 1. Problem Statement

Retail investors lack a unified tool that:
- Aggregates real-time social sentiment around stocks from Reddit, StockTwits, and other sources
- Identifies trending tickers before they spike
- Combines sentiment signals with technical analysis to surface actionable buy points
- Is accessible as a personal web app hosted on AWS

## 2. Goals

1. **Collect** stock-related posts/comments from Reddit, StockTwits, Google Trends, and news APIs
2. **Analyze** sentiment using NLP (FinBERT + VADER ensemble)
3. **Rank** most-discussed stocks by mention velocity, engagement, and sentiment momentum
4. **Monitor** real-time and historical price data with technical indicators
5. **Recommend** buy points using a multi-signal fusion model
6. **Alert** the user via dashboard + push/email notifications
7. **Host** on AWS for anywhere-access with authentication

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     AWS Infrastructure                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Route 53 → ALB → ECS Fargate (or single EC2 + Docker)      │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Frontend   │  │  Backend    │  │  Workers            │  │
│  │  Next.js    │  │  FastAPI    │  │  Celery + Beat      │  │
│  │  Port 3000  │  │  Port 8000  │  │  (scrape, analyze)  │  │
│  └─────────────┘  └──────┬──────┘  └──────────┬──────────┘  │
│                           │                     │             │
│            ┌──────────────▼─────────────────────▼──────┐     │
│            │         PostgreSQL (TimescaleDB)           │     │
│            │         Redis (cache + broker)             │     │
│            └───────────────────────────────────────────┘     │
│                                                               │
│  S3 (backups) · CloudWatch (logs) · Cognito (auth)           │
└──────────────────────────────────────────────────────────────┘
```

## 4. Data Sources

### 4.1 Social & Sentiment

| Source | Method | Rate Limit | Cost |
|--------|--------|-----------|------|
| Reddit (r/wallstreetbets, r/stocks, r/investing, r/options, r/pennystocks, r/stockmarket) | PRAW (Reddit API) | 60 req/min | Free |
| StockTwits | REST API | 200 req/hr | Free |
| Google Trends | pytrends library | ~10 req/min | Free |
| HackerNews | Algolia API | Generous | Free |
| YouTube (finance channels) | YouTube Data API v3 | 10,000 units/day | Free |

### 4.2 Market Data

| Source | Data | Cost |
|--------|------|------|
| yfinance | Historical OHLCV, fundamentals | Free (unofficial) |
| Polygon.io | Real-time/delayed quotes, news | Free tier (delayed 15 min) |
| Finnhub | Real-time quotes, news, sentiment, insider trades | Free (60 calls/min) |
| Alpha Vantage | Intraday data, technicals | Free (5 calls/min) |
| Twelve Data | Pre-calculated technical indicators | Free (8 calls/min) |

### 4.3 News & Filings

| Source | Data | Cost |
|--------|------|------|
| Finnhub News | Market news with sentiment | Free tier |
| SEC EDGAR | 13F filings, insider transactions | Free |
| FRED | Macro indicators (CPI, rates, unemployment) | Free |
| Financial Modeling Prep | Earnings, DCF, ratios | Free (250 calls/day) |

## 5. Core Modules

### 5.1 Data Ingestion Pipeline

```
Scheduler (every 5-15 min)
    │
    ├── Reddit Scraper → Extract posts/comments
    ├── StockTwits Scraper → Extract messages
    ├── Google Trends → Interest over time
    └── News Fetcher → Headlines + summaries
          │
          ▼
    Ticker Extraction (regex + NLP)
          │
          ▼
    Sentiment Scoring (FinBERT / VADER)
          │
          ▼
    Store in PostgreSQL
```

**Ticker Extraction Rules:**
- Match `$TICKER` pattern (e.g., `$AAPL`)
- NLP NER for company names (e.g., "Apple" → AAPL)
- Filter out common false positives (e.g., $A, $IT, $ALL, $FOR)
- Validate against known ticker list (NYSE + NASDAQ)

### 5.2 Sentiment Analysis Engine

**Primary Model**: FinBERT (HuggingFace `ProsusAI/finbert`)
- Input: post/comment text (truncated to 512 tokens)
- Output: `{positive, negative, neutral}` probabilities → mapped to score [-1, 1]

**Fallback**: VADER (for high-throughput when FinBERT queue is full)

**Aggregation**:
```
weighted_sentiment = Σ(sentiment_i × weight_i) / Σ(weight_i)

where weight_i = log(1 + upvotes) × recency_decay × source_credibility
```

### 5.3 Trending Stocks Ranking

**Composite Score Formula:**
```
trend_score = (mention_velocity × 0.30)
            + (sentiment_avg × 0.25)
            + (engagement_ratio × 0.20)
            + (cross_platform_presence × 0.15)
            + (volume_anomaly × 0.10)
```

**Anomaly Detection:**
- Z-score: alert when `(current_mentions - μ_7day) / σ_7day > 2.0`
- Pump detection: flag if > 60% of mentions come from < 3 unique authors

### 5.4 Price Monitor

**Technical Indicators Computed:**
- RSI (14-period)
- MACD (12, 26, 9)
- Bollinger Bands (20-period, 2σ)
- 50-day & 200-day EMA
- VWAP
- Average True Range (ATR)
- Volume vs 20-day average

**Library**: `pandas-ta` or `ta-lib`

### 5.5 Buy-Point Recommendation Engine

**Multi-Signal Fusion:**

| Signal | Weight | Trigger Condition |
|--------|--------|-------------------|
| Sentiment surge | 25% | Score > 0.6 AND mention velocity in top 10% |
| Technical oversold | 30% | RSI < 30 OR price < lower Bollinger Band |
| Volume confirmation | 20% | Volume > 1.5× 20-day avg |
| Historical similarity | 15% | Past similar setups yielded 5%+ in 5 days |
| News catalyst | 10% | Positive news sentiment in last 24h |

**Output per signal:**
```json
{
  "ticker": "AAPL",
  "rating": "BUY",
  "confidence": 0.78,
  "entry_zone": {"low": 172.50, "high": 174.00},
  "stop_loss": 168.00,
  "target": 182.00,
  "reasoning": ["RSI oversold at 28", "Positive sentiment spike +40%", "Volume 2.1x average"],
  "expires_at": "2024-01-15T16:00:00Z"
}
```

**Safety Rails:**
- Minimum market cap: $500M (no micro-caps)
- Minimum average daily volume: 500K shares
- Auto-expire signals after 48 hours
- Maximum 5 active buy signals at once
- Prominent "not financial advice" disclaimer

### 5.6 Alert System

- **In-app**: Real-time dashboard badge + toast notifications
- **Email**: Daily digest + immediate alerts for buy signals on watchlist stocks
- **Push**: Browser push notifications (via service worker)
- **Configurable**: Per-stock sensitivity thresholds

## 6. Data Model

```sql
-- Core tables
CREATE TABLE stocks (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255),
    sector VARCHAR(100),
    market_cap BIGINT,
    avg_volume BIGINT,
    last_price DECIMAL(10, 2),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE reddit_posts (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(20) UNIQUE,
    subreddit VARCHAR(50),
    title TEXT,
    body TEXT,
    author VARCHAR(50),
    score INT,
    num_comments INT,
    url TEXT,
    created_at TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE stocktwits_messages (
    id SERIAL PRIMARY KEY,
    external_id BIGINT UNIQUE,
    body TEXT,
    author VARCHAR(50),
    sentiment_tag VARCHAR(10),  -- bullish/bearish from StockTwits
    likes INT,
    created_at TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE mentions (
    id SERIAL PRIMARY KEY,
    stock_id INT REFERENCES stocks(id),
    source_type VARCHAR(20),  -- reddit, stocktwits, news, youtube
    source_id INT,
    sentiment_score DECIMAL(4, 3),  -- -1.000 to 1.000
    confidence DECIMAL(4, 3),
    model_used VARCHAR(20),  -- finbert, vader
    created_at TIMESTAMPTZ
);

-- TimescaleDB hypertable
CREATE TABLE prices (
    stock_id INT REFERENCES stocks(id),
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10, 2),
    high DECIMAL(10, 2),
    low DECIMAL(10, 2),
    close DECIMAL(10, 2),
    volume BIGINT,
    PRIMARY KEY (stock_id, timestamp)
);
SELECT create_hypertable('prices', 'timestamp');

CREATE TABLE technical_indicators (
    stock_id INT REFERENCES stocks(id),
    timestamp TIMESTAMPTZ NOT NULL,
    rsi DECIMAL(6, 2),
    macd DECIMAL(10, 4),
    macd_signal DECIMAL(10, 4),
    bb_upper DECIMAL(10, 2),
    bb_lower DECIMAL(10, 2),
    ema_50 DECIMAL(10, 2),
    ema_200 DECIMAL(10, 2),
    vwap DECIMAL(10, 2),
    PRIMARY KEY (stock_id, timestamp)
);

CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    stock_id INT REFERENCES stocks(id),
    signal_type VARCHAR(10),  -- BUY, HOLD, AVOID
    confidence DECIMAL(4, 3),
    entry_low DECIMAL(10, 2),
    entry_high DECIMAL(10, 2),
    stop_loss DECIMAL(10, 2),
    target DECIMAL(10, 2),
    reasoning JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    outcome VARCHAR(10)  -- hit_target, hit_stop, expired
);

CREATE TABLE trending_snapshots (
    id SERIAL PRIMARY KEY,
    stock_id INT REFERENCES stocks(id),
    mention_count INT,
    mention_velocity DECIMAL(8, 2),
    avg_sentiment DECIMAL(4, 3),
    trend_score DECIMAL(6, 3),
    rank INT,
    snapshot_at TIMESTAMPTZ DEFAULT NOW()
);

-- User tables
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE watchlists (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    stock_id INT REFERENCES stocks(id),
    alert_on_buy_signal BOOLEAN DEFAULT TRUE,
    alert_on_sentiment_spike BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, stock_id)
);

CREATE TABLE alert_history (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    stock_id INT REFERENCES stocks(id),
    alert_type VARCHAR(30),
    message TEXT,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ
);
```

## 7. API Endpoints

### Dashboard
- `GET /api/trending` — Top 20 trending stocks with scores
- `GET /api/trending/{ticker}` — Detailed trending data for a stock

### Sentiment
- `GET /api/sentiment/{ticker}` — Current & historical sentiment
- `GET /api/sentiment/{ticker}/posts` — Recent posts mentioning ticker

### Prices
- `GET /api/prices/{ticker}` — OHLCV + indicators
- `GET /api/prices/{ticker}/chart?period=1M` — Chart data

### Signals
- `GET /api/signals` — Active buy signals
- `GET /api/signals/history` — Past signals with outcomes

### Watchlist
- `GET /api/watchlist` — User's watchlist
- `POST /api/watchlist/{ticker}` — Add to watchlist
- `DELETE /api/watchlist/{ticker}` — Remove from watchlist

### Auth
- `POST /api/auth/login`
- `POST /api/auth/register`
- `POST /api/auth/refresh`

## 8. Frontend Pages

| Page | Description |
|------|-------------|
| `/dashboard` | Overview: top trending, active signals, watchlist summary |
| `/trending` | Full trending leaderboard with filters (timeframe, sector) |
| `/stock/{ticker}` | Detail: price chart, sentiment timeline, recent posts, signals |
| `/signals` | All active/past buy signals with performance tracking |
| `/watchlist` | Manage watchlist, configure alerts |
| `/settings` | Profile, notification preferences, API keys |

## 9. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Next.js | 14.x |
| UI Framework | TailwindCSS + shadcn/ui | Latest |
| Charts | Recharts or Lightweight Charts (TradingView) | Latest |
| Backend | FastAPI (Python) | 0.110+ |
| Task Queue | Celery + Redis | 5.3+ |
| NLP | HuggingFace Transformers (FinBERT) | 4.x |
| NLP (fast) | vaderSentiment | 3.3+ |
| Ticker NER | spaCy (en_core_web_sm) | 3.x |
| Technical Analysis | pandas-ta | 0.3+ |
| Database | PostgreSQL + TimescaleDB | 16 + 2.x |
| Cache/Broker | Redis | 7.x |
| Auth | JWT (PyJWT) or AWS Cognito | — |
| Containerization | Docker + Docker Compose | Latest |
| Infrastructure | AWS (EC2 or ECS Fargate) | — |
| CI/CD | GitHub Actions | — |
| Monitoring | CloudWatch + optional Grafana | — |

## 10. AWS Deployment

### Option A: Single EC2 (Recommended for Personal Use)
- **Instance**: t3.small (2 vCPU, 2 GB RAM) — ~$15/mo
- **Storage**: 30 GB gp3 EBS
- **Setup**: Docker Compose with Nginx reverse proxy + Let's Encrypt SSL
- **Database**: PostgreSQL in Docker (or RDS db.t4g.micro for $13/mo)
- **Domain**: Route 53 ($0.50/mo) + ACM cert (free)
- **Total**: ~$30–50/mo

### Option B: ECS Fargate (If Scaling Later)
- Frontend + API + Worker as separate Fargate tasks
- RDS PostgreSQL + ElastiCache Redis
- ALB + ACM for HTTPS
- **Total**: ~$80–120/mo

### Security
- VPC with private subnets for DB/Redis
- Security groups: only ALB exposed publicly
- Secrets Manager for API keys
- CloudWatch alarms for anomalies

## 11. Development Phases

### Phase 1 — Foundation (Week 1–2)
- [ ] Project scaffolding (monorepo: `/backend`, `/frontend`, `/workers`)
- [ ] Docker Compose setup (FastAPI + Next.js + PostgreSQL + Redis)
- [ ] Database schema + migrations (Alembic)
- [ ] Reddit scraper (PRAW) + ticker extraction
- [ ] Basic VADER sentiment scoring
- [ ] `/api/trending` endpoint
- [ ] Minimal dashboard page showing top mentions

### Phase 2 — Intelligence (Week 3–4)
- [ ] FinBERT integration for improved sentiment
- [ ] StockTwits scraper
- [ ] Price data pipeline (yfinance + Finnhub)
- [ ] Technical indicators calculation
- [ ] Buy-signal engine v1 (RSI + sentiment threshold)
- [ ] Stock detail page with price chart + sentiment overlay
- [ ] Trending leaderboard with filters

### Phase 3 — User Features (Week 5–6)
- [ ] User auth (JWT or Cognito)
- [ ] Watchlist CRUD
- [ ] Alert/notification system
- [ ] Signal history + outcome tracking
- [ ] Pump-and-dump detection
- [ ] Google Trends integration
- [ ] News headlines integration (Finnhub)

### Phase 4 — Deploy & Polish (Week 7–8)
- [ ] AWS infrastructure setup (EC2 + Docker or ECS)
- [ ] CI/CD pipeline (GitHub Actions → deploy)
- [ ] SSL + domain setup
- [ ] Performance optimization (caching, lazy loading)
- [ ] Mobile-responsive design
- [ ] Backtesting past signals
- [ ] Paper-trading simulation mode

## 12. Configuration

```env
# .env.example
# Reddit
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=stock-sentinel/1.0

# StockTwits (no auth needed for public endpoints)
STOCKTWITS_BASE_URL=https://api.stocktwits.com/api/2

# Market Data
FINNHUB_API_KEY=
POLYGON_API_KEY=
ALPHA_VANTAGE_API_KEY=

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/stock_sentinel
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET=
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# AWS (for deployment)
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=

# Notifications
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
ALERT_EMAIL_FROM=
```

## 13. Success Metrics

- Sentiment accuracy: > 75% agreement with StockTwits crowd labels
- Signal hit rate: > 55% of buy signals reach target before stop/expiry
- Latency: trending page loads in < 2 seconds
- Data freshness: Reddit data no older than 15 minutes
- Uptime: > 99% (personal project tolerance)

## 14. Disclaimers

- This tool is for **informational purposes only** and does not constitute financial advice
- Past signal performance does not guarantee future results
- Users should conduct their own due diligence before making investment decisions
- The application does not manage any user funds
