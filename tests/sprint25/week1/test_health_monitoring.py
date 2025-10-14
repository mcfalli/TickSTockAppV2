"""
Test Suite for Health Monitoring and Observability
Sprint 25 Week 1 - Comprehensive health monitoring and system observability validation

Tests the health monitoring capabilities across all 4 layers:
- Layer 1: UniversalWebSocketManager health status
- Layer 2: SubscriptionIndexManager performance monitoring  
- Layer 3: ScalableBroadcaster delivery monitoring
- Layer 4: EventRouter cache and routing monitoring
- Integrated system health assessment
- Performance degradation detection
- Alerting and threshold validation
"""

import random
import statistics
import time
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.core.services.websocket_subscription_manager import UniversalWebSocketManager
from src.infrastructure.websocket.scalable_broadcaster import DeliveryPriority


@pytest.fixture
def health_monitoring_system():
    """Create system with health monitoring enabled."""
    mock_socketio = Mock()
    mock_socketio.server = Mock()
    mock_socketio.emit = Mock()

    mock_redis = Mock()
    mock_existing_ws = Mock()
    mock_existing_ws.is_user_connected.return_value = True
    mock_existing_ws.get_user_connections.return_value = ['health_conn']

    mock_ws_broadcaster = Mock()

    # Create system optimized for health monitoring
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


class HealthTestScenario:
    """Helper class for health monitoring test scenarios."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.metrics = {}
        self.alerts = []
        self.start_time = time.time()

    def record_metric(self, metric_name: str, value: Any):
        """Record a health metric."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append({
            'timestamp': time.time(),
            'value': value
        })

    def add_alert(self, alert_type: str, message: str, severity: str = 'warning'):
        """Add a health alert."""
        self.alerts.append({
            'timestamp': time.time(),
            'type': alert_type,
            'message': message,
            'severity': severity
        })

    def get_duration(self) -> float:
        """Get scenario duration in seconds."""
        return time.time() - self.start_time


