"""
Test ScalableBroadcaster 500+ Concurrent Users Scalability
Sprint 25 Day 3 Tests: Scalability validation with 500+ concurrent users and batching optimization.

Tests scalability scenarios including:
- 500+ concurrent users with full system performance validation
- Memory usage patterns during sustained high-volume broadcasting
- Scalability validation under 4,000+ ticker load simulation
- Batch optimization effectiveness at scale
- System resource utilization and stability under load
"""

import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from unittest.mock import Mock

import psutil
import pytest

from src.infrastructure.websocket.scalable_broadcaster import (
    DeliveryPriority,
    ScalableBroadcaster,
)


class SystemResourceMonitor:
    """Monitor system resources during scalability tests."""

    def __init__(self):
        self.monitoring = False
        self.samples = []
        self.monitor_thread = None
        self.sample_interval = 0.1  # 100ms intervals

    def start_monitoring(self):
        """Start resource monitoring."""
        self.monitoring = True
        self.samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop resource monitoring and return results."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()

        if not self.samples:
            return {}

        # Calculate statistics
        cpu_usage = [s['cpu_percent'] for s in self.samples]
        memory_usage = [s['memory_mb'] for s in self.samples]
        thread_count = [s['thread_count'] for s in self.samples]

        return {
            'duration_seconds': len(self.samples) * self.sample_interval,
            'sample_count': len(self.samples),
            'cpu_percent': {
                'avg': sum(cpu_usage) / len(cpu_usage),
                'max': max(cpu_usage),
                'min': min(cpu_usage)
            },
            'memory_mb': {
                'avg': sum(memory_usage) / len(memory_usage),
                'max': max(memory_usage),
                'min': min(memory_usage),
                'growth': memory_usage[-1] - memory_usage[0] if len(memory_usage) > 1 else 0
            },
            'threads': {
                'avg': sum(thread_count) / len(thread_count),
                'max': max(thread_count),
                'min': min(thread_count)
            }
        }

    def _monitor_resources(self):
        """Resource monitoring loop."""
        process = psutil.Process()

        while self.monitoring:
            try:
                sample = {
                    'timestamp': time.time(),
                    'cpu_percent': process.cpu_percent(),
                    'memory_mb': process.memory_info().rss / 1024 / 1024,
                    'thread_count': process.num_threads(),
                }
                self.samples.append(sample)
                time.sleep(self.sample_interval)
            except Exception:
                # Ignore monitoring errors
                pass


