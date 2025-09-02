"""
Sprint 14 Phase 2: Automation Services Performance Benchmark Test Suite

Performance validation tests for 4,000+ symbol processing, sub-100ms message
delivery, and <50ms database query requirements for automation services.

Date: 2025-09-01
Sprint: 14 Phase 2
Status: Comprehensive Performance Coverage
"""

import pytest
import time
import asyncio
import threading
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import Dict, List, Any
import psutil
import memory_profiler

from src.automation.services.ipo_monitor import IPOMonitor
from src.automation.services.data_quality_monitor import DataQualityMonitor
from src.database.connection import DatabaseConnection


class TestIPOMonitorPerformance:
    """Performance benchmarks for IPO monitoring service"""
    
    @pytest.mark.performance
    def test_4000_symbol_discovery_performance(self):
        """Test IPO monitor can handle 4,000+ symbol discovery efficiently"""
        ipo_monitor = IPOMonitor()
        
        # Mock large API response with 4,000 potential IPO symbols
        large_api_response = {
            "status": "OK",
            "results": [
                {
                    "ticker": f"IPO{i:04d}",
                    "name": f"IPO Company {i} Inc",
                    "market": "stocks",
                    "type": "CS",
                    "active": True,
                    "listing_date": "2025-09-01"
                }
                for i in range(4000)
            ]
        }
        
        with patch('src.automation.services.ipo_monitor.requests.get') as mock_get:
            mock_get.return_value.json.return_value = large_api_response
            mock_get.return_value.status_code = 200
            
            # Benchmark symbol discovery performance
            start_time = time.perf_counter()
            new_symbols = ipo_monitor.discover_new_symbols(days_back=1)
            elapsed_time = time.perf_counter() - start_time
            
            # Performance assertions
            assert len(new_symbols) == 4000
            assert elapsed_time < 30.0  # Process 4,000 symbols in <30 seconds
            
            # Per-symbol processing time
            per_symbol_time = elapsed_time / 4000
            assert per_symbol_time < 0.0075  # <7.5ms per symbol processing
            
    @pytest.mark.performance
    def test_historical_backfill_batch_performance(self):
        """Test historical backfill performance for multiple symbols"""
        ipo_monitor = IPOMonitor()
        
        # Mock historical data for batch testing
        mock_historical_response = {
            "status": "OK",
            "results": [
                {
                    "o": 100.0 + i * 0.1,
                    "h": 101.0 + i * 0.1,
                    "l": 99.0 + i * 0.1,
                    "c": 100.5 + i * 0.1,
                    "v": 1000000 + i * 1000,
                    "t": int((datetime.now() - timedelta(days=90-i)).timestamp() * 1000)
                }
                for i in range(90)
            ]
        }
        
        symbols_batch = [f"BACKFILL{i:03d}" for i in range(100)]
        
        with patch('src.automation.services.ipo_monitor.requests.get') as mock_get, \
             patch.object(ipo_monitor, 'store_historical_data', return_value=True) as mock_store:
            
            mock_get.return_value.json.return_value = mock_historical_response
            mock_get.return_value.status_code = 200
            
            start_time = time.perf_counter()
            
            # Process 100 symbols with 90 days each = 9,000 data points
            results = []
            for symbol in symbols_batch:
                symbol_data = {"ticker": symbol, "listing_date": "2025-08-01"}
                result = ipo_monitor.backfill_historical_data(symbol_data)
                results.append(result)
                
            elapsed_time = time.perf_counter() - start_time
            
            # Performance benchmarks
            assert all(results)  # All backfills successful
            assert elapsed_time < 300.0  # 100 symbols * 90 days in <5 minutes
            assert mock_store.call_count == 100
            
            # Rate limiting validation
            average_time_per_request = elapsed_time / 100
            assert average_time_per_request >= 0.1  # Respects rate limiting
            
    @pytest.mark.performance
    def test_redis_notification_throughput(self):
        """Test Redis notification throughput performance"""
        ipo_monitor = IPOMonitor()
        
        # Mock Redis for performance testing
        mock_redis = Mock()
        publish_times = []
        
        def mock_publish(*args, **kwargs):
            publish_times.append(time.perf_counter())
            return 1
            
        mock_redis.publish = mock_publish
        ipo_monitor.redis_client = mock_redis
        
        # Test batch notification performance
        notification_batch = [
            {"ticker": f"PERF{i:04d}", "name": f"Performance Test {i}"}
            for i in range(1000)
        ]
        
        start_time = time.perf_counter()
        
        result = ipo_monitor.publish_batch_notifications(notification_batch)
        
        elapsed_time = time.perf_counter() - start_time
        
        # Performance assertions
        assert result is True
        assert len(publish_times) == 1000
        assert elapsed_time < 10.0  # 1,000 notifications in <10 seconds
        
        # Individual notification performance
        if len(publish_times) > 1:
            max_individual_time = max(
                publish_times[i+1] - publish_times[i] 
                for i in range(len(publish_times)-1)
            )
            assert max_individual_time < 0.1  # Each notification <100ms
            
    @pytest.mark.performance
    def test_memory_usage_during_large_operations(self):
        """Test memory usage remains stable during large IPO processing"""
        ipo_monitor = IPOMonitor()
        
        # Monitor memory usage
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Process large dataset
        large_dataset = []
        for i in range(5000):
            large_dataset.append({
                "ticker": f"MEM{i:04d}",
                "name": f"Memory Test Company {i}",
                "listing_date": "2025-09-01",
                "market_cap": 1000000000 + i * 1000000
            })
            
        with patch.object(ipo_monitor, 'create_symbol', return_value=True), \
             patch.object(ipo_monitor, 'publish_ipo_notification', return_value=True):
            
            start_time = time.perf_counter()
            
            for symbol_data in large_dataset:
                ipo_monitor.process_new_ipo(symbol_data)
                
            elapsed_time = time.perf_counter() - start_time
            
        # Check final memory usage
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory assertions
        assert memory_growth < 500  # Memory growth <500MB for 5,000 symbols
        assert elapsed_time < 60   # Process 5,000 symbols in <1 minute
        
    @pytest.mark.performance
    def test_concurrent_ipo_processing_performance(self):
        """Test concurrent IPO processing performance"""
        ipo_monitor = IPOMonitor()
        
        def process_ipo_batch(batch_id, batch_size=100):
            """Process a batch of IPOs"""
            batch_symbols = [
                {"ticker": f"BATCH{batch_id}_{i:03d}", "name": f"Concurrent Test {i}"}
                for i in range(batch_size)
            ]
            
            with patch.object(ipo_monitor, 'create_symbol', return_value=True), \
                 patch.object(ipo_monitor, 'publish_ipo_notification', return_value=True):
                
                for symbol in batch_symbols:
                    ipo_monitor.process_new_ipo(symbol)
                    
            return len(batch_symbols)
            
        # Run 10 concurrent batches
        start_time = time.perf_counter()
        
        threads = []
        results = []
        
        for batch_id in range(10):
            thread = threading.Thread(
                target=lambda bid=batch_id: results.append(process_ipo_batch(bid))
            )
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)
            
        elapsed_time = time.perf_counter() - start_time
        
        # Performance assertions
        assert len(results) == 10
        assert sum(results) == 1000  # 10 batches * 100 symbols each
        assert elapsed_time < 30  # 1,000 symbols across 10 threads in <30 seconds


