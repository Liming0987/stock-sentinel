#!/usr/bin/env python3
"""Strategy Daily Review — generates a local HTML report for all 9 strategies.

Usage:
    python3 generate_report.py [--api-base URL] [--date YYYY-MM-DD]

Defaults:
    --api-base  http://34.201.111.94
    --date      today (local time)
"""

import argparse
import json
import os
import subprocess
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

STRATEGIES = [
    "momentum",
    "rsi_meanreversion",
    "bb_breakout",
    "macd_histogram",
    "fib_retracement",
    "elliott_fib",
    "vcp",
    "vwap_cross",
    "opening_range_breakout",
]

STRATEGY_LABELS = {
    "momentum":              "Momentum",
    "rsi_meanreversion":     "RSI Mean Reversion",
    "bb_breakout":           "BB Breakout",
    "macd_histogram":        "MACD Histogram",
    "fib_retracement":       "Fib Retracement",
    "elliott_fib":           "Elliott Wave + Fib",
    "vcp":                   "VCP",
    "vwap_cross":            "VWAP Cross",
    "opening_range_breakout":"Opening Range Breakout",
}

STRATEGY_TAGLINES = {
    "momentum":               "Buys stocks already in a confirmed uptrend with active MACD momentum.",
    "rsi_meanreversion":      "Buys the bounce when RSI crosses back above 30 after an oversold dip.",
    "bb_breakout":            "Buys when price breaks above the upper Bollinger Band with heavy volume.",
    "macd_histogram":         "Catches momentum shifts early — buys when the MACD histogram turns upward from negative.",
    "fib_retracement":        "Buys pullbacks to Fibonacci levels (38.2%, 50%, 61.8%) in an uptrend.",
    "elliott_fib":            "Enters Wave 4 pullbacks inside a confirmed 5-wave Elliott impulse.",
    "vcp":                    "Buys volume-confirmed breakouts after a coiling pattern of shrinking pullbacks (Minervini VCP).",
    "vwap_cross":             "Intraday: buys when price crosses above VWAP with a volume surge.",
    "opening_range_breakout": "Intraday: buys breakouts above the first 30-minute high with heavy volume.",
}

NOT_EXECUTED_REASONS = {
    "position_cap":        "Already holding the maximum number of positions for this strategy",
    "insufficient_funds":  "Not enough buying power available",
    "alpaca_error":        "Order placement failed (Alpaca error)",
    "confidence_too_low":  "Signal confidence was below the minimum threshold to trade",
    "market_closed":       "Market was closed when the signal fired",
    "already_in_position": "Already holding an open position in this stock for this strategy",
    "disabled":            "Strategy is currently disabled",
    "below_ema_200":       "Stock is below its 200-day moving average (downtrend filter)",
}

REPO_ROOT = Path(__file__).resolve().parents[4]
SPECS_DIR = REPO_ROOT / "openspec" / "specs" / "strategies"
OUTPUT_DIR = REPO_ROOT / "reports" / "strategy-review"


# ── Data fetching ─────────────────────────────────────────────────────────────

def fetch(url: str):
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ✗ Failed to fetch {url}: {e}", file=sys.stderr)
        return {}


def fetch_all_data(api_base: str) -> dict:
    print("Fetching strategy performance metrics…")
    strategies_resp = fetch(f"{api_base}/api/strategies")
    perf_by_name = {s["name"]: s for s in (strategies_resp if isinstance(strategies_resp, list) else [])}

    data = {}
    for name in STRATEGIES:
        print(f"  {STRATEGY_LABELS[name]}…")
        signals_resp = fetch(f"{api_base}/api/strategies/{name}/signals?limit=100")
        trades_resp  = fetch(f"{api_base}/api/strategies/{name}/trades?status=closed")

        signals = signals_resp.get("signals", []) if isinstance(signals_resp, dict) else []
        trades  = trades_resp.get("trades", [])   if isinstance(trades_resp, dict) else []

        data[name] = {
            "perf":    perf_by_name.get(name, {}),
            "signals": signals,
            "trades":  trades,
        }
    return data


# ── 30-day metrics ────────────────────────────────────────────────────────────

