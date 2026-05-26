"""Alpaca trading service.

Loads credentials from AWS Secrets Manager (production) or environment variables (local dev).
Defaults to paper trading. Switch to live by setting `paper=false` in the secret JSON.
"""
import json
import logging
from functools import lru_cache
from typing import Optional, Dict

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_alpaca_credentials() -> Dict[str, any]:
    """
    Fetch Alpaca creds in this priority order:
      1. AWS Secrets Manager (if running on EC2 with IAM role)
      2. Environment variables (ALPACA_API_KEY / ALPACA_API_SECRET)
    Cached for the process lifetime.
    """
    # Try AWS Secrets Manager first
    try:
        import boto3
        client = boto3.client("secretsmanager", region_name=settings.aws_region)
        response = client.get_secret_value(SecretId=settings.alpaca_secret_name)
        secret = json.loads(response["SecretString"])
        if secret.get("api_key") and secret["api_key"] != "PLACEHOLDER":
            logger.info("Loaded Alpaca credentials from AWS Secrets Manager")
            return {
                "api_key": secret["api_key"],
                "api_secret": secret["api_secret"],
                "paper": secret.get("paper", True),
            }
    except Exception as e:
        logger.info(f"Could not load from Secrets Manager ({e}); falling back to env")

    # Fallback to env vars
    if settings.alpaca_api_key:
        logger.info("Loaded Alpaca credentials from environment variables")
        return {
            "api_key": settings.alpaca_api_key,
            "api_secret": settings.alpaca_api_secret,
            "paper": settings.alpaca_paper,
        }

    return {"api_key": None, "api_secret": None, "paper": True}


class AlpacaService:
    """Wrapper around alpaca-py for paper/live trading."""

    def __init__(self):
        creds = get_alpaca_credentials()
        self.api_key = creds["api_key"]
        self.api_secret = creds["api_secret"]
        self.paper = creds["paper"]
        self._trading_client = None
        self._data_client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    @property
    def trading_client(self):
        if self._trading_client is None:
            from alpaca.trading.client import TradingClient
            if not self.is_configured:
                raise RuntimeError("Alpaca credentials not configured")
            self._trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
                paper=self.paper,
            )
        return self._trading_client

    @property
    def data_client(self):
        if self._data_client is None:
            from alpaca.data.historical import StockHistoricalDataClient
            if not self.is_configured:
                raise RuntimeError("Alpaca credentials not configured")
            self._data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
            )
        return self._data_client

    def get_account(self) -> Dict:
        """Return account snapshot (cash, portfolio value, buying power)."""
        if not self.is_configured:
            return {"configured": False}
        acc = self.trading_client.get_account()
        return {
            "configured": True,
            "paper": self.paper,
            "account_number": acc.account_number,
            "status": acc.status.value if hasattr(acc.status, "value") else str(acc.status),
            "cash": float(acc.cash),
            "portfolio_value": float(acc.portfolio_value),
            "buying_power": float(acc.buying_power),
            "equity": float(acc.equity),
        }

    def submit_order(
        self,
        symbol: str,
        qty: float,
        side: str,  # "buy" or "sell"
        order_type: str = "market",
        time_in_force: str = "day",
        client_order_id: Optional[str] = None,
    ):
        """Submit a market order. Returns the alpaca Order object."""
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif_enum = TimeInForce.DAY if time_in_force == "day" else TimeInForce.GTC

        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side_enum,
            time_in_force=tif_enum,
            client_order_id=client_order_id,
        )
        return self.trading_client.submit_order(req)

    def get_positions(self):
        """Return list of open positions."""
        if not self.is_configured:
            return []
        return self.trading_client.get_all_positions()

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the latest trade price for a symbol."""
        try:
            from alpaca.data.requests import StockLatestTradeRequest
            req = StockLatestTradeRequest(symbol_or_symbols=symbol)
            trades = self.data_client.get_stock_latest_trade(req)
            return float(trades[symbol].price)
        except Exception as e:
            logger.warning(f"Failed to get latest price for {symbol}: {e}")
            return None
