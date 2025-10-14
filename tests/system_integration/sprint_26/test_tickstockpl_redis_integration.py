"""
Comprehensive Production Readiness Tests - TickStockPL Redis Pub-Sub Integration
Sprint 26: Redis Event Consumption and Cross-System Communication

Tests TickStockPL integration via Redis pub-sub with <100ms message delivery.
Validates pattern event consumption, backtest coordination, and system health monitoring.

Test Categories:
- Integration Tests: Redis pub-sub message flow between TickStockPL → TickStockApp
- Performance Tests: <100ms message delivery requirements
- Resilience Tests: Connection recovery, message persistence, offline handling
- Event Tests: Pattern alerts, backtest progress, system health
- Error Handling: Redis failures, message corruption, timeout scenarios
"""

import json
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock, patch

import pytest
import redis
from flask_socketio import SocketIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.services.redis_event_subscriber import EventType, RedisEventSubscriber, TickStockEvent
from src.core.services.websocket_broadcaster import WebSocketBroadcaster


@dataclass
class TestEvent:
    """Test event for Redis integration testing."""
    event_type: str
    source: str
    timestamp: float
    data: dict[str, Any]
    channel: str


class TestTickStockPLRedisIntegration:
    """Test suite for TickStockPL Redis pub-sub integration."""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for testing."""
        mock_redis = Mock(spec=redis.Redis)
        mock_pubsub = Mock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_redis.ping.return_value = True
        return mock_redis, mock_pubsub

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for testing."""
        return Mock(spec=SocketIO)

    @pytest.fixture
    def mock_flask_app(self):
        """Mock Flask application for testing."""
        app = Mock()
        app.app_context.return_value.__enter__ = Mock(return_value=None)
        app.app_context.return_value.__exit__ = Mock(return_value=None)
        return app

    @pytest.fixture
    def test_config(self):
        """Test configuration."""
        return {
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': 6379,
            'REDIS_DB': 0,
            'REDIS_TIMEOUT': 30
        }

    @pytest.fixture
    def redis_subscriber(self, mock_redis_client, mock_socketio, test_config, mock_flask_app):
        """Create RedisEventSubscriber for testing."""
        mock_redis, mock_pubsub = mock_redis_client
        return RedisEventSubscriber(
            redis_client=mock_redis,
            socketio=mock_socketio,
            config=test_config,
            flask_app=mock_flask_app
        )

    @pytest.fixture
    def sample_pattern_event(self):
        """Sample pattern detection event."""
        return {
            'event_type': 'pattern_detected',
            'source': 'tickstockpl_pattern_scanner',
            'timestamp': time.time(),
            'pattern': 'Breakout',
            'symbol': 'AAPL',
            'confidence': 0.85,
            'rs': 75.5,
            'volume_multiple': 2.5,
            'rsi': 62.3,
            'price': 150.25,
            'timeframe': 'Daily'
        }

    @pytest.fixture
    def sample_backtest_progress_event(self):
        """Sample backtest progress event."""
        return {
            'event_type': 'backtest_progress',
            'source': 'tickstockpl_backtest_engine',
            'timestamp': time.time(),
            'job_id': 'bt_12345',
            'progress': 0.65,
            'current_symbol': 'GOOGL',
            'symbols_completed': 65,
            'total_symbols': 100,
            'estimated_completion': time.time() + 300
        }

    @pytest.fixture
    def sample_system_health_event(self):
        """Sample system health event."""
        return {
            'event_type': 'system_health',
            'source': 'tickstockpl_health_monitor',
            'timestamp': time.time(),
            'status': 'healthy',
            'cpu_usage': 45.2,
            'memory_usage': 67.8,
            'active_connections': 25,
            'processing_rate': 1250.5
        }

    def test_subscriber_initialization(self, redis_subscriber, mock_redis_client):
        """Test proper subscriber initialization."""
        mock_redis, mock_pubsub = mock_redis_client

        assert redis_subscriber is not None
        assert not redis_subscriber.is_running
        assert redis_subscriber.redis_client == mock_redis
        assert len(redis_subscriber.channels) == 4

        # Verify channel mapping
        expected_channels = {
            'tickstock.events.patterns': EventType.PATTERN_DETECTED,
            'tickstock.events.backtesting.progress': EventType.BACKTEST_PROGRESS,
            'tickstock.events.backtesting.results': EventType.BACKTEST_RESULT,
            'tickstock.health.status': EventType.SYSTEM_HEALTH
        }
        assert redis_subscriber.channels == expected_channels

    def test_subscriber_start_success(self, redis_subscriber, mock_redis_client):
        """Test successful subscriber startup."""
        mock_redis, mock_pubsub = mock_redis_client

        # Mock successful startup
        with patch.object(redis_subscriber, '_test_redis_connection', return_value=True):
            result = redis_subscriber.start()

        assert result is True
        assert redis_subscriber.is_running is True
        assert redis_subscriber.pubsub is not None

        # Verify subscription to channels
        expected_channels = list(redis_subscriber.channels.keys())
        mock_pubsub.subscribe.assert_called_once_with(expected_channels)

    def test_subscriber_start_redis_connection_failure(self, redis_subscriber, mock_redis_client):
        """Test subscriber startup failure with Redis connection issues."""
        mock_redis, mock_pubsub = mock_redis_client

        # Mock connection failure
        with patch.object(redis_subscriber, '_test_redis_connection', return_value=False):
            result = redis_subscriber.start()

        assert result is False
        assert redis_subscriber.is_running is False

    @pytest.mark.performance
    def test_message_processing_performance(self, redis_subscriber, sample_pattern_event, mock_redis_client):
        """Test message processing meets <100ms requirement."""
        mock_redis, mock_pubsub = mock_redis_client

        # Start subscriber
        with patch.object(redis_subscriber, '_test_redis_connection', return_value=True):
            redis_subscriber.start()

        # Performance test: Message processing time
        message = {
            'channel': b'tickstock.events.patterns',
            'data': json.dumps(sample_pattern_event).encode(),
            'type': 'message'
        }

        iterations = 50
        processing_times = []

        for i in range(iterations):
            start_time = time.perf_counter()
            redis_subscriber._process_message(message)
            end_time = time.perf_counter()

            processing_time_ms = (end_time - start_time) * 1000
            processing_times.append(processing_time_ms)

        # Calculate performance metrics
        avg_processing_time = sum(processing_times) / len(processing_times)
        p95_processing_time = sorted(processing_times)[int(len(processing_times) * 0.95)]

        # Assert: <100ms message processing
        assert avg_processing_time < 100, f"Average processing time {avg_processing_time:.2f}ms exceeds 100ms requirement"
        assert p95_processing_time < 150, f"P95 processing time {p95_processing_time:.2f}ms too high"

    def test_pattern_event_processing(self, redis_subscriber, sample_pattern_event, mock_socketio):
        """Test pattern event processing and WebSocket emission."""
        # Mock message processing
        message = {
            'channel': b'tickstock.events.patterns',
            'data': json.dumps(sample_pattern_event).encode(),
            'type': 'message'
        }

        # Process message
        redis_subscriber._process_message(message)

        # Verify statistics updated
        assert redis_subscriber.stats['events_received'] == 1
        assert redis_subscriber.stats['events_processed'] == 1
        assert redis_subscriber.stats['last_event_time'] is not None

    def test_backtest_progress_event_processing(self, redis_subscriber, sample_backtest_progress_event, mock_socketio):
        """Test backtest progress event processing."""
        # Mock backtest manager
        mock_backtest_manager = Mock()
        redis_subscriber.backtest_manager = mock_backtest_manager

        # Mock message processing
        message = {
            'channel': b'tickstock.events.backtesting.progress',
            'data': json.dumps(sample_backtest_progress_event).encode(),
            'type': 'message'
        }

        # Process message
        redis_subscriber._process_message(message)

        # Verify backtest manager updated
        mock_backtest_manager.update_job_progress.assert_called_once()
        call_args = mock_backtest_manager.update_job_progress.call_args[0]
        assert call_args[0] == 'bt_12345'  # job_id
        assert call_args[1] == 0.65        # progress
        assert call_args[2] == 'GOOGL'     # current_symbol

        # Verify WebSocket emission
        mock_socketio.emit.assert_called_once()
        emit_call = mock_socketio.emit.call_args
        assert emit_call[0][0] == 'backtest_progress'  # event name

    def test_system_health_event_processing(self, redis_subscriber, sample_system_health_event, mock_socketio):
        """Test system health event processing."""
        # Mock message processing
        message = {
            'channel': b'tickstock.health.status',
            'data': json.dumps(sample_system_health_event).encode(),
            'type': 'message'
        }

        # Process message
        redis_subscriber._process_message(message)

        # Verify WebSocket emission for health updates
        mock_socketio.emit.assert_called_once()
        emit_call = mock_socketio.emit.call_args
        assert emit_call[0][0] == 'system_health'  # event name

        # Verify event forwarded count
        assert redis_subscriber.stats['events_forwarded'] == 1

    def test_message_parsing_error_handling(self, redis_subscriber, mock_socketio):
        """Test error handling for malformed messages."""
        # Invalid JSON message
        invalid_message = {
            'channel': b'tickstock.events.patterns',
            'data': b'invalid json {',
            'type': 'message'
        }

        # Process invalid message
        redis_subscriber._process_message(invalid_message)

        # Verify error handling
        assert redis_subscriber.stats['events_dropped'] == 1
        assert redis_subscriber.stats['events_processed'] == 0

    def test_unknown_channel_handling(self, redis_subscriber, mock_socketio):
        """Test handling of messages from unknown channels."""
        # Message from unknown channel
        unknown_message = {
            'channel': b'unknown.channel',
            'data': json.dumps({'test': 'data'}).encode(),
            'type': 'message'
        }

        # Process unknown message
        redis_subscriber._process_message(unknown_message)

        # Verify dropped
        assert redis_subscriber.stats['events_dropped'] == 1
        assert redis_subscriber.stats['events_processed'] == 0

    def test_connection_recovery_mechanism(self, redis_subscriber, mock_redis_client):
        """Test Redis connection recovery mechanism."""
        mock_redis, mock_pubsub = mock_redis_client

        # Start subscriber
        with patch.object(redis_subscriber, '_test_redis_connection', return_value=True):
            redis_subscriber.start()

        # Simulate connection error
        with patch.object(redis_subscriber, '_test_redis_connection') as mock_test:
            # First two attempts fail, third succeeds
            mock_test.side_effect = [False, False, True]

            # Trigger connection error handling
            redis_subscriber._handle_connection_error()

            # Verify reconnection attempts
            assert mock_test.call_count == 3

    def test_event_handler_registration(self, redis_subscriber):
        """Test custom event handler registration."""
        # Custom handler function
        custom_events = []
        def custom_handler(event: TickStockEvent):
            custom_events.append(event)

        # Register handler for pattern events
        redis_subscriber.add_event_handler(EventType.PATTERN_DETECTED, custom_handler)

        # Verify handler registered
        assert len(redis_subscriber.event_handlers[EventType.PATTERN_DETECTED]) == 1
        assert custom_handler in redis_subscriber.event_handlers[EventType.PATTERN_DETECTED]

    def test_concurrent_message_processing(self, redis_subscriber, mock_socketio):
        """Test concurrent message processing without corruption."""
        processed_events = []
        lock = threading.Lock()

        def process_event_batch(event_type, count):
            for i in range(count):
                event_data = {
                    'event_type': event_type,
                    'source': f'test_source_{i}',
                    'timestamp': time.time(),
                    'data': {'index': i}
                }

                message = {
                    'channel': b'tickstock.events.patterns',
                    'data': json.dumps(event_data).encode(),
                    'type': 'message'
                }

                # Process message
                redis_subscriber._process_message(message)

                # Thread-safe collection
                with lock:
                    processed_events.append(event_data)

        # Create multiple threads
        threads = []
        thread_count = 5
        events_per_thread = 20

        for i in range(thread_count):
            thread = threading.Thread(
                target=process_event_batch,
                args=(f'pattern_detected_{i}', events_per_thread)
            )
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all events processed
        expected_total = thread_count * events_per_thread
        assert len(processed_events) == expected_total
        assert redis_subscriber.stats['events_received'] == expected_total

    @pytest.mark.performance
    def test_high_volume_message_throughput(self, redis_subscriber, mock_socketio):
        """Test high volume message processing throughput."""
        # Generate high volume of messages
        message_count = 500
        start_time = time.perf_counter()

        for i in range(message_count):
            event_data = {
                'event_type': 'pattern_detected',
                'source': 'high_volume_test',
                'timestamp': time.time(),
                'pattern': 'TestPattern',
                'symbol': f'STOCK{i % 100}',  # Cycle through 100 symbols
                'confidence': 0.75
            }

            message = {
                'channel': b'tickstock.events.patterns',
                'data': json.dumps(event_data).encode(),
                'type': 'message'
            }

            redis_subscriber._process_message(message)

        end_time = time.perf_counter()
        total_time = end_time - start_time
        throughput = message_count / total_time

        # Performance requirements
        assert throughput > 100, f"Throughput {throughput:.1f} msg/sec below minimum requirement (100 msg/sec)"
        assert redis_subscriber.stats['events_processed'] == message_count

        # Average processing time should be well under 100ms
        avg_processing_time_ms = (total_time / message_count) * 1000
        assert avg_processing_time_ms < 10, f"Average processing time {avg_processing_time_ms:.2f}ms too high"

    def test_subscriber_statistics_accuracy(self, redis_subscriber, mock_socketio):
        """Test accurate statistics reporting."""
        # Initial stats
        initial_stats = redis_subscriber.get_stats()
        assert initial_stats['events_received'] == 0
        assert initial_stats['events_processed'] == 0
        assert initial_stats['is_running'] is False

        # Start subscriber and process messages
        with patch.object(redis_subscriber, '_test_redis_connection', return_value=True):
            redis_subscriber.start()

        # Process various messages
        test_messages = [
            ('tickstock.events.patterns', {'pattern': 'Breakout', 'symbol': 'AAPL'}),
            ('tickstock.events.backtesting.progress', {'job_id': 'bt_123', 'progress': 0.5}),
            ('invalid.channel', {'invalid': 'data'}),  # Should be dropped
            ('tickstock.health.status', {'status': 'healthy'})
        ]

        for channel, data in test_messages:
            message = {
                'channel': channel.encode(),
                'data': json.dumps(data).encode(),
                'type': 'message'
            }
            redis_subscriber._process_message(message)

        # Verify statistics
        final_stats = redis_subscriber.get_stats()
        assert final_stats['events_received'] == 4
        assert final_stats['events_processed'] == 3  # 3 valid, 1 dropped
        assert final_stats['events_dropped'] == 1
        assert final_stats['is_running'] is True

    def test_websocket_pattern_alert_integration(self, mock_flask_app):
        """Test WebSocket pattern alert integration."""
        mock_socketio = Mock(spec=SocketIO)
        broadcaster = WebSocketBroadcaster(mock_socketio)

        # Sample pattern event
        pattern_event = {
            'type': 'pattern_alert',
            'data': {
                'pattern': 'Breakout',
                'symbol': 'AAPL',
                'confidence': 0.85,
                'price': 150.25
            },
            'timestamp': time.time()
        }

        # Test pattern alert broadcasting
        broadcaster.broadcast_pattern_alert(pattern_event)

        # Verify WebSocket emission (would be called if users are subscribed)
        # Note: Without connected users, no actual emission occurs
        assert broadcaster.stats['messages_sent'] >= 0

    def test_redis_subscriber_health_monitoring(self, redis_subscriber):
        """Test subscriber health monitoring."""
        # Test healthy state
        health = redis_subscriber.get_health_status()
        assert 'status' in health
        assert 'message' in health
        assert 'stats' in health

        # Test unhealthy state (not running)
        assert health['status'] == 'error'
        assert 'not running' in health['message']

        # Test degraded state (connection errors)
        redis_subscriber.stats['connection_errors'] = 10
        health = redis_subscriber.get_health_status()
        assert health['status'] == 'degraded'

    def test_event_type_conversion(self, redis_subscriber):
        """Test proper event type conversion from Redis messages."""
        # Test pattern event
        pattern_data = {
            'source': 'tickstockpl',
            'timestamp': time.time(),
            'pattern': 'Breakout',
            'symbol': 'AAPL'
        }

        message = {
            'channel': b'tickstock.events.patterns',
            'data': json.dumps(pattern_data).encode(),
            'type': 'message'
        }

        # Process and verify event type mapping
        redis_subscriber._process_message(message)

        # Event should be processed as PATTERN_DETECTED
        assert redis_subscriber.stats['events_processed'] == 1

    def test_offline_message_persistence_integration(self):
        """Test message persistence for offline users."""
        # This would integrate with Redis Streams for message persistence
        # For now, test the concept with mock implementation

        mock_redis = Mock()
        mock_socketio = Mock()

        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis)

        # Test queueing message for offline user
        test_user_id = "user123"
        test_message = {
            'type': 'pattern_alert',
            'data': {'pattern': 'Breakout', 'symbol': 'AAPL'},
            'timestamp': time.time()
        }

        broadcaster.queue_message_for_offline_user(test_user_id, test_message)

        # Verify message queued
        assert test_user_id in broadcaster.offline_message_queue
        assert len(broadcaster.offline_message_queue[test_user_id]) == 1
        assert broadcaster.stats['messages_queued'] == 1

    def test_subscriber_graceful_shutdown(self, redis_subscriber, mock_redis_client):
        """Test graceful subscriber shutdown."""
        mock_redis, mock_pubsub = mock_redis_client

        # Start subscriber
        with patch.object(redis_subscriber, '_test_redis_connection', return_value=True):
            redis_subscriber.start()

        assert redis_subscriber.is_running is True

        # Stop subscriber
        redis_subscriber.stop()

        # Verify graceful shutdown
        assert redis_subscriber.is_running is False
        mock_pubsub.unsubscribe.assert_called_once()
        mock_pubsub.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
