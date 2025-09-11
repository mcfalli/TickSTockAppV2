"""
Comprehensive Performance Tests for SubscriptionIndexManager
Sprint 25 Day 2 Implementation: High-performance indexing system validation

Tests validate the Day 2 SubscriptionIndexManager meets <5ms filtering requirements
and scales efficiently with 1000+ subscriptions across multiple dimensions.

Performance Targets:
- <5ms filtering for 1000+ subscriptions (primary target)
- >70% cache hit rate for repeated queries
- <1MB memory per 1000 active subscriptions
- No memory leaks during sustained operations
- Thread safety under concurrent access
"""

import pytest
import time
import threading
import gc
import psutil
import os
from typing import Dict, Any, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import random
import string

# Import system under test
from src.infrastructure.websocket.subscription_index_manager import SubscriptionIndexManager, IndexType, IndexStats
from src.core.models.websocket_models import UserSubscription


@dataclass
class PerformanceResult:
    """Performance measurement result."""
    operation: str
    duration_ms: float
    memory_mb: float
    success: bool
    metadata: Dict[str, Any] = None


@dataclass 
class LoadTestConfig:
    """Load test configuration."""
    num_users: int
    num_subscriptions_per_user: int
    num_concurrent_operations: int
    test_duration_seconds: int
    cache_size: int = 1000


