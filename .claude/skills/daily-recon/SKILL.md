---
name: daily-recon
description: >
  Run the Stock Sentinel Daily Recon — a pre-market analysis report for every stock in the watchlist.
  Use this skill when the user says things like "run daily recon", "run the recon", "generate the pre-market report",
  "analyze my watchlist before market open", "what does my watchlist look like today", "daily stock analysis
  report", or any phrasing that implies generating a per-stock analysis to read before trading. The skill
  calls the live backend API for every stock, runs all analysis frameworks (Wyckoff, VCP, DCF, fundamentals,
  technicals, sentiment, strategy signals), searches the web for breaking news catalysts, synthesizes a
  Claude analysis per stock, renders per-stock HTML reports + an index page, commits everything to the repo,
  and pushes so the reports are live on the website. Do NOT use this for the YouTube digest (use
  stock-sentinel-daily for that) or for general stock questions.
---

# Stock Sentinel Daily Recon — Skill Runbook

## Purpose

Generate a pre-market intelligence report for every stock in the watchlist. Each stock gets:
- A structured Claude analysis synthesizing ALL available frameworks
- Breaking news + catalyst identification via web search
- An HTML report committed to `frontend/public/morning-briefs/YYYY-MM-DD/TICKER.html`
- An index page at `frontend/public/morning-briefs/index.html`

Run this daily at ~8:30 AM ET before the 9:30 AM market open.

---

## Step 1 — Setup

```bash
REPORT_DATE=$(date +%Y-%m-%d)
API_BASE="http://54.91.140.94"
REPO_ROOT="/Users/liming/Desktop/stock-sentinel"
OUT_DIR="$REPO_ROOT/frontend/public/morning-briefs/$REPORT_DATE"
mkdir -p "$OUT_DIR"
```

---

## Step 2 — Fetch the watchlist

```bash
curl -s "$API_BASE/api/watchlist" | python3 -m json.tool
```

Parse the `stocks` array. Each item has: `ticker`, `name`, `price`, `change_pct`, `sentiment_score`, `has_active_signal`.

If the watchlist is empty, tell the user and stop.

---

## Step 3 — For each stock, fetch all analysis data

Call these endpoints for every ticker (can run concurrently with curl &):

| Data | Endpoint |
|------|----------|
| Volume analysis (Wyckoff + VCP + OBV + history) | `GET /api/watchlist/{ticker}/volume-analysis?period=90d` |
| DCF valuation | `GET /api/watchlist/{ticker}/dcf` |
| Latest news (from backend) | `GET /api/watchlist/{ticker}/news?limit=10` |
| Fundamentals + grade | `GET /api/fundamentals/{ticker}` |
| Price data + indicators | `GET /api/prices/{ticker}?period=3M&interval=1d` |
| Sentiment history | `GET /api/sentiment/{ticker}?period=7d` |
| Active strategy signals | `GET /api/strategy-signals?limit=50` |

Save each response to a working JSON file per ticker. Suggested layout:
```
/tmp/daily-recon-YYYY-MM-DD/{TICKER}/volume.json
/tmp/daily-recon-YYYY-MM-DD/{TICKER}/dcf.json
/tmp/daily-recon-YYYY-MM-DD/{TICKER}/news.json
/tmp/daily-recon-YYYY-MM-DD/{TICKER}/fundamentals.json
/tmp/daily-recon-YYYY-MM-DD/{TICKER}/prices.json
/tmp/daily-recon-YYYY-MM-DD/{TICKER}/sentiment.json
```

---

## Step 4 — Web search for breaking news (Claude does this)

For each stock, use your **WebSearch** and **WebFetch** tools to find:
1. Any news from the last 24-48 hours about the company
2. Any sector/macro news that would affect this stock
3. Earnings dates, FDA approvals, product launches, analyst upgrades/downgrades

Search query pattern: `"{ticker} {company_name} stock news today"`

