#!/usr/bin/env python3
"""
Test script to verify real monitoring data flow from TickStockPL
"""

import json
import sys
import time
from pathlib import Path

import redis

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def check_redis_monitoring_events():
    """Subscribe to Redis and check for monitoring events from TickStockPL."""

    print("=" * 60)
    print("Testing TickStockPL Monitoring Integration")
    print("=" * 60)

    # Connect to Redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("[OK] Redis connected")
    except redis.ConnectionError:
        print("[FAIL] Cannot connect to Redis. Make sure Redis is running.")
        return False

    # Subscribe to monitoring channel
    pubsub = r.pubsub()
    pubsub.subscribe('tickstock:monitoring')
    print("[OK] Subscribed to tickstock:monitoring channel")

    print("\nWaiting for events from TickStockPL...")
    print("Make sure TickStockPL monitoring is running:")
    print("  cd ../TickStockPL && python scripts/run_monitoring.py")
    print("\nListening for 30 seconds...\n")

    # Listen for events
    start_time = time.time()
    event_count = 0
    event_types = set()

    while time.time() - start_time < 30:
        message = pubsub.get_message(timeout=1.0)

        if message and message['type'] == 'message':
            try:
                event = json.loads(message['data'])
                event_type = event.get('event_type', 'UNKNOWN')
                event_count += 1
                event_types.add(event_type)

                print(f"[EVENT {event_count}] {event_type}")

                # Show key metrics
                if event_type == 'METRIC_UPDATE':
                    metrics = event.get('metrics', {})
                    system = metrics.get('system', {})
                    health = event.get('health_score', {})

                    print(f"  CPU: {system.get('cpu_percent', 'N/A')}%")
                    print(f"  Memory: {system.get('memory_percent', 'N/A')}%")
                    print(f"  Health Score: {health.get('overall', 'N/A')}")
                    print(f"  Status: {health.get('status', 'N/A')}")

                elif event_type == 'ALERT_TRIGGERED':
                    alert = event.get('alert', {})
                    print(f"  Level: {alert.get('level', 'N/A')}")
                    print(f"  Message: {alert.get('message', 'N/A')}")

                print()

            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse event: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total events received: {event_count}")
    print(f"  Event types: {', '.join(event_types) if event_types else 'None'}")

    if event_count > 0:
        print("\n[SUCCESS] TickStockPL monitoring is working!")
        print("\nTo see this data in the dashboard:")
        print("  1. Start TickStockAppV2: python src/app.py")
        print("  2. Navigate to: http://localhost:5000/admin/monitoring")
        print("  3. Data will update automatically every 5 seconds")
        return True
    print("\n[WARNING] No events received!")
    print("\nTroubleshooting:")
    print("  1. Is TickStockPL monitoring running?")
    print("     cd ../TickStockPL && python scripts/run_monitoring.py")
    print("  2. Is Redis running on localhost:6379?")
    print("  3. Check TickStockPL logs for errors")
    return False


def test_app_endpoint():
    """Test if the monitoring endpoint is working in TickStockAppV2."""

    print("\n" + "=" * 60)
    print("Testing TickStockAppV2 Monitoring Endpoint")
    print("=" * 60)

    try:
        import requests

        # Try to get monitoring status
        response = requests.get('http://localhost:5000/api/admin/monitoring/status', timeout=5)

        if response.ok:
            data = response.json()
            print("[OK] Monitoring endpoint is accessible")

            if data.get('latest_update'):
                print(f"[OK] Latest update: {data['latest_update']}")
                print(f"[OK] Active alerts: {data.get('active_alerts', 0)}")
                print(f"[OK] Health score: {data.get('health_score', 'N/A')}")

                if data.get('latest_metrics'):
                    print("[OK] Real metrics are available!")
                else:
                    print("[WARNING] No metrics data yet")
            else:
                print("[WARNING] No monitoring data received yet")

            return True
        print(f"[FAIL] Endpoint returned status: {response.status_code}")
        return False

    except requests.ConnectionError:
        print("[FAIL] Cannot connect to TickStockAppV2")
        print("Make sure the app is running: python src/app.py")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


if __name__ == "__main__":
    print("\nThis script will test the real monitoring data flow.\n")

    # Test 1: Check Redis events
    redis_ok = check_redis_monitoring_events()

    # Test 2: Check app endpoint
    app_ok = test_app_endpoint()

    # Final summary
    print("\n" + "=" * 60)
    print("Final Status:")
    print(f"  Redis Events: {'WORKING' if redis_ok else 'NOT WORKING'}")
    print(f"  App Endpoint: {'WORKING' if app_ok else 'NOT WORKING'}")

    if redis_ok and app_ok:
        print("\n[SUCCESS] Full integration is working!")
        print("The monitoring dashboard should display real data.")
    elif redis_ok:
        print("\n[PARTIAL] TickStockPL is publishing, but TickStockAppV2 needs to be started.")
    else:
        print("\n[FAILED] Please check the troubleshooting steps above.")

    print("=" * 60)
