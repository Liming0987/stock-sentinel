#!/usr/bin/env python3
"""
generate_stock_report.py — Render a per-stock HTML morning brief from analysis JSON.

Usage:
    python3 generate_stock_report.py \
        --analysis /tmp/morning-brief-2026-06-27/AAPL/analysis.json \
        --output /path/to/frontend/public/morning-briefs/2026-06-27/AAPL.html
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).parent.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "stock_report.html"


def stance_class(stance: str) -> str:
    return {"accumulate": "accumulate", "watch": "watch", "hold": "hold", "avoid": "avoid"}.get(stance, "neutral")


def sentiment_pill_class(score: float) -> str:
    if score > 0.1:
        return "bullish"
    if score < -0.1:
        return "bearish"
    return "neutral"


def fmt_price(v) -> str:
    if v is None:
        return "—"
    return f"${float(v):,.2f}"


def fmt_pct(v, sign=True) -> str:
    if v is None:
        return "—"
    prefix = "+" if sign and float(v) >= 0 else ""
    return f"{prefix}{float(v):.1f}%"


def render(analysis: dict, template: str) -> str:
    a = analysis
    tech = a.get("technical", {})
    val = a.get("valuation", {})
    fund = a.get("fundamentals", {})
    sent = a.get("sentiment", {})
    news = a.get("news_catalyst", {})
    signals = a.get("strategy_signals", [])
    risks = a.get("risks", [])

    stance = a.get("overall_stance", "watch")
    price = a.get("price", 0)
    chg = a.get("change_pct", 0)
    change_class = "change-up" if chg >= 0 else "change-down"

    # Strategy signals HTML
    signals_html = ""
    for sig in signals:
        action = sig.get("action", "").upper()
        action_color = "up" if sig.get("action") == "buy" else "down"
        conf_pct = int(float(sig.get("confidence", 0)) * 100)
        signals_html += f"""<div class="signal-card">
  <div class="signal-header">
    <span class="signal-name">{sig.get('strategy','')}</span>
    <span class="pill pill-{'accumulate' if sig.get('action') == 'buy' else 'avoid'}">{action}</span>
    <span class="signal-conf">{conf_pct}% confidence</span>
  </div>
  <div class="signal-levels">
    Entry: {fmt_price(sig.get('entry_low'))}–{fmt_price(sig.get('entry_high'))}
    &nbsp;·&nbsp; Stop: <span class="down">{fmt_price(sig.get('stop_loss'))}</span>
    &nbsp;·&nbsp; Target: <span class="up">{fmt_price(sig.get('target'))}</span>
  </div>
</div>"""
    if not signals_html:
        signals_html = '<p style="color:var(--muted);font-size:0.85rem">No active strategy signals</p>'

    # Risks HTML
    risks_html = "".join(f"<li>{r}</li>" for r in risks) if risks else "<li>No specific risks flagged</li>"

    # Wyckoff
    wy_score = tech.get("wyckoff_signals_detected", 0)
    wy_pct = int((wy_score / 5) * 100)
    wy_bias = tech.get("wyckoff_bias", "neutral")
    wy_bias_class = wy_bias if wy_bias in ("bullish", "bearish") else "neutral"

    # Fundamentals
    strengths_html = "".join(f"<li>{s}</li>" for s in fund.get("key_strengths", [])) or "<li>—</li>"
    concerns_html  = "".join(f"<li>{c}</li>" for c in fund.get("key_concerns", []))  or "<li>—</li>"

    # VCP
    if tech.get("vcp_detected"):
        vcp_html = f"""<div class="vcp-box">
  ✓ VCP Detected — Pivot: {fmt_price(tech.get('vcp_pivot'))}
  <small>{tech.get('vcp_stage', '')}</small>
</div>"""
    else:
        vcp_html = '<p style="color:var(--muted);font-size:0.85rem;margin:0.5rem 0">No VCP setup detected</p>'

    # DCF
    if val.get("feasible"):
        upside = val.get("upside_pct", 0)
        upside_class = "up" if float(upside) > 0 else "down"
        dcf_html = f"""<table class="metric-table">
  <tr><td>Intrinsic Value (base)</td><td>{fmt_price(val.get('base_intrinsic_value'))}</td></tr>
  <tr><td>Upside / Downside</td><td class="{upside_class}">{fmt_pct(upside)}</td></tr>
  <tr><td>Bear / Bull Range</td><td>{fmt_price(val.get('bear_value'))} – {fmt_price(val.get('bull_value'))}</td></tr>
  <tr><td>Discount Rate</td><td>{fmt_pct(float(val.get('discount_rate', 0))*100, sign=False)}</td></tr>
