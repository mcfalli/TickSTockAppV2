"""
RedisEventSubscriber Integration Tests
Comprehensive integration tests for Redis event consumption and processing.

Sprint 10 Phase 2: Validate Redis pub-sub message flow, event processing,
error handling, reconnection logic, and performance requirements.
"""

import pytest
import threading
import time
import json
from unittest.mock import Mock, patch, MagicMock
import redis

from .fixtures import (
    MockRedisClient, MockSocketIO, TickStockPLSimulator,
    assert_redis_message_valid, assert_performance_acceptable
)

# Import components under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from core.services.redis_event_subscriber import (
    RedisEventSubscriber, EventType, TickStockEvent
)


class TestRedisEventSubscriberIntegration:
    """Integration tests for RedisEventSubscriber service."""

    def test_subscriber_initialization_and_startup(self, mock_redis_client, mock_socketio, test_config):
        """Test subscriber initializes and starts successfully."""
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        
        # Verify initialization state
        assert subscriber.redis_client == mock_redis_client
        assert subscriber.socketio == mock_socketio
        assert subscriber.is_running is False
        assert len(subscriber.channels) == 4
        assert subscriber.pubsub is None
        
        # Test successful startup
        success = subscriber.start()
        assert success is True
        assert subscriber.is_running is True
        assert subscriber.pubsub is not None
        assert subscriber.subscriber_thread is not None
        assert subscriber.subscriber_thread.is_alive()
        
        # Verify channels subscribed
        expected_channels = [
            'tickstock.events.patterns',
            'tickstock.events.backtesting.progress',
            'tickstock.events.backtesting.results',
            'tickstock.health.status'
        ]
        assert subscriber.pubsub.subscribed_channels == set(expected_channels)
        
        # Cleanup
        subscriber.stop()
        
    def test_subscriber_startup_failure_with_redis_down(self, mock_socketio, test_config):
        """Test subscriber handles Redis connection failure gracefully."""
        # Create Redis client that fails ping
        failed_redis = MockRedisClient()
        failed_redis.simulate_connection_failure()
        
        subscriber = RedisEventSubscriber(failed_redis, mock_socketio, test_config)
        
        # Test startup failure
        success = subscriber.start()
        assert success is False
        assert subscriber.is_running is False
        assert subscriber.pubsub is None
        assert subscriber.subscriber_thread is None
        
    def test_pattern_event_processing(self, redis_subscriber, tickstockpl_simulator, performance_timer):
        """Test pattern detection event processing and forwarding."""
        # Start subscriber
        assert redis_subscriber.start() is True
        
        # Track received events
        received_events = []
        redis_subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: received_events.append(event)
        )
        
        # Simulate TickStockPL publishing pattern event
        performance_timer.start()
        sent_event = tickstockpl_simulator.publish_pattern_event(
            symbol='AAPL', 
            pattern='Doji', 
            confidence=0.85
        )
        
        # Wait for processing
        time.sleep(0.1)
        performance_timer.stop()
        
        # Verify event received and processed
        assert len(received_events) == 1
        received_event = received_events[0]
        
        assert received_event.event_type == EventType.PATTERN_DETECTED
        assert received_event.source == 'tickstock_pl'
        assert received_event.data['pattern'] == 'Doji'
        assert received_event.data['symbol'] == 'AAPL'
        assert received_event.data['confidence'] == 0.85
        assert received_event.channel == 'tickstock.events.patterns'
        
        # Verify performance requirement
        assert_performance_acceptable(performance_timer.elapsed_ms, max_ms=100)
        
        # Verify SocketIO emission
        assert len(redis_subscriber.socketio.broadcast_messages) == 1
        websocket_message = redis_subscriber.socketio.broadcast_messages[0]
        assert websocket_message['event'] == 'pattern_alert'
        assert websocket_message['data']['type'] == 'pattern_alert'
        
        # Verify statistics updated
        stats = redis_subscriber.get_stats()
        assert stats['events_received'] == 1
        assert stats['events_processed'] == 1
        assert stats['events_forwarded'] == 1
        assert stats['events_dropped'] == 0
        
        redis_subscriber.stop()
        
    def test_backtest_progress_processing(self, redis_subscriber, tickstockpl_simulator):
        """Test backtest progress event processing."""
        assert redis_subscriber.start() is True
        
        received_events = []
        redis_subscriber.add_event_handler(
            EventType.BACKTEST_PROGRESS,
            lambda event: received_events.append(event)
        )
        
        # Simulate backtest progress updates
        job_id = 'test_job_12345'
        progress_values = [0.25, 0.50, 0.75, 1.0]
        
        for progress in progress_values:
            tickstockpl_simulator.publish_backtest_progress(
                job_id=job_id,
                progress=progress,
                status='processing' if progress < 1.0 else 'completed'
            )
        
        # Wait for processing
        time.sleep(0.2)
        
        # Verify all progress events received
        assert len(received_events) == 4
        
        for i, event in enumerate(received_events):
            assert event.event_type == EventType.BACKTEST_PROGRESS
            assert event.data['job_id'] == job_id
            assert event.data['progress'] == progress_values[i]
            
        # Verify SocketIO emissions
        assert len(redis_subscriber.socketio.broadcast_messages) == 4
        
        redis_subscriber.stop()
        
    def test_backtest_result_processing(self, redis_subscriber, tickstockpl_simulator):
        """Test backtest result event processing."""
        assert redis_subscriber.start() is True
        
        received_events = []
        redis_subscriber.add_event_handler(
            EventType.BACKTEST_RESULT,
            lambda event: received_events.append(event)
        )
        
        # Simulate backtest completion
        job_id = 'test_job_67890'
        result_data = tickstockpl_simulator.publish_backtest_result(
            job_id=job_id,
            status='completed'
        )
        
        time.sleep(0.1)
        
        # Verify result event received
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.event_type == EventType.BACKTEST_RESULT
        assert event.data['job_id'] == job_id
        assert event.data['status'] == 'completed'
        assert 'results' in event.data
        assert event.data['results']['win_rate'] == 0.65
        
        # Verify SocketIO emission
        assert len(redis_subscriber.socketio.broadcast_messages) == 1
        
        redis_subscriber.stop()
        
    def test_system_health_processing(self, redis_subscriber, tickstockpl_simulator):
        """Test system health event processing."""
        assert redis_subscriber.start() is True
        
        received_events = []
        redis_subscriber.add_event_handler(
            EventType.SYSTEM_HEALTH,
            lambda event: received_events.append(event)
        )
        
        # Simulate system health updates
        health_statuses = ['healthy', 'degraded', 'error', 'healthy']
        
        for status in health_statuses:
            tickstockpl_simulator.publish_system_health(status=status)
            
        time.sleep(0.2)
        
        # Verify all health events received
        assert len(received_events) == 4
        
        for i, event in enumerate(received_events):
            assert event.event_type == EventType.SYSTEM_HEALTH
            assert event.data['status'] == health_statuses[i]
            
        redis_subscriber.stop()
        
    def test_invalid_message_handling(self, redis_subscriber, mock_redis_client):
        """Test handling of invalid JSON messages."""
        assert redis_subscriber.start() is True
        
        # Publish invalid JSON
        mock_redis_client.publish('tickstock.events.patterns', 'invalid json {')
        
        time.sleep(0.1)
        
        # Verify error handling
        stats = redis_subscriber.get_stats()
        assert stats['events_received'] == 1
        assert stats['events_processed'] == 0  # Should not be processed
        assert stats['events_dropped'] == 1    # Should be dropped
        
        redis_subscriber.stop()
        
    def test_unknown_channel_handling(self, redis_subscriber, mock_redis_client):
        """Test handling of messages from unknown channels."""
        assert redis_subscriber.start() is True
        
        # Publish to unknown channel
        test_data = json.dumps({
            'event_type': 'unknown_event',
            'source': 'tickstock_pl',
            'timestamp': time.time()
        })
        mock_redis_client.publish('unknown.channel', test_data)
        
        time.sleep(0.1)
        
        # Verify unknown channel handling
        stats = redis_subscriber.get_stats()
        # Message won't be received because we're not subscribed to unknown channels
        assert stats['events_received'] == 0
        
        redis_subscriber.stop()
        
    def test_connection_error_and_recovery(self, redis_subscriber, mock_redis_client):
        """Test Redis connection error handling and recovery."""
        assert redis_subscriber.start() is True
        
        # Wait for subscriber to be fully started
        time.sleep(0.1)
        
        initial_stats = redis_subscriber.get_stats()
        initial_errors = initial_stats['connection_errors']
        
        # Simulate connection failure
        mock_redis_client.simulate_connection_failure()
        
        # Wait for error to be detected
        time.sleep(0.2)
        
        # Verify connection error tracked
        error_stats = redis_subscriber.get_stats()
        assert error_stats['connection_errors'] > initial_errors
        
        # Restore connection
        mock_redis_client.restore_connection()
        
        # Wait for recovery
        time.sleep(0.2)
        
        # Test that subscriber can still process events after recovery
        received_events = []
        redis_subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: received_events.append(event)
        )
        
        # Should be able to publish and receive after recovery
        test_event = {
            'event_type': 'pattern_detected',
            'source': 'tickstock_pl',
            'timestamp': time.time(),
            'pattern': 'Hammer',
            'symbol': 'GOOGL'
        }
        mock_redis_client.publish('tickstock.events.patterns', json.dumps(test_event))
        
        time.sleep(0.1)
        
        # Verify recovery worked
        assert len(received_events) == 1
        
        redis_subscriber.stop()
        
    def test_multiple_event_handlers(self, redis_subscriber, tickstockpl_simulator):
        """Test multiple event handlers for same event type."""
        assert redis_subscriber.start() is True
        
        # Register multiple handlers for pattern events
        handler1_calls = []
        handler2_calls = []
        handler3_calls = []
        
        redis_subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: handler1_calls.append(event.data['pattern'])
        )
        redis_subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: handler2_calls.append(event.data['symbol'])
        )
        redis_subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: handler3_calls.append(event.data['confidence'])
        )
        
        # Publish pattern event
        tickstockpl_simulator.publish_pattern_event(
            symbol='TSLA',
            pattern='Engulfing',
            confidence=0.92
        )
        
        time.sleep(0.1)
        
        # Verify all handlers called
        assert len(handler1_calls) == 1
        assert handler1_calls[0] == 'Engulfing'
        
        assert len(handler2_calls) == 1
        assert handler2_calls[0] == 'TSLA'
        
        assert len(handler3_calls) == 1
        assert handler3_calls[0] == 0.92
        
        redis_subscriber.stop()
        
    def test_event_handler_exception_handling(self, redis_subscriber, tickstockpl_simulator):
        """Test that event handler exceptions don't crash subscriber."""
        assert redis_subscriber.start() is True
        
        # Register handlers - one that works, one that raises exception
        successful_calls = []
        
        def failing_handler(event):
            raise ValueError("Handler intentionally failed")
            
        def working_handler(event):
            successful_calls.append(event.data['pattern'])
        
        redis_subscriber.add_event_handler(EventType.PATTERN_DETECTED, failing_handler)
        redis_subscriber.add_event_handler(EventType.PATTERN_DETECTED, working_handler)
        
        # Publish pattern event
        tickstockpl_simulator.publish_pattern_event(
            symbol='MSFT',
            pattern='Doji'
        )
        
        time.sleep(0.1)
        
        # Verify working handler still executed despite failing handler
        assert len(successful_calls) == 1
        assert successful_calls[0] == 'Doji'
        
        # Verify subscriber is still running
        assert redis_subscriber.is_running is True
        
        redis_subscriber.stop()
        
    def test_subscriber_statistics(self, redis_subscriber, tickstockpl_simulator):
        """Test subscriber statistics tracking."""
        initial_stats = redis_subscriber.get_stats()
        assert initial_stats['events_received'] == 0
        assert initial_stats['events_processed'] == 0
        assert initial_stats['events_forwarded'] == 0
        assert initial_stats['events_dropped'] == 0
        assert initial_stats['is_running'] is False
        
        assert redis_subscriber.start() is True
        
        running_stats = redis_subscriber.get_stats()
        assert running_stats['is_running'] is True
        assert running_stats['active_thread'] is True
        assert len(running_stats['subscribed_channels']) == 4
        
        # Process some events
        for i in range(3):
            tickstockpl_simulator.publish_pattern_event(
                symbol=f'TEST{i}',
                pattern='TestPattern'
            )
            
        # Add invalid message
        redis_subscriber.redis_client.publish(
            'tickstock.events.patterns', 
            'invalid json'
        )
        
        time.sleep(0.2)
        
        final_stats = redis_subscriber.get_stats()
        assert final_stats['events_received'] == 4  # 3 valid + 1 invalid
        assert final_stats['events_processed'] == 3  # Only valid ones processed
        assert final_stats['events_forwarded'] == 3  # All processed events forwarded
        assert final_stats['events_dropped'] == 1    # Invalid message dropped
        assert final_stats['events_per_second'] > 0   # Should have event rate
        
        redis_subscriber.stop()
        
    def test_health_status_monitoring(self, redis_subscriber, tickstockpl_simulator):
        """Test health status monitoring functionality."""
        # Test stopped state
        stopped_health = redis_subscriber.get_health_status()
        assert stopped_health['status'] == 'error'
        assert 'not running' in stopped_health['message']
        
        assert redis_subscriber.start() is True
        
        # Test healthy state
        healthy_state = redis_subscriber.get_health_status()
        assert healthy_state['status'] == 'healthy'
        assert 'operating normally' in healthy_state['message']
        
        # Simulate many connection errors
        for _ in range(6):
            redis_subscriber.stats['connection_errors'] += 1
            
        degraded_health = redis_subscriber.get_health_status()
        assert degraded_health['status'] == 'degraded'
        assert 'connection errors' in degraded_health['message']
        
        # Reset connection errors, simulate old last event
        redis_subscriber.stats['connection_errors'] = 0
        redis_subscriber.stats['last_event_time'] = time.time() - 400  # 400 seconds ago
        
        warning_health = redis_subscriber.get_health_status()
        assert warning_health['status'] == 'warning'
        assert 'No events received' in warning_health['message']
        
        redis_subscriber.stop()
        
    def test_concurrent_message_processing(self, redis_subscriber, tickstockpl_simulator, performance_timer):
        """Test handling of concurrent message processing."""
        assert redis_subscriber.start() is True
        
        received_events = []
        redis_subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: received_events.append(event)
        )
        
        # Publish multiple events rapidly
        performance_timer.start()
        patterns = ['Doji', 'Hammer', 'Engulfing', 'Morning Star', 'Evening Star']
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
        
        for pattern, symbol in zip(patterns, symbols):
            tickstockpl_simulator.publish_pattern_event(
                symbol=symbol,
                pattern=pattern,
                confidence=0.8
            )
            
        time.sleep(0.3)  # Wait for all events to process
        performance_timer.stop()
        
        # Verify all events processed
        assert len(received_events) == 5
        
        # Verify performance acceptable for batch processing
        assert_performance_acceptable(performance_timer.elapsed_ms, max_ms=300)
        
        # Verify all unique patterns received
        received_patterns = [e.data['pattern'] for e in received_events]
        assert set(received_patterns) == set(patterns)
        
        redis_subscriber.stop()
        
    def test_graceful_shutdown(self, redis_subscriber, tickstockpl_simulator):
        """Test graceful subscriber shutdown."""
        assert redis_subscriber.start() is True
        
        # Verify running state
        assert redis_subscriber.is_running is True
        assert redis_subscriber.subscriber_thread.is_alive()
        
        # Publish event during shutdown
        tickstockpl_simulator.publish_pattern_event(
            symbol='AAPL',
            pattern='TestPattern'
        )
        
        time.sleep(0.1)
        
        # Shutdown
        redis_subscriber.stop()
        
        # Verify stopped state
        assert redis_subscriber.is_running is False
        
        # Wait for thread to finish
        time.sleep(0.5)
        assert not redis_subscriber.subscriber_thread.is_alive()
        
        # Verify pubsub cleaned up
        assert redis_subscriber.pubsub.closed is True
        
    def test_websocket_dict_conversion(self, redis_subscriber, tickstockpl_simulator):
        """Test TickStockEvent to WebSocket dict conversion."""
        assert redis_subscriber.start() is True
        
        received_events = []
        redis_subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: received_events.append(event)
        )
        
        # Publish complex pattern event
        sent_event = tickstockpl_simulator.publish_pattern_event(
            symbol='COMPLEX_TEST',
            pattern='ComplexPattern',
            confidence=0.95
        )
        
        time.sleep(0.1)
        
        # Verify event received
        assert len(received_events) == 1
        event = received_events[0]
        
        # Test WebSocket dict conversion
        websocket_dict = event.to_websocket_dict()
        
        expected_keys = ['event_type', 'source', 'timestamp', 'data', 'channel']
        assert all(key in websocket_dict for key in expected_keys)
        
        assert websocket_dict['event_type'] == 'pattern_detected'
        assert websocket_dict['source'] == 'tickstock_pl'
        assert websocket_dict['data']['pattern'] == 'ComplexPattern'
        assert websocket_dict['data']['symbol'] == 'COMPLEX_TEST'
        assert websocket_dict['data']['confidence'] == 0.95
        assert websocket_dict['channel'] == 'tickstock.events.patterns'
        
        redis_subscriber.stop()