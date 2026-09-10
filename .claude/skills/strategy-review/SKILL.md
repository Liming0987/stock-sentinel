---
name: strategy-review
description: >
  Generate the Strategy Daily Review report — a local HTML file summarising how all 9
  trading strategies performed today and over the last 30 days, with plain-English health
  summaries written by Claude. Use when the user says things like "run the strategy review",
  "generate the strategy report", "how are my strategies doing", "daily strategy check",
  or any phrasing implying a review of strategy performance. Opens the HTML file in the
  browser automatically. Does NOT publish to the website.
---

# Strategy Daily Review — Skill Runbook

## Purpose

Generate a single local HTML report covering all 9 strategies:
- Today's signals (ticker, action, confidence, whether executed or skipped and why)
- Last 30 days of performance (win rate, P&L, avg win/loss)
- A 2-3 sentence plain-English health summary per strategy written by Claude

Output: `reports/strategy-review/YYYY-MM-DD.html` (gitignored, never published)

---

## Prerequisites

1. **Backend must be running** — the script calls the live API. Default: `http://54.91.140.94`. For local dev use `http://127.0.0.1:8001`.
2. **`anthropic` Python package** — needed for health summaries. Install if missing:
   ```bash
   pip3 install anthropic
   ```
3. **`ANTHROPIC_API_KEY`** — must be set in the environment. Check with:
   ```bash
   echo $ANTHROPIC_API_KEY
   ```

---

## Step 1 — Run the script

```bash
REPO_ROOT="/Users/liming/Desktop/stock-sentinel"
python3 "$REPO_ROOT/.claude/skills/strategy-review/scripts/generate_report.py"
```

To use a different backend (e.g. local):
```bash
python3 "$REPO_ROOT/.claude/skills/strategy-review/scripts/generate_report.py" \
  --api-base http://127.0.0.1:8001
```

To generate for a specific date:
```bash
python3 "$REPO_ROOT/.claude/skills/strategy-review/scripts/generate_report.py" \
  --date 2026-09-08
```

---

## Step 2 — Confirm output

The script prints progress as it runs and opens the report in the browser automatically when done:

```
Strategy Daily Review — 2026-09-09
API: http://54.91.140.94

Fetching strategy performance metrics…
  Momentum…
  RSI Mean Reversion…
  ...

Generating health summaries…
  Momentum…
  ...

✓ Report written to: /Users/liming/Desktop/stock-sentinel/reports/strategy-review/2026-09-09.html
```

If the browser doesn't open automatically, open the file manually:
```bash
open "$REPO_ROOT/reports/strategy-review/$(date +%Y-%m-%d).html"
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Failed to fetch /api/strategies` | Backend is not running or not reachable — check `http://54.91.140.94` |
| `Install the anthropic package` | Run `pip3 install anthropic` |
| Health summaries missing | `ANTHROPIC_API_KEY` is not set — export it before running |
| Report shows "No trades in 30 days" for all strategies | Normal on first run — no paper trades yet |
