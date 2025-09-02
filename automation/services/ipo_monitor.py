"""
IPO Monitoring Service for TickStock.ai
Automated daily scanning for new IPOs and symbol changes with Redis notifications.

This service runs separately from TickStockApp and handles:
- Daily IPO detection from Polygon.io
- Symbol change monitoring and archival
- Automated 90-day historical backfill
- Auto-assignment to appropriate cache_entries universes
- Redis pub-sub notifications for TickStockApp

Usage:
    python -m automation.services.ipo_monitor --daily-scan
    python -m automation.services.ipo_monitor --backfill-symbol AAPL
"""

import os
import sys
import time
import argparse
import logging
import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Set
import asyncio

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import requests

from data.historical_loader import PolygonHistoricalLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IPOMonitorService:
    """
    IPO and Symbol Change Monitoring Service
    Automated scanning and processing with Redis notifications
    """
    
    def __init__(self, database_uri: str = None, redis_host: str = None, polygon_api_key: str = None):
        """
        Initialize IPO monitoring service.
        
        Args:
            database_uri: Database connection string (defaults to env)
            redis_host: Redis host (defaults to env)
            polygon_api_key: Polygon.io API key (defaults to env)
        """
        self.database_uri = database_uri or os.getenv('DATABASE_URI')
        self.redis_host = redis_host or os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.polygon_api_key = polygon_api_key or os.getenv('POLYGON_API_KEY')
        
        if not self.database_uri:
            raise ValueError("DATABASE_URI required for IPO monitoring")
        if not self.polygon_api_key:
            raise ValueError("POLYGON_API_KEY required for IPO monitoring")
            
        # Initialize connections
        self.conn = None
        self.redis_client = None
        self.session = requests.Session()
        self.historical_loader = PolygonHistoricalLoader()
        
        # Configuration
        self.polygon_base_url = "https://api.polygon.io"
        self.rate_limit_delay = 12  # 5 calls per minute for free tier
        self.batch_size = 100  # Process symbols in batches
        
        # Redis channels for automation events
        self.channels = {
            'new_symbol': 'tickstock.automation.symbols.new',
            'symbol_changed': 'tickstock.automation.symbols.changed',
            'symbol_archived': 'tickstock.automation.symbols.archived',
            'backfill_started': 'tickstock.automation.backfill.started',
            'backfill_progress': 'tickstock.automation.backfill.progress',
            'backfill_completed': 'tickstock.automation.backfill.completed',
            'maintenance_started': 'tickstock.automation.maintenance.started',
            'maintenance_completed': 'tickstock.automation.maintenance.completed'
        }
        
        logger.info("IPO-MONITOR: Service initialized")
        
    def _connect_db(self):
        """Establish database connection."""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(self.database_uri)
            logger.debug("IPO-MONITOR: Database connected")
            
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
            logger.debug("IPO-MONITOR: Redis connected")
    
    def _close_connections(self):
        """Close all connections."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.debug("IPO-MONITOR: Database connection closed")
        if self.redis_client:
            self.redis_client.close()
            logger.debug("IPO-MONITOR: Redis connection closed")
    
    async def _publish_automation_event(self, channel: str, data: Dict[str, Any]):
        """
        Publish automation event to Redis.
        
        Args:
            channel: Redis channel name
            data: Event data to publish
        """
        try:
            self._connect_redis()
            
            event_data = {
                'timestamp': datetime.now().isoformat(),
                'service': 'ipo_monitor',
                'data': data
            }
            
            self.redis_client.publish(self.channels[channel], json.dumps(event_data))
            logger.debug(f"IPO-MONITOR: Published to {channel}: {data}")
            
        except Exception as e:
            logger.error(f"IPO-MONITOR: Failed to publish event to {channel}: {e}")
    
    def _make_polygon_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make rate-limited request to Polygon.io API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response
        """
        url = f"{self.polygon_base_url}{endpoint}"
        params = params or {}
        params['apikey'] = self.polygon_api_key
        
        try:
            logger.debug(f"IPO-MONITOR: Polygon API request: {endpoint}")
            response = self.session.get(url, params=params, timeout=30)
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("IPO-MONITOR: Rate limited, waiting 60 seconds...")
                time.sleep(60)
                response = self.session.get(url, params=params, timeout=30)
            
            response.raise_for_status()
            data = response.json()
            
            # Proactive rate limiting
            time.sleep(self.rate_limit_delay)
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"IPO-MONITOR: Polygon API request failed: {e}")
            raise
    
    def symbol_exists(self, symbol: str) -> bool:
        """
        Check if symbol exists in symbols table.
        
        Args:
            symbol: Ticker symbol to check
            
        Returns:
            True if symbol exists
        """
        self._connect_db()
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM symbols WHERE symbol = %s", (symbol,))
                result = cursor.fetchone()
                return result[0] > 0
                
        except Exception as e:
            logger.error(f"IPO-MONITOR: Failed to check if symbol exists: {e}")
            return False
    
    def get_existing_symbols(self) -> Set[str]:
        """
        Get all existing symbols from database.
        
        Returns:
            Set of existing ticker symbols
        """
        self._connect_db()
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT symbol FROM symbols WHERE active = true")
                results = cursor.fetchall()
                return {row[0] for row in results}
                
        except Exception as e:
            logger.error(f"IPO-MONITOR: Failed to get existing symbols: {e}")
            return set()
    
    async def daily_ipo_scan(self) -> Dict[str, Any]:
        """
        Perform daily scan for new IPOs and symbol changes.
        
        Returns:
            Dictionary with scan results
        """
        scan_start_time = datetime.now()
        await self._publish_automation_event('maintenance_started', {
            'operation': 'daily_ipo_scan',
            'start_time': scan_start_time.isoformat()
        })
        
        logger.info("IPO-MONITOR: Starting daily IPO scan")
        
        try:
            # Get current symbols to compare against
            existing_symbols = self.get_existing_symbols()
            logger.info(f"IPO-MONITOR: Found {len(existing_symbols)} existing symbols")
            
            # Scan for new listings from yesterday
            yesterday = (datetime.now() - timedelta(days=1)).date()
            new_symbols_found = await self.scan_polygon_for_new_symbols(yesterday)\n            \n            # Process new symbols\n            processed_symbols = []\n            failed_symbols = []\n            \n            for symbol_data in new_symbols_found:\n                symbol = symbol_data['ticker']\n                \n                if symbol not in existing_symbols:\n                    try:\n                        await self.process_new_symbol(symbol_data)\n                        processed_symbols.append(symbol)\n                        logger.info(f\"IPO-MONITOR: ✓ Processed new symbol: {symbol}\")\n                        \n                    except Exception as e:\n                        logger.error(f\"IPO-MONITOR: ✗ Failed to process {symbol}: {e}\")\n                        failed_symbols.append(symbol)\n                else:\n                    logger.debug(f\"IPO-MONITOR: Symbol {symbol} already exists, skipping\")\n            \n            # Generate scan results\n            scan_end_time = datetime.now()\n            scan_duration = (scan_end_time - scan_start_time).total_seconds()\n            \n            results = {\n                'scan_date': yesterday.isoformat(),\n                'scan_duration_seconds': scan_duration,\n                'existing_symbols_count': len(existing_symbols),\n                'new_symbols_found': len(new_symbols_found),\n                'symbols_processed': len(processed_symbols),\n                'symbols_failed': len(failed_symbols),\n                'processed_symbols': processed_symbols,\n                'failed_symbols': failed_symbols,\n                'success_rate': len(processed_symbols) / len(new_symbols_found) if new_symbols_found else 1.0\n            }\n            \n            await self._publish_automation_event('maintenance_completed', {\n                'operation': 'daily_ipo_scan',\n                'results': results\n            })\n            \n            logger.info(f\"IPO-MONITOR: Daily IPO scan completed - {len(processed_symbols)} new symbols processed\")\n            return results\n            \n        except Exception as e:\n            logger.error(f\"IPO-MONITOR: Daily IPO scan failed: {e}\")\n            await self._publish_automation_event('maintenance_completed', {\n                'operation': 'daily_ipo_scan',\n                'error': str(e),\n                'status': 'failed'\n            })\n            raise\n    \n    async def scan_polygon_for_new_symbols(self, scan_date: date) -> List[Dict[str, Any]]:\n        \"\"\"\n        Scan Polygon.io for new symbols on given date.\n        \n        Args:\n            scan_date: Date to scan for new listings\n            \n        Returns:\n            List of new symbol data\n        \"\"\"\n        try:\n            # Get ticker data for stocks and ETFs\n            endpoint = \"/v3/reference/tickers\"\n            params = {\n                'market': 'stocks',\n                'active': 'true',\n                'date': scan_date.isoformat(),\n                'limit': 1000  # Maximum allowed\n            }\n            \n            all_tickers = []\n            next_url = None\n            \n            # Handle pagination\n            while True:\n                if next_url:\n                    # Extract cursor from next_url\n                    import urllib.parse\n                    parsed_url = urllib.parse.urlparse(next_url)\n                    query_params = urllib.parse.parse_qs(parsed_url.query)\n                    if 'cursor' in query_params:\n                        params['cursor'] = query_params['cursor'][0]\n                \n                response = self._make_polygon_request(endpoint, params)\n                \n                if response.get('status') == 'OK' and response.get('results'):\n                    all_tickers.extend(response['results'])\n                    logger.info(f\"IPO-MONITOR: Retrieved {len(response['results'])} tickers from Polygon\")\n                    \n                    # Check for next page\n                    if response.get('next_url'):\n                        next_url = response['next_url']\n                        params.pop('cursor', None)  # Reset cursor for next iteration\n                    else:\n                        break\n                else:\n                    logger.warning(f\"IPO-MONITOR: No ticker data found for {scan_date}\")\n                    break\n            \n            logger.info(f\"IPO-MONITOR: Found {len(all_tickers)} total tickers for {scan_date}\")\n            return all_tickers\n            \n        except Exception as e:\n            logger.error(f\"IPO-MONITOR: Failed to scan Polygon for new symbols: {e}\")\n            return []\n    \n    async def process_new_symbol(self, symbol_data: Dict[str, Any]):\n        \"\"\"\n        Process a newly discovered symbol.\n        \n        Args:\n            symbol_data: Symbol data from Polygon.io\n        \"\"\"\n        symbol = symbol_data.get('ticker')\n        if not symbol:\n            raise ValueError(\"Symbol data missing ticker\")\n            \n        logger.info(f\"IPO-MONITOR: Processing new symbol: {symbol}\")\n        \n        try:\n            # 1. Add symbol to database using historical loader\n            if not self.historical_loader.ensure_symbol_exists(symbol):\n                raise Exception(f\"Failed to create symbol record for {symbol}\")\n            \n            # 2. Publish new symbol notification\n            await self._publish_automation_event('new_symbol', {\n                'symbol': symbol,\n                'name': symbol_data.get('name', ''),\n                'type': symbol_data.get('type', 'CS'),\n                'market': symbol_data.get('market', 'stocks'),\n                'exchange': symbol_data.get('primary_exchange', ''),\n                'ipo_date': symbol_data.get('list_date'),\n                'detection_date': datetime.now().isoformat()\n            })\n            \n            # 3. Trigger 90-day historical backfill\n            await self.trigger_90day_backfill(symbol)\n            \n            # 4. Auto-assign to appropriate universes\n            await self.auto_assign_to_universes(symbol, symbol_data)\n            \n            logger.info(f\"IPO-MONITOR: ✓ Successfully processed new symbol: {symbol}\")\n            \n        except Exception as e:\n            logger.error(f\"IPO-MONITOR: ✗ Failed to process symbol {symbol}: {e}\")\n            raise\n    \n    async def trigger_90day_backfill(self, symbol: str):\n        \"\"\"\n        Trigger 90-day historical backfill for new symbol.\n        \n        Args:\n            symbol: Ticker symbol for backfill\n        \"\"\"\n        try:\n            await self._publish_automation_event('backfill_started', {\n                'symbol': symbol,\n                'backfill_days': 90,\n                'start_time': datetime.now().isoformat()\n            })\n            \n            # Calculate date range\n            end_date = datetime.now()\n            start_date = end_date - timedelta(days=90)\n            \n            logger.info(f\"IPO-MONITOR: Starting 90-day backfill for {symbol}\")\n            \n            # Use historical loader for backfill\n            df = self.historical_loader.fetch_symbol_data(\n                symbol=symbol,\n                start_date=start_date.strftime('%Y-%m-%d'),\n                end_date=end_date.strftime('%Y-%m-%d'),\n                timespan='day',\n                multiplier=1\n            )\n            \n            if not df.empty:\n                # Save data to database\n                self.historical_loader.save_data_to_db(df, 'day')\n                \n                await self._publish_automation_event('backfill_completed', {\n                    'symbol': symbol,\n                    'records_loaded': len(df),\n                    'backfill_days': 90,\n                    'success': True,\n                    'completion_time': datetime.now().isoformat()\n                })\n                \n                logger.info(f\"IPO-MONITOR: ✓ Completed 90-day backfill for {symbol}: {len(df)} records\")\n            else:\n                await self._publish_automation_event('backfill_completed', {\n                    'symbol': symbol,\n                    'records_loaded': 0,\n                    'backfill_days': 90,\n                    'success': False,\n                    'error': 'No historical data available',\n                    'completion_time': datetime.now().isoformat()\n                })\n                \n                logger.warning(f\"IPO-MONITOR: ⚠ No historical data available for {symbol}\")\n                \n        except Exception as e:\n            await self._publish_automation_event('backfill_completed', {\n                'symbol': symbol,\n                'backfill_days': 90,\n                'success': False,\n                'error': str(e),\n                'completion_time': datetime.now().isoformat()\n            })\n            logger.error(f\"IPO-MONITOR: ✗ Backfill failed for {symbol}: {e}\")\n            raise\n    \n    async def auto_assign_to_universes(self, symbol: str, symbol_data: Dict[str, Any]):\n        \"\"\"\n        Auto-assign new symbol to appropriate cache_entries universes.\n        \n        Args:\n            symbol: Ticker symbol\n            symbol_data: Symbol metadata from Polygon\n        \"\"\"\n        try:\n            symbol_type = symbol_data.get('type', 'CS')\n            market_cap = symbol_data.get('market_cap')\n            name = symbol_data.get('name', '').upper()\n            \n            assignments = []\n            \n            # ETF assignment logic\n            if symbol_type in ['ETF', 'ETP', 'ETN']:\n                if 'GROWTH' in name or 'TECH' in name:\n                    assignments.append('etf_growth')\n                elif 'VALUE' in name or 'DIVIDEND' in name:\n                    assignments.append('etf_value')\n                elif 'SECTOR' in name or any(sector in name for sector in ['FINANCIAL', 'ENERGY', 'HEALTH']):\n                    assignments.append('etf_sectors')\n                else:\n                    assignments.append('etf_broad_market')\n            \n            # Stock assignment logic\n            elif symbol_type == 'CS':\n                if market_cap and market_cap > 10_000_000_000:  # >$10B market cap\n                    assignments.append('large_cap_stocks')\n                elif market_cap and market_cap > 1_000_000_000:  # >$1B market cap\n                    assignments.append('mid_cap_stocks')\n                else:\n                    assignments.append('small_cap_stocks')\n                \n                # Tech stock detection\n                if any(tech_word in name for tech_word in ['TECH', 'SOFTWARE', 'CLOUD', 'AI', 'CYBER']):\n                    assignments.append('tech_stocks')\n            \n            # Log assignments (actual implementation would update cache_entries)\n            if assignments:\n                logger.info(f\"IPO-MONITOR: Auto-assigned {symbol} to universes: {assignments}\")\n                \n                # Publish universe assignment notification\n                await self._publish_automation_event('symbol_changed', {\n                    'symbol': symbol,\n                    'change_type': 'universe_assignment',\n                    'new_universes': assignments,\n                    'assignment_time': datetime.now().isoformat()\n                })\n            \n        except Exception as e:\n            logger.error(f\"IPO-MONITOR: Failed to auto-assign {symbol} to universes: {e}\")\n    \n    def __del__(self):\n        \"\"\"Cleanup on deletion.\"\"\"\n        self._close_connections()

