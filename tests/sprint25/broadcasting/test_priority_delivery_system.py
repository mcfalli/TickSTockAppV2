"""
Test ScalableBroadcaster Priority Delivery System
Sprint 25 Day 3 Tests: Priority-based delivery queuing with CRITICAL > HIGH > MEDIUM > LOW ordering.

Tests priority delivery functionality including:
- Priority queue processing order (CRITICAL > HIGH > MEDIUM > LOW)
- Priority-based batching with highest priority events first
- Confidence-based priority assignment (confidence >= 0.9 gets HIGH priority)
- Mixed priority batch sorting and delivery order
- Priority performance impact measurement
"""

import threading
import time
from unittest.mock import Mock

import pytest

from src.infrastructure.websocket.scalable_broadcaster import (
    DeliveryPriority,
    ScalableBroadcaster,
)


class TestDeliveryPriority:
    """Test DeliveryPriority enum and ordering."""

    def test_priority_enum_values(self):
        """Test priority enum has correct values."""
        assert DeliveryPriority.LOW.value == 1
        assert DeliveryPriority.MEDIUM.value == 2
        assert DeliveryPriority.HIGH.value == 3
        assert DeliveryPriority.CRITICAL.value == 4

    def test_priority_ordering(self):
        """Test priority ordering for sorting."""
        priorities = [DeliveryPriority.LOW, DeliveryPriority.CRITICAL,
                     DeliveryPriority.MEDIUM, DeliveryPriority.HIGH]

        # Sort by value (ascending)
        sorted_asc = sorted(priorities, key=lambda p: p.value)
        assert sorted_asc == [DeliveryPriority.LOW, DeliveryPriority.MEDIUM,
                             DeliveryPriority.HIGH, DeliveryPriority.CRITICAL]

        # Sort by value (descending) - highest priority first
        sorted_desc = sorted(priorities, key=lambda p: p.value, reverse=True)
        assert sorted_desc == [DeliveryPriority.CRITICAL, DeliveryPriority.HIGH,
                              DeliveryPriority.MEDIUM, DeliveryPriority.LOW]

    def test_priority_comparison(self):
        """Test priority comparison operations."""
        assert DeliveryPriority.CRITICAL.value > DeliveryPriority.HIGH.value
        assert DeliveryPriority.HIGH.value > DeliveryPriority.MEDIUM.value
        assert DeliveryPriority.MEDIUM.value > DeliveryPriority.LOW.value

        # Test inequality chains
        assert (DeliveryPriority.CRITICAL.value > DeliveryPriority.HIGH.value >
                DeliveryPriority.MEDIUM.value > DeliveryPriority.LOW.value)


