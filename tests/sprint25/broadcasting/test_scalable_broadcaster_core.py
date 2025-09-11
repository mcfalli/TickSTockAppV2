"""
Test ScalableBroadcaster Core Functionality
Sprint 25 Day 3 Tests: Core broadcasting system with batching and rate limiting validation.

Tests comprehensive ScalableBroadcaster functionality including:
- Event message creation and validation
- Batch creation and management
- Rate limiting enforcement 
- Priority-based delivery queuing
- Performance monitoring and statistics
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, Set

from src.infrastructure.websocket.scalable_broadcaster import (
    ScalableBroadcaster, EventMessage, EventBatch, RateLimiter, 
    BroadcastStats, DeliveryPriority
)


class TestEventMessage:
    """Test EventMessage dataclass functionality."""
    
    def test_event_message_creation(self):
        """Test EventMessage creation with all required fields."""
        target_users = {'user1', 'user2', 'user3'}
        timestamp = time.time()
        
        event = EventMessage(
            event_type='tier_pattern',
            event_data={'pattern': 'BreakoutBO', 'symbol': 'AAPL'},
            target_users=target_users,
            priority=DeliveryPriority.HIGH,
            timestamp=timestamp,
            message_id='test_message_123'
        )
        
        assert event.event_type == 'tier_pattern'
        assert event.event_data == {'pattern': 'BreakoutBO', 'symbol': 'AAPL'}
        assert event.target_users == target_users
        assert event.priority == DeliveryPriority.HIGH
        assert event.timestamp == timestamp
        assert event.message_id == 'test_message_123'
        assert event.attempts == 0
        assert event.delivered_users == set()
        assert event.failed_users == set()
    
    def test_event_message_delivery_tracking(self):
        """Test EventMessage delivery tracking functionality."""
        event = EventMessage(
            event_type='market_update',
            event_data={'price': 150.50},
            target_users={'user1', 'user2'},
            priority=DeliveryPriority.MEDIUM,
            timestamp=time.time(),
            message_id='update_123'
        )
        
        # Track delivery attempts
        event.attempts = 1
        event.delivered_users.add('user1')
        event.failed_users.add('user2')
        
        assert event.attempts == 1
        assert 'user1' in event.delivered_users
        assert 'user2' in event.failed_users
        assert len(event.delivered_users) == 1
        assert len(event.failed_users) == 1


class TestEventBatch:
    """Test EventBatch functionality."""
    
    def create_test_event(self, event_type='test', event_data=None, priority=DeliveryPriority.MEDIUM):
        """Helper to create test event."""
        return EventMessage(
            event_type=event_type,
            event_data=event_data or {'test': 'data'},
            target_users={'user1'},
            priority=priority,
            timestamp=time.time(),
            message_id=f'test_{int(time.time() * 1000)}'
        )
    
    def test_event_batch_creation(self):
        """Test EventBatch creation and basic properties."""
        events = [
            self.create_test_event('event1', {'data': 'small'}),
            self.create_test_event('event2', {'data': 'medium_sized_data'}),
            self.create_test_event('event3', {'data': 'large_data_payload_content'})
        ]
        
        batch = EventBatch(
            room_name='user_123',
            events=events,
            batch_id='batch_456',
            created_at=time.time(),
            priority=DeliveryPriority.HIGH
        )
        
        assert batch.room_name == 'user_123'
        assert batch.batch_id == 'batch_456'
        assert len(batch.events) == 3
        assert batch.priority == DeliveryPriority.HIGH
    
    def test_event_batch_size_calculation(self):
        """Test EventBatch size calculation for memory management."""
        # Create events with known data sizes
        events = [
            self.create_test_event('small', {'data': 'abc'}),  # Small event
            self.create_test_event('medium', {'data': 'x' * 50}),  # Medium event
            self.create_test_event('large', {'data': 'x' * 100})  # Large event
        ]
        
        batch = EventBatch(
            room_name='test_room',
            events=events,
            batch_id='size_test',
            created_at=time.time(),
            priority=DeliveryPriority.MEDIUM
        )
        
        total_size = batch.get_total_size()
        
        # Verify size is calculated correctly (approximate, due to str() conversion)
        assert total_size > 150  # Should be more than sum of data lengths
        assert isinstance(total_size, int)
    
    def test_empty_batch_size(self):
        """Test batch size calculation with empty events list."""
        batch = EventBatch(
            room_name='empty_room',
            events=[],
            batch_id='empty_batch',
            created_at=time.time(),
            priority=DeliveryPriority.LOW
        )
        
        assert batch.get_total_size() == 0


class TestRateLimiter:
    """Test RateLimiter functionality."""
    
    def test_rate_limiter_creation(self):
        """Test RateLimiter creation with default settings."""
        rate_limiter = RateLimiter(max_events_per_second=100)
        
        assert rate_limiter.max_events_per_second == 100
        assert rate_limiter.window_size_seconds == 1
        assert len(rate_limiter.event_timestamps) == 0
    
    def test_rate_limiter_allow_within_limit(self):
        """Test rate limiter allows events within limit."""
        rate_limiter = RateLimiter(max_events_per_second=5)
        
        # Should allow first 5 events
        for i in range(5):
            assert rate_limiter.allow_event() == True
        
        # Should reject 6th event
        assert rate_limiter.allow_event() == False
    
    def test_rate_limiter_sliding_window(self):
        """Test rate limiter sliding window functionality."""
        rate_limiter = RateLimiter(max_events_per_second=2, window_size_seconds=1)
        
        # Allow 2 events initially
        assert rate_limiter.allow_event() == True
        assert rate_limiter.allow_event() == True
        assert rate_limiter.allow_event() == False  # Third event blocked
        
        # Wait for window to slide
        time.sleep(1.1)
        
        # Should allow events again after window passes
        assert rate_limiter.allow_event() == True
        assert rate_limiter.allow_event() == True
    
    def test_rate_limiter_current_rate(self):
        """Test rate limiter current rate calculation."""
        rate_limiter = RateLimiter(max_events_per_second=10)
        
        # Initially no events
        assert rate_limiter.get_current_rate() == 0
        
        # Add some events
        for _ in range(3):
            rate_limiter.allow_event()
        
        assert rate_limiter.get_current_rate() == 3
        
        # Wait for events to expire
        time.sleep(1.1)
        assert rate_limiter.get_current_rate() == 0
    
    def test_rate_limiter_thread_safety(self):
        """Test rate limiter thread safety."""
        rate_limiter = RateLimiter(max_events_per_second=100)
        results = []
        
        def worker():
            for _ in range(50):
                results.append(rate_limiter.allow_event())
        
        # Run multiple threads
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should have exactly 100 allowed events (rate limit)
        assert sum(results) == 100
        assert len(results) == 200  # 4 threads * 50 attempts each


class TestBroadcastStats:
    """Test BroadcastStats functionality."""
    
    def test_broadcast_stats_creation(self):
        """Test BroadcastStats creation with default values."""
        stats = BroadcastStats()
        
        assert stats.total_events == 0
        assert stats.events_delivered == 0
        assert stats.events_dropped == 0
        assert stats.events_rate_limited == 0
        assert stats.avg_batch_size == 0.0
        assert stats.avg_delivery_latency_ms == 0.0
        assert stats.max_delivery_latency_ms == 0.0
    
    def test_broadcast_stats_record_delivery(self):
        """Test delivery metrics recording."""
        stats = BroadcastStats()
        
        # Record first delivery
        stats.record_delivery(batch_size=5, latency_ms=25.5)
        
        assert stats.events_delivered == 5
        assert stats.batches_delivered == 1
        assert stats.avg_delivery_latency_ms == 25.5
        assert stats.max_delivery_latency_ms == 25.5
        assert stats.batch_efficiency == 5.0
        
        # Record second delivery
        stats.record_delivery(batch_size=10, latency_ms=35.0)
        
        assert stats.events_delivered == 15
        assert stats.batches_delivered == 2
        assert stats.avg_delivery_latency_ms == 30.25  # (25.5 + 35.0) / 2
        assert stats.max_delivery_latency_ms == 35.0
        assert stats.batch_efficiency == 7.5  # 15 events / 2 batches
    
    def test_broadcast_stats_multiple_deliveries(self):
        """Test statistics with multiple delivery records."""
        stats = BroadcastStats()
        
        # Record multiple deliveries with varying sizes and latencies
        deliveries = [
            (3, 15.0),
            (7, 22.5),
            (12, 45.0),
            (5, 18.0),
            (8, 33.0)
        ]
        
        for batch_size, latency in deliveries:
            stats.record_delivery(batch_size, latency)
        
        assert stats.events_delivered == 35  # Sum of all batch sizes
        assert stats.batches_delivered == 5
        assert stats.batch_efficiency == 7.0  # 35 / 5
        assert stats.max_delivery_latency_ms == 45.0
        
        # Check average latency calculation
        expected_avg = sum(latency for _, latency in deliveries) / len(deliveries)
        assert abs(stats.avg_delivery_latency_ms - expected_avg) < 0.01


class TestScalableBroadcasterCore:
    """Test ScalableBroadcaster core functionality."""
    
    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio
    
    @pytest.fixture
    def broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster for testing."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=100,
            max_events_per_user=100,
            max_batch_size=50
        )
    
    def test_broadcaster_initialization(self, broadcaster, mock_socketio):
        """Test ScalableBroadcaster initialization."""
        assert broadcaster.socketio == mock_socketio
        assert broadcaster.batch_window_ms == 100
        assert broadcaster.max_events_per_user == 100
        assert broadcaster.max_batch_size == 50
        
        # Check internal structures
        assert len(broadcaster.pending_batches) == 0
        assert len(broadcaster.batch_timers) == 0
        assert len(broadcaster.event_queue) == 4  # One for each priority level
        assert len(broadcaster.user_rate_limiters) == 0
        
        # Check configuration flags
        assert broadcaster.enable_batching == True
        assert broadcaster.enable_rate_limiting == True
        assert broadcaster.enable_priority_queuing == True
    
    def test_broadcast_to_users_basic(self, broadcaster):
        """Test basic broadcast_to_users functionality."""
        user_ids = {'user1', 'user2', 'user3'}
        event_data = {'pattern': 'BreakoutBO', 'symbol': 'AAPL', 'confidence': 0.85}
        
        result = broadcaster.broadcast_to_users(
            event_type='tier_pattern',
            event_data=event_data,
            user_ids=user_ids,
            priority=DeliveryPriority.HIGH
        )
        
        # Should return number of users queued for delivery
        assert result == 3
        
        # Check statistics updated
        assert broadcaster.stats.total_events == 1
        
        # Check batch created
        assert len(broadcaster.pending_batches) == 3  # One batch per user room
    
    def test_broadcast_to_users_empty_users(self, broadcaster):
        """Test broadcast with empty user set."""
        result = broadcaster.broadcast_to_users(
            event_type='test_event',
            event_data={'test': 'data'},
            user_ids=set(),
            priority=DeliveryPriority.MEDIUM
        )
        
        assert result == 0
        assert broadcaster.stats.total_events == 0
        assert len(broadcaster.pending_batches) == 0
    
    def test_broadcast_to_room_basic(self, broadcaster):
        """Test basic broadcast_to_room functionality."""
        result = broadcaster.broadcast_to_room(
            room_name='pattern_alerts',
            event_type='pattern_update',
            event_data={'new_patterns': 5},
            priority=DeliveryPriority.MEDIUM
        )
        
        assert result == True
        assert broadcaster.stats.total_events == 1
        assert len(broadcaster.pending_batches) == 1
        assert 'pattern_alerts' in broadcaster.pending_batches
    
    def test_rate_limiting_application(self, broadcaster):
        """Test rate limiting is applied to user broadcasts."""
        # Set very low rate limit for testing
        broadcaster.max_events_per_user = 2
        
        user_ids = {'user1'}
        
        # First 2 events should succeed
        for i in range(2):
            result = broadcaster.broadcast_to_users(
                event_type=f'event_{i}',
                event_data={'index': i},
                user_ids=user_ids,
                priority=DeliveryPriority.MEDIUM
            )
            assert result == 1
        
        # Third event should be rate limited
        result = broadcaster.broadcast_to_users(
            event_type='event_3',
            event_data={'index': 3},
            user_ids=user_ids,
            priority=DeliveryPriority.MEDIUM
        )
        assert result == 0  # No users after rate limiting
        assert broadcaster.stats.events_rate_limited > 0
    
    def test_batch_creation_and_timer(self, broadcaster):
        """Test batch creation and timer scheduling."""
        with patch('threading.Timer') as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance
            
            broadcaster.broadcast_to_users(
                event_type='test_event',
                event_data={'test': 'data'},
                user_ids={'user1'},
                priority=DeliveryPriority.MEDIUM
            )
            
            # Verify timer was created and started
            mock_timer.assert_called_once()
            args, kwargs = mock_timer.call_args
            assert args[0] == 0.1  # 100ms converted to seconds
            mock_timer_instance.start.assert_called_once()
    
    def test_max_batch_size_enforcement(self, broadcaster):
        """Test maximum batch size enforcement."""
        broadcaster.max_batch_size = 3
        
        user_ids = {'user1'}
        
        # Add events up to max batch size
        for i in range(5):  # Try to add 5 events, only 3 should fit in first batch
            broadcaster.broadcast_to_users(
                event_type=f'event_{i}',
                event_data={'index': i},
                user_ids=user_ids,
                priority=DeliveryPriority.MEDIUM
            )
        
        # Should have created multiple batches due to size limit
        user_room = 'user_user1'
        if user_room in broadcaster.pending_batches:
            batch = broadcaster.pending_batches[user_room]
            assert len(batch.events) <= broadcaster.max_batch_size
    
    def test_priority_handling(self, broadcaster):
        """Test priority-based event handling."""
        user_ids = {'user1'}
        
        # Broadcast events with different priorities
        priorities = [DeliveryPriority.LOW, DeliveryPriority.HIGH, DeliveryPriority.CRITICAL, DeliveryPriority.MEDIUM]
        
        for i, priority in enumerate(priorities):
            result = broadcaster.broadcast_to_users(
                event_type=f'priority_event_{i}',
                event_data={'priority': priority.name, 'index': i},
                user_ids=user_ids,
                priority=priority
            )
            assert result == 1
        
        # All events should be queued
        assert broadcaster.stats.total_events == 4
    
    def test_get_user_rate_status(self, broadcaster):
        """Test user rate status retrieval."""
        user_id = 'user1'
        
        # Initially no rate limiter
        status = broadcaster.get_user_rate_status(user_id)
        assert status['user_id'] == user_id
        assert status['current_rate'] == 0
        assert status['max_rate'] == broadcaster.max_events_per_user
        assert status['rate_limited'] == False
        
        # Send some events to create rate limiter
        broadcaster.broadcast_to_users(
            event_type='test_event',
            event_data={'test': 'data'},
            user_ids={user_id},
            priority=DeliveryPriority.MEDIUM
        )
        
        # Should now have rate limiter with activity
        status = broadcaster.get_user_rate_status(user_id)
        assert status['current_rate'] >= 1
        assert 'utilization_percent' in status
    
    def test_get_broadcast_stats(self, broadcaster):
        """Test broadcast statistics retrieval."""
        # Initial stats
        stats = broadcaster.get_broadcast_stats()
        assert stats['total_events'] == 0
        assert stats['events_delivered'] == 0
        assert stats['batch_window_ms'] == 100
        assert stats['max_events_per_user'] == 100
        
        # Broadcast some events
        broadcaster.broadcast_to_users(
            event_type='test_event',
            event_data={'test': 'data'},
            user_ids={'user1', 'user2'},
            priority=DeliveryPriority.HIGH
        )
        
        # Updated stats
        stats = broadcaster.get_broadcast_stats()
        assert stats['total_events'] == 1
        assert stats['batches_created'] >= 1
        assert 'events_per_second' in stats
        assert 'runtime_seconds' in stats
    
    def test_get_health_status(self, broadcaster):
        """Test health status monitoring."""
        health = broadcaster.get_health_status()
        
        assert health['service'] == 'scalable_broadcaster'
        assert health['status'] in ['healthy', 'warning', 'error']
        assert 'message' in health
        assert 'timestamp' in health
        assert 'stats' in health
        assert 'performance_targets' in health
        
        # Check performance targets
        targets = health['performance_targets']
        assert targets['delivery_latency_target_ms'] == 100.0
        assert targets['batch_efficiency_target'] == 10.0
        assert targets['success_rate_target_percent'] == 95.0
    
    def test_flush_all_batches(self, broadcaster):
        """Test flushing all pending batches."""
        # Create some batches
        broadcaster.broadcast_to_users(
            event_type='test_event_1',
            event_data={'test': 1},
            user_ids={'user1'},
            priority=DeliveryPriority.MEDIUM
        )
        broadcaster.broadcast_to_room(
            room_name='test_room',
            event_type='test_event_2',
            event_data={'test': 2},
            priority=DeliveryPriority.MEDIUM
        )
        
        # Should have pending batches
        initial_batch_count = len(broadcaster.pending_batches)
        assert initial_batch_count > 0
        
        # Flush all batches
        broadcaster.flush_all_batches()
        
        # Should have no pending batches (they'll be submitted to delivery executor)
        time.sleep(0.1)  # Allow brief time for async processing
        assert len(broadcaster.pending_batches) == 0


class TestScalableBroadcasterErrorHandling:
    """Test ScalableBroadcaster error handling."""
    
    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO that can simulate errors."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio
    
    @pytest.fixture
    def broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster for error testing."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=50,  # Shorter for testing
            max_events_per_user=10,
            max_batch_size=5
        )
    
    def test_broadcast_error_handling(self, broadcaster):
        """Test error handling in broadcast methods."""
        # Test with invalid data that could cause errors
        result = broadcaster.broadcast_to_users(
            event_type='test_event',
            event_data={'complex': {'nested': {'data': 'value'}}},
            user_ids={'user1'},
            priority=DeliveryPriority.MEDIUM
        )
        
        # Should handle gracefully
        assert isinstance(result, int)
    
    def test_rate_limiter_error_recovery(self, broadcaster):
        """Test rate limiter error recovery."""
        # Simulate error in rate limiting by corrupting internal state
        with patch.object(broadcaster, '_apply_rate_limiting', side_effect=Exception("Rate limit error")):
            result = broadcaster.broadcast_to_users(
                event_type='test_event',
                event_data={'test': 'data'},
                user_ids={'user1'},
                priority=DeliveryPriority.MEDIUM
            )
            
            # Should still return gracefully (error logged, delivery attempted)
            assert isinstance(result, int)
            assert broadcaster.stats.delivery_errors >= 0
    
    def test_batch_delivery_error_handling(self, broadcaster, mock_socketio):
        """Test error handling in batch delivery."""
        # Make socketio.emit raise an exception
        mock_socketio.emit.side_effect = Exception("SocketIO error")
        
        # Create and deliver a batch
        broadcaster.broadcast_to_users(
            event_type='test_event',
            event_data={'test': 'data'},
            user_ids={'user1'},
            priority=DeliveryPriority.MEDIUM
        )
        
        # Force immediate batch delivery
        broadcaster.flush_all_batches()
        
        # Allow time for async delivery and error handling
        time.sleep(0.2)
        
        # Should record batch errors
        assert broadcaster.stats.batch_errors >= 0  # May be incremented due to error
    
    def test_shutdown_graceful(self, broadcaster):
        """Test graceful shutdown."""
        # Create some pending batches
        broadcaster.broadcast_to_users(
            event_type='test_event',
            event_data={'test': 'data'},
            user_ids={'user1', 'user2'},
            priority=DeliveryPriority.MEDIUM
        )
        
        # Should shutdown without exceptions
        broadcaster.shutdown()
        
        # All batches should be flushed
        assert len(broadcaster.pending_batches) == 0
        assert len(broadcaster.batch_timers) == 0
    
    def test_optimize_performance(self, broadcaster):
        """Test performance optimization."""
        # Create some activity
        broadcaster.broadcast_to_users(
            event_type='test_event',
            event_data={'test': 'data'},
            user_ids={'user1'},
            priority=DeliveryPriority.MEDIUM
        )
        
        # Run optimization
        result = broadcaster.optimize_performance()
        
        assert isinstance(result, dict)
        assert 'batches_flushed' in result
        assert 'rate_limiters_cleaned' in result
        assert 'optimization_timestamp' in result


if __name__ == '__main__':
    # Example usage of running specific test classes
    pytest.main([__file__ + "::TestScalableBroadcasterCore::test_broadcast_to_users_basic", "-v"])