"""
Massive WebSocket Multi-Connection Test Utility

Tests multiple concurrent WebSocket connections to Massive API.
Specifically tests the aggregates (per-minute bars) endpoint.

Based on: https://massive.com/docs/websocket/stocks/aggregates-per-minute

Usage:
    python scripts/dev_tools/util_massive_websocket_test.py
    python scripts/dev_tools/util_massive_websocket_test.py --connections 3 --symbols SPY,QQQ,XLF
    python scripts/dev_tools/util_massive_websocket_test.py --duration 60 --verbose
"""

import argparse
import asyncio
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import websockets

from src.core.services.config_manager import ConfigManager

class MassiveWebSocketTester:
    """Test multiple concurrent WebSocket connections to Massive API"""

    def __init__(self, api_key, num_connections=1, verbose=False):
        """
        Initialize WebSocket tester

        Args:
            api_key: Massive API key
            num_connections: Number of concurrent connections to test
            verbose: Show detailed message output
        """
        self.api_key = api_key
        self.num_connections = num_connections
        self.verbose = verbose

        # WebSocket URL (stocks aggregates per minute)
        self.ws_url = "wss://socket.massive.com/stocks"

        # Connection stats
        self.connections = {}
        self.stats = defaultdict(lambda: {
            'messages_received': 0,
            'bars_received': 0,
            'symbols_seen': set(),
            'errors': 0,
            'connected_at': None,
            'last_message_at': None
        })

    async def connect_and_subscribe(self, connection_id, symbols):
        """
        Connect to WebSocket and subscribe to symbols

        Args:
            connection_id: Unique ID for this connection
            symbols: List of symbols to subscribe to

        Returns:
            WebSocket connection or None on error
        """
        try:
            print(f"\n[Conn {connection_id}] Connecting to {self.ws_url}...")

            ws = await websockets.connect(self.ws_url)
            self.connections[connection_id] = ws
            self.stats[connection_id]['connected_at'] = datetime.now()

            print(f"[Conn {connection_id}] ✅ Connected")

            # Authenticate
            auth_msg = {
                "action": "auth",
                "params": self.api_key
            }
            await ws.send(json.dumps(auth_msg))
            print(f"[Conn {connection_id}] 🔑 Authentication sent")

            # Wait for auth response
            auth_response = await ws.recv()
            auth_data = json.loads(auth_response)

            if auth_data[0].get('status') == 'auth_success':
                print(f"[Conn {connection_id}] ✅ Authenticated successfully")
            else:
                print(f"[Conn {connection_id}] ❌ Authentication failed: {auth_data}")
                return None

            # Subscribe to symbols (minute aggregates)
            subscribe_msg = {
                "action": "subscribe",
                "params": f"AM.{',AM.'.join(symbols)}"  # AM = Aggregates per Minute
            }
            await ws.send(json.dumps(subscribe_msg))
            print(f"[Conn {connection_id}] 📡 Subscribed to {len(symbols)} symbols: {', '.join(symbols)}")

            return ws

        except Exception as e:
            print(f"[Conn {connection_id}] ❌ Connection error: {e}")
            self.stats[connection_id]['errors'] += 1
            return None

    async def listen_to_connection(self, connection_id, ws, duration):
        """
        Listen to WebSocket messages for specified duration

        Args:
            connection_id: Connection identifier
            ws: WebSocket connection
            duration: How long to listen (seconds)
        """
        start_time = time.time()
        print(f"[Conn {connection_id}] 👂 Listening for {duration} seconds...")

        try:
            while time.time() - start_time < duration:
                try:
                    # Receive with timeout
                    message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    self.stats[connection_id]['messages_received'] += 1
                    self.stats[connection_id]['last_message_at'] = datetime.now()

                    # Parse message
                    data = json.loads(message)

                    # Handle different message types
                    if isinstance(data, list):
                        for msg in data:
                            self._process_message(connection_id, msg)
                    else:
                        self._process_message(connection_id, data)

                except asyncio.TimeoutError:
                    # No message received in timeout window
                    if self.verbose:
                        print(f"[Conn {connection_id}] ⏳ No messages in last 5 seconds")
                    continue

        except websockets.exceptions.ConnectionClosed:
            print(f"[Conn {connection_id}] 🔌 Connection closed by server")
            self.stats[connection_id]['errors'] += 1

        except Exception as e:
            print(f"[Conn {connection_id}] ❌ Error listening: {e}")
            self.stats[connection_id]['errors'] += 1

        finally:
            # Close connection
            try:
                await ws.close()
                print(f"[Conn {connection_id}] 🔌 Connection closed")
            except:
                pass

    def _process_message(self, connection_id, msg):
        """
        Process a single WebSocket message

        Args:
            connection_id: Connection identifier
            msg: Message data (dict)
        """
        msg_type = msg.get('ev')  # Event type

        if msg_type == 'AM':
            # Aggregate per minute bar
            self.stats[connection_id]['bars_received'] += 1
            symbol = msg.get('sym')
            if symbol:
                self.stats[connection_id]['symbols_seen'].add(symbol)

            if self.verbose:
                print(f"[Conn {connection_id}] 📊 Bar: {symbol} "
                      f"O={msg.get('o')} H={msg.get('h')} "
                      f"L={msg.get('l')} C={msg.get('c')} "
                      f"V={msg.get('v')}")

        elif msg_type == 'status':
            status_msg = msg.get('message', 'Unknown status')
            print(f"[Conn {connection_id}] ℹ️  Status: {status_msg}")

        elif self.verbose:
            print(f"[Conn {connection_id}] 📨 Message type: {msg_type}")

    async def run_test(self, symbols_per_connection, duration):
        """
        Run multi-connection test

        Args:
            symbols_per_connection: List of symbol lists (one per connection)
            duration: How long to run test (seconds)
        """
        print("\n" + "=" * 70)
        print(f"MASSIVE WEBSOCKET MULTI-CONNECTION TEST")
        print("=" * 70)
        print(f"Connections: {self.num_connections}")
        print(f"Duration: {duration} seconds")
        print(f"Total symbols: {sum(len(symbols) for symbols in symbols_per_connection)}")
        print("=" * 70)

        # Connect all connections
        tasks = []
        for i in range(self.num_connections):
            connection_id = i + 1
            symbols = symbols_per_connection[i] if i < len(symbols_per_connection) else []

            if not symbols:
                print(f"[Conn {connection_id}] ⚠️  No symbols assigned, skipping")
                continue

            # Connect and subscribe
            ws = await self.connect_and_subscribe(connection_id, symbols)
            if ws:
                # Start listening
                task = asyncio.create_task(
                    self.listen_to_connection(connection_id, ws, duration)
                )
                tasks.append(task)

        if not tasks:
            print("\n❌ No connections established, exiting")
            return

        # Wait for all connections to complete
        print(f"\n⏱️  Test running for {duration} seconds...\n")
        await asyncio.gather(*tasks)

        # Print results
        self.print_results()

    def print_results(self):
        """Print test results summary"""
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)

        total_messages = 0
        total_bars = 0
        total_symbols = set()
        total_errors = 0

        for connection_id, stats in sorted(self.stats.items()):
            print(f"\nConnection {connection_id}:")
            print(f"  Connected at:      {stats['connected_at'].strftime('%H:%M:%S') if stats['connected_at'] else 'N/A'}")
            print(f"  Last message at:   {stats['last_message_at'].strftime('%H:%M:%S') if stats['last_message_at'] else 'N/A'}")
            print(f"  Messages received: {stats['messages_received']}")
            print(f"  Bars received:     {stats['bars_received']}")
            print(f"  Symbols seen:      {len(stats['symbols_seen'])} - {', '.join(sorted(stats['symbols_seen']))}")
            print(f"  Errors:            {stats['errors']}")

            if stats['connected_at'] and stats['last_message_at']:
                duration = (stats['last_message_at'] - stats['connected_at']).total_seconds()
                if duration > 0:
                    rate = stats['messages_received'] / duration
                    print(f"  Message rate:      {rate:.2f} msgs/sec")

            total_messages += stats['messages_received']
            total_bars += stats['bars_received']
            total_symbols.update(stats['symbols_seen'])
            total_errors += stats['errors']

        print(f"\n{'─' * 70}")
        print(f"TOTALS:")
        print(f"  Active connections: {len(self.stats)}")
        print(f"  Total messages:     {total_messages}")
        print(f"  Total bars:         {total_bars}")
        print(f"  Unique symbols:     {len(total_symbols)}")
        print(f"  Total errors:       {total_errors}")

        if total_messages > 0:
            print(f"\n✅ Test successful - {total_messages} messages received")
        else:
            print(f"\n⚠️  No messages received - check market hours and subscriptions")

