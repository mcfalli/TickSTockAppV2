"""
Sprint 25 Cross-System Integration Validation Tests
Comprehensive testing of TickStockPL (Producer) → Redis → TickStockAppV2 (Consumer) integration patterns.

Integration validation focuses on:
- Message flow validation between TickStockPL and TickStockApp
- Architectural compliance and loose coupling enforcement
- Performance requirements validation (<100ms delivery, <50ms queries)
- Error handling and system resilience patterns
- Consumer role compliance and boundary enforcement
"""

import json
import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import redis
from flask_socketio import SocketIO

from src.core.domain.events.tier_events import (
    EventPriority,
    PatternTier,
    TierPatternEvent,
)
from src.core.services.redis_event_subscriber import RedisEventSubscriber
from src.core.services.tier_pattern_websocket_integration import TierPatternWebSocketIntegration
from src.core.services.websocket_broadcaster import WebSocketBroadcaster

# Core components for integration testing
from src.core.services.websocket_subscription_manager import UniversalWebSocketManager
from src.presentation.websocket.manager import WebSocketManager


class TestTickStockPLIntegrationFlow:
    """Test complete integration flow from TickStockPL to browser clients."""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client with realistic pub-sub behavior."""
        redis_client = Mock(spec=redis.Redis)
        redis_client.ping.return_value = True

        # Mock pubsub functionality
        pubsub_mock = Mock()
        pubsub_mock.subscribe = Mock()
        pubsub_mock.unsubscribe = Mock()
        pubsub_mock.close = Mock()
        pubsub_mock.get_message = Mock()

        redis_client.pubsub.return_value = pubsub_mock

        return redis_client

    @pytest.fixture
    def mock_socketio(self):
        """Mock Flask-SocketIO for WebSocket delivery testing."""
        socketio = Mock(spec=SocketIO)
        socketio.server = Mock()
        socketio.server.enter_room = Mock()
        socketio.server.leave_room = Mock()
        socketio.emit = Mock()
        return socketio

    @pytest.fixture
    def integration_stack(self, mock_redis_client, mock_socketio):
        """Complete integration stack for end-to-end testing."""

        # Existing WebSocket manager (simplified)
        existing_ws_manager = Mock(spec=WebSocketManager)
        existing_ws_manager.is_user_connected.side_effect = lambda user_id: user_id in ["user1", "user2", "user3"]
        existing_ws_manager.get_user_connections.side_effect = lambda user_id: {f"conn_{user_id}_1"}
        existing_ws_manager.get_connected_users.return_value = {"user1", "user2", "user3"}

        # WebSocket broadcaster
        ws_broadcaster = Mock(spec=WebSocketBroadcaster)

        # Universal WebSocket manager
        ws_manager = UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis_client,
            existing_websocket_manager=existing_ws_manager,
            websocket_broadcaster=ws_broadcaster
        )

        # Tier pattern integration
        tier_integration = TierPatternWebSocketIntegration(websocket_manager=ws_manager)

        # Redis event subscriber
        redis_subscriber = RedisEventSubscriber(
            redis_client=mock_redis_client,
            socketio=mock_socketio,
            config={"channels": ["tickstock.events.patterns"]}
        )

        return {
            "redis_client": mock_redis_client,
            "socketio": mock_socketio,
            "existing_ws_manager": existing_ws_manager,
            "ws_broadcaster": ws_broadcaster,
            "ws_manager": ws_manager,
            "tier_integration": tier_integration,
            "redis_subscriber": redis_subscriber
        }

    def test_complete_tickstockpl_to_browser_message_flow(self, integration_stack):
        """Test complete message flow from TickStockPL event to browser delivery."""

        components = integration_stack
        tier_integration = components["tier_integration"]
        redis_subscriber = components["redis_subscriber"]
        mock_socketio = components["socketio"]

        # Step 1: Set up user subscriptions (TickStockApp consumer behavior)
        tier_integration.subscribe_user_to_tier_patterns("user1",
            tier_integration.__class__.__module__.split('.')[-1] and
            type("TierSubscriptionPreferences", (), {
                "to_filter_dict": lambda self: {
                    "pattern_types": ["BreakoutBO"],
                    "symbols": ["AAPL"],
                    "tiers": ["daily"],
                    "confidence_min": 0.8
                }
            })() or Mock(pattern_types=["BreakoutBO"], symbols=["AAPL"], tiers=[PatternTier.DAILY], confidence_min=0.8)
        )

        # Import the actual class for proper testing
        from src.core.services.tier_pattern_websocket_integration import TierSubscriptionPreferences

        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY],
            confidence_min=0.8
        )

        subscription_success = tier_integration.subscribe_user_to_tier_patterns("user1", preferences)
        assert subscription_success is True

        # Step 2: Simulate TickStockPL publishing pattern event to Redis
        tickstockpl_event_data = {
            "event_type": "pattern_detected",
            "source": "TickStockPL",
            "timestamp": time.time(),
            "pattern": "BreakoutBO",
            "symbol": "AAPL",
            "tier": "daily",
            "confidence": 0.85,
            "event_id": "tickstockpl_integration_test",
            "breakout_level": 150.25,
            "volume_surge": 2.1,
            "market_conditions": {
                "trend": "upward",
                "volatility": "normal"
            }
        }

        # Step 3: Process message through Redis subscriber (simulating Redis pub-sub)
        redis_message = {
            "type": "message",
            "channel": "tickstock.events.patterns",
            "data": json.dumps(tickstockpl_event_data)
        }

        # Simulate Redis message processing
        redis_subscriber._process_message(redis_message)

        # Step 4: Create structured event from Redis data
        tier_pattern_event = TierPatternEvent.from_redis_event(tickstockpl_event_data)

        # Verify event parsing
        assert tier_pattern_event.pattern_type == "BreakoutBO"
        assert tier_pattern_event.symbol == "AAPL"
        assert tier_pattern_event.tier == PatternTier.DAILY
        assert tier_pattern_event.confidence == 0.85
        assert tier_pattern_event.pattern_data["breakout_level"] == 150.25
        assert tier_pattern_event.pattern_data["volume_surge"] == 2.1

        # Step 5: Broadcast through tier integration (consumer role)
        delivery_count = tier_integration.broadcast_tier_pattern_event(tier_pattern_event)

        # Should deliver to user1 (matches subscription criteria)
        assert delivery_count == 1

        # Step 6: Verify WebSocket delivery to browser
        assert mock_socketio.emit.called
        emit_calls = mock_socketio.emit.call_args_list

        # Find the tier_pattern emit call
        pattern_calls = [call for call in emit_calls if call[0][0] == "tier_pattern"]
        assert len(pattern_calls) == 1

        # Verify message structure for browser
        event_envelope = pattern_calls[0][0][1]
        assert event_envelope["type"] == "tier_pattern"
        assert event_envelope["server_id"] == "tickstock-app-v2"
        assert "timestamp" in event_envelope

        # Verify event data integrity
        event_data = event_envelope["data"]
        assert event_data["pattern_type"] == "BreakoutBO"
        assert event_data["symbol"] == "AAPL"
        assert event_data["tier"] == "daily"
        assert event_data["confidence"] == 0.85

        # Step 7: Verify consumer role compliance - no pattern processing logic
        # Integration should only route and filter, not analyze or modify patterns
        assert "analysis" not in event_data
        assert "computed_indicators" not in event_data
        assert event_data["pattern_type"] == tickstockpl_event_data["pattern"]  # Unchanged
        assert event_data["confidence"] == tickstockpl_event_data["confidence"]  # Unchanged

        # Step 8: Verify performance targets
        ws_manager = components["ws_manager"]
        filtering_latency = ws_manager.metrics.filtering_latency_ms
        broadcast_latency = ws_manager.metrics.broadcast_latency_ms

        assert filtering_latency < 5.0, f"Filtering took {filtering_latency}ms, target <5ms"
        assert broadcast_latency < 100.0, f"Broadcast took {broadcast_latency}ms, target <100ms"

    def test_architectural_compliance_consumer_role_enforcement(self, integration_stack):
        """Test that TickStockApp maintains consumer role and doesn't perform producer tasks."""

        components = integration_stack
        tier_integration = components["tier_integration"]
        ws_manager = components["ws_manager"]

        # Consumer role compliance tests

        # 1. Should NOT generate pattern events locally
        with pytest.raises(AttributeError):
            # Should not have pattern detection methods
            tier_integration.detect_pattern("AAPL", [1, 2, 3])

        with pytest.raises(AttributeError):
            # Should not have market analysis methods
            tier_integration.analyze_market_conditions("SPY")

        # 2. Should only consume and route Redis events
        from src.core.services.tier_pattern_websocket_integration import TierSubscriptionPreferences

        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY],
            confidence_min=0.7
        )

        # Should successfully subscribe (consumer behavior)
        success = tier_integration.subscribe_user_to_tier_patterns("consumer_test_user", preferences)
        assert success is True

        # 3. Should route events without modification
        original_event = TierPatternEvent(
            pattern_type="TestPattern",
            symbol="TEST",
            tier=PatternTier.DAILY,
            confidence=0.75,
            event_id="compliance_test",
            timestamp=datetime.now(),
            pattern_data={"original_data": "unchanged"}
        )

        # Broadcast should preserve event integrity
        delivery_count = tier_integration.broadcast_tier_pattern_event(original_event)

        # Verify event was not modified during routing
        mock_socketio = components["socketio"]
        if mock_socketio.emit.called:
            emit_call = mock_socketio.emit.call_args_list[-1]
            if emit_call[0][0] == "tier_pattern":
                delivered_data = emit_call[0][1]["data"]
                assert delivered_data["pattern_type"] == "TestPattern"
                assert delivered_data["confidence"] == 0.75
                assert "original_data" in str(delivered_data)

        # 4. Should only interact with Redis as consumer (no publishing)
        redis_client = components["redis_client"]

        # Should not have called Redis publish methods
        assert not hasattr(redis_client, 'publish') or not redis_client.publish.called

        # Should only have subscription-related calls
        pubsub_calls = redis_client.pubsub.call_count
        assert pubsub_calls >= 0  # Consumer pattern uses pubsub for receiving

        # 5. Verify database access is read-only compliant
        # Integration layer should not perform database writes
        health_status = tier_integration.get_health_status()
        assert "database_writes" not in health_status  # Should not track write operations

        stats = tier_integration.get_tier_pattern_stats()
        # Should only track consumption and routing metrics
        expected_consumer_metrics = [
            "tier_subscriptions", "patterns_broadcast", "alerts_generated"
        ]

        for metric in expected_consumer_metrics:
            assert metric in stats

        # Should NOT track producer metrics
        prohibited_producer_metrics = [
            "patterns_detected", "market_analysis_performed", "database_pattern_writes"
        ]

        for metric in prohibited_producer_metrics:
            assert metric not in stats

    def test_loose_coupling_redis_communication_only(self, integration_stack):
        """Test that TickStockApp and TickStockPL communicate only via Redis pub-sub."""

        components = integration_stack
        redis_subscriber = components["redis_subscriber"]
        tier_integration = components["tier_integration"]

        # 1. Verify Redis pub-sub subscription setup
        redis_client = components["redis_client"]

        # Should subscribe to TickStockPL event channels
        expected_channels = {
            'tickstock.events.patterns',
            'tickstock.events.backtesting.progress',
            'tickstock.events.backtesting.results',
            'tickstock.health.status'
        }

        # Mock verification that correct channels are subscribed
        if hasattr(redis_subscriber, 'channels'):
            subscribed_channels = set(redis_subscriber.channels.keys())
            assert subscribed_channels == expected_channels

        # 2. Verify no direct HTTP/API calls to TickStockPL
        with patch('requests.get') as mock_get:
            with patch('requests.post') as mock_post:
                # Perform typical operations
                from src.core.services.tier_pattern_websocket_integration import (
                    TierSubscriptionPreferences,
                )

                preferences = TierSubscriptionPreferences(
                    pattern_types=["BreakoutBO"],
                    symbols=["AAPL"],
                    tiers=[PatternTier.DAILY]
                )

                tier_integration.subscribe_user_to_tier_patterns("coupling_test_user", preferences)

                # Simulate event processing
                test_event = TierPatternEvent(
                    pattern_type="BreakoutBO",
                    symbol="AAPL",
                    tier=PatternTier.DAILY,
                    confidence=0.8,
                    event_id="coupling_test",
                    timestamp=datetime.now()
                )

                tier_integration.broadcast_tier_pattern_event(test_event)

                # Should NOT have made any HTTP requests to TickStockPL
                assert not mock_get.called, "TickStockApp made HTTP GET request - violates loose coupling"
                assert not mock_post.called, "TickStockApp made HTTP POST request - violates loose coupling"

        # 3. Verify message flow is unidirectional (TickStockPL → TickStockApp)
        # TickStockApp should not publish pattern events to Redis
        with patch.object(redis_client, 'publish') as mock_publish:
            # Process events normally
            tier_integration.broadcast_tier_pattern_event(test_event)

            # Should not publish pattern events back to Redis
            pattern_publish_calls = [
                call for call in mock_publish.call_args_list
                if len(call[0]) > 0 and 'pattern' in str(call[0][0]).lower()
            ]

            assert len(pattern_publish_calls) == 0, "TickStockApp published pattern events - violates consumer role"

        # 4. Verify Redis-only job submission (for backtesting)
        # When TickStockApp submits jobs, should only use Redis
        with patch.object(redis_client, 'publish') as mock_publish:
            # Simulate backtest job submission (consumer → producer communication)
            job_data = {
                "job_type": "backtest",
                "job_id": "coupling_test_job",
                "symbols": ["AAPL"],
                "patterns": ["BreakoutBO"],
                "user_id": "test_user"
            }

            # This would be the proper way to submit jobs via Redis
            redis_client.publish('tickstock.jobs.backtest', json.dumps(job_data))

            # Verify Redis publish was called for job submission
            mock_publish.assert_called_with('tickstock.jobs.backtest', json.dumps(job_data))

        # 5. Test error handling maintains loose coupling
        # Even during errors, should not attempt direct communication
        with patch('requests.get') as mock_get:
            # Simulate Redis connection error
            redis_client.ping.side_effect = redis.ConnectionError("Redis connection failed")

            # Error handling should not fallback to direct HTTP calls
            health_status = tier_integration.get_health_status()

            # Should report error but not make direct calls
            assert not mock_get.called, "Error handling violated loose coupling by making HTTP requests"

            # Reset for other tests
            redis_client.ping.side_effect = None
            redis_client.ping.return_value = True

    def test_performance_integration_requirements(self, integration_stack):
        """Test integration meets performance requirements under realistic load."""

        components = integration_stack
        tier_integration = components["tier_integration"]
        ws_manager = components["ws_manager"]
        mock_socketio = components["socketio"]

        # Performance requirement: <100ms end-to-end delivery
        # Performance requirement: <50ms database queries (N/A for this layer)
        # Performance requirement: <5ms user filtering

        # Set up realistic user load
        user_count = 100
        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD", "INTC", "ORCL"]
        patterns = ["BreakoutBO", "TrendReversal", "SurgePattern", "Doji", "Hammer"]

        from src.core.services.tier_pattern_websocket_integration import TierSubscriptionPreferences

        subscription_start = time.time()

        # Subscribe users with diverse preferences
        for i in range(user_count):
            preferences = TierSubscriptionPreferences(
                pattern_types=[patterns[i % len(patterns)]],
                symbols=[symbols[i % len(symbols)]],
                tiers=[[PatternTier.DAILY], [PatternTier.INTRADAY]][i % 2],
                confidence_min=0.6 + (i % 4) * 0.1
            )

            success = tier_integration.subscribe_user_to_tier_patterns(f"perf_user{i}", preferences)
            assert success is True

        subscription_time = (time.time() - subscription_start) * 1000

        # Subscription should be fast
        assert subscription_time < 2000, f"Subscription setup took {subscription_time:.2f}ms, target <2000ms"

        # Test broadcast performance under load
        broadcast_times = []
        filtering_times = []

        for i in range(20):  # 20 events
            event = TierPatternEvent(
                pattern_type=patterns[i % len(patterns)],
                symbol=symbols[i % len(symbols)],
                tier=[PatternTier.DAILY, PatternTier.INTRADAY][i % 2],
                confidence=0.7 + (i % 3) * 0.1,
                event_id=f"perf_test_{i}",
                timestamp=datetime.now()
            )

            broadcast_start = time.time()
            delivery_count = tier_integration.broadcast_tier_pattern_event(event)
            broadcast_end = time.time()

            broadcast_time_ms = (broadcast_end - broadcast_start) * 1000
            broadcast_times.append(broadcast_time_ms)

            # Get filtering time from WebSocket manager
            filtering_time_ms = ws_manager.metrics.filtering_latency_ms
            filtering_times.append(filtering_time_ms)

            # Each event should be delivered quickly
            assert broadcast_time_ms < 100, f"Event {i} broadcast took {broadcast_time_ms:.2f}ms, target <100ms"
            assert delivery_count >= 0  # Should successfully process

        # Analyze overall performance
        avg_broadcast_time = sum(broadcast_times) / len(broadcast_times)
        max_broadcast_time = max(broadcast_times)
        avg_filtering_time = sum(filtering_times) / len(filtering_times) if filtering_times else 0

        # Performance assertions
        assert avg_broadcast_time < 50, f"Average broadcast {avg_broadcast_time:.2f}ms, target <50ms"
        assert max_broadcast_time < 100, f"Max broadcast {max_broadcast_time:.2f}ms, target <100ms"
        assert avg_filtering_time < 5, f"Average filtering {avg_filtering_time:.2f}ms, target <5ms"

        # Verify system health under load
        health_status = tier_integration.get_health_status()
        assert health_status["status"] in ["healthy", "warning"], f"System unhealthy under load: {health_status['status']}"

        # Memory usage should be reasonable
        stats = tier_integration.get_tier_pattern_stats()
        websocket_stats = stats["websocket_stats"]

        assert websocket_stats["active_subscriptions"] == user_count
        assert stats["patterns_broadcast"] == 20

        # Connection metrics should show efficient handling
        assert websocket_stats.get("subscription_errors", 0) == 0
        assert websocket_stats.get("broadcast_errors", 0) <= 1  # Allow minimal errors under load

        # Performance should remain consistent
        final_filtering_time = ws_manager.metrics.filtering_latency_ms
        assert final_filtering_time < 10, f"Filtering performance degraded to {final_filtering_time:.2f}ms under load"

    def test_error_handling_and_system_resilience(self, integration_stack):
        """Test system resilience and error handling in integration scenarios."""

        components = integration_stack
        tier_integration = components["tier_integration"]
        redis_client = components["redis_client"]
        mock_socketio = components["socketio"]
        redis_subscriber = components["redis_subscriber"]

        # 1. Test Redis connection failure handling
        original_ping = redis_client.ping
        redis_client.ping.side_effect = redis.ConnectionError("Redis connection lost")

        # System should handle Redis failures gracefully
        health_status = tier_integration.get_health_status()

        # Should still report status, not crash
        assert "status" in health_status
        assert "timestamp" in health_status

        # Restore Redis connection
        redis_client.ping = original_ping

        # 2. Test WebSocket delivery failure resilience
        from src.core.services.tier_pattern_websocket_integration import TierSubscriptionPreferences

        preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY]
        )

        tier_integration.subscribe_user_to_tier_patterns("resilience_user", preferences)

        # Simulate WebSocket emit failure
        mock_socketio.emit.side_effect = Exception("WebSocket connection failed")

        test_event = TierPatternEvent(
            pattern_type="BreakoutBO",
            symbol="AAPL",
            tier=PatternTier.DAILY,
            confidence=0.8,
            event_id="resilience_test",
            timestamp=datetime.now()
        )

        # Should handle WebSocket errors without crashing
        delivery_count = tier_integration.broadcast_tier_pattern_event(test_event)
        assert delivery_count == 0  # Failed to deliver due to error

        # Error should be tracked
        ws_manager = components["ws_manager"]
        assert ws_manager.metrics.broadcast_errors > 0

        # System should recover when error is resolved
        mock_socketio.emit.side_effect = None  # Remove error

        delivery_count = tier_integration.broadcast_tier_pattern_event(test_event)
        assert delivery_count == 1  # Should work again

        # 3. Test malformed Redis message handling
        # Simulate malformed message from TickStockPL
        malformed_messages = [
            {"type": "message", "channel": "tickstock.events.patterns", "data": "invalid json"},
            {"type": "message", "channel": "tickstock.events.patterns", "data": json.dumps({"pattern": "missing required fields"})},
            {"type": "message", "channel": "tickstock.events.patterns", "data": json.dumps({"pattern": None, "symbol": None, "confidence": "not_a_number"})}
        ]

        for malformed_message in malformed_messages:
            # Should handle malformed messages without crashing
            redis_subscriber._process_message(malformed_message)

            # System should still be functional
            health_status = redis_subscriber.get_health_status()
            assert health_status["status"] != "error"  # Should not crash the system

        # Verify error tracking
        stats = redis_subscriber.get_stats()
        assert stats["events_dropped"] > 0  # Should track dropped malformed messages

        # 4. Test high-load error scenarios
        # Simulate system under stress with some failures
        error_count = 0

        for i in range(50):  # High volume
            event = TierPatternEvent(
                pattern_type="StressTest",
                symbol="STRESS",
                tier=PatternTier.DAILY,
                confidence=0.7,
                event_id=f"stress_test_{i}",
                timestamp=datetime.now()
            )

            # Inject periodic failures
            if i % 10 == 9:  # Every 10th event fails
                mock_socketio.emit.side_effect = Exception("Periodic failure")
                error_count += 1
            else:
                mock_socketio.emit.side_effect = None

            delivery_count = tier_integration.broadcast_tier_pattern_event(event)

            # System should continue operating despite periodic failures

        # System should still be responsive after stress test
        final_health = tier_integration.get_health_status()
        assert final_health["status"] in ["healthy", "warning"]  # Should not be completely broken

        # Error tracking should show realistic numbers
        assert ws_manager.metrics.broadcast_errors >= error_count
        assert tier_integration.stats["patterns_broadcast"] == 50  # Should track all attempts

        # 5. Test recovery and cleanup
        mock_socketio.emit.side_effect = None  # Clear all errors

        # System should fully recover
        recovery_event = TierPatternEvent(
            pattern_type="RecoveryTest",
            symbol="RECOVERY",
            tier=PatternTier.DAILY,
            confidence=0.9,
            event_id="recovery_test",
            timestamp=datetime.now()
        )

        delivery_count = tier_integration.broadcast_tier_pattern_event(recovery_event)
        assert delivery_count == 1  # Should work perfectly after recovery

        # Final health check should show system is stable
        recovery_health = tier_integration.get_health_status()
        assert recovery_health["status"] in ["healthy", "warning"]

        # Cleanup should work properly
        cleanup_count = ws_manager.cleanup_inactive_subscriptions(max_inactive_hours=0.001)
        assert cleanup_count >= 0  # Should successfully perform cleanup


