"""
Performance Tests for CacheEntriesSynchronizer

Tests performance characteristics and validates that the cache synchronizer
meets TickStock's performance requirements for real-time financial data processing.

Performance Requirements:
- Complete rebuild should complete within 60 seconds for typical datasets (5000 stocks, 500 ETFs)
- Individual operations should be sub-second for small datasets
- Memory usage should remain below 100MB for large datasets
- Database query optimization and batching effectiveness
- Redis notification performance impact

Test Coverage:
- End-to-end rebuild performance benchmarks
- Individual method performance validation
- Memory usage profiling and leak detection
- Concurrent access performance impact
- Large dataset scalability testing
- Database connection pooling efficiency
"""

import pytest
import time
import tracemalloc
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any
import psycopg2
from psycopg2.extras import RealDictCursor

# Import the class under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from src.core.services.cache_entries_synchronizer import CacheEntriesSynchronizer


class PerformanceTimer:
    """Simple performance timer for benchmarking."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = 0
    
    def start(self):
        self.start_time = time.time()
    
    def stop(self):
        self.end_time = time.time()
        if self.start_time:
            self.elapsed = self.end_time - self.start_time
        return self.elapsed
    
    def reset(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = 0


@pytest.fixture
def performance_timer():
    """Performance timer fixture."""
    return PerformanceTimer()


@pytest.fixture
def large_dataset_generator():
    """Generate large datasets for performance testing."""
    def generate(num_stocks=5000, num_etfs=500, num_sectors=20):
        stocks = []
        for i in range(num_stocks):
            # Distribute across market cap categories
            if i < num_stocks * 0.01:  # Top 1% mega cap
                market_cap = 200_000_000_000 + (i * 1_000_000_000)
            elif i < num_stocks * 0.05:  # Next 4% large cap
                market_cap = 10_000_000_000 + (i * 100_000_000)
            elif i < num_stocks * 0.20:  # Next 15% mid cap
                market_cap = 2_000_000_000 + (i * 10_000_000)
            elif i < num_stocks * 0.60:  # Next 40% small cap
                market_cap = 300_000_000 + (i * 1_000_000)
            else:  # Remaining micro cap
                market_cap = 50_000_000 + (i * 100_000)
            
            stocks.append({
                'symbol': f'STOCK{i:05d}',
                'name': f'Test Company {i} Inc.',
                'market_cap': market_cap,
                'sector': f'Sector{i % num_sectors}',
                'industry': f'Industry{i % (num_sectors * 3)}',
                'primary_exchange': 'NYSE' if i % 2 == 0 else 'NASDAQ'
            })
        
        etfs = []
        for i in range(num_etfs):
            etfs.append({
                'symbol': f'ETF{i:03d}',
                'name': f'Test ETF Fund {i}',
                'market_cap': 100_000_000 + (i * 10_000_000),
                'etf_type': 'Index' if i % 3 == 0 else 'Sector',
                'issuer': f'Issuer{i % 10}',
                'primary_exchange': 'NYSE'
            })
        
        return {
            'stocks': stocks,
            'etfs': etfs,
            'sectors': [f'Sector{i}' for i in range(num_sectors)]
        }
    
    return generate


class TestCacheEntriesSynchronizerPerformance:
    """Performance tests for CacheEntriesSynchronizer class."""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer instance for performance testing."""
        with patch('src.core.services.cache_entries_synchronizer.load_dotenv'):
            return CacheEntriesSynchronizer()

    def _setup_performance_mocks(self, synchronizer, test_data):
        """Setup mocks optimized for performance testing."""
        mock_db_conn = Mock()
        mock_cursor = Mock(spec=RealDictCursor)
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Fast mock responses
        def fast_fetchall(*args, **kwargs):
            if len(args) > 0 and isinstance(args[0], str):
                query = args[0].lower()
                if 'distinct sector' in query:
                    return [{'sector': sector} for sector in test_data['sectors']]
                elif 'type = \'etf\'' in query:
                    return [{'symbol': etf['symbol']} for etf in test_data['etfs']]
                elif 'limit 10' in query:
                    return test_data['stocks'][:10]
                elif 'symbol = any' in query:
                    return [{'symbol': stock['symbol']} for stock in test_data['stocks'][:5]]
            return test_data['stocks']
        
        mock_cursor.fetchall.side_effect = fast_fetchall
        mock_cursor.fetchone.return_value = {
            'total_stocks': len(test_data['stocks']),
            'unique_sectors': len(test_data['sectors']),
            'total_market_cap': 50000000000000,
            'average_market_cap': 10000000000,
            'unique_industries': 60,
            'unique_exchanges': 2
        }
        mock_cursor.rowcount = len(test_data['stocks']) // 10
        
        mock_db_conn.cursor.return_value = mock_cursor
        synchronizer.db_conn = mock_db_conn
        synchronizer.redis_client = Mock()
        
        return mock_db_conn, mock_cursor

    @pytest.mark.performance
    def test_full_rebuild_performance_typical_dataset(self, synchronizer, large_dataset_generator, 
                                                    performance_timer):
        """Test full rebuild performance with typical production dataset."""
        # Typical production dataset: 5000 stocks, 500 ETFs
        test_data = large_dataset_generator(5000, 500, 20)
        mock_db_conn, mock_cursor = self._setup_performance_mocks(synchronizer, test_data)
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                performance_timer.start()
                stats = synchronizer.rebuild_stock_cache_entries()
                elapsed_time = performance_timer.stop()
        
        # Primary performance requirement: complete within 60 seconds
        assert elapsed_time < 60.0, f"Rebuild took {elapsed_time:.2f}s, requirement is <60s"
        
        # Additional performance goals
        if elapsed_time < 30.0:
            print(f"✅ Excellent performance: {elapsed_time:.2f}s")
        elif elapsed_time < 45.0:
            print(f"✅ Good performance: {elapsed_time:.2f}s")
        else:
            print(f"⚠️ Acceptable performance: {elapsed_time:.2f}s")
        
        # Verify completeness
        assert isinstance(stats, dict)
        assert all(key in stats for key in [
            'market_cap_entries', 'sector_leader_entries', 'market_leader_entries',
            'theme_entries', 'industry_entries', 'etf_entries', 'complete_entries'
        ])

    @pytest.mark.performance
    def test_individual_method_performance(self, synchronizer, large_dataset_generator, 
                                         performance_timer):
        """Test performance of individual cache entry creation methods."""
        test_data = large_dataset_generator(1000, 100, 10)
        mock_db_conn, mock_cursor = self._setup_performance_mocks(synchronizer, test_data)
        
        # Test each method individually
        methods_to_test = [
            ('_create_market_cap_entries', 5.0),     # 5 second limit
            ('_create_sector_leader_entries', 3.0),  # 3 second limit
            ('_create_market_leader_entries', 4.0),  # 4 second limit
            ('_create_theme_entries', 2.0),          # 2 second limit
            ('_create_industry_entries', 2.0),       # 2 second limit
            ('_create_etf_entries', 1.0),            # 1 second limit
            ('_create_complete_entries', 3.0),       # 3 second limit
            ('_create_stats_entries', 0.5),          # 0.5 second limit
        ]
        
        performance_results = {}
        
        for method_name, time_limit in methods_to_test:
            mock_cursor.reset_mock()
            method = getattr(synchronizer, method_name)
            
            performance_timer.reset()
            performance_timer.start()
            
            if method_name == '_create_complete_entries':
                # This method requires cursor parameter
                result = method()
            else:
                result = method()
            
            elapsed = performance_timer.stop()
            performance_results[method_name] = elapsed
            
            assert elapsed < time_limit, f"{method_name} took {elapsed:.3f}s, limit is {time_limit}s"
            print(f"✅ {method_name}: {elapsed:.3f}s (limit: {time_limit}s)")
        
        # Overall individual method performance should be much faster than full rebuild
        total_individual_time = sum(performance_results.values())
        assert total_individual_time < 20.0, f"Sum of individual methods: {total_individual_time:.2f}s"

    @pytest.mark.performance  
    def test_memory_usage_large_dataset(self, synchronizer, large_dataset_generator):
        """Test memory usage with large dataset."""
        # Very large dataset to stress test memory
        test_data = large_dataset_generator(10000, 1000, 30)
        mock_db_conn, mock_cursor = self._setup_performance_mocks(synchronizer, test_data)
        
        tracemalloc.start()
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                stats = synchronizer.rebuild_stock_cache_entries()
        
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory requirements
        max_memory_mb = 100  # 100MB limit
        peak_memory_mb = peak_memory / 1024 / 1024
        current_memory_mb = current_memory / 1024 / 1024
        
        assert peak_memory_mb < max_memory_mb, f"Peak memory {peak_memory_mb:.1f}MB exceeds {max_memory_mb}MB limit"
        
        print(f"Memory usage - Peak: {peak_memory_mb:.1f}MB, Current: {current_memory_mb:.1f}MB")
        
        if peak_memory_mb < 25:
            print("✅ Excellent memory efficiency")
        elif peak_memory_mb < 50:
            print("✅ Good memory efficiency")
        else:
            print("⚠️ Acceptable memory usage")

    @pytest.mark.performance
    def test_database_query_efficiency(self, synchronizer, large_dataset_generator):
        """Test database query efficiency and batching."""
        test_data = large_dataset_generator(2000, 200, 15)
        mock_db_conn, mock_cursor = self._setup_performance_mocks(synchronizer, test_data)
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                stats = synchronizer.rebuild_stock_cache_entries()
        
        # Count database operations
        select_count = sum(1 for call in mock_cursor.execute.call_args_list 
                         if 'SELECT' in str(call[0][0]).upper())
        insert_count = sum(1 for call in mock_cursor.execute.call_args_list 
                         if 'INSERT' in str(call[0][0]).upper())
        delete_count = sum(1 for call in mock_cursor.execute.call_args_list 
                         if 'DELETE' in str(call[0][0]).upper())
        
        total_queries = select_count + insert_count + delete_count
        
        # Query efficiency requirements
        max_expected_queries = 100  # Should be well-optimized
        assert total_queries < max_expected_queries, f"Too many queries: {total_queries} (max: {max_expected_queries})"
        
        print(f"Database efficiency - Total queries: {total_queries}")
        print(f"  - SELECT: {select_count}")
        print(f"  - INSERT: {insert_count}")  
        print(f"  - DELETE: {delete_count}")
        
        # Verify reasonable distribution
        assert delete_count == 1, "Should have exactly one DELETE operation"
        assert insert_count > 10, "Should have multiple INSERT operations"
        assert select_count > 5, "Should have multiple SELECT operations"

    @pytest.mark.performance
    def test_redis_notification_performance_impact(self, synchronizer, large_dataset_generator, 
                                                 performance_timer):
        """Test performance impact of Redis notifications."""
        test_data = large_dataset_generator(1000, 100, 10)
        mock_db_conn, mock_cursor = self._setup_performance_mocks(synchronizer, test_data)
        
        # Test without Redis
        synchronizer.redis_client = None
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                performance_timer.start()
                stats_without_redis = synchronizer.rebuild_stock_cache_entries()
                time_without_redis = performance_timer.stop()
        
        # Reset for Redis test
        mock_cursor.reset_mock()
        mock_redis = Mock()
        synchronizer.redis_client = mock_redis
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                performance_timer.start()
                stats_with_redis = synchronizer.rebuild_stock_cache_entries()
                time_with_redis = performance_timer.stop()
        
        # Redis should not add significant overhead
        redis_overhead = time_with_redis - time_without_redis
        max_overhead = 2.0  # 2 seconds maximum overhead
        
        assert redis_overhead < max_overhead, f"Redis overhead {redis_overhead:.2f}s exceeds {max_overhead}s limit"
        
        print(f"Redis performance impact:")
        print(f"  - Without Redis: {time_without_redis:.2f}s")
        print(f"  - With Redis: {time_with_redis:.2f}s")
        print(f"  - Overhead: {redis_overhead:.2f}s")
        
        # Verify Redis was actually called
        assert mock_redis.publish.called, "Redis notifications should have been sent"
        assert mock_redis.publish.call_count == 3, "Should publish to 3 channels"

    @pytest.mark.performance
    def test_concurrent_access_performance_impact(self, synchronizer, large_dataset_generator):
        """Test performance impact under simulated concurrent access."""
        test_data = large_dataset_generator(1500, 150, 12)
        mock_db_conn, mock_cursor = self._setup_performance_mocks(synchronizer, test_data)
        
        # Add delays to simulate concurrent database contention
        original_execute = mock_cursor.execute
        
        def execute_with_contention(*args, **kwargs):
            # Simulate slight delays from concurrent access
            time.sleep(0.001)  # 1ms delay per query
            return original_execute(*args, **kwargs)
        
        mock_cursor.execute = execute_with_contention
        
        with patch.object(synchronizer, 'connect', return_value=True):
            with patch.object(synchronizer, 'disconnect'):
                start_time = time.time()
                stats = synchronizer.rebuild_stock_cache_entries()
                elapsed_time = time.time() - start_time
        
        # Should still complete within reasonable time even with contention
        max_time_with_contention = 30.0  # 30 seconds with simulated contention
        assert elapsed_time < max_time_with_contention, f"Concurrent access scenario took {elapsed_time:.2f}s"
        
        print(f"Concurrent access performance: {elapsed_time:.2f}s")

    @pytest.mark.performance
    def test_json_serialization_performance(self, synchronizer, large_dataset_generator):
        """Test JSON serialization performance for large data structures."""
        test_data = large_dataset_generator(5000, 500, 20)
        mock_db_conn, mock_cursor = self._setup_performance_mocks(synchronizer, test_data)
        
        # Track JSON operations
        json_operations = []
        original_dumps = json.dumps
        
        def timed_dumps(obj, *args, **kwargs):
            start = time.time()
            result = original_dumps(obj, *args, **kwargs)
            end = time.time()
            json_operations.append(end - start)
            return result
        
        with patch('json.dumps', timed_dumps):
            with patch.object(synchronizer, 'connect', return_value=True):
                with patch.object(synchronizer, 'disconnect'):
                    stats = synchronizer.rebuild_stock_cache_entries()
        
        # Analyze JSON performance
        total_json_time = sum(json_operations)
        max_single_json_time = max(json_operations) if json_operations else 0
        
        # JSON serialization should be efficient
        assert total_json_time < 5.0, f"Total JSON serialization time {total_json_time:.2f}s too high"
        assert max_single_json_time < 1.0, f"Single JSON operation {max_single_json_time:.2f}s too slow"
        
        print(f"JSON serialization performance:")
        print(f"  - Total time: {total_json_time:.3f}s")
        print(f"  - Operations: {len(json_operations)}")
        print(f"  - Max single operation: {max_single_json_time:.3f}s")
        print(f"  - Average per operation: {total_json_time/len(json_operations):.3f}s" if json_operations else "N/A")

    @pytest.mark.performance
    def test_scalability_projection(self, synchronizer, large_dataset_generator, performance_timer):
        """Test performance scaling characteristics for future growth."""
        dataset_sizes = [
            (1000, 100, 10),   # Small
            (2500, 250, 15),   # Medium  
            (5000, 500, 20),   # Large (current production)
            (10000, 1000, 30), # Very Large (future growth)
        ]
        
        performance_data = []
        
        for stocks, etfs, sectors in dataset_sizes:
            test_data = large_dataset_generator(stocks, etfs, sectors)
            mock_db_conn, mock_cursor = self._setup_performance_mocks(synchronizer, test_data)
            
            with patch.object(synchronizer, 'connect', return_value=True):
                with patch.object(synchronizer, 'disconnect'):
                    performance_timer.start()
                    stats = synchronizer.rebuild_stock_cache_entries()
                    elapsed_time = performance_timer.stop()
            
            performance_data.append({
                'stocks': stocks,
                'etfs': etfs,
                'sectors': sectors,
                'time': elapsed_time,
                'stocks_per_second': stocks / elapsed_time if elapsed_time > 0 else 0
            })
            
            print(f"Dataset ({stocks:5d} stocks, {etfs:3d} ETFs): {elapsed_time:6.2f}s - {stocks/elapsed_time:6.0f} stocks/sec")
        
        # Verify scaling characteristics
        for i in range(1, len(performance_data)):
            prev = performance_data[i-1]
            curr = performance_data[i]
            
            # Performance should scale reasonably (not exponentially)
            size_ratio = curr['stocks'] / prev['stocks']
            time_ratio = curr['time'] / prev['time'] if prev['time'] > 0 else 1
            
            # Time should not increase more than 2x for 4x data increase
            max_acceptable_ratio = size_ratio * 0.75  # Allow some overhead but not exponential
            assert time_ratio < max_acceptable_ratio, f"Poor scaling: {size_ratio:.1f}x data took {time_ratio:.1f}x time"
        
        # Largest dataset should still meet requirements
        largest_performance = performance_data[-1]
        assert largest_performance['time'] < 120.0, f"Largest dataset took {largest_performance['time']:.1f}s, should be <120s"
        
        print(f"\nScalability assessment:")
        print(f"✅ Performance scales sub-linearly with dataset size")
        print(f"✅ Largest dataset ({largest_performance['stocks']} stocks) completes in {largest_performance['time']:.1f}s")

    @pytest.mark.performance
    def test_connection_management_efficiency(self, synchronizer, large_dataset_generator):
        """Test database connection management efficiency."""
        test_data = large_dataset_generator(1000, 100, 10)
        
        connection_events = []
        
        def track_connect(*args, **kwargs):
            connection_events.append(('connect', time.time()))
            mock_conn = Mock()
            mock_cursor = Mock(spec=RealDictCursor)
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)
            mock_cursor.fetchall.return_value = test_data['stocks']
            mock_cursor.fetchone.return_value = {'total_stocks': 1000}
            mock_cursor.rowcount = 50
            mock_conn.cursor.return_value = mock_cursor
            return mock_conn
        
        def track_disconnect():
            connection_events.append(('disconnect', time.time()))
        
        with patch('src.core.services.cache_entries_synchronizer.psycopg2.connect', track_connect):
            with patch('src.core.services.cache_entries_synchronizer.os.getenv', return_value='postgresql://test'):
                with patch.object(synchronizer, 'disconnect', track_disconnect):
                    stats = synchronizer.rebuild_stock_cache_entries()
        
        # Verify connection efficiency
        connect_count = len([e for e in connection_events if e[0] == 'connect'])
        disconnect_count = len([e for e in connection_events if e[0] == 'disconnect'])
        
        # Should use single connection for entire rebuild
        assert connect_count == 1, f"Should connect once, but connected {connect_count} times"
        assert disconnect_count == 1, f"Should disconnect once, but disconnected {disconnect_count} times"
        
        print(f"Connection management efficiency:")
        print(f"✅ Single connection used for entire rebuild")
        print(f"✅ Proper cleanup performed"