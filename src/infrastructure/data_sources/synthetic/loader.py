import random
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SyntheticDataLoader:
    """Loads and manages baseline data for synthetic market data generation with universe support."""
    
    def __init__(self, universe: Optional[str] = None, cache_control=None):
        """
        Initialize SyntheticDataLoader.
        
        Args:
            universe: Universe key to load from cache (e.g., 'DEFAULT_UNIVERSE' or 'market_leaders:top_50')
            cache_control: CacheControl instance for universe loading
        """
        self.universe = universe or 'DEFAULT_UNIVERSE'
        self.cache_control = cache_control
        self.baseline_data = {}
        self.sectors = []
        self.load_method = 'cache'  # Always cache now, no CSV
        
        # Load data
        self.load_from_cache()
    
    def load_from_cache(self) -> bool:
        """Load baseline data from CacheControl universe or stock group."""
        try:
            if not self.cache_control:
                logger.error("No CacheControl instance provided for cache loading")
                return False
            
            tickers = []
            if ':' in self.universe:
                # Handle stock_group format: 'name:key' (NEW: Support for specific keys like 'market_leaders:top_50')
                name, key = self.universe.split(':', 1)
                value = self.cache_control.get_stock_universe_value(name, key)
                if value:
                    tickers = [stock['ticker'] for stock in value.get('stocks', [])]
                    logger.info(f"Loaded stock group {self.universe} with {len(tickers)} tickers")
                else:
                    logger.warning(f"Stock group {self.universe} not found in cache")
                    return False
            else:
                # Existing universe logic
                tickers = self.cache_control.get_universe_tickers(self.universe)
                if not tickers:
                    logger.warning(f"No tickers found in universe: {self.universe}")
                    return False
                logger.info(f"Loaded universe {self.universe} with {len(tickers)} tickers")
            
            logger.debug(f"DIAG-SYNTHETIC-DATA: Loading synthetic data for {len(tickers)} tickers from {self.universe}")
            
            # Generate baseline data for each ticker
            for ticker in tickers:
                # Get stock metadata from cache
                metadata = self.cache_control.get_stock_metadata(ticker)
                
                # Generate baseline data using metadata
                baseline = self._generate_ticker_baseline(ticker, metadata)
                self.baseline_data[ticker] = baseline
                
                # Collect unique sectors
                sector = baseline.get('sector', 'Unknown')
                if sector not in self.sectors:
                    self.sectors.append(sector)
            
            logger.debug(f"DIAG-SYNTHETIC-DATA: Generated synthetic baseline data for {len(self.baseline_data)} tickers from {self.universe}")
            logger.debug(f"DIAG-SYNTHETIC-DATA: Sectors found: {len(self.sectors)} - {', '.join(self.sectors)}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading synthetic data from cache: {e}")
            return False
    
    def _generate_ticker_baseline(self, ticker: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate baseline data for a ticker using metadata."""
        
        # Extract metadata values
        sector = metadata.get('sector', 'Unknown')
        market_cap = metadata.get('market_cap', 0)
        name = metadata.get('name', ticker)
        
        # Generate realistic price based on market cap and sector
        base_price = self._estimate_price_from_market_cap(market_cap, sector)
        
        # Generate realistic volume based on market cap
        avg_volume = self._estimate_volume_from_market_cap(market_cap)
        
        # Generate sector-based volatility
        volatility = self._get_sector_volatility(sector)
        
        # Generate realistic variations
        prev_close = round(base_price * (1 + random.uniform(-0.02, 0.02)), 2)
        opening_price = round(prev_close * (1 + random.uniform(-0.01, 0.01)), 2)
        
        # Average trade size varies based on price
        avg_trade_size = int(max(100, min(1000, base_price * 2)))
        
        # Additional fields for enhanced MarketEvent
        tick_high = round(base_price * (1 + random.uniform(0, 0.005)), 2)
        tick_low = round(base_price * (1 - random.uniform(0, 0.005)), 2)
        tick_open = round(base_price * (1 - random.uniform(-0.002, 0.002)), 2)
        tick_close = base_price
        tick_vwap = round(base_price * (1 + random.uniform(-0.002, 0.002)), 2)
        vwap = round(base_price * (1 + random.uniform(-0.005, 0.005)), 2)
        
        baseline = {
            'ticker': ticker,
            'name': name,
            'sector': sector,
            'baseline_price': base_price,
            'prev_close': prev_close,
            'avg_volume': avg_volume,
            'volatility': volatility,
            'market_cap': market_cap,
            'opening_price': opening_price,
            'avg_trade_size': avg_trade_size,
            
            # Additional fields for enhanced MarketEvent
            'day_high': round(max(base_price, opening_price) * (1 + random.uniform(0, 0.01)), 2),
            'day_low': round(min(base_price, opening_price) * (1 - random.uniform(0, 0.01)), 2),
            'tick_high': tick_high,
            'tick_low': tick_low,
            'tick_open': tick_open,
            'tick_close': tick_close,
            'tick_vwap': tick_vwap,
            'vwap': vwap,
            'volume_weighted_price': vwap
        }
        
        return baseline
    
    def _estimate_price_from_market_cap(self, market_cap: Optional[int], sector: str) -> float:
        """Estimate realistic stock price based on market cap and sector."""
        if not market_cap or market_cap <= 0:
            # Default price for unknown market cap
            return 100.0 + (hash(sector) % 100)
        
        # Rough estimation based on typical shares outstanding for different market cap ranges
        if market_cap > 1000000000000:  # > $1T (mega caps like AAPL, MSFT)
            shares_outstanding = random.uniform(15000000000, 20000000000)  # 15-20B shares
        elif market_cap > 500000000000:  # > $500B
            shares_outstanding = random.uniform(10000000000, 16000000000)  # 10-16B shares
        elif market_cap > 100000000000:  # > $100B
            shares_outstanding = random.uniform(3000000000, 8000000000)   # 3-8B shares
        elif market_cap > 10000000000:   # > $10B
            shares_outstanding = random.uniform(500000000, 3000000000)    # 500M-3B shares
        elif market_cap > 1000000000:    # > $1B
            shares_outstanding = random.uniform(100000000, 500000000)     # 100M-500M shares
        else:  # < $1B
            shares_outstanding = random.uniform(50000000, 200000000)      # 50M-200M shares
        
        estimated_price = market_cap / shares_outstanding
        
        # Add sector-based adjustment
        sector_multipliers = {
            'Technology': 1.2,
            'Healthcare': 1.1,
            'Financial Services': 0.8,
            'Consumer Discretionary': 1.0,
            'Communication Services': 0.9,
            'Industrials': 0.9,
            'Consumer Staples': 1.0,
            'Energy': 0.8,
            'Materials': 0.7,
            'Real Estate': 0.6,
            'Utilities': 0.7
        }
        
        sector_multiplier = sector_multipliers.get(sector, 1.0)
        estimated_price *= sector_multiplier
        
        # Ensure reasonable price range
        estimated_price = max(5.0, min(1000.0, estimated_price))
        
        return round(estimated_price, 2)
    
    def _estimate_volume_from_market_cap(self, market_cap: Optional[int]) -> int:
        """Estimate typical daily volume based on market cap."""
        if not market_cap or market_cap <= 0:
            return 5000000  # Default 5M volume
        
        # Larger companies typically have higher volume
        if market_cap > 500000000000:    # > $500B
            return int(random.uniform(30000000, 80000000))   # 30-80M
        elif market_cap > 100000000000:  # > $100B
            return int(random.uniform(15000000, 40000000))   # 15-40M
        elif market_cap > 10000000000:   # > $10B
            return int(random.uniform(5000000, 20000000))    # 5-20M
        elif market_cap > 1000000000:    # > $1B
            return int(random.uniform(1000000, 10000000))    # 1-10M
        else:  # < $1B
            return int(random.uniform(500000, 3000000))      # 500K-3M
    
    def _get_sector_volatility(self, sector: str) -> float:
        """Get typical volatility for a sector."""
        sector_volatilities = {
            'Technology': 0.020,
            'Healthcare': 0.015,
            'Financial Services': 0.018,
            'Consumer Discretionary': 0.016,
            'Communication Services': 0.014,
            'Industrials': 0.012,
            'Consumer Staples': 0.008,
            'Energy': 0.022,
            'Materials': 0.016,
            'Real Estate': 0.014,
            'Utilities': 0.010
        }
        
        base_volatility = sector_volatilities.get(sector, 0.015)
        # Add some randomness
        volatility = base_volatility * (1 + random.uniform(-0.3, 0.3))
        return round(max(0.005, min(0.05, volatility)), 4)
    
    def get_ticker_baseline(self, ticker: str) -> Dict[str, Any]:
        """Get baseline data for a specific ticker."""
        if ticker in self.baseline_data:
            return self.baseline_data[ticker]
        
        # If ticker not found, generate on-the-fly
        if self.cache_control:
            metadata = self.cache_control.get_stock_metadata(ticker)
            return self._generate_ticker_baseline(ticker, metadata)
        
        # Fallback (no CSV, so default)
        default_price = 100.0 + hash(ticker) % 100
        return {
            'ticker': ticker,
            'baseline_price': default_price,
            'prev_close': default_price,
            'sector': random.choice(self.sectors) if self.sectors else "Technology",
            'avg_volume': 1000000,
            'volatility': 0.015,
            'market_cap': 10000000000,
            'opening_price': default_price,
            'avg_trade_size': 500,
            'day_high': default_price * 1.01,
            'day_low': default_price * 0.99,
            'tick_high': default_price * 1.005,
            'tick_low': default_price * 0.995,
            'tick_open': default_price * 0.998,
            'tick_close': default_price,
            'tick_vwap': default_price * 1.001,
            'vwap': default_price * 1.002,
            'volume_weighted_price': default_price * 1.002
        }

    def get_all_tickers(self) -> List[str]:
        """Get list of all available tickers."""
        return list(self.baseline_data.keys())
    
    def get_universe_info(self) -> Dict[str, Any]:
        """Get information about the loaded universe or stock group."""
        if not self.cache_control:
            # Fallback if no cache (though we always expect cache now)
            return {
                'universe': self.universe,
                'method': 'cache',
                'ticker_count': len(self.baseline_data),
                'sectors': self.sectors,
                'metadata': {}
            }
        
        metadata: Optional[Dict[str, Any]] = None
        method = 'cache'
        
        try:
            if ':' in self.universe:
                # Handle stock_group format: 'name:key'
                name, key = self.universe.split(':', 1)
                value = self.cache_control.get_stock_universe_value(name, key)
                if value:
                    # Derive metadata to match universe format
                    tickers = [stock['ticker'] for stock in value.get('stocks', [])]
                    sectors = list(set(stock.get('sector', 'Unknown') for stock in value.get('stocks', [])))  # Derive if needed
                    metadata = {
                        'count': value.get('count', 0),
                        'criteria': value.get('criteria', ''),
                        'description': value.get('criteria', '')  # Fallback, or generate: f"Stock group {name}/{key}"
                    }
                    # Optionally update self.baseline_data / self.sectors if not already set
                    if not self.baseline_data:
                        self.baseline_data = {t: None for t in tickers}  # Placeholder if needed, but load_from_cache handles
                    if not self.sectors:
                        self.sectors = sectors
                    method = 'stock_group'
                    logger.info(f"Loaded stock group {self.universe} with {metadata['count']} tickers")
                else:
                    logger.warning(f"Stock group {self.universe} not found in cache")
            else:
                # Existing universe logic
                metadata = self.cache_control.get_universe_metadata(self.universe)
                if metadata:
                    logger.info(f"Loaded universe {self.universe} with {metadata.get('count', 0)} tickers")
                else:
                    logger.warning(f"Universe {self.universe} not found in cache")
        
        except Exception as e:
            logger.error(f"Error fetching universe/group info for {self.universe}: {e}")
            metadata = {}
        
        return {
            'universe': self.universe,
            'method': method,
            'ticker_count': len(self.baseline_data),
            'sectors': self.sectors,
            'metadata': metadata or {}
        }

    '''
    @classmethod
    def create_from_universe(cls, universe: str = 'DEFAULT_UNIVERSE', cache_control=None):
        """Factory method to create SyntheticDataLoader from a universe."""
        if not cache_control:
            from src.infrastructure.cache.cache_control import CacheControl
            cache_control = CacheControl()
            cache_control.initialize()
        
        return cls(universe=universe, cache_control=cache_control)
    '''