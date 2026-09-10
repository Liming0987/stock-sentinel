---
name: stock-sentinel-daily
description: Use this skill when the user asks to run the daily stock sentinel report, generate today's stock YouTube digest, pull stock mentions from YouTube, analyze finance YouTube videos, or any phrasing indicating they want the daily YouTube-stock-analysis pipeline to run. Fetches latest videos from configured finance YouTubers, downloads transcripts, has Claude analyze each one for ticker mentions and sentiment, renders an HTML report, and commits to the repo to publish. Do NOT trigger for general stock questions, requests about the trading strategies system, or requests about the Alpaca/backtesting pipelines.
---

# Stock Sentinel Daily — Skill Runbook

## When to use this skill

Trigger when the user says something like:
- "run the daily stock sentinel report"
- "generate today's YouTube digest"
- "pull stock mentions from YouTube"
- "run the stock YouTube pipeline"

Do **not** trigger for general questions about stocks, the backtesting system, or the trading strategies in `backend/app/strategies/`.

---

## Overview

All scripts live in `.claude/skills/stock-sentinel-daily/scripts/` and run from the **skill root** (`.claude/skills/stock-sentinel-daily/`). The Python venv is at `.claude/skills/stock-sentinel-daily/.venv/`.

Report output: `frontend/public/youtube-reports/YYYY-MM-DD.html`
Index output: `frontend/public/youtube-reports/index.html`

---

## Prerequisites check

Before running anything:

1. **`.env` exists** in the repo root (or any parent up to 6 levels). Check:
   ```bash
   ls /Users/liming/Desktop/stock-sentinel/.env 2>/dev/null || echo "MISSING"
   ```
   If missing, tell the user: "Please create `.env` in the repo root with `YOUTUBE_API_KEY=<your key>`."

2. **Python venv** is ready. Check:
   ```bash
   .venv/bin/python --version 2>/dev/null || echo "MISSING"
   ```
   If missing, create it:
   ```bash
   cd .claude/skills/stock-sentinel-daily
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt -q
   ```

3. **`config/youtubers.yaml`** has at least one `enabled: true` entry. If all are disabled, tell the user before proceeding.

---

## Execution steps

All commands run from `.claude/skills/stock-sentinel-daily/` unless noted.

### Step 1 — Set the date

Determine today's date in YYYY-MM-DD format (or use `--date` flag if the user passed one):
```bash
REPORT_DATE=$(date +%Y-%m-%d)
```

Create the workdir:
```bash
mkdir -p workdir/transcripts workdir/analyses
```

### Step 2 — Fetch new videos

```bash
.venv/bin/python scripts/fetch_videos.py \
  --since-hours 26 \
  --output workdir/new_videos.json
```

If `--channels A,B,C` was passed by the user, append: `--channels A,B,C`

If the YouTube API quota error appears (HTTP 403, quotaExceeded), stop immediately and tell the user. Do not continue.