Then cross-reference: if the stock moved significantly (|change_pct| > 2%), try to find the catalyst. If the stock is near a Wyckoff resistance or VCP pivot, check if there's a news trigger. Write 2-3 sentences tying news to price action.

---

## Step 5 — Analyze each stock (Claude does this)

Read all the fetched data for a stock and synthesize a structured analysis. Think like a pre-market trader who has 5 minutes to size up each position.

### Analysis depth standard

The goal is the kind of layered, narrative analysis a skilled pre-market trader would write — not a data dump. Each analysis should read like this, structured from raw numbers up to story:

1. **The numbers** — specific quantitative facts: today's OHLCV with exact values, volume vs historical dataset (not just "elevated" but "248M = highest in the 90-day dataset, 4.69x avg, 3x the next-biggest spike"), RSI, MACD.
2. **The price action story** — what actually happened intraday: did it gap? reverse? close near high or low? How does it relate to recent structure (pullback, breakout, support test)?
3. **The catalyst** — news-driven or technical? If news-driven, which specific story and how does it tie to the price move? If organic, say so.
4. **The framework** — apply Wyckoff, VCP, absorption concepts explicitly by name. "This is a candidate Sign of Strength (SOS)" not "high volume bounce." Note what would confirm or invalidate the reading in coming sessions.

The `technical.summary`, `news_catalyst.summary`, and `wyckoff_narrative` fields are the main analytical content — write them as 3-5 paragraph prose, not 1-2 sentences.

### Analysis schema (write to `/tmp/daily-recon-YYYY-MM-DD/{TICKER}/analysis.json`):

```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "report_date": "2026-06-27",
  "price": 182.50,
  "change_pct": -1.2,
  "overall_stance": "watch | avoid | accumulate | hold",
  "conviction": 0.0,
  "one_liner": "Single punchy sentence: the pre-market verdict with the key number and the key reason",
  "price_action": {
    "open": 0.0,
    "high": 0.0,
    "low": 0.0,
    "close": 0.0,
    "volume": 0,
    "vol_ratio": 0.0,
    "vol_rank": "e.g. Highest in 90-day dataset | Top-3 spike | Above average",
    "intraday_story": "2-3 sentences: what happened intraday — gap, reversal, close position relative to range, and what that means structurally"
  },
  "news_catalyst": {
    "headline": "Most relevant news headline from the last 48 hours",
    "summary": "3-5 sentences: what happened, why it matters, how it ties to the price move and technical structure. Layer in context — sector dynamics, timing relative to key levels, whether this is news-driven or organic.",
    "source_url": "https://...",
    "sentiment": "bullish | bearish | neutral"
  },
  "technical": {
    "trend": "uptrend | downtrend | sideways",
    "wyckoff_phase": "from wyckoff.phase field",
    "wyckoff_bias": "bullish | bearish | neutral",
    "wyckoff_signals_detected": 3,
    "vcp_detected": true,
    "vcp_pivot": 185.0,
    "vcp_stage": "e.g. Stage 2 — 3 contractions",
    "key_support": 178.0,
    "key_resistance": 188.0,
    "rsi": 52.1,
    "macd_signal": "bullish crossover | bearish crossover | flat",
    "volume_ratio_today": 1.8,
    "volume_signal": "climactic | elevated | normal | drying up",
    "summary": "3-5 paragraphs: layer from raw numbers to story. Start with specific volume/price facts. Then zoom out to show where this sits in the longer structure (6-week pullback, ATH date/price, etc.). Then interpret — what is this candle telling us? What would confirm or invalidate the reading in the next 2-3 sessions? Name the Wyckoff event explicitly if applicable (SC, SOS, LPSY, etc.)."
  },
  "wyckoff_narrative": "2-3 paragraphs applying Wyckoff methodology explicitly. Name the events that have been tagged in the dataset. Describe the current phase. Say what the next expected event would be and what volume/price behavior would confirm it. Note any ambiguities or conflicting signals.",
  "valuation": {
    "feasible": true,
    "base_intrinsic_value": 210.0,
    "upside_pct": 15.0,
    "bear_value": 160.0,
    "bull_value": 260.0,
    "discount_rate": 0.095,
    "growth_rate": 0.12,
    "summary": "2-3 sentences: the DCF verdict with a caveat where relevant (e.g. capex distortion, ADR share count, pre-revenue stage). State whether the current price represents a margin of safety or not."
  },
  "fundamentals": {
    "grade": "B+",
    "score": 0.72,
    "key_strengths": ["Specific strength with a number if possible", "Another strength"],
    "key_concerns": ["Specific concern with a number if possible"],
    "summary": "2-3 sentences: what the grade reflects, what's driving the score up or down, and whether the fundamentals support or contradict the technical stance."
  },
  "sentiment": {
    "score": 0.35,
    "label": "Bullish | Bearish | Neutral",
    "mentions_24h": 45,
    "trend": "rising | falling | flat"
  },
  "strategy_signals": [
    {
      "strategy": "Momentum",
      "action": "buy",
      "confidence": 0.78,
      "entry_low": 180.0,
      "entry_high": 183.0,
      "stop_loss": 175.0,
      "target": 200.0
    }
  ],
  "risks": [
    "Specific risk with a number or condition: e.g. 'If volume dries up below 50M on the next session before holding $226, the absorption thesis fails'",
    "Another specific risk"
  ],
  "watchlist_priority": "high | medium | low"
}
```

