"""
Comprehensive unit tests for TierPatternWebSocketIntegration.

Sprint 25 Day 1 Implementation Testing:
- High-level WebSocket integration wrapper for tier-specific patterns
- User subscription preferences management
- Event broadcasting and alert generation
- Integration with UniversalWebSocketManager
"""

import time
from datetime import datetime
from unittest.mock import Mock

import pytest

from src.core.domain.events.tier_events import (
    EventPriority,
    MarketRegime,
    MarketStateEvent,
    PatternAlertEvent,
    PatternTier,
    TierPatternEvent,
)

# Import the components under test
from src.core.services.tier_pattern_websocket_integration import (
    TierPatternWebSocketIntegration,
    TierSubscriptionPreferences,
    create_daily_pattern_subscription,
    create_high_confidence_subscription,
    create_specific_pattern_subscription,
)
from src.core.services.websocket_subscription_manager import UniversalWebSocketManager


class TestTierSubscriptionPreferences:
    """Test TierSubscriptionPreferences dataclass functionality."""

    def test_tier_subscription_preferences_creation(self):
        """Test TierSubscriptionPreferences creation with all parameters."""
        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO", "TrendReversal"],
            symbols=["AAPL", "TSLA", "MSFT"],
            tiers=[PatternTier.DAILY, PatternTier.INTRADAY],
            confidence_min=0.8,
            priority_min=EventPriority.HIGH,
            max_events_per_hour=100,
            enable_market_hours_only=True
        )

        assert preferences.pattern_types == ["BreakoutBO", "TrendReversal"]
        assert preferences.symbols == ["AAPL", "TSLA", "MSFT"]
        assert preferences.tiers == [PatternTier.DAILY, PatternTier.INTRADAY]
        assert preferences.confidence_min == 0.8
        assert preferences.priority_min == EventPriority.HIGH
        assert preferences.max_events_per_hour == 100
        assert preferences.enable_market_hours_only is True

    def test_tier_subscription_preferences_defaults(self):
        """Test TierSubscriptionPreferences with default values."""
        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY]
        )

        # Check defaults
        assert preferences.confidence_min == 0.6
        assert preferences.priority_min == EventPriority.MEDIUM
        assert preferences.max_events_per_hour == 50
        assert preferences.enable_market_hours_only is False

    def test_to_filter_dict(self):
        """Test conversion to filter dictionary format."""
        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO", "TrendReversal"],
            symbols=["AAPL", "TSLA"],
            tiers=[PatternTier.DAILY, PatternTier.COMBO],
            confidence_min=0.75,
            priority_min=EventPriority.HIGH,
            max_events_per_hour=75,
            enable_market_hours_only=True
        )

        filter_dict = preferences.to_filter_dict()

        expected = {
            "pattern_types": ["BreakoutBO", "TrendReversal"],
            "symbols": ["AAPL", "TSLA"],
            "tiers": ["daily", "combo"],  # Should convert enum values to strings
            "confidence_min": 0.75,
            "priority_min": "high",       # Should convert enum value to string
            "max_events_per_hour": 75,
            "market_hours_only": True
        }

        assert filter_dict == expected


