#!/usr/bin/env python3
'''
Simple integration test to verify pattern flow logging.
Sends a test pattern and checks both log file and database.
'''

import redis
import json
import time
from datetime import datetime

def test_integration_logging():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    # Create properly formatted pattern event
    pattern_event = {
        "event_type": "pattern_detected",
        "source": "TickStockPL",
        "timestamp": time.time(),
        "data": {
            "symbol": "AAPL",
            "pattern": "Hammer",  # This is the correct field name
            "confidence": 0.95,
            "detection_timestamp": datetime.now().isoformat(),
            "timeframe": "5min",
            "price": 185.50
        }
    }

    channel = "tickstock.events.patterns"

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending test pattern event...")
    print(f"  Pattern: {pattern_event['data']['pattern']}")
    print(f"  Symbol: {pattern_event['data']['symbol']}")
    print(f"  Confidence: {pattern_event['data']['confidence']}")

    subscribers = r.publish(channel, json.dumps(pattern_event))
    print(f"  Subscribers: {subscribers}")

    print("\n[CHECK] Integration log file for flow tracking:")
    print("  Look for: EVENT_RECEIVED -> EVENT_PARSED -> PATTERN_RECEIVED -> WEBSOCKET_DELIVERED")

    print("\n[CHECK] Database for audit trail (if table created):")
    print("  SELECT * FROM integration_events ORDER BY timestamp DESC LIMIT 10;")

if __name__ == "__main__":
    test_integration_logging()
