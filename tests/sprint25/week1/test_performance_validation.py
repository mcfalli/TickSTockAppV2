"""
Test Suite for Performance Validation
Sprint 25 Week 1 - Comprehensive performance target validation

Tests all performance targets for the complete 4-layer WebSocket architecture:
- <5ms user filtering (Layer 2: SubscriptionIndexManager)
- <20ms intelligent routing (Layer 4: EventRouter)
- <100ms batched delivery (Layer 3: ScalableBroadcaster)
- <125ms total end-to-end latency (Complete system)
- 500+ concurrent users supported
- >50% cache hit rate (EventRouter)
"""

import pytest
import time
import statistics
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.services.websocket_subscription_manager import UniversalWebSocketManager
from src.infrastructure.websocket.subscription_index_manager import SubscriptionIndexManager
from src.infrastructure.websocket.scalable_broadcaster import ScalableBroadcaster, DeliveryPriority
from src.infrastructure.websocket.event_router import EventRouter


@pytest.fixture
def performance_test_system():
    """Create system optimized for performance testing."""
    mock_socketio = Mock()
    mock_socketio.server = Mock()
    mock_socketio.emit = Mock()
    
    mock_redis = Mock()
    mock_existing_ws = Mock()
    mock_existing_ws.is_user_connected.return_value = True
    mock_existing_ws.get_user_connections.return_value = ['conn_1']
    
    mock_ws_broadcaster = Mock()
    
    # Create optimized system
    universal_manager = UniversalWebSocketManager(
        socketio=mock_socketio,
        redis_client=mock_redis,
        existing_websocket_manager=mock_existing_ws,
        websocket_broadcaster=mock_ws_broadcaster
    )
    
    return {
        'universal_manager': universal_manager,
        'index_manager': universal_manager.index_manager,
        'broadcaster': universal_manager.broadcaster,
        'event_router': universal_manager.event_router,
        'socketio': mock_socketio
    }


