## Why

The morning brief's current analysis framework defaults to "watch" for nearly every stock because Wyckoff events rarely fire and social sentiment data is empty — making the buy/sell recommendations too vague to act on. The framework also lacks the two highest-signal inputs missing from every report: relative strength vs the market, and earnings proximity risk.

## What Changes

- **New: Relative Strength (RS) rating** — computed from yfinance price history, ranks each stock's 12-week performance vs SPY on a 1–99 scale; added to the analysis schema and shown in the report
- **New: Earnings proximity** — fetches next earnings date from yfinance; overrides stance to "watch" when < 5 days out; flags as catalyst opportunity at 5–14 days
- **New: Sector relative strength** — computes the stock's sector ETF performance (4-week return) from yfinance; shown as context in the report
- **Fix: DCF response fields** — `upside_pct`, `growth_rate`, and `discount_rate` are present in the DCF service but missing from the API response serialisation; surfaced so Claude can write a complete DCF verdict
- **Rework: Stance scoring** — replace the binary accumulate/watch/hold/avoid with a 0–100 scored framework across three dimensions (Trend Health 0–30, Fundamental Quality 0–30, Timing/Setup 0–40); thresholds: 75+ = accumulate, 50–74 = watch, below 50 = avoid; computed by the skill before Claude writes the narrative

## Capabilities

### New Capabilities

- `tools/daily-recon-scoring`: Quantitative 0–100 scoring engine for the morning brief — computes Trend Health, Fundamental Quality, and Timing/Setup scores from existing API data and new RS/earnings/sector inputs

### Modified Capabilities

- `tools/daily-recon`: Morning brief skill — updated analysis schema (adds `rs_rating`, `earnings_days`, `sector_momentum`, scored breakdown), updated stance logic, updated SKILL.md runbook steps 3–5

## Impact

- **Modified:** `.claude/skills/morning-brief/SKILL.md` — updated analysis schema, stance guidance, and scoring instructions
- **Modified:** `.claude/skills/morning-brief/scripts/generate_stock_report.py` — render RS rating, earnings flag, sector momentum, and score breakdown in HTML
- **Modified:** `backend/app/routers/watchlist.py` — surface missing DCF fields (`upside_pct`, `growth_rate`, `discount_rate`) in the `/api/watchlist/{ticker}/dcf` response
- **No new backend services** — RS rating, earnings date, and sector momentum are all computed client-side in the skill script from yfinance data
- **No schema changes** — purely additive to the analysis JSON written by Claude
