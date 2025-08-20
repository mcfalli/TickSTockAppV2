"""
Unit tests for ChannelMetrics system.

Tests comprehensive metrics tracking including:
- Thread-safe performance monitoring
- Health status calculations
- Metrics aggregation and reporting
- Time-series data tracking

Sprint 105: Core Channel Infrastructure Testing
"""

import pytest
import time
import threading
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

from src.processing.channels.channel_metrics import (
    ChannelMetrics,
    ChannelHealthStatus,
    MetricsSnapshot,
    ChannelStatus
)


class TestChannelMetricsBasicFunctionality:
    """Test basic metrics functionality"""

    @pytest.fixture
    def metrics(self):
        return ChannelMetrics("test_channel", "test_id_123")

    def test_metrics_initialization(self, metrics):
        """Test metrics proper initialization"""
        assert metrics.channel_name == "test_channel"
        assert metrics.channel_id == "test_id_123"
        assert metrics.processed_count == 0
        assert metrics.error_count == 0
        assert metrics.avg_processing_time_ms == 0.0
        assert metrics.start_time is None

    def test_increment_processed_count(self, metrics):
        """Test processed count increment"""
        initial_count = metrics.processed_count
        
        metrics.increment_processed_count()
        assert metrics.processed_count == initial_count + 1
        
        metrics.increment_processed_count(5)
        assert metrics.processed_count == initial_count + 6

    def test_increment_error_count(self, metrics):
        """Test error count increment"""
        initial_count = metrics.error_count
        
        metrics.increment_error_count()
        assert metrics.error_count == initial_count + 1
        
        metrics.increment_error_count(3)
        assert metrics.error_count == initial_count + 4

    def test_update_processing_time(self, metrics):
        """Test processing time updates"""
        # First update
        metrics.update_processing_time(50.0)
        assert metrics.avg_processing_time_ms == 50.0
        
        # Second update should calculate average
        metrics.update_processing_time(100.0)
        assert metrics.avg_processing_time_ms == 75.0
        
        # Third update
        metrics.update_processing_time(25.0)
        expected_avg = (50.0 + 100.0 + 25.0) / 3
        assert abs(metrics.avg_processing_time_ms - expected_avg) < 0.001

    def test_mark_started_stopped(self, metrics):
        """Test start and stop time tracking"""
        assert metrics.start_time is None
        assert metrics.stop_time is None
        
        metrics.mark_started()
        assert metrics.start_time is not None
        assert metrics.stop_time is None
        
        time.sleep(0.01)  # Small delay
        
        metrics.mark_stopped()
        assert metrics.stop_time is not None
        assert metrics.stop_time > metrics.start_time

    def test_uptime_calculation(self, metrics):
        """Test uptime calculation"""
        # Not started yet
        assert metrics.get_uptime_seconds() == 0.0
        
        metrics.mark_started()
        time.sleep(0.05)
        
        uptime = metrics.get_uptime_seconds()
        assert uptime >= 0.04  # Account for timing precision
        assert uptime < 1.0    # Reasonable upper bound


class TestChannelMetricsAdvancedTracking:
    """Test advanced metrics tracking features"""

    @pytest.fixture
    def metrics(self):
        return ChannelMetrics("advanced_test", "adv_123")

    def test_events_generated_tracking(self, metrics):
        """Test event generation tracking"""
        metrics.increment_events_generated(5)
        assert metrics.events_generated == 5
        
        metrics.increment_events_generated(3)
        assert metrics.events_generated == 8

    def test_queue_overflow_tracking(self, metrics):
        """Test queue overflow tracking"""
        metrics.increment_queue_overflows()
        assert metrics.queue_overflows == 1
        
        metrics.increment_queue_overflows(2)
        assert metrics.queue_overflows == 3

    def test_circuit_breaker_metrics(self, metrics):
        """Test circuit breaker metrics tracking"""
        # Circuit breaker opens
        metrics.increment_circuit_breaker_opens()
        assert metrics.circuit_breaker_opens == 1
        
        metrics.increment_circuit_breaker_opens(2)
        assert metrics.circuit_breaker_opens == 3
        
        # Circuit breaker closes
        metrics.increment_circuit_breaker_closes()
        assert metrics.circuit_breaker_closes == 1
        
        # Rejections while open
        metrics.increment_circuit_breaker_rejections(5)
        assert metrics.circuit_breaker_rejections == 5

    def test_batch_processing_metrics(self, metrics):
        """Test batch processing metrics"""
        metrics.increment_batches_processed()
        assert metrics.batches_processed == 1
        
        metrics.increment_batch_failures()
        assert metrics.batch_failures == 1
        
        # Calculate batch success rate
        metrics.increment_batches_processed(9)  # Total 10 batches
        metrics.increment_batch_failures(1)     # Total 2 failures
        
        success_rate = metrics.get_batch_success_rate()
        assert success_rate == 0.8  # 8/10 = 80%

    def test_batch_success_rate_edge_cases(self, metrics):
        """Test batch success rate edge cases"""
        # No batches processed
        assert metrics.get_batch_success_rate() == 1.0
        
        # All failures
        metrics.increment_batches_processed(5)
        metrics.increment_batch_failures(5)
        assert metrics.get_batch_success_rate() == 0.0


