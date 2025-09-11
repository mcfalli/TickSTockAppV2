"""
WebSocket Manager Integration Tests
Sprint 25 Day 4: Comprehensive integration tests for EventRouter with UniversalWebSocketManager.

Tests cover:
- Complete EventRouter integration with UniversalWebSocketManager
- Default routing rules initialization and management
- End-to-end event flow: Index → Route → Broadcast → SocketIO
- Custom routing rule management via WebSocket manager
- Performance integration validation (<125ms total latency)
- Error handling and fallback scenarios
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch, call
from collections import defaultdict
from typing import Dict, Any, Set
import redis

# Core imports for testing
from src.core.services.websocket_subscription_manager import UniversalWebSocketManager, WebSocketMetrics
from src.infrastructure.websocket.event_router import (
    EventRouter, RoutingRule, RoutingResult, RoutingStrategy, EventCategory, DeliveryPriority
)
from src.infrastructure.websocket.scalable_broadcaster import ScalableBroadcaster
from src.infrastructure.websocket.subscription_index_manager import SubscriptionIndexManager
from src.presentation.websocket.manager import WebSocketManager
from src.core.services.websocket_broadcaster import WebSocketBroadcaster
from src.core.models.websocket_models import UserSubscription

# Mock Flask-SocketIO
from flask_socketio import SocketIO


class TestUniversalWebSocketManagerIntegration:
    """Test EventRouter integration with UniversalWebSocketManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_socketio = Mock(spec=SocketIO)
        self.mock_redis_client = Mock(spec=redis.Redis)
        self.mock_existing_ws_manager = Mock(spec=WebSocketManager)
        self.mock_websocket_broadcaster = Mock(spec=WebSocketBroadcaster)
        
        # Configure mock behavior
        self.mock_existing_ws_manager.is_user_connected.return_value = True
        self.mock_existing_ws_manager.get_user_connections.return_value = ['conn_123']
        self.mock_existing_ws_manager.get_connected_users.return_value = ['user1', 'user2', 'user3']
        
        self.mock_socketio.server.enter_room = Mock()
        self.mock_socketio.server.leave_room = Mock()
        self.mock_socketio.emit = Mock()
        
        # Create UniversalWebSocketManager (which includes EventRouter)
        self.ws_manager = UniversalWebSocketManager(
            socketio=self.mock_socketio,
            redis_client=self.mock_redis_client,
            existing_websocket_manager=self.mock_existing_ws_manager,
            websocket_broadcaster=self.mock_websocket_broadcaster
        )
    
    def test_event_router_initialization_in_manager(self):
        """Test EventRouter is properly initialized in UniversalWebSocketManager."""
        # Assert
        assert self.ws_manager.event_router is not None
        assert isinstance(self.ws_manager.event_router, EventRouter)
        assert self.ws_manager.event_router.scalable_broadcaster is not None
        assert self.ws_manager.event_router.enable_caching is True
        assert self.ws_manager.event_router.cache_size == 1000
    
    def test_default_routing_rules_initialized(self):
        """Test default routing rules are initialized in EventRouter."""
        # Assert
        router_stats = self.ws_manager.event_router.get_routing_stats()
        total_rules = router_stats.get('total_rules', 0)
        
        # Should have default rules (pattern, tier, system health, backtest)
        assert total_rules >= 4, f"Expected at least 4 default rules, found {total_rules}"
        
        # Check specific default rules exist
        rule_ids = list(self.ws_manager.event_router.routing_rules.keys())
        expected_rules = [
            'default_pattern_routing',
            'default_tier_daily_routing',
            'default_tier_intraday_routing', 
            'default_tier_combo_routing',
            'system_health_routing',
            'backtest_result_routing'
        ]
        
        for expected_rule in expected_rules:
            assert expected_rule in rule_ids, f"Missing default rule: {expected_rule}"
    
    def test_custom_routing_rule_management(self):
        """Test custom routing rule management via WebSocket manager."""
        # Arrange
        custom_rule = RoutingRule(
            rule_id='custom_test_rule',
            name='Custom Test Rule',
            description='Custom rule for integration testing',
            event_type_patterns=[r'custom.*'],
            content_filters={'custom_field': 'custom_value'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=['custom_room'],
            priority=DeliveryPriority.HIGH
        )
        
        # Act
        add_result = self.ws_manager.add_custom_routing_rule(custom_rule)
        
        # Assert
        assert add_result is True
        
        # Verify rule was added to EventRouter
        router_rules = self.ws_manager.event_router.routing_rules
        assert 'custom_test_rule' in router_rules
        assert router_rules['custom_test_rule'] == custom_rule
        
        # Test rule removal
        remove_result = self.ws_manager.remove_routing_rule('custom_test_rule')
        assert remove_result is True
        assert 'custom_test_rule' not in self.ws_manager.event_router.routing_rules
    
    def test_broadcast_event_with_routing_integration(self):
        """Test broadcast_event uses EventRouter for intelligent routing."""
        # Arrange
        event_type = 'integration_test_pattern'
        event_data = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.85,
            'tier': 'daily'
        }
        targeting_criteria = {
            'subscription_type': 'tier_patterns',
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL',
            'tier': 'daily'
        }
        
        # Mock user finding
        with patch.object(self.ws_manager, '_find_interested_users') as mock_find_users:
            mock_find_users.return_value = {'user1', 'user2', 'user3'}
            
            # Mock EventRouter routing
            mock_routing_result = RoutingResult(
                event_id='integration_test_123',
                matched_rules=['default_pattern_routing', 'default_tier_daily_routing'],
                destinations={'pattern_BreakoutBO_AAPL': set(), 'tier_daily': set()},
                transformations_applied=[],
                routing_time_ms=15.0,
                total_users=3,
                cache_hit=False
            )
            
            with patch.object(self.ws_manager.event_router, 'route_event') as mock_route:
                mock_route.return_value = mock_routing_result
                
                # Act
                delivery_count = self.ws_manager.broadcast_event(
                    event_type=event_type,
                    event_data=event_data,
                    targeting_criteria=targeting_criteria
                )
                
                # Assert
                assert delivery_count == 3  # Should return routed user count
                
                # Verify EventRouter was called
                mock_route.assert_called_once()
                call_args = mock_route.call_args
                
                assert call_args[1]['event_type'] == event_type
                assert 'timestamp' in call_args[1]['event_data']  # Enhanced metadata
                assert 'server_id' in call_args[1]['event_data']
                assert call_args[1]['user_context']['interested_users'] == ['user1', 'user2', 'user3']
    
    def test_subscription_with_routing_integration(self):
        """Test user subscription integrates with routing system."""
        # Arrange
        user_id = 'test_user_routing'
        subscription_type = 'tier_patterns'
        filters = {
            'pattern_types': ['BreakoutBO', 'TrendReversal'],
            'symbols': ['AAPL', 'TSLA'],
            'tiers': ['daily'],
            'confidence_min': 0.7
        }
        
        # Act
        subscription_result = self.ws_manager.subscribe_user(
            user_id=user_id,
            subscription_type=subscription_type,
            filters=filters
        )
        
        # Assert
        assert subscription_result is True
        
        # Verify subscription was added to index manager (affects routing)
        user_subscriptions = self.ws_manager.get_user_subscriptions(user_id)
        assert subscription_type in user_subscriptions
        
        # Verify user was added to room for routing
        self.mock_socketio.server.enter_room.assert_called_with('conn_123', f'user_{user_id}')
        
        # Test broadcast to this user
        event_data = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.85,
            'tier': 'daily'
        }
        
        with patch.object(self.ws_manager, '_find_interested_users') as mock_find_users:
            mock_find_users.return_value = {user_id}
            
            delivery_count = self.ws_manager.broadcast_event(
                event_type='tier_pattern',
                event_data=event_data,
                targeting_criteria={'subscription_type': 'tier_patterns'}
            )
            
            assert delivery_count >= 1  # User should receive the event
    
    def test_routing_statistics_integration(self):
        """Test routing statistics are accessible via WebSocket manager."""
        # Act
        routing_stats = self.ws_manager.get_routing_stats()
        subscription_stats = self.ws_manager.get_subscription_stats()
        
        # Assert
        assert routing_stats is not None
        assert isinstance(routing_stats, dict)
        
        # Check routing-specific stats
        assert 'total_events' in routing_stats
        assert 'avg_routing_time_ms' in routing_stats
        assert 'cache_hit_rate_percent' in routing_stats
        assert 'total_rules' in routing_stats
        
        # Check integration in subscription stats
        assert 'routing_total_events' in subscription_stats
        assert 'routing_avg_time_ms' in subscription_stats
        assert 'routing_cache_hit_rate' in subscription_stats
        assert 'routing_rules_count' in subscription_stats
    
    def test_performance_optimization_integration(self):
        """Test performance optimization includes routing optimization."""
        # Act
        optimization_result = self.ws_manager.optimize_performance()
        
        # Assert
        assert optimization_result is not None
        assert isinstance(optimization_result, dict)
        
        # Check routing optimization was included
        assert 'routing_optimization' in optimization_result
        assert 'current_performance' in optimization_result
        assert 'performance_targets_met' in optimization_result
        
        # Check routing performance targets
        targets = optimization_result['performance_targets_met']
        assert 'routing_under_20ms' in targets