class TestScalability500Users:
    """Test scalability with 500+ concurrent users."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO optimized for high-volume testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()

        # Thread-safe emit counting
        socketio._emit_count = 0
        socketio._emit_lock = threading.Lock()

        def count_emit(*args, **kwargs):
            with socketio._emit_lock:
                socketio._emit_count += 1

        socketio.emit.side_effect = count_emit
        return socketio

    @pytest.fixture
    def scalable_broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster optimized for high scalability."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=100,  # 100ms batching for scalability
            max_events_per_user=200,  # Higher rate limit for scale testing
            max_batch_size=50  # Larger batches for efficiency
        )

    @pytest.fixture
    def resource_monitor(self):
        """Resource monitor fixture."""
        return SystemResourceMonitor()

    def test_500_users_subscription_performance(self, scalable_broadcaster, resource_monitor):
        """Test subscription creation performance with 500+ users."""
        num_users = 500
        batch_size = 50

        # Start resource monitoring
        resource_monitor.start_monitoring()

        print(f"Creating {num_users} user subscriptions...")
        start_time = time.time()

        subscription_times = []
        user_creation_results = []

        def create_user_batch(batch_start: int, batch_size: int) -> dict[str, Any]:
            """Create batch of users with subscriptions."""
            batch_result = {
                'batch_start': batch_start,
                'users_created': 0,
                'subscription_times': [],
                'errors': 0
            }

            for i in range(batch_size):
                user_id = f'scale_user_{batch_start + i}'

                subscription_start = time.time()
                try:
                    # Simulate subscription creation (would normally go through UniversalWebSocketManager)
                    # For ScalableBroadcaster testing, we'll simulate by creating rate limiters
                    scalable_broadcaster.get_user_rate_status(user_id)

                    batch_result['users_created'] += 1
                    batch_result['subscription_times'].append(time.time() - subscription_start)

                except Exception:
                    batch_result['errors'] += 1

            return batch_result

        # Create users in parallel batches
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(create_user_batch, i, batch_size)
                for i in range(0, num_users, batch_size)
            ]

            for future in as_completed(futures):
                user_creation_results.append(future.result())

        creation_duration = time.time() - start_time

        # Stop resource monitoring
        resource_stats = resource_monitor.stop_monitoring()

        # Analyze subscription performance
        total_users_created = sum(r['users_created'] for r in user_creation_results)
        total_errors = sum(r['errors'] for r in user_creation_results)
        all_subscription_times = []
        for result in user_creation_results:
            all_subscription_times.extend(result['subscription_times'])

        avg_subscription_time = sum(all_subscription_times) / len(all_subscription_times) if all_subscription_times else 0
        max_subscription_time = max(all_subscription_times) if all_subscription_times else 0
        subscriptions_per_second = total_users_created / creation_duration

        # Scalability assertions for 500 users
        assert total_users_created >= num_users * 0.99  # At least 99% success
        assert total_errors <= num_users * 0.01  # Less than 1% errors
        assert avg_subscription_time < 0.001  # Less than 1ms average (mock operations)
        assert max_subscription_time < 0.010  # Less than 10ms maximum
        assert subscriptions_per_second > 100  # More than 100 subscriptions/sec

        # Resource usage should be reasonable
        if resource_stats:
            assert resource_stats['memory_mb']['max'] < 500  # Less than 500MB peak
            assert resource_stats['cpu_percent']['avg'] < 80   # Less than 80% average CPU

        print("Subscription Performance:")
        print(f"  Users created: {total_users_created}/{num_users}")
        print(f"  Average time: {avg_subscription_time*1000:.2f}ms")
        print(f"  Rate: {subscriptions_per_second:.0f} subscriptions/sec")
        print(f"  Peak memory: {resource_stats['memory_mb']['max']:.1f}MB")

    def test_500_users_concurrent_broadcasting(self, scalable_broadcaster, resource_monitor):
        """Test concurrent broadcasting to 500+ users."""
        num_users = 500
        events_per_broadcast = 100
        concurrent_broadcasts = 10

        # Pre-create user set for broadcasting
        user_ids = {f'broadcast_user_{i}' for i in range(num_users)}

        # Start resource monitoring
        resource_monitor.start_monitoring()

        print(f"Starting concurrent broadcasting to {num_users} users...")
        broadcast_start = time.time()

        broadcast_results = []

        def concurrent_broadcast_worker(worker_id: int) -> dict[str, Any]:
            """Worker that broadcasts events to user set."""
            worker_result = {
                'worker_id': worker_id,
                'events_sent': 0,
                'total_deliveries': 0,
                'broadcast_times': [],
                'errors': 0
            }

            for i in range(events_per_broadcast):
                event_start = time.time()

                try:
                    delivered_count = scalable_broadcaster.broadcast_to_users(
                        event_type=f'scale_event_{worker_id}_{i}',
                        event_data={
                            'worker_id': worker_id,
                            'sequence': i,
                            'timestamp': time.time(),
                            'user_count': len(user_ids)
                        },
                        user_ids=user_ids,  # Broadcast to all 500 users
                        priority=DeliveryPriority.MEDIUM
                    )

                    broadcast_time = time.time() - event_start
                    worker_result['events_sent'] += 1
                    worker_result['total_deliveries'] += delivered_count
                    worker_result['broadcast_times'].append(broadcast_time)

                except Exception:
                    worker_result['errors'] += 1

                # Brief pause to simulate realistic load
                time.sleep(0.001)

            return worker_result

        # Run concurrent broadcasts
        with ThreadPoolExecutor(max_workers=concurrent_broadcasts) as executor:
            futures = [
                executor.submit(concurrent_broadcast_worker, i)
                for i in range(concurrent_broadcasts)
            ]

            for future in as_completed(futures):
                broadcast_results.append(future.result())

        broadcast_duration = time.time() - broadcast_start

        # Stop resource monitoring
        resource_stats = resource_monitor.stop_monitoring()

        # Analyze broadcasting performance
        total_events_sent = sum(r['events_sent'] for r in broadcast_results)
        total_deliveries = sum(r['total_deliveries'] for r in broadcast_results)
        total_errors = sum(r['errors'] for r in broadcast_results)

        all_broadcast_times = []
        for result in broadcast_results:
            all_broadcast_times.extend(result['broadcast_times'])

        avg_broadcast_time = sum(all_broadcast_times) / len(all_broadcast_times) if all_broadcast_times else 0
        max_broadcast_time = max(all_broadcast_times) if all_broadcast_times else 0
        events_per_second = total_events_sent / broadcast_duration
        deliveries_per_event = total_deliveries / total_events_sent if total_events_sent else 0

        expected_events = concurrent_broadcasts * events_per_broadcast
        expected_deliveries = expected_events * num_users

        # Scalability assertions for 500-user broadcasting
        assert total_events_sent >= expected_events * 0.95  # At least 95% events sent
        assert total_deliveries >= expected_deliveries * 0.90  # At least 90% deliveries (accounting for rate limiting)
        assert total_errors <= expected_events * 0.05  # Less than 5% errors
        assert avg_broadcast_time < 0.100  # Less than 100ms average broadcast time
        assert max_broadcast_time < 0.500  # Less than 500ms maximum broadcast time
        assert events_per_second > 10  # More than 10 events/sec overall
        assert deliveries_per_event >= num_users * 0.80  # At least 80% delivery rate per event

        # Resource usage validation
        if resource_stats:
            assert resource_stats['memory_mb']['growth'] < 100  # Less than 100MB growth
            assert resource_stats['cpu_percent']['max'] < 95    # Less than 95% peak CPU

        # System statistics should be healthy
        broadcaster_stats = scalable_broadcaster.get_broadcast_stats()
        assert broadcaster_stats['total_events'] >= total_events_sent
        assert broadcaster_stats['events_delivered'] > 0
        assert broadcaster_stats['avg_delivery_latency_ms'] < 200.0

        print("Broadcasting Performance:")
        print(f"  Events sent: {total_events_sent}/{expected_events}")
        print(f"  Deliveries: {total_deliveries} ({deliveries_per_event:.1f} per event)")
        print(f"  Average broadcast time: {avg_broadcast_time*1000:.1f}ms")
        print(f"  Events per second: {events_per_second:.1f}")
        print(f"  Memory growth: {resource_stats['memory_mb']['growth']:.1f}MB")

    def test_sustained_load_500_users(self, scalable_broadcaster, resource_monitor):
        """Test sustained load performance with 500+ users over time."""
        num_users = 600  # Slightly over 500 for stress testing
        sustained_duration = 10.0  # 10 seconds of sustained load
        event_frequency = 20  # 20 events per second

        user_ids = {f'sustained_user_{i}' for i in range(num_users)}

        # Start resource monitoring
        resource_monitor.start_monitoring()

        print(f"Starting sustained load test: {num_users} users, {sustained_duration}s duration...")

        sustained_start = time.time()
        load_results = []

        def sustained_load_generator() -> dict[str, Any]:
            """Generate sustained event load."""
            generator_result = {
                'events_generated': 0,
                'deliveries': 0,
                'broadcast_times': [],
                'errors': 0,
                'start_time': time.time()
            }

            interval = 1.0 / event_frequency
            end_time = time.time() + sustained_duration

            event_sequence = 0
            while time.time() < end_time:
                cycle_start = time.time()

                try:
                    delivered_count = scalable_broadcaster.broadcast_to_users(
                        event_type='sustained_load_event',
                        event_data={
                            'sequence': event_sequence,
                            'timestamp': time.time(),
                            'user_count': len(user_ids),
                            'target_frequency': event_frequency
                        },
                        user_ids=user_ids,
                        priority=DeliveryPriority.MEDIUM
                    )

                    broadcast_time = time.time() - cycle_start
                    generator_result['events_generated'] += 1
                    generator_result['deliveries'] += delivered_count
                    generator_result['broadcast_times'].append(broadcast_time)
                    event_sequence += 1

                except Exception:
                    generator_result['errors'] += 1

                # Maintain frequency
                elapsed = time.time() - cycle_start
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            generator_result['end_time'] = time.time()
            generator_result['actual_duration'] = generator_result['end_time'] - generator_result['start_time']
            generator_result['actual_frequency'] = generator_result['events_generated'] / generator_result['actual_duration']

            return generator_result

        # Run sustained load with multiple generators for realism
        num_generators = 3
        with ThreadPoolExecutor(max_workers=num_generators) as executor:
            futures = [executor.submit(sustained_load_generator) for _ in range(num_generators)]

            for future in as_completed(futures):
                load_results.append(future.result())

        sustained_duration_actual = time.time() - sustained_start

        # Stop resource monitoring
        resource_stats = resource_monitor.stop_monitoring()

        # Analyze sustained load performance
        total_events = sum(r['events_generated'] for r in load_results)
        total_deliveries = sum(r['deliveries'] for r in load_results)
        total_errors = sum(r['errors'] for r in load_results)

        all_broadcast_times = []
        for result in load_results:
            all_broadcast_times.extend(result['broadcast_times'])

        avg_broadcast_time = sum(all_broadcast_times) / len(all_broadcast_times) if all_broadcast_times else 0
        max_broadcast_time = max(all_broadcast_times) if all_broadcast_times else 0
        overall_frequency = total_events / sustained_duration_actual

        expected_events = num_generators * event_frequency * sustained_duration
        expected_deliveries = expected_events * num_users

        # Sustained load assertions
        assert total_events >= expected_events * 0.80  # At least 80% of target events
        assert total_deliveries >= expected_deliveries * 0.70  # At least 70% deliveries (rate limiting expected)
        assert total_errors <= expected_events * 0.10  # Less than 10% errors
        assert avg_broadcast_time < 0.200  # Less than 200ms average (higher tolerance for sustained load)
        assert max_broadcast_time < 1.000  # Less than 1s maximum
        assert overall_frequency >= event_frequency * num_generators * 0.70  # At least 70% of target frequency

        # Performance should not degrade significantly over time
        # Check early vs late performance
        early_times = all_broadcast_times[:len(all_broadcast_times)//3]
        late_times = all_broadcast_times[-len(all_broadcast_times)//3:]

        if early_times and late_times:
            early_avg = sum(early_times) / len(early_times)
            late_avg = sum(late_times) / len(late_times)
            degradation_ratio = late_avg / early_avg

            assert degradation_ratio < 2.0  # Performance should not degrade more than 2x

        # Resource usage should be stable
        if resource_stats:
            assert resource_stats['memory_mb']['growth'] < 200  # Less than 200MB growth
            assert resource_stats['cpu_percent']['avg'] < 85    # Less than 85% average CPU

        # Final system health check
        health = scalable_broadcaster.get_health_status()
        assert health['status'] in ['healthy', 'warning']  # Should not be in error state

        print("Sustained Load Performance:")
        print(f"  Events generated: {total_events} (target: {expected_events:.0f})")
        print(f"  Overall frequency: {overall_frequency:.1f} events/sec")
        print(f"  Average broadcast time: {avg_broadcast_time*1000:.1f}ms")
        print(f"  Total deliveries: {total_deliveries}")
        print(f"  Memory growth: {resource_stats['memory_mb']['growth']:.1f}MB")
        print(f"  Average CPU: {resource_stats['cpu_percent']['avg']:.1f}%")


class TestScalability4000Tickers:
    """Test scalability under 4,000+ ticker simulation."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for ticker scalability testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()
        return socketio

    @pytest.fixture
    def ticker_broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster optimized for ticker load."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=50,  # Shorter batching for high frequency
            max_events_per_user=500,  # High rate limit for ticker data
            max_batch_size=100  # Large batches for efficiency
        )

    def generate_ticker_symbols(self, count: int) -> list[str]:
        """Generate realistic ticker symbols."""
        # Start with real symbols
        base_symbols = [
            'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
            'ORCL', 'CRM', 'ADBE', 'INTC', 'AMD', 'QCOM', 'AVGO', 'TXN',
            'IBM', 'CSCO', 'VZ', 'T', 'KO', 'PEP', 'WMT', 'HD', 'UNH',
            'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'TMO', 'DHR', 'ABT'
        ]

        symbols = base_symbols.copy()

        # Generate additional symbols to reach target count
        for i in range(count - len(base_symbols)):
            # Create synthetic ticker symbols
            symbol = f"SYM{i:04d}"
            symbols.append(symbol)

        return symbols[:count]

    def test_4000_ticker_event_simulation(self, ticker_broadcaster, resource_monitor):
        """Test event processing with 4,000+ ticker simulation."""
        num_tickers = 4000
        num_users = 200  # Users interested in various tickers
        ticker_events_per_second = 100  # 100 ticker events per second
        simulation_duration = 5.0  # 5 seconds

        # Generate ticker universe
        ticker_symbols = self.generate_ticker_symbols(num_tickers)

        # Create users with varied ticker interests
        user_ticker_interests = {}
        for i in range(num_users):
            user_id = f'ticker_user_{i}'
            # Each user interested in 10-50 random tickers
            num_interests = random.randint(10, 50)
            interested_tickers = random.sample(ticker_symbols, num_interests)
            user_ticker_interests[user_id] = set(interested_tickers)

        # Start resource monitoring
        resource_monitor.start_monitoring()

        print(f"Simulating {num_tickers} tickers with {num_users} users for {simulation_duration}s...")

        simulation_start = time.time()
        simulation_results = []

        def ticker_event_generator(generator_id: int) -> dict[str, Any]:
            """Generate ticker events at high frequency."""
            generator_result = {
                'generator_id': generator_id,
                'events_generated': 0,
                'deliveries': 0,
                'broadcast_times': [],
                'ticker_coverage': set(),
                'errors': 0
            }

            interval = 1.0 / ticker_events_per_second
            end_time = time.time() + simulation_duration

            while time.time() < end_time:
                cycle_start = time.time()

                try:
                    # Select random ticker
                    ticker = random.choice(ticker_symbols)
                    generator_result['ticker_coverage'].add(ticker)

                    # Find users interested in this ticker
                    interested_users = {
                        user_id for user_id, interests in user_ticker_interests.items()
                        if ticker in interests
                    }

                    if interested_users:
                        # Generate ticker event
                        delivered_count = ticker_broadcaster.broadcast_to_users(
                            event_type='ticker_update',
                            event_data={
                                'symbol': ticker,
                                'price': 100.0 + random.uniform(-10.0, 10.0),
                                'volume': random.randint(1000, 100000),
                                'timestamp': time.time(),
                                'generator_id': generator_id
                            },
                            user_ids=interested_users,
                            priority=DeliveryPriority.MEDIUM
                        )

                        broadcast_time = time.time() - cycle_start
                        generator_result['events_generated'] += 1
                        generator_result['deliveries'] += delivered_count
                        generator_result['broadcast_times'].append(broadcast_time)

                except Exception:
                    generator_result['errors'] += 1

                # Maintain frequency
                elapsed = time.time() - cycle_start
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            return generator_result

        # Run multiple generators for realistic load distribution
        num_generators = 4
        with ThreadPoolExecutor(max_workers=num_generators) as executor:
            futures = [
                executor.submit(ticker_event_generator, i)
                for i in range(num_generators)
            ]

            for future in as_completed(futures):
                simulation_results.append(future.result())

        simulation_duration_actual = time.time() - simulation_start

        # Stop resource monitoring
        resource_stats = resource_monitor.stop_monitoring()

        # Analyze ticker simulation performance
        total_events = sum(r['events_generated'] for r in simulation_results)
        total_deliveries = sum(r['deliveries'] for r in simulation_results)
        total_errors = sum(r['errors'] for r in simulation_results)

        all_broadcast_times = []
        all_ticker_coverage = set()
        for result in simulation_results:
            all_broadcast_times.extend(result['broadcast_times'])
            all_ticker_coverage.update(result['ticker_coverage'])

        avg_broadcast_time = sum(all_broadcast_times) / len(all_broadcast_times) if all_broadcast_times else 0
        max_broadcast_time = max(all_broadcast_times) if all_broadcast_times else 0
        events_per_second = total_events / simulation_duration_actual
        ticker_coverage_percent = len(all_ticker_coverage) / num_tickers * 100

        expected_events = num_generators * ticker_events_per_second * simulation_duration

        # Ticker scalability assertions
        assert total_events >= expected_events * 0.70  # At least 70% of target events
        assert total_deliveries > 0  # Some deliveries should occur
        assert total_errors <= expected_events * 0.20  # Less than 20% errors
        assert avg_broadcast_time < 0.100  # Less than 100ms average broadcast time
        assert max_broadcast_time < 0.500  # Less than 500ms maximum
        assert events_per_second >= ticker_events_per_second * num_generators * 0.60  # At least 60% of target rate
        assert ticker_coverage_percent >= 10.0  # At least 10% of tickers covered

        # System should handle ticker volume without excessive resource usage
        if resource_stats:
            assert resource_stats['memory_mb']['growth'] < 300  # Less than 300MB growth
            assert resource_stats['cpu_percent']['max'] < 95    # Less than 95% peak CPU

        # Broadcasting system should remain healthy
        broadcaster_stats = ticker_broadcaster.get_broadcast_stats()
        assert broadcaster_stats['avg_delivery_latency_ms'] < 200.0
        assert broadcaster_stats['delivery_success_rate_percent'] > 60.0

        print("Ticker Simulation Performance:")
        print(f"  Tickers: {num_tickers}, Users: {num_users}")
        print(f"  Events generated: {total_events} ({events_per_second:.1f}/sec)")
        print(f"  Ticker coverage: {len(all_ticker_coverage)}/{num_tickers} ({ticker_coverage_percent:.1f}%)")
        print(f"  Deliveries: {total_deliveries}")
        print(f"  Average broadcast time: {avg_broadcast_time*1000:.1f}ms")
        print(f"  Memory usage: {resource_stats['memory_mb']['max']:.1f}MB peak")