class TestChannelMetricsThreadSafety:
    """Test thread safety of metrics operations"""

    @pytest.fixture
    def metrics(self):
        return ChannelMetrics("thread_test", "thread_123")

    def test_concurrent_counter_updates(self, metrics):
        """Test thread-safe counter updates"""
        def increment_counters():
            for _ in range(100):
                metrics.increment_processed_count()
                metrics.increment_error_count()
                metrics.increment_events_generated(2)
        
        # Run concurrent increments
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(increment_counters) for _ in range(5)]
            for future in futures:
                future.result()
        
        # Verify all increments were counted
        assert metrics.processed_count == 500  # 5 threads * 100 increments
        assert metrics.error_count == 500
        assert metrics.events_generated == 1000  # 5 threads * 100 * 2

    def test_concurrent_processing_time_updates(self, metrics):
        """Test thread-safe processing time updates"""
        def update_processing_times():
            for i in range(50):
                metrics.update_processing_time(float(i + 1))
        
        # Run concurrent updates
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(update_processing_times) for _ in range(3)]
            for future in futures:
                future.result()
        
        # Verify average is calculated correctly
        # Each thread updates with 1,2,3...50, three times = 150 updates total
        expected_sum = 3 * sum(range(1, 51))  # Sum of 1..50, three times
        expected_avg = expected_sum / 150
        
        assert abs(metrics.avg_processing_time_ms - expected_avg) < 0.1

    def test_concurrent_metric_snapshots(self, metrics):
        """Test thread-safe snapshot generation"""
        def update_and_snapshot():
            metrics.increment_processed_count(10)
            return metrics.get_snapshot()
        
        # Run concurrent snapshot operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update_and_snapshot) for _ in range(10)]
            snapshots = [future.result() for future in futures]
        
        # All snapshots should be valid
        assert len(snapshots) == 10
        assert all(isinstance(snapshot, MetricsSnapshot) for snapshot in snapshots)
        
        # Final processed count should reflect all updates
        assert metrics.processed_count == 100