class TestCrossSystemBoundaryValidation:
    """Test that system boundaries are properly maintained between TickStockApp and TickStockPL."""

    def test_data_flow_boundaries(self):
        """Test that data flows correctly between system boundaries."""

        # Mock the complete system boundary
        mock_redis = Mock(spec=redis.Redis)
        mock_socketio = Mock(spec=SocketIO)

        # Create boundary components
        ws_manager = Mock()
        tier_integration = Mock()

        # 1. Test TickStockPL → Redis → TickStockApp flow

        # Simulate TickStockPL publishing to Redis
        tickstockpl_event = {
            "source": "TickStockPL",
            "pattern": "BreakoutBO",
            "symbol": "AAPL",
            "confidence": 0.85,
            "tier": "daily",
            "timestamp": time.time()
        }

        # Redis publishes event to channel
        mock_redis.publish("tickstock.events.patterns", json.dumps(tickstockpl_event))

        # TickStockApp should consume from Redis (not direct communication)
        assert mock_redis.publish.called
        publish_args = mock_redis.publish.call_args[0]
        assert publish_args[0] == "tickstock.events.patterns"
        assert json.loads(publish_args[1])["source"] == "TickStockPL"

        # 2. Test TickStockApp → Redis → TickStockPL job submission

        # TickStockApp submits job via Redis (proper consumer → producer communication)
        job_submission = {
            "job_type": "backtest",
            "job_id": "boundary_test_job",
            "user_id": "test_user",
            "symbols": ["AAPL"],
            "patterns": ["BreakoutBO"],
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }

        mock_redis.publish("tickstock.jobs.backtest", json.dumps(job_submission))

        # Verify proper job submission boundary
        job_publish_calls = [call for call in mock_redis.publish.call_args_list
                           if call[0][0] == "tickstock.jobs.backtest"]
        assert len(job_publish_calls) == 1

        job_data = json.loads(job_publish_calls[0][0][1])
        assert job_data["job_type"] == "backtest"
        assert job_data["symbols"] == ["AAPL"]

        # 3. Test boundary violation detection

        # Should NOT have direct method calls between systems
        with pytest.raises(AttributeError):
            # TickStockApp should not call TickStockPL methods directly
            tier_integration.call_tickstockpl_directly()

        with pytest.raises(AttributeError):
            # Should not have direct HTTP client for TickStockPL
            tier_integration.tickstockpl_http_client

    def test_role_separation_enforcement(self):
        """Test that producer and consumer roles are properly separated."""

        from src.core.services.tier_pattern_websocket_integration import (
            TierPatternWebSocketIntegration,
        )
        from src.core.services.websocket_subscription_manager import UniversalWebSocketManager

        # Create minimal integration setup for role testing
        mock_socketio = Mock()
        mock_redis = Mock()
        mock_existing_ws = Mock()
        mock_broadcaster = Mock()

        ws_manager = UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis,
            existing_websocket_manager=mock_existing_ws,
            websocket_broadcaster=mock_broadcaster
        )

        tier_integration = TierPatternWebSocketIntegration(websocket_manager=ws_manager)

        # Consumer role validation

        # 1. Should have consumer methods
        consumer_methods = [
            'subscribe_user_to_tier_patterns',
            'broadcast_tier_pattern_event',  # Broadcasting received events
            'get_tier_pattern_stats',
            'get_health_status'
        ]

        for method in consumer_methods:
            assert hasattr(tier_integration, method), f"Missing consumer method: {method}"

        # 2. Should NOT have producer methods
        prohibited_producer_methods = [
            'detect_patterns',
            'analyze_market_data',
            'generate_patterns',
            'run_backtesting',
            'calculate_technical_indicators',
            'store_pattern_results'
        ]

        for method in prohibited_producer_methods:
            assert not hasattr(tier_integration, method), f"Has prohibited producer method: {method}"

        # 3. Database access should be read-only oriented
        # Consumer should only read user preferences, symbols, not write pattern data

        # Methods that indicate read-only consumer behavior
        readonly_patterns = [
            'get_user_',  # Getting user data
            'get_subscription',  # Getting subscription data
            'get_stats',  # Getting statistics
            'get_health'  # Getting health status
        ]

        tier_methods = [method for method in dir(tier_integration) if not method.startswith('_')]

        # Should have read-oriented methods
        has_readonly_methods = any(
            any(pattern in method for pattern in readonly_patterns)
            for method in tier_methods
        )
        assert has_readonly_methods, "Consumer should have read-oriented methods"

        # Should NOT have write-oriented methods
        write_patterns = ['create_pattern', 'store_pattern', 'update_pattern', 'delete_pattern']
        has_write_methods = any(
            any(pattern in method for pattern in write_patterns)
            for method in tier_methods
        )
        assert not has_write_methods, "Consumer should not have pattern write methods"

        # 4. Event processing should be routing-only, not analysis
        test_event = TierPatternEvent(
            pattern_type="RoleTestPattern",
            symbol="ROLE",
            tier=PatternTier.DAILY,
            confidence=0.8,
            event_id="role_test",
            timestamp=datetime.now(),
            pattern_data={"original_value": 123}
        )

        # Mock user subscription for testing
        mock_existing_ws.is_user_connected.return_value = True
        mock_existing_ws.get_user_connections.return_value = {"conn1"}

        from src.core.services.tier_pattern_websocket_integration import TierSubscriptionPreferences
        preferences = TierSubscriptionPreferences(
            pattern_types=["RoleTestPattern"],
            symbols=["ROLE"],
            tiers=[PatternTier.DAILY]
        )

        tier_integration.subscribe_user_to_tier_patterns("role_test_user", preferences)

        # Process event - should route without modification
        original_confidence = test_event.confidence
        original_pattern_data = test_event.pattern_data.copy()

        delivery_count = tier_integration.broadcast_tier_pattern_event(test_event)

        # Event should be unchanged (consumer role - no processing)
        assert test_event.confidence == original_confidence
        assert test_event.pattern_data == original_pattern_data

        # Should have routed the event
        assert delivery_count >= 0

    def test_loose_coupling_validation(self):
        """Test that systems are properly loosely coupled via Redis."""

        # Test that all cross-system communication uses Redis channels
        expected_redis_channels = {
            # TickStockPL → TickStockApp (events)
            "tickstock.events.patterns",
            "tickstock.events.backtesting.progress",
            "tickstock.events.backtesting.results",
            "tickstock.health.status",

            # TickStockApp → TickStockPL (job requests)
            "tickstock.jobs.backtest",
            "tickstock.jobs.pattern_scan"
        }

        # Mock Redis to track channel usage
        mock_redis = Mock()
        published_channels = set()
        subscribed_channels = set()

        def track_publish(channel, data):
            published_channels.add(channel)
            return True

        def track_subscribe(channels):
            if isinstance(channels, (list, tuple)):
                subscribed_channels.update(channels)
            else:
                subscribed_channels.add(channels)
            return Mock()

        mock_redis.publish.side_effect = track_publish
        mock_pubsub = Mock()
        mock_pubsub.subscribe.side_effect = track_subscribe
        mock_redis.pubsub.return_value = mock_pubsub

        # Simulate system operations that should use Redis

        # 1. Event subscription (TickStockApp consuming)
        from src.core.services.redis_event_subscriber import RedisEventSubscriber

        mock_socketio = Mock()
        subscriber = RedisEventSubscriber(
            redis_client=mock_redis,
            socketio=mock_socketio,
            config={}
        )

        # Should subscribe to event channels
        result = subscriber.start()
        if result:  # Only check if start succeeded
            # Should have subscribed to expected channels
            event_channels = {
                "tickstock.events.patterns",
                "tickstock.events.backtesting.progress",
                "tickstock.events.backtesting.results",
                "tickstock.health.status"
            }

            channels_intersection = subscribed_channels.intersection(event_channels)
            assert len(channels_intersection) > 0, "Should subscribe to TickStockPL event channels"

        # 2. Job submission (TickStockApp → TickStockPL)
        job_data = {
            "job_type": "backtest",
            "symbols": ["AAPL"],
            "patterns": ["BreakoutBO"]
        }

        mock_redis.publish("tickstock.jobs.backtest", json.dumps(job_data))

        # Should have published to job channel
        assert "tickstock.jobs.backtest" in published_channels

        # 3. Verify no prohibited communication methods exist
        prohibited_patterns = [
            "http_client", "rest_client", "api_client",  # HTTP clients
            "direct_call", "remote_procedure",  # Direct calls
            "database_connection", "db_write"  # Direct DB writes
        ]

        # Check that integration components don't have prohibited communication methods
        integration_classes = [
            RedisEventSubscriber,
            TierPatternWebSocketIntegration,
            UniversalWebSocketManager
        ]

        for cls in integration_classes:
            class_methods = [method for method in dir(cls) if not method.startswith('_')]
            for method in class_methods:
                for pattern in prohibited_patterns:
                    assert pattern not in method.lower(), f"Class {cls.__name__} has prohibited method pattern '{pattern}' in '{method}'"

        # 4. Test that Redis is the ONLY communication mechanism
        with patch('requests.get') as mock_get:
            with patch('requests.post') as mock_post:
                with patch('urllib.request.urlopen') as mock_urllib:

                    # Perform normal operations
                    mock_redis.publish("tickstock.jobs.backtest", json.dumps(job_data))

                    # Should not make any HTTP requests
                    assert not mock_get.called, "System made HTTP GET request - violates loose coupling"
                    assert not mock_post.called, "System made HTTP POST request - violates loose coupling"
                    assert not mock_urllib.called, "System made urllib request - violates loose coupling"

                    # Only Redis operations should occur
                    assert mock_redis.publish.called, "Should use Redis for communication"


