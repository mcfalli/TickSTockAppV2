"""
Test script to publish a pattern event to Redis for TickStockApp consumption.
This simulates what TickStockPL would publish.
"""

import json
import time

import redis


def publish_test_pattern():
    """Publish a test pattern event to Redis."""

    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0)

    # Test connection
    try:
        r.ping()
        print("[OK] Connected to Redis")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Redis: {e}")
        return

    # Create a test pattern event (mimicking TickStockPL format)
    pattern_event = {
        "event_type": "pattern_detected",
        "source": "TickStockPL",
        "timestamp": time.time(),
        "data": {
            "symbol": "AAPL",
            "pattern": "Bull_Flag",  # Changed from pattern_type to pattern
            "confidence": 0.85,
            "current_price": 185.50,
            "price_change": 2.3,
            "timestamp": time.time(),  # Changed from detected_at to timestamp
            "expires_at": time.time() + 3600,  # Expires in 1 hour
            "indicators": {
                "relative_strength": 1.5,
                "relative_volume": 2.1,
                "support_level": 180.0,
                "resistance_level": 190.0
            },
            "source": "intraday",  # Changed from source_tier to source
            "description": "Bullish flag pattern detected on 5-minute chart",
            "action": "BUY",
            "stop_loss": 182.0,
            "target_price": 192.0
        }
    }

    # Publish to the pattern channel
    channel = "tickstock.events.patterns"
    message = json.dumps(pattern_event)

    try:
        subscribers = r.publish(channel, message)
        print(f"[OK] Published pattern event to channel '{channel}'")
        print(f"   Subscribers: {subscribers}")
        print(f"   Pattern: {pattern_event['data']['pattern']} for {pattern_event['data']['symbol']}")
        print(f"   Confidence: {pattern_event['data']['confidence']}")

        # Publish a few more test patterns with different symbols
        test_patterns = [
            {"symbol": "MSFT", "pattern": "Breakout", "confidence": 0.92, "price": 380.25, "change": 3.1},
            {"symbol": "GOOGL", "pattern": "Support_Test", "confidence": 0.78, "price": 140.80, "change": -0.5},
            {"symbol": "TSLA", "pattern": "Volume_Spike", "confidence": 0.88, "price": 245.60, "change": 5.2},
            {"symbol": "NVDA", "pattern": "Ascending_Triangle", "confidence": 0.81, "price": 495.30, "change": 1.8}
        ]

        for i, pattern in enumerate(test_patterns, 1):
            time.sleep(0.5)  # Small delay between messages

            event = {
                "event_type": "pattern_detected",
                "source": "TickStockPL",
                "timestamp": time.time(),
                "data": {
                    "symbol": pattern["symbol"],
                    "pattern": pattern["pattern"],  # Fixed field name
                    "confidence": pattern["confidence"],
                    "current_price": pattern["price"],
                    "price_change": pattern["change"],
                    "timestamp": time.time(),  # Fixed field name
                    "expires_at": time.time() + 3600,
                    "indicators": {
                        "relative_strength": 1.2 + i * 0.1,
                        "relative_volume": 1.5 + i * 0.2
                    },
                    "source": "daily" if i % 2 == 0 else "intraday"  # Fixed field name
                }
            }

            r.publish(channel, json.dumps(event))
            print(f"   -> Published {pattern['pattern']} for {pattern['symbol']}")

        print("\n[SUMMARY] Test Results:")
        print(f"   Total patterns published: {len(test_patterns) + 1}")
        print(f"   Channel: {channel}")
        print("\n[ACTION] Check your TickStockApp UI for pattern alerts!")
        print("   - Look for WebSocket events in browser console")
        print("   - Check /api/patterns/scan endpoint")
        print("   - Monitor pattern_alert WebSocket events")

    except Exception as e:
        print(f"[ERROR] Failed to publish message: {e}")

if __name__ == "__main__":
    publish_test_pattern()
