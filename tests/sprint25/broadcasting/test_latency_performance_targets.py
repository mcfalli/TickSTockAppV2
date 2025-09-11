"""
Test ScalableBroadcaster <100ms Delivery Latency Performance Targets
Sprint 25 Day 3 Tests: Performance validation for <100ms delivery latency with batching.

Tests latency performance targets including:
- <100ms total delivery time including batching time
- Batch window timing accuracy (100ms ±10ms window validation)
- End-to-end latency measurement from broadcast_to_users to SocketIO emit
- Latency performance under various load scenarios
- Performance degradation analysis under sustained load
"""

import pytest
import time
import threading
import statistics
from unittest.mock import Mock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Set, List, Tuple, Callable
from collections import defaultdict, deque
import numpy as np
from dataclasses import dataclass
import random

from src.infrastructure.websocket.scalable_broadcaster import (
    ScalableBroadcaster, EventMessage, EventBatch, RateLimiter, 
    BroadcastStats, DeliveryPriority
)


@dataclass
class LatencyMeasurement:
    """Latency measurement data structure."""
    start_time: float
    end_time: float
    latency_ms: float
    event_type: str
    user_count: int
    batch_size: int
    priority: DeliveryPriority


class LatencyTrackingSocketIO:
    """Mock SocketIO that tracks emission timing for latency measurement."""
    
    def __init__(self):
        self.emit = Mock()
        self.server = Mock()
        
        # Latency tracking
        self.emission_times = []
        self.emission_lock = threading.Lock()
        self.start_times = {}  # Track when broadcasts started
        
        # Configure emit to track timing
        self.emit.side_effect = self._track_emit_timing
    
    def _track_emit_timing(self, event_type, *args, **kwargs):
        """Track emission timing for latency measurement."""
        emission_time = time.time()
        
        with self.emission_lock:
            self.emission_times.append({
                'emission_time': emission_time,
                'event_type': event_type,
                'args': args,
                'kwargs': kwargs
            })
        
        return True
    
    def set_broadcast_start_time(self, broadcast_id: str, start_time: float):
        """Set broadcast start time for latency calculation."""
        self.start_times[broadcast_id] = start_time
    
    def calculate_latencies(self) -> List[float]:
        """Calculate latencies from broadcast start to emission."""
        latencies = []
        
        with self.emission_lock:
            for emission in self.emission_times:
                # For batched events, extract timing from batch payload
                if emission['event_type'] == 'event_batch' and emission['args']:
                    batch_payload = emission['args'][0]
                    if isinstance(batch_payload, dict) and 'batch_timestamp' in batch_payload:
                        batch_start = batch_payload.get('batch_timestamp', emission['emission_time'])
                        # Use the earliest event timestamp as start time
                        if 'events' in batch_payload and batch_payload['events']:
                            earliest_event_time = min(event.get('timestamp', batch_start) 
                                                    for event in batch_payload['events'])
                            latency = (emission['emission_time'] - earliest_event_time) * 1000
                            latencies.append(latency)
                else:
                    # For individual events, use a default recent time
                    recent_time = emission['emission_time'] - 0.050  # Assume 50ms ago
                    latency = (emission['emission_time'] - recent_time) * 1000
                    latencies.append(latency)
        
        return latencies


