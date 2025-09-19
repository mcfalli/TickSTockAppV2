#!/usr/bin/env python3
"""
Comprehensive Test for Integration Monitoring System
Tests heartbeats, subscriptions, pattern flow, and database logging.
"""

import sys
import os
import time
import uuid
import json
import redis
import psycopg2
from datetime import datetime
from colorama import init, Fore, Style

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.services.database_integration_logger import (
    DatabaseIntegrationLogger,
    IntegrationEventType,
    IntegrationCheckpoint
)

# Initialize colorama for Windows
init()

# Configuration
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'decode_responses': True
}

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'tickstock',
    'user': 'app_readwrite',
    'password': 'LJI48rUEkUpe6e'
}

APP_CONFIG = {
    'database': {
        'host': 'localhost',
        'port': 5433,
        'name': 'tickstock',
        'user': 'app_readwrite',
        'password': 'LJI48rUEkUpe6e'
    }
}

def print_header(title):
    """Print a formatted header."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{title}")
    print(f"{'='*60}{Style.RESET_ALL}")

def print_test(name, passed, details=""):
    """Print test result."""
    if passed:
        status = f"{Fore.GREEN}[PASS]{Style.RESET_ALL}"
    else:
        status = f"{Fore.RED}[FAIL]{Style.RESET_ALL}"

    print(f"  {status} - {name}")
    if details:
        print(f"    {Fore.YELLOW}{details}{Style.RESET_ALL}")

def test_database_connection():
    """Test database connectivity."""
    print_header("Testing Database Connection")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Test basic connection
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print_test("Database connection", result[0] == 1)

        # Test integration_events table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'integration_events'
            )
        """)
        table_exists = cursor.fetchone()[0]
        print_test("integration_events table exists", table_exists)

        # Test pattern_flow_analysis view exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.views
                WHERE table_schema = 'public'
                AND table_name = 'pattern_flow_analysis'
            )
        """)
        view_exists = cursor.fetchone()[0]
        print_test("pattern_flow_analysis view exists", view_exists)

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print_test("Database connection", False, str(e))
        return False

def test_redis_connection():
    """Test Redis connectivity."""
    print_header("Testing Redis Connection")

    try:
        r = redis.Redis(**REDIS_CONFIG)

        # Test basic connection
        ping_result = r.ping()
        print_test("Redis connection", ping_result)

        # Test pub/sub functionality
        pubsub = r.pubsub()
        test_channel = 'test.integration.monitoring'
        pubsub.subscribe(test_channel)

        # Get subscription confirmation
        message = pubsub.get_message(timeout=1)
        subscribed = message and message['type'] == 'subscribe'
        print_test("Redis pub/sub subscription", subscribed,
                  f"Subscribed to {test_channel}")

        pubsub.unsubscribe()
        pubsub.close()
        return True

    except Exception as e:
        print_test("Redis connection", False, str(e))
        return False

def test_database_logger():
    """Test DatabaseIntegrationLogger functionality."""
    print_header("Testing Database Integration Logger")

    try:
        # Initialize logger
        logger = DatabaseIntegrationLogger(APP_CONFIG)
        print_test("Logger initialization", logger.is_enabled())

        # Test system event logging (heartbeat)
        flow_id = logger.log_system_event(
            event_type='heartbeat',
            source_system='TickStockAppV2_Test',
            checkpoint='SUBSCRIBER_ALIVE',
            channel='test.channel',
            details={
                'test': True,
                'timestamp': time.time(),
                'events_received': 100,
                'uptime_seconds': 300
            }
        )
        print_test("Heartbeat logging", flow_id is not False,
                  f"Logged heartbeat with flow_id")

        # Test subscription event logging
        flow_id = logger.log_system_event(
            event_type='subscription_active',
            source_system='TickStockAppV2_Test',
            checkpoint='CHANNEL_SUBSCRIBED',
            channel='tickstock.events.patterns',
            details={'status': 'listening'}
        )
        print_test("Subscription logging", flow_id is not False,
                  f"Logged subscription event")

        # Test pattern event logging
        test_flow_id = str(uuid.uuid4())

        # Log pattern received
        received_flow_id = logger.log_pattern_received(
            event_data={
                'event_type': 'pattern_detected',
                'source': 'TickStockPL',
                'data': {
                    'symbol': 'TEST',
                    'pattern': 'Test_Pattern',
                    'confidence': 0.95,
                    'flow_id': test_flow_id
                }
            },
            channel='tickstock.events.patterns'
        )
        print_test("Pattern received logging", received_flow_id == test_flow_id,
                  f"Flow ID: {test_flow_id[:8]}...")

        # Log pattern parsed
        success = logger.log_pattern_parsed(
            flow_id=test_flow_id,
            symbol='TEST',
            pattern_name='Test_Pattern',
            confidence=0.95
        )
        print_test("Pattern parsed logging", success)

        # Log WebSocket delivery
        success = logger.log_websocket_delivery(
            flow_id=test_flow_id,
            symbol='TEST',
            pattern_name='Test_Pattern',
            user_count=5
        )
        print_test("WebSocket delivery logging", success)

        # Test health status
        health = logger.get_health_status()
        print_test("Health status check", health['status'] == 'healthy',
                  f"Status: {health.get('status', 'unknown')}")

        return True

    except Exception as e:
        print_test("Database logger", False, str(e))
        return False

def test_complete_flow():
    """Test a complete pattern flow from TickStockPL to TickStockAppV2."""
    print_header("Testing Complete Pattern Flow")

    try:
        # Initialize components
        r = redis.Redis(**REDIS_CONFIG)
        logger = DatabaseIntegrationLogger(APP_CONFIG)

        # Generate test pattern event
        test_flow_id = str(uuid.uuid4())
        test_pattern = {
            'event_type': 'pattern_detected',
            'source': 'TickStockPL_Test',
            'timestamp': time.time(),
            'data': {
                'symbol': 'AAPL',
                'pattern': 'Volume_Spike_Test',
                'confidence': 0.85,
                'flow_id': test_flow_id,
                'tier': 'intraday',
                'price_change': 2.5,
                'current_price': 185.50
            }
        }

        # Step 1: Simulate TickStockPL publishing
        channel = 'tickstock.events.patterns'

        # Log from TickStockPL side (would normally be in TickStockPL)
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT log_integration_event(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            test_flow_id,
            'pattern_detected',
            'TickStockPL_Test',
            'PATTERN_PUBLISHED',
            channel,
            'AAPL',
            'Volume_Spike_Test',
            0.85,
            None,
            json.dumps({'test': True, 'timestamp': time.time()})
        ))
        conn.commit()
        print_test("TickStockPL publish simulation", True,
                  f"Published pattern with flow_id: {test_flow_id[:8]}...")

        # Step 2: Simulate TickStockAppV2 receiving
        received_id = logger.log_pattern_received(test_pattern, channel)
        print_test("TickStockAppV2 receive", received_id == test_flow_id,
                  "EVENT_RECEIVED logged")

        # Step 3: Simulate parsing
        success = logger.log_pattern_parsed(
            test_flow_id, 'AAPL', 'Volume_Spike_Test', 0.85
        )
        print_test("Pattern parsing", success, "EVENT_PARSED logged")

        # Step 4: Simulate WebSocket delivery
        success = logger.log_websocket_delivery(
            test_flow_id, 'AAPL', 'Volume_Spike_Test', 3
        )
        print_test("WebSocket delivery", success, "WEBSOCKET_DELIVERED logged")

        # Verify complete flow in database
        time.sleep(0.5)  # Allow database to process

        cursor.execute("""
            SELECT checkpoints_logged, total_latency_ms, flow_path
            FROM pattern_flow_analysis
            WHERE flow_id = %s
        """, (test_flow_id,))

        result = cursor.fetchone()
        if result:
            checkpoints, latency, path = result
            flow_complete = checkpoints >= 3  # Should have at least 3 checkpoints
            print_test("Complete flow verification", flow_complete,
                      f"Checkpoints: {checkpoints}, Latency: {float(latency):.2f}ms")
            print(f"    Flow path: {' -> '.join(path)}")
        else:
            print_test("Complete flow verification", False, "Flow not found in analysis view")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print_test("Complete flow test", False, str(e))
        return False

def verify_recent_activity():
    """Check for recent integration activity in the database."""
    print_header("Verifying Recent Integration Activity")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Check heartbeats
        cursor.execute("""
            SELECT COUNT(*), MAX(timestamp) as last_heartbeat
            FROM integration_events
            WHERE event_type = 'heartbeat'
            AND timestamp > NOW() - INTERVAL '5 minutes'
        """)
        count, last_hb = cursor.fetchone()

        if count > 0 and last_hb:
            age = (datetime.now(last_hb.tzinfo) - last_hb).total_seconds()
            print_test("Recent heartbeats", True,
                      f"{count} heartbeats, last: {int(age)}s ago")
        else:
            print_test("Recent heartbeats", False,
                      "No recent heartbeats found")

        # Check subscriptions
        cursor.execute("""
            SELECT COUNT(DISTINCT channel)
            FROM integration_events
            WHERE event_type IN ('subscription_active', 'subscription_confirmed')
            AND timestamp > NOW() - INTERVAL '5 minutes'
        """)
        sub_count = cursor.fetchone()[0]
        print_test("Active subscriptions", sub_count > 0,
                  f"{sub_count} channels with recent activity")

        # Check patterns
        cursor.execute("""
            SELECT COUNT(*)
            FROM integration_events
            WHERE event_type = 'pattern_detected'
            AND timestamp > NOW() - INTERVAL '1 hour'
        """)
        pattern_count = cursor.fetchone()[0]
        print_test("Recent patterns", True,
                  f"{pattern_count} pattern events in last hour")

        # Summary statistics
        cursor.execute("""
            SELECT source_system, checkpoint, COUNT(*) as event_count
            FROM integration_events
            WHERE timestamp > NOW() - INTERVAL '10 minutes'
            GROUP BY source_system, checkpoint
            ORDER BY source_system, event_count DESC
        """)

        print(f"\n  {Fore.CYAN}Recent Activity Summary (last 10 minutes):{Style.RESET_ALL}")
        for system, checkpoint, count in cursor.fetchall():
            print(f"    {system}: {checkpoint} ({count} events)")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print_test("Recent activity check", False, str(e))
        return False

def cleanup_test_data():
    """Clean up test data from the database."""
    print_header("Cleaning Up Test Data")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Delete test events
        cursor.execute("""
            DELETE FROM integration_events
            WHERE source_system IN ('TickStockAppV2_Test', 'TickStockPL_Test')
            AND timestamp > NOW() - INTERVAL '1 hour'
        """)

        deleted = cursor.rowcount
        conn.commit()

        print_test("Test data cleanup", True,
                  f"Removed {deleted} test records")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print_test("Cleanup", False, str(e))
        return False

def main():
    """Run all integration monitoring tests."""
    print(f"{Fore.MAGENTA}{'='*60}")
    print(f"Integration Monitoring System Test Suite")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{Style.RESET_ALL}")

    # Run tests
    all_passed = True

    # Basic connectivity tests
    if not test_database_connection():
        all_passed = False
        print(f"{Fore.RED}Database connection failed - cannot continue{Style.RESET_ALL}")
        return 1

    if not test_redis_connection():
        all_passed = False
        print(f"{Fore.YELLOW}Redis connection failed - some tests may fail{Style.RESET_ALL}")

    # Component tests
    if not test_database_logger():
        all_passed = False

    # Integration tests
    if not test_complete_flow():
        all_passed = False

    # Verification
    if not verify_recent_activity():
        all_passed = False

    # Cleanup
    cleanup_test_data()

    # Summary
    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    if all_passed:
        print(f"{Fore.GREEN}[SUCCESS] All tests passed successfully!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}[FAILURE] Some tests failed. Check the output above.{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}Next Steps:{Style.RESET_ALL}")
    print(f"1. Start TickStockPL pattern service")
    print(f"2. Start TickStockAppV2")
    print(f"3. Run: python scripts/monitor_system_health.py")
    print(f"4. Check for heartbeats every 60 seconds")

    return 0 if all_passed else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Test interrupted by user.{Style.RESET_ALL}")
        sys.exit(1)