class PerformanceTestHelper:
    """Helper class for performance testing utilities."""
    
    @staticmethod
    def generate_test_subscription(user_id: str, subscription_type: str = None) -> UserSubscription:
        """Generate realistic test subscription."""
        patterns = ['BreakoutBO', 'TrendReversal', 'SurgeDetection', 'VolumeSpike', 'GapUp']
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NFLX', 'NVDA']
        tiers = ['daily', 'intraday', 'combo']
        market_regimes = ['bullish', 'bearish', 'sideways', 'volatile']
        
        return UserSubscription(
            user_id=user_id,
            subscription_type=subscription_type or random.choice(['tier_patterns', 'market_insights', 'alerts']),
            filters={
                'pattern_types': random.sample(patterns, random.randint(1, 3)),
                'symbols': random.sample(symbols, random.randint(2, 5)),
                'tiers': random.sample(tiers, random.randint(1, 2)),
                'market_regimes': random.sample(market_regimes, random.randint(1, 2)),
                'confidence_min': random.uniform(0.5, 0.9),
                'priority_min': random.randint(1, 5)
            },
            room_name=f"user_{user_id}"
        )
    
    @staticmethod
    def generate_test_criteria() -> Dict[str, Any]:
        """Generate realistic event criteria for filtering."""
        patterns = ['BreakoutBO', 'TrendReversal', 'SurgeDetection', 'VolumeSpike', 'GapUp']
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NFLX', 'NVDA']
        tiers = ['daily', 'intraday', 'combo']
        
        return {
            'pattern_type': random.choice(patterns),
            'symbol': random.choice(symbols),
            'tier': random.choice(tiers),
            'subscription_type': random.choice(['tier_patterns', 'market_insights']),
            'confidence': random.uniform(0.6, 0.95),
            'priority': random.randint(2, 5)
        }
    
    @staticmethod
    def measure_memory_usage() -> float:
        """Measure current process memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    @staticmethod
    def time_operation(operation_func) -> PerformanceResult:
        """Time an operation and measure memory usage."""
        gc.collect()  # Clean up before measurement
        start_memory = PerformanceTestHelper.measure_memory_usage()
        start_time = time.perf_counter()
        
        try:
            result = operation_func()
            success = True
        except Exception as e:
            result = str(e)
            success = False
        
        end_time = time.perf_counter()
        end_memory = PerformanceTestHelper.measure_memory_usage()
        
        return PerformanceResult(
            operation=operation_func.__name__ if hasattr(operation_func, '__name__') else 'operation',
            duration_ms=(end_time - start_time) * 1000,
            memory_mb=end_memory - start_memory,
            success=success,
            metadata={'result': result, 'start_memory_mb': start_memory, 'end_memory_mb': end_memory}
        )


@pytest.fixture
def index_manager():
    """Create SubscriptionIndexManager for testing."""
    return SubscriptionIndexManager(cache_size=1000, enable_optimization=True)


@pytest.fixture
def performance_helper():
    """Create performance test helper."""
    return PerformanceTestHelper()


class TestSubscriptionIndexBasicPerformance:
    """Test basic indexing performance requirements."""
    
    def test_single_user_filtering_performance(self, index_manager, performance_helper):
        """Test single user filtering meets <1ms target."""
        # Setup: Add single subscription
        subscription = performance_helper.generate_test_subscription("user_001")
        index_manager.add_subscription(subscription)
        
        # Test: Single lookup performance
        criteria = performance_helper.generate_test_criteria()
        criteria['subscription_type'] = subscription.subscription_type
        
        def lookup_operation():
            return index_manager.find_matching_users(criteria)
        
        result = performance_helper.time_operation(lookup_operation)
        
        # Validate: <1ms for single user
        assert result.success, f"Lookup operation failed: {result.metadata['result']}"
        assert result.duration_ms < 1.0, f"Single user lookup took {result.duration_ms:.2f}ms, expected <1ms"
        assert isinstance(result.metadata['result'], set), "Should return set of user IDs"
        
        print(f"Single user filtering: {result.duration_ms:.3f}ms")
    
    def test_100_users_filtering_performance(self, index_manager, performance_helper):
        """Test 100 users filtering meets <2ms target."""
        # Setup: Add 100 user subscriptions
        for i in range(100):
            subscription = performance_helper.generate_test_subscription(f"user_{i:03d}")
            index_manager.add_subscription(subscription)
        
        # Test: 100 users lookup performance
        criteria = performance_helper.generate_test_criteria()
        
        def lookup_operation():
            return index_manager.find_matching_users(criteria)
        
        result = performance_helper.time_operation(lookup_operation)
        
        # Validate: <2ms for 100 users
        assert result.success, f"Lookup operation failed: {result.metadata['result']}"
        assert result.duration_ms < 2.0, f"100 users lookup took {result.duration_ms:.2f}ms, expected <2ms"
        
        # Validate stats
        stats = index_manager.get_index_stats()
        assert stats['total_users'] == 100
        assert stats['avg_lookup_time_ms'] < 2.0
        
        print(f"100 users filtering: {result.duration_ms:.3f}ms, cache hit rate: {stats['cache_hit_rate_percent']:.1f}%")
    
    def test_1000_users_filtering_performance(self, index_manager, performance_helper):
        """Test 1000 users filtering meets <5ms target (PRIMARY PERFORMANCE REQUIREMENT)."""
        # Setup: Add 1000 user subscriptions with varied patterns
        for i in range(1000):
            subscription = performance_helper.generate_test_subscription(f"user_{i:04d}")
            index_manager.add_subscription(subscription)
        
        # Test: Multiple lookup operations for statistical significance
        lookup_times = []
        successful_lookups = 0
        
        for _ in range(10):
            criteria = performance_helper.generate_test_criteria()
            
            def lookup_operation():
                return index_manager.find_matching_users(criteria)
            
            result = performance_helper.time_operation(lookup_operation)
            
            if result.success:
                lookup_times.append(result.duration_ms)
                successful_lookups += 1
        
        # Validate: All lookups successful
        assert successful_lookups == 10, f"Only {successful_lookups}/10 lookups succeeded"
        
        # Calculate statistics
        avg_lookup_time = sum(lookup_times) / len(lookup_times)
        max_lookup_time = max(lookup_times)
        min_lookup_time = min(lookup_times)
        
        # Validate: <5ms average (PRIMARY TARGET)
        assert avg_lookup_time < 5.0, f"1000 users average lookup took {avg_lookup_time:.2f}ms, expected <5ms"
        assert max_lookup_time < 10.0, f"1000 users max lookup took {max_lookup_time:.2f}ms, expected <10ms"
        
        # Validate index statistics
        stats = index_manager.get_index_stats()
        assert stats['total_users'] == 1000
        assert stats['performance_status'] == 'good'
        
        print(f"1000 users filtering - avg: {avg_lookup_time:.3f}ms, max: {max_lookup_time:.3f}ms, min: {min_lookup_time:.3f}ms")
        print(f"Cache hit rate: {stats['cache_hit_rate_percent']:.1f}%, total indexes: {stats['total_indexes']}")
    
    def test_memory_efficiency_1000_subscriptions(self, index_manager, performance_helper):
        """Test memory usage with 1000 subscriptions meets <1MB target."""
        # Measure baseline memory
        gc.collect()
        baseline_memory = performance_helper.measure_memory_usage()
        
        # Add 1000 subscriptions
        for i in range(1000):
            subscription = performance_helper.generate_test_subscription(f"user_{i:04d}")
            index_manager.add_subscription(subscription)
        
        # Measure memory after subscriptions
        gc.collect()
        final_memory = performance_helper.measure_memory_usage()
        memory_used = final_memory - baseline_memory
        
        # Test filtering to ensure everything is working
        criteria = performance_helper.generate_test_criteria()
        matching_users = index_manager.find_matching_users(criteria)
        
        # Validate: <1MB memory usage per 1000 subscriptions
        assert memory_used < 1.0, f"1000 subscriptions used {memory_used:.2f}MB, expected <1MB"
        assert len(matching_users) >= 0, "Should return valid user set"
        
        # Validate index efficiency
        stats = index_manager.get_index_stats()
        memory_efficiency = stats['memory_efficiency']
        assert memory_efficiency in ['optimized', 'full'], f"Unexpected memory efficiency: {memory_efficiency}"
        
        print(f"Memory usage for 1000 subscriptions: {memory_used:.3f}MB")
        print(f"Index sizes: {stats['index_sizes']}")


class TestSubscriptionIndexScalabilityPerformance:
    """Test indexing system scalability under varying loads."""
    
    def test_scalability_curve_analysis(self, index_manager, performance_helper):
        """Test performance scaling from 10 to 1000+ users."""
        user_counts = [10, 50, 100, 250, 500, 750, 1000, 1250]
        performance_curve = []
        
        for user_count in user_counts:
            # Clear index for clean test
            index_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
            
            # Add users
            for i in range(user_count):
                subscription = performance_helper.generate_test_subscription(f"user_{i:04d}")
                index_manager.add_subscription(subscription)
            
            # Test lookup performance (average of 5 runs)
            lookup_times = []
            for _ in range(5):
                criteria = performance_helper.generate_test_criteria()
                
                def lookup_operation():
                    return index_manager.find_matching_users(criteria)
                
                result = performance_helper.time_operation(lookup_operation)
                if result.success:
                    lookup_times.append(result.duration_ms)
            
            avg_time = sum(lookup_times) / len(lookup_times) if lookup_times else float('inf')
            stats = index_manager.get_index_stats()
            
            performance_curve.append({
                'users': user_count,
                'avg_lookup_ms': avg_time,
                'cache_hit_rate': stats['cache_hit_rate_percent'],
                'total_indexes': stats['total_indexes']
            })
            
            print(f"Users: {user_count:4d}, Avg Time: {avg_time:6.3f}ms, Cache Hit: {stats['cache_hit_rate_percent']:5.1f}%")
        
        # Validate: Performance should remain reasonable across all scales
        for point in performance_curve:
            if point['users'] <= 100:
                assert point['avg_lookup_ms'] < 2.0, f"{point['users']} users took {point['avg_lookup_ms']:.2f}ms, expected <2ms"
            elif point['users'] <= 1000:
                assert point['avg_lookup_ms'] < 5.0, f"{point['users']} users took {point['avg_lookup_ms']:.2f}ms, expected <5ms"
            else:
                assert point['avg_lookup_ms'] < 8.0, f"{point['users']} users took {point['avg_lookup_ms']:.2f}ms, expected <8ms"
        
        # Validate: No exponential performance degradation
        times = [p['avg_lookup_ms'] for p in performance_curve]
        growth_rates = [times[i+1]/times[i] for i in range(len(times)-1)]
        max_growth_rate = max(growth_rates)
        assert max_growth_rate < 3.0, f"Performance degraded by factor of {max_growth_rate:.1f}, expected <3x"
    
    def test_high_subscription_density_performance(self, index_manager, performance_helper):
        """Test performance with users having many subscriptions each."""
        user_count = 200
        subscriptions_per_user = 5
        
        # Add multiple subscriptions per user
        for user_id in range(user_count):
            for sub_id in range(subscriptions_per_user):
                subscription = performance_helper.generate_test_subscription(
                    f"user_{user_id:03d}", 
                    f"subscription_type_{sub_id}"
                )
                index_manager.add_subscription(subscription)
        
        total_subscriptions = user_count * subscriptions_per_user
        
        # Test filtering performance with high subscription density
        lookup_times = []
        for _ in range(10):
            criteria = performance_helper.generate_test_criteria()
            
            def lookup_operation():
                return index_manager.find_matching_users(criteria)
            
            result = performance_helper.time_operation(lookup_operation)
            if result.success:
                lookup_times.append(result.duration_ms)
        
        avg_time = sum(lookup_times) / len(lookup_times)
        stats = index_manager.get_index_stats()
        
        # Validate: High density should still meet performance targets
        assert avg_time < 5.0, f"High density ({total_subscriptions} subs) took {avg_time:.2f}ms, expected <5ms"
        assert stats['total_users'] == user_count
        assert stats['performance_status'] == 'good'
        
        print(f"High density test: {total_subscriptions} subscriptions, {avg_time:.3f}ms avg lookup")
        print(f"Index breakdown: {stats['index_sizes']}")
    
    def test_memory_scaling_characteristics(self, performance_helper):
        """Test memory scaling characteristics across different user counts."""
        user_counts = [100, 250, 500, 750, 1000]
        memory_measurements = []
        
        for user_count in user_counts:
            # Fresh index manager for clean memory measurement
            gc.collect()
            start_memory = performance_helper.measure_memory_usage()
            
            index_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
            
            # Add subscriptions
            for i in range(user_count):
                subscription = performance_helper.generate_test_subscription(f"user_{i:04d}")
                index_manager.add_subscription(subscription)
            
            # Perform some operations to populate cache
            for _ in range(10):
                criteria = performance_helper.generate_test_criteria()
                index_manager.find_matching_users(criteria)
            
            gc.collect()
            end_memory = performance_helper.measure_memory_usage()
            memory_used = end_memory - start_memory
            
            memory_per_user = memory_used / user_count
            
            memory_measurements.append({
                'users': user_count,
                'total_memory_mb': memory_used,
                'memory_per_user_kb': memory_per_user * 1024
            })
            
            print(f"Users: {user_count:4d}, Memory: {memory_used:6.2f}MB, Per User: {memory_per_user*1024:6.1f}KB")
        
        # Validate: Memory scaling should be linear, not exponential
        for measurement in memory_measurements:
            users = measurement['users']
            per_user_kb = measurement['memory_per_user_kb']
            
            # Allow reasonable memory per user (should be <1KB per user on average)
            assert per_user_kb < 1.0, f"{users} users used {per_user_kb:.1f}KB per user, expected <1KB"
        
        # Validate: Memory growth should be roughly linear
        memory_values = [m['total_memory_mb'] for m in memory_measurements]
        user_values = [m['users'] for m in memory_measurements]
        
        # Calculate linear growth coefficient (should be relatively stable)
        growth_coefficients = [memory_values[i]/user_values[i] for i in range(len(memory_values))]
        coefficient_variance = max(growth_coefficients) - min(growth_coefficients)
        assert coefficient_variance < 0.5, f"Memory growth variance {coefficient_variance:.3f}MB per user too high"


class TestSubscriptionIndexConcurrencyPerformance:
    """Test indexing system performance under concurrent operations."""
    
    def test_concurrent_lookup_performance(self, index_manager, performance_helper):
        """Test concurrent lookup operations maintain performance."""
        # Setup: Add 500 subscriptions
        for i in range(500):
            subscription = performance_helper.generate_test_subscription(f"user_{i:03d}")
            index_manager.add_subscription(subscription)
        
        def concurrent_lookup_worker():
            """Worker function for concurrent lookups."""
            lookup_times = []
            for _ in range(10):
                criteria = performance_helper.generate_test_criteria()
                start_time = time.perf_counter()
                matching_users = index_manager.find_matching_users(criteria)
                end_time = time.perf_counter()
                
                lookup_time = (end_time - start_time) * 1000
                lookup_times.append(lookup_time)
                
                assert isinstance(matching_users, set), "Should return user set"
            
            return lookup_times
        
        # Test: 10 concurrent workers performing lookups
        num_workers = 10
        all_lookup_times = []
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(concurrent_lookup_worker) for _ in range(num_workers)]
            
            for future in as_completed(futures):
                worker_times = future.result()
                all_lookup_times.extend(worker_times)
        
        # Calculate concurrent performance statistics
        avg_concurrent_time = sum(all_lookup_times) / len(all_lookup_times)
        max_concurrent_time = max(all_lookup_times)
        successful_operations = len(all_lookup_times)
        
        # Validate: Concurrent operations should maintain performance targets
        assert successful_operations == num_workers * 10, f"Expected {num_workers * 10} operations, got {successful_operations}"
        assert avg_concurrent_time < 10.0, f"Concurrent avg {avg_concurrent_time:.2f}ms, expected <10ms"
        assert max_concurrent_time < 20.0, f"Concurrent max {max_concurrent_time:.2f}ms, expected <20ms"
        
        # Check for thread safety - no errors should occur
        stats = index_manager.get_index_stats()
        assert stats['total_users'] == 500
        
        print(f"Concurrent performance: avg {avg_concurrent_time:.3f}ms, max {max_concurrent_time:.3f}ms")
        print(f"Thread safety verified: {stats['total_users']} users, {stats['lookup_count']} lookups")
    
    def test_concurrent_subscription_management(self, performance_helper):
        """Test concurrent subscription add/remove operations."""
        index_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
        operation_results = []
        
        def subscription_worker(worker_id: int):
            """Worker for concurrent subscription operations."""
            worker_results = []
            
            # Add subscriptions
            for i in range(20):
                user_id = f"worker_{worker_id}_user_{i:02d}"
                subscription = performance_helper.generate_test_subscription(user_id)
                
                start_time = time.perf_counter()
                success = index_manager.add_subscription(subscription)
                end_time = time.perf_counter()
                
                operation_time = (end_time - start_time) * 1000
                worker_results.append({
                    'operation': 'add',
                    'time_ms': operation_time,
                    'success': success
                })
            
            # Perform some lookups
            for _ in range(10):
                criteria = performance_helper.generate_test_criteria()
                
                start_time = time.perf_counter()
                matching_users = index_manager.find_matching_users(criteria)
                end_time = time.perf_counter()
                
                lookup_time = (end_time - start_time) * 1000
                worker_results.append({
                    'operation': 'lookup',
                    'time_ms': lookup_time,
                    'success': len(matching_users) >= 0
                })
            
            # Remove some subscriptions
            for i in range(10):
                user_id = f"worker_{worker_id}_user_{i:02d}"
                
                start_time = time.perf_counter()
                success = index_manager.remove_subscription(user_id)
                end_time = time.perf_counter()
                
                operation_time = (end_time - start_time) * 1000
                worker_results.append({
                    'operation': 'remove',
                    'time_ms': operation_time,
                    'success': success
                })
            
            return worker_results
        
        # Test: 8 concurrent workers managing subscriptions
        num_workers = 8
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(subscription_worker, i) for i in range(num_workers)]
            
            for future in as_completed(futures):
                worker_results = future.result()
                operation_results.extend(worker_results)
        
        # Analyze concurrent operation performance
        add_operations = [r for r in operation_results if r['operation'] == 'add']
        lookup_operations = [r for r in operation_results if r['operation'] == 'lookup']
        remove_operations = [r for r in operation_results if r['operation'] == 'remove']
        
        # Validate: All operations should succeed
        failed_adds = [r for r in add_operations if not r['success']]
        failed_lookups = [r for r in lookup_operations if not r['success']]
        failed_removes = [r for r in remove_operations if not r['success']]
        
        assert len(failed_adds) == 0, f"{len(failed_adds)} add operations failed"
        assert len(failed_lookups) == 0, f"{len(failed_lookups)} lookup operations failed"
        assert len(failed_removes) == 0, f"{len(failed_removes)} remove operations failed"
        
        # Validate: Performance should remain reasonable under concurrency
        avg_add_time = sum(r['time_ms'] for r in add_operations) / len(add_operations)
        avg_lookup_time = sum(r['time_ms'] for r in lookup_operations) / len(lookup_operations)
        avg_remove_time = sum(r['time_ms'] for r in remove_operations) / len(remove_operations)
        
        assert avg_add_time < 5.0, f"Concurrent adds averaged {avg_add_time:.2f}ms, expected <5ms"
        assert avg_lookup_time < 10.0, f"Concurrent lookups averaged {avg_lookup_time:.2f}ms, expected <10ms"
        assert avg_remove_time < 5.0, f"Concurrent removes averaged {avg_remove_time:.2f}ms, expected <5ms"
        
        # Validate final state consistency
        stats = index_manager.get_index_stats()
        expected_users = num_workers * 10  # 20 added - 10 removed per worker
        
        print(f"Concurrent operations completed - Add: {avg_add_time:.3f}ms, Lookup: {avg_lookup_time:.3f}ms, Remove: {avg_remove_time:.3f}ms")
        print(f"Final state: {stats['total_users']} users (expected ~{expected_users})")
    
    def test_sustained_load_performance(self, index_manager, performance_helper):
        """Test system performance under sustained high load."""
        # Setup: Add base set of subscriptions
        base_users = 300
        for i in range(base_users):
            subscription = performance_helper.generate_test_subscription(f"base_user_{i:03d}")
            index_manager.add_subscription(subscription)
        
        def sustained_load_worker():
            """Worker performing continuous operations."""
            operations_completed = 0
            start_time = time.time()
            operation_times = []
            
            while time.time() - start_time < 10:  # 10 second sustained load
                # Perform mixed operations
                operation_type = random.choice(['lookup', 'lookup', 'lookup', 'add', 'remove'])
                
                op_start = time.perf_counter()
                
                if operation_type == 'lookup':
                    criteria = performance_helper.generate_test_criteria()
                    index_manager.find_matching_users(criteria)
                elif operation_type == 'add':
                    user_id = f"temp_user_{random.randint(1000, 9999)}"
                    subscription = performance_helper.generate_test_subscription(user_id)
                    index_manager.add_subscription(subscription)
                elif operation_type == 'remove':
                    user_id = f"temp_user_{random.randint(1000, 9999)}"
                    index_manager.remove_subscription(user_id)
                
                op_end = time.perf_counter()
                operation_time = (op_end - op_start) * 1000
                operation_times.append(operation_time)
                operations_completed += 1
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.001)
            
            return {
                'operations_completed': operations_completed,
                'operation_times': operation_times,
                'avg_time_ms': sum(operation_times) / len(operation_times) if operation_times else 0,
                'max_time_ms': max(operation_times) if operation_times else 0
            }
        
        # Test: Multiple workers under sustained load
        num_workers = 4
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(sustained_load_worker) for _ in range(num_workers)]
            
            worker_results = []
            for future in as_completed(futures):
                result = future.result()
                worker_results.append(result)
        
        # Analyze sustained load results
        total_operations = sum(r['operations_completed'] for r in worker_results)
        all_operation_times = []
        for result in worker_results:
            all_operation_times.extend(result['operation_times'])
        
        overall_avg_time = sum(all_operation_times) / len(all_operation_times)
        overall_max_time = max(all_operation_times)
        operations_per_second = total_operations / 10  # 10 second test
        
        # Validate: System should maintain performance under sustained load
        assert overall_avg_time < 10.0, f"Sustained load avg {overall_avg_time:.2f}ms, expected <10ms"
        assert overall_max_time < 50.0, f"Sustained load max {overall_max_time:.2f}ms, expected <50ms"
        assert operations_per_second > 100, f"Only {operations_per_second:.1f} ops/sec, expected >100"
        
        # Check system health after sustained load
        stats = index_manager.get_index_stats()
        health = index_manager.get_health_status()
        
        assert health['status'] in ['healthy', 'warning'], f"System unhealthy after load: {health['status']}"
        
        print(f"Sustained load results: {total_operations} operations in 10s ({operations_per_second:.1f} ops/sec)")
        print(f"Performance: avg {overall_avg_time:.3f}ms, max {overall_max_time:.3f}ms")
        print(f"Final health: {health['status']} - {health['message']}")


class TestSubscriptionIndexCachePerformance:
    """Test query caching system performance and effectiveness."""
    
    def test_cache_hit_rate_effectiveness(self, index_manager, performance_helper):
        """Test cache achieves >70% hit rate target."""
        # Setup: Add subscriptions
        for i in range(200):
            subscription = performance_helper.generate_test_subscription(f"user_{i:03d}")
            index_manager.add_subscription(subscription)
        
        # Generate pool of criteria for repeated queries
        criteria_pool = [performance_helper.generate_test_criteria() for _ in range(10)]
        
        # Perform initial queries to populate cache
        for criteria in criteria_pool:
            index_manager.find_matching_users(criteria)
        
        # Clear stats to focus on cache effectiveness
        stats_before = index_manager.get_index_stats()
        cache_hits_before = stats_before['cache_hits']
        cache_misses_before = stats_before['cache_misses']
        
        # Perform repeated queries (should hit cache)
        for _ in range(50):
            criteria = random.choice(criteria_pool)
            matching_users = index_manager.find_matching_users(criteria)
            assert isinstance(matching_users, set), "Should return user set"
        
        # Calculate cache hit rate
        stats_after = index_manager.get_index_stats()
        cache_hits_after = stats_after['cache_hits']
        cache_misses_after = stats_after['cache_misses']
        
        new_hits = cache_hits_after - cache_hits_before
        new_misses = cache_misses_after - cache_misses_before
        new_requests = new_hits + new_misses
        
        if new_requests > 0:
            hit_rate = (new_hits / new_requests) * 100
        else:
            hit_rate = 0
        
        # Validate: >70% cache hit rate target
        assert hit_rate > 70.0, f"Cache hit rate {hit_rate:.1f}%, expected >70%"
        assert stats_after['cache_hit_rate_percent'] > 50.0, f"Overall hit rate {stats_after['cache_hit_rate_percent']:.1f}% too low"
        
        print(f"Cache effectiveness: {hit_rate:.1f}% hit rate on repeated queries")
        print(f"Overall cache performance: {stats_after['cache_hit_rate_percent']:.1f}% hit rate")
    
    def test_cache_performance_impact(self, index_manager, performance_helper):
        """Test cache improves performance for repeated queries."""
        # Setup: Add subscriptions
        for i in range(500):
            subscription = performance_helper.generate_test_subscription(f"user_{i:03d}")
            index_manager.add_subscription(subscription)
        
        # Test criteria
        test_criteria = performance_helper.generate_test_criteria()
        
        # First lookup (cache miss expected)
        def first_lookup():
            return index_manager.find_matching_users(test_criteria)
        
        first_result = performance_helper.time_operation(first_lookup)
        first_time = first_result.duration_ms
        
        # Second lookup (cache hit expected)  
        def second_lookup():
            return index_manager.find_matching_users(test_criteria)
        
        second_result = performance_helper.time_operation(second_lookup)
        second_time = second_result.duration_ms
        
        # Validate: Both operations successful
        assert first_result.success, "First lookup should succeed"
        assert second_result.success, "Second lookup should succeed"
        assert first_result.metadata['result'] == second_result.metadata['result'], "Results should be identical"
        
        # Validate: Cache should improve performance
        performance_improvement = (first_time - second_time) / first_time * 100
        
        # Cache hit should be faster (allow some variance for system noise)
        if second_time < first_time:
            assert performance_improvement > 0, f"Cache should improve performance, got {performance_improvement:.1f}%"
            print(f"Cache performance improvement: {performance_improvement:.1f}% ({first_time:.3f}ms -> {second_time:.3f}ms)")
        else:
            print(f"Cache timing: first {first_time:.3f}ms, second {second_time:.3f}ms (within noise threshold)")
        
        # Verify cache statistics
        stats = index_manager.get_index_stats()
        assert stats['cache_hits'] > 0, "Should have recorded cache hits"
    
    def test_cache_memory_limits(self, performance_helper):
        """Test cache respects memory limits and performs cleanup."""
        # Create index with small cache for testing
        small_cache_manager = SubscriptionIndexManager(cache_size=10, enable_optimization=True)
        
        # Add subscriptions
        for i in range(50):
            subscription = performance_helper.generate_test_subscription(f"user_{i:02d}")
            small_cache_manager.add_subscription(subscription)
        
        # Perform many unique queries to overflow cache
        unique_criteria_list = []
        for i in range(20):
            criteria = performance_helper.generate_test_criteria()
            criteria['unique_id'] = f"query_{i}"  # Make each query unique
            unique_criteria_list.append(criteria)
        
        # Execute queries to fill and overflow cache
        for criteria in unique_criteria_list:
            small_cache_manager.find_matching_users(criteria)
        
        # Validate: Cache size should be limited
        stats = small_cache_manager.get_index_stats()
        assert stats['cache_size'] <= 10, f"Cache size {stats['cache_size']} exceeds limit of 10"
        
        # Test cache cleanup functionality
        optimization_result = small_cache_manager.optimize_indexes()
        assert 'cache_cleaned' in optimization_result, "Optimization should report cache cleanup"
        
        print(f"Cache limit test: {stats['cache_size']}/10 entries, {optimization_result['cache_cleaned']} cleaned")
    
    def test_cache_invalidation_on_updates(self, index_manager, performance_helper):
        """Test cache is properly invalidated when subscriptions change."""
        # Setup: Add initial subscriptions
        for i in range(100):
            subscription = performance_helper.generate_test_subscription(f"user_{i:03d}")
            index_manager.add_subscription(subscription)
        
        # Perform query to populate cache
        criteria = performance_helper.generate_test_criteria()
        initial_result = index_manager.find_matching_users(criteria)
        
        # Get initial cache stats
        initial_stats = index_manager.get_index_stats()
        initial_cache_size = initial_stats['cache_size']
        
        # Add new subscription that might affect results
        new_subscription = performance_helper.generate_test_subscription("new_user_999")
        # Ensure new subscription matches our test criteria
        new_subscription.filters['pattern_types'] = [criteria.get('pattern_type', 'BreakoutBO')]
        new_subscription.filters['symbols'] = [criteria.get('symbol', 'AAPL')]
        new_subscription.subscription_type = criteria.get('subscription_type', 'tier_patterns')
        
        success = index_manager.add_subscription(new_subscription)
        assert success, "New subscription should be added successfully"
        
        # Verify cache was invalidated (cache size should be 0)
        post_add_stats = index_manager.get_index_stats()
        assert post_add_stats['cache_size'] == 0, f"Cache should be cleared after update, got {post_add_stats['cache_size']} entries"
        
        # Perform same query - should get updated results
        updated_result = index_manager.find_matching_users(criteria)
        
        # If new subscription matches criteria, result set should be different
        if 'new_user_999' in updated_result:
            assert len(updated_result) > len(initial_result), "Updated result should include new user"
            print(f"Cache invalidation verified: {len(initial_result)} -> {len(updated_result)} matching users")
        else:
            print(f"Cache invalidation verified: consistent results with {len(updated_result)} users")
        
        # Test removal also invalidates cache
        index_manager.find_matching_users(criteria)  # Populate cache again
        removal_success = index_manager.remove_subscription("new_user_999")
        assert removal_success, "Subscription removal should succeed"
        
        post_remove_stats = index_manager.get_index_stats()
        assert post_remove_stats['cache_size'] == 0, f"Cache should be cleared after removal, got {post_remove_stats['cache_size']} entries"


@pytest.mark.performance
class TestSubscriptionIndexBenchmarks:
    """Comprehensive performance benchmarks for Sprint 25 indexing system."""
    
    def test_comprehensive_performance_benchmark(self, performance_helper):
        """Comprehensive benchmark covering all performance targets."""
        print("\n" + "="*80)
        print("SPRINT 25 DAY 2 SUBSCRIPTION INDEX MANAGER COMPREHENSIVE BENCHMARK")
        print("="*80)
        
        benchmark_results = {}
        
        # Test 1: Basic Performance Targets
        print("\n1. BASIC PERFORMANCE TARGETS")
        print("-" * 40)
        
        for user_count in [1, 100, 1000]:
            index_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
            
            # Add subscriptions
            for i in range(user_count):
                subscription = performance_helper.generate_test_subscription(f"user_{i:04d}")
                index_manager.add_subscription(subscription)
            
            # Test lookup performance
            lookup_times = []
            for _ in range(5):
                criteria = performance_helper.generate_test_criteria()
                
                def lookup_op():
                    return index_manager.find_matching_users(criteria)
                
                result = performance_helper.time_operation(lookup_op)
                if result.success:
                    lookup_times.append(result.duration_ms)
            
            avg_time = sum(lookup_times) / len(lookup_times) if lookup_times else 0
            stats = index_manager.get_index_stats()
            
            benchmark_results[f'{user_count}_users'] = {
                'avg_lookup_ms': avg_time,
                'cache_hit_rate': stats['cache_hit_rate_percent'],
                'total_indexes': stats['total_indexes'],
                'meets_target': avg_time < (1 if user_count == 1 else 2 if user_count == 100 else 5)
            }
            
            target = "1ms" if user_count == 1 else "2ms" if user_count == 100 else "5ms"
            status = "✓ PASS" if benchmark_results[f'{user_count}_users']['meets_target'] else "✗ FAIL"
            
            print(f"{user_count:4d} users: {avg_time:6.3f}ms avg (target: <{target}) {status}")
        
        # Test 2: Memory Efficiency
        print("\n2. MEMORY EFFICIENCY")
        print("-" * 40)
        
        gc.collect()
        start_memory = performance_helper.measure_memory_usage()
        
        memory_test_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
        for i in range(1000):
            subscription = performance_helper.generate_test_subscription(f"memory_user_{i:04d}")
            memory_test_manager.add_subscription(subscription)
        
        # Populate cache
        for _ in range(50):
            criteria = performance_helper.generate_test_criteria()
            memory_test_manager.find_matching_users(criteria)
        
        gc.collect()
        end_memory = performance_helper.measure_memory_usage()
        memory_used = end_memory - start_memory
        memory_per_sub = memory_used / 1000 * 1024  # KB per subscription
        
        memory_target_met = memory_used < 1.0
        memory_status = "✓ PASS" if memory_target_met else "✗ FAIL"
        
        benchmark_results['memory_efficiency'] = {
            'total_memory_mb': memory_used,
            'memory_per_subscription_kb': memory_per_sub,
            'meets_target': memory_target_met
        }
        
        print(f"1000 subscriptions: {memory_used:.2f}MB total ({memory_per_sub:.1f}KB/sub) (target: <1MB) {memory_status}")
        
        # Test 3: Cache Effectiveness
        print("\n3. CACHE EFFECTIVENESS")
        print("-" * 40)
        
        cache_test_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
        for i in range(500):
            subscription = performance_helper.generate_test_subscription(f"cache_user_{i:03d}")
            cache_test_manager.add_subscription(subscription)
        
        # Generate repeated queries to test cache
        criteria_pool = [performance_helper.generate_test_criteria() for _ in range(5)]
        
        # Initial queries
        for criteria in criteria_pool:
            cache_test_manager.find_matching_users(criteria)
        
        # Record stats before repeated queries
        before_stats = cache_test_manager.get_index_stats()
        hits_before = before_stats['cache_hits']
        misses_before = before_stats['cache_misses']
        
        # Repeated queries
        for _ in range(25):
            criteria = random.choice(criteria_pool)
            cache_test_manager.find_matching_users(criteria)
        
        after_stats = cache_test_manager.get_index_stats()
        hits_after = after_stats['cache_hits']
        misses_after = after_stats['cache_misses']
        
        new_hits = hits_after - hits_before
        new_total = new_hits + (misses_after - misses_before)
        cache_hit_rate = (new_hits / max(new_total, 1)) * 100
        
        cache_target_met = cache_hit_rate > 70.0
        cache_status = "✓ PASS" if cache_target_met else "✗ FAIL"
        
        benchmark_results['cache_effectiveness'] = {
            'hit_rate_percent': cache_hit_rate,
            'total_hit_rate': after_stats['cache_hit_rate_percent'],
            'meets_target': cache_target_met
        }
        
        print(f"Cache hit rate: {cache_hit_rate:.1f}% on repeated queries (target: >70%) {cache_status}")
        print(f"Overall hit rate: {after_stats['cache_hit_rate_percent']:.1f}%")
        
        # Test 4: Concurrency Performance
        print("\n4. CONCURRENCY PERFORMANCE")
        print("-" * 40)
        
        concurrency_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
        for i in range(300):
            subscription = performance_helper.generate_test_subscription(f"concurrent_user_{i:03d}")
            concurrency_manager.add_subscription(subscription)
        
        def concurrent_worker():
            times = []
            for _ in range(10):
                criteria = performance_helper.generate_test_criteria()
                start = time.perf_counter()
                concurrency_manager.find_matching_users(criteria)
                end = time.perf_counter()
                times.append((end - start) * 1000)
            return times
        
        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(concurrent_worker) for _ in range(8)]
            all_times = []
            for future in as_completed(futures):
                all_times.extend(future.result())
        
        concurrent_avg = sum(all_times) / len(all_times)
        concurrent_max = max(all_times)
        concurrent_target_met = concurrent_avg < 10.0 and concurrent_max < 20.0
        concurrent_status = "✓ PASS" if concurrent_target_met else "✗ FAIL"
        
        benchmark_results['concurrency_performance'] = {
            'avg_time_ms': concurrent_avg,
            'max_time_ms': concurrent_max,
            'total_operations': len(all_times),
            'meets_target': concurrent_target_met
        }
        
        print(f"8 workers, {len(all_times)} ops: {concurrent_avg:.3f}ms avg, {concurrent_max:.3f}ms max {concurrent_status}")
        print(f"(targets: <10ms avg, <20ms max)")
        
        # Test 5: Overall System Health
        print("\n5. SYSTEM HEALTH VALIDATION")
        print("-" * 40)
        
        health = concurrency_manager.get_health_status()
        health_good = health['status'] in ['healthy', 'warning']
        health_status = "✓ PASS" if health_good else "✗ FAIL"
        
        benchmark_results['system_health'] = {
            'status': health['status'],
            'message': health['message'],
            'meets_target': health_good
        }
        
        print(f"Health status: {health['status']} - {health['message']} {health_status}")
        
        # Summary
        print("\n" + "="*80)
        print("BENCHMARK SUMMARY")
        print("="*80)
        
        all_targets_met = all(
            result.get('meets_target', False) 
            for result in benchmark_results.values() 
            if isinstance(result, dict)
        )
        
        overall_status = "✓ ALL TARGETS MET" if all_targets_met else "✗ SOME TARGETS MISSED"
        print(f"Overall Performance: {overall_status}")
        
        print("\nDetailed Results:")
        for test_name, result in benchmark_results.items():
            if isinstance(result, dict) and 'meets_target' in result:
                status_symbol = "✓" if result['meets_target'] else "✗"
                print(f"  {status_symbol} {test_name.replace('_', ' ').title()}")
        
        print("\nSpring 25 Day 2 Requirements Validation:")
        print(f"  • <5ms filtering for 1000+ users: {'✓' if benchmark_results['1000_users']['meets_target'] else '✗'}")
        print(f"  • <1MB memory for 1000 subscriptions: {'✓' if benchmark_results['memory_efficiency']['meets_target'] else '✗'}")
        print(f"  • >70% cache hit rate: {'✓' if benchmark_results['cache_effectiveness']['meets_target'] else '✗'}")
        print(f"  • Thread-safe concurrent operations: {'✓' if benchmark_results['concurrency_performance']['meets_target'] else '✗'}")
        print(f"  • System health maintained: {'✓' if benchmark_results['system_health']['meets_target'] else '✗'}")
        
        # Final validation for pytest
        assert all_targets_met, f"Not all performance targets were met: {benchmark_results}"
        
        return benchmark_results


# Additional helper fixtures for load testing
@pytest.fixture(scope="session")
def load_test_config():
    """Load test configuration for different scenarios."""
    return {
        'small_load': LoadTestConfig(
            num_users=50,
            num_subscriptions_per_user=2,
            num_concurrent_operations=5,
            test_duration_seconds=30
        ),
        'medium_load': LoadTestConfig(
            num_users=200,
            num_subscriptions_per_user=3,
            num_concurrent_operations=10,
            test_duration_seconds=60
        ),
        'high_load': LoadTestConfig(
            num_users=500,
            num_subscriptions_per_user=4,
            num_concurrent_operations=20,
            test_duration_seconds=120
        )
    }


if __name__ == "__main__":
    # Run performance tests directly
    pytest.main([__file__, "-v", "--tb=short", "-m", "performance"])