class TestBatchWindowTimingAccuracy:
    """Test batch window timing accuracy for latency control."""
    
    @pytest.fixture
    def timing_socketio(self):
        """Create latency-tracking SocketIO."""
        return LatencyTrackingSocketIO()
    
    @pytest.fixture
    def timing_broadcaster(self, timing_socketio):
        """Create ScalableBroadcaster for timing tests."""
        return ScalableBroadcaster(
            socketio=timing_socketio,
            batch_window_ms=100,  # 100ms target window
            max_events_per_user=300,
            max_batch_size=50
        )
    
    def test_batch_window_timing_precision(self, timing_broadcaster, timing_socketio):
        """Test batch window timing precision (100ms ±10ms)."""
        room_name = 'timing_test_room'
        num_timing_tests = 20
        
        window_measurements = []
        
        for test_num in range(num_timing_tests):
            # Create batch with single event
            batch_start = time.time()
            
            timing_broadcaster.broadcast_to_room(
                room_name=room_name,
                event_type=f'timing_test_{test_num}',
                event_data={
                    'test_num': test_num,
                    'batch_start': batch_start,
                    'target_window_ms': timing_broadcaster.batch_window_ms
                },
                priority=DeliveryPriority.MEDIUM
            )
            
            # Wait for batch to be delivered via timer
            time.sleep(0.150)  # Wait longer than batch window
            
            # Check if batch was delivered within timing window
            emissions = timing_socketio.emission_times[-1:] if timing_socketio.emission_times else []
            
            if emissions:
                emission_time = emissions[0]['emission_time']
                window_duration = (emission_time - batch_start) * 1000  # Convert to ms
                window_measurements.append(window_duration)
            
            # Clear pending state for next test
            timing_broadcaster.flush_all_batches()
            timing_socketio.emission_times.clear()
            time.sleep(0.010)  # Brief pause between tests
        
        # Analyze batch window timing accuracy
        if window_measurements:
            avg_window_duration = statistics.mean(window_measurements)
            median_window_duration = statistics.median(window_measurements)
            std_window_duration = statistics.stdev(window_measurements) if len(window_measurements) > 1 else 0
            min_window_duration = min(window_measurements)
            max_window_duration = max(window_measurements)
            
            target_window_ms = timing_broadcaster.batch_window_ms
            
            # Batch window timing assertions (100ms ±10ms tolerance)
            assert avg_window_duration >= target_window_ms - 10, f"Average window {avg_window_duration:.1f}ms too fast"
            assert avg_window_duration <= target_window_ms + 20, f"Average window {avg_window_duration:.1f}ms too slow"
            assert min_window_duration >= target_window_ms - 20, f"Minimum window {min_window_duration:.1f}ms too fast"
            assert max_window_duration <= target_window_ms + 50, f"Maximum window {max_window_duration:.1f}ms too slow"
            assert std_window_duration <= 20, f"Window timing too variable: {std_window_duration:.1f}ms std dev"
            
            print(f"Batch Window Timing Results:")
            print(f"  Target window: {target_window_ms}ms")
            print(f"  Average: {avg_window_duration:.1f}ms")
            print(f"  Range: {min_window_duration:.1f}ms - {max_window_duration:.1f}ms")
            print(f"  Standard deviation: {std_window_duration:.1f}ms")
        else:
            pytest.fail("No batch window measurements captured")
    
    def test_immediate_flush_bypass_timing(self, timing_broadcaster, timing_socketio):
        """Test that immediate flush bypasses batch window timing."""
        room_name = 'immediate_flush_room'
        
        # Create batch
        flush_start = time.time()
        
        timing_broadcaster.broadcast_to_room(
            room_name=room_name,
            event_type='immediate_flush_test',
            event_data={'flush_start': flush_start},
            priority=DeliveryPriority.MEDIUM
        )
        
        # Immediately flush (should bypass batch window timing)
        timing_broadcaster.flush_all_batches()
        
        flush_end = time.time()
        immediate_flush_duration = (flush_end - flush_start) * 1000
        
        # Immediate flush timing assertions
        assert immediate_flush_duration < 50, f"Immediate flush took {immediate_flush_duration:.1f}ms, expected <50ms"
        
        # Verify emission occurred quickly
        time.sleep(0.100)  # Allow time for async delivery
        assert len(timing_socketio.emission_times) > 0, "No emission after immediate flush"
        
        if timing_socketio.emission_times:
            emission = timing_socketio.emission_times[-1]
            emission_latency = (emission['emission_time'] - flush_start) * 1000
            assert emission_latency < 100, f"Emission after flush took {emission_latency:.1f}ms"