class TestBatchOptimizationAtScale:
    """Test batch optimization effectiveness at scale."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for batch optimization testing."""
        socketio = Mock()
        socketio.emit = Mock()
        socketio.server = Mock()

        # Track batch vs individual emissions
        socketio._batch_emissions = 0
        socketio._individual_emissions = 0
        socketio._emit_lock = threading.Lock()

        def track_emissions(event_type, *args, **kwargs):
            with socketio._emit_lock:
                if event_type == 'event_batch':
                    socketio._batch_emissions += 1
                else:
                    socketio._individual_emissions += 1

        socketio.emit.side_effect = track_emissions
        return socketio

    @pytest.fixture
    def batch_broadcaster(self, mock_socketio):
        """Create ScalableBroadcaster for batch optimization testing."""
        return ScalableBroadcaster(
            socketio=mock_socketio,
            batch_window_ms=100,  # 100ms batching window
            max_events_per_user=300,
            max_batch_size=50
        )

    def test_batch_efficiency_at_scale(self, batch_broadcaster, mock_socketio, resource_monitor):
        """Test batching efficiency with large user base."""
        num_users = 800  # Large user base
        events_per_user = 20

        # Start resource monitoring
        resource_monitor.start_monitoring()

        print(f"Testing batch efficiency with {num_users} users, {events_per_user} events per user...")

        batch_test_start = time.time()

        # Generate high volume of events that should be batched efficiently
        def batch_efficiency_worker(worker_id: int, users_per_worker: int) -> dict[str, Any]:
            """Worker that generates events for batching efficiency testing."""
            worker_result = {
                'worker_id': worker_id,
                'events_sent': 0,
                'deliveries': 0,
                'errors': 0
            }

            # Create user set for this worker
            worker_users = {
                f'batch_user_{worker_id}_{i}' for i in range(users_per_worker)
            }

            for event_num in range(events_per_user):
                try:
                    delivered_count = batch_broadcaster.broadcast_to_users(
                        event_type=f'batch_efficiency_event_{event_num}',
                        event_data={
                            'worker_id': worker_id,
                            'event_num': event_num,
                            'timestamp': time.time(),
                            'user_count': len(worker_users)
                        },
                        user_ids=worker_users,
                        priority=DeliveryPriority.MEDIUM
                    )

                    worker_result['events_sent'] += 1
                    worker_result['deliveries'] += delivered_count

                except Exception:
                    worker_result['errors'] += 1

                # Brief pause to allow batching
                time.sleep(0.005)  # 5ms between events

            return worker_result

        # Distribute users across workers for parallel event generation
        num_workers = 20
        users_per_worker = num_users // num_workers

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(batch_efficiency_worker, i, users_per_worker)
                for i in range(num_workers)
            ]

            worker_results = []
            for future in as_completed(futures):
                worker_results.append(future.result())

        # Allow time for all batches to be delivered
        time.sleep(1.0)
        batch_broadcaster.flush_all_batches()
        time.sleep(0.5)

        batch_test_duration = time.time() - batch_test_start

        # Stop resource monitoring
        resource_stats = resource_monitor.stop_monitoring()

        # Analyze batch efficiency
        total_events_sent = sum(r['events_sent'] for r in worker_results)
        total_deliveries = sum(r['deliveries'] for r in worker_results)
        total_errors = sum(r['errors'] for r in worker_results)

        # Get emission statistics
        batch_emissions = mock_socketio._batch_emissions
        individual_emissions = mock_socketio._individual_emissions
        total_emissions = batch_emissions + individual_emissions

        # Get broadcaster statistics
        broadcaster_stats = batch_broadcaster.get_broadcast_stats()

        expected_events = num_workers * events_per_user
        expected_deliveries = expected_events * users_per_worker

        # Batch efficiency assertions
        assert total_events_sent >= expected_events * 0.95  # At least 95% events sent
        assert total_deliveries >= expected_deliveries * 0.80  # At least 80% deliveries
        assert total_errors <= expected_events * 0.05  # Less than 5% errors

        # Batching efficiency validation
        if total_emissions > 0:
            batch_ratio = batch_emissions / total_emissions
            assert batch_ratio >= 0.70  # At least 70% should be batched

            # Batch size efficiency
            if batch_emissions > 0 and broadcaster_stats['events_delivered'] > 0:
                avg_events_per_emission = broadcaster_stats['events_delivered'] / batch_emissions
                assert avg_events_per_emission >= 5.0  # At least 5 events per batch on average

        # Performance should benefit from batching
        assert broadcaster_stats['avg_delivery_latency_ms'] < 150.0  # Should be efficient
        assert broadcaster_stats['batch_efficiency'] >= 10.0  # Good batch efficiency

        # Resource usage should be reasonable with batching
        if resource_stats:
            assert resource_stats['memory_mb']['growth'] < 400  # Less than 400MB growth

        print("Batch Efficiency Results:")
        print(f"  Events sent: {total_events_sent}, Deliveries: {total_deliveries}")
        print(f"  Batch emissions: {batch_emissions}, Individual: {individual_emissions}")
        print(f"  Batch ratio: {batch_ratio*100:.1f}%" if total_emissions > 0 else "  No emissions recorded")
        print(f"  Batch efficiency: {broadcaster_stats['batch_efficiency']:.1f} events/batch")
        print(f"  Average delivery latency: {broadcaster_stats['avg_delivery_latency_ms']:.1f}ms")

    def test_batch_optimization_under_load(self, batch_broadcaster):
        """Test batch optimization effectiveness under varying load."""
        load_scenarios = [
            (50, 10, "Low load"),      # 50 users, 10 events each
            (200, 25, "Medium load"),  # 200 users, 25 events each
            (500, 40, "High load"),    # 500 users, 40 events each
            (100, 15, "Recovery")      # 100 users, 15 events each
        ]

        scenario_results = []

        for num_users, events_per_user, scenario_name in load_scenarios:
            print(f"Testing batch optimization: {scenario_name} ({num_users} users, {events_per_user} events)")

            scenario_start = time.time()

            # Generate load for this scenario
            user_ids = {f'optimization_user_{scenario_name}_{i}' for i in range(num_users)}

            events_sent = 0
            broadcast_times = []

            for event_num in range(events_per_user):
                event_start = time.time()

                delivered_count = batch_broadcaster.broadcast_to_users(
                    event_type=f'optimization_event_{scenario_name}_{event_num}',
                    event_data={
                        'scenario': scenario_name,
                        'event_num': event_num,
                        'user_count': num_users,
                        'timestamp': time.time()
                    },
                    user_ids=user_ids,
                    priority=DeliveryPriority.MEDIUM
                )

                if delivered_count > 0:
                    events_sent += 1

                broadcast_times.append(time.time() - event_start)

                # Small delay for batching
                time.sleep(0.002)

            # Force batch delivery and measure
            flush_start = time.time()
            batch_broadcaster.flush_all_batches()
            flush_duration = time.time() - flush_start

            scenario_duration = time.time() - scenario_start
            avg_broadcast_time = sum(broadcast_times) / len(broadcast_times) if broadcast_times else 0

            # Get broadcaster stats for this scenario
            scenario_stats = batch_broadcaster.get_broadcast_stats()

            scenario_results.append({
                'scenario': scenario_name,
                'num_users': num_users,
                'events_per_user': events_per_user,
                'events_sent': events_sent,
                'scenario_duration': scenario_duration,
                'avg_broadcast_time': avg_broadcast_time,
                'flush_duration': flush_duration,
                'batch_efficiency': scenario_stats['batch_efficiency'],
                'avg_delivery_latency': scenario_stats['avg_delivery_latency_ms']
            })

            time.sleep(0.1)  # Brief pause between scenarios

        # Analyze batch optimization across load scenarios
        for i, result in enumerate(scenario_results):
            scenario = result['scenario']

            # Each scenario should complete efficiently
            assert result['events_sent'] >= result['events_per_user'] * 0.90  # At least 90% events
            assert result['avg_broadcast_time'] < 0.200  # Less than 200ms average
            assert result['flush_duration'] < 2.0  # Flush should complete quickly
            assert result['batch_efficiency'] >= 5.0  # Good batching efficiency
            assert result['avg_delivery_latency'] < 200.0  # Reasonable delivery latency

            print(f"  {scenario}: {result['events_sent']} events, "
                  f"{result['avg_broadcast_time']*1000:.1f}ms avg, "
                  f"{result['batch_efficiency']:.1f} batch efficiency")

        # Performance should remain stable across scenarios
        latencies = [r['avg_delivery_latency'] for r in scenario_results]
        if len(latencies) > 1:
            max_latency = max(latencies)
            min_latency = min(latencies)
            latency_variation = max_latency / min_latency if min_latency > 0 else 1

            # Performance variation should be reasonable
            assert latency_variation < 3.0  # Less than 3x variation across load scenarios


if __name__ == '__main__':
    # Example of running scalability tests
    pytest.main([__file__ + "::TestScalability500Users::test_500_users_concurrent_broadcasting", "-v", "-s"])
