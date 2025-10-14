"""
Comprehensive unit tests for UniversalWebSocketManager.

Sprint 25 Day 1 Implementation Testing:
- Core scalable WebSocket service for 500+ concurrent users
- User-specific room-based subscriptions with intelligent filtering
- Integration with existing Flask-SocketIO and Redis infrastructure
- Performance metrics and health monitoring
"""

import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
import redis

from src.core.services.websocket_broadcaster import WebSocketBroadcaster

# Import the components under test
from src.core.services.websocket_subscription_manager import (
    UniversalWebSocketManager,
    UserSubscription,
    WebSocketMetrics,
)
from src.presentation.websocket.manager import WebSocketManager


class TestUserSubscription:
    """Test UserSubscription dataclass functionality."""

    def test_user_subscription_creation(self):
        """Test UserSubscription object creation with defaults."""
        subscription = UserSubscription(
            user_id="user123",
            subscription_type="tier_patterns",
            filters={"symbols": ["AAPL", "TSLA"], "confidence_min": 0.7},
            room_name="user_user123"
        )

        assert subscription.user_id == "user123"
        assert subscription.subscription_type == "tier_patterns"
        assert subscription.filters["symbols"] == ["AAPL", "TSLA"]
        assert subscription.room_name == "user_user123"
        assert subscription.active is True
        assert isinstance(subscription.created_at, datetime)
        assert isinstance(subscription.last_activity, datetime)

    def test_update_activity(self):
        """Test activity timestamp update."""
        subscription = UserSubscription(
            user_id="user123",
            subscription_type="tier_patterns",
            filters={},
            room_name="user_user123"
        )

        initial_time = subscription.last_activity
        time.sleep(0.01)  # Small delay
        subscription.update_activity()

        assert subscription.last_activity > initial_time

    def test_matches_criteria_subscription_type(self):
        """Test subscription type matching in criteria."""
        subscription = UserSubscription(
            user_id="user123",
            subscription_type="tier_patterns",
            filters={},
            room_name="user_user123"
        )

        # Should match same subscription type
        assert subscription.matches_criteria({"subscription_type": "tier_patterns"}) is True

        # Should not match different subscription type
        assert subscription.matches_criteria({"subscription_type": "market_insights"}) is False

    def test_matches_criteria_symbol_filtering(self):
        """Test symbol-based filtering in criteria matching."""
        subscription = UserSubscription(
            user_id="user123",
            subscription_type="tier_patterns",
            filters={"symbols": ["AAPL", "TSLA", "MSFT"]},
            room_name="user_user123"
        )

        # Should match symbols in user filter
        assert subscription.matches_criteria({
            "subscription_type": "tier_patterns",
            "symbol": "AAPL"
        }) is True

        assert subscription.matches_criteria({
            "subscription_type": "tier_patterns",
            "symbol": "TSLA"
        }) is True

        # Should not match symbols not in user filter
        assert subscription.matches_criteria({
            "subscription_type": "tier_patterns",
            "symbol": "GOOGL"
        }) is False

    def test_matches_criteria_list_filtering(self):
        """Test filtering with list values."""
        subscription = UserSubscription(
            user_id="user123",
            subscription_type="tier_patterns",
            filters={
                "pattern_types": ["BreakoutBO", "TrendReversal"],
                "tiers": ["daily", "intraday"]
            },
            room_name="user_user123"
        )

        # Should match values in lists
        assert subscription.matches_criteria({
            "subscription_type": "tier_patterns",
            "pattern_type": "BreakoutBO",
            "tier": "daily"
        }) is True

        # Should not match values not in lists
        assert subscription.matches_criteria({
            "subscription_type": "tier_patterns",
            "pattern_type": "SomeOtherPattern"
        }) is False

    def test_matches_criteria_no_filter_accepts_all(self):
        """Test that missing filters accept all values."""
        subscription = UserSubscription(
            user_id="user123",
            subscription_type="tier_patterns",
            filters={},  # No filters
            room_name="user_user123"
        )

        # Should accept any criteria for subscription type
        assert subscription.matches_criteria({
            "subscription_type": "tier_patterns",
            "symbol": "AAPL",
            "pattern_type": "AnyPattern"
        }) is True

    def test_matches_criteria_error_handling(self):
        """Test error handling in criteria matching."""
        subscription = UserSubscription(
            user_id="user123",
            subscription_type="tier_patterns",
            filters={"invalid": object()},  # Non-serializable object
            room_name="user_user123"
        )

        # Should return False on any error
        assert subscription.matches_criteria({
            "subscription_type": "tier_patterns"
        }) is False


