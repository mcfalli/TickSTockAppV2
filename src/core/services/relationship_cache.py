"""
Relationship Cache - Sprint 60 Phase 2.1

In-memory cache for ETF-stock-sector-theme relationships with sub-millisecond access.
Replaces old cache_entries pattern with relational database backend.

Performance Targets:
- Cache hit: <1ms (in-memory lookup)
- Cache miss: <10ms (database query + cache population)
- Cache size: <50MB for 3,700 stocks + 24 ETFs + 20 themes

Usage:
    from src.core.services.relationship_cache import get_relationship_cache

    cache = get_relationship_cache()
    holdings = cache.get_etf_holdings('SPY')  # Returns list of symbols
    sectors = cache.get_stock_sector('AAPL')  # Returns sector dict
"""

import logging
import time
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from threading import Lock

import psycopg2
from urllib.parse import urlparse

from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)


class RelationshipCache:
    """
    In-memory cache for relationship data with TTL-based expiration
    """

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize cache

        Args:
            ttl_seconds: Time-to-live for cache entries (default: 1 hour)
        """
        self.ttl_seconds = ttl_seconds
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')
        self.environment = self.config.get('ENVIRONMENT', 'DEFAULT')

        # Cache storage
        self._etf_holdings: Dict[str, tuple[List[str], datetime]] = {}
        self._stock_etfs: Dict[str, tuple[List[str], datetime]] = {}
        self._stock_sector: Dict[str, tuple[Dict[str, str], datetime]] = {}
        self._sector_stocks: Dict[str, tuple[List[str], datetime]] = {}
        self._theme_members: Dict[str, tuple[List[str], datetime]] = {}
        self._universe_members: Dict[str, tuple[List[str], datetime]] = {}
        self._universe_symbols: Dict[str, tuple[List[str], datetime]] = {}  # Sprint 61: Multi-universe join support
        self._universe_metadata_cache: Dict[str, tuple[List[Dict], datetime]] = {}  # Sprint 62: Available universes metadata
        self._all_etfs: Optional[tuple[List[Dict], datetime]] = None
        self._all_sectors: Optional[tuple[List[Dict], datetime]] = None
        self._all_themes: Optional[tuple[List[Dict], datetime]] = None
        self._all_universes: Optional[tuple[List[Dict], datetime]] = None

        # Thread safety
        self._lock = Lock()

        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'loads': 0,
            'evictions': 0
        }

        logger.info(f"RelationshipCache initialized (TTL: {ttl_seconds}s)")

    def _get_connection(self):
        """Get database connection"""
        parsed = urlparse(self.db_uri)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password
        )

    def _is_expired(self, timestamp: datetime) -> bool:
        """Check if cache entry is expired"""
        return datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds)

    def get_etf_holdings(self, etf_symbol: str) -> List[str]:
        """
        Get holdings for an ETF

        Args:
            etf_symbol: ETF ticker symbol (e.g., 'SPY')

        Returns:
            List of stock symbols in the ETF
        """
        etf_symbol = etf_symbol.upper()

        with self._lock:
            # Check cache
            if etf_symbol in self._etf_holdings:
                holdings, timestamp = self._etf_holdings[etf_symbol]
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    return holdings.copy()

            # Cache miss - load from database
            self._stats['misses'] += 1

        # Load outside lock to avoid blocking
        holdings = self._load_etf_holdings_from_db(etf_symbol)

        with self._lock:
            self._etf_holdings[etf_symbol] = (holdings, datetime.now())
            self._stats['loads'] += 1

        return holdings.copy()

    def _load_etf_holdings_from_db(self, etf_symbol: str) -> List[str]:
        """Load ETF holdings from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT gm.symbol
                FROM definition_groups dg
                JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.name = %s AND dg.type = 'ETF' AND dg.environment = %s
                ORDER BY gm.symbol
            """
            cursor.execute(query, (etf_symbol, self.environment))
            holdings = [row[0] for row in cursor.fetchall()]

            conn.close()
            return holdings

        except Exception as e:
            logger.error(f"Error loading ETF holdings for {etf_symbol}: {e}")
            return []

    def get_stock_etfs(self, stock_symbol: str) -> List[str]:
        """
        Get all ETFs that contain a stock

        Args:
            stock_symbol: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            List of ETF symbols containing the stock
        """
        stock_symbol = stock_symbol.upper()

        with self._lock:
            # Check cache
            if stock_symbol in self._stock_etfs:
                etfs, timestamp = self._stock_etfs[stock_symbol]
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    return etfs.copy()

            # Cache miss
            self._stats['misses'] += 1

        # Load from database
        etfs = self._load_stock_etfs_from_db(stock_symbol)

        with self._lock:
            self._stock_etfs[stock_symbol] = (etfs, datetime.now())
            self._stats['loads'] += 1

        return etfs.copy()

    def _load_stock_etfs_from_db(self, stock_symbol: str) -> List[str]:
        """Load ETFs containing a stock from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT dg.name
                FROM definition_groups dg
                JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE gm.symbol = %s AND dg.type = 'ETF' AND dg.environment = %s
                ORDER BY dg.name
            """
            cursor.execute(query, (stock_symbol, self.environment))
            etfs = [row[0] for row in cursor.fetchall()]

            conn.close()
            return etfs

        except Exception as e:
            logger.error(f"Error loading ETFs for {stock_symbol}: {e}")
            return []

    def get_stock_sector(self, stock_symbol: str) -> Dict[str, str]:
        """
        Get sector information for a stock

        Args:
            stock_symbol: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            Dict with 'sector' and 'industry' keys
        """
        stock_symbol = stock_symbol.upper()

        with self._lock:
            # Check cache
            if stock_symbol in self._stock_sector:
                sector_info, timestamp = self._stock_sector[stock_symbol]
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    return sector_info.copy()

            # Cache miss
            self._stats['misses'] += 1

        # Load from database
        sector_info = self._load_stock_sector_from_db(stock_symbol)

        with self._lock:
            self._stock_sector[stock_symbol] = (sector_info, datetime.now())
            self._stats['loads'] += 1

        return sector_info.copy()

    def _load_stock_sector_from_db(self, stock_symbol: str) -> Dict[str, str]:
        """Load stock sector from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT dg.name, gm.metadata->>'industry'
                FROM definition_groups dg
                JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE gm.symbol = %s AND dg.type = 'SECTOR' AND dg.environment = %s
                LIMIT 1
            """
            cursor.execute(query, (stock_symbol, self.environment))
            result = cursor.fetchone()

            conn.close()

            if result:
                return {
                    'sector': result[0],
                    'industry': result[1] or 'Unknown'
                }
            return {'sector': 'unknown', 'industry': 'Unknown'}

        except Exception as e:
            logger.error(f"Error loading sector for {stock_symbol}: {e}")
            return {'sector': 'unknown', 'industry': 'Unknown'}

    def get_sector_stocks(self, sector_key: str) -> List[str]:
        """
        Get all stocks in a sector

        Args:
            sector_key: Sector key (e.g., 'information_technology')

        Returns:
            List of stock symbols in the sector
        """
        sector_key = sector_key.lower()

        with self._lock:
            # Check cache
            if sector_key in self._sector_stocks:
                stocks, timestamp = self._sector_stocks[sector_key]
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    return stocks.copy()

            # Cache miss
            self._stats['misses'] += 1

        # Load from database
        stocks = self._load_sector_stocks_from_db(sector_key)

        with self._lock:
            self._sector_stocks[sector_key] = (stocks, datetime.now())
            self._stats['loads'] += 1

        return stocks.copy()

    def _load_sector_stocks_from_db(self, sector_key: str) -> List[str]:
        """Load sector stocks from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT gm.symbol
                FROM definition_groups dg
                JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.name = %s AND dg.type = 'SECTOR' AND dg.environment = %s
                ORDER BY gm.symbol
            """
            cursor.execute(query, (sector_key, self.environment))
            stocks = [row[0] for row in cursor.fetchall()]

            conn.close()
            return stocks

        except Exception as e:
            logger.error(f"Error loading stocks for sector {sector_key}: {e}")
            return []

    def get_theme_members(self, theme_key: str) -> List[str]:
        """
        Get all stocks in a theme

        Args:
            theme_key: Theme key (e.g., 'crypto_miners')

        Returns:
            List of stock symbols in the theme
        """
        theme_key = theme_key.lower()

        with self._lock:
            # Check cache
            if theme_key in self._theme_members:
                stocks, timestamp = self._theme_members[theme_key]
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    return stocks.copy()

            # Cache miss
            self._stats['misses'] += 1

        # Load from database
        stocks = self._load_theme_members_from_db(theme_key)

        with self._lock:
            self._theme_members[theme_key] = (stocks, datetime.now())
            self._stats['loads'] += 1

        return stocks.copy()

    def _load_theme_members_from_db(self, theme_key: str) -> List[str]:
        """Load theme members from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT gm.symbol
                FROM definition_groups dg
                JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.name = %s AND dg.type = 'THEME' AND dg.environment = %s
                ORDER BY gm.symbol
            """
            cursor.execute(query, (theme_key, self.environment))
            stocks = [row[0] for row in cursor.fetchall()]

            conn.close()
            return stocks

        except Exception as e:
            logger.error(f"Error loading theme members for {theme_key}: {e}")
            return []

    def get_universe_members(self, universe_key: str) -> List[str]:
        """
        Get all stocks in a universe

        Args:
            universe_key: Universe key (e.g., 'nasdaq100')

        Returns:
            List of stock symbols in the universe
        """
        universe_key = universe_key.lower()

        with self._lock:
            # Check cache
            if universe_key in self._universe_members:
                stocks, timestamp = self._universe_members[universe_key]
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    return stocks.copy()

            # Cache miss
            self._stats['misses'] += 1

        # Load from database
        stocks = self._load_universe_members_from_db(universe_key)

        with self._lock:
            self._universe_members[universe_key] = (stocks, datetime.now())
            self._stats['loads'] += 1

        return stocks.copy()

    def _load_universe_members_from_db(self, universe_key: str) -> List[str]:
        """Load universe members from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT gm.symbol
                FROM definition_groups dg
                JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.name = %s AND dg.type = 'UNIVERSE' AND dg.environment = %s
                ORDER BY gm.symbol
            """
            cursor.execute(query, (universe_key, self.environment))
            stocks = [row[0] for row in cursor.fetchall()]

            conn.close()
            return stocks

        except Exception as e:
            logger.error(f"Error loading universe members for {universe_key}: {e}")
            return []

    def get_universe_symbols(self, universe_key: str) -> List[str]:
        """
        Get symbols for universe(s). Supports multi-universe join with colon separator.

        Sprint 61: WebSocket universe loading with multi-universe join support.

        Examples:
            'nasdaq100' -> 102 symbols
            'sp500:nasdaq100' -> ~550 distinct symbols (union)
            'SPY' -> 504 ETF holdings
            'sp500:nasdaq100:dow30' -> ~600 distinct symbols (union of all 3)

        Args:
            universe_key: Universe key (single or colon-separated for join)

        Returns:
            List of distinct stock symbols (sorted)
        """
        universe_key = universe_key.strip()

        # Check cache first
        cache_key = f"universe_symbols:{universe_key}"
        with self._lock:
            if cache_key in self._universe_symbols:
                symbols, timestamp = self._universe_symbols[cache_key]
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    return symbols.copy()

            # Cache miss
            self._stats['misses'] += 1

        # Parse universe key (supports multi-universe join)
        universe_parts = self._parse_universe_key(universe_key)
        logger.debug(f"Parsed universe key '{universe_key}' into parts: {universe_parts}")

        # Load symbols from all universes
        all_symbols: Set[str] = set()
        for universe_name in universe_parts:
            symbols = self._load_universe_symbols_from_db(universe_name)
            all_symbols.update(symbols)
            logger.debug(f"Loaded {len(symbols)} symbols from '{universe_name}'")

        # Convert to sorted list
        symbols_list = sorted(list(all_symbols))
        logger.info(
            f"Loaded {len(symbols_list)} distinct symbols from universe key '{universe_key}' "
            f"({len(universe_parts)} universes)"
        )

        # Cache result
        with self._lock:
            self._universe_symbols[cache_key] = (symbols_list, datetime.now())
            self._stats['loads'] += 1

        return symbols_list.copy()

    def _parse_universe_key(self, universe_key: str) -> List[str]:
        """
        Parse universe key into individual universe names.

        Supports colon-separated multi-universe join:
            'nasdaq100' -> ['nasdaq100']
            'sp500:nasdaq100' -> ['sp500', 'nasdaq100']
            'sp500:nasdaq100:dow30' -> ['sp500', 'nasdaq100', 'dow30']

        Args:
            universe_key: Universe key (single or colon-separated)

        Returns:
            List of individual universe names
        """
        if ':' not in universe_key:
            return [universe_key]

        # Split on colon and strip whitespace
        parts = [part.strip() for part in universe_key.split(':') if part.strip()]
        return parts

    def _load_universe_symbols_from_db(self, universe_name: str) -> List[str]:
        """
        Load symbols for a single universe from database.

        Supports both UNIVERSE and ETF types:
        - UNIVERSE: nasdaq100, sp500, dow30, russell3000
        - ETF: SPY, VOO, QQQ, etc.

        Args:
            universe_name: Single universe/ETF name (e.g., 'nasdaq100', 'SPY')

        Returns:
            List of symbols for this universe
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Query for both UNIVERSE and ETF types
            query = """
                SELECT gm.symbol
                FROM definition_groups dg
                JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.name = %s
                  AND dg.type IN ('UNIVERSE', 'ETF')
                  AND dg.environment = %s
                ORDER BY gm.symbol
            """
            cursor.execute(query, (universe_name, self.environment))
            symbols = [row[0] for row in cursor.fetchall()]

            conn.close()

            if not symbols:
                logger.warning(
                    f"No symbols found for universe '{universe_name}' "
                    f"(type UNIVERSE or ETF, environment {self.environment})"
                )

            return symbols

        except Exception as e:
            logger.error(f"Error loading symbols for universe '{universe_name}': {e}")
            return []

    def get_available_universes(self, types: List[str] = None) -> List[Dict]:
        """
        Get list of available universes with metadata.

        Sprint 62: Admin UI dynamic universe dropdown population.

        Args:
            types: Optional filter by type (e.g., ['UNIVERSE', 'ETF'])
                   Default: ['UNIVERSE', 'ETF']

        Returns:
            List of universe metadata:
            [
                {
                    'name': 'nasdaq100',
                    'type': 'UNIVERSE',
                    'description': 'NASDAQ-100 Index Components',
                    'member_count': 102,
                    'environment': 'DEFAULT',
                    'created_at': '2025-12-20T...',
                    'updated_at': '2025-12-20T...'
                },
                ...
            ]
        """
        if types is None:
            types = ['UNIVERSE', 'ETF']

        # Check cache first
        cache_key = f"available_universes:{':'.join(sorted(types))}"
        with self._lock:
            if cache_key in self._universe_metadata_cache:
                metadata, timestamp = self._universe_metadata_cache[cache_key]
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    logger.debug(f"Cache hit for available_universes (types: {types})")
                    return metadata.copy()
            self._stats['misses'] += 1

        # Query database
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT
                    dg.name,
                    dg.type,
                    dg.description,
                    COUNT(gm.symbol) as member_count,
                    dg.environment,
                    dg.created_at,
                    dg.updated_at
                FROM definition_groups dg
                LEFT JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.type = ANY(%s)
                  AND dg.environment = %s
                GROUP BY dg.id, dg.name, dg.type, dg.description, dg.environment, dg.created_at, dg.updated_at
                ORDER BY dg.type, dg.name
            """

            cursor.execute(query, (types, self.environment))

            universes = []
            for row in cursor.fetchall():
                universes.append({
                    'name': row[0],
                    'type': row[1],
                    'description': row[2] or f"{row[1]}: {row[0]}",
                    'member_count': row[3],
                    'environment': row[4],
                    'created_at': row[5].isoformat() if row[5] else None,
                    'updated_at': row[6].isoformat() if row[6] else None
                })

            conn.close()

            logger.info(
                f"Loaded {len(universes)} available universes from database "
                f"(types: {types}, environment: {self.environment})"
            )

            # Cache result
            with self._lock:
                self._universe_metadata_cache[cache_key] = (universes, datetime.now())
                self._stats['loads'] += 1

            return universes.copy()

        except Exception as e:
            logger.error(f"Error loading available universes: {e}")
            return []

    def get_all_etfs(self) -> List[Dict]:
        """
        Get all ETFs with metadata

        Returns:
            List of dicts with ETF info (name, description, holdings_count)
        """
        with self._lock:
            # Check cache
            if self._all_etfs is not None:
                etfs, timestamp = self._all_etfs
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    return [e.copy() for e in etfs]

            # Cache miss
            self._stats['misses'] += 1

        # Load from database
        etfs = self._load_all_etfs_from_db()

        with self._lock:
            self._all_etfs = (etfs, datetime.now())
            self._stats['loads'] += 1

        return [e.copy() for e in etfs]

    def _load_all_etfs_from_db(self) -> List[Dict]:
        """Load all ETFs from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT dg.name, dg.description, COUNT(gm.symbol) as holdings_count
                FROM definition_groups dg
                LEFT JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.type = 'ETF' AND dg.environment = %s
                GROUP BY dg.id, dg.name, dg.description
                ORDER BY dg.name
            """
            cursor.execute(query, (self.environment,))

            etfs = []
            for row in cursor.fetchall():
                etfs.append({
                    'symbol': row[0],
                    'name': row[1],
                    'holdings_count': row[2]
                })

            conn.close()
            return etfs

        except Exception as e:
            logger.error(f"Error loading all ETFs: {e}")
            return []

    def get_all_sectors(self) -> List[Dict]:
        """
        Get all sectors with metadata

        Returns:
            List of dicts with sector info (name, description, stock_count)
        """
        with self._lock:
            # Check cache
            if self._all_sectors is not None:
                sectors, timestamp = self._all_sectors
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    return [s.copy() for s in sectors]

            # Cache miss
            self._stats['misses'] += 1

        # Load from database
        sectors = self._load_all_sectors_from_db()

        with self._lock:
            self._all_sectors = (sectors, datetime.now())
            self._stats['loads'] += 1

        return [s.copy() for s in sectors]

    def _load_all_sectors_from_db(self) -> List[Dict]:
        """Load all sectors from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT dg.name, dg.description, COUNT(DISTINCT gm.symbol) as stock_count
                FROM definition_groups dg
                LEFT JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.type = 'SECTOR' AND dg.environment = %s
                GROUP BY dg.id, dg.name, dg.description
                ORDER BY stock_count DESC
            """
            cursor.execute(query, (self.environment,))

            sectors = []
            for row in cursor.fetchall():
                sectors.append({
                    'key': row[0],
                    'name': row[1],
                    'stock_count': row[2]
                })

            conn.close()
            return sectors

        except Exception as e:
            logger.error(f"Error loading all sectors: {e}")
            return []

    def get_all_themes(self) -> List[Dict]:
        """
        Get all themes with metadata

        Returns:
            List of dicts with theme info (name, description, member_count)
        """
        with self._lock:
            # Check cache
            if self._all_themes is not None:
                themes, timestamp = self._all_themes
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    return [t.copy() for t in themes]

            # Cache miss
            self._stats['misses'] += 1

        # Load from database
        themes = self._load_all_themes_from_db()

        with self._lock:
            self._all_themes = (themes, datetime.now())
            self._stats['loads'] += 1

        return [t.copy() for t in themes]

    def _load_all_themes_from_db(self) -> List[Dict]:
        """Load all themes from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT dg.name, dg.description, COUNT(gm.symbol) as member_count
                FROM definition_groups dg
                LEFT JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.type = 'THEME' AND dg.environment = %s
                GROUP BY dg.id, dg.name, dg.description
                ORDER BY dg.name
            """
            cursor.execute(query, (self.environment,))

            themes = []
            for row in cursor.fetchall():
                themes.append({
                    'key': row[0],
                    'name': row[1],
                    'member_count': row[2]
                })

            conn.close()
            return themes

        except Exception as e:
            logger.error(f"Error loading all themes: {e}")
            return []

    def get_all_universes(self) -> List[Dict]:
        """
        Get all universes with metadata

        Returns:
            List of dicts with universe info (name, description, member_count)
        """
        with self._lock:
            # Check cache
            if self._all_universes is not None:
                universes, timestamp = self._all_universes
                if not self._is_expired(timestamp):
                    self._stats['hits'] += 1
                    return [u.copy() for u in universes]

            # Cache miss
            self._stats['misses'] += 1

        # Load from database
        universes = self._load_all_universes_from_db()

        with self._lock:
            self._all_universes = (universes, datetime.now())
            self._stats['loads'] += 1

        return [u.copy() for u in universes]

    def _load_all_universes_from_db(self) -> List[Dict]:
        """Load all universes from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT dg.name, dg.description, COUNT(gm.symbol) as member_count
                FROM definition_groups dg
                LEFT JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.type = 'UNIVERSE' AND dg.environment = %s
                GROUP BY dg.id, dg.name, dg.description
                ORDER BY dg.name
            """
            cursor.execute(query, (self.environment,))

            universes = []
            for row in cursor.fetchall():
                universes.append({
                    'key': row[0],
                    'name': row[1],
                    'member_count': row[2]
                })

            conn.close()
            return universes

        except Exception as e:
            logger.error(f"Error loading all universes: {e}")
            return []

    def invalidate(self, cache_type: Optional[str] = None, key: Optional[str] = None):
        """
        Invalidate cache entries

        Args:
            cache_type: Type to invalidate ('etf', 'sector', 'theme', 'universe', 'all')
            key: Specific key to invalidate (if None, invalidates all of that type)
        """
        with self._lock:
            if cache_type is None or cache_type == 'all':
                # Invalidate everything
                self._etf_holdings.clear()
                self._stock_etfs.clear()
                self._stock_sector.clear()
                self._sector_stocks.clear()
                self._theme_members.clear()
                self._universe_members.clear()
                self._universe_symbols.clear()  # Sprint 61
                self._universe_metadata_cache.clear()  # Sprint 62
                self._all_etfs = None
                self._all_sectors = None
                self._all_themes = None
                self._all_universes = None
                self._stats['evictions'] += 1
                logger.info("Cache invalidated: all")

            elif cache_type == 'etf':
                if key:
                    self._etf_holdings.pop(key.upper(), None)
                else:
                    self._etf_holdings.clear()
                    self._all_etfs = None
                self._stats['evictions'] += 1
                logger.info(f"Cache invalidated: etf/{key or 'all'}")

            elif cache_type == 'sector':
                if key:
                    self._sector_stocks.pop(key.lower(), None)
                else:
                    self._sector_stocks.clear()
                    self._all_sectors = None
                self._stats['evictions'] += 1
                logger.info(f"Cache invalidated: sector/{key or 'all'}")

            elif cache_type == 'theme':
                if key:
                    self._theme_members.pop(key.lower(), None)
                else:
                    self._theme_members.clear()
                    self._all_themes = None
                self._stats['evictions'] += 1
                logger.info(f"Cache invalidated: theme/{key or 'all'}")

            elif cache_type == 'universe':
                if key:
                    self._universe_members.pop(key.lower(), None)
                    # Sprint 61: Also clear universe_symbols cache entries that contain this key
                    keys_to_remove = [k for k in self._universe_symbols.keys() if key.lower() in k]
                    for k in keys_to_remove:
                        self._universe_symbols.pop(k, None)
                else:
                    self._universe_members.clear()
                    self._universe_symbols.clear()  # Sprint 61
                    self._universe_metadata_cache.clear()  # Sprint 62
                    self._all_universes = None
                self._stats['evictions'] += 1
                logger.info(f"Cache invalidated: universe/{key or 'all'}")

    def get_stats(self) -> Dict:
        """
        Get cache statistics

        Returns:
            Dict with cache statistics
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0

            return {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'loads': self._stats['loads'],
                'evictions': self._stats['evictions'],
                'hit_rate': round(hit_rate, 2),
                'total_requests': total_requests,
                'cache_sizes': {
                    'etf_holdings': len(self._etf_holdings),
                    'stock_etfs': len(self._stock_etfs),
                    'stock_sector': len(self._stock_sector),
                    'sector_stocks': len(self._sector_stocks),
                    'theme_members': len(self._theme_members),
                    'universe_members': len(self._universe_members)
                }
            }

    def warm_cache(self):
        """
        Pre-populate cache with common queries
        """
        logger.info("Warming cache...")
        start_time = time.time()

        # Load all metadata
        self.get_all_etfs()
        self.get_all_sectors()
        self.get_all_themes()
        self.get_all_universes()

        # Load major ETFs
        major_etfs = ['SPY', 'QQQ', 'DIA', 'VTI', 'IWM']
        for etf in major_etfs:
            self.get_etf_holdings(etf)

        # Load all sector stocks
        sectors = self.get_all_sectors()
        for sector in sectors:
            self.get_sector_stocks(sector['key'])

        elapsed = time.time() - start_time
        logger.info(f"Cache warmed in {elapsed:.2f}s")


# Singleton instance
_cache_instance: Optional[RelationshipCache] = None
_cache_lock = Lock()


def get_relationship_cache(ttl_seconds: int = 3600) -> RelationshipCache:
    """
    Get singleton cache instance

    Args:
        ttl_seconds: TTL for cache entries (default: 1 hour)

    Returns:
        RelationshipCache instance
    """
    global _cache_instance

    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = RelationshipCache(ttl_seconds=ttl_seconds)

    return _cache_instance
