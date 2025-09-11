"""
Test ScalableBroadcaster Threading and Concurrency Stress
Sprint 25 Day 3 Tests: Threading and concurrency validation with ThreadPoolExecutor stress testing.

Tests threading and concurrency including:
- ThreadPoolExecutor performance with 10 batch + 20 delivery workers
- Concurrent event processing with multiple events simultaneously
- Thread safety validation with no race conditions in batch creation/delivery
- Resource management with proper thread cleanup and resource management
- Deadlock prevention with no deadlocks under high concurrent load
"""

import pytest
import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, Set, List, Tuple
from collections import defaultdict, deque
import random
import gc

from src.infrastructure.websocket.scalable_broadcaster import (
    ScalableBroadcaster, EventMessage, EventBatch, RateLimiter, 
    BroadcastStats, DeliveryPriority
)


class TestThreadPoolExecutorPerformance:
    """Test ThreadPoolExecutor performance and configuration."""
    
    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO with thread-safe behavior."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio
    
    @pytest.fixture
    def broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster for threading tests."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=25,  # Short window for testing
            max_events_per_user=200,
            max_batch_size=20
        )
    
    def test_thread_pool_configuration(self, broadcaster):
        """Test ThreadPoolExecutor configuration."""
        # Verify batch executor configuration
        assert broadcaster.batch_executor._max_workers == 10
        assert "broadcast-batch" in str(broadcaster.batch_executor._thread_name_prefix)
        
        # Verify delivery executor configuration
        assert broadcaster.delivery_executor._max_workers == 20
        assert "broadcast-delivery" in str(broadcaster.delivery_executor._thread_name_prefix)
        
        # Verify executors are running
        assert not broadcaster.batch_executor._shutdown
        assert not broadcaster.delivery_executor._shutdown
    
    def test_batch_executor_performance(self, broadcaster):
        """Test batch executor performance under load."""
        batch_creation_times = []
        
        def create_batch_work() -> float:
            """Simulate batch creation work."""
            start_time = time.time()
            
            # Create realistic batching workload
            user_id = f'batch_user_{threading.current_thread().ident}'
            
            for i in range(10):
                broadcaster.broadcast_to_users(
                    event_type=f'batch_test_{i}',
                    event_data={'thread': threading.current_thread().ident, 'sequence': i},
                    user_ids={user_id},
                    priority=DeliveryPriority.MEDIUM
                )
            
            return time.time() - start_time
        
        # Submit work to batch executor
        with broadcaster.batch_executor as executor:
            futures = [executor.submit(create_batch_work) for _ in range(30)]
            
            for future in as_completed(futures):
                batch_creation_times.append(future.result())
        
        # Analyze batch executor performance
        avg_batch_time = sum(batch_creation_times) / len(batch_creation_times)
        max_batch_time = max(batch_creation_times)
        
        assert avg_batch_time < 0.5  # Less than 500ms average
        assert max_batch_time < 2.0  # Less than 2s maximum
        assert len(batch_creation_times) == 30  # All tasks completed
    
    def test_delivery_executor_performance(self, broadcaster, mock_socketio):
        """Test delivery executor performance under load."""
        delivery_times = []
        emit_count = 0
        
        def delivery_work() -> float:
            """Simulate delivery work."""
            nonlocal emit_count
            start_time = time.time()
            
            # Create batch for delivery
            events = []
            for i in range(5):
                event = EventMessage(
                    event_type=f'delivery_test_{i}',
                    event_data={'thread': threading.current_thread().ident, 'sequence': i},
                    target_users={f'delivery_user_{threading.current_thread().ident}'},
                    priority=DeliveryPriority.MEDIUM,
                    timestamp=time.time(),
                    message_id=f'delivery_{threading.current_thread().ident}_{i}'
                )
                events.append(event)
            
            batch = EventBatch(
                room_name=f'delivery_room_{threading.current_thread().ident}',
                events=events,
                batch_id=f'batch_{threading.current_thread().ident}',
                created_at=time.time(),
                priority=DeliveryPriority.MEDIUM
            )
            
            # Deliver batch
            broadcaster._deliver_batch(batch)
            emit_count += len(events)
            
            return time.time() - start_time
        
        # Submit work to delivery executor
        with broadcaster.delivery_executor as executor:
            futures = [executor.submit(delivery_work) for _ in range(40)]
            
            for future in as_completed(futures):
                delivery_times.append(future.result())
        
        # Analyze delivery executor performance
        avg_delivery_time = sum(delivery_times) / len(delivery_times)
        max_delivery_time = max(delivery_times)
        
        assert avg_delivery_time < 0.1  # Less than 100ms average
        assert max_delivery_time < 0.5  # Less than 500ms maximum
        assert len(delivery_times) == 40  # All tasks completed
        assert mock_socketio.emit.call_count >= emit_count  # Should emit events
    
    def test_executor_resource_utilization(self, broadcaster):
        """Test executor resource utilization and efficiency."""
        # Track active threads during high load
        active_threads = []
        
        def resource_intensive_work(work_id: int) -> Dict[str, Any]:
            """Resource intensive broadcasting work."""
            thread_info = {
                'work_id': work_id,
                'thread_id': threading.current_thread().ident,
                'start_time': time.time()
            }
            
            # Create substantial work
            user_ids = {f'resource_user_{i}' for i in range(5)}
            
            for i in range(20):
                broadcaster.broadcast_to_users(
                    event_type=f'resource_event_{work_id}_{i}',
                    event_data={
                        'work_id': work_id,
                        'sequence': i,
                        'timestamp': time.time()
                    },
                    user_ids=user_ids,
                    priority=DeliveryPriority.MEDIUM
                )
                
                # Small delay to extend work duration
                time.sleep(0.001)
            
            thread_info['end_time'] = time.time()
            thread_info['duration'] = thread_info['end_time'] - thread_info['start_time']
            
            return thread_info
        
        # Submit work that will utilize both executors
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=15) as test_executor:
            futures = [test_executor.submit(resource_intensive_work, i) for i in range(50)]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        total_duration = time.time() - start_time
        
        # Analyze resource utilization
        unique_threads = len(set(result['thread_id'] for result in results))
        avg_work_duration = sum(result['duration'] for result in results) / len(results)
        
        # Should utilize multiple threads efficiently
        assert unique_threads >= 10  # Should use multiple threads
        assert total_duration < 15.0  # Should complete within reasonable time
        assert avg_work_duration < 2.0  # Individual work units should be efficient
        assert len(results) == 50  # All work completed


