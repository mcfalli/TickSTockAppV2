"""
Test ScalableBroadcaster Rate Limiting Performance
Sprint 25 Day 3 Tests: Comprehensive rate limiting validation with 100 events/sec enforcement.

Tests rate limiting functionality including:
- 100 events/sec per user enforcement
- Sliding window accuracy (1-second window)
- Rate limit recovery after window expires
- Fair rate limiting across multiple users
- High-load rate limiting with 500+ users
- Rate limiting statistics and monitoring
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock

import pytest

from src.infrastructure.websocket.scalable_broadcaster import (
    DeliveryPriority,
    RateLimiter,
    ScalableBroadcaster,
)


class TestRateLimiterPerformance:
    """Test RateLimiter performance and accuracy."""

    def test_rate_limiter_100_events_per_second(self):
        """Test rate limiter enforces exactly 100 events/sec limit."""
        rate_limiter = RateLimiter(max_events_per_second=100)

        # Should allow exactly 100 events
        allowed_count = 0
        rejected_count = 0

        for i in range(150):  # Try 150 events
            if rate_limiter.allow_event():
                allowed_count += 1
            else:
                rejected_count += 1

        assert allowed_count == 100
        assert rejected_count == 50
        assert rate_limiter.get_current_rate() == 100

    def test_rate_limiter_sliding_window_accuracy(self):
        """Test sliding window accuracy with precise timing."""
        rate_limiter = RateLimiter(max_events_per_second=10, window_size_seconds=1)

        start_time = time.time()

        # Fill up the rate limit
        for i in range(10):
            assert rate_limiter.allow_event() == True

        # Next event should be rejected
        assert rate_limiter.allow_event() == False

        # Wait for partial window to expire (0.6 seconds)
        time.sleep(0.6)
        assert rate_limiter.allow_event() == False  # Still blocked

        # Wait for full window to expire
        time.sleep(0.5)  # Total 1.1 seconds

        # Should allow new events after window expires
        assert rate_limiter.allow_event() == True
        assert rate_limiter.get_current_rate() == 1

        elapsed = time.time() - start_time
        assert elapsed >= 1.0  # Verify we actually waited the full window

    def test_rate_limiter_window_sliding_behavior(self):
        """Test gradual window sliding behavior."""
        rate_limiter = RateLimiter(max_events_per_second=5, window_size_seconds=1)

        # Send events at 0.2 second intervals
        timestamps = []

        for i in range(8):
            timestamp = time.time()
            allowed = rate_limiter.allow_event()
            timestamps.append((timestamp, allowed))
            time.sleep(0.2)

        # First 5 should be allowed, next 3 rejected
        allowed_events = [allowed for _, allowed in timestamps[:5]]
        rejected_events = [allowed for _, allowed in timestamps[5:]]

        assert all(allowed_events)  # All True
        assert not any(rejected_events)  # All False

        # Wait for first events to expire and try again
        time.sleep(0.5)
        assert rate_limiter.allow_event() == True  # Should be allowed now

    def test_rate_limiter_burst_then_sustained(self):
        """Test burst followed by sustained rate."""
        rate_limiter = RateLimiter(max_events_per_second=20)

        # Phase 1: Burst - should allow exactly 20 events immediately
        burst_allowed = 0
        for _ in range(30):
            if rate_limiter.allow_event():
                burst_allowed += 1

        assert burst_allowed == 20

        # Phase 2: Wait for window to reset
        time.sleep(1.1)

        # Phase 3: Sustained rate - send 1 event every 100ms (10 events/sec)
        sustained_allowed = 0
        for i in range(10):
            if rate_limiter.allow_event():
                sustained_allowed += 1
            time.sleep(0.1)

        assert sustained_allowed == 10  # All should be allowed at sustained rate

    def test_rate_limiter_thread_safety_stress(self):
        """Stress test rate limiter thread safety with high concurrency."""
        rate_limiter = RateLimiter(max_events_per_second=100)
        results = []

        def worker_thread(thread_id: int, attempts: int):
            """Worker thread that attempts events."""
            thread_results = []
            for _ in range(attempts):
                thread_results.append(rate_limiter.allow_event())
            return thread_results

        # Run 20 threads, each attempting 50 events = 1000 total attempts
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker_thread, i, 50) for i in range(20)]

            for future in as_completed(futures):
                results.extend(future.result())

        # Should have exactly 100 allowed events regardless of threading
        allowed_count = sum(results)
        assert allowed_count == 100
        assert len(results) == 1000  # All attempts recorded

        # Verify final rate
        assert rate_limiter.get_current_rate() == 100

    def test_rate_limiter_precision_under_load(self):
        """Test rate limiter precision under high load."""
        rate_limiter = RateLimiter(max_events_per_second=50)

        # Rapid-fire event attempts
        start_time = time.time()
        allowed_events = []
        rejected_events = []

        for i in range(200):
            if rate_limiter.allow_event():
                allowed_events.append(time.time())
            else:
                rejected_events.append(time.time())

        # Should have exactly 50 allowed, 150 rejected
        assert len(allowed_events) == 50
        assert len(rejected_events) == 150

        # All allowed events should be within a tight timeframe
        if allowed_events:
            event_duration = allowed_events[-1] - allowed_events[0]
            assert event_duration < 0.1  # Should complete very quickly


class TestScalableBroadcasterRateLimiting:
    """Test ScalableBroadcaster rate limiting integration."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio

    @pytest.fixture
    def broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster with rate limiting."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=50,  # Short window for testing
            max_events_per_user=100,  # 100 events/sec per user
            max_batch_size=25
        )

    def test_per_user_rate_limiting_enforcement(self, broadcaster):
        """Test per-user rate limiting with 100 events/sec limit."""
        user_id = 'test_user_123'
        user_ids = {user_id}

        # Send 120 events rapidly - should only allow 100
        delivered_count = 0
        for i in range(120):
            result = broadcaster.broadcast_to_users(
                event_type=f'rapid_event_{i}',
                event_data={'sequence': i, 'timestamp': time.time()},
                user_ids=user_ids,
                priority=DeliveryPriority.MEDIUM
            )
            delivered_count += result

        # Should deliver to exactly 100 events (rate limit)
        assert delivered_count == 100

        # Check rate limiting statistics
        assert broadcaster.stats.events_rate_limited == 20  # 120 - 100
        assert broadcaster.stats.rate_limit_violations > 0

        # Verify user's current rate
        rate_status = broadcaster.get_user_rate_status(user_id)
        assert rate_status['current_rate'] == 100
        assert rate_status['rate_limited'] == True
        assert rate_status['utilization_percent'] == 100.0

    def test_multiple_users_independent_rate_limiting(self, broadcaster):
        """Test independent rate limiting across multiple users."""
        users = ['user_1', 'user_2', 'user_3', 'user_4', 'user_5']
        results_per_user = {}

        # Each user sends events independently
        for user_id in users:
            delivered_count = 0
            for i in range(80):  # Under rate limit per user
                result = broadcaster.broadcast_to_users(
                    event_type=f'user_event_{i}',
                    event_data={'user': user_id, 'sequence': i},
                    user_ids={user_id},
                    priority=DeliveryPriority.MEDIUM
                )
                delivered_count += result
            results_per_user[user_id] = delivered_count

        # Each user should receive all their events (under rate limit)
        for user_id in users:
            assert results_per_user[user_id] == 80

            # Check individual rate status
            rate_status = broadcaster.get_user_rate_status(user_id)
            assert rate_status['current_rate'] == 80
            assert rate_status['rate_limited'] == False
            assert rate_status['utilization_percent'] == 80.0

        # Total events should be 5 * 80 = 400
        assert broadcaster.stats.total_events == 400
        assert broadcaster.stats.events_rate_limited == 0  # No rate limiting

    def test_rate_limit_recovery_after_window(self, broadcaster):
        """Test users can resume sending after rate limit window expires."""
        user_id = 'recovery_user'
        user_ids = {user_id}

        # Phase 1: Fill rate limit
        initial_delivered = 0
        for i in range(100):
            result = broadcaster.broadcast_to_users(
                event_type=f'initial_event_{i}',
                event_data={'phase': 'initial', 'sequence': i},
                user_ids=user_ids,
                priority=DeliveryPriority.MEDIUM
            )
            initial_delivered += result

        assert initial_delivered == 100

        # Phase 2: Try to send more - should be rate limited
        blocked_result = broadcaster.broadcast_to_users(
            event_type='blocked_event',
            event_data={'phase': 'blocked'},
            user_ids=user_ids,
            priority=DeliveryPriority.MEDIUM
        )
        assert blocked_result == 0  # Should be blocked

        # Phase 3: Wait for rate limit window to expire
        time.sleep(1.2)  # Slightly longer than 1 second window

        # Phase 4: Should be able to send again
        recovery_delivered = 0
        for i in range(50):  # Send more events
            result = broadcaster.broadcast_to_users(
                event_type=f'recovery_event_{i}',
                event_data={'phase': 'recovery', 'sequence': i},
                user_ids=user_ids,
                priority=DeliveryPriority.MEDIUM
            )
            recovery_delivered += result

        assert recovery_delivered == 50  # Should all be delivered

        # Verify rate status after recovery
        rate_status = broadcaster.get_user_rate_status(user_id)
        assert rate_status['current_rate'] == 50
        assert rate_status['rate_limited'] == False

    def test_fair_rate_limiting_high_concurrency(self, broadcaster):
        """Test fair rate limiting with many users sending simultaneously."""
        num_users = 20
        events_per_user = 80  # Under individual rate limit
        users = [f'concurrent_user_{i}' for i in range(num_users)]

        results = {}

        def send_user_events(user_id: str) -> int:
            """Send events for a single user."""
            delivered_count = 0
            for i in range(events_per_user):
                result = broadcaster.broadcast_to_users(
                    event_type=f'concurrent_event_{i}',
                    event_data={'user': user_id, 'sequence': i, 'timestamp': time.time()},
                    user_ids={user_id},
                    priority=DeliveryPriority.MEDIUM
                )
                delivered_count += result
            return delivered_count

        # Send events concurrently from all users
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            future_to_user = {executor.submit(send_user_events, user): user for user in users}

            for future in as_completed(future_to_user):
                user = future_to_user[future]
                results[user] = future.result()

        # Each user should get their fair share (all events delivered)
        for user_id in users:
            assert results[user_id] == events_per_user

            # Check rate status
            rate_status = broadcaster.get_user_rate_status(user_id)
            assert rate_status['current_rate'] == events_per_user
            assert rate_status['rate_limited'] == False

        # Total events should be correct
        total_expected = num_users * events_per_user
        assert broadcaster.stats.total_events == total_expected
        assert broadcaster.stats.events_rate_limited == 0  # No rate limiting should occur

    def test_rate_limiting_with_priority_events(self, broadcaster):
        """Test rate limiting behavior with different priority events."""
        user_id = 'priority_user'
        user_ids = {user_id}

        # Fill rate limit with low priority events
        low_priority_delivered = 0
        for i in range(70):
            result = broadcaster.broadcast_to_users(
                event_type=f'low_priority_{i}',
                event_data={'priority': 'low', 'sequence': i},
                user_ids=user_ids,
                priority=DeliveryPriority.LOW
            )
            low_priority_delivered += result

        assert low_priority_delivered == 70

        # Try to send high priority events - should still be rate limited
        high_priority_delivered = 0
        for i in range(40):  # This would exceed rate limit
            result = broadcaster.broadcast_to_users(
                event_type=f'high_priority_{i}',
                event_data={'priority': 'high', 'sequence': i},
                user_ids=user_ids,
                priority=DeliveryPriority.HIGH
            )
            high_priority_delivered += result

        # Should only deliver 30 more events (100 - 70 = 30)
        assert high_priority_delivered == 30

        # Verify total delivered is at rate limit
        rate_status = broadcaster.get_user_rate_status(user_id)
        assert rate_status['current_rate'] == 100
        assert rate_status['rate_limited'] == True

    def test_rate_limiting_statistics_accuracy(self, broadcaster):
        """Test accuracy of rate limiting statistics."""
        users = ['stats_user_1', 'stats_user_2', 'stats_user_3']

        initial_stats = broadcaster.get_broadcast_stats()
        initial_rate_limited = initial_stats['events_rate_limited']
        initial_violations = initial_stats['rate_limit_violations']

        # Send events that will trigger rate limiting
        for user_id in users:
            for i in range(120):  # Exceed rate limit by 20 per user
                broadcaster.broadcast_to_users(
                    event_type=f'stats_event_{i}',
                    event_data={'user': user_id, 'sequence': i},
                    user_ids={user_id},
                    priority=DeliveryPriority.MEDIUM
                )

        updated_stats = broadcaster.get_broadcast_stats()

        # Should have 60 rate-limited events total (20 per user * 3 users)
        expected_rate_limited = initial_rate_limited + 60
        assert updated_stats['events_rate_limited'] == expected_rate_limited

        # Should have 3 rate limit violations (one per user)
        expected_violations = initial_violations + 3
        assert updated_stats['rate_limit_violations'] >= expected_violations

        # Check users with rate limiters count
        assert updated_stats['users_with_rate_limiters'] >= 3

    def test_rate_limiting_disabled_scenario(self, broadcaster):
        """Test behavior when rate limiting is disabled."""
        # Disable rate limiting
        broadcaster.enable_rate_limiting = False

        user_id = 'unlimited_user'
        user_ids = {user_id}

        # Send many events - should all be delivered
        delivered_count = 0
        for i in range(200):  # Well over normal rate limit
            result = broadcaster.broadcast_to_users(
                event_type=f'unlimited_event_{i}',
                event_data={'sequence': i},
                user_ids=user_ids,
                priority=DeliveryPriority.MEDIUM
            )
            delivered_count += result

        # All events should be delivered (no rate limiting)
        assert delivered_count == 200
        assert broadcaster.stats.events_rate_limited == 0

        # User should not have a rate limiter created
        rate_status = broadcaster.get_user_rate_status(user_id)
        assert rate_status['current_rate'] == 0  # No rate limiter exists

    def test_rate_limiting_performance_benchmarks(self, broadcaster):
        """Benchmark rate limiting performance impact."""
        user_id = 'benchmark_user'
        user_ids = {user_id}

        # Benchmark with rate limiting enabled
        start_time = time.time()
        for i in range(100):
            broadcaster.broadcast_to_users(
                event_type=f'benchmark_event_{i}',
                event_data={'sequence': i},
                user_ids=user_ids,
                priority=DeliveryPriority.MEDIUM
            )
        rate_limited_duration = time.time() - start_time

        # Disable rate limiting for comparison
        broadcaster.enable_rate_limiting = False

        # Clear user rate limiter
        broadcaster.user_rate_limiters.clear()

        # Benchmark without rate limiting
        start_time = time.time()
        for i in range(100):
            broadcaster.broadcast_to_users(
                event_type=f'unlimited_benchmark_{i}',
                event_data={'sequence': i},
                user_ids={f'unlimited_user_{i}'},  # Different users to avoid batching effects
                priority=DeliveryPriority.MEDIUM
            )
        unlimited_duration = time.time() - start_time

        # Rate limiting should add minimal overhead
        overhead_ratio = rate_limited_duration / unlimited_duration
        assert overhead_ratio < 2.0  # Less than 2x overhead

        # Both should complete reasonably quickly
        assert rate_limited_duration < 1.0  # Less than 1 second
        assert unlimited_duration < 1.0


if __name__ == '__main__':
    # Example of running specific rate limiting tests
    pytest.main([__file__ + "::TestScalableBroadcasterRateLimiting::test_per_user_rate_limiting_enforcement", "-v"])
