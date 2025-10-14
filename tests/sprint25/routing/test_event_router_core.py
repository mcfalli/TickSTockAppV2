"""
EventRouter Core Functionality Tests
Sprint 25 Day 4: Comprehensive test coverage for intelligent routing system.

Tests cover:
- EventRouter initialization and configuration
- Routing rule management (add/remove/matching)
- Core routing strategies (BROADCAST_ALL, CONTENT_BASED, etc.)
- Route caching system with LRU eviction
- Content transformation and enrichment
- Performance monitoring and metrics
"""

import threading
import time
from unittest.mock import Mock, patch

import pytest

# Core imports for testing
from src.infrastructure.websocket.event_router import (
    DeliveryPriority,
    EventCategory,
    EventRouter,
    RouterStats,
    RoutingRule,
    RoutingStrategy,
    create_market_data_routing_rule,
    create_pattern_routing_rule,
    create_tier_routing_rule,
)
from src.infrastructure.websocket.scalable_broadcaster import ScalableBroadcaster


class TestEventRouterInitialization:
    """Test EventRouter initialization and configuration."""

    def test_event_router_initialization_success(self):
        """Test successful EventRouter initialization with default settings."""
        # Arrange
        mock_broadcaster = Mock(spec=ScalableBroadcaster)

        # Act
        router = EventRouter(
            scalable_broadcaster=mock_broadcaster,
            cache_size=1000,
            enable_caching=True
        )

        # Assert
        assert router.scalable_broadcaster == mock_broadcaster
        assert router.cache_size == 1000
        assert router.enable_caching is True
        assert len(router.routing_rules) == 0
        assert len(router.route_cache) == 0
        assert isinstance(router.stats, RouterStats)
        assert router.routing_executor is not None

    def test_event_router_initialization_custom_settings(self):
        """Test EventRouter initialization with custom settings."""
        # Arrange
        mock_broadcaster = Mock(spec=ScalableBroadcaster)

        # Act
        router = EventRouter(
            scalable_broadcaster=mock_broadcaster,
            cache_size=500,
            enable_caching=False
        )

        # Assert
        assert router.cache_size == 500
        assert router.enable_caching is False
        assert len(router.route_cache) == 0

    def test_event_router_thread_safety_initialization(self):
        """Test EventRouter thread safety locks are properly initialized."""
        # Arrange
        mock_broadcaster = Mock(spec=ScalableBroadcaster)

        # Act
        router = EventRouter(scalable_broadcaster=mock_broadcaster)

        # Assert
        assert router.routing_lock is not None
        assert router.cache_lock is not None
        assert isinstance(router.routing_lock, threading.RLock)
        assert isinstance(router.cache_lock, threading.Lock)