class TestChannelHealthStatus:
    """Test health status calculations"""

    @pytest.fixture
    def healthy_metrics(self):
        metrics = ChannelMetrics("healthy_channel", "healthy_123")
        metrics.mark_started()
        metrics.increment_processed_count(100)
        metrics.increment_error_count(2)  # 2% error rate
        metrics.update_processing_time(25.0)  # Fast processing
        return metrics

    @pytest.fixture
    def unhealthy_metrics(self):
        metrics = ChannelMetrics("unhealthy_channel", "unhealthy_123")
        metrics.mark_started()
        metrics.increment_processed_count(100)
        metrics.increment_error_count(50)  # 50% error rate
        metrics.update_processing_time(5000.0)  # Slow processing
        return metrics

    def test_healthy_status_calculation(self, healthy_metrics):
        """Test healthy status calculation"""
        health_status = ChannelHealthStatus(
            channel_name=healthy_metrics.channel_name,
            channel_id=healthy_metrics.channel_id,
            status=ChannelStatus.ACTIVE,
            is_healthy=True,
            uptime_seconds=healthy_metrics.get_uptime_seconds(),
            processed_count=healthy_metrics.processed_count,
            error_count=healthy_metrics.error_count,
            error_rate=healthy_metrics.get_error_rate(),
            avg_processing_time_ms=healthy_metrics.avg_processing_time_ms,
            queue_size=0,
            queue_utilization=0.0,
            circuit_breaker_open=False,
            consecutive_errors=0
        )
        
        assert health_status.is_healthy
        assert health_status.error_rate == 0.02
        assert health_status.avg_processing_time_ms == 25.0
        assert health_status.status == ChannelStatus.ACTIVE

    def test_unhealthy_status_calculation(self, unhealthy_metrics):
        """Test unhealthy status calculation"""
        health_status = ChannelHealthStatus(
            channel_name=unhealthy_metrics.channel_name,
            channel_id=unhealthy_metrics.channel_id,
            status=ChannelStatus.ERROR,
            is_healthy=False,
            uptime_seconds=unhealthy_metrics.get_uptime_seconds(),
            processed_count=unhealthy_metrics.processed_count,
            error_count=unhealthy_metrics.error_count,
            error_rate=unhealthy_metrics.get_error_rate(),
            avg_processing_time_ms=unhealthy_metrics.avg_processing_time_ms,
            queue_size=90,
            queue_utilization=0.9,
            circuit_breaker_open=True,
            consecutive_errors=10
        )
        
        assert not health_status.is_healthy
        assert health_status.error_rate == 0.5
        assert health_status.avg_processing_time_ms == 5000.0
        assert health_status.queue_utilization == 0.9
        assert health_status.circuit_breaker_open

    def test_health_status_string_representation(self, healthy_metrics):
        """Test health status string representation"""
        health_status = ChannelHealthStatus(
            channel_name="test_channel",
            channel_id="test_123",
            status=ChannelStatus.ACTIVE,
            is_healthy=True,
            uptime_seconds=120.0,
            processed_count=1000,
            error_count=5,
            error_rate=0.005,
            avg_processing_time_ms=50.0,
            queue_size=10,
            queue_utilization=0.1,
            circuit_breaker_open=False,
            consecutive_errors=0
        )
        
        status_str = str(health_status)
        assert "test_channel" in status_str
        assert "HEALTHY" in status_str
        assert "1000 processed" in status_str
        assert "0.50% errors" in status_str


class TestMetricsSnapshot:
    """Test metrics snapshot functionality"""

    @pytest.fixture
    def populated_metrics(self):
        metrics = ChannelMetrics("snapshot_test", "snap_123")
        metrics.mark_started()
        metrics.increment_processed_count(100)
        metrics.increment_error_count(5)
        metrics.increment_events_generated(150)
        metrics.update_processing_time(75.0)
        metrics.increment_batches_processed(20)
        metrics.increment_batch_failures(2)
        metrics.increment_circuit_breaker_opens(1)
        metrics.increment_circuit_breaker_closes(1)
        return metrics

    def test_snapshot_creation(self, populated_metrics):
        """Test snapshot creation and data integrity"""
        snapshot = populated_metrics.get_snapshot()
        
        assert isinstance(snapshot, MetricsSnapshot)
        assert snapshot.channel_name == "snapshot_test"
        assert snapshot.channel_id == "snap_123"
        assert snapshot.processed_count == 100
        assert snapshot.error_count == 5
        assert snapshot.events_generated == 150
        assert snapshot.avg_processing_time_ms == 75.0
        assert snapshot.batches_processed == 20
        assert snapshot.batch_failures == 2

    def test_snapshot_immutability(self, populated_metrics):
        """Test that snapshot is immutable (doesn't change with source)"""
        snapshot1 = populated_metrics.get_snapshot()
        original_count = snapshot1.processed_count
        
        # Modify original metrics
        populated_metrics.increment_processed_count(50)
        
        # Original snapshot should be unchanged
        assert snapshot1.processed_count == original_count
        
        # New snapshot should reflect changes
        snapshot2 = populated_metrics.get_snapshot()
        assert snapshot2.processed_count == original_count + 50

    def test_snapshot_serialization(self, populated_metrics):
        """Test snapshot can be serialized to dict"""
        snapshot = populated_metrics.get_snapshot()
        snapshot_dict = asdict(snapshot)
        
        assert isinstance(snapshot_dict, dict)
        assert snapshot_dict['channel_name'] == "snapshot_test"
        assert snapshot_dict['processed_count'] == 100
        assert snapshot_dict['error_count'] == 5
        assert 'timestamp' in snapshot_dict

    def test_multiple_snapshots_timing(self, populated_metrics):
        """Test multiple snapshots have different timestamps"""
        snapshot1 = populated_metrics.get_snapshot()
        time.sleep(0.01)
        snapshot2 = populated_metrics.get_snapshot()
        
        assert snapshot2.timestamp > snapshot1.timestamp


