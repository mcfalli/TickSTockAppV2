"""
Test Script for Sprint 33 Phase 5 Streaming Integration

Simulates streaming events from TickStockPL to test the complete integration:
- Redis event publishing
- WebSocket broadcasting
- UI updates
- Buffering behavior

Run this script to test outside market hours.
"""

import json
import random
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import redis

# Configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# Test symbols
TEST_SYMBOLS = ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN', 'NVDA', 'META', 'JPM', 'BAC', 'WMT']

# Pattern types from TickStockPL
PATTERN_TYPES = ['Doji', 'Hammer', 'HeadShoulders']

# Indicator types
INDICATOR_TYPES = ['RSI', 'SMA', 'MACD', 'BollingerBands']

class StreamingEventSimulator:
    """Simulates Phase 5 streaming events for testing."""

    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=False
        )
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now(UTC)

        print(f"Initialized simulator with session ID: {self.session_id}")

    def start_session(self):
        """Simulate streaming session start."""
        event = {
            "event": "session_started",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "session_id": self.session_id,
                "symbol_universe_key": "test_universe:top_10",
                "start_time": self.start_time.isoformat(),
                "trigger_type": "manual_test"
            }
        }

        channel = 'tickstock:streaming:session_started'
        self.redis_client.publish(channel, json.dumps(event))
        print(f"Published session start event to {channel}")

    def simulate_pattern_detection(self, count: int = 5):
        """Simulate pattern detection events."""
        for i in range(count):
            symbol = random.choice(TEST_SYMBOLS)
            pattern_type = random.choice(PATTERN_TYPES)
            confidence = random.uniform(0.6, 0.95)

            event = {
                "event": "pattern_detected",
                "session_id": self.session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "detection": {
                    "pattern_type": pattern_type,
                    "symbol": symbol,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "confidence": round(confidence, 3),
                    "parameters": {
                        "open": round(random.uniform(100, 200), 2),
                        "close": round(random.uniform(100, 200), 2),
                        "high": round(random.uniform(100, 200), 2),
                        "low": round(random.uniform(100, 200), 2),
                        "volume": random.randint(1000000, 10000000)
                    },
                    "timeframe": "1min"
                }
            }

            # Publish to both channels
            if confidence >= 0.8:
                # High confidence goes to both channels
                self.redis_client.publish('tickstock:patterns:detected', json.dumps(event))
                print(f"Published high confidence {pattern_type} pattern for {symbol} (confidence: {confidence:.1%})")

            # All patterns go to streaming channel
            self.redis_client.publish('tickstock:patterns:streaming', json.dumps(event))

            # Small delay to simulate real-time flow
            time.sleep(random.uniform(0.1, 0.5))

    def simulate_indicator_calculations(self, count: int = 10):
        """Simulate indicator calculation events."""
        for i in range(count):
            symbol = random.choice(TEST_SYMBOLS)
            indicator_type = random.choice(INDICATOR_TYPES)

            values = {}
            if indicator_type == 'RSI':
                values['value'] = round(random.uniform(20, 80), 2)
            elif indicator_type == 'SMA':
                values['sma_20'] = round(random.uniform(100, 200), 2)
                values['sma_50'] = round(random.uniform(100, 200), 2)
            elif indicator_type == 'MACD':
                values['macd'] = round(random.uniform(-2, 2), 4)
                values['signal'] = round(random.uniform(-2, 2), 4)
                values['histogram'] = round(random.uniform(-1, 1), 4)
            elif indicator_type == 'BollingerBands':
                values['upper'] = round(random.uniform(150, 200), 2)
                values['middle'] = round(random.uniform(120, 150), 2)
                values['lower'] = round(random.uniform(100, 120), 2)

            event = {
                "event": "indicator_calculated",
                "session_id": self.session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "calculation": {
                    "indicator_type": indicator_type,
                    "symbol": symbol,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "values": values,
                    "timeframe": "1min"
                }
            }

            self.redis_client.publish('tickstock:indicators:streaming', json.dumps(event))
            print(f"Published {indicator_type} calculation for {symbol}")

            # Check for alerts
            if indicator_type == 'RSI':
                rsi_value = values['value']
                if rsi_value > 70:
                    self.send_indicator_alert('RSI_OVERBOUGHT', symbol, {'rsi': rsi_value})
                elif rsi_value < 30:
                    self.send_indicator_alert('RSI_OVERSOLD', symbol, {'rsi': rsi_value})

            time.sleep(random.uniform(0.05, 0.2))

    def send_indicator_alert(self, alert_type: str, symbol: str, data: dict[str, Any]):
        """Send indicator alert event."""
        alert = {
            "alert_type": alert_type,
            "symbol": symbol,
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": self.session_id,
            "data": data
        }

        self.redis_client.publish('tickstock:alerts:indicators', json.dumps(alert))
        print(f"  -> Alert: {alert_type} for {symbol}")

    def simulate_health_update(self):
        """Simulate streaming health update."""
        active_symbols = len(TEST_SYMBOLS)
        ticks_per_second = random.randint(500, 1000)

        health = {
            "event": "streaming_health",
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": self.session_id,
            "status": "healthy",
            "issues": [],
            "connection": {
                "active": 1,
                "failed": 0,
                "reconnections": 0
            },
            "data_flow": {
                "ticks_per_second": ticks_per_second,
                "bars_per_minute": active_symbols,
                "processing_lag_ms": random.randint(10, 50)
            },
            "resources": {
                "cpu_percent": round(random.uniform(20, 40), 1),
                "memory_mb": round(random.uniform(800, 1500), 1),
                "memory_percent": round(random.uniform(10, 20), 1)
            },
            "active_symbols": active_symbols,
            "stale_symbols": {
                "count": 0,
                "symbols": []
            }
        }

        self.redis_client.publish('tickstock:streaming:health', json.dumps(health))
        print(f"Published health update - Status: {health['status']}, Active symbols: {active_symbols}")

    def simulate_critical_alert(self):
        """Simulate a critical alert."""
        alert = {
            "type": "CONNECTION_LOST",
            "message": "Lost connection to Massive WebSocket",
            "severity": "critical",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "reconnect_attempts": 3,
                "last_error": "Connection timeout"
            }
        }

        self.redis_client.publish('tickstock:alerts:critical', json.dumps(alert))
        print(f"⚠️  Published critical alert: {alert['message']}")

    def stop_session(self):
        """Simulate streaming session stop."""
        event = {
            "event": "session_stopped",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "session_id": self.session_id,
                "stop_time": datetime.now(UTC).isoformat(),
                "reason": "test_complete"
            }
        }

        self.redis_client.publish('tickstock:streaming:session_stopped', json.dumps(event))
        print("Published session stop event")

    def run_continuous_simulation(self, duration_seconds: int = 60):
        """Run continuous simulation for testing."""
        print(f"\n{'='*60}")
        print(f"Starting {duration_seconds} second streaming simulation")
        print(f"{'='*60}\n")

        # Start session
        self.start_session()
        time.sleep(2)

        # Send initial health update
        self.simulate_health_update()

        start = time.time()
        pattern_counter = 0
        indicator_counter = 0

        while time.time() - start < duration_seconds:
            # Simulate patterns (lower frequency)
            if random.random() < 0.3:  # 30% chance per iteration
                self.simulate_pattern_detection(random.randint(1, 3))
                pattern_counter += 1

            # Simulate indicators (higher frequency)
            if random.random() < 0.7:  # 70% chance per iteration
                self.simulate_indicator_calculations(random.randint(2, 5))
                indicator_counter += 1

            # Health update every 10 seconds
            if int(time.time() - start) % 10 == 0:
                self.simulate_health_update()

            # Small chance of critical alert
            if random.random() < 0.02:  # 2% chance
                self.simulate_critical_alert()

            time.sleep(1)

        # Stop session
        self.stop_session()

        print(f"\n{'='*60}")
        print("Simulation complete!")
        print(f"Total pattern batches: {pattern_counter}")
        print(f"Total indicator batches: {indicator_counter}")
        print(f"{'='*60}\n")


def main():
    """Main test runner."""
    print("Sprint 33 Phase 5 - Streaming Event Simulator")
    print("=" * 60)

    simulator = StreamingEventSimulator()

    print("\nTest Options:")
    print("1. Quick test (20 seconds)")
    print("2. Standard test (60 seconds)")
    print("3. Extended test (5 minutes)")
    print("4. Single event test")

    choice = input("\nSelect test option (1-4): ").strip()

    if choice == '1':
        simulator.run_continuous_simulation(20)
    elif choice == '2':
        simulator.run_continuous_simulation(60)
    elif choice == '3':
        simulator.run_continuous_simulation(300)
    elif choice == '4':
        print("\nRunning single event test...")
        simulator.start_session()
        time.sleep(1)
        simulator.simulate_pattern_detection(1)
        simulator.simulate_indicator_calculations(2)
        simulator.send_indicator_alert('RSI_OVERBOUGHT', 'AAPL', {'rsi': 75.5})
        simulator.simulate_health_update()
        time.sleep(1)
        simulator.stop_session()
        print("Single event test complete!")
    else:
        print("Invalid choice. Running quick test...")
        simulator.run_continuous_simulation(20)


if __name__ == "__main__":
    main()
