#!/usr/bin/env python3
"""
Test the complete integration flow from TickStockPL to TickStockAppV2.
This simulates what TickStockPL sends and checks the database for flow tracking.
"""

import redis
import json
import time
import psycopg2
import uuid
from datetime import datetime

def get_db_connection():
    return psycopg2.connect(
        host='localhost',
        port=5432,
        database='tickstock',
        user='app_readwrite',
        password='LJI48rUEkUpe6e'
    )

def send_test_pattern():
    """Send a test pattern like TickStockPL does."""
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    # Generate flow ID for tracking
    flow_id = str(uuid.uuid4())

    # Create pattern event matching TickStockPL format
    pattern_event = {
        "event_type": "pattern_detected",
        "source": "TickStockPL",
        "timestamp": time.time(),
        "data": {
            "symbol": "TEST",
            "pattern": "Integration_Test",  # Using "pattern" field
            "pattern_name": "Integration_Test",  # Also include pattern_name
            "confidence": 0.95,
            "current_price": 100.50,
            "price_change": 2.5,
            "tier": "integration_test",
            "flow_id": flow_id  # Include flow_id for tracking
        }
    }

    # Publish to Redis
    channel = "tickstock.events.patterns"
    message = json.dumps(pattern_event)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Publishing test pattern...")
    print(f"  Flow ID: {flow_id}")
    print(f"  Pattern: {pattern_event['data']['pattern']}@{pattern_event['data']['symbol']}")

    subscribers = r.publish(channel, message)
    print(f"  Subscribers: {subscribers}")

    # Log to database like TickStockPL does
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO integration_events (
                flow_id, event_type, source_system, checkpoint,
                channel, symbol, pattern_name, confidence, details
            ) VALUES (
                %s, 'pattern_detected', 'TickStockPL', 'PATTERN_PUBLISHED',
                %s, %s, %s, %s, %s::jsonb
            )
        """, (
            flow_id,
            channel,
            pattern_event['data']['symbol'],
            pattern_event['data']['pattern'],
            pattern_event['data']['confidence'],
            json.dumps({"test": True, "timestamp": datetime.now().isoformat()})
        ))

        conn.commit()
        cur.close()
        conn.close()
        print(f"  [OK] Logged to database")

    except Exception as e:
        print(f"  [FAIL] Database logging failed: {e}")

    return flow_id

def check_integration_flow(flow_id):
    """Check if TickStockAppV2 received and logged the pattern."""
    time.sleep(2)  # Wait for processing

    conn = get_db_connection()
    cur = conn.cursor()

    # Check all events for this flow_id
    cur.execute("""
        SELECT source_system, checkpoint, timestamp
        FROM integration_events
        WHERE flow_id = %s
        ORDER BY timestamp
    """, (flow_id,))

    events = cur.fetchall()

    print(f"\n[INTEGRATION FLOW CHECK]")
    if events:
        for source, checkpoint, timestamp in events:
            print(f"  {timestamp.strftime('%H:%M:%S')} | {source:15} | {checkpoint}")
    else:
        print(f"  No events found for flow_id: {flow_id}")

    # Check latest events regardless of flow_id
    print(f"\n[LATEST EVENTS]")
    cur.execute("""
        SELECT timestamp, source_system, checkpoint, symbol, pattern_name
        FROM integration_events
        ORDER BY timestamp DESC
        LIMIT 5
    """)

    for timestamp, source, checkpoint, symbol, pattern in cur.fetchall():
        print(f"  {timestamp.strftime('%H:%M:%S')} | {source:15} | {checkpoint:20} | {pattern}@{symbol}")

    cur.close()
    conn.close()

def main():
    print("=" * 60)
    print("INTEGRATION FLOW TEST")
    print("=" * 60)

    # Send test pattern
    flow_id = send_test_pattern()

    # Check the flow
    check_integration_flow(flow_id)

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nExpected flow:")
    print("1. TickStockPL: PATTERN_PUBLISHED [OK]")
    print("2. TickStockAppV2: EVENT_RECEIVED")
    print("3. TickStockAppV2: EVENT_PARSED")
    print("4. TickStockAppV2: WEBSOCKET_DELIVERED")
    print("\nCheck above for actual flow status.")
    print("If missing checkpoints, TickStockAppV2 may need restart.")

if __name__ == "__main__":
    main()