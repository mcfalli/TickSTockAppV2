"""
OHLCV Data Service for fetching price data from TimescaleDB.

Sprint 72: Database Integration
Centralized OHLCV data access with connection pooling and error handling.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy import text

from src.infrastructure.database.tickstock_db import TickStockDatabase
from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)


# Timeframe to table mapping
TIMEFRAME_TABLE_MAP = {
    'daily': 'ohlcv_daily',
    'hourly': 'ohlcv_hourly',
    'intraday': 'ohlcv_1min',
    '1min': 'ohlcv_1min',
    'weekly': 'ohlcv_weekly',
    'monthly': 'ohlcv_monthly',
}


class OHLCVDataService:
    """
    Service for fetching OHLCV data from TimescaleDB.

    Sprint 72: Database Integration
    Provides centralized access to stock price data with connection pooling.
    """

    def __init__(self):
        """Initialize OHLCV data service with database connection."""
        config = get_config()
        self.db = TickStockDatabase(config)

    def get_ohlcv_data(
        self,
        symbol: str,
        timeframe: str = 'daily',
        limit: int = 200,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol from database.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            timeframe: Data timeframe ('daily', 'hourly', 'intraday', '1min', 'weekly', 'monthly')
            limit: Maximum number of bars to fetch (default: 200)
            start_date: Optional start date for data range
            end_date: Optional end date for data range

        Returns:
            DataFrame with columns: [open, high, low, close, volume]
            Indexed by timestamp, sorted ascending (oldest first)

        Raises:
            ValueError: If timeframe is invalid
            RuntimeError: If database query fails

        Examples:
            >>> service = OHLCVDataService()
            >>> df = service.get_ohlcv_data('AAPL', 'daily', limit=200)
            >>> print(df.head())
                             open    high     low   close      volume
            time
            2025-01-01  150.5  152.0  149.0  151.5  1000000
        """
        # Validate timeframe
        if timeframe not in TIMEFRAME_TABLE_MAP:
            raise ValueError(
                f"Invalid timeframe: {timeframe}. "
                f"Supported: {', '.join(TIMEFRAME_TABLE_MAP.keys())}"
            )

        # Get table name
        table_name = TIMEFRAME_TABLE_MAP[timeframe]

        try:
            # Build query
            if start_date and end_date:
                # Date range query
                query = text(f"""
                    SELECT date, open, high, low, close, volume
                    FROM {table_name}
                    WHERE symbol = :symbol
                    AND date >= :start_date
                    AND date <= :end_date
                    ORDER BY date DESC
                    LIMIT :limit
                """)
                params = {
                    'symbol': symbol.upper(),
                    'start_date': start_date,
                    'end_date': end_date,
                    'limit': limit
                }
            elif start_date:
                # Start date only
                query = text(f"""
                    SELECT date, open, high, low, close, volume
                    FROM {table_name}
                    WHERE symbol = :symbol
                    AND date >= :start_date
                    ORDER BY date DESC
                    LIMIT :limit
                """)
                params = {
                    'symbol': symbol.upper(),
                    'start_date': start_date,
                    'limit': limit
                }
            else:
                # Latest N bars
                query = text(f"""
                    SELECT date, open, high, low, close, volume
                    FROM {table_name}
                    WHERE symbol = :symbol
                    ORDER BY date DESC
                    LIMIT :limit
                """)
                params = {
                    'symbol': symbol.upper(),
                    'limit': limit
                }

            # Execute query
            with self.db.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)

            # Check if data exists
            if df.empty:
                logger.warning(f"No data found for symbol {symbol} ({timeframe})")
                return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

            # Set index and sort ascending (oldest first for indicators)
            df = df.set_index('date')
            df = df.sort_index(ascending=True)

            logger.info(f"Fetched {len(df)} bars for {symbol} ({timeframe})")
            return df

        except Exception as e:
            logger.error(f"Database query failed for {symbol} ({timeframe}): {e}")
            raise RuntimeError(f"Failed to fetch OHLCV data: {str(e)}") from e

    def get_latest_ohlcv(
        self,
        symbol: str,
        timeframe: str = 'daily',
    ) -> Optional[pd.Series]:
        """
        Fetch the latest OHLCV bar for a symbol.

        Args:
            symbol: Stock symbol
            timeframe: Data timeframe

        Returns:
            Series with [open, high, low, close, volume] or None if no data

        Examples:
            >>> service = OHLCVDataService()
            >>> latest = service.get_latest_ohlcv('AAPL', 'daily')
            >>> print(f"Latest close: {latest['close']}")
        """
        df = self.get_ohlcv_data(symbol, timeframe, limit=1)
        if df.empty:
            return None
        return df.iloc[-1]

    def validate_symbol_exists(
        self,
        symbol: str,
        timeframe: str = 'daily',
    ) -> bool:
        """
        Check if symbol has data in database.

        Args:
            symbol: Stock symbol
            timeframe: Data timeframe

        Returns:
            True if symbol has data, False otherwise

        Examples:
            >>> service = OHLCVDataService()
            >>> exists = service.validate_symbol_exists('AAPL')
            >>> print(f"AAPL exists: {exists}")
        """
        table_name = TIMEFRAME_TABLE_MAP.get(timeframe, 'stock_prices_1day')

        try:
            query = text(f"""
                SELECT COUNT(*) as count
                FROM {table_name}
                WHERE symbol = :symbol
                LIMIT 1
            """)
            params = {'symbol': symbol.upper()}

            with self.db.get_connection() as conn:
                result = conn.execute(query, params)
                count = result.scalar()

            return count > 0

        except Exception as e:
            logger.error(f"Symbol validation failed for {symbol}: {e}")
            return False

    def get_available_symbols(
        self,
        timeframe: str = 'daily',
        min_bars: int = 100,
    ) -> list[str]:
        """
        Get list of symbols with sufficient data in database.

        Args:
            timeframe: Data timeframe
            min_bars: Minimum number of bars required

        Returns:
            List of symbol strings

        Examples:
            >>> service = OHLCVDataService()
            >>> symbols = service.get_available_symbols('daily', min_bars=200)
            >>> print(f"Found {len(symbols)} symbols with 200+ bars")
        """
        table_name = TIMEFRAME_TABLE_MAP.get(timeframe, 'stock_prices_1day')

        try:
            query = text(f"""
                SELECT symbol, COUNT(*) as bar_count
                FROM {table_name}
                GROUP BY symbol
                HAVING COUNT(*) >= :min_bars
                ORDER BY symbol
            """)
            params = {'min_bars': min_bars}

            with self.db.get_connection() as conn:
                result = conn.execute(query, params)
                symbols = [row[0] for row in result]

            logger.info(f"Found {len(symbols)} symbols with {min_bars}+ bars ({timeframe})")
            return symbols

        except Exception as e:
            logger.error(f"Failed to get available symbols: {e}")
            return []

    def get_universe_ohlcv_data(
        self,
        symbols: list[str],
        timeframe: str = 'daily',
        limit: int = 200,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data for multiple symbols (batch query).

        Args:
            symbols: List of stock symbols
            timeframe: Data timeframe
            limit: Maximum bars per symbol

        Returns:
            Dictionary mapping symbol to DataFrame

        Examples:
            >>> service = OHLCVDataService()
            >>> data = service.get_universe_ohlcv_data(['AAPL', 'MSFT', 'GOOGL'])
            >>> print(f"Loaded data for {len(data)} symbols")
        """
        result = {}

        # Use batch query for efficiency
        table_name = TIMEFRAME_TABLE_MAP.get(timeframe, 'stock_prices_1day')

        try:
            # Build batch query with window function for limiting rows per symbol
            symbols_upper = [s.upper() for s in symbols]
            symbols_str = "', '".join(symbols_upper)

            query = text(f"""
                WITH ranked AS (
                    SELECT
                        date, symbol, open, high, low, close, volume,
                        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) as rn
                    FROM {table_name}
                    WHERE symbol IN ('{symbols_str}')
                )
                SELECT date, symbol, open, high, low, close, volume
                FROM ranked
                WHERE rn <= :limit
                ORDER BY symbol, date
            """)
            params = {'limit': limit}

            with self.db.get_connection() as conn:
                df_all = pd.read_sql_query(query, conn, params=params)

            # Split by symbol
            for symbol in symbols_upper:
                symbol_df = df_all[df_all['symbol'] == symbol].copy()
                if not symbol_df.empty:
                    symbol_df = symbol_df.drop('symbol', axis=1)
                    symbol_df = symbol_df.set_index('date')
                    symbol_df = symbol_df.sort_index(ascending=True)
                    result[symbol] = symbol_df
                else:
                    logger.warning(f"No data found for symbol {symbol}")
                    result[symbol] = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

            logger.info(f"Batch loaded data for {len(result)} symbols ({timeframe})")
            return result

        except Exception as e:
            logger.error(f"Batch query failed: {e}")
            raise RuntimeError(f"Failed to fetch universe OHLCV data: {str(e)}") from e

    def health_check(self) -> dict[str, any]:
        """
        Check database connection and data availability.

        Returns:
            Dictionary with health status

        Examples:
            >>> service = OHLCVDataService()
            >>> health = service.health_check()
            >>> print(f"Database status: {health['status']}")
        """
        try:
            # Test connection
            db_health = self.db.health_check()

            if db_health['status'] != 'healthy':
                return {
                    'status': 'unhealthy',
                    'message': 'Database connection failed',
                    'database': db_health
                }

            # Count available symbols
            symbols = self.get_available_symbols('daily', min_bars=100)

            return {
                'status': 'healthy',
                'message': 'OHLCV data service operational',
                'symbols_available': len(symbols),
                'database': db_health
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': str(e),
                'error': type(e).__name__
            }
