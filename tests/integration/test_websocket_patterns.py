#!/usr/bin/env python3
"""
Test WebSocket Pattern Events Integration
Tests real-time pattern event flow from Redis to WebSocket frontend
"""

import eventlet
eventlet.monkey_patch()

import redis
import json
import time
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.services.config_manager import ConfigManager

def test_websocket_pattern_integration():
    """Test the complete pattern event flow: Redis -> WebSocket -> Frontend"""
    try:
        print("Testing WebSocket Pattern Integration...")
        
        # Get Redis configuration
        config_manager = ConfigManager()
        config = config_manager.config
        
        # Connect to Redis using the same method as the app
        redis_url = config.get('REDIS_URL', 'redis://localhost:6379/0')
        if not redis_url.startswith('redis://'):
            redis_url = f'redis://{redis_url}'
        
        redis_client = redis.Redis.from_url(redis_url, decode_responses=False)
        
        # Test Redis connection
        redis_client.ping()
        print("SUCCESS: Redis connection established")
        
        # Create test pattern event (simulating TickStockPL)
        test_pattern_event = {
            "source": "TickStockPL-Test",
            "timestamp": time.time(),
            "pattern": "BreakoutBO",
            "symbol": "AAPL",
            "confidence": 0.95,
            "tier": "daily",
            "price_at_detection": 150.25,
            "timeframe": "1d",
            "category": "breakout",
            "detection_timestamp": time.time(),
            "metadata": {
                "test": True,
                "description": "Test pattern event for WebSocket integration"
            }
        }
        
        print(f"Publishing test pattern event: {test_pattern_event['pattern']} on {test_pattern_event['symbol']}")
        
        # Publish to Redis pattern channel (same channel that TickStockPL uses)
        channel = 'tickstock.events.patterns'
        message = json.dumps(test_pattern_event)
        
        redis_client.publish(channel, message)
        print(f"SUCCESS: Pattern event published to Redis channel: {channel}")
        
        # Test multiple pattern events
        test_patterns = [
            {
                "pattern": "DivergenceDO",
                "symbol": "GOOGL", 
                "confidence": 0.87,
                "tier": "intraday",
                "timeframe": "5m"
            },
            {
                "pattern": "ComboPattern",
                "symbol": "TSLA",
                "confidence": 0.92,
                "tier": "combo",
                "category": "combo"
            }
        ]
        
        print("\nPublishing additional test patterns...")
        for i, pattern in enumerate(test_patterns):
            pattern.update({
                "source": "TickStockPL-Test",
                "timestamp": time.time(),
                "detection_timestamp": time.time(),
                "price_at_detection": 100 + (i * 10),
                "metadata": {"test": True, "sequence": i+1}
            })
            
            redis_client.publish(channel, json.dumps(pattern))
            print(f"  SUCCESS: Published {pattern['pattern']} on {pattern['symbol']} ({pattern['tier']} tier)")
            time.sleep(0.5)  # Small delay between events
        
        print("\n" + "="*60)
        print("PATTERN EVENT TESTING COMPLETE")
        print("="*60)
        print("\nVERIFICATION STEPS:")
        print("1. Check browser console for '[TierPatternService] Real-time pattern alert processed'")
        print("2. Verify pattern alerts appear in the Pattern Dashboard")
        print("3. Check for browser notifications (if enabled)")
        print("4. Verify events are categorized into correct tiers (daily/intraday/combo)")
        print("\nEXPECTED BEHAVIOR:")
        print("- BreakoutBO on AAPL should appear in DAILY tier")
        print("- DivergenceDO on GOOGL should appear in INTRADAY tier") 
        print("- ComboPattern on TSLA should appear in COMBO tier")
        print("\nTIP: Open the Pattern Dashboard and browser console before running this test")
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("WebSocket Pattern Integration Test")
    print("="*50)
    
    success = test_websocket_pattern_integration()
    
    if success:
        print("\nSUCCESS: Test completed successfully!")
        print("\nNext: Open http://localhost:5000 and check the Pattern Dashboard")
    else:
        print("\nERROR: Test failed!")
        sys.exit(1)