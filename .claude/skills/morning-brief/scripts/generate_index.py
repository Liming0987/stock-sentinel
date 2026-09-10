#!/usr/bin/env python3
"""
generate_index.py — Build the morning-briefs index page.

Usage:
    python3 generate_index.py \
        --date 2026-06-27 \
        --analyses-dir /tmp/morning-brief-2026-06-27/ \
        --output frontend/public/morning-briefs/index.html \
        --reports-dir frontend/public/morning-briefs/2026-06-27/
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

STANCE_ORDER = {"accumulate": 0, "watch": 1, "hold": 2, "avoid": 3}


def fmt_price(v):
    return f"${float(v):,.2f}" if v is not None else "—"


def fmt_pct(v):
    if v is None:
        return "—"
    prefix = "+" if float(v) >= 0 else ""
    return f"{prefix}{float(v):.1f}%"


def change_class(pct):
    return "up" if float(pct or 0) >= 0 else "down"


def stance_class(stance):
    return {"accumulate": "accumulate", "watch": "watch", "hold": "hold", "avoid": "avoid"}.get(stance, "neutral")


def build_index(date: str, analyses: list, reports_root: Path) -> str:
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    sorted_analyses = sorted(
        analyses,
        key=lambda a: (
            STANCE_ORDER.get(a.get("overall_stance", "watch"), 1),
            {"high": 0, "medium": 1, "low": 2}.get(a.get("watchlist_priority", "medium"), 1),
        ),
    )

    accumulate = [a for a in analyses if a.get("overall_stance") == "accumulate"]
    watch      = [a for a in analyses if a.get("overall_stance") == "watch"]
    avoid      = [a for a in analyses if a.get("overall_stance") == "avoid"]

    # Stock cards
    cards_html = ""
    for a in sorted_analyses:
        ticker  = a.get("ticker", "")
        stance  = a.get("overall_stance", "watch")
        sc      = stance_class(stance)
        chg     = a.get("change_pct", 0)
        tech    = a.get("technical", {})
        sent    = a.get("sentiment", {})
        signals = a.get("strategy_signals", [])
        priority = a.get("watchlist_priority", "medium")

        signal_badge = f'<span class="badge badge-signal">⚡ {len(signals)} signal{"s" if len(signals)!=1 else ""}</span>' if signals else ""
        vcp_badge    = '<span class="badge badge-vcp">VCP</span>' if tech.get("vcp_detected") else ""

        cards_html += f"""
<a href="{date}/{ticker}.html" class="stock-card">
  <div class="card-top">
    <span class="card-ticker">{ticker} {vcp_badge} {signal_badge}</span>
    <span class="pill pill-{sc}">{stance.upper()}</span>
  </div>
  <div class="card-company">{a.get('company_name','')}</div>
  <div class="card-price">
    {fmt_price(a.get('price'))}
    <span class="{change_class(chg)}" style="margin-left:6px;font-size:0.9rem">{fmt_pct(chg)}</span>
  </div>
  <div class="card-oneliner">{a.get('one_liner','')}</div>
  <div class="card-meta">
    {tech.get('wyckoff_phase','—')} &nbsp;·&nbsp;
    RSI {f"{tech.get('rsi'):.0f}" if isinstance(tech.get('rsi'), (int,float)) else '—'} &nbsp;·&nbsp;
    {sent.get('label','—')}
  </div>
