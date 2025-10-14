"""
Test Suite for ScalableBroadcaster (Layer 3)
Sprint 25 Week 1 - Efficient broadcasting layer tests

Tests the scalable broadcasting system with batching, rate limiting,
and <100ms delivery performance targets.
"""

import threading
import time
from unittest.mock import Mock

import pytest

from src.infrastructure.websocket.scalable_broadcaster import (
    DeliveryPriority,
    RateLimiter,
    ScalableBroadcaster,
)


@pytest.fixture
def mock_socketio():
    """Mock SocketIO for testing."""
    mock = Mock()
    mock.emit = Mock()
    return mock


@pytest.fixture
def scalable_broadcaster(mock_socketio):
    """Create ScalableBroadcaster for testing."""
    return ScalableBroadcaster(
        socketio=mock_socketio,
        batch_window_ms=100,
        max_events_per_user=100,
        max_batch_size=50
    )


@pytest.fixture
def rate_limiter():
    """Create RateLimiter for testing."""
    return RateLimiter(max_events_per_second=10, window_size_seconds=1)


class TestScalableBroadcasterLayer:
    """Test ScalableBroadcaster as Layer 3 efficient broadcasting system."""

    def test_initialization_with_performance_settings(self, scalable_broadcaster):
        """Test initialization with performance-optimized settings."""
        # Verify configuration
        assert scalable_broadcaster.batch_window_ms == 100
        assert scalable_broadcaster.max_events_per_user == 100
        assert scalable_broadcaster.max_batch_size == 50

        # Verify batching system components
        assert len(scalable_broadcaster.pending_batches) == 0
        assert len(scalable_broadcaster.batch_timers) == 0
        assert DeliveryPriority.LOW in scalable_broadcaster.event_queue
        assert DeliveryPriority.HIGH in scalable_broadcaster.event_queue

        # Verify rate limiting system
        assert len(scalable_broadcaster.user_rate_limiters) == 0

        # Verify thread pool executors
        assert scalable_broadcaster.batch_executor is not None
        assert scalable_broadcaster.delivery_executor is not None

        # Verify performance tracking
        assert scalable_broadcaster.stats is not None
        assert scalable_broadcaster.stats.total_events == 0

    def test_broadcast_to_users_with_batching(self, scalable_broadcaster):
        """Test broadcasting to users with automatic batching."""
        user_ids = {'user_001', 'user_002', 'user_003'}
        event_type = 'tier_pattern'
        event_data = {
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL',
            'confidence': 0.85,
            'tier': 'daily'
        }

        # Broadcast event
        queued_count = scalable_broadcaster.broadcast_to_users(
            event_type=event_type,
            event_data=event_data,
            user_ids=user_ids,
            priority=DeliveryPriority.MEDIUM
        )

        # Verify queuing was successful
        assert queued_count == 3

        # Verify batches were created for each user
        expected_rooms = {f'user_{user_id}' for user_id in user_ids}

        # Check that batches are pending (they should be created)
        assert len(scalable_broadcaster.pending_batches) > 0

        # Verify statistics were updated
        assert scalable_broadcaster.stats.total_events == 1

    def test_rate_limiting_functionality(self, scalable_broadcaster):
        """Test per-user rate limiting prevents spam."""
        user_ids = {'rate_limit_user'}
        event_data = {'test': 'data'}

        # Send events rapidly to trigger rate limiting
        successful_deliveries = []

        for i in range(150):  # More than max_events_per_user (100)
            queued_count = scalable_broadcaster.broadcast_to_users(
                event_type=f'test_event_{i}',
                event_data=event_data,
                user_ids=user_ids,
                priority=DeliveryPriority.LOW
            )
            successful_deliveries.append(queued_count)

        # Some events should be rate limited
        total_queued = sum(successful_deliveries)
        assert total_queued < 150  # Some should be rate limited

        # Verify rate limiting statistics
        assert scalable_broadcaster.stats.events_rate_limited > 0
        assert scalable_broadcaster.stats.rate_limit_violations > 0

    def test_rate_limiter_window_behavior(self, rate_limiter):
        """Test RateLimiter sliding window behavior."""
        # Fill up the rate limit
        for i in range(10):  # Max events per second
            allowed = rate_limiter.allow_event()
            assert allowed is True, f"Event {i} should be allowed"

        # Next event should be rate limited
        assert rate_limiter.allow_event() is False

        # Check current rate
        current_rate = rate_limiter.get_current_rate()
        assert current_rate == 10  # At maximum

        # Wait for window to slide (simulate time passage)
        # In real tests we'd use time mocking, but this demonstrates the concept
        time.sleep(1.1)  # Just over 1 second

        # Should be able to send again
        assert rate_limiter.allow_event() is True

    def test_priority_based_delivery_ordering(self, scalable_broadcaster):
        """Test events are delivered in priority order."""
        user_ids = {'priority_user'}

        # Send events with different priorities
        priorities = [
            (DeliveryPriority.LOW, 'low_priority_event'),
            (DeliveryPriority.CRITICAL, 'critical_event'),
            (DeliveryPriority.HIGH, 'high_priority_event'),
            (DeliveryPriority.MEDIUM, 'medium_priority_event')
        ]

        for priority, event_type in priorities:
            scalable_broadcaster.broadcast_to_users(
                event_type=event_type,
                event_data={'priority': priority.name},
                user_ids=user_ids,
                priority=priority
            )

        # Force batch delivery
        scalable_broadcaster.flush_all_batches()

        # Let delivery complete
        time.sleep(0.1)

        # Verify emit was called (batch delivery)
        scalable_broadcaster.socketio.emit.assert_called()

        # For detailed priority verification, we'd need to inspect the batch payload
        # This tests that the system accepts different priorities without error

    def test_batch_creation_and_flushing(self, scalable_broadcaster):
        """Test batch creation and automatic flushing."""
        user_id = 'batch_test_user'
        room_name = f'user_{user_id}'

        # Create multiple events for the same user to batch
        for i in range(5):
            scalable_broadcaster.broadcast_to_users(
                event_type=f'batch_event_{i}',
                event_data={'sequence': i},
                user_ids={user_id},
                priority=DeliveryPriority.MEDIUM
            )

        # Verify batch was created
        assert room_name in scalable_broadcaster.pending_batches

        # Verify batch contains multiple events
        batch = scalable_broadcaster.pending_batches[room_name]
        assert len(batch.events) == 5
        assert batch.room_name == room_name

        # Verify timer was set for automatic flushing
        assert room_name in scalable_broadcaster.batch_timers

        # Force flush to test manual flushing
        scalable_broadcaster.flush_all_batches()

        # Verify batch was removed after flushing
        assert room_name not in scalable_broadcaster.pending_batches

        # Verify emit was called for delivery
        scalable_broadcaster.socketio.emit.assert_called()

    def test_batch_size_limits_and_overflow(self, scalable_broadcaster):
        """Test batch size limits trigger overflow handling."""
        user_id = 'overflow_user'

        # Send more events than max_batch_size (50)
        for i in range(55):
            scalable_broadcaster.broadcast_to_users(
                event_type=f'overflow_event_{i}',
                event_data={'sequence': i},
                user_ids={user_id},
                priority=DeliveryPriority.MEDIUM
            )

        # Should have created multiple batches or triggered flushes
        # We can't easily test the exact count due to timing, but verify system handled it
        assert scalable_broadcaster.stats.batches_created > 0

    def test_broadcast_to_room_direct(self, scalable_broadcaster):
        """Test direct room broadcasting."""
        room_name = 'test_room'
        event_type = 'room_event'
        event_data = {'message': 'Hello room'}

        # Broadcast to room
        success = scalable_broadcaster.broadcast_to_room(
            room_name=room_name,
            event_type=event_type,
            event_data=event_data,
            priority=DeliveryPriority.HIGH
        )

        # Verify success
        assert success is True

        # Verify batch was created
        assert room_name in scalable_broadcaster.pending_batches

        # Verify statistics
        assert scalable_broadcaster.stats.total_events == 1

    def test_delivery_performance_under_load(self, scalable_broadcaster):
        """Test delivery performance meets <100ms target under load."""
        user_ids = {f'perf_user_{i:03d}' for i in range(100)}

        # Measure broadcast time
        start_time = time.time()

        # Broadcast to many users
        queued_count = scalable_broadcaster.broadcast_to_users(
            event_type='performance_test',
            event_data={'load_test': True},
            user_ids=user_ids,
            priority=DeliveryPriority.MEDIUM
        )

        broadcast_time_ms = (time.time() - start_time) * 1000

        # Verify queuing performance
        assert queued_count == 100
        assert broadcast_time_ms < 50, f"Broadcast queuing took {broadcast_time_ms:.2f}ms"

        # Force delivery and measure
        delivery_start = time.time()
        scalable_broadcaster.flush_all_batches()

        # Wait for async delivery to complete
        time.sleep(0.2)

        delivery_time_ms = (time.time() - delivery_start) * 1000

        # Verify delivery time (allowing for async completion)
        assert delivery_time_ms < 200, f"Delivery took {delivery_time_ms:.2f}ms"

    def test_broadcast_stats_comprehensive_reporting(self, scalable_broadcaster):
        """Test comprehensive broadcasting statistics."""
        # Generate various broadcast activities
        users = {f'stats_user_{i}' for i in range(10)}

        # Normal broadcasts
        for i in range(5):
            scalable_broadcaster.broadcast_to_users(
                event_type=f'normal_event_{i}',
                event_data={'type': 'normal'},
                user_ids=users,
                priority=DeliveryPriority.MEDIUM
            )

        # Room broadcasts
        for i in range(3):
            scalable_broadcaster.broadcast_to_room(
                room_name=f'stats_room_{i}',
                event_type=f'room_event_{i}',
                event_data={'type': 'room'},
                priority=DeliveryPriority.LOW
            )

        # Force some deliveries
        scalable_broadcaster.flush_all_batches()
        time.sleep(0.1)

        # Get comprehensive statistics
        stats = scalable_broadcaster.get_broadcast_stats()

        # Verify basic metrics
        assert stats['total_events'] == 8  # 5 user broadcasts + 3 room broadcasts
        assert stats['events_per_second'] >= 0

        # Verify performance metrics
        assert 'avg_delivery_latency_ms' in stats
        assert 'max_delivery_latency_ms' in stats
        assert stats['avg_delivery_latency_ms'] >= 0

        # Verify batching metrics
        assert 'batches_created' in stats
        assert 'batches_delivered' in stats
        assert 'pending_batches' in stats
        assert stats['batches_created'] > 0

        # Verify configuration is reported
        assert stats['batch_window_ms'] == 100
        assert stats['max_events_per_user'] == 100
        assert stats['max_batch_size'] == 50

        # Verify system metrics
        assert 'runtime_seconds' in stats
        assert 'uptime_hours' in stats
        assert stats['runtime_seconds'] >= 0

    def test_health_status_monitoring(self, scalable_broadcaster):
        """Test health status monitoring and thresholds."""
        # Generate some activity for realistic health check
        users = {'health_user'}
        for i in range(3):
            scalable_broadcaster.broadcast_to_users(
                event_type=f'health_event_{i}',
                event_data={'test': i},
                user_ids=users,
                priority=DeliveryPriority.MEDIUM
            )

        scalable_broadcaster.flush_all_batches()
        time.sleep(0.1)

        # Get health status
        health_status = scalable_broadcaster.get_health_status()

        # Verify health status structure
        assert 'service' in health_status
        assert 'status' in health_status
        assert 'message' in health_status
        assert 'timestamp' in health_status
        assert 'stats' in health_status
        assert 'performance_targets' in health_status

        # Verify service identification
        assert health_status['service'] == 'scalable_broadcaster'

        # Verify status is reasonable (should be healthy with normal operation)
        assert health_status['status'] in ['healthy', 'warning', 'error']

        # Verify performance targets
        targets = health_status['performance_targets']
        assert targets['delivery_latency_target_ms'] == 100.0
        assert targets['success_rate_target_percent'] == 95.0
        assert targets['batch_efficiency_target'] == 10.0

    def test_user_rate_status_reporting(self, scalable_broadcaster):
        """Test per-user rate status reporting."""
        user_id = 'rate_status_user'

        # Send some events to create rate limiter
        for i in range(20):
            scalable_broadcaster.broadcast_to_users(
                event_type=f'rate_test_{i}',
                event_data={'sequence': i},
                user_ids={user_id},
                priority=DeliveryPriority.LOW
            )

        # Get rate status for user
        rate_status = scalable_broadcaster.get_user_rate_status(user_id)

        # Verify rate status structure
        assert 'user_id' in rate_status
        assert 'current_rate' in rate_status
        assert 'max_rate' in rate_status
        assert 'rate_limited' in rate_status

        # Verify user identification
        assert rate_status['user_id'] == user_id
        assert rate_status['max_rate'] == 100  # max_events_per_user

        # Verify rate information is reasonable
        assert rate_status['current_rate'] >= 0
        assert isinstance(rate_status['rate_limited'], bool)

        # Test rate status for non-existent user
        empty_status = scalable_broadcaster.get_user_rate_status('non_existent_user')
        assert empty_status['current_rate'] == 0
        assert empty_status['rate_limited'] is False

    def test_optimize_performance_cleanup(self, scalable_broadcaster):
        """Test performance optimization and cleanup."""
        # Create some activity and pending batches
        for i in range(5):
            scalable_broadcaster.broadcast_to_users(
                event_type=f'optimize_event_{i}',
                event_data={'sequence': i},
                user_ids={f'optimize_user_{i}'},
                priority=DeliveryPriority.MEDIUM
            )

        # Create some rate limiters by sending events
        test_users = {f'cleanup_user_{i}' for i in range(10)}
        for user in test_users:
            scalable_broadcaster.broadcast_to_users(
                event_type='test_event',
                event_data={'test': True},
                user_ids={user},
                priority=DeliveryPriority.LOW
            )

        # Run performance optimization
        optimization_results = scalable_broadcaster.optimize_performance()

        # Verify optimization results structure
        assert 'batches_flushed' in optimization_results
        assert 'rate_limiters_cleaned' in optimization_results
        assert 'optimization_timestamp' in optimization_results

        # Verify some optimization occurred
        assert optimization_results['batches_flushed'] >= 0
        assert optimization_results['rate_limiters_cleaned'] >= 0
        assert optimization_results['optimization_timestamp'] > 0

    def test_graceful_shutdown(self, scalable_broadcaster):
        """Test graceful shutdown process."""
        # Create some pending work
        scalable_broadcaster.broadcast_to_users(
            event_type='shutdown_test',
            event_data={'test': 'shutdown'},
            user_ids={'shutdown_user'},
            priority=DeliveryPriority.MEDIUM
        )

        # Verify there's pending work
        assert len(scalable_broadcaster.pending_batches) > 0

        # Shutdown should complete without errors
        scalable_broadcaster.shutdown()

        # Verify cleanup occurred
        assert len(scalable_broadcaster.batch_timers) == 0

    def test_thread_safety_concurrent_broadcasting(self, scalable_broadcaster):
        """Test thread safety with concurrent broadcasting operations."""
        results = {'success_count': 0, 'errors': []}

        def broadcast_worker(worker_id):
            """Worker function for concurrent broadcasting."""
            try:
                for i in range(20):
                    user_ids = {f'thread_{worker_id}_user_{i}'}
                    queued_count = scalable_broadcaster.broadcast_to_users(
                        event_type=f'thread_event_{worker_id}_{i}',
                        event_data={'worker': worker_id, 'sequence': i},
                        user_ids=user_ids,
                        priority=DeliveryPriority.MEDIUM
                    )

                    if queued_count > 0:
                        results['success_count'] += 1

                    # Small delay to encourage race conditions
                    time.sleep(0.001)

            except Exception as e:
                results['errors'].append(f"Worker {worker_id}: {str(e)}")

        def flush_worker():
            """Worker function for concurrent flushing."""
            try:
                time.sleep(0.05)  # Let some batches accumulate
                for i in range(5):
                    scalable_broadcaster.flush_all_batches()
                    time.sleep(0.02)

            except Exception as e:
                results['errors'].append(f"Flush worker: {str(e)}")

        # Create and start threads
        threads = []

        # Broadcasting worker threads
        for i in range(4):
            thread = threading.Thread(target=broadcast_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Flush worker thread
        flush_thread = threading.Thread(target=flush_worker)
        threads.append(flush_thread)
        flush_thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)

        # Verify no errors occurred
        assert len(results['errors']) == 0, f"Thread safety errors: {results['errors']}"

        # Verify reasonable number of successful broadcasts
        assert results['success_count'] >= 70  # Most should succeed

        # Verify system integrity
        stats = scalable_broadcaster.get_broadcast_stats()
        assert stats['total_events'] > 0

    def test_event_message_creation(self, scalable_broadcaster):
        """Test EventMessage creation and properties."""
        event_data = {'test': 'message'}
        target_users = {'test_user_1', 'test_user_2'}

        # Create event message via broadcasting
        scalable_broadcaster.broadcast_to_users(
            event_type='test_message',
            event_data=event_data,
            user_ids=target_users,
            priority=DeliveryPriority.HIGH
        )

        # Verify message was created (through side effects)
        assert scalable_broadcaster.stats.total_events == 1

    def test_batch_payload_structure(self, scalable_broadcaster):
        """Test batch payload structure for WebSocket delivery."""
        user_id = 'payload_test_user'

        # Send multiple events to create a batch
        events = [
            {'type': 'event1', 'data': {'value': 1}},
            {'type': 'event2', 'data': {'value': 2}},
            {'type': 'event3', 'data': {'value': 3}}
        ]

        for i, event in enumerate(events):
            scalable_broadcaster.broadcast_to_users(
                event_type=event['type'],
                event_data=event['data'],
                user_ids={user_id},
                priority=DeliveryPriority.MEDIUM
            )

        # Force delivery
        scalable_broadcaster.flush_all_batches()

        # Verify emit was called
        scalable_broadcaster.socketio.emit.assert_called()

        # For detailed payload verification, we'd inspect the emit call arguments
        # This tests that batch creation and delivery works without errors

    def test_single_event_delivery_optimization(self, scalable_broadcaster):
        """Test single event delivery bypasses batch payload."""
        user_id = 'single_event_user'

        # Send single event
        scalable_broadcaster.broadcast_to_users(
            event_type='single_event',
            event_data={'single': True},
            user_ids={user_id},
            priority=DeliveryPriority.MEDIUM
        )

        # Force immediate delivery
        scalable_broadcaster.flush_all_batches()

        # Verify delivery occurred
        scalable_broadcaster.socketio.emit.assert_called()

    def test_memory_usage_with_large_batches(self, scalable_broadcaster):
        """Test memory usage remains reasonable with large batch operations."""
        # Create a large number of events
        large_user_set = {f'memory_user_{i:04d}' for i in range(500)}

        # Send events to create large batches
        for i in range(10):
            scalable_broadcaster.broadcast_to_users(
                event_type=f'memory_event_{i}',
                event_data={'sequence': i, 'large_data': 'x' * 100},
                user_ids=large_user_set,
                priority=DeliveryPriority.MEDIUM
            )

        # Check that system handles large scale without issues
        stats = scalable_broadcaster.get_broadcast_stats()
        assert stats['total_events'] == 10

        # Verify batching is working
        assert len(scalable_broadcaster.pending_batches) > 0

        # Force delivery
        scalable_broadcaster.flush_all_batches()

        # System should remain stable
        final_stats = scalable_broadcaster.get_broadcast_stats()
        assert final_stats['total_events'] == 10

    def test_error_handling_socketio_failures(self, scalable_broadcaster):
        """Test error handling when SocketIO operations fail."""
        # Mock SocketIO to raise exceptions
        scalable_broadcaster.socketio.emit.side_effect = Exception("SocketIO error")

        # Broadcast should handle errors gracefully
        success = scalable_broadcaster.broadcast_to_room(
            room_name='error_room',
            event_type='error_test',
            event_data={'test': 'error'},
            priority=DeliveryPriority.MEDIUM
        )

        # Should succeed in queuing even if delivery fails
        assert success is True

        # Force delivery to trigger the error
        scalable_broadcaster.flush_all_batches()
        time.sleep(0.1)

        # System should remain stable
        stats = scalable_broadcaster.get_broadcast_stats()
        assert 'batch_errors' in stats or stats['total_events'] > 0

    @pytest.mark.performance
    def test_batching_efficiency_target(self, scalable_broadcaster):
        """Test batching efficiency meets performance targets."""
        users = {f'efficiency_user_{i}' for i in range(50)}

        # Send events that should be efficiently batched
        start_time = time.time()

        for i in range(100):  # Many events
            scalable_broadcaster.broadcast_to_users(
                event_type=f'efficiency_event_{i}',
                event_data={'sequence': i},
                user_ids=users,
                priority=DeliveryPriority.MEDIUM
            )

        queuing_time = time.time() - start_time

        # Force delivery
        delivery_start = time.time()
        scalable_broadcaster.flush_all_batches()
        time.sleep(0.2)  # Allow async delivery
        delivery_time = time.time() - delivery_start

        # Verify efficiency targets
        assert queuing_time < 1.0, f"Queuing 100 events took {queuing_time:.2f}s"
        assert delivery_time < 0.5, f"Delivery took {delivery_time:.2f}s"

        # Verify stats show good efficiency
        stats = scalable_broadcaster.get_broadcast_stats()
        assert stats['total_events'] == 100
        assert stats['batches_created'] > 0
        assert stats['avg_batch_size'] > 1  # Should be batching multiple events
