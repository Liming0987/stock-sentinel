## Why

There is no daily feedback loop on whether the trading strategies are working. Performance metrics exist in the database but are only visible via the web UI, and today's signals require navigating multiple API endpoints. A daily local HTML report — triggered as a skill — gives a single plain-English read on all 9 strategies without needing to open the website or interpret raw numbers.

## What Changes

- New Claude Code skill `strategy-review` that can be triggered manually or on a daily schedule
- Fetches today's signals, 30-day trade history, and lifetime performance metrics for all 9 strategies via the existing backend API
- Calls Claude to write a 2-3 sentence plain-English health summary per strategy
- Renders a single self-contained HTML file at `reports/strategy-review/YYYY-MM-DD.html` and opens it in the browser
- Translates internal `not_executed_reason` codes into plain-English explanations
- Report is local-only — not committed, not published to the website

## Capabilities

### New Capabilities

- `tools/strategy-review`: Daily HTML report skill — fetches strategy signals, trades, and performance metrics; generates plain-English health summaries per strategy; renders to a local HTML file

### Modified Capabilities

_(none — no existing spec-level behavior changes)_

## Impact

- **New file:** `.claude/skills/strategy-review/SKILL.md` (skill runbook)
- **New file:** `.claude/skills/strategy-review/scripts/generate_report.py` (data fetching + HTML rendering)
- **New directory:** `reports/strategy-review/` (output, gitignored)
- **Reads:** existing backend API endpoints — `/api/strategies`, `/api/strategies/{name}/signals`, `/api/strategies/{name}/trades`
- **Reads:** `openspec/specs/strategies/` for strategy descriptions used in Claude's health summaries
- **No backend changes** — all data is already available via existing endpoints
- **No frontend changes** — output is a local file only