class TestTierPatternWebSocketIntegration:
    """Comprehensive tests for TierPatternWebSocketIntegration."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock UniversalWebSocketManager."""
        manager = Mock(spec=UniversalWebSocketManager)
        manager.subscribe_user.return_value = True
        manager.unsubscribe_user.return_value = True
        manager.broadcast_event.return_value = 5  # 5 users delivered to
        manager.get_user_subscriptions.return_value = {}
        manager.get_subscription_stats.return_value = {
            "total_users": 10,
            "active_subscriptions": 15,
            "events_broadcast": 100,
            "events_delivered": 250
        }
        return manager

    @pytest.fixture
    def integration(self, mock_websocket_manager):
        """TierPatternWebSocketIntegration instance with mocked dependencies."""
        return TierPatternWebSocketIntegration(websocket_manager=mock_websocket_manager)

    def test_integration_initialization(self, integration, mock_websocket_manager):
        """Test integration service initialization."""
        assert integration.websocket_manager is mock_websocket_manager
        assert isinstance(integration.stats, dict)

        # Check initial stats
        assert integration.stats["tier_subscriptions"] == 0
        assert integration.stats["patterns_broadcast"] == 0
        assert integration.stats["market_updates_sent"] == 0
        assert integration.stats["alerts_generated"] == 0
        assert integration.stats["last_pattern_time"] is None
        assert integration.stats["start_time"] > 0

    def test_subscribe_user_to_tier_patterns_success(self, integration, mock_websocket_manager):
        """Test successful user subscription to tier patterns."""
        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO", "TrendReversal"],
            symbols=["AAPL", "TSLA", "MSFT"],
            tiers=[PatternTier.DAILY, PatternTier.INTRADAY],
            confidence_min=0.75,
            priority_min=EventPriority.HIGH
        )

        result = integration.subscribe_user_to_tier_patterns("user123", preferences)

        assert result is True

        # Should call websocket manager with correct parameters
        mock_websocket_manager.subscribe_user.assert_called_once_with(
            user_id="user123",
            subscription_type="tier_patterns",
            filters={
                "pattern_types": ["BreakoutBO", "TrendReversal"],
                "symbols": ["AAPL", "TSLA", "MSFT"],
                "tiers": ["daily", "intraday"],
                "confidence_min": 0.75,
                "priority_min": "high",
                "max_events_per_hour": 50,  # Default
                "market_hours_only": False  # Default
            }
        )

        # Should update stats
        assert integration.stats["tier_subscriptions"] == 1

    def test_subscribe_user_to_tier_patterns_failure(self, integration, mock_websocket_manager):
        """Test failed user subscription to tier patterns."""
        mock_websocket_manager.subscribe_user.return_value = False

        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY]
        )

        result = integration.subscribe_user_to_tier_patterns("user123", preferences)

        assert result is False

        # Stats should not be updated on failure
        assert integration.stats["tier_subscriptions"] == 0

    def test_subscribe_user_to_tier_patterns_error_handling(self, integration, mock_websocket_manager):
        """Test error handling during subscription."""
        mock_websocket_manager.subscribe_user.side_effect = Exception("Subscription failed")

        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY]
        )

        result = integration.subscribe_user_to_tier_patterns("user123", preferences)

        assert result is False
        assert integration.stats["tier_subscriptions"] == 0

    def test_unsubscribe_user_from_tier_patterns_success(self, integration, mock_websocket_manager):
        """Test successful user unsubscription."""
        result = integration.unsubscribe_user_from_tier_patterns("user123")

        assert result is True
        mock_websocket_manager.unsubscribe_user.assert_called_once_with("user123", "tier_patterns")

    def test_unsubscribe_user_from_tier_patterns_failure(self, integration, mock_websocket_manager):
        """Test failed user unsubscription."""
        mock_websocket_manager.unsubscribe_user.return_value = False

        result = integration.unsubscribe_user_from_tier_patterns("user123")

        assert result is False

    def test_unsubscribe_user_from_tier_patterns_error_handling(self, integration, mock_websocket_manager):
        """Test error handling during unsubscription."""
        mock_websocket_manager.unsubscribe_user.side_effect = Exception("Unsubscription failed")

        result = integration.unsubscribe_user_from_tier_patterns("user123")

        assert result is False

    def test_broadcast_tier_pattern_event_success(self, integration, mock_websocket_manager):
        """Test successful tier pattern event broadcasting."""
        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.85,
            event_id="broadcast_test_123",
            timestamp=datetime(2025, 1, 1, 10, 0, 0),
            priority=EventPriority.HIGH
        )

        delivery_count = integration.broadcast_tier_pattern_event(pattern_event)

        assert delivery_count == 5  # Mock returns 5

        # Should call websocket manager with correct parameters
        expected_criteria = {
            "subscription_type": "tier_patterns",
            "pattern_type": "BreakoutBO",
            "symbol": "AAPL",
            "tier": "daily",
            "confidence": 0.85,
            "priority": "high"
        }

        mock_websocket_manager.broadcast_event.assert_called_once_with(
            event_type="tier_pattern",
            event_data=pattern_event.to_websocket_dict(),
            targeting_criteria=expected_criteria
        )

        # Should update stats
        assert integration.stats["patterns_broadcast"] == 1
        assert integration.stats["last_pattern_time"] > 0

    def test_broadcast_tier_pattern_event_error_handling(self, integration, mock_websocket_manager):
        """Test error handling during pattern broadcasting."""
        mock_websocket_manager.broadcast_event.side_effect = Exception("Broadcast failed")

        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.85,
            event_id="error_test",
            timestamp=datetime.now()
        )

        delivery_count = integration.broadcast_tier_pattern_event(pattern_event)

        assert delivery_count == 0
        # Stats should still be updated for attempt
        assert integration.stats["patterns_broadcast"] == 0  # Should not increment on error

    def test_broadcast_market_state_update_success(self, integration, mock_websocket_manager):
        """Test successful market state update broadcasting."""
        market_event = MarketStateEvent(
            regime=MarketRegime.BULL,
            regime_confidence=0.85,
            etf_performance={"SPY": 0.02, "QQQ": 0.03},
            sector_strength={"Technology": 0.025},
            event_id="market_test_456",
            timestamp=datetime(2025, 1, 1, 15, 30, 0),
            volatility_regime="low"
        )

        delivery_count = integration.broadcast_market_state_update(market_event)

        assert delivery_count == 5  # Mock returns 5

        expected_criteria = {
            "subscription_type": "market_insights",
            "market_regime": "bull",
            "volatility_regime": "low"
        }

        mock_websocket_manager.broadcast_event.assert_called_once_with(
            event_type="market_state_update",
            event_data=market_event.to_websocket_dict(),
            targeting_criteria=expected_criteria
        )

        # Should update stats
        assert integration.stats["market_updates_sent"] == 1

    def test_broadcast_market_state_update_error_handling(self, integration, mock_websocket_manager):
        """Test error handling during market state broadcasting."""
        mock_websocket_manager.broadcast_event.side_effect = Exception("Market broadcast failed")

        market_event = MarketStateEvent(
            regime=MarketRegime.BEAR,
            regime_confidence=0.7,
            etf_performance={},
            sector_strength={},
            event_id="market_error_test",
            timestamp=datetime.now()
        )

        delivery_count = integration.broadcast_market_state_update(market_event)

        assert delivery_count == 0
        assert integration.stats["market_updates_sent"] == 0

    def test_generate_pattern_alert(self, integration):
        """Test pattern alert generation."""
        pattern_event = TierPatternEvent(
            pattern_type="TrendReversal",
            symbol="TSLA",
            tier=PatternTier.INTRADAY,
            confidence=0.92,
            event_id="pattern_alert_source",
            timestamp=datetime(2025, 1, 1, 12, 15, 0),
            priority=EventPriority.HIGH
        )

        user_filters = {
            "symbols": ["TSLA"],
            "pattern_types": ["TrendReversal"],
            "confidence_min": 0.9
        }

        alert = integration.generate_pattern_alert("user789", pattern_event, user_filters)

        assert isinstance(alert, PatternAlertEvent)
        assert alert.alert_id == "alert_user789_pattern_alert_source"
        assert alert.user_id == "user789"
        assert alert.pattern_event == pattern_event
        assert alert.user_filters == user_filters
        assert alert.alert_priority == EventPriority.CRITICAL  # High confidence -> CRITICAL
        assert alert.delivery_channels == ["websocket"]

        # Should update stats
        assert integration.stats["alerts_generated"] == 1

    def test_generate_pattern_alert_priority_assignment(self, integration):
        """Test alert priority assignment based on pattern confidence."""
        # Test CRITICAL priority (>= 0.9)
        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO", symbol="AAPL", tier=PatternTier.DAILY,
            confidence=0.95, event_id="crit_test", timestamp=datetime.now()
        )
        alert = integration.generate_pattern_alert("user1", pattern_event, {})
        assert alert.alert_priority == EventPriority.CRITICAL

        # Test HIGH priority (>= 0.8)
        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO", symbol="AAPL", tier=PatternTier.DAILY,
            confidence=0.85, event_id="high_test", timestamp=datetime.now(),
            priority=EventPriority.MEDIUM  # Should be overridden
        )
        alert = integration.generate_pattern_alert("user1", pattern_event, {})
        assert alert.alert_priority == EventPriority.HIGH

        # Test keeping original priority (< 0.8)
        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO", symbol="AAPL", tier=PatternTier.DAILY,
            confidence=0.7, event_id="med_test", timestamp=datetime.now(),
            priority=EventPriority.MEDIUM
        )
        alert = integration.generate_pattern_alert("user1", pattern_event, {})
        assert alert.alert_priority == EventPriority.MEDIUM  # Should keep original

    def test_generate_pattern_alert_error_handling(self, integration):
        """Test error handling during alert generation."""
        # Force an error by passing invalid data
        pattern_event = Mock()
        pattern_event.confidence = "invalid"  # Non-numeric
        pattern_event.event_id = "error_test"

        alert = integration.generate_pattern_alert("user123", pattern_event, {})

        assert alert is None
        assert integration.stats["alerts_generated"] == 0  # Should not increment on error

    def test_broadcast_pattern_alert_success(self, integration, mock_websocket_manager):
        """Test successful pattern alert broadcasting."""
        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO", symbol="AAPL", tier=PatternTier.DAILY,
            confidence=0.8, event_id="alert_broadcast_test", timestamp=datetime.now()
        )

        alert_event = PatternAlertEvent(
            alert_id="test_alert_123",
            user_id="user456",
            timestamp=datetime.now(),
            pattern_event=pattern_event
        )

        mock_websocket_manager.broadcast_event.return_value = 1  # Delivered to 1 user

        result = integration.broadcast_pattern_alert(alert_event)

        assert result is True

        expected_criteria = {
            "subscription_type": "pattern_alerts",
            "user_id": "user456"
        }

        mock_websocket_manager.broadcast_event.assert_called_once_with(
            event_type="pattern_alert",
            event_data=alert_event.to_websocket_dict(),
            targeting_criteria=expected_criteria
        )

    def test_broadcast_pattern_alert_not_delivered(self, integration, mock_websocket_manager):
        """Test pattern alert not delivered (user offline)."""
        alert_event = PatternAlertEvent(
            alert_id="offline_test",
            user_id="offline_user",
            timestamp=datetime.now(),
            pattern_event=Mock()
        )

        mock_websocket_manager.broadcast_event.return_value = 0  # Not delivered

        result = integration.broadcast_pattern_alert(alert_event)

        assert result is False

    def test_broadcast_pattern_alert_error_handling(self, integration, mock_websocket_manager):
        """Test error handling during alert broadcasting."""
        mock_websocket_manager.broadcast_event.side_effect = Exception("Alert broadcast failed")

        alert_event = PatternAlertEvent(
            alert_id="error_alert",
            user_id="user123",
            timestamp=datetime.now(),
            pattern_event=Mock()
        )

        result = integration.broadcast_pattern_alert(alert_event)

        assert result is False

    def test_get_user_tier_subscriptions_found(self, integration, mock_websocket_manager):
        """Test getting user tier subscriptions when found."""
        from src.core.services.websocket_subscription_manager import UserSubscription

        # Mock subscription data
        subscription = UserSubscription(
            user_id="user123",
            subscription_type="tier_patterns",
            filters={"symbols": ["AAPL"], "confidence_min": 0.8},
            room_name="user_user123"
        )

        mock_websocket_manager.get_user_subscriptions.return_value = {
            "tier_patterns": subscription
        }

        result = integration.get_user_tier_subscriptions("user123")

        assert result is not None
        assert result["subscription_type"] == "tier_patterns"
        assert result["filters"] == {"symbols": ["AAPL"], "confidence_min": 0.8}
        assert result["active"] is True
        assert "created_at" in result
        assert "last_activity" in result

        mock_websocket_manager.get_user_subscriptions.assert_called_once_with("user123")

    def test_get_user_tier_subscriptions_not_found(self, integration, mock_websocket_manager):
        """Test getting user tier subscriptions when not found."""
        mock_websocket_manager.get_user_subscriptions.return_value = {}

        result = integration.get_user_tier_subscriptions("user123")

        assert result is None

    def test_get_user_tier_subscriptions_error_handling(self, integration, mock_websocket_manager):
        """Test error handling when getting user subscriptions."""
        mock_websocket_manager.get_user_subscriptions.side_effect = Exception("Get subscriptions failed")

        result = integration.get_user_tier_subscriptions("user123")

        assert result is None

    def test_get_tier_pattern_stats(self, integration, mock_websocket_manager):
        """Test getting tier pattern integration statistics."""
        # Set up some stats
        integration.stats["tier_subscriptions"] = 5
        integration.stats["patterns_broadcast"] = 50
        integration.stats["market_updates_sent"] = 10
        integration.stats["alerts_generated"] = 25
        integration.stats["last_pattern_time"] = time.time() - 100
        integration.stats["start_time"] = time.time() - 3600  # 1 hour ago

        stats = integration.get_tier_pattern_stats()

        # Check tier-specific stats
        assert stats["tier_subscriptions"] == 5
        assert stats["patterns_broadcast"] == 50
        assert stats["market_updates_sent"] == 10
        assert stats["alerts_generated"] == 25
        assert "patterns_per_minute" in stats
        assert stats["patterns_per_minute"] > 0  # Should calculate rate
        assert stats["last_pattern_time"] == integration.stats["last_pattern_time"]

        # Check WebSocket stats inclusion
        assert "websocket_stats" in stats
        assert stats["websocket_stats"]["total_users"] == 10

        # Check runtime metrics
        assert "runtime_seconds" in stats
        assert "service_uptime_hours" in stats
        assert "last_updated" in stats
        assert stats["runtime_seconds"] > 0
        assert stats["service_uptime_hours"] > 0

        mock_websocket_manager.get_subscription_stats.assert_called_once()

    def test_get_tier_pattern_stats_error_handling(self, integration, mock_websocket_manager):
        """Test error handling when getting statistics."""
        mock_websocket_manager.get_subscription_stats.side_effect = Exception("Stats failed")

        stats = integration.get_tier_pattern_stats()

        assert "error" in stats
        assert "Stats failed" in stats["error"]
        assert "last_updated" in stats

    def test_get_health_status_healthy(self, integration, mock_websocket_manager):
        """Test health status when system is healthy."""
        # Mock healthy WebSocket manager
        mock_websocket_manager.get_health_status.return_value = {
            "status": "healthy",
            "message": "All good"
        }

        # Set up some activity
        integration.stats["tier_subscriptions"] = 10
        integration.stats["patterns_broadcast"] = 50
        integration.stats["last_pattern_time"] = time.time() - 30  # Recent activity

        health = integration.get_health_status()

        assert health["service"] == "tier_pattern_websocket_integration"
        assert health["status"] == "healthy"
        assert "healthy" in health["message"].lower()
        assert "10 subscriptions" in health["message"]
        assert "stats" in health
        assert "websocket_health" in health

    def test_get_health_status_websocket_unhealthy(self, integration, mock_websocket_manager):
        """Test health status when WebSocket manager is unhealthy."""
        mock_websocket_manager.get_health_status.return_value = {
            "status": "error",
            "message": "WebSocket errors detected"
        }

        health = integration.get_health_status()

        assert health["status"] == "error"
        assert "WebSocket manager unhealthy" in health["message"]
        assert "WebSocket errors detected" in health["message"]

    def test_get_health_status_no_patterns(self, integration, mock_websocket_manager):
        """Test health status when no patterns have been broadcast."""
        mock_websocket_manager.get_health_status.return_value = {
            "status": "healthy", "message": "All good"
        }

        # Set start time to >10 minutes ago but no patterns broadcast
        integration.stats["start_time"] = time.time() - 700  # 11+ minutes ago
        integration.stats["patterns_broadcast"] = 0

        health = integration.get_health_status()

        assert health["status"] == "warning"
        assert "No patterns broadcast in last 10 minutes" in health["message"]

    def test_get_health_status_old_pattern(self, integration, mock_websocket_manager):
        """Test health status when last pattern is old."""
        mock_websocket_manager.get_health_status.return_value = {
            "status": "healthy", "message": "All good"
        }

        # Set last pattern time to >1 hour ago
        integration.stats["patterns_broadcast"] = 10
        integration.stats["last_pattern_time"] = time.time() - 3700  # >1 hour ago

        health = integration.get_health_status()

        assert health["status"] == "warning"
        assert "Last pattern received" in health["message"]
        assert "minutes ago" in health["message"]

    def test_get_health_status_error_handling(self, integration, mock_websocket_manager):
        """Test error handling in health status check."""
        mock_websocket_manager.get_health_status.side_effect = Exception("Health check failed")

        health = integration.get_health_status()

        assert health["service"] == "tier_pattern_websocket_integration"
        assert health["status"] == "error"
        assert "Health check failed" in health["message"]


