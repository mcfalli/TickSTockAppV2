#!/usr/bin/env python3
"""
Diagnostic Script: Check Redis Pattern/Indicator Event Publishing
Purpose: Monitor Redis channels to verify TickStockPL is publishing events
Date: 2025-10-15

This script listens to Redis channels and reports what events are being published.
Use this to diagnose why UI is not showing pattern/indicator detections.
"""

import json
import redis
import sys
import time
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Configure Redis connection
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 0

# Channels to monitor (TickStockAppV2 is subscribed to these)
CHANNELS = [
    'tickstock:patterns:streaming',
    'tickstock:patterns:detected',
    'tickstock:indicators:streaming',
    'tickstock.events.patterns',  # Legacy channel
    'tickstock.events.indicators',  # Legacy channel
]

def main():
    print("="*80)
    print("REDIS PATTERN/INDICATOR EVENT MONITOR")
    print("="*80)
    print(f"\nMonitoring Redis channels for pattern/indicator events...")
    print(f"Host: {REDIS_HOST}:{REDIS_PORT}")
    print(f"Channels: {', '.join(CHANNELS)}\n")
    print("Press Ctrl+C to stop\n")
    print("-"*80)

    try:
        # Connect to Redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        r.ping()
        print(f"✓ Connected to Redis\n")

        # Subscribe to channels
        pubsub = r.pubsub()
        pubsub.subscribe(*CHANNELS)
        print(f"✓ Subscribed to {len(CHANNELS)} channels\n")

        # Event counters
        event_counts = {channel: 0 for channel in CHANNELS}
        total_events = 0
        start_time = time.time()

        print(f"{'Time':<12} | {'Channel':<35} | {'Event Type':<20} | {'Symbol':<10} | {'Details'}")
        print("-"*120)

        # Listen for messages
        for message in pubsub.listen():
            if message['type'] == 'subscribe':
                channel = message['channel']
                print(f"\n[SUBSCRIBED] {channel}")
                continue

            if message['type'] != 'message':
                continue

            # Process message
            total_events += 1
            channel = message['channel']
            event_counts[channel] += 1

            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]

            try:
                # Parse JSON data
                data = json.loads(message['data'])

                # Extract event details
                event_type = data.get('type', data.get('event_type', 'unknown'))
                symbol = data.get('symbol', data.get('detection', {}).get('symbol', 'N/A'))

                # Get pattern/indicator specific details
                if 'pattern_type' in data:
                    details = f"Pattern: {data['pattern_type']}, Conf: {data.get('confidence', 'N/A')}"
                elif 'indicator_type' in data:
                    details = f"Indicator: {data['indicator_type']}, Value: {data.get('value', 'N/A')}"
                elif 'detection' in data:
                    det = data['detection']
                    details = f"Pattern: {det.get('pattern_type', 'N/A')}, Conf: {det.get('confidence', 'N/A')}"
                elif 'calculation' in data:
                    calc = data['calculation']
                    details = f"Indicator: {calc.get('indicator_type', 'N/A')}"
                else:
                    details = f"Data keys: {', '.join(data.keys())}"

                print(f"{timestamp:<12} | {channel:<35} | {event_type:<20} | {symbol:<10} | {details}")

            except json.JSONDecodeError:
                print(f"{timestamp:<12} | {channel:<35} | {'[JSON ERROR]':<20} | {'N/A':<10} | Raw: {message['data'][:50]}")
            except Exception as e:
                print(f"{timestamp:<12} | {channel:<35} | {'[ERROR]':<20} | {'N/A':<10} | {str(e)}")

            # Print summary every 30 seconds
            if total_events % 10 == 0:
                runtime = time.time() - start_time
                print(f"\n--- SUMMARY (Runtime: {runtime:.0f}s) ---")
                print(f"Total events received: {total_events}")
                for ch, count in event_counts.items():
                    if count > 0:
                        print(f"  {ch}: {count} events")
                print("-"*120 + "\n")

    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("MONITORING STOPPED")
        print("="*80)

        runtime = time.time() - start_time
        print(f"\nRuntime: {runtime:.0f} seconds")
        print(f"Total events received: {total_events}")
        print("\nEvent breakdown by channel:")
        for channel, count in event_counts.items():
            status = "✓" if count > 0 else "✗"
            print(f"  {status} {channel:<35} : {count:>5} events")

        if total_events == 0:
            print("\n⚠ WARNING: NO EVENTS RECEIVED")
            print("\nPossible causes:")
            print("  1. TickStockPL is not running")
            print("  2. TickStockPL is not publishing to Redis")
            print("  3. TickStockPL is using different channel names")
            print("  4. Pattern/Indicator jobs in TickStockPL are not running")
            print("\nNext steps:")
            print("  - Check TickStockPL logs for pattern/indicator job activity")
            print("  - Verify TickStockPL Redis configuration")
            print("  - Confirm TickStockPL streaming session is active")
        else:
            print("\n✓ Events are being published to Redis")
            print("\nIf UI is not showing patterns/indicators, check:")
            print("  - TickStockAppV2 logs for subscription confirmation")
            print("  - WebSocket connection status in browser")
            print("  - Browser console for JavaScript errors")

    except redis.ConnectionError as e:
        print(f"\n❌ Redis connection error: {e}")
        print("\nCheck that Redis is running:")
        print("  redis-cli ping")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