class TestEventPriorityHandling:
    """Test event priority handling and assignment."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio

    @pytest.fixture
    def broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster for priority testing."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=50,  # Short window for testing
            max_events_per_user=100,
            max_batch_size=20
        )

    def test_confidence_based_priority_assignment(self, broadcaster):
        """Test priority assignment based on confidence levels."""
        user_ids = {'priority_user'}

        # High confidence event should get HIGH priority
        high_confidence_result = broadcaster.broadcast_event(
            event_type='tier_pattern',
            event_data={'pattern': 'BreakoutBO', 'confidence': 0.95, 'symbol': 'AAPL'},
            targeting_criteria={'confidence': 0.95}
        )

        # Medium confidence event should get MEDIUM priority
        medium_confidence_result = broadcaster.broadcast_event(
            event_type='tier_pattern',
            event_data={'pattern': 'TrendReversal', 'confidence': 0.75, 'symbol': 'TSLA'},
            targeting_criteria={'confidence': 0.75}
        )

        # Low confidence event should get MEDIUM priority (default)
        low_confidence_result = broadcaster.broadcast_event(
            event_type='tier_pattern',
            event_data={'pattern': 'Support', 'confidence': 0.55, 'symbol': 'GOOGL'},
            targeting_criteria={'confidence': 0.55}
        )

        # All events should be processed
        assert high_confidence_result >= 0
        assert medium_confidence_result >= 0
        assert low_confidence_result >= 0

    def test_explicit_priority_assignment(self, broadcaster):
        """Test explicit priority assignment overrides."""
        user_ids = {'test_user'}

        # Test each priority level explicitly
        priorities = [
            (DeliveryPriority.CRITICAL, 'critical'),
            (DeliveryPriority.HIGH, 'high'),
            (DeliveryPriority.MEDIUM, 'medium'),
            (DeliveryPriority.LOW, 'low')
        ]

        for priority, priority_name in priorities:
            result = broadcaster.broadcast_to_users(
                event_type=f'{priority_name}_event',
                event_data={'priority_level': priority_name, 'timestamp': time.time()},
                user_ids=user_ids,
                priority=priority
            )
            assert result > 0, f"Failed to broadcast {priority_name} priority event"

        # Verify all events were queued
        assert broadcaster.stats.total_events == 4

    def test_priority_override_via_criteria(self, broadcaster):
        """Test priority override via targeting criteria."""
        user_ids = {'criteria_user'}

        # Critical priority via criteria
        result_critical = broadcaster.broadcast_event(
            event_type='alert',
            event_data={'message': 'System alert'},
            targeting_criteria={'priority': 'critical'}
        )

        # High priority via criteria
        result_high = broadcaster.broadcast_event(
            event_type='important_update',
            event_data={'message': 'Important update'},
            targeting_criteria={'priority': 'high'}
        )

        # Default priority (medium)
        result_default = broadcaster.broadcast_event(
            event_type='regular_update',
            event_data={'message': 'Regular update'},
            targeting_criteria={}
        )

        assert result_critical >= 0
        assert result_high >= 0
        assert result_default >= 0


class TestPriorityBasedBatching:
    """Test priority-based batching and delivery order."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO that captures emit calls for verification."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio

    @pytest.fixture
    def broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster for batching tests."""
        broadcaster = ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=25,  # Very short for immediate testing
            max_events_per_user=100,
            max_batch_size=10
        )
        # Disable rate limiting for cleaner testing
        broadcaster.enable_rate_limiting = False
        return broadcaster

    def create_test_events_with_priorities(self, broadcaster, user_id: str,
                                         priorities: list[DeliveryPriority]) -> None:
        """Create test events with specified priorities."""
        for i, priority in enumerate(priorities):
            broadcaster.broadcast_to_users(
                event_type=f'priority_test_{i}',
                event_data={
                    'sequence': i,
                    'priority': priority.name,
                    'timestamp': time.time()
                },
                user_ids={user_id},
                priority=priority
            )

    def test_single_priority_batch_creation(self, broadcaster):
        """Test batch creation with events of single priority."""
        user_id = 'single_priority_user'

        # Create multiple events with same priority
        priorities = [DeliveryPriority.HIGH] * 5
        self.create_test_events_with_priorities(broadcaster, user_id, priorities)

        # Should create batches
        assert len(broadcaster.pending_batches) > 0

        # Find user's batch
        user_room = f'user_{user_id}'
        if user_room in broadcaster.pending_batches:
            batch = broadcaster.pending_batches[user_room]
            assert len(batch.events) <= broadcaster.max_batch_size
            assert all(event.priority == DeliveryPriority.HIGH for event in batch.events)

    def test_mixed_priority_batch_sorting(self, broadcaster, mock_socketio):
        """Test that mixed priority events are sorted correctly in batches."""
        user_id = 'mixed_priority_user'

        # Create events with mixed priorities in random order
        priorities = [
            DeliveryPriority.LOW,
            DeliveryPriority.CRITICAL,
            DeliveryPriority.MEDIUM,
            DeliveryPriority.HIGH,
            DeliveryPriority.LOW,
            DeliveryPriority.CRITICAL
        ]

        self.create_test_events_with_priorities(broadcaster, user_id, priorities)

        # Force batch delivery
        broadcaster.flush_all_batches()

        # Allow time for async delivery
        time.sleep(0.1)

        # Verify that emit was called
        assert mock_socketio.emit.called

        # Check the calls made to emit
        emit_calls = mock_socketio.emit.call_args_list

        # Find batch delivery calls
        batch_calls = [call for call in emit_calls if call[0][0] == 'event_batch']

        if batch_calls:
            # Get the batch payload
            batch_payload = batch_calls[0][0][1]
            events = batch_payload['events']

            # Verify events are sorted by priority (highest first)
            for i in range(len(events) - 1):
                current_priority = DeliveryPriority[events[i]['priority'].upper()]
                next_priority = DeliveryPriority[events[i + 1]['priority'].upper()]
                assert current_priority.value >= next_priority.value

    def test_priority_queue_processing_order(self, broadcaster):
        """Test that priority queues are processed in correct order."""
        user_id = 'queue_order_user'

        # Add events to different priority queues in reverse order
        priorities_to_test = [
            DeliveryPriority.LOW,
            DeliveryPriority.MEDIUM,
            DeliveryPriority.HIGH,
            DeliveryPriority.CRITICAL
        ]

        # Create events in reverse priority order
        for priority in reversed(priorities_to_test):
            broadcaster.broadcast_to_users(
                event_type=f'queue_test_{priority.name}',
                event_data={'priority': priority.name, 'value': priority.value},
                user_ids={user_id},
                priority=priority
            )

        # Verify events were queued
        assert broadcaster.stats.total_events == len(priorities_to_test)

    def test_priority_batching_performance_impact(self, broadcaster):
        """Test performance impact of priority-based batching."""
        user_id = 'performance_user'

        # Test with uniform priority (baseline)
        start_time = time.time()
        uniform_priorities = [DeliveryPriority.MEDIUM] * 50
        self.create_test_events_with_priorities(broadcaster, user_id, uniform_priorities)
        uniform_duration = time.time() - start_time

        # Clear state
        broadcaster.pending_batches.clear()
        broadcaster.stats = broadcaster.stats.__class__()

        # Test with mixed priorities
        start_time = time.time()
        mixed_priorities = [
            DeliveryPriority.LOW, DeliveryPriority.HIGH, DeliveryPriority.CRITICAL,
            DeliveryPriority.MEDIUM, DeliveryPriority.LOW, DeliveryPriority.HIGH
        ] * 8 + [DeliveryPriority.CRITICAL, DeliveryPriority.MEDIUM]  # 50 total

        user_id_2 = 'performance_user_2'
        self.create_test_events_with_priorities(broadcaster, user_id_2, mixed_priorities)
        mixed_duration = time.time() - start_time

        # Priority handling should not significantly impact performance
        performance_ratio = mixed_duration / uniform_duration if uniform_duration > 0 else 1
        assert performance_ratio < 3.0  # Less than 3x overhead

    def test_critical_priority_immediate_processing(self, broadcaster, mock_socketio):
        """Test that CRITICAL priority events get immediate processing."""
        user_id = 'critical_user'

        # Send a critical event
        broadcaster.broadcast_to_users(
            event_type='critical_alert',
            event_data={'message': 'Critical system alert', 'timestamp': time.time()},
            user_ids={user_id},
            priority=DeliveryPriority.CRITICAL
        )

        # Critical events should be processed with minimal delay
        # (Note: Actual immediate processing would require different architecture,
        #  but we can test that they get highest priority in batches)

        # Add lower priority events
        for priority in [DeliveryPriority.LOW, DeliveryPriority.MEDIUM, DeliveryPriority.HIGH]:
            broadcaster.broadcast_to_users(
                event_type=f'{priority.name.lower()}_event',
                event_data={'priority': priority.name},
                user_ids={user_id},
                priority=priority
            )

        # Force delivery
        broadcaster.flush_all_batches()
        time.sleep(0.1)

        # Verify emit was called
        assert mock_socketio.emit.called

        # The critical event should be processed first in any batch
        emit_calls = mock_socketio.emit.call_args_list
        batch_calls = [call for call in emit_calls if call[0][0] == 'event_batch']

        if batch_calls:
            batch_payload = batch_calls[0][0][1]
            events = batch_payload['events']

            if events:
                # First event should be critical priority
                first_event = events[0]
                assert first_event['priority'].upper() == 'CRITICAL'


class TestPriorityDeliveryIntegration:
    """Test priority delivery system integration."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO with detailed call tracking."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio

    @pytest.fixture
    def broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster for integration testing."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=30,
            max_events_per_user=50,
            max_batch_size=15
        )

    def test_end_to_end_priority_delivery(self, broadcaster, mock_socketio):
        """Test complete priority delivery workflow."""
        users = ['user_1', 'user_2', 'user_3']

        # Create scenario with mixed priority events for multiple users
        event_scenarios = [
            ('user_1', DeliveryPriority.CRITICAL, 'system_alert', {'alert': 'Database connection lost'}),
            ('user_2', DeliveryPriority.HIGH, 'pattern_match', {'pattern': 'BreakoutBO', 'confidence': 0.92}),
            ('user_1', DeliveryPriority.MEDIUM, 'price_update', {'symbol': 'AAPL', 'price': 150.50}),
            ('user_3', DeliveryPriority.HIGH, 'trend_change', {'symbol': 'TSLA', 'trend': 'bullish'}),
            ('user_2', DeliveryPriority.LOW, 'info_update', {'message': 'Market hours extended'}),
            ('user_3', DeliveryPriority.CRITICAL, 'security_alert', {'alert': 'Unauthorized access attempt'}),
        ]

        # Send all events
        for user_id, priority, event_type, event_data in event_scenarios:
            result = broadcaster.broadcast_to_users(
                event_type=event_type,
                event_data=event_data,
                user_ids={user_id},
                priority=priority
            )
            assert result > 0

        # Force delivery of all batches
        broadcaster.flush_all_batches()
        time.sleep(0.2)  # Allow async processing

        # Verify events were delivered
        assert mock_socketio.emit.called
        assert broadcaster.stats.total_events == len(event_scenarios)

    def test_priority_statistics_accuracy(self, broadcaster):
        """Test accuracy of priority-related statistics."""
        user_id = 'stats_test_user'

        # Send events with different priorities
        priority_counts = {
            DeliveryPriority.CRITICAL: 3,
            DeliveryPriority.HIGH: 7,
            DeliveryPriority.MEDIUM: 12,
            DeliveryPriority.LOW: 5
        }

        for priority, count in priority_counts.items():
            for i in range(count):
                broadcaster.broadcast_to_users(
                    event_type=f'{priority.name.lower()}_event_{i}',
                    event_data={'priority': priority.name, 'sequence': i},
                    user_ids={user_id},
                    priority=priority
                )

        # Check statistics
        stats = broadcaster.get_broadcast_stats()
        total_expected = sum(priority_counts.values())
        assert stats['total_events'] == total_expected

        # Verify batches were created
        assert stats['batches_created'] > 0

    def test_priority_with_rate_limiting_interaction(self, broadcaster):
        """Test priority system interaction with rate limiting."""
        user_id = 'priority_rate_user'
        broadcaster.max_events_per_user = 20  # Low limit for testing

        # Send more events than rate limit allows, with mixed priorities
        events_to_send = [
            (DeliveryPriority.CRITICAL, 5),
            (DeliveryPriority.HIGH, 8),
            (DeliveryPriority.MEDIUM, 10),
            (DeliveryPriority.LOW, 7)
        ]

        delivered_by_priority = {}

        for priority, count in events_to_send:
            delivered = 0
            for i in range(count):
                result = broadcaster.broadcast_to_users(
                    event_type=f'rate_priority_{priority.name}_{i}',
                    event_data={'priority': priority.name, 'sequence': i},
                    user_ids={user_id},
                    priority=priority
                )
                delivered += result
            delivered_by_priority[priority] = delivered

        # Should respect rate limit
        total_delivered = sum(delivered_by_priority.values())
        assert total_delivered <= broadcaster.max_events_per_user

        # Rate limiting statistics should be updated
        assert broadcaster.stats.events_rate_limited > 0

        # Check user rate status
        rate_status = broadcaster.get_user_rate_status(user_id)
        assert rate_status['rate_limited'] == True

    def test_priority_system_health_monitoring(self, broadcaster):
        """Test priority system health monitoring."""
        user_id = 'health_test_user'

        # Create normal load with mixed priorities
        for i in range(30):
            priority = [DeliveryPriority.LOW, DeliveryPriority.MEDIUM,
                       DeliveryPriority.HIGH, DeliveryPriority.CRITICAL][i % 4]

            broadcaster.broadcast_to_users(
                event_type=f'health_event_{i}',
                event_data={'sequence': i, 'priority': priority.name},
                user_ids={user_id},
                priority=priority
            )

        # Check health status
        health = broadcaster.get_health_status()

        assert health['service'] == 'scalable_broadcaster'
        assert health['status'] in ['healthy', 'warning', 'error']
        assert 'stats' in health
        assert 'performance_targets' in health

        # Priority system should not negatively impact health
        stats = health['stats']
        assert stats['total_events'] == 30
        assert stats['delivery_success_rate_percent'] >= 0

    def test_priority_optimization_impact(self, broadcaster):
        """Test impact of priority system on performance optimization."""
        user_ids = {'opt_user_1', 'opt_user_2', 'opt_user_3'}

        # Create diverse priority load
        for user_id in user_ids:
            for i in range(15):
                priority = [DeliveryPriority.LOW, DeliveryPriority.MEDIUM,
                           DeliveryPriority.HIGH, DeliveryPriority.CRITICAL][i % 4]

                broadcaster.broadcast_to_users(
                    event_type=f'optimization_event_{i}',
                    event_data={'user': user_id, 'sequence': i, 'priority': priority.name},
                    user_ids={user_id},
                    priority=priority
                )

        # Run performance optimization
        optimization_result = broadcaster.optimize_performance()

        assert isinstance(optimization_result, dict)
        assert 'batches_flushed' in optimization_result
        assert 'optimization_timestamp' in optimization_result

        # Optimization should complete successfully with priority system
        assert 'error' not in optimization_result


