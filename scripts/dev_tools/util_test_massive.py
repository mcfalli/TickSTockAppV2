"""
Massive API Connection Test Utility

Simple utility to test both REST API and WebSocket connections to Massive.com
using configuration from .env file.

Usage:
    python scripts/dev_tools/util_test_massive.py
    python scripts/dev_tools/util_test_massive.py --rest-only
    python scripts/dev_tools/util_test_massive.py --websocket-only
    python scripts/dev_tools/util_test_massive.py --symbols SPY,QQQ,AAPL --duration 60
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import requests

from src.core.services.config_manager import ConfigManager


class MassiveAPITester:
    """Test Massive API REST and WebSocket connections"""

    def __init__(self, api_key, verbose=False):
        """
        Initialize tester

        Args:
            api_key: Massive API key from .env
            verbose: Show detailed output
        """
        self.api_key = api_key
        self.verbose = verbose
        self.rest_base_url = "https://api.massive.com"
        self.websocket_url = "wss://socket.massive.com/stocks"

    def test_rest_api(self, test_ticker="AAPL"):
        """
        Test REST API endpoints

        Args:
            test_ticker: Symbol to use for testing

        Returns:
            bool: True if all tests passed
        """
        print("\n" + "=" * 70)
        print("MASSIVE REST API TEST")
        print("=" * 70)
        print(f"Base URL: {self.rest_base_url}")
        print(f"Test Ticker: {test_ticker}")
        print(f"API Key: {'*****' + self.api_key[-4:]}")
        print("=" * 70)

        # Calculate dates for historical data (previous week)
        today = datetime.now()
        prev_week = today - timedelta(days=7)
        start_date = prev_week.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        # Test endpoints
        endpoints = [
            {
                "path": "/v1/marketstatus/now",
                "description": "Market Status",
                "params": {}
            },
            {
                "path": f"/v2/aggs/ticker/{test_ticker}/range/1/day/{start_date}/{end_date}",
                "description": f"Historical Aggregates ({test_ticker})",
                "params": {"adjusted": "true"}
            },
            {
                "path": f"/v2/last/trade/{test_ticker}",
                "description": f"Last Trade ({test_ticker})",
                "params": {}
            },
            {
                "path": "/v3/reference/tickers",
                "description": "Ticker List",
                "params": {"active": "true", "limit": 5, "market": "stocks"}
            }
        ]

        success_count = 0
        total_count = len(endpoints)

        for test in endpoints:
            print(f"\n{'-' * 70}")
            print(f"Testing: {test['description']}")
            print(f"Endpoint: {test['path']}")

            try:
                # Add API key to params
                params = {"apiKey": self.api_key, **test['params']}

                # Make request
                start_time = time.time()
                response = requests.get(
                    f"{self.rest_base_url}{test['path']}",
                    params=params,
                    timeout=10
                )
                elapsed = time.time() - start_time

                print(f"Status: {response.status_code}")
                print(f"Response Time: {elapsed:.3f}s")

                if self.verbose:
                    print(f"Rate Limit Remaining: {response.headers.get('X-Ratelimit-Remaining', 'N/A')}")

                if response.status_code == 200:
                    print("✅ SUCCESS")
                    success_count += 1

                    # Show sample data
                    if self.verbose:
                        data = response.json()
                        if isinstance(data, dict):
                            if 'results' in data:
                                print(f"Results Count: {len(data['results'])}")
                                if data['results']:
                                    print(f"Sample: {json.dumps(data['results'][0], indent=2)}")
                            elif 'status' in data:
                                print(f"Market Status: {data['status']}")
                else:
                    print(f"❌ FAILED: {response.text[:200]}")

            except Exception as e:
                print(f"❌ ERROR: {e}")

        # Summary
        print(f"\n{'=' * 70}")
        print(f"REST API RESULTS: {success_count}/{total_count} tests passed")
        print("=" * 70)

        return success_count == total_count

    async def test_websocket(self, symbols=None, duration=30):
        """
        Test WebSocket connection

        Args:
            symbols: List of symbols to subscribe to
            duration: How long to listen (seconds)

        Returns:
            bool: True if test passed
        """
        # Import websockets only when needed
        try:
            import websockets
        except ImportError:
            print("\n❌ ERROR: 'websockets' package not installed")
            print("Install it with: pip install websockets")
            return False

        if symbols is None:
            symbols = ["SPY", "QQQ", "AAPL"]

        print("\n" + "=" * 70)
        print("MASSIVE WEBSOCKET TEST")
        print("=" * 70)
        print(f"URL: {self.websocket_url}")
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Duration: {duration}s")
        print(f"API Key: {'*****' + self.api_key[-4:]}")
        print("=" * 70)

        stats = {
            'connected': False,
            'authenticated': False,
            'messages_received': 0,
            'bars_received': 0,
            'symbols_seen': set(),
            'errors': []
        }

        try:
            # Connect
            print(f"\n[1/4] Connecting to WebSocket...")
            ws = await websockets.connect(self.websocket_url)
            stats['connected'] = True
            print("✅ Connected")

            # Authenticate
            print(f"\n[2/4] Authenticating...")
            auth_msg = {
                "action": "auth",
                "params": self.api_key
            }
            await ws.send(json.dumps(auth_msg))

            # Wait for auth response
            auth_response = await asyncio.wait_for(ws.recv(), timeout=10)
            auth_data = json.loads(auth_response)

            if isinstance(auth_data, list) and auth_data[0].get('status') == 'auth_success':
                stats['authenticated'] = True
                print(f"✅ Authenticated")
            else:
                print(f"❌ Authentication failed: {auth_data}")
                stats['errors'].append(f"Auth failed: {auth_data}")
                await ws.close()
                return False

            # Subscribe
            print(f"\n[3/4] Subscribing to {len(symbols)} symbols...")
            subscribe_msg = {
                "action": "subscribe",
                "params": f"AM.{',AM.'.join(symbols)}"  # AM = Aggregates per Minute
            }
            await ws.send(json.dumps(subscribe_msg))
            print(f"✅ Subscription sent")

            # Listen for messages
            print(f"\n[4/4] Listening for data (up to {duration}s)...")
            start_time = time.time()

            while time.time() - start_time < duration:
                try:
                    # Receive with timeout
                    message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    stats['messages_received'] += 1

                    # Parse message
                    data = json.loads(message)

                    # Process messages
                    if isinstance(data, list):
                        for msg in data:
                            self._process_websocket_message(msg, stats)
                    else:
                        self._process_websocket_message(data, stats)

                except asyncio.TimeoutError:
                    if self.verbose:
                        print("  ⏳ Waiting for messages...")
                    continue

            # Close connection
            await ws.close()
            print("\n🔌 Connection closed")

        except websockets.exceptions.WebSocketException as e:
            print(f"\n❌ WebSocket error: {e}")
            stats['errors'].append(str(e))
            return False

        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            stats['errors'].append(str(e))
            return False

        # Print results
        print(f"\n{'=' * 70}")
        print("WEBSOCKET RESULTS")
        print("=" * 70)
        print(f"Connected:         {'✅ Yes' if stats['connected'] else '❌ No'}")
        print(f"Authenticated:     {'✅ Yes' if stats['authenticated'] else '❌ No'}")
        print(f"Messages Received: {stats['messages_received']}")
        print(f"Bars Received:     {stats['bars_received']}")
        print(f"Symbols Seen:      {len(stats['symbols_seen'])} - {', '.join(sorted(stats['symbols_seen']))}")
        print(f"Errors:            {len(stats['errors'])}")

        if stats['errors']:
            print(f"\nErrors:")
            for error in stats['errors']:
                print(f"  - {error}")

        print("=" * 70)

        # Success if authenticated and received some data
        success = stats['authenticated'] and stats['messages_received'] > 0

        if success:
            print(f"\n✅ WebSocket test PASSED - Received {stats['bars_received']} bars")
        elif stats['messages_received'] == 0:
            print(f"\n⚠️  No data received - This is normal outside market hours")
            print(f"    Market Status: Pre-market (4-9:30 AM ET), Regular (9:30 AM-4 PM ET), After-hours (4-8 PM ET)")
        else:
            print(f"\n❌ WebSocket test FAILED")

        return success

    def _process_websocket_message(self, msg, stats):
        """
        Process a single WebSocket message

        Args:
            msg: Message dict
            stats: Stats dict to update
        """
        msg_type = msg.get('ev')  # Event type

        if msg_type == 'AM':
            # Aggregate per minute bar
            stats['bars_received'] += 1
            symbol = msg.get('sym')
            if symbol:
                stats['symbols_seen'].add(symbol)

            if self.verbose:
                print(f"  📊 {symbol}: O={msg.get('o')} H={msg.get('h')} "
                      f"L={msg.get('l')} C={msg.get('c')} V={msg.get('v')}")

        elif msg_type == 'status':
            status_msg = msg.get('message', 'Unknown')
            print(f"  ℹ️  Status: {status_msg}")

        elif self.verbose:
            print(f"  📨 Message: {msg_type}")


def main():
    parser = argparse.ArgumentParser(
        description='Test Massive API REST and WebSocket connections'
    )
    parser.add_argument(
        '--rest-only',
        action='store_true',
        help='Test REST API only (skip WebSocket)'
    )
    parser.add_argument(
        '--websocket-only',
        action='store_true',
        help='Test WebSocket only (skip REST)'
    )
    parser.add_argument(
        '--symbols', '-s',
        default='SPY,QQQ,AAPL',
        help='Comma-separated symbols for WebSocket test (default: SPY,QQQ,AAPL)'
    )
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=30,
        help='WebSocket test duration in seconds (default: 30)'
    )
    parser.add_argument(
        '--ticker', '-t',
        default='AAPL',
        help='Ticker for REST API test (default: AAPL)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )

    args = parser.parse_args()

    # Load configuration from .env
    print("\n" + "=" * 70)
    print("MASSIVE API TEST UTILITY")
    print("=" * 70)
    print(f"Loading configuration from .env...")

    config_manager = ConfigManager()
    config_manager.load_from_env()
    config = config_manager.get_config()
    api_key = config.get('MASSIVE_API_KEY')

    if not api_key:
        print("❌ ERROR: MASSIVE_API_KEY not found in .env file")
        print("Please set MASSIVE_API_KEY in your .env file")
        sys.exit(1)

    print(f"✅ API Key loaded: {'*****' + api_key[-4:]}")

    # Create tester
    tester = MassiveAPITester(api_key=api_key, verbose=args.verbose)

    # Run tests
    rest_passed = True
    websocket_passed = True

    if not args.websocket_only:
        rest_passed = tester.test_rest_api(test_ticker=args.ticker)

    if not args.rest_only:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
        try:
            websocket_passed = asyncio.run(
                tester.test_websocket(symbols=symbols, duration=args.duration)
            )
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
        except Exception as e:
            print(f"\n\n❌ WebSocket test error: {e}")
            websocket_passed = False

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    if not args.websocket_only:
        print(f"REST API:   {'✅ PASSED' if rest_passed else '❌ FAILED'}")

    if not args.rest_only:
        print(f"WebSocket:  {'✅ PASSED' if websocket_passed else '⚠️  NO DATA (see note above)'}")

    print("=" * 70)

    # Exit code
    if (not args.websocket_only and not rest_passed) or (not args.rest_only and not websocket_passed):
        sys.exit(1)


if __name__ == '__main__':
    main()
