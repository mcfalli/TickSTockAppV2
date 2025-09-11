"""
Test Suite for UniversalWebSocketManager (Layer 1)
Sprint 25 Week 1 - Foundation service layer tests

Tests the core WebSocket subscription management layer with
integrated 4-layer architecture components.
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, Set

from src.core.services.websocket_subscription_manager import (
    UniversalWebSocketManager, 
    WebSocketMetrics,
    UserSubscription
)
from src.infrastructure.websocket.subscription_index_manager import SubscriptionIndexManager
from src.infrastructure.websocket.scalable_broadcaster import ScalableBroadcaster
from src.infrastructure.websocket.event_router import EventRouter
from src.presentation.websocket.manager import WebSocketManager
from src.core.services.websocket_broadcaster import WebSocketBroadcaster


@pytest.fixture
def mock_socketio():
    """Mock SocketIO server."""
    mock = Mock()
    mock.server = Mock()
    mock.server.enter_room = Mock()
    mock.server.leave_room = Mock()
    mock.emit = Mock()
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = Mock()
    return mock


@pytest.fixture
def mock_existing_ws_manager():
    """Mock existing WebSocket manager."""
    mock = Mock(spec=WebSocketManager)
    mock.is_user_connected.return_value = True
    mock.get_user_connections.return_value = ['conn_123']
    mock.get_connected_users.return_value = ['user1', 'user2']
    return mock


@pytest.fixture
def mock_websocket_broadcaster():
    """Mock WebSocket broadcaster."""
    mock = Mock(spec=WebSocketBroadcaster)
    return mock


@pytest.fixture
def universal_ws_manager(mock_socketio, mock_redis, mock_existing_ws_manager, mock_websocket_broadcaster):
    """Create UniversalWebSocketManager with all dependencies."""
    manager = UniversalWebSocketManager(
        socketio=mock_socketio,
        redis_client=mock_redis,
        existing_websocket_manager=mock_existing_ws_manager,
        websocket_broadcaster=mock_websocket_broadcaster
    )
    return manager


class TestUniversalWebSocketManagerLayer:
    """Test UniversalWebSocketManager as Layer 1 foundation service."""

    def test_initialization_with_4_layers(self, universal_ws_manager):
        """Test initialization creates all 4 layers correctly."""
        # Verify 4-layer architecture components are initialized
        assert universal_ws_manager.index_manager is not None
        assert isinstance(universal_ws_manager.index_manager, SubscriptionIndexManager)
        
        assert universal_ws_manager.broadcaster is not None
        assert isinstance(universal_ws_manager.broadcaster, ScalableBroadcaster)
        
        assert universal_ws_manager.event_router is not None
        assert isinstance(universal_ws_manager.event_router, EventRouter)
        
        # Verify integration between layers
        assert universal_ws_manager.scalable_broadcaster is universal_ws_manager.broadcaster
        assert universal_ws_manager.event_router.scalable_broadcaster is universal_ws_manager.broadcaster

    def test_subscribe_user_with_indexing_integration(self, universal_ws_manager):
        """Test user subscription integrates with SubscriptionIndexManager."""
        user_id = "test_user_001"
        subscription_type = "tier_patterns"
        filters = {
            'pattern_types': ['BreakoutBO', 'TrendReversal'],
            'symbols': ['AAPL', 'TSLA'],
            'tiers': ['daily', 'intraday'],
            'confidence_min': 0.7
        }
        
        # Subscribe user
        success = universal_ws_manager.subscribe_user(user_id, subscription_type, filters)
        
        # Verify subscription success
        assert success is True
        
        # Verify user is stored in subscription manager
        assert user_id in universal_ws_manager.user_subscriptions
        assert subscription_type in universal_ws_manager.user_subscriptions[user_id]
        
        # Verify subscription was added to index manager
        user_subscription = universal_ws_manager.user_subscriptions[user_id][subscription_type]
        assert user_subscription.user_id == user_id
        assert user_subscription.subscription_type == subscription_type
        assert user_subscription.filters == filters
        
        # Verify room join was attempted
        universal_ws_manager.socketio.server.enter_room.assert_called_with('conn_123', f'user_{user_id}')

    def test_broadcast_event_with_4_layer_routing(self, universal_ws_manager):
        """Test event broadcasting uses complete 4-layer architecture."""
        # Setup user subscription first
        user_id = "broadcast_test_user"
        universal_ws_manager.subscribe_user(user_id, "tier_patterns", {
            'pattern_types': ['BreakoutBO'],
            'symbols': ['AAPL']
        })
        
        # Mock finding interested users from index manager
        with patch.object(universal_ws_manager, '_find_interested_users') as mock_find:
            mock_find.return_value = {user_id}
            
            # Mock event router routing
            mock_routing_result = Mock()
            mock_routing_result.total_users = 1
            mock_routing_result.matched_rules = ['test_rule']
            mock_routing_result.routing_time_ms = 15.0
            mock_routing_result.cache_hit = False
            
            with patch.object(universal_ws_manager.event_router, 'route_event') as mock_route:
                mock_route.return_value = mock_routing_result
                
                # Broadcast event
                delivery_count = universal_ws_manager.broadcast_event(
                    event_type='tier_pattern',
                    event_data={
                        'pattern_type': 'BreakoutBO',
                        'symbol': 'AAPL',
                        'confidence': 0.85,
                        'tier': 'daily'
                    },
                    targeting_criteria={
                        'subscription_type': 'tier_patterns',
                        'pattern_type': 'BreakoutBO',
                        'symbol': 'AAPL'
                    }
                )
                
                # Verify delivery count
                assert delivery_count == 1
                
                # Verify event router was called
                mock_route.assert_called_once()
                
                # Verify metrics were updated
                assert universal_ws_manager.metrics.events_broadcast > 0

    def test_user_filtering_performance_target(self, universal_ws_manager):
        """Test user filtering meets <5ms performance target."""
        # Setup multiple users with various subscriptions
        users = []
        for i in range(100):
            user_id = f"perf_user_{i:03d}"
            users.append(user_id)
            universal_ws_manager.subscribe_user(user_id, "tier_patterns", {
                'pattern_types': ['BreakoutBO', 'TrendReversal'],
                'symbols': ['AAPL', 'MSFT', 'GOOGL'][i % 3],
                'tiers': ['daily', 'intraday'],
                'confidence_min': 0.6 + (i % 4) * 0.1
            })
        
        # Test filtering performance
        start_time = time.time()
        
        interested_users = universal_ws_manager._find_interested_users({
            'subscription_type': 'tier_patterns',
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL',
            'confidence': 0.8
        })
        
        filtering_time_ms = (time.time() - start_time) * 1000
        
        # Verify performance target <5ms
        assert filtering_time_ms < 5.0, f"Filtering took {filtering_time_ms:.2f}ms, exceeds 5ms target"
        
        # Verify we found relevant users
        assert len(interested_users) > 0
        assert isinstance(interested_users, set)

    def test_metrics_tracking_comprehensive(self, universal_ws_manager):
        """Test comprehensive metrics tracking across all layers."""
        # Subscribe multiple users
        for i in range(5):
            universal_ws_manager.subscribe_user(f"metrics_user_{i}", "tier_patterns", {
                'pattern_types': ['BreakoutBO'],
                'symbols': ['AAPL']
            })
        
        # Broadcast events to generate metrics
        with patch.object(universal_ws_manager, '_find_interested_users') as mock_find:
            mock_find.return_value = {f"metrics_user_{i}" for i in range(5)}
            
            mock_routing_result = Mock()
            mock_routing_result.total_users = 5
            mock_routing_result.matched_rules = ['test_rule']
            mock_routing_result.routing_time_ms = 10.0
            mock_routing_result.cache_hit = True
            
            with patch.object(universal_ws_manager.event_router, 'route_event') as mock_route:
                mock_route.return_value = mock_routing_result
                
                # Broadcast multiple events
                for i in range(3):
                    universal_ws_manager.broadcast_event(
                        event_type='tier_pattern',
                        event_data={'pattern_type': 'BreakoutBO', 'symbol': 'AAPL'},
                        targeting_criteria={'subscription_type': 'tier_patterns'}
                    )
        
        # Get comprehensive statistics
        stats = universal_ws_manager.get_subscription_stats()
        
        # Verify layer-specific metrics are included
        assert 'index_lookup_count' in stats
        assert 'index_avg_lookup_ms' in stats
        assert 'index_cache_hit_rate' in stats
        
        assert 'broadcast_events_delivered' in stats
        assert 'broadcast_avg_latency_ms' in stats
        assert 'broadcast_success_rate' in stats
        
        assert 'routing_total_events' in stats
        assert 'routing_avg_time_ms' in stats
        assert 'routing_cache_hit_rate' in stats
        
        # Verify overall metrics
        assert stats['total_users'] == 5
        assert stats['events_broadcast'] == 3
        assert stats['events_delivered'] == 15  # 3 events * 5 users

    def test_health_status_4_layer_integration(self, universal_ws_manager):
        """Test health status incorporates all 4 layers."""
        # Mock broadcaster health status
        mock_broadcaster_health = {
            'status': 'healthy',
            'message': 'Broadcasting performance within targets'
        }
        
        with patch.object(universal_ws_manager.scalable_broadcaster, 'get_health_status') as mock_health:
            mock_health.return_value = mock_broadcaster_health
            
            health_status = universal_ws_manager.get_health_status()
            
            # Verify health status structure
            assert 'status' in health_status
            assert 'message' in health_status
            assert 'stats' in health_status
            assert 'broadcaster_health' in health_status
            assert 'performance_targets' in health_status
            
            # Verify performance targets include all layers
            targets = health_status['performance_targets']
            assert 'filtering_target_ms' in targets
            assert 'broadcast_target_ms' in targets
            assert 'target_concurrent_users' in targets
            
            assert targets['filtering_target_ms'] == 5.0
            assert targets['broadcast_target_ms'] == 100.0
            assert targets['target_concurrent_users'] == 500

    def test_connection_lifecycle_integration(self, universal_ws_manager):
        """Test user connection/disconnection integrates with all layers."""
        user_id = "lifecycle_test_user"
        connection_id = "conn_lifecycle_123"
        
        # Subscribe user first
        universal_ws_manager.subscribe_user(user_id, "tier_patterns", {
            'pattern_types': ['BreakoutBO'],
            'symbols': ['AAPL']
        })
        
        # Test connection handling
        universal_ws_manager.handle_user_connection(user_id, connection_id)
        
        # Verify room join
        universal_ws_manager.socketio.server.enter_room.assert_called_with(
            connection_id, f'user_{user_id}'
        )
        
        # Verify subscription status emission
        universal_ws_manager.socketio.emit.assert_called()
        emit_call = universal_ws_manager.socketio.emit.call_args
        assert emit_call[0][0] == 'subscription_status'
        assert 'active_subscriptions' in emit_call[0][1]
        assert 'tier_patterns' in emit_call[0][1]['active_subscriptions']
        
        # Test disconnection handling
        universal_ws_manager.handle_user_disconnection(user_id, connection_id)
        
        # Verify metrics are updated
        assert universal_ws_manager.metrics.total_connections > 0

    def test_performance_optimization_all_layers(self, universal_ws_manager):
        """Test performance optimization affects all 4 layers."""
        # Mock optimization results from each layer
        mock_index_optimization = {'indexes_optimized': 10, 'cache_cleaned': 5}
        mock_broadcast_optimization = {'batches_flushed': 3, 'performance_improved': True}
        mock_routing_optimization = {'cache_cleaned': 8, 'rules_optimized': 15}
        
        with patch.object(universal_ws_manager.index_manager, 'optimize_indexes') as mock_idx_opt, \
             patch.object(universal_ws_manager.scalable_broadcaster, 'optimize_performance') as mock_broadcast_opt, \
             patch.object(universal_ws_manager.event_router, 'optimize_performance') as mock_routing_opt:
            
            mock_idx_opt.return_value = mock_index_optimization
            mock_broadcast_opt.return_value = mock_broadcast_optimization
            mock_routing_opt.return_value = mock_routing_optimization
            
            # Run optimization
            optimization_results = universal_ws_manager.optimize_performance()
            
            # Verify all layers were optimized
            mock_idx_opt.assert_called_once()
            mock_broadcast_opt.assert_called_once()
            mock_routing_opt.assert_called_once()
            
            # Verify results include all layer optimizations
            assert 'index_optimization' in optimization_results
            assert 'broadcast_optimization' in optimization_results
            assert 'routing_optimization' in optimization_results
            assert 'current_performance' in optimization_results
            assert 'performance_targets_met' in optimization_results

    def test_thread_safety_layer_integration(self, universal_ws_manager):
        """Test thread safety across all 4 layers."""
        results = {'success_count': 0, 'errors': []}
        
        def subscribe_user_worker(thread_id):
            """Worker function for concurrent subscription testing."""
            try:
                for i in range(10):
                    user_id = f"thread_{thread_id}_user_{i}"
                    success = universal_ws_manager.subscribe_user(user_id, "tier_patterns", {
                        'pattern_types': ['BreakoutBO'],
                        'symbols': ['AAPL'],
                        'confidence_min': 0.7
                    })
                    if success:
                        results['success_count'] += 1
                    
                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
                    
            except Exception as e:
                results['errors'].append(str(e))
        
        def broadcast_worker():
            """Worker function for concurrent broadcasting."""
            try:
                for i in range(5):
                    with patch.object(universal_ws_manager, '_find_interested_users') as mock_find:
                        mock_find.return_value = {f"thread_0_user_{i}"}
                        
                        mock_routing_result = Mock()
                        mock_routing_result.total_users = 1
                        mock_routing_result.matched_rules = ['test_rule']
                        mock_routing_result.routing_time_ms = 5.0
                        mock_routing_result.cache_hit = False
                        
                        with patch.object(universal_ws_manager.event_router, 'route_event') as mock_route:
                            mock_route.return_value = mock_routing_result
                            
                            universal_ws_manager.broadcast_event(
                                event_type='tier_pattern',
                                event_data={'pattern_type': 'BreakoutBO', 'symbol': 'AAPL'},
                                targeting_criteria={'subscription_type': 'tier_patterns'}
                            )
                    
                    time.sleep(0.002)
                    
            except Exception as e:
                results['errors'].append(str(e))
        
        # Create and start threads
        threads = []
        
        # Subscription threads
        for i in range(3):
            thread = threading.Thread(target=subscribe_user_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Broadcasting thread
        broadcast_thread = threading.Thread(target=broadcast_worker)
        threads.append(broadcast_thread)
        broadcast_thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify no errors occurred
        assert len(results['errors']) == 0, f"Thread safety errors: {results['errors']}"
        
        # Verify expected number of successful subscriptions
        assert results['success_count'] == 30  # 3 threads * 10 users each
        
        # Verify internal consistency
        total_users = len(universal_ws_manager.user_subscriptions)
        assert total_users == 30

    @pytest.mark.performance
    def test_500_concurrent_users_capacity(self, universal_ws_manager):
        """Test system can handle 500+ concurrent user subscriptions."""
        start_time = time.time()
        successful_subscriptions = 0
        
        # Subscribe 500 users
        for i in range(500):
            user_id = f"capacity_user_{i:03d}"
            success = universal_ws_manager.subscribe_user(user_id, "tier_patterns", {
                'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'][i % 5],
                'tiers': ['daily', 'intraday'],
                'confidence_min': 0.6 + (i % 4) * 0.1
            })
            
            if success:
                successful_subscriptions += 1
        
        subscription_time = time.time() - start_time
        
        # Verify capacity targets
        assert successful_subscriptions >= 500, f"Only {successful_subscriptions}/500 subscriptions successful"
        assert subscription_time < 10.0, f"Subscription time {subscription_time:.2f}s exceeds 10s target"
        
        # Verify system performance under load
        stats = universal_ws_manager.get_subscription_stats()
        assert stats['total_users'] >= 500
        assert stats['total_subscriptions'] >= 500
        
        # Test filtering performance with 500+ users
        filter_start = time.time()
        interested_users = universal_ws_manager._find_interested_users({
            'subscription_type': 'tier_patterns',
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL'
        })
        filter_time_ms = (time.time() - filter_start) * 1000
        
        # Verify filtering performance remains under target
        assert filter_time_ms < 5.0, f"Filtering with 500 users took {filter_time_ms:.2f}ms"
        assert len(interested_users) > 0

    def test_cleanup_inactive_subscriptions_integration(self, universal_ws_manager):
        """Test cleanup integrates with all layers properly."""
        # Create some subscriptions
        test_users = []
        for i in range(10):
            user_id = f"cleanup_user_{i}"
            test_users.append(user_id)
            universal_ws_manager.subscribe_user(user_id, "tier_patterns", {
                'pattern_types': ['BreakoutBO'],
                'symbols': ['AAPL']
            })
        
        # Mock some users as disconnected
        def mock_is_connected(user_id):
            return user_id not in ['cleanup_user_5', 'cleanup_user_6', 'cleanup_user_7']
        
        universal_ws_manager.existing_ws_manager.is_user_connected.side_effect = mock_is_connected
        
        # Mock index manager cleanup
        with patch.object(universal_ws_manager.index_manager, 'cleanup_stale_entries') as mock_cleanup:
            mock_cleanup.return_value = 5
            
            # Run cleanup with short max_inactive_hours for testing
            cleaned_count = universal_ws_manager.cleanup_inactive_subscriptions(max_inactive_hours=0)
            
            # Verify cleanup was called on index manager
            mock_cleanup.assert_called_once_with(0)
            
            # Verify some subscriptions were cleaned
            assert cleaned_count >= 5  # At least the index manager cleanup count
            
            # Verify user count decreased
            current_users = len(universal_ws_manager.user_subscriptions)
            assert current_users < 10  # Some users should be removed

    def test_error_handling_layer_resilience(self, universal_ws_manager):
        """Test error handling doesn't cascade across layers."""
        # Test index manager failure doesn't break subscription
        with patch.object(universal_ws_manager.index_manager, 'add_subscription') as mock_add_index:
            mock_add_index.side_effect = Exception("Index manager error")
            
            # Subscription should still work despite index manager failure
            success = universal_ws_manager.subscribe_user("error_user", "tier_patterns", {
                'pattern_types': ['BreakoutBO'],
                'symbols': ['AAPL']
            })
            
            # Should gracefully handle the error
            assert success is True  # Core subscription still works
            assert universal_ws_manager.metrics.subscription_errors == 0  # Error was handled
        
        # Test event router failure doesn't break broadcasting
        with patch.object(universal_ws_manager.event_router, 'route_event') as mock_route:
            mock_route.side_effect = Exception("Router error")
            
            with patch.object(universal_ws_manager, '_find_interested_users') as mock_find:
                mock_find.return_value = {"error_user"}
                
                # Broadcasting should handle router errors gracefully
                delivery_count = universal_ws_manager.broadcast_event(
                    event_type='tier_pattern',
                    event_data={'pattern_type': 'BreakoutBO'},
                    targeting_criteria={'subscription_type': 'tier_patterns'}
                )
                
                # Should return 0 but not crash
                assert delivery_count == 0
                assert universal_ws_manager.metrics.broadcast_errors > 0

    def test_default_routing_rules_initialization(self, universal_ws_manager):
        """Test default routing rules are properly initialized."""
        # Verify event router has routing rules
        routing_stats = universal_ws_manager.get_routing_stats()
        
        # Should have some default rules configured
        assert routing_stats['total_rules'] > 0
        
        # Verify rule categories exist
        assert 'rule_usage' in routing_stats
        
        # Test adding custom routing rule
        mock_rule = Mock()
        mock_rule.rule_id = 'test_custom_rule'
        
        success = universal_ws_manager.add_custom_routing_rule(mock_rule)
        assert success is True
        
        # Test removing routing rule
        success = universal_ws_manager.remove_routing_rule('test_custom_rule')
        assert success is True

    def test_unsubscribe_user_layer_cleanup(self, universal_ws_manager):
        """Test unsubscribing user cleans up all layers properly."""
        user_id = "unsubscribe_test_user"
        
        # Subscribe user
        universal_ws_manager.subscribe_user(user_id, "tier_patterns", {
            'pattern_types': ['BreakoutBO'],
            'symbols': ['AAPL']
        })
        
        # Verify user exists in subscription manager
        assert user_id in universal_ws_manager.user_subscriptions
        
        # Mock index manager removal
        with patch.object(universal_ws_manager.index_manager, 'remove_subscription') as mock_remove:
            # Unsubscribe user
            success = universal_ws_manager.unsubscribe_user(user_id)
            
            # Verify unsubscription was successful
            assert success is True
            
            # Verify user was removed from subscription manager
            assert user_id not in universal_ws_manager.user_subscriptions
            
            # Verify index manager cleanup was called
            mock_remove.assert_called_once_with(user_id, None)
            
            # Verify room leave was attempted
            universal_ws_manager.socketio.server.leave_room.assert_called()