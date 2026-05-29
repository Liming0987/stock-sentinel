import re
import praw
from typing import List, Dict
from datetime import datetime, timezone

from app.services.secrets import get_reddit_credentials

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
    # ── Articles / prepositions / conjunctions ──
    "A", "I", "AN", "AS", "AT", "BE", "BY", "DO", "GO", "IF",
    "IN", "IS", "IT", "MY", "NO", "OF", "ON", "OR", "SO", "TO",
    "UP", "US", "WE", "AM", "AND", "ARE", "BUT", "CAN", "DID",
    "FOR", "GET", "GOT", "HAD", "HAS", "HOW", "ITS", "LET", "MAY",
    "NOR", "NOT", "NOW", "OFF", "OUT", "OWN", "PUT", "RAN", "SET",
    "THE", "WAS", "YET", "ALSO", "BEEN", "BOTH", "EACH", "EVEN",
    "FROM", "HAVE", "INTO", "JUST", "LIKE", "MADE", "MAKE", "MANY",
    "MORE", "MOST", "MUCH", "NEED", "ONCE", "ONLY", "OVER", "SAME",
    "SOME", "SUCH", "THAN", "THAT", "THEM", "THEN", "THEY", "THIS",
    "VERY", "WANT", "WELL", "WERE", "WHAT", "WHEN", "WITH", "WILL",
    "ABOUT", "AFTER", "AGAIN", "BEING", "COULD", "EVERY", "FIRST",
    "GOING", "GREAT", "LARGE", "LATER", "LEAST", "MAJOR", "MAYBE",
    "MIGHT", "NEVER", "OFTEN", "OTHER", "QUITE", "SMALL", "STILL",
    "THEIR", "THERE", "THESE", "THOSE", "TODAY", "UNDER", "UNTIL",
    "USING", "WHERE", "WHICH", "WHILE", "WHOSE", "WOULD", "YEARS",
    # ── Common nouns / adjectives ──
    "OLD", "NEW", "BIG", "TOP", "LOW", "HIGH", "LONG", "BACK",
    "BEST", "GOOD", "HARD", "HUGE", "LAST", "LATE", "LEFT", "MAIN",
    "NEAR", "NEXT", "OPEN", "PAST", "PEAK", "REAL", "RICH", "SAFE",
    "SLOW", "FAST", "SOON", "SURE", "TRUE", "WEEK", "YEAR", "ZERO",
    "BASE", "BLUE", "DARK", "EASY", "FIVE", "FOUR", "FULL", "GOLD",
    "HALF", "NINE", "ONCE", "READ", "RISE", "SHOW", "STAY", "STOP",
    "TERM", "WAIT", "WIDE", "ABLE", "ALSO", "CORE", "DEAL", "DONE",
    "DOWN", "DROP", "FEEL", "FIND", "HAND", "HEAR", "HELP", "HITS",
    "HOLD", "KEEP", "KNOW", "LOOK", "LOSE", "LOSS", "MOVE", "ONCE",
    "PAID", "PLAN", "PLAY", "POST", "FREE", "PICK", "RATE", "RISK",
    "SELL", "SOLD", "SOON", "STAY", "TAKE", "USED", "WENT", "WORK",
    "YEAR", "ABLE", "BOOK", "BOND", "CALL", "CASH", "COST", "DAYS",
    "DEBT", "FIVE", "FUND", "GAIN", "GROW", "LEFT", "LINK", "NOTE",
    "ONCE", "PAYS", "RISE", "RUNS", "SAYS", "SEES", "SETS", "SIZE",
    "SOLD", "SOON", "TALK", "TIME", "VOTE", "WAIT", "WAYS", "WITH",
    "BLACK", "WHITE", "GREEN", "HOLES", "CLOSE", "ABOVE", "BELOW",
    "AFTER", "BREAK", "BRING", "BUILT", "CLAIM", "CLEAN", "CLEAR",
    "COSTS", "COVER", "DAILY", "DOING", "FINAL", "GIVEN", "AHEAD",
    "KNOWN", "LEVEL", "LIGHT", "LOWER", "MAKES", "MEANS", "MONEY",
    "MONTH", "MOVED", "MOVED", "NAMES", "NOTES", "OFFER", "ORDER",
    "PARTS", "POINT", "POWER", "PRESS", "PRICE", "RIGHT", "ROUND",
    "SHARE", "SHORT", "SHOWS", "SINCE", "SOLID", "SPACE", "STAGE",
    "STAND", "START", "STATE", "STOCK", "TAKES", "TERMS", "THINK",
    "THREE", "TIMES", "TOTAL", "TRADE", "TRUMP", "TURNS", "TWICE",
    "TYPES", "ULTRA", "UNION", "UNITS", "UPPER", "USAGE", "VALUE",
    "VIEWS", "WASTE", "WATCH", "WEEKS", "WHOLE", "WORTH", "WRONG",
    "YIELD", "YOUNG", "YOURS",
    # ── Reddit / trading slang ──
    "DD", "OP", "RH", "WSB", "YOLO", "FOMO", "FUD", "ATH", "ATL",
    "EOD", "HODL", "BTFD", "DYOR", "NFA", "NGMI", "WAGMI", "REKT",
    "BAGS", "MOON", "PUMP", "DUMP", "BULL", "BEAR", "PRINT", "PUTS",
    "CALLS", "GAIN", "GAINS", "LOSS", "LOSER", "BASED", "CALLS",
    # ── Finance / accounting acronyms ──
    "CEO", "CFO", "CTO", "COO", "CRO", "IPO", "SEC", "FBI", "NYSE",
    "NASDAQ", "ETF", "OTC", "EPS", "IMO", "FYI", "TIL", "PSA",
    "GDP", "CPI", "PPI", "PCE", "PMI", "ISM", "AUM", "NAV", "DCF",
    "FCF", "OCF", "ROE", "ROA", "ROI", "EV", "PE", "PB",
    "EBIT", "GAAP", "IFRS", "REIT", "SPAC", "PIPE", "ESOP", "DRIP",
    "CAGR", "TTM", "LTM", "NTM", "YOY", "QOQ", "MOM", "YTD",
    "LIBOR", "SOFR", "REPO", "ZIRP", "NIRP", "TARP", "QE", "QT",
    "FOMC", "FDIC", "SIPC", "DTCC", "FINRA", "CFTC", "PCAOB",
    "EDGAR", "POTUS", "SCOTUS",
    # ── Options jargon ──
    "LEAP", "LEAPS", "CALL", "IRON", "STRANGLE", "STRADDLE",
    "ITM", "OTM", "ATM", "VWAP", "TWAP",
    # ── Technical analysis terms ──
    "RSI", "EMA", "SMA", "MACD", "VWAP", "ATR", "ADX",
    # ── Macro / news terms ──
    "USA", "FED", "IMF", "ECB", "BOJ", "PBOC",
    "COVID", "SARS", "MERS", "DELTA", "MACRO", "MICRO",
    # ── Tech / semiconductor terms ──
    "NAND", "DRAM", "SRAM", "CPU", "GPU", "NPU", "TPU", "FPGA",
    "ASIC", "API", "SDK", "SAAS", "PAAS", "IAAS", "NLP", "LLM",
    "BERT", "CHAT", "BING", "SIRI", "GROK",
    # ── Brands / products that are NOT tickers ──
    "AVIS",   # ticker is CAR
    "LSEG",   # London Stock Exchange (UK, not US)
    "VWRP",   # Vanguard ETF on London exchange
    "SAME", "NEVER", "HOLES", "BLACK", "DAYS",
}

