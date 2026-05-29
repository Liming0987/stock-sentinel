import math
from decimal import Decimal
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
        """Query recent mentions, compute composite scores, persist TrendingSnapshot rows, and return ranked list."""
        from sqlalchemy import create_engine, select, and_
        from sqlalchemy.orm import Session
        from app.config import settings
        from app.models.stock import Stock
        from app.models.mention import Mention, RedditPost
        from app.models.signal import TrendingSnapshot

        sync_url = settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")
        engine = create_engine(sync_url)
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=24)
        prev_window_start = now - timedelta(hours=48)
        rankings = []

        with Session(engine) as session:
            # Purge snapshots older than 7 days to keep the table lean
            from sqlalchemy import delete as sa_delete
            session.execute(
                sa_delete(TrendingSnapshot).where(
                    TrendingSnapshot.snapshot_at < now - timedelta(days=7)
                )
            )
            session.commit()

            active_stock_ids = session.execute(
                select(Mention.stock_id)
                .where(Mention.created_at >= window_start)
                .distinct()
            ).scalars().all()

            for stock_id in active_stock_ids:
                stock = session.get(Stock, stock_id)
                if not stock:
                    continue

                current = session.execute(
                    select(Mention).where(
                        and_(Mention.stock_id == stock_id, Mention.created_at >= window_start)
                    )
                ).scalars().all()

                prev = session.execute(
                    select(Mention).where(
                        and_(
                            Mention.stock_id == stock_id,
                            Mention.created_at >= prev_window_start,
                            Mention.created_at < window_start,
                        )
                    )
                ).scalars().all()

                mention_count = len(current)
                velocity = self.compute_mention_velocity(mention_count, len(prev), hours=24.0)

                scores = [float(m.sentiment_score) for m in current if m.sentiment_score is not None]
                avg_sentiment = sum(scores) / len(scores) if scores else 0.0

                # Engagement from linked Reddit posts
                reddit_source_ids = [m.source_id for m in current if m.source_type == "reddit" and m.source_id]
                total_upvotes = 0
                num_posts = 0
                if reddit_source_ids:
                    posts = session.execute(
                        select(RedditPost).where(RedditPost.id.in_(reddit_source_ids))
                    ).scalars().all()
                    total_upvotes = sum(p.score or 0 for p in posts)
                    num_posts = len(posts)
                engagement_ratio = self.compute_engagement_ratio(total_upvotes, num_posts)

                sources = {m.source_type for m in current}
                cross_platform = len(sources) / 4.0  # reddit, stocktwits, news, youtube

                trend_score = self.compute_trend_score({
                    "mention_velocity": velocity,
                    "sentiment_avg": avg_sentiment,
                    "engagement_ratio": engagement_ratio,
                    "cross_platform": cross_platform,
                    "volume_anomaly": 0.0,
                })

                session.add(TrendingSnapshot(
                    stock_id=stock_id,
                    mention_count=mention_count,
                    mention_velocity=Decimal(str(round(velocity, 2))),
                    avg_sentiment=Decimal(str(round(avg_sentiment, 3))),
                    trend_score=Decimal(str(round(trend_score, 3))),
                    rank=0,
                ))
                rankings.append({
                    "stock_id": stock_id,
                    "ticker": stock.ticker,
                    "mention_count": mention_count,
                    "mention_velocity": velocity,
                    "avg_sentiment": avg_sentiment,
                    "trend_score": trend_score,
                    "sources": list(sources),
                })

            rankings.sort(key=lambda x: x["trend_score"], reverse=True)
            session.commit()

        engine.dispose()
        return rankings