If zero videos are found, tell the user and stop (don't generate an empty report).

### Step 3 — Get transcripts

```bash
.venv/bin/python scripts/get_transcripts.py \
  --input workdir/new_videos.json \
  --output workdir/transcripts/
```

Videos without transcripts are logged to `workdir/transcripts/transcript_failures.json` and skipped automatically. That's expected — continue.

### Step 4 — Analyze each transcript (YOU do this, Claude)

For each `.txt` file in `workdir/transcripts/` (skip `transcript_failures.json`):

1. Read the transcript file with the Read tool
2. Read the corresponding video metadata from `workdir/new_videos.json` (match by filename stem = video_id)
3. Analyze the transcript directly — **do not call any external API**. You are the analyst.
4. Write the analysis JSON to `workdir/analyses/<video_id>.json`

Follow the schema exactly:

```json
{
  "video_id": "string",
  "channel_name": "string",
  "video_title": "string",
  "video_url": "string",
  "published_at": "ISO 8601 string",
  "duration_minutes": 0,
  "summary": "3-5 paragraph detailed summary. Cover: creator's main thesis, stocks/sectors discussed, overall market view, specific recommendations or warnings. Prose, not bullets.",
  "macro_topics": ["string"],
  "stocks": [
    {
      "symbol": "NVDA",
      "company_name": "NVIDIA Corp",
      "sentiment": "bullish | bearish | neutral | mixed",
      "conviction": 0.75,
      "thesis": "1-2 sentences on why the creator holds this view",
      "price_target": "string or null",
      "key_points": ["Paraphrased point (never verbatim)", "Another point"],
      "time_spent_estimate_minutes": 3
    }
  ],
  "key_theses": ["Top 3-5 overall takeaways"],
  "warnings_or_risks": ["Bearish points or risks the creator raised"]
}
```

**Analysis rules:**
- A stock mention requires the creator to be discussing a specific publicly-traded company or ETF. General sector talk without a name does not count.
- At least one of `symbol` or `company_name` is required per stock. Prefer both. If only a ticker was said, set `symbol` and `company_name: null`. If only a company name, set `company_name` and `symbol: null`.
- Uppercase symbols only. Don't guess tickers — leave `symbol: null` if uncertain.
- Ignore stocks mentioned only in sponsor reads or disclaimers.
- Ambiguous tickers ("IT", "A") — only include if context clearly establishes them as stock references.
- `conviction` (0.0–1.0): time spent + directness + tonal confidence.
- `key_points` must be **paraphrased** — never copy verbatim from the transcript.
- Strip sponsor reads: skip analysis of stocks mentioned after phrases like "this video is brought to you by", "use code", "check the link in the description".

After writing each analysis file, print a brief confirmation: `✓ Analyzed: <video_title> → workdir/analyses/<video_id>.json`

### Step 5 — Generate HTML report

```bash
.venv/bin/python scripts/generate_report.py \
  --analyses-dir workdir/analyses/ \
  --videos workdir/new_videos.json \
  --date "$REPORT_DATE" \
  --output ../../../frontend/public/youtube-reports/"$REPORT_DATE".html \
  --index ../../../frontend/public/youtube-reports/index.html
```

If zero analysis JSONs exist (all transcripts failed), do not run this step. Tell the user.

### Step 6 — Update processed video list

Append the video IDs from `workdir/new_videos.json` to `data/processed_videos.json` so they are not reprocessed on future runs:

```bash
.venv/bin/python - <<'PYEOF'
import json
from pathlib import Path

new_path = Path("workdir/new_videos.json")
proc_path = Path("data/processed_videos.json")

new_ids = [v["video_id"] for v in json.loads(new_path.read_text())]
existing = json.loads(proc_path.read_text()) if proc_path.exists() else []
updated = list(dict.fromkeys(existing + new_ids))  # deduplicate, preserve order
proc_path.write_text(json.dumps(updated, indent=2))
print(f"Recorded {len(new_ids)} video IDs → {proc_path}")
PYEOF
```

### Step 7 — Commit and push

Unless `--dry-run` was passed by the user:

```bash
cd /Users/liming/Desktop/stock-sentinel
git add frontend/public/youtube-reports/
git add .claude/skills/stock-sentinel-daily/data/processed_videos.json
git commit -m "Stock Sentinel daily report $REPORT_DATE"
git push
```

If the user said `--dry-run`, skip this step and instead show the path to the generated report file.

### Step 8 — Summary to user

Print:
- Number of videos processed
- Number of stocks identified
- Top 3 consensus picks (stocks mentioned by 2+ channels), if any
- Path to the generated report
- Whether git push succeeded

---

## Flags the user may pass

| Flag | Behavior |
|------|----------|
| `--dry-run` | Run everything but the git commit/push |
| `--date YYYY-MM-DD` | Use this date instead of today (for backfill) |
| `--channels A,B,C` | Only process specific channel handles or IDs from config |

---

## Failure handling

- Individual video failures (transcript unavailable, analysis write error) do not halt the run. Log and continue.
- If zero videos make it through to HTML render, do not commit — just report how many failed and why.
- YouTube quota error (HTTP 403 quotaExceeded): stop immediately, log, ask the user how to proceed.
- If git push fails due to upstream changes, run `git pull --rebase` and try pushing again once. If it still fails, report to the user.
