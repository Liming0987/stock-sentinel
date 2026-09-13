## Why

The morning brief's current analysis framework defaults to "watch" for nearly every stock because Wyckoff events rarely fire and social sentiment data is empty — making the buy/sell recommendations too vague to act on. The framework also lacks the two highest-signal inputs missing from every report: relative strength vs the market, and earnings proximity risk.

## What Changes

- **New: Relative Strength (RS) rating** — computed from yfinance price history, ranks each stock's 12-week performance vs SPY on a 1–99 scale; added to the analysis schema and shown in the report
- **New: Earnings proximity** — fetches next earnings date from yfinance; overrides stance to "watch" when < 5 days out; flags as catalyst opportunity at 5–14 days
- **New: Sector relative strength** — computes the stock's sector ETF performance (4-week return) from yfinance; shown as context in the report
- **Fix: DCF response fields** — `upside_pct`, `growth_rate`, and `discount_rate` are present in the DCF service but missing from the API response serialisation; surfaced so Claude can write a complete DCF verdict
- **Rework: Stance scoring** — replace the binary accumulate/watch/hold/avoid with a 0–100 scored framework across three dimensions (Trend Health 0–30, Fundamental Quality 0–30, Timing/Setup 0–40); thresholds: 75+ = accumulate, 50–74 = watch, below 50 = avoid; computed by the skill before Claude writes the narrative
- **New: Financial statements** — fetch the 4 most recent quarters of balance sheet, income statement, and cash flow from yfinance; summarise key red flags (margin deterioration, rising debt, FCF diverging from net income) and pass into Claude's analysis context for deeper growth and financial health assessment
- **Fix: Sector momentum plain-English explanation** — the HTML report now shows a human-readable note explaining what "QQQ -3.2% (4w)" means (e.g. "fund managers are rotating money out of this sector, creating headwinds for individual stocks") so a layman can understand it without knowing what a sector ETF is

## Capabilities

### New Capabilities

- `tools/daily-recon-scoring`: Quantitative 0–100 scoring engine for the morning brief — computes Trend Health, Fundamental Quality, and Timing/Setup scores from existing API data and new RS/earnings/sector inputs

### Modified Capabilities

- `tools/daily-recon`: Morning brief skill — updated analysis schema (adds `rs_rating`, `earnings_days`, `sector_momentum`, scored breakdown), updated stance logic, updated SKILL.md runbook steps 3–5

## Impact

- **Modified:** `.claude/skills/morning-brief/SKILL.md` — updated analysis schema, stance guidance, and scoring instructions
- **Modified:** `.claude/skills/morning-brief/scripts/generate_stock_report.py` — render RS rating, earnings flag, sector momentum, and score breakdown in HTML
- **Modified:** `backend/app/routers/watchlist.py` — surface missing DCF fields (`upside_pct`, `growth_rate`, `discount_rate`) in the `/api/watchlist/{ticker}/dcf` response
- **New file:** `.claude/skills/daily-recon/scripts/financials.py` — fetches and summarises 4-quarter financial statements via yfinance; flags margin deterioration, debt increases, FCF/NI divergence
- **Modified:** `.claude/skills/daily-recon/SKILL.md` — new step to run financials.py and include summary in analysis context
- **Modified:** `.claude/skills/daily-recon/scripts/generate_stock_report.py` — render financial health summary section in HTML; add plain-English sector momentum explanation
- **No new backend services** — financial statements fetched client-side via yfinance in the skill script
- **No schema changes** — purely additive to the analysis JSON written by Claude
