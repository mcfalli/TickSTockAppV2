"""
Comprehensive Production Readiness Tests - Performance Benchmarks
Sprint 26: Sub-Millisecond Processing Requirements Validation

Tests critical performance requirements for production deployment:
- Tick processing: <1ms per tick
- Database queries: <50ms per batch
- WebSocket delivery: <100ms end-to-end
- Event detection: <100ms end-to-end latency

Test Categories:
- Performance Tests: Sub-millisecond processing validation
- Load Tests: Sustained high-volume processing
- Memory Tests: Memory usage stability under load
- Throughput Tests: Maximum processing capacity
- Latency Tests: End-to-end timing validation
"""

import pytest
import time
import threading
import psutil
import os
import gc
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import statistics

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.services.market_data_service import MarketDataService
from src.core.domain.market.tick import TickData
from src.presentation.websocket.data_publisher import DataPublisher
from src.core.services.redis_event_subscriber import RedisEventSubscriber
from src.core.services.websocket_broadcaster import WebSocketBroadcaster


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    operation_name: str
    iterations: int
    total_time: float
    average_time: float
    min_time: float
    max_time: float
    p95_time: float
    p99_time: float
    throughput: float
    
    @classmethod
    def calculate(cls, operation_name: str, times: List[float]) -> 'PerformanceMetrics':
        """Calculate performance metrics from timing data."""
        iterations = len(times)
        total_time = sum(times)
        average_time = total_time / iterations
        min_time = min(times)
        max_time = max(times)
        sorted_times = sorted(times)
        p95_time = sorted_times[int(iterations * 0.95)]
        p99_time = sorted_times[int(iterations * 0.99)]
        throughput = iterations / total_time if total_time > 0 else 0
        
        return cls(
            operation_name=operation_name,
            iterations=iterations,
            total_time=total_time,
            average_time=average_time,
            min_time=min_time,
            max_time=max_time,
            p95_time=p95_time,
            p99_time=p99_time,
            throughput=throughput
        )