class TestWebSocketMetrics:
    """Test WebSocketMetrics dataclass functionality."""

    def test_metrics_initialization(self):
        """Test metrics initialization with defaults."""
        metrics = WebSocketMetrics()

        assert metrics.total_subscriptions == 0
        assert metrics.active_subscriptions == 0
        assert len(metrics.subscriptions_by_type) == 0
        assert metrics.events_broadcast == 0
        assert metrics.events_delivered == 0
        assert metrics.broadcast_latency_ms == 0.0
        assert metrics.filtering_latency_ms == 0.0

    def test_record_subscription(self):
        """Test subscription recording."""
        metrics = WebSocketMetrics()

        metrics.record_subscription("tier_patterns")

        assert metrics.total_subscriptions == 1
        assert metrics.active_subscriptions == 1
        assert metrics.subscriptions_by_type["tier_patterns"] == 1

        metrics.record_subscription("market_insights")

        assert metrics.total_subscriptions == 2
        assert metrics.active_subscriptions == 2
        assert metrics.subscriptions_by_type["market_insights"] == 1

    def test_record_unsubscription(self):
        """Test unsubscription recording."""
        metrics = WebSocketMetrics()
        metrics.record_subscription("tier_patterns")
        metrics.record_subscription("tier_patterns")

        metrics.record_unsubscription("tier_patterns")

        assert metrics.active_subscriptions == 1
        assert metrics.subscriptions_by_type["tier_patterns"] == 1

        # Should not go below zero
        metrics.record_unsubscription("tier_patterns")
        metrics.record_unsubscription("tier_patterns")

        assert metrics.active_subscriptions == 0
        assert metrics.subscriptions_by_type["tier_patterns"] == 0

    def test_record_broadcast(self):
        """Test broadcast recording."""
        metrics = WebSocketMetrics()

        metrics.record_broadcast("tier_pattern", 5, 25.5)

        assert metrics.events_broadcast == 1
        assert metrics.events_delivered == 5
        assert metrics.broadcast_latency_ms == 25.5


