#!/usr/bin/env python3
"""
generate_report.py — Render the daily HTML report from analysis JSONs.

Usage:
    python scripts/generate_report.py \\
        --analyses-dir workdir/analyses/ \\
        --videos workdir/new_videos.json \\
        --date 2026-06-19 \\
        --output ../../../frontend/public/youtube-reports/2026-06-19.html \\
        --index ../../../frontend/public/youtube-reports/index.html
    python scripts/generate_report.py --help
"""

import argparse
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

SKILL_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

SENTIMENT_SCORE = {"bullish": 1, "mixed": 0, "neutral": 0, "bearish": -1}


def normalize_company_name(name: str) -> str:
    if not name:
        return ""
    # Strip common suffixes for deduplication
    name = name.lower().strip()
    for suffix in [" inc", " corp", " ltd", " llc", " plc", " co", ".", ","]:
        name = name.rstrip(suffix)
    return name.strip()


def canonical_stock_key(stock: dict) -> str:
    """Canonical key for deduplication: prefer symbol, fall back to normalized name."""
    if stock.get("symbol"):
        return stock["symbol"].upper()
    return normalize_company_name(stock.get("company_name", ""))


def compute_consensus(analyses: list, videos_by_id: dict) -> list:
    """
    Group stock mentions across all analyses, compute weighted sentiment.
    Only include stocks mentioned by >= 2 distinct channels.
    """
    # stocks_data[key] = {symbol, company_name, mentions: [{channel, sentiment, conviction, thesis, ...}]}
    stocks_data: dict[str, dict] = {}

    for analysis in analyses:
        channel = analysis.get("channel_name", "Unknown")
        for stock in analysis.get("stocks", []):
            key = canonical_stock_key(stock)
            if not key:
                continue
            if key not in stocks_data:
                stocks_data[key] = {
                    "symbol": stock.get("symbol"),
                    "company_name": stock.get("company_name"),
                    "channels": set(),
                    "mentions": [],
                }
            entry = stocks_data[key]
            # Update symbol/name if we have better info
            if stock.get("symbol") and not entry["symbol"]:
                entry["symbol"] = stock["symbol"]
            if stock.get("company_name") and not entry["company_name"]:
                entry["company_name"] = stock["company_name"]
            entry["channels"].add(channel)
            entry["mentions"].append({
                "channel": channel,
                "sentiment": stock.get("sentiment", "neutral"),
                "conviction": float(stock.get("conviction", 0.5)),
                "thesis": stock.get("thesis", ""),
                "key_points": stock.get("key_points", []),
                "price_target": stock.get("price_target"),
                "video_id": analysis.get("video_id"),
                "video_title": analysis.get("video_title"),
                "video_url": analysis.get("video_url"),
            })

    consensus = []
    for key, data in stocks_data.items():
        channel_count = len(data["channels"])
        if channel_count < 2:
            continue

        mentions = data["mentions"]
        weighted_score = sum(
            SENTIMENT_SCORE.get(m["sentiment"], 0) * m["conviction"]
            for m in mentions
        )
        avg_sentiment_score = weighted_score / len(mentions) if mentions else 0

        # Pick the highest-conviction thesis
        best_mention = max(mentions, key=lambda m: m["conviction"])

        # Overall sentiment label
        if avg_sentiment_score >= 0.4:
            overall_sentiment = "bullish"
        elif avg_sentiment_score <= -0.4:
            overall_sentiment = "bearish"
        elif avg_sentiment_score > 0:
            overall_sentiment = "mixed"
        else:
            overall_sentiment = "neutral"

        consensus.append({
            "symbol": data["symbol"],
            "company_name": data["company_name"],
            "display": data["symbol"] or data["company_name"] or key,
            "channel_count": channel_count,
            "channels": sorted(data["channels"]),
            "weighted_score": round(weighted_score, 3),
            "avg_sentiment_score": round(avg_sentiment_score, 3),
            "overall_sentiment": overall_sentiment,
            "avg_conviction": round(sum(m["conviction"] for m in mentions) / len(mentions), 2),
            "top_thesis": best_mention["thesis"],
            "mentions": mentions,
        })

    # Sort by absolute weighted score descending
    consensus.sort(key=lambda x: abs(x["weighted_score"]), reverse=True)
    return consensus



def parse_args():
    p = argparse.ArgumentParser(description="Render daily HTML report from analysis JSONs.")
    p.add_argument("--analyses-dir", required=True, help="Directory containing analysis JSON files")
    p.add_argument("--videos", required=True, help="Path to new_videos.json")
    p.add_argument("--date", required=True, help="Report date YYYY-MM-DD")
    p.add_argument("--output", required=True, help="Output HTML file path")
    p.add_argument("--index", default="", help="Optional: path to index.html to update")
    return p.parse_args()


