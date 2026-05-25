from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.stock import Stock
from app.models.signal import Signal as SignalModel
from app.services.price_service import PriceService


def _sync_db_url() -> str:
    """Convert async DB URL to sync for Celery tasks."""
    return settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")


class SignalService:
    """Generate buy/hold/avoid signals using multi-factor model."""

    BOOTSTRAP_TICKERS = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "META", "GOOG", "AMZN"]

    WEIGHTS = {
        "sentiment_surge": 0.25,
        "technical_oversold": 0.30,
        "volume_confirmation": 0.20,
        "historical_similarity": 0.15,
        "news_catalyst": 0.10,
    }

    SIGNAL_EXPIRY_HOURS = 48
    MAX_ACTIVE_SIGNALS = 10

    def evaluate_stock(self, ticker: str, sentiment_data: Dict, indicators: Dict) -> Optional[Dict]:
        """
        Evaluate a stock for potential buy signal.

        Returns signal dict or None if no signal.
        """
        scores = {}

        # 1. Sentiment surge
        avg_sentiment = sentiment_data.get("avg_sentiment", 0)
        mention_velocity_pct = sentiment_data.get("velocity_percentile", 0)
        if avg_sentiment > 0.6 and mention_velocity_pct > 90:
            scores["sentiment_surge"] = 1.0
        elif avg_sentiment > 0.4 and mention_velocity_pct > 75:
            scores["sentiment_surge"] = 0.6
        elif avg_sentiment > 0.2:
            scores["sentiment_surge"] = 0.3
        else:
            scores["sentiment_surge"] = 0.0

        # 2. Technical oversold
        rsi = indicators.get("rsi", 50)
        last_price = indicators.get("last_price", 0)
        bb_lower = indicators.get("bb_lower", 0)

        if rsi < 25:
            scores["technical_oversold"] = 1.0
        elif rsi < 30:
            scores["technical_oversold"] = 0.8
        elif rsi < 40 and last_price <= bb_lower * 1.02:
            scores["technical_oversold"] = 0.6
        else:
            scores["technical_oversold"] = 0.0

        # 3. Volume confirmation
        volume_ratio = indicators.get("volume_ratio", 1.0)
        if volume_ratio >= 2.0:
            scores["volume_confirmation"] = 1.0
        elif volume_ratio >= 1.5:
            scores["volume_confirmation"] = 0.7
        elif volume_ratio >= 1.2:
            scores["volume_confirmation"] = 0.3
        else:
            scores["volume_confirmation"] = 0.0

        # 4. Historical similarity (placeholder)
        scores["historical_similarity"] = 0.5

        # 5. News catalyst
        news_sentiment = sentiment_data.get("news_sentiment", 0)
        if news_sentiment > 0.5:
            scores["news_catalyst"] = 1.0
        elif news_sentiment > 0.2:
            scores["news_catalyst"] = 0.5
        else:
            scores["news_catalyst"] = 0.0

        # Compute composite confidence
        confidence = sum(
            scores[factor] * weight
            for factor, weight in self.WEIGHTS.items()
        )

        # Only generate signal if confidence > 0.40 (lowered to produce results with no sentiment data yet)
        if confidence < 0.40:
            return None

        # Determine signal type
        if confidence >= 0.75:
            signal_type = "BUY"
        elif confidence >= 0.55:
            signal_type = "HOLD"
        elif confidence >= 0.40:
            signal_type = "HOLD"
        else:
            return None

        # Compute entry zone and stop loss
        atr = indicators.get("atr", last_price * 0.02)
        if not atr or atr == 0:
            atr = last_price * 0.02
        entry_low = round(last_price - atr * 0.5, 2)
        entry_high = round(last_price + atr * 0.3, 2)
        stop_loss = round(last_price - atr * 2, 2)
        target = round(last_price + atr * 3, 2)

        # Build reasoning
        reasoning = []
        if scores["technical_oversold"] >= 0.6:
            reasoning.append(f"RSI oversold at {rsi:.0f}")
        if scores["sentiment_surge"] >= 0.6:
            reasoning.append(f"Positive sentiment surge ({avg_sentiment:.2f})")
        if scores["volume_confirmation"] >= 0.7:
            reasoning.append(f"Volume {volume_ratio:.1f}x average")
        if scores["news_catalyst"] >= 0.5:
            reasoning.append("Positive news catalyst")
        if not reasoning:
            reasoning.append(f"Multi-factor score {confidence:.0%}")

        return {
            "ticker": ticker,
            "signal_type": signal_type,
            "confidence": round(confidence, 3),
            "entry_low": entry_low,
            "entry_high": entry_high,
            "stop_loss": stop_loss,
            "target": target,
            "reasoning": reasoning,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=self.SIGNAL_EXPIRY_HOURS),
        }

    def generate(self) -> List[Dict]:
        """Generate signals for all tracked stocks using live price data."""
        engine = create_engine(_sync_db_url())
        price_service = PriceService()
        generated = []

        with Session(engine) as session:
            # Get stocks from DB, or bootstrap if empty
            stocks = session.execute(select(Stock)).scalars().all()
            tickers = [s.ticker for s in stocks]

            if not tickers:
                tickers = self.BOOTSTRAP_TICKERS
                for t in tickers:
                    info = price_service.get_stock_info(t)
                    existing = session.execute(
                        select(Stock).where(Stock.ticker == t)
                    ).scalar_one_or_none()
                    if not existing:
                        stock = Stock(
                            ticker=t,
                            name=info.get("name", t),
                            sector=info.get("sector"),
                            market_cap=info.get("market_cap"),
                            avg_volume=info.get("avg_volume"),
                        )
                        session.add(stock)
                session.commit()
                stocks = session.execute(select(Stock)).scalars().all()

            # Clear existing non-expired signals to avoid duplicates
            now = datetime.now(timezone.utc)

            for stock_row in stocks:
                try:
                    df = price_service.get_price_data(stock_row.ticker, period="3mo")
                    if df is None or df.empty:
                        continue

                    indicators = price_service.compute_indicators(df)
                    if not indicators:
                        continue

                    # Use placeholder sentiment (no scraping data yet)
                    sentiment_data = {
                        "avg_sentiment": 0.3,
                        "velocity_percentile": 50,
                        "news_sentiment": 0.3,
                    }

                    result = self.evaluate_stock(stock_row.ticker, sentiment_data, indicators)
                    if result is None:
                        continue

                    # Check if active signal already exists for this stock
                    existing_signal = session.execute(
                        select(SignalModel).where(
                            and_(
                                SignalModel.stock_id == stock_row.id,
                                SignalModel.expires_at > now,
                                SignalModel.outcome.is_(None),
                            )
                        )
                    ).scalar_one_or_none()

                    if existing_signal:
                        continue

                    # Update stock price
                    stock_row.last_price = Decimal(str(indicators["last_price"]))
                    session.add(stock_row)

                    # Create signal
                    signal = SignalModel(
                        stock_id=stock_row.id,
                        signal_type=result["signal_type"],
                        confidence=Decimal(str(result["confidence"])),
                        entry_low=Decimal(str(result["entry_low"])),
                        entry_high=Decimal(str(result["entry_high"])),
                        stop_loss=Decimal(str(result["stop_loss"])),
                        target=Decimal(str(result["target"])),
                        reasoning=result["reasoning"],
                        expires_at=result["expires_at"],
                    )
                    session.add(signal)
                    generated.append(result)
                    print(f"Signal generated: {result['signal_type']} {stock_row.ticker} (conf: {result['confidence']})")
                except Exception as e:
                    print(f"Error evaluating {stock_row.ticker}: {e}")
                    continue

            session.commit()

        engine.dispose()
        return generated

    def cleanup_expired(self) -> int:
        """Mark expired signals and compute outcomes."""
        engine = create_engine(_sync_db_url())
        now = datetime.now(timezone.utc)
        cleaned = 0

        with Session(engine) as session:
            expired = session.execute(
                select(SignalModel).where(
                    and_(
                        SignalModel.expires_at <= now,
                        SignalModel.outcome.is_(None),
                    )
                )
            ).scalars().all()

            for signal in expired:
                signal.outcome = "expired"
                cleaned += 1

            session.commit()

        engine.dispose()
        return cleaned
