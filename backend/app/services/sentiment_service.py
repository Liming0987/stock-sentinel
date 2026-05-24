import math
from typing import Dict, Tuple
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class SentimentService:
    """Sentiment analysis using FinBERT (primary) and VADER (fallback)."""

    def __init__(self, use_finbert: bool = True):
        self.vader = SentimentIntensityAnalyzer()
        self.finbert_model = None
        self.finbert_tokenizer = None

        if use_finbert:
            self._load_finbert()

    def _load_finbert(self):
        """Lazy-load FinBERT model."""
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch

            model_name = "ProsusAI/finbert"
            self.finbert_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.finbert_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.finbert_model.eval()
        except Exception as e:
            print(f"Failed to load FinBERT, falling back to VADER: {e}")
            self.finbert_model = None

    def analyze_vader(self, text: str) -> Tuple[float, float]:
        """Analyze sentiment using VADER. Returns (score, confidence)."""
        scores = self.vader.polarity_scores(text)
        compound = scores["compound"]  # -1 to 1
        confidence = abs(compound)
        return compound, confidence

    def analyze_finbert(self, text: str) -> Tuple[float, float]:
        """Analyze sentiment using FinBERT. Returns (score, confidence)."""
        if not self.finbert_model:
            return self.analyze_vader(text)

        import torch

        inputs = self.finbert_tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )

        with torch.no_grad():
            outputs = self.finbert_model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)[0]

        # FinBERT outputs: [positive, negative, neutral]
        positive = probs[0].item()
        negative = probs[1].item()
        neutral = probs[2].item()

        # Map to -1 to 1 score
        score = positive - negative
        confidence = 1.0 - neutral  # Higher confidence when less neutral

        return score, confidence

    def analyze(self, text: str, method: str = "auto") -> Dict:
        """
        Analyze text sentiment.

        Args:
            text: Input text to analyze
            method: 'finbert', 'vader', or 'auto' (uses FinBERT if available)

        Returns:
            dict with score (-1 to 1), confidence (0 to 1), and model_used
        """
        if not text or len(text.strip()) < 10:
            return {"score": 0.0, "confidence": 0.0, "model_used": "none"}

        if method == "vader" or (method == "auto" and not self.finbert_model):
            score, confidence = self.analyze_vader(text)
            model_used = "vader"
        else:
            score, confidence = self.analyze_finbert(text)
            model_used = "finbert"

        return {
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "model_used": model_used,
        }

    def compute_weighted_sentiment(
        self, mentions: list, decay_hours: float = 24.0
    ) -> float:
        """
        Compute weighted average sentiment for a list of mentions.

        Weight = log(1 + upvotes) * recency_decay
        """
        if not mentions:
            return 0.0

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        total_weight = 0.0
        weighted_sum = 0.0

        for mention in mentions:
            score = mention.get("sentiment_score", 0)
            upvotes = mention.get("score", 1)
            created_at = mention.get("created_at", now)

            # Recency decay
            hours_old = (now - created_at).total_seconds() / 3600
            recency = math.exp(-hours_old / decay_hours)

            # Weight
            weight = math.log(1 + max(upvotes, 0)) * recency

            weighted_sum += score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return round(weighted_sum / total_weight, 3)
