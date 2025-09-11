#!/usr/bin/env python3
"""
Cache Entries Synchronization Service
Implements cache_entries organization based on cache_entries_directions.md

Organizes stocks and ETFs into logical groups in the cache_entries table:
- Market cap categories (mega_cap, large_cap, mid_cap, small_cap, micro_cap) 
- Sector leaders (top 10 per sector)
- Market leaders (top_10_stocks, top_50, top_100, top_250, top_500)
- Themes (AI, Biotech, Cloud, Crypto, etc.)
- Industry groups (banks, insurance, software, retail)
- ETF universes (broad_market, sectors, growth, value, international, technology, bonds, commodities)
- Complete universes (all_stocks)

Works with existing table structure: type, name, key, value
PRESERVES app_settings and other non-stock content
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class CacheEntriesSynchronizer:
    """
    Cache entries synchronization service for TickStock
    
    Rebuilds and organizes stock/ETF cache entries based on current symbols table data.
    Preserves app_settings and other non-stock entries.
    """
    
    def __init__(self, environment='DEFAULT'):
        """Initialize synchronizer with database and Redis connections."""
        self.db_conn = None
        self.redis_client = None
        self.sync_timestamp = datetime.utcnow()
        self.environment = environment
        
        # Configuration loaded from database (cache_entries with type='cache_config')
        self.market_cap_thresholds = {}
        self.theme_definitions = {}
        self.industry_groups = {}
        self.etf_categories = {}
        self.complete_limits = {}
    
    def connect(self) -> bool:
        """Establish database and Redis connections."""
        try:
            # Database connection using .env
            database_url = os.getenv('DATABASE_URI')
            if not database_url:
                raise ValueError("DATABASE_URI not found in .env file")
                
            parsed = urlparse(database_url)
            db_config = {
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "database": parsed.path.lstrip('/'),
                "user": parsed.username,
                "password": parsed.password
            }
            self.db_conn = psycopg2.connect(**db_config)
            
            # Redis connection (optional for notifications)
            try:
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', 6379))
                redis_db = int(os.getenv('REDIS_DB', 0))
                self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
                self.redis_client.ping()  # Test connection
            except:
                logger.warning("Redis connection failed, notifications will be disabled")
                self.redis_client = None
            
            logger.info("✅ CacheEntriesSynchronizer connected to database")
            
            # Load configuration from database
            self._load_configuration()
            
            return True
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close all connections."""
        if self.db_conn:
            self.db_conn.close()
        if self.redis_client:
            self.redis_client.close()
        logger.info("🔌 CacheEntriesSynchronizer disconnected")
    
    def _load_configuration(self):
        """Load configuration from cache_entries table (type='cache_config')."""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT name, key, value
                    FROM cache_entries
                    WHERE type = 'cache_config'
                    ORDER BY name, key
                """)
                
                config_rows = cursor.fetchall()
                
                for row in config_rows:
                    config_name = row['name']
                    config_key = row['key']
                    config_value = row['value']
                    
                    # Parse JSON values
                    try:
                        if isinstance(config_value, str):
                            parsed_value = json.loads(config_value)
                        else:
                            parsed_value = config_value
                    except:
                        # Handle non-JSON values (like simple numbers)
                        if config_value.isdigit():
                            parsed_value = int(config_value)
                        else:
                            parsed_value = config_value
                    
                    # Load into appropriate configuration dictionary
                    if config_name == 'market_cap_thresholds':
                        self.market_cap_thresholds[config_key] = parsed_value
                    elif config_name == 'theme_definitions':
                        self.theme_definitions[config_key] = parsed_value
                    elif config_name == 'industry_groups':
                        self.industry_groups[config_key] = parsed_value
                    elif config_name == 'etf_categories':
                        self.etf_categories[config_key] = parsed_value
                    elif config_name == 'complete_limits':
                        self.complete_limits[config_key] = parsed_value
                
                logger.info(f"📋 Loaded configuration: {len(self.market_cap_thresholds)} thresholds, "
                           f"{len(self.theme_definitions)} themes, {len(self.industry_groups)} industries, "
                           f"{len(self.etf_categories)} ETF categories")
                
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            # Fall back to default configuration
            self._load_default_configuration()
    
    def _load_default_configuration(self):
        """Load default configuration as fallback."""
        logger.warning("⚠️ Loading default configuration as fallback")
        
        self.market_cap_thresholds = {
            'mega_cap': 200_000_000_000,
            'large_cap': 10_000_000_000,
            'mid_cap': 2_000_000_000,
            'small_cap': 300_000_000,
            'micro_cap': 0
        }
        
        self.theme_definitions = {
            'ai': ['NVDA', 'GOOGL', 'MSFT', 'AMD'],
            'biotech': ['MRNA', 'GILD', 'BIIB', 'AMGN'],
            'cloud': ['CRM', 'SNOW', 'AMZN', 'MSFT'],
            'crypto': ['COIN', 'RIOT', 'MARA', 'SQ']
        }
        
        self.industry_groups = {
            'banks': ['Banks', 'Regional Banks'],
            'insurance': ['Insurance', 'Property & Casualty Insurance'],
            'software': ['Software', 'Application Software'],
            'retail': ['Retail', 'Specialty Retail']
        }
        
        self.etf_categories = {
            'etf_broad_market': 'Broad Market ETFs',
            'etf_sectors': 'Sector ETFs',
            'etf_growth': 'Growth ETFs',
            'etf_value': 'Value ETFs'
        }
        
        self.complete_limits = {
            'stocks_full_metadata_limit': 1000,
            'etfs_full_metadata_limit': 100
        }
    
    def rebuild_stock_cache_entries(self, delete_existing: bool = True) -> Dict[str, int]:
        """
        Rebuild stock and ETF cache entries from current symbols table.
        
        Args:
            delete_existing: If True, removes existing stock/ETF entries first
            
        Returns:
            Dict with rebuild statistics
        """
        logger.info(f"🔄 Starting cache entries rebuild at {self.sync_timestamp}")
        
        stats = {
            'deleted_entries': 0,
            'market_cap_entries': 0,
            'sector_leader_entries': 0,
            'market_leader_entries': 0, 
            'theme_entries': 0,
            'industry_entries': 0,
            'etf_entries': 0,
            'complete_entries': 0,
            'combo_entries': 0,
            'stats_entries': 0,
            'redis_notifications': 0
        }
        
        try:
            if not self.connect():
                raise Exception("Failed to establish connections")
            
            # Step 1: Clear existing stock/ETF entries (preserve app_settings)
            if delete_existing:
                stats['deleted_entries'] = self._delete_stock_etf_entries()
            
            # Step 2: Create market cap categories
            stats['market_cap_entries'] = self._create_market_cap_entries()
            
            # Step 3: Create sector leaders
            stats['sector_leader_entries'] = self._create_sector_leader_entries()
            
            # Step 4: Create market leaders
            stats['market_leader_entries'] = self._create_market_leader_entries()
            
            # Step 5: Create theme entries
            stats['theme_entries'] = self._create_theme_entries()
            
            # Step 6: Create industry entries
            stats['industry_entries'] = self._create_industry_entries()
            
            # Step 7: Create ETF entries
            stats['etf_entries'] = self._create_etf_entries()
            
            # Step 8: Create complete universe
            stats['complete_entries'] = self._create_complete_entries()
            
            # Step 9: Create combo test universe
            stats['combo_entries'] = self._create_combo_test_entries()
            
            # Step 10: Create statistics summary
            stats['stats_entries'] = self._create_stats_entries()
            
            # Step 11: Redis notifications
            if self.redis_client:
                stats['redis_notifications'] = self._publish_rebuild_notifications(stats)
            
            # Commit all changes
            self.db_conn.commit()
            
            logger.info(f"✅ Cache rebuild completed successfully: {stats}")
            return stats
            
        except Exception as e:
            if self.db_conn:
                self.db_conn.rollback()
            logger.error(f"❌ Cache rebuild failed: {e}")
            raise
        finally:
            self.disconnect()
    
    def _delete_stock_etf_entries(self) -> int:
        """Delete existing stock/ETF entries, preserving app_settings and cache_config."""
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM cache_entries 
                WHERE type NOT IN ('app_settings', 'cache_config')
            """)
            deleted_count = cursor.rowcount
            logger.info(f"🗑️ Deleted {deleted_count} existing cache entries (preserved app_settings and cache_config)")
            return deleted_count
    
    def _create_market_cap_entries(self) -> int:
        """Create market cap category entries."""
        created_count = 0
        
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for category, min_threshold in self.market_cap_thresholds.items():
                # Build query based on threshold
                if category == 'mega_cap':
                    where_clause = f"market_cap >= {min_threshold}"
                elif category == 'micro_cap':
                    where_clause = f"market_cap < {self.market_cap_thresholds['small_cap']}"
                else:
                    if category == 'large_cap':
                        where_clause = f"market_cap >= {min_threshold} AND market_cap < {self.market_cap_thresholds['mega_cap']}"
                    elif category == 'mid_cap':
                        where_clause = f"market_cap >= {min_threshold} AND market_cap < {self.market_cap_thresholds['large_cap']}"
                    elif category == 'small_cap':
                        where_clause = f"market_cap >= {min_threshold} AND market_cap < {self.market_cap_thresholds['mid_cap']}"
                
                # Get stocks for this market cap category
                cursor.execute(f"""
                    SELECT symbol, name, market_cap, primary_exchange, market
                    FROM symbols
                    WHERE {where_clause} 
                      AND active = true 
                      AND type = 'CS'
                      AND market_cap IS NOT NULL
                    ORDER BY market_cap DESC
                """)
                
                stocks = cursor.fetchall()
                
                if stocks:
                    # Create stock universe format
                    stock_data = {
                        "count": len(stocks),
                        "stocks": [
                            {
                                "name": stock['name'],
                                "rank": idx + 1,
                                "sector": "Unknown",  # Sector data not available in symbols table
                                "ticker": stock['symbol'],
                                "exchange": stock['primary_exchange'] or 'Unknown',
                                "industry": "Unknown",  # Industry data not available in symbols table
                                "market_cap": float(stock['market_cap']) if stock['market_cap'] else 0.0,
                                "market": stock['market'] or 'Unknown'
                            }
                            for idx, stock in enumerate(stocks)
                        ]
                    }
                    
                    # Insert into cache_entries
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, ('stock_universe', 'market_cap', category, json.dumps(stock_data), self.environment))
                    
                    created_count += 1
                    logger.info(f"📊 Created {category} with {len(stocks)} stocks")
        
        return created_count
    
    def _create_sector_leader_entries(self) -> int:
        """Create sector leader entries (top 10 per sector) - NOW WITH REAL DATA!"""
        created_count = 0
        
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get distinct sectors from symbols with SIC data
            cursor.execute("""
                SELECT DISTINCT sector
                FROM symbols
                WHERE sector IS NOT NULL 
                  AND sector != 'Unknown'
                  AND active = true
                  AND type = 'CS'
                  AND market_cap IS NOT NULL
            """)
            
            sectors = [row['sector'] for row in cursor.fetchall()]
            logger.info(f"🏢 Found {len(sectors)} sectors with classified stocks")
            
            for sector in sectors:
                # Get top 10 stocks by market cap for this sector
                cursor.execute("""
                    SELECT symbol, name, market_cap, sector, industry, primary_exchange, market
                    FROM symbols
                    WHERE sector = %s
                      AND active = true
                      AND type = 'CS'
                      AND market_cap IS NOT NULL
                    ORDER BY market_cap DESC
                    LIMIT 10
                """, (sector,))
                
                stocks = cursor.fetchall()
                
                if stocks:
                    sector_key = f"top_10_{sector.lower().replace(' ', '_').replace('&', 'and')}"
                    
                    stock_data = {
                        "count": len(stocks),
                        "stocks": [
                            {
                                "name": stock['name'],
                                "rank": idx + 1,
                                "sector": stock['sector'],
                                "ticker": stock['symbol'],
                                "exchange": stock['primary_exchange'] or 'Unknown',
                                "industry": stock['industry'] or 'Unknown',
                                "market_cap": float(stock['market_cap']),
                                "market": stock['market'] or 'Unknown'
                            }
                            for idx, stock in enumerate(stocks)
                        ]
                    }
                    
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, ('stock_universe', 'sector_leaders', sector_key, json.dumps(stock_data), self.environment))
                    
                    created_count += 1
                    logger.info(f"🏢 Created sector leaders for {sector}: {len(stocks)} stocks")
        
        return created_count
    
    def _create_market_leader_entries(self) -> int:
        """Create market leader entries (top 10, 50, 100, 250, 500)."""
        created_count = 0
        leader_counts = [10, 50, 100, 250, 500]
        
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for count in leader_counts:
                cursor.execute("""
                    SELECT symbol, name, market_cap, primary_exchange, market
                    FROM symbols
                    WHERE active = true
                      AND type = 'CS'
                      AND market_cap IS NOT NULL
                    ORDER BY market_cap DESC
                    LIMIT %s
                """, (count,))
                
                stocks = cursor.fetchall()
                
                if stocks:
                    key_name = f"top_{count}_stocks" if count == 10 else f"top_{count}"
                    
                    stock_data = {
                        "count": len(stocks),
                        "stocks": [
                            {
                                "name": stock['name'],
                                "rank": idx + 1,
                                "sector": "Unknown",  # Sector data not available
                                "ticker": stock['symbol'],
                                "exchange": stock['primary_exchange'] or 'Unknown',
                                "industry": "Unknown",  # Industry data not available
                                "market_cap": float(stock['market_cap']),
                                "market": stock['market'] or 'Unknown'
                            }
                            for idx, stock in enumerate(stocks)
                        ]
                    }
                    
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, ('stock_universe', 'market_leaders', key_name, json.dumps(stock_data), self.environment))
                    
                    created_count += 1
                    logger.info(f"📈 Created market leaders top {count}: {len(stocks)} stocks")
        
        return created_count
    
    def _create_theme_entries(self) -> int:
        """Create theme entries."""
        created_count = 0
        
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for theme_name, core_tickers in self.theme_definitions.items():
                # Get stocks for this theme that exist in our database
                cursor.execute("""
                    SELECT symbol
                    FROM symbols
                    WHERE symbol = ANY(%s)
                      AND active = true
                      AND type = 'CS'
                    ORDER BY symbol
                """, (core_tickers,))
                
                available_tickers = [row['symbol'] for row in cursor.fetchall()]
                
                if available_tickers:
                    # Create theme entry (simple ticker array format)
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, ('themes', theme_name.title(), 'list', json.dumps(available_tickers), self.environment))
                    
                    # Also create stock_universe theme entry for consistency
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, ('stock_universe', 'themes', theme_name, json.dumps(available_tickers), self.environment))
                    
                    created_count += 2
                    logger.info(f"🎯 Created theme {theme_name}: {len(available_tickers)} stocks")
        
        return created_count
    
    def _create_industry_entries(self) -> int:
        """Create industry group entries - NOW WITH REAL DATA!"""
        created_count = 0
        
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get top industries by stock count (limit to most significant industries)
            cursor.execute("""
                SELECT industry, sector, COUNT(*) as stock_count
                FROM symbols
                WHERE industry IS NOT NULL 
                  AND industry != 'Unknown'
                  AND active = true
                  AND type = 'CS'
                  AND market_cap IS NOT NULL
                GROUP BY industry, sector
                HAVING COUNT(*) >= 3  -- Only industries with at least 3 stocks
                ORDER BY COUNT(*) DESC
                LIMIT 20  -- Top 20 industries by stock count
            """)
            
            industries = cursor.fetchall()
            logger.info(f"🏭 Found {len(industries)} significant industries with classified stocks")
            
            for industry_info in industries:
                industry = industry_info['industry']
                sector = industry_info['sector']
                
                # Get top 15 stocks by market cap for this industry
                cursor.execute("""
                    SELECT symbol, name, market_cap, sector, industry, primary_exchange, market
                    FROM symbols
                    WHERE industry = %s
                      AND active = true
                      AND type = 'CS'
                      AND market_cap IS NOT NULL
                    ORDER BY market_cap DESC
                    LIMIT 15
                """, (industry,))
                
                stocks = cursor.fetchall()
                
                if stocks:
                    industry_key = f"{industry.lower().replace(' ', '_').replace('&', 'and')}"
                    
                    stock_data = {
                        "count": len(stocks),
                        "sector": sector,
                        "stocks": [
                            {
                                "name": stock['name'],
                                "rank": idx + 1,
                                "sector": stock['sector'],
                                "ticker": stock['symbol'],
                                "exchange": stock['primary_exchange'] or 'Unknown',
                                "industry": stock['industry'],
                                "market_cap": float(stock['market_cap']),
                                "market": stock['market'] or 'Unknown'
                            }
                            for idx, stock in enumerate(stocks)
                        ]
                    }
                    
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, ('stock_universe', 'industry', industry_key, json.dumps(stock_data), self.environment))
                    
                    created_count += 1
                    logger.info(f"🏭 Created industry group {industry} ({sector}): {len(stocks)} stocks")
        
        return created_count
    
    def _create_etf_entries(self) -> int:
        """Create ETF universe entries with proper categorization."""
        created_count = 0
        
        # Define ETF categories with smart filtering patterns
        etf_categories = {
            'etf_broad_market': {
                'name': 'Broad Market ETFs',
                'patterns': ['Total Stock Market', 'Total Market', 'S&P 500', 'Russell', 'SPDR', 'Core'],
                'exclude': ['Bond', 'International', 'Emerging', 'Value', 'Growth', 'Technology', 'Sector']
            },
            'etf_growth': {
                'name': 'Growth ETFs', 
                'patterns': ['Growth'],
                'exclude': ['Bond', 'International']
            },
            'etf_value': {
                'name': 'Value ETFs',
                'patterns': ['Value'],
                'exclude': ['Bond', 'International']
            },
            'etf_technology': {
                'name': 'Technology ETFs',
                'patterns': ['Technology', 'Information Technology', 'Tech'],
                'exclude': ['Bond']
            },
            'etf_bonds': {
                'name': 'Bond ETFs',
                'patterns': ['Bond', 'Aggregate'],
                'exclude': []
            },
            'etf_international': {
                'name': 'International ETFs',
                'patterns': ['International', 'Emerging Markets', 'EAFE', 'Developed Markets'],
                'exclude': ['Bond']
            },
            'etf_factor': {
                'name': 'Factor ETFs',
                'patterns': ['Factor', 'Momentum', 'Quality', 'Min Vol', 'Low Vol'],
                'exclude': []
            },
            'etf_all': {
                'name': 'All ETFs',
                'patterns': [],  # No filtering - all ETFs
                'exclude': []
            }
        }
        
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for key, config in etf_categories.items():
                name = config['name']
                patterns = config['patterns']
                exclude_patterns = config['exclude']
                
                if key == 'etf_all':
                    # Special case: get all ETFs
                    cursor.execute("""
                        SELECT symbol, name as etf_name, etf_type, issuer
                        FROM symbols
                        WHERE type = 'ETF'
                          AND active = true
                        ORDER BY symbol
                    """)
                else:
                    # Build WHERE clause for pattern matching
                    where_conditions = []
                    params = []
                    
                    if patterns:
                        # Include patterns (OR logic)
                        pattern_conditions = []
                        for pattern in patterns:
                            pattern_conditions.append("name ILIKE %s")
                            params.append(f'%{pattern}%')
                        where_conditions.append(f"({' OR '.join(pattern_conditions)})")
                    
                    if exclude_patterns:
                        # Exclude patterns (AND NOT logic)
                        for exclude_pattern in exclude_patterns:
                            where_conditions.append("name NOT ILIKE %s")
                            params.append(f'%{exclude_pattern}%')
                    
                    # Build final query
                    base_query = """
                        SELECT symbol, name as etf_name, etf_type, issuer
                        FROM symbols
                        WHERE type = 'ETF'
                          AND active = true
                    """
                    
                    if where_conditions:
                        final_query = f"{base_query} AND {' AND '.join(where_conditions)} ORDER BY symbol"
                    else:
                        final_query = f"{base_query} ORDER BY symbol"
                    
                    cursor.execute(final_query, params)
                
                etf_rows = cursor.fetchall()
                
                if etf_rows:
                    # Create both simple ticker list and detailed metadata
                    etf_tickers = [row['symbol'] for row in etf_rows]
                    
                    etf_detailed = {
                        "count": len(etf_rows),
                        "etfs": [
                            {
                                "symbol": row['symbol'],
                                "name": row['etf_name'],
                                "etf_type": row['etf_type'] or 'ETF',
                                "issuer": row['issuer'] or 'Unknown'
                            }
                            for row in etf_rows
                        ]
                    }
                    
                    # Insert simple ticker list
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, ('etf_universe', name, key, json.dumps(etf_tickers), self.environment))
                    
                    # Insert detailed metadata
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, ('etf_universe', name, f"{key}_detailed", json.dumps(etf_detailed), self.environment))
                    
                    created_count += 2
                    logger.info(f"📊 Created ETF category {name}: {len(etf_tickers)} ETFs ({etf_tickers})")
        
        return created_count
    
    def _create_complete_entries(self) -> int:
        """Create complete universe entries (separate stocks/ETFs, performance optimized)."""
        created_count = 0
        
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Create complete stocks entries
            created_count += self._create_complete_stocks_entries(cursor)
            
            # Create complete ETF entries  
            created_count += self._create_complete_etf_entries(cursor)
        
        return created_count
    
    def _create_complete_stocks_entries(self, cursor) -> int:
        """Create complete stock universe entries."""
        created_count = 0
        
        # Get all active stocks
        cursor.execute("""
            SELECT symbol, name, market_cap, primary_exchange, market
            FROM symbols
            WHERE active = true
              AND type = 'CS'
              AND market_cap IS NOT NULL
            ORDER BY market_cap DESC
        """)
        
        all_stocks = cursor.fetchall()
        
        if all_stocks:
            # 1. Top N stocks with full metadata (from configuration)
            limit = int(self.complete_limits.get('stocks_full_metadata_limit', 1000))
            top_limited = all_stocks[:limit] if len(all_stocks) > limit else all_stocks
            
            stock_data_limited = {
                "count": len(top_limited),
                "stocks": [
                    {
                        "name": stock['name'],
                        "rank": idx + 1,
                        "sector": "Unknown",  # Sector data not available
                        "ticker": stock['symbol'],
                        "exchange": stock['primary_exchange'] or 'Unknown',
                        "industry": "Unknown",  # Industry data not available
                        "market_cap": float(stock['market_cap']),
                        "market": stock['market'] or 'Unknown'
                    }
                    for idx, stock in enumerate(top_limited)
                ]
            }
            
            cursor.execute("""
                INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, ('stock_universe', 'complete', f'top_{limit}', json.dumps(stock_data_limited), self.environment))
            
            created_count += 1
            logger.info(f"📊 Created complete stocks top {limit}: {len(top_limited)} stocks")
            
            # 2. All stocks as simple ticker array (performance optimized)
            all_tickers = [stock['symbol'] for stock in all_stocks]
            
            cursor.execute("""
                INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, ('stock_universe', 'complete', 'all_stocks', json.dumps(all_tickers), self.environment))
            
            created_count += 1
            logger.info(f"🌍 Created complete stocks ticker list: {len(all_tickers)} stocks")
        
        return created_count
    
    def _create_complete_etf_entries(self, cursor) -> int:
        """Create complete ETF universe entries."""
        created_count = 0
        
        # Get all active ETFs
        cursor.execute("""
            SELECT symbol, name, market_cap, etf_type, issuer, primary_exchange
            FROM symbols
            WHERE active = true
              AND type = 'ETF'
            ORDER BY COALESCE(market_cap, aum_millions * 1000000, 0) DESC
        """)
        
        all_etfs = cursor.fetchall()
        
        if all_etfs:
            # 1. Top N ETFs with full metadata (from configuration)
            limit = int(self.complete_limits.get('etfs_full_metadata_limit', 100))
            top_limited = all_etfs[:limit] if len(all_etfs) > limit else all_etfs
            
            etf_data_limited = {
                "count": len(top_limited),
                "etfs": [
                    {
                        "name": etf['name'],
                        "rank": idx + 1,
                        "ticker": etf['symbol'],
                        "etf_type": etf['etf_type'] or 'ETF',
                        "issuer": etf['issuer'] or 'Unknown',
                        "exchange": etf['primary_exchange'] or 'Unknown',
                        "market_cap": float(etf['market_cap']) if etf['market_cap'] else 0.0
                    }
                    for idx, etf in enumerate(top_limited)
                ]
            }
            
            cursor.execute("""
                INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, ('etf_universe', 'complete', f'top_{limit}', json.dumps(etf_data_limited), self.environment))
            
            created_count += 1
            logger.info(f"📊 Created complete ETFs top {limit}: {len(top_limited)} ETFs")
            
            # 2. All ETFs as simple ticker array (performance optimized)
            all_etf_tickers = [etf['symbol'] for etf in all_etfs]
            
            cursor.execute("""
                INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, ('etf_universe', 'complete', 'all_etfs', json.dumps(all_etf_tickers), self.environment))
            
            created_count += 1
            logger.info(f"🏛️ Created complete ETF ticker list: {len(all_etf_tickers)} ETFs")
        
        return created_count
    
    def _create_stats_entries(self) -> int:
        """Create stock statistics summary."""
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get summary statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_stocks,
                    SUM(market_cap) as total_market_cap,
                    AVG(market_cap) as average_market_cap,
                    COUNT(DISTINCT primary_exchange) as unique_exchanges,
                    COUNT(DISTINCT market) as unique_markets
                FROM symbols
                WHERE active = true
                  AND type = 'CS'
                  AND market_cap IS NOT NULL
            """)
            
            stats = cursor.fetchone()
            
            if stats:
                overview_data = {
                    "overview": {
                        "total_stocks": stats['total_stocks'],
                        "unique_exchanges": stats['unique_exchanges'],
                        "unique_markets": stats['unique_markets'],
                        "total_market_cap": float(stats['total_market_cap']) if stats['total_market_cap'] else 0.0,
                        "average_market_cap": float(stats['average_market_cap']) if stats['average_market_cap'] else 0.0,
                        "last_updated": self.sync_timestamp.isoformat(),
                        "note": "Sector and industry data not available in current symbols table structure"
                    }
                }
                
                cursor.execute("""
                    INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, ('stock_stats', 'universe', 'summary', json.dumps(overview_data), self.environment))
                
                logger.info(f"📊 Created stock statistics summary")
                return 1
        
        return 0
    
    def _create_combo_test_entries(self) -> int:
        """Create combo test universe (stocks + ETFs) for comprehensive testing."""
        created_count = 0
        
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get top 50 stocks by market cap
            cursor.execute("""
                SELECT symbol, name, market_cap, sector, industry, primary_exchange, market
                FROM symbols
                WHERE active = true
                  AND type = 'CS'
                  AND market_cap IS NOT NULL
                ORDER BY market_cap DESC
                LIMIT 50
            """)
            
            stock_rows = cursor.fetchall()
            
            # Define essential ETFs for testing - comprehensive market coverage
            essential_etfs = [
                # Broad Market Indices
                'SPY',   # S&P 500
                'QQQ',   # NASDAQ 100
                'IWM',   # Russell 2000
                'VTI',   # Total Stock Market
                
                # Style/Factor ETFs
                'VUG',   # Growth
                'VTV',   # Value
                'MTUM',  # Momentum
                
                # Technology Focus
                'VGT',   # Vanguard Technology
                'XLK',   # Technology Select Sector
                
                # Sector ETFs
                'XLF',   # Financial
                'XLV',   # Healthcare
                'XLE',   # Energy
                'XLI',   # Industrial
                'XLP',   # Consumer Staples
                'XLY',   # Consumer Discretionary
                
                # Bonds
                'AGG',   # Core Bonds
                'BND',   # Total Bond Market
                
                # International
                'VEA',   # Developed Markets
                'EEM',   # Emerging Markets
                'IEFA'   # Core EAFE
            ]
            
            # Get ETF details for the essential ETFs
            placeholders = ','.join(['%s'] * len(essential_etfs))
            cursor.execute(f"""
                SELECT symbol, name as etf_name, etf_type, issuer, primary_exchange, market
                FROM symbols
                WHERE type = 'ETF'
                  AND active = true
                  AND symbol IN ({placeholders})
                ORDER BY symbol
            """, essential_etfs)
            
            etf_rows = cursor.fetchall()
            
            if stock_rows and etf_rows:
                # Create combined symbol list for simple access
                stock_symbols = [row['symbol'] for row in stock_rows]
                etf_symbols = [row['symbol'] for row in etf_rows]
                all_symbols = stock_symbols + etf_symbols
                
                # Create detailed combo data structure
                combo_detailed = {
                    "count": len(all_symbols),
                    "description": "Comprehensive test universe: Top 50 stocks + essential ETFs for market coverage",
                    "composition": {
                        "stocks": len(stock_symbols),
                        "etfs": len(etf_symbols)
                    },
                    "stocks": [
                        {
                            "name": stock['name'],
                            "rank": idx + 1,
                            "sector": stock['sector'] or 'Unknown',
                            "ticker": stock['symbol'],
                            "exchange": stock['primary_exchange'] or 'Unknown',
                            "industry": stock['industry'] or 'Unknown',
                            "market_cap": float(stock['market_cap']),
                            "market": stock['market'] or 'Unknown',
                            "type": "stock"
                        }
                        for idx, stock in enumerate(stock_rows)
                    ],
                    "etfs": [
                        {
                            "name": etf['etf_name'],
                            "ticker": etf['symbol'],
                            "etf_type": etf['etf_type'] or 'ETF',
                            "issuer": etf['issuer'] or 'Unknown',
                            "exchange": etf['primary_exchange'] or 'Unknown',
                            "market": etf['market'] or 'Unknown',
                            "type": "etf"
                        }
                        for etf in etf_rows
                    ]
                }
                
                # Insert simple symbol list version
                cursor.execute("""
                    INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, ('stock_etf_combo', 'stock_etf_test', 'combo_test', json.dumps(all_symbols), self.environment))
                
                # Insert detailed version with full metadata
                cursor.execute("""
                    INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, ('stock_etf_combo', 'stock_etf_test', 'combo_test_detailed', json.dumps(combo_detailed), self.environment))
                
                created_count = 2
                logger.info(f"🧪 Created combo test universe: {len(stock_symbols)} stocks + {len(etf_symbols)} ETFs = {len(all_symbols)} total symbols")
                logger.info(f"🧪 ETFs included: {etf_symbols}")
        
        return created_count
    
    def _publish_rebuild_notifications(self, stats: Dict[str, int]) -> int:
        """Publish Redis notifications about cache rebuild."""
        if not self.redis_client:
            return 0
            
        try:
            notification = {
                'event': 'cache_rebuild_completed',
                'timestamp': self.sync_timestamp.isoformat(),
                'stats': stats,
                'source': 'CacheEntriesSynchronizer'
            }
            
            # Publish to Redis channels
            channels = ['cache_updates', 'universe_updates', 'admin_notifications']
            published = 0
            
            for channel in channels:
                self.redis_client.publish(channel, json.dumps(notification))
                published += 1
            
            logger.info(f"📢 Published rebuild notifications to {published} Redis channels")
            return published
            
        except Exception as e:
            logger.error(f"❌ Failed to publish Redis notifications: {e}")
            return 0

def main():
    """Standalone execution for cache rebuild job."""
    synchronizer = CacheEntriesSynchronizer()
    
    try:
        stats = synchronizer.rebuild_stock_cache_entries()
        print(f"✅ Cache rebuild completed: {stats}")
        return 0
    except Exception as e:
        print(f"❌ Cache rebuild failed: {e}")
        return 1

if __name__ == '__main__':
    exit(main())