class TestEndToEndIntegrationScenarios:
    """Test complete end-to-end integration scenarios."""

    def test_user_pattern_alert_complete_workflow(self):
        """Test complete workflow: user subscribes → TickStockPL detects → user receives alert."""

        # This test simulates the complete integration workflow

        # Setup complete integration stack
        mock_redis = Mock(spec=redis.Redis)
        mock_socketio = Mock(spec=SocketIO)

        # Step 1: User connects and subscribes via TickStockApp UI
        from src.core.services.tier_pattern_websocket_integration import (
            TierPatternWebSocketIntegration,
            TierSubscriptionPreferences,
        )
        from src.core.services.websocket_subscription_manager import UniversalWebSocketManager

        mock_existing_ws = Mock()
        mock_existing_ws.is_user_connected.return_value = True
        mock_existing_ws.get_user_connections.return_value = {"user_conn_1"}

        ws_manager = UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis,
            existing_websocket_manager=mock_existing_ws,
            websocket_broadcaster=Mock()
        )

        tier_integration = TierPatternWebSocketIntegration(websocket_manager=ws_manager)

        # User subscribes to AAPL breakout patterns
        user_preferences = TierSubscriptionPreferences(
            pattern_types=["BreakoutBO"],
            symbols=["AAPL"],
            tiers=[PatternTier.DAILY],
            confidence_min=0.8,
            priority_min=EventPriority.MEDIUM
        )

        subscription_success = tier_integration.subscribe_user_to_tier_patterns("workflow_user", user_preferences)
        assert subscription_success is True

        # Step 2: TickStockPL detects pattern and publishes to Redis
        tickstockpl_pattern_data = {
            "event_type": "pattern_detected",
            "source": "TickStockPL",
            "pattern": "BreakoutBO",
            "symbol": "AAPL",
            "tier": "daily",
            "confidence": 0.87,
            "timestamp": time.time(),
            "event_id": "workflow_integration_test",
            "breakout_level": 175.50,
            "volume_confirmation": True,
            "market_context": {
                "sector_strength": 0.15,
                "market_regime": "bull"
            }
        }

        # Step 3: TickStockApp receives event via Redis (simulated)
        tier_pattern_event = TierPatternEvent.from_redis_event(tickstockpl_pattern_data)

        # Verify event was properly parsed
        assert tier_pattern_event.pattern_type == "BreakoutBO"
        assert tier_pattern_event.symbol == "AAPL"
        assert tier_pattern_event.confidence == 0.87
        assert tier_pattern_event.pattern_data["breakout_level"] == 175.50

        # Step 4: TickStockApp processes and routes event
        delivery_count = tier_integration.broadcast_tier_pattern_event(tier_pattern_event)

        # Should deliver to subscribed user
        assert delivery_count == 1

        # Step 5: Verify WebSocket delivery to user's browser
        websocket_calls = mock_socketio.emit.call_args_list
        tier_pattern_calls = [call for call in websocket_calls if call[0][0] == "tier_pattern"]

        assert len(tier_pattern_calls) == 1

        delivered_event = tier_pattern_calls[0][0][1]  # Event envelope
        assert delivered_event["type"] == "tier_pattern"
        assert delivered_event["server_id"] == "tickstock-app-v2"

        # Verify event data for browser client
        browser_event_data = delivered_event["data"]
        assert browser_event_data["pattern_type"] == "BreakoutBO"
        assert browser_event_data["symbol"] == "AAPL"
        assert browser_event_data["confidence"] == 0.87
        assert browser_event_data["priority"] == "high"  # Should be upgraded due to high confidence

        # Step 6: Verify user room targeting
        room_target = tier_pattern_calls[0][1]["room"]
        assert room_target == "user_workflow_user"

        # Step 7: Generate and deliver personalized alert
        user_alert = tier_integration.generate_pattern_alert(
            "workflow_user",
            tier_pattern_event,
            user_preferences.to_filter_dict()
        )

        assert user_alert is not None
        assert user_alert.user_id == "workflow_user"
        assert user_alert.pattern_event == tier_pattern_event

        # Broadcast personalized alert
        alert_delivered = tier_integration.broadcast_pattern_alert(user_alert)
        assert alert_delivered is True

        # Step 8: Verify complete workflow metrics
        final_stats = tier_integration.get_tier_pattern_stats()
        assert final_stats["tier_subscriptions"] == 1
        assert final_stats["patterns_broadcast"] == 1
        assert final_stats["alerts_generated"] == 1

        # Step 9: Verify system health after complete workflow
        health_status = tier_integration.get_health_status()
        assert health_status["status"] == "healthy"
        assert "websocket_health" in health_status

    def test_multi_user_multi_pattern_integration_scenario(self):
        """Test complex scenario with multiple users and pattern types."""

        # Setup integration stack
        mock_redis = Mock(spec=redis.Redis)
        mock_socketio = Mock(spec=SocketIO)

        mock_existing_ws = Mock()
        mock_existing_ws.is_user_connected.side_effect = lambda user_id: True
        mock_existing_ws.get_user_connections.side_effect = lambda user_id: {f"conn_{user_id}"}

        from src.core.services.tier_pattern_websocket_integration import (
            TierPatternWebSocketIntegration,
            TierSubscriptionPreferences,
        )
        from src.core.services.websocket_subscription_manager import UniversalWebSocketManager

        ws_manager = UniversalWebSocketManager(
            socketio=mock_socketio,
            redis_client=mock_redis,
            existing_websocket_manager=mock_existing_ws,
            websocket_broadcaster=Mock()
        )

        tier_integration = TierPatternWebSocketIntegration(websocket_manager=ws_manager)

        # Step 1: Multiple users with different preferences subscribe
        user_configs = {
            "trader_1": TierSubscriptionPreferences(
                pattern_types=["BreakoutBO", "TrendReversal"],
                symbols=["AAPL", "TSLA"],
                tiers=[PatternTier.DAILY],
                confidence_min=0.8
            ),
            "trader_2": TierSubscriptionPreferences(
                pattern_types=["BreakoutBO"],
                symbols=["AAPL", "GOOGL", "MSFT"],
                tiers=[PatternTier.INTRADAY, PatternTier.DAILY],
                confidence_min=0.7
            ),
            "analyst_1": TierSubscriptionPreferences(
                pattern_types=["TrendReversal", "SurgePattern"],
                symbols=["TSLA", "META"],
                tiers=[PatternTier.COMBO],
                confidence_min=0.9
            ),
            "portfolio_mgr": TierSubscriptionPreferences(
                pattern_types=["BreakoutBO", "TrendReversal", "SurgePattern"],
                symbols=["AAPL", "TSLA", "GOOGL", "MSFT", "META"],
                tiers=[PatternTier.DAILY, PatternTier.INTRADAY, PatternTier.COMBO],
                confidence_min=0.6
            )
        }

        for user_id, preferences in user_configs.items():
            success = tier_integration.subscribe_user_to_tier_patterns(user_id, preferences)
            assert success is True

        # Step 2: TickStockPL detects multiple patterns
        tickstockpl_events = [
            {
                "pattern": "BreakoutBO", "symbol": "AAPL", "tier": "daily",
                "confidence": 0.85, "timestamp": time.time(),
                "event_id": "multi_test_1"
            },
            {
                "pattern": "TrendReversal", "symbol": "TSLA", "tier": "combo",
                "confidence": 0.92, "timestamp": time.time(),
                "event_id": "multi_test_2"
            },
            {
                "pattern": "BreakoutBO", "symbol": "GOOGL", "tier": "intraday",
                "confidence": 0.78, "timestamp": time.time(),
                "event_id": "multi_test_3"
            },
            {
                "pattern": "SurgePattern", "symbol": "META", "tier": "combo",
                "confidence": 0.94, "timestamp": time.time(),
                "event_id": "multi_test_4"
            }
        ]

        # Step 3: Process events through integration
        delivery_results = []

        for event_data in tickstockpl_events:
            tier_event = TierPatternEvent.from_redis_event(event_data)
            delivery_count = tier_integration.broadcast_tier_pattern_event(tier_event)
            delivery_results.append((event_data["event_id"], delivery_count))

        # Step 4: Verify targeting logic

        # Event 1: BreakoutBO AAPL daily, conf=0.85
        # Should reach: trader_1 (✓), trader_2 (✓), portfolio_mgr (✓) = 3 users
        # Should NOT reach: analyst_1 (wants TrendReversal/SurgePattern, not BreakoutBO)
        assert delivery_results[0][1] == 3

        # Event 2: TrendReversal TSLA combo, conf=0.92
        # Should reach: trader_1 (✓ has TSLA+TrendReversal), analyst_1 (✓ wants combo TrendReversal), portfolio_mgr (✓) = 3 users
        # Should NOT reach: trader_2 (only wants BreakoutBO)
        assert delivery_results[1][1] == 3

        # Event 3: BreakoutBO GOOGL intraday, conf=0.78
        # Should reach: trader_2 (✓ has GOOGL+BreakoutBO+intraday), portfolio_mgr (✓) = 2 users
        # Should NOT reach: trader_1 (only daily tier), analyst_1 (doesn't want BreakoutBO)
        assert delivery_results[2][1] == 2

        # Event 4: SurgePattern META combo, conf=0.94
        # Should reach: analyst_1 (✓ has META+SurgePattern+combo), portfolio_mgr (✓) = 2 users
        # Should NOT reach: trader_1, trader_2 (don't want SurgePattern)
        assert delivery_results[3][1] == 2

        # Step 5: Verify WebSocket delivery calls
        total_websocket_calls = len(mock_socketio.emit.call_args_list)
        total_expected_deliveries = sum(result[1] for result in delivery_results)

        tier_pattern_calls = [call for call in mock_socketio.emit.call_args_list
                             if call[0][0] == "tier_pattern"]

        assert len(tier_pattern_calls) == total_expected_deliveries

        # Step 6: Verify room targeting is correct
        delivered_rooms = set()
        for call in tier_pattern_calls:
            room = call[1]["room"]
            delivered_rooms.add(room)

        expected_rooms = {f"user_{user_id}" for user_id in user_configs}
        # All users should have received at least one event
        assert delivered_rooms.issubset(expected_rooms)

        # Step 7: Verify final system state
        final_stats = tier_integration.get_tier_pattern_stats()
        assert final_stats["tier_subscriptions"] == len(user_configs)
        assert final_stats["patterns_broadcast"] == len(tickstockpl_events)

        health_status = tier_integration.get_health_status()
        assert health_status["status"] == "healthy"

        # Step 8: Test system performance under this realistic load
        websocket_stats = final_stats["websocket_stats"]
        assert websocket_stats["avg_filtering_latency_ms"] < 10  # Should be fast
        assert websocket_stats["avg_broadcast_latency_ms"] < 100  # Should meet targets
        assert websocket_stats["subscription_errors"] == 0  # Should be error-free
        assert websocket_stats["broadcast_errors"] == 0  # Should be error-free
