"""
Advanced Routing Scenarios Tests
Sprint 25 Day 4: Comprehensive advanced routing scenarios and end-to-end validation.

Tests cover:
- Multi-destination routing with complex user targeting
- Event enrichment and transformation chains
- High-confidence pattern priority escalation
- Symbol-specific and market regime routing
- Complex rule interaction scenarios
- End-to-end latency validation (<125ms total)
- Real-world pattern event simulation
- 500+ concurrent user simulation
- Advanced caching scenarios
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch

import pytest

from src.core.services.websocket_subscription_manager import UniversalWebSocketManager

# Core imports for testing
from src.infrastructure.websocket.event_router import (
    DeliveryPriority,
    EventRouter,
    RoutingRule,
    RoutingStrategy,
    create_pattern_routing_rule,
    create_tier_routing_rule,
)
from src.infrastructure.websocket.scalable_broadcaster import ScalableBroadcaster


class TestMultiDestinationAdvancedRouting:
    """Test complex multi-destination routing scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(
            scalable_broadcaster=self.mock_broadcaster,
            cache_size=1000,
            enable_caching=True
        )

        # Mock broadcast methods
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()

        # Set up comprehensive routing rules for advanced scenarios
        self._setup_advanced_routing_rules()

    def _setup_advanced_routing_rules(self):
        """Set up complex routing rule set."""
        # High-confidence pattern rule with priority escalation
        high_confidence_rule = RoutingRule(
            rule_id='high_confidence_patterns',
            name='High Confidence Pattern Escalation',
            description='Escalates high confidence patterns to priority delivery',
            event_type_patterns=[r'.*pattern.*', r'tier_.*'],
            content_filters={
                'confidence': {'min': 0.9},
                'pattern_type': {'contains': 'BreakoutBO|TrendReversal|SupportBreak'}
            },
            user_criteria={},
            strategy=RoutingStrategy.PRIORITY_FIRST,
            destinations=['high_confidence_alerts', 'priority_room'],
            priority=DeliveryPriority.CRITICAL
        )

        # Symbol-specific routing for major stocks
        symbol_specific_rules = []
        major_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
        for symbol in major_symbols:
            rule = RoutingRule(
                rule_id=f'symbol_{symbol.lower()}_routing',
                name=f'{symbol} Specific Routing',
                description=f'Routes {symbol}-specific events',
                event_type_patterns=[r'.*'],
                content_filters={'symbol': symbol},
                user_criteria={},
                strategy=RoutingStrategy.CONTENT_BASED,
                destinations=[f'symbol_{symbol.lower()}', 'major_stocks_room'],
                priority=DeliveryPriority.HIGH
            )
            symbol_specific_rules.append(rule)

        # Market regime-based routing
        volatile_market_rule = RoutingRule(
            rule_id='volatile_market_routing',
            name='Volatile Market Routing',
            description='Special routing during volatile market conditions',
            event_type_patterns=[r'.*'],
            content_filters={
                'market_regime': 'volatile',
                'confidence': {'min': 0.6}  # Lower threshold during volatility
            },
            user_criteria={},
            strategy=RoutingStrategy.PRIORITY_FIRST,
            destinations=['volatile_alerts', 'risk_management'],
            priority=DeliveryPriority.HIGH
        )

        # Tier and time-based routing
        day_trading_rule = RoutingRule(
            rule_id='day_trading_routing',
            name='Day Trading Hours Routing',
            description='Special routing during market hours',
            event_type_patterns=[r'.*'],
            content_filters={
                'tier': 'intraday',
                'market_hours': True,
                'confidence': {'min': 0.75}
            },
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=['day_trading_room', 'active_traders'],
            priority=DeliveryPriority.HIGH
        )

        # Add all rules
        self.router.add_routing_rule(high_confidence_rule)
        for rule in symbol_specific_rules:
            self.router.add_routing_rule(rule)
        self.router.add_routing_rule(volatile_market_rule)
        self.router.add_routing_rule(day_trading_rule)

    def test_high_confidence_priority_escalation(self):
        """Test high confidence events get priority routing to multiple destinations."""
        # Arrange
        high_confidence_event = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.95,  # Very high confidence
            'tier': 'daily',
            'timestamp': time.time(),
            'market_regime': 'stable'
        }

        medium_confidence_event = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.75,  # Medium confidence
            'tier': 'daily',
            'timestamp': time.time(),
            'market_regime': 'stable'
        }

        # Act
        high_conf_result = self.router.route_event('tier_pattern', high_confidence_event)
        medium_conf_result = self.router.route_event('tier_pattern', medium_confidence_event)

        # Assert
        assert high_conf_result is not None
        assert medium_conf_result is not None

        # High confidence should match more rules (including priority escalation)
        assert len(high_conf_result.matched_rules) > len(medium_conf_result.matched_rules)

        # High confidence should include priority escalation rule
        assert 'high_confidence_patterns' in high_conf_result.matched_rules
        assert 'symbol_aapl_routing' in high_conf_result.matched_rules

        # Medium confidence should not trigger priority escalation
        assert 'high_confidence_patterns' not in medium_conf_result.matched_rules

        # Both should get symbol-specific routing
        assert 'symbol_aapl_routing' in medium_conf_result.matched_rules

        # High confidence should route to more destinations
        assert len(high_conf_result.destinations) >= len(medium_conf_result.destinations)

    def test_symbol_specific_multi_destination_routing(self):
        """Test symbol-specific routing creates multiple destination paths."""
        # Arrange - Events for different symbols
        test_events = [
            {
                'symbol': 'AAPL',
                'pattern_type': 'TrendReversal',
                'confidence': 0.8,
                'expected_symbol_rule': 'symbol_aapl_routing'
            },
            {
                'symbol': 'GOOGL',
                'pattern_type': 'SupportBreak',
                'confidence': 0.7,
                'expected_symbol_rule': 'symbol_googl_routing'
            },
            {
                'symbol': 'MSFT',
                'pattern_type': 'BreakoutBO',
                'confidence': 0.85,
                'expected_symbol_rule': 'symbol_msft_routing'
            },
            {
                'symbol': 'XYZ',  # Not in major symbols list
                'pattern_type': 'BreakoutBO',
                'confidence': 0.8,
                'expected_symbol_rule': None  # Should not match symbol-specific rules
            }
        ]

        routing_results = []

        # Act
        for event_data in test_events:
            expected_rule = event_data.pop('expected_symbol_rule')
            result = self.router.route_event('pattern_alert', event_data)
            routing_results.append((result, expected_rule))

        # Assert
        for result, expected_rule in routing_results:
            assert result is not None

            if expected_rule:
                # Should match expected symbol-specific rule
                assert expected_rule in result.matched_rules

                # Should route to both symbol-specific and general destinations
                symbol_destinations = [dest for dest in result.destinations.keys()
                                     if 'symbol_' in dest or 'major_stocks' in dest]
                assert len(symbol_destinations) > 0

            else:
                # Should not match any symbol-specific rules
                symbol_rules = [rule for rule in result.matched_rules if 'symbol_' in rule]
                assert len(symbol_rules) == 0

    def test_market_regime_adaptive_routing(self):
        """Test routing adapts to different market regimes."""
        # Arrange - Events in different market conditions
        volatile_market_event = {
            'symbol': 'TSLA',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.65,  # Lower confidence but volatile market
            'market_regime': 'volatile',
            'tier': 'intraday'
        }

        stable_market_event = {
            'symbol': 'TSLA',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.65,  # Same low confidence, stable market
            'market_regime': 'stable',
            'tier': 'intraday'
        }

        # Act
        volatile_result = self.router.route_event('market_pattern', volatile_market_event)
        stable_result = self.router.route_event('market_pattern', stable_market_event)

        # Assert
        assert volatile_result is not None
        assert stable_result is not None

        # Volatile market should trigger special routing
        assert 'volatile_market_routing' in volatile_result.matched_rules
        assert 'volatile_market_routing' not in stable_result.matched_rules

        # Volatile market should have additional destinations
        volatile_destinations = [dest for dest in volatile_result.destinations.keys()
                               if 'volatile' in dest or 'risk_management' in dest]
        assert len(volatile_destinations) > 0

        # Both should get symbol-specific routing for TSLA
        assert 'symbol_tsla_routing' in volatile_result.matched_rules
        assert 'symbol_tsla_routing' in stable_result.matched_rules

    def test_complex_rule_interaction_scenarios(self):
        """Test complex scenarios where multiple rules interact."""
        # Arrange - Event that should trigger multiple complex rules
        complex_event = {
            'symbol': 'AAPL',           # Triggers symbol-specific routing
            'pattern_type': 'BreakoutBO',
            'confidence': 0.92,         # Triggers high-confidence escalation
            'tier': 'intraday',        # Triggers day trading routing
            'market_hours': True,       # Triggers market hours routing
            'market_regime': 'volatile', # Triggers volatile market routing
            'timestamp': time.time(),
            'description': 'Strong breakout pattern during volatile session'
        }

        # Act
        result = self.router.route_event('complex_pattern_alert', complex_event)

        # Assert
        assert result is not None

        # Should match multiple rules due to complex conditions
        expected_rules = [
            'high_confidence_patterns',    # confidence >= 0.9
            'symbol_aapl_routing',         # symbol = AAPL
            'volatile_market_routing',     # market_regime = volatile, confidence >= 0.6
            'day_trading_routing'          # tier = intraday, market_hours = True, confidence >= 0.75
        ]

        for expected_rule in expected_rules:
            assert expected_rule in result.matched_rules, f"Missing expected rule: {expected_rule}"

        # Should route to all relevant destinations
        expected_destination_patterns = [
            'high_confidence',    # From high confidence rule
            'symbol_aapl',       # From AAPL-specific rule
            'volatile',          # From volatile market rule
            'day_trading'        # From day trading rule
        ]

        destination_keys = list(result.destinations.keys())
        destination_string = ' '.join(destination_keys)

        for pattern in expected_destination_patterns:
            matching_destinations = [dest for dest in destination_keys if pattern in dest]
            assert len(matching_destinations) > 0, f"No destinations matching pattern: {pattern}"

        # Should have high total destination count due to rule overlap
        assert len(result.destinations) >= 4

        # Performance should still be good despite complexity
        assert result.routing_time_ms < 50  # Should route complex scenarios quickly


