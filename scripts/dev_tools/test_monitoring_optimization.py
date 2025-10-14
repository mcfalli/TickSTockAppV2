#!/usr/bin/env python3
"""
Test suite for validating monitoring.py optimizations
Can run standalone without the full application
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

# Mock the dependencies if not available
try:
    from src.monitoring import DiagnosticCollector, MetricsBuffer, MonitoringConfig, SystemMonitor
except ImportError:
    print("Note: monitoring.py not found, using mock mode")
    SystemMonitor = Mock
    DiagnosticCollector = Mock
    MonitoringConfig = Mock
    MetricsBuffer = Mock

try:
    from src.monitoring.tracer import DebugTracer, TickerTrace, tracer
except ImportError:
    print("Note: tracer.py not found, using mock mode")
    tracer = Mock()
    DebugTracer = Mock
    TickerTrace = Mock


class MockTracer:
    """Mock tracer for testing without real tracer"""
    def __init__(self):
        self.enabled = True
        self.traces = {}
        self._counters = {
            'events_detected_total': 100,
            'events_emitted_total': 85,
            'events_queued_total': 95,
            'events_collected': 90,
            'empty_collections': 20,
            'non_empty_collections': 80
        }

    def get_all_active_traces(self):
        return ['NVDA', 'AAPL', 'TSLA', 'SYSTEM']

    def get_flow_summary(self, ticker):
        return {
            'events_detected': self._counters['events_detected_total'],
            'events_emitted': self._counters['events_emitted_total'],
            'events_queued': self._counters['events_queued_total'],
            'events_collected': self._counters['events_collected'],
            'user_connections': {
                'first_user_time': time.time() - 300,
                'events_before_first_user': 10,
                'total_users': 3,
                'adjusted_efficiency': 94.4,
                'raw_efficiency': 85.0
            },
            'by_type': {
                'high': {'detected': 40, 'emitted': 35},
                'low': {'detected': 30, 'emitted': 28},
                'surge': {'detected': 20, 'emitted': 15},
                'trend': {'detected': 10, 'emitted': 7}
            }
        }

    def get_system_metrics(self):
        return {
            'uptime_seconds': 3600,
            'health_checks': 120,
            'traced_tickers': ['NVDA', 'AAPL', 'TSLA']
        }

    def print_flow_status(self):
        print("[MockTracer] Flow status called")


class MockMarketService:
    """Mock market service for testing"""
    def __init__(self):
        self.changed_tickers = ['NVDA', 'AAPL', 'TSLA']
        self.priority_manager = Mock()
        self.priority_manager.get_diagnostics_queue_diagnostics.return_value = {
            'current_size': 50,
            'max_configured_size': 1000,
            'utilization_percent': 5.0,
            'drop_rate_percent': 0.1,
            'flow_efficiency_percent': 95.0
        }

    def get_display_queue_status(self):
        return {
            'current_size': 10,
            'max_size': 100,
            'utilization_percent': 10.0,
            'collection_efficiency': 92.0
        }

    def is_healthy(self):
        return True


class TestMonitoringOptimization(unittest.TestCase):
    """Test suite for monitoring optimizations"""

    def setUp(self):
        """Set up test environment"""
        # Create temp directory for logs
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        os.makedirs('logs', exist_ok=True)

        # Reset any global state
        self.cleanup_singletons()

    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
        self.cleanup_singletons()

    def cleanup_singletons(self):
        """Clean up singleton instances"""
        # Reset monitoring singleton if it exists
        if hasattr(SystemMonitor, '_instance'):
            SystemMonitor._instance = None

    @patch('monitoring.tracer', MockTracer())
    def test_1_monitoring_initialization(self):
        """Test 1: Basic initialization and configuration"""
        print("\n=== Test 1: Monitoring Initialization ===")

        config = MonitoringConfig(
            trace_status_interval=5,
            diagnostic_dump_interval=10,
            buffer_size=50,
            batch_write_interval=2
        )

        monitor = SystemMonitor(config)

        # Verify configuration
        self.assertEqual(monitor.config.trace_status_interval, 5)
        self.assertEqual(monitor.config.buffer_size, 50)
        self.assertFalse(monitor.monitoring_active)
        self.assertEqual(len(monitor._threads), 0)

        print("✅ Configuration properly initialized")
        print(f"   Buffer size: {monitor.config.buffer_size}")
        print(f"   Batch write interval: {monitor.config.batch_write_interval}s")

    @patch('monitoring.tracer', MockTracer())
    def test_2_performance_metrics(self):
        """Test 2: Performance metrics collection"""
        print("\n=== Test 2: Performance Metrics ===")

        import psutil
        process = psutil.Process()

        # Baseline measurements
        mem_before = process.memory_info().rss / 1024 / 1024
        cpu_before = process.cpu_percent(interval=0.1)
        threads_before = threading.active_count()

        # Start monitoring
        monitor = SystemMonitor()
        monitor.collector.set_services(
            market_service=MockMarketService(),
            data_publisher=Mock()
        )
        monitor.start_monitoring()

        # Let it run briefly
        time.sleep(2)

        # After measurements
        mem_after = process.memory_info().rss / 1024 / 1024
        cpu_after = process.cpu_percent(interval=0.1)
        threads_after = threading.active_count()

        # Stop monitoring
        monitor.stop_monitoring()

        # Analysis
        mem_increase = mem_after - mem_before
        thread_increase = threads_after - threads_before

        print(f"✅ Memory: {mem_before:.1f}MB → {mem_after:.1f}MB (Δ{mem_increase:+.1f}MB)")
        print(f"✅ CPU: {cpu_before:.1f}% → {cpu_after:.1f}%")
        print(f"✅ Threads: {threads_before} → {threads_after} (Δ{thread_increase:+d})")

        # Verify only 2 new threads created
        self.assertLessEqual(thread_increase, 2, "Should create at most 2 threads")

        # Verify low memory overhead
        self.assertLess(mem_increase, 5, "Memory increase should be < 5MB")

    @patch('monitoring.tracer', MockTracer())
    def test_3_file_io_buffering(self):
        """Test 3: File I/O buffering verification"""
        print("\n=== Test 3: File I/O Buffering ===")

        config = MonitoringConfig(
            diagnostic_dump_interval=2,  # Fast dumps for testing
            batch_write_interval=1       # Fast writes for testing
        )

        monitor = SystemMonitor(config)
        monitor.collector.set_services(market_service=MockMarketService())

        # Track file writes
        log_file = f"./logs/diag_{datetime.now().strftime('%Y%m%d')}.log"
        write_times = []

        def check_file_size():
            if os.path.exists(log_file):
                return os.path.getsize(log_file)
            return 0

        initial_size = check_file_size()

        # Start monitoring
        monitor.start_monitoring()

        # Monitor file writes for 5 seconds
        for i in range(10):  # 10 x 0.5s = 5s
            time.sleep(0.5)
            current_size = check_file_size()
            if current_size > initial_size:
                write_times.append(i * 0.5)
                initial_size = current_size

        monitor.stop_monitoring()

        print(f"✅ File writes detected at: {write_times} seconds")
        print(f"✅ Total writes in 5 seconds: {len(write_times)}")

        # Should have buffered writes, not continuous
        self.assertLess(len(write_times), 5, "Should have fewer than 5 writes in 5 seconds")

    @patch('monitoring.tracer', MockTracer())
    def test_4_thread_verification(self):
        """Test 4: Thread count and naming verification"""
        print("\n=== Test 4: Thread Verification ===")

        monitor = SystemMonitor()
        monitor.collector.set_services(market_service=MockMarketService())

        # Get threads before
        threads_before = set(t.name for t in threading.enumerate())

        # Start monitoring
        monitor.start_monitoring()
        time.sleep(0.5)  # Let threads start

        # Get threads after
        threads_after = set(t.name for t in threading.enumerate())
        new_threads = threads_after - threads_before

        print("✅ New threads created:")
        for thread_name in new_threads:
            print(f"   - {thread_name}")

        # Verify thread names
        expected_threads = {'UnifiedMonitor', 'BufferWriter'}
        self.assertEqual(new_threads, expected_threads,
                        f"Should have exactly {expected_threads}")

        # Verify old thread names don't exist
        old_thread_names = {'TraceMonitor', 'DiagnosticMonitor', 'PerformanceMonitor'}
        for old_name in old_thread_names:
            self.assertNotIn(old_name, threads_after,
                           f"Old thread {old_name} should not exist")

        monitor.stop_monitoring()
        print("✅ Thread architecture verified - only 2 threads as expected")

    @patch('monitoring.tracer', MockTracer())
    def test_5_integration_with_tracer(self):
        """Test 5: Integration test with tracer"""
        print("\n=== Test 5: Integration with Tracer ===")

        monitor = SystemMonitor()
        mock_service = MockMarketService()
        monitor.collector.set_services(market_service=mock_service)

        # Start monitoring
        monitor.start_monitoring()

        # Get diagnostics summary
        summary = monitor.get_diagnostics_summary()

        print("✅ Diagnostics Summary:")
        print(json.dumps(summary, indent=2))

        # Verify summary structure
        self.assertIn('timestamp', summary)
        self.assertIn('health', summary)
        self.assertIn('monitoring_active', summary)
        self.assertIn('metrics', summary)

        # Verify health status
        self.assertEqual(summary['health'], 'healthy')

        # Test with degraded health
        mock_service.is_healthy = Mock(return_value=False)
        summary2 = monitor.get_diagnostics_summary()
        self.assertEqual(summary2['health'], 'degraded')

        monitor.stop_monitoring()
        print("✅ Integration with tracer working correctly")

    @patch('monitoring.tracer', MockTracer())
    def test_6_error_handling(self):
        """Test 6: Error handling and graceful degradation"""
        print("\n=== Test 6: Error Handling ===")

        monitor = SystemMonitor()

        # Test without services
        summary = monitor.get_diagnostics_summary()
        print(f"✅ Health without services: {summary.get('health')}")
        self.assertEqual(summary['health'], 'unknown')

        # Start monitoring without services - should not crash
        monitor.start_monitoring()
        time.sleep(0.5)
        self.assertTrue(monitor.monitoring_active)
        print("✅ Monitoring started successfully without services")

        # Test with failing service
        failing_service = Mock()
        failing_service.get_display_queue_status.side_effect = Exception("Test error")
        failing_service.priority_manager = None
        failing_service.changed_tickers = []

        monitor.collector.set_services(market_service=failing_service)

        # Should handle errors gracefully
        diagnostics = monitor.collector.collect_all_diagnostics()
        self.assertIn('display_queue', diagnostics)
        self.assertEqual(diagnostics['display_queue']['error'], 'Test error')
        print("✅ Service errors handled gracefully")

        # Stop cleanly
        monitor.stop_monitoring()
        time.sleep(0.5)
        self.assertFalse(monitor.monitoring_active)
        print("✅ Clean shutdown successful")

    def test_7_metrics_buffer(self):
        """Test 7: MetricsBuffer functionality"""
        print("\n=== Test 7: Metrics Buffer ===")

        buffer = MetricsBuffer(max_size=5)

        # Add messages
        for i in range(7):
            buffer.add(f"Message {i}")

        # Buffer should only keep last 5
        messages = buffer.flush()
        self.assertEqual(len(messages), 5)
        self.assertEqual(messages[0], "Message 2\n")  # First 2 dropped
        self.assertEqual(messages[-1], "Message 6\n")

        # Buffer should be empty after flush
        messages2 = buffer.flush()
        self.assertEqual(len(messages2), 0)

        print("✅ Buffer correctly limits size and flushes properly")

    @patch('monitoring.tracer', MockTracer())
    def test_8_caching_behavior(self):
        """Test 8: Diagnostic collector caching"""
        print("\n=== Test 8: Caching Behavior ===")

        collector = DiagnosticCollector()

        # Create a slow mock service to test caching
        slow_service = MockMarketService()
        def slow_diagnostics():
            time.sleep(0.01)  # Simulate 10ms operation
            return {
                'current_size': 50,
                'max_configured_size': 1000,
                'utilization_percent': 5.0
            }
        slow_service.priority_manager.get_diagnostics_queue_diagnostics = slow_diagnostics

        collector.set_services(market_service=slow_service)

        # First call - should compute
        start = time.time()
        result1 = collector._collect_queue_diagnostics()
        time1 = time.time() - start

        # Second call - should use cache
        start = time.time()
        result2 = collector._collect_queue_diagnostics()
        time2 = time.time() - start

        # Cached call should be much faster
        self.assertLess(time2, time1 / 2)
        self.assertEqual(result1, result2)  # Same data

        print(f"✅ First call: {time1*1000:.2f}ms")
        print(f"✅ Cached call: {time2*1000:.2f}ms")
        if time2 > 0:
            print(f"✅ Cache speedup: {time1/time2:.1f}x")
        else:
            print("✅ Cache speedup: >1000x (instant)")

        # Wait for cache to expire
        time.sleep(6)  # Cache TTL is 5 seconds

        # Should recompute
        start = time.time()
        result3 = collector._collect_queue_diagnostics()
        time3 = time.time() - start

        # Should be slow again after cache expiry
        self.assertGreater(time3, time2 * 5)
        print("✅ Cache expiration working correctly")

    def run_performance_comparison(self):
        """Compare old vs new monitoring performance (requires both versions)"""
        print("\n=== Performance Comparison ===")
        print("This would compare old vs new monitoring.py")
        print("Requires both versions to be available")

        # This is a placeholder for manual comparison
        comparison = {
            'file_size': {
                'old': '~1,130 lines',
                'new': '~520 lines',
                'reduction': '54%'
            },
            'threads': {
                'old': '4+ threads',
                'new': '2 threads',
                'reduction': '50%+'
            },
            'file_io': {
                'old': 'Every event',
                'new': 'Buffered (5s)',
                'reduction': '~95%'
            }
        }

        print("Expected improvements:")
        for metric, data in comparison.items():
            print(f"\n{metric}:")
            for key, value in data.items():
                print(f"  {key}: {value}")


def run_all_tests():
    """Run all tests with summary"""
    print("=" * 60)
    print("MONITORING OPTIMIZATION TEST SUITE")
    print("=" * 60)

    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMonitoringOptimization)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED! Monitoring optimizations verified.")
    else:
        print("\n❌ Some tests failed. Review output above.")

    return result.wasSuccessful()


if __name__ == '__main__':
    # Check if we have required modules
    try:
        import psutil
    except ImportError:
        print("Warning: psutil not installed. Install with: pip install psutil")
        print("Some tests will be skipped.\n")

    # Run tests
    success = run_all_tests()
    sys.exit(0 if success else 1)
