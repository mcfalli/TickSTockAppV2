#!/usr/bin/env python3
"""
Test Database Integration Logging
Verifies that the database integration logging is working properly for TickStockAppV2.
"""

import redis
import json
import time
import uuid
from datetime import datetime

def send_test_pattern_event():
    """Send a test pattern event to Redis to trigger database logging."""
    try:
        # Connect to Redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

        # Create a properly formatted pattern event with flow_id (simulating TickStockPL)
        flow_id = str(uuid.uuid4())
        pattern_event = {
            "event_type": "pattern_detected",
            "source": "TickStockPL",
            "timestamp": time.time(),
            "flow_id": flow_id,  # Include flow_id for tracking
            "data": {
                "symbol": "AAPL",
                "pattern": "Doji",
                "confidence": 0.87,
                "detection_timestamp": datetime.now().isoformat(),
                "timeframe": "5min",
                "price": 185.50,
                "flow_id": flow_id  # Also in data section
            }
        }

        channel = "tickstock.events.patterns"

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending test pattern event with database logging...")
        print(f"  Flow ID: {flow_id}")
        print(f"  Pattern: {pattern_event['data']['pattern']}")
        print(f"  Symbol: {pattern_event['data']['symbol']}")
        print(f"  Confidence: {pattern_event['data']['confidence']}")
        print(f"  Channel: {channel}")

        # Publish the event
        subscribers = r.publish(channel, json.dumps(pattern_event))
        print(f"  Subscribers: {subscribers}")

        print(f"\n[CHECK] If TickStockAppV2 is running, you should see:")
        print(f"  1. Console logs showing database integration logging")
        print(f"  2. File-based integration logs in logs/integration_*.log")
        print(f"  3. Database entries in integration_events table")

        print(f"\n[DATABASE CHECK] Run this SQL to verify database logging:")
        print(f"  SELECT * FROM integration_events WHERE flow_id = '{flow_id}' ORDER BY timestamp;")

        return flow_id

    except Exception as e:
        print(f"ERROR: Failed to send test event: {e}")
        return None

def check_database_entries(flow_id):
    """Check if the database entries were created properly."""
    try:
        import psycopg2

        # Connect to database
        conn = psycopg2.connect(
            host='localhost',
            port=5433,
            database='tickstock',
            user='app_readwrite',
            password='LJI48rUEkUpe6e'
        )

        with conn.cursor() as cursor:
            # Check for entries with our flow_id
            cursor.execute("""
                SELECT timestamp, checkpoint, symbol, pattern_name, confidence, user_count
                FROM integration_events
                WHERE flow_id = %s
                ORDER BY timestamp
            """, (flow_id,))

            entries = cursor.fetchall()

            if entries:
                print(f"\n[SUCCESS] Found {len(entries)} database entries for flow {flow_id}:")
                for entry in entries:
                    timestamp, checkpoint, symbol, pattern, confidence, user_count = entry
                    print(f"  {timestamp} | {checkpoint} | {pattern}@{symbol} | conf={confidence} | users={user_count}")
            else:
                print(f"\n[WARNING] No database entries found for flow {flow_id}")
                print("This could mean:")
                print("  1. TickStockAppV2 is not running")
                print("  2. Database integration logger is disabled")
                print("  3. integration_events table doesn't exist")

        conn.close()

    except Exception as e:
        print(f"ERROR: Failed to check database: {e}")

def main():
    """Test database integration logging end-to-end."""
    print("=" * 60)
    print("Testing Database Integration Logging")
    print("=" * 60)

    # Send test event
    flow_id = send_test_pattern_event()

    if flow_id:
        # Wait a moment for processing
        print(f"\n[WAITING] Allowing 3 seconds for processing...")
        time.sleep(3)

        # Check database entries
        check_database_entries(flow_id)

    print(f"\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()