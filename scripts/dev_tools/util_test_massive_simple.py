"""
Simple Massive API Connection Test

Standalone utility to test Massive API without importing application code.
Uses python-dotenv to read .env directly.

Usage:
    python scripts/dev_tools/util_test_massive_simple.py
    python scripts/dev_tools/util_test_massive_simple.py --rest-only
    python scripts/dev_tools/util_test_massive_simple.py --websocket-only
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests


def load_api_key():
    """Load API key from .env file"""
    env_path = Path(__file__).parent.parent.parent / '.env'

    if not env_path.exists():
        print(f"❌ ERROR: .env file not found at {env_path}")
        return None

    # Simple .env parser
    api_key = None
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('MASSIVE_API_KEY='):
                api_key = line.split('=', 1)[1].strip()
                break

    return api_key


def test_rest_api(api_key, test_ticker="AAPL", verbose=False):
    """Test REST API endpoints"""

    print("\n" + "=" * 70)
    print("MASSIVE REST API TEST")
    print("=" * 70)
    print(f"Base URL: https://api.massive.com")
    print(f"Test Ticker: {test_ticker}")
    print(f"API Key: {'*****' + api_key[-4:]}")
    print("=" * 70)

    # Calculate dates
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

    for test in endpoints:
        print(f"\n{'-' * 70}")
        print(f"Testing: {test['description']}")
        print(f"Endpoint: {test['path']}")

        try:
            # Add API key
            params = {"apiKey": api_key, **test['params']}

            # Make request
            start_time = time.time()
            response = requests.get(
                f"https://api.massive.com{test['path']}",
                params=params,
                timeout=10
            )
            elapsed = time.time() - start_time

            print(f"Status: {response.status_code}")
            print(f"Response Time: {elapsed:.3f}s")

            if response.status_code == 200:
                print("✅ SUCCESS")
                success_count += 1

                if verbose:
                    data = response.json()
                    print(f"Response sample: {json.dumps(data, indent=2)[:200]}...")
            else:
                print(f"❌ FAILED")
                if verbose:
                    print(f"Response: {response.text[:200]}")

        except Exception as e:
            print(f"❌ ERROR: {e}")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"REST API RESULTS: {success_count}/{len(endpoints)} tests passed")
    print("=" * 70)

    return success_count == len(endpoints)


def test_websocket(api_key, symbols=None, duration=30, verbose=False, aggregate_type="A"):
    """Test WebSocket connection using existing project pattern
    
    Args:
        aggregate_type: "A" for per-second, "AM" for per-minute aggregates
    """

    # Import websocket-client (same as project uses)
    try:
        import websocket
        import threading
    except ImportError:
        print("\n❌ ERROR: 'websocket-client' package not installed")
        print("Install it with: pip install websocket-client")
        return False

    if symbols is None:
        symbols = ["SPY", "QQQ", "AAPL"]

    print("\n" + "=" * 70)
    print("MASSIVE WEBSOCKET TEST")
    print("=" * 70)
    print(f"URL: wss://socket.massive.com/stocks")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Duration: {duration}s")
    print(f"API Key: {'*****' + api_key[-4:]}")
    print("=" * 70)

    stats = {
        'connected': False,
        'authenticated': False,
        'messages_received': 0,
        'bars_received': 0,
        'symbols_seen': set(),
        'start_time': None
    }

    def on_open(ws):
        """Called when WebSocket connection opens"""
        print("\n[1/3] ✅ Connected")
        stats['connected'] = True

        # Authenticate (same as project code)
        print("[2/3] Authenticating...")
        auth_msg = {"action": "auth", "params": api_key}
        ws.send(json.dumps(auth_msg))

    def on_message(ws, message):
        """Called when message received"""
        stats['messages_received'] += 1

        try:
            data = json.loads(message)

            # Handle auth response
            if isinstance(data, list):
                for msg in data:
                    if msg.get('status') == 'auth_success':
                        stats['authenticated'] = True
                        print("[2/3] ✅ Authenticated")

                        # Subscribe (per-second or per-minute aggregates)
                        print(f"[3/3] Subscribing to {len(symbols)} symbols ({aggregate_type} aggregates)...")
                        formatted_symbols = [f"{aggregate_type}.{sym}" for sym in symbols]
                        subscribe_msg = {
                            "action": "subscribe",
                            "params": ",".join(formatted_symbols)
                        }
                        ws.send(json.dumps(subscribe_msg))
                        print(f"[3/3] ✅ Subscribed")
                        stats['start_time'] = time.time()

                    # Count bars
                    elif msg.get('ev') in ('A', 'AM'):  # Per-second or per-minute aggregate
                        stats['bars_received'] += 1
                        symbol = msg.get('sym')
                        if symbol:
                            stats['symbols_seen'].add(symbol)

                        if verbose:
                            print(f"  📊 {symbol}: O={msg.get('o')} H={msg.get('h')} "
                                  f"L={msg.get('l')} C={msg.get('c')} V={msg.get('v')}")

        except json.JSONDecodeError:
            if verbose:
                print(f"  ⚠️  Non-JSON message: {message[:100]}")

    def on_error(ws, error):
        """Called on error"""
        if verbose:
            print(f"  ❌ Error: {error}")

    def on_close(ws, close_status_code, close_msg):
        """Called when connection closes"""
        if verbose:
            print(f"  🔌 Connection closed: {close_status_code} - {close_msg}")

    # Create WebSocket (same pattern as project)
    print(f"\n[1/3] Connecting...")
    ws = websocket.WebSocketApp(
        "wss://socket.massive.com/stocks",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # Run in thread
    ws_thread = threading.Thread(
        target=ws.run_forever,
        kwargs={'ping_interval': 30, 'ping_timeout': 10}
    )
    ws_thread.daemon = True
    ws_thread.start()

    # Wait for connection and auth
    print("Waiting for connection and authentication...")
    timeout = 10
    start = time.time()
    while time.time() - start < timeout:
        if stats['authenticated']:
            break
        time.sleep(0.5)

    if not stats['authenticated']:
        print("\n❌ Authentication failed or timed out")
        ws.close()
        return False

    # Listen for data
    print(f"\n📡 Listening for {duration} seconds...")
    time.sleep(duration)

    # Close
    ws.close()
    time.sleep(1)

    # Results
    print(f"\n{'=' * 70}")
    print("WEBSOCKET RESULTS")
    print("=" * 70)
    print(f"Connected:     {'✅' if stats['connected'] else '❌'}")
    print(f"Authenticated: {'✅' if stats['authenticated'] else '❌'}")
    print(f"Messages:      {stats['messages_received']}")
    print(f"Bars:          {stats['bars_received']}")
    print(f"Symbols Seen:  {len(stats['symbols_seen'])} - {', '.join(sorted(stats['symbols_seen']))}")
    print("=" * 70)

    if stats['bars_received'] > 0:
        print(f"\n✅ WebSocket test PASSED - Received {stats['bars_received']} bars")
        return True
    elif stats['authenticated']:
        print(f"\n⚠️  No data received (normal outside market hours)")
        print(f"   Market hours: Pre-market 4-9:30 AM, Regular 9:30 AM-4 PM, After 4-8 PM ET")
        return True
    else:
        print(f"\n❌ WebSocket test FAILED")
        return False


def main():
    parser = argparse.ArgumentParser(description='Test Massive API connections')
    parser.add_argument('--rest-only', action='store_true', help='Test REST only')
    parser.add_argument('--websocket-only', action='store_true', help='Test WebSocket only')
    parser.add_argument('--symbols', '-s', default='SPY,QQQ,AAPL', help='Symbols for WebSocket')
    parser.add_argument('--duration', '-d', type=int, default=30, help='WebSocket duration (seconds)')
    parser.add_argument('--ticker', '-t', default='AAPL', help='Ticker for REST test')
    parser.add_argument('--aggregate', '-a', default='A', choices=['A', 'AM'], help='Aggregate type: A (per-second) or AM (per-minute)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("MASSIVE API TEST UTILITY (Simple)")
    print("=" * 70)

    # Load API key
    api_key = load_api_key()
    if not api_key:
        print("❌ ERROR: MASSIVE_API_KEY not found in .env")
        sys.exit(1)

    print(f"✅ API Key loaded: {'*****' + api_key[-4:]}")

    # Run tests
    rest_passed = True
    websocket_passed = True

    if not args.websocket_only:
        rest_passed = test_rest_api(api_key, args.ticker, args.verbose)

    if not args.rest_only:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
        try:
            websocket_passed = test_websocket(api_key, symbols, args.duration, args.verbose, args.aggregate)
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted")
        except Exception as e:
            print(f"\n\n❌ WebSocket error: {e}")
            import traceback
            traceback.print_exc()
            websocket_passed = False

    # Summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    if not args.websocket_only:
        print(f"REST API:   {'✅ PASSED' if rest_passed else '❌ FAILED'}")

    if not args.rest_only:
        print(f"WebSocket:  {'✅ PASSED' if websocket_passed else '❌ FAILED'}")

    print("=" * 70)

    sys.exit(0 if (rest_passed and websocket_passed) else 1)


if __name__ == '__main__':
    main()
