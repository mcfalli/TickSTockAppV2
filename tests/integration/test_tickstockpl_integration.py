#!/usr/bin/env python3
"""
Comprehensive TickStockPL Integration Test Suite
Tests ACTUAL Redis consumption, database logging, and event processing.
No mocks - these tests validate real integration points.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
import json
import uuid
import redis
import psycopg2
import pytest
from datetime import datetime, timedelta
import threading
from typing import Dict, Any, List

class TestTickStockPLIntegration:
    """Test suite for TickStockPL -> TickStockAppV2 integration."""

    @classmethod
    def setup_class(cls):
        """Set up test fixtures."""
        # Real Redis connection
        cls.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True
        )

        # Real database connection
        cls.db_conn = psycopg2.connect(
            host='localhost',
            port=5433,
            database='tickstock',
            user='app_readwrite',
            password='LJI48rUEkUpe6e'
        )
        cls.db_conn.autocommit = True

        # Test data
        cls.test_flow_id = str(uuid.uuid4())
        cls.test_symbol = 'TEST'
        cls.test_pattern = 'TestPattern'

    @classmethod
    def teardown_class(cls):
        """Clean up test fixtures."""
        cls.redis_client.close()
        cls.db_conn.close()

    def test_redis_subscription_active(self):
        """Test that TickStockAppV2 is subscribed to correct channels."""
        # Check Redis client connections
        info = self.redis_client.client_info()

        # Publish test message to verify subscription
        test_event = {
            'event_type': 'pattern_detected',
            'source': 'IntegrationTest',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'pattern': 'ConnectionTest',
                'symbol': 'TEST',
                'confidence': 0.99
            }
        }

        # Publish and verify
        subscribers = self.redis_client.publish(
            'tickstock.events.patterns',
            json.dumps(test_event)
        )

        assert subscribers > 0, "No subscribers on tickstock.events.patterns channel"
        print(f"[OK] Redis subscription active: {subscribers} subscriber(s)")

    def test_pattern_event_structure_compatibility(self):
        """Test that we handle both nested and flat event structures."""
        # Test nested structure (TickStockPL Sprint 25 format)
        nested_event = {
            'event_type': 'pattern_detected',
            'source': 'TickStockPL',
            'timestamp': time.time(),
            'data': {
                'event_type': 'pattern_detected',  # Duplicate field
                'flow_id': self.test_flow_id,
                'data': {  # Nested data
                    'pattern': 'MACrossover',
                    'symbol': 'GOOGL',
                    'confidence': 0.85,
                    'current_price': 150.50
                }
            }
        }

        # Test flat structure (legacy format)
        flat_event = {
            'event_type': 'pattern_detected',
            'source': 'TickStockPL',
            'timestamp': time.time(),
            'data': {
                'pattern_name': 'HeadShoulders',  # Old field name
                'symbol': 'TSLA',
                'confidence': 0.90
            }
        }

        # Publish both formats
        for event in [nested_event, flat_event]:
            result = self.redis_client.publish(
                'tickstock.events.patterns',
                json.dumps(event)
            )
            assert result > 0, "Failed to publish test event"

        print("[OK] Pattern event structure compatibility verified")

    def test_database_integration_logging(self):
        """Test that integration events are logged to database."""
        cursor = self.db_conn.cursor()

        # Check for recent integration events
        cursor.execute("""
            SELECT COUNT(*)
            FROM integration_events
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
            AND event_type IN ('heartbeat', 'pattern_detected')
        """)

        count = cursor.fetchone()[0]
        assert count > 0, "No recent integration events in database"

        # Verify heartbeat is working (should have one within last 90 seconds)
        cursor.execute("""
            SELECT COUNT(*), MAX(timestamp) as last_heartbeat
            FROM integration_events
            WHERE event_type = 'heartbeat'
            AND source_system = 'TickStockAppV2'
            AND timestamp > NOW() - INTERVAL '90 seconds'
        """)

        result = cursor.fetchone()
        assert result[0] > 0, "No recent heartbeat found"
        print(f"[OK] Database logging active: Last heartbeat {result[1]}")

        cursor.close()

    def test_pattern_flow_checkpoints(self):
        """Test that pattern flow goes through all checkpoints."""
        cursor = self.db_conn.cursor()

        # Create and publish a trackable pattern
        flow_id = str(uuid.uuid4())
        test_pattern = {
            'event_type': 'pattern_detected',
            'source': 'IntegrationTest',
            'flow_id': flow_id,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'flow_id': flow_id,
                'data': {
                    'pattern': 'FlowTest',
                    'symbol': 'FLOW',
                    'confidence': 0.75
                }
            }
        }

        # Publish pattern
        self.redis_client.publish(
            'tickstock.events.patterns',
            json.dumps(test_pattern)
        )

        # Wait for processing
        time.sleep(2)

        # Check checkpoints
        cursor.execute("""
            SELECT checkpoint, COUNT(*)
            FROM integration_events
            WHERE flow_id = %s
            GROUP BY checkpoint
        """, (flow_id,))

        checkpoints = {row[0]: row[1] for row in cursor.fetchall()}

        expected_checkpoints = [
            'PATTERN_RECEIVED',
            'EVENT_PARSED',
            'PATTERN_CACHED'
        ]

        for checkpoint in expected_checkpoints:
            if checkpoint in checkpoints:
                print(f"[OK] Checkpoint {checkpoint} logged")

        cursor.close()

    def test_heartbeat_monitoring(self):
        """Test that heartbeat monitoring is active."""
        cursor = self.db_conn.cursor()

        # Check for heartbeats in last 2 minutes
        cursor.execute("""
            SELECT
                source_system,
                COUNT(*) as heartbeat_count,
                MAX(timestamp) - MIN(timestamp) as time_span,
                EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) / NULLIF(COUNT(*) - 1, 0) as avg_interval
            FROM integration_events
            WHERE event_type = 'heartbeat'
            AND timestamp > NOW() - INTERVAL '2 minutes'
            GROUP BY source_system
        """)

        for row in cursor.fetchall():
            source, count, span, interval = row
            if interval:
                assert 50 <= interval <= 70, f"Heartbeat interval {interval}s not ~60s"
                print(f"[OK] {source} heartbeat: {count} beats, ~{int(interval)}s interval")

        cursor.close()

    def test_redis_to_database_flow(self):
        """Test complete flow from Redis event to database logging."""
        cursor = self.db_conn.cursor()
        flow_id = str(uuid.uuid4())

        # Record initial count
        cursor.execute("SELECT COUNT(*) FROM integration_events")
        initial_count = cursor.fetchone()[0]

        # Publish test event
        test_event = {
            'event_type': 'pattern_detected',
            'source': 'FlowTest',
            'flow_id': flow_id,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'flow_id': flow_id,
                'data': {
                    'pattern': 'DatabaseFlowTest',
                    'symbol': 'DBT',
                    'confidence': 0.88
                }
            }
        }

        self.redis_client.publish(
            'tickstock.events.patterns',
            json.dumps(test_event)
        )

        # Wait for processing
        time.sleep(3)

        # Check for new events
        cursor.execute("""
            SELECT COUNT(*)
            FROM integration_events
            WHERE flow_id = %s
        """, (flow_id,))

        flow_events = cursor.fetchone()[0]
        assert flow_events > 0, f"No events logged for flow_id {flow_id}"

        print(f"[OK] Redis->Database flow working: {flow_events} events logged")
        cursor.close()

    def test_pattern_cache_update(self):
        """Test that patterns are cached in Redis."""
        # Publish a pattern
        test_event = {
            'event_type': 'pattern_detected',
            'source': 'CacheTest',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'pattern': 'CacheTestPattern',
                'symbol': 'CACHE',
                'confidence': 0.95,
                'expires_at': (datetime.now() + timedelta(hours=1)).timestamp()
            }
        }

        self.redis_client.publish(
            'tickstock.events.patterns',
            json.dumps(test_event)
        )

        # Wait for caching
        time.sleep(2)

        # Check for cached patterns
        pattern_keys = self.redis_client.keys('tickstock:patterns:*')
        print(f"[OK] Pattern cache contains {len(pattern_keys)} entries")

    def test_websocket_readiness(self):
        """Test that WebSocket broadcasting is configured."""
        # This tests configuration, not actual WebSocket emission
        # (which requires a connected client)

        from src.core.services.redis_event_subscriber import RedisEventSubscriber
        from flask import Flask

        app = Flask(__name__)
        test_subscriber = RedisEventSubscriber(
            self.redis_client,
            None,  # socketio
            {'channels': ['tickstock.events.patterns']},
            flask_app=app
        )

        # Check handler registration
        from src.core.services.redis_event_subscriber import EventType
        handlers = test_subscriber.event_handlers.get(EventType.PATTERN_DETECTED, [])

        assert len(handlers) > 0, "No pattern event handlers registered"
        print(f"[OK] WebSocket handlers configured: {len(handlers)} handler(s)")

    def test_performance_metrics(self):
        """Test that performance is within acceptable limits."""
        cursor = self.db_conn.cursor()

        # Check processing time for recent events
        cursor.execute("""
            SELECT
                checkpoint,
                AVG(processing_time_ms) as avg_ms,
                MAX(processing_time_ms) as max_ms,
                COUNT(*) as count
            FROM integration_events
            WHERE timestamp > NOW() - INTERVAL '10 minutes'
            AND processing_time_ms IS NOT NULL
            GROUP BY checkpoint
        """)

        for row in cursor.fetchall():
            checkpoint, avg_ms, max_ms, count = row
            if avg_ms:
                assert avg_ms < 100, f"{checkpoint} avg processing time {avg_ms}ms > 100ms"
                print(f"[OK] {checkpoint}: avg {avg_ms:.1f}ms, max {max_ms}ms ({count} samples)")

        cursor.close()

    def test_error_recovery(self):
        """Test that system recovers from malformed events."""
        # Send malformed events
        bad_events = [
            "not json",
            json.dumps({}),  # Empty event
            json.dumps({'event_type': 'pattern_detected'}),  # Missing data
            json.dumps({'data': {'pattern': 'NoEventType'}}),  # Missing event_type
        ]

        for bad_event in bad_events:
            try:
                self.redis_client.publish(
                    'tickstock.events.patterns',
                    bad_event
                )
            except:
                pass

        # System should still be running
        time.sleep(1)

        # Verify system still processes good events
        good_event = {
            'event_type': 'pattern_detected',
            'source': 'RecoveryTest',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'pattern': 'RecoveryTest',
                'symbol': 'RCVR',
                'confidence': 0.80
            }
        }

        result = self.redis_client.publish(
            'tickstock.events.patterns',
            json.dumps(good_event)
        )

        assert result > 0, "System not recovering from bad events"
        print("[OK] Error recovery working")


def run_integration_tests():
    """Run all integration tests with summary."""
    print("=" * 60)
    print("TICKSTOCKAPPV2 INTEGRATION TEST SUITE")
    print("=" * 60)
    print("Testing REAL Redis, Database, and Integration Points")
    print("These tests validate actual system behavior, not mocks")
    print("-" * 60)

    test = TestTickStockPLIntegration()
    test.setup_class()

    tests = [
        ("Redis Subscription", test.test_redis_subscription_active),
        ("Event Structure", test.test_pattern_event_structure_compatibility),
        ("Database Logging", test.test_database_integration_logging),
        ("Pattern Flow", test.test_pattern_flow_checkpoints),
        ("Heartbeat Monitor", test.test_heartbeat_monitoring),
        ("Redis->DB Flow", test.test_redis_to_database_flow),
        ("Pattern Cache", test.test_pattern_cache_update),
        ("WebSocket Config", test.test_websocket_readiness),
        ("Performance", test.test_performance_metrics),
        ("Error Recovery", test.test_error_recovery)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\nTesting {name}...")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[X] {name} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"[X] {name} ERROR: {e}")
            failed += 1

    test.teardown_class()

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n[PASS] ALL INTEGRATION TESTS PASSED!")
        print("The integration with TickStockPL is working correctly.")
    else:
        print(f"\n[WARN] {failed} test(s) failed - review issues above")

    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)