def compute_30d_metrics(trades: list) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent = []
    for t in trades:
        closed_at = t.get("closed_at")
        if not closed_at:
            continue
        try:
            dt = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
            if dt >= cutoff:
                recent.append(t)
        except Exception:
            continue

    if not recent:
        return {"count": 0}

    pnls  = [float(t["pnl"]) for t in recent if t.get("pnl") is not None]
    wins  = [p for p in pnls if p > 0]
    losses= [p for p in pnls if p <= 0]

    return {
        "count":       len(recent),
        "win_rate":    len(wins) / len(pnls) if pnls else 0,
        "total_pnl":   sum(pnls),
        "avg_win":     sum(wins) / len(wins) if wins else 0,
        "avg_loss":    sum(losses) / len(losses) if losses else 0,
        "wins":        len(wins),
        "losses":      len(losses),
    }


# ── Today's signals ───────────────────────────────────────────────────────────

def todays_signals(signals: list, report_date: str) -> list:
    result = []
    for s in signals:
        created = s.get("created_at", "")
        if created.startswith(report_date):
            result.append(s)
    return result


# ── not_executed_reason translation ──────────────────────────────────────────

def translate_reason(code) -> str:
    if not code:
        return ""
    return NOT_EXECUTED_REASONS.get(code, f'"{code}"')


# ── Strategy spec loader ──────────────────────────────────────────────────────

def load_spec(strategy_name: str) -> str:
    for subdir in ("swing", "intraday", ""):
        slug = strategy_name.replace("_", "-")
        candidates = [
            SPECS_DIR / subdir / slug / "spec.md",
            SPECS_DIR / slug / "spec.md",
        ]
        for path in candidates:
            if path.exists():
                return path.read_text()
    return ""


# ── Claude health summary ─────────────────────────────────────────────────────

def generate_health_summary(name: str, signals_today: list, metrics: dict, spec_text: str) -> str:
    try:
        import anthropic
    except ImportError:
        return "Install the anthropic package to enable health summaries: pip install anthropic"

    client = anthropic.Anthropic()

    signals_desc = "No signals today." if not signals_today else (
        f"{len(signals_today)} signal(s) today: " +
        ", ".join(
            f"{s.get('ticker','?')} {s.get('action','?')} (conf {float(s.get('confidence') or 0):.0%})"
            + (f" — skipped: {translate_reason(s.get('not_executed_reason'))}" if s.get("not_executed_reason") else " — executed")
            for s in signals_today
        )
    )

    if metrics.get("count", 0) == 0:
        metrics_desc = "No trades in the last 30 days."
    else:
        metrics_desc = (
            f"Last 30 days: {metrics['count']} trades, "
            f"{metrics['win_rate']:.0%} win rate, "
            f"total P&L ${metrics['total_pnl']:+.2f}, "
            f"avg win ${metrics['avg_win']:+.2f}, avg loss ${metrics['avg_loss']:+.2f}."
        )

    spec_section = f"\n\nStrategy spec for reference:\n{spec_text[:1500]}" if spec_text else ""

    prompt = (
        f"You are reviewing the {STRATEGY_LABELS[name]} trading strategy for a daily health check. "
        f"Write 2-3 sentences in plain English that a layman can understand. "
        f"Assess whether the strategy is performing as expected, note anything worth watching, "
        f"and be specific — reference the actual numbers. Do not use jargon.\n\n"
        f"Today's activity: {signals_desc}\n"
        f"Performance: {metrics_desc}"
        f"{spec_section}"
    )

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        return f"Could not generate summary: {e}"


# ── HTML rendering ────────────────────────────────────────────────────────────

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #fafafa; --surface: #ffffff; --border: #e5e7eb;
  --text: #111827; --muted: #6b7280; --faint: #9ca3af;
  --accent: #2563eb; --bullish: #16a34a; --bearish: #dc2626;
  --warn: #d97706; --radius: 8px; --shadow: 0 1px 3px rgba(0,0,0,.08);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1117; --surface: #1a1d27; --border: #2d3142;
    --text: #f0f2f5; --muted: #9ca3af; --faint: #6b7280;
    --accent: #60a5fa; --bullish: #4ade80; --bearish: #f87171;
    --warn: #fbbf24; --shadow: 0 1px 3px rgba(0,0,0,.4);
  }
}
body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
       background: var(--bg); color: var(--text); font-size: 15px;
       line-height: 1.6; padding: 2rem 1.5rem; }
