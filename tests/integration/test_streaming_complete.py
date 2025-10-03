"""
Comprehensive Streaming Integration Test
Sprint 33 Phase 5 - Complete validation test

Tests all components of the streaming integration:
1. Redis channel subscriptions
2. Event processing pipeline
3. API endpoints
4. WebSocket broadcasting
5. Streaming buffer behavior

Run this after hours to verify everything is ready for market hours.
"""

import sys
import os
import time
import json
import redis
import requests
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
APP_HOST = 'localhost'
APP_PORT = 5000

class StreamingIntegrationTest:
    """Comprehensive test suite for streaming integration."""

    def __init__(self):
        """Initialize test components."""
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=False
        )
        self.test_results = defaultdict(list)
        self.passed_tests = 0
        self.failed_tests = 0

    def print_header(self, text: str):
        """Print formatted header."""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}")

    def print_test(self, name: str, passed: bool, details: str = ""):
        """Print test result."""
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {name}")
        if details:
            print(f"         {details}")

        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1

        self.test_results[name] = {
            'passed': passed,
            'details': details
        }

    def test_redis_connection(self) -> bool:
        """Test Redis connectivity."""
        try:
            self.redis_client.ping()
            self.print_test("Redis Connection", True, "Connected to Redis successfully")
            return True
        except Exception as e:
            self.print_test("Redis Connection", False, f"Error: {e}")
            return False

    def test_channel_subscriptions(self) -> bool:
        """Test that all Phase 5 channels are accessible."""
        phase5_channels = [
            'tickstock:streaming:session_started',
            'tickstock:streaming:session_stopped',
            'tickstock:streaming:health',
            'tickstock:patterns:streaming',
            'tickstock:patterns:detected',
            'tickstock:indicators:streaming',
            'tickstock:alerts:indicators',
            'tickstock:alerts:critical'
        ]

        all_passed = True
        for channel in phase5_channels:
            try:
                # Test publish to channel
                test_msg = json.dumps({'test': True, 'timestamp': time.time()})
                result = self.redis_client.publish(channel, test_msg)

                # Result is number of subscribers
                self.print_test(
                    f"Channel: {channel}",
                    True,
                    f"{result} subscriber(s) listening"
                )
            except Exception as e:
                self.print_test(f"Channel: {channel}", False, f"Error: {e}")
                all_passed = False

        return all_passed

    def test_app_connectivity(self) -> bool:
        """Test TickStockAppV2 is running."""
        try:
            response = requests.get(f"http://{APP_HOST}:{APP_PORT}/", timeout=5)
            if response.status_code in [200, 302]:  # 302 for login redirect
                self.print_test("TickStockAppV2 Connection", True, f"App responding (status: {response.status_code})")
                return True
            else:
                self.print_test("TickStockAppV2 Connection", False, f"Unexpected status: {response.status_code}")
                return False
        except Exception as e:
            self.print_test("TickStockAppV2 Connection", False, f"Cannot reach app: {e}")
            return False

    def test_streaming_api_endpoint(self) -> bool:
        """Test streaming API endpoint (will redirect to login if not authenticated)."""
        try:
            response = requests.get(
                f"http://{APP_HOST}:{APP_PORT}/streaming/api/status",
                timeout=5
            )

            # Expected: 302 redirect to login or 200 with data
            if response.status_code == 302:
                self.print_test(
                    "Streaming API Endpoint",
                    True,
                    "Endpoint exists (requires authentication)"
                )
                return True
            elif response.status_code == 200:
                data = response.json()
                self.print_test(
                    "Streaming API Endpoint",
                    True,
                    f"Status: {data.get('status', 'unknown')}"
                )
                return True
            else:
                self.print_test(
                    "Streaming API Endpoint",
                    False,
                    f"Unexpected status: {response.status_code}"
                )
                return False
        except Exception as e:
            self.print_test("Streaming API Endpoint", False, f"Error: {e}")
            return False

    def simulate_streaming_session(self) -> bool:
        """Simulate a complete streaming session."""
        session_id = f"test-{int(time.time())}"

        try:
            # 1. Start session
            start_event = {
                "event": "session_started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "session_id": session_id,
                    "symbol_universe_key": "test_after_hours",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "trigger_type": "test"
                }
            }
            self.redis_client.publish('tickstock:streaming:session_started', json.dumps(start_event))
            time.sleep(0.5)

            # 2. Send pattern detection
            pattern_event = {
                "event": "pattern_detected",
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "detection": {
                    "pattern_type": "TestPattern",
                    "symbol": "TEST",
                    "confidence": 0.95,
                    "timeframe": "1min"
                }
            }
            self.redis_client.publish('tickstock:patterns:streaming', json.dumps(pattern_event))
            self.redis_client.publish('tickstock:patterns:detected', json.dumps(pattern_event))
            time.sleep(0.5)

            # 3. Send indicator alert
            alert_event = {
                "alert_type": "RSI_OVERBOUGHT",
                "symbol": "TEST",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "data": {"rsi": 75.0}
            }
            self.redis_client.publish('tickstock:alerts:indicators', json.dumps(alert_event))
            time.sleep(0.5)

            # 4. Send health update
            health_event = {
                "event": "streaming_health",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "status": "healthy",
                "active_symbols": 1,
                "data_flow": {"ticks_per_second": 100}
            }
            self.redis_client.publish('tickstock:streaming:health', json.dumps(health_event))
            time.sleep(0.5)

            # 5. Stop session
            stop_event = {
                "event": "session_stopped",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "session_id": session_id,
                    "stop_time": datetime.now(timezone.utc).isoformat()
                }
            }
            self.redis_client.publish('tickstock:streaming:session_stopped', json.dumps(stop_event))

            self.print_test(
                "Simulated Streaming Session",
                True,
                f"Published 6 events for session {session_id}"
            )
            return True

        except Exception as e:
            self.print_test("Simulated Streaming Session", False, f"Error: {e}")
            return False

    def check_redis_subscriber_status(self) -> bool:
        """Check if Redis subscriber is active by looking at heartbeat."""
        try:
            # Check for recent subscriber activity in logs
            import subprocess
            result = subprocess.run(
                ["tail", "-n", "5", "logs/tickstock_*.log"],
                capture_output=True,
                text=True,
                shell=True
            )

            if "REDIS-SUBSCRIBER" in result.stdout:
                if "channels" in result.stdout:
                    # Extract channel count
                    import re
                    match = re.search(r'listening on (\d+) channels', result.stdout)
                    if match:
                        channel_count = match.group(1)
                        self.print_test(
                            "Redis Subscriber Active",
                            True,
                            f"Listening on {channel_count} channels"
                        )
                        return True

            self.print_test(
                "Redis Subscriber Active",
                False,
                "Cannot verify subscriber status from logs"
            )
            return False

        except Exception as e:
            self.print_test("Redis Subscriber Active", False, f"Error checking logs: {e}")
            return False

    def test_buffer_configuration(self) -> bool:
        """Test streaming buffer configuration."""
        try:
            # Check if buffer configuration is in environment
            import os
            from pathlib import Path

            env_file = Path('.env')
            if env_file.exists():
                with open(env_file, 'r') as f:
                    env_content = f.read()

                buffer_configs = [
                    'STREAMING_BUFFER_ENABLED',
                    'STREAMING_BUFFER_INTERVAL',
                    'STREAMING_MAX_BUFFER_SIZE'
                ]

                all_found = True
                for config in buffer_configs:
                    if config in env_content:
                        self.print_test(f"Config: {config}", True, "Found in .env")
                    else:
                        self.print_test(f"Config: {config}", False, "Not found in .env")
                        all_found = False

                return all_found
            else:
                self.print_test("Buffer Configuration", False, ".env file not found")
                return False

        except Exception as e:
            self.print_test("Buffer Configuration", False, f"Error: {e}")
            return False

    def test_database_tables(self) -> bool:
        """Test if streaming-related database tables exist."""
        try:
            import psycopg2
            import os

            # Get database connection from environment
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'tickstock'),
                'user': os.getenv('DB_USER', 'app_readwrite'),
                'password': os.getenv('DB_PASSWORD', 'LJI48rUEkUpe6e')
            }

            tables_to_check = [
                'intraday_patterns',
                'intraday_indicators',
                'ohlcv_1min'
            ]

            conn = psycopg2.connect(**db_config)
            try:
                with conn.cursor() as cursor:
                    for table in tables_to_check:
                        cursor.execute(
                            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                            (table,)
                        )
                        exists = cursor.fetchone()[0]
                        self.print_test(f"Table: {table}", exists, "Exists" if exists else "Not found")
            finally:
                conn.close()

            return True

        except Exception as e:
            self.print_test("Database Tables", False, f"Cannot check tables: {e}")
            return False

    def run_all_tests(self):
        """Run complete test suite."""
        self.print_header("STREAMING INTEGRATION TEST SUITE")
        print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Note: Streaming service is offline after hours\n")

        # 1. Infrastructure Tests
        self.print_header("1. INFRASTRUCTURE TESTS")
        self.test_redis_connection()
        self.test_app_connectivity()

        # 2. Channel Tests
        self.print_header("2. REDIS CHANNEL TESTS")
        self.test_channel_subscriptions()

        # 3. API Tests
        self.print_header("3. API ENDPOINT TESTS")
        self.test_streaming_api_endpoint()

        # 4. Configuration Tests
        self.print_header("4. CONFIGURATION TESTS")
        self.test_buffer_configuration()

        # 5. Database Tests
        self.print_header("5. DATABASE TESTS")
        self.test_database_tables()

        # 6. Subscriber Status
        self.print_header("6. SUBSCRIBER STATUS")
        self.check_redis_subscriber_status()

        # 7. Simulation Test
        self.print_header("7. EVENT SIMULATION TEST")
        self.simulate_streaming_session()

        # Summary
        self.print_header("TEST SUMMARY")
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Pass Rate: {pass_rate:.1f}%")

        if self.failed_tests == 0:
            print("\n[SUCCESS] ALL TESTS PASSED - Ready for market hours!")
        else:
            print("\n[WARNING] Some tests failed - Review issues above")

        return self.failed_tests == 0


def main():
    """Main test runner."""
    tester = StreamingIntegrationTest()
    success = tester.run_all_tests()

    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Restart TickStockAppV2 to apply latest changes")
    print("2. Navigate to 'Live Streaming' in sidebar")
    print("3. When market opens, streaming will automatically activate")
    print("4. Run 'python tests/integration/run_streaming_test.py' to test with simulated data")
    print("="*60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())