class TestConvenienceFunctions:
    """Test convenience functions for creating subscription preferences."""

    def test_create_daily_pattern_subscription(self):
        """Test creating daily pattern subscription."""
        symbols = ["AAPL", "TSLA", "MSFT"]
        preferences = create_daily_pattern_subscription("user123", symbols, confidence_min=0.8)

        assert preferences.pattern_types == []  # All patterns
        assert preferences.symbols == symbols
        assert preferences.tiers == [PatternTier.DAILY]
        assert preferences.confidence_min == 0.8
        assert preferences.priority_min == EventPriority.MEDIUM

    def test_create_daily_pattern_subscription_defaults(self):
        """Test creating daily pattern subscription with defaults."""
        symbols = ["GOOGL"]
        preferences = create_daily_pattern_subscription("user456", symbols)

        assert preferences.confidence_min == 0.7  # Default
        assert preferences.tiers == [PatternTier.DAILY]
        assert preferences.priority_min == EventPriority.MEDIUM

    def test_create_high_confidence_subscription(self):
        """Test creating high confidence subscription."""
        symbols = ["AAPL", "TSLA"]
        preferences = create_high_confidence_subscription("user789", symbols)

        assert preferences.pattern_types == []  # All patterns
        assert preferences.symbols == symbols
        assert preferences.tiers == [PatternTier.DAILY, PatternTier.INTRADAY, PatternTier.COMBO]
        assert preferences.confidence_min == 0.8
        assert preferences.priority_min == EventPriority.HIGH

    def test_create_specific_pattern_subscription(self):
        """Test creating subscription for specific patterns."""
        pattern_types = ["BreakoutBO", "TrendReversal"]
        symbols = ["AAPL", "MSFT", "GOOGL"]
        preferences = create_specific_pattern_subscription("user101", pattern_types, symbols)

        assert preferences.pattern_types == pattern_types
        assert preferences.symbols == symbols
        assert preferences.tiers == [PatternTier.DAILY, PatternTier.INTRADAY, PatternTier.COMBO]
        assert preferences.confidence_min == 0.6
        assert preferences.priority_min == EventPriority.MEDIUM


