import httpx
from typing import List, Dict
from datetime import datetime


STOCKTWITS_BASE_URL = "https://api.stocktwits.com/api/2"


class StockTwitsScraper:
    def __init__(self):
        self.client = httpx.Client(timeout=30)

    def scrape_trending(self) -> List[Dict]:
        """Scrape trending stocks and their messages from StockTwits."""
        results = []

        # Get trending symbols
        try:
            resp = self.client.get(f"{STOCKTWITS_BASE_URL}/trending/symbols.json")
            resp.raise_for_status()
            symbols = resp.json().get("symbols", [])
        except Exception as e:
            print(f"Error fetching StockTwits trending: {e}")
            return results

        # Get messages for top trending symbols
        for symbol in symbols[:20]:
            ticker = symbol.get("symbol", "")
            try:
                messages = self.scrape_symbol(ticker)
                results.extend(messages)
            except Exception as e:
                print(f"Error fetching StockTwits messages for {ticker}: {e}")

        return results

    def scrape_symbol(self, ticker: str, limit: int = 30) -> List[Dict]:
        """Scrape recent messages for a specific symbol."""
        results = []

        try:
            resp = self.client.get(
                f"{STOCKTWITS_BASE_URL}/streams/symbol/{ticker}.json",
                params={"limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Error fetching StockTwits stream for {ticker}: {e}")
            return results

        messages = data.get("messages", [])
        for msg in messages:
            sentiment_tag = None
            if msg.get("entities", {}).get("sentiment"):
                sentiment_tag = msg["entities"]["sentiment"].get("basic")

            results.append({
                "external_id": str(msg["id"]),
                "body": msg.get("body", ""),
                "author": msg.get("user", {}).get("username", ""),
                "sentiment_tag": sentiment_tag,  # "Bullish" or "Bearish"
                "likes": msg.get("likes", {}).get("total", 0),
                "created_at": msg.get("created_at"),
                "ticker": ticker,
            })

        return results

    def __del__(self):
        self.client.close()