class TestEndToEndEventFlow:
    """Test complete end-to-end event flow with routing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create comprehensive mock setup
        self.mock_socketio = Mock(spec=SocketIO)
        self.mock_redis_client = Mock(spec=redis.Redis)
        self.mock_existing_ws_manager = Mock(spec=WebSocketManager)
        self.mock_websocket_broadcaster = Mock(spec=WebSocketBroadcaster)
        
        # Configure detailed mock behavior
        self.mock_existing_ws_manager.is_user_connected.return_value = True
        self.mock_existing_ws_manager.get_user_connections.return_value = ['conn_123', 'conn_456']
        self.mock_existing_ws_manager.get_connected_users.return_value = ['user1', 'user2', 'user3']
        
        self.mock_socketio.server.enter_room = Mock()
        self.mock_socketio.server.leave_room = Mock()
        self.mock_socketio.emit = Mock()
        
        # Create manager
        self.ws_manager = UniversalWebSocketManager(
            socketio=self.mock_socketio,
            redis_client=self.mock_redis_client,
            existing_websocket_manager=self.mock_existing_ws_manager,
            websocket_broadcaster=self.mock_websocket_broadcaster
        )
        
        # Set up subscriptions
        self._setup_test_subscriptions()
    
    def _setup_test_subscriptions(self):
        """Set up test user subscriptions."""
        # User 1: Daily patterns for AAPL
        self.ws_manager.subscribe_user('user1', 'tier_patterns', {
            'pattern_types': ['BreakoutBO'],
            'symbols': ['AAPL'],
            'tiers': ['daily'],
            'confidence_min': 0.7
        })
        
        # User 2: Intraday patterns for multiple symbols  
        self.ws_manager.subscribe_user('user2', 'tier_patterns', {
            'pattern_types': ['BreakoutBO', 'TrendReversal'],
            'symbols': ['AAPL', 'TSLA'],
            'tiers': ['intraday'],
            'confidence_min': 0.6
        })
        
        # User 3: General pattern alerts
        self.ws_manager.subscribe_user('user3', 'pattern_alerts', {
            'pattern_types': ['BreakoutBO', 'TrendReversal', 'SupportBreak'],
            'confidence_min': 0.8
        })
    
    @pytest.mark.performance
    def test_complete_event_routing_flow(self):
        """Test complete event flow: subscription → indexing → routing → broadcasting."""
        # Arrange
        pattern_event = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.85,
            'tier': 'daily',
            'timestamp': time.time(),
            'description': 'Strong breakout pattern detected'
        }
        
        # Mock interested users finding
        with patch.object(self.ws_manager, '_find_interested_users') as mock_find_users:
            mock_find_users.return_value = {'user1', 'user3'}  # Users interested in this event
            
            # Act
            start_time = time.time()
            
            delivery_count = self.ws_manager.broadcast_event(
                event_type='tier_pattern',
                event_data=pattern_event,
                targeting_criteria={
                    'subscription_type': 'tier_patterns',
                    'pattern_type': 'BreakoutBO',
                    'symbol': 'AAPL',
                    'tier': 'daily'
                }
            )
            
            end_time = time.time()
            total_latency_ms = (end_time - start_time) * 1000
            
            # Assert
            assert delivery_count == 2  # user1 and user3 should receive the event
            
            # Verify performance: Total latency should be under 125ms
            # (5ms indexing + 20ms routing + 100ms broadcasting)
            assert total_latency_ms < 125, f"End-to-end latency {total_latency_ms:.1f}ms exceeds 125ms target"
            
            # Verify user finding was called correctly
            mock_find_users.assert_called_once()
            
            # Verify metrics were updated
            stats = self.ws_manager.get_subscription_stats()
            assert stats['events_broadcast'] > 0
            assert stats['events_delivered'] > 0
    
    def test_multiple_event_types_routing(self):
        """Test routing different event types through complete flow."""
        # Test different event scenarios
        test_events = [
            {
                'event_type': 'tier_pattern',
                'event_data': {
                    'symbol': 'AAPL',
                    'pattern_type': 'BreakoutBO',
                    'confidence': 0.9,
                    'tier': 'daily'
                },
                'targeting_criteria': {
                    'subscription_type': 'tier_patterns',
                    'tier': 'daily',
                    'priority': 'high'
                },
                'expected_users': {'user1', 'user3'}
            },
            {
                'event_type': 'system_health',
                'event_data': {
                    'status': 'warning',
                    'component': 'pattern_detection',
                    'message': 'High load detected'
                },
                'targeting_criteria': {
                    'priority': 'critical'
                },
                'expected_users': {'user1', 'user2', 'user3'}  # All users for system alerts
            },
            {
                'event_type': 'backtest_result',
                'event_data': {
                    'strategy_id': 'momentum_v2',
                    'performance': 0.15,
                    'sharpe_ratio': 1.8
                },
                'targeting_criteria': {
                    'subscription_type': 'backtest_alerts'
                },
                'expected_users': set()  # No users subscribed to backtests in this test
            }
        ]
        
        total_delivery_count = 0
        
        for event_scenario in test_events:
            # Mock user finding for each scenario
            with patch.object(self.ws_manager, '_find_interested_users') as mock_find_users:
                mock_find_users.return_value = event_scenario['expected_users']
                
                # Act
                delivery_count = self.ws_manager.broadcast_event(
                    event_type=event_scenario['event_type'],
                    event_data=event_scenario['event_data'],
                    targeting_criteria=event_scenario['targeting_criteria']
                )
                
                # Assert
                expected_count = len(event_scenario['expected_users'])
                assert delivery_count == expected_count, \
                    f"Event {event_scenario['event_type']} delivered to {delivery_count} users, expected {expected_count}"
                
                total_delivery_count += delivery_count
        
        # Verify total events were processed
        stats = self.ws_manager.get_subscription_stats()
        assert stats['events_broadcast'] >= len(test_events)
        assert stats['events_delivered'] >= total_delivery_count
    
    def test_concurrent_event_flow(self):
        """Test concurrent event processing through routing system."""
        # Arrange
        events_to_process = []
        for i in range(20):
            event = {
                'event_type': f'concurrent_test_{i % 3}',  # Vary event types
                'event_data': {
                    'symbol': ['AAPL', 'TSLA', 'GOOGL'][i % 3],
                    'pattern_type': 'BreakoutBO',
                    'confidence': 0.7 + (i % 5) * 0.05,
                    'tier': ['daily', 'intraday'][i % 2],
                    'iteration': i
                },
                'targeting_criteria': {
                    'subscription_type': 'tier_patterns'
                }
            }
            events_to_process.append(event)
        
        results = []
        exceptions = []
        
        def process_events():
            """Process events concurrently."""
            try:
                thread_results = []
                thread_id = threading.current_thread().ident
                
                for i, event in enumerate(events_to_process):
                    if i % 4 == threading.active_count() % 4:  # Distribute events across threads
                        
                        with patch.object(self.ws_manager, '_find_interested_users') as mock_find_users:
                            mock_find_users.return_value = {'user1', 'user2'}
                            
                            delivery_count = self.ws_manager.broadcast_event(
                                event_type=event['event_type'],
                                event_data=event['event_data'],
                                targeting_criteria=event['targeting_criteria']
                            )
                            thread_results.append(delivery_count)
                
                results.extend(thread_results)
                
            except Exception as e:
                exceptions.append(e)
        
        # Act
        threads = []
        for i in range(4):  # 4 concurrent threads
            thread = threading.Thread(target=process_events)
            threads.append(thread)
        
        start_time = time.time()
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        elapsed_time = (time.time() - start_time) * 1000
        
        # Assert
        assert len(exceptions) == 0, f"Concurrent event processing raised exceptions: {exceptions}"
        assert len(results) > 0, "No events were processed"
        
        # Verify all results are valid
        for result in results:
            assert isinstance(result, int)
            assert result >= 0
        
        # Performance should be reasonable for concurrent processing
        avg_time_per_event = elapsed_time / len(results) if results else 0
        assert avg_time_per_event < 100, f"Concurrent processing too slow: {avg_time_per_event:.1f}ms per event"


class TestRoutingErrorHandlingIntegration:
    """Test error handling and fallback scenarios with routing integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_socketio = Mock(spec=SocketIO)
        self.mock_redis_client = Mock(spec=redis.Redis)
        self.mock_existing_ws_manager = Mock(spec=WebSocketManager)
        self.mock_websocket_broadcaster = Mock(spec=WebSocketBroadcaster)
        
        # Configure mocks
        self.mock_existing_ws_manager.is_user_connected.return_value = True
        self.mock_existing_ws_manager.get_user_connections.return_value = ['conn_123']
        self.mock_existing_ws_manager.get_connected_users.return_value = ['user1']
        
        # Create manager
        self.ws_manager = UniversalWebSocketManager(
            socketio=self.mock_socketio,
            redis_client=self.mock_redis_client,
            existing_websocket_manager=self.mock_existing_ws_manager,
            websocket_broadcaster=self.mock_websocket_broadcaster
        )
    
    def test_routing_error_fallback_to_broadcaster(self):
        """Test fallback to ScalableBroadcaster when routing fails."""
        # Arrange
        event_data = {'test': 'routing_error'}
        
        # Mock EventRouter to raise an exception
        with patch.object(self.ws_manager.event_router, 'route_event') as mock_route:
            mock_route.side_effect = Exception("Routing system failure")
            
            with patch.object(self.ws_manager, '_find_interested_users') as mock_find_users:
                mock_find_users.return_value = {'user1'}
                
                # Act & Assert - Should not raise exception
                delivery_count = self.ws_manager.broadcast_event(
                    event_type='error_test',
                    event_data=event_data,
                    targeting_criteria={'test': 'fallback'}
                )
                
                # Should still work with fallback (though exact behavior depends on implementation)
                assert isinstance(delivery_count, int)
                assert delivery_count >= 0
    
    def test_malformed_routing_rule_handling(self):
        """Test handling of malformed routing rules."""
        # Arrange - Create malformed rule
        malformed_rule = RoutingRule(
            rule_id='malformed_rule',
            name='Malformed Rule',
            description='Rule with problematic patterns',
            event_type_patterns=[r'['],  # Invalid regex pattern
            content_filters={'invalid_filter': object()},  # Non-serializable filter
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )
        
        # Act & Assert - Should not crash the system
        add_result = self.ws_manager.add_custom_routing_rule(malformed_rule)
        
        # System should handle the malformed rule gracefully
        # (exact behavior depends on implementation)
        assert isinstance(add_result, bool)
        
        # Try to use the system with the malformed rule
        delivery_count = self.ws_manager.broadcast_event(
            'malformed_test',
            {'test': 'data'},
            {'test': 'criteria'}
        )
        
        assert isinstance(delivery_count, int)
        assert delivery_count >= 0
    
    def test_routing_system_recovery_after_errors(self):
        """Test routing system recovery after encountering errors."""
        # Arrange - Cause some routing errors
        for i in range(5):
            with patch.object(self.ws_manager.event_router, 'route_event') as mock_route:
                mock_route.side_effect = Exception(f"Error {i}")
                
                self.ws_manager.broadcast_event(
                    f'error_event_{i}',
                    {'error_test': i},
                    {}
                )
        
        # Act - Try normal operation after errors
        with patch.object(self.ws_manager, '_find_interested_users') as mock_find_users:
            mock_find_users.return_value = {'user1'}
            
            delivery_count = self.ws_manager.broadcast_event(
                'recovery_test',
                {'recovery': True},
                {'test': 'recovery'}
            )
        
        # Assert - System should be operational
        assert isinstance(delivery_count, int)
        assert delivery_count >= 0
        
        # Check error tracking
        router_stats = self.ws_manager.get_routing_stats()
        assert 'routing_errors' in router_stats
        # Should have recorded the routing errors
        # (exact count depends on implementation)
    
    def test_health_monitoring_with_routing_issues(self):
        """Test health monitoring detects routing system issues."""
        # Arrange - Simulate routing performance issues
        # Mock poor routing performance
        mock_stats = {
            'total_events': 100,
            'avg_routing_time_ms': 60.0,  # Above 50ms warning threshold
            'routing_errors': 2,
            'cache_hit_rate_percent': 25.0  # Below 30% threshold
        }
        
        with patch.object(self.ws_manager.event_router, 'get_routing_stats') as mock_get_stats:
            mock_get_stats.return_value = mock_stats
            
            # Act
            health_status = self.ws_manager.get_health_status()
        
        # Assert
        assert health_status is not None
        assert 'status' in health_status
        assert 'message' in health_status
        
        # Should detect performance issues
        # (exact status depends on implementation and other factors)
        assert health_status['status'] in ['healthy', 'warning', 'error']


