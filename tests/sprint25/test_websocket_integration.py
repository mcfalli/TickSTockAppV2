"""
Integration tests for Sprint 25 WebSocket message flow.

Sprint 25 Day 1 Implementation Integration Testing:
- End-to-end WebSocket message delivery flow
- Redis event consumption → WebSocket → Browser delivery
- Cross-system integration validation
- Performance and reliability testing
"""

import pytest
import time
import json
import asyncio
import threading
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, AsyncMock, call
from typing import Dict, Any, List, Set
import redis
from flask_socketio import SocketIO

# Import components under test
from src.core.services.websocket_subscription_manager import UniversalWebSocketManager
from src.core.services.tier_pattern_websocket_integration import TierPatternWebSocketIntegration, TierSubscriptionPreferences
from src.core.domain.events.tier_events import TierPatternEvent, MarketStateEvent, PatternTier, MarketRegime, EventPriority
from src.presentation.websocket.manager import WebSocketManager
from src.core.services.websocket_broadcaster import WebSocketBroadcaster


class TestWebSocketMessageFlow:
    """Integration tests for end-to-end WebSocket message flow."""
    
    @pytest.fixture
    def mock_socketio(self):
        """Mock Flask-SocketIO with realistic behavior."""
        socketio = Mock(spec=SocketIO)
        socketio.server = Mock()
        socketio.server.enter_room = Mock()
        socketio.server.leave_room = Mock()
        socketio.emit = Mock()
        return socketio
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client with pub-sub simulation."""
        redis_client = Mock(spec=redis.Redis)
        return redis_client
    
    @pytest.fixture
    def mock_existing_ws_manager(self):
        """Mock existing WebSocketManager with user connections."""
        manager = Mock(spec=WebSocketManager)
        
        # Simulate multiple connected users
        manager.is_user_connected.side_effect = lambda user_id: user_id in ["user1", "user2", "user3"]
        manager.get_user_connections.side_effect = lambda user_id: {f"conn_{user_id}_1", f"conn_{user_id}_2"}
        manager.get_connected_users.return_value = {"user1", "user2", "user3"}
        
        return manager
    
    @pytest.fixture
    def mock_ws_broadcaster(self):
        """Mock WebSocketBroadcaster."""
        broadcaster = Mock(spec=WebSocketBroadcaster)
        return broadcaster
    
    @pytest.fixture
    def websocket_manager(self, mock_socketio, mock_redis_client, mock_existing_ws_manager, mock_ws_broadcaster):
        """UniversalWebSocketManager for integration testing."""
        return UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis_client,
            existing_websocket_manager=mock_existing_ws_manager,
            websocket_broadcaster=mock_ws_broadcaster
        )
    
    @pytest.fixture
    def tier_integration(self, websocket_manager):
        """TierPatternWebSocketIntegration for integration testing."""
        return TierPatternWebSocketIntegration(websocket_manager=websocket_manager)
    
    def test_complete_subscription_to_delivery_flow(self, tier_integration, websocket_manager, mock_socketio):
        """Test complete flow: subscribe → receive event → filter → deliver."""
        
        # Step 1: Subscribe users with different preferences
        user_preferences = {
            "user1": TierSubscriptionPreferences(
                pattern_types=["BreakoutBO"],
                symbols=["AAPL", "TSLA"],
                tiers=[PatternTier.DAILY],
                confidence_min=0.8
            ),
            "user2": TierSubscriptionPreferences(
                pattern_types=["BreakoutBO", "TrendReversal"],
                symbols=["AAPL"],  # Only AAPL
                tiers=[PatternTier.DAILY, PatternTier.INTRADAY],
                confidence_min=0.7
            ),
            "user3": TierSubscriptionPreferences(
                pattern_types=["TrendReversal"],  # Different pattern
                symbols=["AAPL", "TSLA"],
                tiers=[PatternTier.DAILY],
                confidence_min=0.6
            )
        }
        
        subscription_results = []
        for user_id, preferences in user_preferences.items():
            result = tier_integration.subscribe_user_to_tier_patterns(user_id, preferences)
            subscription_results.append(result)
            assert result is True
        
        # Verify subscriptions were created
        assert len(websocket_manager.user_subscriptions) == 3
        assert websocket_manager.metrics.active_subscriptions == 3
        
        # Step 2: Create and broadcast tier pattern event
        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.85,
            event_id="integration_test_event",
            timestamp=datetime.now(),
            priority=EventPriority.HIGH
        )
        
        # Step 3: Broadcast event through tier integration
        delivery_count = tier_integration.broadcast_tier_pattern_event(pattern_event)
        
        # Should deliver to user1 and user2 (both have BreakoutBO + AAPL)
        # user3 should be filtered out (only wants TrendReversal patterns)
        assert delivery_count == 2
        
        # Step 4: Verify WebSocket emit calls
        assert mock_socketio.emit.call_count == 2  # Two users received the event
        
        # Check emit parameters
        emit_calls = mock_socketio.emit.call_args_list
        event_types = [call[0][0] for call in emit_calls]
        rooms = [call[1]["room"] for call in emit_calls]
        
        assert all(event_type == "tier_pattern" for event_type in event_types)
        assert set(rooms) == {"user_user1", "user_user2"}
        
        # Step 5: Verify event data integrity
        for call_args in emit_calls:
            event_envelope = call_args[0][1]  # Second argument is event envelope
            
            assert event_envelope["type"] == "tier_pattern"
            assert "data" in event_envelope
            assert "timestamp" in event_envelope
            assert event_envelope["server_id"] == "tickstock-app-v2"
            
            # Check event data structure
            event_data = event_envelope["data"]
            assert event_data["pattern_type"] == "BreakoutBO"
            assert event_data["symbol"] == "AAPL"
            assert event_data["tier"] == "daily"
            assert event_data["confidence"] == 0.85
    
    def test_multi_user_concurrent_subscription_and_broadcast(self, tier_integration, websocket_manager, mock_socketio):
        """Test concurrent operations with multiple users."""
        
        # Step 1: Set up many users with various preferences
        user_count = 50
        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
        patterns = ["BreakoutBO", "TrendReversal", "SurgePattern"]
        
        # Subscribe users concurrently
        def subscribe_users(start_idx, end_idx):
            for i in range(start_idx, end_idx):
                preferences = TierSubscriptionPreferences(
                    pattern_types=[patterns[i % len(patterns)]],
                    symbols=[symbols[i % len(symbols)]],
                    tiers=[PatternTier.DAILY],
                    confidence_min=0.6 + (i % 3) * 0.1  # 0.6, 0.7, 0.8
                )
                tier_integration.subscribe_user_to_tier_patterns(f"user{i}", preferences)
        
        # Use threads to simulate concurrent subscriptions
        threads = []
        batch_size = 10
        for start in range(0, user_count, batch_size):
            end = min(start + batch_size, user_count)
            thread = threading.Thread(target=subscribe_users, args=(start, end))
            threads.append(thread)
            thread.start()
        
        # Wait for all subscriptions to complete
        for thread in threads:
            thread.join()
        
        # Verify all subscriptions were created
        assert len(websocket_manager.user_subscriptions) == user_count
        assert websocket_manager.metrics.active_subscriptions == user_count
        
        # Step 2: Broadcast multiple events for different symbols/patterns
        events = [
            TierPatternEvent(
                pattern_type="BreakoutBO", symbol="AAPL", tier=PatternTier.DAILY,
                confidence=0.8, event_id="concurrent_test_1", timestamp=datetime.now()
            ),
            TierPatternEvent(
                pattern_type="TrendReversal", symbol="TSLA", tier=PatternTier.DAILY,
                confidence=0.75, event_id="concurrent_test_2", timestamp=datetime.now()
            ),
            TierPatternEvent(
                pattern_type="SurgePattern", symbol="MSFT", tier=PatternTier.DAILY,
                confidence=0.9, event_id="concurrent_test_3", timestamp=datetime.now()
            )
        ]
        
        total_deliveries = 0
        for event in events:
            deliveries = tier_integration.broadcast_tier_pattern_event(event)
            total_deliveries += deliveries
        
        # Should have delivered events to matching users
        assert total_deliveries > 0
        assert tier_integration.stats["patterns_broadcast"] == 3
        
        # Should not have any filtering performance issues
        assert websocket_manager.metrics.filtering_latency_ms < 50  # Should be fast
    
    def test_user_connection_lifecycle_integration(self, websocket_manager, mock_existing_ws_manager, mock_socketio):
        """Test user connection, subscription, disconnection lifecycle."""
        
        # Step 1: User connects and subscribes
        websocket_manager.subscribe_user("user1", "tier_patterns", {
            "symbols": ["AAPL"], "confidence_min": 0.7
        })
        
        # Step 2: Handle user connection
        websocket_manager.handle_user_connection("user1", "conn_123")
        
        # Should join user to their room
        mock_socketio.server.enter_room.assert_called_with("conn_123", "user_user1")
        
        # Should emit subscription status
        status_calls = [call for call in mock_socketio.emit.call_args_list 
                       if call[0][0] == "subscription_status"]
        assert len(status_calls) == 1
        
        status_data = status_calls[0][0][1]
        assert status_data["active_subscriptions"] == ["tier_patterns"]
        assert status_data["room"] == "user_user1"
        
        # Step 3: Broadcast event to connected user
        mock_socketio.emit.reset_mock()  # Clear previous calls
        
        delivery_count = websocket_manager.broadcast_event("test_event", {"data": "test"}, {
            "subscription_type": "tier_patterns"
        })
        
        assert delivery_count == 1
        assert mock_socketio.emit.called
        
        # Step 4: Handle user disconnection
        websocket_manager.handle_user_disconnection("user1", "conn_123")
        
        # Should update connection metrics
        mock_existing_ws_manager.get_connected_users.assert_called()
        
        # Step 5: Unsubscribe user
        websocket_manager.unsubscribe_user("user1")
        
        # Should leave user room
        mock_socketio.server.leave_room.assert_called()
    
    def test_redis_event_to_websocket_delivery_simulation(self, tier_integration):
        """Simulate Redis event consumption and WebSocket delivery."""
        
        # Step 1: Subscribe users
        tier_integration.subscribe_user_to_tier_patterns("user1", TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY],
            confidence_min=0.8
        ))
        
        tier_integration.subscribe_user_to_tier_patterns("user2", TierSubscriptionPreferences(
            pattern_types=["TrendReversal"],
            symbols=["AAPL", "TSLA"],
            tiers=[PatternTier.INTRADAY],
            confidence_min=0.7
        ))
        
        # Step 2: Simulate Redis event data (what would come from TickStockPL)
        redis_event_data = {
            "pattern": "BreakoutBO",
            "symbol": "AAPL",
            "tier": "daily",
            "confidence": 0.85,
            "timestamp": time.time(),
            "event_id": "redis_sim_123",
            "breakout_level": 150.25,
            "volume_surge": 2.1
        }
        
        # Step 3: Create TierPatternEvent from Redis data (simulating Redis consumer)
        pattern_event = TierPatternEvent.from_redis_event(redis_event_data)
        
        # Verify event was parsed correctly
        assert pattern_event.pattern_type == "BreakoutBO"
        assert pattern_event.symbol == "AAPL"
        assert pattern_event.tier == PatternTier.DAILY
        assert pattern_event.confidence == 0.85
        assert pattern_event.pattern_data["breakout_level"] == 150.25
        assert pattern_event.pattern_data["volume_surge"] == 2.1
        
        # Step 4: Broadcast event through integration layer
        delivery_count = tier_integration.broadcast_tier_pattern_event(pattern_event)
        
        # Should deliver to user1 (matches BreakoutBO + AAPL + daily + confidence >= 0.8)
        # Should NOT deliver to user2 (wants TrendReversal, not BreakoutBO)
        assert delivery_count == 1
        
        # Step 5: Verify event reaches WebSocket layer with proper format
        ws_manager = tier_integration.websocket_manager
        
        # Check that broadcast was called with correct parameters
        assert ws_manager.metrics.events_broadcast == 1
        assert ws_manager.metrics.events_delivered == 1
        
        # Verify integration stats
        assert tier_integration.stats["patterns_broadcast"] == 1
        assert tier_integration.stats["last_pattern_time"] > 0
    
    def test_error_handling_in_message_flow(self, tier_integration, websocket_manager, mock_socketio):
        """Test error handling throughout the message delivery flow."""
        
        # Step 1: Subscribe user successfully
        result = tier_integration.subscribe_user_to_tier_patterns("user1", TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY]
        ))
        assert result is True
        
        # Step 2: Simulate WebSocket emission error
        mock_socketio.emit.side_effect = Exception("WebSocket delivery failed")
        
        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO", symbol="AAPL", tier=PatternTier.DAILY,
            confidence=0.8, event_id="error_test", timestamp=datetime.now()
        )
        
        # Step 3: Attempt broadcast - should handle error gracefully
        delivery_count = tier_integration.broadcast_tier_pattern_event(pattern_event)
        
        assert delivery_count == 0  # No successful deliveries due to error
        
        # Should track broadcast errors
        assert websocket_manager.metrics.broadcast_errors == 1
        
        # Step 4: Reset and verify recovery
        mock_socketio.emit.side_effect = None  # Remove error
        
        delivery_count = tier_integration.broadcast_tier_pattern_event(pattern_event)
        assert delivery_count == 1  # Should work again
        
        # Stats should show both attempts
        assert tier_integration.stats["patterns_broadcast"] == 2
    
    def test_performance_under_load_simulation(self, tier_integration, websocket_manager):
        """Simulate high-load conditions and measure performance."""
        
        # Step 1: Set up realistic load - 100 users with diverse preferences
        user_count = 100
        subscription_time_start = time.time()
        
        for i in range(user_count):
            preferences = TierSubscriptionPreferences(
                pattern_types=["BreakoutBO", "TrendReversal", "SurgePattern"][i % 3],
                symbols=[f"SYMBOL{i // 10}"],  # 10 users per symbol
                tiers=[PatternTier.DAILY, PatternTier.INTRADAY][i % 2],
                confidence_min=0.6 + (i % 4) * 0.1
            )
            
            result = tier_integration.subscribe_user_to_tier_patterns(f"load_user{i}", preferences)
            assert result is True
        
        subscription_time = (time.time() - subscription_time_start) * 1000
        
        # Should handle 100 subscriptions quickly
        assert subscription_time < 1000, f"Subscriptions took {subscription_time:.2f}ms, target <1000ms"
        
        # Step 2: Broadcast multiple events and measure performance
        events = []
        for i in range(20):  # 20 events
            events.append(TierPatternEvent(
                pattern_type=["BreakoutBO", "TrendReversal", "SurgePattern"][i % 3],
                symbol=f"SYMBOL{i % 10}",
                tier=[PatternTier.DAILY, PatternTier.INTRADAY][i % 2],
                confidence=0.7 + (i % 3) * 0.1,
                event_id=f"load_test_{i}",
                timestamp=datetime.now()
            ))
        
        broadcast_start = time.time()
        total_deliveries = 0
        
        for event in events:
            deliveries = tier_integration.broadcast_tier_pattern_event(event)
            total_deliveries += deliveries
        
        broadcast_time = (time.time() - broadcast_start) * 1000
        
        # Performance targets
        assert broadcast_time < 2000, f"Broadcasting 20 events took {broadcast_time:.2f}ms, target <2000ms"
        assert total_deliveries > 0, "Should have delivered events to interested users"
        
        # Check filtering performance stayed reasonable
        avg_filtering_ms = websocket_manager.metrics.filtering_latency_ms
        assert avg_filtering_ms < 10, f"Average filtering {avg_filtering_ms:.2f}ms, target <10ms"
        
        # Step 3: Verify system health under load
        health = tier_integration.get_health_status()
        assert health["status"] in ["healthy", "warning"], f"System unhealthy under load: {health['status']}"
    
    def test_market_state_integration_flow(self, tier_integration, websocket_manager, mock_socketio):
        """Test market state event integration flow."""
        
        # Step 1: Subscribe users to market insights (different from tier patterns)
        websocket_manager.subscribe_user("market_user1", "market_insights", {
            "market_regimes": ["bull", "bear"],
            "volatility_regimes": ["normal", "high"]
        })
        
        websocket_manager.subscribe_user("market_user2", "market_insights", {
            "market_regimes": ["bull"],  # Only bull markets
        })
        
        # Step 2: Create and broadcast market state event
        market_event = MarketStateEvent(
            regime=MarketRegime.BULL,
            regime_confidence=0.85,
            etf_performance={"SPY": 0.02, "QQQ": 0.03, "IWM": 0.01},
            sector_strength={"Technology": 0.025, "Healthcare": 0.01},
            event_id="market_integration_test",
            timestamp=datetime.now(),
            volatility_regime="normal",
            risk_on_score=0.6
        )
        
        delivery_count = tier_integration.broadcast_market_state_update(market_event)
        
        # Should deliver to both users (both want bull market updates)
        assert delivery_count == 2
        
        # Step 3: Verify WebSocket calls
        market_emit_calls = [call for call in mock_socketio.emit.call_args_list 
                           if call[0][0] == "market_state_update"]
        assert len(market_emit_calls) == 2
        
        # Step 4: Check event data structure
        for call_args in market_emit_calls:
            event_envelope = call_args[0][1]
            assert event_envelope["type"] == "market_state_update"
            
            event_data = event_envelope["data"]
            assert event_data["regime"] == "bull"
            assert event_data["regime_confidence"] == 0.85
            assert "etf_performance" in event_data
            assert "sector_strength" in event_data
        
        # Step 5: Verify integration stats
        assert tier_integration.stats["market_updates_sent"] == 1
    
    def test_alert_generation_and_delivery_flow(self, tier_integration, mock_socketio):
        """Test pattern alert generation and delivery flow."""
        
        # Step 1: Subscribe user to tier patterns
        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY],
            confidence_min=0.8,
            priority_min=EventPriority.HIGH
        )
        
        tier_integration.subscribe_user_to_tier_patterns("alert_user", preferences)
        
        # Step 2: Create high-confidence pattern event
        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL", 
            tier=PatternTier.DAILY,
            confidence=0.92,  # High confidence
            event_id="alert_pattern_test",
            timestamp=datetime.now(),
            priority=EventPriority.HIGH
        )
        
        # Step 3: Generate pattern alert for user
        alert = tier_integration.generate_pattern_alert(
            "alert_user", 
            pattern_event, 
            preferences.to_filter_dict()
        )
        
        assert alert is not None
        assert alert.user_id == "alert_user"
        assert alert.pattern_event == pattern_event
        assert alert.alert_priority == EventPriority.CRITICAL  # Upgraded due to high confidence
        
        # Step 4: Broadcast alert
        alert_delivered = tier_integration.broadcast_pattern_alert(alert)
        assert alert_delivered is True
        
        # Step 5: Verify alert was delivered via WebSocket
        alert_emit_calls = [call for call in mock_socketio.emit.call_args_list 
                          if call[0][0] == "pattern_alert"]
        assert len(alert_emit_calls) == 1
        
        alert_data = alert_emit_calls[0][0][1]["data"]
        assert alert_data["alert_id"] == alert.alert_id
        assert alert_data["user_id"] == "alert_user"
        assert alert_data["priority"] == "critical"
        
        # Step 6: Verify integration stats
        assert tier_integration.stats["alerts_generated"] == 1


class TestCrossSystemIntegration:
    """Test integration between different system components."""
    
    @pytest.fixture
    def full_system_setup(self):
        """Set up full system components for cross-system testing."""
        mock_socketio = Mock(spec=SocketIO)
        mock_socketio.server = Mock()
        mock_socketio.emit = Mock()
        
        mock_redis = Mock(spec=redis.Redis)
        
        mock_existing_ws = Mock(spec=WebSocketManager)
        mock_existing_ws.is_user_connected.return_value = True
        mock_existing_ws.get_user_connections.return_value = {"conn1", "conn2"}
        mock_existing_ws.get_connected_users.return_value = {"user1", "user2"}
        
        mock_broadcaster = Mock(spec=WebSocketBroadcaster)
        
        # Create integrated system
        ws_manager = UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis,
            existing_websocket_manager=mock_existing_ws,
            websocket_broadcaster=mock_broadcaster
        )
        
        tier_integration = TierPatternWebSocketIntegration(websocket_manager=ws_manager)
        
        return {
            "socketio": mock_socketio,
            "redis": mock_redis,
            "existing_ws": mock_existing_ws,
            "broadcaster": mock_broadcaster,
            "ws_manager": ws_manager,
            "tier_integration": tier_integration
        }
    
    def test_system_health_monitoring_integration(self, full_system_setup):
        """Test system health monitoring across components."""
        components = full_system_setup
        ws_manager = components["ws_manager"]
        tier_integration = components["tier_integration"]
        
        # Set up some system activity
        ws_manager.subscribe_user("health_user1", "tier_patterns", {"symbols": ["AAPL"]})
        ws_manager.subscribe_user("health_user2", "market_insights", {"regimes": ["bull"]})
        
        # Simulate some events
        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO", symbol="AAPL", tier=PatternTier.DAILY,
            confidence=0.8, event_id="health_test", timestamp=datetime.now()
        )
        tier_integration.broadcast_tier_pattern_event(pattern_event)
        
        # Check WebSocket manager health
        ws_health = ws_manager.get_health_status()
        assert ws_health["status"] in ["healthy", "warning"]
        assert "stats" in ws_health
        assert ws_health["performance_targets"]["filtering_target_ms"] == 5.0
        
        # Check tier integration health
        tier_health = tier_integration.get_health_status()
        assert tier_health["service"] == "tier_pattern_websocket_integration"
        assert "websocket_health" in tier_health
        assert tier_health["websocket_health"] == ws_health
        
        # Verify health data consistency
        assert "stats" in tier_health
        tier_stats = tier_health["stats"]
        assert tier_stats["tier_subscriptions"] == 1  # Only one tier pattern subscription
        assert tier_stats["patterns_broadcast"] == 1
        assert "websocket_stats" in tier_stats
    
    def test_concurrent_multi_component_operations(self, full_system_setup):
        """Test concurrent operations across multiple components."""
        components = full_system_setup
        ws_manager = components["ws_manager"]
        tier_integration = components["tier_integration"]
        
        # Simulate concurrent operations from multiple sources
        results = []
        errors = []
        
        def websocket_operations():
            try:
                for i in range(20):
                    # Direct WebSocket manager operations
                    ws_manager.subscribe_user(f"ws_user{i}", "tier_patterns", {
                        "symbols": [f"SYMBOL{i % 5}"]
                    })
                    
                    # Broadcast through WebSocket manager
                    delivery_count = ws_manager.broadcast_event("test_event", {"data": i}, {
                        "subscription_type": "tier_patterns"
                    })
                    results.append(("ws", delivery_count))
            except Exception as e:
                errors.append(("ws", e))
        
        def tier_integration_operations():
            try:
                for i in range(15):
                    # Tier integration operations
                    preferences = TierSubscriptionPreferences(
                        pattern_types=["BreakoutBO"],
                        symbols=[f"SYMBOL{i % 3}"],
                        tiers=[PatternTier.DAILY]
                    )
                    tier_integration.subscribe_user_to_tier_patterns(f"tier_user{i}", preferences)
                    
                    # Broadcast through tier integration
                    event = TierPatternEvent(
                        pattern_type="BreakoutBO", symbol=f"SYMBOL{i % 3}",
                        tier=PatternTier.DAILY, confidence=0.8,
                        event_id=f"concurrent_{i}", timestamp=datetime.now()
                    )
                    delivery_count = tier_integration.broadcast_tier_pattern_event(event)
                    results.append(("tier", delivery_count))
            except Exception as e:
                errors.append(("tier", e))
        
        def connection_management_operations():
            try:
                for i in range(10):
                    # Connection lifecycle operations
                    user_id = f"conn_user{i}"
                    connection_id = f"conn_{i}"
                    
                    ws_manager.handle_user_connection(user_id, connection_id)
                    time.sleep(0.001)  # Small delay
                    ws_manager.handle_user_disconnection(user_id, connection_id)
                    results.append(("conn", 1))
            except Exception as e:
                errors.append(("conn", e))
        
        # Run concurrent operations
        threads = [
            threading.Thread(target=websocket_operations),
            threading.Thread(target=tier_integration_operations),
            threading.Thread(target=connection_management_operations)
        ]
        
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during concurrent operations: {errors}"
        
        # Verify operations completed successfully
        assert len(results) > 0
        ws_results = [r for r in results if r[0] == "ws"]
        tier_results = [r for r in results if r[0] == "tier"]
        conn_results = [r for r in results if r[0] == "conn"]
        
        assert len(ws_results) == 20
        assert len(tier_results) == 15
        assert len(conn_results) == 10
        
        # Verify performance
        assert total_time < 5.0, f"Concurrent operations took {total_time:.2f}s, should be <5s"
        
        # Check final system state
        total_subscriptions = len(ws_manager.user_subscriptions)
        assert total_subscriptions == 35  # 20 + 15 users
        
        final_health = tier_integration.get_health_status()
        assert final_health["status"] in ["healthy", "warning"]
    
    def test_memory_and_resource_management_integration(self, full_system_setup):
        """Test memory and resource management across integrated components."""
        components = full_system_setup
        ws_manager = components["ws_manager"]
        tier_integration = components["tier_integration"]
        
        import sys
        
        # Measure baseline memory usage
        initial_ws_size = sys.getsizeof(ws_manager.user_subscriptions)
        initial_tier_size = sys.getsizeof(tier_integration.stats)
        
        # Perform operations that should manage resources properly
        user_count = 200
        for i in range(user_count):
            # Add subscriptions
            ws_manager.subscribe_user(f"resource_user{i}", "tier_patterns", {
                "symbols": [f"SYM{i % 20}"],
                "confidence_min": 0.7
            })
            
            # Periodically clean up (simulate real-world scenario)
            if i % 50 == 0:
                cleaned = ws_manager.cleanup_inactive_subscriptions(max_inactive_hours=0)
                # Most users should still be active, so minimal cleanup
        
        # Broadcast many events
        for i in range(100):
            event = TierPatternEvent(
                pattern_type="BreakoutBO", symbol=f"SYM{i % 20}",
                tier=PatternTier.DAILY, confidence=0.8,
                event_id=f"resource_test_{i}", timestamp=datetime.now()
            )
            tier_integration.broadcast_tier_pattern_event(event)
        
        # Check memory growth is reasonable
        final_ws_size = sys.getsizeof(ws_manager.user_subscriptions)
        final_tier_size = sys.getsizeof(tier_integration.stats)
        
        ws_growth = final_ws_size - initial_ws_size
        tier_growth = final_tier_size - initial_tier_size
        
        # Memory growth should be reasonable for the operations performed
        assert ws_growth < 5000000, f"WebSocket manager memory grew by {ws_growth} bytes, should be <5MB"
        assert tier_growth < 1000000, f"Tier integration memory grew by {tier_growth} bytes, should be <1MB"
        
        # Verify system is still responsive
        health = tier_integration.get_health_status()
        assert health["status"] in ["healthy", "warning"]
        
        # Check performance metrics are still good
        stats = tier_integration.get_tier_pattern_stats()
        ws_stats = stats["websocket_stats"]
        
        assert ws_stats["active_subscriptions"] > 0
        assert stats["patterns_broadcast"] == 100
        
        # Resource cleanup should work
        cleanup_count = ws_manager.cleanup_inactive_subscriptions(max_inactive_hours=0.001)  # Very short threshold
        # Should clean up some subscriptions if they're deemed inactive
        final_stats = ws_manager.get_subscription_stats()
        
        # System should still be functional after cleanup
        final_health = tier_integration.get_health_status()
        assert final_health["status"] in ["healthy", "warning"]