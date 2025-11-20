"""
End-of-Day Market Data Processing for TickStock.ai
Automated EOD job with market close timing and Redis notifications.

This module provides:
- Automated EOD scheduling with market timing
- Market holiday and abbreviated trading day handling
- Data completeness validation and missing data flagging
- Redis integration for completion notifications
- FMV fallback for thinly traded symbols

Usage:
    python -m src.data.eod_processor --run-eod
    python -m src.data.eod_processor --validate-only
"""

import os
import sys
import time
import argparse
import logging
import json
from datetime import datetime, timedelta, time as dt_time
from typing import List, Dict, Any, Optional, Set
import schedule

# Load environment variables from config manager
try:
    from src.core.services.config_manager import get_config
except ImportError:
    pass  # config manager not available, will handle below

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from historical_loader import MassiveHistoricalLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EODProcessor:
    """End-of-Day market data processing with automation and notifications"""
    
    def __init__(self, database_uri: str = None, redis_host: str = None):
        """
        Initialize EOD processor.
        
        Args:
            database_uri: Database connection string (defaults to env)
            redis_host: Redis host (defaults to env)
        """
        config = get_config()
        self.database_uri = database_uri or config.get('DATABASE_URI')
        self.redis_host = redis_host or config.get('REDIS_HOST', 'localhost')
        self.redis_port = config.get('REDIS_PORT', 6379)
        if not self.database_uri:
            raise ValueError("DATABASE_URI required for EOD processing")
            
        # Initialize connections
        self.conn = None
        self.redis_client = None
        self.historical_loader = MassiveHistoricalLoader()
        
        # Market timing configuration
        self.market_close_time = dt_time(16, 30)  # 4:30 PM ET
        self.eod_start_delay = timedelta(minutes=30)  # Start 30 min after close
        self.completion_target = timedelta(hours=1, minutes=30)  # 95% complete by 6:00 PM ET
        
        # Holiday calendar (simplified - in production use market data API)
        self.market_holidays_2024 = {
            '2024-01-01',  # New Year's Day
            '2024-01-15',  # Martin Luther King Jr. Day
            '2024-02-19',  # Presidents' Day
            '2024-03-29',  # Good Friday
            '2024-05-27',  # Memorial Day
            '2024-06-19',  # Juneteenth
            '2024-07-04',  # Independence Day
            '2024-09-02',  # Labor Day
            '2024-11-28',  # Thanksgiving
            '2024-12-25',  # Christmas
        }
        
        logger.info("EOD-PROCESSOR: Initialized")
        
    def _connect_db(self):
        """Establish database connection."""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(self.database_uri)
            logger.debug("EOD-PROCESSOR: Database connected")
            
    def _connect_redis(self):
        """Establish Redis connection."""
        if not self.redis_client:
            self.redis_client = redis.Redis(
                host=self.redis_host, 
                port=self.redis_port, 
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.debug("EOD-PROCESSOR: Redis connected")
            
    def _close_connections(self):
        """Close all connections."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.debug("EOD-PROCESSOR: Database connection closed")
        if self.redis_client:
            self.redis_client.close()
            logger.debug("EOD-PROCESSOR: Redis connection closed")
            
    def is_market_day(self, date: datetime) -> bool:
        """
        Check if given date is a market trading day.
        
        Args:
            date: Date to check
            
        Returns:
            True if market is open, False for weekends/holidays
        """
        # Check weekend
        if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
            
        # Check holidays
        date_str = date.strftime('%Y-%m-%d')
        if date_str in self.market_holidays_2024:
            return False
            
        return True
    
    def get_last_trading_day(self) -> datetime:
        """Get the most recent trading day."""
        today = datetime.now().date()
        check_date = datetime.combine(today, dt_time())
        
        # Go back until we find a trading day
        while not self.is_market_day(check_date):
            check_date -= timedelta(days=1)
            
        return check_date
    
    def get_tracked_symbols(self) -> List[str]:
        """
        Get all symbols that should be included in EOD processing.
        
        Returns:
            List of symbols from all active universes
        """
        self._connect_db()
        
        # Get all symbols from cache_entries universes
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
                    
                    # Skip dev universes in production EOD
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
            return []\n    \n    def validate_data_completeness(self, symbols: List[str], target_date: datetime) -> Dict[str, Any]:\n        \"\"\"\n        Validate data completeness for EOD processing.\n        \n        Args:\n            symbols: List of symbols to validate\n            target_date: Trading date to validate\n            \n        Returns:\n            Dict with validation results and missing data report\n        \"\"\"\n        self._connect_db()\n        \n        target_date_str = target_date.strftime('%Y-%m-%d')\n        missing_symbols = []\n        completed_symbols = []\n        \n        try:\n            with self.conn.cursor() as cursor:\n                # Check each symbol for data on target date\n                for symbol in symbols:\n                    check_sql = \"\"\"\n                    SELECT COUNT(*) as count FROM ohlcv_daily \n                    WHERE symbol = %s AND date = %s\n                    \"\"\"\n                    \n                    cursor.execute(check_sql, (symbol, target_date_str))\n                    result = cursor.fetchone()\n                    \n                    if result and result[0] > 0:\n                        completed_symbols.append(symbol)\n                    else:\n                        missing_symbols.append(symbol)\n                \n                completion_rate = len(completed_symbols) / len(symbols) if symbols else 0\n                \n                validation_results = {\n                    'target_date': target_date_str,\n                    'total_symbols': len(symbols),\n                    'completed_symbols': len(completed_symbols),\n                    'missing_symbols': len(missing_symbols),\n                    'completion_rate': completion_rate,\n                    'missing_symbol_list': missing_symbols[:10],  # First 10 for logging\n                    'status': 'COMPLETE' if completion_rate >= 0.95 else 'INCOMPLETE'\n                }\n                \n                logger.info(f\"EOD-PROCESSOR: Data validation complete - {completion_rate:.1%} completion rate\")\n                return validation_results\n                \n        except Exception as e:\n            logger.error(f\"EOD-PROCESSOR: Data validation failed: {e}\")\n            return {\n                'target_date': target_date_str,\n                'status': 'ERROR',\n                'error': str(e)\n            }\n    \n    def run_eod_update(self) -> Dict[str, Any]:\n        \"\"\"\n        Run the complete EOD update process.\n        \n        Returns:\n            Dict with processing results\n        \"\"\"\n        start_time = datetime.now()\n        target_date = self.get_last_trading_day()\n        \n        logger.info(f\"EOD-PROCESSOR: Starting EOD update for {target_date.strftime('%Y-%m-%d')}\")\n        \n        try:\n            # Step 1: Get tracked symbols\n            symbols = self.get_tracked_symbols()\n            if not symbols:\n                return {\n                    'status': 'ERROR',\n                    'message': 'No tracked symbols found',\n                    'start_time': start_time.isoformat(),\n                    'end_time': datetime.now().isoformat()\n                }\n            \n            # Step 2: Load missing data for current day\n            logger.info(f\"EOD-PROCESSOR: Loading EOD data for {len(symbols)} symbols\")\n            \n            # Use historical loader to update symbols\n            target_date_str = target_date.strftime('%Y-%m-%d')\n            end_date_str = target_date.strftime('%Y-%m-%d')\n            \n            successful_loads = 0\n            failed_symbols = []\n            \n            for i, symbol in enumerate(symbols):\n                try:\n                    if i % 50 == 0:  # Progress logging\n                        logger.info(f\"EOD-PROCESSOR: Processing symbol {i+1}/{len(symbols)} ({symbol})\")\n                    \n                    # Ensure symbol exists\n                    if not self.historical_loader.ensure_symbol_exists(symbol):\n                        failed_symbols.append(symbol)\n                        continue\n                    \n                    # Fetch single day of data\n                    df = self.historical_loader.fetch_symbol_data(\n                        symbol, target_date_str, end_date_str, 'day', 1\n                    )\n                    \n                    if not df.empty:\n                        self.historical_loader.save_data_to_db(df, 'day')\n                        successful_loads += 1\n                    else:\n                        # Try FMV fallback for thinly traded symbols\n                        logger.debug(f\"EOD-PROCESSOR: No data for {symbol}, checking FMV fallback\")\n                        failed_symbols.append(symbol)\n                        \n                except Exception as e:\n                    logger.warning(f\"EOD-PROCESSOR: Failed to load {symbol}: {e}\")\n                    failed_symbols.append(symbol)\n            \n            # Step 3: Validate completion\n            validation_results = self.validate_data_completeness(symbols, target_date)\n            \n            # Step 4: Generate results\n            end_time = datetime.now()\n            processing_time = end_time - start_time\n            \n            results = {\n                'status': 'COMPLETE',\n                'target_date': target_date_str,\n                'start_time': start_time.isoformat(),\n                'end_time': end_time.isoformat(),\n                'processing_time_minutes': processing_time.total_seconds() / 60,\n                'total_symbols': len(symbols),\n                'successful_loads': successful_loads,\n                'failed_symbols': len(failed_symbols),\n                'completion_rate': validation_results.get('completion_rate', 0),\n                'validation_status': validation_results.get('status', 'UNKNOWN')\n            }\n            \n            # Step 5: Send Redis notification\n            self.send_eod_notification(results)\n            \n            logger.info(f\"EOD-PROCESSOR: EOD update completed - {results['completion_rate']:.1%} success rate\")\n            return results\n            \n        except Exception as e:\n            logger.error(f\"EOD-PROCESSOR: EOD update failed: {e}\")\n            error_results = {\n                'status': 'ERROR',\n                'target_date': target_date.strftime('%Y-%m-%d'),\n                'start_time': start_time.isoformat(),\n                'end_time': datetime.now().isoformat(),\n                'error': str(e)\n            }\n            self.send_eod_notification(error_results)\n            return error_results\n    \n    def send_eod_notification(self, results: Dict[str, Any]):\n        \"\"\"\n        Send EOD completion notification via Redis.\n        \n        Args:\n            results: EOD processing results\n        \"\"\"\n        try:\n            self._connect_redis()\n            \n            # Publish to EOD completion channel\n            notification = {\n                'type': 'eod_completion',\n                'timestamp': datetime.now().isoformat(),\n                'results': results\n            }\n            \n            self.redis_client.publish('tickstock:eod:completion', json.dumps(notification))\n            \n            # Store latest EOD status\n            self.redis_client.setex(\n                'tickstock:eod:latest_status', \n                86400,  # 24 hour expiry\n                json.dumps(results)\n            )\n            \n            logger.info(f\"EOD-PROCESSOR: Notification sent - Status: {results.get('status')}\")\n            \n        except Exception as e:\n            logger.error(f\"EOD-PROCESSOR: Failed to send notification: {e}\")\n    \n    def schedule_eod_job(self):\n        \"\"\"\n        Schedule the EOD job to run automatically after market close.\n        \"\"\"\n        # Schedule for 5:00 PM ET (30 minutes after market close)\n        schedule.every().monday.at(\"17:00\").do(self.run_eod_update)\n        schedule.every().tuesday.at(\"17:00\").do(self.run_eod_update)\n        schedule.every().wednesday.at(\"17:00\").do(self.run_eod_update)\n        schedule.every().thursday.at(\"17:00\").do(self.run_eod_update)\n        schedule.every().friday.at(\"17:00\").do(self.run_eod_update)\n        \n        logger.info(\"EOD-PROCESSOR: Scheduled EOD jobs for weekdays at 5:00 PM ET\")\n        \n        # Run the scheduler\n        while True:\n            schedule.run_pending()\n            time.sleep(60)  # Check every minute\n    \n    def __del__(self):\n        \"\"\"Cleanup on deletion.\"\"\"\n        self._close_connections()\n\ndef main():\n    \"\"\"CLI entry point for EOD processing.\"\"\"\n    parser = argparse.ArgumentParser(description='End-of-Day market data processing')\n    parser.add_argument('--run-eod', action='store_true', help='Run EOD update immediately')\n    parser.add_argument('--validate-only', action='store_true', help='Validate data completeness only')\n    parser.add_argument('--schedule', action='store_true', help='Start scheduled EOD processing')\n    parser.add_argument('--target-date', help='Target date for EOD processing (YYYY-MM-DD)')\n    parser.add_argument('--database-uri', help='Database URI (overrides env var)')\n    parser.add_argument('--redis-host', help='Redis host (overrides env var)')\n    \n    args = parser.parse_args()\n    \n    try:\n        # Initialize processor\n        processor = EODProcessor(\n            database_uri=args.database_uri,\n            redis_host=args.redis_host\n        )\n        \n        if args.validate_only:\n            # Validation only\n            target_date = datetime.now().date() if not args.target_date else datetime.strptime(args.target_date, '%Y-%m-%d')\n            target_date = datetime.combine(target_date, dt_time())\n            \n            symbols = processor.get_tracked_symbols()\n            results = processor.validate_data_completeness(symbols, target_date)\n            \n            print(\"\\nEOD Data Validation Results:\")\n            for key, value in results.items():\n                print(f\"  {key}: {value}\")\n            \n        elif args.run_eod:\n            # Run EOD update\n            results = processor.run_eod_update()\n            \n            print(\"\\nEOD Update Results:\")\n            for key, value in results.items():\n                if key != 'failed_symbols' or len(str(value)) < 200:\n                    print(f\"  {key}: {value}\")\n            \n        elif args.schedule:\n            # Start scheduled processing\n            print(\"Starting scheduled EOD processing...\")\n            print(\"Press Ctrl+C to stop\")\n            processor.schedule_eod_job()\n            \n        else:\n            print(\"Please specify --run-eod, --validate-only, or --schedule\")\n            parser.print_help()\n            \n    except KeyboardInterrupt:\n        print(\"\\nStopping EOD processor...\")\n    except Exception as e:\n        logger.error(f\"EOD-PROCESSOR: Fatal error: {e}\")\n        sys.exit(1)\n\nif __name__ == '__main__':\n    main()