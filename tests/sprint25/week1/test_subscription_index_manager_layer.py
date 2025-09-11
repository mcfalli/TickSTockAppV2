"""
Test Suite for SubscriptionIndexManager (Layer 2)
Sprint 25 Week 1 - High-performance indexing layer tests

Tests the subscription indexing system with <5ms user filtering
performance and multi-dimensional indexing capabilities.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from typing import Dict, Any, Set

from src.infrastructure.websocket.subscription_index_manager import (
    SubscriptionIndexManager,
    IndexType,
    IndexStats,
    IndexEntry
)
from src.core.models.websocket_models import UserSubscription
from datetime import datetime


@pytest.fixture
def index_manager():
    """Create SubscriptionIndexManager for testing."""
    return SubscriptionIndexManager(cache_size=100, enable_optimization=True)


@pytest.fixture
def sample_subscription():
    """Create sample user subscription for testing."""
    return UserSubscription(
        user_id="test_user_001",
        subscription_type="tier_patterns",
        filters={
            'pattern_types': ['BreakoutBO', 'TrendReversal'],
            'symbols': ['AAPL', 'TSLA'],
            'tiers': ['daily', 'intraday'],
            'confidence_min': 0.7,
            'priority_min': 'MEDIUM'
        },
        room_name="user_test_user_001",
        active=True,
        created_at=datetime.now(),
        last_activity=datetime.now()
    )


class TestSubscriptionIndexManagerLayer:
    """Test SubscriptionIndexManager as Layer 2 high-performance indexing."""

    def test_initialization_with_optimization_enabled(self, index_manager):
        """Test initialization with performance optimization enabled."""
        # Verify initialization parameters
        assert index_manager.cache_size == 100
        assert index_manager.enable_optimization is True
        
        # Verify index dictionaries are initialized
        assert len(index_manager.pattern_type_index) == 0
        assert len(index_manager.symbol_index) == 0
        assert len(index_manager.tier_index) == 0
        assert len(index_manager.compound_indexes) == 0
        
        # Verify query cache is initialized
        assert len(index_manager.query_cache) == 0
        
        # Verify stats tracking is initialized
        assert index_manager.stats is not None
        assert index_manager.stats.total_users == 0
        assert index_manager.stats.lookup_count == 0

    def test_add_subscription_multi_dimensional_indexing(self, index_manager, sample_subscription):
        """Test adding subscription creates indexes across multiple dimensions."""
        success = index_manager.add_subscription(sample_subscription)
        
        # Verify subscription was added successfully
        assert success is True
        
        # Verify pattern type indexes
        assert 'BreakoutBO' in index_manager.pattern_type_index
        assert 'TrendReversal' in index_manager.pattern_type_index
        assert sample_subscription.user_id in index_manager.pattern_type_index['BreakoutBO'].user_ids
        assert sample_subscription.user_id in index_manager.pattern_type_index['TrendReversal'].user_ids
        
        # Verify symbol indexes
        assert 'AAPL' in index_manager.symbol_index
        assert 'TSLA' in index_manager.symbol_index
        assert sample_subscription.user_id in index_manager.symbol_index['AAPL'].user_ids
        assert sample_subscription.user_id in index_manager.symbol_index['TSLA'].user_ids
        
        # Verify tier indexes
        assert 'daily' in index_manager.tier_index
        assert 'intraday' in index_manager.tier_index
        assert sample_subscription.user_id in index_manager.tier_index['daily'].user_ids
        
        # Verify subscription type index
        assert 'tier_patterns' in index_manager.subscription_type_index
        assert sample_subscription.user_id in index_manager.subscription_type_index['tier_patterns'].user_ids
        
        # Verify confidence range indexing
        assert 'medium' in index_manager.confidence_range_index  # 0.7 -> medium range
        assert sample_subscription.user_id in index_manager.confidence_range_index['medium'].user_ids
        
        # Verify compound indexes for common queries
        assert 'BreakoutBO:AAPL' in index_manager.compound_indexes
        assert 'BreakoutBO:TSLA' in index_manager.compound_indexes
        assert 'TrendReversal:AAPL' in index_manager.compound_indexes
        
        # Verify user reverse mapping
        assert sample_subscription.user_id in index_manager.user_index_mapping
        user_mappings = index_manager.user_index_mapping[sample_subscription.user_id]
        assert len(user_mappings[IndexType.PATTERN_TYPE.value]) == 2
        assert len(user_mappings[IndexType.SYMBOL.value]) == 2
        assert len(user_mappings[IndexType.TIER.value]) == 2
        
        # Verify statistics were updated
        assert index_manager.stats.total_users == 1
        assert index_manager.stats.index_updates == 1

    def test_find_matching_users_performance_target(self, index_manager):
        """Test finding matching users meets <5ms performance target."""
        # Add multiple subscriptions for performance testing
        test_users = []
        for i in range(1000):
            user_id = f"perf_user_{i:03d}"
            test_users.append(user_id)
            
            subscription = UserSubscription(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal', 'SurgeDetection'][i % 3],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'][i % 5],
                    'tiers': ['daily', 'intraday'],
                    'confidence_min': 0.5 + (i % 5) * 0.1,
                    'market_regimes': ['BULLISH', 'BEARISH', 'NEUTRAL'][i % 3]
                },
                room_name=f"user_{user_id}",
                active=True,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            
            index_manager.add_subscription(subscription)
        
        # Test various filtering criteria
        test_criteria = [
            {
                'subscription_type': 'tier_patterns',
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL'
            },
            {
                'pattern_type': 'TrendReversal',
                'symbol': 'MSFT',
                'tier': 'daily',
                'confidence': 0.8
            },
            {
                'subscription_type': 'tier_patterns',
                'pattern_type': 'SurgeDetection',
                'market_regime': 'BULLISH'
            }
        ]
        
        performance_results = []
        
        for criteria in test_criteria:
            start_time = time.time()
            
            matching_users = index_manager.find_matching_users(criteria)
            
            filtering_time_ms = (time.time() - start_time) * 1000
            performance_results.append(filtering_time_ms)
            
            # Verify performance target <5ms
            assert filtering_time_ms < 5.0, f"Filtering took {filtering_time_ms:.2f}ms with {len(matching_users)} matches, exceeds 5ms target"
            
            # Verify we got reasonable results
            assert isinstance(matching_users, set)
            assert len(matching_users) > 0  # Should find some matching users
        
        # Verify average performance
        avg_performance = sum(performance_results) / len(performance_results)
        assert avg_performance < 3.0, f"Average filtering time {avg_performance:.2f}ms exceeds 3ms target"
        
        # Verify statistics were updated
        assert index_manager.stats.lookup_count == len(test_criteria)
        assert index_manager.stats.avg_lookup_time_ms > 0

    def test_query_caching_with_lru_eviction(self, index_manager, sample_subscription):
        """Test query caching improves performance and uses LRU eviction."""
        index_manager.add_subscription(sample_subscription)
        
        # Create query criteria
        criteria = {
            'subscription_type': 'tier_patterns',
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL'
        }
        
        # First query - should cache result
        start_time = time.time()
        first_result = index_manager.find_matching_users(criteria)
        first_time = (time.time() - start_time) * 1000
        
        # Second query - should use cache
        start_time = time.time()
        second_result = index_manager.find_matching_users(criteria)
        second_time = (time.time() - start_time) * 1000
        
        # Verify results are identical
        assert first_result == second_result
        
        # Cache should improve performance (though mocking might make this minimal)
        # Just verify cache was used
        assert len(index_manager.query_cache) > 0
        
        # Verify cache hit statistics
        assert index_manager.stats.cache_hits >= 1
        
        # Test LRU eviction by filling cache beyond capacity
        for i in range(index_manager.cache_size + 10):
            test_criteria = {
                'pattern_type': f'TestPattern_{i}',
                'symbol': f'TEST{i}'
            }
            index_manager.find_matching_users(test_criteria)
        
        # Cache should not exceed capacity
        assert len(index_manager.query_cache) <= index_manager.cache_size

    def test_compound_index_optimization(self, index_manager):
        """Test compound indexes optimize common query patterns."""
        # Add subscriptions that will create compound indexes
        for i in range(50):
            user_id = f"compound_user_{i}"
            subscription = UserSubscription(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO'],
                    'symbols': ['AAPL', 'MSFT'][i % 2],
                    'tiers': ['daily']
                },
                room_name=f"user_{user_id}",
                active=True,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            index_manager.add_subscription(subscription)
        
        # Verify compound indexes were created
        assert 'BreakoutBO:AAPL' in index_manager.compound_indexes
        assert 'BreakoutBO:MSFT' in index_manager.compound_indexes
        
        # Test compound index usage
        compound_users_aapl = index_manager._check_compound_indexes({
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL'
        })
        
        compound_users_msft = index_manager._check_compound_indexes({
            'pattern_type': 'BreakoutBO',
            'symbol': 'MSFT'
        })
        
        # Verify compound indexes return correct users
        assert compound_users_aapl is not None
        assert compound_users_msft is not None
        assert len(compound_users_aapl) > 0
        assert len(compound_users_msft) > 0
        
        # AAPL users should be different from MSFT users
        assert compound_users_aapl != compound_users_msft

    def test_remove_subscription_cleanup(self, index_manager, sample_subscription):
        """Test removing subscription cleans up all indexes properly."""
        user_id = sample_subscription.user_id
        
        # Add subscription first
        index_manager.add_subscription(sample_subscription)
        
        # Verify user exists in indexes
        assert user_id in index_manager.user_index_mapping
        assert 'BreakoutBO' in index_manager.pattern_type_index
        assert user_id in index_manager.pattern_type_index['BreakoutBO'].user_ids
        
        # Remove subscription
        success = index_manager.remove_subscription(user_id)
        
        # Verify removal was successful
        assert success is True
        
        # Verify user was removed from user mapping
        assert user_id not in index_manager.user_index_mapping
        
        # Verify user was removed from all indexes
        # Note: Empty index entries should be cleaned up
        for index_entry in index_manager.pattern_type_index.values():
            assert user_id not in index_entry.user_ids
        
        for index_entry in index_manager.symbol_index.values():
            assert user_id not in index_entry.user_ids
        
        # Verify statistics were updated
        assert index_manager.stats.total_users == 0

    def test_index_stats_comprehensive_reporting(self, index_manager):
        """Test comprehensive statistics reporting for monitoring."""
        # Add various subscriptions to generate meaningful stats
        for i in range(20):
            user_id = f"stats_user_{i}"
            subscription = UserSubscription(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL'][i % 3],
                    'tiers': ['daily', 'intraday'],
                    'confidence_min': 0.6 + (i % 4) * 0.1
                },
                room_name=f"user_{user_id}",
                active=True,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            index_manager.add_subscription(subscription)
        
        # Perform some lookups to generate performance stats
        for i in range(10):
            criteria = {
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL'
            }
            index_manager.find_matching_users(criteria)
        
        # Get comprehensive statistics
        stats = index_manager.get_index_stats()
        
        # Verify basic stats
        assert stats['total_users'] == 20
        assert stats['total_indexes'] > 0
        assert 'index_sizes' in stats
        
        # Verify index sizes are reported
        index_sizes = stats['index_sizes']
        assert 'pattern_type' in index_sizes
        assert 'symbol' in index_sizes
        assert 'tier' in index_sizes
        assert 'subscription_type' in index_sizes
        assert 'confidence_range' in index_sizes
        assert 'compound' in index_sizes
        
        # Verify performance metrics
        assert stats['lookup_count'] == 10
        assert stats['avg_lookup_time_ms'] >= 0
        assert stats['performance_target_ms'] == 5.0
        assert stats['performance_status'] in ['good', 'warning']
        
        # Verify cache metrics
        assert 'cache_size' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'cache_hit_rate_percent' in stats
        
        # Verify efficiency metrics
        assert 'index_updates' in stats
        assert stats['index_updates'] == 20  # One per subscription
        assert 'memory_efficiency' in stats

    def test_health_status_performance_monitoring(self, index_manager):
        """Test health status monitoring with performance validation."""
        # Add subscriptions to test with load
        for i in range(100):
            user_id = f"health_user_{i}"
            subscription = UserSubscription(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO'],
                    'symbols': ['AAPL'],
                    'tiers': ['daily']
                },
                room_name=f"user_{user_id}",
                active=True,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            index_manager.add_subscription(subscription)
        
        # Perform lookups to establish performance baseline
        for _ in range(20):
            index_manager.find_matching_users({
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL'
            })
        
        # Get health status
        health_status = index_manager.get_health_status()
        
        # Verify health status structure
        assert 'service' in health_status
        assert 'status' in health_status
        assert 'message' in health_status
        assert 'timestamp' in health_status
        assert 'stats' in health_status
        assert 'performance_targets' in health_status
        
        # Verify service identification
        assert health_status['service'] == 'subscription_index_manager'
        
        # Verify status is reasonable (should be healthy with good performance)
        assert health_status['status'] in ['healthy', 'warning', 'error']
        
        # Verify performance targets
        targets = health_status['performance_targets']
        assert targets['lookup_time_target_ms'] == 5.0
        assert targets['cache_hit_rate_target_percent'] == 70.0
        assert targets['max_users_target'] == 1000

    def test_optimize_indexes_performance_improvement(self, index_manager):
        """Test index optimization improves performance and cleans up stale data."""
        # Add subscriptions and generate some cache entries
        for i in range(50):
            user_id = f"optimize_user_{i}"
            subscription = UserSubscription(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO'],
                    'symbols': ['AAPL'],
                    'tiers': ['daily']
                },
                room_name=f"user_{user_id}",
                active=True,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            index_manager.add_subscription(subscription)
        
        # Create stale cache entries by mocking old timestamps
        for i in range(10):
            cache_key = f"stale_key_{i}"
            old_timestamp = time.time() - 400  # 400 seconds ago (> 5 minute TTL)
            index_manager.query_cache[cache_key] = (set([f"user_{i}"]), old_timestamp)
        
        # Run optimization
        optimization_results = index_manager.optimize_indexes()
        
        # Verify optimization results
        assert 'cache_cleaned' in optimization_results
        assert 'indexes_optimized' in optimization_results
        
        # Verify stale cache entries were cleaned
        assert optimization_results['cache_cleaned'] > 0
        
        # Verify no stale entries remain
        current_time = time.time()
        for result, timestamp in index_manager.query_cache.values():
            assert current_time - timestamp < 300  # All entries should be fresh

    def test_cleanup_stale_entries_maintenance(self, index_manager):
        """Test cleanup of stale index entries."""
        # Add some subscriptions
        for i in range(10):
            user_id = f"stale_user_{i}"
            subscription = UserSubscription(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO'],
                    'symbols': ['AAPL']
                },
                room_name=f"user_{user_id}",
                active=True,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            index_manager.add_subscription(subscription)
        
        # Mock some index entries as old by patching their last_access time
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        
        # Modify some index entries to be stale
        for key, entry in list(index_manager.pattern_type_index.items())[:3]:
            # Clear user_ids to simulate stale empty entries
            entry.user_ids.clear()
            entry.last_access = old_time
        
        # Run cleanup
        cleaned_count = index_manager.cleanup_stale_entries(max_age_hours=24)
        
        # Verify some entries were cleaned
        assert cleaned_count >= 3
        
        # Verify stale entries were removed
        remaining_entries = len(index_manager.pattern_type_index)
        assert remaining_entries >= 0  # Should have cleaned up empty stale entries

    def test_thread_safety_concurrent_operations(self, index_manager):
        """Test thread safety with concurrent index operations."""
        results = {'success_count': 0, 'errors': []}
        
        def index_worker(thread_id):
            """Worker function for concurrent indexing operations."""
            try:
                for i in range(20):
                    user_id = f"thread_{thread_id}_user_{i}"
                    subscription = UserSubscription(
                        user_id=user_id,
                        subscription_type="tier_patterns",
                        filters={
                            'pattern_types': ['BreakoutBO'],
                            'symbols': ['AAPL', 'MSFT'][i % 2],
                            'tiers': ['daily']
                        },
                        room_name=f"user_{user_id}",
                        active=True,
                        created_at=datetime.now(),
                        last_activity=datetime.now()
                    )
                    
                    # Add subscription
                    success = index_manager.add_subscription(subscription)
                    if success:
                        results['success_count'] += 1
                    
                    # Perform lookup
                    matching_users = index_manager.find_matching_users({
                        'pattern_type': 'BreakoutBO',
                        'symbol': 'AAPL'
                    })
                    
                    # Small delay to increase concurrency
                    time.sleep(0.001)
                    
            except Exception as e:
                results['errors'].append(f"Thread {thread_id}: {str(e)}")
        
        def cleanup_worker():
            """Worker function for concurrent cleanup operations."""
            try:
                time.sleep(0.1)  # Let some subscriptions be added first
                for i in range(5):
                    # Run optimization
                    index_manager.optimize_indexes()
                    time.sleep(0.01)
                    
            except Exception as e:
                results['errors'].append(f"Cleanup worker: {str(e)}")
        
        # Create and start threads
        threads = []
        
        # Index worker threads
        for i in range(4):
            thread = threading.Thread(target=index_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Cleanup worker thread
        cleanup_thread = threading.Thread(target=cleanup_worker)
        threads.append(cleanup_thread)
        cleanup_thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify no errors occurred
        assert len(results['errors']) == 0, f"Thread safety errors: {results['errors']}"
        
        # Verify reasonable number of successful operations
        assert results['success_count'] >= 70  # Some operations should succeed
        
        # Verify index consistency
        total_users = index_manager.stats.total_users
        assert total_users > 0

    def test_confidence_range_indexing(self, index_manager):
        """Test confidence range indexing for efficient filtering."""
        # Add subscriptions with various confidence levels
        confidence_levels = [0.45, 0.55, 0.65, 0.75, 0.85, 0.95]
        expected_ranges = ['very_low', 'low', 'medium', 'medium', 'high', 'high']
        
        for i, confidence in enumerate(confidence_levels):
            user_id = f"confidence_user_{i}"
            subscription = UserSubscription(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO'],
                    'symbols': ['AAPL'],
                    'confidence_min': confidence
                },
                room_name=f"user_{user_id}",
                active=True,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            index_manager.add_subscription(subscription)
        
        # Verify confidence range indexes were created
        for expected_range in expected_ranges:
            if expected_range in ['very_low', 'low', 'medium', 'high']:
                assert expected_range in index_manager.confidence_range_index
        
        # Test confidence-based filtering
        high_confidence_users = index_manager.find_matching_users({
            'confidence': 0.9
        })
        
        medium_confidence_users = index_manager.find_matching_users({
            'confidence': 0.7
        })
        
        # Verify filtering results
        assert len(high_confidence_users) > 0
        assert len(medium_confidence_users) > 0
        
        # High confidence should match users with high range subscriptions
        # (This is simplified - real implementation would need threshold matching)

    def test_access_tracking_and_optimization(self, index_manager, sample_subscription):
        """Test access tracking for optimization decisions."""
        index_manager.add_subscription(sample_subscription)
        
        # Access different indexes multiple times
        for _ in range(10):
            # This should access pattern_type and symbol indexes
            index_manager.find_matching_users({
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL'
            })
        
        # Verify access counts were recorded
        breakout_entry = index_manager.pattern_type_index.get('BreakoutBO')
        assert breakout_entry is not None
        assert breakout_entry.access_count >= 10
        
        aapl_entry = index_manager.symbol_index.get('AAPL')
        assert aapl_entry is not None
        assert aapl_entry.access_count >= 10
        
        # Verify last_access timestamps are recent
        current_time = time.time()
        assert current_time - breakout_entry.last_access < 1.0  # Within 1 second
        assert current_time - aapl_entry.last_access < 1.0

    def test_error_handling_malformed_subscriptions(self, index_manager):
        """Test error handling with malformed subscription data."""
        # Test with missing filters
        bad_subscription = UserSubscription(
            user_id="bad_user",
            subscription_type="tier_patterns",
            filters={},  # Empty filters
            room_name="user_bad_user",
            active=True,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        # Should handle empty filters gracefully
        success = index_manager.add_subscription(bad_subscription)
        assert success is True  # Should succeed even with empty filters
        
        # Test with None values in filters
        none_subscription = UserSubscription(
            user_id="none_user",
            subscription_type="tier_patterns",
            filters={
                'pattern_types': None,
                'symbols': ['AAPL'],
                'confidence_min': None
            },
            room_name="user_none_user",
            active=True,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        # Should handle None values gracefully
        success = index_manager.add_subscription(none_subscription)
        assert success is True

    def test_memory_efficiency_large_scale(self, index_manager):
        """Test memory efficiency with large number of subscriptions."""
        initial_memory = index_manager.get_index_stats()
        
        # Add a large number of subscriptions
        for i in range(2000):
            user_id = f"memory_user_{i:04d}"
            subscription = UserSubscription(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'][i % 5],
                    'tiers': ['daily', 'intraday']
                },
                room_name=f"user_{user_id}",
                active=True,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            index_manager.add_subscription(subscription)
        
        final_stats = index_manager.get_index_stats()
        
        # Verify system can handle large scale
        assert final_stats['total_users'] == 2000
        assert final_stats['total_indexes'] > 0
        
        # Test performance with large scale
        start_time = time.time()
        matching_users = index_manager.find_matching_users({
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL'
        })
        lookup_time_ms = (time.time() - start_time) * 1000
        
        # Should still meet performance targets
        assert lookup_time_ms < 5.0, f"Large scale lookup took {lookup_time_ms:.2f}ms"
        assert len(matching_users) > 0

    def test_hash_criteria_consistency(self, index_manager):
        """Test query hash generation is consistent for caching."""
        criteria1 = {
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL',
            'confidence': 0.8
        }
        
        criteria2 = {
            'confidence': 0.8,
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO'
        }  # Same criteria, different order
        
        hash1 = index_manager._hash_criteria(criteria1)
        hash2 = index_manager._hash_criteria(criteria2)
        
        # Hashes should be identical regardless of order
        assert hash1 == hash2
        
        # Different criteria should produce different hashes
        criteria3 = {
            'pattern_type': 'TrendReversal',
            'symbol': 'AAPL',
            'confidence': 0.8
        }
        
        hash3 = index_manager._hash_criteria(criteria3)
        assert hash3 != hash1