"""
Performance Tests for UniversalWebSocketManager Integration with SubscriptionIndexManager
Sprint 25 Day 2 Implementation: End-to-end WebSocket performance validation

Tests validate the enhanced UniversalWebSocketManager achieves performance targets
when integrated with the new SubscriptionIndexManager indexing system.

Performance Targets:
- <100ms end-to-end event delivery (WebSocket broadcast)
- <5ms user filtering with indexing system
- 500+ concurrent users supported
- No performance degradation with indexing integration
- Memory efficiency maintained under load
"""

import gc
import os
import random
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

import psutil
import pytest
import redis

from src.core.services.websocket_broadcaster import WebSocketBroadcaster

# Import system under test
from src.core.services.websocket_subscription_manager import (
    UniversalWebSocketManager,
)


@dataclass
class WebSocketPerformanceResult:
    """WebSocket performance measurement result."""
    operation: str
    duration_ms: float
    user_count: int
    delivery_count: int
    filtering_time_ms: float
    memory_mb: float
    success: bool
    metadata: dict[str, Any] = None


class MockSocketIO:
    """Mock SocketIO for testing without actual WebSocket connections."""

    def __init__(self):
        self.emit_calls = []
        self.room_operations = []
        self.server = self

    def emit(self, event_type: str, data: dict[str, Any], room: str = None):
        """Mock emit method."""
        self.emit_calls.append({
            'event_type': event_type,
            'data': data,
            'room': room,
            'timestamp': time.time()
        })

    def enter_room(self, connection_id: str, room_name: str):
        """Mock enter room method."""
        self.room_operations.append({
            'operation': 'enter',
            'connection_id': connection_id,
            'room': room_name,
            'timestamp': time.time()
        })

    def leave_room(self, connection_id: str, room_name: str):
        """Mock leave room method."""
        self.room_operations.append({
            'operation': 'leave',
            'connection_id': connection_id,
            'room': room_name,
            'timestamp': time.time()
        })

    def get_emit_count_for_event(self, event_type: str) -> int:
        """Get count of emit calls for specific event type."""
        return len([call for call in self.emit_calls if call['event_type'] == event_type])

    def get_rooms_for_user(self, user_id: str) -> list[str]:
        """Get rooms for user based on mock operations."""
        user_rooms = set()
        for op in self.room_operations:
            if f"user_{user_id}" in op.get('connection_id', ''):
                if op['operation'] == 'enter':
                    user_rooms.add(op['room'])
                elif op['operation'] == 'leave':
                    user_rooms.discard(op['room'])
        return list(user_rooms)


class MockWebSocketManager:
    """Mock WebSocketManager for testing."""

    def __init__(self):
        self.connected_users = set()
        self.user_connections = defaultdict(list)

    def is_user_connected(self, user_id: str) -> bool:
        """Check if user is connected."""
        return user_id in self.connected_users

    def get_user_connections(self, user_id: str) -> list[str]:
        """Get connections for user."""
        return self.user_connections.get(user_id, [])

    def get_connected_users(self) -> set[str]:
        """Get all connected users."""
        return self.connected_users.copy()

    def connect_user(self, user_id: str, connection_id: str = None):
        """Mock user connection."""
        self.connected_users.add(user_id)
        if connection_id:
            self.user_connections[user_id].append(connection_id)

    def disconnect_user(self, user_id: str, connection_id: str = None):
        """Mock user disconnection."""
        if connection_id and connection_id in self.user_connections[user_id]:
            self.user_connections[user_id].remove(connection_id)
        if not self.user_connections[user_id]:
            self.connected_users.discard(user_id)


