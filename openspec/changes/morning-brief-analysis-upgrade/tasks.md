## 1. Backend — Fix DCF response

- [x] 1.1 In `backend/app/routers/watchlist.py`, update the `/api/watchlist/{ticker}/dcf` endpoint to include `upside_pct`, `growth_rate`, and `discount_rate` from the DCF service response — verify `curl http://54.91.140.94/api/watchlist/NVDA/dcf` returns all three fields

## 2. Skill — Scoring engine

- [x] 2.1 Create `.claude/skills/daily-recon/scripts/score.py` implementing `compute_score(indicators, wyckoff, vcp, fundamentals, dcf, signals, rs_rating, earnings_days)` → returns `{total, trend_health, fundamental_quality, timing_setup, stance, earnings_flag}` per the spec — verify with a unit-style manual test using hardcoded inputs
- [x] 2.2 Implement `compute_rs_rating(ticker, price_df, spy_df)` in `score.py` — weighted 12-week return vs SPY (40% Q1, 20% each Q2-Q4), returns 1–99 — verify NVDA gets a score > 50 when it has outperformed SPY
- [x] 2.3 Implement `compute_sector_momentum(sector)` in `score.py` — maps sector string to ETF (Technology→QQQ, Energy→XLE, etc.), fetches 4-week return from yfinance, returns `{etf, return_4w_pct, label}` — verify it returns a non-null result for "Technology"
- [x] 2.4 Implement `fetch_earnings_days(ticker)` in `score.py` — parses `yf.Ticker(ticker).info["earningsDate"]` robustly (handles list, single timestamp, or missing), returns days until next earnings or None — verify NVDA returns an integer

## 3. Skill — SKILL.md update

- [x] 3.1 Update `.claude/skills/daily-recon/SKILL.md` step 3 to fetch SPY price data alongside each ticker (needed for RS calculation), and add a new step between steps 4 and 5 that runs `score.py` and writes the score breakdown into the analysis JSON before Claude writes the narrative — verify the runbook is self-contained and Claude can follow it without ambiguity

## 4. Skill — HTML report update

- [x] 4.1 Update `.claude/skills/daily-recon/scripts/generate_stock_report.py` to render: RS rating badge near price header, score breakdown bar (trend/fundamental/timing sub-scores), earnings flag warning banner when `earnings_flag == "earnings_risk"`, sector momentum label — verify the HTML renders correctly by opening a sample report in the browser

## 5. End-to-end verification

- [x] 5.1 Run `/daily-recon` against the live backend — verify the generated HTML shows RS rating, score breakdown, and earnings proximity for NVDA and META; verify stance is not "watch" for both stocks if scores differ
