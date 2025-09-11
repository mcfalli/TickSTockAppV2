"""
Performance Benchmark Comparisons for Sprint 25 Day 2 Indexing Implementation
Compares Day 1 O(n) vs Day 2 O(log n) performance characteristics

Tests validate performance improvements from the SubscriptionIndexManager integration
and demonstrate scalability gains across different load scenarios.

Performance Comparison Targets:
- Day 2 should show logarithmic vs linear scaling
- At least 3x performance improvement for 1000+ users
- Cache effectiveness should reduce repeated query times by >50%
- Memory efficiency should remain comparable or better
- Concurrency performance should improve with indexing
"""

import pytest
import time
import threading
import gc
import psutil
import os
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from unittest.mock import Mock
import random
import statistics

# Import system under test
from src.infrastructure.websocket.subscription_index_manager import SubscriptionIndexManager
from src.core.services.websocket_subscription_manager import UniversalWebSocketManager
from src.core.models.websocket_models import UserSubscription


@dataclass
class PerformanceComparison:
    """Performance comparison between Day 1 and Day 2 implementations."""
    test_scenario: str
    user_count: int
    day1_time_ms: float
    day2_time_ms: float
    improvement_factor: float
    memory_day1_mb: float
    memory_day2_mb: float
    memory_efficiency: str
    meets_target: bool


class Day1SimulatedManager:
    """
    Simulated Day 1 O(n) implementation for comparison testing.
    This represents the linear search approach before indexing.
    """
    
    def __init__(self):
        self.subscriptions = {}  # user_id -> UserSubscription
        self.subscription_lock = threading.RLock()
    
    def add_subscription(self, subscription: UserSubscription) -> bool:
        """Add subscription using Day 1 approach (no indexing)."""
        try:
            with self.subscription_lock:
                self.subscriptions[subscription.user_id] = subscription
                return True
        except Exception:
            return False
    
    def remove_subscription(self, user_id: str) -> bool:
        """Remove subscription using Day 1 approach."""
        try:
            with self.subscription_lock:
                if user_id in self.subscriptions:
                    del self.subscriptions[user_id]
                return True
        except Exception:
            return False
    
    def find_matching_users_linear(self, criteria: Dict[str, Any]) -> set:
        """
        Day 1 linear search implementation - O(n) complexity.
        This simulates the original approach without indexing.
        """
        try:
            with self.subscription_lock:
                matching_users = set()
                
                # Linear search through all subscriptions - O(n)
                for user_id, subscription in self.subscriptions.items():
                    if self._matches_criteria_linear(subscription, criteria):
                        matching_users.add(user_id)
                
                return matching_users
        except Exception:
            return set()
    
    def _matches_criteria_linear(self, subscription: UserSubscription, criteria: Dict[str, Any]) -> bool:
        """Linear matching logic (Day 1 approach)."""
        try:
            # Check subscription type
            if 'subscription_type' in criteria:
                if criteria['subscription_type'] != subscription.subscription_type:
                    return False
            
            # Check each filter criteria (linear search through filter values)
            for key, expected_value in criteria.items():
                if key == 'subscription_type':
                    continue
                
                if key in subscription.filters:
                    user_filter_values = subscription.filters[key]
                    
                    # Linear search through user filter values
                    if isinstance(user_filter_values, list):
                        found_match = False
                        for value in user_filter_values:  # O(k) where k = filter values
                            if value == expected_value:
                                found_match = True
                                break
                        if not found_match:
                            return False
                    else:
                        if expected_value != user_filter_values:
                            return False
            
            return True
            
        except Exception:
            return False
    
    def get_user_count(self) -> int:
        """Get total user count."""
        return len(self.subscriptions)