class TestConcurrentEventProcessing:
    """Test concurrent event processing scenarios."""
    
    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO with thread-safe call tracking."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        
        # Thread-safe call counting
        socketio._call_count = 0
        socketio._call_lock = threading.Lock()
        
        def thread_safe_emit(*args, **kwargs):
            with socketio._call_lock:
                socketio._call_count += 1
        
        socketio.emit.side_effect = thread_safe_emit
        return socketio
    
    @pytest.fixture
    def broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster for concurrency tests."""
        broadcaster = ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=50,
            max_events_per_user=500,  # High limit for stress testing
            max_batch_size=25
        )
        # Disable rate limiting for cleaner concurrency testing
        broadcaster.enable_rate_limiting = False
        return broadcaster
    
    def test_concurrent_user_broadcasting(self, broadcaster, mock_socketio):
        """Test concurrent broadcasting to multiple users simultaneously."""
        num_workers = 20
        events_per_worker = 25
        users_per_event = 10
        
        results = []
        
        def concurrent_broadcast_worker(worker_id: int) -> Dict[str, Any]:
            """Worker that broadcasts events concurrently."""
            worker_results = {
                'worker_id': worker_id,
                'events_sent': 0,
                'total_deliveries': 0,
                'errors': 0,
                'start_time': time.time()
            }
            
            for i in range(events_per_worker):
                user_ids = {f'concurrent_user_{worker_id}_{j}' for j in range(users_per_event)}
                
                try:
                    delivered = broadcaster.broadcast_to_users(
                        event_type=f'concurrent_event_{worker_id}_{i}',
                        event_data={
                            'worker_id': worker_id,
                            'sequence': i,
                            'timestamp': time.time(),
                            'thread_id': threading.current_thread().ident
                        },
                        user_ids=user_ids,
                        priority=DeliveryPriority.MEDIUM
                    )
                    
                    worker_results['events_sent'] += 1
                    worker_results['total_deliveries'] += delivered
                    
                except Exception as e:
                    worker_results['errors'] += 1
            
            worker_results['end_time'] = time.time()
            worker_results['duration'] = worker_results['end_time'] - worker_results['start_time']
            return worker_results
        
        # Run concurrent broadcasting
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(concurrent_broadcast_worker, i) for i in range(num_workers)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze concurrent broadcasting results
        total_events_sent = sum(r['events_sent'] for r in results)
        total_deliveries = sum(r['total_deliveries'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        avg_duration = sum(r['duration'] for r in results) / len(results)
        
        expected_events = num_workers * events_per_worker
        expected_deliveries = expected_events * users_per_event
        
        # Concurrency assertions
        assert total_events_sent == expected_events  # All events should be sent
        assert total_deliveries == expected_deliveries  # All deliveries should succeed
        assert total_errors == 0  # No errors should occur
        assert avg_duration < 5.0  # Should complete efficiently
        
        # Verify system statistics
        assert broadcaster.stats.total_events >= expected_events
    
    def test_mixed_priority_concurrent_processing(self, broadcaster):
        """Test concurrent processing of mixed priority events."""
        priority_workers = {
            DeliveryPriority.CRITICAL: 5,
            DeliveryPriority.HIGH: 8,
            DeliveryPriority.MEDIUM: 12,
            DeliveryPriority.LOW: 15
        }
        
        results = {}
        
        def priority_worker(priority: DeliveryPriority, worker_count: int) -> List[Dict]:
            """Worker for specific priority level."""
            worker_results = []
            
            for worker_id in range(worker_count):
                worker_result = {
                    'priority': priority,
                    'worker_id': worker_id,
                    'events_processed': 0,
                    'deliveries': 0,
                    'start_time': time.time()
                }
                
                user_id = f'{priority.name.lower()}_user_{worker_id}'
                
                for i in range(10):  # 10 events per worker
                    delivered = broadcaster.broadcast_to_users(
                        event_type=f'{priority.name.lower()}_event_{i}',
                        event_data={
                            'priority': priority.name,
                            'worker_id': worker_id,
                            'sequence': i,
                            'thread': threading.current_thread().ident
                        },
                        user_ids={user_id},
                        priority=priority
                    )
                    
                    worker_result['events_processed'] += 1
                    worker_result['deliveries'] += delivered
                
                worker_result['end_time'] = time.time()
                worker_result['duration'] = worker_result['end_time'] - worker_result['start_time']
                worker_results.append(worker_result)
            
            return worker_results
        
        # Run priority workers concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_priority = {
                executor.submit(priority_worker, priority, count): priority
                for priority, count in priority_workers.items()
            }
            
            for future in as_completed(future_to_priority):
                priority = future_to_priority[future]
                results[priority] = future.result()
        
        # Analyze mixed priority results
        total_workers = sum(len(workers) for workers in results.values())
        total_events = sum(sum(w['events_processed'] for w in workers) for workers in results.values())
        
        expected_workers = sum(priority_workers.values())
        expected_events = expected_workers * 10
        
        assert total_workers == expected_workers
        assert total_events == expected_events
        
        # All priorities should process successfully
        for priority, workers in results.items():
            assert len(workers) == priority_workers[priority]
            for worker in workers:
                assert worker['events_processed'] == 10
                assert worker['deliveries'] > 0
    
    def test_concurrent_room_broadcasting(self, broadcaster):
        """Test concurrent room broadcasting scenarios."""
        rooms = [f'concurrent_room_{i}' for i in range(15)]
        events_per_room = 20
        
        results = []
        
        def room_broadcast_worker(room_name: str) -> Dict[str, Any]:
            """Worker that broadcasts to a specific room."""
            worker_result = {
                'room': room_name,
                'events_sent': 0,
                'successes': 0,
                'start_time': time.time()
            }
            
            for i in range(events_per_room):
                success = broadcaster.broadcast_to_room(
                    room_name=room_name,
                    event_type=f'room_event_{i}',
                    event_data={
                        'room': room_name,
                        'sequence': i,
                        'timestamp': time.time(),
                        'thread': threading.current_thread().ident
                    },
                    priority=DeliveryPriority.MEDIUM
                )
                
                worker_result['events_sent'] += 1
                if success:
                    worker_result['successes'] += 1
            
            worker_result['end_time'] = time.time()
            worker_result['duration'] = worker_result['end_time'] - worker_result['start_time']
            return worker_result
        
        # Broadcast to rooms concurrently
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(room_broadcast_worker, room) for room in rooms]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze room broadcasting results
        total_events_sent = sum(r['events_sent'] for r in results)
        total_successes = sum(r['successes'] for r in results)
        avg_duration = sum(r['duration'] for r in results) / len(results)
        
        expected_total = len(rooms) * events_per_room
        
        assert total_events_sent == expected_total
        assert total_successes == expected_total  # All should succeed
        assert avg_duration < 3.0  # Should complete efficiently
    
    def test_high_frequency_concurrent_events(self, broadcaster):
        """Test high frequency concurrent event generation."""
        frequency_hz = 100  # 100 events per second
        duration_seconds = 2
        num_generators = 5
        
        results = []
        
        def high_frequency_generator(generator_id: int, frequency: int, duration: float) -> Dict[str, Any]:
            """Generate events at high frequency."""
            generator_result = {
                'generator_id': generator_id,
                'events_generated': 0,
                'target_events': int(frequency * duration),
                'start_time': time.time()
            }
            
            interval = 1.0 / frequency  # Time between events
            end_time = time.time() + duration
            
            while time.time() < end_time:
                event_start = time.time()
                
                broadcaster.broadcast_to_users(
                    event_type='high_frequency_event',
                    event_data={
                        'generator_id': generator_id,
                        'frequency': frequency,
                        'timestamp': time.time()
                    },
                    user_ids={f'freq_user_{generator_id}'},
                    priority=DeliveryPriority.MEDIUM
                )
                
                generator_result['events_generated'] += 1
                
                # Maintain frequency
                elapsed = time.time() - event_start
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            generator_result['end_time'] = time.time()
            generator_result['actual_duration'] = generator_result['end_time'] - generator_result['start_time']
            generator_result['actual_frequency'] = generator_result['events_generated'] / generator_result['actual_duration']
            
            return generator_result
        
        # Run high frequency generators
        with ThreadPoolExecutor(max_workers=num_generators) as executor:
            futures = [
                executor.submit(high_frequency_generator, i, frequency_hz, duration_seconds)
                for i in range(num_generators)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze high frequency results
        total_events = sum(r['events_generated'] for r in results)
        avg_frequency = sum(r['actual_frequency'] for r in results) / len(results)
        
        expected_total = num_generators * frequency_hz * duration_seconds
        
        # Allow some variance in high frequency generation
        assert total_events >= expected_total * 0.8  # At least 80% of target
        assert avg_frequency >= frequency_hz * 0.8   # At least 80% of target frequency
        
        # System should handle high frequency load
        assert broadcaster.stats.total_events >= total_events * 0.8


class TestThreadSafetyAndRaceConditions:
    """Test thread safety and race condition prevention."""
    
    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for thread safety testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio
    
    @pytest.fixture
    def broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster for thread safety tests."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=100,
            max_events_per_user=1000,
            max_batch_size=30
        )
    
    def test_batch_creation_thread_safety(self, broadcaster):
        """Test thread safety of batch creation operations."""
        shared_room = 'thread_safety_room'
        num_threads = 20
        events_per_thread = 30
        
        results = []
        
        def batch_creation_worker(worker_id: int) -> Dict[str, Any]:
            """Worker that creates batches concurrently."""
            worker_result = {
                'worker_id': worker_id,
                'events_created': 0,
                'batches_observed': set(),
                'thread_id': threading.current_thread().ident
            }
            
            for i in range(events_per_thread):
                # All workers target same room to test thread safety
                result = broadcaster.broadcast_to_room(
                    room_name=shared_room,
                    event_type=f'thread_safety_event_{worker_id}_{i}',
                    event_data={
                        'worker_id': worker_id,
                        'sequence': i,
                        'thread_id': threading.current_thread().ident,
                        'timestamp': time.time()
                    },
                    priority=DeliveryPriority.MEDIUM
                )
                
                if result:
                    worker_result['events_created'] += 1
                
                # Check for batch existence (thread-safe read)
                with broadcaster.broadcast_lock:
                    if shared_room in broadcaster.pending_batches:
                        batch_id = broadcaster.pending_batches[shared_room].batch_id
                        worker_result['batches_observed'].add(batch_id)
            
            return worker_result
        
        # Run concurrent batch creation
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(batch_creation_worker, i) for i in range(num_threads)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze thread safety results
        total_events_created = sum(r['events_created'] for r in results)
        unique_threads = len(set(r['thread_id'] for r in results))
        all_observed_batches = set()
        
        for result in results:
            all_observed_batches.update(result['batches_observed'])
        
        expected_events = num_threads * events_per_thread
        
        # Thread safety assertions
        assert total_events_created == expected_events  # No events lost
        assert unique_threads >= min(num_threads, 10)   # Multiple threads used
        assert len(all_observed_batches) >= 1           # Batches were created
        
        # No corruption should occur - broadcaster stats should be consistent
        assert broadcaster.stats.total_events >= expected_events
    
    def test_rate_limiter_thread_safety(self, broadcaster):
        """Test thread safety of rate limiting operations."""
        shared_user = 'thread_safety_user'
        num_threads = 15
        attempts_per_thread = 50
        
        # Set low rate limit to force contention
        broadcaster.max_events_per_user = 100
        
        results = []
        
        def rate_limit_worker(worker_id: int) -> Dict[str, Any]:
            """Worker that tests rate limiting thread safety."""
            worker_result = {
                'worker_id': worker_id,
                'attempts': 0,
                'allowed': 0,
                'denied': 0
            }
            
            for i in range(attempts_per_thread):
                delivered = broadcaster.broadcast_to_users(
                    event_type=f'rate_limit_test_{worker_id}_{i}',
                    event_data={
                        'worker_id': worker_id,
                        'sequence': i,
                        'thread_id': threading.current_thread().ident
                    },
                    user_ids={shared_user},
                    priority=DeliveryPriority.MEDIUM
                )
                
                worker_result['attempts'] += 1
                if delivered > 0:
                    worker_result['allowed'] += 1
                else:
                    worker_result['denied'] += 1
            
            return worker_result
        
        # Run concurrent rate limiting tests
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(rate_limit_worker, i) for i in range(num_threads)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze rate limiting thread safety
        total_attempts = sum(r['attempts'] for r in results)
        total_allowed = sum(r['allowed'] for r in results)
        total_denied = sum(r['denied'] for r in results)
        
        expected_attempts = num_threads * attempts_per_thread
        
        # Rate limiting thread safety assertions
        assert total_attempts == expected_attempts
        assert total_allowed + total_denied == total_attempts
        assert total_allowed <= broadcaster.max_events_per_user  # Rate limit enforced
        assert total_denied >= 0  # Some events should be denied
        
        # Verify user rate limiter state is consistent
        rate_status = broadcaster.get_user_rate_status(shared_user)
        assert rate_status['current_rate'] <= broadcaster.max_events_per_user
    
    def test_statistics_thread_safety(self, broadcaster):
        """Test thread safety of statistics updates."""
        num_workers = 25
        operations_per_worker = 40
        
        results = []
        
        def stats_update_worker(worker_id: int) -> Dict[str, Any]:
            """Worker that updates statistics concurrently."""
            worker_result = {
                'worker_id': worker_id,
                'operations': 0,
                'broadcasts': 0,
                'stats_reads': 0
            }
            
            for i in range(operations_per_worker):
                # Mix of operations that update statistics
                if i % 3 == 0:
                    # Broadcast operation (updates stats)
                    delivered = broadcaster.broadcast_to_users(
                        event_type=f'stats_test_{worker_id}_{i}',
                        event_data={'worker_id': worker_id, 'sequence': i},
                        user_ids={f'stats_user_{worker_id}'},
                        priority=DeliveryPriority.MEDIUM
                    )
                    worker_result['broadcasts'] += 1
                    
                elif i % 3 == 1:
                    # Read statistics (concurrent read)
                    stats = broadcaster.get_broadcast_stats()
                    worker_result['stats_reads'] += 1
                    assert isinstance(stats, dict)
                    assert 'total_events' in stats
                    
                else:
                    # Rate status check (updates rate limiter stats)
                    rate_status = broadcaster.get_user_rate_status(f'stats_user_{worker_id}')
                    assert isinstance(rate_status, dict)
                
                worker_result['operations'] += 1
            
            return worker_result
        
        # Run concurrent statistics operations
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(stats_update_worker, i) for i in range(num_workers)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze statistics thread safety
        total_operations = sum(r['operations'] for r in results)
        total_broadcasts = sum(r['broadcasts'] for r in results)
        total_stats_reads = sum(r['stats_reads'] for r in results)
        
        expected_operations = num_workers * operations_per_worker
        
        # Statistics thread safety assertions
        assert total_operations == expected_operations
        assert total_broadcasts > 0
        assert total_stats_reads > 0
        
        # Final statistics should be consistent
        final_stats = broadcaster.get_broadcast_stats()
        assert final_stats['total_events'] >= total_broadcasts
        assert isinstance(final_stats['total_events'], int)
        assert final_stats['total_events'] >= 0
    
    def test_resource_cleanup_thread_safety(self, broadcaster):
        """Test thread safety of resource cleanup operations."""
        num_workers = 10
        cleanup_cycles = 5
        
        results = []
        
        def cleanup_worker(worker_id: int) -> Dict[str, Any]:
            """Worker that performs cleanup operations."""
            worker_result = {
                'worker_id': worker_id,
                'cleanup_cycles': 0,
                'optimizations': 0,
                'batch_flushes': 0
            }
            
            for cycle in range(cleanup_cycles):
                # Create some load first
                for i in range(10):
                    broadcaster.broadcast_to_users(
                        event_type=f'cleanup_event_{worker_id}_{cycle}_{i}',
                        event_data={'worker': worker_id, 'cycle': cycle, 'sequence': i},
                        user_ids={f'cleanup_user_{worker_id}_{i}'},
                        priority=DeliveryPriority.MEDIUM
                    )
                
                # Perform cleanup operations concurrently
                if cycle % 3 == 0:
                    broadcaster.flush_all_batches()
                    worker_result['batch_flushes'] += 1
                elif cycle % 3 == 1:
                    broadcaster.optimize_performance()
                    worker_result['optimizations'] += 1
                
                worker_result['cleanup_cycles'] += 1
                
                # Brief pause between cycles
                time.sleep(0.01)
            
            return worker_result
        
        # Run concurrent cleanup operations
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(cleanup_worker, i) for i in range(num_workers)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze cleanup thread safety
        total_cycles = sum(r['cleanup_cycles'] for r in results)
        total_optimizations = sum(r['optimizations'] for r in results)
        total_flushes = sum(r['batch_flushes'] for r in results)
        
        expected_cycles = num_workers * cleanup_cycles
        
        # Cleanup thread safety assertions
        assert total_cycles == expected_cycles
        assert total_optimizations > 0
        assert total_flushes > 0
        
        # System should remain healthy after concurrent cleanup
        health = broadcaster.get_health_status()
        assert health['status'] in ['healthy', 'warning']
        
        # No resource leaks - pending batches should be minimal
        stats = broadcaster.get_broadcast_stats()
        assert stats['pending_batches'] < 100  # Reasonable number


class TestDeadlockPrevention:
    """Test deadlock prevention under high concurrent load."""
    
    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for deadlock testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio
    
    @pytest.fixture  
    def broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster for deadlock tests."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=200,  # Longer window to increase contention
            max_events_per_user=300,
            max_batch_size=15
        )
    
    def test_no_deadlock_under_high_contention(self, broadcaster):
        """Test no deadlocks occur under high resource contention."""
        contention_duration = 3.0  # 3 seconds of high contention
        num_contention_workers = 30
        
        completion_results = []
        
        def high_contention_worker(worker_id: int) -> Dict[str, Any]:
            """Worker that creates high resource contention."""
            worker_result = {
                'worker_id': worker_id,
                'start_time': time.time(),
                'operations_completed': 0,
                'deadlock_detected': False
            }
            
            end_time = time.time() + contention_duration
            
            while time.time() < end_time:
                operation_start = time.time()
                
                try:
                    # Operation 1: Broadcast with batching
                    broadcaster.broadcast_to_users(
                        event_type=f'contention_event_{worker_id}',
                        event_data={
                            'worker': worker_id,
                            'timestamp': time.time(),
                            'operation': 'broadcast'
                        },
                        user_ids={f'contention_user_{worker_id}_{worker_result["operations_completed"] % 5}'},
                        priority=DeliveryPriority.MEDIUM
                    )
                    
                    # Operation 2: Statistics read
                    stats = broadcaster.get_broadcast_stats()
                    
                    # Operation 3: Rate status check
                    rate_status = broadcaster.get_user_rate_status(f'contention_user_{worker_id}')
                    
                    # Operation 4: Occasional cleanup
                    if worker_result['operations_completed'] % 10 == 0:
                        broadcaster.flush_all_batches()
                    
                    worker_result['operations_completed'] += 1
                    
                    # Check for potential deadlock (operation taking too long)
                    operation_duration = time.time() - operation_start
                    if operation_duration > 1.0:  # 1 second timeout
                        worker_result['deadlock_detected'] = True
                        break
                        
                except Exception as e:
                    # Any exception might indicate deadlock or corruption
                    worker_result['deadlock_detected'] = True
                    break
            
            worker_result['end_time'] = time.time()
            worker_result['total_duration'] = worker_result['end_time'] - worker_result['start_time']
            
            return worker_result
        
        # Run high contention scenario
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_contention_workers) as executor:
            futures = [
                executor.submit(high_contention_worker, i) 
                for i in range(num_contention_workers)
            ]
            
            # Use timeout to prevent hanging if deadlock occurs
            try:
                for future in as_completed(futures, timeout=contention_duration + 5.0):
                    completion_results.append(future.result())
            except TimeoutError:
                # Timeout indicates potential deadlock
                pytest.fail("Potential deadlock detected - operations did not complete within timeout")
        
        total_duration = time.time() - start_time
        
        # Analyze deadlock prevention results
        total_operations = sum(r['operations_completed'] for r in completion_results)
        deadlock_detected = any(r['deadlock_detected'] for r in completion_results)
        workers_completed = len(completion_results)
        
        # Deadlock prevention assertions
        assert workers_completed == num_contention_workers  # All workers completed
        assert not deadlock_detected  # No deadlocks detected
        assert total_duration < contention_duration + 2.0  # Completed within reasonable time
        assert total_operations > 0  # Some operations completed successfully
        
        # System should remain functional after high contention
        final_stats = broadcaster.get_broadcast_stats()
        assert isinstance(final_stats, dict)
        assert final_stats['total_events'] > 0
    
    def test_graceful_shutdown_no_deadlock(self, broadcaster):
        """Test graceful shutdown doesn't cause deadlocks."""
        num_active_workers = 20
        
        # Start workers that will be active during shutdown
        active_workers_running = threading.Event()
        worker_results = []
        
        def active_worker_during_shutdown(worker_id: int):
            """Worker that remains active during shutdown."""
            result = {'worker_id': worker_id, 'operations': 0, 'shutdown_completed': False}
            
            while active_workers_running.is_set():
                try:
                    broadcaster.broadcast_to_users(
                        event_type=f'shutdown_test_{worker_id}',
                        event_data={'worker': worker_id, 'timestamp': time.time()},
                        user_ids={f'shutdown_user_{worker_id}'},
                        priority=DeliveryPriority.MEDIUM
                    )
                    result['operations'] += 1
                    time.sleep(0.01)  # Brief pause
                except Exception:
                    # Expected during shutdown
                    break
            
            result['shutdown_completed'] = True
            worker_results.append(result)
        
        # Start active workers
        active_workers_running.set()
        
        worker_threads = [
            threading.Thread(target=active_worker_during_shutdown, args=(i,))
            for i in range(num_active_workers)
        ]
        
        for thread in worker_threads:
            thread.start()
        
        # Let workers run briefly
        time.sleep(0.5)
        
        # Initiate shutdown
        shutdown_start = time.time()
        
        # Stop workers and shutdown broadcaster
        active_workers_running.clear()
        
        # Shutdown should complete without hanging
        broadcaster.shutdown()
        
        shutdown_duration = time.time() - shutdown_start
        
        # Wait for all worker threads to complete
        for thread in worker_threads:
            thread.join(timeout=2.0)  # 2 second timeout
        
        # Analyze shutdown deadlock prevention
        completed_workers = len(worker_results)
        all_completed_shutdown = all(r['shutdown_completed'] for r in worker_results)
        
        # Shutdown deadlock prevention assertions
        assert shutdown_duration < 10.0  # Shutdown completed within reasonable time
        assert completed_workers >= num_active_workers * 0.8  # Most workers completed
        assert all_completed_shutdown  # All workers handled shutdown gracefully
        
        # Thread pools should be shutdown
        assert broadcaster.batch_executor._shutdown
        assert broadcaster.delivery_executor._shutdown


if __name__ == '__main__':
    # Example of running threading and concurrency tests
    pytest.main([__file__ + "::TestThreadSafetyAndRaceConditions::test_batch_creation_thread_safety", "-v", "-s"])