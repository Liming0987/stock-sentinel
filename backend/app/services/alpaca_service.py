"""Alpaca trading service. Credentials loaded exclusively from AWS Secrets Manager."""
import logging
from typing import Optional, Dict

from app.services.secrets import get_alpaca_credentials, SecretNotConfiguredError

logger = logging.getLogger(__name__)


class AlpacaService:
    """Wrapper around alpaca-py for paper/live trading."""

    def __init__(self):
        try:
            creds = get_alpaca_credentials()
            self.api_key = creds["api_key"]
            self.api_secret = creds["api_secret"]
            self.paper = creds.get("paper", True)
        except SecretNotConfiguredError as e:
            logger.warning(f"Alpaca not configured: {e}")
            self.api_key = None
            self.api_secret = None
            self.paper = True
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

    def is_market_open(self) -> bool:
        """Check if the US equity market is currently open via Alpaca clock."""
        if not self.is_configured:
            return False
        try:
            clock = self.trading_client.get_clock()
            return bool(clock.is_open)
        except Exception as e:
            logger.warning(f"Failed to check market clock: {e}")
            return False

    def get_latest_prices(self, symbols: list) -> dict:
        """Get latest trade price for multiple symbols in one call. Returns {symbol: price}."""
        if not self.is_configured:
            return {}
        try:
            from alpaca.data.requests import StockLatestTradeRequest
            req = StockLatestTradeRequest(symbol_or_symbols=symbols)
            trades = self.data_client.get_stock_latest_trade(req)
            return {sym: float(trades[sym].price) for sym in symbols if sym in trades}
        except Exception as e:
            logger.warning(f"Failed to get latest prices: {e}")
            return {}

    def get_minute_bars(self, symbol: str, limit: int = 120):
        """Get recent 1-minute OHLCV bars for a symbol. Returns a pandas DataFrame or None."""
        if not self.is_configured:
            return None
        try:
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            from datetime import datetime, timedelta, timezone
            end = datetime.now(timezone.utc)
            start = end - timedelta(hours=3)
            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=start,
                end=end,
                limit=limit,
            )
            bars = self.data_client.get_stock_bars(req)
            if symbol not in bars or bars[symbol] is None:
                return None
            return bars[symbol].df
        except Exception as e:
            logger.warning(f"Failed to get minute bars for {symbol}: {e}")
            return None
