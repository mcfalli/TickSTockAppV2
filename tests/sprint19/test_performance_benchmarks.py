"""
Sprint 19 Performance Benchmarks Test Suite
Comprehensive performance validation for Pattern Discovery API components.

Performance Targets:
- API response times: <50ms for 95th percentile
- Redis cache operations: <25ms for pattern scans
- Database queries: <50ms for symbol/user data
- Cache hit ratio: >70% after warm-up period
- Concurrent load testing: Support 100+ simultaneous API requests
- Memory stability: No memory leaks during sustained processing
"""

import pytest
import time
import json
import gc
import psutil
import os
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

# Sprint 19 imports
from src.infrastructure.cache.redis_pattern_cache import RedisPatternCache
from src.api.rest.pattern_consumer import pattern_consumer_bp
from src.api.rest.user_universe import user_universe_bp


@pytest.mark.performance
class TestRedisPatternCachePerformance:
    """Performance benchmarks for Redis Pattern Cache operations."""
    
    def test_pattern_caching_speed(self, redis_pattern_cache, pattern_data_generator, 
                                  performance_benchmark):
        """Test pattern caching performance with large datasets."""
        target_ms = 25  # <25ms for Redis operations
        
        # Generate test patterns
        patterns = pattern_data_generator.generate_patterns(500)  # Large dataset
        events = [{'event_type': 'pattern_detected', 'data': p} for p in patterns]
        
        # Benchmark pattern caching
        for i, event in enumerate(events):
            result, elapsed_ms = performance_benchmark.measure(
                redis_pattern_cache.process_pattern_event, event
            )
            assert result is True
            
            if i < 100:  # Check early operations more strictly
                performance_benchmark.assert_performance(elapsed_ms, f"Pattern caching #{i}")
        
        # Analyze performance statistics
        perf_stats = performance_benchmark.get_statistics()
        
        print(f"\nPattern Caching Performance:")
        print(f"  Patterns processed: {len(events)}")
        print(f"  Average time: {perf_stats['avg_ms']:.2f}ms")
        print(f"  P95 time: {perf_stats['p95_ms']:.2f}ms")
        print(f"  P99 time: {perf_stats['p99_ms']:.2f}ms")
        print(f"  Target met: {perf_stats['target_met_pct']:.1f}%")
        
        # Performance assertions
        assert perf_stats['p95_ms'] < target_ms, f"P95 {perf_stats['p95_ms']:.2f}ms exceeds {target_ms}ms"
        assert perf_stats['target_met_pct'] >= 90, "Less than 90% of operations met target"
    
    def test_pattern_scanning_performance(self, redis_pattern_cache, multiple_pattern_events,
                                         performance_benchmark):
        """Test pattern scanning performance under various scenarios."""
        # Cache patterns first
        for event in multiple_pattern_events:
            redis_pattern_cache.process_pattern_event(event)
        
        # Define scan scenarios with varying complexity
        scan_scenarios = [
            # Simple scans
            {'confidence_min': 0.5, 'per_page': 10, 'scenario': 'basic_scan'},
            {'confidence_min': 0.7, 'per_page': 20, 'scenario': 'moderate_filter'},
            
            # Complex scans
            {
                'confidence_min': 0.6,
                'symbols': ['AAPL', 'GOOGL', 'MSFT'],
                'pattern_types': ['Weekly_Breakout', 'Volume_Spike'],
                'rs_min': 1.2,
                'per_page': 15,
                'scenario': 'complex_multi_filter'
            },
            
            # Large result sets
            {'confidence_min': 0.3, 'per_page': 50, 'scenario': 'large_results'},
            
            # Sorting variations
            {
                'confidence_min': 0.5,
                'sort_by': 'symbol',
                'sort_order': 'asc',
                'per_page': 25,
                'scenario': 'symbol_sort'
            }
        ]
        
        target_ms = 50  # <50ms for scan operations
        scenario_results = {}
        
        for scenario_config in scan_scenarios:
            scenario_name = scenario_config.pop('scenario')
            scenario_times = []
            
            # Run multiple iterations for statistical significance
            for _ in range(10):
                result, elapsed_ms = performance_benchmark.measure(
                    redis_pattern_cache.scan_patterns, scenario_config
                )
                
                assert 'patterns' in result
                scenario_times.append(elapsed_ms)
            
            # Calculate scenario statistics
            avg_time = sum(scenario_times) / len(scenario_times)
            max_time = max(scenario_times)
            min_time = min(scenario_times)
            
            scenario_results[scenario_name] = {
                'avg_ms': avg_time,
                'max_ms': max_time,
                'min_ms': min_time,
                'target_met': all(t <= target_ms for t in scenario_times)
            }
            
            print(f"\n{scenario_name} Performance:")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  Range: {min_time:.2f}ms - {max_time:.2f}ms")
            print(f"  Target met: {scenario_results[scenario_name]['target_met']}")
            
            # Assert performance targets
            assert avg_time < target_ms, f"{scenario_name} average {avg_time:.2f}ms exceeds {target_ms}ms"
            assert max_time < target_ms * 1.5, f"{scenario_name} max {max_time:.2f}ms too high"
        
        # Overall performance assertion
        all_scenarios_passed = all(r['target_met'] for r in scenario_results.values())
        assert all_scenarios_passed, "Not all scan scenarios met performance targets"
    
    def test_cache_hit_ratio_performance(self, redis_pattern_cache, multiple_pattern_events):
        """Test cache hit ratio performance and effectiveness."""
        # Cache patterns
        for event in multiple_pattern_events:
            redis_pattern_cache.process_pattern_event(event)
        
        # Define repeatable query patterns to build cache hits
        query_patterns = [
            {'confidence_min': 0.6, 'per_page': 10},
            {'confidence_min': 0.7, 'sort_by': 'symbol'},
            {'symbols': ['AAPL', 'GOOGL'], 'per_page': 15},
            {'pattern_types': ['Weekly_Breakout'], 'per_page': 20}
        ]
        
        cache_hit_times = []
        cache_miss_times = []
        
        # Generate cache misses and hits
        for i in range(50):
            query = query_patterns[i % len(query_patterns)].copy()
            
            # First request = cache miss, subsequent = cache hits
            if i < len(query_patterns):
                # Add variation to ensure cache miss
                query['page'] = i + 1
            
            start_time = time.perf_counter()
            result = redis_pattern_cache.scan_patterns(query)
            end_time = time.perf_counter()
            
            elapsed_ms = (end_time - start_time) * 1000
            
            # Categorize as hit or miss based on response
            if result.get('cache_info', {}).get('cached', False):
                cache_hit_times.append(elapsed_ms)
            else:
                cache_miss_times.append(elapsed_ms)
        
        # Analyze cache performance
        stats = redis_pattern_cache.get_cache_stats()
        hit_ratio = stats['cache_hit_ratio']
        
        print(f"\nCache Hit Ratio Performance:")
        print(f"  Hit ratio: {hit_ratio:.1%}")
        print(f"  Cache hits: {len(cache_hit_times)}")
        print(f"  Cache misses: {len(cache_miss_times)}")
        
        if cache_hit_times:
            avg_hit_time = sum(cache_hit_times) / len(cache_hit_times)
            print(f"  Average hit time: {avg_hit_time:.2f}ms")
            
            # Cache hits should be significantly faster
            assert avg_hit_time < 10, f"Cache hits too slow: {avg_hit_time:.2f}ms"
        
        if cache_miss_times:
            avg_miss_time = sum(cache_miss_times) / len(cache_miss_times)
            print(f"  Average miss time: {avg_miss_time:.2f}ms")
            
            # Cache misses should still be reasonable
            assert avg_miss_time < 50, f"Cache misses too slow: {avg_miss_time:.2f}ms"
        
        # Hit ratio should meet target after warm-up
        target_hit_ratio = 0.70
        assert hit_ratio >= target_hit_ratio, f"Hit ratio {hit_ratio:.1%} below {target_hit_ratio:.1%} target"
    
    def test_memory_usage_under_load(self, redis_pattern_cache, pattern_data_generator):
        """Test memory usage and stability under sustained load."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"\nMemory Load Test:")
        print(f"  Initial memory: {initial_memory:.2f} MB")
        
        # Generate large dataset
        large_pattern_count = 1000
        patterns = pattern_data_generator.generate_patterns(large_pattern_count)
        events = [{'event_type': 'pattern_detected', 'data': p} for p in patterns]
        
        # Process patterns in batches to monitor memory
        batch_size = 100
        memory_readings = []
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            
            # Process batch
            for event in batch:
                success = redis_pattern_cache.process_pattern_event(event)
                assert success is True
            
            # Force garbage collection
            gc.collect()
            
            # Take memory reading
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_readings.append(current_memory)
            
            if len(memory_readings) % 2 == 0:
                print(f"  Processed {i + len(batch)} patterns, Memory: {current_memory:.2f} MB")
        
        final_memory = memory_readings[-1]
        memory_growth = final_memory - initial_memory
        max_memory = max(memory_readings)
        
        print(f"  Final memory: {final_memory:.2f} MB")
        print(f"  Memory growth: {memory_growth:.2f} MB")
        print(f"  Peak memory: {max_memory:.2f} MB")
        
        # Memory growth should be reasonable (allow for Redis data)
        expected_growth_limit = 50  # MB - adjust based on pattern data size
        assert memory_growth < expected_growth_limit, f"Excessive memory growth: {memory_growth:.2f} MB"
        
        # Memory should be stable (not continuously growing)
        recent_readings = memory_readings[-5:]
        memory_variance = max(recent_readings) - min(recent_readings)
        assert memory_variance < 10, f"Unstable memory usage: {memory_variance:.2f} MB variance"


@pytest.mark.performance
class TestPatternConsumerAPIPerformance:
    """Performance benchmarks for Pattern Consumer API endpoints."""
    
    def test_api_response_times(self, app_with_mocks, performance_benchmark):
        """Test API response time performance across all endpoints."""
        client = app_with_mocks.test_client()
        
        # Mock consistent fast responses
        mock_scan_response = {
            'patterns': [
                {'symbol': 'TEST', 'pattern': 'Test', 'conf': 0.8, 'rs': '1x',
                 'vol': '1x', 'price': '$100', 'chg': '+1%', 'time': '1m',
                 'exp': '30m', 'source': 'test'}
            ],
            'pagination': {'page': 1, 'per_page': 30, 'total': 1, 'pages': 1}
        }
        
        mock_stats = {'cached_patterns': 100, 'cache_hit_ratio': 0.75}
        
        app_with_mocks.pattern_cache.scan_patterns.return_value = mock_scan_response
        app_with_mocks.pattern_cache.get_cache_stats.return_value = mock_stats
        
        # Test endpoints with performance measurement
        endpoints = [
            ('/api/patterns/scan', 'Basic scan'),
            ('/api/patterns/scan?confidence_min=0.7&per_page=20', 'Filtered scan'),
            ('/api/patterns/stats', 'Pattern stats'),
            ('/api/patterns/summary', 'Pattern summary'),
            ('/api/patterns/health', 'Health check')
        ]
        
        target_ms = 50
        endpoint_results = {}
        
        for endpoint, description in endpoints:
            endpoint_times = []
            
            # Multiple requests for statistical significance
            for _ in range(20):
                def make_request():
                    response = client.get(endpoint)
                    return response.status_code == 200
                
                result, elapsed_ms = performance_benchmark.measure(make_request)
                assert result is True
                endpoint_times.append(elapsed_ms)
            
            # Calculate statistics
            avg_time = sum(endpoint_times) / len(endpoint_times)
            p95_time = sorted(endpoint_times)[int(len(endpoint_times) * 0.95)]
            
            endpoint_results[endpoint] = {
                'avg_ms': avg_time,
                'p95_ms': p95_time,
                'target_met': p95_time <= target_ms
            }
            
            print(f"\n{description} ({endpoint}):")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  P95: {p95_time:.2f}ms")
            print(f"  Target met: {endpoint_results[endpoint]['target_met']}")
            
            # Assert performance targets
            assert p95_time <= target_ms, f"{description} P95 {p95_time:.2f}ms exceeds {target_ms}ms"
        
        # Overall API performance summary
        all_targets_met = all(r['target_met'] for r in endpoint_results.values())
        avg_p95 = sum(r['p95_ms'] for r in endpoint_results.values()) / len(endpoint_results)
        
        print(f"\nOverall API Performance:")
        print(f"  Average P95 across endpoints: {avg_p95:.2f}ms")
        print(f"  All targets met: {all_targets_met}")
        
        assert all_targets_met, "Not all API endpoints met performance targets"
    
    def test_concurrent_api_load_performance(self, app_with_mocks, concurrent_load_tester):
        """Test API performance under concurrent load."""
        client = app_with_mocks.test_client()
        
        # Mock responses
        mock_response = {
            'patterns': [{'symbol': 'LOAD_TEST', 'pattern': 'Load', 'conf': 0.8,
                         'rs': '1x', 'vol': '1x', 'price': '$100', 'chg': '+1%',
                         'time': '1m', 'exp': '30m', 'source': 'test'}],
            'pagination': {'page': 1, 'per_page': 30, 'total': 1, 'pages': 1}
        }
        app_with_mocks.pattern_cache.scan_patterns.return_value = mock_response
        
        def make_concurrent_request():
            response = client.get('/api/patterns/scan?confidence_min=0.7')
            return response.status_code == 200
        
        # Test different concurrency levels
        concurrency_tests = [
            (50, 5, "Low concurrency"),
            (100, 10, "Medium concurrency"),
            (200, 20, "High concurrency")
        ]
        
        for num_requests, max_concurrent, test_name in concurrency_tests:
            print(f"\n{test_name} Test ({num_requests} requests, {max_concurrent} concurrent):")
            
            results = concurrent_load_tester.run_concurrent_requests(
                make_concurrent_request,
                num_requests=num_requests,
                max_concurrent=max_concurrent
            )
            
            # Analyze results
            successful = [r for r in results if r['success']]
            failed = [r for r in results if not r['success']]
            
            success_rate = len(successful) / len(results) * 100
            
            if successful:
                response_times = [r['elapsed_ms'] for r in successful if r['elapsed_ms']]
                avg_time = sum(response_times) / len(response_times)
                p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
                
                print(f"  Success rate: {success_rate:.1f}%")
                print(f"  Average response time: {avg_time:.2f}ms")
                print(f"  P95 response time: {p95_time:.2f}ms")
                print(f"  Failed requests: {len(failed)}")
                
                # Performance assertions
                assert success_rate >= 95, f"Success rate too low: {success_rate}%"
                assert p95_time <= 100, f"P95 response time too high under load: {p95_time:.2f}ms"
            else:
                pytest.fail(f"No successful requests in {test_name}")
    
    def test_api_throughput_capacity(self, app_with_mocks):
        """Test API throughput capacity and sustained load."""
        client = app_with_mocks.test_client()
        
        # Mock fast response
        mock_response = {
            'patterns': [],
            'pagination': {'page': 1, 'per_page': 30, 'total': 0, 'pages': 0}
        }
        app_with_mocks.pattern_cache.scan_patterns.return_value = mock_response
        
        # Measure sustained throughput
        duration_seconds = 10
        start_time = time.time()
        request_count = 0
        response_times = []
        
        while time.time() - start_time < duration_seconds:
            request_start = time.perf_counter()
            response = client.get('/api/patterns/scan?per_page=10')
            request_end = time.perf_counter()
            
            assert response.status_code == 200
            
            request_count += 1
            response_times.append((request_end - request_start) * 1000)
            
            # Small delay to prevent overwhelming
            time.sleep(0.01)
        
        actual_duration = time.time() - start_time
        throughput = request_count / actual_duration
        avg_response_time = sum(response_times) / len(response_times)
        
        print(f"\nThroughput Test Results:")
        print(f"  Duration: {actual_duration:.1f}s")
        print(f"  Total requests: {request_count}")
        print(f"  Throughput: {throughput:.1f} requests/second")
        print(f"  Average response time: {avg_response_time:.2f}ms")
        
        # Throughput assertions
        min_throughput = 50  # requests per second
        assert throughput >= min_throughput, f"Throughput {throughput:.1f} rps below {min_throughput} rps"
        assert avg_response_time <= 50, f"Average response time {avg_response_time:.2f}ms too high"


@pytest.mark.performance
class TestUserUniverseAPIPerformance:
    """Performance benchmarks for User Universe API endpoints."""
    
    def test_database_query_performance(self, app_with_mocks, performance_benchmark):
        """Test database query performance for User Universe API."""
        client = app_with_mocks.test_client()
        
        # Test database-dependent endpoints
        db_endpoints = [
            ('/api/symbols', 'Symbols listing'),
            ('/api/symbols/AAPL', 'Symbol details'),
            ('/api/dashboard/stats', 'Dashboard stats')
        ]
        
        target_ms = 50  # <50ms for database queries
        
        for endpoint, description in db_endpoints:
            db_times = []
            
            for _ in range(10):
                def make_request():
                    response = client.get(endpoint)
                    return response.status_code in [200, 404]  # Both are valid for testing
                
                result, elapsed_ms = performance_benchmark.measure(make_request)
                assert result is True
                db_times.append(elapsed_ms)
            
            avg_time = sum(db_times) / len(db_times)
            max_time = max(db_times)
            
            print(f"\n{description} Database Performance:")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  Maximum: {max_time:.2f}ms")
            
            # Database performance assertions
            assert avg_time <= target_ms, f"{description} average {avg_time:.2f}ms exceeds {target_ms}ms"
            assert max_time <= target_ms * 1.5, f"{description} max {max_time:.2f}ms too high"
    
    def test_cache_operations_performance(self, app_with_mocks, performance_benchmark):
        """Test cache operations performance for universe data."""
        client = app_with_mocks.test_client()
        
        # Test cache-dependent endpoints
        cache_endpoints = [
            ('/api/users/universe', 'Universe listing'),
            ('/api/users/universe/sp500_large', 'Universe tickers')
        ]
        
        target_ms = 25  # <25ms for cache operations
        
        for endpoint, description in cache_endpoints:
            cache_times = []
            
            for _ in range(15):
                def make_request():
                    response = client.get(endpoint)
                    return response.status_code in [200, 404, 503]
                
                result, elapsed_ms = performance_benchmark.measure(make_request)
                assert result is True
                cache_times.append(elapsed_ms)
            
            avg_time = sum(cache_times) / len(cache_times)
            p95_time = sorted(cache_times)[int(len(cache_times) * 0.95)]
            
            print(f"\n{description} Cache Performance:")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  P95: {p95_time:.2f}ms")
            
            # Cache performance assertions (more lenient due to mocking)
            assert p95_time <= target_ms * 2, f"{description} P95 {p95_time:.2f}ms too high"


@pytest.mark.performance
class TestIntegratedSystemPerformance:
    """End-to-end system performance tests."""
    
    def test_full_pattern_discovery_workflow_performance(self, app_with_mocks, 
                                                        multiple_pattern_events,
                                                        performance_benchmark):
        """Test complete pattern discovery workflow performance."""
        client = app_with_mocks.test_client()
        
        # Mock full workflow responses
        mock_scan_response = {
            'patterns': [
                {'symbol': 'AAPL', 'pattern': 'WeeklyBO', 'conf': 0.85,
                 'rs': '1.4x', 'vol': '2.1x', 'price': '$150.25',
                 'chg': '+2.3%', 'time': '5m', 'exp': '30m', 'source': 'daily'}
            ],
            'pagination': {'page': 1, 'per_page': 30, 'total': 1, 'pages': 1}
        }
        
        mock_stats = {'cached_patterns': 150, 'cache_hit_ratio': 0.75}
        
        app_with_mocks.pattern_cache.scan_patterns.return_value = mock_scan_response
        app_with_mocks.pattern_cache.get_cache_stats.return_value = mock_stats
        
        # Simulate full workflow
        workflow_steps = [
            ('/api/health', 'System health check'),
            ('/api/symbols?limit=10', 'Load symbols'),
            ('/api/users/universe', 'Load universes'),
            ('/api/patterns/scan?confidence_min=0.7', 'Scan patterns'),
            ('/api/patterns/stats', 'Get pattern stats'),
            ('/api/dashboard/stats', 'Get dashboard stats')
        ]
        
        total_workflow_times = []
        
        # Run complete workflow multiple times
        for workflow_run in range(5):
            workflow_start = time.perf_counter()
            step_times = []
            
            for endpoint, step_name in workflow_steps:
                step_start = time.perf_counter()
                response = client.get(endpoint)
                step_end = time.perf_counter()
                
                step_time = (step_end - step_start) * 1000
                step_times.append((step_name, step_time))
                
                # Each step should complete reasonably quickly
                assert response.status_code in [200, 404, 503], f"{step_name} failed"
                assert step_time <= 100, f"{step_name} took {step_time:.2f}ms"
            
            workflow_end = time.perf_counter()
            total_time = (workflow_end - workflow_start) * 1000
            total_workflow_times.append(total_time)
            
            print(f"\nWorkflow Run {workflow_run + 1}:")
            for step_name, step_time in step_times:
                print(f"  {step_name}: {step_time:.2f}ms")
            print(f"  Total: {total_time:.2f}ms")
        
        # Analyze workflow performance
        avg_workflow_time = sum(total_workflow_times) / len(total_workflow_times)
        max_workflow_time = max(total_workflow_times)
        
        print(f"\nWorkflow Performance Summary:")
        print(f"  Average total time: {avg_workflow_time:.2f}ms")
        print(f"  Maximum total time: {max_workflow_time:.2f}ms")
        
        # Workflow performance targets
        target_workflow_time = 300  # 300ms for complete workflow
        assert avg_workflow_time <= target_workflow_time, \
            f"Average workflow time {avg_workflow_time:.2f}ms exceeds {target_workflow_time}ms"
        assert max_workflow_time <= target_workflow_time * 1.5, \
            f"Maximum workflow time {max_workflow_time:.2f}ms too high"
    
    def test_system_scalability_limits(self, app_with_mocks, concurrent_load_tester):
        """Test system scalability and breaking point identification."""
        client = app_with_mocks.test_client()
        
        # Mock lightweight response
        mock_response = {'patterns': [], 'pagination': {'total': 0}}
        app_with_mocks.pattern_cache.scan_patterns.return_value = mock_response
        
        def make_scalability_request():
            response = client.get('/api/patterns/scan')
            return response.status_code == 200
        
        # Test increasing load levels
        load_levels = [
            (100, 10, "Baseline"),
            (250, 25, "Moderate load"),
            (500, 50, "High load"),
            (1000, 100, "Stress test")
        ]
        
        scalability_results = {}
        
        for num_requests, max_concurrent, load_name in load_levels:
            print(f"\n{load_name} ({num_requests} requests, {max_concurrent} concurrent):")
            
            try:
                results = concurrent_load_tester.run_concurrent_requests(
                    make_scalability_request,
                    num_requests=num_requests,
                    max_concurrent=max_concurrent
                )
                
                successful = [r for r in results if r['success']]
                success_rate = len(successful) / len(results) * 100
                
                if successful:
                    response_times = [r['elapsed_ms'] for r in successful if r['elapsed_ms']]
                    avg_time = sum(response_times) / len(response_times)
                    p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
                    
                    scalability_results[load_name] = {
                        'success_rate': success_rate,
                        'avg_time': avg_time,
                        'p95_time': p95_time,
                        'passed': success_rate >= 90 and p95_time <= 200
                    }
                    
                    print(f"  Success rate: {success_rate:.1f}%")
                    print(f"  Average time: {avg_time:.2f}ms")
                    print(f"  P95 time: {p95_time:.2f}ms")
                    print(f"  Passed: {scalability_results[load_name]['passed']}")
                
            except Exception as e:
                print(f"  Failed with exception: {e}")
                scalability_results[load_name] = {
                    'success_rate': 0,
                    'avg_time': float('inf'),
                    'p95_time': float('inf'),
                    'passed': False
                }
        
        # Find maximum sustainable load
        max_sustainable_load = None
        for load_name, results in scalability_results.items():
            if results['passed']:
                max_sustainable_load = load_name
        
        print(f"\nScalability Analysis:")
        print(f"  Maximum sustainable load: {max_sustainable_load}")
        
        # At minimum, baseline should pass
        assert scalability_results.get('Baseline', {}).get('passed', False), \
            "System failed baseline scalability test"


@pytest.mark.performance
class TestPerformanceRegression:
    """Performance regression tests to detect performance degradation."""
    
    def test_performance_baseline_comparison(self, redis_pattern_cache, 
                                           pattern_data_generator):
        """Compare current performance against baseline metrics."""
        # Define performance baselines (adjust based on initial benchmarking)
        baselines = {
            'pattern_caching_ms': 25,
            'pattern_scanning_ms': 50,
            'cache_hit_ratio': 0.70
        }
        
        # Test pattern caching performance
        patterns = pattern_data_generator.generate_patterns(100)
        events = [{'event_type': 'pattern_detected', 'data': p} for p in patterns]
        
        caching_times = []
        for event in events:
            start_time = time.perf_counter()
            result = redis_pattern_cache.process_pattern_event(event)
            end_time = time.perf_counter()
            
            assert result is True
            caching_times.append((end_time - start_time) * 1000)
        
        avg_caching_time = sum(caching_times) / len(caching_times)
        
        # Test pattern scanning performance
        scan_filters = {'confidence_min': 0.6, 'per_page': 20}
        
        scanning_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            result = redis_pattern_cache.scan_patterns(scan_filters)
            end_time = time.perf_counter()
            
            assert 'patterns' in result
            scanning_times.append((end_time - start_time) * 1000)
        
        avg_scanning_time = sum(scanning_times) / len(scanning_times)
        
        # Test cache hit ratio
        stats = redis_pattern_cache.get_cache_stats()
        hit_ratio = stats['cache_hit_ratio']
        
        # Compare against baselines
        current_metrics = {
            'pattern_caching_ms': avg_caching_time,
            'pattern_scanning_ms': avg_scanning_time,
            'cache_hit_ratio': hit_ratio
        }
        
        print(f"\nPerformance Baseline Comparison:")
        
        regression_detected = False
        for metric, current_value in current_metrics.items():
            baseline_value = baselines[metric]
            
            if metric == 'cache_hit_ratio':
                # Higher is better for hit ratio
                performance_ratio = current_value / baseline_value
                regression = performance_ratio < 0.9  # 10% degradation threshold
            else:
                # Lower is better for time metrics
                performance_ratio = baseline_value / current_value  # Inverted for time
                regression = current_value > baseline_value * 1.2  # 20% degradation threshold
            
            print(f"  {metric}:")
            print(f"    Baseline: {baseline_value}")
            print(f"    Current: {current_value:.2f}")
            print(f"    Performance ratio: {performance_ratio:.2f}")
            print(f"    Regression: {regression}")
            
            if regression:
                regression_detected = True
        
        # Assert no significant performance regression
        assert not regression_detected, "Performance regression detected against baseline"
    
    def test_memory_leak_detection(self, redis_pattern_cache, pattern_data_generator):
        """Detect potential memory leaks in pattern processing."""
        process = psutil.Process(os.getpid())
        
        # Baseline memory measurement
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process patterns in cycles to detect leaks
        cycles = 5
        patterns_per_cycle = 200
        
        memory_after_cycles = []
        
        for cycle in range(cycles):
            # Generate and process patterns
            patterns = pattern_data_generator.generate_patterns(patterns_per_cycle)
            events = [{'event_type': 'pattern_detected', 'data': p} for p in patterns]
            
            for event in events:
                redis_pattern_cache.process_pattern_event(event)
            
            # Clear some patterns to simulate normal cleanup
            if cycle > 0:
                redis_pattern_cache._cleanup_expired_patterns()
            
            # Force garbage collection
            gc.collect()
            
            # Measure memory
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_after_cycles.append(current_memory)
            
            print(f"  Cycle {cycle + 1}: {current_memory:.2f} MB "
                  f"(+{current_memory - initial_memory:.2f} MB)")
        
        # Analyze memory growth pattern
        memory_growth = [mem - initial_memory for mem in memory_after_cycles]
        
        # Check for continuous growth (potential leak)
        if len(memory_growth) >= 3:
            # Memory should stabilize after initial growth
            recent_growth = memory_growth[-3:]  # Last 3 cycles
            growth_variance = max(recent_growth) - min(recent_growth)
            
            print(f"\nMemory Leak Analysis:")
            print(f"  Initial memory: {initial_memory:.2f} MB")
            print(f"  Final memory: {memory_after_cycles[-1]:.2f} MB")
            print(f"  Total growth: {memory_growth[-1]:.2f} MB")
            print(f"  Recent variance: {growth_variance:.2f} MB")
            
            # Memory should be stable (low variance in recent cycles)
            assert growth_variance < 5, f"Potential memory leak: {growth_variance:.2f} MB variance"
            
            # Total growth should be reasonable
            max_acceptable_growth = 20  # MB
            assert memory_growth[-1] < max_acceptable_growth, \
                f"Excessive memory growth: {memory_growth[-1]:.2f} MB"


if __name__ == "__main__":
    # Allow running performance tests directly
    pytest.main([__file__, "-v", "-m", "performance", "--tb=short"])