def distribute_symbols(symbols, num_connections):
    """
    Distribute symbols evenly across connections

    Args:
        symbols: List of all symbols
        num_connections: Number of connections

    Returns:
        List of symbol lists (one per connection)
    """
    result = [[] for _ in range(num_connections)]

    for i, symbol in enumerate(symbols):
        connection_idx = i % num_connections
        result[connection_idx].append(symbol)

    return result

def main():
    parser = argparse.ArgumentParser(
        description='Test multiple concurrent WebSocket connections to Massive API'
    )
    parser.add_argument(
        '--connections', '-c',
        type=int,
        default=1,
        help='Number of concurrent connections to test (default: 1, max: 3)'
    )
    parser.add_argument(
        '--symbols', '-s',
        default='SPY,QQQ,XLF,XLE,XLK,XLV,XLI,DIA,IWM,GLD',
        help='Comma-separated list of symbols to test'
    )
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=30,
        help='Test duration in seconds (default: 30)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed message output'
    )

    args = parser.parse_args()

    # Validate connections
    if args.connections < 1:
        print("❌ Must have at least 1 connection")
        sys.exit(1)
    if args.connections > 3:
        print("⚠️  Warning: Massive API typically limits to 3 concurrent connections")

    # Get API key
    config_manager = ConfigManager()
    config_manager.load_from_env()
    config = config_manager.get_config()
    api_key = config.get('MASSIVE_API_KEY')

    if not api_key:
        print("❌ ERROR: MASSIVE_API_KEY not found in configuration")
        print("Set MASSIVE_API_KEY in your .env file")
        sys.exit(1)

    # Parse symbols
    symbols = [s.strip().upper() for s in args.symbols.split(',')]

    # Distribute symbols across connections
    symbols_per_connection = distribute_symbols(symbols, args.connections)

    # Print distribution
    print("\nSymbol Distribution:")
    for i, conn_symbols in enumerate(symbols_per_connection):
        print(f"  Connection {i+1}: {len(conn_symbols)} symbols - {', '.join(conn_symbols)}")

    # Create tester
    tester = MassiveWebSocketTester(
        api_key=api_key,
        num_connections=args.connections,
        verbose=args.verbose
    )

    # Run test
    try:
        asyncio.run(tester.run_test(symbols_per_connection, args.duration))
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        tester.print_results()
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