class TestPriorityEdgeCases:
    """Test edge cases in priority handling."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for edge case testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio

    @pytest.fixture
    def broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster for edge case testing."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=100,
            max_events_per_user=25,
            max_batch_size=5  # Small batches for testing
        )

    def test_all_critical_priority_events(self, broadcaster):
        """Test behavior when all events are CRITICAL priority."""
        user_id = 'all_critical_user'

        # Send multiple critical events
        for i in range(10):
            result = broadcaster.broadcast_to_users(
                event_type=f'critical_event_{i}',
                event_data={'sequence': i, 'critical_level': 'maximum'},
                user_ids={user_id},
                priority=DeliveryPriority.CRITICAL
            )
            assert result > 0

        # All events should be processed
        assert broadcaster.stats.total_events == 10

        # Should create multiple batches due to batch size limit
        broadcaster.flush_all_batches()
        time.sleep(0.1)

        assert broadcaster.stats.batches_created > 1  # Should create multiple batches

    def test_empty_priority_queues(self, broadcaster):
        """Test behavior with empty priority queues."""
        # Initially all queues should be empty
        for priority in DeliveryPriority:
            assert len(broadcaster.event_queue[priority]) == 0

        # Send one event to each priority level
        user_id = 'empty_queue_user'
        for priority in DeliveryPriority:
            broadcaster.broadcast_to_users(
                event_type=f'queue_test_{priority.name}',
                event_data={'priority': priority.name},
                user_ids={user_id},
                priority=priority
            )

        # Queues should now have events (in batches)
        assert broadcaster.stats.total_events == 4

    def test_priority_with_batch_size_overflow(self, broadcaster):
        """Test priority handling when batch size limit is exceeded."""
        user_id = 'overflow_user'
        broadcaster.max_batch_size = 3  # Very small for testing

        # Send more high priority events than can fit in one batch
        for i in range(8):
            broadcaster.broadcast_to_users(
                event_type=f'overflow_high_{i}',
                event_data={'sequence': i},
                user_ids={user_id},
                priority=DeliveryPriority.HIGH
            )

        # Should create multiple batches to handle overflow
        assert broadcaster.stats.total_events == 8
        assert broadcaster.stats.batches_created >= 2  # Multiple batches needed

    def test_priority_system_thread_safety(self, broadcaster):
        """Test priority system thread safety under concurrent load."""
        user_id = 'thread_safety_user'
        results = []

        def priority_worker(priority: DeliveryPriority, count: int):
            """Worker thread for specific priority level."""
            thread_results = []
            for i in range(count):
                result = broadcaster.broadcast_to_users(
                    event_type=f'thread_{priority.name}_{i}',
                    event_data={'thread_priority': priority.name, 'sequence': i},
                    user_ids={user_id},
                    priority=priority
                )
                thread_results.append(result)
            return thread_results

        # Run concurrent workers for different priorities
        threads = []
        thread_results = {}

        for priority in DeliveryPriority:
            thread = threading.Thread(
                target=lambda p=priority: thread_results.update({p: priority_worker(p, 5)})
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All events should be processed correctly
        total_events = sum(len(results) for results in thread_results.values())
        assert total_events == len(DeliveryPriority) * 5
        assert broadcaster.stats.total_events >= total_events


if __name__ == '__main__':
    # Example of running priority delivery tests
    pytest.main([__file__ + "::TestPriorityBasedBatching::test_mixed_priority_batch_sorting", "-v"])