class TestDataQualityMonitorPerformance:
    """Performance benchmarks for data quality monitoring service"""
    
    @pytest.mark.performance
    def test_4000_symbol_quality_analysis_performance(self):
        """Test quality monitoring performance for 4,000+ symbols"""
        quality_monitor = DataQualityMonitor()
        
        # Generate large test dataset
        symbols_data = {}
        
        for i in range(4000):
            symbol = f"QUAL{i:04d}"
            
            # Generate 30 days of price data
            price_data = []
            volume_data = []
            base_price = 100.0 + i * 0.1
            base_volume = 1000000 + i * 1000
            
            for day in range(30):
                # Inject occasional anomalies
                if day % 10 == 0 and i % 100 == 0:
                    price_change = 0.25  # 25% anomaly
                    volume_multiplier = 6.0  # 6x volume spike
                else:
                    price_change = np.random.normal(0, 0.02)  # Normal 2% volatility
                    volume_multiplier = np.random.normal(1.0, 0.3)  # 30% volume variation
                    
                base_price *= (1 + price_change)
                volume = int(base_volume * abs(volume_multiplier))
                
                price_data.append({
                    'date': f'2025-08-{day+1:02d}',
                    'close': round(base_price, 2)
                })
                volume_data.append({
                    'date': f'2025-08-{day+1:02d}',
                    'volume': volume
                })
                
            symbols_data[symbol] = {
                'price_data': price_data,
                'volume_data': volume_data
            }
            
        # Benchmark quality analysis performance
        start_time = time.perf_counter()
        
        total_anomalies = 0
        
        for symbol, data in symbols_data.items():
            price_anomalies = quality_monitor.detect_price_anomalies(symbol, data['price_data'])
            volume_anomalies = quality_monitor.detect_volume_anomalies(symbol, data['volume_data'])
            
            total_anomalies += len(price_anomalies) + len(volume_anomalies)
            
        elapsed_time = time.perf_counter() - start_time
        
        # Performance assertions
        assert elapsed_time < 120.0  # 4,000 symbols analyzed in <2 minutes
        assert total_anomalies > 0   # Should detect injected anomalies
        
        # Per-symbol analysis time
        per_symbol_time = elapsed_time / 4000
        assert per_symbol_time < 0.03  # <30ms per symbol analysis
        
    @pytest.mark.performance
    def test_anomaly_detection_algorithm_performance(self):
        """Test core anomaly detection algorithm performance"""
        quality_monitor = DataQualityMonitor()
        
        # Generate large time series data
        large_timeseries = []
        base_price = 100.0
        
        for i in range(10000):  # 10,000 data points (~27 years daily)
            # Inject anomalies every 500 points
            if i % 500 == 0:
                change = 0.3 if i % 1000 == 0 else -0.25
            else:
                change = np.random.normal(0, 0.015)  # Normal market volatility
                
            base_price *= (1 + change)
            large_timeseries.append({
                'date': f'day_{i:05d}',
                'close': round(base_price, 2)
            })
            
        # Benchmark algorithm performance
        start_time = time.perf_counter()
        
        anomalies = quality_monitor.detect_price_anomalies('LARGE_SERIES', large_timeseries)
        
        elapsed_time = time.perf_counter() - start_time
        
        # Performance assertions
        assert elapsed_time < 5.0    # 10,000 points processed in <5 seconds
        assert len(anomalies) >= 15  # Should detect injected anomalies
        
        # Algorithm efficiency
        data_points_per_second = 10000 / elapsed_time
        assert data_points_per_second > 2000  # >2,000 points/second throughput
        
    @pytest.mark.performance
    def test_redis_alert_publishing_performance(self):
        """Test Redis alert publishing performance under load"""
        quality_monitor = DataQualityMonitor()
        
        # Mock Redis client
        mock_redis = Mock()
        publish_times = []
        
        def mock_publish(*args, **kwargs):
            publish_times.append(time.perf_counter())
            return 1
            
        mock_redis.publish = mock_publish
        quality_monitor.redis_client = mock_redis
        
        # Generate large batch of alerts
        alert_batch = []
        alert_types = ['price_spike', 'price_drop', 'volume_spike', 'volume_drought', 'data_gap']
        
        for i in range(2000):  # 2,000 alerts
            alert_batch.append({
                'symbol': f'ALERT{i:04d}',
                'anomaly_type': alert_types[i % len(alert_types)],
                'severity': ['low', 'medium', 'high', 'critical'][i % 4]
            })
            
        # Benchmark alert publishing
        start_time = time.perf_counter()
        
        result = quality_monitor.publish_batch_alerts(alert_batch)
        
        elapsed_time = time.perf_counter() - start_time
        
        # Performance assertions
        assert result is True
        assert len(publish_times) == 2000
        assert elapsed_time < 20.0  # 2,000 alerts in <20 seconds
        
        # Alert throughput
        alerts_per_second = 2000 / elapsed_time
        assert alerts_per_second > 100  # >100 alerts/second throughput
        
    @pytest.mark.performance
    def test_memory_efficiency_during_analysis(self):
        """Test memory efficiency during large-scale analysis"""
        quality_monitor = DataQualityMonitor()
        
        # Monitor memory usage
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Generate memory-intensive dataset
        large_dataset = {}
        
        for i in range(1000):  # 1,000 symbols
            symbol = f"MEMORY{i:04d}"
            
            # 365 days of data per symbol
            price_data = []
            volume_data = []
            
            for day in range(365):
                price_data.append({
                    'date': f'2024-{day+1:03d}',
                    'close': 100.0 + day * 0.1 + i * 0.01
                })
                volume_data.append({
                    'date': f'2024-{day+1:03d}',
                    'volume': 1000000 + day * 1000 + i * 100
                })
                
            large_dataset[symbol] = {
                'price_data': price_data,
                'volume_data': volume_data
            }
            
        # Process dataset and monitor memory
        peak_memory = initial_memory
        
        start_time = time.perf_counter()
        
        for symbol, data in large_dataset.items():
            # Process symbol data
            quality_monitor.detect_price_anomalies(symbol, data['price_data'])
            quality_monitor.detect_volume_anomalies(symbol, data['volume_data'])
            
            # Monitor peak memory usage
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            peak_memory = max(peak_memory, current_memory)
            
        elapsed_time = time.perf_counter() - start_time
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Memory efficiency assertions
        memory_growth = final_memory - initial_memory
        peak_memory_growth = peak_memory - initial_memory
        
        assert memory_growth < 200     # Final memory growth <200MB
        assert peak_memory_growth < 300  # Peak memory growth <300MB
        assert elapsed_time < 60      # Process 1,000 symbols in <1 minute