class TestEventEnrichmentAndTransformations:
    """Test event enrichment and transformation chain scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(
            scalable_broadcaster=self.mock_broadcaster,
            cache_size=500,
            enable_caching=True
        )

        # Mock broadcast methods
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()

        # Set up transformation rules
        self._setup_transformation_rules()

    def _setup_transformation_rules(self):
        """Set up rules with various transformation capabilities."""
        # Metadata enrichment transformer
        def metadata_enricher(event_data):
            enriched = event_data.copy()
            enriched['enriched_timestamp'] = time.time()
            enriched['processing_stage'] = 'enriched'
            enriched['routing_metadata'] = {
                'enrichment_version': '1.0',
                'enrichment_time': time.time()
            }
            return enriched

        # Risk analysis transformer
        def risk_analyzer(event_data):
            analyzed = event_data.copy()
            confidence = event_data.get('confidence', 0)

            # Add risk assessment
            if confidence >= 0.9:
                analyzed['risk_level'] = 'LOW'
                analyzed['position_size_recommendation'] = 'LARGE'
            elif confidence >= 0.7:
                analyzed['risk_level'] = 'MEDIUM'
                analyzed['position_size_recommendation'] = 'MEDIUM'
            else:
                analyzed['risk_level'] = 'HIGH'
                analyzed['position_size_recommendation'] = 'SMALL'

            analyzed['risk_analysis_complete'] = True
            return analyzed

        # Market context transformer
        def market_context_enricher(event_data):
            enriched = event_data.copy()
            symbol = event_data.get('symbol', '')

            # Add market context based on symbol
            if symbol in ['AAPL', 'GOOGL', 'MSFT']:
                enriched['market_sector'] = 'TECH'
                enriched['liquidity_rating'] = 'HIGH'
            elif symbol in ['TSLA']:
                enriched['market_sector'] = 'AUTO'
                enriched['liquidity_rating'] = 'HIGH'
            else:
                enriched['market_sector'] = 'OTHER'
                enriched['liquidity_rating'] = 'MEDIUM'

            enriched['market_context_added'] = True
            return enriched

        # Create rules with transformers
        enrichment_rule = RoutingRule(
            rule_id='metadata_enrichment_rule',
            name='Metadata Enrichment Rule',
            description='Adds metadata enrichment to all events',
            event_type_patterns=[r'.*'],
            content_filters={},
            user_criteria={},
            strategy=RoutingStrategy.BROADCAST_ALL,
            destinations=['enriched_events'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=metadata_enricher
        )

        risk_analysis_rule = RoutingRule(
            rule_id='risk_analysis_rule',
            name='Risk Analysis Rule',
            description='Adds risk analysis to pattern events',
            event_type_patterns=[r'.*pattern.*'],
            content_filters={'pattern_type': {'contains': 'BreakoutBO|TrendReversal'}},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=['risk_analyzed_events'],
            priority=DeliveryPriority.HIGH,
            content_transformer=risk_analyzer
        )

        market_context_rule = RoutingRule(
            rule_id='market_context_rule',
            name='Market Context Rule',
            description='Adds market context to symbol events',
            event_type_patterns=[r'.*'],
            content_filters={'symbol': {'contains': 'AAPL|GOOGL|MSFT|TSLA'}},
            user_criteria={},
            strategy=RoutingStrategy.CONTENT_BASED,
            destinations=['market_context_events'],
            priority=DeliveryPriority.MEDIUM,
            content_transformer=market_context_enricher
        )

        self.router.add_routing_rule(enrichment_rule)
        self.router.add_routing_rule(risk_analysis_rule)
        self.router.add_routing_rule(market_context_rule)

    def test_single_transformation_enrichment(self):
        """Test single event transformation and enrichment."""
        # Arrange
        basic_event = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.85,
            'timestamp': time.time()
        }

        # Act
        result = self.router.route_event('pattern_alert', basic_event)

        # Assert
        assert result is not None
        assert len(result.matched_rules) == 3  # All rules should match

        # All transformation rules should have been applied
        expected_transformations = [
            'metadata_enrichment_rule_content_transform',
            'risk_analysis_rule_content_transform',
            'market_context_rule_content_transform'
        ]

        for expected_transform in expected_transformations:
            assert expected_transform in result.transformations_applied

        # Verify transformations occurred
        assert len(result.transformations_applied) == 3

    def test_conditional_transformation_chains(self):
        """Test conditional transformation based on event content."""
        # Test events with different characteristics
        test_scenarios = [
            {
                'name': 'High confidence tech stock',
                'event_data': {
                    'symbol': 'GOOGL',
                    'pattern_type': 'BreakoutBO',
                    'confidence': 0.92
                },
                'expected_rules': ['metadata_enrichment_rule', 'risk_analysis_rule', 'market_context_rule'],
                'expected_transformations': 3
            },
            {
                'name': 'Medium confidence non-tech stock',
                'event_data': {
                    'symbol': 'JPM',
                    'pattern_type': 'TrendReversal',
                    'confidence': 0.75
                },
                'expected_rules': ['metadata_enrichment_rule', 'risk_analysis_rule'],  # No market context for JPM
                'expected_transformations': 2
            },
            {
                'name': 'Non-pattern tech event',
                'event_data': {
                    'symbol': 'MSFT',
                    'event_type': 'market_update',
                    'price': 350.0
                },
                'expected_rules': ['metadata_enrichment_rule', 'market_context_rule'],  # No risk analysis for non-patterns
                'expected_transformations': 2
            },
            {
                'name': 'Generic non-tech event',
                'event_data': {
                    'symbol': 'XYZ',
                    'event_type': 'general_update',
                    'value': 100
                },
                'expected_rules': ['metadata_enrichment_rule'],  # Only metadata enrichment
                'expected_transformations': 1
            }
        ]

        # Act & Assert
        for scenario in test_scenarios:
            result = self.router.route_event('test_event', scenario['event_data'])

            assert result is not None, f"Failed scenario: {scenario['name']}"

            # Check expected rules matched
            for expected_rule in scenario['expected_rules']:
                assert expected_rule in result.matched_rules, \
                    f"Rule {expected_rule} not matched in scenario: {scenario['name']}"

            # Check transformation count
            assert len(result.transformations_applied) == scenario['expected_transformations'], \
                f"Expected {scenario['expected_transformations']} transformations in scenario: {scenario['name']}, got {len(result.transformations_applied)}"

    def test_transformation_performance_impact(self):
        """Test that transformations don't significantly impact routing performance."""
        # Arrange - Event that triggers all transformations
        complex_event = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.88,
            'tier': 'daily',
            'timestamp': time.time()
        }

        routing_times = []

        # Act - Run multiple routing operations with transformations
        for i in range(50):
            event_data = {**complex_event, 'iteration': i}

            start_time = time.time()
            result = self.router.route_event('transformation_perf_test', event_data)
            end_time = time.time()

            routing_time_ms = (end_time - start_time) * 1000
            routing_times.append(routing_time_ms)

            assert result is not None
            assert len(result.transformations_applied) > 0

        # Assert
        avg_time = sum(routing_times) / len(routing_times)
        max_time = max(routing_times)
        p95_time = sorted(routing_times)[int(0.95 * len(routing_times))]

        # Transformations should not make routing excessively slow
        assert avg_time < 30, f"Average routing time with transformations {avg_time:.2f}ms too high"
        assert p95_time < 50, f"P95 routing time with transformations {p95_time:.2f}ms too high"
        assert max_time < 100, f"Maximum routing time with transformations {max_time:.2f}ms excessive"