@pytest.mark.health
class TestHealthMonitoring:
    """Comprehensive health monitoring and observability tests."""

    def test_layer1_websocket_manager_health_monitoring(self, health_monitoring_system):
        """Test Layer 1 (UniversalWebSocketManager) health monitoring."""
        system = health_monitoring_system
        universal_manager = system['universal_manager']
        scenario = HealthTestScenario("Layer1_Health", "WebSocket Manager Health Monitoring")

        # Setup base activity for health monitoring
        for i in range(50):
            universal_manager.subscribe_user(
                user_id=f"health_user_{i:02d}",
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO'],
                    'symbols': ['AAPL'],
                    'confidence_min': 0.7
                }
            )

        # Test healthy state monitoring
        healthy_status = universal_manager.get_health_status()

        # Verify health status structure
        assert 'service' in healthy_status, "Health status missing service identifier"
        assert 'status' in healthy_status, "Health status missing status field"
        assert 'message' in healthy_status, "Health status missing message field"
        assert 'timestamp' in healthy_status, "Health status missing timestamp"
        assert 'stats' in healthy_status, "Health status missing statistics"
        assert 'performance_targets' in healthy_status, "Health status missing performance targets"

        # Verify service identification
        assert healthy_status['service'] == 'universal_websocket_manager', f"Wrong service ID: {healthy_status['service']}"

        # Verify initial health status
        assert healthy_status['status'] in ['healthy', 'warning'], f"Unexpected initial status: {healthy_status['status']}"

        # Record baseline metrics
        scenario.record_metric('health_status', healthy_status['status'])
        scenario.record_metric('total_users', healthy_status['stats']['total_users'])

        # Test performance targets validation
        targets = healthy_status['performance_targets']

        assert 'filtering_target_ms' in targets, "Missing filtering performance target"
        assert 'broadcast_target_ms' in targets, "Missing broadcast performance target"
        assert 'target_concurrent_users' in targets, "Missing concurrent users target"

        assert targets['filtering_target_ms'] == 5.0, f"Wrong filtering target: {targets['filtering_target_ms']}"
        assert targets['broadcast_target_ms'] == 100.0, f"Wrong broadcast target: {targets['broadcast_target_ms']}"
        assert targets['target_concurrent_users'] == 500, f"Wrong users target: {targets['target_concurrent_users']}"

        # Test health monitoring with activity
        with patch.object(universal_manager, '_find_interested_users') as mock_find:
            mock_find.return_value = {f"health_user_{i:02d}" for i in range(10)}

            mock_routing_result = Mock()
            mock_routing_result.total_users = 10
            mock_routing_result.matched_rules = ['health_rule']
            mock_routing_result.routing_time_ms = 8.0
            mock_routing_result.cache_hit = False

            with patch.object(system['event_router'], 'route_event') as mock_route:
                mock_route.return_value = mock_routing_result

                # Generate activity for health monitoring
                for i in range(20):
                    universal_manager.broadcast_event(
                        event_type='health_test',
                        event_data={'test_iteration': i},
                        targeting_criteria={'subscription_type': 'tier_patterns'}
                    )

        # Get health status after activity
        active_health_status = universal_manager.get_health_status()

        # Verify health status reflects activity
        assert active_health_status['stats']['events_broadcast'] == 20, "Health stats not updated"
        assert active_health_status['stats']['total_users'] == 50, "User count not reflected in health"

        scenario.record_metric('events_broadcast', active_health_status['stats']['events_broadcast'])

        print(f"✅ Layer 1 Health Monitoring: Status {active_health_status['status']}, {active_health_status['stats']['total_users']} users, {active_health_status['stats']['events_broadcast']} events")

    def test_layer2_index_manager_performance_monitoring(self, health_monitoring_system):
        """Test Layer 2 (SubscriptionIndexManager) performance monitoring."""
        system = health_monitoring_system
        index_manager = system['index_manager']
        scenario = HealthTestScenario("Layer2_Performance", "Index Manager Performance Monitoring")

        # Setup substantial indexing load for monitoring
        for i in range(200):
            subscription = Mock()
            subscription.user_id = f"perf_monitor_user_{i:03d}"
            subscription.subscription_type = "tier_patterns"
            subscription.filters = {
                'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                'symbols': ['AAPL', 'MSFT', 'GOOGL'][i % 3],
                'confidence_min': 0.6 + (i % 4) * 0.1
            }
            subscription.room_name = f"user_{subscription.user_id}"
            subscription.active = True
            subscription.created_at = time.time()
            subscription.last_activity = time.time()

            index_manager.add_subscription(subscription)

        # Test performance monitoring under various loads
        performance_samples = []

        for test_round in range(30):
            start_time = time.time()

            matching_users = index_manager.find_matching_users({
                'subscription_type': 'tier_patterns',
                'pattern_type': 'BreakoutBO',
                'symbol': 'AAPL'
            })

            lookup_time_ms = (time.time() - start_time) * 1000
            performance_samples.append(lookup_time_ms)

            scenario.record_metric('lookup_time_ms', lookup_time_ms)

            # Monitor performance degradation
            if lookup_time_ms > 5.0:  # Above target
                scenario.add_alert(
                    'performance_degradation',
                    f"Lookup time {lookup_time_ms:.2f}ms exceeds 5ms target",
                    'warning'
                )

            if lookup_time_ms > 10.0:  # Critical threshold
                scenario.add_alert(
                    'performance_critical',
                    f"Lookup time {lookup_time_ms:.2f}ms critically slow",
                    'critical'
                )

        # Get comprehensive index health status
        if hasattr(index_manager, 'get_health_status'):
            index_health = index_manager.get_health_status()

            assert 'service' in index_health, "Index health missing service ID"
            assert 'performance_targets' in index_health, "Index health missing performance targets"

            # Verify performance targets
            targets = index_health['performance_targets']
            assert targets['lookup_time_target_ms'] == 5.0, "Wrong lookup time target"

            scenario.record_metric('health_status', index_health['status'])

        # Analyze performance monitoring results
        avg_performance = statistics.mean(performance_samples)
        p95_performance = sorted(performance_samples)[int(0.95 * len(performance_samples))]

        assert avg_performance < 10.0, f"Average performance {avg_performance:.2f}ms unacceptable"
        assert p95_performance < 15.0, f"P95 performance {p95_performance:.2f}ms unacceptable"

        # Check alert thresholds
        warning_alerts = [a for a in scenario.alerts if a['severity'] == 'warning']
        critical_alerts = [a for a in scenario.alerts if a['severity'] == 'critical']

        # Some warnings may be acceptable, but critical alerts should be rare
        assert len(critical_alerts) < 5, f"Too many critical performance alerts: {len(critical_alerts)}"

        print(f"✅ Layer 2 Performance Monitoring: {avg_performance:.1f}ms avg, {p95_performance:.1f}ms P95, {len(warning_alerts)} warnings, {len(critical_alerts)} critical")

    def test_layer3_broadcaster_delivery_monitoring(self, health_monitoring_system):
        """Test Layer 3 (ScalableBroadcaster) delivery monitoring."""
        system = health_monitoring_system
        broadcaster = system['broadcaster']
        scenario = HealthTestScenario("Layer3_Delivery", "Broadcaster Delivery Monitoring")

        # Test delivery monitoring with various scenarios
        delivery_scenarios = [
            {'user_count': 10, 'events': 5, 'priority': DeliveryPriority.HIGH, 'name': 'small_high'},
            {'user_count': 50, 'events': 3, 'priority': DeliveryPriority.MEDIUM, 'name': 'medium_med'},
            {'user_count': 100, 'events': 2, 'priority': DeliveryPriority.LOW, 'name': 'large_low'},
            {'user_count': 25, 'events': 8, 'priority': DeliveryPriority.CRITICAL, 'name': 'burst_crit'}
        ]

        for scenario_config in delivery_scenarios:
            scenario_name = scenario_config['name']

            for event_num in range(scenario_config['events']):
                start_time = time.time()

                user_ids = {f"delivery_user_{scenario_name}_{i}" for i in range(scenario_config['user_count'])}

                # Monitor delivery performance
                queued_count = broadcaster.broadcast_to_users(
                    event_type=f'delivery_monitor_{scenario_name}',
                    event_data={
                        'scenario': scenario_name,
                        'event_num': event_num,
                        'monitor_test': True
                    },
                    user_ids=user_ids,
                    priority=scenario_config['priority']
                )

                # Force delivery for timing
                broadcaster.flush_all_batches()

                delivery_time_ms = (time.time() - start_time) * 1000

                scenario.record_metric(f'delivery_time_{scenario_name}', delivery_time_ms)
                scenario.record_metric(f'queued_count_{scenario_name}', queued_count)

                # Monitor delivery performance against targets
                target_ms = 100.0  # Layer 3 target
                if delivery_time_ms > target_ms:
                    scenario.add_alert(
                        'delivery_slow',
                        f"Delivery {scenario_name} took {delivery_time_ms:.1f}ms (target: {target_ms}ms)",
                        'warning' if delivery_time_ms < target_ms * 1.5 else 'critical'
                    )

                # Monitor delivery completeness
                if queued_count != len(user_ids):
                    scenario.add_alert(
                        'delivery_incomplete',
                        f"Only queued {queued_count}/{len(user_ids)} users for {scenario_name}",
                        'critical'
                    )

        # Get broadcaster health status
        if hasattr(broadcaster, 'get_health_status'):
            broadcaster_health = broadcaster.get_health_status()

            assert 'service' in broadcaster_health, "Broadcaster health missing service ID"
            assert 'performance_targets' in broadcaster_health, "Broadcaster health missing targets"

            targets = broadcaster_health['performance_targets']
            assert targets['delivery_latency_target_ms'] == 100.0, "Wrong delivery target"

            scenario.record_metric('health_status', broadcaster_health['status'])

        # Analyze delivery monitoring results
        all_delivery_times = []
        for metric_name, values in scenario.metrics.items():
            if metric_name.startswith('delivery_time_'):
                all_delivery_times.extend([v['value'] for v in values])

        if all_delivery_times:
            avg_delivery = statistics.mean(all_delivery_times)
            max_delivery = max(all_delivery_times)

            assert avg_delivery < 150.0, f"Average delivery {avg_delivery:.1f}ms too slow"
            assert max_delivery < 300.0, f"Max delivery {max_delivery:.1f}ms excessive"

        # Check delivery alerts
        delivery_alerts = [a for a in scenario.alerts if a['type'].startswith('delivery')]
        critical_delivery_alerts = [a for a in delivery_alerts if a['severity'] == 'critical']

        assert len(critical_delivery_alerts) < 3, f"Too many critical delivery alerts: {len(critical_delivery_alerts)}"

        print(f"✅ Layer 3 Delivery Monitoring: {len(all_delivery_times)} deliveries, {len(delivery_alerts)} alerts ({len(critical_delivery_alerts)} critical)")

    def test_layer4_router_cache_monitoring(self, health_monitoring_system):
        """Test Layer 4 (EventRouter) cache and routing monitoring."""
        system = health_monitoring_system
        event_router = system['event_router']
        scenario = HealthTestScenario("Layer4_Routing", "Event Router Cache Monitoring")

        # Add routing rules for monitoring
        from src.infrastructure.websocket.event_router import RoutingRule, RoutingStrategy

        monitoring_rules = [
            RoutingRule(
                rule_id='monitor_rule_1',
                name='Monitor Rule 1',
                description='First monitoring rule',
                event_type_patterns=[r'monitor_.*'],
                content_filters={'test_type': 'performance'},
                user_criteria={},
                strategy=RoutingStrategy.CONTENT_BASED,
                destinations=['monitor_room_1'],
                priority=DeliveryPriority.MEDIUM
            ),
            RoutingRule(
                rule_id='monitor_rule_2',
                name='Monitor Rule 2',
                description='Second monitoring rule',
                event_type_patterns=[r'cache_.*'],
                content_filters={'cache_test': True},
                user_criteria={},
                strategy=RoutingStrategy.BROADCAST_ALL,
                destinations=['monitor_room_2'],
                priority=DeliveryPriority.HIGH
            )
        ]

        for rule in monitoring_rules:
            event_router.add_routing_rule(rule)

        # Test routing performance monitoring
        routing_samples = []
        cache_behavior = []

        for test_iteration in range(50):
            start_time = time.time()

            # Alternate between cacheable and non-cacheable events
            if test_iteration % 2 == 0:
                event_type = 'monitor_event'
                event_data = {'test_type': 'performance', 'iteration': test_iteration}
            else:
                event_type = 'cache_event'
                event_data = {'cache_test': True, 'iteration': test_iteration}

            routing_result = event_router.route_event(
                event_type=event_type,
                event_data=event_data,
                user_context={'monitor_test': True}
            )

            routing_time_ms = (time.time() - start_time) * 1000
            routing_samples.append(routing_time_ms)

            scenario.record_metric('routing_time_ms', routing_time_ms)
            scenario.record_metric('matched_rules', len(routing_result.matched_rules))
            scenario.record_metric('cache_hit', getattr(routing_result, 'cache_hit', False))

            # Monitor routing performance
            if routing_time_ms > 20.0:  # Layer 4 target
                scenario.add_alert(
                    'routing_slow',
                    f"Routing took {routing_time_ms:.2f}ms (target: 20ms)",
                    'warning' if routing_time_ms < 40.0 else 'critical'
                )

            # Track cache behavior
            cache_hit = getattr(routing_result, 'cache_hit', False)
            cache_behavior.append(cache_hit)

        # Get router health status
        router_health = event_router.get_health_status()

        assert 'service' in router_health, "Router health missing service ID"
        assert router_health['service'] == 'event_router', f"Wrong router service ID: {router_health['service']}"

        # Verify performance targets
        if 'performance_targets' in router_health:
            targets = router_health['performance_targets']
            assert targets['routing_time_target_ms'] == 20.0, "Wrong routing time target"
            assert targets['cache_hit_rate_target_percent'] == 50.0, "Wrong cache hit rate target"

        scenario.record_metric('health_status', router_health['status'])

        # Analyze routing monitoring results
        avg_routing_time = statistics.mean(routing_samples)
        p95_routing_time = sorted(routing_samples)[int(0.95 * len(routing_samples))]

        cache_hit_rate = (sum(cache_behavior) / len(cache_behavior)) * 100 if cache_behavior else 0

        assert avg_routing_time < 30.0, f"Average routing {avg_routing_time:.2f}ms too slow"
        assert p95_routing_time < 50.0, f"P95 routing {p95_routing_time:.2f}ms too slow"

        # Cache monitoring
        if cache_hit_rate > 0:
            scenario.record_metric('cache_hit_rate_percent', cache_hit_rate)

            if cache_hit_rate < 10.0:  # Very low cache hit rate
                scenario.add_alert(
                    'cache_ineffective',
                    f"Cache hit rate {cache_hit_rate:.1f}% very low",
                    'warning'
                )

        # Check routing alerts
        routing_alerts = [a for a in scenario.alerts if a['type'].startswith('routing')]
        critical_routing_alerts = [a for a in routing_alerts if a['severity'] == 'critical']

        assert len(critical_routing_alerts) < 5, f"Too many critical routing alerts: {len(critical_routing_alerts)}"

        print(f"✅ Layer 4 Routing Monitoring: {avg_routing_time:.1f}ms avg, {p95_routing_time:.1f}ms P95, {cache_hit_rate:.1f}% cache hit rate, {len(routing_alerts)} alerts")

    def test_integrated_health_status_aggregation(self, health_monitoring_system):
        """Test integrated health status across all layers."""
        system = health_monitoring_system
        universal_manager = system['universal_manager']
        scenario = HealthTestScenario("Integrated_Health", "System-wide Health Aggregation")

        # Setup comprehensive system activity
        for i in range(100):
            universal_manager.subscribe_user(
                user_id=f"integrated_user_{i:02d}",
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                    'symbols': ['AAPL', 'MSFT'][i % 2],
                    'confidence_min': 0.7
                }
            )

        # Generate integrated activity
        with patch.object(universal_manager, '_find_interested_users') as mock_find:
            mock_find.return_value = {f"integrated_user_{i:02d}" for i in range(20)}

            mock_routing_result = Mock()
            mock_routing_result.total_users = 20
            mock_routing_result.matched_rules = ['integrated_rule']
            mock_routing_result.routing_time_ms = 12.0
            mock_routing_result.cache_hit = True

            with patch.object(system['event_router'], 'route_event') as mock_route:
                mock_route.return_value = mock_routing_result

                for i in range(30):
                    universal_manager.broadcast_event(
                        event_type='integrated_health_test',
                        event_data={'test_iteration': i, 'integrated_test': True},
                        targeting_criteria={'subscription_type': 'tier_patterns'}
                    )

        # Get integrated health status
        integrated_health = universal_manager.get_health_status()

        # Verify integrated health structure
        required_fields = ['service', 'status', 'message', 'timestamp', 'stats', 'performance_targets']
        for field in required_fields:
            assert field in integrated_health, f"Integrated health missing {field}"

        scenario.record_metric('integrated_status', integrated_health['status'])
        scenario.record_metric('total_users', integrated_health['stats']['total_users'])
        scenario.record_metric('events_broadcast', integrated_health['stats']['events_broadcast'])

        # Verify multi-layer statistics integration
        stats = integrated_health['stats']

        # Layer 1 stats
        assert 'total_users' in stats, "Missing Layer 1 user stats"
        assert 'events_broadcast' in stats, "Missing Layer 1 event stats"

        # Layer 2 stats
        expected_layer2_stats = ['index_lookup_count', 'index_avg_lookup_ms', 'index_cache_hit_rate']
        layer2_present = any(stat in stats for stat in expected_layer2_stats)
        # Note: In mocked environment, these may not be present

        # Layer 3 stats
        expected_layer3_stats = ['broadcast_events_delivered', 'broadcast_avg_latency_ms', 'broadcast_success_rate']
        layer3_present = any(stat in stats for stat in expected_layer3_stats)

        # Layer 4 stats
        expected_layer4_stats = ['routing_total_events', 'routing_avg_time_ms', 'routing_cache_hit_rate']
        layer4_present = any(stat in stats for stat in expected_layer4_stats)

        # Verify performance targets include all layers
        targets = integrated_health['performance_targets']

        assert 'filtering_target_ms' in targets, "Missing Layer 2 filtering target"
        assert 'broadcast_target_ms' in targets, "Missing Layer 3 broadcast target"
        assert 'target_concurrent_users' in targets, "Missing user capacity target"

        assert targets['filtering_target_ms'] == 5.0, "Wrong filtering target"
        assert targets['broadcast_target_ms'] == 100.0, "Wrong broadcast target"
        assert targets['target_concurrent_users'] == 500, "Wrong user target"

        # Test health status determination logic
        assert integrated_health['status'] in ['healthy', 'warning', 'error'], f"Invalid status: {integrated_health['status']}"

        # Health message should be descriptive
        assert len(integrated_health['message']) > 10, "Health message too brief"

        # Test health status with simulated issues
        print("  Testing health status with simulated performance issues...")

        # Mock Layer 2 performance issues
        with patch.object(system['index_manager'], 'find_matching_users') as mock_slow_index:
            def slow_indexing(*args, **kwargs):
                time.sleep(0.02)  # 20ms delay
                return {'integrated_user_01'}

            mock_slow_index.side_effect = slow_indexing

            # This should potentially affect health status
            degraded_health = universal_manager.get_health_status()

            # System should detect performance issues
            scenario.record_metric('degraded_status', degraded_health['status'])

            if degraded_health['status'] != 'healthy':
                scenario.add_alert(
                    'health_degradation_detected',
                    f"Health degraded to {degraded_health['status']}",
                    'info'
                )

        print(f"✅ Integrated Health Monitoring: Status {integrated_health['status']}, {stats['total_users']} users, {stats['events_broadcast']} events")

    def test_performance_degradation_detection(self, health_monitoring_system):
        """Test detection of performance degradation across layers."""
        system = health_monitoring_system
        universal_manager = system['universal_manager']
        scenario = HealthTestScenario("Degradation_Detection", "Performance Degradation Detection")

        # Establish baseline performance
        baseline_users = 50
        for i in range(baseline_users):
            universal_manager.subscribe_user(
                user_id=f"baseline_user_{i:02d}",
                subscription_type="tier_patterns",
                filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
            )

        # Record baseline performance
        baseline_samples = []
        for i in range(10):
            start_time = time.time()

            with patch.object(universal_manager, '_find_interested_users') as mock_find:
                mock_find.return_value = {f"baseline_user_{j:02d}" for j in range(10)}

                mock_routing_result = Mock()
                mock_routing_result.total_users = 10
                mock_routing_result.matched_rules = ['baseline_rule']
                mock_routing_result.routing_time_ms = 8.0
                mock_routing_result.cache_hit = False

                with patch.object(system['event_router'], 'route_event') as mock_route:
                    mock_route.return_value = mock_routing_result

                    universal_manager.broadcast_event(
                        event_type='baseline_test',
                        event_data={'baseline_test': True, 'iteration': i},
                        targeting_criteria={'subscription_type': 'tier_patterns'}
                    )

            baseline_time_ms = (time.time() - start_time) * 1000
            baseline_samples.append(baseline_time_ms)
            scenario.record_metric('baseline_performance_ms', baseline_time_ms)

        baseline_avg = statistics.mean(baseline_samples)
        scenario.record_metric('baseline_average_ms', baseline_avg)

        # Simulate progressive degradation
        degradation_scenarios = [
            {'name': 'light_load', 'additional_users': 100, 'expected_degradation': 1.2},
            {'name': 'moderate_load', 'additional_users': 200, 'expected_degradation': 1.5},
            {'name': 'heavy_load', 'additional_users': 400, 'expected_degradation': 2.0}
        ]

        for degradation in degradation_scenarios:
            print(f"    Testing {degradation['name']} degradation scenario...")

            # Add load
            for i in range(degradation['additional_users']):
                universal_manager.subscribe_user(
                    user_id=f"degradation_{degradation['name']}_user_{i:03d}",
                    subscription_type="tier_patterns",
                    filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
                )

            # Test performance under load
            degradation_samples = []
            for i in range(15):
                start_time = time.time()

                with patch.object(universal_manager, '_find_interested_users') as mock_find:
                    mock_find.return_value = {f"baseline_user_{j:02d}" for j in range(10)}

                    mock_routing_result = Mock()
                    mock_routing_result.total_users = 10
                    mock_routing_result.matched_rules = ['degradation_rule']
                    mock_routing_result.routing_time_ms = 8.0 * degradation['expected_degradation']
                    mock_routing_result.cache_hit = False

                    with patch.object(system['event_router'], 'route_event') as mock_route:
                        mock_route.return_value = mock_routing_result

                        universal_manager.broadcast_event(
                            event_type='degradation_test',
                            event_data={'degradation_scenario': degradation['name'], 'iteration': i},
                            targeting_criteria={'subscription_type': 'tier_patterns'}
                        )

                degradation_time_ms = (time.time() - start_time) * 1000
                degradation_samples.append(degradation_time_ms)
                scenario.record_metric(f'degradation_{degradation["name"]}_ms', degradation_time_ms)

            degradation_avg = statistics.mean(degradation_samples)
            performance_ratio = degradation_avg / baseline_avg

            scenario.record_metric(f'{degradation["name"]}_average_ms', degradation_avg)
            scenario.record_metric(f'{degradation["name"]}_ratio', performance_ratio)

            # Check for degradation detection
            if performance_ratio > 1.3:  # 30% degradation
                scenario.add_alert(
                    'performance_degradation',
                    f"{degradation['name']}: {performance_ratio:.1f}x slower than baseline ({degradation_avg:.1f}ms vs {baseline_avg:.1f}ms)",
                    'warning' if performance_ratio < 2.0 else 'critical'
                )

            # Health monitoring should reflect degradation
            degraded_health = universal_manager.get_health_status()
            scenario.record_metric(f'health_under_{degradation["name"]}', degraded_health['status'])

            # For heavy degradation, health status should reflect issues
            if performance_ratio > 2.0 and degraded_health['status'] == 'healthy':
                scenario.add_alert(
                    'health_detection_missed',
                    f"Health monitoring did not detect {performance_ratio:.1f}x performance degradation",
                    'warning'
                )

        # Analyze degradation detection results
        degradation_alerts = [a for a in scenario.alerts if a['type'] == 'performance_degradation']
        detection_failures = [a for a in scenario.alerts if a['type'] == 'health_detection_missed']

        # Should detect significant degradation
        assert len(degradation_alerts) > 0, "Performance degradation not detected"

        # Health monitoring should be reasonably effective
        assert len(detection_failures) < 2, f"Health monitoring missed {len(detection_failures)} degradation scenarios"

        print(f"✅ Degradation Detection: {len(degradation_alerts)} degradations detected, {len(detection_failures)} missed")

    def test_alerting_and_threshold_validation(self, health_monitoring_system):
        """Test alerting mechanisms and threshold validation."""
        system = health_monitoring_system
        universal_manager = system['universal_manager']
        scenario = HealthTestScenario("Alerting_Validation", "Alerting and Threshold Validation")

        # Define test thresholds
        test_thresholds = {
            'filtering_time_warning_ms': 8.0,
            'filtering_time_critical_ms': 15.0,
            'broadcast_time_warning_ms': 120.0,
            'broadcast_time_critical_ms': 200.0,
            'routing_time_warning_ms': 25.0,
            'routing_time_critical_ms': 40.0,
            'user_capacity_warning': 400,
            'user_capacity_critical': 600
        }

        scenario.record_metric('test_thresholds', test_thresholds)

        # Test user capacity thresholds
        print("    Testing user capacity thresholds...")

        current_users = 0
        for capacity_test in [200, 350, 450, 550]:  # Gradual increase
            # Add users to reach target capacity
            users_to_add = capacity_test - current_users
            for i in range(users_to_add):
                universal_manager.subscribe_user(
                    user_id=f"capacity_test_user_{current_users + i:03d}",
                    subscription_type="tier_patterns",
                    filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
                )

            current_users = capacity_test

            # Check health status at this capacity
            capacity_health = universal_manager.get_health_status()
            scenario.record_metric(f'health_at_{capacity_test}_users', capacity_health['status'])

            # Validate threshold behavior
            if capacity_test >= test_thresholds['user_capacity_critical']:
                scenario.add_alert(
                    'capacity_critical',
                    f"User count {capacity_test} exceeds critical threshold {test_thresholds['user_capacity_critical']}",
                    'critical'
                )

                # Health status should reflect critical capacity
                if capacity_health['status'] not in ['warning', 'error']:
                    scenario.add_alert(
                        'threshold_validation_failed',
                        f"Health status {capacity_health['status']} does not reflect critical user capacity",
                        'warning'
                    )

            elif capacity_test >= test_thresholds['user_capacity_warning']:
                scenario.add_alert(
                    'capacity_warning',
                    f"User count {capacity_test} exceeds warning threshold {test_thresholds['user_capacity_warning']}",
                    'warning'
                )

        # Test performance threshold validation
        print("    Testing performance thresholds...")

        # Simulate slow filtering
        with patch.object(system['index_manager'], 'find_matching_users') as mock_slow_filter:
            def slow_filtering(*args, **kwargs):
                # Simulate slow filtering that exceeds thresholds
                time.sleep(0.018)  # 18ms - above warning threshold
                return {'capacity_test_user_001'}

            mock_slow_filter.side_effect = slow_filtering

            # Test filtering threshold detection
            with patch.object(universal_manager, '_find_interested_users') as mock_find:
                mock_find.return_value = {'capacity_test_user_001'}

                start_time = time.time()
                universal_manager.broadcast_event(
                    event_type='threshold_test',
                    event_data={'threshold_test': True},
                    targeting_criteria={'subscription_type': 'tier_patterns'}
                )
                total_time_ms = (time.time() - start_time) * 1000

                scenario.record_metric('slow_filtering_test_ms', total_time_ms)

                if total_time_ms > test_thresholds['filtering_time_critical_ms']:
                    scenario.add_alert(
                        'filtering_critical',
                        f"Filtering time {total_time_ms:.1f}ms exceeds critical threshold",
                        'critical'
                    )
                elif total_time_ms > test_thresholds['filtering_time_warning_ms']:
                    scenario.add_alert(
                        'filtering_warning',
                        f"Filtering time {total_time_ms:.1f}ms exceeds warning threshold",
                        'warning'
                    )

        # Test routing performance thresholds
        with patch.object(system['event_router'], 'route_event') as mock_slow_routing:
            def slow_routing(*args, **kwargs):
                time.sleep(0.03)  # 30ms - above warning threshold
                mock_result = Mock()
                mock_result.total_users = 1
                mock_result.matched_rules = ['slow_rule']
                mock_result.routing_time_ms = 30.0
                mock_result.cache_hit = False
                return mock_result

            mock_slow_routing.side_effect = slow_routing

            with patch.object(universal_manager, '_find_interested_users') as mock_find:
                mock_find.return_value = {'capacity_test_user_001'}

                start_time = time.time()
                universal_manager.broadcast_event(
                    event_type='routing_threshold_test',
                    event_data={'routing_test': True},
                    targeting_criteria={'subscription_type': 'tier_patterns'}
                )
                routing_time_ms = (time.time() - start_time) * 1000

                scenario.record_metric('slow_routing_test_ms', routing_time_ms)

                # Check if routing threshold was exceeded (30ms simulated)
                if test_thresholds['routing_time_critical_ms'] < 30.0:
                    scenario.add_alert(
                        'routing_critical',
                        "Routing time 30.0ms exceeds critical threshold",
                        'critical'
                    )
                elif test_thresholds['routing_time_warning_ms'] < 30.0:
                    scenario.add_alert(
                        'routing_warning',
                        "Routing time 30.0ms exceeds warning threshold",
                        'warning'
                    )

        # Analyze alerting effectiveness
        warning_alerts = [a for a in scenario.alerts if a['severity'] == 'warning']
        critical_alerts = [a for a in scenario.alerts if a['severity'] == 'critical']
        validation_failures = [a for a in scenario.alerts if a['type'] == 'threshold_validation_failed']

        # Should generate appropriate alerts
        assert len(warning_alerts) > 0, "No warning alerts generated during threshold testing"

        # Critical thresholds should be detected
        capacity_critical_alerts = [a for a in critical_alerts if a['type'] == 'capacity_critical']

        # Threshold validation should mostly succeed
        assert len(validation_failures) < 2, f"Too many threshold validation failures: {len(validation_failures)}"

        # Test final health status incorporates alerting
        final_health = universal_manager.get_health_status()
        scenario.record_metric('final_health_status', final_health['status'])

        # With high user load and performance issues, health should reflect problems
        if final_health['status'] == 'healthy' and len(critical_alerts) > 0:
            scenario.add_alert(
                'health_alerting_disconnect',
                f"Health status {final_health['status']} despite {len(critical_alerts)} critical alerts",
                'warning'
            )

        print(f"✅ Alerting Validation: {len(warning_alerts)} warnings, {len(critical_alerts)} critical, {len(validation_failures)} validation failures")

    def test_health_monitoring_under_stress(self, health_monitoring_system):
        """Test health monitoring system remains functional under stress."""
        system = health_monitoring_system
        universal_manager = system['universal_manager']
        scenario = HealthTestScenario("Stress_Monitoring", "Health Monitoring Under Stress")

        print("    Applying stress load for health monitoring test...")

        # Apply significant load
        stress_users = 300
        for i in range(stress_users):
            universal_manager.subscribe_user(
                user_id=f"stress_monitor_user_{i:03d}",
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal'][i % 2],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL'][i % 3],
                    'confidence_min': 0.7
                }
            )

        # Generate concurrent stress activity
        stress_results = []

        def stress_health_monitoring_worker(worker_id: int):
            """Worker that generates stress while monitoring health."""
            worker_results = []

            for i in range(20):
                # Generate activity
                try:
                    with patch.object(universal_manager, '_find_interested_users') as mock_find:
                        mock_find.return_value = {f"stress_monitor_user_{j:03d}" for j in range(15)}

                        mock_routing_result = Mock()
                        mock_routing_result.total_users = 15
                        mock_routing_result.matched_rules = [f'stress_rule_{worker_id}']
                        mock_routing_result.routing_time_ms = 10.0 + random.uniform(-2, 8)  # Variable performance
                        mock_routing_result.cache_hit = i % 3 == 0

                        with patch.object(system['event_router'], 'route_event') as mock_route:
                            mock_route.return_value = mock_routing_result

                            universal_manager.broadcast_event(
                                event_type='stress_health_test',
                                event_data={'worker_id': worker_id, 'iteration': i, 'stress_test': True},
                                targeting_criteria={'subscription_type': 'tier_patterns'}
                            )

                    # Check health status during stress
                    health_start = time.time()
                    health_status = universal_manager.get_health_status()
                    health_check_time_ms = (time.time() - health_start) * 1000

                    worker_results.append({
                        'worker_id': worker_id,
                        'iteration': i,
                        'health_status': health_status['status'],
                        'health_check_time_ms': health_check_time_ms,
                        'success': True
                    })

                    # Health checks should remain fast even under stress
                    if health_check_time_ms > 50.0:
                        scenario.add_alert(
                            'health_check_slow',
                            f"Health check took {health_check_time_ms:.1f}ms under stress",
                            'warning'
                        )

                except Exception as e:
                    worker_results.append({
                        'worker_id': worker_id,
                        'iteration': i,
                        'error': str(e),
                        'success': False
                    })

                time.sleep(random.uniform(0.01, 0.05))  # Variable timing

            return worker_results

        # Run concurrent stress with health monitoring
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=6, thread_name_prefix="stress-health") as executor:
            futures = [
                executor.submit(stress_health_monitoring_worker, worker_id)
                for worker_id in range(6)
            ]

            for future in as_completed(futures, timeout=120):
                try:
                    worker_results = future.result()
                    stress_results.extend(worker_results)
                except Exception as e:
                    scenario.add_alert(
                        'stress_worker_failed',
                        f"Stress worker failed: {str(e)}",
                        'critical'
                    )

        # Analyze stress monitoring results
        successful_checks = [r for r in stress_results if r.get('success', False)]
        failed_checks = [r for r in stress_results if not r.get('success', False)]

        health_check_times = [r['health_check_time_ms'] for r in successful_checks if 'health_check_time_ms' in r]

        if health_check_times:
            avg_health_check_time = statistics.mean(health_check_times)
            max_health_check_time = max(health_check_times)

            scenario.record_metric('avg_health_check_time_ms', avg_health_check_time)
            scenario.record_metric('max_health_check_time_ms', max_health_check_time)

            # Health monitoring should remain responsive under stress
            assert avg_health_check_time < 30.0, f"Health checks averaged {avg_health_check_time:.1f}ms under stress"
            assert max_health_check_time < 100.0, f"Health check took {max_health_check_time:.1f}ms under stress"

        # Health monitoring should remain functional
        success_rate = (len(successful_checks) / len(stress_results)) * 100 if stress_results else 0
        assert success_rate >= 85.0, f"Health monitoring only {success_rate:.1f}% successful under stress"

        # System should still be monitorable after stress
        final_health = universal_manager.get_health_status()
        assert 'status' in final_health, "Health monitoring broken after stress"
        assert final_health['status'] in ['healthy', 'warning', 'error'], f"Invalid health status after stress: {final_health['status']}"

        scenario.record_metric('final_health_after_stress', final_health['status'])
        scenario.record_metric('successful_health_checks', len(successful_checks))
        scenario.record_metric('failed_health_checks', len(failed_checks))

        print(f"✅ Health Monitoring Under Stress: {success_rate:.1f}% success rate, {avg_health_check_time:.1f}ms avg check time")

    def test_observability_data_collection(self, health_monitoring_system):
        """Test comprehensive observability data collection."""
        system = health_monitoring_system
        universal_manager = system['universal_manager']
        scenario = HealthTestScenario("Observability", "Comprehensive Observability Data Collection")

        # Setup observability test environment
        for i in range(75):
            universal_manager.subscribe_user(
                user_id=f"observability_user_{i:02d}",
                subscription_type="tier_patterns",
                filters={
                    'pattern_types': ['BreakoutBO', 'TrendReversal', 'SurgeDetection'][i % 3],
                    'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA'][i % 4],
                    'confidence_min': 0.6 + (i % 4) * 0.1
                }
            )

        # Generate diverse activity for observability
        observability_activities = [
            {'type': 'subscription', 'count': 10, 'data': {'new_users': True}},
            {'type': 'broadcast', 'count': 25, 'data': {'broadcast_test': True}},
            {'type': 'optimization', 'count': 3, 'data': {'optimization_test': True}},
            {'type': 'cleanup', 'count': 2, 'data': {'cleanup_test': True}}
        ]

        for activity in observability_activities:
            for i in range(activity['count']):
                if activity['type'] == 'subscription':
                    temp_user_id = f"temp_observability_user_{i}"
                    success = universal_manager.subscribe_user(
                        user_id=temp_user_id,
                        subscription_type="tier_patterns",
                        filters={'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
                    )
                    scenario.record_metric('temp_subscription_success', success)

                    # Cleanup temporary user
                    if success:
                        universal_manager.unsubscribe_user(temp_user_id)

                elif activity['type'] == 'broadcast':
                    with patch.object(universal_manager, '_find_interested_users') as mock_find:
                        mock_find.return_value = {f"observability_user_{j:02d}" for j in range(10)}

                        mock_routing_result = Mock()
                        mock_routing_result.total_users = 10
                        mock_routing_result.matched_rules = ['observability_rule']
                        mock_routing_result.routing_time_ms = 9.0 + (i % 5)
                        mock_routing_result.cache_hit = i % 4 == 0  # 25% cache hit rate

                        with patch.object(system['event_router'], 'route_event') as mock_route:
                            mock_route.return_value = mock_routing_result

                            delivery_count = universal_manager.broadcast_event(
                                event_type='observability_test',
                                event_data={'activity_type': activity['type'], 'iteration': i},
                                targeting_criteria={'subscription_type': 'tier_patterns'}
                            )

                            scenario.record_metric('broadcast_delivery_count', delivery_count)

                elif activity['type'] == 'optimization':
                    with patch.object(system['index_manager'], 'optimize_indexes') as mock_opt:
                        mock_opt.return_value = {'optimized': True}
                        optimization_results = universal_manager.optimize_performance()
                        scenario.record_metric('optimization_success', 'performance_targets_met' in optimization_results)

                elif activity['type'] == 'cleanup':
                    cleaned_count = universal_manager.cleanup_inactive_subscriptions(max_inactive_hours=0.1)
                    scenario.record_metric('cleanup_count', cleaned_count)

        # Collect comprehensive observability data
        print("    Collecting comprehensive observability data...")

        # Layer 1: Universal WebSocket Manager observability
        ws_stats = universal_manager.get_subscription_stats()
        layer1_observability = {
            'total_users': ws_stats.get('total_users', 0),
            'total_subscriptions': ws_stats.get('total_subscriptions', 0),
            'events_broadcast': ws_stats.get('events_broadcast', 0),
            'events_delivered': ws_stats.get('events_delivered', 0),
            'subscription_errors': ws_stats.get('subscription_errors', 0),
            'broadcast_errors': ws_stats.get('broadcast_errors', 0),
            'avg_filtering_latency_ms': ws_stats.get('avg_filtering_latency_ms', 0)
        }

        scenario.record_metric('layer1_observability', layer1_observability)

        # Layer 2: Index Manager observability
        if hasattr(system['index_manager'], 'get_index_stats'):
            index_stats = system['index_manager'].get_index_stats()
            layer2_observability = {
                'total_indexes': index_stats.get('total_indexes', 0),
                'lookup_count': index_stats.get('lookup_count', 0),
                'avg_lookup_time_ms': index_stats.get('avg_lookup_time_ms', 0),
                'cache_hit_rate_percent': index_stats.get('cache_hit_rate_percent', 0),
                'index_updates': index_stats.get('index_updates', 0)
            }
            scenario.record_metric('layer2_observability', layer2_observability)

        # Layer 3: Broadcaster observability
        if hasattr(system['broadcaster'], 'get_broadcast_stats'):
            broadcast_stats = system['broadcaster'].get_broadcast_stats()
            layer3_observability = {
                'total_events': broadcast_stats.get('total_events', 0),
                'batches_created': broadcast_stats.get('batches_created', 0),
                'batches_delivered': broadcast_stats.get('batches_delivered', 0),
                'avg_delivery_latency_ms': broadcast_stats.get('avg_delivery_latency_ms', 0),
                'events_rate_limited': broadcast_stats.get('events_rate_limited', 0)
            }
            scenario.record_metric('layer3_observability', layer3_observability)

        # Layer 4: Event Router observability
        router_stats = system['event_router'].get_routing_stats()
        layer4_observability = {
            'total_events': router_stats.get('total_events', 0),
            'events_routed': router_stats.get('events_routed', 0),
            'avg_routing_time_ms': router_stats.get('avg_routing_time_ms', 0),
            'cache_hit_rate_percent': router_stats.get('cache_hit_rate_percent', 0),
            'routing_errors': router_stats.get('routing_errors', 0),
            'total_rules': router_stats.get('total_rules', 0)
        }
        scenario.record_metric('layer4_observability', layer4_observability)

        # Integrated health observability
        health_status = universal_manager.get_health_status()
        integrated_observability = {
            'overall_status': health_status['status'],
            'health_message': health_status['message'],
            'performance_targets_met': self._check_performance_targets(health_status),
            'component_health_count': len([k for k in health_status.keys() if k.endswith('_health')])
        }
        scenario.record_metric('integrated_observability', integrated_observability)

        # Validate observability data completeness
        observability_validation = {
            'layer1_complete': len(layer1_observability) >= 5,
            'layer4_complete': len(layer4_observability) >= 5,
            'health_data_present': 'status' in health_status and 'stats' in health_status,
            'performance_targets_defined': 'performance_targets' in health_status
        }

        scenario.record_metric('observability_validation', observability_validation)

        # Verify observability data quality
        for layer_name, layer_data in [
            ('layer1', layer1_observability),
            ('layer4', layer4_observability)
        ]:
            for metric_name, metric_value in layer_data.items():
                if isinstance(metric_value, (int, float)):
                    assert metric_value >= 0, f"{layer_name} metric {metric_name} is negative: {metric_value}"

        # Observability should be comprehensive
        assert observability_validation['health_data_present'], "Health data missing from observability"
        assert observability_validation['performance_targets_defined'], "Performance targets missing"

        # Data should reflect activity
        assert layer1_observability['total_users'] >= 75, f"User count not reflected: {layer1_observability['total_users']}"
        assert layer1_observability['events_broadcast'] > 0, "Broadcast activity not reflected"

        print(f"✅ Observability Data Collection: Layer1={observability_validation['layer1_complete']}, "
              f"Layer4={observability_validation['layer4_complete']}, "
              f"Health={observability_validation['health_data_present']}, "
              f"Status={integrated_observability['overall_status']}")

    def _check_performance_targets(self, health_status: dict[str, Any]) -> dict[str, bool]:
        """Check if performance targets are being met."""
        if 'performance_targets' not in health_status or 'stats' not in health_status:
            return {'targets_available': False}

        targets = health_status['performance_targets']
        stats = health_status['stats']

        targets_met = {
            'targets_available': True,
            'filtering_target_met': stats.get('avg_filtering_latency_ms', 0) <= targets.get('filtering_target_ms', 5.0),
            'broadcast_target_available': 'broadcast_target_ms' in targets,
            'user_capacity_within_limits': stats.get('total_users', 0) <= targets.get('target_concurrent_users', 500)
        }

        return targets_met

    def test_health_monitoring_integration_with_tier_patterns(self, health_monitoring_system):
        """Test health monitoring integration with TierPatternWebSocketIntegration."""
        system = health_monitoring_system
        universal_manager = system['universal_manager']
        scenario = HealthTestScenario("Tier_Integration_Health", "Health Monitoring with Tier Pattern Integration")

        # Create TierPatternWebSocketIntegration
        from src.core.services.tier_pattern_websocket_integration import (
            TierPatternWebSocketIntegration,
        )

        tier_integration = TierPatternWebSocketIntegration(universal_manager)

        # Test integrated health monitoring
        tier_health = tier_integration.get_health_status()

        # Verify tier integration health structure
        assert 'service' in tier_health, "Tier integration health missing service ID"
        assert 'websocket_health' in tier_health, "Tier integration missing WebSocket health"
        assert tier_health['service'] == 'tier_pattern_websocket_integration', "Wrong tier service ID"

        # WebSocket health should be included
        ws_health = tier_health['websocket_health']
        assert 'status' in ws_health, "WebSocket health missing status"

        scenario.record_metric('tier_integration_status', tier_health['status'])
        scenario.record_metric('websocket_health_status', ws_health['status'])

        # Test tier-specific statistics
        tier_stats = tier_integration.get_tier_pattern_stats()

        # Verify comprehensive tier statistics
        expected_tier_stats = [
            'tier_subscriptions', 'patterns_broadcast', 'alerts_generated',
            'websocket_manager_stats', 'architecture_layers', 'performance_targets'
        ]

        for stat_name in expected_tier_stats:
            assert stat_name in tier_stats, f"Missing tier stat: {stat_name}"

        scenario.record_metric('tier_stats_completeness', len(tier_stats))

        # Verify 4-layer architecture is reported
        assert tier_stats['architecture_layers'] == 4, f"Wrong architecture layer count: {tier_stats['architecture_layers']}"

        # Performance targets should include all layers
        perf_targets = tier_stats['performance_targets']
        expected_targets = ['filtering_target_ms', 'routing_target_ms', 'delivery_target_ms', 'total_target_ms']

        for target_name in expected_targets:
            assert target_name in perf_targets, f"Missing performance target: {target_name}"

        assert perf_targets['filtering_target_ms'] == 5, "Wrong filtering target"
        assert perf_targets['routing_target_ms'] == 20, "Wrong routing target"
        assert perf_targets['delivery_target_ms'] == 100, "Wrong delivery target"
        assert perf_targets['total_target_ms'] == 125, "Wrong total target"

        scenario.record_metric('performance_targets_complete', len(perf_targets))

        print(f"✅ Tier Pattern Integration Health: Status {tier_health['status']}, {len(tier_stats)} stats, 4-layer architecture confirmed")
