"""
Test Suite for EventRouter (Layer 4)
Sprint 25 Week 1 - Intelligent routing layer tests

Tests the intelligent event routing system with content-based routing,
route caching, and <20ms routing performance targets.
"""

import threading
import time
from unittest.mock import Mock, patch

import pytest

from src.infrastructure.websocket.event_router import (
    DeliveryPriority,
    EventRouter,
    RoutingRule,
    RoutingStrategy,
    create_market_data_routing_rule,
    create_pattern_routing_rule,
    create_tier_routing_rule,
)
from src.infrastructure.websocket.scalable_broadcaster import ScalableBroadcaster


@pytest.fixture
def mock_scalable_broadcaster():
    """Mock ScalableBroadcaster for testing."""
    mock = Mock(spec=ScalableBroadcaster)
    mock.broadcast_to_users = Mock(return_value=5)
    mock.broadcast_to_room = Mock(return_value=True)
    return mock


@pytest.fixture
def event_router(mock_scalable_broadcaster):
    """Create EventRouter for testing."""
    return EventRouter(
        scalable_broadcaster=mock_scalable_broadcaster,
        cache_size=100,
        enable_caching=True
    )


@pytest.fixture
def sample_routing_rule():
    """Create sample routing rule for testing."""
    return RoutingRule(
        rule_id='test_pattern_rule',
        name='Test Pattern Routing',
        description='Routes test pattern events',
        event_type_patterns=[r'tier_pattern', r'.*pattern.*'],
        content_filters={
            'pattern_type': 'BreakoutBO',
            'confidence': {'min': 0.7}
        },
        user_criteria={},
        strategy=RoutingStrategy.CONTENT_BASED,
        destinations=['pattern_room'],
        priority=DeliveryPriority.HIGH
    )


