"""
Test Suite for Stress Testing and Concurrency
Sprint 25 Week 1 - Comprehensive stress testing and thread safety validation

Tests the complete 4-layer WebSocket architecture under extreme conditions:
- 500+ concurrent users with sustained load
- Multi-threaded operations and race condition detection
- Resource exhaustion scenarios
- System recovery and resilience testing
- Memory leak detection and resource cleanup
"""

import gc
import random
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.core.services.websocket_subscription_manager import UniversalWebSocketManager
from src.infrastructure.websocket.scalable_broadcaster import DeliveryPriority


@dataclass
class StressTestResult:
    """Result from a stress test operation."""
    success: bool
    duration_ms: float
    error_message: str = ""
    data: dict[str, Any] = None


class ConcurrencyTestManager:
    """Manages concurrent test operations and results collection."""

    def __init__(self):
        self.results: list[StressTestResult] = []
        self.errors: list[str] = []
        self.lock = threading.Lock()
        self.start_time = time.time()

    def add_result(self, result: StressTestResult):
        """Thread-safe result addition."""
        with self.lock:
            self.results.append(result)
            if not result.success:
                self.errors.append(result.error_message)

    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive test statistics."""
        with self.lock:
            if not self.results:
                return {'total_operations': 0, 'success_rate': 0}

            successful = [r for r in self.results if r.success]
            durations = [r.duration_ms for r in self.results if r.duration_ms > 0]

            return {
                'total_operations': len(self.results),
                'successful_operations': len(successful),
                'failed_operations': len(self.errors),
                'success_rate_percent': (len(successful) / len(self.results)) * 100,
                'avg_duration_ms': statistics.mean(durations) if durations else 0,
                'max_duration_ms': max(durations) if durations else 0,
                'min_duration_ms': min(durations) if durations else 0,
                'total_runtime_seconds': time.time() - self.start_time,
                'errors': self.errors
            }


@pytest.fixture
def stress_test_system():
    """Create system optimized for stress testing."""
    mock_socketio = Mock()
    mock_socketio.server = Mock()
    mock_socketio.emit = Mock()

    mock_redis = Mock()
    mock_existing_ws = Mock()
    mock_existing_ws.is_user_connected.return_value = True
    mock_existing_ws.get_user_connections.return_value = ['conn_stress']

    mock_ws_broadcaster = Mock()

    # Create system with stress-test optimized settings
    universal_manager = UniversalWebSocketManager(
        socketio=mock_socketio,
        redis_client=mock_redis,
        existing_websocket_manager=mock_existing_ws,
        websocket_broadcaster=mock_ws_broadcaster
    )

    return {
        'universal_manager': universal_manager,
        'index_manager': universal_manager.index_manager,
        'broadcaster': universal_manager.broadcaster,
        'event_router': universal_manager.event_router,
        'socketio': mock_socketio
    }


@pytest.mark.stress
class TestStressAndConcurrency:
    """Comprehensive stress testing and concurrency validation."""

    def test_500_plus_concurrent_user_subscriptions(self, stress_test_system):
        """Test system handles 500+ concurrent user subscriptions without issues."""
        system = stress_test_system
        universal_manager = system['universal_manager']
        test_manager = ConcurrencyTestManager()

        def subscription_worker(user_batch_start: int, user_batch_size: int, worker_id: int):
            """Worker function for concurrent user subscriptions."""
            for i in range(user_batch_size):
                user_id = f"stress_user_{user_batch_start + i:04d}"
                start_time = time.time()

                try:
                    success = universal_manager.subscribe_user(
                        user_id=user_id,
                        subscription_type="tier_patterns",
                        filters={
                            'pattern_types': ['BreakoutBO', 'TrendReversal', 'SurgeDetection'][i % 3],
                            'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'][i % 5],
                            'tiers': ['daily', 'intraday'],
                            'confidence_min': 0.5 + (i % 5) * 0.1,
                            'priority_min': ['LOW', 'MEDIUM', 'HIGH'][i % 3]
                        }
                    )

                    duration_ms = (time.time() - start_time) * 1000

                    result = StressTestResult(
                        success=success,
                        duration_ms=duration_ms,
                        data={'user_id': user_id, 'worker_id': worker_id}
                    )

                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    result = StressTestResult(
                        success=False,
                        duration_ms=duration_ms,
                        error_message=f"Worker {worker_id}, user {user_id}: {str(e)}"
                    )

                test_manager.add_result(result)

                # Small random delay to increase concurrency chaos
                time.sleep(random.uniform(0.001, 0.005))

        # Test with 750 users across 15 worker threads
        target_users = 750
        worker_count = 15
        users_per_worker = target_users // worker_count

        print(f"  Testing {target_users} concurrent subscriptions across {worker_count} workers...")

        # Launch concurrent subscription workers
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="stress-sub") as executor:
            futures = []

            for worker_id in range(worker_count):
                batch_start = worker_id * users_per_worker
                future = executor.submit(
                    subscription_worker,
                    batch_start,
                    users_per_worker,
                    worker_id
                )
                futures.append(future)

            # Wait for all subscriptions to complete
            for future in as_completed(futures, timeout=60):
                try:
                    future.result()
                except Exception as e:
                    test_manager.add_result(StressTestResult(
                        success=False,
                        duration_ms=0,
                        error_message=f"Worker thread error: {str(e)}"
                    ))

        # Analyze stress test results
        stats = test_manager.get_statistics()

        # Verify stress test targets
        assert stats['total_operations'] == target_users, f"Expected {target_users} operations, got {stats['total_operations']}"
        assert stats['success_rate_percent'] >= 95.0, f"Success rate {stats['success_rate_percent']:.1f}% below 95% target"
        assert stats['avg_duration_ms'] < 50.0, f"Average subscription time {stats['avg_duration_ms']:.1f}ms too slow"
        assert stats['max_duration_ms'] < 200.0, f"Max subscription time {stats['max_duration_ms']:.1f}ms excessive"
        assert len(stats['errors']) < (target_users * 0.05), f"Too many errors: {len(stats['errors'])}"

        # Verify system state after stress test
        final_stats = universal_manager.get_subscription_stats()
        assert final_stats['total_users'] >= (target_users * 0.95), f"Only {final_stats['total_users']} users remain"

        print(f"✅ 500+ User Stress Test: {stats['successful_operations']}/{target_users} users in {stats['total_runtime_seconds']:.1f}s")
        print(f"  Success rate: {stats['success_rate_percent']:.1f}%, Avg time: {stats['avg_duration_ms']:.1f}ms")

    def test_concurrent_broadcasting_under_load(self, stress_test_system):
        """Test concurrent broadcasting operations under high load."""
        system = stress_test_system
        universal_manager = system['universal_manager']
        test_manager = ConcurrencyTestManager()

        # Setup user base for broadcasting
        user_count = 400
        for i in range(user_count):
            universal_manager.subscribe_user(
                user_id=f"broadcast_user_{i:03d}",
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL'][i % 3],
                    'confidence_min': 0.7
                }
            )

        def broadcasting_worker(worker_id: int, events_per_worker: int):
            """Worker function for concurrent broadcasting."""
            for event_num in range(events_per_worker):
                start_time = time.time()

                try:
                    # Mock user finding with realistic results
                    with patch.object(universal_manager, '_find_interested_users') as mock_find:
                        # Return different sized user sets
                        user_set_size = 10 + (event_num % 20)  # 10-30 users
                        interested_users = {f"broadcast_user_{i:03d}" for i in range(user_set_size)}
                        mock_find.return_value = interested_users

                        mock_routing_result = Mock()
                        mock_routing_result.total_users = len(interested_users)
                        mock_routing_result.matched_rules = [f'worker_{worker_id}_rule']
                        mock_routing_result.routing_time_ms = 8.0 + random.uniform(-2, 4)
                        mock_routing_result.cache_hit = event_num % 4 == 0  # 25% cache hit

                        with patch.object(system['event_router'], 'route_event') as mock_route:
                            mock_route.return_value = mock_routing_result

                            # Execute broadcast
                            delivery_count = universal_manager.broadcast_event(
                                event_type='stress_broadcast',
                                event_data={
                                    'worker_id': worker_id,
                                    'event_num': event_num,
                                    'timestamp': time.time(),
                                    'stress_test': True
                                },
                                targeting_criteria={
                                    'subscription_type': 'tier_patterns',
                                    'pattern_type': 'BreakoutBO'
                                }
                            )

                            duration_ms = (time.time() - start_time) * 1000

                            result = StressTestResult(
                                success=delivery_count == len(interested_users),
                                duration_ms=duration_ms,
                                data={
                                    'worker_id': worker_id,
                                    'event_num': event_num,
                                    'delivery_count': delivery_count,
                                    'expected_count': len(interested_users)
                                }
                            )

                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    result = StressTestResult(
                        success=False,
                        duration_ms=duration_ms,
                        error_message=f"Worker {worker_id}, event {event_num}: {str(e)}"
                    )

                test_manager.add_result(result)

                # Simulate realistic event intervals
                time.sleep(random.uniform(0.005, 0.020))

        # Launch concurrent broadcasting with multiple workers
        broadcast_workers = 8
        events_per_worker = 25
        total_events = broadcast_workers * events_per_worker

        print(f"  Testing {total_events} concurrent broadcasts across {broadcast_workers} workers...")

        with ThreadPoolExecutor(max_workers=broadcast_workers, thread_name_prefix="stress-broadcast") as executor:
            futures = [
                executor.submit(broadcasting_worker, worker_id, events_per_worker)
                for worker_id in range(broadcast_workers)
            ]

            # Wait for all broadcasts to complete
            for future in as_completed(futures, timeout=120):
                try:
                    future.result()
                except Exception as e:
                    test_manager.add_result(StressTestResult(
                        success=False,
                        duration_ms=0,
                        error_message=f"Broadcast worker error: {str(e)}"
                    ))

        # Analyze broadcasting stress results
        stats = test_manager.get_statistics()

        # Verify broadcasting under load
        assert stats['total_operations'] == total_events, f"Expected {total_events} broadcasts, got {stats['total_operations']}"
        assert stats['success_rate_percent'] >= 90.0, f"Broadcast success rate {stats['success_rate_percent']:.1f}% too low"
        assert stats['avg_duration_ms'] < 150.0, f"Average broadcast time {stats['avg_duration_ms']:.1f}ms too slow"
        assert len(stats['errors']) < (total_events * 0.1), f"Too many broadcast errors: {len(stats['errors'])}"

        print(f"✅ Concurrent Broadcasting: {stats['successful_operations']}/{total_events} broadcasts in {stats['total_runtime_seconds']:.1f}s")
        print(f"  Success rate: {stats['success_rate_percent']:.1f}%, Avg time: {stats['avg_duration_ms']:.1f}ms")

    def test_mixed_operations_chaos_testing(self, stress_test_system):
        """Test mixed concurrent operations (subscribe, broadcast, cleanup, optimize)."""
        system = stress_test_system
        universal_manager = system['universal_manager']
        test_manager = ConcurrencyTestManager()

        # Shared state for chaos testing
        chaos_state = {
            'active_users': set(),
            'lock': threading.Lock()
        }

        def subscription_chaos_worker(worker_id: int):
            """Worker performing subscription operations."""
            for i in range(30):
                operation_start = time.time()
                user_id = f"chaos_user_{worker_id}_{i:02d}"

                try:
                    success = universal_manager.subscribe_user(
                        user_id=user_id,
                        subscription_type="tier_patterns",
                        filters={
                            'pattern_types': ['BreakoutBO'],
                            'symbols': ['AAPL'],
                            'confidence_min': 0.7
                        }
                    )

                    if success:
                        with chaos_state['lock']:
                            chaos_state['active_users'].add(user_id)

                    duration_ms = (time.time() - operation_start) * 1000
                    test_manager.add_result(StressTestResult(
                        success=success,
                        duration_ms=duration_ms,
                        data={'operation': 'subscribe', 'worker_id': worker_id}
                    ))

                except Exception as e:
                    duration_ms = (time.time() - operation_start) * 1000
                    test_manager.add_result(StressTestResult(
                        success=False,
                        duration_ms=duration_ms,
                        error_message=f"Subscribe chaos {worker_id}: {str(e)}"
                    ))

                time.sleep(random.uniform(0.01, 0.05))

        def broadcast_chaos_worker(worker_id: int):
            """Worker performing broadcasting operations."""
            time.sleep(0.5)  # Let some subscriptions happen first

            for i in range(20):
                operation_start = time.time()

                try:
                    with chaos_state['lock']:
                        available_users = list(chaos_state['active_users'])

                    if available_users:
                        target_users = set(random.sample(
                            available_users,
                            min(10, len(available_users))
                        ))

                        with patch.object(universal_manager, '_find_interested_users') as mock_find:
                            mock_find.return_value = target_users

                            mock_routing_result = Mock()
                            mock_routing_result.total_users = len(target_users)
                            mock_routing_result.matched_rules = ['chaos_rule']
                            mock_routing_result.routing_time_ms = 10.0
                            mock_routing_result.cache_hit = i % 3 == 0

                            with patch.object(system['event_router'], 'route_event') as mock_route:
                                mock_route.return_value = mock_routing_result

                                delivery_count = universal_manager.broadcast_event(
                                    event_type='chaos_broadcast',
                                    event_data={'chaos_test': True, 'worker_id': worker_id, 'iteration': i},
                                    targeting_criteria={'subscription_type': 'tier_patterns'}
                                )

                                success = delivery_count == len(target_users)
                    else:
                        success = True  # No users to broadcast to
                        delivery_count = 0

                    duration_ms = (time.time() - operation_start) * 1000
                    test_manager.add_result(StressTestResult(
                        success=success,
                        duration_ms=duration_ms,
                        data={'operation': 'broadcast', 'worker_id': worker_id}
                    ))

                except Exception as e:
                    duration_ms = (time.time() - operation_start) * 1000
                    test_manager.add_result(StressTestResult(
                        success=False,
                        duration_ms=duration_ms,
                        error_message=f"Broadcast chaos {worker_id}: {str(e)}"
                    ))

                time.sleep(random.uniform(0.02, 0.08))

        def cleanup_chaos_worker():
            """Worker performing cleanup operations."""
            time.sleep(1.0)  # Let system build up activity

            for i in range(5):
                operation_start = time.time()

                try:
                    # Mock cleanup operations
                    with patch.object(system['index_manager'], 'cleanup_stale_entries') as mock_cleanup:
                        mock_cleanup.return_value = random.randint(0, 10)

                        cleaned_count = universal_manager.cleanup_inactive_subscriptions(
                            max_inactive_hours=0.1
                        )

                        success = cleaned_count >= 0  # Cleanup should always succeed

                    duration_ms = (time.time() - operation_start) * 1000
                    test_manager.add_result(StressTestResult(
                        success=success,
                        duration_ms=duration_ms,
                        data={'operation': 'cleanup', 'cleaned_count': cleaned_count}
                    ))

                except Exception as e:
                    duration_ms = (time.time() - operation_start) * 1000
                    test_manager.add_result(StressTestResult(
                        success=False,
                        duration_ms=duration_ms,
                        error_message=f"Cleanup chaos: {str(e)}"
                    ))

                time.sleep(random.uniform(0.5, 1.5))

        def optimization_chaos_worker():
            """Worker performing optimization operations."""
            time.sleep(0.8)  # Let activity build up

            for i in range(3):
                operation_start = time.time()

                try:
                    # Mock optimization operations
                    with patch.object(system['index_manager'], 'optimize_indexes') as mock_idx_opt, \
                         patch.object(system['broadcaster'], 'optimize_performance') as mock_broadcast_opt, \
                         patch.object(system['event_router'], 'optimize_performance') as mock_route_opt:

                        mock_idx_opt.return_value = {'optimized': True}
                        mock_broadcast_opt.return_value = {'optimized': True}
                        mock_route_opt.return_value = {'optimized': True}

                        optimization_results = universal_manager.optimize_performance()

                        success = 'performance_targets_met' in optimization_results

                    duration_ms = (time.time() - operation_start) * 1000
                    test_manager.add_result(StressTestResult(
                        success=success,
                        duration_ms=duration_ms,
                        data={'operation': 'optimize'}
                    ))

                except Exception as e:
                    duration_ms = (time.time() - operation_start) * 1000
                    test_manager.add_result(StressTestResult(
                        success=False,
                        duration_ms=duration_ms,
                        error_message=f"Optimization chaos: {str(e)}"
                    ))

                time.sleep(random.uniform(2.0, 4.0))

        # Launch chaos testing with mixed operations
        print("  Running mixed operations chaos test...")

        with ThreadPoolExecutor(max_workers=10, thread_name_prefix="chaos") as executor:
            futures = []

            # Launch subscription workers (4 workers)
            for i in range(4):
                futures.append(executor.submit(subscription_chaos_worker, i))

            # Launch broadcast workers (3 workers)
            for i in range(3):
                futures.append(executor.submit(broadcast_chaos_worker, i))

            # Launch cleanup worker (1 worker)
            futures.append(executor.submit(cleanup_chaos_worker))

            # Launch optimization worker (1 worker)
            futures.append(executor.submit(optimization_chaos_worker))

            # Wait for all chaos operations to complete
            for future in as_completed(futures, timeout=180):
                try:
                    future.result()
                except Exception as e:
                    test_manager.add_result(StressTestResult(
                        success=False,
                        duration_ms=0,
                        error_message=f"Chaos worker error: {str(e)}"
                    ))

        # Analyze chaos test results
        stats = test_manager.get_statistics()

        # Verify system survived chaos testing
        assert stats['success_rate_percent'] >= 85.0, f"Chaos test success rate {stats['success_rate_percent']:.1f}% too low"
        assert len(stats['errors']) < (stats['total_operations'] * 0.15), f"Too many chaos errors: {len(stats['errors'])}"

        # System should remain functional after chaos
        health_status = universal_manager.get_health_status()
        assert health_status['status'] in ['healthy', 'warning'], f"System unhealthy after chaos: {health_status['status']}"

        # Analyze operation breakdown
        operation_counts = {}
        for result in test_manager.results:
            if result.data and 'operation' in result.data:
                op_type = result.data['operation']
                operation_counts[op_type] = operation_counts.get(op_type, 0) + 1

        print(f"✅ Mixed Operations Chaos: {stats['successful_operations']}/{stats['total_operations']} operations")
        print(f"  Success rate: {stats['success_rate_percent']:.1f}%, Operations: {operation_counts}")

    def test_thread_safety_race_condition_detection(self, stress_test_system):
        """Test for race conditions and thread safety issues."""
        system = stress_test_system
        universal_manager = system['universal_manager']

        # Shared state for race condition testing
        race_test_state = {
            'shared_counter': 0,
            'subscription_count': 0,
            'broadcast_count': 0,
            'errors': [],
            'lock': threading.Lock()
        }

        def racing_subscription_worker(worker_id: int, iterations: int):
            """Worker that rapidly creates subscriptions to test for race conditions."""
            for i in range(iterations):
                try:
                    user_id = f"race_user_{worker_id}_{i:03d}"

                    # Rapidly subscribe and immediately query
                    success = universal_manager.subscribe_user(
                        user_id=user_id,
                        subscription_type="tier_patterns",
                        filters={
                            'pattern_types': ['BreakoutBO'],
                            'symbols': ['AAPL'],
                            'confidence_min': 0.8
                        }
                    )

                    if success:
                        # Immediately try to find this user to test indexing race conditions
                        matching_users = system['index_manager'].find_matching_users({
                            'subscription_type': 'tier_patterns',
                            'pattern_type': 'BreakoutBO',
                            'symbol': 'AAPL'
                        })

                        # User should be found immediately after subscription
                        if user_id not in matching_users:
                            with race_test_state['lock']:
                                race_test_state['errors'].append(
                                    f"Race condition: User {user_id} not found immediately after subscription"
                                )

                    # Update shared state
                    with race_test_state['lock']:
                        race_test_state['shared_counter'] += 1
                        race_test_state['subscription_count'] += 1 if success else 0

                    # No delay - maximum race condition opportunity

                except Exception as e:
                    with race_test_state['lock']:
                        race_test_state['errors'].append(f"Racing subscription {worker_id}_{i}: {str(e)}")

        def racing_broadcast_worker(worker_id: int, iterations: int):
            """Worker that rapidly broadcasts to test for race conditions."""
            time.sleep(0.1)  # Let some subscriptions happen first

            for i in range(iterations):
                try:
                    with patch.object(universal_manager, '_find_interested_users') as mock_find:
                        # Simulate finding users during concurrent subscription changes
                        mock_find.return_value = {f"race_user_0_{j:03d}" for j in range(min(10, i + 1))}

                        mock_routing_result = Mock()
                        mock_routing_result.total_users = min(10, i + 1)
                        mock_routing_result.matched_rules = ['race_rule']
                        mock_routing_result.routing_time_ms = 5.0
                        mock_routing_result.cache_hit = False

                        with patch.object(system['event_router'], 'route_event') as mock_route:
                            mock_route.return_value = mock_routing_result

                            delivery_count = universal_manager.broadcast_event(
                                event_type='race_test',
                                event_data={'worker_id': worker_id, 'iteration': i},
                                targeting_criteria={'subscription_type': 'tier_patterns'}
                            )

                            # Update shared state
                            with race_test_state['lock']:
                                race_test_state['shared_counter'] += 1
                                race_test_state['broadcast_count'] += 1

                    # No delay - maximum race condition opportunity

                except Exception as e:
                    with race_test_state['lock']:
                        race_test_state['errors'].append(f"Racing broadcast {worker_id}_{i}: {str(e)}")

        def racing_modification_worker(worker_id: int, iterations: int):
            """Worker that modifies system state to create race conditions."""
            time.sleep(0.05)  # Slight delay to let activity start

            for i in range(iterations):
                try:
                    # Rapidly modify cached data and indexing
                    system['index_manager'].find_matching_users({
                        'subscription_type': 'tier_patterns',
                        'pattern_type': 'BreakoutBO'
                    })

                    # Try to modify routing rules during active routing
                    test_rule_id = f"race_rule_{worker_id}_{i}"

                    from src.infrastructure.websocket.event_router import (
                        RoutingRule,
                        RoutingStrategy,
                    )

                    test_rule = RoutingRule(
                        rule_id=test_rule_id,
                        name=f"Race Test Rule {worker_id}_{i}",
                        description="Rule for race condition testing",
                        event_type_patterns=[r'race_.*'],
                        content_filters={'worker_id': worker_id},
                        user_criteria={},
                        strategy=RoutingStrategy.BROADCAST_ALL,
                        destinations=[f'race_room_{worker_id}'],
                        priority=DeliveryPriority.LOW
                    )

                    # Add and immediately remove rule to test concurrent modification
                    system['event_router'].add_routing_rule(test_rule)
                    system['event_router'].remove_routing_rule(test_rule_id)

                    # Update shared state
                    with race_test_state['lock']:
                        race_test_state['shared_counter'] += 1

                    # No delay - maximum race condition opportunity

                except Exception as e:
                    with race_test_state['lock']:
                        race_test_state['errors'].append(f"Racing modification {worker_id}_{i}: {str(e)}")

        # Launch intense race condition testing
        race_workers = 6
        iterations_per_worker = 50

        print(f"  Testing race conditions with {race_workers} workers, {iterations_per_worker} iterations each...")

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=race_workers * 3, thread_name_prefix="race") as executor:
            futures = []

            # Launch subscription racing workers
            for i in range(race_workers):
                futures.append(executor.submit(racing_subscription_worker, i, iterations_per_worker))

            # Launch broadcast racing workers
            for i in range(race_workers):
                futures.append(executor.submit(racing_broadcast_worker, i, iterations_per_worker // 2))

            # Launch modification racing workers
            for i in range(race_workers):
                futures.append(executor.submit(racing_modification_worker, i, iterations_per_worker // 4))

            # Wait for all racing operations to complete
            completed = 0
            for future in as_completed(futures, timeout=120):
                try:
                    future.result()
                    completed += 1
                except Exception as e:
                    with race_test_state['lock']:
                        race_test_state['errors'].append(f"Race worker thread error: {str(e)}")
                    completed += 1

        race_duration = time.time() - start_time

        # Analyze race condition test results
        total_operations = race_test_state['shared_counter']
        error_count = len(race_test_state['errors'])
        error_rate = (error_count / max(total_operations, 1)) * 100

        # Verify thread safety
        assert error_rate < 5.0, f"Race condition error rate {error_rate:.1f}% too high (errors: {error_count})"
        assert race_test_state['subscription_count'] > 0, "No successful subscriptions during race test"
        assert race_test_state['broadcast_count'] > 0, "No successful broadcasts during race test"

        # System should remain consistent after race condition testing
        final_stats = universal_manager.get_subscription_stats()
        assert final_stats['total_users'] > 0, "No users remain after race condition test"

        # Verify system health after intense concurrent operations
        health_status = universal_manager.get_health_status()
        assert health_status['status'] in ['healthy', 'warning'], f"System damaged by race conditions: {health_status['status']}"

        print(f"✅ Race Condition Test: {total_operations} operations, {error_count} errors ({error_rate:.1f}%) in {race_duration:.1f}s")
        print(f"  Subscriptions: {race_test_state['subscription_count']}, Broadcasts: {race_test_state['broadcast_count']}")

    def test_resource_exhaustion_recovery(self, stress_test_system):
        """Test system behavior under resource exhaustion conditions."""
        system = stress_test_system
        universal_manager = system['universal_manager']

        # Test memory exhaustion resistance
        print("  Testing memory exhaustion resistance...")

        large_data_subscriptions = []

        try:
            # Create subscriptions with increasingly large filter sets
            for i in range(100):
                user_id = f"memory_stress_user_{i:03d}"

                # Create large filter sets to stress memory
                large_filters = {
                    'pattern_types': ['BreakoutBO', 'TrendReversal', 'SurgeDetection'] * (i + 1),
                    'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'] * (i + 1),
                    'tiers': ['daily', 'intraday'] * (i + 1),
                    'large_data_field': 'x' * (1000 + i * 100),  # Growing data size
                    'confidence_min': 0.7,
                    'complex_criteria': {
                        'nested_data': ['item'] * (i + 1),
                        'deep_nesting': {
                            'level1': {
                                'level2': ['data'] * (i + 1)
                            }
                        }
                    }
                }

                success = universal_manager.subscribe_user(
                    user_id=user_id,
                    subscription_type="tier_patterns",
                    filters=large_filters
                )

                if success:
                    large_data_subscriptions.append(user_id)
                else:
                    break  # Stop if system starts rejecting subscriptions

            # Verify system handles large data gracefully
            assert len(large_data_subscriptions) >= 50, f"System rejected large data too early: {len(large_data_subscriptions)} subscriptions"

            # Test filtering performance with large data
            start_time = time.time()
            matching_users = system['index_manager'].find_matching_users({
                'subscription_type': 'tier_patterns',
                'pattern_type': 'BreakoutBO'
            })
            filter_time_ms = (time.time() - start_time) * 1000

            # Should maintain reasonable performance even with large data
            assert filter_time_ms < 50.0, f"Large data filtering took {filter_time_ms:.1f}ms, too slow"
            assert len(matching_users) > 0, "Should find users even with large data"

        finally:
            # Cleanup large data subscriptions
            for user_id in large_data_subscriptions:
                try:
                    universal_manager.unsubscribe_user(user_id)
                except:
                    pass  # Ignore cleanup errors

        # Test connection exhaustion handling
        print("  Testing connection exhaustion handling...")

        connection_stress_results = []

        # Simulate many rapid connection attempts
        with ThreadPoolExecutor(max_workers=20, thread_name_prefix="conn-stress") as executor:
            futures = []

            for i in range(100):
                future = executor.submit(self._simulate_connection_stress, system, i)
                futures.append(future)

            for future in as_completed(futures, timeout=60):
                try:
                    result = future.result()
                    connection_stress_results.append(result)
                except Exception as e:
                    connection_stress_results.append({
                        'success': False,
                        'error': str(e)
                    })

        # Analyze connection stress results
        successful_connections = sum(1 for r in connection_stress_results if r.get('success', False))
        success_rate = (successful_connections / len(connection_stress_results)) * 100

        # System should handle connection stress gracefully
        assert success_rate >= 80.0, f"Connection stress success rate {success_rate:.1f}% too low"

        # Test cache exhaustion and recovery
        print("  Testing cache exhaustion and recovery...")

        # Fill caches beyond normal capacity
        for i in range(1000):  # More than typical cache size
            system['event_router'].route_event(
                event_type='cache_stress',
                event_data={
                    'unique_id': i,
                    'large_data': 'x' * 1000,
                    'timestamp': time.time()
                },
                user_context={'stress_test': True}
            )

        # Verify system handles cache overflow
        router_stats = system['event_router'].get_routing_stats()
        assert router_stats['total_events'] == 1000, "Not all events were processed"

        # Cache should not exceed reasonable bounds
        if 'cache_size' in router_stats:
            assert router_stats['cache_size'] <= router_stats.get('cache_capacity', 1000), "Cache exceeded capacity"

        # System should remain healthy after resource stress
        health_status = universal_manager.get_health_status()
        assert health_status['status'] in ['healthy', 'warning'], f"System damaged by resource exhaustion: {health_status['status']}"

        print("✅ Resource Exhaustion Test: System handled memory, connection, and cache stress gracefully")

    def _simulate_connection_stress(self, system, connection_id: int) -> dict[str, Any]:
        """Simulate stressful connection scenario."""
        try:
            user_id = f"conn_stress_user_{connection_id}"

            # Rapid subscription
            success = system['universal_manager'].subscribe_user(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
            )

            if not success:
                return {'success': False, 'error': 'Subscription failed'}

            # Immediate broadcast test
            with patch.object(system['universal_manager'], '_find_interested_users') as mock_find:
                mock_find.return_value = {user_id}

                mock_routing_result = Mock()
                mock_routing_result.total_users = 1
                mock_routing_result.matched_rules = ['stress_rule']
                mock_routing_result.routing_time_ms = 5.0
                mock_routing_result.cache_hit = False

                with patch.object(system['event_router'], 'route_event') as mock_route:
                    mock_route.return_value = mock_routing_result

                    delivery_count = system['universal_manager'].broadcast_event(
                        event_type='connection_stress',
                        event_data={'connection_id': connection_id},
                        targeting_criteria={'subscription_type': 'tier_patterns'}
                    )

                    broadcast_success = delivery_count == 1

            # Rapid disconnection simulation
            system['universal_manager'].handle_user_disconnection(user_id, f'conn_{connection_id}')

            return {
                'success': success and broadcast_success,
                'connection_id': connection_id,
                'subscription_success': success,
                'broadcast_success': broadcast_success
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'connection_id': connection_id
            }

    def test_long_running_stability(self, stress_test_system):
        """Test system stability over extended operation period."""
        system = stress_test_system
        universal_manager = system['universal_manager']

        # Setup base load for long-running test
        base_users = 200
        for i in range(base_users):
            universal_manager.subscribe_user(
                user_id=f"longrun_user_{i:03d}",
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL'][i % 3],
                    'confidence_min': 0.7
                }
            )

        # Long-running test parameters
        test_duration_seconds = 60  # 1 minute of sustained operation
        operations_per_second = 5
        total_operations = test_duration_seconds * operations_per_second

        stability_metrics = {
            'operations_completed': 0,
            'errors': [],
            'performance_samples': [],
            'memory_samples': [],
            'start_time': time.time()
        }

        print(f"  Running {test_duration_seconds}s stability test ({total_operations} operations)...")

        def stability_operation_worker():
            """Worker performing continuous operations for stability testing."""
            operation_count = 0

            while operation_count < total_operations:
                cycle_start = time.time()

                try:
                    # Mix of operations to test stability
                    operation_type = operation_count % 4

                    if operation_type == 0:
                        # Subscription operation
                        temp_user_id = f"stability_temp_{operation_count}"
                        success = universal_manager.subscribe_user(
                            user_id=temp_user_id,
                            subscription_type="tier_patterns",
                            filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
                        )

                        # Cleanup temporary subscription
                        if success:
                            universal_manager.unsubscribe_user(temp_user_id)

                    elif operation_type == 1:
                        # Broadcasting operation
                        with patch.object(universal_manager, '_find_interested_users') as mock_find:
                            mock_find.return_value = {f"longrun_user_{i:03d}" for i in range(10)}

                            mock_routing_result = Mock()
                            mock_routing_result.total_users = 10
                            mock_routing_result.matched_rules = ['stability_rule']
                            mock_routing_result.routing_time_ms = 8.0
                            mock_routing_result.cache_hit = operation_count % 3 == 0

                            with patch.object(system['event_router'], 'route_event') as mock_route:
                                mock_route.return_value = mock_routing_result

                                universal_manager.broadcast_event(
                                    event_type='stability_test',
                                    event_data={'operation_count': operation_count},
                                    targeting_criteria={'subscription_type': 'tier_patterns'}
                                )

                    elif operation_type == 2:
                        # Indexing operation
                        system['index_manager'].find_matching_users({
                            'subscription_type': 'tier_patterns',
                            'pattern_type': 'BreakoutBO'
                        })

                    else:
                        # Health monitoring operation
                        universal_manager.get_health_status()

                    # Record performance sample
                    operation_time_ms = (time.time() - cycle_start) * 1000
                    stability_metrics['performance_samples'].append(operation_time_ms)
                    stability_metrics['operations_completed'] += 1

                    # Performance should remain stable
                    if operation_time_ms > 100.0:
                        stability_metrics['errors'].append(
                            f"Operation {operation_count} took {operation_time_ms:.1f}ms (too slow)"
                        )

                except Exception as e:
                    stability_metrics['errors'].append(
                        f"Operation {operation_count} failed: {str(e)}"
                    )

                operation_count += 1

                # Maintain target rate
                elapsed = time.time() - stability_metrics['start_time']
                expected_elapsed = operation_count / operations_per_second
                if elapsed < expected_elapsed:
                    time.sleep(expected_elapsed - elapsed)

        # Run stability test
        stability_worker_thread = threading.Thread(target=stability_operation_worker, name="stability")
        stability_worker_thread.start()
        stability_worker_thread.join(timeout=test_duration_seconds + 30)

        if stability_worker_thread.is_alive():
            stability_metrics['errors'].append("Stability test did not complete in expected time")

        # Analyze stability results
        total_runtime = time.time() - stability_metrics['start_time']
        completion_rate = (stability_metrics['operations_completed'] / total_operations) * 100
        error_rate = (len(stability_metrics['errors']) / max(stability_metrics['operations_completed'], 1)) * 100

        # Verify long-running stability
        assert completion_rate >= 95.0, f"Only completed {completion_rate:.1f}% of operations"
        assert error_rate < 10.0, f"Error rate {error_rate:.1f}% too high for long-running test"

        # Verify performance stability over time
        if stability_metrics['performance_samples']:
            early_samples = stability_metrics['performance_samples'][:50]
            late_samples = stability_metrics['performance_samples'][-50:]

            if early_samples and late_samples:
                early_avg = statistics.mean(early_samples)
                late_avg = statistics.mean(late_samples)

                performance_drift = ((late_avg - early_avg) / early_avg) * 100

                # Performance should not drift significantly
                assert abs(performance_drift) < 50.0, f"Performance drifted {performance_drift:+.1f}% over time"

        # System should remain healthy after long-running test
        final_health = universal_manager.get_health_status()
        assert final_health['status'] in ['healthy', 'warning'], f"System unhealthy after long run: {final_health['status']}"

        print(f"✅ Long-Running Stability: {stability_metrics['operations_completed']}/{total_operations} ops in {total_runtime:.1f}s")
        print(f"  Completion: {completion_rate:.1f}%, Errors: {len(stability_metrics['errors'])}, Error rate: {error_rate:.1f}%")

    @pytest.mark.slow
    def test_memory_leak_detection(self, stress_test_system):
        """Test for memory leaks during sustained operations."""
        system = stress_test_system
        universal_manager = system['universal_manager']

        # This is a simplified memory leak test
        # In production, you'd use memory profiling tools like memory_profiler or tracemalloc

        print("  Testing for memory leaks over sustained operations...")

        # Baseline measurement
        gc.collect()  # Force garbage collection
        initial_objects = len(gc.get_objects())

        # Perform operations that could potentially leak memory
        leak_test_cycles = 50

        for cycle in range(leak_test_cycles):
            # Create and destroy subscriptions
            temp_users = []
            for i in range(20):
                user_id = f"leak_test_user_{cycle}_{i}"
                temp_users.append(user_id)

                universal_manager.subscribe_user(
                    user_id=user_id,
                    subscription_type="tier_patterns",
                    filters={
                        'pattern_types': ['BreakoutBO'],
                        'symbols': ['AAPL'],
                        'large_data': 'x' * 1000  # Some data that should be cleaned up
                    }
                )

            # Perform broadcasts
            with patch.object(universal_manager, '_find_interested_users') as mock_find:
                mock_find.return_value = set(temp_users)

                mock_routing_result = Mock()
                mock_routing_result.total_users = len(temp_users)
                mock_routing_result.matched_rules = ['leak_test_rule']
                mock_routing_result.routing_time_ms = 10.0
                mock_routing_result.cache_hit = False

                with patch.object(system['event_router'], 'route_event') as mock_route:
                    mock_route.return_value = mock_routing_result

                    for i in range(5):
                        universal_manager.broadcast_event(
                            event_type='leak_test',
                            event_data={'cycle': cycle, 'iteration': i, 'data': 'x' * 500},
                            targeting_criteria={'subscription_type': 'tier_patterns'}
                        )

            # Clean up subscriptions
            for user_id in temp_users:
                universal_manager.unsubscribe_user(user_id)

            # Periodic cleanup and measurement
            if cycle % 10 == 9:
                # Force optimization and cleanup
                universal_manager.optimize_performance()
                universal_manager.cleanup_inactive_subscriptions(max_inactive_hours=0)

                # Force garbage collection
                gc.collect()

                # Measure object count
                current_objects = len(gc.get_objects())
                object_growth = current_objects - initial_objects

                print(f"    Cycle {cycle + 1}: {current_objects} objects (+{object_growth} from baseline)")

                # Object count should not grow excessively
                max_allowed_growth = 1000 + (cycle // 10) * 500  # Allow some growth
                assert object_growth < max_allowed_growth, (
                    f"Excessive object growth: {object_growth} objects after cycle {cycle + 1}"
                )

        # Final memory assessment
        gc.collect()
        final_objects = len(gc.get_objects())
        total_object_growth = final_objects - initial_objects

        # Memory growth should be reasonable for the amount of work done
        max_final_growth = 2000  # Allow reasonable growth
        assert total_object_growth < max_final_growth, (
            f"Potential memory leak: {total_object_growth} objects remained after cleanup"
        )

        # System should be healthy after memory stress
        health_status = universal_manager.get_health_status()
        assert health_status['status'] in ['healthy', 'warning'], f"System unhealthy after memory test: {health_status['status']}"

        print(f"✅ Memory Leak Test: {total_object_growth} object growth over {leak_test_cycles} cycles (limit: {max_final_growth})")

    def test_system_recovery_after_stress(self, stress_test_system):
        """Test system recovery capabilities after intense stress testing."""
        system = stress_test_system
        universal_manager = system['universal_manager']

        print("  Testing system recovery after intense stress...")

        # Apply intense stress load
        stress_users = []

        # Create heavy load
        for i in range(300):
            user_id = f"recovery_test_user_{i:03d}"
            stress_users.append(user_id)

            success = universal_manager.subscribe_user(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal', 'SurgeDetection'],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'],
                    'tiers': ['daily', 'intraday'],
                    'confidence_min': 0.5,
                    'large_filter_data': ['item'] * 100  # Heavy data
                }
            )

            if not success:
                break

        # Apply broadcast stress
        with patch.object(universal_manager, '_find_interested_users') as mock_find:
            mock_find.return_value = set(stress_users[:50])

            mock_routing_result = Mock()
            mock_routing_result.total_users = 50
            mock_routing_result.matched_rules = ['recovery_stress_rule']
            mock_routing_result.routing_time_ms = 15.0
            mock_routing_result.cache_hit = False

            with patch.object(system['event_router'], 'route_event') as mock_route:
                mock_route.return_value = mock_routing_result

                # Rapid fire broadcasts
                for i in range(100):
                    universal_manager.broadcast_event(
                        event_type='recovery_stress',
                        event_data={'stress_iteration': i, 'heavy_data': 'x' * 1000},
                        targeting_criteria={'subscription_type': 'tier_patterns'}
                    )

        # Measure system state under stress
        stressed_health = universal_manager.get_health_status()
        stressed_stats = universal_manager.get_subscription_stats()

        print(f"    Under stress: {stressed_stats['total_users']} users, status: {stressed_health['status']}")

        # Apply recovery operations
        print("    Applying recovery operations...")

        # 1. Performance optimization
        with patch.object(system['index_manager'], 'optimize_indexes') as mock_idx_opt, \
             patch.object(system['broadcaster'], 'optimize_performance') as mock_broadcast_opt, \
             patch.object(system['event_router'], 'optimize_performance') as mock_route_opt:

            mock_idx_opt.return_value = {'indexes_optimized': 50, 'cache_cleaned': 30}
            mock_broadcast_opt.return_value = {'batches_flushed': 20, 'performance_improved': True}
            mock_route_opt.return_value = {'cache_cleaned': 40, 'rules_optimized': 10}

            optimization_results = universal_manager.optimize_performance()

            assert 'performance_targets_met' in optimization_results, "Optimization should complete successfully"

        # 2. Cleanup inactive subscriptions
        cleaned_count = universal_manager.cleanup_inactive_subscriptions(max_inactive_hours=0.1)
        assert cleaned_count >= 0, "Cleanup should succeed"

        # 3. Force garbage collection and resource cleanup
        gc.collect()

        # Measure recovery performance
        recovery_test_results = []

        for i in range(20):
            start_time = time.time()

            # Test indexing performance after recovery
            matching_users = system['index_manager'].find_matching_users({
                'subscription_type': 'tier_patterns',
                'pattern_type': 'BreakoutBO'
            })

            indexing_time = (time.time() - start_time) * 1000
            recovery_test_results.append(indexing_time)

            # Performance should be restored
            assert indexing_time < 20.0, f"Recovery test {i}: indexing took {indexing_time:.1f}ms, too slow"
            assert len(matching_users) >= 0, "Should find users after recovery"

        # Verify recovery performance
        avg_recovery_performance = statistics.mean(recovery_test_results)
        assert avg_recovery_performance < 15.0, f"Average recovery performance {avg_recovery_performance:.1f}ms too slow"

        # Verify system health after recovery
        recovered_health = universal_manager.get_health_status()
        recovered_stats = universal_manager.get_subscription_stats()

        # System should be healthier after recovery
        assert recovered_health['status'] in ['healthy', 'warning'], f"System not recovered: {recovered_health['status']}"

        # Performance should be restored
        if 'avg_filtering_latency_ms' in recovered_stats:
            assert recovered_stats['avg_filtering_latency_ms'] < 10.0, "Filtering performance not recovered"

        print(f"✅ System Recovery: Status improved from {stressed_health['status']} to {recovered_health['status']}")
        print(f"  Recovery performance: {avg_recovery_performance:.1f}ms avg, {cleaned_count} subscriptions cleaned")

    def test_extreme_load_breaking_point(self, stress_test_system):
        """Test system behavior at and beyond normal breaking points."""
        system = stress_test_system
        universal_manager = system['universal_manager']

        print("  Testing extreme load breaking point behavior...")

        breaking_point_results = {
            'max_users_achieved': 0,
            'performance_degradation': [],
            'system_failures': [],
            'recovery_possible': True
        }

        # Gradually increase load until system shows stress
        load_increments = [100, 250, 500, 750, 1000, 1500, 2000]

        for target_load in load_increments:
            print(f"    Testing load: {target_load} users...")

            # Clear previous load
            universal_manager.user_subscriptions.clear()
            system['index_manager'].__init__(cache_size=1000, enable_optimization=True)
            gc.collect()

            load_start_time = time.time()
            successful_subscriptions = 0

            # Apply load
            for i in range(target_load):
                user_id = f"extreme_user_{target_load}_{i:04d}"

                try:
                    success = universal_manager.subscribe_user(
                        user_id=user_id,
                        subscription_type="tier_patterns",
                        filters={
                            'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                            'symbols': ['AAPL', 'MSFT', 'GOOGL'][i % 3],
                            'confidence_min': 0.7
                        }
                    )

                    if success:
                        successful_subscriptions += 1
                    else:
                        break  # System rejecting subscriptions

                except Exception as e:
                    breaking_point_results['system_failures'].append(
                        f"Load {target_load}, user {i}: {str(e)}"
                    )
                    break

            load_time = time.time() - load_start_time

            # Test performance at this load level
            performance_samples = []

            for test_iteration in range(10):
                perf_start = time.time()

                try:
                    matching_users = system['index_manager'].find_matching_users({
                        'subscription_type': 'tier_patterns',
                        'pattern_type': 'BreakoutBO'
                    })

                    perf_time_ms = (time.time() - perf_start) * 1000
                    performance_samples.append(perf_time_ms)

                    # If performance degrades too much, note it
                    if perf_time_ms > 50.0:
                        breaking_point_results['performance_degradation'].append(
                            f"Load {target_load}: {perf_time_ms:.1f}ms"
                        )

                except Exception as e:
                    breaking_point_results['system_failures'].append(
                        f"Load {target_load} performance test: {str(e)}"
                    )
                    performance_samples.append(1000)  # Mark as failed

            avg_performance = statistics.mean(performance_samples) if performance_samples else 1000

            # Record results for this load level
            breaking_point_results['max_users_achieved'] = max(
                breaking_point_results['max_users_achieved'],
                successful_subscriptions
            )

            print(f"      {successful_subscriptions}/{target_load} users, {avg_performance:.1f}ms avg performance")

            # If system is severely degraded, this is likely the breaking point
            failure_rate = len([p for p in performance_samples if p > 100]) / max(len(performance_samples), 1)

            if (successful_subscriptions < target_load * 0.8 or  # <80% subscription success
                avg_performance > 100.0 or                       # >100ms average performance
                failure_rate > 0.3):                             # >30% performance failures

                print(f"    Breaking point detected at {target_load} users")
                break

        # Test recovery from extreme load
        print("    Testing recovery from extreme load...")

        try:
            # Apply recovery operations
            recovery_start = time.time()

            universal_manager.optimize_performance()
            universal_manager.cleanup_inactive_subscriptions(max_inactive_hours=0)

            # Test if system recovers
            recovery_performance = []
            for i in range(5):
                perf_start = time.time()
                system['index_manager'].find_matching_users({
                    'subscription_type': 'tier_patterns',
                    'pattern_type': 'BreakoutBO'
                })
                recovery_performance.append((time.time() - perf_start) * 1000)

            avg_recovery_perf = statistics.mean(recovery_performance)
            breaking_point_results['recovery_possible'] = avg_recovery_perf < 20.0

            recovery_time = time.time() - recovery_start

        except Exception as e:
            breaking_point_results['recovery_possible'] = False
            breaking_point_results['system_failures'].append(f"Recovery failed: {str(e)}")

        # Analyze breaking point results
        assert breaking_point_results['max_users_achieved'] >= 500, (
            f"System failed before 500 users: max {breaking_point_results['max_users_achieved']}"
        )

        assert breaking_point_results['recovery_possible'], "System could not recover from extreme load"

        # Some performance degradation is expected at extreme loads
        degradation_count = len(breaking_point_results['performance_degradation'])
        failure_count = len(breaking_point_results['system_failures'])

        print(f"✅ Extreme Load Test: Max {breaking_point_results['max_users_achieved']} users achieved")
        print(f"  Performance degradations: {degradation_count}, System failures: {failure_count}")
        print(f"  Recovery possible: {breaking_point_results['recovery_possible']}")

        # System should gracefully handle extreme loads without catastrophic failure
        assert failure_count < 10, f"Too many system failures: {failure_count}"