class TestIntegrationWorkflows:
    """Test complete workflows combining multiple operations."""

    @pytest.fixture
    def integration(self):
        """Integration instance with mock WebSocket manager."""
        mock_manager = Mock(spec=UniversalWebSocketManager)
        mock_manager.subscribe_user.return_value = True
        mock_manager.broadcast_event.return_value = 3
        return TierPatternWebSocketIntegration(websocket_manager=mock_manager)

    def test_complete_subscription_and_broadcast_workflow(self, integration):
        """Test complete workflow: subscribe user, broadcast event, generate alert."""
        # 1. Subscribe user to tier patterns
        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY],
            confidence_min=0.8
        )

        subscribe_result = integration.subscribe_user_to_tier_patterns("user123", preferences)
        assert subscribe_result is True

        # 2. Broadcast tier pattern event
        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.9,
            event_id="workflow_test",
            timestamp=datetime.now(),
            priority=EventPriority.HIGH
        )

        delivery_count = integration.broadcast_tier_pattern_event(pattern_event)
        assert delivery_count == 3

        # 3. Generate pattern alert
        alert = integration.generate_pattern_alert(
            "user123", pattern_event, {"symbols": ["AAPL"]}
        )

        assert alert is not None
        assert alert.user_id == "user123"
        assert alert.pattern_event == pattern_event

        # 4. Broadcast alert
        alert_result = integration.broadcast_pattern_alert(alert)
        assert alert_result is True  # Mock returns 3 > 0

        # Check final stats
        assert integration.stats["tier_subscriptions"] == 1
        assert integration.stats["patterns_broadcast"] == 1
        assert integration.stats["alerts_generated"] == 1

    def test_multiple_user_subscription_management(self, integration):
        """Test managing subscriptions for multiple users."""
        users_and_preferences = [
            ("user1", ["AAPL"], ["BreakoutBO"]),
            ("user2", ["TSLA", "MSFT"], ["TrendReversal"]),
            ("user3", ["GOOGL"], ["BreakoutBO", "TrendReversal"])
        ]

        # Subscribe all users
        for user_id, symbols, patterns in users_and_preferences:
            preferences = TierSubscriptionPreferences(
                pattern_types=patterns,
                symbols=symbols,
                tiers=[PatternTier.DAILY],
                confidence_min=0.7
            )

            result = integration.subscribe_user_to_tier_patterns(user_id, preferences)
            assert result is True

        # Check stats
        assert integration.stats["tier_subscriptions"] == 3

        # Broadcast events for different patterns
        events = [
            TierPatternEvent(
                pattern_type="BreakoutBO", symbol="AAPL", tier=PatternTier.DAILY,
                confidence=0.8, event_id="multi_test_1", timestamp=datetime.now()
            ),
            TierPatternEvent(
                pattern_type="TrendReversal", symbol="TSLA", tier=PatternTier.DAILY,
                confidence=0.85, event_id="multi_test_2", timestamp=datetime.now()
            )
        ]

        total_deliveries = 0
        for event in events:
            deliveries = integration.broadcast_tier_pattern_event(event)
            total_deliveries += deliveries

        assert integration.stats["patterns_broadcast"] == 2
        assert total_deliveries == 6  # 3 deliveries per event

    def test_error_recovery_workflow(self, integration):
        """Test error recovery in workflows."""
        # Subscribe successfully
        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY]
        )

        result = integration.subscribe_user_to_tier_patterns("user123", preferences)
        assert result is True

        # Mock broadcast failure
        integration.websocket_manager.broadcast_event.side_effect = Exception("Broadcast failed")

        pattern_event = TierPatternEvent(
            pattern_type="BreakoutBO", symbol="AAPL", tier=PatternTier.DAILY,
            confidence=0.8, event_id="error_recovery_test", timestamp=datetime.now()
        )

        # Broadcast should fail gracefully
        delivery_count = integration.broadcast_tier_pattern_event(pattern_event)
        assert delivery_count == 0

        # But subscription should still be intact and stats should show the attempt
        assert integration.stats["tier_subscriptions"] == 1

        # Reset mock to work again
        integration.websocket_manager.broadcast_event.side_effect = None
        integration.websocket_manager.broadcast_event.return_value = 1

        # Should work again
        delivery_count = integration.broadcast_tier_pattern_event(pattern_event)
        assert delivery_count == 1