class WebSocketPerformanceTestHelper:
    """Helper class for WebSocket performance testing utilities."""

    @staticmethod
    def create_test_universal_manager() -> UniversalWebSocketManager:
        """Create UniversalWebSocketManager with mocked dependencies."""
        mock_socketio = MockSocketIO()
        mock_redis = Mock(spec=redis.Redis)
        mock_existing_ws = MockWebSocketManager()
        mock_broadcaster = Mock(spec=WebSocketBroadcaster)

        return UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis,
            existing_websocket_manager=mock_existing_ws,
            websocket_broadcaster=mock_broadcaster
        )

    @staticmethod
    def generate_realistic_subscription(user_id: str) -> dict[str, Any]:
        """Generate realistic subscription data."""
        patterns = ['BreakoutBO', 'TrendReversal', 'SurgeDetection', 'VolumeSpike', 'GapUp']
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NFLX', 'NVDA', 'CRM', 'ORCL']
        tiers = ['daily', 'intraday', 'combo']

        return {
            'pattern_types': random.sample(patterns, random.randint(1, 3)),
            'symbols': random.sample(symbols, random.randint(2, 6)),
            'tiers': random.sample(tiers, random.randint(1, 2)),
            'confidence_min': random.uniform(0.6, 0.9),
            'priority_min': random.randint(1, 5)
        }

    @staticmethod
    def generate_realistic_event_data() -> dict[str, Any]:
        """Generate realistic event data for broadcasting."""
        patterns = ['BreakoutBO', 'TrendReversal', 'SurgeDetection', 'VolumeSpike', 'GapUp']
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NFLX', 'NVDA', 'CRM', 'ORCL']
        tiers = ['daily', 'intraday', 'combo']

        return {
            'pattern': random.choice(patterns),
            'symbol': random.choice(symbols),
            'tier': random.choice(tiers),
            'confidence': random.uniform(0.7, 0.95),
            'price': random.uniform(100, 500),
            'volume': random.randint(100000, 10000000),
            'timestamp': time.time()
        }

    @staticmethod
    def generate_targeting_criteria(event_data: dict[str, Any]) -> dict[str, Any]:
        """Generate targeting criteria from event data."""
        return {
            'subscription_type': 'tier_patterns',
            'pattern_type': event_data['pattern'],
            'symbol': event_data['symbol'],
            'tier': event_data['tier'],
            'confidence': event_data['confidence']
        }

    @staticmethod
    def measure_memory_usage() -> float:
        """Measure current process memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    @staticmethod
    def time_websocket_operation(operation_func, operation_name: str) -> WebSocketPerformanceResult:
        """Time a WebSocket operation and measure performance."""
        gc.collect()  # Clean up before measurement
        start_memory = WebSocketPerformanceTestHelper.measure_memory_usage()
        start_time = time.perf_counter()

        try:
            result = operation_func()
            success = True
        except Exception as e:
            result = str(e)
            success = False

        end_time = time.perf_counter()
        end_memory = WebSocketPerformanceTestHelper.measure_memory_usage()

        # Extract relevant metrics from result
        user_count = 0
        delivery_count = 0
        filtering_time_ms = 0

        if isinstance(result, dict):
            user_count = result.get('user_count', 0)
            delivery_count = result.get('delivery_count', 0)
            filtering_time_ms = result.get('filtering_time_ms', 0)
        elif isinstance(result, int):
            delivery_count = result

        return WebSocketPerformanceResult(
            operation=operation_name,
            duration_ms=(end_time - start_time) * 1000,
            user_count=user_count,
            delivery_count=delivery_count,
            filtering_time_ms=filtering_time_ms,
            memory_mb=end_memory - start_memory,
            success=success,
            metadata={
                'result': result,
                'start_memory_mb': start_memory,
                'end_memory_mb': end_memory
            }
        )


@pytest.fixture
def ws_performance_helper():
    """Create WebSocket performance test helper."""
    return WebSocketPerformanceTestHelper()


@pytest.fixture
def universal_manager():
    """Create UniversalWebSocketManager for testing."""
    return WebSocketPerformanceTestHelper.create_test_universal_manager()


class TestWebSocketManagerBasicPerformance:
    """Test basic WebSocket manager performance with indexing integration."""

    def test_subscription_performance_with_indexing(self, universal_manager, ws_performance_helper):
        """Test subscription operations performance with indexing system."""
        # Test single subscription performance
        user_id = "test_user_001"
        subscription_type = "tier_patterns"
        filters = ws_performance_helper.generate_realistic_subscription(user_id)

        def subscribe_operation():
            success = universal_manager.subscribe_user(user_id, subscription_type, filters)
            return {'success': success}

        result = ws_performance_helper.time_websocket_operation(subscribe_operation, "single_subscription")

        # Validate: Subscription should be fast
        assert result.success, f"Subscription operation failed: {result.metadata['result']}"
        assert result.duration_ms < 10.0, f"Subscription took {result.duration_ms:.2f}ms, expected <10ms"

        # Validate: Index manager should be updated
        stats = universal_manager.get_subscription_stats()
        assert stats['total_users'] == 1
        assert stats['active_subscriptions'] == 1

        print(f"Single subscription performance: {result.duration_ms:.3f}ms")

    def test_bulk_subscription_performance(self, universal_manager, ws_performance_helper):
        """Test bulk subscription operations performance."""
        num_users = 100
        subscriptions_added = 0

        def bulk_subscribe_operation():
            nonlocal subscriptions_added
            for i in range(num_users):
                user_id = f"bulk_user_{i:03d}"
                filters = ws_performance_helper.generate_realistic_subscription(user_id)
                success = universal_manager.subscribe_user(user_id, "tier_patterns", filters)
                if success:
                    subscriptions_added += 1
            return {'subscriptions_added': subscriptions_added}

        result = ws_performance_helper.time_websocket_operation(bulk_subscribe_operation, "bulk_subscriptions")

        # Validate: Bulk operations should complete successfully
        assert result.success, f"Bulk subscription failed: {result.metadata['result']}"
        assert subscriptions_added == num_users, f"Only {subscriptions_added}/{num_users} subscriptions succeeded"

        # Calculate per-subscription time
        per_subscription_ms = result.duration_ms / num_users
        assert per_subscription_ms < 2.0, f"Per-subscription time {per_subscription_ms:.2f}ms too high"

        # Validate: Index system should be properly populated
        stats = universal_manager.get_subscription_stats()
        assert stats['total_users'] == num_users
        assert stats['index_performance_status'] == 'good'

        print(f"Bulk subscription performance: {result.duration_ms:.3f}ms total ({per_subscription_ms:.3f}ms per subscription)")
        print(f"Index system: {stats['total_indexes']} indexes, {stats['index_cache_hit_rate']:.1f}% cache hit rate")

    def test_filtering_performance_integration(self, universal_manager, ws_performance_helper):
        """Test filtering performance with indexing system integration."""
        # Setup: Add 500 users with varied subscriptions
        for i in range(500):
            user_id = f"filter_user_{i:03d}"
            filters = ws_performance_helper.generate_realistic_subscription(user_id)
            universal_manager.subscribe_user(user_id, "tier_patterns", filters)

        # Test filtering performance
        event_data = ws_performance_helper.generate_realistic_event_data()
        criteria = ws_performance_helper.generate_targeting_criteria(event_data)

        def filtering_operation():
            # Access the internal filtering method for direct testing
            matching_users = universal_manager._find_interested_users(criteria)
            filtering_stats = universal_manager.get_subscription_stats()
            return {
                'matching_users': len(matching_users),
                'filtering_time_ms': filtering_stats['avg_filtering_latency_ms'],
                'index_lookup_ms': filtering_stats['index_avg_lookup_ms']
            }

        result = ws_performance_helper.time_websocket_operation(filtering_operation, "user_filtering")

        # Validate: Filtering should meet performance targets
        assert result.success, f"Filtering operation failed: {result.metadata['result']}"

        filtering_result = result.metadata['result']
        index_lookup_time = filtering_result['index_lookup_ms']

        # Primary target: <5ms filtering with indexing
        assert index_lookup_time < 5.0, f"Index lookup took {index_lookup_time:.2f}ms, expected <5ms"
        assert result.duration_ms < 10.0, f"Overall filtering took {result.duration_ms:.2f}ms, expected <10ms"

        print(f"Filtering performance: {result.duration_ms:.3f}ms total, {index_lookup_time:.3f}ms index lookup")
        print(f"Found {filtering_result['matching_users']} matching users out of 500")

    def test_broadcast_end_to_end_performance(self, universal_manager, ws_performance_helper):
        """Test end-to-end broadcast performance with indexing."""
        # Setup: Add users and connect them
        num_users = 200
        connected_users = []

        for i in range(num_users):
            user_id = f"broadcast_user_{i:03d}"
            filters = ws_performance_helper.generate_realistic_subscription(user_id)
            universal_manager.subscribe_user(user_id, "tier_patterns", filters)

            # Mock connection for some users
            if i % 2 == 0:  # Connect every other user
                universal_manager.existing_ws_manager.connect_user(user_id, f"conn_{i}")
                connected_users.append(user_id)

        # Test broadcast performance
        event_data = ws_performance_helper.generate_realistic_event_data()
        criteria = ws_performance_helper.generate_targeting_criteria(event_data)

        def broadcast_operation():
            delivery_count = universal_manager.broadcast_event(
                "tier_pattern_detected",
                event_data,
                criteria
            )
            broadcast_stats = universal_manager.get_subscription_stats()
            return {
                'delivery_count': delivery_count,
                'filtering_time_ms': broadcast_stats['avg_filtering_latency_ms'],
                'broadcast_time_ms': broadcast_stats['avg_broadcast_latency_ms']
            }

        result = ws_performance_helper.time_websocket_operation(broadcast_operation, "broadcast_event")

        # Validate: Broadcast should meet performance targets
        assert result.success, f"Broadcast operation failed: {result.metadata['result']}"

        broadcast_result = result.metadata['result']
        delivery_count = broadcast_result['delivery_count']
        filtering_time = broadcast_result['filtering_time_ms']
        broadcast_time = broadcast_result['broadcast_time_ms']

        # Performance targets
        assert result.duration_ms < 100.0, f"End-to-end broadcast took {result.duration_ms:.2f}ms, expected <100ms"
        assert filtering_time < 5.0, f"Filtering took {filtering_time:.2f}ms, expected <5ms"
        assert delivery_count > 0, "Should deliver to at least some users"

        # Validate WebSocket emit calls
        socketio_mock = universal_manager.socketio
        emit_count = socketio_mock.get_emit_count_for_event("tier_pattern_detected")
        assert emit_count == delivery_count, f"Expected {delivery_count} emits, got {emit_count}"

        print(f"Broadcast performance: {result.duration_ms:.3f}ms end-to-end")
        print(f"Delivered to {delivery_count} users, filtering: {filtering_time:.3f}ms")


class TestWebSocketManagerScalabilityPerformance:
    """Test WebSocket manager scalability with indexing system."""

    def test_concurrent_user_scalability(self, ws_performance_helper):
        """Test scalability with increasing concurrent user counts."""
        user_counts = [50, 100, 250, 500]
        scalability_results = []

        for user_count in user_counts:
            # Create fresh manager for each test
            manager = ws_performance_helper.create_test_universal_manager()

            # Add users
            for i in range(user_count):
                user_id = f"scale_user_{i:03d}"
                filters = ws_performance_helper.generate_realistic_subscription(user_id)
                manager.subscribe_user(user_id, "tier_patterns", filters)

                # Connect some users
                if i % 3 == 0:
                    manager.existing_ws_manager.connect_user(user_id, f"conn_{i}")

            # Test broadcast performance
            event_data = ws_performance_helper.generate_realistic_event_data()
            criteria = ws_performance_helper.generate_targeting_criteria(event_data)

            def scale_broadcast_operation():
                return manager.broadcast_event("tier_pattern_detected", event_data, criteria)

            result = ws_performance_helper.time_websocket_operation(scale_broadcast_operation, f"scale_{user_count}_users")

            # Get detailed stats
            stats = manager.get_subscription_stats()

            scalability_results.append({
                'user_count': user_count,
                'broadcast_time_ms': result.duration_ms,
                'delivery_count': result.metadata['result'] if result.success else 0,
                'filtering_time_ms': stats['avg_filtering_latency_ms'],
                'index_lookup_ms': stats['index_avg_lookup_ms'],
                'cache_hit_rate': stats['index_cache_hit_rate'],
                'total_indexes': stats['total_indexes']
            })

            print(f"{user_count:3d} users: {result.duration_ms:6.2f}ms broadcast, "
                  f"{stats['index_avg_lookup_ms']:5.2f}ms indexing, "
                  f"{stats['index_cache_hit_rate']:5.1f}% cache hit")

        # Validate: Performance should scale reasonably
        for i, result_data in enumerate(scalability_results):
            user_count = result_data['user_count']
            broadcast_time = result_data['broadcast_time_ms']
            index_time = result_data['index_lookup_ms']

            # Performance targets based on user count
            if user_count <= 100:
                max_broadcast_time = 50.0
                max_index_time = 3.0
            elif user_count <= 250:
                max_broadcast_time = 75.0
                max_index_time = 4.0
            else:  # 500+ users
                max_broadcast_time = 100.0
                max_index_time = 5.0

            assert broadcast_time < max_broadcast_time, f"{user_count} users: broadcast {broadcast_time:.2f}ms > {max_broadcast_time}ms"
            assert index_time < max_index_time, f"{user_count} users: indexing {index_time:.2f}ms > {max_index_time}ms"

        # Validate: No exponential degradation
        broadcast_times = [r['broadcast_time_ms'] for r in scalability_results]
        index_times = [r['index_lookup_ms'] for r in scalability_results]

        # Check growth rates
        broadcast_growth_rates = [broadcast_times[i+1]/broadcast_times[i] for i in range(len(broadcast_times)-1)]
        index_growth_rates = [index_times[i+1]/max(index_times[i], 0.001) for i in range(len(index_times)-1)]

        max_broadcast_growth = max(broadcast_growth_rates)
        max_index_growth = max(index_growth_rates)

        assert max_broadcast_growth < 3.0, f"Broadcast performance degraded by {max_broadcast_growth:.1f}x, expected <3x"
        assert max_index_growth < 2.0, f"Index performance degraded by {max_index_growth:.1f}x, expected <2x"

    def test_high_frequency_event_performance(self, universal_manager, ws_performance_helper):
        """Test performance under high-frequency event broadcasting."""
        # Setup: Add 300 users
        for i in range(300):
            user_id = f"freq_user_{i:03d}"
            filters = ws_performance_helper.generate_realistic_subscription(user_id)
            universal_manager.subscribe_user(user_id, "tier_patterns", filters)

            # Connect users
            if i % 2 == 0:
                universal_manager.existing_ws_manager.connect_user(user_id, f"conn_{i}")

        # Test high-frequency broadcasting
        def high_frequency_broadcast():
            event_times = []
            total_deliveries = 0

            for i in range(50):  # 50 rapid events
                event_data = ws_performance_helper.generate_realistic_event_data()
                criteria = ws_performance_helper.generate_targeting_criteria(event_data)

                start_time = time.perf_counter()
                delivery_count = universal_manager.broadcast_event(f"rapid_event_{i}", event_data, criteria)
                end_time = time.perf_counter()

                event_time_ms = (end_time - start_time) * 1000
                event_times.append(event_time_ms)
                total_deliveries += delivery_count

                # Small delay to avoid overwhelming
                time.sleep(0.001)

            return {
                'event_count': len(event_times),
                'total_deliveries': total_deliveries,
                'avg_event_time_ms': sum(event_times) / len(event_times),
                'max_event_time_ms': max(event_times),
                'events_per_second': len(event_times) / (sum(event_times) / 1000)
            }

        result = ws_performance_helper.time_websocket_operation(high_frequency_broadcast, "high_frequency_events")

        # Validate: High-frequency performance
        assert result.success, f"High-frequency broadcast failed: {result.metadata['result']}"

        freq_result = result.metadata['result']
        avg_event_time = freq_result['avg_event_time_ms']
        max_event_time = freq_result['max_event_time_ms']
        events_per_second = freq_result['events_per_second']

        # Performance targets for high-frequency events
        assert avg_event_time < 20.0, f"Average event time {avg_event_time:.2f}ms too high for high frequency"
        assert max_event_time < 50.0, f"Max event time {max_event_time:.2f}ms too high"
        assert events_per_second > 10, f"Only {events_per_second:.1f} events/sec, expected >10"

        # Validate system remains healthy
        stats = universal_manager.get_subscription_stats()
        assert stats['index_avg_lookup_ms'] < 5.0, "Index performance degraded during high-frequency test"

        print(f"High-frequency performance: {avg_event_time:.3f}ms avg, {max_event_time:.3f}ms max")
        print(f"Throughput: {events_per_second:.1f} events/sec, {freq_result['total_deliveries']} total deliveries")

    def test_memory_efficiency_under_load(self, ws_performance_helper):
        """Test memory efficiency with sustained load."""
        # Create manager and measure baseline
        gc.collect()
        baseline_memory = ws_performance_helper.measure_memory_usage()

        manager = ws_performance_helper.create_test_universal_manager()

        # Add users in batches and measure memory growth
        batch_size = 100
        num_batches = 5
        memory_measurements = []

        for batch in range(num_batches):
            # Add batch of users
            for i in range(batch_size):
                user_id = f"memory_user_{batch}_{i:03d}"
                filters = ws_performance_helper.generate_realistic_subscription(user_id)
                manager.subscribe_user(user_id, "tier_patterns", filters)

                # Connect and perform some operations
                if i % 3 == 0:
                    manager.existing_ws_manager.connect_user(user_id, f"conn_{batch}_{i}")

            # Perform broadcast operations to populate caches
            for _ in range(20):
                event_data = ws_performance_helper.generate_realistic_event_data()
                criteria = ws_performance_helper.generate_targeting_criteria(event_data)
                manager.broadcast_event("memory_test_event", event_data, criteria)

            # Measure memory
            gc.collect()
            current_memory = ws_performance_helper.measure_memory_usage()
            memory_used = current_memory - baseline_memory
            total_users = (batch + 1) * batch_size

            memory_measurements.append({
                'users': total_users,
                'memory_mb': memory_used,
                'memory_per_user_kb': (memory_used / total_users) * 1024
            })

            print(f"Batch {batch + 1}: {total_users} users, {memory_used:.2f}MB ({(memory_used/total_users)*1024:.1f}KB/user)")

        # Validate: Memory growth should be reasonable and linear
        for measurement in memory_measurements:
            users = measurement['users']
            memory_per_user = measurement['memory_per_user_kb']

            # Memory per user should be reasonable (allow for indexing overhead)
            max_memory_per_user = 2.0  # 2KB per user including indexing
            assert memory_per_user < max_memory_per_user, f"{users} users: {memory_per_user:.1f}KB per user > {max_memory_per_user}KB"

        # Check final system health
        final_stats = manager.get_subscription_stats()
        health = manager.get_health_status()

        assert health['status'] in ['healthy', 'warning'], f"System unhealthy after load: {health['status']}"
        assert final_stats['total_users'] == num_batches * batch_size

        final_memory = memory_measurements[-1]['memory_mb']
        print(f"Final memory usage: {final_memory:.2f}MB for {final_stats['total_users']} users")


class TestWebSocketManagerConcurrencyPerformance:
    """Test WebSocket manager performance under concurrent operations."""

    def test_concurrent_subscription_operations(self, universal_manager, ws_performance_helper):
        """Test concurrent subscription add/remove operations performance."""
        operation_results = []

        def subscription_worker(worker_id: int):
            """Worker performing concurrent subscription operations."""
            worker_results = []

            # Add subscriptions
            for i in range(15):
                user_id = f"concurrent_worker_{worker_id}_user_{i:02d}"
                filters = ws_performance_helper.generate_realistic_subscription(user_id)

                start_time = time.perf_counter()
                success = universal_manager.subscribe_user(user_id, "tier_patterns", filters)
                end_time = time.perf_counter()

                operation_time = (end_time - start_time) * 1000
                worker_results.append({
                    'operation': 'subscribe',
                    'time_ms': operation_time,
                    'success': success
                })

                # Mock connection
                if i % 2 == 0:
                    universal_manager.existing_ws_manager.connect_user(user_id, f"conn_{worker_id}_{i}")

            # Perform broadcasts
            for _ in range(10):
                event_data = ws_performance_helper.generate_realistic_event_data()
                criteria = ws_performance_helper.generate_targeting_criteria(event_data)

                start_time = time.perf_counter()
                delivery_count = universal_manager.broadcast_event("concurrent_test", event_data, criteria)
                end_time = time.perf_counter()

                broadcast_time = (end_time - start_time) * 1000
                worker_results.append({
                    'operation': 'broadcast',
                    'time_ms': broadcast_time,
                    'success': delivery_count >= 0,
                    'delivery_count': delivery_count
                })

            # Remove some subscriptions
            for i in range(7):
                user_id = f"concurrent_worker_{worker_id}_user_{i:02d}"

                start_time = time.perf_counter()
                success = universal_manager.unsubscribe_user(user_id)
                end_time = time.perf_counter()

                operation_time = (end_time - start_time) * 1000
                worker_results.append({
                    'operation': 'unsubscribe',
                    'time_ms': operation_time,
                    'success': success
                })

            return worker_results

        # Run concurrent workers
        num_workers = 6
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(subscription_worker, i) for i in range(num_workers)]

            for future in as_completed(futures):
                worker_results = future.result()
                operation_results.extend(worker_results)

        # Analyze concurrent operation performance
        subscribe_ops = [r for r in operation_results if r['operation'] == 'subscribe']
        broadcast_ops = [r for r in operation_results if r['operation'] == 'broadcast']
        unsubscribe_ops = [r for r in operation_results if r['operation'] == 'unsubscribe']

        # Validate: All operations should succeed
        failed_subscribes = [r for r in subscribe_ops if not r['success']]
        failed_broadcasts = [r for r in broadcast_ops if not r['success']]
        failed_unsubscribes = [r for r in unsubscribe_ops if not r['success']]

        assert len(failed_subscribes) == 0, f"{len(failed_subscribes)} subscribe operations failed"
        assert len(failed_broadcasts) == 0, f"{len(failed_broadcasts)} broadcast operations failed"
        assert len(failed_unsubscribes) == 0, f"{len(failed_unsubscribes)} unsubscribe operations failed"

        # Calculate performance metrics
        avg_subscribe_time = sum(r['time_ms'] for r in subscribe_ops) / len(subscribe_ops)
        avg_broadcast_time = sum(r['time_ms'] for r in broadcast_ops) / len(broadcast_ops)
        avg_unsubscribe_time = sum(r['time_ms'] for r in unsubscribe_ops) / len(unsubscribe_ops)

        total_deliveries = sum(r.get('delivery_count', 0) for r in broadcast_ops)

        # Validate: Concurrent performance should remain reasonable
        assert avg_subscribe_time < 10.0, f"Concurrent subscribe avg {avg_subscribe_time:.2f}ms too high"
        assert avg_broadcast_time < 50.0, f"Concurrent broadcast avg {avg_broadcast_time:.2f}ms too high"
        assert avg_unsubscribe_time < 10.0, f"Concurrent unsubscribe avg {avg_unsubscribe_time:.2f}ms too high"

        # Validate final system state
        stats = universal_manager.get_subscription_stats()
        expected_remaining_users = num_workers * (15 - 7)  # 15 added - 7 removed per worker

        print(f"Concurrent operations - Subscribe: {avg_subscribe_time:.2f}ms, "
              f"Broadcast: {avg_broadcast_time:.2f}ms, Unsubscribe: {avg_unsubscribe_time:.2f}ms")
        print(f"Total deliveries: {total_deliveries}, Final users: {stats['total_users']}")
        print(f"Index performance: {stats['index_avg_lookup_ms']:.2f}ms avg lookup")

    def test_sustained_concurrent_load(self, universal_manager, ws_performance_helper):
        """Test system performance under sustained concurrent load."""
        # Setup: Add base users
        base_users = 200
        for i in range(base_users):
            user_id = f"sustained_user_{i:03d}"
            filters = ws_performance_helper.generate_realistic_subscription(user_id)
            universal_manager.subscribe_user(user_id, "tier_patterns", filters)

            if i % 2 == 0:
                universal_manager.existing_ws_manager.connect_user(user_id, f"conn_{i}")

        def sustained_worker():
            """Worker performing continuous operations for sustained load test."""
            operations_completed = 0
            operation_times = []
            start_time = time.time()

            while time.time() - start_time < 30:  # 30 second sustained test
                operation_type = random.choice(['broadcast', 'broadcast', 'subscribe', 'unsubscribe'])

                op_start = time.perf_counter()

                try:
                    if operation_type == 'broadcast':
                        event_data = ws_performance_helper.generate_realistic_event_data()
                        criteria = ws_performance_helper.generate_targeting_criteria(event_data)
                        universal_manager.broadcast_event("sustained_test", event_data, criteria)
                    elif operation_type == 'subscribe':
                        user_id = f"temp_user_{random.randint(10000, 99999)}"
                        filters = ws_performance_helper.generate_realistic_subscription(user_id)
                        universal_manager.subscribe_user(user_id, "tier_patterns", filters)
                    elif operation_type == 'unsubscribe':
                        user_id = f"temp_user_{random.randint(10000, 99999)}"
                        universal_manager.unsubscribe_user(user_id)

                    op_end = time.perf_counter()
                    operation_time = (op_end - op_start) * 1000
                    operation_times.append(operation_time)
                    operations_completed += 1

                except Exception as e:
                    print(f"Operation failed: {e}")

                # Small delay
                time.sleep(0.01)

            return {
                'operations_completed': operations_completed,
                'avg_time_ms': sum(operation_times) / len(operation_times) if operation_times else 0,
                'max_time_ms': max(operation_times) if operation_times else 0,
                'total_time_ms': sum(operation_times)
            }

        # Run sustained load with multiple workers
        num_workers = 4
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(sustained_worker) for _ in range(num_workers)]

            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # Analyze sustained load results
        total_operations = sum(r['operations_completed'] for r in results)
        all_avg_times = [r['avg_time_ms'] for r in results if r['avg_time_ms'] > 0]
        all_max_times = [r['max_time_ms'] for r in results if r['max_time_ms'] > 0]

        overall_avg_time = sum(all_avg_times) / len(all_avg_times) if all_avg_times else 0
        overall_max_time = max(all_max_times) if all_max_times else 0
        operations_per_second = total_operations / 30  # 30 second test

        # Validate: Sustained performance should remain reasonable
        assert overall_avg_time < 25.0, f"Sustained load avg {overall_avg_time:.2f}ms too high"
        assert overall_max_time < 100.0, f"Sustained load max {overall_max_time:.2f}ms too high"
        assert operations_per_second > 20, f"Only {operations_per_second:.1f} ops/sec sustained"

        # Check system health after sustained load
        stats = universal_manager.get_subscription_stats()
        health = universal_manager.get_health_status()

        assert health['status'] in ['healthy', 'warning'], f"System degraded after sustained load: {health['status']}"

        print(f"Sustained load: {total_operations} operations in 30s ({operations_per_second:.1f} ops/sec)")
        print(f"Performance: avg {overall_avg_time:.2f}ms, max {overall_max_time:.2f}ms")
        print(f"Index performance: {stats['index_avg_lookup_ms']:.2f}ms, cache hit: {stats['index_cache_hit_rate']:.1f}%")
        print(f"Final health: {health['status']}")


@pytest.mark.performance
class TestWebSocketIntegrationBenchmarks:
    """Comprehensive performance benchmarks for WebSocket integration with indexing."""

    def test_comprehensive_websocket_performance_benchmark(self, ws_performance_helper):
        """Comprehensive benchmark for WebSocket manager with indexing integration."""
        print("\n" + "="*80)
        print("SPRINT 25 DAY 2 WEBSOCKET INTEGRATION PERFORMANCE BENCHMARK")
        print("="*80)

        benchmark_results = {}

        # Test 1: Subscription Performance
        print("\n1. SUBSCRIPTION PERFORMANCE")
        print("-" * 40)

        manager = ws_performance_helper.create_test_universal_manager()

        # Single subscription
        def single_subscription():
            return manager.subscribe_user("bench_user_001", "tier_patterns",
                                        ws_performance_helper.generate_realistic_subscription("bench_user_001"))

        single_result = ws_performance_helper.time_websocket_operation(single_subscription, "single_subscription")

        # Bulk subscriptions
        def bulk_subscriptions():
            success_count = 0
            for i in range(100):
                user_id = f"bulk_user_{i:03d}"
                filters = ws_performance_helper.generate_realistic_subscription(user_id)
                if manager.subscribe_user(user_id, "tier_patterns", filters):
                    success_count += 1
            return success_count

        bulk_result = ws_performance_helper.time_websocket_operation(bulk_subscriptions, "bulk_subscriptions")
        bulk_per_sub_ms = bulk_result.duration_ms / 100

        benchmark_results['subscriptions'] = {
            'single_time_ms': single_result.duration_ms,
            'bulk_total_ms': bulk_result.duration_ms,
            'bulk_per_subscription_ms': bulk_per_sub_ms,
            'meets_targets': single_result.duration_ms < 10.0 and bulk_per_sub_ms < 2.0
        }

        single_status = "✓ PASS" if single_result.duration_ms < 10.0 else "✗ FAIL"
        bulk_status = "✓ PASS" if bulk_per_sub_ms < 2.0 else "✗ FAIL"

        print(f"Single subscription: {single_result.duration_ms:.3f}ms (target: <10ms) {single_status}")
        print(f"Bulk subscriptions: {bulk_per_sub_ms:.3f}ms per sub (target: <2ms) {bulk_status}")

        # Test 2: Filtering Performance with Indexing
        print("\n2. FILTERING PERFORMANCE (WITH INDEXING)")
        print("-" * 40)

        # Test different user counts
        filtering_results = {}
        for user_count in [100, 500, 1000]:
            fresh_manager = ws_performance_helper.create_test_universal_manager()

            # Add users
            for i in range(user_count):
                user_id = f"filter_user_{user_count}_{i:04d}"
                filters = ws_performance_helper.generate_realistic_subscription(user_id)
                fresh_manager.subscribe_user(user_id, "tier_patterns", filters)

            # Test filtering
            event_data = ws_performance_helper.generate_realistic_event_data()
            criteria = ws_performance_helper.generate_targeting_criteria(event_data)

            filtering_times = []
            for _ in range(5):
                start_time = time.perf_counter()
                fresh_manager._find_interested_users(criteria)
                end_time = time.perf_counter()
                filtering_times.append((end_time - start_time) * 1000)

            avg_filtering_time = sum(filtering_times) / len(filtering_times)
            stats = fresh_manager.get_subscription_stats()

            target_time = 2.0 if user_count == 100 else 4.0 if user_count == 500 else 5.0
            meets_target = avg_filtering_time < target_time
            status = "✓ PASS" if meets_target else "✗ FAIL"

            filtering_results[f'{user_count}_users'] = {
                'avg_filtering_ms': avg_filtering_time,
                'index_lookup_ms': stats['index_avg_lookup_ms'],
                'cache_hit_rate': stats['index_cache_hit_rate'],
                'meets_target': meets_target
            }

            print(f"{user_count:4d} users: {avg_filtering_time:.3f}ms filtering, "
                  f"{stats['index_avg_lookup_ms']:.3f}ms index (target: <{target_time}ms) {status}")

        benchmark_results['filtering'] = filtering_results

        # Test 3: End-to-End Broadcast Performance
        print("\n3. END-TO-END BROADCAST PERFORMANCE")
        print("-" * 40)

        broadcast_manager = ws_performance_helper.create_test_universal_manager()

        # Setup users with connections
        num_users = 300
        for i in range(num_users):
            user_id = f"broadcast_user_{i:03d}"
            filters = ws_performance_helper.generate_realistic_subscription(user_id)
            broadcast_manager.subscribe_user(user_id, "tier_patterns", filters)

            if i % 2 == 0:  # Connect half the users
                broadcast_manager.existing_ws_manager.connect_user(user_id, f"conn_{i}")

        # Test broadcast performance
        def end_to_end_broadcast():
            event_data = ws_performance_helper.generate_realistic_event_data()
            criteria = ws_performance_helper.generate_targeting_criteria(event_data)
            return broadcast_manager.broadcast_event("benchmark_event", event_data, criteria)

        broadcast_times = []
        delivery_counts = []
        for _ in range(10):
            result = ws_performance_helper.time_websocket_operation(end_to_end_broadcast, "broadcast")
            if result.success:
                broadcast_times.append(result.duration_ms)
                delivery_counts.append(result.metadata['result'])

        avg_broadcast_time = sum(broadcast_times) / len(broadcast_times)
        avg_delivery_count = sum(delivery_counts) / len(delivery_counts)

        broadcast_stats = broadcast_manager.get_subscription_stats()

        broadcast_target_met = avg_broadcast_time < 100.0
        broadcast_status = "✓ PASS" if broadcast_target_met else "✗ FAIL"

        benchmark_results['broadcast'] = {
            'avg_time_ms': avg_broadcast_time,
            'avg_deliveries': avg_delivery_count,
            'filtering_time_ms': broadcast_stats['avg_filtering_latency_ms'],
            'meets_target': broadcast_target_met
        }

        print(f"End-to-end broadcast: {avg_broadcast_time:.3f}ms avg (target: <100ms) {broadcast_status}")
        print(f"Average deliveries: {avg_delivery_count:.1f} users, filtering: {broadcast_stats['avg_filtering_latency_ms']:.3f}ms")

        # Test 4: Memory Efficiency
        print("\n4. MEMORY EFFICIENCY")
        print("-" * 40)

        gc.collect()
        start_memory = ws_performance_helper.measure_memory_usage()

        memory_manager = ws_performance_helper.create_test_universal_manager()

        # Add users and perform operations
        memory_users = 500
        for i in range(memory_users):
            user_id = f"memory_user_{i:03d}"
            filters = ws_performance_helper.generate_realistic_subscription(user_id)
            memory_manager.subscribe_user(user_id, "tier_patterns", filters)

            if i % 3 == 0:
                memory_manager.existing_ws_manager.connect_user(user_id, f"mem_conn_{i}")

        # Perform operations to populate caches
        for _ in range(50):
            event_data = ws_performance_helper.generate_realistic_event_data()
            criteria = ws_performance_helper.generate_targeting_criteria(event_data)
            memory_manager.broadcast_event("memory_test", event_data, criteria)

        gc.collect()
        end_memory = ws_performance_helper.measure_memory_usage()
        memory_used = end_memory - start_memory
        memory_per_user_kb = (memory_used / memory_users) * 1024

        memory_target_met = memory_used < 3.0  # Allow 3MB for 500 users with indexing
        memory_status = "✓ PASS" if memory_target_met else "✗ FAIL"

        benchmark_results['memory'] = {
            'total_memory_mb': memory_used,
            'memory_per_user_kb': memory_per_user_kb,
            'meets_target': memory_target_met
        }

        print(f"Memory usage: {memory_used:.2f}MB for {memory_users} users ({memory_per_user_kb:.1f}KB/user) (target: <3MB) {memory_status}")

        # Test 5: Concurrency Performance
        print("\n5. CONCURRENCY PERFORMANCE")
        print("-" * 40)

        concurrency_manager = ws_performance_helper.create_test_universal_manager()

        # Setup base users
        for i in range(150):
            user_id = f"conc_user_{i:03d}"
            filters = ws_performance_helper.generate_realistic_subscription(user_id)
            concurrency_manager.subscribe_user(user_id, "tier_patterns", filters)

            if i % 2 == 0:
                concurrency_manager.existing_ws_manager.connect_user(user_id, f"conc_conn_{i}")

        def concurrent_broadcast_worker():
            times = []
            for _ in range(8):
                event_data = ws_performance_helper.generate_realistic_event_data()
                criteria = ws_performance_helper.generate_targeting_criteria(event_data)

                start = time.perf_counter()
                concurrency_manager.broadcast_event("concurrent_test", event_data, criteria)
                end = time.perf_counter()
                times.append((end - start) * 1000)
            return times

        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(concurrent_broadcast_worker) for _ in range(6)]
            all_concurrent_times = []
            for future in as_completed(futures):
                all_concurrent_times.extend(future.result())

        concurrent_avg = sum(all_concurrent_times) / len(all_concurrent_times)
        concurrent_max = max(all_concurrent_times)

        concurrent_target_met = concurrent_avg < 50.0 and concurrent_max < 100.0
        concurrent_status = "✓ PASS" if concurrent_target_met else "✗ FAIL"

        benchmark_results['concurrency'] = {
            'avg_time_ms': concurrent_avg,
            'max_time_ms': concurrent_max,
            'operations': len(all_concurrent_times),
            'meets_target': concurrent_target_met
        }

        print(f"Concurrent operations: {concurrent_avg:.3f}ms avg, {concurrent_max:.3f}ms max {concurrent_status}")
        print(f"({len(all_concurrent_times)} operations, targets: <50ms avg, <100ms max)")

        # Summary
        print("\n" + "="*80)
        print("WEBSOCKET INTEGRATION BENCHMARK SUMMARY")
        print("="*80)

        all_targets_met = all(
            result.get('meets_targets', result.get('meets_target', False))
            for result in benchmark_results.values()
            if isinstance(result, dict) and ('meets_targets' in result or 'meets_target' in result)
        )

        # Check filtering results separately
        filtering_targets_met = all(
            result['meets_target'] for result in benchmark_results['filtering'].values()
        )

        overall_targets_met = all_targets_met and filtering_targets_met
        overall_status = "✓ ALL TARGETS MET" if overall_targets_met else "✗ SOME TARGETS MISSED"
        print(f"Overall Performance: {overall_status}")

        print("\nSpring 25 Day 2 WebSocket Integration Requirements:")
        print(f"  • Fast subscription operations: {'✓' if benchmark_results['subscriptions']['meets_targets'] else '✗'}")
        print(f"  • <5ms filtering with indexing: {'✓' if benchmark_results['filtering']['1000_users']['meets_target'] else '✗'}")
        print(f"  • <100ms end-to-end broadcast: {'✓' if benchmark_results['broadcast']['meets_target'] else '✗'}")
        print(f"  • Efficient memory usage: {'✓' if benchmark_results['memory']['meets_target'] else '✗'}")
        print(f"  • Concurrent operation support: {'✓' if benchmark_results['concurrency']['meets_target'] else '✗'}")

        # Final validation
        assert overall_targets_met, f"WebSocket integration performance targets not met: {benchmark_results}"

        return benchmark_results


if __name__ == "__main__":
    # Run WebSocket integration performance tests directly
    pytest.main([__file__, "-v", "--tb=short", "-m", "performance"])
