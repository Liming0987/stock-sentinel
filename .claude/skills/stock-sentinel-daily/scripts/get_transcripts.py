#!/usr/bin/env python3
"""
get_transcripts.py — Download and clean transcripts for a list of videos.

Usage:
    python scripts/get_transcripts.py --input workdir/new_videos.json --output workdir/transcripts/
    python scripts/get_transcripts.py --help
"""

import argparse
import json
import logging
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Optional

TRANSCRIPT_TIMEOUT_SECS = 30

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

SPONSOR_TRIGGERS = [
    "this video is sponsored by",
    "today's video is sponsored",
    "brought to you by",
    "use code ",
    "use my referral",
    "use my link",
    "check the link in the description",
    "check the description below",
    "affiliate link",
    "discount code",
    "promo code",
    "sign up using",
    "get a free trial",
    "try it for free",
    "click the link below",
    "coupon code",
]

# Seconds to strip around each detected sponsor block
SPONSOR_BUFFER_SECS = 90


def detect_sponsor_windows(segments: list) -> list[tuple[float, float]]:
    """
    Return a list of (start, end) time windows that appear to be sponsor reads.
    """
    windows = []
    for seg in segments:
        text_lower = (seg.text if hasattr(seg, "text") else seg["text"]).lower()
        if any(phrase in text_lower for phrase in SPONSOR_TRIGGERS):
            t = seg.start if hasattr(seg, "start") else float(seg["start"])
            dur = seg.duration if hasattr(seg, "duration") else float(seg.get("duration", 30))
            windows.append((t - SPONSOR_BUFFER_SECS, t + dur + SPONSOR_BUFFER_SECS))
    # Merge overlapping windows
    if not windows:
        return []
    windows.sort()
    merged = [windows[0]]
    for lo, hi in windows[1:]:
        if lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def in_sponsor_window(t: float, windows: list) -> bool:
    return any(lo <= t <= hi for lo, hi in windows)


def segments_to_text(segments: list, sponsor_windows: list) -> str:
    """Convert transcript segments to clean text, skipping sponsor blocks."""
    lines = []
    for seg in segments:
        t = seg.start if hasattr(seg, "start") else float(seg["start"])
        if sponsor_windows and in_sponsor_window(t, sponsor_windows):
            continue
        text = (seg.text if hasattr(seg, "text") else seg["text"]).strip()
        # Clean common transcript artifacts
        text = re.sub(r"\[.*?\]", "", text)          # [Music], [Applause], etc.
        text = re.sub(r"\(.*?\)", "", text)          # (inaudible), etc.
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            lines.append(text)
    return " ".join(lines)


def fetch_transcript(video_id: str) -> Optional[str]:
    """
    Fetch transcript for a video. Tries English first, then any available language.
    Returns cleaned plain-text transcript, or None if unavailable.
    """
    try:
        transcript_list = YouTubeTranscriptApi().list(video_id)
    except (TranscriptsDisabled, VideoUnavailable) as e:
        log.warning(f"  {video_id}: transcript unavailable — {e}")
        return None
    except Exception as e:
        log.warning(f"  {video_id}: unexpected error listing transcripts — {e}")
        return None

    # Priority: manual English, auto English, any manual, any auto
    transcript = None
    for lang_codes in [["en", "en-US", "en-GB"], None]:
        try:
            if lang_codes:
                transcript = transcript_list.find_transcript(lang_codes)
            else:
                # Fall back to any available language
                try:
                    transcript = transcript_list.find_manually_created_transcript()
                except NoTranscriptFound:
                    transcript = transcript_list.find_generated_transcript(
                        [t.language_code for t in transcript_list]
                    )
            break
        except NoTranscriptFound:
            continue
        except Exception:
            continue

    if transcript is None:
        log.warning(f"  {video_id}: no usable transcript found")
        return None

    try:
        segments = transcript.fetch()
    except Exception as e:
        log.warning(f"  {video_id}: failed to fetch transcript segments — {e}")
        return None

    sponsor_windows = detect_sponsor_windows(segments)
    if sponsor_windows:
        log.info(f"  {video_id}: stripped {len(sponsor_windows)} sponsor block(s)")

    text = segments_to_text(segments, sponsor_windows)
    if len(text) < 200:
        log.warning(f"  {video_id}: transcript too short ({len(text)} chars) — skipping")
        return None

    return text


def parse_args():
    p = argparse.ArgumentParser(description="Download and clean YouTube transcripts.")
    p.add_argument("--input", required=True, help="Path to new_videos.json from fetch_videos.py")
    p.add_argument("--output", required=True, help="Directory to write transcript .txt files")
    return p.parse_args()


def main():
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        log.error(f"Input file not found: {input_path}")
        raise SystemExit(1)

    videos = json.loads(input_path.read_text())
    if not videos:
        log.info("No videos to process.")
        return

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    failures = []
    success_count = 0

    for video in videos:
        vid_id = video["video_id"]
        title = video.get("title", vid_id)
        log.info(f"Fetching transcript: {title[:70]}")

        # Skip if already downloaded
        out_file = output_dir / f"{vid_id}.txt"
        if out_file.exists():
            log.info(f"  Already downloaded, skipping.")
            success_count += 1
            continue

        failure_reason = None
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fetch_transcript, vid_id)
            try:
                text = future.result(timeout=TRANSCRIPT_TIMEOUT_SECS)
            except FuturesTimeoutError:
                log.warning(f"  {vid_id}: transcript fetch timed out after {TRANSCRIPT_TIMEOUT_SECS}s")
                text = None
                failure_reason = "timeout"

        if text is None:
            failures.append({
                "video_id": vid_id,
                "title": title,
                "url": video.get("url"),
                "reason": failure_reason or "no_transcript",
            })
        else:
            # Write metadata header + transcript text
            header = (
                f"TITLE: {title}\n"
                f"CHANNEL: {video.get('channel_name', '')}\n"
                f"URL: {video.get('url', '')}\n"
                f"PUBLISHED: {video.get('published_at', '')}\n"
                f"DURATION_SECONDS: {video.get('duration_seconds', '')}\n"
                f"{'─' * 60}\n\n"
            )
            out_file.write_text(header + text, encoding="utf-8")
            log.info(f"  ✓ Saved {len(text):,} chars → {out_file.name}")
            success_count += 1

        # Polite delay between requests
        time.sleep(random.uniform(1.0, 3.0))

    # Write failures log
    failures_path = output_dir / "transcript_failures.json"
    failures_path.write_text(json.dumps(failures, indent=2, ensure_ascii=False))

    log.info(f"\n{'─'*50}")
    log.info(f"Transcripts downloaded: {success_count}/{len(videos)}")
    if failures:
        log.info(f"Failures ({len(failures)}): {failures_path}")


if __name__ == "__main__":
    main()
