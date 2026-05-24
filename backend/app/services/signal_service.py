from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta


class SignalService:
    """Generate buy/hold/avoid signals using multi-factor model."""

    # Signal weights
    WEIGHTS = {
        "sentiment_surge": 0.25,
        "technical_oversold": 0.30,
        "volume_confirmation": 0.20,
        "historical_similarity": 0.15,
        "news_catalyst": 0.10,
    }

    # Thresholds
    MIN_MARKET_CAP = 500_000_000  # $500M
    MIN_AVG_VOLUME = 500_000  # 500K shares/day
    SIGNAL_EXPIRY_HOURS = 48
    MAX_ACTIVE_SIGNALS = 5

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

        # 4. Historical similarity (placeholder — needs backtesting data)
        scores["historical_similarity"] = 0.5  # Neutral until we have data

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

        # Only generate signal if confidence > 0.55
        if confidence < 0.55:
            return None

        # Determine signal type
        if confidence >= 0.75:
            signal_type = "BUY"
        elif confidence >= 0.55:
            signal_type = "HOLD"
        else:
            return None

        # Compute entry zone and stop loss
        atr = indicators.get("atr", last_price * 0.02)
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
        """Generate signals for all eligible stocks."""
        # TODO: Query DB for stocks with recent sentiment data + compute indicators
        return []

    def cleanup_expired(self) -> int:
        """Mark expired signals and compute outcomes."""
        # TODO: Query DB for expired signals, check if target/stop was hit
        return 0
