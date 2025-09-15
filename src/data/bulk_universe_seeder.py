"""
Bulk Universe Seeder Service
Enhanced bulk loading capabilities for admin interface with testing limiters.

Features:
- Predefined universe loading (S&P 500, Russell 3000, etc.)
- Testing limits for controlled seeding
- Polygon.io API integration for fresh symbol data
- Cache organization auto-creation
"""

import logging
import requests
import time
import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

logger = logging.getLogger(__name__)

class UniverseType(Enum):
    """Predefined universe types for bulk loading."""
    SP_500 = "sp_500"
    RUSSELL_3000 = "russell_3000"  
    NASDAQ_100 = "nasdaq_100"
    DOW_30 = "dow_30"
    ALL_ETFS = "all_etfs"
    CURATED_ETFS = "curated_etfs"
    SECTOR_TECH = "sector_technology"
    SECTOR_HEALTHCARE = "sector_healthcare"
    SECTOR_FINANCIAL = "sector_financial"
    SECTOR_ENERGY = "sector_energy"
    MARKET_CAP_LARGE = "large_cap"
    MARKET_CAP_MID = "mid_cap"
    MARKET_CAP_SMALL = "small_cap"

@dataclass
class UniverseConfig:
    """Configuration for a predefined universe."""
    name: str
    description: str
    estimated_count: int
    api_endpoint: Optional[str] = None
    filter_criteria: Optional[Dict[str, Any]] = None

@dataclass
class BulkLoadRequest:
    """Request parameters for bulk universe loading."""
    universe_type: UniverseType
    limit: Optional[int] = None  # Testing limiter
    sort_by: str = "market_cap"  # How to select limited symbols
    include_metadata: bool = True
    create_cache_entries: bool = True
    overwrite_existing: bool = False

@dataclass 
class BulkLoadResult:
    """Result of bulk loading operation."""
    success: bool
    symbols_loaded: int
    symbols_updated: int
    symbols_skipped: int
    cache_entries_created: int
    errors: List[str]
    execution_time: float
    