def main():
    args = parse_args()

    analyses_dir = Path(args.analyses_dir)
    analysis_files = sorted(analyses_dir.glob("*.json"))

    if not analysis_files:
        log.error(f"No analysis JSON files found in {analyses_dir}")
        raise SystemExit(1)

    analyses = []
    for f in analysis_files:
        try:
            analyses.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception as e:
            log.warning(f"Skipping {f.name}: {e}")

    if not analyses:
        log.error("No valid analyses to render.")
        raise SystemExit(1)

    # Load video metadata
    videos_path = Path(args.videos)
    videos_list = json.loads(videos_path.read_text()) if videos_path.exists() else []
    videos_by_id = {v["video_id"]: v for v in videos_list}

    consensus = compute_consensus(analyses, videos_by_id)

    # Collect all stocks for the "by stock" section (any mention)
    all_stocks: dict[str, dict] = {}
    for analysis in analyses:
        for stock in analysis.get("stocks", []):
            key = canonical_stock_key(stock)
            if not key:
                continue
            if key not in all_stocks:
                all_stocks[key] = {
                    "symbol": stock.get("symbol"),
                    "company_name": stock.get("company_name"),
                    "display": stock.get("symbol") or stock.get("company_name") or key,
                    "mentions": [],
                }
            entry = all_stocks[key]
            if stock.get("symbol") and not entry["symbol"]:
                entry["symbol"] = stock["symbol"]
            if stock.get("company_name") and not entry["company_name"]:
                entry["company_name"] = stock["company_name"]
            entry["mentions"].append({
                "channel": analysis.get("channel_name"),
                "video_title": analysis.get("video_title"),
                "video_url": analysis.get("video_url"),
                "sentiment": stock.get("sentiment", "neutral"),
                "conviction": stock.get("conviction", 0.5),
                "thesis": stock.get("thesis", ""),
                "key_points": stock.get("key_points", []),
                "price_target": stock.get("price_target"),
            })
    all_stocks_list = sorted(all_stocks.values(), key=lambda s: s["display"])

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    total_stocks = len(all_stocks)
    all_sources = [
        {"channel": a.get("channel_name"), "title": a.get("video_title"), "url": a.get("video_url")}
        for a in analyses
    ]

    # Render template
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    template = env.get_template("report.html.jinja")
    html = template.render(
        report_date=args.date,
        generated_at=generated_at,
        video_count=len(analyses),
        stock_count=total_stocks,
        consensus=consensus,
        analyses=analyses,
        all_stocks=all_stocks_list,
        sources=all_sources,
        sentiment_score=SENTIMENT_SCORE,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    log.info(f"Report written: {output_path}")

    # Write JSON manifest for the React page
    data_dir = output_path.parent / "data"
    data_dir.mkdir(exist_ok=True)
    manifest = {
        "date": args.date,
        "generated_at": generated_at,
        "video_count": len(analyses),
        "stock_count": total_stocks,
        "consensus": consensus,
        "analyses": analyses,
        "all_stocks": all_stocks_list,
        "sources": all_sources,
    }
    manifest_path = data_dir / f"{args.date}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"Manifest written: {manifest_path}")

    # Update index if requested
    if args.index:
        index_path = Path(args.index)
        entry_template = env.get_template("index_entry.html")
        entry_html = entry_template.render(
            report_date=args.date,
            video_count=len(analyses),
            stock_count=total_stocks,
            consensus_top=[c["display"] for c in consensus[:3]],
            report_url=f"{args.date}.html",
        )
        if index_path.exists():
            content = index_path.read_text(encoding="utf-8")
            if args.date in content:
                log.info(f"Index already has entry for {args.date} — skipping duplicate")
            else:
                content = content.replace("<!-- ENTRIES -->", entry_html + "\n<!-- ENTRIES -->")
                index_path.write_text(content, encoding="utf-8")
                log.info(f"Index updated: {index_path}")
        else:
            _create_index(index_path, entry_html)
            log.info(f"Index created: {index_path}")

    log.info(f"\n{'─'*50}")
    log.info(f"Videos analyzed: {len(analyses)}")
    log.info(f"Stocks identified: {total_stocks}")
    log.info(f"Consensus picks (2+ channels): {len(consensus)}")
    if consensus:
        log.info(f"Top consensus: {', '.join(c['display'] for c in consensus[:3])}")


def _create_index(index_path: Path, first_entry: str):
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stock Sentinel — YouTube Daily Reports</title>
<style>
  :root {{
    --bg: #fff; --text: #1a1a1a; --muted: #666; --border: #e5e7eb;
    --accent: #2563eb;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #111; --text: #f0f0f0; --muted: #999; --border: #2a2a2a; --accent: #60a5fa; }}
  }}
  body {{ font-family: system-ui,-apple-system,sans-serif; background: var(--bg); color: var(--text);
          max-width: 720px; margin: 0 auto; padding: 2rem 1.5rem; }}
  h1 {{ font-size: 1.75rem; margin-bottom: 0.5rem; }}
  p.sub {{ color: var(--muted); margin-top: 0; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ border-bottom: 1px solid var(--border); padding: 1rem 0; }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .meta {{ font-size: 0.8rem; color: var(--muted); margin-top: 0.3rem; }}
</style>
</head>
<body>
<h1>📊 Stock Sentinel Daily Reports</h1>
<p class="sub">AI-generated summaries of finance YouTube content. Not financial advice.</p>
<ul>
{first_entry}
<!-- ENTRIES -->
</ul>
</body>
</html>
""", encoding="utf-8")


if __name__ == "__main__":
    main()