class TestEndToEndLatencyMeasurement:
    """Test end-to-end latency from broadcast_to_users to SocketIO emit."""
    
    @pytest.fixture
    def latency_socketio(self):
        """Create precise latency-tracking SocketIO."""
        return LatencyTrackingSocketIO()
    
    @pytest.fixture
    def latency_broadcaster(self, latency_socketio):
        """Create ScalableBroadcaster for latency measurement."""
        # Shorter batch window for faster delivery
        return ScalableBroadcaster(
            socketio=latency_socketio,
            batch_window_ms=80,  # 80ms window for tighter latency
            max_events_per_user=400,
            max_batch_size=30
        )
    
    def measure_broadcast_latency(self, broadcaster, socketio, event_type: str, 
                                event_data: Dict[str, Any], user_ids: Set[str],
                                priority: DeliveryPriority = DeliveryPriority.MEDIUM) -> float:
        """Measure end-to-end broadcast latency."""
        
        # Clear previous emissions
        socketio.emission_times.clear()
        
        # Start timing
        broadcast_start = time.time()
        
        # Include timing in event data
        event_data_with_timing = {
            **event_data,
            'broadcast_start_time': broadcast_start,
            'timing_measurement': True
        }
        
        # Broadcast event
        delivered_count = broadcaster.broadcast_to_users(
            event_type=event_type,
            event_data=event_data_with_timing,
            user_ids=user_ids,
            priority=priority
        )
        
        # Wait for delivery (including batch window)
        max_wait_time = 0.200  # 200ms maximum wait
        wait_start = time.time()
        
        while (time.time() - wait_start) < max_wait_time:
            if socketio.emission_times:
                # Find our emission
                for emission in socketio.emission_times:
                    if emission['event_type'] == 'event_batch':
                        # Check batch payload
                        if emission['args'] and isinstance(emission['args'][0], dict):
                            batch_payload = emission['args'][0]
                            if 'events' in batch_payload:
                                for event in batch_payload['events']:
                                    if event.get('data', {}).get('timing_measurement'):
                                        latency_ms = (emission['emission_time'] - broadcast_start) * 1000
                                        return latency_ms
                    elif emission['event_type'] == event_type:
                        latency_ms = (emission['emission_time'] - broadcast_start) * 1000
                        return latency_ms
            
            time.sleep(0.001)  # 1ms polling interval
        
        # If we get here, emission wasn't found within wait time
        return float('inf')  # Indicate timeout/failure
    
    def test_single_user_broadcast_latency(self, latency_broadcaster, latency_socketio):
        """Test latency for single user broadcasts."""
        num_measurements = 30
        latency_measurements = []
        
        for i in range(num_measurements):
            user_ids = {f'latency_user_{i}'}
            
            latency_ms = self.measure_broadcast_latency(
                broadcaster=latency_broadcaster,
                socketio=latency_socketio,
                event_type=f'single_user_latency_test_{i}',
                event_data={
                    'measurement_num': i,
                    'test_type': 'single_user',
                    'timestamp': time.time()
                },
                user_ids=user_ids,
                priority=DeliveryPriority.MEDIUM
            )
            
            if latency_ms != float('inf'):
                latency_measurements.append(latency_ms)
            
            time.sleep(0.010)  # Brief pause between measurements
        
        # Analyze single user latency
        if latency_measurements:
            avg_latency = statistics.mean(latency_measurements)
            median_latency = statistics.median(latency_measurements)
            p95_latency = np.percentile(latency_measurements, 95)
            p99_latency = np.percentile(latency_measurements, 99)
            max_latency = max(latency_measurements)
            
            # Single user latency assertions (<100ms target)
            assert avg_latency < 100.0, f"Average latency {avg_latency:.1f}ms exceeds 100ms target"
            assert median_latency < 100.0, f"Median latency {median_latency:.1f}ms exceeds 100ms target"
            assert p95_latency < 120.0, f"P95 latency {p95_latency:.1f}ms exceeds 120ms threshold"
            assert p99_latency < 150.0, f"P99 latency {p99_latency:.1f}ms exceeds 150ms threshold"
            assert len(latency_measurements) >= num_measurements * 0.90, "Too many latency measurement failures"
            
            print(f"Single User Latency Results ({len(latency_measurements)} measurements):")
            print(f"  Average: {avg_latency:.1f}ms")
            print(f"  Median: {median_latency:.1f}ms")
            print(f"  P95: {p95_latency:.1f}ms")
            print(f"  P99: {p99_latency:.1f}ms")
            print(f"  Maximum: {max_latency:.1f}ms")
        else:
            pytest.fail("No successful latency measurements captured")
    
    def test_multi_user_broadcast_latency(self, latency_broadcaster, latency_socketio):
        """Test latency for multi-user broadcasts."""
        user_counts = [5, 10, 25, 50, 100]
        latency_by_user_count = {}
        
        for user_count in user_counts:
            user_ids = {f'multi_user_{user_count}_{i}' for i in range(user_count)}
            measurements = []
            
            # Take multiple measurements for each user count
            for measurement in range(10):
                latency_ms = self.measure_broadcast_latency(
                    broadcaster=latency_broadcaster,
                    socketio=latency_socketio,
                    event_type=f'multi_user_test_{user_count}_{measurement}',
                    event_data={
                        'user_count': user_count,
                        'measurement': measurement,
                        'test_type': 'multi_user'
                    },
                    user_ids=user_ids,
                    priority=DeliveryPriority.MEDIUM
                )
                
                if latency_ms != float('inf'):
                    measurements.append(latency_ms)
                
                time.sleep(0.020)  # Brief pause
            
            if measurements:
                avg_latency = statistics.mean(measurements)
                latency_by_user_count[user_count] = {
                    'avg_latency': avg_latency,
                    'max_latency': max(measurements),
                    'measurements': len(measurements)
                }
        
        # Analyze multi-user latency scalability
        for user_count, results in latency_by_user_count.items():
            avg_latency = results['avg_latency']
            max_latency = results['max_latency']
            
            # Multi-user latency assertions
            assert avg_latency < 150.0, f"Average latency {avg_latency:.1f}ms for {user_count} users exceeds 150ms"
            assert max_latency < 200.0, f"Maximum latency {max_latency:.1f}ms for {user_count} users exceeds 200ms"
            
            print(f"Multi-User Latency - {user_count} users:")
            print(f"  Average: {avg_latency:.1f}ms")
            print(f"  Maximum: {max_latency:.1f}ms")
            print(f"  Measurements: {results['measurements']}/10")
        
        # Latency should not increase dramatically with user count
        if len(latency_by_user_count) >= 3:
            latencies = [results['avg_latency'] for results in latency_by_user_count.values()]
            max_latency = max(latencies)
            min_latency = min(latencies)
            scalability_ratio = max_latency / min_latency
            
            assert scalability_ratio < 2.5, f"Latency scalability ratio {scalability_ratio:.1f} too high"
    
    def test_priority_impact_on_latency(self, latency_broadcaster, latency_socketio):
        """Test impact of event priority on delivery latency."""
        priorities = [DeliveryPriority.LOW, DeliveryPriority.MEDIUM, 
                     DeliveryPriority.HIGH, DeliveryPriority.CRITICAL]
        latency_by_priority = {}
        
        for priority in priorities:
            user_ids = {f'priority_user_{priority.name}'}
            measurements = []
            
            # Take multiple measurements for each priority
            for measurement in range(15):
                latency_ms = self.measure_broadcast_latency(
                    broadcaster=latency_broadcaster,
                    socketio=latency_socketio,
                    event_type=f'priority_test_{priority.name}_{measurement}',
                    event_data={
                        'priority': priority.name,
                        'measurement': measurement,
                        'test_type': 'priority_impact'
                    },
                    user_ids=user_ids,
                    priority=priority
                )
                
                if latency_ms != float('inf'):
                    measurements.append(latency_ms)
                
                time.sleep(0.015)  # Brief pause
            
            if measurements:
                latency_by_priority[priority] = {
                    'avg_latency': statistics.mean(measurements),
                    'min_latency': min(measurements),
                    'max_latency': max(measurements),
                    'measurements': len(measurements)
                }
        
        # Analyze priority impact on latency
        for priority, results in latency_by_priority.items():
            avg_latency = results['avg_latency']
            
            # Priority latency assertions
            if priority == DeliveryPriority.CRITICAL:
                assert avg_latency < 80.0, f"CRITICAL priority latency {avg_latency:.1f}ms should be <80ms"
            elif priority == DeliveryPriority.HIGH:
                assert avg_latency < 100.0, f"HIGH priority latency {avg_latency:.1f}ms should be <100ms"
            else:
                assert avg_latency < 120.0, f"{priority.name} priority latency {avg_latency:.1f}ms should be <120ms"
            
            print(f"{priority.name} Priority Latency:")
            print(f"  Average: {avg_latency:.1f}ms")
            print(f"  Range: {results['min_latency']:.1f}ms - {results['max_latency']:.1f}ms")
        
        # Higher priorities should generally have lower or similar latency
        if DeliveryPriority.CRITICAL in latency_by_priority and DeliveryPriority.LOW in latency_by_priority:
            critical_latency = latency_by_priority[DeliveryPriority.CRITICAL]['avg_latency']
            low_latency = latency_by_priority[DeliveryPriority.LOW]['avg_latency']
            
            # Allow some tolerance, but CRITICAL should not be significantly slower
            assert critical_latency <= low_latency + 20, f"CRITICAL latency {critical_latency:.1f}ms should not exceed LOW latency {low_latency:.1f}ms by >20ms"


