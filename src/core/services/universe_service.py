"""Simplified universe service for TickStockPL integration.

PHASE 8 CLEANUP: Simplified to basic ticker management with:
- Simple universe loading and caching
- Basic ticker validation
- No complex universe building or analytics

Removed: Complex universe construction, cache analysis, sophisticated filtering.
"""

import time
from typing import List, Set, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TickStockUniverseManager:
    """Simplified universe manager for ticker management."""
    
    def __init__(self, cache_control=None):
        self.cache_control = cache_control
        self.universe_cache = set()
        self.last_update = None
        
        # Default universe for demo/testing
        self.default_universe = {
            'AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NFLX', 'META', 'NVDA',
            'SPY', 'QQQ', 'IWM', 'GLD', 'TLT', 'VIX', 'UBER', 'LYFT',
            'COIN', 'HOOD', 'PLTR', 'RBLX', 'ZM', 'PELOTON', 'DOCU', 'SQ'
        }
        
        logger.info("UNIVERSE-SERVICE: Simplified universe manager initialized")
    
    def get_core_universe(self) -> List[str]:
        """Get the core universe of tickers."""
        if not self.universe_cache or self._needs_refresh():
            self._refresh_universe()
        
        return list(self.universe_cache)
    
    def get_core_universe_set(self) -> Set[str]:
        """Get the core universe as a set for fast membership testing."""
        if not self.universe_cache or self._needs_refresh():
            self._refresh_universe()
        
        return self.universe_cache.copy()
    
    def is_in_universe(self, ticker: str) -> bool:
        """Check if ticker is in the universe."""
        if not self.universe_cache or self._needs_refresh():
            self._refresh_universe()
        
        return ticker.upper() in self.universe_cache
    
    def add_ticker(self, ticker: str):
        """Add a ticker to the universe."""
        self.universe_cache.add(ticker.upper())
        logger.info(f"UNIVERSE-SERVICE: Added {ticker} to universe")
    
    def remove_ticker(self, ticker: str):
        """Remove a ticker from the universe."""
        self.universe_cache.discard(ticker.upper())
        logger.info(f"UNIVERSE-SERVICE: Removed {ticker} from universe")
    
    def _refresh_universe(self):
        """Refresh the universe from cache or use default."""
        try:
            if self.cache_control:
                # Try to load from cache_control if available
                cached_tickers = self._load_from_cache()
                if cached_tickers:
                    self.universe_cache = set(cached_tickers)
                    logger.info(f"UNIVERSE-SERVICE: Loaded {len(self.universe_cache)} tickers from cache")
                else:
                    self.universe_cache = self.default_universe.copy()
                    logger.info(f"UNIVERSE-SERVICE: Using default universe with {len(self.universe_cache)} tickers")
            else:
                self.universe_cache = self.default_universe.copy()
                logger.info(f"UNIVERSE-SERVICE: Using default universe with {len(self.universe_cache)} tickers")
            
            self.last_update = time.time()
            
        except Exception as e:
            logger.error(f"UNIVERSE-SERVICE: Error refreshing universe: {e}")
            self.universe_cache = self.default_universe.copy()
            self.last_update = time.time()
    
    def _load_from_cache(self) -> List[str]:
        """Load tickers from cache_control if available."""
        try:
            if hasattr(self.cache_control, 'get_all_tickers'):
                return self.cache_control.get_all_tickers()
            else:
                return []
        except Exception as e:
            logger.error(f"UNIVERSE-SERVICE: Error loading from cache: {e}")
            return []
    
    def _needs_refresh(self) -> bool:
        """Check if universe needs refreshing."""
        if not self.last_update:
            return True
        
        # Refresh every hour
        return time.time() - self.last_update > 3600
    
    def get_stats(self) -> Dict[str, Any]:
        """Get universe statistics."""
        return {
            'universe_size': len(self.universe_cache),
            'last_update': self.last_update,
            'has_cache_control': self.cache_control is not None,
            'using_default': self.universe_cache == self.default_universe
        }