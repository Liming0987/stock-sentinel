## Context

The backend already exposes all required data via three REST endpoints:
- `GET /api/strategies` — lifetime metrics per strategy (win rate, total P&L, consecutive losses, best/worst trade)
- `GET /api/strategies/{name}/signals?limit=N` — signal history with reasoning and not_executed_reason
- `GET /api/strategies/{name}/trades` — trade history with P&L, entry/exit, timestamps

The existing morning-brief skill (`/.claude/skills/morning-brief/`) is the closest pattern: it calls the API, calls Claude per item, and renders an HTML file. This skill follows the same structure. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Single Python script that fetches all data, calls Claude for health summaries, and renders HTML
- Skill runbook (SKILL.md) that Claude can follow to run the script
- Output at `reports/strategy-review/YYYY-MM-DD.html`, opened in browser, gitignored

**Non-Goals:**
- No backend changes — all endpoints already exist
- No scheduling — triggered manually; user can wire to a cron separately
- No publishing to the website
- No per-strategy HTML files — one file covers all 9

## Decisions

### 1. Single Python script, not a multi-file pipeline
The morning-brief skill uses separate `generate_stock_report.py` and `generate_index.py` scripts. For this feature, one script handles everything — data fetching, Claude calls, and HTML rendering. The report is simpler (one file, fixed set of 9 strategies vs. dynamic watchlist) and doesn't justify the split.

**Alternative:** Separate fetch/render modules. Rejected — unnecessary complexity for a single-output report.

### 2. Claude called once per strategy for the health summary
Each strategy gets an independent Claude API call that receives: the strategy's spec (from `openspec/specs/strategies/`), today's signals, and 30-day metrics. This keeps prompts focused and avoids a single massive prompt that mixes all 9 strategies.

**Alternative:** One Claude call for all 9 strategies. Rejected — harder to control output format and more likely to produce generic summaries.

### 3. 30-day window computed client-side from trade history
The `/api/strategies/{name}/trades` endpoint returns all trades. The script filters to the last 30 calendar days client-side. This avoids adding a `?days=30` query param to the backend.

**Alternative:** Add date filtering to the backend. Rejected — no backend changes is a hard constraint from the proposal.

### 4. not_executed_reason translation table in the script
A static dict maps known codes to plain English. Unknown codes fall back to displaying the raw code in quotes. The table lives in the script, not a config file — it's small and changes rarely.

### 5. HTML is self-contained (inline CSS, no external dependencies)
Same approach as morning-brief templates — no CDN links, no JS frameworks. The file must open correctly offline and without a web server.

## Risks / Trade-offs

- **API unavailable**: If the backend is down or not running locally, the script will fail with a clear error. Mitigation: check connectivity before fetching and print a helpful message.
- **Claude API latency**: 9 sequential Claude calls may take 30-60 seconds total. Acceptable for a daily report. Could be parallelised later if needed.
- **Stale strategy specs**: The health summary uses `openspec/specs/strategies/` as context. If a strategy is tuned but the spec isn't updated, the summary may reference outdated parameter rationale. Mitigation: the OpenSpec workflow keeps specs in sync when changes are archived.

## Migration Plan

1. Add `reports/` to `.gitignore`
2. Create `.claude/skills/strategy-review/SKILL.md`
3. Create `.claude/skills/strategy-review/scripts/generate_report.py`
4. Test by running the skill manually against the live backend
5. No rollback needed — new files only, no existing code changed