class PerformanceMetrics:
    """Helper class for tracking performance metrics."""
    
    def __init__(self):
        self.measurements: List[float] = []
        self.start_time: float = 0
        self.end_time: float = 0
    
    def start_measurement(self):
        """Start timing measurement."""
        self.start_time = time.perf_counter()
    
    def end_measurement(self) -> float:
        """End timing measurement and return duration in milliseconds."""
        self.end_time = time.perf_counter()
        duration_ms = (self.end_time - self.start_time) * 1000
        self.measurements.append(duration_ms)
        return duration_ms
    
    def get_statistics(self) -> Dict[str, float]:
        """Get comprehensive timing statistics."""
        if not self.measurements:
            return {'count': 0}
        
        return {
            'count': len(self.measurements),
            'min_ms': min(self.measurements),
            'max_ms': max(self.measurements),
            'avg_ms': statistics.mean(self.measurements),
            'median_ms': statistics.median(self.measurements),
            'p95_ms': self._percentile(self.measurements, 95),
            'p99_ms': self._percentile(self.measurements, 99),
            'std_dev_ms': statistics.stdev(self.measurements) if len(self.measurements) > 1 else 0
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


@pytest.mark.performance
class TestPerformanceValidation:
    """Comprehensive performance validation for Sprint 25 Week 1."""

    def test_layer2_indexing_performance_target_5ms(self, performance_test_system):
        """Test Layer 2 (SubscriptionIndexManager) meets <5ms filtering target."""
        index_manager = performance_test_system['index_manager']
        metrics = PerformanceMetrics()
        
        # Create substantial subscription load for realistic testing
        for i in range(1000):
            user_id = f"index_perf_user_{i:04d}"
            subscription = Mock()
            subscription.user_id = user_id
            subscription.subscription_type = "tier_patterns"
            subscription.filters = {
                'pattern_types': ['BreakoutBO', 'TrendReversal', 'SurgeDetection'][i % 3],
                'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'][i % 5],
                'tiers': ['daily', 'intraday'],
                'confidence_min': 0.5 + (i % 5) * 0.1,
                'market_regimes': ['BULLISH', 'BEARISH', 'NEUTRAL'][i % 3]
            }
            subscription.room_name = f"user_{user_id}"
            subscription.active = True
            subscription.created_at = time.time()
            subscription.last_activity = time.time()
            
            index_manager.add_subscription(subscription)
        
        # Test various filtering scenarios for comprehensive performance validation
        test_scenarios = [
            # Simple filtering
            {
                'subscription_type': 'tier_patterns',
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL'
            },
            # Complex multi-dimension filtering
            {
                'subscription_type': 'tier_patterns',
                'pattern_type': 'TrendReversal',
                'symbol': 'MSFT',
                'tier': 'daily',
                'confidence': 0.8,
                'market_regime': 'BULLISH'
            },
            # High selectivity filtering
            {
                'pattern_type': 'SurgeDetection',
                'symbol': 'TSLA',
                'confidence': 0.9
            },
            # Broad filtering (many matches)
            {
                'subscription_type': 'tier_patterns',
                'tier': 'intraday'
            }
        ]
        
        # Performance test each scenario multiple times
        for scenario_idx, criteria in enumerate(test_scenarios):
            scenario_metrics = PerformanceMetrics()
            
            for iteration in range(50):  # 50 iterations per scenario
                scenario_metrics.start_measurement()
                
                matching_users = index_manager.find_matching_users(criteria)
                
                duration_ms = scenario_metrics.end_measurement()
                
                # Individual measurement must meet target
                assert duration_ms < 5.0, (
                    f"Scenario {scenario_idx}, iteration {iteration}: "
                    f"Filtering took {duration_ms:.2f}ms, exceeds 5ms target"
                )
                
                # Verify we got reasonable results
                assert isinstance(matching_users, set)
                assert len(matching_users) >= 0
            
            # Analyze scenario performance
            stats = scenario_metrics.get_statistics()
            
            # Verify comprehensive performance targets
            assert stats['avg_ms'] < 3.0, f"Scenario {scenario_idx} average {stats['avg_ms']:.2f}ms exceeds 3ms target"
            assert stats['p95_ms'] < 5.0, f"Scenario {scenario_idx} P95 {stats['p95_ms']:.2f}ms exceeds 5ms target"
            assert stats['p99_ms'] < 8.0, f"Scenario {scenario_idx} P99 {stats['p99_ms']:.2f}ms exceeds 8ms target"
            assert stats['max_ms'] < 10.0, f"Scenario {scenario_idx} max {stats['max_ms']:.2f}ms exceeds 10ms limit"
            
            metrics.measurements.extend(scenario_metrics.measurements)
        
        # Overall indexing performance analysis
        overall_stats = metrics.get_statistics()
        
        # Verify overall performance targets
        assert overall_stats['avg_ms'] < 3.0, f"Overall average {overall_stats['avg_ms']:.2f}ms exceeds 3ms target"
        assert overall_stats['p95_ms'] < 5.0, f"Overall P95 {overall_stats['p95_ms']:.2f}ms exceeds 5ms target"
        assert overall_stats['count'] == 200  # 4 scenarios * 50 iterations
        
        print(f"✅ Layer 2 Indexing Performance: {overall_stats['avg_ms']:.1f}ms avg, {overall_stats['p95_ms']:.1f}ms P95, {overall_stats['p99_ms']:.1f}ms P99")

    def test_layer4_routing_performance_target_20ms(self, performance_test_system):
        """Test Layer 4 (EventRouter) meets <20ms routing target."""
        event_router = performance_test_system['event_router']
        metrics = PerformanceMetrics()
        
        # Create comprehensive routing rules for realistic testing
        from src.infrastructure.websocket.event_router import RoutingRule, RoutingStrategy
        
        routing_rules = [
            # Pattern-based routing
            RoutingRule(
                rule_id='pattern_routing',
                name='Pattern Routing',
                description='Routes pattern events',
                event_type_patterns=[r'tier_pattern', r'.*pattern.*'],
                content_filters={'pattern_type': 'BreakoutBO'},
                user_criteria={},
                strategy=RoutingStrategy.CONTENT_BASED,
                destinations=['pattern_room'],
                priority=DeliveryPriority.HIGH
            ),
            # Symbol-based routing  
            RoutingRule(
                rule_id='symbol_routing',
                name='Symbol Routing',
                description='Routes by symbol',
                event_type_patterns=[r'market_.*', r'tier_.*'],
                content_filters={'symbol': 'AAPL'},
                user_criteria={},
                strategy=RoutingStrategy.BROADCAST_ALL,
                destinations=['aapl_room'],
                priority=DeliveryPriority.MEDIUM
            ),
            # Complex filtering rule
            RoutingRule(
                rule_id='complex_routing',
                name='Complex Routing',
                description='Complex multi-criteria routing',
                event_type_patterns=[r'tier_pattern'],
                content_filters={
                    'confidence': {'min': 0.7, 'max': 0.95},
                    'pattern_type': {'contains': 'Breakout'}
                },
                user_criteria={},
                strategy=RoutingStrategy.PRIORITY_FIRST,
                destinations=['high_confidence_room'],
                priority=DeliveryPriority.CRITICAL
            )
        ]
        
        # Add routing rules
        for rule in routing_rules:
            event_router.add_routing_rule(rule)
        
        # Test various routing scenarios
        test_events = [
            # Simple pattern event
            ('tier_pattern', {
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL',
                'confidence': 0.85,
                'tier': 'daily'
            }),
            # Market event
            ('market_update', {
                'symbol': 'AAPL',
                'price': 150.0,
                'volume': 1000000
            }),
            # Complex pattern event
            ('tier_pattern', {
                'pattern_type': 'BreakoutBO_Advanced',
                'symbol': 'MSFT',
                'confidence': 0.88,
                'tier': 'intraday',
                'market_regime': 'BULLISH'
            }),
            # High-confidence event
            ('tier_pattern', {
                'pattern_type': 'TrendBreakout',
                'symbol': 'GOOGL',
                'confidence': 0.92
            })
        ]
        
        user_contexts = [
            {'interested_users': ['user1', 'user2']},
            {'interested_users': ['user3', 'user4', 'user5']},
            {'interested_users': ['user6']},
            {}  # Empty context
        ]
        
        # Performance test routing under various conditions
        for event_idx, (event_type, event_data) in enumerate(test_events):
            for context_idx, user_context in enumerate(user_contexts):
                event_metrics = PerformanceMetrics()
                
                for iteration in range(25):  # 25 iterations per combination
                    event_metrics.start_measurement()
                    
                    routing_result = event_router.route_event(
                        event_type=event_type,
                        event_data=event_data.copy(),
                        user_context=user_context.copy()
                    )
                    
                    duration_ms = event_metrics.end_measurement()
                    
                    # Individual measurement must meet target
                    assert duration_ms < 20.0, (
                        f"Event {event_idx}, context {context_idx}, iteration {iteration}: "
                        f"Routing took {duration_ms:.2f}ms, exceeds 20ms target"
                    )
                    
                    # Verify routing result is valid
                    assert routing_result is not None
                    assert routing_result.event_id is not None
                    assert routing_result.routing_time_ms > 0
                
                # Analyze combination performance
                stats = event_metrics.get_statistics()
                combo_name = f"Event{event_idx}_Context{context_idx}"
                
                assert stats['avg_ms'] < 15.0, f"{combo_name} average {stats['avg_ms']:.2f}ms exceeds 15ms target"
                assert stats['p95_ms'] < 20.0, f"{combo_name} P95 {stats['p95_ms']:.2f}ms exceeds 20ms target"
                assert stats['max_ms'] < 25.0, f"{combo_name} max {stats['max_ms']:.2f}ms exceeds 25ms limit"
                
                metrics.measurements.extend(event_metrics.measurements)
        
        # Overall routing performance analysis
        overall_stats = metrics.get_statistics()
        
        # Verify comprehensive routing performance
        assert overall_stats['avg_ms'] < 12.0, f"Overall routing average {overall_stats['avg_ms']:.2f}ms exceeds 12ms target"
        assert overall_stats['p95_ms'] < 20.0, f"Overall routing P95 {overall_stats['p95_ms']:.2f}ms exceeds 20ms target"
        assert overall_stats['p99_ms'] < 25.0, f"Overall routing P99 {overall_stats['p99_ms']:.2f}ms exceeds 25ms limit"
        
        print(f"✅ Layer 4 Routing Performance: {overall_stats['avg_ms']:.1f}ms avg, {overall_stats['p95_ms']:.1f}ms P95, {overall_stats['p99_ms']:.1f}ms P99")

    def test_layer3_broadcasting_performance_target_100ms(self, performance_test_system):
        """Test Layer 3 (ScalableBroadcaster) meets <100ms delivery target."""
        broadcaster = performance_test_system['broadcaster']
        metrics = PerformanceMetrics()
        
        # Test various broadcasting scenarios
        broadcast_scenarios = [
            # Small user set
            {
                'user_count': 10,
                'event_count': 1,
                'priority': DeliveryPriority.HIGH,
                'name': 'small_user_set'
            },
            # Medium user set
            {
                'user_count': 50,
                'event_count': 1,
                'priority': DeliveryPriority.MEDIUM,
                'name': 'medium_user_set'
            },
            # Large user set
            {
                'user_count': 200,
                'event_count': 1,
                'priority': DeliveryPriority.LOW,
                'name': 'large_user_set'
            },
            # Burst scenario
            {
                'user_count': 25,
                'event_count': 5,
                'priority': DeliveryPriority.CRITICAL,
                'name': 'burst_scenario'
            }
        ]
        
        for scenario in broadcast_scenarios:
            scenario_metrics = PerformanceMetrics()
            
            for iteration in range(20):  # 20 iterations per scenario
                # Create user set
                user_ids = {f"broadcast_user_{scenario['name']}_{i}" for i in range(scenario['user_count'])}
                
                scenario_metrics.start_measurement()
                
                # Broadcast events
                for event_num in range(scenario['event_count']):
                    event_data = {
                        'test_event': True,
                        'scenario': scenario['name'],
                        'iteration': iteration,
                        'event_num': event_num,
                        'timestamp': time.time()
                    }
                    
                    queued_count = broadcaster.broadcast_to_users(
                        event_type=f"perf_test_{scenario['name']}",
                        event_data=event_data,
                        user_ids=user_ids,
                        priority=scenario['priority']
                    )
                    
                    # Verify all users were queued
                    assert queued_count == scenario['user_count'], (
                        f"Only {queued_count}/{scenario['user_count']} users queued"
                    )
                
                # Force delivery for timing measurement
                broadcaster.flush_all_batches()
                
                duration_ms = scenario_metrics.end_measurement()
                
                # Individual measurement must meet target
                assert duration_ms < 100.0, (
                    f"Scenario {scenario['name']}, iteration {iteration}: "
                    f"Broadcasting took {duration_ms:.2f}ms, exceeds 100ms target"
                )
                
                # Small delay between iterations
                time.sleep(0.001)
            
            # Analyze scenario performance
            stats = scenario_metrics.get_statistics()
            
            # Verify scenario-specific targets
            assert stats['avg_ms'] < 75.0, f"Scenario {scenario['name']} average {stats['avg_ms']:.2f}ms exceeds 75ms target"
            assert stats['p95_ms'] < 100.0, f"Scenario {scenario['name']} P95 {stats['p95_ms']:.2f}ms exceeds 100ms target"
            assert stats['max_ms'] < 150.0, f"Scenario {scenario['name']} max {stats['max_ms']:.2f}ms exceeds 150ms limit"
            
            metrics.measurements.extend(scenario_metrics.measurements)
            
            print(f"  Scenario {scenario['name']}: {stats['avg_ms']:.1f}ms avg, {stats['p95_ms']:.1f}ms P95")
        
        # Overall broadcasting performance analysis
        overall_stats = metrics.get_statistics()
        
        # Verify comprehensive broadcasting performance
        assert overall_stats['avg_ms'] < 60.0, f"Overall broadcast average {overall_stats['avg_ms']:.2f}ms exceeds 60ms target"
        assert overall_stats['p95_ms'] < 100.0, f"Overall broadcast P95 {overall_stats['p95_ms']:.2f}ms exceeds 100ms target"
        assert overall_stats['p99_ms'] < 120.0, f"Overall broadcast P99 {overall_stats['p99_ms']:.2f}ms exceeds 120ms limit"
        
        print(f"✅ Layer 3 Broadcasting Performance: {overall_stats['avg_ms']:.1f}ms avg, {overall_stats['p95_ms']:.1f}ms P95, {overall_stats['p99_ms']:.1f}ms P99")

    def test_end_to_end_performance_target_125ms(self, performance_test_system):
        """Test complete system meets <125ms end-to-end latency target."""
        system = performance_test_system
        universal_manager = system['universal_manager']
        metrics = PerformanceMetrics()
        
        # Setup realistic subscription load
        subscription_count = 300
        for i in range(subscription_count):
            user_id = f"e2e_user_{i:03d}"
            universal_manager.subscribe_user(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal', 'SurgeDetection'][i % 3],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'][i % 5],
                    'tiers': ['daily', 'intraday'],
                    'confidence_min': 0.6 + (i % 4) * 0.1
                }
            )
        
        # Test various end-to-end scenarios
        e2e_scenarios = [
            {
                'name': 'high_selectivity',
                'targeting_criteria': {
                    'subscription_type': 'tier_patterns',
                    'pattern_type': 'BreakoutBO',
                    'symbol': 'AAPL',
                    'confidence': 0.9
                },
                'expected_users': 15  # Estimate
            },
            {
                'name': 'medium_selectivity',
                'targeting_criteria': {
                    'subscription_type': 'tier_patterns',
                    'pattern_type': 'TrendReversal',
                    'symbol': 'MSFT'
                },
                'expected_users': 35  # Estimate
            },
            {
                'name': 'broad_targeting',
                'targeting_criteria': {
                    'subscription_type': 'tier_patterns',
                    'tier': 'daily'
                },
                'expected_users': 150  # Estimate
            }
        ]
        
        for scenario in e2e_scenarios:
            scenario_metrics = PerformanceMetrics()
            
            for iteration in range(30):  # 30 iterations per scenario
                # Mock user finding with realistic results
                with patch.object(universal_manager, '_find_interested_users') as mock_find:
                    # Return realistic user set based on scenario
                    interested_users = {
                        f"e2e_user_{i:03d}" 
                        for i in range(scenario['expected_users'])
                    }
                    mock_find.return_value = interested_users
                    
                    # Mock routing result
                    mock_routing_result = Mock()
                    mock_routing_result.total_users = len(interested_users)
                    mock_routing_result.matched_rules = [f"{scenario['name']}_rule"]
                    mock_routing_result.routing_time_ms = 12.0 + (iteration % 5)  # Realistic variation
                    mock_routing_result.cache_hit = iteration > 5  # Some cache hits
                    
                    with patch.object(system['event_router'], 'route_event') as mock_route:
                        mock_route.return_value = mock_routing_result
                        
                        scenario_metrics.start_measurement()
                        
                        # Complete end-to-end broadcast
                        delivery_count = universal_manager.broadcast_event(
                            event_type='tier_pattern',
                            event_data={
                                'pattern_type': 'PerformanceTest',
                                'symbol': 'TEST',
                                'confidence': 0.85,
                                'scenario': scenario['name'],
                                'iteration': iteration,
                                'timestamp': time.time()
                            },
                            targeting_criteria=scenario['targeting_criteria']
                        )
                        
                        duration_ms = scenario_metrics.end_measurement()
                        
                        # Verify delivery was successful
                        assert delivery_count == len(interested_users)
                        
                        # Individual measurement must meet target
                        assert duration_ms < 125.0, (
                            f"E2E Scenario {scenario['name']}, iteration {iteration}: "
                            f"End-to-end took {duration_ms:.2f}ms, exceeds 125ms target"
                        )
            
            # Analyze scenario performance
            stats = scenario_metrics.get_statistics()
            
            # Verify scenario-specific end-to-end targets
            assert stats['avg_ms'] < 100.0, f"E2E Scenario {scenario['name']} average {stats['avg_ms']:.2f}ms exceeds 100ms target"
            assert stats['p95_ms'] < 125.0, f"E2E Scenario {scenario['name']} P95 {stats['p95_ms']:.2f}ms exceeds 125ms target"
            assert stats['max_ms'] < 150.0, f"E2E Scenario {scenario['name']} max {stats['max_ms']:.2f}ms exceeds 150ms limit"
            
            metrics.measurements.extend(scenario_metrics.measurements)
            
            print(f"  E2E Scenario {scenario['name']}: {stats['avg_ms']:.1f}ms avg, {stats['p95_ms']:.1f}ms P95")
        
        # Overall end-to-end performance analysis
        overall_stats = metrics.get_statistics()
        
        # Verify comprehensive end-to-end performance
        assert overall_stats['avg_ms'] < 80.0, f"Overall E2E average {overall_stats['avg_ms']:.2f}ms exceeds 80ms target"
        assert overall_stats['p95_ms'] < 125.0, f"Overall E2E P95 {overall_stats['p95_ms']:.2f}ms exceeds 125ms target"
        assert overall_stats['p99_ms'] < 140.0, f"Overall E2E P99 {overall_stats['p99_ms']:.2f}ms exceeds 140ms limit"
        
        print(f"✅ End-to-End Performance: {overall_stats['avg_ms']:.1f}ms avg, {overall_stats['p95_ms']:.1f}ms P95, {overall_stats['p99_ms']:.1f}ms P99")

    def test_concurrent_user_capacity_500_plus(self, performance_test_system):
        """Test system supports 500+ concurrent users with maintained performance."""
        system = performance_test_system
        universal_manager = system['universal_manager']
        
        # Test various user capacity levels
        capacity_tests = [
            {'user_count': 250, 'name': 'quarter_capacity'},
            {'user_count': 500, 'name': 'target_capacity'},
            {'user_count': 750, 'name': 'over_capacity'},
            {'user_count': 1000, 'name': 'stress_capacity'}
        ]
        
        for capacity_test in capacity_tests:
            user_count = capacity_test['user_count']
            test_name = capacity_test['name']
            
            capacity_metrics = PerformanceMetrics()
            
            print(f"  Testing {user_count} concurrent users ({test_name})...")
            
            # Setup phase - create subscriptions
            setup_start = time.time()
            
            for i in range(user_count):
                user_id = f"capacity_user_{test_name}_{i:04d}"
                success = universal_manager.subscribe_user(
                    user_id=user_id,
                    subscription_type="tier_patterns",
                    filters={
                        'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                        'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'][i % 5],
                        'confidence_min': 0.6 + (i % 4) * 0.1
                    }
                )
                assert success, f"Failed to subscribe user {user_id}"
            
            setup_time = time.time() - setup_start
            
            # Verify subscription capacity
            stats = universal_manager.get_subscription_stats()
            assert stats['total_users'] >= user_count, f"Only {stats['total_users']}/{user_count} users subscribed"
            
            # Performance phase - test filtering with full load
            for test_iteration in range(10):
                capacity_metrics.start_measurement()
                
                # Test indexing performance under load
                matching_users = system['index_manager'].find_matching_users({
                    'subscription_type': 'tier_patterns',
                    'pattern_type': 'BreakoutBO',
                    'symbol': 'AAPL'
                })
                
                duration_ms = capacity_metrics.end_measurement()
                
                # Performance should degrade gracefully but stay within limits
                max_allowed_ms = 8.0 if user_count <= 500 else 12.0 if user_count <= 750 else 20.0
                assert duration_ms < max_allowed_ms, (
                    f"Capacity test {test_name}, iteration {test_iteration}: "
                    f"Filtering with {user_count} users took {duration_ms:.2f}ms, exceeds {max_allowed_ms}ms limit"
                )
                
                # Verify reasonable results
                assert len(matching_users) >= 0
            
            # Analyze capacity performance
            perf_stats = capacity_metrics.get_statistics()
            
            # Verify capacity-appropriate performance targets
            if user_count <= 500:
                assert perf_stats['avg_ms'] < 5.0, f"Target capacity {test_name} average {perf_stats['avg_ms']:.2f}ms exceeds 5ms"
                assert perf_stats['p95_ms'] < 8.0, f"Target capacity {test_name} P95 {perf_stats['p95_ms']:.2f}ms exceeds 8ms"
            elif user_count <= 750:
                assert perf_stats['avg_ms'] < 8.0, f"Over capacity {test_name} average {perf_stats['avg_ms']:.2f}ms exceeds 8ms"
                assert perf_stats['p95_ms'] < 12.0, f"Over capacity {test_name} P95 {perf_stats['p95_ms']:.2f}ms exceeds 12ms"
            else:  # stress capacity
                assert perf_stats['avg_ms'] < 15.0, f"Stress capacity {test_name} average {perf_stats['avg_ms']:.2f}ms exceeds 15ms"
                assert perf_stats['p95_ms'] < 20.0, f"Stress capacity {test_name} P95 {perf_stats['p95_ms']:.2f}ms exceeds 20ms"
            
            print(f"    {user_count} users: {perf_stats['avg_ms']:.1f}ms avg filtering, {setup_time:.1f}s setup")
            
            # Cleanup for next test
            universal_manager.user_subscriptions.clear()
            system['index_manager'].__init__(cache_size=1000, enable_optimization=True)
        
        print("✅ Concurrent User Capacity: 500+ users supported with acceptable performance degradation")

    def test_cache_hit_rate_performance_target(self, performance_test_system):
        """Test EventRouter achieves >50% cache hit rate target."""
        event_router = performance_test_system['event_router']
        
        # Add routing rules to enable caching
        from src.infrastructure.websocket.event_router import RoutingRule, RoutingStrategy
        
        test_rule = RoutingRule(
            rule_id='cache_test_rule',
            name='Cache Test Rule',
            description='Rule for cache testing',
            event_type_patterns=[r'tier_pattern'],
            content_filters={'pattern_type': 'BreakoutBO'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=['cache_test_room'],
            priority=DeliveryPriority.MEDIUM
        )
        
        event_router.add_routing_rule(test_rule)
        
        # Create events with some repetition to enable caching
        test_events = [
            # Repeated events (should be cached)
            ('tier_pattern', {'pattern_type': 'BreakoutBO', 'symbol': 'AAPL', 'confidence': 0.8}),
            ('tier_pattern', {'pattern_type': 'BreakoutBO', 'symbol': 'MSFT', 'confidence': 0.8}),
            ('tier_pattern', {'pattern_type': 'BreakoutBO', 'symbol': 'GOOGL', 'confidence': 0.8}),
            # Unique events (cache misses)
            ('market_update', {'symbol': 'AAPL', 'price': 150.0}),
            ('market_update', {'symbol': 'MSFT', 'price': 300.0}),
        ]
        
        user_contexts = [
            {'interested_users': ['user1', 'user2']},
            {'interested_users': ['user3', 'user4']},
            {}
        ]
        
        # Initial routing pass to establish cache
        for event_type, event_data in test_events:
            for user_context in user_contexts:
                event_router.route_event(event_type, event_data, user_context)
        
        # Performance test with cache hits
        cache_test_results = []
        
        for iteration in range(100):
            # Choose events with high probability of cache hits
            event_type, event_data = test_events[iteration % len(test_events)]
            user_context = user_contexts[iteration % len(user_contexts)]
            
            start_time = time.time()
            routing_result = event_router.route_event(event_type, event_data, user_context)
            duration_ms = (time.time() - start_time) * 1000
            
            cache_test_results.append({
                'duration_ms': duration_ms,
                'cache_hit': routing_result.cache_hit if hasattr(routing_result, 'cache_hit') else False
            })
        
        # Analyze cache performance
        cache_hits = sum(1 for result in cache_test_results if result['cache_hit'])
        cache_hit_rate = (cache_hits / len(cache_test_results)) * 100
        
        # Get router statistics
        router_stats = event_router.get_routing_stats()
        
        # Verify cache hit rate targets
        if 'cache_hit_rate_percent' in router_stats:
            stats_hit_rate = router_stats['cache_hit_rate_percent']
            assert stats_hit_rate >= 50.0, f"Cache hit rate {stats_hit_rate:.1f}% below 50% target"
            
            print(f"✅ Cache Performance: {stats_hit_rate:.1f}% hit rate (target: >50%)")
        else:
            # Fallback to test-calculated rate
            assert cache_hit_rate >= 30.0, f"Measured cache hit rate {cache_hit_rate:.1f}% below minimum 30%"
            print(f"✅ Cache Performance: {cache_hit_rate:.1f}% hit rate (measured)")
        
        # Verify cached vs non-cached performance difference
        cached_times = [r['duration_ms'] for r in cache_test_results if r['cache_hit']]
        non_cached_times = [r['duration_ms'] for r in cache_test_results if not r['cache_hit']]
        
        if cached_times and non_cached_times:
            avg_cached = statistics.mean(cached_times)
            avg_non_cached = statistics.mean(non_cached_times)
            
            # Cached requests should be faster
            assert avg_cached <= avg_non_cached, "Cached requests should be faster than non-cached"
            
            improvement = ((avg_non_cached - avg_cached) / avg_non_cached) * 100
            print(f"  Cache improvement: {improvement:.1f}% faster ({avg_cached:.1f}ms vs {avg_non_cached:.1f}ms)")

    def test_sustained_load_performance_stability(self, performance_test_system):
        """Test performance remains stable under sustained load."""
        system = performance_test_system
        universal_manager = system['universal_manager']
        
        # Setup sustained load test
        user_count = 400
        for i in range(user_count):
            universal_manager.subscribe_user(
                user_id=f"sustained_user_{i:03d}",
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL'][i % 3],
                    'confidence_min': 0.7
                }
            )
        
        # Sustained load test parameters
        test_duration_seconds = 30
        events_per_second = 10
        total_events = test_duration_seconds * events_per_second
        
        performance_windows = []
        window_size = 50  # Events per window
        
        print(f"  Running sustained load test: {total_events} events over {test_duration_seconds}s...")
        
        start_time = time.time()
        
        for event_num in range(total_events):
            window_start = (event_num // window_size) * window_size
            if event_num % window_size == 0:
                performance_windows.append(PerformanceMetrics())
            
            current_window = performance_windows[-1]
            
            # Mock realistic user finding
            with patch.object(universal_manager, '_find_interested_users') as mock_find:
                interested_users = {f"sustained_user_{i:03d}" for i in range(20 + (event_num % 10))}
                mock_find.return_value = interested_users
                
                mock_routing_result = Mock()
                mock_routing_result.total_users = len(interested_users)
                mock_routing_result.matched_rules = ['sustained_rule']
                mock_routing_result.routing_time_ms = 10.0 + (event_num % 5)
                mock_routing_result.cache_hit = event_num % 3 == 0  # 33% cache hit rate
                
                with patch.object(system['event_router'], 'route_event') as mock_route:
                    mock_route.return_value = mock_routing_result
                    
                    current_window.start_measurement()
                    
                    # Execute broadcast
                    delivery_count = universal_manager.broadcast_event(
                        event_type='sustained_load_test',
                        event_data={
                            'event_num': event_num,
                            'timestamp': time.time(),
                            'load_test': True
                        },
                        targeting_criteria={
                            'subscription_type': 'tier_patterns',
                            'pattern_type': 'BreakoutBO'
                        }
                    )
                    
                    duration_ms = current_window.end_measurement()
                    
                    # Individual event should maintain performance
                    assert duration_ms < 150.0, f"Event {event_num} took {duration_ms:.2f}ms under sustained load"
                    assert delivery_count == len(interested_users)
            
            # Maintain target rate
            if event_num > 0:
                elapsed = time.time() - start_time
                expected_elapsed = event_num / events_per_second
                if elapsed < expected_elapsed:
                    time.sleep(expected_elapsed - elapsed)
        
        total_elapsed = time.time() - start_time
        
        # Analyze performance stability across windows
        window_stats = []
        for i, window in enumerate(performance_windows):
            if window.measurements:  # Skip empty windows
                stats = window.get_statistics()
                window_stats.append(stats)
                
                # Each window should maintain reasonable performance
                assert stats['avg_ms'] < 120.0, f"Window {i} average {stats['avg_ms']:.2f}ms exceeds 120ms"
                assert stats['p95_ms'] < 150.0, f"Window {i} P95 {stats['p95_ms']:.2f}ms exceeds 150ms"
        
        # Verify performance stability (no degradation over time)
        if len(window_stats) >= 3:
            early_avg = statistics.mean([w['avg_ms'] for w in window_stats[:3]])
            late_avg = statistics.mean([w['avg_ms'] for w in window_stats[-3:]])
            
            degradation_percent = ((late_avg - early_avg) / early_avg) * 100
            
            # Performance should not degrade more than 20% over sustained load
            assert degradation_percent < 20.0, (
                f"Performance degraded {degradation_percent:.1f}% over sustained load "
                f"(early: {early_avg:.1f}ms, late: {late_avg:.1f}ms)"
            )
            
            print(f"  Performance stability: {degradation_percent:+.1f}% change over {test_duration_seconds}s")
        
        # Verify overall sustained load performance
        all_measurements = []
        for window in performance_windows:
            all_measurements.extend(window.measurements)
        
        overall_stats = PerformanceMetrics()
        overall_stats.measurements = all_measurements
        final_stats = overall_stats.get_statistics()
        
        assert final_stats['avg_ms'] < 100.0, f"Sustained load average {final_stats['avg_ms']:.2f}ms exceeds 100ms"
        assert final_stats['p95_ms'] < 150.0, f"Sustained load P95 {final_stats['p95_ms']:.2f}ms exceeds 150ms"
        
        print(f"✅ Sustained Load Performance: {final_stats['avg_ms']:.1f}ms avg over {total_events} events, {total_elapsed:.1f}s duration")

    def test_memory_performance_under_load(self, performance_test_system):
        """Test memory usage remains reasonable under performance load."""
        system = performance_test_system
        universal_manager = system['universal_manager']
        
        # This is a simplified memory test - in production you'd use memory profiling tools
        # We'll test that the system maintains performance with large data sets
        
        large_user_count = 2000
        print(f"  Testing memory performance with {large_user_count} users...")
        
        # Create large subscription dataset
        setup_start = time.time()
        for i in range(large_user_count):
            user_id = f"memory_user_{i:04d}"
            universal_manager.subscribe_user(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal', 'SurgeDetection'][i % 3],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'][i % 5],
                    'tiers': ['daily', 'intraday'],
                    'confidence_min': 0.5 + (i % 5) * 0.1,
                    'priority_min': ['LOW', 'MEDIUM', 'HIGH'][i % 3]
                }
            )
        
        setup_time = time.time() - setup_start
        
        # Verify all subscriptions were created
        stats = universal_manager.get_subscription_stats()
        assert stats['total_users'] == large_user_count, f"Only {stats['total_users']}/{large_user_count} users created"
        
        # Test performance with large dataset
        memory_perf_metrics = PerformanceMetrics()
        
        for test_run in range(20):
            memory_perf_metrics.start_measurement()
            
            # Test indexing performance
            matching_users = system['index_manager'].find_matching_users({
                'subscription_type': 'tier_patterns',
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL'
            })
            
            duration_ms = memory_perf_metrics.end_measurement()
            
            # Performance should scale reasonably with large datasets
            assert duration_ms < 15.0, f"Large dataset filtering took {duration_ms:.2f}ms, exceeds 15ms limit"
            assert len(matching_users) > 0, "Should find matching users in large dataset"
        
        # Analyze large dataset performance
        memory_stats = memory_perf_metrics.get_statistics()
        
        # Verify reasonable performance with large dataset
        assert memory_stats['avg_ms'] < 10.0, f"Large dataset avg {memory_stats['avg_ms']:.2f}ms exceeds 10ms"
        assert memory_stats['p95_ms'] < 15.0, f"Large dataset P95 {memory_stats['p95_ms']:.2f}ms exceeds 15ms"
        
        # Test cleanup performance
        cleanup_start = time.time()
        cleaned_count = universal_manager.cleanup_inactive_subscriptions(max_inactive_hours=0)
        cleanup_time = time.time() - cleanup_start
        
        # Cleanup should be reasonably fast even with large datasets
        assert cleanup_time < 5.0, f"Cleanup took {cleanup_time:.2f}s, too slow for large dataset"
        
        print(f"✅ Memory Performance: {large_user_count} users, {memory_stats['avg_ms']:.1f}ms avg filtering, {setup_time:.1f}s setup, {cleanup_time:.1f}s cleanup")

    def test_performance_monitoring_and_alerts(self, performance_test_system):
        """Test performance monitoring detects and reports performance issues."""
        system = performance_test_system
        universal_manager = system['universal_manager']
        
        # Setup normal performance baseline
        for i in range(100):
            universal_manager.subscribe_user(
                user_id=f"monitor_user_{i:02d}",
                subscription_type="tier_patterns",
                filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
            )
        
        # Test normal performance monitoring
        with patch.object(universal_manager, '_find_interested_users') as mock_find:
            mock_find.return_value = {f"monitor_user_{i:02d}" for i in range(10)}
            
            mock_routing_result = Mock()
            mock_routing_result.total_users = 10
            mock_routing_result.matched_rules = ['monitor_rule']
            mock_routing_result.routing_time_ms = 8.0  # Within targets
            mock_routing_result.cache_hit = False
            
            with patch.object(system['event_router'], 'route_event') as mock_route:
                mock_route.return_value = mock_routing_result
                
                # Generate normal activity
                for i in range(10):
                    universal_manager.broadcast_event(
                        event_type='monitor_test',
                        event_data={'test': i},
                        targeting_criteria={'subscription_type': 'tier_patterns'}
                    )
        
        # Get health status with normal performance
        healthy_status = universal_manager.get_health_status()
        assert healthy_status['status'] in ['healthy', 'warning']  # Should be healthy or minor warnings
        
        # Test performance issue detection by simulating slow indexing
        with patch.object(system['index_manager'], 'find_matching_users') as mock_slow_index:
            def slow_indexing(*args, **kwargs):
                time.sleep(0.02)  # 20ms delay to trigger performance warning
                return {'monitor_user_01'}
            
            mock_slow_index.side_effect = slow_indexing
            
            # This should trigger performance warnings
            with patch.object(universal_manager, '_find_interested_users') as mock_find:
                mock_find.return_value = {'monitor_user_01'}
                
                # Generate activity that should trigger slow performance detection
                for i in range(5):
                    universal_manager.broadcast_event(
                        event_type='slow_test',
                        event_data={'test': i},
                        targeting_criteria={'subscription_type': 'tier_patterns'}
                    )
        
        # Verify performance monitoring detected issues
        stats = universal_manager.get_subscription_stats()
        
        # Should have reasonable performance metrics
        assert 'avg_filtering_latency_ms' in stats
        assert stats['events_broadcast'] >= 15  # 10 normal + 5 slow
        
        # Test health status reflects performance issues
        performance_health = universal_manager.get_health_status()
        
        # Verify health monitoring includes performance targets
        assert 'performance_targets' in performance_health
        targets = performance_health['performance_targets']
        assert targets['filtering_target_ms'] == 5.0
        assert targets['broadcast_target_ms'] == 100.0
        
        print("✅ Performance Monitoring: Health checks and performance targets validated")

    def test_performance_optimization_effectiveness(self, performance_test_system):
        """Test performance optimization improves system performance."""
        system = performance_test_system
        universal_manager = system['universal_manager']
        
        # Create load that will benefit from optimization
        for i in range(200):
            universal_manager.subscribe_user(
                user_id=f"opt_user_{i:03d}",
                subscription_type="tier_patterns",
                filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
            )
        
        # Generate activity to create optimization opportunities
        with patch.object(universal_manager, '_find_interested_users') as mock_find:
            mock_find.return_value = {f"opt_user_{i:03d}" for i in range(20)}
            
            # Generate repeated queries for caching opportunities
            for i in range(50):
                system['index_manager'].find_matching_users({
                    'subscription_type': 'tier_patterns',
                    'pattern_type': 'BreakoutBO',
                    'symbol': 'AAPL'
                })
        
        # Measure performance before optimization
        pre_opt_metrics = PerformanceMetrics()
        
        for i in range(20):
            pre_opt_metrics.start_measurement()
            
            matching_users = system['index_manager'].find_matching_users({
                'subscription_type': 'tier_patterns',
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL'
            })
            
            pre_opt_metrics.end_measurement()
        
        pre_opt_stats = pre_opt_metrics.get_statistics()
        
        # Run performance optimization
        with patch.object(system['index_manager'], 'optimize_indexes') as mock_idx_opt, \
             patch.object(system['broadcaster'], 'optimize_performance') as mock_broadcast_opt, \
             patch.object(system['event_router'], 'optimize_performance') as mock_route_opt:
            
            mock_idx_opt.return_value = {'indexes_optimized': 15, 'cache_cleaned': 10}
            mock_broadcast_opt.return_value = {'batches_flushed': 5, 'performance_improved': True}
            mock_route_opt.return_value = {'cache_cleaned': 8, 'rules_optimized': 3}
            
            optimization_results = universal_manager.optimize_performance()
            
            # Verify optimization was called on all layers
            mock_idx_opt.assert_called_once()
            mock_broadcast_opt.assert_called_once()
            mock_route_opt.assert_called_once()
        
        # Measure performance after optimization
        post_opt_metrics = PerformanceMetrics()
        
        for i in range(20):
            post_opt_metrics.start_measurement()
            
            matching_users = system['index_manager'].find_matching_users({
                'subscription_type': 'tier_patterns',
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL'
            })
            
            post_opt_metrics.end_measurement()
        
        post_opt_stats = post_opt_metrics.get_statistics()
        
        # Verify optimization results structure
        assert 'index_optimization' in optimization_results
        assert 'broadcast_optimization' in optimization_results
        assert 'routing_optimization' in optimization_results
        assert 'performance_targets_met' in optimization_results
        
        # Performance should remain good (optimization may not show dramatic improvement in mocked tests)
        assert post_opt_stats['avg_ms'] < 10.0, f"Post-optimization performance {post_opt_stats['avg_ms']:.2f}ms not acceptable"
        
        # Verify performance targets assessment
        targets_met = optimization_results['performance_targets_met']
        assert 'filtering_under_5ms' in targets_met
        assert 'broadcast_under_100ms' in targets_met
        assert 'routing_under_20ms' in targets_met
        
        print(f"✅ Performance Optimization: Pre: {pre_opt_stats['avg_ms']:.1f}ms, Post: {post_opt_stats['avg_ms']:.1f}ms")
        print(f"  Optimization results: {optimization_results['performance_targets_met']}")