# US exchange codes reported by yfinance — used to filter non-US stocks
_US_EXCHANGES = {
    "NMS",   # NASDAQ National Market
    "NGM",   # NASDAQ Global Market
    "NCM",   # NASDAQ Capital Market
    "NYQ",   # NYSE
    "ASE",   # NYSE American (AMEX)
    "BTS",   # CBOE / BATS
    "PCX",   # NYSE Arca
    "PNK",   # OTC Pink Sheets
    "OBB",   # OTC Bulletin Board
}

# Regex to match $TICKER or standalone uppercase tickers
TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b')
STANDALONE_TICKER = re.compile(r'\b([A-Z]{2,5})\b')


class RedditScraper:
    def __init__(self):
        creds = get_reddit_credentials()
        self.reddit = praw.Reddit(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            user_agent=creds.get("user_agent", "stock-sentinel/1.0"),
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

    def scrape_for_tickers(self, tickers: List[str], limit_per_ticker: int = 10) -> List[Dict]:
        """Targeted Reddit search for specific tickers (used for watchlist stocks).

        Searches across the key finance subreddits in one call per ticker so
        watchlist stocks get coverage even when they're not trending.
        """
        subreddit = self.reddit.subreddit("+".join(TARGET_SUBREDDITS))
        all_results = []

        for ticker in tickers:
            try:
                query = f'${ticker} OR "{ticker}"'
                for post in subreddit.search(query, sort="new", time_filter="week", limit=limit_per_ticker):
                    found = self.extract_tickers(f"{post.title} {post.selftext}")
                    # Guarantee the searched ticker is linked even if regex misses it
                    if ticker not in found:
                        found.append(ticker)
                    all_results.append({
                        "external_id": post.id,
                        "subreddit": post.subreddit.display_name,
                        "title": post.title,
                        "body": post.selftext[:5000],
                        "author": str(post.author) if post.author else "[deleted]",
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "url": post.url,
                        "created_at": datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                        "tickers": found,
                    })
            except Exception as e:
                print(f"Error searching Reddit for {ticker}: {e}")

        return all_results