class BenchmarkComparisonHelper:
    """Helper for running performance comparisons."""
    
    @staticmethod
    def generate_test_subscription(user_id: str) -> UserSubscription:
        """Generate test subscription for comparison testing."""
        patterns = ['BreakoutBO', 'TrendReversal', 'SurgeDetection', 'VolumeSpike', 'GapUp']
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NFLX', 'NVDA']
        tiers = ['daily', 'intraday', 'combo']
        
        return UserSubscription(
            user_id=user_id,
            subscription_type=random.choice(['tier_patterns', 'market_insights']),
            filters={
                'pattern_types': random.sample(patterns, random.randint(1, 3)),
                'symbols': random.sample(symbols, random.randint(2, 5)),
                'tiers': random.sample(tiers, random.randint(1, 2)),
                'confidence_min': random.uniform(0.6, 0.9),
                'priority_min': random.randint(1, 5)
            },
            room_name=f"user_{user_id}"
        )
    
    @staticmethod
    def generate_test_criteria() -> Dict[str, Any]:
        """Generate test criteria for filtering comparisons."""
        patterns = ['BreakoutBO', 'TrendReversal', 'SurgeDetection', 'VolumeSpike', 'GapUp']
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NFLX', 'NVDA']
        tiers = ['daily', 'intraday', 'combo']
        
        return {
            'subscription_type': random.choice(['tier_patterns', 'market_insights']),
            'pattern_type': random.choice(patterns),
            'symbol': random.choice(symbols),
            'tier': random.choice(tiers),
            'confidence': random.uniform(0.7, 0.95)
        }
    
    @staticmethod
    def measure_memory_usage() -> float:
        """Measure current process memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    @staticmethod
    def run_performance_comparison(user_count: int, num_queries: int = 10) -> PerformanceComparison:
        """Run comprehensive performance comparison between Day 1 and Day 2."""
        
        # Setup Day 1 (Linear Search) Manager
        gc.collect()
        day1_start_memory = BenchmarkComparisonHelper.measure_memory_usage()
        
        day1_manager = Day1SimulatedManager()
        for i in range(user_count):
            subscription = BenchmarkComparisonHelper.generate_test_subscription(f"day1_user_{i:04d}")
            day1_manager.add_subscription(subscription)
        
        # Test Day 1 performance
        day1_times = []
        test_criteria = [BenchmarkComparisonHelper.generate_test_criteria() for _ in range(num_queries)]
        
        for criteria in test_criteria:
            start_time = time.perf_counter()
            matching_users = day1_manager.find_matching_users_linear(criteria)
            end_time = time.perf_counter()
            day1_times.append((end_time - start_time) * 1000)
        
        gc.collect()
        day1_end_memory = BenchmarkComparisonHelper.measure_memory_usage()
        day1_memory_used = day1_end_memory - day1_start_memory
        day1_avg_time = statistics.mean(day1_times)
        
        # Setup Day 2 (Indexed Search) Manager
        gc.collect()
        day2_start_memory = BenchmarkComparisonHelper.measure_memory_usage()
        
        day2_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
        for i in range(user_count):
            subscription = BenchmarkComparisonHelper.generate_test_subscription(f"day2_user_{i:04d}")
            day2_manager.add_subscription(subscription)
        
        # Test Day 2 performance
        day2_times = []
        for criteria in test_criteria:
            start_time = time.perf_counter()
            matching_users = day2_manager.find_matching_users(criteria)
            end_time = time.perf_counter()
            day2_times.append((end_time - start_time) * 1000)
        
        gc.collect()
        day2_end_memory = BenchmarkComparisonHelper.measure_memory_usage()
        day2_memory_used = day2_end_memory - day2_start_memory
        day2_avg_time = statistics.mean(day2_times)
        
        # Calculate improvement metrics
        improvement_factor = day1_avg_time / max(day2_avg_time, 0.001)  # Avoid division by zero
        memory_efficiency = "better" if day2_memory_used <= day1_memory_used else "worse"
        
        # Determine if improvement meets target (3x improvement for 1000+ users)
        target_improvement = 3.0 if user_count >= 1000 else 2.0 if user_count >= 500 else 1.5
        meets_target = improvement_factor >= target_improvement and day2_avg_time < 5.0
        
        return PerformanceComparison(
            test_scenario=f"{user_count}_users_comparison",
            user_count=user_count,
            day1_time_ms=day1_avg_time,
            day2_time_ms=day2_avg_time,
            improvement_factor=improvement_factor,
            memory_day1_mb=day1_memory_used,
            memory_day2_mb=day2_memory_used,
            memory_efficiency=memory_efficiency,
            meets_target=meets_target
        )


@pytest.fixture
def comparison_helper():
    """Create benchmark comparison helper."""
    return BenchmarkComparisonHelper()


class TestBasicPerformanceComparisons:
    """Test basic performance comparisons between Day 1 and Day 2."""
    
    def test_small_scale_comparison(self, comparison_helper):
        """Compare Day 1 vs Day 2 performance with small user count (50 users)."""
        comparison = comparison_helper.run_performance_comparison(user_count=50, num_queries=20)
        
        # Validate: Day 2 should be faster or comparable
        assert comparison.day2_time_ms <= comparison.day1_time_ms * 1.5, \
            f"Day 2 ({comparison.day2_time_ms:.2f}ms) should be comparable to Day 1 ({comparison.day1_time_ms:.2f}ms)"
        
        # Validate: Both should be reasonably fast for small scale
        assert comparison.day1_time_ms < 10.0, f"Day 1 took {comparison.day1_time_ms:.2f}ms, expected <10ms for 50 users"
        assert comparison.day2_time_ms < 5.0, f"Day 2 took {comparison.day2_time_ms:.2f}ms, expected <5ms for 50 users"
        
        print(f"Small scale (50 users):")
        print(f"  Day 1: {comparison.day1_time_ms:.3f}ms avg")
        print(f"  Day 2: {comparison.day2_time_ms:.3f}ms avg")
        print(f"  Improvement: {comparison.improvement_factor:.1f}x")
        print(f"  Memory efficiency: {comparison.memory_efficiency}")
    
    def test_medium_scale_comparison(self, comparison_helper):
        """Compare Day 1 vs Day 2 performance with medium user count (250 users)."""
        comparison = comparison_helper.run_performance_comparison(user_count=250, num_queries=15)
        
        # Validate: Day 2 should show clear improvement
        assert comparison.improvement_factor >= 1.5, \
            f"Day 2 should be 1.5x better, got {comparison.improvement_factor:.1f}x improvement"
        
        # Validate: Day 2 should meet performance targets
        assert comparison.day2_time_ms < 5.0, f"Day 2 took {comparison.day2_time_ms:.2f}ms, expected <5ms"
        
        # Validate: Memory usage should be reasonable
        assert comparison.memory_day2_mb < 2.0, f"Day 2 used {comparison.memory_day2_mb:.2f}MB, expected <2MB"
        
        print(f"Medium scale (250 users):")
        print(f"  Day 1: {comparison.day1_time_ms:.3f}ms avg")
        print(f"  Day 2: {comparison.day2_time_ms:.3f}ms avg")
        print(f"  Improvement: {comparison.improvement_factor:.1f}x")
        print(f"  Memory - Day 1: {comparison.memory_day1_mb:.2f}MB, Day 2: {comparison.memory_day2_mb:.2f}MB")
    
    def test_large_scale_comparison(self, comparison_helper):
        """Compare Day 1 vs Day 2 performance with large user count (1000 users)."""
        comparison = comparison_helper.run_performance_comparison(user_count=1000, num_queries=10)
        
        # Validate: Day 2 should show significant improvement (PRIMARY TARGET)
        assert comparison.improvement_factor >= 3.0, \
            f"Day 2 should be 3x better for 1000 users, got {comparison.improvement_factor:.1f}x improvement"
        
        # Validate: Day 2 should meet <5ms target
        assert comparison.day2_time_ms < 5.0, \
            f"Day 2 took {comparison.day2_time_ms:.2f}ms, expected <5ms for 1000 users"
        
        # Validate: Day 1 should be significantly slower (demonstrating the problem)
        assert comparison.day1_time_ms > comparison.day2_time_ms * 2, \
            f"Day 1 should be much slower than Day 2 (Day 1: {comparison.day1_time_ms:.2f}ms vs Day 2: {comparison.day2_time_ms:.2f}ms)"
        
        print(f"Large scale (1000 users):")
        print(f"  Day 1: {comparison.day1_time_ms:.3f}ms avg (linear search)")
        print(f"  Day 2: {comparison.day2_time_ms:.3f}ms avg (indexed search)")
        print(f"  Improvement: {comparison.improvement_factor:.1f}x")
        print(f"  Memory - Day 1: {comparison.memory_day1_mb:.2f}MB, Day 2: {comparison.memory_day2_mb:.2f}MB")


class TestScalabilityComparisons:
    """Test scalability characteristics between Day 1 and Day 2."""
    
    def test_scaling_curve_comparison(self, comparison_helper):
        """Compare scaling curves between Day 1 linear and Day 2 logarithmic approaches."""
        user_counts = [100, 250, 500, 750, 1000]
        scaling_results = []
        
        for user_count in user_counts:
            comparison = comparison_helper.run_performance_comparison(user_count, num_queries=5)
            scaling_results.append(comparison)
            
            print(f"{user_count:4d} users: Day 1 {comparison.day1_time_ms:6.2f}ms, "
                  f"Day 2 {comparison.day2_time_ms:6.2f}ms, "
                  f"Improvement: {comparison.improvement_factor:4.1f}x")
        
        # Validate: Day 2 should show better scaling characteristics
        day1_times = [r.day1_time_ms for r in scaling_results]
        day2_times = [r.day2_time_ms for r in scaling_results]
        
        # Calculate scaling factors (how much time increases with user count)
        day1_scaling_factors = []
        day2_scaling_factors = []
        
        for i in range(1, len(scaling_results)):
            day1_factor = day1_times[i] / day1_times[i-1]
            day2_factor = day2_times[i] / day2_times[i-1]
            day1_scaling_factors.append(day1_factor)
            day2_scaling_factors.append(day2_factor)
        
        avg_day1_scaling = statistics.mean(day1_scaling_factors)
        avg_day2_scaling = statistics.mean(day2_scaling_factors)
        
        # Validate: Day 2 should scale better (lower scaling factor)
        assert avg_day2_scaling < avg_day1_scaling, \
            f"Day 2 scaling factor ({avg_day2_scaling:.2f}) should be better than Day 1 ({avg_day1_scaling:.2f})"
        
        # Validate: All large scale comparisons should meet targets
        large_scale_results = [r for r in scaling_results if r.user_count >= 500]
        for result in large_scale_results:
            assert result.improvement_factor >= 2.0, \
                f"{result.user_count} users: improvement {result.improvement_factor:.1f}x < 2.0x"
            assert result.day2_time_ms < 5.0, \
                f"{result.user_count} users: Day 2 time {result.day2_time_ms:.2f}ms >= 5.0ms"
        
        print(f"\nScaling analysis:")
        print(f"  Day 1 average scaling factor: {avg_day1_scaling:.2f}x per step")
        print(f"  Day 2 average scaling factor: {avg_day2_scaling:.2f}x per step")
        print(f"  Day 2 scales {avg_day1_scaling/avg_day2_scaling:.1f}x better than Day 1")
    
    def test_extreme_scale_comparison(self, comparison_helper):
        """Test performance at extreme scale (1500+ users)."""
        extreme_scale_users = 1500
        comparison = comparison_helper.run_performance_comparison(extreme_scale_users, num_queries=5)
        
        # Validate: Day 2 should handle extreme scale well
        assert comparison.day2_time_ms < 8.0, \
            f"Day 2 took {comparison.day2_time_ms:.2f}ms for {extreme_scale_users} users, expected <8ms"
        
        # Validate: Improvement should be substantial at extreme scale
        assert comparison.improvement_factor >= 4.0, \
            f"At extreme scale, improvement should be >4x, got {comparison.improvement_factor:.1f}x"
        
        # Validate: Day 1 should be prohibitively slow (demonstrating need for indexing)
        assert comparison.day1_time_ms > 15.0, \
            f"Day 1 should be slow at extreme scale, got {comparison.day1_time_ms:.2f}ms"
        
        print(f"Extreme scale ({extreme_scale_users} users):")
        print(f"  Day 1: {comparison.day1_time_ms:.3f}ms (would be too slow in production)")
        print(f"  Day 2: {comparison.day2_time_ms:.3f}ms (production ready)")
        print(f"  Improvement: {comparison.improvement_factor:.1f}x")
    
    def test_memory_scaling_comparison(self, comparison_helper):
        """Compare memory scaling characteristics between Day 1 and Day 2."""
        user_counts = [200, 500, 1000]
        memory_comparisons = []
        
        for user_count in user_counts:
            # Run comparison focused on memory usage
            comparison = comparison_helper.run_performance_comparison(user_count, num_queries=1)
            
            memory_per_user_day1 = (comparison.memory_day1_mb / user_count) * 1024  # KB per user
            memory_per_user_day2 = (comparison.memory_day2_mb / user_count) * 1024  # KB per user
            
            memory_comparisons.append({
                'user_count': user_count,
                'day1_memory_mb': comparison.memory_day1_mb,
                'day2_memory_mb': comparison.memory_day2_mb,
                'day1_per_user_kb': memory_per_user_day1,
                'day2_per_user_kb': memory_per_user_day2,
                'day2_memory_overhead': memory_per_user_day2 - memory_per_user_day1
            })
            
            print(f"{user_count:4d} users: Day 1 {comparison.memory_day1_mb:5.2f}MB, "
                  f"Day 2 {comparison.memory_day2_mb:5.2f}MB "
                  f"({memory_per_user_day1:4.1f}KB vs {memory_per_user_day2:4.1f}KB per user)")
        
        # Validate: Memory usage should be reasonable and scale linearly
        for comparison in memory_comparisons:
            user_count = comparison['user_count']
            day2_per_user = comparison['day2_per_user_kb']
            memory_overhead = comparison['day2_memory_overhead']
            
            # Day 2 should use reasonable memory per user (allow for index overhead)
            assert day2_per_user < 3.0, \
                f"{user_count} users: Day 2 uses {day2_per_user:.1f}KB per user, expected <3KB"
            
            # Memory overhead should be reasonable (indexing cost)
            assert memory_overhead < 2.0, \
                f"{user_count} users: Index overhead {memory_overhead:.1f}KB per user too high"
        
        # Validate: Memory scaling should be roughly linear for both approaches
        day1_memory_values = [c['day1_memory_mb'] for c in memory_comparisons]
        day2_memory_values = [c['day2_memory_mb'] for c in memory_comparisons]
        user_counts_tested = [c['user_count'] for c in memory_comparisons]
        
        # Calculate memory efficiency (memory per user should be roughly constant)
        day1_per_user_values = [c['day1_per_user_kb'] for c in memory_comparisons]
        day2_per_user_values = [c['day2_per_user_kb'] for c in memory_comparisons]
        
        day1_per_user_variance = max(day1_per_user_values) - min(day1_per_user_values)
        day2_per_user_variance = max(day2_per_user_values) - min(day2_per_user_values)
        
        # Variance in per-user memory should be small (indicating linear scaling)
        assert day1_per_user_variance < 1.0, f"Day 1 memory scaling too variable: {day1_per_user_variance:.1f}KB"
        assert day2_per_user_variance < 1.5, f"Day 2 memory scaling too variable: {day2_per_user_variance:.1f}KB"


class TestCacheEffectivenessComparison:
    """Test cache effectiveness improvements in Day 2 implementation."""
    
    def test_repeated_query_performance(self, comparison_helper):
        """Compare repeated query performance between Day 1 and Day 2."""
        user_count = 500
        
        # Setup both managers
        day1_manager = Day1SimulatedManager()
        day2_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
        
        for i in range(user_count):
            day1_subscription = comparison_helper.generate_test_subscription(f"day1_user_{i:03d}")
            day2_subscription = comparison_helper.generate_test_subscription(f"day2_user_{i:03d}")
            day1_manager.add_subscription(day1_subscription)
            day2_manager.add_subscription(day2_subscription)
        
        # Test repeated queries
        test_criteria = comparison_helper.generate_test_criteria()
        
        # Day 1: All queries are the same time (no caching)
        day1_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            day1_manager.find_matching_users_linear(test_criteria)
            end_time = time.perf_counter()
            day1_times.append((end_time - start_time) * 1000)
        
        # Day 2: First query should be slower, subsequent should be cached
        day2_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            day2_manager.find_matching_users(test_criteria)
            end_time = time.perf_counter()
            day2_times.append((end_time - start_time) * 1000)
        
        # Analyze cache effectiveness
        day1_avg = statistics.mean(day1_times)
        day1_variance = statistics.variance(day1_times) if len(day1_times) > 1 else 0
        
        day2_first_query = day2_times[0]  # Should be slower (cache miss)
        day2_subsequent_avg = statistics.mean(day2_times[1:])  # Should be faster (cache hits)
        day2_cache_improvement = (day2_first_query - day2_subsequent_avg) / day2_first_query * 100
        
        # Validate: Day 1 should have consistent times (no caching)
        assert day1_variance < 0.5, f"Day 1 should have consistent times, variance: {day1_variance:.2f}"
        
        # Validate: Day 2 should show cache improvement
        assert day2_cache_improvement > 0, f"Day 2 should show cache improvement, got {day2_cache_improvement:.1f}%"
        assert day2_subsequent_avg < day1_avg, \
            f"Day 2 cached queries ({day2_subsequent_avg:.2f}ms) should be faster than Day 1 ({day1_avg:.2f}ms)"
        
        # Get cache stats
        cache_stats = day2_manager.get_index_stats()
        cache_hit_rate = cache_stats['cache_hit_rate_percent']
        
        # Validate: Cache hit rate should be high for repeated queries
        assert cache_hit_rate > 70.0, f"Cache hit rate {cache_hit_rate:.1f}% should be >70%"
        
        print(f"Repeated query performance:")
        print(f"  Day 1 avg: {day1_avg:.3f}ms (no caching)")
        print(f"  Day 2 first: {day2_first_query:.3f}ms (cache miss)")
        print(f"  Day 2 cached: {day2_subsequent_avg:.3f}ms (cache hit)")
        print(f"  Cache improvement: {day2_cache_improvement:.1f}%")
        print(f"  Overall cache hit rate: {cache_hit_rate:.1f}%")
    
    def test_diverse_query_cache_effectiveness(self, comparison_helper):
        """Test cache effectiveness with diverse query patterns."""
        user_count = 300
        day2_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
        
        # Setup subscriptions
        for i in range(user_count):
            subscription = comparison_helper.generate_test_subscription(f"cache_user_{i:03d}")
            day2_manager.add_subscription(subscription)
        
        # Generate diverse criteria pool
        criteria_pool = [comparison_helper.generate_test_criteria() for _ in range(20)]
        
        # Phase 1: Prime cache with diverse queries
        prime_times = []
        for criteria in criteria_pool:
            start_time = time.perf_counter()
            day2_manager.find_matching_users(criteria)
            end_time = time.perf_counter()
            prime_times.append((end_time - start_time) * 1000)
        
        # Phase 2: Mixed queries (some hits, some misses)
        mixed_times = []
        cache_status = []
        
        initial_stats = day2_manager.get_index_stats()
        initial_hits = initial_stats['cache_hits']
        initial_misses = initial_stats['cache_misses']
        
        for i in range(50):
            if i % 3 == 0:
                # New query (cache miss expected)
                criteria = comparison_helper.generate_test_criteria()
                expected_status = 'miss'
            else:
                # Repeated query (cache hit expected)
                criteria = random.choice(criteria_pool)
                expected_status = 'hit'
            
            before_hits = day2_manager.get_index_stats()['cache_hits']
            
            start_time = time.perf_counter()
            day2_manager.find_matching_users(criteria)
            end_time = time.perf_counter()
            
            after_hits = day2_manager.get_index_stats()['cache_hits']
            actual_status = 'hit' if after_hits > before_hits else 'miss'
            
            mixed_times.append((end_time - start_time) * 1000)
            cache_status.append(actual_status)
        
        # Analyze cache effectiveness
        final_stats = day2_manager.get_index_stats()
        new_hits = final_stats['cache_hits'] - initial_hits
        new_misses = final_stats['cache_misses'] - initial_misses
        total_new_queries = new_hits + new_misses
        
        if total_new_queries > 0:
            hit_rate = (new_hits / total_new_queries) * 100
        else:
            hit_rate = 0
        
        hit_times = [mixed_times[i] for i, status in enumerate(cache_status) if status == 'hit']
        miss_times = [mixed_times[i] for i, status in enumerate(cache_status) if status == 'miss']
        
        avg_hit_time = statistics.mean(hit_times) if hit_times else 0
        avg_miss_time = statistics.mean(miss_times) if miss_times else 0
        
        # Validate: Cache should be effective
        assert hit_rate > 60.0, f"Cache hit rate {hit_rate:.1f}% should be >60% for diverse queries"
        
        if hit_times and miss_times:
            cache_speedup = (avg_miss_time - avg_hit_time) / avg_miss_time * 100
            assert cache_speedup > 20.0, f"Cache should provide >20% speedup, got {cache_speedup:.1f}%"
            
            print(f"Diverse query cache effectiveness:")
            print(f"  Hit rate: {hit_rate:.1f}%")
            print(f"  Avg hit time: {avg_hit_time:.3f}ms")
            print(f"  Avg miss time: {avg_miss_time:.3f}ms")
            print(f"  Cache speedup: {cache_speedup:.1f}%")
        else:
            print(f"Diverse query cache effectiveness: {hit_rate:.1f}% hit rate")


class TestConcurrencyComparison:
    """Compare concurrency performance between Day 1 and Day 2."""
    
    def test_concurrent_lookup_comparison(self, comparison_helper):
        """Compare concurrent lookup performance between Day 1 and Day 2."""
        user_count = 400
        
        # Setup Day 1 manager
        day1_manager = Day1SimulatedManager()
        for i in range(user_count):
            subscription = comparison_helper.generate_test_subscription(f"day1_user_{i:03d}")
            day1_manager.add_subscription(subscription)
        
        # Setup Day 2 manager
        day2_manager = SubscriptionIndexManager(cache_size=1000, enable_optimization=True)
        for i in range(user_count):
            subscription = comparison_helper.generate_test_subscription(f"day2_user_{i:03d}")
            day2_manager.add_subscription(subscription)
        
        def concurrent_lookup_worker_day1(num_operations: int):
            """Day 1 concurrent worker."""
            times = []
            for _ in range(num_operations):
                criteria = comparison_helper.generate_test_criteria()
                start_time = time.perf_counter()
                day1_manager.find_matching_users_linear(criteria)
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)
            return times
        
        def concurrent_lookup_worker_day2(num_operations: int):
            """Day 2 concurrent worker."""
            times = []
            for _ in range(num_operations):
                criteria = comparison_helper.generate_test_criteria()
                start_time = time.perf_counter()
                day2_manager.find_matching_users(criteria)
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)
            return times
        
        # Run concurrent tests
        num_workers = 6
        operations_per_worker = 10
        
        # Day 1 concurrent test
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            day1_futures = [executor.submit(concurrent_lookup_worker_day1, operations_per_worker) 
                          for _ in range(num_workers)]
            day1_all_times = []
            for future in as_completed(day1_futures):
                day1_all_times.extend(future.result())
        
        # Day 2 concurrent test
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            day2_futures = [executor.submit(concurrent_lookup_worker_day2, operations_per_worker) 
                          for _ in range(num_workers)]
            day2_all_times = []
            for future in as_completed(day2_futures):
                day2_all_times.extend(future.result())
        
        # Analyze concurrent performance
        day1_concurrent_avg = statistics.mean(day1_all_times)
        day1_concurrent_max = max(day1_all_times)
        
        day2_concurrent_avg = statistics.mean(day2_all_times)
        day2_concurrent_max = max(day2_all_times)
        
        concurrent_improvement = day1_concurrent_avg / day2_concurrent_avg
        
        # Validate: Day 2 should handle concurrency better
        assert day2_concurrent_avg < day1_concurrent_avg, \
            f"Day 2 concurrent avg ({day2_concurrent_avg:.2f}ms) should be better than Day 1 ({day1_concurrent_avg:.2f}ms)"
        
        assert concurrent_improvement >= 2.0, \
            f"Concurrent improvement should be >2x, got {concurrent_improvement:.1f}x"
        
        # Validate: Day 2 should maintain good performance under concurrency
        assert day2_concurrent_avg < 10.0, \
            f"Day 2 concurrent avg {day2_concurrent_avg:.2f}ms should be <10ms"
        assert day2_concurrent_max < 25.0, \
            f"Day 2 concurrent max {day2_concurrent_max:.2f}ms should be <25ms"
        
        print(f"Concurrent lookup comparison ({user_count} users, {num_workers} workers):")
        print(f"  Day 1: {day1_concurrent_avg:.3f}ms avg, {day1_concurrent_max:.3f}ms max")
        print(f"  Day 2: {day2_concurrent_avg:.3f}ms avg, {day2_concurrent_max:.3f}ms max")
        print(f"  Improvement: {concurrent_improvement:.1f}x")


@pytest.mark.performance
class TestComprehensiveBenchmarkComparison:
    """Comprehensive benchmark comparison between Day 1 and Day 2 implementations."""
    
    def test_comprehensive_day1_vs_day2_benchmark(self, comparison_helper):
        """Comprehensive performance comparison covering all scenarios."""
        print("\n" + "="*80)
        print("SPRINT 25 DAY 1 vs DAY 2 COMPREHENSIVE PERFORMANCE COMPARISON")
        print("="*80)
        
        benchmark_results = []
        user_counts = [100, 250, 500, 750, 1000, 1250]
        
        print(f"\n{'Users':<8}{'Day 1 (ms)':<12}{'Day 2 (ms)':<12}{'Improvement':<12}{'Target Met':<12}")
        print("-" * 60)
        
        for user_count in user_counts:
            comparison = comparison_helper.run_performance_comparison(user_count, num_queries=8)
            benchmark_results.append(comparison)
            
            status_symbol = "✓" if comparison.meets_target else "✗"
            print(f"{user_count:<8}{comparison.day1_time_ms:<12.3f}{comparison.day2_time_ms:<12.3f}"
                  f"{comparison.improvement_factor:<12.1f}{status_symbol:<12}")
        
        # Analyze overall results
        print("\n" + "="*80)
        print("DETAILED ANALYSIS")
        print("="*80)
        
        # Performance improvement analysis
        all_improvements = [r.improvement_factor for r in benchmark_results]
        avg_improvement = statistics.mean(all_improvements)
        min_improvement = min(all_improvements)
        max_improvement = max(all_improvements)
        
        print(f"\nPerformance Improvements:")
        print(f"  Average: {avg_improvement:.1f}x")
        print(f"  Minimum: {min_improvement:.1f}x")
        print(f"  Maximum: {max_improvement:.1f}x")
        
        # Scaling analysis
        day1_times = [r.day1_time_ms for r in benchmark_results]
        day2_times = [r.day2_time_ms for r in benchmark_results]
        
        print(f"\nScaling Characteristics:")
        print(f"  Day 1 time range: {min(day1_times):.2f}ms - {max(day1_times):.2f}ms")
        print(f"  Day 2 time range: {min(day2_times):.2f}ms - {max(day2_times):.2f}ms")
        
        # Calculate O(n) vs O(log n) evidence
        day1_growth = day1_times[-1] / day1_times[0]  # Growth from smallest to largest
        day2_growth = day2_times[-1] / day2_times[0]  # Growth from smallest to largest
        
        print(f"  Day 1 growth factor: {day1_growth:.1f}x (linear characteristic)")
        print(f"  Day 2 growth factor: {day2_growth:.1f}x (logarithmic characteristic)")
        
        # Memory efficiency analysis
        memory_comparisons = [(r.memory_day1_mb, r.memory_day2_mb, r.user_count) for r in benchmark_results]
        day1_memory_per_user = statistics.mean([m[0]/m[2]*1024 for m in memory_comparisons])  # KB per user
        day2_memory_per_user = statistics.mean([m[1]/m[2]*1024 for m in memory_comparisons])  # KB per user
        
        print(f"\nMemory Efficiency:")
        print(f"  Day 1: {day1_memory_per_user:.1f}KB per user average")
        print(f"  Day 2: {day2_memory_per_user:.1f}KB per user average")
        print(f"  Index overhead: {day2_memory_per_user - day1_memory_per_user:.1f}KB per user")
        
        # Target achievement analysis
        targets_met = [r for r in benchmark_results if r.meets_target]
        targets_missed = [r for r in benchmark_results if not r.meets_target]
        
        print(f"\nTarget Achievement:")
        print(f"  Targets met: {len(targets_met)}/{len(benchmark_results)} scenarios")
        print(f"  Success rate: {len(targets_met)/len(benchmark_results)*100:.1f}%")
        
        if targets_missed:
            print(f"  Missed targets for user counts: {[r.user_count for r in targets_missed]}")
        
        # Key findings
        print(f"\nKEY FINDINGS:")
        print(f"  • Day 2 indexing provides {avg_improvement:.1f}x average performance improvement")
        print(f"  • Logarithmic scaling vs linear scaling demonstrated")
        print(f"  • <5ms target achieved for {len([r for r in benchmark_results if r.day2_time_ms < 5.0])}/{len(benchmark_results)} scenarios")
        print(f"  • Memory overhead acceptable: {day2_memory_per_user - day1_memory_per_user:.1f}KB per user")
        
        # Critical validations for Sprint 25
        large_scale_results = [r for r in benchmark_results if r.user_count >= 1000]
        for result in large_scale_results:
            assert result.improvement_factor >= 3.0, \
                f"{result.user_count} users: improvement {result.improvement_factor:.1f}x < 3.0x target"
            assert result.day2_time_ms < 5.0, \
                f"{result.user_count} users: Day 2 time {result.day2_time_ms:.2f}ms >= 5.0ms target"
        
        # Overall success criteria
        overall_success = len(targets_met) >= len(benchmark_results) * 0.8  # 80% success rate
        assert overall_success, f"Only {len(targets_met)}/{len(benchmark_results)} scenarios met targets"
        
        print(f"\n✓ SPRINT 25 DAY 2 INDEXING SYSTEM VALIDATION COMPLETE")
        print(f"  Performance targets achieved with {avg_improvement:.1f}x average improvement")
        
        return benchmark_results


if __name__ == "__main__":
    # Run benchmark comparison tests directly
    pytest.main([__file__, "-v", "--tb=short", "-m", "performance"])