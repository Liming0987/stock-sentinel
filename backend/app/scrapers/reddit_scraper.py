import re
import praw
from typing import List, Dict
from datetime import datetime, timezone

from app.config import settings

# Subreddits to monitor
TARGET_SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "options",
    "pennystocks",
    "stockmarket",
]

# Common false positive tickers to exclude
FALSE_POSITIVES = {
    "A", "I", "AM", "PM", "IT", "ALL", "FOR", "ARE", "BE", "SO",
    "OR", "AT", "ON", "GO", "DO", "HAS", "CEO", "CFO", "CTO",
    "USA", "GDP", "IMO", "FYI", "TIL", "PSA", "DD", "YOLO",
    "FOMO", "FUD", "ATH", "ATL", "EOD", "IPO", "SEC", "FBI",
    "NYSE", "NASDAQ", "ETF", "OTC", "RH", "WSB", "OP", "EPS",
}

# Regex to match $TICKER or standalone uppercase tickers
TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b')
STANDALONE_TICKER = re.compile(r'\b([A-Z]{2,5})\b')


class RedditScraper:
    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )

    def extract_tickers(self, text: str) -> List[str]:
        """Extract stock tickers from text."""
        if not text:
            return []

        tickers = set()

        # Match $TICKER pattern (high confidence)
        for match in TICKER_PATTERN.finditer(text):
            ticker = match.group(1)
            if ticker not in FALSE_POSITIVES:
                tickers.add(ticker)

        # Match standalone uppercase words (lower confidence, stricter filtering)
        for match in STANDALONE_TICKER.finditer(text):
            ticker = match.group(1)
            if ticker not in FALSE_POSITIVES and len(ticker) >= 3:
                tickers.add(ticker)

        return list(tickers)

    def scrape_subreddit(self, subreddit_name: str, limit: int = 50) -> List[Dict]:
        """Scrape hot posts from a subreddit."""
        results = []
        subreddit = self.reddit.subreddit(subreddit_name)

        for post in subreddit.hot(limit=limit):
            tickers = self.extract_tickers(f"{post.title} {post.selftext}")
            if not tickers:
                continue

            results.append({
                "external_id": post.id,
                "subreddit": subreddit_name,
                "title": post.title,
                "body": post.selftext[:5000],  # Truncate long posts
                "author": str(post.author) if post.author else "[deleted]",
                "score": post.score,
                "num_comments": post.num_comments,
                "url": post.url,
                "created_at": datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                "tickers": tickers,
            })

        return results

    def scrape_all(self) -> List[Dict]:
        """Scrape all target subreddits."""
        all_results = []
        for subreddit in TARGET_SUBREDDITS:
            try:
                results = self.scrape_subreddit(subreddit)
                all_results.extend(results)
            except Exception as e:
                print(f"Error scraping r/{subreddit}: {e}")
        return all_results