</a>"""

    # Archive links
    date_dirs = sorted(
        [d.name for d in reports_root.iterdir() if d.is_dir()],
        reverse=True
    )
    archive_html = " ".join(
        f'<a href="{d}/index.html">{d}</a>'
        for d in date_dirs
        if (reports_root / d / "index.html").exists() or d == date
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stock Sentinel — Morning Brief {date}</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --bg:      #fafafa;  --surface: #ffffff;  --border:  #e5e7eb;
  --text:    #111827;  --muted:   #6b7280;  --faint:   #9ca3af;
  --accent:  #2563eb;  --bullish: #16a34a;  --bearish: #dc2626;
  --neutral: #6b7280;  --mixed:   #d97706;
  --radius:  8px;      --shadow:  0 1px 3px rgba(0,0,0,.08);
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg:      #0f1117;  --surface: #1a1d27;  --border:  #2d3142;
    --text:    #f0f2f5;  --muted:   #9ca3af;  --faint:   #6b7280;
    --accent:  #60a5fa;  --bullish: #4ade80;  --bearish: #f87171;
    --neutral: #9ca3af;  --mixed:   #fbbf24;
    --shadow:  0 1px 3px rgba(0,0,0,.4);
  }}
}}
body {{
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--bg); color: var(--text);
  font-size: 15px; line-height: 1.6; padding: 2rem 1.5rem;
}}
.wrap {{ max-width: 1060px; margin: 0 auto; }}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
hr {{ border: none; border-top: 1px solid var(--border); margin: 2rem 0; }}

/* header */
.kicker {{ font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--accent); margin-bottom: 0.4rem; }}
h1 {{ font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 0.3rem; }}
.meta {{ color: var(--muted); font-size: 0.82rem; margin-bottom: 1.25rem; }}

/* summary chips */
.chips {{ display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1.5rem; }}
.chip {{
  font-size: 0.78rem; font-weight: 600; padding: 0.3em 0.85em; border-radius: 99px;
  border: 1px solid;
}}
.chip-accumulate {{ color: var(--bullish); background: color-mix(in srgb, var(--bullish) 12%, transparent); border-color: color-mix(in srgb, var(--bullish) 30%, transparent); }}
.chip-watch      {{ color: var(--mixed);   background: color-mix(in srgb, var(--mixed)   12%, transparent); border-color: color-mix(in srgb, var(--mixed)   30%, transparent); }}
.chip-avoid      {{ color: var(--bearish); background: color-mix(in srgb, var(--bearish) 12%, transparent); border-color: color-mix(in srgb, var(--bearish) 30%, transparent); }}

/* nav */
nav {{ display: flex; gap: 1.25rem; font-size: 0.82rem; margin-bottom: 1.5rem; color: var(--muted); }}
nav a {{ color: var(--accent); }}

/* grid */
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}

/* stock card */
.stock-card {{
  display: block; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); box-shadow: var(--shadow);
  padding: 1rem 1.25rem; color: var(--text); text-decoration: none;
  transition: border-color 0.15s, transform 0.12s;
}}
.stock-card:hover {{ border-color: var(--accent); transform: translateY(-2px); text-decoration: none; }}
.card-top {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.3rem; gap: 0.5rem; }}
.card-ticker {{ font-family: "SF Mono","Fira Code",ui-monospace,monospace; font-weight: 700; font-size: 1rem; display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }}
.card-company {{ color: var(--muted); font-size: 0.78rem; margin-bottom: 0.5rem; }}
.card-price {{ font-family: "SF Mono","Fira Code",ui-monospace,monospace; font-size: 1.05rem; font-weight: 600; margin-bottom: 0.5rem; }}
.card-oneliner {{ font-size: 0.82rem; color: var(--muted); font-style: italic; margin-bottom: 0.5rem; line-height: 1.4; }}
.card-meta {{ font-size: 0.72rem; color: var(--faint); }}

/* pills */
.pill {{ display: inline-flex; align-items: center; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; padding: 0.2em 0.6em; border-radius: 99px; }}
.pill-accumulate {{ background: color-mix(in srgb, var(--bullish) 15%, transparent); color: var(--bullish); }}
.pill-watch      {{ background: color-mix(in srgb, var(--mixed)   15%, transparent); color: var(--mixed);   }}
.pill-hold       {{ background: color-mix(in srgb, var(--accent)  15%, transparent); color: var(--accent);  }}
.pill-avoid      {{ background: color-mix(in srgb, var(--bearish) 15%, transparent); color: var(--bearish); }}
.pill-neutral    {{ background: color-mix(in srgb, var(--neutral) 15%, transparent); color: var(--neutral); }}

/* small badges */
.badge {{ font-size: 0.62rem; font-weight: 700; padding: 0.15em 0.5em; border-radius: 4px; }}
.badge-signal {{ background: color-mix(in srgb, var(--accent) 15%, transparent); color: var(--accent); border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); }}
.badge-vcp    {{ background: color-mix(in srgb, var(--bullish) 12%, transparent); color: var(--bullish); border: 1px solid color-mix(in srgb, var(--bullish) 25%, transparent); }}

/* color helpers */
.up   {{ color: var(--bullish); }}
.down {{ color: var(--bearish); }}

/* archive */
.archive {{ margin-top: 1rem; }}
.archive-title {{ font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--faint); margin-bottom: 0.6rem; }}
.archive a {{ font-size: 0.82rem; margin-right: 1rem; }}

@media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="wrap">

  <div class="kicker">Stock Sentinel</div>
  <h1>Morning Brief — {date}</h1>
  <p class="meta">Generated {now_str} · {len(analyses)} stocks analyzed</p>

  <div class="chips">
    <span class="chip chip-accumulate">✓ {len(accumulate)} Accumulate</span>
    <span class="chip chip-watch">👁 {len(watch)} Watch</span>
    <span class="chip chip-avoid">✗ {len(avoid)} Avoid</span>
  </div>

  <nav>
    <a href="/">← Home</a>
    <a href="/youtube-reports/index.html">YouTube Digest</a>
  </nav>

  <div class="grid">
    {cards_html}
  </div>

  <hr>

  <div class="archive">
    <div class="archive-title">Past Reports</div>
    {archive_html or '<span style="color:var(--faint);font-size:0.82rem">No past reports yet</span>'}
  </div>

</div>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--analyses-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reports-dir", required=True)
    args = parser.parse_args()

    analyses_dir = Path(args.analyses_dir)
    analyses = []
    for ticker_dir in sorted(analyses_dir.iterdir()):
        if not ticker_dir.is_dir():
            continue
        f = ticker_dir / "analysis.json"
        if f.exists():
            try:
                analyses.append(json.loads(f.read_text()))
            except Exception as e:
                print(f"WARN  Skipping {ticker_dir.name}: {e}")

    if not analyses:
        print("ERROR No analysis files — aborting")
        return 1

    reports_root = Path(args.reports_dir).parent
    html = build_index(args.date, analyses, reports_root)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"INFO  Index written: {out}")

    dated_index = Path(args.reports_dir) / "index.html"
    Path(args.reports_dir).mkdir(parents=True, exist_ok=True)
    dated_index.write_text(html)
    print(f"INFO  Dated index written: {dated_index}")


if __name__ == "__main__":
    main()
