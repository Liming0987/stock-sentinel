#!/usr/bin/env python3
"""
fetch_videos.py — Pull new videos from configured finance YouTubers.

Usage:
    python scripts/fetch_videos.py --since-hours 26 --output workdir/new_videos.json
    python scripts/fetch_videos.py --since-hours 26 --output workdir/new_videos.json --channels @StockswithJosh,@DividendData
    python scripts/fetch_videos.py --help
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import isodate
import yaml
from dotenv import find_dotenv, load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ── Paths (all relative to the skill root, one level up from scripts/) ──────
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
CONFIG_FILE = SKILL_DIR / "config" / "youtubers.yaml"
CACHE_FILE = DATA_DIR / "channel_id_cache.json"
PROCESSED_FILE = DATA_DIR / "processed_videos.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

SPONSOR_PHRASES = [
    "this video is sponsored by", "brought to you by", "use code",
    "use my link", "check the description", "affiliate link",
    "discount code", "promo code", "sign up using",
]


def load_env():
    dotenv_path = find_dotenv(usecwd=True)
    if not dotenv_path:
        # walk up until we find .env or hit filesystem root
        p = SKILL_DIR
        for _ in range(6):
            candidate = p / ".env"
            if candidate.exists():
                dotenv_path = str(candidate)
                break
            p = p.parent
    load_dotenv(dotenv_path)
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        log.error(".env not found or YOUTUBE_API_KEY not set. "
                  "Create a .env file in the repo root with YOUTUBE_API_KEY=<your-key>")
        sys.exit(1)
    return key


def load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {}


def save_cache(cache: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def load_processed() -> set:
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text()))
    return set()


def load_config() -> list:
    with open(CONFIG_FILE) as f:
        cfg = yaml.safe_load(f)
    return [ch for ch in cfg.get("youtubers", []) if ch.get("enabled", True)]


def resolve_handle(service, handle: str, cache: dict) -> Optional[str]:
    """Resolve @handle → channel_id, with caching."""
    key = handle.lstrip("@")
    if key in cache:
        return cache[key]
    try:
        resp = service.channels().list(forHandle=handle, part="id").execute()
        items = resp.get("items", [])
        if not items:
            log.warning(f"Could not resolve handle {handle}")
            return None
        channel_id = items[0]["id"]
        cache[key] = channel_id
        log.info(f"Resolved {handle} → {channel_id}")
        return channel_id
    except HttpError as e:
        log.error(f"API error resolving {handle}: {e}")
        return None


def get_uploads_playlist(service, channel_id: str, cache: dict) -> Optional[str]:
    """Get the uploads playlist ID for a channel, with caching."""
    cache_key = f"uploads:{channel_id}"
    if cache_key in cache:
        return cache[cache_key]
    try:
        resp = service.channels().list(id=channel_id, part="contentDetails").execute()
        items = resp.get("items", [])
        if not items:
            return None
        playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        cache[cache_key] = playlist_id
        return playlist_id
    except HttpError as e:
        log.error(f"API error getting uploads playlist for {channel_id}: {e}")
        return None


def list_playlist_videos(service, playlist_id: str, since: datetime) -> list:
    """List videos from an uploads playlist published after `since`."""
    videos = []
    page_token = None
    while True:
        try:
            resp = service.playlistItems().list(
                playlistId=playlist_id,
                part="snippet,contentDetails",
                maxResults=50,
                pageToken=page_token,
            ).execute()
        except HttpError as e:
            log.error(f"API error listing playlist {playlist_id}: {e}")
            break

        for item in resp.get("items", []):
            snippet = item["snippet"]
            published_raw = snippet.get("publishedAt", "")
            if not published_raw:
                continue
            published = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
            if published < since:
                # Playlist is newest-first; once we hit older videos we can stop
                return videos
            videos.append({
                "video_id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "channel_id": snippet["channelId"],
                "published_at": published_raw,
            })

        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return videos


def get_video_details(service, video_ids: list) -> dict:
    """Batch-fetch duration and livestream info. Returns {video_id: details}."""
    result = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        try:
            resp = service.videos().list(
                id=",".join(batch),
                part="contentDetails,snippet,liveStreamingDetails",
            ).execute()
        except HttpError as e:
            log.error(f"API error fetching video details: {e}")
            continue
        for item in resp.get("items", []):
            vid = item["id"]
            duration_iso = item["contentDetails"].get("duration", "PT0S")
            try:
                duration_secs = int(isodate.parse_duration(duration_iso).total_seconds())
            except Exception:
                duration_secs = 0
            is_live = "liveStreamingDetails" in item
            definition = item["contentDetails"].get("definition", "sd")
            # Detect Shorts: duration <= 60s and vertical aspect (heuristic)
            is_short = duration_secs <= 60
            result[vid] = {
                "duration_seconds": duration_secs,
                "is_livestream": is_live,
                "is_short": is_short,
            }
    return result


def parse_args():
    p = argparse.ArgumentParser(description="Fetch new YouTube videos from configured finance channels.")
    p.add_argument("--since-hours", type=float, default=26,
                   help="Look back this many hours (default: 26)")
    p.add_argument("--output", required=True,
                   help="Output JSON path for new videos list")
    p.add_argument("--channels", default="",
                   help="Comma-separated handles or channel IDs to restrict to")
    return p.parse_args()


def main():
    args = parse_args()
    api_key = load_env()
    service = build("youtube", "v3", developerKey=api_key)

    channels = load_config()
    if args.channels:
        filters = {c.strip().lstrip("@").lower() for c in args.channels.split(",")}
        channels = [
            ch for ch in channels
            if ch.get("handle", "").lstrip("@").lower() in filters
            or ch.get("channel_id", "").lower() in filters
        ]
        if not channels:
            log.error(f"No matching channels found for filter: {args.channels}")
            sys.exit(1)

    if not channels:
        log.error("No enabled channels in config/youtubers.yaml")
        sys.exit(1)

    since = datetime.now(timezone.utc) - timedelta(hours=args.since_hours)
    processed = load_processed()
    cache = load_cache()

    all_new_videos = []
    quota_units = 0

    for ch in channels:
        display = ch.get("display_name", ch.get("handle", ch.get("channel_id")))
        log.info(f"Processing channel: {display}")

        # Resolve channel ID
        channel_id = ch.get("channel_id")
        if not channel_id:
            handle = ch.get("handle")
            if not handle:
                log.warning(f"Channel entry has neither channel_id nor handle: {ch}")
                continue
            channel_id = resolve_handle(service, handle, cache)
            quota_units += 1
            if not channel_id:
                continue

        # Get uploads playlist
        playlist_id = get_uploads_playlist(service, channel_id, cache)
        quota_units += 1
        if not playlist_id:
            log.warning(f"No uploads playlist for {display}")
            continue

        # List recent videos
        raw_videos = list_playlist_videos(service, playlist_id, since)
        quota_units += len(raw_videos) // 50 + 1
        log.info(f"  {len(raw_videos)} videos since {since.isoformat()}")

        # Filter already processed
        raw_videos = [v for v in raw_videos if v["video_id"] not in processed]

        if not raw_videos:
            log.info(f"  No new videos for {display}")
            continue

        # Get video details (duration, livestream detection)
        video_ids = [v["video_id"] for v in raw_videos]
        details = get_video_details(service, video_ids)
        quota_units += len(video_ids) // 50 + 1

        min_dur = ch.get("min_duration_seconds", 300)
        include_shorts = ch.get("include_shorts", False)
        include_live = ch.get("include_livestreams", False)

        for v in raw_videos:
            d = details.get(v["video_id"], {})
            dur = d.get("duration_seconds", 0)
            if not include_live and d.get("is_livestream"):
                log.info(f"  Skipping livestream: {v['title'][:60]}")
                continue
            if not include_shorts and d.get("is_short"):
                log.info(f"  Skipping short: {v['title'][:60]}")
                continue
            if dur < min_dur:
                log.info(f"  Skipping short video ({dur}s): {v['title'][:60]}")
                continue

            all_new_videos.append({
                "video_id": v["video_id"],
                "channel_id": channel_id,
                "channel_name": display,
                "title": v["title"],
                "url": f"https://www.youtube.com/watch?v={v['video_id']}",
                "published_at": v["published_at"],
                "duration_seconds": dur,
            })
            log.info(f"  ✓ {v['title'][:70]} ({dur//60}m{dur%60}s)")

    save_cache(cache)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(all_new_videos, indent=2, ensure_ascii=False))

    log.info(f"\n{'─'*50}")
    log.info(f"New videos found: {len(all_new_videos)}")
    log.info(f"Estimated quota used: ~{quota_units} units")
    log.info(f"Output written to: {output_path}")


if __name__ == "__main__":
    main()
