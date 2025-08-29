"""
Historical Data Loader for TickStock.ai
Loads historical OHLCV data from Polygon.io API into TimescaleDB.

This module provides selective data loading with:
- Batch processing by date ranges
- Rate limiting and API quota management  
- Symbol-by-symbol loading with progress tracking
- Data validation and duplicate handling
- Flexible timeframe support (daily, 1min, etc.)

Usage:
    python -m src.data.historical_loader --symbols AAPL,MSFT,NVDA --years 1 --timespan day
"""

import os
import sys

# Load environment variables from .env file first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not available, continue without it

# Import other standard libraries
import time
import argparse
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

# Import third-party libraries
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PolygonHistoricalLoader:
    """Loads historical market data from Polygon.io API"""
    
    def __init__(self, api_key: str = None, database_uri: str = None):
        """
        Initialize historical data loader.
        
        Args:
            api_key: Polygon.io API key (defaults to env POLYGON_API_KEY)
            database_uri: Database connection string (defaults to env DATABASE_URI)
        """
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        self.database_uri = database_uri or os.getenv('DATABASE_URI')
        
        # API key only required for data fetching, not for summary/database operations
        if not self.database_uri:
            raise ValueError("DATABASE_URI environment variable or database_uri parameter required")
            
        self.base_url = "https://api.polygon.io"
        self.rate_limit_delay = 12  # 5 calls per minute = 12 sec between calls
        self.session = requests.Session()
        self.batch_size = 1000  # Records per database insert
        
        # Connection will be established per operation
        self.conn = None
        
        if self.api_key:
            logger.info(f"HISTORICAL-LOADER: Initialized with API key: {'***' + self.api_key[-4:]}")
        else:
            logger.info("HISTORICAL-LOADER: Initialized without API key (database operations only)")
        
    def _connect_db(self):
        """Establish database connection."""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(self.database_uri)
            logger.info("HISTORICAL-LOADER: Database connected")
            
    def _close_db(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("HISTORICAL-LOADER: Database connection closed")
            
    def _make_api_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make rate-limited API request to Polygon.io.
        
        Args:
            endpoint: API endpoint (e.g., '/v2/aggs/ticker/AAPL/range/1/day/2023-01-01/2024-01-01')
            params: Additional query parameters
            
        Returns:
            JSON response as dictionary
        """
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY required for API requests")
            
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params['apikey'] = self.api_key
        
        try:
            logger.debug(f"HISTORICAL-LOADER: API request: {endpoint}")
            response = self.session.get(url, params=params, timeout=30)
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("HISTORICAL-LOADER: Rate limited, waiting 60 seconds...")
                time.sleep(60)
                response = self.session.get(url, params=params, timeout=30)
            
            response.raise_for_status()
            data = response.json()
            
            # Respect rate limits proactively
            time.sleep(self.rate_limit_delay)
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HISTORICAL-LOADER: API request failed: {e}")
            raise
            
    def fetch_symbol_metadata(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch symbol metadata from Polygon.io tickers endpoint.
        
        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            
        Returns:
            Dictionary with symbol metadata or None if not found
        """
        endpoint = f"/v3/reference/tickers/{symbol}"
        
        try:
            response = self._make_api_request(endpoint)
            
            if response.get('status') == 'OK' and response.get('results'):
                ticker_data = response['results']
                
                # Map API response to our schema
                metadata = {
                    'symbol': ticker_data.get('ticker', symbol),
                    'name': ticker_data.get('name', ''),
                    'market': ticker_data.get('market', 'stocks'),
                    'locale': ticker_data.get('locale', 'us'),
                    'currency_name': ticker_data.get('currency_name', 'USD'),
                    'currency_symbol': ticker_data.get('currency_symbol', '$'),
                    'type': ticker_data.get('type', 'CS'),
                    'active': ticker_data.get('active', True),
                    'cik': ticker_data.get('cik'),
                    'composite_figi': ticker_data.get('composite_figi'),
                    'share_class_figi': ticker_data.get('share_class_figi'),
                    'market_cap': ticker_data.get('market_cap'),
                    'weighted_shares_outstanding': ticker_data.get('weighted_shares_outstanding'),
                    'exchange': ticker_data.get('primary_exchange', ''),
                    'last_updated_utc': ticker_data.get('last_updated_utc')
                }
                
                logger.debug(f"HISTORICAL-LOADER: Fetched metadata for {symbol}: {metadata['name']}")
                return metadata
            else:
                logger.warning(f"HISTORICAL-LOADER: No metadata found for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to fetch metadata for {symbol}: {e}")
            return None
    
    def ensure_symbol_exists(self, symbol: str) -> bool:
        """
        Ensure symbol exists in symbols table, create or update with latest metadata.
        Always fetches fresh metadata from Polygon.io to capture any updates.
        
        Args:
            symbol: Stock ticker to check/create/update
            
        Returns:
            True if symbol was processed successfully
        """
        self._connect_db()
        
        try:
            # Always fetch fresh metadata from API
            logger.info(f"HISTORICAL-LOADER: Fetching/updating symbol metadata for {symbol}")
            metadata = self.fetch_symbol_metadata(symbol)
            
            if not metadata:
                # Create basic record if metadata fetch fails
                metadata = {
                    'symbol': symbol,
                    'name': '',
                    'market': 'stocks',
                    'locale': 'us',
                    'currency_name': 'USD',
                    'currency_symbol': '$',
                    'type': 'CS',
                    'active': True,
                    'cik': None,
                    'composite_figi': None,
                    'share_class_figi': None,
                    'market_cap': None,
                    'weighted_shares_outstanding': None,
                    'exchange': '',
                    'last_updated_utc': datetime.utcnow()
                }
                logger.warning(f"HISTORICAL-LOADER: Using default metadata for {symbol}")
            
            # Upsert symbol record (insert or update)
            with self.conn.cursor() as cursor:
                insert_sql = """
                INSERT INTO symbols (
                    symbol, name, exchange, market, locale, currency_name, 
                    currency_symbol, type, active, cik, composite_figi, 
                    share_class_figi, market_cap, weighted_shares_outstanding, 
                    last_updated_utc, last_updated
                ) VALUES (
                    %(symbol)s, %(name)s, %(exchange)s, %(market)s, %(locale)s, 
                    %(currency_name)s, %(currency_symbol)s, %(type)s, %(active)s, 
                    %(cik)s, %(composite_figi)s, %(share_class_figi)s, 
                    %(market_cap)s, %(weighted_shares_outstanding)s, 
                    %(last_updated_utc)s, CURRENT_TIMESTAMP
                ) ON CONFLICT (symbol) DO UPDATE SET
                    name = EXCLUDED.name,
                    exchange = EXCLUDED.exchange,
                    market = EXCLUDED.market,
                    locale = EXCLUDED.locale,
                    currency_name = EXCLUDED.currency_name,
                    currency_symbol = EXCLUDED.currency_symbol,
                    type = EXCLUDED.type,
                    active = EXCLUDED.active,
                    cik = EXCLUDED.cik,
                    composite_figi = EXCLUDED.composite_figi,
                    share_class_figi = EXCLUDED.share_class_figi,
                    market_cap = EXCLUDED.market_cap,
                    weighted_shares_outstanding = EXCLUDED.weighted_shares_outstanding,
                    last_updated_utc = EXCLUDED.last_updated_utc,
                    last_updated = CURRENT_TIMESTAMP
                """
                
                cursor.execute(insert_sql, metadata)
                self.conn.commit()
                
                # Log successful upsert (ON CONFLICT handles insert vs update)
                logger.info(f"HISTORICAL-LOADER: ✓ Upserted symbol metadata for {symbol}")
                return True
                
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to ensure symbol {symbol} exists: {e}")
            logger.error(f"HISTORICAL-LOADER: Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"HISTORICAL-LOADER: Traceback: {traceback.format_exc()}")
            if self.conn:
                self.conn.rollback()
            return False
            
    def _create_tables_if_needed(self):
        """Create historical data tables if they don't exist."""
        self._connect_db()
        
        # Table creation SQL
        daily_table_sql = """
        CREATE TABLE IF NOT EXISTS ohlcv_daily (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            date DATE NOT NULL,
            open DECIMAL(12,4),
            high DECIMAL(12,4),
            low DECIMAL(12,4),
            close DECIMAL(12,4),
            volume BIGINT,
            transactions INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        );
        
        -- Create hypertable for TimescaleDB if available
        SELECT create_hypertable('ohlcv_daily', 'date', if_not_exists => TRUE);
        """
        
        minute_table_sql = """
        CREATE TABLE IF NOT EXISTS ohlcv_1min (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DECIMAL(12,4),
            high DECIMAL(12,4),
            low DECIMAL(12,4),
            close DECIMAL(12,4),
            volume BIGINT,
            transactions INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timestamp)
        );
        
        -- Create hypertable for TimescaleDB if available
        SELECT create_hypertable('ohlcv_1min', 'timestamp', if_not_exists => TRUE);
        """
        
        try:
            with self.conn.cursor() as cursor:
                # Try to create daily table
                try:
                    cursor.execute(daily_table_sql)
                    logger.info("HISTORICAL-LOADER: ohlcv_daily table ready")
                except Exception as e:
                    # Fallback without hypertable creation
                    cursor.execute("ROLLBACK")
                    cursor.execute(daily_table_sql.split('SELECT create_hypertable')[0])
                    logger.warning(f"HISTORICAL-LOADER: Created ohlcv_daily without hypertable: {e}")
                
                # Try to create minute table
                try:
                    cursor.execute(minute_table_sql)
                    logger.info("HISTORICAL-LOADER: ohlcv_1min table ready")
                except Exception as e:
                    # Fallback without hypertable creation
                    cursor.execute("ROLLBACK")
                    cursor.execute(minute_table_sql.split('SELECT create_hypertable')[0])
                    logger.warning(f"HISTORICAL-LOADER: Created ohlcv_1min without hypertable: {e}")
                    
                self.conn.commit()
                
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to create tables: {e}")
            self.conn.rollback()
            raise
    
    def fetch_symbol_data(self, symbol: str, start_date: str, end_date: str, 
                         timespan: str = 'day', multiplier: int = 1) -> pd.DataFrame:
        """
        Fetch historical data for a single symbol.
        
        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            timespan: 'day', 'minute', 'hour' etc.
            multiplier: Time multiplier (e.g., 1 for 1-day, 5 for 5-minute)
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"HISTORICAL-LOADER: Fetching {symbol} data from {start_date} to {end_date}")
        
        all_data = []
        current_start = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Process in chunks to respect API limits
        while current_start < end_dt:
            # For daily data, process yearly chunks; for minute data, monthly chunks
            if timespan == 'day':
                current_end = min(current_start + timedelta(days=365), end_dt)
            else:
                current_end = min(current_start + timedelta(days=30), end_dt)
            
            chunk_start = current_start.strftime('%Y-%m-%d')
            chunk_end = current_end.strftime('%Y-%m-%d')
            
            endpoint = f"/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{chunk_start}/{chunk_end}"
            
            try:
                response = self._make_api_request(endpoint, {
                    'adjusted': 'true',
                    'sort': 'asc',
                    'limit': 50000
                })
                
                if response.get('status') == 'OK' and response.get('results'):
                    for result in response['results']:
                        record = {
                            'symbol': symbol,
                            'timestamp': pd.to_datetime(result['t'], unit='ms'),
                            'open': result['o'],
                            'high': result['h'], 
                            'low': result['l'],
                            'close': result['c'],
                            'volume': result['v'],
                            'transactions': result.get('n', None)
                        }
                        all_data.append(record)
                        
                    logger.info(f"HISTORICAL-LOADER: {symbol} chunk {chunk_start} to {chunk_end}: {len(response['results'])} records")
                else:
                    logger.warning(f"HISTORICAL-LOADER: No data for {symbol} {chunk_start}-{chunk_end}")
                    
            except Exception as e:
                logger.error(f"HISTORICAL-LOADER: Failed to fetch {symbol} {chunk_start}-{chunk_end}: {e}")
                
            current_start = current_end + timedelta(days=1)
            
        df = pd.DataFrame(all_data)
        logger.info(f"HISTORICAL-LOADER: Fetched {len(df)} total records for {symbol}")
        return df
    
    def save_data_to_db(self, df: pd.DataFrame, timespan: str = 'day'):
        """
        Save DataFrame to appropriate database table.
        
        Args:
            df: DataFrame with OHLCV data
            timespan: 'day' or 'minute' to determine target table
        """
        if df.empty:
            logger.warning("HISTORICAL-LOADER: No data to save")
            return
            
        self._connect_db()
        
        table_name = 'ohlcv_daily' if timespan == 'day' else 'ohlcv_1min'
        date_col = 'date' if timespan == 'day' else 'timestamp'
        
        # Prepare data
        if timespan == 'day':
            df['date'] = df['timestamp'].dt.date
            df = df.drop('timestamp', axis=1)
        
        # Remove transactions column if present (not in existing schema)
        if 'transactions' in df.columns:
            df = df.drop('transactions', axis=1)
        
        # Insert with ON CONFLICT handling for duplicates
        insert_sql = f"""
        INSERT INTO {table_name} (symbol, {date_col}, open, high, low, close, volume)
        VALUES (%(symbol)s, %({date_col})s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
        ON CONFLICT (symbol, {date_col}) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            created_at = CURRENT_TIMESTAMP
        """
        
        try:
            with self.conn.cursor() as cursor:
                # Insert in batches
                records = df.to_dict('records')
                for i in range(0, len(records), self.batch_size):
                    batch = records[i:i + self.batch_size]
                    cursor.executemany(insert_sql, batch)
                    logger.info(f"HISTORICAL-LOADER: Inserted batch {i//self.batch_size + 1} ({len(batch)} records)")
                
                self.conn.commit()
                logger.info(f"HISTORICAL-LOADER: Successfully saved {len(df)} records to {table_name}")
                
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to save data: {e}")
            self.conn.rollback()
            raise
    
    def load_symbols_from_cache(self, universe_key: str = 'top_50') -> List[str]:
        """
        Load symbols from cache_entries table.
        
        Args:
            universe_key: Cache key (e.g., 'top_50')
            
        Returns:
            List of ticker symbols
        """
        self._connect_db()
        
        query = """
        SELECT value FROM cache_entries 
        WHERE type = 'stock_universe' AND key = %s
        """
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (universe_key,))
                result = cursor.fetchone()
                
                if result and result['value']:
                    stocks = result['value'].get('stocks', [])
                    symbols = [stock['ticker'] for stock in stocks]
                    logger.info(f"HISTORICAL-LOADER: Loaded {len(symbols)} symbols from {universe_key}")
                    return symbols
                else:
                    logger.warning(f"HISTORICAL-LOADER: No symbols found for {universe_key}")
                    return []
                    
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to load symbols: {e}")
            return []
    
    def load_historical_data(self, symbols: List[str], years: int = 1, 
                           timespan: str = 'day', multiplier: int = 1):
        """
        Load historical data for multiple symbols.
        
        Args:
            symbols: List of ticker symbols
            years: Number of years of historical data to load
            timespan: 'day' or 'minute'
            multiplier: Time multiplier
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=int(years * 365))
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"HISTORICAL-LOADER: Starting bulk load for {len(symbols)} symbols")
        logger.info(f"HISTORICAL-LOADER: Date range: {start_str} to {end_str}")
        logger.info(f"HISTORICAL-LOADER: Timespan: {multiplier} {timespan}")
        
        # Create tables if needed
        self._create_tables_if_needed()
        
        successful_loads = 0
        failed_symbols = []
        
        for i, symbol in enumerate(symbols):
            try:
                logger.info(f"HISTORICAL-LOADER: Processing {symbol} ({i+1}/{len(symbols)})")
                
                # Ensure symbol exists in symbols table first
                logger.debug(f"HISTORICAL-LOADER: About to ensure symbol {symbol} exists")
                if not self.ensure_symbol_exists(symbol):
                    logger.error(f"HISTORICAL-LOADER: ✗ {symbol} - failed to create symbol record")
                    failed_symbols.append(symbol)
                    continue
                logger.debug(f"HISTORICAL-LOADER: Symbol {symbol} existence confirmed")
                
                # Fetch data
                df = self.fetch_symbol_data(symbol, start_str, end_str, timespan, multiplier)
                
                if not df.empty:
                    # Save to database
                    self.save_data_to_db(df, timespan)
                    successful_loads += 1
                    logger.info(f"HISTORICAL-LOADER: ✓ {symbol} completed ({len(df)} records)")
                else:
                    logger.warning(f"HISTORICAL-LOADER: ✗ {symbol} - no data received")
                    failed_symbols.append(symbol)
                    
            except Exception as e:
                logger.error(f"HISTORICAL-LOADER: ✗ {symbol} failed: {e}")
                failed_symbols.append(symbol)
                
        logger.info(f"HISTORICAL-LOADER: Bulk load completed")
        logger.info(f"HISTORICAL-LOADER: Successful: {successful_loads}/{len(symbols)}")
        if failed_symbols:
            logger.warning(f"HISTORICAL-LOADER: Failed symbols: {', '.join(failed_symbols)}")
            
    def get_data_summary(self, timespan: str = 'day') -> Dict[str, Any]:
        """Get summary of loaded historical data."""
        self._connect_db()
        
        table_name = 'ohlcv_daily' if timespan == 'day' else 'ohlcv_1min'
        date_col = 'date' if timespan == 'day' else 'timestamp'
        
        query = f"""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT symbol) as unique_symbols,
            MIN({date_col}) as earliest_date,
            MAX({date_col}) as latest_date
        FROM {table_name}
        """
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return dict(result) if result else {}
                
        except Exception as e:
            logger.error(f"HISTORICAL-LOADER: Failed to get summary: {e}")
            return {}
    
    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, 'conn'):
            self._close_db()