### Stance guidance:
- **accumulate**: VCP detected + DCF has upside + fundamentals grade B or above + volume drying up (setup forming)
- **watch**: Mixed signals — technically interesting but one or more concerns (high valuation, bearish news)
- **hold**: Already in position, no new entry signal
- **avoid**: Bearish Wyckoff structure, DCF overvalued, or strong negative news catalyst

---

## Step 6 — Generate HTML report per stock

Use the script at `scripts/generate_stock_report.py`:

```bash
python3 "$REPO_ROOT/.claude/skills/daily-recon/scripts/generate_stock_report.py" \
  --analysis /tmp/daily-recon-$REPORT_DATE/{TICKER}/analysis.json \
  --output "$OUT_DIR/{TICKER}.html"
```

The script renders a clean, dark-themed HTML report using the template at `templates/stock_report.html`.

---

## Step 7 — Generate index page

After all per-stock reports are done:

```bash
python3 "$REPO_ROOT/.claude/skills/daily-recon/scripts/generate_index.py" \
  --date "$REPORT_DATE" \
  --analyses-dir /tmp/daily-recon-$REPORT_DATE/ \
  --output "$REPO_ROOT/frontend/public/morning-briefs/index.html" \
  --reports-dir "$OUT_DIR"
```

The index shows a card per stock sorted by `watchlist_priority` (high first), with the one-liner, stance badge, and price change.

---

## Step 8 — Commit and push

```bash
cd "$REPO_ROOT"
git add frontend/public/morning-briefs/
git commit -m "Daily recon $REPORT_DATE — {N} stocks analyzed"
git push origin main
```

If push fails due to upstream changes: `git pull --rebase && git push origin main`

---

## Step 9 — Summary to user

Report:
- Stocks analyzed (count)
- Top picks (accumulate stance)
- Any urgent alerts (active signals, large moves with news)
- URL to the index: `http://54.91.140.94/morning-briefs/index.html`

---

## Flags

| Flag | Behavior |
|------|----------|
| `--dry-run` | Skip git commit/push, print the report path |
| `--ticker AAPL,NVDA` | Only analyze specific tickers from the watchlist |
| `--date YYYY-MM-DD` | Use a specific date (backfill) |

---

## Error handling

- If an API endpoint returns an error for one stock, log it and continue with the others — don't abort the whole run.
- If DCF is `feasible: false`, skip the DCF section in the report (don't show "N/A" — just omit).
- If web search finds no recent news, write "No significant news in the last 48 hours."
- If all stocks fail, do not commit — report the errors to the user.
