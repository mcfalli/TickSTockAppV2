"""
Polygon.io data provider with enhanced rate limiting and caching.
"""
import os
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Any, Optional
import threading
import json
import requests  # Standard import, patched by app.py
import time

from src.infrastructure.data_sources.polygon..base.data_provider import DataProvider
from src.core.domain.market.tick import TickData

from config.logging_config import get_domain_logger, LogDomain
logger = get_domain_logger(LogDomain.CORE, 'polygon_data_provider')

class PolygonDataProvider(DataProvider):
    """Class to handle Polygon.io API interactions with enhanced rate limiting and caching"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Polygon API client.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Get API key directly from config
        self.api_key = config.get('POLYGON_API_KEY')
        
        if not self.api_key:
            logger.warning("POLYGON-DATA_PROVIDER: No Polygon API key provided in config. API calls will fail.")
        else:
            logger.info("POLYGON-DATA_PROVIDER: Polygon API key found in configuration")
        
        self.base_url = "https://api.polygon.io"
        self.session = requests.Session()
        
        # Rate limiting settings
        self.rate_limit_remaining = 100  # Initial assumption
        self.rate_limit_reset = 0
        self.rate_limit_mutex = threading.Lock()  # Add mutex for thread safety
        self.min_request_interval = config.get('API_MIN_REQUEST_INTERVAL', 0.12)  # Minimum time between requests
        self.last_request_time = 0
        
        # Define caching settings
        self.market_timezone = pytz.timezone(config.get('MARKET_TIMEZONE', 'US/Eastern'))
        self.cache = {}
        self.cache_expiry = {}
        self.default_cache_ttl = config.get('API_CACHE_TTL', 60)  # Default cache TTL in seconds
        
        # Set up caching TTLs for different data types
        self.cache_ttls = {
            'market_status': 30,  # Market status - cache for 1 minute
            'ticker_price': 2,    # Price data - cache for 5 seconds
            'ticker_details': 120, # Ticker details - cache for 5 minutes
            'snapshot': 5        # Snapshot data - cache for 10 seconds
        }
        
        logger.info("POLYGON-DATA_PROVIDER: Initialized Polygon.io data provider")
    

    def convert_polygon_tick(self, ws_data: dict) -> TickData:
        """Convert Polygon WebSocket data to TickData."""
        from src.core.domain.market.tick import TickData
        return TickData.from_polygon_ws(ws_data)

    def _handle_rate_limit(self):
        """
        Modified rate limiting for unlimited subscription plan.
        Still maintains minimal intervals to prevent request flooding.
        """
        current_time = time.time()
        
        with self.rate_limit_mutex:
            # Reduce minimum interval between requests
            time_since_last = current_time - self.last_request_time
            # Change from 0.12s to 0.05s minimum interval
            min_interval = self.config.get('API_MIN_REQUEST_INTERVAL', 0.05)
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                logger.debug(f"POLYGON-DATA_PROVIDER: Minimal interval spacing: {sleep_time:.3f}s")
                time.sleep(sleep_time)
            
            # Significantly relax the buffer threshold
            # Change from 5 to 1 (just enough to detect rate limit headers)
            if self.rate_limit_remaining <= 1:
                if current_time < self.rate_limit_reset:
                    sleep_time = self.rate_limit_reset - current_time + 0.1
                    logger.warning(f"POLYGON-DATA_PROVIDER: Rate limit approaching, sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
            
            # Update last request time
            self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None, cache_key_override: str = None, cache_ttl: int = None) -> Dict:
        """
        Make a request to the Polygon API with enhanced rate limit handling and caching.
        
        Args:
            endpoint: API endpoint to call
            params: Optional query parameters
            cache_key_override: Optional override for the cache key
            cache_ttl: Time to live for cache entry in seconds, overrides default
            
        Returns:
            JSON response as dictionary
        """
        if not self.api_key:
            logger.error("POLYGON-DATA_PROVIDER: Polygon API key is required but not provided")
            return {"status": "error", "message": "API key is required"}
        
        # Create cache key from endpoint and params
        cache_key = cache_key_override or (endpoint + str(params or {}))
        
        # Check if we have a cached response that's still valid
        current_time = time.time()
        if cache_key in self.cache and self.cache_expiry.get(cache_key, 0) > current_time:
            logger.debug(f"POLYGON-DATA_PROVIDER: Cache hit for {endpoint}")
            return self.cache[cache_key]
        
        # Determine cache TTL - use parameter, or look up by endpoint type, or use default
        if cache_ttl is None:
            for key, ttl in self.cache_ttls.items():
                if key in endpoint:
                    cache_ttl = ttl
                    break
            if cache_ttl is None:
                cache_ttl = self.default_cache_ttl
        
        # Handle rate limiting before making the request
        self._handle_rate_limit()
        
        # Prepare request
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params['apiKey'] = self.api_key
        
        logger.debug(f"POLYGON-DATA_PROVIDER: Requesting {endpoint} with params {params}")  # Was INFO
        try:
            response = self.session.get(url, params=params, timeout=10)
            
            # Update rate limit info if headers are present
            if 'X-Ratelimit-Remaining' in response.headers:
                with self.rate_limit_mutex:
                    self.rate_limit_remaining = int(response.headers['X-Ratelimit-Remaining'])
                    logger.debug(f"POLYGON-DATA_PROVIDER: Rate limit remaining: {self.rate_limit_remaining}")
                    
            if 'X-Ratelimit-Reset' in response.headers:
                with self.rate_limit_mutex:
                    self.rate_limit_reset = int(response.headers['X-Ratelimit-Reset'])
                    
            response.raise_for_status()
            result = response.json()

            logger.debug(f"POLYGON-DATA_PROVIDER: Received response for {endpoint}") 

            # Cache the response
            self.cache[cache_key] = result
            self.cache_expiry[cache_key] = current_time + cache_ttl
            
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"POLYGON-DATA_PROVIDER: API request error ({endpoint}): {e}")
            # Return cached data if available (even if expired) when API request fails
            if cache_key in self.cache:
                logger.warning(f"POLYGON-DATA_PROVIDER: Using expired cache data for {endpoint} due to request error")
                return self.cache[cache_key]
            return {"status": "error", "message": str(e)}
    
    def get_market_status(self) -> str:
        """
        Get the current market status from Polygon.io API.
        
        Returns:
            str: Market status ("PRE", "REGULAR", "AFTER", or "CLOSED")
        """
        try:
            result = self._make_request("/v1/marketstatus/now", 
                                       cache_key_override="market_status", 
                                       cache_ttl=self.cache_ttls['market_status'])
            
            if result.get("status") == "OK" or "market" in result:
                market_status = result.get("market")
                if market_status == "open":
                    return "REGULAR"
                elif market_status == "extended-hours":
                    # Determine if pre or after market
                    utc_now = datetime.now(pytz.utc)
                    eastern_now = utc_now.astimezone(self.market_timezone)
                    if eastern_now.hour < 9 or (eastern_now.hour == 9 and eastern_now.minute < 30):
                        return "PRE"
                    else:
                        return "AFTER"
                else:
                    return "CLOSED"
            else:
                # Fallback to time-based determination
                return self._get_market_status_from_time()
        except Exception as e:
            logger.error(f"POLYGON-DATA_PROVIDER: Error getting market status: {e}")
            return self._get_market_status_from_time()
    
    def _get_market_status_from_time(self) -> str:
        """
        Determine market status based on current time (fallback method).
        
        Returns:
            str: Market status ("PRE", "REGULAR", "AFTER", or "CLOSED")
        """
        utc_now = datetime.now(pytz.utc)
        eastern_now = utc_now.astimezone(self.market_timezone)
        
        market_status = "CLOSED"
        if eastern_now.weekday() < 5:  # Monday to Friday
            if (eastern_now.hour == 9 and eastern_now.minute >= 30) or (eastern_now.hour > 9 and eastern_now.hour < 16):
                market_status = "REGULAR"
            elif (eastern_now.hour >= 4 and eastern_now.hour < 9) or (eastern_now.hour == 9 and eastern_now.minute < 30):
                market_status = "PRE"
            elif eastern_now.hour >= 16 and eastern_now.hour < 20:
                market_status = "AFTER"
        
        return market_status
    
    def get_ticker_price(self, ticker: str) -> float:
        """
        Get the last trade price for a ticker from Polygon.io API.
        
        Args:
            ticker: Stock symbol to get price for
            
        Returns:
            float: Current price or None on error
        """
        endpoint = f"/v2/last/trade/{ticker}"
        cache_key = f"last_trade_{ticker}"
        
        result = self._make_request(endpoint, cache_key_override=cache_key, 
                                  cache_ttl=self.cache_ttls['ticker_price'])
        
        if result.get("status") == "OK" and result.get("results"):
            return result["results"]["p"]  # Last price
        else:
            logger.warning(f"POLYGON-DATA_PROVIDER: Failed to get price for {ticker}, error: {result.get('message', 'Unknown error')}")
            return None
    
    def get_ticker_details(self, ticker: str) -> Dict[str, Any]:
        """
        Get detailed information for a ticker from Polygon.io API with enhanced caching.
        
        Args:
            ticker: Stock symbol to get details for
            
        Returns:
            dict: Ticker details
        """
        # Use a combined approach with snapshot and details
        snapshot_endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        cache_key = f"ticker_details_{ticker}"
        
        result = self._make_request(snapshot_endpoint, cache_key_override=cache_key, 
                                  cache_ttl=self.cache_ttls['ticker_details'])
        
        if (result.get("status") == "OK" or "ticker" in result) and result.get("ticker"):
            data = result["ticker"]
            last_trade = data.get("lastTrade", {})
            day_data = data.get("day", {})
            prev_day = data.get("prevDay", {})
            
            # Get additional ticker info using the reference endpoint if needed
            # Only query this occasionally as it rarely changes
            ticker_name = ticker
            ticker_sector = "Unknown"
            
            # Check if we need to refresh ticker metadata (less frequently updated)
            metadata_cache_key = f"ticker_metadata_{ticker}"
            if metadata_cache_key not in self.cache or self.cache_expiry.get(metadata_cache_key, 0) <= time.time():
                try:
                    details_endpoint = f"/v3/reference/tickers/{ticker}"
                    details_result = self._make_request(details_endpoint, cache_ttl=86400)  # Cache for a day
                    
                    if "results" in details_result:
                        details = details_result.get("results", {})
                        ticker_name = details.get("name", ticker)
                        ticker_sector = details.get("sic_description", "Unknown")
                        
                        # Cache this metadata separately with long TTL
                        self.cache[metadata_cache_key] = {
                            "name": ticker_name,
                            "sector": ticker_sector
                        }
                        self.cache_expiry[metadata_cache_key] = time.time() + 86400  # 24 hours
                except Exception as e:
                    logger.warning(f"POLYGON-DATA_PROVIDER: Error fetching ticker metadata for {ticker}: {e}")
            else:
                # Use cached metadata
                metadata = self.cache.get(metadata_cache_key, {})
                ticker_name = metadata.get("name", ticker)
                ticker_sector = metadata.get("sector", "Unknown")
            
            return {
                "ticker": ticker,
                "name": ticker_name,
                "price": last_trade.get("p"),
                "change": day_data.get("c"),
                "change_percent": day_data.get("cp"),
                "open": day_data.get("o"),
                "high": day_data.get("h"),
                "low": day_data.get("l"),
                "prev_close": prev_day.get("c"),
                "volume": day_data.get("v"),
                "sector": ticker_sector,
                "last_updated": datetime.now().isoformat()
            }
        else:
            logger.warning(f"POLYGON-DATA_PROVIDER: Failed to get details for {ticker}, error: {result.get('message', 'Unknown error')}")
            return {
                "ticker": ticker,
                "error": True,
                "message": result.get("message", "Unknown error")
            }
    
    def get_multiple_tickers(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get data for multiple tickers from Polygon.io API with batching optimization.
        
        Args:
            tickers: List of stock symbols
            
        Returns:
            dict: Dictionary mapping tickers to their data
        """
        results = {}
        
        # Try to use the multi-ticker snapshot endpoint if available
        if len(tickers) <= 50:  # API limit for tickers parameter
            try:
                # Join tickers with comma
                tickers_param = ','.join(tickers)
                
                # Use grouped snapshot endpoint
                endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers"
                params = {'tickers': tickers_param}
                cache_key = f"multi_ticker_snapshot_{tickers_param}"
                
                group_result = self._make_request(endpoint, params=params, 
                                               cache_key_override=cache_key,
                                               cache_ttl=self.cache_ttls['snapshot'])
                
                if group_result.get("status") == "OK" and group_result.get("tickers"):
                    # Process batch results
                    for ticker_data in group_result.get("tickers", []):
                        ticker = ticker_data.get("ticker")
                        if ticker:
                            results[ticker] = self._process_snapshot_data(ticker_data, ticker)
                    
                    # If we got results for all tickers, return them
                    if len(results) == len(tickers):
                        return results
                    
                    # Otherwise continue with individual requests for missing tickers
                    logger.warning(f"POLYGON-DATA_PROVIDER: Batch request got {len(results)} of {len(tickers)} tickers, fetching remaining individually")
            except Exception as e:
                logger.error(f"POLYGON-DATA_PROVIDER: Error in batch ticker request: {e}")
                # Continue with individual requests
        
        # Process individually if batch failed or for any missing tickers
        missing_tickers = [t for t in tickers if t not in results]
        if missing_tickers:
            # Process in smaller batches to avoid rate limiting
            batch_size = 5
            for i in range(0, len(missing_tickers), batch_size):
                batch = missing_tickers[i:i+batch_size]
                
                for ticker in batch:
                    results[ticker] = self.get_ticker_details(ticker)
                
                # Small delay between batches
                if i + batch_size < len(missing_tickers):
                    time.sleep(0.5)
        
        return results
    
    def get_recent_candle(self, ticker, start, end, timeframe='5'):
        """
        Legacy method for fetching candle data - retained for compatibility but not actively used.
        Will be removed in future versions.
        """
        logger.warning(f"POLYGON-DATA_PROVIDER: get_recent_candle is deprecated and will be removed in future versions")
        return None
        
    def _process_snapshot_data(self, data: Dict, ticker: str) -> Dict:
        """Helper to process snapshot data into a consistent format"""
        last_trade = data.get("lastTrade", {})
        day_data = data.get("day", {})
        prev_day = data.get("prevDay", {})
        
        # Get ticker name and sector from cache if available
        metadata_cache_key = f"ticker_metadata_{ticker}"
        metadata = self.cache.get(metadata_cache_key, {})
        ticker_name = metadata.get("name", ticker)
        ticker_sector = metadata.get("sector", "Unknown")
        
        return {
            "ticker": ticker,
            "name": ticker_name,
            "price": last_trade.get("p"),
            "change": day_data.get("c"),
            "change_percent": day_data.get("cp"),
            "open": day_data.get("o"),
            "high": day_data.get("h"),
            "low": day_data.get("l"),
            "prev_close": prev_day.get("c"),
            "volume": day_data.get("v"),
            "sector": ticker_sector,
            "last_updated": datetime.now().isoformat()
        }
    
    def is_available(self):
        logger.info("POLYGON-DATA_PROVIDER: Checking Polygon API availability...")
        endpoint = "/v1/marketstatus/now"
        logger.debug(f"POLYGON-DATA_PROVIDER: Testing connection to {self.base_url}{endpoint}")
        logger.debug(f"POLYGON-DATA_PROVIDER: Using API key: {self.api_key[:4]}*** (length: {len(self.api_key)})")

        # Try direct requests
        for attempt in range(3):
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(f"{self.base_url}{endpoint}", headers=headers, timeout=5)
                response_dict = response.json()
                if isinstance(response_dict, dict) and 'market' in response_dict:
                    logger.info("POLYGON-DATA_PROVIDER: WebSockets SUCCESS: Connected via requests")
                    return True
                else:
                    logger.warning(f"POLYGON-DATA_PROVIDER: Unexpected response: {response_dict}")
            except Exception as e:
                logger.error(f"POLYGON-DATA_PROVIDER: CONNECTION ERROR: Request failed (attempt {attempt + 1}/3): {str(e)}")
            time.sleep(2 if attempt < 2 else 0)

        logger.debug("POLYGON-DATA_PROVIDER: Falling back to requests library for availability check")
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.base_url}{endpoint}", headers=headers, timeout=5)
            if response.status_code == 200:
                logger.debug(f"POLYGON-DATA_PROVIDER: Response status code: {response.status_code}")
                logger.info("POLYGON-DATA_PROVIDER: WebSockets SUCCESS: Connected via requests FALLBACK APPROACH")
                return True
            else:
                logger.warning(f"POLYGON-DATA_PROVIDER: Unexpected status code: {response.status_code}")
        except Exception as e:
            logger.error(f"POLYGON-DATA_PROVIDER: Fallback request failed: {str(e)}")
        logger.error("POLYGON-DATA_PROVIDER: All attempts failed - Polygon API unavailable")
        return False