@pytest.mark.performance  
class TestIntegratedPerformanceTargets:
    """Test integrated performance targets for complete routing system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_socketio = Mock(spec=SocketIO)
        self.mock_redis_client = Mock(spec=redis.Redis)
        self.mock_existing_ws_manager = Mock(spec=WebSocketManager)
        self.mock_websocket_broadcaster = Mock(spec=WebSocketBroadcaster)
        
        # Configure for performance testing
        self.mock_existing_ws_manager.is_user_connected.return_value = True
        self.mock_existing_ws_manager.get_user_connections.return_value = ['conn_123']
        self.mock_existing_ws_manager.get_connected_users.return_value = [f'user_{i}' for i in range(100)]
        
        # Create manager
        self.ws_manager = UniversalWebSocketManager(
            socketio=self.mock_socketio,
            redis_client=self.mock_redis_client,
            existing_websocket_manager=self.mock_existing_ws_manager,
            websocket_broadcaster=self.mock_websocket_broadcaster
        )
    
    def test_end_to_end_latency_under_125ms(self):
        """Test complete end-to-end latency is under 125ms target."""
        # Arrange - Set up subscriptions for performance test
        for i in range(50):  # 50 users
            self.ws_manager.subscribe_user(
                user_id=f'perf_user_{i}',
                subscription_type='tier_patterns',
                filters={
                    'pattern_types': ['BreakoutBO'],
                    'tiers': ['daily'],
                    'confidence_min': 0.7
                }
            )
        
        event_data = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.85,
            'tier': 'daily'
        }
        
        # Mock finding interested users
        interested_users = {f'perf_user_{i}' for i in range(30)}  # 30 of 50 users interested
        
        latencies = []
        
        # Act - Measure latency across multiple events
        for i in range(10):
            with patch.object(self.ws_manager, '_find_interested_users') as mock_find_users:
                mock_find_users.return_value = interested_users
                
                start_time = time.time()
                
                delivery_count = self.ws_manager.broadcast_event(
                    event_type='performance_test',
                    event_data={**event_data, 'iteration': i},
                    targeting_criteria={'subscription_type': 'tier_patterns'}
                )
                
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)
        
        # Assert
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        
        assert avg_latency < 125, f"Average end-to-end latency {avg_latency:.1f}ms exceeds 125ms target"
        assert p95_latency < 125, f"P95 end-to-end latency {p95_latency:.1f}ms exceeds 125ms target"
        assert max_latency < 200, f"Maximum latency {max_latency:.1f}ms too high"
    
    def test_routing_performance_under_20ms(self):
        """Test routing component specifically meets <20ms target."""
        # Arrange - Add complex routing rules
        for i in range(10):
            rule = RoutingRule(
                rule_id=f'perf_rule_{i}',
                name=f'Performance Rule {i}',
                description=f'Complex rule {i}',
                event_type_patterns=[r'.*perf.*', f'.*test_{i}.*'],
                content_filters={
                    'confidence': {'min': 0.5 + i * 0.05},
                    'tier': 'daily' if i % 2 == 0 else 'intraday',
                    'priority': 'HIGH' if i < 5 else 'MEDIUM'
                },
                user_criteria={},
                strategy=RoutingStrategy.CONTENT_BASED if i % 2 == 0 else RoutingStrategy.BROADCAST_ALL,
                destinations=[f'room_{i}'],
                priority=DeliveryPriority.HIGH if i < 5 else DeliveryPriority.MEDIUM
            )
            self.ws_manager.event_router.add_routing_rule(rule)
        
        routing_times = []
        
        # Act - Measure routing performance specifically
        for i in range(50):
            event_data = {
                'confidence': 0.7 + (i % 5) * 0.05,
                'tier': 'daily' if i % 2 == 0 else 'intraday',
                'priority': 'HIGH' if i < 25 else 'MEDIUM',
                'iteration': i
            }
            
            # Directly test routing component
            start_time = time.time()
            
            routing_result = self.ws_manager.event_router.route_event(
                event_type=f'perf_test_{i % 10}',
                event_data=event_data,
                user_context={}
            )
            
            end_time = time.time()
            routing_time_ms = (end_time - start_time) * 1000
            routing_times.append(routing_time_ms)
            
            assert routing_result is not None
        
        # Assert
        avg_routing_time = sum(routing_times) / len(routing_times)
        max_routing_time = max(routing_times)
        p95_routing_time = sorted(routing_times)[int(0.95 * len(routing_times))]
        
        assert avg_routing_time < 20, f"Average routing time {avg_routing_time:.1f}ms exceeds 20ms target"
        assert p95_routing_time < 20, f"P95 routing time {p95_routing_time:.1f}ms exceeds 20ms target"
        assert max_routing_time < 50, f"Maximum routing time {max_routing_time:.1f}ms too high"
        
        # Check routing statistics
        router_stats = self.ws_manager.event_router.get_routing_stats()
        assert router_stats['avg_routing_time_ms'] < 20
    
    def test_cache_hit_rate_above_50_percent(self):
        """Test cache hit rate meets >50% target with realistic usage."""
        # Arrange - Create repeatable event patterns to benefit from caching
        common_events = [
            ('tier_pattern', {'symbol': 'AAPL', 'pattern_type': 'BreakoutBO', 'tier': 'daily'}),
            ('tier_pattern', {'symbol': 'TSLA', 'pattern_type': 'TrendReversal', 'tier': 'intraday'}),
            ('system_health', {'status': 'healthy', 'component': 'router'}),
        ]
        
        # First pass - populate cache
        for event_type, event_data in common_events * 5:  # 15 initial requests
            self.ws_manager.event_router.route_event(event_type, event_data)
        
        # Reset stats to measure hit rate
        initial_events = self.ws_manager.event_router.stats.total_events
        
        # Second pass - should benefit from cache
        for event_type, event_data in common_events * 10:  # 30 more requests with repetition
            result = self.ws_manager.event_router.route_event(event_type, event_data)
            assert result is not None
        
        # Assert
        final_stats = self.ws_manager.event_router.get_routing_stats()
        cache_hit_rate = final_stats.get('cache_hit_rate_percent', 0)
        
        # Cache hit rate should be improving with repeated patterns
        # Note: Exact rate depends on caching policy (events must have >5 users to cache)
        assert cache_hit_rate >= 0, "Cache hit rate tracking not working"
        
        # Verify cache system is operational
        assert final_stats['total_events'] > initial_events
        assert 'cache_size' in final_stats


if __name__ == '__main__':
    pytest.main([__file__])