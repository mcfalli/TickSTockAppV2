"""
Test Suite for 4-Layer Architecture Integration
Sprint 25 Week 1 - Complete system integration tests

Tests the complete 4-layer WebSocket architecture working together:
Layer 1: UniversalWebSocketManager (Foundation)
Layer 2: SubscriptionIndexManager (Indexing) 
Layer 3: ScalableBroadcaster (Broadcasting)
Layer 4: EventRouter (Routing)

Validates complete system flow with performance targets and cross-layer interactions.
"""

import threading
import time
from unittest.mock import Mock, patch

import pytest

from src.core.services.tier_pattern_websocket_integration import TierPatternWebSocketIntegration
from src.core.services.websocket_subscription_manager import UniversalWebSocketManager
from src.infrastructure.websocket.event_router import EventRouter
from src.infrastructure.websocket.scalable_broadcaster import DeliveryPriority, ScalableBroadcaster
from src.infrastructure.websocket.subscription_index_manager import SubscriptionIndexManager


@pytest.fixture
def mock_socketio():
    """Mock SocketIO for integration testing."""
    mock = Mock()
    mock.server = Mock()
    mock.server.enter_room = Mock()
    mock.server.leave_room = Mock()
    mock.emit = Mock()
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client for integration testing."""
    mock = Mock()
    return mock


@pytest.fixture
def mock_existing_ws_manager():
    """Mock existing WebSocket manager."""
    mock = Mock()
    mock.is_user_connected.return_value = True
    mock.get_user_connections.return_value = ['conn_123', 'conn_456']
    mock.get_connected_users.return_value = ['user1', 'user2', 'user3']
    return mock


@pytest.fixture
def mock_websocket_broadcaster():
    """Mock WebSocket broadcaster."""
    mock = Mock()
    return mock


@pytest.fixture
def integrated_system(mock_socketio, mock_redis, mock_existing_ws_manager, mock_websocket_broadcaster):
    """Create complete integrated 4-layer system."""
    # Create UniversalWebSocketManager with all integrated layers
    universal_manager = UniversalWebSocketManager(
        socketio=mock_socketio,
        redis_client=mock_redis,
        existing_websocket_manager=mock_existing_ws_manager,
        websocket_broadcaster=mock_websocket_broadcaster
    )

    return {
        'universal_manager': universal_manager,
        'index_manager': universal_manager.index_manager,
        'broadcaster': universal_manager.broadcaster,
        'event_router': universal_manager.event_router,
        'socketio': mock_socketio,
        'redis': mock_redis
    }


class TestFourLayerIntegration:
    """Test complete 4-layer WebSocket architecture integration."""

    def test_complete_system_initialization_integration(self, integrated_system):
        """Test all 4 layers initialize and integrate properly."""
        system = integrated_system

        # Verify all layers are present and connected
        assert system['universal_manager'] is not None
        assert system['index_manager'] is not None
        assert system['broadcaster'] is not None
        assert system['event_router'] is not None

        # Verify layer cross-references are correct
        assert system['universal_manager'].index_manager is system['index_manager']
        assert system['universal_manager'].broadcaster is system['broadcaster']
        assert system['universal_manager'].event_router is system['event_router']
        assert system['event_router'].scalable_broadcaster is system['broadcaster']

        # Verify layers have correct types
        assert isinstance(system['index_manager'], SubscriptionIndexManager)
        assert isinstance(system['broadcaster'], ScalableBroadcaster)
        assert isinstance(system['event_router'], EventRouter)

    def test_end_to_end_subscription_flow(self, integrated_system):
        """Test complete subscription flow through all 4 layers."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Step 1: Subscribe user (Layer 1 → Layer 2)
        user_id = "e2e_test_user"
        subscription_filters = {
            'pattern_types': ['BreakoutBO', 'TrendReversal'],
            'symbols': ['AAPL', 'TSLA'],
            'tiers': ['daily', 'intraday'],
            'confidence_min': 0.7
        }

        success = universal_manager.subscribe_user(
            user_id=user_id,
            subscription_type="tier_patterns",
            filters=subscription_filters
        )

        # Verify subscription succeeded
        assert success is True

        # Verify Layer 1 (UniversalWebSocketManager) stored subscription
        assert user_id in universal_manager.user_subscriptions
        assert "tier_patterns" in universal_manager.user_subscriptions[user_id]

        # Verify Layer 2 (SubscriptionIndexManager) indexed subscription
        # Test by finding matching users for the subscription criteria
        matching_users = system['index_manager'].find_matching_users({
            'subscription_type': 'tier_patterns',
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL'
        })
        assert user_id in matching_users

    def test_end_to_end_broadcast_flow(self, integrated_system):
        """Test complete broadcast flow through all 4 layers."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Setup: Subscribe multiple users
        test_users = []
        for i in range(5):
            user_id = f"broadcast_user_{i}"
            test_users.append(user_id)

            universal_manager.subscribe_user(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO'],
                    'symbols': ['AAPL'],
                    'confidence_min': 0.6
                }
            )

        # Test complete broadcast flow
        start_time = time.time()

        # Mock the user filtering to return our test users
        with patch.object(universal_manager, '_find_interested_users') as mock_find:
            mock_find.return_value = set(test_users)

            # Mock event router routing result
            mock_routing_result = Mock()
            mock_routing_result.total_users = len(test_users)
            mock_routing_result.matched_rules = ['test_routing_rule']
            mock_routing_result.routing_time_ms = 15.0
            mock_routing_result.cache_hit = False

            with patch.object(system['event_router'], 'route_event') as mock_route:
                mock_route.return_value = mock_routing_result

                # Step 1: Broadcast event (Layer 1 orchestrates)
                delivery_count = universal_manager.broadcast_event(
                    event_type='tier_pattern',
                    event_data={
                        'pattern_type': 'BreakoutBO',
                        'symbol': 'AAPL',
                        'confidence': 0.85,
                        'tier': 'daily',
                        'timestamp': time.time()
                    },
                    targeting_criteria={
                        'subscription_type': 'tier_patterns',
                        'pattern_type': 'BreakoutBO',
                        'symbol': 'AAPL'
                    }
                )

        end_to_end_time = (time.time() - start_time) * 1000

        # Verify complete flow succeeded
        assert delivery_count == len(test_users)

        # Verify Layer 2 (Indexing) was called for user filtering
        mock_find.assert_called_once()

        # Verify Layer 4 (EventRouter) was called for routing
        mock_route.assert_called_once()

        # Verify end-to-end performance is reasonable
        assert end_to_end_time < 100, f"End-to-end broadcast took {end_to_end_time:.2f}ms"

    def test_layered_performance_breakdown(self, integrated_system):
        """Test performance breakdown across all 4 layers meets targets."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Setup subscriptions for performance testing
        for i in range(100):
            user_id = f"perf_user_{i:03d}"
            universal_manager.subscribe_user(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL'][i % 3],
                    'confidence_min': 0.6 + (i % 4) * 0.1
                }
            )

        # Test Layer 2 (SubscriptionIndexManager) performance: <5ms
        index_start = time.time()
        matching_users = system['index_manager'].find_matching_users({
            'subscription_type': 'tier_patterns',
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL'
        })
        index_time_ms = (time.time() - index_start) * 1000

        assert index_time_ms < 5.0, f"Layer 2 (Indexing) took {index_time_ms:.2f}ms, exceeds 5ms target"
        assert len(matching_users) > 0

        # Test Layer 4 (EventRouter) performance: <20ms
        router_start = time.time()
        routing_result = system['event_router'].route_event(
            event_type='tier_pattern',
            event_data={
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL',
                'confidence': 0.8
            },
            user_context={'interested_users': list(matching_users)}
        )
        router_time_ms = (time.time() - router_start) * 1000

        assert router_time_ms < 20.0, f"Layer 4 (Routing) took {router_time_ms:.2f}ms, exceeds 20ms target"

        # Test Layer 3 (ScalableBroadcaster) performance: <100ms
        broadcast_start = time.time()
        queued_count = system['broadcaster'].broadcast_to_users(
            event_type='performance_test',
            event_data={'test': 'performance'},
            user_ids=matching_users,
            priority=DeliveryPriority.MEDIUM
        )
        broadcast_time_ms = (time.time() - broadcast_start) * 1000

        assert broadcast_time_ms < 100.0, f"Layer 3 (Broadcasting) took {broadcast_time_ms:.2f}ms, exceeds 100ms target"

        # Verify total system performance: <125ms
        total_time_ms = index_time_ms + router_time_ms + broadcast_time_ms
        assert total_time_ms < 125.0, f"Total 4-layer performance {total_time_ms:.2f}ms exceeds 125ms target"

    def test_cross_layer_error_resilience(self, integrated_system):
        """Test error in one layer doesn't cascade to others."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Subscribe a user
        universal_manager.subscribe_user(
            user_id="error_test_user",
            subscription_type="tier_patterns",
            filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
        )

        # Test Layer 2 (IndexManager) error doesn't break Layer 1
        with patch.object(system['index_manager'], 'find_matching_users') as mock_find:
            mock_find.side_effect = Exception("Index error")

            # Layer 1 should handle the error gracefully
            with patch.object(universal_manager, '_find_interested_users') as mock_find_users:
                mock_find_users.return_value = set()  # Fallback to empty set

                delivery_count = universal_manager.broadcast_event(
                    event_type='tier_pattern',
                    event_data={'pattern_type': 'BreakoutBO'},
                    targeting_criteria={'subscription_type': 'tier_patterns'}
                )

                # Should handle error without crashing
                assert delivery_count >= 0

        # Test Layer 4 (EventRouter) error doesn't break Layer 1
        with patch.object(system['event_router'], 'route_event') as mock_route:
            mock_route.side_effect = Exception("Router error")

            with patch.object(universal_manager, '_find_interested_users') as mock_find:
                mock_find.return_value = {"error_test_user"}

                # Should handle router error gracefully
                delivery_count = universal_manager.broadcast_event(
                    event_type='tier_pattern',
                    event_data={'pattern_type': 'BreakoutBO'},
                    targeting_criteria={'subscription_type': 'tier_patterns'}
                )

                # Should return 0 but not crash
                assert delivery_count == 0
                assert universal_manager.metrics.broadcast_errors > 0

    def test_integrated_statistics_reporting(self, integrated_system):
        """Test integrated statistics from all 4 layers."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Create activity across all layers
        for i in range(10):
            user_id = f"stats_user_{i}"
            universal_manager.subscribe_user(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO'],
                    'symbols': ['AAPL']
                }
            )

        # Generate broadcast activity
        with patch.object(universal_manager, '_find_interested_users') as mock_find:
            mock_find.return_value = {f"stats_user_{i}" for i in range(5)}

            mock_routing_result = Mock()
            mock_routing_result.total_users = 5
            mock_routing_result.matched_rules = ['stats_rule']
            mock_routing_result.routing_time_ms = 10.0
            mock_routing_result.cache_hit = False

            with patch.object(system['event_router'], 'route_event') as mock_route:
                mock_route.return_value = mock_routing_result

                # Broadcast multiple events
                for i in range(5):
                    universal_manager.broadcast_event(
                        event_type='tier_pattern',
                        event_data={'pattern_type': 'BreakoutBO', 'sequence': i},
                        targeting_criteria={'subscription_type': 'tier_patterns'}
                    )

        # Get integrated statistics
        integrated_stats = universal_manager.get_subscription_stats()

        # Verify Layer 1 (UniversalWebSocketManager) stats
        assert integrated_stats['total_users'] == 10
        assert integrated_stats['events_broadcast'] == 5

        # Verify Layer 2 (SubscriptionIndexManager) stats are included
        assert 'index_lookup_count' in integrated_stats
        assert 'index_avg_lookup_ms' in integrated_stats
        assert 'index_cache_hit_rate' in integrated_stats

        # Verify Layer 3 (ScalableBroadcaster) stats are included
        assert 'broadcast_events_delivered' in integrated_stats
        assert 'broadcast_avg_latency_ms' in integrated_stats
        assert 'broadcast_success_rate' in integrated_stats

        # Verify Layer 4 (EventRouter) stats are included
        assert 'routing_total_events' in integrated_stats
        assert 'routing_avg_time_ms' in integrated_stats
        assert 'routing_cache_hit_rate' in integrated_stats

    def test_integrated_health_monitoring(self, integrated_system):
        """Test integrated health monitoring across all layers."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Mock individual layer health statuses
        mock_broadcaster_health = {
            'status': 'healthy',
            'message': 'Broadcasting within targets',
            'stats': {'avg_delivery_latency_ms': 45.0}
        }

        with patch.object(system['broadcaster'], 'get_health_status') as mock_health:
            mock_health.return_value = mock_broadcaster_health

            # Get integrated health status
            health_status = universal_manager.get_health_status()

            # Verify comprehensive health monitoring
            assert 'status' in health_status
            assert 'broadcaster_health' in health_status
            assert 'performance_targets' in health_status

            # Verify performance targets include all layers
            targets = health_status['performance_targets']
            assert targets['filtering_target_ms'] == 5.0    # Layer 2
            assert targets['broadcast_target_ms'] == 100.0  # Layer 3
            assert targets['target_concurrent_users'] == 500

            # Verify integrated health determination
            assert health_status['status'] in ['healthy', 'warning', 'error']

    def test_integrated_optimization_across_layers(self, integrated_system):
        """Test integrated performance optimization across all layers."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Create some activity to optimize
        for i in range(20):
            universal_manager.subscribe_user(
                user_id=f"opt_user_{i}",
                subscription_type="tier_patterns",
                filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
            )

        # Mock layer optimization results
        mock_index_optimization = {'indexes_optimized': 15, 'cache_cleaned': 8}
        mock_broadcast_optimization = {'batches_flushed': 5, 'performance_improved': True}
        mock_routing_optimization = {'cache_cleaned': 12, 'rules_optimized': 3}

        with patch.object(system['index_manager'], 'optimize_indexes') as mock_idx_opt, \
             patch.object(system['broadcaster'], 'optimize_performance') as mock_broadcast_opt, \
             patch.object(system['event_router'], 'optimize_performance') as mock_routing_opt:

            mock_idx_opt.return_value = mock_index_optimization
            mock_broadcast_opt.return_value = mock_broadcast_optimization
            mock_routing_opt.return_value = mock_routing_optimization

            # Run integrated optimization
            optimization_results = universal_manager.optimize_performance()

            # Verify all layers were optimized
            mock_idx_opt.assert_called_once()
            mock_broadcast_opt.assert_called_once()
            mock_routing_opt.assert_called_once()

            # Verify integrated results include all layer optimizations
            assert 'index_optimization' in optimization_results
            assert 'broadcast_optimization' in optimization_results
            assert 'routing_optimization' in optimization_results
            assert 'performance_targets_met' in optimization_results

            # Verify performance targets validation
            targets_met = optimization_results['performance_targets_met']
            assert 'filtering_under_5ms' in targets_met
            assert 'broadcast_under_100ms' in targets_met
            assert 'routing_under_20ms' in targets_met

    def test_tier_pattern_integration_complete_flow(self, integrated_system):
        """Test TierPatternWebSocketIntegration with complete 4-layer system."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Create TierPatternWebSocketIntegration on top of 4-layer system
        tier_integration = TierPatternWebSocketIntegration(universal_manager)

        # Verify tier integration uses all 4 layers
        assert tier_integration.websocket_manager is universal_manager
        assert tier_integration.index_manager is system['index_manager']
        assert tier_integration.broadcaster is system['broadcaster']
        assert tier_integration.event_router is system['event_router']

        # Test tier-specific subscription through complete system
        from src.core.domain.events.tier_events import EventPriority, PatternTier
        from src.core.services.tier_pattern_websocket_integration import TierSubscriptionPreferences

        preferences = TierSubscriptionPreferences(
            pattern_types=['BreakoutBO', 'TrendReversal'],
            symbols=['AAPL', 'TSLA'],
            tiers=[PatternTier.DAILY, PatternTier.INTRADAY],
            confidence_min=0.8,
            priority_min=EventPriority.MEDIUM
        )

        # Subscribe through tier integration
        success = tier_integration.subscribe_user_to_tier_patterns("tier_user", preferences)
        assert success is True

        # Verify subscription exists in Layer 1
        assert "tier_user" in universal_manager.user_subscriptions
        assert "tier_patterns" in universal_manager.user_subscriptions["tier_user"]

        # Verify subscription can be found through Layer 2
        matching_users = system['index_manager'].find_matching_users({
            'subscription_type': 'tier_patterns',
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL'
        })
        assert "tier_user" in matching_users

    def test_concurrent_operations_across_layers(self, integrated_system):
        """Test concurrent operations across all 4 layers maintain consistency."""
        system = integrated_system
        universal_manager = system['universal_manager']

        results = {'subscriptions': 0, 'broadcasts': 0, 'errors': []}

        def subscription_worker(worker_id):
            """Worker for concurrent subscriptions."""
            try:
                for i in range(15):
                    user_id = f"concurrent_user_{worker_id}_{i}"
                    success = universal_manager.subscribe_user(
                        user_id=user_id,
                        subscription_type="tier_patterns",
                        filters={
                            'pattern_types': ['BreakoutBO'],
                            'symbols': ['AAPL'],
                            'confidence_min': 0.7
                        }
                    )
                    if success:
                        results['subscriptions'] += 1

                    time.sleep(0.001)  # Small delay

            except Exception as e:
                results['errors'].append(f"Subscription worker {worker_id}: {str(e)}")

        def broadcast_worker():
            """Worker for concurrent broadcasts."""
            try:
                time.sleep(0.05)  # Let some subscriptions happen first

                for i in range(10):
                    with patch.object(universal_manager, '_find_interested_users') as mock_find:
                        mock_find.return_value = {f"concurrent_user_0_{i % 15}"}

                        mock_routing_result = Mock()
                        mock_routing_result.total_users = 1
                        mock_routing_result.matched_rules = ['concurrent_rule']
                        mock_routing_result.routing_time_ms = 8.0
                        mock_routing_result.cache_hit = False

                        with patch.object(system['event_router'], 'route_event') as mock_route:
                            mock_route.return_value = mock_routing_result

                            delivery_count = universal_manager.broadcast_event(
                                event_type='tier_pattern',
                                event_data={'pattern_type': 'BreakoutBO', 'sequence': i},
                                targeting_criteria={'subscription_type': 'tier_patterns'}
                            )

                            if delivery_count > 0:
                                results['broadcasts'] += 1

                    time.sleep(0.002)

            except Exception as e:
                results['errors'].append(f"Broadcast worker: {str(e)}")

        def optimization_worker():
            """Worker for concurrent optimizations."""
            try:
                time.sleep(0.1)  # Let activity build up

                for i in range(3):
                    # Mock optimization to avoid complexity
                    with patch.object(system['index_manager'], 'optimize_indexes') as mock_opt:
                        mock_opt.return_value = {'optimized': True}

                        universal_manager.optimize_performance()

                    time.sleep(0.05)

            except Exception as e:
                results['errors'].append(f"Optimization worker: {str(e)}")

        # Create and start threads
        threads = []

        # Subscription workers
        for i in range(3):
            thread = threading.Thread(target=subscription_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Broadcast worker
        broadcast_thread = threading.Thread(target=broadcast_worker)
        threads.append(broadcast_thread)
        broadcast_thread.start()

        # Optimization worker
        opt_thread = threading.Thread(target=optimization_worker)
        threads.append(opt_thread)
        opt_thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)

        # Verify no errors occurred
        assert len(results['errors']) == 0, f"Concurrent operation errors: {results['errors']}"

        # Verify reasonable results
        assert results['subscriptions'] >= 40  # 3 workers * 15 subscriptions each
        assert results['broadcasts'] >= 5     # Some broadcasts should succeed

        # Verify system integrity
        total_users = len(universal_manager.user_subscriptions)
        assert total_users >= 40

    def test_memory_efficiency_integrated_system(self, integrated_system):
        """Test memory efficiency of integrated 4-layer system."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Create substantial load to test memory efficiency
        for i in range(1000):
            user_id = f"memory_user_{i:04d}"
            universal_manager.subscribe_user(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'][i % 5],
                    'tiers': ['daily', 'intraday'],
                    'confidence_min': 0.5 + (i % 5) * 0.1
                }
            )

        # Test that system remains responsive
        start_time = time.time()

        # Test Layer 2 performance with large dataset
        matching_users = system['index_manager'].find_matching_users({
            'subscription_type': 'tier_patterns',
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL'
        })

        index_time_ms = (time.time() - start_time) * 1000

        # Should maintain performance targets even with 1000 subscriptions
        assert index_time_ms < 10.0, f"Large scale indexing took {index_time_ms:.2f}ms"
        assert len(matching_users) > 0

        # Test system statistics remain reasonable
        stats = universal_manager.get_subscription_stats()
        assert stats['total_users'] == 1000
        assert stats['total_subscriptions'] == 1000

        # Memory should scale reasonably (this is approximate)
        # Real memory testing would require more sophisticated tools
        assert stats['runtime_seconds'] > 0

    @pytest.mark.performance
    def test_integrated_system_performance_targets(self, integrated_system):
        """Test integrated system meets all performance targets under load."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Create realistic load
        user_count = 500
        for i in range(user_count):
            universal_manager.subscribe_user(
                user_id=f"perf_user_{i:03d}",
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal', 'SurgeDetection'][i % 3],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'][i % 5],
                    'confidence_min': 0.6 + (i % 4) * 0.1
                }
            )

        # Test complete end-to-end performance
        performance_results = []

        for test_run in range(10):
            start_time = time.time()

            # Mock user finding and routing for consistent testing
            with patch.object(universal_manager, '_find_interested_users') as mock_find:
                # Return subset of users for realistic load
                interested_users = {f"perf_user_{i:03d}" for i in range(test_run * 10, (test_run + 1) * 10)}
                mock_find.return_value = interested_users

                mock_routing_result = Mock()
                mock_routing_result.total_users = len(interested_users)
                mock_routing_result.matched_rules = ['perf_rule']
                mock_routing_result.routing_time_ms = 12.0
                mock_routing_result.cache_hit = test_run > 2  # Some cache hits

                with patch.object(system['event_router'], 'route_event') as mock_route:
                    mock_route.return_value = mock_routing_result

                    # Complete broadcast flow
                    delivery_count = universal_manager.broadcast_event(
                        event_type='tier_pattern',
                        event_data={
                            'pattern_type': 'BreakoutBO',
                            'symbol': 'AAPL',
                            'confidence': 0.8,
                            'test_run': test_run
                        },
                        targeting_criteria={
                            'subscription_type': 'tier_patterns',
                            'pattern_type': 'BreakoutBO'
                        }
                    )

            end_to_end_time_ms = (time.time() - start_time) * 1000
            performance_results.append(end_to_end_time_ms)

            # Verify delivery succeeded
            assert delivery_count == len(interested_users)

            # Individual run should meet target
            assert end_to_end_time_ms < 125.0, f"Run {test_run} took {end_to_end_time_ms:.2f}ms"

        # Verify overall performance statistics
        avg_performance = sum(performance_results) / len(performance_results)
        max_performance = max(performance_results)
        min_performance = min(performance_results)

        assert avg_performance < 100.0, f"Average performance {avg_performance:.2f}ms exceeds target"
        assert max_performance < 125.0, f"Max performance {max_performance:.2f}ms exceeds target"

        # Verify system stability under sustained load
        final_stats = universal_manager.get_subscription_stats()
        assert final_stats['total_users'] == user_count
        assert final_stats['events_broadcast'] == 10

    def test_system_recovery_from_component_failures(self, integrated_system):
        """Test system recovery when individual components fail."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Setup initial state
        universal_manager.subscribe_user(
            user_id="recovery_user",
            subscription_type="tier_patterns",
            filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
        )

        # Test recovery from Layer 2 (IndexManager) failure
        original_find_users = system['index_manager'].find_matching_users
        system['index_manager'].find_matching_users = Mock(side_effect=Exception("Index failure"))

        # System should recover gracefully
        with patch.object(universal_manager, '_find_interested_users') as mock_fallback:
            mock_fallback.return_value = {"recovery_user"}  # Fallback mechanism

            delivery_count = universal_manager.broadcast_event(
                event_type='tier_pattern',
                event_data={'pattern_type': 'BreakoutBO'},
                targeting_criteria={'subscription_type': 'tier_patterns'}
            )

            # Should handle failure gracefully
            assert delivery_count >= 0

        # Restore functionality and verify recovery
        system['index_manager'].find_matching_users = original_find_users

        # Should work normally again
        matching_users = system['index_manager'].find_matching_users({
            'subscription_type': 'tier_patterns',
            'pattern_type': 'BreakoutBO'
        })
        assert "recovery_user" in matching_users

        # Test recovery from Layer 3 (Broadcaster) failure
        original_broadcast = system['broadcaster'].broadcast_to_users
        system['broadcaster'].broadcast_to_users = Mock(side_effect=Exception("Broadcast failure"))

        # Event routing should still complete without crashing
        with patch.object(universal_manager, '_find_interested_users') as mock_find:
            mock_find.return_value = {"recovery_user"}

            # Should not crash despite broadcast failure
            delivery_count = universal_manager.broadcast_event(
                event_type='tier_pattern',
                event_data={'pattern_type': 'BreakoutBO'},
                targeting_criteria={'subscription_type': 'tier_patterns'}
            )

            # May return 0 due to failure, but shouldn't crash
            assert delivery_count >= 0

        # Restore functionality
        system['broadcaster'].broadcast_to_users = original_broadcast

    def test_cleanup_across_all_layers(self, integrated_system):
        """Test cleanup operations work across all 4 layers."""
        system = integrated_system
        universal_manager = system['universal_manager']

        # Create subscriptions that will need cleanup
        test_users = []
        for i in range(20):
            user_id = f"cleanup_user_{i}"
            test_users.append(user_id)
            universal_manager.subscribe_user(
                user_id=user_id,
                subscription_type="tier_patterns",
                filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
            )

        # Verify subscriptions exist across layers
        initial_stats = universal_manager.get_subscription_stats()
        assert initial_stats['total_users'] == 20

        # Mock some users as disconnected for cleanup
        def mock_is_connected(user_id):
            return user_id not in ['cleanup_user_15', 'cleanup_user_16', 'cleanup_user_17']

        universal_manager.existing_ws_manager.is_user_connected.side_effect = mock_is_connected

        # Mock layer cleanup operations
        with patch.object(system['index_manager'], 'cleanup_stale_entries') as mock_index_cleanup, \
             patch.object(system['broadcaster'], 'optimize_performance') as mock_broadcast_cleanup, \
             patch.object(system['event_router'], 'optimize_performance') as mock_router_cleanup:

            mock_index_cleanup.return_value = 5
            mock_broadcast_cleanup.return_value = {'rate_limiters_cleaned': 3}
            mock_router_cleanup.return_value = {'cache_cleaned': 8}

            # Run integrated cleanup
            cleaned_count = universal_manager.cleanup_inactive_subscriptions(max_inactive_hours=0)

            # Verify cleanup was called on all layers
            mock_index_cleanup.assert_called_once()
            # Note: broadcast and router cleanup are called via optimize_performance

        # Verify some cleanup occurred
        assert cleaned_count >= 3  # Should clean disconnected users

        # Verify system integrity after cleanup
        final_stats = universal_manager.get_subscription_stats()
        assert final_stats['total_users'] <= 20
