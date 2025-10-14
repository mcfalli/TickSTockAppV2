"""
Test ScalableBroadcaster Error Handling and Resilience
Sprint 25 Day 3 Tests: Error handling and resilience validation for broadcasting system.

Tests error handling and resilience including:
- SocketIO delivery failures with proper error handling
- Batch creation errors with graceful degradation
- Thread pool exhaustion with proper queuing behavior
- Resource cleanup with no memory leaks during extended operation
- Network failures and connection issues recovery
"""

import gc
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.infrastructure.websocket.scalable_broadcaster import (
    DeliveryPriority,
    ScalableBroadcaster,
)


class TestSocketIODeliveryFailures:
    """Test error handling for SocketIO delivery failures."""

    @pytest.fixture
    def failing_socketio(self):
        """Mock SocketIO that simulates various failure scenarios."""
        socketio = Mock()
        socketio.server = Mock()

        # Failure simulation controls
        socketio._failure_rate = 0.0
        socketio._failure_type = 'exception'
        socketio._call_count = 0
        socketio._failure_calls = []

        def simulate_failures(*args, **kwargs):
            socketio._call_count += 1

            # Determine if this call should fail
            should_fail = random.random() < socketio._failure_rate

            if should_fail:
                socketio._failure_calls.append(socketio._call_count)

                if socketio._failure_type == 'exception':
                    raise Exception("Simulated SocketIO delivery failure")
                if socketio._failure_type == 'timeout':
                    raise TimeoutError("SocketIO delivery timeout")
                if socketio._failure_type == 'connection_error':
                    raise ConnectionError("SocketIO connection lost")
                if socketio._failure_type == 'memory_error':
                    raise MemoryError("Insufficient memory for delivery")

            return True  # Success case

        socketio.emit = Mock(side_effect=simulate_failures)
        return socketio

    @pytest.fixture
    def resilient_broadcaster(self, failing_socketio):
        """Create ScalableBroadcaster for resilience testing."""
        return ScalableBroadcaster(
            socketio=failing_socketio,
            batch_window_ms=50,  # Short window for testing
            max_events_per_user=100,
            max_batch_size=25
        )

    def test_socketio_delivery_exception_handling(self, resilient_broadcaster, failing_socketio):
        """Test handling of SocketIO delivery exceptions."""
        # Set 30% failure rate
        failing_socketio._failure_rate = 0.3
        failing_socketio._failure_type = 'exception'

        num_events = 100
        user_ids = {'resilient_user_1', 'resilient_user_2', 'resilient_user_3'}

        events_sent = 0

        # Send events that will experience failures
        for i in range(num_events):
            try:
                delivered = resilient_broadcaster.broadcast_to_users(
                    event_type=f'exception_test_{i}',
                    event_data={
                        'sequence': i,
                        'timestamp': time.time(),
                        'failure_test': 'socketio_exceptions'
                    },
                    user_ids=user_ids,
                    priority=DeliveryPriority.MEDIUM
                )
                events_sent += 1

            except Exception as e:
                # Should not propagate exceptions to caller
                pytest.fail(f"Exception propagated to caller: {e}")

        # Force delivery to trigger SocketIO calls
        resilient_broadcaster.flush_all_batches()
        time.sleep(0.2)  # Allow async delivery

        # Verify error handling
        assert events_sent == num_events  # All events should be accepted
        assert len(failing_socketio._failure_calls) > 0  # Some failures should have occurred

        # Check error statistics
        stats = resilient_broadcaster.get_broadcast_stats()
        assert stats['total_events'] == num_events

        # System should remain functional despite failures
        health = resilient_broadcaster.get_health_status()
        assert health['status'] in ['healthy', 'warning']  # Should not be in error state

    def test_socketio_timeout_resilience(self, resilient_broadcaster, failing_socketio):
        """Test resilience to SocketIO timeout errors."""
        failing_socketio._failure_rate = 0.2  # 20% timeout rate
        failing_socketio._failure_type = 'timeout'

        events_with_timeouts = []

        def timeout_test_worker(worker_id: int) -> dict[str, Any]:
            """Worker that sends events during timeout scenarios."""
            worker_result = {
                'worker_id': worker_id,
                'events_sent': 0,
                'successes': 0,
                'errors': 0
            }

            for i in range(20):
                try:
                    delivered = resilient_broadcaster.broadcast_to_users(
                        event_type=f'timeout_test_{worker_id}_{i}',
                        event_data={
                            'worker_id': worker_id,
                            'sequence': i,
                            'timeout_test': True
                        },
                        user_ids={f'timeout_user_{worker_id}'},
                        priority=DeliveryPriority.MEDIUM
                    )

                    worker_result['events_sent'] += 1
                    if delivered > 0:
                        worker_result['successes'] += 1

                except Exception:
                    worker_result['errors'] += 1

            return worker_result

        # Run multiple workers to increase timeout likelihood
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(timeout_test_worker, i) for i in range(10)]

            results = []
            for future in as_completed(futures):
                results.append(future.result())

        # Force delivery to trigger timeouts
        resilient_broadcaster.flush_all_batches()
        time.sleep(0.5)

        # Analyze timeout resilience
        total_events_sent = sum(r['events_sent'] for r in results)
        total_successes = sum(r['successes'] for r in results)
        total_caller_errors = sum(r['errors'] for r in results)

        # Timeout resilience assertions
        assert total_events_sent == 200  # All events should be accepted by broadcaster
        assert total_caller_errors == 0  # No errors should propagate to callers
        assert len(failing_socketio._failure_calls) > 0  # Some timeouts should occur

        # Broadcaster should track errors internally
        broadcaster_stats = resilient_broadcaster.get_broadcast_stats()
        assert broadcaster_stats['total_events'] >= total_events_sent

    def test_socketio_connection_error_recovery(self, resilient_broadcaster, failing_socketio):
        """Test recovery from SocketIO connection errors."""
        # Start with high failure rate, then reduce (simulating recovery)
        failing_socketio._failure_rate = 0.8  # 80% initial failure rate
        failing_socketio._failure_type = 'connection_error'

        phase_1_events = 30
        phase_2_events = 30

        # Phase 1: High failure rate (connection issues)
        for i in range(phase_1_events):
            resilient_broadcaster.broadcast_to_users(
                event_type=f'connection_error_phase1_{i}',
                event_data={'phase': 1, 'sequence': i},
                user_ids={'recovery_user'},
                priority=DeliveryPriority.MEDIUM
            )

        resilient_broadcaster.flush_all_batches()
        time.sleep(0.1)

        phase_1_failures = len(failing_socketio._failure_calls)

        # Phase 2: Simulate connection recovery
        failing_socketio._failure_rate = 0.1  # 10% failure rate (mostly recovered)

        for i in range(phase_2_events):
            resilient_broadcaster.broadcast_to_users(
                event_type=f'connection_error_phase2_{i}',
                event_data={'phase': 2, 'sequence': i},
                user_ids={'recovery_user'},
                priority=DeliveryPriority.MEDIUM
            )

        resilient_broadcaster.flush_all_batches()
        time.sleep(0.1)

        total_failures = len(failing_socketio._failure_calls)
        phase_2_failures = total_failures - phase_1_failures

        # Recovery assertions
        assert phase_1_failures > phase_2_failures  # Should have fewer failures after recovery
        assert total_failures > 0  # Some failures should have occurred

        # System should handle recovery gracefully
        final_stats = resilient_broadcaster.get_broadcast_stats()
        assert final_stats['total_events'] == phase_1_events + phase_2_events

        # Health should improve after recovery
        health = resilient_broadcaster.get_health_status()
        assert health['status'] in ['healthy', 'warning']


