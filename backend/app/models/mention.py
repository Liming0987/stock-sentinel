from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, func
from app.models.database import Base


class RedditPost(Base):
    __tablename__ = "reddit_posts"

    id = Column(Integer, primary_key=True)
    external_id = Column(String(20), unique=True)
    subreddit = Column(String(50), index=True)
    title = Column(Text)
    body = Column(Text)
    author = Column(String(50))
    score = Column(Integer, default=0)
    num_comments = Column(Integer, default=0)
    url = Column(Text)
    created_at = Column(DateTime(timezone=True))
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())


class StocktwitsMessage(Base):
    __tablename__ = "stocktwits_messages"

    id = Column(Integer, primary_key=True)
    external_id = Column(String(20), unique=True)
    body = Column(Text)
    author = Column(String(50))
    sentiment_tag = Column(String(10))
    likes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True))
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())


class Mention(Base):
    __tablename__ = "mentions"

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), index=True)
    source_type = Column(String(20))  # reddit, stocktwits, news, youtube
    source_id = Column(Integer)
    sentiment_score = Column(Numeric(4, 3))  # -1.000 to 1.000
    confidence = Column(Numeric(4, 3))
    model_used = Column(String(20))  # finbert, vader
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