def main():
    """CLI entry point for historical data loading."""
    parser = argparse.ArgumentParser(description='Load historical data from Polygon.io')
    parser.add_argument('--symbols', help='Comma-separated list of symbols (e.g., AAPL,MSFT)')
    parser.add_argument('--universe', default='top_50', help='Stock universe key from cache_entries')
    parser.add_argument('--years', type=float, default=1, help='Years of historical data to load')
    parser.add_argument('--timespan', default='day', choices=['day', 'minute'], help='Data timespan')
    parser.add_argument('--multiplier', type=int, default=1, help='Time multiplier')
    parser.add_argument('--api-key', help='Polygon.io API key (overrides env var)')
    parser.add_argument('--database-uri', help='Database URI (overrides env var)')
    parser.add_argument('--summary', action='store_true', help='Show data summary only')
    
    args = parser.parse_args()
    
    try:
        # Initialize loader
        loader = PolygonHistoricalLoader(
            api_key=args.api_key,
            database_uri=args.database_uri
        )
        
        if args.summary:
            # Show summary
            summary = loader.get_data_summary(args.timespan)
            print("\nHistorical Data Summary:")
            print(f"Table: ohlcv_{args.timespan}")
            for key, value in summary.items():
                print(f"  {key}: {value}")
            return
        
        # Determine symbols to load
        if args.symbols:
            symbols = [s.strip().upper() for s in args.symbols.split(',')]
        else:
            symbols = loader.load_symbols_from_cache(args.universe)
            
        if not symbols:
            logger.error("No symbols to load. Specify --symbols or ensure cache_entries has data.")
            return
            
        # Load historical data
        loader.load_historical_data(
            symbols=symbols,
            years=args.years,
            timespan=args.timespan,
            multiplier=args.multiplier
        )
        
        # Show final summary
        summary = loader.get_data_summary(args.timespan)
        print("\nLoad Complete - Data Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        logger.error(f"HISTORICAL-LOADER: Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()