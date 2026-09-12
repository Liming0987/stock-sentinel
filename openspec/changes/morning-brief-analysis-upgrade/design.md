## Context

The daily-recon skill is a Claude Code skill (SKILL.md runbook + Python scripts). Analysis data comes from the live backend API plus yfinance client-side in the skill script. The DCF fix is a pure backend serialisation change. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Scoring engine implemented as a Python function in the skill scripts (no new backend service)
- RS rating, earnings date, sector ETF return fetched from yfinance client-side
- DCF fields (`upside_pct`, `growth_rate`, `discount_rate`) surfaced from existing DCF service
- SKILL.md updated with scoring instructions for Claude
- HTML report updated to show new fields

**Non-Goals:**
- No new backend API endpoints
- No database schema changes
- No frontend changes

## Decisions

### 1. Scoring engine lives in the skill script, not the backend
The score is computed from data the skill already fetches. Adding it to the backend would require a new endpoint, new tests, and deployment — for what is essentially a pre-market CLI tool. Client-side in Python is simpler and faster to change.

### 2. RS rating computed from yfinance price history, not a data provider
IBD-style RS requires a subscription. We approximate with: weighted 12-week return vs SPY (40% Q1, 20% each Q2-Q4), then rank among watchlist stocks. Approximate but directionally correct for a small watchlist.

### 3. Sector ETF mapping hardcoded in the script
A static dict maps yfinance `sector` strings to sector ETFs (e.g. `"Technology" → "QQQ"`, `"Energy" → "XLE"`). Simple, no external dependency.

### 4. DCF fix is a one-line serialisation change
`upside_pct`, `growth_rate`, `discount_rate` are computed in `DCFService.analyze()` but the watchlist router was not returning them. Fix: include them in the response dict.

## Risks / Trade-offs

- **RS ranking with 2-stock watchlist**: ranking among 2 stocks produces scores of ~99 and ~1 — not meaningful. RS is most useful with 10+ stocks. Acceptable for now; show raw percentile vs SPY rather than rank-among-watchlist.
- **yfinance earnings date reliability**: `info["earningsDate"]` is sometimes a list, sometimes a timestamp, sometimes missing. Need robust parsing.
- **Score subjectivity**: the point allocations (10pts for EMA stack, etc.) are reasonable but not backtested. They can be tuned after observing a few weeks of output.

## Migration Plan

1. Fix DCF router (backend change — requires deploy)
2. Add scoring module to skill scripts
3. Update SKILL.md with scoring step
4. Update generate_stock_report.py to render new fields
5. No rollback needed — purely additive
