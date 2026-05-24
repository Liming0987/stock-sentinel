import math
from typing import List, Dict
from datetime import datetime, timezone, timedelta


class TrendingService:
    """Compute trending stock rankings based on multi-factor scoring."""

    # Scoring weights
    WEIGHTS = {
        "mention_velocity": 0.30,
        "sentiment_avg": 0.25,
        "engagement_ratio": 0.20,
        "cross_platform": 0.15,
        "volume_anomaly": 0.10,
    }

    def compute_mention_velocity(self, mentions_now: int, mentions_prev: int, hours: float = 1.0) -> float:
        """Compute rate of change in mentions per hour."""
        if mentions_prev == 0:
            return float(mentions_now)
        return (mentions_now - mentions_prev) / max(hours, 0.1)

    def compute_engagement_ratio(self, total_score: int, num_posts: int) -> float:
        """Average engagement (upvotes) per post."""
        if num_posts == 0:
            return 0.0
        return total_score / num_posts

    def detect_anomaly(self, current_value: float, mean: float, std: float) -> float:
        """Compute Z-score for anomaly detection."""
        if std == 0:
            return 0.0
        return (current_value - mean) / std

    def is_pump_suspect(self, mentions: List[Dict], threshold_authors: int = 3, threshold_pct: float = 0.6) -> bool:
        """Detect potential pump-and-dump: too many mentions from too few authors."""
        if not mentions:
            return False

        authors = [m.get("author", "") for m in mentions]
        total = len(authors)
        if total < 5:
            return False

        from collections import Counter
        author_counts = Counter(authors)
        top_authors = author_counts.most_common(threshold_authors)
        top_count = sum(count for _, count in top_authors)

        return (top_count / total) > threshold_pct

    def compute_trend_score(self, stock_data: Dict) -> float:
        """
        Compute composite trend score for a stock.

        Expected stock_data keys:
        - mention_velocity: float (mentions/hour change)
        - sentiment_avg: float (-1 to 1)
        - engagement_ratio: float (avg upvotes per post)
        - cross_platform: float (0-1, present on how many platforms)
        - volume_anomaly: float (z-score of current volume vs historical)
        """
        # Normalize each factor to 0-1 range
        scores = {}

        # Mention velocity: log scale, cap at 100 mentions/hour
        mv = stock_data.get("mention_velocity", 0)
        scores["mention_velocity"] = min(math.log(1 + mv) / math.log(101), 1.0)

        # Sentiment: shift from [-1,1] to [0,1]
        sent = stock_data.get("sentiment_avg", 0)
        scores["sentiment_avg"] = (sent + 1) / 2

        # Engagement: log scale, cap at 1000 avg upvotes
        eng = stock_data.get("engagement_ratio", 0)
        scores["engagement_ratio"] = min(math.log(1 + eng) / math.log(1001), 1.0)

        # Cross-platform presence: already 0-1
        scores["cross_platform"] = stock_data.get("cross_platform", 0)

        # Volume anomaly: sigmoid of z-score
        z = stock_data.get("volume_anomaly", 0)
        scores["volume_anomaly"] = 1 / (1 + math.exp(-z))

        # Weighted sum
        trend_score = sum(
            scores[factor] * weight
            for factor, weight in self.WEIGHTS.items()
        )

        return round(trend_score, 3)

    def compute_rankings(self) -> List[Dict]:
        """Compute rankings for all stocks with recent activity."""
        # TODO: Query DB for recent mentions, compute scores, rank
        return []