</table>
<p style="color:var(--muted);font-size:0.85rem;margin-top:0.75rem;margin-bottom:0">{val.get('summary', '')}</p>"""
    else:
        dcf_html = '<p style="color:var(--muted);font-size:0.85rem">DCF not applicable for this stock</p>'

    # News
    news_url = news.get("source_url", "")
    headline_text = news.get("headline", "No significant news found in the last 48 hours")
    news_headline = f'<a href="{news_url}" target="_blank" rel="noopener">{headline_text}</a>' if news_url else headline_text
    news_sent = news.get("sentiment", "neutral").lower()
    news_sent_class = {"bullish": "bullish", "bearish": "bearish"}.get(news_sent, "neutral")

    # Sentiment pill class
    sent_score = float(sent.get("score", 0))
    sent_label = sent.get("label", "Neutral")
    sent_pill = sentiment_pill_class(sent_score)

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return template.format(
        TICKER=a.get("ticker", ""),
        COMPANY_NAME=a.get("company_name", ""),
        REPORT_DATE=a.get("report_date", ""),
        GENERATED_AT=now_str,
        PRICE=fmt_price(price),
        CHANGE_PCT=fmt_pct(chg),
        CHANGE_CLASS=change_class,
        STANCE=stance.upper(),
        STANCE_CLASS=stance_class(stance),
        CONVICTION=int(float(a.get("conviction", 0)) * 100),
        ONE_LINER=a.get("one_liner", ""),
        GRADE=fund.get("grade", "N/A"),
        PRIORITY=a.get("watchlist_priority", "medium").upper(),
        PRIORITY_CLASS=a.get("watchlist_priority", "medium").lower(),
        # Technical
        TREND=tech.get("trend", "—").capitalize(),
        WYCKOFF_PHASE=tech.get("wyckoff_phase", "—"),
        WYCKOFF_BIAS=wy_bias.capitalize(),
        WY_SCORE=wy_score,
        WY_PCT=wy_pct,
        WY_BIAS_CLASS=wy_bias_class,
        VCP_HTML=vcp_html,
        KEY_SUPPORT=fmt_price(tech.get("key_support")),
        KEY_RESISTANCE=fmt_price(tech.get("key_resistance")),
        RSI=f"{tech.get('rsi'):.1f}" if isinstance(tech.get("rsi"), (int, float)) else "—",
        MACD_SIGNAL=tech.get("macd_signal", "—"),
        VOL_RATIO=f"{tech.get('volume_ratio_today'):.2f}×" if isinstance(tech.get("volume_ratio_today"), (int, float)) else "—",
        VOL_SIGNAL=tech.get("volume_signal", "—").capitalize(),
        TECH_SUMMARY=tech.get("summary", ""),
        # DCF
        DCF_HTML=dcf_html,
        # Fundamentals
        STRENGTHS_HTML=strengths_html,
        CONCERNS_HTML=concerns_html,
        FUND_SUMMARY=fund.get("summary", ""),
        # Sentiment
        SENT_SCORE=f"{sent_score:+.2f}",
        SENT_LABEL=sent_label,
        SENT_PILL_CLASS=sent_pill,
        MENTIONS_24H=sent.get("mentions_24h", 0),
        SENT_TREND=sent.get("trend", "flat").capitalize(),
        # News
        NEWS_HEADLINE=news_headline,
        NEWS_SUMMARY=news.get("summary", ""),
        NEWS_SENT_CLASS=news_sent_class,
        NEWS_SENTIMENT=news_sent.upper(),
        # Signals & risks
        SIGNALS_HTML=signals_html,
        RISKS_HTML=risks_html,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    analysis = json.loads(Path(args.analysis).read_text())
    template = TEMPLATE_PATH.read_text()
    html = render(analysis, template)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"INFO  Report written: {args.output}")
    # Also copy analysis JSON alongside HTML so the Next.js page can read it
    ticker_dir = out.parent / analysis.get("ticker", out.stem)
    ticker_dir.mkdir(parents=True, exist_ok=True)
    (ticker_dir / "analysis.json").write_text(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    main()
