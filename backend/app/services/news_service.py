import logging
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger(__name__)


class NewsService:
    def get_news(self, ticker: str, limit: int = 20) -> List[Dict]:
        """Fetch news from Alpaca (primary) and yfinance (supplement), merged and deduped."""
        items: List[Dict] = []
        items.extend(self._fetch_alpaca(ticker, limit))
        items.extend(self._fetch_yfinance(ticker))

        seen: set = set()
        deduped: List[Dict] = []
        for item in items:
            key = item.get("url") or item.get("title", "")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            deduped.append(item)

        deduped.sort(key=lambda x: x.get("published_at") or "", reverse=True)
        return deduped[:limit]

    def _fetch_alpaca(self, ticker: str, limit: int) -> List[Dict]:
        try:
            from app.services.secrets import SecretNotConfiguredError, get_alpaca_credentials
            creds = get_alpaca_credentials()
            from alpaca.data.historical.news import NewsClient
            from alpaca.data.requests import NewsRequest

            client = NewsClient(api_key=creds["api_key"], secret_key=creds["api_secret"])
            resp = client.get_news(NewsRequest(symbols=[ticker], limit=limit))
            news = getattr(resp, "news", resp) if not isinstance(resp, list) else resp

            items = []
            for a in news:
                images = getattr(a, "images", None) or []
                image_url = images[0].url if images else None
                published = getattr(a, "created_at", None)
                items.append({
                    "title": getattr(a, "headline", "") or "",
                    "summary": getattr(a, "summary", "") or "",
                    "url": getattr(a, "url", "") or "",
                    "source": getattr(a, "source", "Alpaca") or "Alpaca",
                    "published_at": published.isoformat() if published else None,
                    "tickers": list(getattr(a, "symbols", None) or []),
                    "image_url": image_url,
                })
            return items
        except Exception as e:
            logger.warning("Alpaca news fetch failed for %s: %s", ticker, e)
            return []

    def _fetch_yfinance(self, ticker: str) -> List[Dict]:
        try:
            import yfinance as yf
            raw = yf.Ticker(ticker).news or []
            items = []
            for n in raw:
                ts = n.get("providerPublishTime")
                published_at = (
                    datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None
                )
                items.append({
                    "title": n.get("title", ""),
                    "summary": "",
                    "url": n.get("link", ""),
                    "source": n.get("publisher", "Yahoo Finance"),
                    "published_at": published_at,
                    "tickers": n.get("relatedTickers", []),
                    "image_url": None,
                })
            return items
        except Exception as e:
            logger.warning("yfinance news fetch failed for %s: %s", ticker, e)
            return []