class TestUniversalWebSocketManager:
    """Comprehensive tests for UniversalWebSocketManager."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock Flask-SocketIO instance."""
        socketio = Mock()
        socketio.server = Mock()
        socketio.server.enter_room = Mock()
        socketio.server.leave_room = Mock()
        socketio.emit = Mock()
        return socketio

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        redis_client = Mock(spec=redis.Redis)
        return redis_client

    @pytest.fixture
    def mock_ws_manager(self):
        """Mock existing WebSocketManager."""
        ws_manager = Mock(spec=WebSocketManager)
        ws_manager.is_user_connected.return_value = True
        ws_manager.get_user_connections.return_value = {"conn1", "conn2"}
        ws_manager.get_connected_users.return_value = {"user1", "user2"}
        return ws_manager

    @pytest.fixture
    def mock_ws_broadcaster(self):
        """Mock WebSocketBroadcaster."""
        broadcaster = Mock(spec=WebSocketBroadcaster)
        return broadcaster

    @pytest.fixture
    def manager(self, mock_socketio, mock_redis_client, mock_ws_manager, mock_ws_broadcaster):
        """UniversalWebSocketManager instance with mocked dependencies."""
        return UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis_client,
            existing_websocket_manager=mock_ws_manager,
            websocket_broadcaster=mock_ws_broadcaster
        )

    def test_manager_initialization(self, manager, mock_socketio, mock_redis_client,
                                  mock_ws_manager, mock_ws_broadcaster):
        """Test manager initialization."""
        assert manager.socketio is mock_socketio
        assert manager.redis_client is mock_redis_client
        assert manager.existing_ws_manager is mock_ws_manager
        assert manager.websocket_broadcaster is mock_ws_broadcaster
        assert isinstance(manager.metrics, WebSocketMetrics)
        assert len(manager.user_subscriptions) == 0
        assert isinstance(manager.subscription_lock, threading.RLock)
        assert manager.start_time > 0

    def test_subscribe_user_success(self, manager, mock_ws_manager, mock_socketio):
        """Test successful user subscription."""
        filters = {
            "pattern_types": ["BreakoutBO", "TrendReversal"],
            "symbols": ["AAPL", "TSLA"],
            "confidence_min": 0.7
        }

        result = manager.subscribe_user("user123", "tier_patterns", filters)

        assert result is True
        assert "user123" in manager.user_subscriptions
        assert "tier_patterns" in manager.user_subscriptions["user123"]

        subscription = manager.user_subscriptions["user123"]["tier_patterns"]
        assert subscription.user_id == "user123"
        assert subscription.subscription_type == "tier_patterns"
        assert subscription.filters == filters
        assert subscription.room_name == "user_user123"
        assert subscription.active is True

        # Should have updated metrics
        assert manager.metrics.total_subscriptions == 1
        assert manager.metrics.active_subscriptions == 1
        assert manager.metrics.subscriptions_by_type["tier_patterns"] == 1

        # Should have tried to join user to room
        mock_ws_manager.is_user_connected.assert_called_with("user123")
        mock_ws_manager.get_user_connections.assert_called_with("user123")
        mock_socketio.server.enter_room.assert_called()

    def test_subscribe_user_multiple_subscriptions(self, manager):
        """Test user with multiple subscription types."""
        # Subscribe to tier patterns
        result1 = manager.subscribe_user("user123", "tier_patterns", {"symbols": ["AAPL"]})

        # Subscribe to market insights
        result2 = manager.subscribe_user("user123", "market_insights", {"sectors": ["tech"]})

        assert result1 is True
        assert result2 is True
        assert len(manager.user_subscriptions["user123"]) == 2
        assert "tier_patterns" in manager.user_subscriptions["user123"]
        assert "market_insights" in manager.user_subscriptions["user123"]
        assert manager.metrics.total_subscriptions == 2
        assert manager.metrics.active_subscriptions == 2

    def test_subscribe_user_user_not_connected(self, manager, mock_ws_manager):
        """Test subscription when user not connected."""
        mock_ws_manager.is_user_connected.return_value = False

        result = manager.subscribe_user("user123", "tier_patterns", {})

        # Should still succeed but not try to join rooms
        assert result is True
        assert "user123" in manager.user_subscriptions
        mock_ws_manager.get_user_connections.assert_not_called()

    def test_subscribe_user_room_join_error(self, manager, mock_socketio):
        """Test subscription with room join error."""
        mock_socketio.server.enter_room.side_effect = Exception("Room join failed")

        result = manager.subscribe_user("user123", "tier_patterns", {})

        # Should still succeed despite room join error
        assert result is True
        assert "user123" in manager.user_subscriptions

    def test_subscribe_user_error_handling(self, manager, mock_ws_manager):
        """Test subscription error handling."""
        # Force an error during subscription
        mock_ws_manager.is_user_connected.side_effect = Exception("Connection check failed")

        result = manager.subscribe_user("user123", "tier_patterns", {})

        assert result is False
        assert "user123" not in manager.user_subscriptions
        assert manager.metrics.subscription_errors == 1

    def test_unsubscribe_user_specific_type(self, manager):
        """Test unsubscribing from specific subscription type."""
        # Set up subscriptions
        manager.subscribe_user("user123", "tier_patterns", {})
        manager.subscribe_user("user123", "market_insights", {})

        result = manager.unsubscribe_user("user123", "tier_patterns")

        assert result is True
        assert "tier_patterns" not in manager.user_subscriptions["user123"]
        assert "market_insights" in manager.user_subscriptions["user123"]  # Should remain
        assert manager.metrics.active_subscriptions == 1

    def test_unsubscribe_user_all_types(self, manager, mock_ws_manager, mock_socketio):
        """Test unsubscribing from all subscription types."""
        # Set up subscriptions
        manager.subscribe_user("user123", "tier_patterns", {})
        manager.subscribe_user("user123", "market_insights", {})

        result = manager.unsubscribe_user("user123")

        assert result is True
        assert "user123" not in manager.user_subscriptions
        assert manager.metrics.active_subscriptions == 0

        # Should have tried to leave room
        mock_socketio.server.leave_room.assert_called()

    def test_unsubscribe_user_nonexistent(self, manager):
        """Test unsubscribing nonexistent user."""
        result = manager.unsubscribe_user("nonexistent")

        assert result is True  # Should return True for already unsubscribed
        assert "nonexistent" not in manager.user_subscriptions

    def test_unsubscribe_user_room_leave_error(self, manager, mock_socketio):
        """Test unsubscription with room leave error."""
        manager.subscribe_user("user123", "tier_patterns", {})
        mock_socketio.server.leave_room.side_effect = Exception("Leave room failed")

        result = manager.unsubscribe_user("user123")

        # Should still succeed despite room leave error
        assert result is True
        assert "user123" not in manager.user_subscriptions

    def test_broadcast_event_success(self, manager, mock_socketio):
        """Test successful event broadcasting."""
        # Set up subscriptions that should match
        manager.subscribe_user("user1", "tier_patterns", {
            "pattern_types": ["BreakoutBO"],
            "symbols": ["AAPL"]
        })
        manager.subscribe_user("user2", "tier_patterns", {
            "symbols": ["AAPL", "TSLA"]
        })
        manager.subscribe_user("user3", "market_insights", {})  # Different type, should not match

        event_data = {"pattern": "BreakoutBO", "symbol": "AAPL", "confidence": 0.8}
        targeting_criteria = {
            "subscription_type": "tier_patterns",
            "pattern_type": "BreakoutBO",
            "symbol": "AAPL"
        }

        delivery_count = manager.broadcast_event("tier_pattern", event_data, targeting_criteria)

        assert delivery_count == 2  # Should deliver to user1 and user2
        assert manager.metrics.events_broadcast == 1
        assert manager.metrics.events_delivered == 2

        # Should have called socketio.emit for each user
        assert mock_socketio.emit.call_count == 2
        emit_calls = mock_socketio.emit.call_args_list

        # Check emit calls
        for call_args in emit_calls:
            args, kwargs = call_args
            assert args[0] == "tier_pattern"  # event type
            assert "data" in args[1]  # event envelope
            assert "timestamp" in args[1]
            assert kwargs["room"] in ["user_user1", "user_user2"]

    def test_broadcast_event_no_interested_users(self, manager):
        """Test broadcasting with no interested users."""
        manager.subscribe_user("user1", "market_insights", {})  # Different subscription type

        targeting_criteria = {"subscription_type": "tier_patterns"}

        delivery_count = manager.broadcast_event("tier_pattern", {}, targeting_criteria)

        assert delivery_count == 0
        assert manager.metrics.events_broadcast == 1
        assert manager.metrics.events_delivered == 0

    def test_broadcast_event_delivery_error(self, manager, mock_socketio):
        """Test broadcasting with delivery errors."""
        manager.subscribe_user("user1", "tier_patterns", {})
        mock_socketio.emit.side_effect = Exception("Delivery failed")

        delivery_count = manager.broadcast_event("tier_pattern", {}, {
            "subscription_type": "tier_patterns"
        })

        assert delivery_count == 0  # Should have failed to deliver
        assert manager.metrics.broadcast_errors == 1

    def test_broadcast_event_error_handling(self, manager):
        """Test broadcast error handling."""
        # Force error in broadcast
        with patch.object(manager, '_find_interested_users', side_effect=Exception("Find users failed")):
            delivery_count = manager.broadcast_event("tier_pattern", {}, {})

        assert delivery_count == 0
        assert manager.metrics.broadcast_errors == 1

    def test_find_interested_users_performance(self, manager):
        """Test user filtering performance."""
        # Set up many subscriptions
        for i in range(100):
            manager.subscribe_user(f"user{i}", "tier_patterns", {
                "symbols": ["AAPL", "TSLA", "MSFT"][i % 3]
            })

        start_time = time.time()
        interested_users = manager._find_interested_users({
            "subscription_type": "tier_patterns",
            "symbol": "AAPL"
        })
        filtering_time = (time.time() - start_time) * 1000

        # Should find users with AAPL in symbols (every 3rd user)
        expected_count = len([i for i in range(100) if i % 3 == 0])
        assert len(interested_users) == expected_count

        # Should track filtering performance
        assert manager.metrics.filtering_latency_ms == filtering_time

        # Should be fast (target: <5ms for 1000+ subscriptions)
        assert filtering_time < 50  # Generous limit for 100 users

    def test_find_interested_users_slow_filtering_warning(self, manager):
        """Test slow filtering performance warning."""
        # Mock slow filtering
        with patch('time.time', side_effect=[0, 0.01]):  # 10ms elapsed
            with patch('src.core.services.websocket_subscription_manager.logger') as mock_logger:
                manager._find_interested_users({})
                mock_logger.warning.assert_called()
                assert "Slow filtering" in str(mock_logger.warning.call_args)

    def test_find_interested_users_error_handling(self, manager):
        """Test error handling in user filtering."""
        # Set up subscription
        manager.subscribe_user("user1", "tier_patterns", {})

        # Mock subscription to raise error
        with patch.object(manager.user_subscriptions["user1"]["tier_patterns"], 'matches_criteria',
                         side_effect=Exception("Matching failed")):
            interested_users = manager._find_interested_users({"subscription_type": "tier_patterns"})

        assert interested_users == set()  # Should return empty set on error

    def test_handle_user_connection(self, manager, mock_socketio, mock_ws_manager):
        """Test handling user connection."""
        # Set up subscription
        manager.subscribe_user("user123", "tier_patterns", {})

        manager.handle_user_connection("user123", "connection456")

        # Should join user to room
        mock_socketio.server.enter_room.assert_called_with("connection456", "user_user123")

        # Should emit subscription status
        mock_socketio.emit.assert_called_with(
            'subscription_status',
            {
                'active_subscriptions': ['tier_patterns'],
                'room': 'user_user123',
                'timestamp': pytest.approx(time.time(), abs=1)
            },
            room="connection456"
        )

        # Should update connection metrics
        assert manager.metrics.total_connections == 1

    def test_handle_user_connection_no_subscriptions(self, manager, mock_socketio):
        """Test handling connection for user with no subscriptions."""
        manager.handle_user_connection("user123", "connection456")

        # Should not join room or emit status
        mock_socketio.server.enter_room.assert_not_called()
        mock_socketio.emit.assert_not_called()

    def test_handle_user_connection_error(self, manager, mock_socketio):
        """Test connection handling error."""
        manager.subscribe_user("user123", "tier_patterns", {})
        mock_socketio.server.enter_room.side_effect = Exception("Join room failed")

        manager.handle_user_connection("user123", "connection456")

        # Should increment error count
        assert manager.metrics.connection_errors == 1

    def test_handle_user_disconnection(self, manager, mock_ws_manager):
        """Test handling user disconnection."""
        manager.handle_user_disconnection("user123", "connection456")

        # Should update connection metrics
        mock_ws_manager.get_connected_users.assert_called_once()

    def test_get_user_subscriptions(self, manager):
        """Test getting user subscriptions."""
        # Set up subscriptions
        manager.subscribe_user("user123", "tier_patterns", {"symbols": ["AAPL"]})
        manager.subscribe_user("user123", "market_insights", {"sectors": ["tech"]})

        subscriptions = manager.get_user_subscriptions("user123")

        assert len(subscriptions) == 2
        assert "tier_patterns" in subscriptions
        assert "market_insights" in subscriptions
        assert subscriptions["tier_patterns"].filters["symbols"] == ["AAPL"]
        assert subscriptions["market_insights"].filters["sectors"] == ["tech"]

        # Should return copy, not original
        subscriptions["tier_patterns"].active = False
        assert manager.user_subscriptions["user123"]["tier_patterns"].active is True

    def test_get_user_subscriptions_nonexistent(self, manager):
        """Test getting subscriptions for nonexistent user."""
        subscriptions = manager.get_user_subscriptions("nonexistent")

        assert subscriptions == {}

    def test_get_subscription_stats(self, manager):
        """Test getting subscription statistics."""
        # Set up some data
        manager.subscribe_user("user1", "tier_patterns", {})
        manager.subscribe_user("user2", "tier_patterns", {})
        manager.subscribe_user("user2", "market_insights", {})
        manager.broadcast_event("tier_pattern", {}, {"subscription_type": "tier_patterns"})

        stats = manager.get_subscription_stats()

        assert stats["total_users"] == 2
        assert stats["total_subscriptions"] == 3
        assert stats["active_subscriptions"] == 3
        assert stats["subscription_breakdown"]["tier_patterns"] == 2
        assert stats["subscription_breakdown"]["market_insights"] == 1
        assert stats["events_broadcast"] == 1
        assert stats["events_delivered"] == 2  # Delivered to 2 users with tier_patterns
        assert "avg_broadcast_latency_ms" in stats
        assert "avg_filtering_latency_ms" in stats
        assert "runtime_seconds" in stats
        assert "uptime_hours" in stats
        assert "last_updated" in stats

    def test_get_health_status_healthy(self, manager):
        """Test health status when system is healthy."""
        health = manager.get_health_status()

        assert health["status"] == "healthy"
        assert "healthy" in health["message"].lower()
        assert health["timestamp"] > 0
        assert "stats" in health
        assert "performance_targets" in health
        assert health["performance_targets"]["filtering_target_ms"] == 5.0
        assert health["performance_targets"]["broadcast_target_ms"] == 100.0
        assert health["performance_targets"]["target_concurrent_users"] == 500

    def test_get_health_status_high_errors(self, manager):
        """Test health status with high error rates."""
        # Simulate errors
        manager.metrics.subscription_errors = 15
        manager.metrics.broadcast_errors = 12

        health = manager.get_health_status()

        assert health["status"] == "error"
        assert "High error rate" in health["message"]
        assert "15 subscription" in health["message"]
        assert "12 broadcast" in health["message"]

    def test_get_health_status_slow_filtering(self, manager):
        """Test health status with slow filtering."""
        manager.metrics.filtering_latency_ms = 15.0

        health = manager.get_health_status()

        assert health["status"] == "warning"
        assert "Slow filtering performance" in health["message"]
        assert "15.0ms" in health["message"]

    def test_get_health_status_slow_broadcast(self, manager):
        """Test health status with slow broadcasting."""
        manager.metrics.broadcast_latency_ms = 150.0

        health = manager.get_health_status()

        assert health["status"] == "warning"
        assert "Slow broadcast performance" in health["message"]
        assert "150.0ms" in health["message"]

    def test_cleanup_inactive_subscriptions(self, manager, mock_ws_manager):
        """Test cleanup of inactive subscriptions."""
        # Set up subscriptions with different activity times
        manager.subscribe_user("user1", "tier_patterns", {})
        manager.subscribe_user("user2", "tier_patterns", {})
        manager.subscribe_user("user3", "market_insights", {})

        # Make user1 subscription very old
        old_time = datetime.now() - timedelta(hours=25)
        manager.user_subscriptions["user1"]["tier_patterns"].last_activity = old_time

        # User1 is not connected
        mock_ws_manager.is_user_connected.side_effect = lambda user_id: user_id != "user1"

        cleaned_count = manager.cleanup_inactive_subscriptions(max_inactive_hours=24)

        assert cleaned_count == 1
        assert "user1" not in manager.user_subscriptions  # Should be removed
        assert "user2" in manager.user_subscriptions      # Should remain
        assert "user3" in manager.user_subscriptions      # Should remain

    def test_cleanup_inactive_subscriptions_connected_user_kept(self, manager, mock_ws_manager):
        """Test that connected users are kept even if inactive."""
        manager.subscribe_user("user1", "tier_patterns", {})

        # Make subscription very old but user is connected
        old_time = datetime.now() - timedelta(hours=25)
        manager.user_subscriptions["user1"]["tier_patterns"].last_activity = old_time
        mock_ws_manager.is_user_connected.return_value = True

        cleaned_count = manager.cleanup_inactive_subscriptions(max_inactive_hours=24)

        assert cleaned_count == 0
        assert "user1" in manager.user_subscriptions  # Should be kept

    def test_cleanup_inactive_subscriptions_error_handling(self, manager):
        """Test cleanup error handling."""
        manager.subscribe_user("user1", "tier_patterns", {})

        # Force error during cleanup
        with patch.object(manager.existing_ws_manager, 'is_user_connected',
                         side_effect=Exception("Connection check failed")):
            cleaned_count = manager.cleanup_inactive_subscriptions()

        assert cleaned_count == 0  # Should return 0 on error

    def test_thread_safety_concurrent_operations(self, manager):
        """Test thread safety of concurrent subscription operations."""
        results = []
        errors = []

        def subscribe_worker(user_prefix: str):
            try:
                for i in range(10):
                    user_id = f"{user_prefix}_user{i}"
                    result = manager.subscribe_user(user_id, "tier_patterns", {"symbols": ["AAPL"]})
                    results.append(result)
            except Exception as e:
                errors.append(e)

        def unsubscribe_worker(user_prefix: str):
            try:
                for i in range(5):
                    user_id = f"{user_prefix}_user{i}"
                    result = manager.unsubscribe_user(user_id, "tier_patterns")
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Run concurrent operations
        threads = []
        for i in range(3):
            t1 = threading.Thread(target=subscribe_worker, args=[f"sub{i}"])
            t2 = threading.Thread(target=unsubscribe_worker, args=[f"unsub{i}"])
            threads.extend([t1, t2])

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should not have any errors
        assert len(errors) == 0
        assert len(results) > 0
        assert all(isinstance(r, bool) for r in results)


