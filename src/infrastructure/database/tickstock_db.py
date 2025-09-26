"""
TickStockPL Database Connection Service
Handles read-only connections to shared 'tickstock' TimescaleDB for UI queries.

Sprint 10 Phase 1: Database Integration
- Read-only connection pool to shared 'tickstock' database
- Simple UI queries for dropdowns and basic stats
- Connection health monitoring
"""

import logging
import time
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
import psycopg2
from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)

class TickStockDatabase:
    """Read-only database connection service for TickStockPL integration."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize database connection to shared 'tickstock' database."""
        self.config = config
        self.engine = None
        self.connection_url = self._build_connection_url()
        self._initialize_engine()
        
    def _build_connection_url(self) -> str:
        """Build database connection URL for shared 'tickstock' database."""
        config = get_config()

        # First try to use DATABASE_URI from config (matches .env file)
        database_uri = config.get('DATABASE_URI')
        if database_uri:
            logger.info(f"TICKSTOCK-DB: Using DATABASE_URI from config")
            return database_uri

        # Fallback to individual config variables
        db_host = config.get('TICKSTOCK_DB_HOST', 'localhost')
        db_port = config.get('TICKSTOCK_DB_PORT', 5432)
        db_name = 'tickstock'  # Fixed database name for shared TickStockPL database
        db_user = config.get('TICKSTOCK_DB_USER', 'app_readwrite')
        db_password = config.get('TICKSTOCK_DB_PASSWORD', 'password')

        connection_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        logger.info(f"TICKSTOCK-DB: Using individual config vars - connecting to '{db_name}' at {db_host}:{db_port}")
        return connection_url
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine with read-only connection pool."""
        try:
            # Create read-only connection pool
            self.engine = create_engine(
                self.connection_url,
                poolclass=QueuePool,
                pool_size=5,           # Small pool for UI queries
                max_overflow=2,        # Limited overflow for read-only operations
                pool_timeout=10,       # Quick timeout for UI responsiveness
                pool_recycle=3600,     # Recycle connections hourly
                echo=False,            # Set to True for SQL debugging
                connect_args={
                    'connect_timeout': 5,
                    'application_name': 'TickStockAppV2_ReadOnly'
                }
            )
            
            # Test connection
            self._test_connection()
            logger.info("TICKSTOCK-DB: Read-only connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"TICKSTOCK-DB: Failed to initialize engine: {e}")
            self.engine = None
            raise
    
    def _test_connection(self):
        """Test database connection and basic query."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                if test_value != 1:
                    raise ValueError("Connection test failed")
                    
                # Test TimescaleDB extension
                result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'"))
                timescale_ext = result.scalar()
                if timescale_ext:
                    logger.info("TICKSTOCK-DB: TimescaleDB extension detected")
                else:
                    logger.warning("TICKSTOCK-DB: TimescaleDB extension not found")
                    
        except Exception as e:
            logger.error(f"TICKSTOCK-DB: Connection test failed: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
            
        conn = None
        try:
            conn = self.engine.connect()
            yield conn
        except Exception as e:
            logger.error(f"TICKSTOCK-DB: Connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: list = None) -> List[tuple]:
        """Execute a raw SQL query and return results as list of tuples."""
        try:
            with self.get_connection() as conn:
                if params:
                    # For SQLAlchemy 2.x compatibility, we need to pass parameters correctly
                    # Convert positional parameters to a dict with numbered keys
                    param_dict = {f"param_{i}": param for i, param in enumerate(params)}
                    # Replace %s with numbered parameters in query
                    modified_query = query
                    for i in range(len(params)):
                        modified_query = modified_query.replace('%s', f':param_{i}', 1)
                    result = conn.execute(text(modified_query), param_dict)
                else:
                    result = conn.execute(text(query))
                
                # Fetch all results and convert to list of tuples
                rows = result.fetchall()
                return [tuple(row) for row in rows]
                
        except Exception as e:
            logger.error(f"TICKSTOCK-DB: Query execution failed: {e}")
            logger.error(f"TICKSTOCK-DB: Query: {query}")
            logger.error(f"TICKSTOCK-DB: Params: {params}")
            raise
    
    def get_symbols_for_dropdown(self) -> List[Dict[str, Any]]:
        """Get all active symbols with metadata for UI dropdown population."""
        try:
            with self.get_connection() as conn:
                result = conn.execute(text("""
                    SELECT 
                        symbol, 
                        name, 
                        exchange, 
                        market,
                        type,
                        active
                    FROM symbols 
                    WHERE active = true
                    ORDER BY symbol ASC
                """))
                
                symbols = []
                for row in result:
                    symbols.append({
                        'symbol': row[0],
                        'name': row[1] or '',
                        'exchange': row[2] or '',
                        'market': row[3] or 'stocks',
                        'type': row[4] or 'CS',
                        'active': row[5]
                    })
                
                # Symbol retrieval is normal operation - no debug logging needed
                return symbols
                
        except Exception as e:
            logger.error(f"TICKSTOCK-DB: Failed to get symbols: {e}")
            return []
    
    def get_symbol_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific symbol."""
        try:
            with self.get_connection() as conn:
                result = conn.execute(text("""
                    SELECT 
                        symbol, name, exchange, market, locale, currency_name,
                        currency_symbol, type, active, cik, composite_figi,
                        share_class_figi, market_cap, weighted_shares_outstanding,
                        last_updated_utc, last_updated
                    FROM symbols 
                    WHERE symbol = :symbol
                """), {"symbol": symbol})
                
                row = result.fetchone()
                if row:
                    return {
                        'symbol': row[0],
                        'name': row[1],
                        'exchange': row[2],
                        'market': row[3],
                        'locale': row[4],
                        'currency_name': row[5],
                        'currency_symbol': row[6],
                        'type': row[7],
                        'active': row[8],
                        'cik': row[9],
                        'composite_figi': row[10],
                        'share_class_figi': row[11],
                        'market_cap': row[12],
                        'weighted_shares_outstanding': row[13],
                        'last_updated_utc': row[14].isoformat() if row[14] else None,
                        'last_updated': row[15].isoformat() if row[15] else None
                    }
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"TICKSTOCK-DB: Failed to get symbol details for {symbol}: {e}")
            return None
    
    def get_basic_dashboard_stats(self) -> Dict[str, Any]:
        """Get basic statistics for dashboard display."""
        stats = {
            'symbols_count': 0,
            'active_symbols_count': 0,
            'symbols_by_market': {},
            'events_count': 0,
            'latest_event_time': None,
            'database_status': 'connected'
        }
        
        try:
            with self.get_connection() as conn:
                # Count symbols
                result = conn.execute(text("SELECT COUNT(*) FROM symbols"))
                stats['symbols_count'] = result.scalar() or 0
                
                # Count active symbols
                result = conn.execute(text("SELECT COUNT(*) FROM symbols WHERE active = true"))
                stats['active_symbols_count'] = result.scalar() or 0
                
                # Count symbols by market
                result = conn.execute(text("""
                    SELECT market, COUNT(*) 
                    FROM symbols 
                    WHERE active = true 
                    GROUP BY market 
                    ORDER BY COUNT(*) DESC
                """))
                market_counts = {row[0] or 'unknown': row[1] for row in result}
                stats['symbols_by_market'] = market_counts
                
                # Count events (if table exists)
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM events"))
                    stats['events_count'] = result.scalar() or 0
                    
                    # Get latest event timestamp
                    result = conn.execute(text("""
                        SELECT MAX(created_at) 
                        FROM events 
                        WHERE created_at IS NOT NULL
                    """))
                    latest_time = result.scalar()
                    if latest_time:
                        stats['latest_event_time'] = latest_time.isoformat()
                        
                except SQLAlchemyError:
                    # Events table might not exist yet
                    stats['events_count'] = 0
                    stats['latest_event_time'] = None
                
                # Dashboard stats retrieval is normal operation
                return stats
                
        except Exception as e:
            logger.error(f"TICKSTOCK-DB: Failed to get dashboard stats: {e}")
            stats['database_status'] = 'error'
            return stats
    
    def get_user_alert_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's alert history from events table."""
        try:
            with self.get_connection() as conn:
                result = conn.execute(text("""
                    SELECT 
                        symbol,
                        pattern,
                        confidence,
                        created_at,
                        details
                    FROM events 
                    ORDER BY created_at DESC
                    LIMIT :limit
                """), {"limit": limit})
                
                alerts = []
                for row in result:
                    alerts.append({
                        'symbol': row[0],
                        'pattern': row[1],
                        'confidence': float(row[2]) if row[2] else 0.0,
                        'created_at': row[3].isoformat() if row[3] else None,
                        'details': row[4] or {}
                    })
                
                # Alert retrieval is normal operation
                return alerts
                
        except Exception as e:
            logger.error(f"TICKSTOCK-DB: Failed to get user alerts: {e}")
            return []
    
    def get_pattern_performance(self, pattern_name: str = None) -> List[Dict[str, Any]]:
        """Get pattern performance statistics from events table."""
        try:
            with self.get_connection() as conn:
                if pattern_name:
                    result = conn.execute(text("""
                        SELECT 
                            pattern,
                            COUNT(*) as detection_count,
                            AVG(confidence) as avg_confidence,
                            MAX(confidence) as max_confidence,
                            MIN(confidence) as min_confidence
                        FROM events 
                        WHERE pattern = :pattern_name
                        GROUP BY pattern
                    """), {"pattern_name": pattern_name})
                else:
                    result = conn.execute(text("""
                        SELECT 
                            pattern,
                            COUNT(*) as detection_count,
                            AVG(confidence) as avg_confidence,
                            MAX(confidence) as max_confidence,
                            MIN(confidence) as min_confidence
                        FROM events 
                        GROUP BY pattern
                        ORDER BY detection_count DESC
                    """))
                
                performance_data = []
                for row in result:
                    performance_data.append({
                        'pattern': row[0],
                        'detection_count': int(row[1]),
                        'avg_confidence': float(row[2]) if row[2] else 0.0,
                        'max_confidence': float(row[3]) if row[3] else 0.0,
                        'min_confidence': float(row[4]) if row[4] else 0.0
                    })
                
                # Pattern performance retrieval is normal operation
                return performance_data
                
        except Exception as e:
            logger.error(f"TICKSTOCK-DB: Failed to get pattern performance: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for database connection."""
        health_data = {
            'status': 'healthy',
            'database': 'tickstock',
            'connection_pool': 'inactive',
            'query_performance': None,
            'tables_accessible': [],
            'last_check': time.time()
        }
        
        try:
            if not self.engine:
                health_data['status'] = 'error'
                health_data['error'] = 'Database engine not initialized'
                return health_data
            
            # Check connection pool
            health_data['connection_pool'] = {
                'size': self.engine.pool.size(),
                'checked_in': self.engine.pool.checkedin(),
                'checked_out': self.engine.pool.checkedout(),
                'status': 'active'
            }
            
            # Test query performance
            start_time = time.time()
            with self.get_connection() as conn:
                # Test basic connectivity
                conn.execute(text("SELECT 1"))
                
                # Check table accessibility
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_name IN ('symbols', 'events', 'ohlcv_daily', 'ohlcv_1min', 'ticks')
                    ORDER BY table_name
                """))
                
                accessible_tables = [row[0] for row in result]
                health_data['tables_accessible'] = accessible_tables
                
            query_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            health_data['query_performance'] = round(query_time, 2)
            
            # Determine overall status
            if query_time > 100:  # >100ms is slow for read queries
                health_data['status'] = 'degraded'
            elif not accessible_tables:
                health_data['status'] = 'warning'
                health_data['warning'] = 'No expected tables found'
                
            logger.debug(f"TICKSTOCK-DB: Health check completed: {health_data['status']}")
            return health_data
            
        except Exception as e:
            logger.error(f"TICKSTOCK-DB: Health check failed: {e}")
            health_data['status'] = 'error'
            health_data['error'] = str(e)
            return health_data
    
    def close(self):
        """Close database connections and cleanup."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            logger.info("TICKSTOCK-DB: Database connections closed")