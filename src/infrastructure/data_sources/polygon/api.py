"""
Polygon.io API integration module for the Stock Market High/Low Tracker.
This module handles API interactions with Polygon.io for real-time stock data.
"""

import logging
import os
import time
from datetime import datetime

import pytz
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PolygonAPI:
    """Class to handle Polygon.io API interactions"""

    def __init__(self, api_key: str = None):
        """
        Initialize the Polygon API client.
        
        Args:
            api_key: Polygon.io API key. If None, tries to get from environment variable.
        """
        self.api_key = api_key or os.environ.get('POLYGON_API_KEY')
        if not self.api_key:
            logger.warning("POLYGON-API: No Polygon API key provided. Please set POLYGON_API_KEY environment variable.")

        self.base_url = "https://api.polygon.io"
        self.session = requests.Session()
        self.rate_limit_remaining = 100  # Initial assumption
        self.rate_limit_reset = 0
        self.eastern_tz = pytz.timezone('US/Eastern')

    def _handle_rate_limit(self):
        """Handle rate limiting by waiting if necessary"""
        if self.rate_limit_remaining <= 5:  # Buffer to prevent hitting actual limit
            now = time.time()
            if now < self.rate_limit_reset:
                sleep_time = self.rate_limit_reset - now + 1  # +1 second buffer
                logger.info(f"POLYGON-API: Rate limit approaching, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """
        Make a request to the Polygon API with rate limit handling.
        
        Args:
            endpoint: API endpoint to call
            params: Optional query parameters
            
        Returns:
            JSON response as dictionary
        """
        if not self.api_key:
            raise ValueError("Polygon API key is required")

        self._handle_rate_limit()

        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params['apiKey'] = self.api_key

        try:
            response = self.session.get(url, params=params)

            # Update rate limit info
            if 'X-Ratelimit-Remaining' in response.headers:
                self.rate_limit_remaining = int(response.headers['X-Ratelimit-Remaining'])
            if 'X-Ratelimit-Reset' in response.headers:
                self.rate_limit_reset = int(response.headers['X-Ratelimit-Reset'])

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"POLYGON-API: API request error: {e}")
            return {"status": "error", "message": str(e)}

    def get_market_status(self) -> str:
        """
        Get the current market status (PRE, REGULAR, AFTER, CLOSED).
        
        Returns:
            String indicating market status
        """
        try:
            result = self._make_request("/v1/marketstatus/now")

            if result.get("status") == "OK":
                market_status = result.get("market")
                if market_status == "open":
                    return "REGULAR"
                if market_status == "extended-hours":
                    # Determine if pre or after market
                    utc_now = datetime.now(pytz.utc)
                    eastern_now = utc_now.astimezone(self.eastern_tz)
                    if eastern_now.hour < 9 or (eastern_now.hour == 9 and eastern_now.minute < 30):
                        return "PRE"
                    return "AFTER"
                return "CLOSED"
            # Fallback to time-based determination
            return self._get_market_status_from_time()
        except Exception as e:
            logger.error(f"POLYGON-API: Error getting market status: {e}")
            return self._get_market_status_from_time()

    def _get_market_status_from_time(self) -> str:
        """
        Determine market status based on current time (fallback method).
        
        Returns:
            String indicating market status
        """
        utc_now = datetime.now(pytz.utc)
        eastern_now = utc_now.astimezone(self.eastern_tz)

        market_status = "CLOSED"
        if eastern_now.weekday() < 5:  # Monday to Friday
            if (eastern_now.hour == 9 and eastern_now.minute >= 30) or (eastern_now.hour > 9 and eastern_now.hour < 16):
                market_status = "REGULAR"
            elif (eastern_now.hour >= 4 and eastern_now.hour < 9) or (eastern_now.hour == 9 and eastern_now.minute < 30):
                market_status = "PRE"
            elif eastern_now.hour >= 16 and eastern_now.hour < 20:
                market_status = "AFTER"

        return market_status

    def get_daily_high_low(self, ticker: str) -> dict:
        """
        Get daily high/low information for a ticker.
        
        Args:
            ticker: Stock symbol to get data for
            
        Returns:
            Dictionary with high and low data
        """
        # Format today's date
        utc_now = datetime.now(pytz.utc)
        eastern_now = utc_now.astimezone(self.eastern_tz)
        date_str = eastern_now.strftime("%Y-%m-%d")

        endpoint = f"/v2/aggs/ticker/{ticker}/range/1/day/{date_str}/{date_str}"
        result = self._make_request(endpoint)

        if result.get("status") == "OK" and result.get("results"):
            data = result["results"][0]
            return {
                "high": data.get("h"),
                "low": data.get("l"),
                "current": data.get("c")
            }
        return {"high": None, "low": None, "current": None}

    def get_last_price(self, ticker: str) -> float | None:
        """
        Get the last trade price for a ticker.
        
        Args:
            ticker: Stock symbol to get data for
            
        Returns:
            Float with the last price, or None on error
        """
        endpoint = f"/v2/last/trade/{ticker}"
        result = self._make_request(endpoint)

        if result.get("status") == "OK" and result.get("results"):
            return result["results"]["p"]  # Last price
        return None

    def get_ticker_snapshot(self, symbols: list[str]) -> dict[str, dict]:
        """
        Get snapshot data for multiple tickers.
        
        Args:
            symbols: List of stock symbols to get data for
            
        Returns:
            Dictionary with ticker data
        """
        results = {}

        # Process in batches to avoid rate limiting
        batch_size = 25
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]

            for ticker in batch:
                # Get snapshot data for each ticker
                endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
                result = self._make_request(endpoint)

                if result.get("status") == "OK" and result.get("ticker"):
                    data = result["ticker"]
                    results[ticker] = {
                        "price": data.get("lastTrade", {}).get("p"),
                        "day_high": data.get("day", {}).get("h"),
                        "day_low": data.get("day", {}).get("l"),
                        "prev_close": data.get("prevDay", {}).get("c")
                    }
                else:
                    results[ticker] = {
                        "price": None,
                        "day_high": None,
                        "day_low": None,
                        "prev_close": None,
                        "error": result.get("error")
                    }

                # Small delay between requests to be gentle on the API
                time.sleep(0.1)

        return results
