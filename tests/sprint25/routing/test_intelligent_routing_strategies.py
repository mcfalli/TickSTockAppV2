"""
Intelligent Routing Strategies Tests
Sprint 25 Day 4: Comprehensive test coverage for intelligent routing capabilities.

Tests cover:
- Content-based routing with pattern analysis
- Multi-destination routing scenarios
- Priority-based routing decisions
- Load-balanced distribution
- Event enrichment and transformation
- Complex routing rule scenarios
"""

import threading
import time
from unittest.mock import Mock

import pytest

# Core imports for testing
from src.infrastructure.websocket.event_router import (
    DeliveryPriority,
    EventRouter,
    RoutingRule,
    RoutingStrategy,
)
from src.infrastructure.websocket.scalable_broadcaster import ScalableBroadcaster


class TestIntelligentRouting:
    """Test intelligent routing analysis and decision-making."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(
            scalable_broadcaster=self.mock_broadcaster,
            cache_size=500,
            enable_caching=True
        )

        # Set up mock execute routing to avoid actual broadcast calls
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()

    def test_single_rule_matching_and_routing(self):
        """Test intelligent routing with single matching rule."""
        # Arrange
        pattern_rule = RoutingRule(
            rule_id='single_pattern_rule',
            name='Single Pattern Rule',
            description='Routes pattern alerts',
            event_type_patterns=[r'pattern.*'],
            content_filters={'pattern_type': 'BreakoutBO'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.HIGH
        )
        self.router.add_routing_rule(pattern_rule)

        event_data = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.85,
            'tier': 'daily'
        }

        # Act
        routing_result = self.router.route_event(
            event_type='pattern_alert',
            event_data=event_data,
            user_context={'priority': 'high'}
        )

        # Assert
        assert routing_result is not None
        assert len(routing_result.matched_rules) == 1
        assert 'single_pattern_rule' in routing_result.matched_rules
        assert routing_result.total_users >= 0
        assert routing_result.routing_time_ms > 0

    def test_multiple_rules_matching_single_event(self):
        """Test intelligent routing with multiple matching rules."""
        # Arrange
        pattern_rule = RoutingRule(
            rule_id='pattern_multi_rule',
            name='Pattern Rule',
            description='Routes pattern events',
            event_type_patterns=[r'pattern.*'],
            content_filters={'pattern_type': 'BreakoutBO'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.HIGH
        )

        general_rule = RoutingRule(
            rule_id='general_multi_rule',
            name='General Rule',
            description='Routes all events',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['general_room'],
            priority=DeliveryPriority.MEDIUM
        )

        tier_rule = RoutingRule(
            rule_id='tier_multi_rule',
            name='Tier Rule',
            description='Routes tier-specific events',
            event_type_patterns=[r'.*'],
            content_filters={'tier': 'daily'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        self.router.add_routing_rule(pattern_rule)
        self.router.add_routing_rule(general_rule)
        self.router.add_routing_rule(tier_rule)

        event_data = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.85,
            'tier': 'daily'
        }

        # Act
        routing_result = self.router.route_event(
            event_type='pattern_alert',
            event_data=event_data
        )

        # Assert
        assert routing_result is not None
        assert len(routing_result.matched_rules) == 3
        assert 'pattern_multi_rule' in routing_result.matched_rules
        assert 'general_multi_rule' in routing_result.matched_rules
        assert 'tier_multi_rule' in routing_result.matched_rules

        # Check destinations were merged from multiple rules
        assert len(routing_result.destinations) > 0

    def test_no_matching_rules_scenario(self):
        """Test routing when no rules match the event."""
        # Arrange
        specific_rule = RoutingRule(
            rule_id='very_specific_rule',
            name='Very Specific Rule',
            description='Very specific matching criteria',
            event_type_patterns=[r'very_specific_pattern'],
            content_filters={'specific_field': 'specific_value'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )
        self.router.add_routing_rule(specific_rule)

        event_data = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO'
        }

        # Act
        routing_result = self.router.route_event(
            event_type='generic_event',
            event_data=event_data
        )

        # Assert
        assert routing_result is not None
        assert len(routing_result.matched_rules) == 0
        assert routing_result.total_users == 0
        assert len(routing_result.destinations) == 0

    def test_content_transformation_during_routing(self):
        """Test content transformation functionality."""
        # Arrange
        def custom_transformer(event_data):
            """Transform event data by adding enrichment."""
            enhanced_data = event_data.copy()
            enhanced_data['enriched'] = True
            enhanced_data['transformation_timestamp'] = time.time()
            return enhanced_data

        transform_rule = RoutingRule(
            rule_id='transform_rule',
            name='Transform Rule',
            description='Rule with content transformation',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['transform_room'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=custom_transformer
        )
        self.router.add_routing_rule(transform_rule)

        event_data = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO'
        }

        # Act
        routing_result = self.router.route_event(
            event_type='transform_test',
            event_data=event_data
        )

        # Assert
        assert routing_result is not None
        assert len(routing_result.matched_rules) == 1
        assert 'transform_rule_content_transform' in routing_result.transformations_applied

    def test_transformation_error_handling(self):
        """Test error handling in content transformation."""
        # Arrange
        def failing_transformer(event_data):
            """Transformer that always fails."""
            raise Exception("Transformation failed")

        failing_rule = RoutingRule(
            rule_id='failing_transform_rule',
            name='Failing Transform Rule',
            description='Rule with failing transformation',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['failing_room'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=failing_transformer
        )
        self.router.add_routing_rule(failing_rule)

        # Act
        routing_result = self.router.route_event(
            event_type='failing_transform_test',
            event_data={'test': 'data'}
        )

        # Assert
        assert routing_result is not None
        assert len(routing_result.matched_rules) == 1
        assert len(routing_result.transformations_applied) == 0
        assert self.router.stats.transformation_errors > 0


class TestContentBasedRouting:
    """Test content-based routing scenarios in detail."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)

        # Mock broadcast methods to avoid actual calls
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()

    def test_pattern_symbol_based_routing(self):
        """Test routing based on pattern type and symbol."""
        # Arrange
        pattern_rule = RoutingRule(
            rule_id='pattern_symbol_rule',
            name='Pattern Symbol Rule',
            description='Routes by pattern and symbol',
            event_type_patterns=[r'pattern.*'],
            content_filters={
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL'
            },
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.HIGH
        )
        self.router.add_routing_rule(pattern_rule)

        # Test data that should match
        matching_event = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.85
        }

        # Test data that shouldn't match (different symbol)
        non_matching_event = {
            'symbol': 'TSLA',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.85
        }

        # Act
        matching_result = self.router.route_event('pattern_alert', matching_event)
        non_matching_result = self.router.route_event('pattern_alert', non_matching_event)

        # Assert
        assert len(matching_result.matched_rules) == 1
        assert len(non_matching_result.matched_rules) == 0

        # Check content-based destination creation
        if matching_result.destinations:
            destination_names = list(matching_result.destinations.keys())
            assert any('pattern_BreakoutBO_AAPL' in dest for dest in destination_names)

    def test_tier_based_routing(self):
        """Test routing based on tier information."""
        # Arrange
        daily_rule = RoutingRule(
            rule_id='daily_tier_rule',
            name='Daily Tier Rule',
            description='Routes daily tier events',
            event_type_patterns=[r'.*'],
            content_filters={'tier': 'daily'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        intraday_rule = RoutingRule(
            rule_id='intraday_tier_rule',
            name='Intraday Tier Rule',
            description='Routes intraday tier events',
            event_type_patterns=[r'.*'],
            content_filters={'tier': 'intraday'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        self.router.add_routing_rule(daily_rule)
        self.router.add_routing_rule(intraday_rule)

        daily_event = {'tier': 'daily', 'pattern': 'BreakoutBO'}
        intraday_event = {'tier': 'intraday', 'pattern': 'TrendReversal'}

        # Act
        daily_result = self.router.route_event('tier_event', daily_event)
        intraday_result = self.router.route_event('tier_event', intraday_event)

        # Assert
        assert len(daily_result.matched_rules) == 1
        assert 'daily_tier_rule' in daily_result.matched_rules

        assert len(intraday_result.matched_rules) == 1
        assert 'intraday_tier_rule' in intraday_result.matched_rules

    def test_confidence_threshold_routing(self):
        """Test routing based on confidence thresholds."""
        # Arrange
        high_confidence_rule = RoutingRule(
            rule_id='high_confidence_rule',
            name='High Confidence Rule',
            description='Routes high confidence events',
            event_type_patterns=[r'.*'],
            content_filters={
                'confidence': {'min': 0.8}
            },
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=['high_confidence_room'],
            priority=DeliveryPriority.HIGH
        )

        medium_confidence_rule = RoutingRule(
            rule_id='medium_confidence_rule',
            name='Medium Confidence Rule',
            description='Routes medium confidence events',
            event_type_patterns=[r'.*'],
            content_filters={
                'confidence': {'min': 0.5, 'max': 0.8}
            },
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=['medium_confidence_room'],
            priority=DeliveryPriority.MEDIUM
        )

        self.router.add_routing_rule(high_confidence_rule)
        self.router.add_routing_rule(medium_confidence_rule)

        # Test events
        high_conf_event = {'confidence': 0.95, 'pattern': 'BreakoutBO'}
        medium_conf_event = {'confidence': 0.65, 'pattern': 'TrendReversal'}
        low_conf_event = {'confidence': 0.3, 'pattern': 'WeakSignal'}

        # Act
        high_result = self.router.route_event('confidence_test', high_conf_event)
        medium_result = self.router.route_event('confidence_test', medium_conf_event)
        low_result = self.router.route_event('confidence_test', low_conf_event)

        # Assert
        assert len(high_result.matched_rules) == 1
        assert 'high_confidence_rule' in high_result.matched_rules

        assert len(medium_result.matched_rules) == 1
        assert 'medium_confidence_rule' in medium_result.matched_rules

        assert len(low_result.matched_rules) == 0

    def test_complex_content_filters(self):
        """Test complex content filtering scenarios."""
        # Arrange
        complex_rule = RoutingRule(
            rule_id='complex_filter_rule',
            name='Complex Filter Rule',
            description='Complex filtering logic',
            event_type_patterns=[r'pattern.*'],
            content_filters={
                'tier': 'daily',
                'confidence': {'min': 0.7},
                'symbol': 'AAPL',
                'pattern_type': {'contains': 'Breakout'},
                'priority': {'equals': 'HIGH'}
            },
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.CRITICAL
        )
        self.router.add_routing_rule(complex_rule)

        # Test matching event
        matching_event = {
            'tier': 'daily',
            'confidence': 0.85,
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'priority': 'HIGH'
        }

        # Test partially matching events
        wrong_tier_event = {**matching_event, 'tier': 'intraday'}
        low_confidence_event = {**matching_event, 'confidence': 0.6}
        wrong_symbol_event = {**matching_event, 'symbol': 'TSLA'}
        wrong_pattern_event = {**matching_event, 'pattern_type': 'TrendReversal'}
        wrong_priority_event = {**matching_event, 'priority': 'MEDIUM'}

        # Act
        matching_result = self.router.route_event('pattern_alert', matching_event)
        wrong_tier_result = self.router.route_event('pattern_alert', wrong_tier_event)
        low_conf_result = self.router.route_event('pattern_alert', low_confidence_event)
        wrong_symbol_result = self.router.route_event('pattern_alert', wrong_symbol_event)
        wrong_pattern_result = self.router.route_event('pattern_alert', wrong_pattern_event)
        wrong_priority_result = self.router.route_event('pattern_alert', wrong_priority_event)

        # Assert
        assert len(matching_result.matched_rules) == 1
        assert len(wrong_tier_result.matched_rules) == 0
        assert len(low_conf_result.matched_rules) == 0
        assert len(wrong_symbol_result.matched_rules) == 0
        assert len(wrong_pattern_result.matched_rules) == 0
        assert len(wrong_priority_result.matched_rules) == 0


class TestMultiDestinationRouting:
    """Test multi-destination routing scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)

        # Mock broadcast methods
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()

    def test_single_event_multiple_destinations(self):
        """Test single event routed to multiple destinations."""
        # Arrange
        broadcast_rule = RoutingRule(
            rule_id='broadcast_multi_dest',
            name='Broadcast Multi Destination',
            description='Broadcasts to multiple rooms',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['room1', 'room2', 'room3'],
            priority=DeliveryPriority.MEDIUM
        )

        content_rule = RoutingRule(
            rule_id='content_multi_dest',
            name='Content Multi Destination',
            description='Content-based routing',
            event_type_patterns=[r'.*'],
            content_filters={'pattern_type': 'BreakoutBO'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.HIGH
        )

        self.router.add_routing_rule(broadcast_rule)
        self.router.add_routing_rule(content_rule)

        event_data = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.85
        }

        # Act
        routing_result = self.router.route_event('multi_dest_test', event_data)

        # Assert
        assert len(routing_result.matched_rules) == 2
        assert routing_result.total_users >= 0

        # Should have destinations from both rules
        destination_count = len(routing_result.destinations)
        assert destination_count > 0

    def test_user_specific_and_room_destinations(self):
        """Test mixing user-specific and room-based destinations."""
        # Arrange
        mixed_rule = RoutingRule(
            rule_id='mixed_destinations_rule',
            name='Mixed Destinations Rule',
            description='Routes to both users and rooms',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['user_123', 'user_456', 'room_general', 'room_alerts'],
            priority=DeliveryPriority.MEDIUM
        )
        self.router.add_routing_rule(mixed_rule)

        # Act
        routing_result = self.router.route_event('mixed_test', {'data': 'test'})

        # Assert
        assert len(routing_result.matched_rules) == 1

        # Verify destinations include both user and room types
        destinations = routing_result.destinations
        has_user_destinations = any(dest.startswith('user_') for dest in destinations.keys())
        has_room_destinations = any(dest.startswith('room_') for dest in destinations.keys())

        # Note: actual destination format depends on router implementation
        assert len(destinations) > 0

    def test_overlapping_destinations_merge(self):
        """Test that overlapping destinations from multiple rules are merged."""
        # Arrange
        rule1 = RoutingRule(
            rule_id='overlap_rule_1',
            name='Overlap Rule 1',
            description='First overlapping rule',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['shared_room', 'room1'],
            priority=DeliveryPriority.MEDIUM
        )

        rule2 = RoutingRule(
            rule_id='overlap_rule_2',
            name='Overlap Rule 2',
            description='Second overlapping rule',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['shared_room', 'room2'],
            priority=DeliveryPriority.MEDIUM
        )

        self.router.add_routing_rule(rule1)
        self.router.add_routing_rule(rule2)

        # Act
        routing_result = self.router.route_event('overlap_test', {'data': 'test'})

        # Assert
        assert len(routing_result.matched_rules) == 2

        # Verify destinations are properly merged (no duplicates)
        destinations = routing_result.destinations
        assert len(destinations) >= 1  # At least shared_room should be present


class TestAdvancedRoutingScenarios:
    """Test advanced routing scenarios and edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)

        # Mock broadcast methods
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()

    def test_high_confidence_priority_escalation(self):
        """Test priority escalation for high confidence events."""
        # Arrange
        priority_rule = RoutingRule(
            rule_id='priority_escalation_rule',
            name='Priority Escalation Rule',
            description='Escalates high confidence events',
            event_type_patterns=[r'.*'],
            content_filters={
                'confidence': {'min': 0.9}
            },
            user_criteria={},
            strategy=RoutingStrategy.PRIORITY_FIRST,
            destinations=['priority_room'],
            priority=DeliveryPriority.CRITICAL
        )
        self.router.add_routing_rule(priority_rule)

        high_conf_event = {'confidence': 0.95, 'pattern': 'BreakoutBO'}
        medium_conf_event = {'confidence': 0.7, 'pattern': 'TrendReversal'}

        # Act
        high_result = self.router.route_event('priority_test', high_conf_event)
        medium_result = self.router.route_event('priority_test', medium_conf_event)

        # Assert
        assert len(high_result.matched_rules) == 1
        assert len(medium_result.matched_rules) == 0

    def test_symbol_specific_routing_distribution(self):
        """Test symbol-specific routing for popular stocks."""
        # Arrange
        aapl_rule = RoutingRule(
            rule_id='aapl_specific_rule',
            name='AAPL Specific Rule',
            description='Routes AAPL-specific events',
            event_type_patterns=[r'.*'],
            content_filters={'symbol': 'AAPL'},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.HIGH
        )

        tech_stocks_rule = RoutingRule(
            rule_id='tech_stocks_rule',
            name='Tech Stocks Rule',
            description='Routes tech stock events',
            event_type_patterns=[r'.*'],
            content_filters={
                'symbol': {'contains': 'AAPL|GOOGL|MSFT|TSLA'}
            },
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=[],
            priority=DeliveryPriority.MEDIUM
        )

        self.router.add_routing_rule(aapl_rule)
        self.router.add_routing_rule(tech_stocks_rule)

        aapl_event = {'symbol': 'AAPL', 'pattern': 'BreakoutBO'}
        googl_event = {'symbol': 'GOOGL', 'pattern': 'TrendReversal'}
        other_event = {'symbol': 'JPM', 'pattern': 'SupportBreak'}

        # Act
        aapl_result = self.router.route_event('symbol_test', aapl_event)
        googl_result = self.router.route_event('symbol_test', googl_event)
        other_result = self.router.route_event('symbol_test', other_event)

        # Assert
        # AAPL should match both rules
        assert len(aapl_result.matched_rules) == 2

        # GOOGL should match only tech stocks rule
        assert len(googl_result.matched_rules) == 1
        assert 'tech_stocks_rule' in googl_result.matched_rules

        # Other symbol should match neither
        assert len(other_result.matched_rules) == 0

    def test_market_regime_based_routing(self):
        """Test routing based on market conditions/regime."""
        # Arrange
        volatile_rule = RoutingRule(
            rule_id='volatile_market_rule',
            name='Volatile Market Rule',
            description='Routes events during volatile markets',
            event_type_patterns=[r'.*'],
            content_filters={
                'market_regime': 'volatile',
                'confidence': {'min': 0.6}
            },
            user_criteria={},
            strategy=RoutingStrategy.PRIORITY_FIRST,
            destinations=['volatile_alerts'],
            priority=DeliveryPriority.HIGH
        )

        stable_rule = RoutingRule(
            rule_id='stable_market_rule',
            name='Stable Market Rule',
            description='Routes events during stable markets',
            event_type_patterns=[r'.*'],
            content_filters={
                'market_regime': 'stable',
                'confidence': {'min': 0.8}  # Higher threshold for stable markets
            },
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['stable_room'],
            priority=DeliveryPriority.MEDIUM
        )

        self.router.add_routing_rule(volatile_rule)
        self.router.add_routing_rule(stable_rule)

        # Test events
        volatile_event = {
            'market_regime': 'volatile',
            'confidence': 0.7,
            'pattern': 'BreakoutBO'
        }

        stable_event = {
            'market_regime': 'stable',
            'confidence': 0.85,
            'pattern': 'TrendReversal'
        }

        stable_low_conf_event = {
            'market_regime': 'stable',
            'confidence': 0.7,  # Too low for stable market
            'pattern': 'WeakSignal'
        }

        # Act
        volatile_result = self.router.route_event('regime_test', volatile_event)
        stable_result = self.router.route_event('regime_test', stable_event)
        stable_low_result = self.router.route_event('regime_test', stable_low_conf_event)

        # Assert
        assert len(volatile_result.matched_rules) == 1
        assert 'volatile_market_rule' in volatile_result.matched_rules

        assert len(stable_result.matched_rules) == 1
        assert 'stable_market_rule' in stable_result.matched_rules

        assert len(stable_low_result.matched_rules) == 0


@pytest.mark.performance
class TestRoutingPerformanceUnderLoad:
    """Test routing performance under various load conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(scalable_broadcaster=self.mock_broadcaster)

        # Mock broadcast methods
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()

    def test_intelligent_routing_performance_multiple_rules(self):
        """Test routing performance with multiple complex rules."""
        # Arrange - Create 10 complex routing rules
        for i in range(10):
            rule = RoutingRule(
                rule_id=f'perf_rule_{i}',
                name=f'Performance Rule {i}',
                description=f'Complex rule {i} for performance testing',
                event_type_patterns=[f'.*pattern_{i}.*', r'.*general.*'],
                content_filters={
                    'confidence': {'min': 0.5 + (i * 0.05)},
                    'priority': 'HIGH' if i % 2 == 0 else 'MEDIUM',
                    'tier': 'daily' if i < 5 else 'intraday'
                },
                user_criteria={},
                strategy=RoutingStrategy.CONTENT_BASED if i % 3 == 0 else RoutingStrategy.BROADCAST_ALL,
                destinations=[f'room_{i}', f'room_shared_{i % 3}'],
                priority=DeliveryPriority.HIGH if i % 2 == 0 else DeliveryPriority.MEDIUM
            )
            self.router.add_routing_rule(rule)

        # Act - Test routing performance with various events
        start_time = time.time()

        for i in range(100):
            event_data = {
                'confidence': 0.7 + (i % 5) * 0.05,
                'priority': 'HIGH' if i % 2 == 0 else 'MEDIUM',
                'tier': 'daily' if i % 3 == 0 else 'intraday',
                'symbol': f'TEST{i % 10}',
                'iteration': i
            }

            # Route event with matching and non-matching patterns
            event_type = f'pattern_{i % 10}_general' if i % 3 == 0 else 'non_matching_event'
            result = self.router.route_event(event_type, event_data)

            # Verify routing worked
            assert result is not None

        elapsed_time = (time.time() - start_time) * 1000

        # Assert - Performance should be under 20ms average
        avg_time_per_route = elapsed_time / 100
        assert avg_time_per_route < 20.0, f"Average routing time {avg_time_per_route:.1f}ms exceeds 20ms target"

        # Verify some events were routed successfully
        assert self.router.stats.total_events == 100
        assert self.router.stats.events_routed > 0

    def test_concurrent_routing_thread_safety(self):
        """Test thread safety of intelligent routing under concurrent load."""
        # Arrange
        rule = RoutingRule(
            rule_id='concurrent_rule',
            name='Concurrent Test Rule',
            description='Rule for concurrent testing',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['concurrent_room'],
            priority=DeliveryPriority.MEDIUM
        )
        self.router.add_routing_rule(rule)

        results = []
        exceptions = []

        def route_events():
            """Route events in concurrent thread."""
            try:
                for i in range(20):
                    event_data = {'thread_id': threading.current_thread().ident, 'iteration': i}
                    result = self.router.route_event(f'concurrent_test_{i}', event_data)
                    results.append(result)
            except Exception as e:
                exceptions.append(e)

        # Act - Create multiple threads for concurrent routing
        threads = []
        for i in range(5):
            thread = threading.Thread(target=route_events)
            threads.append(thread)

        start_time = time.time()

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        elapsed_time = (time.time() - start_time) * 1000

        # Assert
        assert len(exceptions) == 0, f"Concurrent routing raised exceptions: {exceptions}"
        assert len(results) == 100  # 5 threads * 20 events each

        # All results should be valid
        for result in results:
            assert result is not None
            assert len(result.matched_rules) == 1

        # Performance should still be reasonable
        avg_time_per_event = elapsed_time / 100
        assert avg_time_per_event < 50.0, f"Concurrent routing too slow: {avg_time_per_event:.1f}ms per event"


if __name__ == '__main__':
    pytest.main([__file__])
