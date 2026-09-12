## 1. Project Setup

- [x] 1.1 Add `reports/` to `.gitignore` and verify `git status` shows no untracked files under `reports/` after creating a test file there
- [x] 1.2 Create `.claude/skills/strategy-review/` directory structure with `SKILL.md` and `scripts/` subdirectory — verify both paths exist

## 2. Data Fetching Script

- [x] 2.1 Implement `fetch_all_data(api_base)` in `generate_report.py` — fetches `/api/strategies`, then signals and trades for each strategy — verify it returns structured data for all 9 strategies when the backend is running
- [x] 2.2 Implement 30-day trade filtering — filter trades to the trailing 30 calendar days client-side and compute: win rate, total P&L, avg winner, avg loser, consecutive losses — verify metrics match manual calculation on sample data
- [x] 2.3 Implement `not_executed_reason` translation table — map known codes (position_cap, insufficient_funds, confidence_too_low, alpaca_error, market_closed) to plain English; unknown codes fall back to raw code in quotes — verify all known codes translate correctly

## 3. Claude Health Summary

- [x] 3.1 Implement `generate_health_summary(strategy_name, signals, metrics, spec_text)` — reads the strategy's spec from `openspec/specs/strategies/`, calls Claude API with signals + metrics + spec context, returns 2-3 sentence plain-English summary — verify output is readable and references the strategy by name
- [x] 3.2 Handle missing spec gracefully — if a strategy's spec file doesn't exist, call Claude without spec context rather than failing — verify the function succeeds for a strategy with no spec file

## 4. HTML Rendering

- [x] 4.1 Implement HTML template with self-contained CSS (no external dependencies) — one section per strategy with: strategy name, plain-English description, today's signals table, 30-day metrics, health summary — verify the file opens correctly in a browser without an internet connection
- [x] 4.2 Implement signal table rendering — show ticker, action, confidence (as percentage), reasoning bullets, executed/skipped status with plain-English not_executed_reason — verify all columns render for a sample signal
- [x] 4.3 Implement "No signals today" and "No trades in 30 days" empty states — verify both render correctly when data is absent

## 5. Skill Runbook

- [x] 5.1 Write `SKILL.md` runbook — documents trigger phrases, step-by-step execution (set API_BASE, run script, confirm output path), and prerequisites (backend must be running, Claude API key must be set) — verify the skill appears in `/skills` and Claude can follow the runbook to generate a report

## 6. End-to-End Verification

- [x] 6.1 Run the skill against the live backend at `http://54.91.140.94` — verify the HTML file is created at `reports/strategy-review/YYYY-MM-DD.html`, opens in the browser, shows all 9 strategies, and health summaries are in plain English
