# Stock Sentinel Daily — YouTube Digest Skill

A Claude Code skill that runs a full daily pipeline: pulls videos from configured finance YouTubers, downloads transcripts, has Claude analyze each one for ticker mentions and sentiment, and renders a static HTML report published to your Next.js site.

## What it does

1. **Fetches** new videos from a configured list of finance YouTubers via the YouTube Data API
2. **Downloads** auto-generated or manual transcripts, stripping sponsor reads
3. **Analyzes** each transcript directly in the Claude Code session (no external LLM API)
4. **Renders** a styled HTML report with consensus picks, per-channel summaries, and per-stock detail
5. **Commits and pushes** the report to `frontend/public/youtube-reports/` so Next.js serves it as a static file

## One-time setup

### 1. Get a YouTube Data API key

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create an API key with access to the **YouTube Data API v3**

### 2. Create `.env` in the repo root

```
YOUTUBE_API_KEY=AIza...
```

### 3. Install Python dependencies

```bash
cd .claude/skills/stock-sentinel-daily
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 4. Edit `config/youtubers.yaml`

Add the channels you want to follow. Each entry needs either a `channel_id` (preferred, stable) or a `handle` (like `@parkevtatevosiancfa9544`).

```yaml
youtubers:
  - handle: "@parkevtatevosiancfa9544"
    display_name: "Parkev Tatevosian, CFA"
    weight: 1.0
    include_shorts: false
    include_livestreams: false
    min_duration_seconds: 300
    enabled: true
```

Handles are resolved to channel IDs automatically on first run and cached in `data/channel_id_cache.json`.

## How to trigger

Just tell Claude Code in plain English:

> "Run the daily stock sentinel report"

> "Generate today's YouTube digest"

> "Pull stock mentions from YouTube"

Claude Code will load this skill and execute the full pipeline.

## Manual flags

You can include these in your request:

| Flag | Effect |
|------|--------|
| `--dry-run` | Run everything but skip the git commit/push |
| `--date 2026-06-15` | Backfill: treat this as "today" (fetches videos from 26h before this date) |
| `--channels @StockswithJosh,@DividendData` | Only process these channels |

Example: "Run the daily sentinel report for 2026-06-15, dry run only"

## Where output goes

- **Reports:** `frontend/public/youtube-reports/YYYY-MM-DD.html`
- **Index:** `frontend/public/youtube-reports/index.html`
- **Processed list:** `.claude/skills/stock-sentinel-daily/data/processed_videos.json`

Next.js serves the `public/` directory as static files, so after a push the report is immediately available at your site at `/youtube-reports/YYYY-MM-DD.html`.

## Directory structure

```
.claude/skills/stock-sentinel-daily/
  SKILL.md                  ← Runbook Claude follows at runtime
  README.md                 ← This file
  requirements.txt          ← Python dependencies
  .env.example              ← Copy to repo root as .env and fill in
  .gitignore                ← Excludes .env, .venv, workdir/
  config/
    youtubers.yaml          ← Channel list (edit this)
  data/
    processed_videos.json   ← Video IDs already covered (auto-managed)
    channel_id_cache.json   ← @handle → channel_id cache (auto-managed)
  scripts/
    fetch_videos.py         ← YouTube Data API: list new videos
    get_transcripts.py      ← youtube-transcript-api: download + clean
    generate_report.py      ← Render HTML from analysis JSONs
  templates/
    report.html.jinja       ← Jinja2 HTML template
    index_entry.html        ← Snippet appended to index listing
  workdir/                  ← Ephemeral (gitignored): transcripts, analyses, etc.
```

## Troubleshooting

**Missing transcripts**
Some videos have transcripts disabled or are age-restricted. These are logged to `workdir/transcripts/transcript_failures.json` and skipped. This is expected — the report is generated from whatever transcripts are available.

**YouTube API quota exceeded**
The YouTube Data API has a 10,000 unit/day quota. Each run uses roughly 3–6 units per channel. If you hit the quota (HTTP 403, `quotaExceeded`), Claude Code will stop and ask you how to proceed. You can wait until the quota resets (midnight Pacific) or set up a separate API key.

**Handle resolution failure**
If a `@handle` can't be resolved to a channel ID, the channel is skipped for that run. The resolution is retried on subsequent runs. You can also look up the channel ID manually in the YouTube URL and add it directly as `channel_id:` in `youtubers.yaml`.

**Deploy not triggering**
The skill commits to the `main` branch and pushes. If your deploy is triggered by pushes to a different branch, update Step 7 in `SKILL.md` accordingly.

**Stale workdir**
`workdir/` is ephemeral and gitignored. You can safely delete it between runs:
```bash
rm -rf .claude/skills/stock-sentinel-daily/workdir/
```