class TestPerformanceRequirements:
    """Test performance requirements for Sprint 25."""

    @pytest.fixture
    def manager_with_many_users(self, mock_socketio, mock_redis_client,
                               mock_ws_manager, mock_ws_broadcaster):
        """Manager with many user subscriptions for performance testing."""
        manager = UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis_client,
            existing_websocket_manager=mock_ws_manager,
            websocket_broadcaster=mock_ws_broadcaster
        )

        # Set up 100 user subscriptions
        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
        pattern_types = ["BreakoutBO", "TrendReversal", "SurgePattern"]

        for i in range(100):
            filters = {
                "symbols": [symbols[i % len(symbols)]],
                "pattern_types": [pattern_types[i % len(pattern_types)]],
                "confidence_min": 0.6 + (i % 4) * 0.1
            }
            manager.subscribe_user(f"user{i}", "tier_patterns", filters)

        return manager

    @pytest.mark.performance
    def test_filtering_performance_target(self, manager_with_many_users):
        """Test that user filtering meets <5ms target for 100+ subscriptions."""
        start_time = time.time()

        # Run filtering multiple times to get average
        iterations = 50
        for _ in range(iterations):
            interested_users = manager_with_many_users._find_interested_users({
                "subscription_type": "tier_patterns",
                "symbol": "AAPL",
                "pattern_type": "BreakoutBO"
            })

        total_time = (time.time() - start_time) * 1000  # Convert to ms
        avg_time_per_filtering = total_time / iterations

        # Should be under 5ms per filtering operation
        assert avg_time_per_filtering < 5.0, f"Filtering took {avg_time_per_filtering:.2f}ms, target <5ms"

        # Should find some users
        assert len(interested_users) > 0

    @pytest.mark.performance
    def test_broadcast_performance_target(self, manager_with_many_users, mock_socketio):
        """Test that broadcasting meets <100ms target."""
        event_data = {"pattern": "BreakoutBO", "symbol": "AAPL", "confidence": 0.8}
        targeting_criteria = {
            "subscription_type": "tier_patterns",
            "symbol": "AAPL",
            "pattern_type": "BreakoutBO"
        }

        start_time = time.time()
        delivery_count = manager_with_many_users.broadcast_event(
            "tier_pattern", event_data, targeting_criteria
        )
        broadcast_time = (time.time() - start_time) * 1000

        # Should complete in under 100ms
        assert broadcast_time < 100.0, f"Broadcasting took {broadcast_time:.2f}ms, target <100ms"

        # Should deliver to some users
        assert delivery_count > 0

        # Metrics should record the broadcast time
        assert manager_with_many_users.metrics.broadcast_latency_ms == broadcast_time

    @pytest.mark.performance
    def test_memory_usage_scalability(self, mock_socketio, mock_redis_client,
                                    mock_ws_manager, mock_ws_broadcaster):
        """Test memory usage stays reasonable with many subscriptions."""
        manager = UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis_client,
            existing_websocket_manager=mock_ws_manager,
            websocket_broadcaster=mock_ws_broadcaster
        )

        import sys

        # Measure initial memory usage
        initial_size = sys.getsizeof(manager.user_subscriptions)

        # Add 500 user subscriptions (target scalability)
        for i in range(500):
            manager.subscribe_user(f"user{i}", "tier_patterns", {
                "symbols": [f"SYMBOL{i % 100}"],
                "confidence_min": 0.7
            })

        # Measure final memory usage
        final_size = sys.getsizeof(manager.user_subscriptions)
        memory_per_subscription = (final_size - initial_size) / 500

        # Should be reasonable per subscription (target: <1MB per 100 subscriptions = ~10KB per subscription)
        assert memory_per_subscription < 50000, f"Memory per subscription: {memory_per_subscription} bytes"

        # Should have all subscriptions
        assert len(manager.user_subscriptions) == 500
        assert manager.metrics.active_subscriptions == 500

    @pytest.mark.performance
    def test_concurrent_user_handling(self, mock_socketio, mock_redis_client,
                                    mock_ws_manager, mock_ws_broadcaster):
        """Test concurrent operations with 100+ users."""
        manager = UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis_client,
            existing_websocket_manager=mock_ws_manager,
            websocket_broadcaster=mock_ws_broadcaster
        )

        start_time = time.time()

        def concurrent_operations():
            # Each thread performs multiple operations
            for i in range(20):
                user_id = f"user{threading.current_thread().ident}_{i}"
                manager.subscribe_user(user_id, "tier_patterns", {"symbols": ["AAPL"]})
                manager.broadcast_event("tier_pattern", {}, {"subscription_type": "tier_patterns"})
                if i % 5 == 0:  # Occasional unsubscribe
                    manager.unsubscribe_user(user_id)

        # Run 10 concurrent threads (200 operations each = 2000 total operations)
        threads = []
        for _ in range(10):
            t = threading.Thread(target=concurrent_operations)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        total_time = (time.time() - start_time) * 1000

        # Should complete all operations in reasonable time
        assert total_time < 5000, f"Concurrent operations took {total_time:.2f}ms"

        # Should have processed subscriptions
        assert manager.metrics.total_subscriptions > 0
        assert manager.metrics.events_broadcast > 0
