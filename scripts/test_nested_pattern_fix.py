#!/usr/bin/env python3
"""
Test script to verify fix for nested data structure from TickStockPL.
"""

import redis
import json
import time
import uuid
from datetime import datetime

def publish_nested_pattern():
    """Publish a pattern event with the exact nested structure from TickStockPL."""
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        decode_responses=True
    )

    # Create the exact nested structure that TickStockPL is sending
    pattern_event = {
        'event_type': 'pattern_detected',
        'source': 'TickStockPL',
        'timestamp': time.time(),
        'data': {
            'event_type': 'pattern_detected',  # Duplicate field
            'source': 'TickStockPL',  # Duplicate field
            'timestamp': time.time(),  # Duplicate field
            'flow_id': str(uuid.uuid4()),
            'data': {  # Nested data!
                'symbol': 'TEST',
                'pattern': 'Support_Bounce',  # Pattern is here in nested data
                'confidence': 0.78,
                'current_price': 100.50,
                'price_change': 0.05,
                'timestamp': time.time(),
                'expires_at': time.time() + 259200,
                'indicators': {
                    'relative_strength': 1.0,
                    'relative_volume': 1.5
                },
                'source': 'daily'
            },
            '_flow_id': str(uuid.uuid4())
        },
        'channel': 'tickstock.events.patterns'
    }

    # Publish to Redis
    channel = 'tickstock.events.patterns'
    redis_client.publish(channel, json.dumps(pattern_event))

    print(f"Published nested pattern event to {channel}")
    print(f"Pattern: {pattern_event['data']['data']['pattern']}")
    print(f"Symbol: {pattern_event['data']['data']['symbol']}")
    print("\nCheck the logs - there should be NO warnings about missing pattern name")
    print("The pattern should be properly extracted from the nested structure")

if __name__ == "__main__":
    publish_nested_pattern()