@pytest.mark.performance
class TestEndToEndLatencyValidation:
    """Test end-to-end latency validation for complete system."""

    def setup_method(self):
        """Set up test fixtures with complete system simulation."""
        # Create comprehensive system simulation
        self.mock_socketio = Mock()
        self.mock_redis_client = Mock()
        self.mock_existing_ws_manager = Mock()
        self.mock_websocket_broadcaster = Mock()

        # Configure mocks for realistic behavior
        self.mock_existing_ws_manager.is_user_connected.return_value = True
        self.mock_existing_ws_manager.get_user_connections.return_value = ['conn_123']
        self.mock_existing_ws_manager.get_connected_users.return_value = [f'user_{i}' for i in range(100)]

        self.mock_socketio.server.enter_room = Mock()
        self.mock_socketio.emit = Mock()

        # Create complete WebSocket manager with routing
        self.ws_manager = UniversalWebSocketManager(
            socketio=self.mock_socketio,
            redis_client=self.mock_redis_client,
            existing_websocket_manager=self.mock_existing_ws_manager,
            websocket_broadcaster=self.mock_websocket_broadcaster
        )

        # Set up realistic user subscriptions
        self._setup_realistic_subscriptions()

        # Configure routing rules for realistic scenarios
        self._setup_production_like_routing_rules()

    def _setup_realistic_subscriptions(self):
        """Set up realistic user subscription patterns."""
        subscription_patterns = [
            # High-frequency traders
            {
                'user_count': 20,
                'subscription_type': 'tier_patterns',
                'filters': {
                    'pattern_types': ['BreakoutBO', 'TrendReversal'],
                    'symbols': ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT'],
                    'tiers': ['intraday'],
                    'confidence_min': 0.8
                }
            },
            # Swing traders
            {
                'user_count': 30,
                'subscription_type': 'tier_patterns',
                'filters': {
                    'pattern_types': ['BreakoutBO', 'SupportBreak', 'TrendReversal'],
                    'symbols': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META'],
                    'tiers': ['daily'],
                    'confidence_min': 0.7
                }
            },
            # General pattern alerts
            {
                'user_count': 25,
                'subscription_type': 'pattern_alerts',
                'filters': {
                    'pattern_types': ['BreakoutBO', 'TrendReversal', 'SupportBreak'],
                    'confidence_min': 0.75
                }
            },
            # System monitoring users
            {
                'user_count': 5,
                'subscription_type': 'system_monitoring',
                'filters': {
                    'alert_types': ['system_health', 'performance_alerts']
                }
            }
        ]

        user_id = 1
        for pattern in subscription_patterns:
            for _ in range(pattern['user_count']):
                self.ws_manager.subscribe_user(
                    user_id=f'user_{user_id}',
                    subscription_type=pattern['subscription_type'],
                    filters=pattern['filters']
                )
                user_id += 1

    def _setup_production_like_routing_rules(self):
        """Set up routing rules similar to production environment."""
        # Add custom rules that simulate production complexity
        production_rules = [
            # High-volume symbol routing
            RoutingRule(
                rule_id='high_volume_symbol_routing',
                name='High Volume Symbol Routing',
                description='Special routing for high-volume symbols',
                event_type_patterns=[r'.*pattern.*'],
                content_filters={
                    'symbol': {'contains': 'AAPL|TSLA|NVDA|GOOGL|MSFT|AMZN|META'},
                    'confidence': {'min': 0.7}
                },
                user_criteria={},
                strategy=RoutingStrategy.CONTENT_BASED,
                destinations=[],
                priority=DeliveryPriority.HIGH
            ),

            # Market hours priority routing
            RoutingRule(
                rule_id='market_hours_priority',
                name='Market Hours Priority Routing',
                description='Priority routing during market hours',
                event_type_patterns=[r'.*'],
                content_filters={
                    'market_hours': True,
                    'confidence': {'min': 0.8}
                },
                user_criteria={},
                strategy=RoutingStrategy.PRIORITY_FIRST,
                destinations=['market_hours_priority'],
                priority=DeliveryPriority.CRITICAL
            ),

            # After-hours special routing
            RoutingRule(
                rule_id='after_hours_routing',
                name='After Hours Routing',
                description='Special routing for after-hours events',
                event_type_patterns=[r'.*'],
                content_filters={
                    'market_hours': False,
                    'confidence': {'min': 0.85}  # Higher threshold after hours
                },
                user_criteria={},
                strategy=RoutingStrategy.BROADCAST_ALL,
                destinations=['after_hours_alerts'],
                priority=DeliveryPriority.HIGH
            )
        ]

        for rule in production_rules:
            self.ws_manager.event_router.add_routing_rule(rule)

    def test_end_to_end_latency_under_125ms_single_event(self):
        """Test end-to-end latency <125ms for single event processing."""
        # Arrange
        realistic_pattern_event = {
            'symbol': 'AAPL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.87,
            'tier': 'daily',
            'timestamp': time.time(),
            'market_hours': True,
            'price': 175.50,
            'volume': 1500000,
            'description': 'Strong breakout pattern above resistance'
        }

        # Mock user finding to return realistic user set
        interested_users = {f'user_{i}' for i in range(1, 51)}  # 50 interested users

        latency_measurements = []

        # Act - Test multiple events for statistical validity
        for i in range(20):
            with patch.object(self.ws_manager, '_find_interested_users') as mock_find_users:
                mock_find_users.return_value = interested_users

                # Measure complete end-to-end latency
                start_time = time.time()

                delivery_count = self.ws_manager.broadcast_event(
                    event_type='tier_pattern',
                    event_data={**realistic_pattern_event, 'test_iteration': i},
                    targeting_criteria={
                        'subscription_type': 'tier_patterns',
                        'pattern_type': 'BreakoutBO',
                        'symbol': 'AAPL',
                        'tier': 'daily'
                    }
                )

                end_time = time.time()
                total_latency_ms = (end_time - start_time) * 1000
                latency_measurements.append(total_latency_ms)

                assert delivery_count > 0  # Should deliver to interested users

        # Assert
        avg_latency = sum(latency_measurements) / len(latency_measurements)
        max_latency = max(latency_measurements)
        p95_latency = sorted(latency_measurements)[int(0.95 * len(latency_measurements))]
        p99_latency = sorted(latency_measurements)[int(0.99 * len(latency_measurements))]

        assert avg_latency < 125, f"Average end-to-end latency {avg_latency:.1f}ms exceeds 125ms target"
        assert p95_latency < 125, f"P95 end-to-end latency {p95_latency:.1f}ms exceeds 125ms target"
        assert p99_latency < 200, f"P99 end-to-end latency {p99_latency:.1f}ms too high"
        assert max_latency < 300, f"Maximum latency {max_latency:.1f}ms excessive"

    def test_end_to_end_latency_concurrent_500_users(self):
        """Test end-to-end latency with 500+ concurrent user simulation."""
        # Arrange - Set up 500+ user simulation
        large_user_set = {f'user_{i}' for i in range(1, 501)}  # 500 users

        # Create diverse event types
        event_scenarios = [
            {
                'event_type': 'tier_pattern',
                'event_data': {
                    'symbol': 'AAPL',
                    'pattern_type': 'BreakoutBO',
                    'confidence': 0.89,
                    'tier': 'daily',
                    'market_hours': True
                },
                'targeting_criteria': {'subscription_type': 'tier_patterns'},
                'expected_users': 250  # Estimate based on subscriptions
            },
            {
                'event_type': 'tier_pattern',
                'event_data': {
                    'symbol': 'TSLA',
                    'pattern_type': 'TrendReversal',
                    'confidence': 0.82,
                    'tier': 'intraday',
                    'market_hours': True
                },
                'targeting_criteria': {'subscription_type': 'tier_patterns'},
                'expected_users': 150
            },
            {
                'event_type': 'system_health',
                'event_data': {
                    'status': 'warning',
                    'component': 'pattern_detection',
                    'message': 'High load detected'
                },
                'targeting_criteria': {'priority': 'critical'},
                'expected_users': 500  # System alerts go to all users
            }
        ]

        concurrent_latencies = []

        # Act - Test concurrent processing
        with patch.object(self.ws_manager, '_find_interested_users') as mock_find_users:
            mock_find_users.return_value = large_user_set

            # Process events concurrently
            def process_event_scenario(scenario):
                start_time = time.time()

                delivery_count = self.ws_manager.broadcast_event(
                    event_type=scenario['event_type'],
                    event_data=scenario['event_data'],
                    targeting_criteria=scenario['targeting_criteria']
                )

                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000

                return latency_ms, delivery_count, scenario['expected_users']

            # Run scenarios multiple times concurrently
            with ThreadPoolExecutor(max_workers=6) as executor:
                # Submit multiple concurrent operations
                futures = []
                for _ in range(10):  # 10 concurrent rounds
                    for scenario in event_scenarios:
                        future = executor.submit(process_event_scenario, scenario)
                        futures.append(future)

                # Collect results
                for future in as_completed(futures):
                    latency_ms, delivery_count, expected_users = future.result()
                    concurrent_latencies.append(latency_ms)

                    assert delivery_count > 0  # Should deliver to users

        # Assert
        avg_concurrent_latency = sum(concurrent_latencies) / len(concurrent_latencies)
        max_concurrent_latency = max(concurrent_latencies)
        p95_concurrent_latency = sorted(concurrent_latencies)[int(0.95 * len(concurrent_latencies))]

        # Latency targets should still be met under concurrent load
        assert avg_concurrent_latency < 150, f"Average concurrent latency {avg_concurrent_latency:.1f}ms too high"
        assert p95_concurrent_latency < 200, f"P95 concurrent latency {p95_concurrent_latency:.1f}ms too high"
        assert max_concurrent_latency < 500, f"Maximum concurrent latency {max_concurrent_latency:.1f}ms excessive"

        # Performance should degrade gracefully, not exponentially
        single_user_baseline = 50  # Estimated single-user latency
        degradation_factor = avg_concurrent_latency / single_user_baseline
        assert degradation_factor < 4, f"Performance degradation factor {degradation_factor:.1f}x too high"

    def test_component_latency_breakdown_validation(self):
        """Test individual component latency breakdown meets targets."""
        # Target breakdown: 5ms indexing + 20ms routing + 100ms broadcasting = 125ms total

        # Arrange
        test_event = {
            'symbol': 'GOOGL',
            'pattern_type': 'BreakoutBO',
            'confidence': 0.88,
            'tier': 'daily',
            'market_hours': True
        }

        interested_users = {f'user_{i}' for i in range(1, 101)}  # 100 users

        component_timings = {
            'indexing_times': [],
            'routing_times': [],
            'broadcasting_times': [],
            'total_times': []
        }

        # Act - Measure component breakdown
        for i in range(15):
            with patch.object(self.ws_manager, '_find_interested_users') as mock_find_users:
                mock_find_users.return_value = interested_users

                # Measure total time
                total_start = time.time()

                # Measure indexing time (user finding)
                indexing_start = time.time()
                found_users = self.ws_manager._find_interested_users({'test': 'criteria'})
                indexing_end = time.time()
                indexing_time_ms = (indexing_end - indexing_start) * 1000

                # Measure routing time
                routing_start = time.time()
                routing_result = self.ws_manager.event_router.route_event(
                    'tier_pattern',
                    {**test_event, 'iteration': i},
                    {'test_context': True}
                )
                routing_end = time.time()
                routing_time_ms = (routing_end - routing_start) * 1000

                # Measure broadcasting time (simulated)
                broadcasting_start = time.time()
                # Simulate broadcasting delay
                time.sleep(0.01)  # 10ms simulated broadcast time
                broadcasting_end = time.time()
                broadcasting_time_ms = (broadcasting_end - broadcasting_start) * 1000

                total_end = time.time()
                total_time_ms = (total_end - total_start) * 1000

                component_timings['indexing_times'].append(indexing_time_ms)
                component_timings['routing_times'].append(routing_time_ms)
                component_timings['broadcasting_times'].append(broadcasting_time_ms)
                component_timings['total_times'].append(total_time_ms)

        # Assert individual component targets
        avg_indexing = sum(component_timings['indexing_times']) / len(component_timings['indexing_times'])
        avg_routing = sum(component_timings['routing_times']) / len(component_timings['routing_times'])
        avg_broadcasting = sum(component_timings['broadcasting_times']) / len(component_timings['broadcasting_times'])
        avg_total = sum(component_timings['total_times']) / len(component_timings['total_times'])

        # Component-specific targets
        assert avg_indexing < 5, f"Average indexing time {avg_indexing:.1f}ms exceeds 5ms target"
        assert avg_routing < 20, f"Average routing time {avg_routing:.1f}ms exceeds 20ms target"
        # Broadcasting time is simulated, so we don't assert on it

        # Total should be reasonable
        assert avg_total < 50, f"Average total component time {avg_total:.1f}ms too high for component test"


