import logging
import os
import time
from typing import Dict, List, Set, Any, Optional
from threading import Lock
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from src.infrastructure.database.models.base import db, CacheEntry

logger = logging.getLogger(__name__)

class CacheControl:
    """Singleton class to manage cached stock lists and metadata."""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        """Ensure singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CacheControl, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize cache instance."""
        if not hasattr(self, '_initialized'):
            self._initialized = False
            self.cache: Dict[str, Any] = {}
            self.environment = None
    
    def initialize(self, environment: str = 'DEFAULT'):
        """Initialize cache with database data if not already initialized."""
        
        if self._initialized:
            logger.info("CacheControl already initialized for environment: %s", self.environment)
            return
        
        self.environment = environment
        
        try:
            if self.load_settings_from_db(environment):
                logger.info("CacheControl initialized from src.infrastructure.database with %d cache sections for environment: %s", 
                        len(self.cache), environment)
            else:
                logger.error("Database load failed for environment %s", environment)
                raise RuntimeError(f"Failed to load cache from src.infrastructure.database for environment: {environment}")
        except Exception as e:
            logger.error("Error initializing cache for environment %s: %s", environment, str(e))
            raise RuntimeError(f"Cache initialization failed for {environment}") from e
        
        self._initialized = True

    def load_settings_from_db(self, environment='DEFAULT'):
        """
        Load cache data from the database for the specified environment, falling back to DEFAULT.
        
        Args:
            environment (str): Environment to load (e.g., 'DEFAULT', 'PROD'). Defaults to 'DEFAULT'.
        
        Returns:
            bool: True if loading succeeded, False otherwise.
        """
        try:
            # Query for specified environment
            stmt = select(CacheEntry).where(CacheEntry.environment == environment)
            result = db.session.execute(stmt).scalars().all()
            
            # Fall back to DEFAULT if no rows found
            if not result:
                logger.warning("No cache entries found for environment '%s', falling back to DEFAULT", environment)
                stmt = select(CacheEntry).where(CacheEntry.environment == 'DEFAULT')
                result = db.session.execute(stmt).scalars().all()
            
            if not result:
                logger.error("No cache entries found for DEFAULT environment")
                return False
            
            # Initialize cache structure
            self.cache = {
                # App settings (unchanged)
                'app_settings': {},
                
                # Universe selections for modal (500-1500 stocks each)
                'universes': {},
                
                # Granular stock groupings (retain all cache_entries individually)
                'stock_groups': {
                    'market_cap': {},
                    'sector_leaders': {},
                    'themes': {},
                    'thematic': {},
                    'industry': {},
                    'market_leaders': {},
                    'complete': {},
                    'priority_stocks': {} 
                },
                
                # Stock metadata lookup (ticker -> metadata)
                'stock_metadata': {},
                
                # Universe metadata (universe_key -> metadata)
                'universe_metadata': {},
                
                # Legacy compatibility (will phase out)
                'market_stock_list': [],
                'themes': {},
                'mag7_stock_list': [],
                'top_priority_stock_list': [],
                'secondary_priority_stock_list': [],
                'tertiary_priority_stock_list': [],
                'sectors': [],
                'industries': [],
                'industry_top_stocks': {},
                'stock_to_industry': {}
            }
            
            # Process database rows - load everything from cache_entries
            stock_universe_entries = {}
            
            for entry in result:
                if entry.type == 'app_settings':
                    # Skip database URI settings - these come from environment
                    if entry.key in ('SQLALCHEMY_DATABASE_URI', 'DATABASE_URI'):
                        continue
                        
                    if 'value' in entry.value:
                        self.cache['app_settings'][entry.key] = entry.value['value']
                    else:
                        logger.warning("Invalid app_settings value for key %s: %s", entry.key, entry.value)
                
                elif entry.type == 'stock_universe':
                    # Load all stock_universe entries into stock_groups
                    if entry.name not in self.cache['stock_groups']:
                        self.cache['stock_groups'][entry.name] = {}
                    
                    # Store full data for internal use
                    self.cache['stock_groups'][entry.name][entry.key] = entry.value
                    
                    # Extract tickers and metadata for performance
                    if 'stocks' in entry.value:
                        tickers = [stock['ticker'] for stock in entry.value['stocks']]
                        
                        # Build stock metadata lookup
                        for stock in entry.value['stocks']:
                            ticker = stock['ticker']
                            if ticker not in self.cache['stock_metadata']:
                                self.cache['stock_metadata'][ticker] = {
                                    'name': stock.get('name', ''),
                                    'sector': stock.get('sector', 'Unknown'),
                                    'industry': stock.get('industry', 'Unknown'),
                                    'market_cap': stock.get('market_cap'),
                                    'exchange': stock.get('exchange', '')
                                }
                        
                        # Store for universe building
                        stock_universe_entries[f"{entry.name}_{entry.key}"] = {
                            'tickers': tickers,
                            'count': len(tickers),
                            'metadata': {
                                'criteria': entry.value.get('criteria', ''),
                                'last_updated': entry.value.get('last_updated', '')
                            }
                        }
                
                elif entry.type == 'priority_stocks':
                    # Store priority stocks in cache
                    if 'priority_stocks' not in self.cache:
                        self.cache['priority_stocks'] = {}
                    
                    # Store in both locations for compatibility
                    self.cache['priority_stocks'][entry.key] = entry.value
                    
                    # Also store in stock_groups for consistency
                    if 'priority_stocks' not in self.cache['stock_groups']:
                        self.cache['stock_groups']['priority_stocks'] = {}
                    self.cache['stock_groups']['priority_stocks'][entry.key] = entry.value
                    
                    # Build fast lookup set for priority tickers
                    if entry.key == 'priority_list' and 'stocks' in entry.value:
                        priority_tickers = [stock['ticker'] for stock in entry.value['stocks']]
                        self._priority_stock_set = set(priority_tickers)
                        
                        # Also create separate sets for each level
                        self._top_priority_set = set([
                            stock['ticker'] for stock in entry.value['stocks']
                            if stock.get('priority_level') == 'TOP'
                        ])
                        self._secondary_priority_set = set([
                            stock['ticker'] for stock in entry.value['stocks']
                            if stock.get('priority_level') == 'SECONDARY'
                        ])



                elif entry.type == 'stock_stats':
                    # Store stats
                    if 'stock_stats' not in self.cache:
                        self.cache['stock_stats'] = {}
                    if entry.name not in self.cache['stock_stats']:
                        self.cache['stock_stats'][entry.name] = {}
                    self.cache['stock_stats'][entry.name][entry.key] = entry.value
                
                elif entry.type == 'themes':
                    # Handle both new detailed themes and legacy simple lists
                    if entry.key == 'list' and 'value' in entry.value:
                        # Legacy format: themes.AI.list -> ["AAPL", "MSFT", ...]
                        import json
                        try:
                            ticker_list = json.loads(entry.value['value']) if isinstance(entry.value['value'], str) else entry.value['value']
                            self.cache['themes'][entry.name] = ticker_list
                        except (json.JSONDecodeError, TypeError):
                            logger.warning("Invalid themes list format for %s: %s", entry.name, entry.value)
                    else:
                        # New detailed format: themes.themes.ai -> full stock data
                        if 'themes_detailed' not in self.cache:
                            self.cache['themes_detailed'] = {}
                        self.cache['themes_detailed'][entry.key] = entry.value
                
                # Legacy compatibility loading
                elif entry.type in ('market_stock_list', 'mag7_stock_list', 'top_priority_stock_list',
                                'secondary_priority_stock_list', 'tertiary_priority_stock_list',
                                'sectors', 'industries'):
                    self.cache[entry.type] = entry.value
                elif entry.type == 'industry_top_stocks':
                    if 'stocks' in entry.value:
                        self.cache['industry_top_stocks'][entry.name] = entry.value['stocks']
                elif entry.type == 'stock_to_industry':
                    if 'industry' in entry.value:
                        self.cache['stock_to_industry'][entry.key] = entry.value['industry']
            
            # Build universe selections from loaded data
            self._build_universe_selections(stock_universe_entries)
            
            # Create sets for fast membership checks (legacy compatibility)
            self._market_stock_set = set(self.cache['market_stock_list'])
            self._mag7_stock_set = set(self.cache['mag7_stock_list'])
            self._top_priority_set = set(self.cache['top_priority_stock_list'])
            self._secondary_priority_set = set(self.cache['secondary_priority_stock_list'])
            self._tertiary_priority_set = set(self.cache['tertiary_priority_stock_list'])
            
            # Universe sets for fast checks
            self._universe_sets = {}
            for universe_key, universe_data in self.cache['universes'].items():
                self._universe_sets[universe_key] = set(universe_data['tickers'])
            
            logger.info("Cache loaded successfully:")
            logger.info("  - App settings: %d", len(self.cache['app_settings']))
            logger.info("  - Stock groups: %d categories", len(self.cache['stock_groups']))
            logger.info("  - Priority stocks: %d entries", len(self.cache.get('priority_stocks', {})))  
            logger.info("  - Universes: %d selections", len(self.cache['universes']))
            logger.info("  - Stock metadata: %d stocks", len(self.cache['stock_metadata']))
            logger.info("  - Legacy themes: %d", len(self.cache['themes']))


            return True
        
        except OperationalError as e:
            logger.error("Database connection error during cache load: %s", str(e))
            return False
        except SQLAlchemyError as e:
            logger.error("Database query error during cache load: %s", str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error loading cache from src.infrastructure.database: %s", str(e))
            return False

    def _build_universe_selections(self, stock_universe_entries):
        """Build universe selections for the modal from loaded stock groups."""
        try:
            # DEFAULT_UNIVERSE (~800 stocks): Balanced selection for broad market coverage
            default_tickers = set()
            
            # Start with top 500 market leaders (core base)
            if 'market_leaders_top_500' in stock_universe_entries:
                default_tickers.update(stock_universe_entries['market_leaders_top_500']['tickers'])
            
            # Add all mega cap stocks
            if 'market_cap_mega_cap' in stock_universe_entries:
                default_tickers.update(stock_universe_entries['market_cap_mega_cap']['tickers'])
            
            # Add all sector leaders (top 10 from each sector for good coverage)
            sector_prefixes = ['communication_services', 'consumer_discretionary', 'consumer_staples', 
                             'energy', 'financial_services', 'healthcare', 'industrials', 'materials', 
                             'real_estate', 'technology', 'utilities']
            
            for sector in sector_prefixes:
                sector_key = f"sector_leaders_top_10_{sector}"
                if sector_key in stock_universe_entries:
                    default_tickers.update(stock_universe_entries[sector_key]['tickers'])
            
            # Add key thematic stocks for modern market representation
            theme_keys = ['themes_ai', 'themes_cloud', 'themes_fintech', 'themes_cybersecurity', 'themes_semi']
            for theme_key in theme_keys:
                if theme_key in stock_universe_entries:
                    default_tickers.update(stock_universe_entries[theme_key]['tickers'])
            
            # Add FAANG+ tech giants
            if 'thematic_faang_plus' in stock_universe_entries:
                default_tickers.update(stock_universe_entries['thematic_faang_plus']['tickers'])
            
            # If we're still under 750, add mid-cap stocks for more diversity
            if len(default_tickers) < 750 and 'market_cap_mid_cap' in stock_universe_entries:
                mid_cap_stocks = stock_universe_entries['market_cap_mid_cap']['tickers']
                # Add top 200 mid-cap stocks not already included
                mid_cap_added = 0
                for ticker in mid_cap_stocks:
                    if ticker not in default_tickers:
                        default_tickers.add(ticker)
                        mid_cap_added += 1
                        if len(default_tickers) >= 800 or mid_cap_added >= 200:
                            break
            
            # If still under target, add some industry leaders
            if len(default_tickers) < 800:
                industry_keys = ['industry_software', 'industry_pharmaceuticals', 'industry_banks']
                for industry_key in industry_keys:
                    if industry_key in stock_universe_entries and len(default_tickers) < 800:
                        industry_stocks = stock_universe_entries[industry_key]['tickers']
                        # Add top 20 from each industry
                        industry_added = 0
                        for ticker in industry_stocks:
                            if ticker not in default_tickers:
                                default_tickers.add(ticker)
                                industry_added += 1
                                if len(default_tickers) >= 800 or industry_added >= 20:
                                    break
            
            # Convert to list and limit to target size
            default_list = list(default_tickers)[:800]  # Cap at 800
            
            self.cache['universes']['DEFAULT_UNIVERSE'] = {
                'tickers': default_list,
                'count': len(default_list),
                'metadata': {
                    'criteria': 'Default universe: Top market leaders + sector representation + key themes',
                    'description': 'Balanced selection of ~800 stocks for general market coverage'
                }
            }
            
            # MARKET_CAP_LARGE_UNIVERSE: Mega + Large Cap
            large_cap_tickers = set()
            if 'market_cap_mega_cap' in stock_universe_entries:
                large_cap_tickers.update(stock_universe_entries['market_cap_mega_cap']['tickers'])
            if 'market_cap_large_cap' in stock_universe_entries:
                large_cap_tickers.update(stock_universe_entries['market_cap_large_cap']['tickers'])
            
            large_cap_list = list(large_cap_tickers)
            self.cache['universes']['MARKET_CAP_LARGE_UNIVERSE'] = {
                'tickers': large_cap_list,
                'count': len(large_cap_list),
                'metadata': {
                    'criteria': 'Large cap universe: Mega cap + Large cap stocks',
                    'description': f'Combined mega and large cap stocks ({len(large_cap_list)} total)'
                }
            }
            
            # MARKET_CAP_MID_UNIVERSE: Mid + Small Cap  
            mid_cap_tickers = set()
            if 'market_cap_mid_cap' in stock_universe_entries:
                mid_cap_tickers.update(stock_universe_entries['market_cap_mid_cap']['tickers'])
            if 'market_cap_small_cap' in stock_universe_entries:
                mid_cap_tickers.update(stock_universe_entries['market_cap_small_cap']['tickers'])
                
            mid_cap_list = list(mid_cap_tickers)
            self.cache['universes']['MARKET_CAP_MID_UNIVERSE'] = {
                'tickers': mid_cap_list,
                'count': len(mid_cap_list),
                'metadata': {
                    'criteria': 'Mid cap universe: Mid cap + Small cap stocks',
                    'description': f'Combined mid and small cap stocks ({len(mid_cap_list)} total)'
                }
            }
            
            # LEADER_UNIVERSE: All sector leaders + market leaders
            leader_tickers = set()
            
            # Add all sector leaders (top 10 from each sector)
            for sector in sector_prefixes:
                sector_key = f"sector_leaders_top_10_{sector}"
                if sector_key in stock_universe_entries:
                    leader_tickers.update(stock_universe_entries[sector_key]['tickers'])
            
            # Add top 500 market leaders
            if 'market_leaders_top_500' in stock_universe_entries:
                leader_tickers.update(stock_universe_entries['market_leaders_top_500']['tickers'])
                
            # Add FAANG+ 
            if 'thematic_faang_plus' in stock_universe_entries:
                leader_tickers.update(stock_universe_entries['thematic_faang_plus']['tickers'])
            
            leader_list = list(leader_tickers)
            self.cache['universes']['LEADER_UNIVERSE'] = {
                'tickers': leader_list,
                'count': len(leader_list),
                'metadata': {
                    'criteria': 'Leader universe: Top performers from all sectors + market leaders',
                    'description': f'Best performing stocks across all sectors ({len(leader_list)} total)'
                }
            }
            
            # Store universe metadata for quick access
            for universe_key, universe_data in self.cache['universes'].items():
                self.cache['universe_metadata'][universe_key] = {
                    'count': universe_data['count'],
                    'criteria': universe_data['metadata']['criteria'],
                    'description': universe_data['metadata']['description']
                }
            
            logger.info("Built universe selections:")
            for universe_key, universe_data in self.cache['universes'].items():
                logger.info(f"  - {universe_key}: {universe_data['count']} stocks")
                
        except Exception as e:
            logger.error("Error building universe selections: %s", str(e))

    '''
    def configure_flask_app(self, app):
        """Apply environment-specific settings to a Flask application."""
        app_settings = self.get_cache('app_settings') or {}
        
        # Apply settings from cache to Flask app
        for key, value in app_settings.items():
            app.config[key] = value
        
        logger.info(f"Applied {len(app_settings)} settings to Flask app from cache")
        return app
    '''

    def get_cache(self, key: str) -> Optional[Any]:
        """Retrieve data from cache by key."""
        if key not in self.cache:
            logger.warning("Cache key not found: %s", key)
            return None
        return self.cache[key]
    
    def get_universe_tickers(self, universe_key: str) -> List[str]:
        """Get ticker list for a specific universe."""
        universes = self.cache.get('universes', {})
        if universe_key not in universes:
            logger.warning("Universe not found: %s", universe_key)
            return []
        return universes[universe_key]['tickers']
    
    def get_universe_metadata(self, universe_key: str) -> Dict[str, Any]:
        """Get metadata for a specific universe."""
        return self.cache.get('universe_metadata', {}).get(universe_key, {})
    
    def get_available_universes(self) -> Dict[str, Dict[str, Any]]:
        """Get all available universes with their metadata for selection modal."""
        return self.cache.get('universe_metadata', {})
    
    def get_stock_metadata(self, ticker: str) -> Dict[str, Any]:
        """Get metadata for a specific stock."""
        return self.cache.get('stock_metadata', {}).get(ticker, {})
    

    # Add these methods to the CacheControl class in cache_control.py

    def get_priority_stocks(self, priority_level: str = None) -> Dict[str, Any]:
        """
        Get priority stocks for processing prioritization.
        
        Args:
            priority_level: Optional - 'TOP', 'SECONDARY', or None for all
            
        Returns:
            Dict containing priority stock information
        """
        if not self._initialized:
            logger.warning("CacheControl not initialized; cannot retrieve priority stocks")
            return {}
        
        stock_groups = self.cache.get('stock_groups', {})
        priority_data = stock_groups.get('priority_stocks', {})
        
        if not priority_data:
            # Try direct lookup if not in stock_groups
            priority_data = self.cache.get('priority_stocks', {})
        
        if priority_level:
            priority_level = priority_level.upper()
            if priority_level == 'TOP':
                return priority_data.get('top_priority', {})
            elif priority_level == 'SECONDARY':
                return priority_data.get('secondary_priority', {})
        
        # Return all priority data
        return priority_data.get('priority_list', {})
    
    def get_priority_tickers(self, priority_level: str = None) -> List[str]:
        """
        Get list of priority stock tickers for quick access.
        
        Args:
            priority_level: Optional - 'TOP', 'SECONDARY', or None for all
            
        Returns:
            List of ticker symbols
        """
        priority_data = self.get_priority_stocks(priority_level)
        
        # Handle different data structures
        if 'tickers' in priority_data:
            return priority_data['tickers']
        elif 'stocks' in priority_data:
            return [stock['ticker'] for stock in priority_data['stocks']]
        else:
            return []
    
    def is_priority_stock(self, ticker: str) -> Dict[str, Any]:
        """
        Check if a stock is in priority list and return its priority info.
        
        Args:
            ticker: Stock symbol to check
            
        Returns:
            Dict with priority information or empty dict if not priority
        """
        all_priority = self.get_priority_stocks()
        
        if 'stocks' in all_priority:
            for stock in all_priority['stocks']:
                if stock['ticker'] == ticker:
                    return {
                        'is_priority': True,
                        'priority_level': stock.get('priority_level', 'UNKNOWN'),
                        'priority_score': stock.get('priority_score', 0),
                        'rank': stock.get('rank', 999)
                    }
        
        return {'is_priority': False}
    
    '''
    def get_priority_stocks_by_score(self, min_score: int = 0) -> List[Dict[str, Any]]:
        """
        Get priority stocks filtered by minimum score.
        
        Args:
            min_score: Minimum priority score (0-100)
            
        Returns:
            List of stocks meeting score threshold, sorted by score
        """
        all_priority = self.get_priority_stocks()
        
        if 'stocks' not in all_priority:
            return []
        
        filtered = [
            stock for stock in all_priority['stocks']
            if stock.get('priority_score', 0) >= min_score
        ]
        
        # Sort by priority score descending
        return sorted(filtered, key=lambda x: x.get('priority_score', 0), reverse=True)
    '''
    def get_processing_priority_set(self) -> Set[str]:
        """
        Get a set of all priority tickers for fast membership checking.
        Optimized for processing loops.
        
        Returns:
            Set of priority ticker symbols
        """
        if not hasattr(self, '_priority_stock_set'):
            self._priority_stock_set = set(self.get_priority_tickers())
        
        return self._priority_stock_set
    
    def should_prioritize_processing(self, ticker: str, throttle_level: int = 0) -> bool:
        """
        Determine if a stock should be prioritized during processing based on throttle level.
        
        Args:
            ticker: Stock symbol to check
            throttle_level: Current throttling level (0=none, 1=mild, 2=moderate, 3=severe)
            
        Returns:
            bool: True if stock should be processed, False if it should be skipped
        """
        priority_info = self.is_priority_stock(ticker)
        
        if not priority_info['is_priority']:
            # Non-priority stocks get increasingly filtered as throttle increases
            if throttle_level >= 3:
                return False  # Severe: Only priority stocks
            elif throttle_level >= 2:
                return False  # Moderate: Only priority stocks
            elif throttle_level >= 1:
                # Mild: Allow some non-priority (random sampling, etc.)
                return hash(ticker) % 3 == 0  # Process ~33% of non-priority
            else:
                return True  # No throttle: Process all
        
        # Priority stocks always processed unless extreme throttling
        if priority_info['priority_level'] == 'TOP':
            return True  # Always process top priority
        elif priority_info['priority_level'] == 'SECONDARY':
            return throttle_level < 3  # Skip secondary only at severe throttle
        else:
            return throttle_level < 2  # Unknown priority: skip at moderate+
    
    def get_priority_stats(self) -> Dict[str, Any]:
        """
        Get statistics about priority stocks in cache.
        
        Returns:
            Dict with priority stock statistics
        """
        all_priority = self.get_priority_stocks()
        top_priority = self.get_priority_stocks('TOP')
        secondary_priority = self.get_priority_stocks('SECONDARY')
        
        return {
            'total_priority_stocks': all_priority.get('count', 0),
            'top_priority_count': top_priority.get('count', 0) if top_priority else all_priority.get('top_priority_count', 0),
            'secondary_priority_count': secondary_priority.get('count', 0) if secondary_priority else all_priority.get('secondary_priority_count', 0),
            'has_priority_data': bool(all_priority),
            'last_updated': all_priority.get('last_updated', 'Unknown')
        }



    def is_stock_in_universe(self, ticker: str, universe_key: str) -> bool:
        """Check if stock is in a specific universe (fast lookup)."""
        return ticker in self._universe_sets.get(universe_key, set())
    
    def get_default_universe(self) -> List[str]:
        """Get the default universe ticker list."""
        return self.get_universe_tickers('DEFAULT_UNIVERSE')
    
    # Legacy compatibility methods
    '''
    def is_stock_priority(self, ticker: str) -> bool:
        """Check if a stock is in any priority list (Top, Secondary, Tertiary)."""
        return (
            ticker in self._top_priority_set or
            ticker in self._secondary_priority_set or
            ticker in self._tertiary_priority_set
        )
    def is_stock_top_priority(self, ticker: str) -> bool:
        """Check if a stock is in top priority list."""
        return ticker in self._top_priority_set
    
    def is_stock_second_priority(self, ticker: str) -> bool:
        """Check if a stock is in secondary priority list."""
        return ticker in self._secondary_priority_set

    def get_stocks_by_theme(self, theme: str) -> List[str]:
        """Retrieve stocks associated with a given theme."""
        themes = self.cache.get('themes', {})
        stocks = themes.get(theme, [])
        return stocks
    
    def get_industry_for_stock(self, ticker: str) -> Optional[str]:
        """Retrieve the industry for a given stock ticker."""
        industry = self.cache.get('stock_to_industry', {}).get(ticker)
        return industry
    '''
    
    def reset_cache(self):
        """Reset and reload the cache with fresh data."""
        with self._lock:
            self.cache.clear()
            self.load_settings_from_db(environment=self.environment or 'DEFAULT')
            logger.info("Cache reset and reloaded with %d sections", len(self.cache))
    
    def get_stock_universe_value(self, name: str, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the full raw value dict for a specific stock_universe entry from the cache.
        
        This corresponds to the database entry where type='stock_universe', using the provided
        name and key. Returns the entire value (e.g., {'count': int, 'stocks': list, 'criteria': str, 
        'last_updated': str}) or None if not found.
        
        Args:
            name (str): The group name (e.g., 'market_leaders').
            key (str): The subgroup key (e.g., 'top_50').
        
        Returns:
            Optional[Dict[str, Any]]: The value dict if found, else None.
        """
        if not self._initialized:
            logger.warning("CacheControl not initialized; cannot retrieve stock_universe value for %s/%s", name, key)
            return None
        
        stock_groups = self.cache.get('stock_groups')
        if stock_groups is None:
            logger.warning("stock_groups section not found in cache")
            return None
        
        if name not in stock_groups:
            logger.warning("Stock group '%s' not found in cache", name)
            return None
        
        if key not in stock_groups[name]:
            logger.warning("Key '%s' not found in stock group '%s'", key, name)
            return None
        
        value = stock_groups[name][key]
        logger.info("Retrieved stock_universe value for %s/%s with count=%d", name, key, value.get('count', 0))
        return value

    def get_cache_contents(self) -> Dict[str, Any]:
        """Return a copy of the entire cache for debugging."""
        return self.cache.copy()
    
    def log_universe_membership(self, ticker: str, user_universes: List[str]) -> Dict[str, Any]:
        """
        Check universe membership and return detailed information for logging.
        
        Args:
            ticker: Stock symbol to check
            user_universes: List of universe keys the user has selected
            
        Returns:
            dict: Detailed membership information for logging
        """
        method_logger = logging.getLogger(f"{__name__}.get_user_membership_info")
        
        membership_info = {
            'ticker': ticker,
            'user_universes': user_universes,
            'membership_results': {},
            'is_in_any_user_universe': False,
            'universe_matches': []
        }
        
        for universe_key in user_universes:
            is_member = self.is_stock_in_universe(ticker, universe_key)
            membership_info['membership_results'][universe_key] = is_member
            
            if is_member:
                membership_info['is_in_any_user_universe'] = True
                membership_info['universe_matches'].append(universe_key)
        
        # Log the check if debug enabled
        if len(user_universes) > 0:
            status = "IN_UNIVERSE" if membership_info['is_in_any_user_universe'] else "FILTERED_OUT"
            if status == "FILTERED_OUT":
                matches = ", ".join(membership_info['universe_matches']) if membership_info['universe_matches'] else "none"
        
        return membership_info
    
    '''
    def get_universe_coverage_stats(self, subscribed_tickers: List[str], user_universes: List[str]) -> Dict[str, Any]:
        """
        Calculate coverage statistics between subscribed tickers and user universe selections.
        
        Args:
            subscribed_tickers: List of tickers we're subscribed to receive data for
            user_universes: List of universe keys the user has selected
            
        Returns:
            dict: Coverage statistics for logging
        """
        method_logger = logging.getLogger(f"{__name__}.get_user_filtered_tickers")
        
        # Get all tickers from user's selected universes
        universe_tickers = set()
        universe_breakdown = {}
        
        for universe_key in user_universes:
            tickers = set(self.get_universe_tickers(universe_key))
            universe_tickers.update(tickers)
            universe_breakdown[universe_key] = {
                'count': len(tickers),
                'tickers': list(tickers)
            }
        
        subscribed_set = set(subscribed_tickers)
        
        # Calculate overlaps
        overlap_tickers = subscribed_set.intersection(universe_tickers)
        subscribed_not_in_universe = subscribed_set - universe_tickers
        universe_not_subscribed = universe_tickers - subscribed_set
        
        coverage_stats = {
            'subscribed_count': len(subscribed_tickers),
            'universe_count': len(universe_tickers),
            'overlap_count': len(overlap_tickers),
            'subscribed_not_in_universe_count': len(subscribed_not_in_universe),
            'universe_not_subscribed_count': len(universe_not_subscribed),
            'coverage_percentage': round((len(overlap_tickers) / len(universe_tickers)) * 100, 1) if universe_tickers else 0,
            'subscription_efficiency': round((len(overlap_tickers) / len(subscribed_tickers)) * 100, 1) if subscribed_tickers else 0,
            'user_universes': user_universes,
            'universe_breakdown': universe_breakdown
        }
        
        method_logger.info(f"Universe coverage stats: {coverage_stats['overlap_count']} overlapping stocks, "
                   f"{coverage_stats['coverage_percentage']}% universe coverage, "
                   f"{coverage_stats['subscription_efficiency']}% subscription efficiency")
        
        return coverage_stats
    '''
    '''
    def get_user_universe_summary(self, user_universes: List[str]) -> Dict[str, Any]:
        """
        Get summary information about user's selected universes.
        
        Args:
            user_universes: List of universe keys the user has selected
            
        Returns:
            dict: Summary information for logging
        """
        method_logger = logging.getLogger(f"{__name__}.get_all_filtered_tickers")
        
        all_tickers = set()
        universe_details = {}
        
        for universe_key in user_universes:
            try:
                tickers = self.get_universe_tickers(universe_key)
                metadata = self.get_universe_metadata(universe_key)
                
                all_tickers.update(tickers)
                universe_details[universe_key] = {
                    'count': len(tickers),
                    'description': metadata.get('description', ''),
                    'criteria': metadata.get('criteria', '')
                }
                
            except Exception as e:
                method_logger.warning(f"Error getting details for universe {universe_key}: {e}")
                universe_details[universe_key] = {
                    'count': 0,
                    'description': 'Error loading universe',
                    'criteria': '',
                    'error': str(e)
                }
        
        summary = {
            'universes_selected': user_universes,
            'total_unique_tickers': len(all_tickers),
            'universe_details': universe_details,
            'overlap_analysis': self._analyze_universe_overlaps(user_universes) if len(user_universes) > 1 else {}
        }
        
        
        return summary
    '''
    def _analyze_universe_overlaps(self, user_universes: List[str]) -> Dict[str, Any]:
        """
        Analyze overlaps between multiple selected universes.
        
        Args:
            user_universes: List of universe keys
            
        Returns:
            dict: Overlap analysis
        """
        if len(user_universes) < 2:
            return {}
        
        universe_sets = {}
        for universe_key in user_universes:
            universe_sets[universe_key] = set(self.get_universe_tickers(universe_key))
        
        # Calculate pairwise overlaps
        overlaps = {}
        for i, universe1 in enumerate(user_universes):
            for universe2 in user_universes[i+1:]:
                overlap_count = len(universe_sets[universe1].intersection(universe_sets[universe2]))
                overlap_key = f"{universe1}_vs_{universe2}"
                overlaps[overlap_key] = {
                    'overlap_count': overlap_count,
                    'universe1_size': len(universe_sets[universe1]),
                    'universe2_size': len(universe_sets[universe2]),
                    'overlap_percentage': round((overlap_count / min(len(universe_sets[universe1]), len(universe_sets[universe2]))) * 100, 1)
                }
        
        return {
            'pairwise_overlaps': overlaps,
            'total_universes': len(user_universes)
        }
    
    def warm_core_universe_cache(self):
        """
        Warm the core universe cache by building and caching the TickStock Core Universe.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from src.core.services.universe_service import TickStockUniverseManager
            
            logger.info("Warming TickStock Core Universe cache...")
            start_time = time.time()
            
            # Create universe manager and build core universe
            universe_manager = TickStockUniverseManager(self)
            
            if universe_manager.build_core_universe():
                # Cache the core universe data
                core_universe_data = {
                    'tickers': universe_manager.get_core_universe(),
                    'metadata': universe_manager.get_universe_metadata(),
                    'build_timestamp': universe_manager.build_timestamp,
                    'criteria': universe_manager.build_criteria,
                    'universe_size': universe_manager.get_universe_size()
                }
                
                # Store in cache
                if 'core_universe' not in self.cache:
                    self.cache['core_universe'] = {}
                
                self.cache['core_universe']['tickstock_core'] = core_universe_data
                
                # Create fast lookup set
                if not hasattr(self, '_core_universe_sets'):
                    self._core_universe_sets = {}
                self._core_universe_sets['tickstock_core'] = universe_manager.core_universe_set
                
                elapsed_time = time.time() - start_time
                logger.info(f"Core universe cache warmed successfully: {core_universe_data['universe_size']} stocks in {elapsed_time:.2f}s")
                
                return True
            else:
                logger.error("Failed to build core universe during cache warming")
                return False
                
        except Exception as e:
            logger.error(f"Error warming core universe cache: {e}", exc_info=True)
            return False

    def get_core_universe_tickers(self, universe_key: str = 'tickstock_core') -> List[str]:
        """
        Get ticker list for the TickStock Core Universe.
        
        Args:
            universe_key: Core universe key (default: 'tickstock_core')
            
        Returns:
            List[str]: List of ticker symbols in core universe
        """
        try:
            core_universe_data = self.cache.get('core_universe', {})
            if universe_key not in core_universe_data:
                logger.warning(f"Core universe '{universe_key}' not found in cache, attempting to warm cache")
                if self.warm_core_universe_cache():
                    core_universe_data = self.cache.get('core_universe', {})
                    logger.warning(f"Core universe cache warmed successfully for key '{universe_key}'")
                else:
                    logger.error("Failed to warm core universe cache!!")
                    return []
            
            return core_universe_data[universe_key].get('tickers', [])
            
        except Exception as e:
            logger.error(f"Error getting core universe tickers: {e}", exc_info=True)
            return []

    def is_stock_in_core_universe(self, ticker: str, universe_key: str = 'tickstock_core') -> bool:
        """
        Fast membership check for TickStock Core Universe.
        Optimized for <1ms performance using set lookup.
        
        Args:
            ticker: Stock symbol to check
            universe_key: Core universe key (default: 'tickstock_core')
            
        Returns:
            bool: True if ticker is in core universe, False otherwise
        """
        try:
            # Ensure we have the fast lookup sets
            if not hasattr(self, '_core_universe_sets'):
                self._core_universe_sets = {}
            
            # Build set if not exists
            if universe_key not in self._core_universe_sets:
                core_tickers = self.get_core_universe_tickers(universe_key)
                if core_tickers:
                    self._core_universe_sets[universe_key] = set(core_tickers)
                else:
                    logger.warning(f"Could not build lookup set for core universe '{universe_key}'")
                    return False
            
            return ticker in self._core_universe_sets[universe_key]
            
        except Exception as e:
            logger.error(f"Error checking core universe membership for {ticker}: {e}")
            return False
    '''
    def get_core_universe_metadata(self, universe_key: str = 'tickstock_core') -> Dict[str, Any]:
        """
        Get metadata for the TickStock Core Universe.
        
        Args:
            universe_key: Core universe key (default: 'tickstock_core')
            
        Returns:
            Dict[str, Any]: Core universe metadata
        """
        try:
            core_universe_data = self.cache.get('core_universe', {})
            if universe_key in core_universe_data:
                return core_universe_data[universe_key].get('metadata', {})
            else:
                logger.warning(f"Core universe '{universe_key}' not found in cache")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting core universe metadata: {e}", exc_info=True)
            return {}
    '''

    def refresh_core_universe_cache(self) -> bool:
        """
        Refresh the core universe cache with latest data.
        
        Returns:
            bool: True if refresh successful, False otherwise
        """
        try:
            logger.info("Refreshing core universe cache...")
            
            # Clear existing core universe cache
            if 'core_universe' in self.cache:
                del self.cache['core_universe']
            
            if hasattr(self, '_core_universe_sets'):
                self._core_universe_sets.clear()
            
            # Rebuild core universe cache
            return self.warm_core_universe_cache()
            
        except Exception as e:
            logger.error(f"Error refreshing core universe cache: {e}", exc_info=True)
            return False

    def get_core_universe_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cached core universe.
        
        Returns:
            Dict[str, Any]: Core universe statistics
        """
        try:
            stats = {
                'core_universes_cached': 0,
                'total_core_stocks': 0,
                'cache_age_hours': None,
                'available_universes': [],
                'cache_memory_sets': 0
            }
            
            core_universe_data = self.cache.get('core_universe', {})
            stats['core_universes_cached'] = len(core_universe_data)
            stats['available_universes'] = list(core_universe_data.keys())
            
            # Get total stocks across all core universes
            for universe_key, universe_data in core_universe_data.items():
                stats['total_core_stocks'] += universe_data.get('universe_size', 0)
            
            # Get cache age for primary universe
            if 'tickstock_core' in core_universe_data:
                build_timestamp = core_universe_data['tickstock_core'].get('build_timestamp')
                if build_timestamp:
                    age_seconds = time.time() - build_timestamp
                    stats['cache_age_hours'] = round(age_seconds / 3600, 2)
            
            # Count memory sets
            if hasattr(self, '_core_universe_sets'):
                stats['cache_memory_sets'] = len(self._core_universe_sets)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting core universe stats: {e}", exc_info=True)
            return {}

    # Update the initialize method to warm core universe cache
    '''
    def initialize_with_core_universe(self, environment: str = 'DEFAULT'):
        """
        Enhanced initialize method that includes core universe cache warming.
        
        Args:
            environment: Environment to load cache for
        """
        # Call original initialize method
        self.initialize(environment)
        
        if self._initialized:
            # Warm the core universe cache
            logger.info("Warming core universe cache during initialization...")
            if self.warm_core_universe_cache():
                logger.info("Core universe cache warmed successfully during initialization")
            else:
                logger.warning("Failed to warm core universe cache during initialization")
    '''