class TestRoutingRuleManagement:
    """Test routing rule addition, removal, and management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)

    def test_add_routing_rule_success(self):
        """Test successful routing rule addition."""
        # Arrange
        rule = RoutingRule(
            rule_id='test_rule_1',
            name='Test Pattern Rule',
            description='Test rule for pattern events',
            event_type_patterns=[r'pattern.*'],
            content_filters={'pattern_type': 'BreakoutBO'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=['pattern_room'],
            priority=DeliveryPriority.HIGH
        )

        # Act
        result = self.router.add_routing_rule(rule)

        # Assert
        assert result is True
        assert 'test_rule_1' in self.router.routing_rules
        assert self.router.routing_rules['test_rule_1'] == rule

    def test_add_multiple_routing_rules(self):
        """Test adding multiple routing rules."""
        # Arrange
        rule1 = RoutingRule(
            rule_id='pattern_rule',
            name='Pattern Rule',
            description='Routes pattern events',
            event_type_patterns=[r'pattern.*'],
            content_filters={'pattern_type': 'BreakoutBO'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=['pattern_room'],
            priority=DeliveryPriority.HIGH
        )

        rule2 = RoutingRule(
            rule_id='market_rule',
            name='Market Data Rule',
            description='Routes market data',
            event_type_patterns=[r'market.*'],
            content_filters={'symbol': 'AAPL'},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['market_room'],
            priority=DeliveryPriority.MEDIUM
        )

        # Act
        result1 = self.router.add_routing_rule(rule1)
        result2 = self.router.add_routing_rule(rule2)

        # Assert
        assert result1 is True
        assert result2 is True
        assert len(self.router.routing_rules) == 2
        assert 'pattern_rule' in self.router.routing_rules
        assert 'market_rule' in self.router.routing_rules

    def test_remove_routing_rule_success(self):
        """Test successful routing rule removal."""
        # Arrange
        rule = RoutingRule(
            rule_id='test_remove_rule',
            name='Test Remove Rule',
            description='Rule to be removed',
            event_type_patterns=[r'test.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )
        self.router.add_routing_rule(rule)

        # Act
        result = self.router.remove_routing_rule('test_remove_rule')

        # Assert
        assert result is True
        assert 'test_remove_rule' not in self.router.routing_rules
        assert len(self.router.routing_rules) == 0

    def test_remove_nonexistent_routing_rule(self):
        """Test removing a routing rule that doesn't exist."""
        # Act
        result = self.router.remove_routing_rule('nonexistent_rule')

        # Assert
        assert result is False

    def test_rule_categorization(self):
        """Test routing rule categorization for optimization."""
        # Arrange
        pattern_rule = RoutingRule(
            rule_id='pattern_categorize',
            name='Pattern Rule',
            description='Test categorization',
            event_type_patterns=[r'pattern.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        market_rule = RoutingRule(
            rule_id='market_categorize',
            name='Market Rule',
            description='Test categorization',
            event_type_patterns=[r'market.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        # Act
        self.router.add_routing_rule(pattern_rule)
        self.router.add_routing_rule(market_rule)

        # Assert
        assert 'pattern_categorize' in self.router.rule_categories[EventCategory.PATTERN_ALERT]
        assert 'market_categorize' in self.router.rule_categories[EventCategory.MARKET_DATA]


class TestRoutingRuleMatching:
    """Test routing rule matching logic and criteria."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)

    def test_rule_matches_event_type_pattern(self):
        """Test rule matching based on event type patterns."""
        # Arrange
        rule = RoutingRule(
            rule_id='type_pattern_rule',
            name='Type Pattern Rule',
            description='Matches event types',
            event_type_patterns=[r'pattern.*', r'tier_.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        # Act & Assert
        assert rule.matches_event('pattern_alert', {}) is True
        assert rule.matches_event('tier_pattern', {}) is True
        assert rule.matches_event('market_data', {}) is False
        assert rule.matches_event('system_health', {}) is False

    def test_rule_matches_content_filters(self):
        """Test rule matching based on content filters."""
        # Arrange
        rule = RoutingRule(
            rule_id='content_filter_rule',
            name='Content Filter Rule',
            description='Matches content filters',
            event_type_patterns=[r'.*'],
            content_filters={
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL',
                'confidence': {'min': 0.7, 'max': 1.0}
            },
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.HIGH
        )

        # Test matching data
        matching_data = {
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL',
            'confidence': 0.85
        }

        # Test non-matching data
        non_matching_data = {
            'pattern_type': 'TrendReversal',  # Wrong pattern
            'symbol': 'AAPL',
            'confidence': 0.85
        }

        low_confidence_data = {
            'pattern_type': 'BreakoutBO',
            'symbol': 'AAPL',
            'confidence': 0.5  # Too low confidence
        }

        # Act & Assert
        assert rule.matches_event('pattern_alert', matching_data) is True
        assert rule.matches_event('pattern_alert', non_matching_data) is False
        assert rule.matches_event('pattern_alert', low_confidence_data) is False

    def test_rule_matches_complex_filters(self):
        """Test rule matching with complex filter conditions."""
        # Arrange
        rule = RoutingRule(
            rule_id='complex_filter_rule',
            name='Complex Filter Rule',
            description='Complex filter matching',
            event_type_patterns=[r'.*'],
            content_filters={
                'tier': 'daily',
                'confidence': {'min': 0.8},
                'description': {'contains': 'breakout'},
                'priority': {'equals': 'HIGH'}
            },
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.HIGH
        )

        # Test data
        matching_data = {
            'tier': 'daily',
            'confidence': 0.9,
            'description': 'Strong breakout pattern detected',
            'priority': 'HIGH'
        }

        partial_match_data = {
            'tier': 'daily',
            'confidence': 0.9,
            'description': 'Trend reversal pattern',  # Missing 'breakout'
            'priority': 'HIGH'
        }

        # Act & Assert
        assert rule.matches_event('tier_pattern', matching_data) is True
        assert rule.matches_event('tier_pattern', partial_match_data) is False

    def test_disabled_rule_does_not_match(self):
        """Test that disabled rules do not match events."""
        # Arrange
        rule = RoutingRule(
            rule_id='disabled_rule',
            name='Disabled Rule',
            description='This rule is disabled',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=[],
            priority=DeliveryPriority.MEDIUM,
            enabled=False  # Disabled rule
        )

        # Act & Assert
        assert rule.matches_event('any_event', {}) is False

    def test_rule_matching_error_handling(self):
        """Test rule matching error handling with malformed patterns."""
        # Arrange
        rule = RoutingRule(
            rule_id='malformed_rule',
            name='Malformed Rule',
            description='Rule with bad regex',
            event_type_patterns=[r'['],  # Invalid regex
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        # Act & Assert - should not crash, should return False
        assert rule.matches_event('test_event', {}) is False

    def test_rule_usage_tracking(self):
        """Test rule usage statistics tracking."""
        # Arrange
        rule = RoutingRule(
            rule_id='usage_tracking_rule',
            name='Usage Tracking Rule',
            description='Tracks usage statistics',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        initial_usage = rule.messages_routed
        initial_time = rule.last_used

        # Act
        time.sleep(0.01)  # Small delay
        rule.record_usage()

        # Assert
        assert rule.messages_routed == initial_usage + 1
        assert rule.last_used > initial_time


class TestRoutingStrategies:
    """Test different routing strategies implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)

    def test_broadcast_all_strategy(self):
        """Test BROADCAST_ALL routing strategy."""
        # Arrange
        rule = RoutingRule(
            rule_id='broadcast_all_rule',
            name='Broadcast All Rule',
            description='Broadcasts to all matching destinations',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['room1', 'room2'],
            priority=DeliveryPriority.MEDIUM
        )

        # Mock the strategy method
        with patch.object(self.router, '_get_broadcast_destinations') as mock_broadcast:
            mock_broadcast.return_value = {'room1': set(), 'room2': set()}

            # Act
            destinations = self.router._apply_routing_strategy(
                rule, 'test_event', {'data': 'test'}, {}
            )

            # Assert
            assert destinations == {'room1': set(), 'room2': set()}
            mock_broadcast.assert_called_once_with(rule, 'test_event', {'data': 'test'})

    def test_content_based_strategy(self):
        """Test CONTENT_BASED routing strategy."""
        # Arrange
        rule = RoutingRule(
            rule_id='content_based_rule',
            name='Content Based Rule',
            description='Routes based on content analysis',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        # Mock the strategy method
        with patch.object(self.router, '_get_content_based_destinations') as mock_content:
            mock_content.return_value = {'pattern_BreakoutBO_AAPL': set()}

            # Act
            destinations = self.router._apply_routing_strategy(
                rule, 'pattern_alert',
                {'symbol': 'AAPL', 'pattern_type': 'BreakoutBO'}, {}
            )

            # Assert
            assert destinations == {'pattern_BreakoutBO_AAPL': set()}
            mock_content.assert_called_once_with(rule, 'pattern_alert',
                                                {'symbol': 'AAPL', 'pattern_type': 'BreakoutBO'})

    def test_priority_first_strategy(self):
        """Test PRIORITY_FIRST routing strategy."""
        # Arrange
        rule = RoutingRule(
            rule_id='priority_first_rule',
            name='Priority First Rule',
            description='Routes to highest priority users first',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.PRIORITY_FIRST,
            destinations=[],
            priority=DeliveryPriority.HIGH
        )

        # Mock the strategy method
        with patch.object(self.router, '_get_priority_destinations') as mock_priority:
            mock_priority.return_value = {'priority_room': {'user1', 'user2'}}

            # Act
            destinations = self.router._apply_routing_strategy(
                rule, 'critical_alert', {'priority': 'HIGH'}, {}
            )

            # Assert
            assert destinations == {'priority_room': {'user1', 'user2'}}
            mock_priority.assert_called_once_with(rule, 'critical_alert', {'priority': 'HIGH'})

    def test_load_balanced_strategy(self):
        """Test LOAD_BALANCED routing strategy."""
        # Arrange
        rule = RoutingRule(
            rule_id='load_balanced_rule',
            name='Load Balanced Rule',
            description='Distributes load across users',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.LOAD_BALANCED,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        # Mock the strategy method
        with patch.object(self.router, '_get_load_balanced_destinations') as mock_load:
            mock_load.return_value = {'balanced_room': {'user1'}}

            # Act
            destinations = self.router._apply_routing_strategy(
                rule, 'load_test', {'load': 0.5}, {}
            )

            # Assert
            assert destinations == {'balanced_room': {'user1'}}
            mock_load.assert_called_once_with(rule, 'load_test', {'load': 0.5})

    def test_unknown_strategy_fallback(self):
        """Test fallback to broadcast strategy for unknown routing strategy."""
        # Arrange
        rule = RoutingRule(
            rule_id='unknown_strategy_rule',
            name='Unknown Strategy Rule',
            description='Uses unknown strategy',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy='UNKNOWN_STRATEGY',  # Invalid strategy
            destinations=['fallback_room'],
            priority=DeliveryPriority.MEDIUM
        )

        # Mock the fallback method
        with patch.object(self.router, '_get_broadcast_destinations') as mock_broadcast:
            mock_broadcast.return_value = {'fallback_room': set()}

            # Act
            destinations = self.router._apply_routing_strategy(
                rule, 'test_event', {}, {}
            )

            # Assert
            assert destinations == {'fallback_room': set()}
            mock_broadcast.assert_called_once_with(rule, 'test_event', {})


class TestContentBasedDestinations:
    """Test content-based destination routing logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)

    def test_pattern_based_destinations(self):
        """Test pattern-based destination routing."""
        # Arrange
        rule = Mock()
        event_data = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO'
        }

        # Act
        destinations = self.router._get_content_based_destinations(
            rule, 'pattern_alert', event_data
        )

        # Assert
        expected_room = 'pattern_BreakoutBO_AAPL'
        assert expected_room in destinations
        assert destinations[expected_room] == set()

    def test_tier_based_destinations(self):
        """Test tier-based destination routing."""
        # Arrange
        rule = Mock()
        event_data = {'tier': 'daily'}

        # Act
        destinations = self.router._get_content_based_destinations(
            rule, 'tier_event', event_data
        )

        # Assert
        expected_room = 'tier_daily'
        assert expected_room in destinations
        assert destinations[expected_room] == set()

    def test_default_content_routing(self):
        """Test default content routing for unrecognized content."""
        # Arrange
        rule = Mock()
        event_data = {'custom_field': 'custom_value'}

        # Act
        destinations = self.router._get_content_based_destinations(
            rule, 'custom_event', event_data
        )

        # Assert
        # Should create a content hash-based room
        assert len(destinations) == 1
        room_name = list(destinations.keys())[0]
        assert room_name.startswith('content_')
        assert len(room_name) == 16  # 'content_' + 8 char hash


class TestBroadcastDestinations:
    """Test broadcast destination routing logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)

    def test_room_based_destinations(self):
        """Test room-based destination routing."""
        # Arrange
        rule = Mock()
        rule.destinations = ['room_patterns', 'room_alerts']

        # Act
        destinations = self.router._get_broadcast_destinations(
            rule, 'test_event', {}
        )

        # Assert
        assert 'room_patterns' in destinations
        assert 'room_alerts' in destinations
        assert destinations['room_patterns'] == set()
        assert destinations['room_alerts'] == set()

    def test_user_based_destinations(self):
        """Test user-based destination routing."""
        # Arrange
        rule = Mock()
        rule.destinations = ['user_123', 'user_456']

        # Act
        destinations = self.router._get_broadcast_destinations(
            rule, 'test_event', {}
        )

        # Assert
        assert 'user_123' in destinations
        assert 'user_456' in destinations
        assert destinations['user_123'] == {'123'}
        assert destinations['user_456'] == {'456'}

    def test_default_room_fallback(self):
        """Test default room fallback when no destinations specified."""
        # Arrange
        rule = Mock()
        rule.destinations = []

        # Act
        destinations = self.router._get_broadcast_destinations(
            rule, 'test_event', {}
        )

        # Assert
        assert 'default_room' in destinations
        assert destinations['default_room'] == set()


class TestConvenienceRuleFunctions:
    """Test convenience functions for creating common routing rules."""

    def test_create_pattern_routing_rule(self):
        """Test pattern routing rule creation."""
        # Act
        rule = create_pattern_routing_rule(
            rule_id='test_pattern_rule',
            pattern_types=['BreakoutBO', 'TrendReversal'],
            symbols=['AAPL', 'TSLA']
        )

        # Assert
        assert rule.rule_id == 'test_pattern_rule'
        assert rule.name == 'Pattern routing: BreakoutBO, TrendReversal'
        assert rule.strategy == RoutingStrategy.CONTENT_BASED
        assert rule.priority == DeliveryPriority.HIGH
        assert r".*pattern.*" in rule.event_type_patterns
        assert r"tier_pattern" in rule.event_type_patterns

    def test_create_market_data_routing_rule(self):
        """Test market data routing rule creation."""
        # Act
        rule = create_market_data_routing_rule(
            rule_id='test_market_rule',
            symbols=['AAPL', 'GOOGL']
        )

        # Assert
        assert rule.rule_id == 'test_market_rule'
        assert rule.name == 'Market data routing: AAPL, GOOGL'
        assert rule.strategy == RoutingStrategy.BROADCAST_ALL
        assert rule.priority == DeliveryPriority.MEDIUM
        assert r"market.*" in rule.event_type_patterns
        assert r".*data.*" in rule.event_type_patterns

    def test_create_tier_routing_rule(self):
        """Test tier-specific routing rule creation."""
        # Act
        rule = create_tier_routing_rule(
            rule_id='test_tier_rule',
            tier='daily'
        )

        # Assert
        assert rule.rule_id == 'test_tier_rule'
        assert rule.name == 'Tier routing: daily'
        assert rule.strategy == RoutingStrategy.CONTENT_BASED
        assert rule.priority == DeliveryPriority.MEDIUM
        assert rule.content_filters['tier'] == 'daily'
        assert 'tier_daily' in rule.destinations


@pytest.mark.performance
class TestRoutingPerformance:
    """Test EventRouter performance requirements."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)

    def test_rule_matching_performance(self):
        """Test rule matching performance under load."""
        # Arrange - Create multiple rules
        for i in range(10):
            rule = RoutingRule(
                rule_id=f'perf_rule_{i}',
                name=f'Performance Rule {i}',
                description=f'Rule {i} for performance testing',
                event_type_patterns=[f'.*test_{i}.*'],
                content_filters={'priority': 'HIGH'},
                user_criteria={},
                strategy=RoutingStrategy.BROADCAST_ALL,
                destinations=[f'room_{i}'],
                priority=DeliveryPriority.MEDIUM
            )
            self.router.add_routing_rule(rule)

        # Act - Test matching performance
        start_time = time.time()

        for i in range(100):
            event_data = {'priority': 'HIGH', 'iteration': i}

            # Check rule matching (simulate routing)
            matched_rules = []
            for rule_id, rule in self.router.routing_rules.items():
                if rule.matches_event(f'test_{i % 10}_event', event_data):
                    matched_rules.append(rule_id)

        elapsed_time = (time.time() - start_time) * 1000

        # Assert - Should be fast enough for real-time processing
        assert elapsed_time < 100  # Less than 100ms for 100 iterations
        avg_time_per_match = elapsed_time / 100
        assert avg_time_per_match < 5  # Less than 5ms per matching operation


class TestRoutingErrorHandling:
    """Test EventRouter error handling and resilience."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)

    def test_routing_strategy_error_handling(self):
        """Test error handling in routing strategies."""
        # Arrange
        rule = Mock()
        rule.strategy = RoutingStrategy.CONTENT_BASED

        # Mock strategy method to raise exception
        with patch.object(self.router, '_get_content_based_destinations') as mock_content:
            mock_content.side_effect = Exception("Strategy error")

            # Act
            destinations = self.router._apply_routing_strategy(
                rule, 'test_event', {}, {}
            )

            # Assert - Should return empty destinations on error
            assert destinations == {}

    def test_rule_matching_exception_handling(self):
        """Test rule matching exception handling."""
        # Arrange
        rule = RoutingRule(
            rule_id='error_rule',
            name='Error Rule',
            description='Rule that causes errors',
            event_type_patterns=[r'.*'],
            content_filters={'bad_filter': object()},  # Non-serializable object
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        # Act & Assert - Should not crash
        result = rule.matches_event('test_event', {'bad_filter': 'test'})
        assert result is False  # Should return False on error

    def test_rule_addition_error_handling(self):
        """Test error handling during rule addition."""
        # Arrange
        invalid_rule = None  # Invalid rule

        # Mock internal error
        with patch.object(self.router, '_categorize_rule') as mock_categorize:
            mock_categorize.side_effect = Exception("Categorization error")

            valid_rule = RoutingRule(
                rule_id='valid_rule',
                name='Valid Rule',
                description='Valid rule',
                event_type_patterns=[r'.*'],
                content_filters={},
                user_criteria={},
                strategy=RoutingStrategy.BROADCAST_ALL,
                destinations=[],
                priority=DeliveryPriority.MEDIUM
            )

            # Act
            result = self.router.add_routing_rule(valid_rule)

            # Assert - Should handle error gracefully
            assert result is False


if __name__ == '__main__':
    pytest.main([__file__])