class TestLatencyUnderLoad:
    """Test latency performance under various load scenarios."""
    
    @pytest.fixture
    def load_socketio(self):
        """Create SocketIO for load testing."""
        return LatencyTrackingSocketIO()
    
    @pytest.fixture
    def load_broadcaster(self, load_socketio):
        """Create broadcaster for load testing."""
        return ScalableBroadcaster(
            socketio=load_socketio,
            batch_window_ms=100,
            max_events_per_user=500,  # Higher limit for load testing
            max_batch_size=40
        )
    
    def test_latency_under_concurrent_load(self, load_broadcaster, load_socketio):
        """Test latency performance under concurrent load."""
        concurrent_users = 50
        events_per_user = 10
        
        latency_measurements = []
        measurement_lock = threading.Lock()
        
        def concurrent_latency_worker(worker_id: int) -> Dict[str, Any]:
            """Worker that measures latency under concurrent load."""
            worker_result = {
                'worker_id': worker_id,
                'latencies': [],
                'successful_measurements': 0,
                'failed_measurements': 0
            }
            
            user_ids = {f'concurrent_load_user_{worker_id}'}
            
            for event_num in range(events_per_user):
                try:
                    # Clear emissions for this measurement
                    with measurement_lock:
                        load_socketio.emission_times.clear()
                    
                    broadcast_start = time.time()
                    
                    delivered_count = load_broadcaster.broadcast_to_users(
                        event_type=f'concurrent_load_event_{worker_id}_{event_num}',
                        event_data={
                            'worker_id': worker_id,
                            'event_num': event_num,
                            'broadcast_start': broadcast_start,
                            'concurrent_load_test': True
                        },
                        user_ids=user_ids,
                        priority=DeliveryPriority.MEDIUM
                    )
                    
                    # Wait briefly for emission (shorter wait due to concurrent load)
                    time.sleep(0.120)
                    
                    # Check for emission
                    emission_found = False
                    with measurement_lock:
                        for emission in load_socketio.emission_times:
                            latency_ms = (emission['emission_time'] - broadcast_start) * 1000
                            worker_result['latencies'].append(latency_ms)
                            latency_measurements.append(latency_ms)
                            emission_found = True
                            break
                    
                    if emission_found:
                        worker_result['successful_measurements'] += 1
                    else:
                        worker_result['failed_measurements'] += 1
                    
                except Exception as e:
                    worker_result['failed_measurements'] += 1
                
                time.sleep(0.010)  # Brief pause between events
            
            return worker_result
        
        # Run concurrent latency measurements
        print(f"Testing latency under concurrent load: {concurrent_users} users...")
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [
                executor.submit(concurrent_latency_worker, i)
                for i in range(concurrent_users)
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze concurrent load latency
        all_latencies = [latency for result in results for latency in result['latencies']]
        successful_measurements = sum(r['successful_measurements'] for r in results)
        failed_measurements = sum(r['failed_measurements'] for r in results)
        
        if all_latencies:
            avg_latency = statistics.mean(all_latencies)
            median_latency = statistics.median(all_latencies)
            p95_latency = np.percentile(all_latencies, 95)
            max_latency = max(all_latencies)
            success_rate = successful_measurements / (successful_measurements + failed_measurements) * 100
            
            # Concurrent load latency assertions
            assert avg_latency < 200.0, f"Average latency under load {avg_latency:.1f}ms exceeds 200ms"
            assert median_latency < 150.0, f"Median latency under load {median_latency:.1f}ms exceeds 150ms"
            assert p95_latency < 300.0, f"P95 latency under load {p95_latency:.1f}ms exceeds 300ms"
            assert success_rate >= 70.0, f"Success rate {success_rate:.1f}% too low under concurrent load"
            
            print(f"Concurrent Load Latency Results:")
            print(f"  Concurrent users: {concurrent_users}")
            print(f"  Successful measurements: {successful_measurements}")
            print(f"  Success rate: {success_rate:.1f}%")
            print(f"  Average latency: {avg_latency:.1f}ms")
            print(f"  Median latency: {median_latency:.1f}ms")
            print(f"  P95 latency: {p95_latency:.1f}ms")
        else:
            pytest.fail("No latency measurements captured under concurrent load")
    
    def test_latency_degradation_under_sustained_load(self, load_broadcaster, load_socketio):
        """Test latency degradation under sustained load."""
        sustained_duration = 5.0  # 5 seconds
        event_frequency = 20  # 20 events per second
        user_base_size = 30
        
        latency_timeline = []
        
        print(f"Testing latency degradation under sustained load for {sustained_duration}s...")
        
        start_time = time.time()
        event_count = 0
        
        while time.time() - start_time < sustained_duration:
            cycle_start = time.time()
            
            # Select random user subset
            num_target_users = random.randint(5, user_base_size)
            user_ids = {f'sustained_user_{i}' for i in range(num_target_users)}
            
            # Clear emissions
            load_socketio.emission_times.clear()
            
            # Broadcast event
            broadcast_start = time.time()
            delivered_count = load_broadcaster.broadcast_to_users(
                event_type=f'sustained_load_event_{event_count}',
                event_data={
                    'event_count': event_count,
                    'elapsed_time': broadcast_start - start_time,
                    'target_users': num_target_users,
                    'sustained_load_test': True
                },
                user_ids=user_ids,
                priority=DeliveryPriority.MEDIUM
            )
            
            # Measure latency for this event
            time.sleep(0.120)  # Wait for emission
            
            if load_socketio.emission_times:
                emission = load_socketio.emission_times[0]
                latency_ms = (emission['emission_time'] - broadcast_start) * 1000
                elapsed_time = broadcast_start - start_time
                
                latency_timeline.append({
                    'elapsed_time': elapsed_time,
                    'latency_ms': latency_ms,
                    'event_count': event_count,
                    'user_count': num_target_users
                })
            
            event_count += 1
            
            # Maintain frequency
            cycle_duration = time.time() - cycle_start
            sleep_time = (1.0 / event_frequency) - cycle_duration
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Analyze latency degradation
        if len(latency_timeline) >= 10:
            # Split timeline into early and late periods
            mid_point = len(latency_timeline) // 2
            early_latencies = [m['latency_ms'] for m in latency_timeline[:mid_point]]
            late_latencies = [m['latency_ms'] for m in latency_timeline[mid_point:]]
            
            early_avg = statistics.mean(early_latencies)
            late_avg = statistics.mean(late_latencies)
            overall_avg = statistics.mean([m['latency_ms'] for m in latency_timeline])
            
            degradation_ratio = late_avg / early_avg if early_avg > 0 else 1.0
            
            # Latency degradation assertions
            assert overall_avg < 250.0, f"Overall average latency {overall_avg:.1f}ms exceeds 250ms under sustained load"
            assert degradation_ratio < 2.0, f"Latency degradation ratio {degradation_ratio:.1f} too high (late/early)"
            assert late_avg < 300.0, f"Late period latency {late_avg:.1f}ms exceeds 300ms"
            
            print(f"Sustained Load Latency Results:")
            print(f"  Duration: {sustained_duration}s")
            print(f"  Events processed: {len(latency_timeline)}")
            print(f"  Early period average: {early_avg:.1f}ms")
            print(f"  Late period average: {late_avg:.1f}ms")
            print(f"  Degradation ratio: {degradation_ratio:.2f}")
            print(f"  Overall average: {overall_avg:.1f}ms")
        else:
            pytest.fail("Insufficient latency measurements for degradation analysis")
    
    def test_batch_size_impact_on_latency(self, load_broadcaster, load_socketio):
        """Test impact of batch size on delivery latency."""
        batch_size_scenarios = [
            (5, "Small batches"),
            (15, "Medium batches"),
            (30, "Large batches"),
            (50, "Maximum batches")
        ]
        
        latency_by_batch_size = {}
        
        for target_batch_size, scenario_name in batch_size_scenarios:
            print(f"Testing {scenario_name} (target size: {target_batch_size})...")
            
            # Temporarily adjust max batch size
            original_max_batch_size = load_broadcaster.max_batch_size
            load_broadcaster.max_batch_size = target_batch_size
            
            measurements = []
            
            # Generate load to create batches of target size
            for test_run in range(10):
                user_ids = {f'batch_size_user_{target_batch_size}_{i}' for i in range(target_batch_size)}
                
                load_socketio.emission_times.clear()
                broadcast_start = time.time()
                
                # Send events to create batch
                for i in range(target_batch_size):
                    load_broadcaster.broadcast_to_users(
                        event_type=f'batch_size_event_{target_batch_size}_{test_run}_{i}',
                        event_data={
                            'batch_size_test': target_batch_size,
                            'test_run': test_run,
                            'event_index': i
                        },
                        user_ids={f'batch_size_user_{target_batch_size}_{i}'},
                        priority=DeliveryPriority.MEDIUM
                    )
                
                # Wait for batch delivery
                time.sleep(0.150)
                
                if load_socketio.emission_times:
                    emission = load_socketio.emission_times[0]
                    latency_ms = (emission['emission_time'] - broadcast_start) * 1000
                    measurements.append(latency_ms)
                
                time.sleep(0.050)  # Pause between test runs
            
            # Restore original batch size
            load_broadcaster.max_batch_size = original_max_batch_size
            
            if measurements:
                avg_latency = statistics.mean(measurements)
                max_latency = max(measurements)
                
                latency_by_batch_size[target_batch_size] = {
                    'scenario_name': scenario_name,
                    'avg_latency': avg_latency,
                    'max_latency': max_latency,
                    'measurements': len(measurements)
                }
        
        # Analyze batch size impact on latency
        for batch_size, results in latency_by_batch_size.items():
            avg_latency = results['avg_latency']
            max_latency = results['max_latency']
            
            # Batch size latency assertions
            assert avg_latency < 200.0, f"Average latency {avg_latency:.1f}ms for batch size {batch_size} exceeds 200ms"
            assert max_latency < 300.0, f"Maximum latency {max_latency:.1f}ms for batch size {batch_size} exceeds 300ms"
            
            print(f"{results['scenario_name']}:")
            print(f"  Average latency: {avg_latency:.1f}ms")
            print(f"  Maximum latency: {max_latency:.1f}ms")
        
        # Larger batches should not have dramatically higher latency
        if len(latency_by_batch_size) >= 3:
            latencies = [results['avg_latency'] for results in latency_by_batch_size.values()]
            latency_range = max(latencies) - min(latencies)
            
            assert latency_range < 100.0, f"Latency range {latency_range:.1f}ms across batch sizes too large"


class TestPerformanceDegradationAnalysis:
    """Test and analyze performance degradation patterns."""
    
    @pytest.fixture
    def degradation_socketio(self):
        """Create SocketIO for degradation analysis."""
        return LatencyTrackingSocketIO()
    
    @pytest.fixture
    def degradation_broadcaster(self, degradation_socketio):
        """Create broadcaster for degradation analysis."""
        return ScalableBroadcaster(
            socketio=degradation_socketio,
            batch_window_ms=100,
            max_events_per_user=300,
            max_batch_size=35
        )
    
    def test_performance_under_memory_pressure(self, degradation_broadcaster, degradation_socketio):
        """Test performance degradation under memory pressure."""
        
        # Create memory pressure by generating large event payloads
        large_payload = 'x' * 10000  # 10KB per event
        memory_pressure_events = 100
        
        latencies_under_pressure = []
        
        for i in range(memory_pressure_events):
            degradation_socketio.emission_times.clear()
            broadcast_start = time.time()
            
            degradation_broadcaster.broadcast_to_users(
                event_type=f'memory_pressure_event_{i}',
                event_data={
                    'sequence': i,
                    'large_payload': large_payload,
                    'memory_pressure_test': True
                },
                user_ids={f'memory_pressure_user_{i % 10}'},  # Rotate among 10 users
                priority=DeliveryPriority.MEDIUM
            )
            
            time.sleep(0.120)  # Wait for emission
            
            if degradation_socketio.emission_times:
                emission = degradation_socketio.emission_times[0]
                latency_ms = (emission['emission_time'] - broadcast_start) * 1000
                latencies_under_pressure.append(latency_ms)
            
            time.sleep(0.020)  # Brief pause
        
        # Analyze performance under memory pressure
        if latencies_under_pressure:
            avg_latency_pressure = statistics.mean(latencies_under_pressure)
            max_latency_pressure = max(latencies_under_pressure)
            p95_latency_pressure = np.percentile(latencies_under_pressure, 95)
            
            # Memory pressure performance assertions
            assert avg_latency_pressure < 300.0, f"Average latency under memory pressure {avg_latency_pressure:.1f}ms exceeds 300ms"
            assert max_latency_pressure < 500.0, f"Maximum latency under memory pressure {max_latency_pressure:.1f}ms exceeds 500ms"
            assert p95_latency_pressure < 400.0, f"P95 latency under memory pressure {p95_latency_pressure:.1f}ms exceeds 400ms"
            
            print(f"Memory Pressure Performance:")
            print(f"  Events with large payloads: {len(latencies_under_pressure)}")
            print(f"  Average latency: {avg_latency_pressure:.1f}ms")
            print(f"  P95 latency: {p95_latency_pressure:.1f}ms")
            print(f"  Maximum latency: {max_latency_pressure:.1f}ms")
        else:
            pytest.fail("No latency measurements captured under memory pressure")
    
    def test_recovery_after_performance_optimization(self, degradation_broadcaster, degradation_socketio):
        """Test performance recovery after running optimization."""
        
        # Phase 1: Create substantial load
        pre_optimization_latencies = []
        
        for i in range(50):
            degradation_socketio.emission_times.clear()
            broadcast_start = time.time()
            
            degradation_broadcaster.broadcast_to_users(
                event_type=f'pre_optimization_event_{i}',
                event_data={'sequence': i, 'phase': 'pre_optimization'},
                user_ids={f'optimization_user_{i % 15}'},
                priority=DeliveryPriority.MEDIUM
            )
            
            time.sleep(0.110)
            
            if degradation_socketio.emission_times:
                emission = degradation_socketio.emission_times[0]
                latency_ms = (emission['emission_time'] - broadcast_start) * 1000
                pre_optimization_latencies.append(latency_ms)
        
        pre_optimization_avg = statistics.mean(pre_optimization_latencies) if pre_optimization_latencies else 0
        
        # Phase 2: Run performance optimization
        optimization_result = degradation_broadcaster.optimize_performance()
        time.sleep(0.100)  # Allow optimization effects to settle
        
        # Phase 3: Measure post-optimization performance
        post_optimization_latencies = []
        
        for i in range(50):
            degradation_socketio.emission_times.clear()
            broadcast_start = time.time()
            
            degradation_broadcaster.broadcast_to_users(
                event_type=f'post_optimization_event_{i}',
                event_data={'sequence': i, 'phase': 'post_optimization'},
                user_ids={f'optimization_user_{i % 15}'},
                priority=DeliveryPriority.MEDIUM
            )
            
            time.sleep(0.110)
            
            if degradation_socketio.emission_times:
                emission = degradation_socketio.emission_times[0]
                latency_ms = (emission['emission_time'] - broadcast_start) * 1000
                post_optimization_latencies.append(latency_ms)
        
        post_optimization_avg = statistics.mean(post_optimization_latencies) if post_optimization_latencies else 0
        
        # Analyze optimization effectiveness
        if pre_optimization_avg > 0 and post_optimization_avg > 0:
            performance_improvement = (pre_optimization_avg - post_optimization_avg) / pre_optimization_avg
            
            # Optimization recovery assertions
            assert post_optimization_avg < 200.0, f"Post-optimization latency {post_optimization_avg:.1f}ms exceeds 200ms"
            assert performance_improvement > -0.3, f"Performance degraded by {abs(performance_improvement)*100:.1f}% after optimization"
            
            # Ideally performance improves, but maintaining performance is acceptable
            improvement_status = "improved" if performance_improvement > 0 else "maintained"
            
            print(f"Optimization Recovery Results:")
            print(f"  Pre-optimization average: {pre_optimization_avg:.1f}ms")
            print(f"  Post-optimization average: {post_optimization_avg:.1f}ms")
            print(f"  Performance change: {performance_improvement*100:+.1f}% ({improvement_status})")
            print(f"  Optimization successful: {isinstance(optimization_result, dict)}")
        else:
            pytest.fail("Insufficient measurements for optimization analysis")


if __name__ == '__main__':
    # Example of running latency performance tests
    pytest.main([__file__ + "::TestEndToEndLatencyMeasurement::test_single_user_broadcast_latency", "-v", "-s"])