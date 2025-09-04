"""
Data fetch utilities for OHLCV candles via ccxt.

What it does:
- Initializes a ccxt exchange client using credentials from `Settings`.
- Enables sandbox mode for testnet-like environments when supported.
- Fetches recent OHLCV candles and normalizes them into dicts.

Where it is used:
- Instantiated by `paperbot.main` to pull candles per symbol.
"""

import logging
from typing import List, Dict, Any
import ccxt
from paperbot.config.loader import load_settings, Settings

class CandleFetcher:
    """Thin wrapper around ccxt to fetch normalized OHLCV candles."""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.exchange = self._init_exchange()

    def _init_exchange(self):
        """Create and configure a ccxt exchange instance.

        Enables sandbox/testnet on supported exchanges when `environment`
        indicates a test setting (e.g., `spot-testnet`).
        """
        exchange_class = getattr(ccxt, self.settings.exchange)
        params = {
            "apiKey": self.settings.api_key,
            "secret": self.settings.api_secret,
        }
        if self.settings.api_passphrase:
            params["password"] = self.settings.api_passphrase
        exchange = exchange_class(params)
        # Enable testnet/sandbox if needed
        if (
            "TESTNET" in self.settings.environment.upper()
            or (self.settings.exchange == "binance" and self.settings.environment == "spot-testnet")
        ):
            if hasattr(exchange, "set_sandbox_mode"):
                exchange.set_sandbox_mode(True)
        return exchange

    def fetch_candles(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent OHLCV and normalize to dictionaries.

        Returns a list of dicts with keys: timestamp, open, high, low, close, volume.
        """
        timeframe = self.settings.timeframe
        candles = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        # Normalize to dicts with UTC timestamps
        return [
            {
                "timestamp": c[0],
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5],
            }
            for c in candles
        ]
