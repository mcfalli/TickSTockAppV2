import json
import logging
from threading import Lock
from typing import Any
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)

class CacheControl:
    """
    Singleton class to manage cached application settings and themes.

    NOTE: As of Sprint 61, stock/ETF/universe loading has migrated to RelationshipCache.
    This class now handles:
    - app_settings (application configuration)
    - cache_config (cache configuration)
    - themes (custom stock groupings)

    For stock universes, ETF holdings, and sectors, use:
        from src.core.services.relationship_cache import get_relationship_cache
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols('nasdaq100')

    Legacy support for cache_entries table will be maintained for non-stock data types.
    """

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
            self.cache: dict[str, Any] = {}
            self.environment = 'DEFAULT'

    def initialize(self, environment: str = 'DEFAULT'):
        """Initialize cache with database data if not already initialized."""

        if self._initialized:
            logger.info("CacheControl already initialized for environment: %s", self.environment)
            return

        self.environment = environment

        try:
            if self.load_settings_from_db():
                logger.info("CacheControl initialized with %d cache sections", len(self.cache))
            else:
                logger.error("Database load failed")
                raise RuntimeError("Failed to load cache from database")
        except Exception as e:
            logger.error("Error initializing cache: %s", str(e))
            raise RuntimeError("Cache initialization failed") from e

        self._initialized = True

    def load_settings_from_db(self) -> bool:
        """
        Load cache data from the cache_entries table.
        
        Returns:
            bool: True if loading succeeded, False otherwise.
        """
        try:
            # Get database connection using config manager
            config = get_config()
            database_url = config.get('DATABASE_URI')
            if not database_url:
                raise ValueError("DATABASE_URI not found in configuration")

            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path.lstrip('/'),
                user=parsed.username,
                password=parsed.password
            )

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT type, name, key, value, created_at, updated_at
                    FROM cache_entries
                    ORDER BY type, name, key
                """)

                entries = cursor.fetchall()

            conn.close()

            if not entries:
                logger.error("No cache entries found in database")
                return False

            # Initialize cache structure
            self.cache = {
                'app_settings': {},
                'cache_config': {},
                'stock_universes': {},
                'etf_universes': {},
                'stock_etf_combos': {},  # Combined stock+ETF universes
                'themes': {},
                'stock_stats': {},
                'universes': {},  # Built universes for dropdowns
                'universe_metadata': {}  # Universe metadata for dropdowns
            }

            # Process database rows
            for entry in entries:
                entry_type = entry['type']
                entry_name = entry['name']
                entry_key = entry['key']
                entry_value = entry['value']

                if entry_type == 'app_settings':
                    # Skip database URI settings - these come from environment
                    if entry_key in ('SQLALCHEMY_DATABASE_URI', 'DATABASE_URI'):
                        continue

                    # Handle different value formats
                    if isinstance(entry_value, dict) and 'value' in entry_value:
                        self.cache['app_settings'][entry_key] = entry_value['value']
                    else:
                        self.cache['app_settings'][entry_key] = entry_value

                elif entry_type == 'cache_config':
                    # Load cache configuration (protected from deletion)
                    if entry_name not in self.cache['cache_config']:
                        self.cache['cache_config'][entry_name] = {}
                    self.cache['cache_config'][entry_name][entry_key] = entry_value

                elif entry_type == 'stock_universe':
                    # Load stock universe entries
                    if entry_name not in self.cache['stock_universes']:
                        self.cache['stock_universes'][entry_name] = {}
                    self.cache['stock_universes'][entry_name][entry_key] = entry_value

                elif entry_type == 'etf_universe':
                    # Load ETF universe entries
                    if entry_name not in self.cache['etf_universes']:
                        self.cache['etf_universes'][entry_name] = {}
                    self.cache['etf_universes'][entry_name][entry_key] = entry_value

                elif entry_type == 'stock_etf_combo':
                    # Load combined stock+ETF universe entries
                    if entry_name not in self.cache['stock_etf_combos']:
                        self.cache['stock_etf_combos'][entry_name] = {}
                    self.cache['stock_etf_combos'][entry_name][entry_key] = entry_value

                elif entry_type == 'themes':
                    # Load theme entries (simple ticker arrays)
                    if entry_key == 'list':
                        # Parse JSON value
                        try:
                            if isinstance(entry_value, str):
                                ticker_list = json.loads(entry_value)
                            elif isinstance(entry_value, dict) and 'value' in entry_value:
                                ticker_list = json.loads(entry_value['value']) if isinstance(entry_value['value'], str) else entry_value['value']
                            else:
                                ticker_list = entry_value
                            self.cache['themes'][entry_name] = ticker_list
                        except (json.JSONDecodeError, TypeError):
                            logger.warning("Invalid themes format for %s: %s", entry_name, entry_value)

                elif entry_type == 'stock_stats':
                    # Load stock statistics
                    if 'stock_stats' not in self.cache:
                        self.cache['stock_stats'] = {}
                    if entry_name not in self.cache['stock_stats']:
                        self.cache['stock_stats'][entry_name] = {}
                    self.cache['stock_stats'][entry_name][entry_key] = entry_value

            # Build universe selections for dropdowns from loaded data
            self._build_universe_selections()

            logger.info("Cache loaded successfully:")
            logger.info("  - App settings: %d", len(self.cache['app_settings']))
            logger.info("  - Cache config: %d categories", len(self.cache['cache_config']))
            logger.info("  - Stock universes: %d categories", len(self.cache['stock_universes']))
            logger.info("  - ETF universes: %d categories", len(self.cache['etf_universes']))
            logger.info("  - Stock+ETF combos: %d categories", len(self.cache['stock_etf_combos']))
            logger.info("  - Themes: %d", len(self.cache['themes']))
            logger.info("  - Built universes: %d selections", len(self.cache['universes']))

            return True

        except Exception as e:
            logger.error("Error loading cache from database: %s", str(e))
            return False

    def _build_universe_selections(self):
        """Build universe selections for dropdowns from loaded cache data."""
        try:
            universes_built = 0

            # Build universes from stock_universe entries
            for category_name, category_data in self.cache['stock_universes'].items():
                for universe_key, universe_data in category_data.items():
                    # Create universe key (use colon format to match config convention)
                    full_key = f"{category_name}:{universe_key}"

                    # Extract tickers based on data format
                    tickers = []
                    if isinstance(universe_data, dict):
                        if 'stocks' in universe_data:
                            # Full stock data format
                            tickers = [stock['ticker'] for stock in universe_data['stocks']]
                        elif isinstance(universe_data, list):
                            # Simple ticker array
                            tickers = universe_data
                        count = universe_data.get('count', len(tickers))
                        description = f"{category_name.title()} {universe_key.replace('_', ' ').title()}"
                    else:
                        # Handle other formats
                        continue

                    if tickers:
                        self.cache['universes'][full_key] = {
                            'tickers': tickers,
                            'count': count,
                            'metadata': {
                                'criteria': f"{category_name} - {universe_key}",
                                'description': description
                            }
                        }

                        # Store metadata separately for quick access
                        self.cache['universe_metadata'][full_key] = {
                            'count': count,
                            'criteria': f"{category_name} - {universe_key}",
                            'description': description
                        }

                        universes_built += 1

            # Build universes from ETF entries (simple ticker arrays)
            for category_name, category_data in self.cache['etf_universes'].items():
                for universe_key, etf_list in category_data.items():
                    full_key = f"etf_{universe_key}"

                    if isinstance(etf_list, list):
                        self.cache['universes'][full_key] = {
                            'tickers': etf_list,
                            'count': len(etf_list),
                            'metadata': {
                                'criteria': f"ETF - {category_name}",
                                'description': f"{category_name} ETFs"
                            }
                        }

                        self.cache['universe_metadata'][full_key] = {
                            'count': len(etf_list),
                            'criteria': f"ETF - {category_name}",
                            'description': f"{category_name} ETFs"
                        }

                        universes_built += 1

            # Build universes from stock+ETF combo entries
            for category_name, category_data in self.cache['stock_etf_combos'].items():
                for universe_key, combo_data in category_data.items():
                    # Create universe key in format 'name:key'
                    full_key = f"{category_name}:{universe_key}"

                    # Extract tickers based on data format (similar to stock_universe processing)
                    tickers = []
                    if isinstance(combo_data, dict):
                        if 'stocks' in combo_data:
                            # Full stock data format with stocks array
                            tickers = [stock['ticker'] for stock in combo_data['stocks'] if isinstance(stock, dict) and 'ticker' in stock]
                        elif 'symbols' in combo_data:
                            # Alternative format with symbols array (mixed stocks/ETFs)
                            symbols = combo_data['symbols']
                            tickers = [symbol['ticker'] if isinstance(symbol, dict) else symbol
                                      for symbol in symbols
                                      if (isinstance(symbol, dict) and 'ticker' in symbol) or isinstance(symbol, str)]
                        elif isinstance(combo_data, list):
                            # Simple ticker array format (mixed stocks/ETFs)
                            tickers = combo_data
                        count = combo_data.get('count', len(tickers))
                        description = f"{category_name.title()} {universe_key.replace('_', ' ').title()}"
                    elif isinstance(combo_data, list):
                        # Simple ticker array format
                        tickers = combo_data
                        count = len(tickers)
                        description = f"{category_name.title()} {universe_key.replace('_', ' ').title()}"
                    else:
                        # Handle other formats
                        continue

                    if tickers:
                        self.cache['universes'][full_key] = {
                            'tickers': tickers,
                            'count': count,
                            'metadata': {
                                'criteria': f"{category_name} - {universe_key}",
                                'description': description
                            }
                        }

                        # Store metadata separately for quick access
                        self.cache['universe_metadata'][full_key] = {
                            'count': count,
                            'criteria': f"{category_name} - {universe_key}",
                            'description': description
                        }

                        universes_built += 1

            # Add theme-based universes
            for theme_name, ticker_list in self.cache['themes'].items():
                if isinstance(ticker_list, list) and ticker_list:
                    full_key = f"theme_{theme_name}"

                    self.cache['universes'][full_key] = {
                        'tickers': ticker_list,
                        'count': len(ticker_list),
                        'metadata': {
                            'criteria': f"Theme - {theme_name}",
                            'description': f"{theme_name.title()} Theme Stocks"
                        }
                    }

                    self.cache['universe_metadata'][full_key] = {
                        'count': len(ticker_list),
                        'criteria': f"Theme - {theme_name}",
                        'description': f"{theme_name.title()} Theme Stocks"
                    }

                    universes_built += 1

            logger.info(f"Built {universes_built} universe selections from cache data")

        except Exception as e:
            logger.error("Error building universe selections: %s", str(e))

    def get_cache(self, key: str) -> Any | None:
        """Retrieve data from cache by key."""
        if not self._initialized:
            logger.warning("CacheControl not initialized, cannot get cache key: %s", key)
            return None

        if key not in self.cache:
            logger.warning("Cache key not found: %s", key)
            return None
        return self.cache[key]

    def get_cache_contents(self) -> dict[str, Any]:
        """Return a copy of the entire cache for debugging."""
        if not self._initialized:
            return {}
        return self.cache.copy()

    def get_available_universes(self) -> dict[str, dict[str, Any]]:
        """Get all available universes with their metadata for selection dropdowns."""
        if not self._initialized:
            logger.warning("CacheControl not initialized, cannot get universes")
            return {}
        return self.cache.get('universe_metadata', {})

    def get_universe_tickers(self, universe_key: str) -> list[str]:
        """
        Get ticker list for a specific universe.

        DEPRECATED (Sprint 61): This method is deprecated for stock/universe loading.
        Use RelationshipCache.get_universe_symbols() instead for:
        - Stock universes (NASDAQ-100, S&P 500, Dow 30, Russell 3000)
        - ETF holdings (SPY, QQQ, etc.)
        - Multi-universe joins (e.g., 'sp500:nasdaq100')

        Example migration:
            # Old (deprecated):
            from src.infrastructure.cache.cache_control import CacheControl
            cache = CacheControl()
            symbols = cache.get_universe_tickers('nasdaq100')

            # New (recommended):
            from src.core.services.relationship_cache import get_relationship_cache
            cache = get_relationship_cache()
            symbols = cache.get_universe_symbols('nasdaq100')

        This method now only supports legacy theme-based universes from cache_entries.
        """
        # Log deprecation warning
        logger.warning(
            f"DEPRECATED: CacheControl.get_universe_tickers('{universe_key}') is deprecated. "
            "Use RelationshipCache.get_universe_symbols() instead for stock/ETF/universe loading. "
            "See class docstring for migration instructions."
        )

        if not self._initialized:
            logger.warning("CacheControl not initialized, cannot get universe tickers")
            return []

        universes = self.cache.get('universes', {})
        if universe_key not in universes:
            logger.warning("Universe not found: %s", universe_key)
            return []
        return universes[universe_key].get('tickers', [])

    def get_universe_metadata(self, universe_key: str) -> dict[str, Any]:
        """Get metadata for a specific universe."""
        if not self._initialized:
            return {}
        return self.cache.get('universe_metadata', {}).get(universe_key, {})

    def reset_cache(self):
        """Reset and reload the cache with fresh data."""
        with self._lock:
            logger.info("Resetting cache...")
            self.cache.clear()
            self._initialized = False
            self.initialize(environment=self.environment)
            logger.info("Cache reset and reloaded with %d sections", len(self.cache))

    def get_stock_universe_value(self, name: str, key: str) -> dict[str, Any] | None:
        """
        Retrieve the full raw value dict for a specific stock_universe entry.
        
        Args:
            name (str): The group name (e.g., 'market_leaders').
            key (str): The subgroup key (e.g., 'top_50').
        
        Returns:
            Optional[Dict[str, Any]]: The value dict if found, else None.
        """
        if not self._initialized:
            logger.warning("CacheControl not initialized; cannot retrieve stock_universe value for %s/%s", name, key)
            return None

        stock_universes = self.cache.get('stock_universes', {})
        if name not in stock_universes:
            logger.warning("Stock universe group '%s' not found in cache", name)
            return None

        if key not in stock_universes[name]:
            logger.warning("Key '%s' not found in stock universe group '%s'", key, name)
            return None

        value = stock_universes[name][key]
        logger.info("Retrieved stock_universe value for %s/%s with count=%d", name, key, value.get('count', 0))
        return value