.wrap { max-width: 860px; margin: 0 auto; }
h1 { font-size: 1.6rem; font-weight: 700; margin-bottom: .25rem; }
h2 { font-size: 1.1rem; font-weight: 600; margin-bottom: .75rem; }
h3 { font-size: .8rem; font-weight: 600; text-transform: uppercase;
     letter-spacing: .08em; color: var(--muted); margin-bottom: .5rem; }
p  { margin-bottom: .6rem; color: var(--muted); font-size: .9rem; }
.subtitle { color: var(--muted); font-size: .9rem; margin-bottom: 2rem; }
.strategy { background: var(--surface); border: 1px solid var(--border);
            border-radius: var(--radius); box-shadow: var(--shadow);
            padding: 1.5rem; margin-bottom: 1.5rem; }
.strategy-header { display: flex; align-items: baseline; gap: .75rem;
                   margin-bottom: .25rem; }
.strategy-name { font-size: 1.15rem; font-weight: 700; }
.strategy-type { font-size: .75rem; color: var(--faint);
                 background: var(--bg); border: 1px solid var(--border);
                 border-radius: 99px; padding: .1rem .55rem; }
.tagline { color: var(--muted); font-size: .88rem; margin-bottom: 1.1rem; }
.section { margin-top: 1rem; }
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: .75rem; margin-bottom: 1rem; }
.metric { background: var(--bg); border: 1px solid var(--border);
          border-radius: var(--radius); padding: .6rem .8rem; }
.metric-label { font-size: .72rem; color: var(--muted); font-weight: 600;
                text-transform: uppercase; letter-spacing: .06em; }
.metric-value { font-size: 1.1rem; font-weight: 700; margin-top: .1rem; }
.bullish { color: var(--bullish); }
.bearish { color: var(--bearish); }
.warn    { color: var(--warn); }
.neutral { color: var(--muted); }
table { width: 100%; border-collapse: collapse; font-size: .85rem; }
th { text-align: left; font-size: .72rem; font-weight: 600; color: var(--muted);
     text-transform: uppercase; letter-spacing: .06em; padding: .4rem .6rem;
     border-bottom: 1px solid var(--border); }
td { padding: .45rem .6rem; border-bottom: 1px solid var(--border); vertical-align: top; }
tr:last-child td { border-bottom: none; }
.tag { display: inline-block; font-size: .72rem; font-weight: 600;
       padding: .1rem .45rem; border-radius: 99px; }