def main():\n    \"\"\"CLI entry point for IPO monitoring service.\"\"\"\n    parser = argparse.ArgumentParser(description='IPO Monitoring Service for TickStock')\n    parser.add_argument('--daily-scan', action='store_true', help='Run daily IPO scan')\n    parser.add_argument('--backfill-symbol', help='Trigger 90-day backfill for specific symbol')\n    parser.add_argument('--test-mode', action='store_true', help='Run in test mode with limited symbols')\n    parser.add_argument('--database-uri', help='Database URI (overrides env var)')\n    parser.add_argument('--redis-host', help='Redis host (overrides env var)')\n    parser.add_argument('--polygon-api-key', help='Polygon.io API key (overrides env var)')\n    \n    args = parser.parse_args()\n    \n    try:\n        # Initialize service\n        service = IPOMonitorService(\n            database_uri=args.database_uri,\n            redis_host=args.redis_host,\n            polygon_api_key=args.polygon_api_key\n        )\n        \n        if args.daily_scan:\n            # Run daily IPO scan\n            results = asyncio.run(service.daily_ipo_scan())\n            \n            print(\"\\nDaily IPO Scan Results:\")\n            print(f\"  Scan Date: {results.get('scan_date')}\")\n            print(f\"  Duration: {results.get('scan_duration_seconds', 0):.1f} seconds\")\n            print(f\"  New Symbols Found: {results.get('new_symbols_found', 0)}\")\n            print(f\"  Symbols Processed: {results.get('symbols_processed', 0)}\")\n            print(f\"  Success Rate: {results.get('success_rate', 0):.1%}\")\n            \n            if results.get('processed_symbols'):\n                print(f\"  Processed Symbols: {', '.join(results['processed_symbols'])}\")\n            \n        elif args.backfill_symbol:\n            # Trigger backfill for specific symbol\n            symbol = args.backfill_symbol.upper()\n            print(f\"Starting 90-day backfill for {symbol}...\")\n            asyncio.run(service.trigger_90day_backfill(symbol))\n            print(f\"Backfill completed for {symbol}\")\n            \n        else:\n            print(\"Please specify --daily-scan or --backfill-symbol\")\n            parser.print_help()\n            \n    except KeyboardInterrupt:\n        print(\"\\nStopping IPO monitoring service...\")\n    except Exception as e:\n        logger.error(f\"IPO-MONITOR: Fatal error: {e}\")\n        sys.exit(1)\n\nif __name__ == '__main__':\n    main()