class TestMetricsCalculations:
    """Test metrics calculation methods"""

    @pytest.fixture
    def calculation_metrics(self):
        return ChannelMetrics("calc_test", "calc_123")

    def test_error_rate_calculation(self, calculation_metrics):
        """Test error rate calculation"""
        # No processing yet
        assert calculation_metrics.get_error_rate() == 0.0
        
        # Some processing with errors
        calculation_metrics.increment_processed_count(100)
        calculation_metrics.increment_error_count(25)
        
        assert calculation_metrics.get_error_rate() == 0.25

    def test_success_rate_calculation(self, calculation_metrics):
        """Test success rate calculation"""
        calculation_metrics.increment_processed_count(100)
        calculation_metrics.increment_error_count(15)
        
        success_rate = calculation_metrics.get_success_rate()
        assert success_rate == 0.85  # (100-15)/100

    def test_events_per_processed_ratio(self, calculation_metrics):
        """Test events per processed data ratio"""
        calculation_metrics.increment_processed_count(50)
        calculation_metrics.increment_events_generated(100)
        
        ratio = calculation_metrics.get_events_per_processed_ratio()
        assert ratio == 2.0  # 100 events / 50 processed = 2.0

    def test_circuit_breaker_efficiency(self, calculation_metrics):
        """Test circuit breaker efficiency calculation"""
        calculation_metrics.increment_circuit_breaker_opens(3)
        calculation_metrics.increment_circuit_breaker_closes(3)
        calculation_metrics.increment_circuit_breaker_rejections(50)
        
        # Efficiency = closes / opens
        efficiency = calculation_metrics.circuit_breaker_closes / calculation_metrics.circuit_breaker_opens
        assert efficiency == 1.0  # Perfect efficiency (all opens were closed)


class TestMetricsPerformance:
    """Test metrics performance characteristics"""

    def test_metrics_memory_efficiency(self):
        """Test that metrics don't consume excessive memory"""
        import sys
        
        # Create metrics and measure memory
        metrics = ChannelMetrics("memory_test", "mem_123")
        
        # Perform many operations
        for i in range(1000):
            metrics.increment_processed_count()
            metrics.increment_error_count()
            metrics.update_processing_time(float(i))
            metrics.increment_events_generated(2)
        
        # Memory usage should be reasonable (metrics object should be small)
        size = sys.getsizeof(metrics)
        assert size < 10000  # Less than 10KB for metrics object

    @pytest.mark.performance
    def test_metrics_operation_speed(self, performance_timer):
        """Test that metrics operations are fast"""
        metrics = ChannelMetrics("speed_test", "speed_123")
        
        performance_timer.start()
        
        # Perform many operations
        for i in range(10000):
            metrics.increment_processed_count()
            metrics.update_processing_time(float(i))
            if i % 100 == 0:
                metrics.get_snapshot()
        
        performance_timer.stop()
        
        # Should complete quickly (< 1 second for 10k operations)
        assert performance_timer.elapsed < 1.0

    def test_concurrent_performance(self):
        """Test performance under concurrent access"""
        metrics = ChannelMetrics("concurrent_perf", "conc_123")
        
        def worker():
            for _ in range(1000):
                metrics.increment_processed_count()
                metrics.update_processing_time(50.0)
        
        start_time = time.time()
        
        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            for future in futures:
                future.result()
        
        elapsed = time.time() - start_time
        
        # Should handle concurrent access efficiently (< 2 seconds for 10k ops * 10 threads)
        assert elapsed < 2.0
        assert metrics.processed_count == 10000


# Test markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.channels,
    pytest.mark.metrics
]