.tag-buy     { background: #dcfce7; color: #166534; }
.tag-sell    { background: #fee2e2; color: #991b1b; }
.tag-hold    { background: #f3f4f6; color: #6b7280; }
.tag-exec    { background: #dbeafe; color: #1e40af; }
.tag-skip    { background: #fef3c7; color: #92400e; }
.health { background: var(--bg); border-left: 3px solid var(--accent);
          border-radius: 0 var(--radius) var(--radius) 0;
          padding: .75rem 1rem; font-size: .9rem; color: var(--text);
          line-height: 1.6; }
.empty { color: var(--faint); font-style: italic; font-size: .88rem; }
hr { border: none; border-top: 1px solid var(--border); margin: 1.25rem 0; }
.reasoning-list { list-style: none; padding: 0; }
.reasoning-list li::before { content: "· "; color: var(--muted); }
"""


def fmt_pnl(v: float) -> str:
    cls = "bullish" if v > 0 else ("bearish" if v < 0 else "neutral")
    return f'<span class="{cls}">${v:+.2f}</span>'


def render_metrics(metrics: dict) -> str:
    if metrics.get("count", 0) == 0:
        return '<p class="empty">No trades in the last 30 days.</p>'

    wr = metrics["win_rate"]
    wr_cls = "bullish" if wr >= 0.5 else ("warn" if wr >= 0.35 else "bearish")
    pnl_cls = "bullish" if metrics["total_pnl"] > 0 else "bearish"

    return f"""
<div class="metrics-grid">
  <div class="metric">
    <div class="metric-label">Trades (30d)</div>
    <div class="metric-value">{metrics['count']}</div>
  </div>
  <div class="metric">
    <div class="metric-label">Win Rate</div>
    <div class="metric-value {wr_cls}">{wr:.0%}</div>
  </div>
  <div class="metric">
    <div class="metric-label">Total P&amp;L</div>
    <div class="metric-value {pnl_cls}">${metrics['total_pnl']:+.2f}</div>
  </div>
  <div class="metric">
    <div class="metric-label">Avg Win</div>
    <div class="metric-value bullish">${metrics['avg_win']:+.2f}</div>
  </div>
  <div class="metric">
    <div class="metric-label">Avg Loss</div>
    <div class="metric-value bearish">${metrics['avg_loss']:+.2f}</div>
  </div>
  <div class="metric">
    <div class="metric-label">W / L</div>
    <div class="metric-value">{metrics['wins']} / {metrics['losses']}</div>
  </div>
</div>"""


def render_signals(signals: list) -> str:
    if not signals:
        return '<p class="empty">No signals today.</p>'

    rows = ""
    for s in signals:
        action = s.get("action", "hold").lower()
        tag_cls = {"buy": "tag-buy", "sell": "tag-sell"}.get(action, "tag-hold")
        conf = float(s.get("confidence") or 0)
        reason_code = s.get("not_executed_reason")
        executed = not reason_code
        exec_tag = (
            '<span class="tag tag-exec">Executed</span>'
            if executed else
            f'<span class="tag tag-skip">Skipped</span>'
        )
        reason_html = f'<div style="font-size:.8rem;color:var(--muted);margin-top:.2rem">{translate_reason(reason_code)}</div>' if reason_code else ""
        reasoning = s.get("reasoning") or []
        reasoning_html = ""
        if reasoning:
            items = "".join(f"<li>{r}</li>" for r in reasoning)
            reasoning_html = f'<ul class="reasoning-list">{items}</ul>'
        rows += f"""
<tr>
  <td><strong>{s.get('ticker','—')}</strong></td>
  <td><span class="tag {tag_cls}">{action.upper()}</span></td>
  <td>{conf:.0%}</td>
  <td>{reasoning_html}</td>
  <td>{exec_tag}{reason_html}</td>
</tr>"""

    return f"""
<table>
  <thead><tr>
    <th>Ticker</th><th>Action</th><th>Confidence</th><th>Why</th><th>Status</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>"""


def render_strategy_section(name: str, signals_today: list, metrics: dict, summary: str) -> str:
    label = STRATEGY_LABELS[name]
    tagline = STRATEGY_TAGLINES[name]
    stype = "Intraday" if name in ("vwap_cross", "opening_range_breakout") else "Swing"

    return f"""
<div class="strategy">
  <div class="strategy-header">
    <span class="strategy-name">{label}</span>
    <span class="strategy-type">{stype}</span>
  </div>
  <div class="tagline">{tagline}</div>

  <div class="section">
    <h3>Today's Signals</h3>
    {render_signals(signals_today)}
  </div>

  <hr>

  <div class="section">
    <h3>Last 30 Days</h3>
    {render_metrics(metrics)}
  </div>

  <hr>

  <div class="section">
    <h3>Health Summary</h3>
    <div class="health">{summary}</div>
  </div>
</div>"""


def render_html(report_date: str, sections) -> str:
    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Strategy Review — {report_date}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <h1>Strategy Daily Review</h1>
  <p class="subtitle">{report_date} &nbsp;·&nbsp; All 9 strategies</p>
  {body}
</div>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate strategy daily review HTML report.")
    parser.add_argument("--api-base", default="http://54.91.140.94", help="Backend API base URL")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Report date (YYYY-MM-DD)")
    args = parser.parse_args()

    api_base    = args.api_base.rstrip("/")
    report_date = args.date

    print(f"\nStrategy Daily Review — {report_date}")
    print(f"API: {api_base}\n")

    # Fetch all data
    data = fetch_all_data(api_base)

    # Build each strategy section
    print("\nGenerating health summaries…")
    sections = []
    for name in STRATEGIES:
        print(f"  {STRATEGY_LABELS[name]}…")
        d             = data[name]
        signals_today = todays_signals(d["signals"], report_date)
        metrics       = compute_30d_metrics(d["trades"])
        spec_text     = load_spec(name)
        summary       = generate_health_summary(name, signals_today, metrics, spec_text)
        sections.append(render_strategy_section(name, signals_today, metrics, summary))

    # Write HTML
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{report_date}.html"
    out_path.write_text(render_html(report_date, sections), encoding="utf-8")

    print(f"\n✓ Report written to: {out_path}")
    webbrowser.open(out_path.as_uri())


if __name__ == "__main__":
    main()