class TestEventRouterLayer:
    """Test EventRouter as Layer 4 intelligent routing system."""

    def test_initialization_with_caching_enabled(self, event_router):
        """Test initialization with performance caching enabled."""
        # Verify configuration
        assert event_router.cache_size == 100
        assert event_router.enable_caching is True

        # Verify routing system components
        assert len(event_router.routing_rules) == 0
        assert len(event_router.rule_categories) >= 0

        # Verify route caching system
        assert len(event_router.route_cache) == 0
        assert len(event_router.cache_access_order) == 0

        # Verify thread pool executor
        assert event_router.routing_executor is not None

        # Verify statistics tracking
        assert event_router.stats is not None
        assert event_router.stats.total_events == 0

    def test_add_routing_rule_with_categorization(self, event_router, sample_routing_rule):
        """Test adding routing rule with automatic categorization."""
        success = event_router.add_routing_rule(sample_routing_rule)

        # Verify rule was added
        assert success is True
        assert sample_routing_rule.rule_id in event_router.routing_rules

        # Verify rule categorization occurred
        found_in_category = False
        for category, rule_ids in event_router.rule_categories.items():
            if sample_routing_rule.rule_id in rule_ids:
                found_in_category = True
                break

        # Rule should be categorized based on event type patterns
        assert found_in_category or len(event_router.rule_categories) == 0  # May not categorize test rules

    def test_remove_routing_rule_with_cleanup(self, event_router, sample_routing_rule):
        """Test removing routing rule cleans up categories and cache."""
        # Add rule first
        event_router.add_routing_rule(sample_routing_rule)
        assert sample_routing_rule.rule_id in event_router.routing_rules

        # Add some cache entries
        event_router.route_cache['test_key'] = (Mock(), time.time())

        # Remove rule
        success = event_router.remove_routing_rule(sample_routing_rule.rule_id)

        # Verify removal was successful
        assert success is True
        assert sample_routing_rule.rule_id not in event_router.routing_rules

        # Verify cache was cleared
        assert len(event_router.route_cache) == 0

    def test_route_event_performance_target(self, event_router, sample_routing_rule):
        """Test event routing meets <20ms performance target."""
        # Add routing rule
        event_router.add_routing_rule(sample_routing_rule)

        # Test routing performance
        event_type = 'tier_pattern'
        event_data = {
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL',
            'confidence': 0.85,
            'tier': 'daily'
        }
        user_context = {
            'interested_users': ['user1', 'user2', 'user3']
        }

        # Measure routing time
        start_time = time.time()

        routing_result = event_router.route_event(
            event_type=event_type,
            event_data=event_data,
            user_context=user_context
        )

        routing_time_ms = (time.time() - start_time) * 1000

        # Verify performance target <20ms
        assert routing_time_ms < 20.0, f"Routing took {routing_time_ms:.2f}ms, exceeds 20ms target"

        # Verify routing result
        assert routing_result is not None
        assert routing_result.event_id is not None
        assert routing_result.routing_time_ms > 0
        assert routing_result.total_users >= 0

    def test_intelligent_routing_strategies(self, event_router):
        """Test different routing strategies work correctly."""
        # Create rules with different strategies
        broadcast_rule = RoutingRule(
            rule_id='broadcast_rule',
            name='Broadcast All Rule',
            description='Broadcast to all users',
            event_type_patterns=[r'system_.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['system_room'],
            priority=DeliveryPriority.HIGH
        )

        content_rule = RoutingRule(
            rule_id='content_rule',
            name='Content Based Rule',
            description='Route based on content',
            event_type_patterns=[r'tier_pattern'],
            content_filters={'pattern_type': 'BreakoutBO'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        priority_rule = RoutingRule(
            rule_id='priority_rule',
            name='Priority First Rule',
            description='Priority-based routing',
            event_type_patterns=[r'alert_.*'],
            content_filters={'priority': 'HIGH'},
            user_criteria={},
            strategy=RoutingStrategy.PRIORITY_FIRST,
            destinations=['priority_room'],
            priority=DeliveryPriority.CRITICAL
        )

        # Add all rules
        event_router.add_routing_rule(broadcast_rule)
        event_router.add_routing_rule(content_rule)
        event_router.add_routing_rule(priority_rule)

        # Test broadcast strategy
        broadcast_result = event_router.route_event(
            event_type='system_health',
            event_data={'status': 'healthy'},
            user_context={}
        )

        assert len(broadcast_result.matched_rules) > 0
        assert 'broadcast_rule' in broadcast_result.matched_rules

        # Test content-based strategy
        content_result = event_router.route_event(
            event_type='tier_pattern',
            event_data={'pattern_type': 'BreakoutBO', 'symbol': 'AAPL'},
            user_context={}
        )

        assert len(content_result.matched_rules) > 0
        assert 'content_rule' in content_result.matched_rules

        # Test priority strategy
        priority_result = event_router.route_event(
            event_type='alert_critical',
            event_data={'priority': 'HIGH', 'message': 'Critical alert'},
            user_context={}
        )

        assert len(priority_result.matched_rules) > 0
        assert 'priority_rule' in priority_result.matched_rules

    def test_route_caching_with_lru_eviction(self, event_router, sample_routing_rule):
        """Test route caching improves performance with LRU eviction."""
        event_router.add_routing_rule(sample_routing_rule)

        event_type = 'tier_pattern'
        event_data = {
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL',
            'confidence': 0.8
        }
        user_context = {'interested_users': ['user1', 'user2']}

        # First routing - should cache result
        first_result = event_router.route_event(event_type, event_data, user_context)
        first_cache_size = len(event_router.route_cache)

        # Second routing with same criteria - should use cache
        second_result = event_router.route_event(event_type, event_data, user_context)
        second_cache_size = len(event_router.route_cache)

        # Cache should be used (same size, marked as cache hit)
        assert first_cache_size == second_cache_size
        assert second_result.cache_hit is True

        # Test LRU eviction by filling cache beyond capacity
        for i in range(event_router.cache_size + 10):
            test_data = {
                'pattern_type': f'TestPattern_{i}',
                'symbol': f'TEST{i}',
                'confidence': 0.7
            }
            event_router.route_event(event_type, test_data, {})

        # Cache should not exceed capacity
        assert len(event_router.route_cache) <= event_router.cache_size

    def test_content_based_routing_with_transformation(self, event_router):
        """Test content-based routing with event transformation."""
        def test_transformer(event_data):
            """Test content transformer."""
            transformed = event_data.copy()
            transformed['enriched'] = True
            transformed['timestamp_enriched'] = time.time()
            return transformed

        # Create rule with content transformation
        transform_rule = RoutingRule(
            rule_id='transform_rule',
            name='Transformation Rule',
            description='Rule with content transformation',
            event_type_patterns=[r'tier_pattern'],
            content_filters={'pattern_type': 'BreakoutBO'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=['enriched_room'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=test_transformer
        )

        event_router.add_routing_rule(transform_rule)

        # Route event that should trigger transformation
        result = event_router.route_event(
            event_type='tier_pattern',
            event_data={
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL',
                'confidence': 0.8
            },
            user_context={}
        )

        # Verify transformation was applied
        assert len(result.transformations_applied) > 0
        assert 'transform_rule_content_transform' in result.transformations_applied

    def test_routing_rule_matching_logic(self, event_router):
        """Test routing rule matching logic with various filters."""
        # Complex rule with multiple filter types
        complex_rule = RoutingRule(
            rule_id='complex_rule',
            name='Complex Matching Rule',
            description='Rule with complex matching criteria',
            event_type_patterns=[r'tier_pattern', r'market_.*'],
            content_filters={
                'confidence': {'min': 0.7, 'max': 0.95},
                'symbol': 'AAPL',
                'pattern_type': {'contains': 'Breakout'}
            },
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['complex_room'],
            priority=DeliveryPriority.MEDIUM
        )

        event_router.add_routing_rule(complex_rule)

        # Test matching event
        matching_result = event_router.route_event(
            event_type='tier_pattern',
            event_data={
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL',
                'confidence': 0.85
            }
        )

        assert 'complex_rule' in matching_result.matched_rules

        # Test non-matching event (wrong symbol)
        non_matching_result = event_router.route_event(
            event_type='tier_pattern',
            event_data={
                'pattern_type': 'BreakoutBO',
                'symbol': 'MSFT',  # Wrong symbol
                'confidence': 0.85
            }
        )

        assert 'complex_rule' not in non_matching_result.matched_rules

        # Test non-matching event (confidence too low)
        low_confidence_result = event_router.route_event(
            event_type='tier_pattern',
            event_data={
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL',
                'confidence': 0.5  # Too low
            }
        )

        assert 'complex_rule' not in low_confidence_result.matched_rules

    def test_routing_execution_with_broadcaster(self, event_router, mock_scalable_broadcaster):
        """Test routing execution integrates with ScalableBroadcaster."""
        # Create rule that should route to users
        user_rule = RoutingRule(
            rule_id='user_route_rule',
            name='User Routing Rule',
            description='Routes events to specific users',
            event_type_patterns=[r'user_event'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        event_router.add_routing_rule(user_rule)

        # Mock routing strategy to return specific users
        with patch.object(event_router, '_get_broadcast_destinations') as mock_destinations:
            mock_destinations.return_value = {
                'user_room_1': {'user1', 'user2'},
                'user_room_2': {'user3'}
            }

            # Route event
            result = event_router.route_event(
                event_type='user_event',
                event_data={'message': 'test'},
                user_context={}
            )

            # Verify routing occurred
            assert result.total_users == 3

            # Verify ScalableBroadcaster was called
            assert mock_scalable_broadcaster.broadcast_to_users.call_count > 0

    def test_routing_stats_comprehensive_reporting(self, event_router, sample_routing_rule):
        """Test comprehensive routing statistics reporting."""
        # Add multiple rules
        event_router.add_routing_rule(sample_routing_rule)

        additional_rule = RoutingRule(
            rule_id='additional_rule',
            name='Additional Rule',
            description='Another routing rule',
            event_type_patterns=[r'market_.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['market_room'],
            priority=DeliveryPriority.LOW
        )
        event_router.add_routing_rule(additional_rule)

        # Route various events to generate statistics
        test_events = [
            ('tier_pattern', {'pattern_type': 'BreakoutBO', 'confidence': 0.8}),
            ('market_update', {'symbol': 'AAPL', 'price': 150.0}),
            ('tier_pattern', {'pattern_type': 'TrendReversal', 'confidence': 0.6})
        ]

        for event_type, event_data in test_events:
            event_router.route_event(event_type, event_data, {})

        # Get comprehensive statistics
        stats = event_router.get_routing_stats()

        # Verify basic event metrics
        assert stats['total_events'] == 3
        assert stats['events_routed'] >= 0
        assert stats['events_per_second'] >= 0

        # Verify performance metrics
        assert 'avg_routing_time_ms' in stats
        assert 'max_routing_time_ms' in stats
        assert 'cache_hit_rate_percent' in stats
        assert stats['avg_routing_time_ms'] >= 0

        # Verify rule effectiveness metrics
        assert stats['total_rules'] == 2
        assert 'avg_rules_matched_per_event' in stats
        assert 'most_used_rule' in stats
        assert 'rule_usage' in stats

        # Verify cache metrics
        assert 'cache_size' in stats
        assert 'cache_capacity' in stats
        assert 'cache_utilization_percent' in stats

        # Verify error tracking
        assert 'routing_errors' in stats
        assert 'transformation_errors' in stats

    def test_health_status_monitoring(self, event_router, sample_routing_rule):
        """Test health status monitoring with performance validation."""
        event_router.add_routing_rule(sample_routing_rule)

        # Generate some routing activity
        for i in range(10):
            event_router.route_event(
                event_type='tier_pattern',
                event_data={'pattern_type': 'BreakoutBO', 'sequence': i},
                user_context={}
            )

        # Get health status
        health_status = event_router.get_health_status()

        # Verify health status structure
        assert 'service' in health_status
        assert 'status' in health_status
        assert 'message' in health_status
        assert 'timestamp' in health_status
        assert 'stats' in health_status
        assert 'performance_targets' in health_status

        # Verify service identification
        assert health_status['service'] == 'event_router'

        # Verify status is reasonable (should be healthy with normal routing)
        assert health_status['status'] in ['healthy', 'warning', 'error']

        # Verify performance targets
        targets = health_status['performance_targets']
        assert targets['routing_time_target_ms'] == 20.0
        assert targets['cache_hit_rate_target_percent'] == 50.0
        assert targets['error_rate_target'] == 5

    def test_optimize_performance_cleanup(self, event_router, sample_routing_rule):
        """Test performance optimization cleans up stale data."""
        event_router.add_routing_rule(sample_routing_rule)

        # Create stale cache entries
        old_time = time.time() - 400  # 400 seconds ago (> 5 minute TTL)
        for i in range(10):
            cache_key = f'stale_key_{i}'
            event_router.route_cache[cache_key] = (Mock(), old_time)

        # Add recent cache entries
        for i in range(5):
            cache_key = f'fresh_key_{i}'
            event_router.route_cache[cache_key] = (Mock(), time.time())

        # Run optimization
        optimization_results = event_router.optimize_performance()

        # Verify optimization results
        assert 'cache_cleaned' in optimization_results
        assert 'rules_optimized' in optimization_results

        # Verify stale entries were cleaned
        assert optimization_results['cache_cleaned'] >= 10

        # Verify rules were optimized (reordered by usage)
        assert optimization_results['rules_optimized'] > 0

    def test_graceful_shutdown(self, event_router):
        """Test graceful shutdown process."""
        # Add some state to clean up
        event_router.route_cache['test_key'] = (Mock(), time.time())

        # Shutdown should complete without errors
        event_router.shutdown()

        # Verify cleanup occurred
        assert len(event_router.route_cache) == 0
        assert len(event_router.cache_access_order) == 0

    def test_convenience_routing_rule_creators(self):
        """Test convenience functions for creating common routing rules."""
        # Test pattern routing rule creation
        pattern_rule = create_pattern_routing_rule(
            rule_id='test_pattern_rule',
            pattern_types=['BreakoutBO', 'TrendReversal'],
            symbols=['AAPL', 'MSFT']
        )

        assert pattern_rule.rule_id == 'test_pattern_rule'
        assert pattern_rule.strategy == RoutingStrategy.CONTENT_BASED
        assert pattern_rule.priority == DeliveryPriority.HIGH

        # Test market data routing rule creation
        market_rule = create_market_data_routing_rule(
            rule_id='test_market_rule',
            symbols=['AAPL', 'GOOGL']
        )

        assert market_rule.rule_id == 'test_market_rule'
        assert market_rule.strategy == RoutingStrategy.BROADCAST_ALL
        assert market_rule.priority == DeliveryPriority.MEDIUM

        # Test tier routing rule creation
        tier_rule = create_tier_routing_rule(
            rule_id='test_tier_rule',
            tier='daily'
        )

        assert tier_rule.rule_id == 'test_tier_rule'
        assert tier_rule.strategy == RoutingStrategy.CONTENT_BASED
        assert 'tier_daily' in tier_rule.destinations

    def test_thread_safety_concurrent_routing(self, event_router, sample_routing_rule):
        """Test thread safety with concurrent routing operations."""
        event_router.add_routing_rule(sample_routing_rule)

        results = {'success_count': 0, 'errors': []}

        def routing_worker(worker_id):
            """Worker function for concurrent routing."""
            try:
                for i in range(30):
                    result = event_router.route_event(
                        event_type='tier_pattern',
                        event_data={
                            'pattern_type': 'BreakoutBO',
                            'symbol': f'TEST{worker_id}',
                            'confidence': 0.7 + (i % 3) * 0.1,
                            'sequence': i
                        },
                        user_context={'worker': worker_id}
                    )

                    if result and result.event_id:
                        results['success_count'] += 1

                    # Small delay to encourage race conditions
                    time.sleep(0.001)

            except Exception as e:
                results['errors'].append(f"Worker {worker_id}: {str(e)}")

        def cache_worker():
            """Worker function for concurrent cache operations."""
            try:
                time.sleep(0.05)  # Let some routing happen first
                for i in range(10):
                    # Trigger cache operations
                    event_router.optimize_performance()
                    time.sleep(0.01)

            except Exception as e:
                results['errors'].append(f"Cache worker: {str(e)}")

        # Create and start threads
        threads = []

        # Routing worker threads
        for i in range(4):
            thread = threading.Thread(target=routing_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Cache worker thread
        cache_thread = threading.Thread(target=cache_worker)
        threads.append(cache_thread)
        cache_thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)

        # Verify no errors occurred
        assert len(results['errors']) == 0, f"Thread safety errors: {results['errors']}"

        # Verify reasonable number of successful routings
        assert results['success_count'] >= 100  # Most should succeed

        # Verify system integrity
        stats = event_router.get_routing_stats()
        assert stats['total_events'] > 0

    def test_error_handling_malformed_rules(self, event_router):
        """Test error handling with malformed routing rules."""
        # Rule with invalid regex pattern
        bad_rule = RoutingRule(
            rule_id='bad_rule',
            name='Bad Rule',
            description='Rule with invalid regex',
            event_type_patterns=[r'[invalid_regex'],  # Invalid regex
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        # Should handle bad rule gracefully
        success = event_router.add_routing_rule(bad_rule)
        assert success is True  # Should still add the rule

        # Routing with bad rule should not crash
        result = event_router.route_event(
            event_type='test_event',
            event_data={'test': True},
            user_context={}
        )

        # Should return valid result even with bad rule
        assert result is not None
        assert result.event_id is not None

    def test_routing_rule_usage_tracking(self, event_router, sample_routing_rule):
        """Test routing rule usage statistics are tracked."""
        event_router.add_routing_rule(sample_routing_rule)

        # Initially, rule should have no usage
        assert sample_routing_rule.messages_routed == 0

        # Route events that match the rule
        for i in range(5):
            event_router.route_event(
                event_type='tier_pattern',
                event_data={
                    'pattern_type': 'BreakoutBO',
                    'confidence': 0.8,
                    'sequence': i
                },
                user_context={}
            )

        # Rule usage should be updated
        assert sample_routing_rule.messages_routed == 5
        assert sample_routing_rule.last_used > 0

    def test_cache_key_generation_consistency(self, event_router):
        """Test cache key generation is consistent and unique."""
        # Same criteria should generate same key
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

        user_context = {'user_id': 'test_user'}

        key1 = event_router._generate_cache_key('tier_pattern', criteria1, user_context)
        key2 = event_router._generate_cache_key('tier_pattern', criteria2, user_context)

        # Should generate identical keys
        assert key1 == key2

        # Different criteria should generate different keys
        criteria3 = {
            'pattern_type': 'TrendReversal',
            'symbol': 'AAPL',
            'confidence': 0.8
        }

        key3 = event_router._generate_cache_key('tier_pattern', criteria3, user_context)
        assert key3 != key1

    def test_routing_with_disabled_rules(self, event_router):
        """Test routing properly handles disabled rules."""
        # Create disabled rule
        disabled_rule = RoutingRule(
            rule_id='disabled_rule',
            name='Disabled Rule',
            description='Rule that is disabled',
            event_type_patterns=[r'tier_pattern'],
            content_filters={'pattern_type': 'BreakoutBO'},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['disabled_room'],
            priority=DeliveryPriority.MEDIUM,
            enabled=False  # Disabled
        )

        event_router.add_routing_rule(disabled_rule)

        # Route event that would match if enabled
        result = event_router.route_event(
            event_type='tier_pattern',
            event_data={'pattern_type': 'BreakoutBO'},
            user_context={}
        )

        # Disabled rule should not be matched
        assert 'disabled_rule' not in result.matched_rules
        assert result.total_users == 0

    @pytest.mark.performance
    def test_routing_performance_under_load(self, event_router):
        """Test routing performance under high load."""
        # Add multiple complex rules
        for i in range(20):
            rule = RoutingRule(
                rule_id=f'load_rule_{i}',
                name=f'Load Rule {i}',
                description=f'Rule for load testing {i}',
                event_type_patterns=[r'tier_pattern', r'market_.*'],
                content_filters={
                    'confidence': {'min': 0.5 + i * 0.02},
                    'pattern_type': ['BreakoutBO', 'TrendReversal'][i % 2]
                },
                user_criteria={},
                strategy=[RoutingStrategy.BROADCAST_ALL, RoutingStrategy.CONTENT_BASED][i % 2],
                destinations=[f'load_room_{i}'],
                priority=list(DeliveryPriority)[i % 4]
            )
            event_router.add_routing_rule(rule)

        # Test routing performance under load
        total_routing_time = 0
        successful_routes = 0

        for i in range(100):
            start_time = time.time()

            result = event_router.route_event(
                event_type='tier_pattern',
                event_data={
                    'pattern_type': ['BreakoutBO', 'TrendReversal'][i % 2],
                    'symbol': f'LOAD{i % 10}',
                    'confidence': 0.5 + (i % 5) * 0.1
                },
                user_context={'load_test': True}
            )

            routing_time = (time.time() - start_time) * 1000
            total_routing_time += routing_time

            if result and result.event_id:
                successful_routes += 1

            # Individual routing should meet performance target
            assert routing_time < 20.0, f"Route {i} took {routing_time:.2f}ms"

        # Verify overall performance
        avg_routing_time = total_routing_time / 100
        assert avg_routing_time < 15.0, f"Average routing time {avg_routing_time:.2f}ms exceeds target"
        assert successful_routes >= 95, f"Only {successful_routes}/100 routes successful"

        # Verify system remains stable under load
        stats = event_router.get_routing_stats()
        assert stats['total_events'] == 100
        assert stats['avg_routing_time_ms'] < 15.0