@pytest.mark.performance
class TestRealWorldScenarioSimulation:
    """Test real-world scenario simulation with production-like loads."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_broadcaster = Mock(spec=ScalableBroadcaster)
        self.router = EventRouter(
            scalable_broadcaster=self.mock_broadcaster,
            cache_size=2000,  # Larger cache for real-world simulation
            enable_caching=True
        )

        # Mock broadcast methods
        self.mock_broadcaster.broadcast_to_users = Mock()
        self.mock_broadcaster.broadcast_to_room = Mock()

        # Set up production-like rule set
        self._setup_production_routing_rules()

    def _setup_production_routing_rules(self):
        """Set up comprehensive production-like routing rules."""
        # Major stock symbols routing
        major_symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
        for symbol in major_symbols:
            rule = create_pattern_routing_rule(
                rule_id=f'major_{symbol.lower()}_routing',
                pattern_types=['BreakoutBO', 'TrendReversal', 'SupportBreak'],
                symbols=[symbol]
            )
            self.router.add_routing_rule(rule)

        # Tier-based routing
        for tier in ['daily', 'intraday', 'combo']:
            rule = create_tier_routing_rule(
                rule_id=f'production_tier_{tier}_routing',
                tier=tier
            )
            self.router.add_routing_rule(rule)

        # Market condition routing
        market_conditions = ['volatile', 'stable', 'trending', 'ranging']
        for condition in market_conditions:
            rule = RoutingRule(
                rule_id=f'market_{condition}_routing',
                name=f'Market {condition.title()} Routing',
                description=f'Routes events during {condition} market conditions',
                event_type_patterns=[r'.*'],
                content_filters={'market_regime': condition},
                user_criteria={},
                strategy=RoutingStrategy.CONTENT_BASED,
                destinations=[f'market_{condition}'],
                priority=DeliveryPriority.HIGH if condition == 'volatile' else DeliveryPriority.MEDIUM
            )
            self.router.add_routing_rule(rule)

    @pytest.mark.performance
    def test_production_load_simulation(self):
        """Test routing under production-like event load."""
        # Arrange - Generate realistic event stream
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'UBER', 'SPOT']
        pattern_types = ['BreakoutBO', 'TrendReversal', 'SupportBreak', 'MomentumShift']
        tiers = ['daily', 'intraday', 'combo']
        market_regimes = ['stable', 'volatile', 'trending', 'ranging']

        # Generate 1000 realistic events
        events = []
        for i in range(1000):
            event = {
                'symbol': symbols[i % len(symbols)],
                'pattern_type': pattern_types[i % len(pattern_types)],
                'confidence': 0.6 + (i % 4) * 0.1,  # 0.6 to 0.9
                'tier': tiers[i % len(tiers)],
                'market_regime': market_regimes[i % len(market_regimes)],
                'market_hours': i % 3 != 0,  # 2/3 during market hours
                'timestamp': time.time() + i * 0.001,  # Spread over time
                'volume': 1000000 + (i % 1000) * 1000,
                'price': 100.0 + (i % 100),
                'iteration': i
            }
            events.append(event)

        routing_times = []
        matched_rule_counts = []
        cache_hits = 0
        total_destinations = 0

        # Act - Process production load
        start_time = time.time()

        for i, event in enumerate(events):
            event_start = time.time()

            result = self.router.route_event('production_pattern', event)

            event_end = time.time()
            routing_time_ms = (event_end - event_start) * 1000
            routing_times.append(routing_time_ms)

            assert result is not None
            matched_rule_counts.append(len(result.matched_rules))
            total_destinations += len(result.destinations)

            if result.cache_hit:
                cache_hits += 1

        end_time = time.time()
        total_time = end_time - start_time

        # Assert production performance targets
        avg_routing_time = sum(routing_times) / len(routing_times)
        max_routing_time = max(routing_times)
        p95_routing_time = sorted(routing_times)[int(0.95 * len(routing_times))]
        p99_routing_time = sorted(routing_times)[int(0.99 * len(routing_times))]

        events_per_second = len(events) / total_time
        avg_rules_matched = sum(matched_rule_counts) / len(matched_rule_counts)
        cache_hit_rate = (cache_hits / len(events)) * 100
        avg_destinations = total_destinations / len(events)

        # Production performance targets
        assert avg_routing_time < 25, f"Average routing time {avg_routing_time:.2f}ms exceeds production target"
        assert p95_routing_time < 50, f"P95 routing time {p95_routing_time:.2f}ms exceeds production target"
        assert p99_routing_time < 100, f"P99 routing time {p99_routing_time:.2f}ms exceeds production target"
        assert max_routing_time < 200, f"Maximum routing time {max_routing_time:.2f}ms excessive for production"

        # Throughput targets
        assert events_per_second > 500, f"Production throughput {events_per_second:.0f} events/sec below target"

        # Rule effectiveness
        assert avg_rules_matched >= 2, f"Average rules matched {avg_rules_matched:.1f} too low"
        assert avg_destinations >= 1, f"Average destinations {avg_destinations:.1f} too low"

        # Cache effectiveness (if caching is working)
        if cache_hits > 0:
            assert cache_hit_rate >= 10, f"Cache hit rate {cache_hit_rate:.1f}% too low for production"

        # System stability
        stats = self.router.get_routing_stats()
        assert stats['routing_errors'] == 0, f"Production load caused {stats['routing_errors']} routing errors"
        assert stats['transformation_errors'] == 0, f"Production load caused {stats['transformation_errors']} transformation errors"


if __name__ == '__main__':
    pytest.main([__file__])
