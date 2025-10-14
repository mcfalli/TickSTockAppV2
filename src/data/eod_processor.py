"""
End-of-Day Market Data Processing for TickStock.ai
Automated EOD job with market close timing and Redis notifications.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from datetime import time as dt_time
from typing import Any

# import schedule  # Optional dependency for scheduled jobs

# Load configuration
try:
    from src.core.services.config_manager import get_config
except ImportError:
    pass  # config manager not available, will handle below

import psycopg2
import redis
from psycopg2.extras import RealDictCursor

from .historical_loader import PolygonHistoricalLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EODProcessor:
    """End-of-Day market data processing with automation and notifications"""

    def __init__(self, database_uri: str = None, redis_host: str = None):
        config = get_config()
        self.database_uri = database_uri or config.get('DATABASE_URI')
        self.redis_host = redis_host or config.get('REDIS_HOST', 'localhost')
        self.redis_port = config.get('REDIS_PORT', 6379)
        if not self.database_uri:
            raise ValueError("DATABASE_URI required for EOD processing")

        self.conn = None
        self.redis_client = None
        self.historical_loader = PolygonHistoricalLoader()

        # Market timing configuration
        self.market_close_time = dt_time(16, 30)  # 4:30 PM ET
        self.eod_start_delay = timedelta(minutes=30)  # Start 30 min after close
        self.completion_target = timedelta(hours=1, minutes=30)  # 95% complete by 6:00 PM ET

        # Holiday calendar (simplified)
        self.market_holidays_2024 = {
            '2024-01-01', '2024-01-15', '2024-02-19', '2024-03-29',
            '2024-05-27', '2024-06-19', '2024-07-04', '2024-09-02',
            '2024-11-28', '2024-12-25'
        }

        logger.info("EOD-PROCESSOR: Initialized")

    def _connect_db(self):
        """Establish database connection."""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(self.database_uri)

    def _connect_redis(self):
        """Establish Redis connection."""
        if not self.redis_client:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )
            self.redis_client.ping()

    def is_market_day(self, date: datetime) -> bool:
        """Check if given date is a market trading day."""
        if date.weekday() >= 5:  # Weekend
            return False
        date_str = date.strftime('%Y-%m-%d')
        if date_str in self.market_holidays_2024:
            return False
        return True

    def get_last_trading_day(self) -> datetime:
        """Get the most recent trading day."""
        today = datetime.now().date()
        check_date = datetime.combine(today, dt_time())

        while not self.is_market_day(check_date):
            check_date -= timedelta(days=1)
        return check_date

    def get_tracked_symbols(self) -> list[str]:
        """Get all symbols for EOD processing."""
        self._connect_db()

        query = """
        SELECT DISTINCT key, value, type FROM cache_entries 
        WHERE type IN ('stock_universe', 'etf_universe') 
        AND environment = 'DEFAULT'
        """

        symbols = set()

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                results = cursor.fetchall()

                for result in results:
                    universe_data = result['value']
                    universe_type = result['type']
                    universe_key = result['key']

                    # Skip dev universes
                    if universe_key.startswith('dev_'):
                        continue

                    # Extract symbols based on universe type
                    if universe_type == 'stock_universe':
                        stocks = universe_data.get('stocks', [])
                        for stock in stocks:
                            if 'ticker' in stock:
                                symbols.add(stock['ticker'])
                    elif universe_type == 'etf_universe':
                        etfs = universe_data.get('etfs', [])
                        for etf in etfs:
                            if 'ticker' in etf:
                                symbols.add(etf['ticker'])

                symbol_list = sorted(list(symbols))
                logger.info(f"EOD-PROCESSOR: Found {len(symbol_list)} tracked symbols")
                return symbol_list

        except Exception as e:
            logger.error(f"EOD-PROCESSOR: Failed to get tracked symbols: {e}")
            return []

    def validate_data_completeness(self, symbols: list[str], target_date: datetime) -> dict[str, Any]:
        """Validate data completeness for EOD processing."""
        self._connect_db()

        target_date_str = target_date.strftime('%Y-%m-%d')
        missing_symbols = []
        completed_symbols = []

        try:
            with self.conn.cursor() as cursor:
                for symbol in symbols:
                    check_sql = """
                    SELECT COUNT(*) as count FROM ohlcv_daily 
                    WHERE symbol = %s AND date = %s
                    """

                    cursor.execute(check_sql, (symbol, target_date_str))
                    result = cursor.fetchone()

                    if result and result[0] > 0:
                        completed_symbols.append(symbol)
                    else:
                        missing_symbols.append(symbol)

                completion_rate = len(completed_symbols) / len(symbols) if symbols else 0

                validation_results = {
                    'target_date': target_date_str,
                    'total_symbols': len(symbols),
                    'completed_symbols': len(completed_symbols),
                    'missing_symbols': len(missing_symbols),
                    'completion_rate': completion_rate,
                    'missing_symbol_list': missing_symbols[:10],
                    'status': 'COMPLETE' if completion_rate >= 0.95 else 'INCOMPLETE'
                }

                logger.info(f"EOD-PROCESSOR: Data validation complete - {completion_rate:.1%} completion rate")
                return validation_results

        except Exception as e:
            logger.error(f"EOD-PROCESSOR: Data validation failed: {e}")
            return {
                'target_date': target_date_str,
                'status': 'ERROR',
                'error': str(e)
            }

    def run_eod_update(self) -> dict[str, Any]:
        """Run the complete EOD update process."""
        start_time = datetime.now()
        target_date = self.get_last_trading_day()

        logger.info(f"EOD-PROCESSOR: Starting EOD update for {target_date.strftime('%Y-%m-%d')}")

        try:
            # Get tracked symbols
            symbols = self.get_tracked_symbols()
            if not symbols:
                return {
                    'status': 'ERROR',
                    'message': 'No tracked symbols found'
                }

            # Validate completion
            validation_results = self.validate_data_completeness(symbols, target_date)

            # Generate results
            end_time = datetime.now()
            processing_time = end_time - start_time

            results = {
                'status': 'COMPLETE',
                'target_date': target_date.strftime('%Y-%m-%d'),
                'processing_time_minutes': processing_time.total_seconds() / 60,
                'total_symbols': len(symbols),
                'completion_rate': validation_results.get('completion_rate', 0),
                'validation_status': validation_results.get('status', 'UNKNOWN')
            }

            # Send notification
            self.send_eod_notification(results)

            logger.info(f"EOD-PROCESSOR: EOD update completed - {results['completion_rate']:.1%} success rate")
            return results

        except Exception as e:
            logger.error(f"EOD-PROCESSOR: EOD update failed: {e}")
            error_results = {
                'status': 'ERROR',
                'target_date': target_date.strftime('%Y-%m-%d'),
                'error': str(e)
            }
            self.send_eod_notification(error_results)
            return error_results

    def send_eod_notification(self, results: dict[str, Any]):
        """Send EOD completion notification via Redis."""
        try:
            self._connect_redis()

            notification = {
                'type': 'eod_completion',
                'timestamp': datetime.now().isoformat(),
                'results': results
            }

            self.redis_client.publish('tickstock:eod:completion', json.dumps(notification))

            self.redis_client.setex(
                'tickstock:eod:latest_status',
                86400,  # 24 hour expiry
                json.dumps(results)
            )

            logger.info(f"EOD-PROCESSOR: Notification sent - Status: {results.get('status')}")

        except Exception as e:
            logger.error(f"EOD-PROCESSOR: Failed to send notification: {e}")

def main():
    """CLI entry point for EOD processing."""
    parser = argparse.ArgumentParser(description='End-of-Day market data processing')
    parser.add_argument('--run-eod', action='store_true', help='Run EOD update immediately')
    parser.add_argument('--validate-only', action='store_true', help='Validate data completeness only')
    parser.add_argument('--target-date', help='Target date for EOD processing (YYYY-MM-DD)')

    args = parser.parse_args()

    try:
        processor = EODProcessor()

        if args.validate_only:
            target_date = datetime.now().date() if not args.target_date else datetime.strptime(args.target_date, '%Y-%m-%d')
            target_date = datetime.combine(target_date, dt_time())

            symbols = processor.get_tracked_symbols()
            results = processor.validate_data_completeness(symbols, target_date)

            print("\nEOD Data Validation Results:")
            for key, value in results.items():
                print(f"  {key}: {value}")

        elif args.run_eod:
            results = processor.run_eod_update()

            print("\nEOD Update Results:")
            for key, value in results.items():
                print(f"  {key}: {value}")

        else:
            print("Please specify --run-eod or --validate-only")
            parser.print_help()

    except Exception as e:
        logger.error(f"EOD-PROCESSOR: Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
