"""
Mock Streaming Data Publisher for Testing
Publishes simulated streaming events to Redis for testing the Live Streaming dashboard
"""

import redis
import json
import time
import random
from datetime import datetime, timezone
from uuid import uuid4

# Redis connection
redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)

# Test session ID
SESSION_ID = str(uuid4())

# Test symbols
SYMBOLS = ['AAPL', 'NVDA', 'TSLA', 'GOOGL', 'MSFT', 'AMZN', 'META', 'AMD']

# Pattern types
PATTERNS = ['Doji', 'Hammer', 'ShootingStar', 'Engulfing', 'Harami']

# Indicator types
INDICATORS = ['RSI', 'SMA', 'EMA', 'MACD', 'BollingerBands']

def publish_session_start():
    """Publish streaming session started event"""
    event = {
        'type': 'streaming_session_started',
        'session': {
            'session_id': SESSION_ID,
            'universe': 'market_leaders:top_500',
            'started_at': datetime.now(timezone.utc).isoformat(),
            'symbol_count': len(SYMBOLS),
            'status': 'active'
        }
    }

    redis_client.publish('tickstock:streaming:session_started', json.dumps(event))
    print(f"✅ Published session start: {SESSION_ID[:8]}")

def publish_pattern_detection():
    """Publish random pattern detection"""
    symbol = random.choice(SYMBOLS)
    pattern = random.choice(PATTERNS)
    confidence = round(random.uniform(0.6, 0.95), 2)

    event = {
        'type': 'pattern_detected',
        'detection': {
            'symbol': symbol,
            'pattern_type': pattern,
            'confidence': confidence,
            'timeframe': '1min',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'bar_data': {
                'open': round(random.uniform(150, 200), 2),
                'high': round(random.uniform(200, 210), 2),
                'low': round(random.uniform(145, 150), 2),
                'close': round(random.uniform(150, 200), 2),
                'volume': random.randint(1000000, 5000000)
            }
        }
    }

    redis_client.publish('tickstock:patterns:streaming', json.dumps(event))
    print(f"📊 Pattern: {symbol} - {pattern} ({confidence})")

def publish_pattern_batch():
    """Publish batch of pattern detections"""
    patterns = []
    count = random.randint(3, 8)

    for _ in range(count):
        symbol = random.choice(SYMBOLS)
        pattern = random.choice(PATTERNS)
        confidence = round(random.uniform(0.6, 0.95), 2)

        patterns.append({
            'detection': {
                'symbol': symbol,
                'pattern_type': pattern,
                'confidence': confidence,
                'timeframe': '1min',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        })

    event = {
        'type': 'patterns_batch',
        'patterns': patterns,
        'count': count
    }

    redis_client.publish('tickstock:patterns:detected', json.dumps(event))
    print(f"📦 Batch: {count} patterns")

def publish_indicator_alert():
    """Publish indicator alert"""
    symbol = random.choice(SYMBOLS)
    alert_types = [
        'RSI_OVERBOUGHT',
        'RSI_OVERSOLD',
        'MACD_BULLISH_CROSS',
        'MACD_BEARISH_CROSS',
        'BB_UPPER_BREAK',
        'BB_LOWER_BREAK'
    ]
    alert_type = random.choice(alert_types)

    event = {
        'type': 'indicator_alert',
        'alert': {
            'symbol': symbol,
            'alert_type': alert_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': {
                'value': round(random.uniform(30, 80), 2),
                'threshold': 70 if 'OVERBOUGHT' in alert_type else 30
            }
        }
    }

    redis_client.publish('tickstock:alerts:indicators', json.dumps(event))
    print(f"🔔 Alert: {symbol} - {alert_type}")

def publish_indicator_update():
    """Publish indicator streaming update"""
    symbol = random.choice(SYMBOLS)
    indicator = random.choice(INDICATORS)

    event = {
        'type': 'indicator_update',
        'indicator': {
            'symbol': symbol,
            'indicator_type': indicator,
            'value': round(random.uniform(40, 70), 2),
            'timeframe': '1min',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    }

    redis_client.publish('tickstock:indicators:streaming', json.dumps(event))
    print(f"📈 Indicator: {symbol} - {indicator}")

def publish_health_update():
    """Publish health status update"""
    event = {
        'type': 'health_update',
        'health': {
            'status': 'healthy',
            'active_symbols': len(SYMBOLS),
            'data_flow': {
                'ticks_per_second': random.randint(100, 500)
            },
            'issues': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    }

    redis_client.publish('tickstock:streaming:health', json.dumps(event))
    print(f"💚 Health: {event['health']['active_symbols']} symbols, {event['health']['data_flow']['ticks_per_second']} ticks/sec")

def publish_session_stop():
    """Publish streaming session stopped event"""
    event = {
        'type': 'streaming_session_stopped',
        'session': {
            'session_id': SESSION_ID,
            'stopped_at': datetime.now(timezone.utc).isoformat(),
            'status': 'completed'
        }
    }

    redis_client.publish('tickstock:streaming:session_stopped', json.dumps(event))
    print(f"❌ Published session stop: {SESSION_ID[:8]}")

def run_mock_streaming(duration_seconds=60):
    """
    Run mock streaming data publisher

    Args:
        duration_seconds: How long to publish data (default: 60 seconds)
    """
    print("=" * 60)
    print("MOCK STREAMING DATA PUBLISHER")
    print("=" * 60)
    print(f"Duration: {duration_seconds} seconds")
    print(f"Session ID: {SESSION_ID}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print("=" * 60)

    # Start session
    publish_session_start()
    time.sleep(2)

    start_time = time.time()
    iteration = 0

    try:
        while (time.time() - start_time) < duration_seconds:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")

            # Publish various events
            publish_pattern_detection()
            time.sleep(1)

            if iteration % 3 == 0:
                publish_pattern_batch()
                time.sleep(1)

            if iteration % 5 == 0:
                publish_indicator_alert()
                time.sleep(1)

            publish_indicator_update()
            time.sleep(1)

            if iteration % 10 == 0:
                publish_health_update()
                time.sleep(1)

            # Random delay between iterations
            delay = random.uniform(2, 5)
            print(f"⏱️  Waiting {delay:.1f}s...")
            time.sleep(delay)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")

    # Stop session
    print("\n" + "=" * 60)
    publish_session_stop()
    print("=" * 60)
    print("✅ Mock streaming complete")
    print(f"Total iterations: {iteration}")

if __name__ == '__main__':
    import sys

    # Get duration from command line argument (default: 60 seconds)
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60

    run_mock_streaming(duration)