class BulkUniverseSeeder:
    """Service for bulk loading predefined symbol universes."""
    
    # Predefined universe configurations
    UNIVERSE_CONFIGS = {
        UniverseType.SP_500: UniverseConfig(
            name="S&P 500",
            description="S&P 500 Index stocks",
            estimated_count=500,
            api_endpoint="https://api.polygon.io/v3/reference/tickers",
            filter_criteria={
                "market": "stocks",
                "active": "true",
                "limit": "1000",
                "order": "desc",
                "sort": "ticker"
            }
        ),
        UniverseType.RUSSELL_3000: UniverseConfig(
            name="Russell 3000", 
            description="Russell 3000 Index stocks",
            estimated_count=3000,
            api_endpoint="https://api.polygon.io/v3/reference/tickers",
            filter_criteria={
                "market": "stocks",
                "active": "true", 
                "limit": "1000",
                "order": "desc",
                "sort": "ticker"
            }
        ),
        UniverseType.NASDAQ_100: UniverseConfig(
            name="NASDAQ 100",
            description="NASDAQ 100 Index stocks", 
            estimated_count=100,
            api_endpoint="https://api.polygon.io/v3/reference/tickers",
            filter_criteria={
                "market": "stocks",
                "active": "true",
                "exchange": "XNAS",
                "limit": "1000",
                "order": "desc", 
                "sort": "ticker"
            }
        ),
        UniverseType.ALL_ETFS: UniverseConfig(
            name="All ETFs",
            description="All active Exchange Traded Funds",
            estimated_count=2500,
            api_endpoint="https://api.polygon.io/v3/reference/tickers",
            filter_criteria={
                "market": "stocks",
                "type": "ETF",
                "active": "true",
                "limit": "1000",
                "order": "desc",
                "sort": "ticker"
            }
        ),
        UniverseType.CURATED_ETFS: UniverseConfig(
            name="Curated ETFs",
            description="Essential ETFs for market analysis (46 curated symbols)",
            estimated_count=46,
            api_endpoint=None,  # Load from CSV file
            filter_criteria=None  # CSV-based loading
        ),
        UniverseType.SECTOR_TECH: UniverseConfig(
            name="Technology Sector",
            description="Technology sector stocks",
            estimated_count=800,
            filter_criteria={
                "market": "stocks", 
                "active": "true",
                "limit": "1000",
                "order": "desc",
                "sort": "ticker"
            }
        ),
        UniverseType.MARKET_CAP_LARGE: UniverseConfig(
            name="Large Cap Stocks",
            description="Large capitalization stocks (>$10B)",
            estimated_count=1000,
            filter_criteria={
                "market": "stocks",
                "active": "true",
                "gte.market_cap": "10000000000",
                "limit": "1000",
                "order": "desc",
                "sort": "ticker"
            }
        )
    }
    
    def __init__(self, polygon_api_key: str, database_uri: str):
        """Initialize bulk seeder service."""
        self.polygon_api_key = polygon_api_key
        self.database_uri = database_uri
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {polygon_api_key}"})
        
    def get_available_universes(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available universes with metadata."""
        return {
            universe_type.value: {
                "name": config.name,
                "description": config.description, 
                "estimated_count": config.estimated_count,
                "supports_limiting": True,
                "sort_options": ["market_cap", "name", "volume"]
            }
            for universe_type, config in self.UNIVERSE_CONFIGS.items()
        }
    
    def estimate_load_size(self, request: BulkLoadRequest) -> int:
        """Estimate number of symbols that will be loaded."""
        config = self.UNIVERSE_CONFIGS.get(request.universe_type)
        if not config:
            return 0
            
        estimated = config.estimated_count
        if request.limit:
            estimated = min(estimated, request.limit)
            
        return estimated
    
    def load_universe(self, request: BulkLoadRequest) -> BulkLoadResult:
        """Load symbols from specified universe with optional limiting."""
        start_time = time.time()
        result = BulkLoadResult(
            success=False, symbols_loaded=0, symbols_updated=0,
            symbols_skipped=0, cache_entries_created=0, errors=[],
            execution_time=0.0
        )
        
        try:
            # Get universe configuration
            config = self.UNIVERSE_CONFIGS.get(request.universe_type)
            if not config:
                result.errors.append(f"Unknown universe type: {request.universe_type}")
                return result
            
            logger.info(f"BULK-SEEDER: Loading {config.name} universe (limit: {request.limit})")
            
            # Fetch symbols from Polygon API
            symbols_data = self._fetch_symbols_from_polygon(config, request)
            if not symbols_data:
                result.errors.append("No symbols retrieved from Polygon API")
                return result
                
            # Apply testing limiter
            if request.limit:
                symbols_data = self._apply_limiter(symbols_data, request.limit, request.sort_by)
                logger.info(f"BULK-SEEDER: Applied limit of {request.limit} symbols")
            
            # Load symbols into database
            load_stats = self._load_symbols_to_database(symbols_data, request.overwrite_existing)
            result.symbols_loaded = load_stats['loaded']
            result.symbols_updated = load_stats['updated'] 
            result.symbols_skipped = load_stats['skipped']
            
            # Create cache entries if requested
            if request.create_cache_entries:
                cache_count = self._create_cache_entries(request.universe_type, symbols_data)
                result.cache_entries_created = cache_count
                
            result.success = True
            result.execution_time = time.time() - start_time
            
            logger.info(f"BULK-SEEDER: Completed {config.name} - "
                       f"Loaded: {result.symbols_loaded}, Updated: {result.symbols_updated}, "
                       f"Time: {result.execution_time:.2f}s")
            
        except Exception as e:
            result.errors.append(f"Bulk loading failed: {str(e)}")
            result.execution_time = time.time() - start_time
            logger.error(f"BULK-SEEDER: Failed to load universe {request.universe_type}: {e}")
            
        return result
    
    def _fetch_symbols_from_polygon(self, config: UniverseConfig, request: BulkLoadRequest) -> List[Dict[str, Any]]:
        """Fetch symbols from Polygon.io API or CSV file for curated lists."""
        
        # Handle curated ETFs - load from CSV file
        if request.universe_type == UniverseType.CURATED_ETFS:
            return self._load_curated_etfs_from_csv()
        
        # Handle standard API-based loading
        all_symbols = []
        next_url = None
        page_count = 0
        max_pages = 10  # Safety limit
        
        while page_count < max_pages:
            try:
                # Prepare API request
                if next_url:
                    # next_url from Polygon API is already a complete URL
                    url = next_url
                    # Use next_url directly (already includes params and apikey)
                    response = self.session.get(url)
                else:
                    # First request - build parameters
                    url = config.api_endpoint or "https://api.polygon.io/v3/reference/tickers"
                    params = config.filter_criteria.copy() if config.filter_criteria else {}
                    params["apikey"] = self.polygon_api_key
                    # Avoid duplicate limit parameter
                    if "limit" not in params:
                        params["limit"] = "1000"
                    response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Extract symbols
                results = data.get('results', [])
                all_symbols.extend(results)
                
                # Check for pagination
                next_url = data.get('next_url')
                if not next_url:
                    break
                    
                page_count += 1
                time.sleep(0.1)  # Rate limiting
                
            except requests.exceptions.RequestException as e:
                logger.error(f"BULK-SEEDER: API request failed: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_data = e.response.json()
                        logger.error(f"BULK-SEEDER: API error details: {error_data}")
                    except:
                        logger.error(f"BULK-SEEDER: API error response: {e.response.text}")
                break
                
        logger.info(f"BULK-SEEDER: Fetched {len(all_symbols)} symbols from Polygon API")
        return all_symbols
    
    def _load_curated_etfs_from_csv(self) -> List[Dict[str, Any]]:
        """Load curated ETFs from CSV file."""
        # Get to project root: src/data -> src -> project root -> data/curated-etfs.csv
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        csv_path = os.path.join(project_root, 'data', 'curated-etfs.csv')
        
        if not os.path.exists(csv_path):
            logger.error(f"BULK-SEEDER: Curated ETF CSV file not found: {csv_path}")
            return []
        
        etf_symbols = []
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Create symbol data in Polygon API format for compatibility
                    symbol_data = {
                        'ticker': row['symbol'],
                        'symbol': row['symbol'],
                        'name': row['name'],
                        'type': 'ETF',
                        'market': 'stocks',
                        'active': True,
                        'locale': 'us',
                        'currency_name': 'USD',
                        'primary_exchange': 'XNAS',  # Default to NASDAQ
                        'composite_figi': None,
                        'share_class_figi': None,
                        'market_cap': None,
                        'cik': None,
                        'sic_description': row.get('category', 'ETF'),
                        'industry': f"{row.get('category', 'ETF')} ETF",
                        'description': row.get('description', ''),
                        'etf_type': 'ETF',
                        'issuer': 'Various'
                    }
                    etf_symbols.append(symbol_data)
            
            logger.info(f"BULK-SEEDER: Loaded {len(etf_symbols)} curated ETFs from CSV")
            return etf_symbols
            
        except Exception as e:
            logger.error(f"BULK-SEEDER: Error loading curated ETFs from CSV: {e}")
            return []
    
    def _apply_limiter(self, symbols_data: List[Dict[str, Any]], limit: int, sort_by: str) -> List[Dict[str, Any]]:
        """Apply testing limiter to symbol list."""
        # Sort symbols based on criteria
        if sort_by == "market_cap":
            symbols_data.sort(key=lambda x: x.get('market_cap', 0), reverse=True)
        elif sort_by == "name":
            symbols_data.sort(key=lambda x: x.get('name', ''))
        elif sort_by == "volume":
            symbols_data.sort(key=lambda x: x.get('share_class_shares_outstanding', 0), reverse=True)
            
        return symbols_data[:limit]
    
    def _load_symbols_to_database(self, symbols_data: List[Dict[str, Any]], overwrite: bool) -> Dict[str, int]:
        """Load symbols into database with enhanced metadata."""
        loaded = updated = skipped = 0
        
        conn = psycopg2.connect(self.database_uri)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                for symbol_data in symbols_data:
                    try:
                        symbol = symbol_data.get('ticker') or symbol_data.get('symbol', '')
                        if not symbol:
                            skipped += 1
                            continue
                            
                        # Check if symbol exists
                        cursor.execute("SELECT symbol FROM symbols WHERE symbol = %s", (symbol,))
                        existing = cursor.fetchone()
                        
                        # Prepare symbol data mapping to actual symbols table schema with truncation
                        def truncate_field(value, max_length):
                            """Safely truncate string fields to fit database constraints."""
                            if value is None:
                                return None
                            return str(value)[:max_length] if len(str(value)) > max_length else str(value)
                        
                        symbol_record = {
                            'symbol': truncate_field(symbol, 20),
                            'name': truncate_field(symbol_data.get('name', ''), 100),
                            'type': truncate_field(symbol_data.get('type', 'CS'), 20),
                            'active': True,
                            'market_cap': symbol_data.get('market_cap'),
                            'sector': truncate_field(symbol_data.get('sic_description', ''), 50),
                            'industry': truncate_field(symbol_data.get('industry', ''), 100),
                            'currency_name': truncate_field(symbol_data.get('currency_name', 'USD'), 10),
                            'primary_exchange': truncate_field(symbol_data.get('primary_exchange'), 20),
                            'composite_figi': truncate_field(symbol_data.get('composite_figi'), 50),
                            'exchange': truncate_field(symbol_data.get('primary_exchange'), 20),
                            'market': truncate_field(symbol_data.get('market', 'stocks'), 20),
                            'locale': truncate_field(symbol_data.get('locale', 'us'), 10),
                            'cik': truncate_field(symbol_data.get('cik'), 20),
                            'share_class_figi': truncate_field(symbol_data.get('share_class_figi'), 50),
                            'last_updated_utc': datetime.now()
                        }
                        
                        if existing and overwrite:
                            # Update existing symbol
                            update_sql = """
                                UPDATE symbols SET 
                                    name = %(name)s, type = %(type)s, market_cap = %(market_cap)s,
                                    sector = %(sector)s, industry = %(industry)s, 
                                    currency_name = %(currency_name)s, primary_exchange = %(primary_exchange)s,
                                    composite_figi = %(composite_figi)s, last_updated_utc = %(last_updated_utc)s,
                                    exchange = %(exchange)s, market = %(market)s, locale = %(locale)s,
                                    cik = %(cik)s, share_class_figi = %(share_class_figi)s
                                WHERE symbol = %(symbol)s
                            """
                            cursor.execute(update_sql, symbol_record)
                            updated += 1
                            
                        elif not existing:
                            # Insert new symbol
                            insert_sql = """
                                INSERT INTO symbols (symbol, name, type, active, market_cap, sector, industry, 
                                                   currency_name, primary_exchange, composite_figi, exchange, 
                                                   market, locale, cik, share_class_figi, last_updated_utc)
                                VALUES (%(symbol)s, %(name)s, %(type)s, %(active)s, %(market_cap)s, %(sector)s, 
                                       %(industry)s, %(currency_name)s, %(primary_exchange)s, %(composite_figi)s,
                                       %(exchange)s, %(market)s, %(locale)s, %(cik)s, %(share_class_figi)s,
                                       %(last_updated_utc)s)
                            """
                            cursor.execute(insert_sql, symbol_record)
                            loaded += 1
                        else:
                            skipped += 1
                            
                    except Exception as e:
                        logger.error(f"BULK-SEEDER: Error processing symbol {symbol}: {e}")
                        skipped += 1
                        continue
                        
            conn.commit()
            
        finally:
            conn.close()
            
        return {'loaded': loaded, 'updated': updated, 'skipped': skipped}
    
    def _create_cache_entries(self, universe_type: UniverseType, symbols_data: List[Dict[str, Any]]) -> int:
        """Create cache entries for loaded universe."""
        config = self.UNIVERSE_CONFIGS.get(universe_type)
        if not config:
            return 0
            
        symbols = [s.get('ticker') or s.get('symbol') for s in symbols_data if s.get('ticker') or s.get('symbol')]
        
        conn = psycopg2.connect(self.database_uri)
        try:
            with conn.cursor() as cursor:
                # Create universe cache entry
                cache_entry_sql = """
                    INSERT INTO cache_entries (type, name, key, value, created_at, updated_at)
                    VALUES ('stock_universe', %s, 'symbols', %s, %s, %s)
                    ON CONFLICT (type, name, key) DO UPDATE SET
                        value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
                """
                cursor.execute(cache_entry_sql, (
                    config.name,
                    ','.join(symbols),
                    datetime.now(),
                    datetime.now()
                ))
                
                # Create metadata entry
                metadata = {
                    'universe_type': universe_type.value,
                    'loaded_count': len(symbols),
                    'load_date': datetime.now().isoformat(),
                    'description': config.description
                }
                
                cursor.execute(cache_entry_sql, (
                    config.name,
                    'metadata',
                    str(metadata),
                    datetime.now(),
                    datetime.now()
                ))
                
            conn.commit()
            return 2  # Created 2 cache entries
            
        finally:
            conn.close()