class TestBatchCreationErrorHandling:
    """Test error handling in batch creation and management."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for batch error testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio

    @pytest.fixture
    def broadcaster_with_batch_errors(self, mock_socketio):
        """Create broadcaster that can simulate batch errors."""
        broadcaster = ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=100,
            max_events_per_user=150,
            max_batch_size=20
        )
        return broadcaster

    def test_batch_creation_memory_errors(self, broadcaster_with_batch_errors):
        """Test handling of memory errors during batch creation."""

        # Patch batch creation to occasionally fail with memory error
        original_create_batch = broadcaster_with_batch_errors._create_new_batch

        def memory_limited_batch_creation(room_name, event_message):
            """Simulate memory errors in batch creation."""
            if 'memory_stress' in room_name and random.random() < 0.3:
                raise MemoryError("Insufficient memory for batch creation")
            return original_create_batch(room_name, event_message)

        with patch.object(broadcaster_with_batch_errors, '_create_new_batch',
                         side_effect=memory_limited_batch_creation):

            successful_broadcasts = 0
            failed_broadcasts = 0

            # Attempt to create batches under memory stress
            for i in range(50):
                try:
                    delivered = broadcaster_with_batch_errors.broadcast_to_room(
                        room_name=f'memory_stress_room_{i % 5}',
                        event_type=f'memory_stress_event_{i}',
                        event_data={
                            'sequence': i,
                            'memory_test': True,
                            'large_data': 'x' * 1000  # 1KB per event
                        },
                        priority=DeliveryPriority.MEDIUM
                    )

                    if delivered:
                        successful_broadcasts += 1
                    else:
                        failed_broadcasts += 1

                except Exception as e:
                    # Should not propagate memory errors
                    pytest.fail(f"Memory error propagated: {e}")

            # Memory error handling assertions
            assert successful_broadcasts + failed_broadcasts == 50
            assert successful_broadcasts > 0  # Some should succeed

            # Check error tracking
            stats = broadcaster_with_batch_errors.get_broadcast_stats()
            assert isinstance(stats, dict)  # Should still provide stats

    def test_batch_timer_creation_failures(self, broadcaster_with_batch_errors):
        """Test handling of timer creation failures."""

        # Patch threading.Timer to occasionally fail
        original_timer = threading.Timer

        def unreliable_timer(*args, **kwargs):
            """Simulate timer creation failures."""
            if random.random() < 0.2:  # 20% failure rate
                raise RuntimeError("Timer creation failed")
            return original_timer(*args, **kwargs)

        with patch('threading.Timer', side_effect=unreliable_timer):

            timer_successes = 0
            timer_failures = 0

            # Attempt to create batches that require timers
            for i in range(30):
                try:
                    result = broadcaster_with_batch_errors.broadcast_to_room(
                        room_name=f'timer_test_room_{i}',
                        event_type=f'timer_test_event_{i}',
                        event_data={'sequence': i, 'timer_test': True},
                        priority=DeliveryPriority.MEDIUM
                    )

                    if result:
                        timer_successes += 1
                    else:
                        timer_failures += 1

                except Exception as e:
                    pytest.fail(f"Timer creation error propagated: {e}")

            # Timer failure handling assertions
            assert timer_successes + timer_failures == 30
            assert timer_successes > timer_failures  # Most should succeed despite timer issues

            # System should remain stable
            health = broadcaster_with_batch_errors.get_health_status()
            assert health['status'] in ['healthy', 'warning', 'error']  # Should not crash

    def test_batch_size_overflow_handling(self, broadcaster_with_batch_errors):
        """Test handling of batch size overflow conditions."""
        # Set very small batch size to force overflow
        broadcaster_with_batch_errors.max_batch_size = 3

        room_name = 'overflow_test_room'
        overflow_events = 20

        # Send many events to same room to force overflow handling
        for i in range(overflow_events):
            result = broadcaster_with_batch_errors.broadcast_to_room(
                room_name=room_name,
                event_type=f'overflow_event_{i}',
                event_data={
                    'sequence': i,
                    'overflow_test': True,
                    'data': 'x' * 100  # Add some size
                },
                priority=DeliveryPriority.MEDIUM
            )

            assert result == True  # Should handle overflow gracefully

        # Force delivery to complete overflow handling
        broadcaster_with_batch_errors.flush_all_batches()
        time.sleep(0.2)

        # Verify overflow handling
        stats = broadcaster_with_batch_errors.get_broadcast_stats()
        assert stats['total_events'] == overflow_events
        assert stats['batches_created'] > 1  # Should create multiple batches due to overflow

        # Check that system handled overflow without errors
        health = broadcaster_with_batch_errors.get_health_status()
        assert health['status'] in ['healthy', 'warning']

    def test_concurrent_batch_corruption_prevention(self, broadcaster_with_batch_errors):
        """Test prevention of batch corruption under concurrent access."""
        shared_room = 'corruption_test_room'
        num_workers = 15
        events_per_worker = 10

        corruption_detected = threading.Event()

        def batch_corruption_worker(worker_id: int) -> dict[str, Any]:
            """Worker that attempts to create batches concurrently."""
            worker_result = {
                'worker_id': worker_id,
                'events_sent': 0,
                'batch_ids_observed': set(),
                'corruption_indicators': []
            }

            for i in range(events_per_worker):
                try:
                    # All workers target same room to test corruption prevention
                    result = broadcaster_with_batch_errors.broadcast_to_room(
                        room_name=shared_room,
                        event_type=f'corruption_test_{worker_id}_{i}',
                        event_data={
                            'worker_id': worker_id,
                            'sequence': i,
                            'thread_id': threading.current_thread().ident,
                            'timestamp': time.time()
                        },
                        priority=DeliveryPriority.MEDIUM
                    )

                    if result:
                        worker_result['events_sent'] += 1

                    # Check for batch consistency (thread-safe read)
                    with broadcaster_with_batch_errors.broadcast_lock:
                        if shared_room in broadcaster_with_batch_errors.pending_batches:
                            batch = broadcaster_with_batch_errors.pending_batches[shared_room]
                            worker_result['batch_ids_observed'].add(batch.batch_id)

                            # Check for corruption indicators
                            if len(batch.events) > broadcaster_with_batch_errors.max_batch_size:
                                worker_result['corruption_indicators'].append('oversized_batch')

                            if not all(hasattr(event, 'event_type') for event in batch.events):
                                worker_result['corruption_indicators'].append('malformed_events')

                except Exception as e:
                    worker_result['corruption_indicators'].append(f'exception: {str(e)}')

            return worker_result

        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(batch_corruption_worker, i)
                for i in range(num_workers)
            ]

            results = []
            for future in as_completed(futures):
                results.append(future.result())

        # Analyze corruption prevention
        total_events_sent = sum(r['events_sent'] for r in results)
        all_corruption_indicators = []
        for result in results:
            all_corruption_indicators.extend(result['corruption_indicators'])

        expected_events = num_workers * events_per_worker

        # Corruption prevention assertions
        assert total_events_sent >= expected_events * 0.95  # At least 95% success
        assert len(all_corruption_indicators) == 0  # No corruption should be detected

        # Final state should be consistent
        stats = broadcaster_with_batch_errors.get_broadcast_stats()
        assert stats['total_events'] >= total_events_sent


class TestThreadPoolExhaustionHandling:
    """Test handling of thread pool exhaustion scenarios."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for thread pool testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio

    @pytest.fixture
    def limited_thread_broadcaster(self, mock_socketio):
        """Create broadcaster with limited thread pools."""
        broadcaster = ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=200,  # Longer window to increase thread usage
            max_events_per_user=300,
            max_batch_size=15
        )

        # Replace with smaller thread pools for testing
        broadcaster.batch_executor.shutdown()
        broadcaster.delivery_executor.shutdown()

        broadcaster.batch_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="limited-batch")
        broadcaster.delivery_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="limited-delivery")

        return broadcaster

    def test_thread_pool_exhaustion_queuing(self, limited_thread_broadcaster):
        """Test proper queuing when thread pools are exhausted."""
        num_users = 50
        events_per_user = 10

        # Generate load that will exhaust small thread pools
        exhaustion_start = time.time()

        def thread_exhaustion_worker(worker_id: int) -> dict[str, Any]:
            """Worker that creates thread pool exhaustion."""
            worker_result = {
                'worker_id': worker_id,
                'events_sent': 0,
                'queue_delays': [],
                'errors': 0
            }

            for i in range(events_per_user):
                event_start = time.time()

                try:
                    delivered = limited_thread_broadcaster.broadcast_to_users(
                        event_type=f'exhaustion_test_{worker_id}_{i}',
                        event_data={
                            'worker_id': worker_id,
                            'sequence': i,
                            'timestamp': time.time()
                        },
                        user_ids={f'exhaustion_user_{worker_id}'},
                        priority=DeliveryPriority.MEDIUM
                    )

                    queue_delay = time.time() - event_start
                    worker_result['events_sent'] += 1
                    worker_result['queue_delays'].append(queue_delay)

                except Exception:
                    worker_result['errors'] += 1

                # Small delay to create sustained load
                time.sleep(0.01)

            return worker_result

        # Create load that exceeds thread pool capacity
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(thread_exhaustion_worker, i)
                for i in range(num_users)
            ]

            results = []
            for future in as_completed(futures):
                results.append(future.result())

        exhaustion_duration = time.time() - exhaustion_start

        # Force all queued work to complete
        limited_thread_broadcaster.flush_all_batches()
        time.sleep(2.0)  # Allow queued work to complete

        # Analyze thread exhaustion handling
        total_events_sent = sum(r['events_sent'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        all_queue_delays = []
        for result in results:
            all_queue_delays.extend(result['queue_delays'])

        avg_queue_delay = sum(all_queue_delays) / len(all_queue_delays) if all_queue_delays else 0
        max_queue_delay = max(all_queue_delays) if all_queue_delays else 0

        expected_events = num_users * events_per_user

        # Thread exhaustion handling assertions
        assert total_events_sent >= expected_events * 0.90  # At least 90% should eventually process
        assert total_errors <= expected_events * 0.10  # Less than 10% errors

        # Queue delays should be reasonable (work should eventually complete)
        assert avg_queue_delay < 5.0  # Average delay under 5 seconds
        assert max_queue_delay < 10.0  # Maximum delay under 10 seconds

        # System should remain responsive despite exhaustion
        health = limited_thread_broadcaster.get_health_status()
        assert health['status'] in ['healthy', 'warning', 'error']  # Should not hang

        print("Thread Exhaustion Results:")
        print(f"  Events processed: {total_events_sent}/{expected_events}")
        print(f"  Average queue delay: {avg_queue_delay:.2f}s")
        print(f"  Maximum queue delay: {max_queue_delay:.2f}s")

    def test_thread_pool_shutdown_graceful_handling(self, limited_thread_broadcaster):
        """Test graceful handling of thread pool shutdown scenarios."""

        # Start some background work
        background_events = 20

        for i in range(background_events):
            limited_thread_broadcaster.broadcast_to_users(
                event_type=f'background_event_{i}',
                event_data={'sequence': i, 'background': True},
                user_ids={f'background_user_{i % 5}'},
                priority=DeliveryPriority.MEDIUM
            )

        # Simulate unexpected shutdown during operation
        shutdown_start = time.time()

        try:
            limited_thread_broadcaster.shutdown()
            shutdown_duration = time.time() - shutdown_start
        except Exception as e:
            pytest.fail(f"Shutdown failed with exception: {e}")

        # Shutdown handling assertions
        assert shutdown_duration < 10.0  # Should complete within reasonable time

        # Thread pools should be shutdown
        assert limited_thread_broadcaster.batch_executor._shutdown
        assert limited_thread_broadcaster.delivery_executor._shutdown

        # Attempting operations after shutdown should be handled gracefully
        try:
            result = limited_thread_broadcaster.broadcast_to_users(
                event_type='post_shutdown_event',
                event_data={'post_shutdown': True},
                user_ids={'post_shutdown_user'},
                priority=DeliveryPriority.MEDIUM
            )
            # Should not crash, but may return 0 or False
            assert isinstance(result, (int, bool))

        except Exception as e:
            # Some exceptions during shutdown are acceptable
            assert 'shutdown' in str(e).lower() or 'closed' in str(e).lower()


class TestResourceCleanupAndMemoryLeaks:
    """Test resource cleanup and memory leak prevention."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for resource testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio

    @pytest.fixture
    def resource_broadcaster(self, mock_socketio):
        """Create broadcaster for resource testing."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=100,
            max_events_per_user=200,
            max_batch_size=30
        )

    def test_memory_leak_prevention_extended_operation(self, resource_broadcaster):
        """Test memory leak prevention during extended operation."""

        # Force garbage collection baseline
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Extended operation simulation
        cycles = 20
        events_per_cycle = 50
        users_per_cycle = 25

        for cycle in range(cycles):
            # Create diverse load each cycle
            user_ids = {f'memory_test_user_{cycle}_{i}' for i in range(users_per_cycle)}

            for event_num in range(events_per_cycle):
                resource_broadcaster.broadcast_to_users(
                    event_type=f'memory_test_cycle_{cycle}_event_{event_num}',
                    event_data={
                        'cycle': cycle,
                        'event_num': event_num,
                        'timestamp': time.time(),
                        'data_payload': 'x' * 500  # 500 bytes per event
                    },
                    user_ids=user_ids,
                    priority=DeliveryPriority.MEDIUM
                )

            # Periodic cleanup
            if cycle % 5 == 0:
                resource_broadcaster.flush_all_batches()
                resource_broadcaster.optimize_performance()
                gc.collect()  # Force garbage collection

            time.sleep(0.01)  # Brief pause between cycles

        # Final cleanup and measurement
        resource_broadcaster.flush_all_batches()
        resource_broadcaster.optimize_performance()
        gc.collect()

        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        # Memory leak prevention assertions
        assert object_growth < 10000  # Less than 10K new objects (reasonable for extended operation)

        # Check that internal structures are cleaned up
        stats = resource_broadcaster.get_broadcast_stats()
        assert stats['pending_batches'] < 100  # Should have minimal pending batches

        # Rate limiters should be reasonable
        assert len(resource_broadcaster.user_rate_limiters) <= cycles * users_per_cycle

        print("Memory Leak Test Results:")
        print(f"  Object growth: {object_growth} objects")
        print(f"  Pending batches: {stats['pending_batches']}")
        print(f"  Rate limiters: {len(resource_broadcaster.user_rate_limiters)}")

    def test_resource_cleanup_optimization_effectiveness(self, resource_broadcaster):
        """Test effectiveness of resource cleanup optimization."""

        # Create substantial resource usage
        num_users = 100
        events_per_user = 20

        # Phase 1: Create load
        for user_num in range(num_users):
            user_id = f'cleanup_user_{user_num}'

            for event_num in range(events_per_user):
                resource_broadcaster.broadcast_to_users(
                    event_type=f'cleanup_event_{event_num}',
                    event_data={
                        'user_num': user_num,
                        'event_num': event_num,
                        'timestamp': time.time()
                    },
                    user_ids={user_id},
                    priority=DeliveryPriority.MEDIUM
                )

        # Measure before optimization
        pre_optimization_stats = resource_broadcaster.get_broadcast_stats()
        pre_optimization_batches = pre_optimization_stats['pending_batches']
        pre_optimization_rate_limiters = len(resource_broadcaster.user_rate_limiters)

        # Run optimization
        optimization_start = time.time()
        optimization_result = resource_broadcaster.optimize_performance()
        optimization_duration = time.time() - optimization_start

        # Measure after optimization
        post_optimization_stats = resource_broadcaster.get_broadcast_stats()
        post_optimization_batches = post_optimization_stats['pending_batches']
        post_optimization_rate_limiters = len(resource_broadcaster.user_rate_limiters)

        # Optimization effectiveness assertions
        assert optimization_duration < 5.0  # Should complete quickly
        assert isinstance(optimization_result, dict)
        assert 'batches_flushed' in optimization_result
        assert 'rate_limiters_cleaned' in optimization_result

        # Resource cleanup should be effective
        assert post_optimization_batches <= pre_optimization_batches  # Should not increase

        # If optimization cleaned up rate limiters, count should decrease or stay same
        rate_limiter_change = pre_optimization_rate_limiters - post_optimization_rate_limiters
        assert rate_limiter_change >= 0  # Should not increase

        print("Resource Cleanup Results:")
        print(f"  Optimization duration: {optimization_duration:.2f}s")
        print(f"  Batches: {pre_optimization_batches} -> {post_optimization_batches}")
        print(f"  Rate limiters: {pre_optimization_rate_limiters} -> {post_optimization_rate_limiters}")
        print(f"  Rate limiters cleaned: {optimization_result.get('rate_limiters_cleaned', 0)}")

    def test_timer_cleanup_prevention_of_leaks(self, resource_broadcaster):
        """Test prevention of timer leaks during operation."""

        # Create many short-lived batches that create timers
        timer_test_rooms = 50

        for room_num in range(timer_test_rooms):
            room_name = f'timer_test_room_{room_num}'

            # Create batch with timer
            resource_broadcaster.broadcast_to_room(
                room_name=room_name,
                event_type=f'timer_test_event_{room_num}',
                event_data={
                    'room_num': room_num,
                    'timer_test': True,
                    'timestamp': time.time()
                },
                priority=DeliveryPriority.MEDIUM
            )

            # Immediately flush to trigger timer cleanup
            resource_broadcaster.flush_all_batches()
            time.sleep(0.001)  # Brief pause

        # Check timer cleanup
        active_timers = len(resource_broadcaster.batch_timers)

        # Timer leak prevention assertions
        assert active_timers < 10  # Should have very few active timers after flushing

        # Final cleanup
        resource_broadcaster.shutdown()
        assert len(resource_broadcaster.batch_timers) == 0  # All timers should be cleaned up


class TestNetworkFailureRecovery:
    """Test recovery from network failures and connection issues."""

    @pytest.fixture
    def network_failing_socketio(self):
        """Mock SocketIO that simulates network failures."""
        socketio = Mock()
        socketio.server = Mock()

        # Network failure simulation
        socketio._network_down = False
        socketio._intermittent_failures = False
        socketio._failure_count = 0

        def network_aware_emit(*args, **kwargs):
            if socketio._network_down:
                socketio._failure_count += 1
                raise ConnectionError("Network is down")
            if socketio._intermittent_failures and random.random() < 0.3:
                socketio._failure_count += 1
                raise ConnectionError("Intermittent network failure")
            return True

        socketio.emit = Mock(side_effect=network_aware_emit)
        return socketio

    @pytest.fixture
    def network_resilient_broadcaster(self, network_failing_socketio):
        """Create broadcaster for network resilience testing."""
        return ScalableBroadcaster(
            socketio=network_failing_socketio,
            batch_window_ms=100,
            max_events_per_user=200,
            max_batch_size=25
        )

    def test_network_outage_resilience(self, network_resilient_broadcaster, network_failing_socketio):
        """Test resilience during complete network outage."""

        # Phase 1: Normal operation
        normal_events = 20
        for i in range(normal_events):
            network_resilient_broadcaster.broadcast_to_users(
                event_type=f'normal_event_{i}',
                event_data={'sequence': i, 'phase': 'normal'},
                user_ids={'network_user'},
                priority=DeliveryPriority.MEDIUM
            )

        network_resilient_broadcaster.flush_all_batches()
        time.sleep(0.1)
        initial_failures = network_failing_socketio._failure_count

        # Phase 2: Network outage
        network_failing_socketio._network_down = True

        outage_events = 30
        outage_start = time.time()

        for i in range(outage_events):
            try:
                # Should continue to accept events during outage
                result = network_resilient_broadcaster.broadcast_to_users(
                    event_type=f'outage_event_{i}',
                    event_data={'sequence': i, 'phase': 'outage'},
                    user_ids={'network_user'},
                    priority=DeliveryPriority.MEDIUM
                )
                # Should not crash or raise exceptions to caller
                assert isinstance(result, int)

            except Exception as e:
                pytest.fail(f"Network outage caused caller exception: {e}")

        network_resilient_broadcaster.flush_all_batches()
        time.sleep(0.2)
        outage_failures = network_failing_socketio._failure_count - initial_failures

        # Phase 3: Network recovery
        network_failing_socketio._network_down = False

        recovery_events = 25
        for i in range(recovery_events):
            network_resilient_broadcaster.broadcast_to_users(
                event_type=f'recovery_event_{i}',
                event_data={'sequence': i, 'phase': 'recovery'},
                user_ids={'network_user'},
                priority=DeliveryPriority.MEDIUM
            )

        network_resilient_broadcaster.flush_all_batches()
        time.sleep(0.1)

        final_failures = network_failing_socketio._failure_count
        recovery_failures = final_failures - outage_failures - initial_failures

        # Network outage resilience assertions
        assert outage_failures > 0  # Should have experienced failures during outage
        assert recovery_failures < outage_failures  # Should have fewer failures after recovery

        # System should remain functional throughout
        final_stats = network_resilient_broadcaster.get_broadcast_stats()
        assert final_stats['total_events'] == normal_events + outage_events + recovery_events

        # Health should reflect network issues but not system failure
        health = network_resilient_broadcaster.get_health_status()
        assert health['status'] in ['healthy', 'warning', 'error']  # Should not crash

        print("Network Outage Test Results:")
        print(f"  Normal phase failures: {initial_failures}")
        print(f"  Outage phase failures: {outage_failures}")
        print(f"  Recovery phase failures: {recovery_failures}")

    def test_intermittent_network_issues(self, network_resilient_broadcaster, network_failing_socketio):
        """Test handling of intermittent network issues."""

        # Enable intermittent failures
        network_failing_socketio._intermittent_failures = True

        intermittent_test_duration = 3.0  # 3 seconds
        event_frequency = 10  # 10 events per second

        start_time = time.time()
        events_sent = 0

        while time.time() - start_time < intermittent_test_duration:
            cycle_start = time.time()

            try:
                result = network_resilient_broadcaster.broadcast_to_users(
                    event_type=f'intermittent_event_{events_sent}',
                    event_data={
                        'sequence': events_sent,
                        'timestamp': time.time(),
                        'intermittent_test': True
                    },
                    user_ids={'intermittent_user'},
                    priority=DeliveryPriority.MEDIUM
                )

                events_sent += 1

            except Exception as e:
                pytest.fail(f"Intermittent network issue caused exception: {e}")

            # Maintain frequency
            elapsed = time.time() - cycle_start
            sleep_time = (1.0 / event_frequency) - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        # Force delivery to complete intermittent failure testing
        network_resilient_broadcaster.flush_all_batches()
        time.sleep(0.5)

        intermittent_failures = network_failing_socketio._failure_count

        # Intermittent failure handling assertions
        assert events_sent >= event_frequency * intermittent_test_duration * 0.8  # At least 80% of target
        assert intermittent_failures > 0  # Should have experienced some failures

        # System should maintain reasonable performance despite intermittent issues
        stats = network_resilient_broadcaster.get_broadcast_stats()
        assert stats['total_events'] >= events_sent

        print("Intermittent Network Test Results:")
        print(f"  Events sent: {events_sent}")
        print(f"  Network failures: {intermittent_failures}")
        print(f"  Success rate: {(events_sent - intermittent_failures) / events_sent * 100:.1f}%")


if __name__ == '__main__':
    # Example of running error handling and resilience tests
    pytest.main([__file__ + "::TestSocketIODeliveryFailures::test_socketio_delivery_exception_handling", "-v", "-s"])
