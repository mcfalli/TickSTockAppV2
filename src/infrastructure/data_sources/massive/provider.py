"""Simplified Massive.com data provider for TickStockPL integration.

PHASE 6 CLEANUP: Simplified to basic API interactions with:
- Simple REST API calls
- Basic error handling
- Standard TickData conversion
- WebSocket integration ready

Removed: Complex caching, rate limiting, metadata management.
"""
import logging
import time
from datetime import datetime
from typing import Any

import pytz
import requests

from src.core.domain.market.tick import TickData
from src.core.interfaces.data_provider import DataProvider

logger = logging.getLogger(__name__)

class MassiveDataProvider(DataProvider):
    """Simplified Massive.com API client for basic market data."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        # Legacy support: fallback to deprecated API key name if new name not found
        self.api_key = config.get('MASSIVE_API_KEY') or config.get('POLYGON_API_KEY')
        self.base_url = "https://api.massive.com"
        self.session = requests.Session()
        self.market_timezone = pytz.timezone(config.get('MARKET_TIMEZONE', 'US/Eastern'))

        if not self.api_key:
            logger.warning("MASSIVE-PROVIDER: No API key provided")
        else:
            logger.info("MASSIVE-PROVIDER: Initialized with API key")

    def convert_massive_tick(self, ws_data: dict) -> TickData:
        """Convert Massive WebSocket data to TickData."""
        return TickData.from_massive_ws(ws_data)

    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Make a simple request to the Massive API."""
        if not self.api_key:
            logger.error("MASSIVE-PROVIDER: API key required")
            return {"status": "error", "message": "API key required"}

        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params['apiKey'] = self.api_key

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"MASSIVE-PROVIDER: API request error: {e}")
            return {"status": "error", "message": str(e)}

    def get_market_status(self) -> str:
        """Get current market status from Massive API."""
        try:
            result = self._make_request("/v1/marketstatus/now")

            if result.get("status") == "OK":
                market_status = result.get("market")
                if market_status == "open":
                    return "REGULAR"
                if market_status == "extended-hours":
                    # Determine pre or after market based on time
                    utc_now = datetime.now(pytz.utc)
                    eastern_now = utc_now.astimezone(self.market_timezone)
                    if eastern_now.hour < 9 or (eastern_now.hour == 9 and eastern_now.minute < 30):
                        return "PRE"
                    return "AFTER"
                return "CLOSED"
            return self._get_market_status_from_time()
        except Exception as e:
            logger.error(f"MASSIVE-PROVIDER: Error getting market status: {e}")
            return self._get_market_status_from_time()

    def _get_market_status_from_time(self) -> str:
        """Fallback market status based on current time."""
        utc_now = datetime.now(pytz.utc)
        eastern_now = utc_now.astimezone(self.market_timezone)

        if eastern_now.weekday() < 5:  # Monday to Friday
            if (eastern_now.hour == 9 and eastern_now.minute >= 30) or (9 < eastern_now.hour < 16):
                return "REGULAR"
            if eastern_now.hour >= 4 and eastern_now.hour < 9 or (eastern_now.hour == 9 and eastern_now.minute < 30):
                return "PRE"
            if 16 <= eastern_now.hour < 20:
                return "AFTER"
        return "CLOSED"

    def get_ticker_price(self, ticker: str) -> float:
        """Get last trade price for a ticker."""
        endpoint = f"/v2/last/trade/{ticker}"
        result = self._make_request(endpoint)

        if result.get("status") == "OK" and result.get("results"):
            return result["results"]["p"]
        logger.warning(f"MASSIVE-PROVIDER: Failed to get price for {ticker}")
        return None

    def get_ticker_details(self, ticker: str) -> dict[str, Any]:
        """Get detailed ticker information."""
        endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        result = self._make_request(endpoint)

        if result.get("status") == "OK" and result.get("ticker"):
            data = result["ticker"]
            last_trade = data.get("lastTrade", {})
            day_data = data.get("day", {})
            prev_day = data.get("prevDay", {})

            return {
                "ticker": ticker,
                "name": f"{ticker} Corporation",
                "price": last_trade.get("p"),
                "change": day_data.get("c"),
                "change_percent": day_data.get("cp"),
                "open": day_data.get("o"),
                "high": day_data.get("h"),
                "low": day_data.get("l"),
                "prev_close": prev_day.get("c"),
                "volume": day_data.get("v"),
                "sector": "Unknown",
                "last_updated": datetime.now().isoformat()
            }
        logger.warning(f"MASSIVE-PROVIDER: Failed to get details for {ticker}")
        return {
            "ticker": ticker,
            "error": True,
            "message": result.get("message", "Unknown error")
        }

    def get_multiple_tickers(self, tickers: list[str]) -> dict[str, dict[str, Any]]:
        """Get data for multiple tickers."""
        results = {}

        # Simple batch processing with basic delay
        for i, ticker in enumerate(tickers):
            results[ticker] = self.get_ticker_details(ticker)
            if i > 0 and i % 5 == 0:  # Small delay every 5 requests
                time.sleep(0.5)

        return results

    def is_available(self) -> bool:
        """Check if Massive API is available."""
        if not self.api_key:
            logger.warning("MASSIVE-PROVIDER: No API key available")
            return False

        try:
            endpoint = "/v1/marketstatus/now"
            params = {"apikey": self.api_key}
            response = requests.get(f"{self.base_url}{endpoint}",
                                  params=params,
                                  timeout=10)
            success = response.status_code == 200
            if success:
                logger.info("MASSIVE-PROVIDER: API availability confirmed")
            else:
                logger.warning(f"MASSIVE-PROVIDER: API availability check failed - status: {response.status_code}")
            return success
        except Exception as e:
            logger.error(f"MASSIVE-PROVIDER: Availability check failed: {e}")
            return False