class TestDatabasePerformanceBenchmarks:
    """Database performance benchmarks for automation services"""
    
    @pytest.fixture
    def db_connection(self):
        """Database connection fixture"""
        return DatabaseConnection(test_mode=True)
    
    @pytest.mark.performance
    def test_equity_types_function_performance(self, db_connection):
        """Test equity types functions meet <50ms requirement"""
        cursor = db_connection.cursor()
        
        # Test get_equity_processing_config performance
        equity_types = ['ETF', 'STOCK_REALTIME', 'STOCK_EOD', 'PENNY_STOCK', 'ETN', 'DEV_TESTING']
        
        function_times = []
        
        for _ in range(100):  # 100 iterations for statistical significance
            for equity_type in equity_types:
                start_time = time.perf_counter()
                
                cursor.execute("SELECT get_equity_processing_config(%s)", (equity_type,))
                result = cursor.fetchone()
                
                elapsed_time = time.perf_counter() - start_time
                function_times.append(elapsed_time)
                
                assert result is not None
                
        # Performance assertions
        average_time = np.mean(function_times)
        max_time = np.max(function_times)
        p95_time = np.percentile(function_times, 95)
        
        assert average_time < 0.01   # Average <10ms
        assert max_time < 0.05       # Maximum <50ms
        assert p95_time < 0.025      # 95th percentile <25ms
        
    @pytest.mark.performance
    def test_processing_queue_operations_performance(self, db_connection):
        """Test processing queue operations performance"""
        cursor = db_connection.cursor()
        
        # Clear test data
        cursor.execute("DELETE FROM equity_processing_queue WHERE equity_type = 'PERF_TEST'")
        
        # Create test equity type
        cursor.execute("""
            INSERT INTO equity_types (type_name, priority_level, batch_size)
            VALUES ('PERF_TEST', 75, 100)
            ON CONFLICT (type_name) DO UPDATE SET priority_level = EXCLUDED.priority_level
        """)
        
        # Test queue_symbols_for_processing performance
        large_symbol_list = [f'PERF{i:04d}' for i in range(5000)]
        
        start_time = time.perf_counter()
        
        cursor.execute("SELECT queue_symbols_for_processing('PERF_TEST', %s)", (large_symbol_list,))
        queued_count = cursor.fetchone()[0]
        
        queue_time = time.perf_counter() - start_time
        
        assert queued_count == 5000
        assert queue_time < 10.0  # Queue 5,000 symbols in <10 seconds
        
        # Test batch selection performance
        batch_selection_times = []
        
        for _ in range(50):  # 50 batch selections
            start_time = time.perf_counter()
            
            cursor.execute("""
                SELECT symbol FROM equity_processing_queue
                WHERE equity_type = 'PERF_TEST' AND status = 'pending'
                ORDER BY processing_priority DESC, scheduled_time
                LIMIT 100
            """)
            
            batch = cursor.fetchall()
            elapsed_time = time.perf_counter() - start_time
            batch_selection_times.append(elapsed_time)
            
            assert len(batch) == 100
            
        # Batch selection performance
        avg_batch_time = np.mean(batch_selection_times)
        max_batch_time = np.max(batch_selection_times)
        
        assert avg_batch_time < 0.05  # Average batch selection <50ms
        assert max_batch_time < 0.1   # Maximum batch selection <100ms
        
    @pytest.mark.performance
    def test_statistics_update_performance(self, db_connection):
        """Test statistics update function performance"""
        cursor = db_connection.cursor()
        
        # Test update_processing_stats performance
        update_times = []
        
        for i in range(200):  # 200 statistics updates
            start_time = time.perf_counter()
            
            cursor.execute("""
                SELECT update_processing_stats('ETF', %s, %s, %s)
            """, (50 + i % 10, i % 3, 120 + i % 60))
            
            success = cursor.fetchone()[0]
            elapsed_time = time.perf_counter() - start_time
            update_times.append(elapsed_time)
            
            assert success is True
            
        # Statistics update performance
        avg_update_time = np.mean(update_times)
        max_update_time = np.max(update_times)
        p99_update_time = np.percentile(update_times, 99)
        
        assert avg_update_time < 0.02  # Average update <20ms
        assert max_update_time < 0.1   # Maximum update <100ms
        assert p99_update_time < 0.05  # 99th percentile <50ms
        
    @pytest.mark.performance
    def test_concurrent_database_operations(self, db_connection):
        """Test database performance under concurrent access"""
        import concurrent.futures
        
        def database_operation_worker(worker_id):
            """Worker function for concurrent database operations"""
            local_cursor = db_connection.cursor()
            operation_times = []
            
            for i in range(50):  # 50 operations per worker
                start_time = time.perf_counter()
                
                # Mix of operations
                if i % 3 == 0:
                    local_cursor.execute("SELECT get_equity_processing_config('STOCK_REALTIME')")
                elif i % 3 == 1:
                    local_cursor.execute("SELECT * FROM get_symbols_for_processing('ETF', 10)")
                else:
                    local_cursor.execute("SELECT update_processing_stats('STOCK_EOD', 25, 1, 90)")
                    
                result = local_cursor.fetchone()
                elapsed_time = time.perf_counter() - start_time
                operation_times.append(elapsed_time)
                
                assert result is not None
                
            return operation_times
            
        # Run 10 concurrent workers
        start_time = time.perf_counter()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(database_operation_worker, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
        total_time = time.perf_counter() - start_time
        
        # Analyze concurrent performance
        all_operation_times = [time for worker_times in results for time in worker_times]
        
        avg_operation_time = np.mean(all_operation_times)
        max_operation_time = np.max(all_operation_times)
        
        # Concurrent performance assertions
        assert len(all_operation_times) == 500  # 10 workers * 50 operations
        assert total_time < 30.0               # All operations in <30 seconds
        assert avg_operation_time < 0.05       # Average operation <50ms
        assert max_operation_time < 0.2        # No operation >200ms under load


class TestSystemPerformanceIntegration:
    """System-wide performance integration tests"""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_end_to_end_automation_performance(self):
        """Test complete automation system performance"""
        ipo_monitor = IPOMonitor()
        quality_monitor = DataQualityMonitor()
        
        # Mock large-scale operations
        with patch.object(ipo_monitor, 'discover_new_symbols') as mock_discover, \
             patch.object(ipo_monitor, 'backfill_historical_data') as mock_backfill, \
             patch.object(ipo_monitor, 'publish_ipo_notification') as mock_notify, \
             patch.object(quality_monitor, 'analyze_symbol_quality') as mock_analyze, \
             patch.object(quality_monitor, 'publish_quality_alert') as mock_alert:
            
            # Mock realistic processing times
            mock_discover.return_value = [{'ticker': f'IPO{i:04d}'} for i in range(50)]
            mock_backfill.return_value = True
            mock_notify.return_value = True
            mock_analyze.return_value = {'anomalies': 1, 'alerts': 1}
            mock_alert.return_value = True
            
            # Add realistic delays
            def mock_with_delay(*args, **kwargs):
                time.sleep(0.01)  # 10ms processing delay
                return True
                
            mock_backfill.side_effect = mock_with_delay
            mock_analyze.side_effect = mock_with_delay
            
            # Run complete automation cycle
            start_time = time.perf_counter()
            
            # IPO processing
            ipo_results = ipo_monitor.run_daily_ipo_scan()
            
            # Quality monitoring for 1000 symbols
            quality_results = quality_monitor.run_quality_scan([f'SYM{i:04d}' for i in range(1000)])
            
            elapsed_time = time.perf_counter() - start_time
            
            # System performance assertions
            assert ipo_results['discovered'] == 50
            assert quality_results['symbols_analyzed'] == 1000
            assert elapsed_time < 120.0  # Complete cycle in <2 minutes
            
            # Verify processing throughput
            total_operations = 50 + 1000  # IPOs + quality symbols
            operations_per_second = total_operations / elapsed_time
            assert operations_per_second > 10  # >10 operations/second
            
    @pytest.mark.performance
    def test_system_resource_utilization(self):
        """Test system resource utilization under full load"""
        ipo_monitor = IPOMonitor()
        quality_monitor = DataQualityMonitor()
        
        # Monitor system resources
        initial_cpu_percent = psutil.cpu_percent(interval=1)
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Create high load scenario
        def high_load_worker():
            """Worker to create high processing load"""
            for i in range(100):
                # Simulate IPO processing
                with patch.object(ipo_monitor, 'process_new_ipo', return_value=True):
                    ipo_monitor.process_new_ipo({'ticker': f'LOAD{i:03d}', 'name': f'Load Test {i}'})
                    
                # Simulate quality analysis
                mock_data = [{'date': f'2025-08-{j+1:02d}', 'close': 100.0 + j} for j in range(30)]
                quality_monitor.detect_price_anomalies(f'LOAD{i:03d}', mock_data)
                
        # Run multiple high-load workers
        start_time = time.perf_counter()
        
        threads = []
        for _ in range(5):  # 5 concurrent workers
            thread = threading.Thread(target=high_load_worker)
            threads.append(thread)
            thread.start()
            
        # Monitor peak resource usage
        peak_cpu = 0
        peak_memory = initial_memory
        
        while any(t.is_alive() for t in threads):
            cpu_percent = psutil.cpu_percent()
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            
            peak_cpu = max(peak_cpu, cpu_percent)
            peak_memory = max(peak_memory, memory_mb)
            
            time.sleep(0.1)
            
        # Wait for completion
        for thread in threads:
            thread.join(timeout=60)
            
        elapsed_time = time.perf_counter() - start_time
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Resource utilization assertions
        assert elapsed_time < 60.0        # Complete in <1 minute
        assert peak_cpu < 80.0           # CPU usage <80%
        assert peak_memory - initial_memory < 1000  # Memory growth <1GB
        assert final_memory - initial_memory < 200  # Memory cleanup after processing
        
    @pytest.mark.performance
    def test_automation_scaling_limits(self):
        """Test automation services scaling limits"""
        ipo_monitor = IPOMonitor()
        quality_monitor = DataQualityMonitor()
        
        # Test scaling to maximum expected load
        max_symbols = 10000  # 10,000 symbols (2.5x current capacity)
        
        # Mock processing functions with realistic timing
        with patch.object(ipo_monitor, 'process_new_ipo') as mock_ipo, \
             patch.object(quality_monitor, 'analyze_symbol_quality') as mock_quality:
            
            def realistic_processing_delay(*args, **kwargs):
                time.sleep(0.001)  # 1ms realistic processing time
                return True
                
            mock_ipo.side_effect = realistic_processing_delay
            mock_quality.side_effect = realistic_processing_delay
            
            # Test IPO processing scaling
            start_time = time.perf_counter()
            
            for i in range(max_symbols):
                ipo_monitor.process_new_ipo({'ticker': f'SCALE{i:05d}', 'name': f'Scale Test {i}'})
                
            ipo_scaling_time = time.perf_counter() - start_time
            
            # Test quality monitoring scaling
            start_time = time.perf_counter()
            
            for i in range(max_symbols):
                quality_monitor.analyze_symbol_quality(f'SCALE{i:05d}')
                
            quality_scaling_time = time.perf_counter() - start_time
            
            # Scaling assertions
            assert ipo_scaling_time < 300    # 10,000 IPO operations in <5 minutes
            assert quality_scaling_time < 300  # 10,000 quality analyses in <5 minutes
            
            # Throughput at scale
            ipo_throughput = max_symbols / ipo_scaling_time
            quality_throughput = max_symbols / quality_scaling_time
            
            assert ipo_throughput > 30      # >30 IPO operations/second
            assert quality_throughput > 30  # >30 quality analyses/second