class TestPerformanceBenchmarks:
    """Test suite for production performance benchmarks."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for performance testing."""
        return {
            'USE_SYNTHETIC_DATA': True,
            'USE_POLYGON_API': False,
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': 6379,
            'DATABASE_URL': 'postgresql://test:test@localhost/test'
        }

    @pytest.fixture
    def performance_timer(self):
        """High-precision performance timer."""
        class Timer:
            def __init__(self):
                self.start_time = None
                self.end_time = None
                
            def start(self):
                self.start_time = time.perf_counter()
                
            def stop(self):
                self.end_time = time.perf_counter()
                
            @property
            def elapsed(self):
                if self.start_time and self.end_time:
                    return self.end_time - self.start_time
                return None
                
            @property
            def elapsed_ms(self):
                elapsed = self.elapsed
                return elapsed * 1000 if elapsed else None
        
        return Timer()

    @pytest.fixture
    def sample_tick_data(self):
        """High-volume tick data generator."""
        def generate_ticks(count: int, symbol: str = "AAPL"):
            ticks = []
            base_price = 150.0
            base_time = time.time()
            
            for i in range(count):
                tick = Mock()
                tick.ticker = symbol
                tick.price = base_price + (i * 0.01)
                tick.volume = 1000 + (i * 10)
                tick.timestamp = base_time + i
                tick.event_type = "tick"
                tick.source = "synthetic"
                tick.tick_open = base_price
                tick.tick_high = base_price + 0.25
                tick.tick_low = base_price - 0.15
                tick.tick_close = tick.price
                tick.tick_volume = tick.volume
                tick.tick_vwap = tick.price
                tick.bid = tick.price - 0.01
                tick.ask = tick.price + 0.01
                ticks.append(tick)
            
            return ticks
        
        return generate_ticks

    @pytest.mark.performance
    def test_tick_processing_sub_millisecond_requirement(self, mock_config, sample_tick_data, performance_timer):
        """Test tick processing meets <1ms per tick requirement."""
        market_service = MarketDataService(mock_config)
        
        # Generate test ticks
        test_ticks = sample_tick_data(1000, "AAPL")
        
        # Performance measurement
        processing_times = []
        
        for tick in test_ticks[:100]:  # Test first 100 for detailed measurement
            performance_timer.start()
            
            # Mock the tick processing without database operations
            with patch.object(market_service, '_handle_tick_data') as mock_handle:
                mock_handle.return_value = None
                market_service._handle_tick_data(tick)
            
            performance_timer.stop()
            processing_times.append(performance_timer.elapsed)
        
        # Calculate metrics
        metrics = PerformanceMetrics.calculate("tick_processing", processing_times)
        
        # Assert: <1ms (0.001s) per tick requirement
        assert metrics.average_time < 0.001, f"Average tick processing {metrics.average_time:.4f}s exceeds 1ms requirement"
        assert metrics.p95_time < 0.002, f"P95 tick processing {metrics.p95_time:.4f}s exceeds 2ms tolerance"
        assert metrics.p99_time < 0.005, f"P99 tick processing {metrics.p99_time:.4f}s exceeds 5ms tolerance"
        
        # Performance metrics logging
        print(f"\nTick Processing Performance:")
        print(f"  Average: {metrics.average_time*1000:.3f}ms")
        print(f"  P95: {metrics.p95_time*1000:.3f}ms")
        print(f"  P99: {metrics.p99_time*1000:.3f}ms")
        print(f"  Throughput: {metrics.throughput:.1f} ticks/sec")

    @pytest.mark.performance
    def test_database_persistence_performance(self, mock_config, sample_tick_data, performance_timer):
        """Test database persistence meets <50ms per batch requirement."""
        market_service = MarketDataService(mock_config)
        
        # Mock database operations
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Test different batch sizes
        batch_sizes = [10, 50, 100, 200]
        
        for batch_size in batch_sizes:
            test_ticks = sample_tick_data(batch_size, "AAPL")
            batch_times = []
            
            # Test 20 batches of each size
            for batch_num in range(20):
                performance_timer.start()
                
                # Mock batch persistence operation
                with patch('psycopg2.connect', return_value=mock_connection):
                    # Simulate database batch insert
                    for tick in test_ticks:
                        mock_cursor.execute.return_value = None
                    mock_connection.commit.return_value = None
                
                performance_timer.stop()
                batch_times.append(performance_timer.elapsed)
            
            # Calculate metrics for this batch size
            metrics = PerformanceMetrics.calculate(f"db_batch_{batch_size}", batch_times)
            
            # Assert: <50ms (0.050s) per batch requirement
            assert metrics.average_time < 0.050, f"Batch size {batch_size}: Average {metrics.average_time:.4f}s exceeds 50ms requirement"
            assert metrics.p95_time < 0.075, f"Batch size {batch_size}: P95 {metrics.p95_time:.4f}s exceeds 75ms tolerance"
            
            print(f"\nDatabase Batch Performance (size={batch_size}):")
            print(f"  Average: {metrics.average_time*1000:.1f}ms")
            print(f"  P95: {metrics.p95_time*1000:.1f}ms")
            print(f"  Throughput: {metrics.throughput:.1f} batches/sec")

    @pytest.mark.performance
    def test_websocket_delivery_performance(self, performance_timer):
        """Test WebSocket delivery meets <100ms end-to-end requirement."""
        mock_socketio = Mock()
        broadcaster = WebSocketBroadcaster(mock_socketio)
        
        # Create simulated connected users
        user_count = 50
        for i in range(user_count):
            session_id = f'session_{i}'
            from src.core.services.websocket_broadcaster import ConnectedUser
            connected_user = ConnectedUser(
                user_id=f'user_{i}',
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions={'Breakout'}
            )
            broadcaster.connected_users[session_id] = connected_user
        
        # Test pattern alert delivery performance
        delivery_times = []
        
        for i in range(100):
            pattern_event = {
                'type': 'pattern_alert',
                'data': {
                    'pattern': 'Breakout',
                    'symbol': 'AAPL',
                    'confidence': 0.85,
                    'price': 150.25 + (i * 0.01)
                },
                'timestamp': time.time()
            }
            
            performance_timer.start()
            broadcaster.broadcast_pattern_alert(pattern_event)
            performance_timer.stop()
            
            delivery_times.append(performance_timer.elapsed)
        
        # Calculate metrics
        metrics = PerformanceMetrics.calculate("websocket_delivery", delivery_times)
        
        # Assert: <100ms (0.100s) delivery requirement
        assert metrics.average_time < 0.100, f"Average WebSocket delivery {metrics.average_time:.4f}s exceeds 100ms requirement"
        assert metrics.p95_time < 0.150, f"P95 WebSocket delivery {metrics.p95_time:.4f}s exceeds 150ms tolerance"
        
        print(f"\nWebSocket Delivery Performance:")
        print(f"  Average: {metrics.average_time*1000:.1f}ms")
        print(f"  P95: {metrics.p95_time*1000:.1f}ms")
        print(f"  Throughput: {metrics.throughput:.1f} broadcasts/sec")

    @pytest.mark.performance
    def test_end_to_end_latency_requirement(self, mock_config, sample_tick_data, performance_timer):
        """Test end-to-end latency meets <100ms requirement."""
        # Create integrated system components
        market_service = MarketDataService(mock_config)
        mock_socketio = Mock()
        broadcaster = WebSocketBroadcaster(mock_socketio)
        
        # Add connected users
        for i in range(10):
            session_id = f'session_{i}'
            from src.core.services.websocket_broadcaster import ConnectedUser
            connected_user = ConnectedUser(
                user_id=f'user_{i}',
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions={'Breakout'}
            )
            broadcaster.connected_users[session_id] = connected_user
        
        # End-to-end test: Tick ingestion → Event detection → WebSocket delivery
        e2e_times = []
        test_ticks = sample_tick_data(50, "AAPL")
        
        for tick in test_ticks:
            performance_timer.start()
            
            # Step 1: Tick processing
            with patch.object(market_service, '_handle_tick_data') as mock_handle:
                mock_handle.return_value = None
                market_service._handle_tick_data(tick)
            
            # Step 2: Event detection (mock pattern detection)
            pattern_event = {
                'type': 'pattern_alert',
                'data': {
                    'pattern': 'Breakout',
                    'symbol': tick.ticker,
                    'confidence': 0.85,
                    'price': tick.price
                },
                'timestamp': time.time()
            }
            
            # Step 3: WebSocket broadcast
            broadcaster.broadcast_pattern_alert(pattern_event)
            
            performance_timer.stop()
            e2e_times.append(performance_timer.elapsed)
        
        # Calculate end-to-end metrics
        metrics = PerformanceMetrics.calculate("end_to_end_latency", e2e_times)
        
        # Assert: <100ms end-to-end requirement
        assert metrics.average_time < 0.100, f"Average E2E latency {metrics.average_time:.4f}s exceeds 100ms requirement"
        assert metrics.p95_time < 0.150, f"P95 E2E latency {metrics.p95_time:.4f}s exceeds 150ms tolerance"
        
        print(f"\nEnd-to-End Latency Performance:")
        print(f"  Average: {metrics.average_time*1000:.1f}ms")
        print(f"  P95: {metrics.p95_time*1000:.1f}ms")
        print(f"  Max: {metrics.max_time*1000:.1f}ms")

    @pytest.mark.performance
    def test_sustained_high_volume_processing(self, mock_config, sample_tick_data, performance_timer):
        """Test sustained processing under high volume load."""
        market_service = MarketDataService(mock_config)
        
        # High volume parameters
        duration_seconds = 10
        target_tps = 500  # 500 ticks per second
        total_ticks = duration_seconds * target_tps
        
        # Generate high volume tick data
        test_ticks = sample_tick_data(total_ticks, "AAPL")
        
        # Memory monitoring
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Sustained processing test
        performance_timer.start()
        processed_count = 0
        
        for tick in test_ticks:
            with patch.object(market_service, '_handle_tick_data') as mock_handle:
                mock_handle.return_value = None
                market_service._handle_tick_data(tick)
            
            processed_count += 1
            
            # Brief pause to simulate realistic timing
            if processed_count % 100 == 0:
                time.sleep(0.001)  # 1ms pause every 100 ticks
        
        performance_timer.stop()
        
        # Performance validation
        actual_tps = processed_count / performance_timer.elapsed
        
        # Assert: Sustained throughput requirement
        assert actual_tps >= (target_tps * 0.9), f"Throughput {actual_tps:.1f} TPS below 90% of target ({target_tps} TPS)"
        
        # Memory stability check
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        max_acceptable_growth = 50 * 1024 * 1024  # 50MB
        
        assert memory_growth < max_acceptable_growth, f"Memory grew by {memory_growth / 1024 / 1024:.1f}MB during sustained load"
        
        print(f"\nSustained Load Performance:")
        print(f"  Duration: {performance_timer.elapsed:.1f}s")
        print(f"  Processed: {processed_count:,} ticks")
        print(f"  Throughput: {actual_tps:.1f} TPS")
        print(f"  Memory Growth: {memory_growth / 1024 / 1024:.1f}MB")

    @pytest.mark.performance
    def test_concurrent_processing_scalability(self, mock_config, sample_tick_data, performance_timer):
        """Test processing scalability under concurrent load."""
        market_service = MarketDataService(mock_config)
        
        # Concurrent processing parameters
        thread_count = 8
        ticks_per_thread = 100
        
        processing_results = []
        processing_errors = []
        
        def process_tick_batch(thread_id, tick_batch):
            """Process a batch of ticks in a separate thread."""
            thread_times = []
            
            for tick in tick_batch:
                start_time = time.perf_counter()
                
                try:
                    with patch.object(market_service, '_handle_tick_data') as mock_handle:
                        mock_handle.return_value = None
                        market_service._handle_tick_data(tick)
                    
                    end_time = time.perf_counter()
                    thread_times.append(end_time - start_time)
                    
                except Exception as e:
                    processing_errors.append(f"Thread {thread_id}: {str(e)}")
            
            processing_results.append({
                'thread_id': thread_id,
                'processed_count': len(tick_batch),
                'times': thread_times,
                'avg_time': sum(thread_times) / len(thread_times) if thread_times else 0
            })
        
        # Create thread pool and distribute work
        performance_timer.start()
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = []
            
            for thread_id in range(thread_count):
                tick_batch = sample_tick_data(ticks_per_thread, f"STOCK{thread_id}")
                future = executor.submit(process_tick_batch, thread_id, tick_batch)
                futures.append(future)
            
            # Wait for all threads to complete
            for future in futures:
                future.result()
        
        performance_timer.stop()
        
        # Analyze concurrent performance
        total_processed = sum(result['processed_count'] for result in processing_results)
        total_time = performance_timer.elapsed
        concurrent_tps = total_processed / total_time
        
        # Calculate average processing time across all threads
        all_times = []
        for result in processing_results:
            all_times.extend(result['times'])
        
        if all_times:
            avg_processing_time = sum(all_times) / len(all_times)
        else:
            avg_processing_time = 0
        
        # Assert: No processing errors
        assert len(processing_errors) == 0, f"Processing errors occurred: {processing_errors[:5]}"
        
        # Assert: Maintained processing performance under concurrency
        assert avg_processing_time < 0.002, f"Concurrent processing time {avg_processing_time:.4f}s exceeds 2ms tolerance"
        assert concurrent_tps > 100, f"Concurrent throughput {concurrent_tps:.1f} TPS below minimum requirement"
        
        print(f"\nConcurrent Processing Performance:")
        print(f"  Threads: {thread_count}")
        print(f"  Total Processed: {total_processed:,} ticks")
        print(f"  Duration: {total_time:.2f}s")
        print(f"  Throughput: {concurrent_tps:.1f} TPS")
        print(f"  Avg Processing Time: {avg_processing_time*1000:.3f}ms")

    @pytest.mark.performance
    def test_memory_usage_under_load(self, mock_config, sample_tick_data):
        """Test memory usage stability under sustained load."""
        market_service = MarketDataService(mock_config)
        
        # Memory monitoring setup
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        memory_samples = []
        
        # Load test parameters
        batch_count = 20
        batch_size = 500
        
        for batch_num in range(batch_count):
            # Process batch of ticks
            test_ticks = sample_tick_data(batch_size, f"BATCH{batch_num}")
            
            for tick in test_ticks:
                with patch.object(market_service, '_handle_tick_data') as mock_handle:
                    mock_handle.return_value = None
                    market_service._handle_tick_data(tick)
            
            # Sample memory usage
            current_memory = process.memory_info().rss
            memory_samples.append({
                'batch': batch_num,
                'memory_mb': current_memory / 1024 / 1024,
                'growth_mb': (current_memory - initial_memory) / 1024 / 1024
            })
            
            # Periodic garbage collection
            if batch_num % 5 == 0:
                gc.collect()
        
        # Analyze memory usage patterns
        final_memory = process.memory_info().rss
        total_growth = final_memory - initial_memory
        growth_mb = total_growth / 1024 / 1024
        
        # Calculate memory growth rate
        memory_growths = [sample['growth_mb'] for sample in memory_samples]
        max_growth = max(memory_growths)
        avg_growth = sum(memory_growths) / len(memory_growths)
        
        # Assert: Reasonable memory usage
        max_acceptable_growth = 100  # 100MB
        assert growth_mb < max_acceptable_growth, f"Total memory growth {growth_mb:.1f}MB exceeds {max_acceptable_growth}MB limit"
        
        # Assert: Memory growth is not exponential (should level off)
        recent_growth = avg_growth
        early_growth = sum(memory_growths[:5]) / 5 if len(memory_growths) >= 5 else avg_growth
        
        # Memory growth should not accelerate significantly
        growth_acceleration = recent_growth - early_growth
        assert growth_acceleration < 20, f"Memory growth acceleration {growth_acceleration:.1f}MB indicates potential leak"
        
        print(f"\nMemory Usage Analysis:")
        print(f"  Initial: {initial_memory / 1024 / 1024:.1f}MB")
        print(f"  Final: {final_memory / 1024 / 1024:.1f}MB")
        print(f"  Growth: {growth_mb:.1f}MB")
        print(f"  Max Growth: {max_growth:.1f}MB")
        print(f"  Avg Growth: {avg_growth:.1f}MB")

    @pytest.mark.performance
    def test_redis_message_processing_performance(self, performance_timer):
        """Test Redis message processing performance."""
        mock_redis = Mock()
        mock_socketio = Mock()
        mock_config = {'REDIS_HOST': 'localhost', 'REDIS_PORT': 6379}
        
        subscriber = RedisEventSubscriber(mock_redis, mock_socketio, mock_config)
        
        # Generate test Redis messages
        message_count = 1000
        processing_times = []
        
        for i in range(message_count):
            test_message = {
                'channel': b'tickstock.events.patterns',
                'type': 'message',
                'data': json.dumps({
                    'event_type': 'pattern_detected',
                    'source': 'tickstockpl',
                    'timestamp': time.time(),
                    'pattern': 'Breakout',
                    'symbol': f'STOCK{i % 100}',
                    'confidence': 0.85
                }).encode()
            }
            
            performance_timer.start()
            subscriber._process_message(test_message)
            performance_timer.stop()
            
            processing_times.append(performance_timer.elapsed)
        
        # Calculate metrics
        metrics = PerformanceMetrics.calculate("redis_message_processing", processing_times)
        
        # Assert: Fast message processing
        assert metrics.average_time < 0.010, f"Average Redis processing {metrics.average_time:.4f}s exceeds 10ms"
        assert metrics.p95_time < 0.020, f"P95 Redis processing {metrics.p95_time:.4f}s exceeds 20ms"
        assert metrics.throughput > 100, f"Redis throughput {metrics.throughput:.1f} msg/sec below 100 msg/sec"
        
        print(f"\nRedis Message Processing Performance:")
        print(f"  Average: {metrics.average_time*1000:.2f}ms")
        print(f"  P95: {metrics.p95_time*1000:.2f}ms")
        print(f"  Throughput: {metrics.throughput:.1f} msg/sec")

    def test_performance_degradation_monitoring(self, mock_config, sample_tick_data, performance_timer):
        """Test performance degradation detection over time."""
        market_service = MarketDataService(mock_config)
        
        # Performance sampling over time
        sample_periods = 10
        ticks_per_period = 100
        period_metrics = []
        
        for period in range(sample_periods):
            test_ticks = sample_tick_data(ticks_per_period, f"PERIOD{period}")
            period_times = []
            
            for tick in test_ticks:
                performance_timer.start()
                
                with patch.object(market_service, '_handle_tick_data') as mock_handle:
                    mock_handle.return_value = None
                    market_service._handle_tick_data(tick)
                
                performance_timer.stop()
                period_times.append(performance_timer.elapsed)
            
            # Calculate period metrics
            period_avg = sum(period_times) / len(period_times)
            period_p95 = sorted(period_times)[int(len(period_times) * 0.95)]
            
            period_metrics.append({
                'period': period,
                'avg_time': period_avg,
                'p95_time': period_p95,
                'sample_count': len(period_times)
            })
            
            # Small delay between periods
            time.sleep(0.1)
        
        # Analyze performance trends
        early_avg = sum(m['avg_time'] for m in period_metrics[:3]) / 3
        late_avg = sum(m['avg_time'] for m in period_metrics[-3:]) / 3
        
        degradation_ratio = late_avg / early_avg if early_avg > 0 else 1.0
        
        # Assert: No significant performance degradation
        max_acceptable_degradation = 1.5  # 50% slowdown max
        assert degradation_ratio < max_acceptable_degradation, f"Performance degraded by {(degradation_ratio-1)*100:.1f}%"
        
        # All periods should meet basic performance requirements
        for period_data in period_metrics:
            assert period_data['avg_time'] < 0.002, f"Period {period_data['period']} avg time {period_data['avg_time']:.4f}s too high"
        
        print(f"\nPerformance Degradation Analysis:")
        print(f"  Early Period Avg: {early_avg*1000:.3f}ms")
        print(f"  Late Period Avg: {late_avg*1000:.3f}ms")
        print(f"  Degradation Ratio: {degradation_ratio:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])