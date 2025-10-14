"""
End-to-End Integration Tests
Complete integration tests for Redis → Subscriber → Broadcaster → WebSocket flow.

Sprint 10 Phase 2: Validate complete TickStockPL integration flow from Redis events
through subscriber processing to WebSocket broadcasting to browser clients.
"""


import os

# Import components under test
import sys

from .fixtures import assert_performance_acceptable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from core.services.redis_event_subscriber import EventType


class TestEndToEndIntegration:
    """End-to-end integration tests for complete TickStockPL event flow."""

    def test_complete_pattern_alert_flow(self, integration_test_environment, performance_timer):
        """Test complete flow: TickStockPL → Redis → Subscriber → Broadcaster → WebSocket clients."""
        env = integration_test_environment

        # Set up WebSocket clients with different subscriptions
        client1 = env.add_mock_user('trader1', 'session1', ['Doji', 'Hammer'])
        client2 = env.add_mock_user('trader2', 'session2', ['Engulfing'])
        client3 = env.add_mock_user('trader3', 'session3', [])  # All patterns

        # Connect subscriber to broadcaster
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )

        # Start subscriber
        assert env.start_subscriber() is True

        # Simulate TickStockPL publishing pattern events
        performance_timer.start()

        # Event 1: Doji pattern (should reach trader1 and trader3)
        doji_event = env.simulator.publish_pattern_event('AAPL', 'Doji', 0.87)

        # Event 2: Engulfing pattern (should reach trader2 and trader3)
        engulfing_event = env.simulator.publish_pattern_event('GOOGL', 'Engulfing', 0.91)

        # Event 3: Morning Star pattern (should reach trader3 only)
        morning_star_event = env.simulator.publish_pattern_event('MSFT', 'Morning Star', 0.83)

        # Wait for complete processing
        env.wait_for_events(0.3)
        performance_timer.stop()

        # Verify end-to-end performance
        assert_performance_acceptable(performance_timer.elapsed_ms, max_ms=300)

        # Verify message delivery to correct clients

        # Trader1 should receive Doji only
        assert len(client1.received_messages) == 1
        doji_msg = client1.received_messages[0]
        assert doji_msg['event'] == 'pattern_alert'
        assert doji_msg['data']['pattern'] == 'Doji'
        assert doji_msg['data']['symbol'] == 'AAPL'

        # Trader2 should receive Engulfing only
        assert len(client2.received_messages) == 1
        engulfing_msg = client2.received_messages[0]
        assert engulfing_msg['event'] == 'pattern_alert'
        assert engulfing_msg['data']['pattern'] == 'Engulfing'
        assert engulfing_msg['data']['symbol'] == 'GOOGL'

        # Trader3 should receive all three patterns
        assert len(client3.received_messages) == 3
        received_patterns = [msg['data']['pattern'] for msg in client3.received_messages]
        assert set(received_patterns) == {'Doji', 'Engulfing', 'Morning Star'}

        # Verify subscriber statistics
        stats = env.subscriber.get_stats()
        assert stats['events_received'] == 3
        assert stats['events_processed'] == 3
        assert stats['events_forwarded'] == 3

        # Verify broadcaster statistics
        broadcaster_stats = env.broadcaster.get_stats()
        assert broadcaster_stats['active_connections'] == 3
        assert broadcaster_stats['messages_sent'] > 0

        env.stop_subscriber()

    def test_complete_backtesting_workflow(self, integration_test_environment, performance_timer):
        """Test complete backtesting workflow from job submission to result delivery."""
        env = integration_test_environment

        # Set up connected users
        client1 = env.add_mock_user('analyst1', 'session_a1', [])
        client2 = env.add_mock_user('analyst2', 'session_a2', [])

        # Connect subscriber to broadcaster for backtest events
        env.subscriber.add_event_handler(
            EventType.BACKTEST_PROGRESS,
            lambda event: env.broadcaster.broadcast_backtest_progress(event.to_websocket_dict())
        )
        env.subscriber.add_event_handler(
            EventType.BACKTEST_RESULT,
            lambda event: env.broadcaster.broadcast_backtest_result(event.to_websocket_dict())
        )

        assert env.start_subscriber() is True

        job_id = 'backtest_job_end2end_001'

        performance_timer.start()

        # Simulate complete backtest workflow
        # 1. Progress updates
        progress_steps = [0.0, 0.25, 0.50, 0.75, 1.0]
        for progress in progress_steps:
            status = 'processing' if progress < 1.0 else 'analyzing'
            env.simulator.publish_backtest_progress(job_id, progress, status)

        # 2. Final results
        env.simulator.publish_backtest_result(job_id, 'completed')

        env.wait_for_events(0.4)
        performance_timer.stop()

        # Verify performance
        assert_performance_acceptable(performance_timer.elapsed_ms, max_ms=400)

        # Verify both clients received all messages
        for client in [client1, client2]:
            # 5 progress updates + 1 result = 6 messages total
            assert len(client.received_messages) == 6

            # Verify progress messages
            progress_messages = [msg for msg in client.received_messages
                               if msg['event'] == 'backtest_progress']
            assert len(progress_messages) == 5

            # Verify progress values in order
            progress_values = [msg['data']['progress'] for msg in progress_messages]
            assert progress_values == progress_steps

            # Verify result message
            result_messages = [msg for msg in client.received_messages
                             if msg['event'] == 'backtest_result']
            assert len(result_messages) == 1

            result_msg = result_messages[0]
            assert result_msg['data']['job_id'] == job_id
            assert result_msg['data']['status'] == 'completed'

        env.stop_subscriber()

    def test_mixed_event_types_concurrent_processing(self, integration_test_environment, performance_timer):
        """Test concurrent processing of multiple event types."""
        env = integration_test_environment

        # Set up clients
        pattern_client = env.add_mock_user('trader', 'session_trader', ['Doji', 'Hammer'])
        backtest_client = env.add_mock_user('analyst', 'session_analyst', [])

        # Connect all event types to broadcaster
        event_handlers = {
            EventType.PATTERN_DETECTED: env.broadcaster.broadcast_pattern_alert,
            EventType.BACKTEST_PROGRESS: env.broadcaster.broadcast_backtest_progress,
            EventType.BACKTEST_RESULT: env.broadcaster.broadcast_backtest_result,
            EventType.SYSTEM_HEALTH: env.broadcaster.broadcast_system_health
        }

        for event_type, handler in event_handlers.items():
            env.subscriber.add_event_handler(
                event_type,
                lambda event, h=handler: h(event.to_websocket_dict())
            )

        assert env.start_subscriber() is True

        performance_timer.start()

        # Publish mixed events concurrently
        events_published = []

        # Pattern events
        for symbol, pattern in [('AAPL', 'Doji'), ('GOOGL', 'Hammer'), ('MSFT', 'Engulfing')]:
            event = env.simulator.publish_pattern_event(symbol, pattern, 0.85)
            events_published.append(('pattern', event))

        # Backtest events
        job_id = 'concurrent_test_job'
        for progress in [0.3, 0.7]:
            event = env.simulator.publish_backtest_progress(job_id, progress)
            events_published.append(('backtest_progress', event))

        backtest_result = env.simulator.publish_backtest_result(job_id)
        events_published.append(('backtest_result', backtest_result))

        # System health
        health_event = env.simulator.publish_system_health('healthy')
        events_published.append(('health', health_event))

        env.wait_for_events(0.5)
        performance_timer.stop()

        # Verify performance under concurrent load
        assert_performance_acceptable(performance_timer.elapsed_ms, max_ms=500)

        # Verify subscriber processed all events
        stats = env.subscriber.get_stats()
        assert stats['events_received'] == 7  # 3 patterns + 2 progress + 1 result + 1 health
        assert stats['events_processed'] == 7

        # Verify pattern client received filtered pattern events
        pattern_messages = [msg for msg in pattern_client.received_messages
                          if msg['event'] == 'pattern_alert']
        # Should receive Doji and Hammer (2 out of 3 patterns)
        assert len(pattern_messages) == 2
        received_patterns = [msg['data']['pattern'] for msg in pattern_messages]
        assert set(received_patterns) == {'Doji', 'Hammer'}

        # Verify backtest client received all broadcast events
        backtest_events = [msg for msg in backtest_client.received_messages
                         if msg['event'] in ['backtest_progress', 'backtest_result', 'system_health']]
        assert len(backtest_events) == 4  # 2 progress + 1 result + 1 health

        env.stop_subscriber()

    def test_subscriber_reconnection_with_active_clients(self, integration_test_environment):
        """Test subscriber reconnection while WebSocket clients remain connected."""
        env = integration_test_environment

        # Set up active client
        client = env.add_mock_user('persistent_user', 'persistent_session', ['Doji'])

        # Connect subscriber to broadcaster
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )

        # Start subscriber
        assert env.start_subscriber() is True

        # Send initial event
        env.simulator.publish_pattern_event('AAPL', 'Doji')
        env.wait_for_events(0.1)

        # Verify initial event received
        assert len(client.received_messages) == 1
        initial_message = client.received_messages[0]

        # Simulate Redis connection failure and recovery
        env.redis_client.simulate_connection_failure()
        env.wait_for_events(0.2)  # Allow error detection

        # Restore connection
        env.redis_client.restore_connection()
        env.wait_for_events(0.2)  # Allow reconnection

        # Send event after recovery
        env.simulator.publish_pattern_event('GOOGL', 'Doji')
        env.wait_for_events(0.2)

        # Verify recovery - should have 2 messages total
        assert len(client.received_messages) == 2
        recovery_message = client.received_messages[1]
        assert recovery_message['data']['symbol'] == 'GOOGL'

        # Verify subscriber statistics show error and recovery
        stats = env.subscriber.get_stats()
        assert stats['connection_errors'] > 0
        assert stats['events_processed'] == 2

        env.stop_subscriber()

    def test_offline_user_message_persistence_and_delivery(self, integration_test_environment):
        """Test message persistence for offline users and delivery on reconnection."""
        env = integration_test_environment

        # Connect subscriber to broadcaster
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: self._handle_pattern_with_offline_queueing(env, event)
        )

        assert env.start_subscriber() is True

        user_id = 'offline_user'

        # Publish events while user is offline
        offline_events = []
        for symbol, pattern in [('AAPL', 'Doji'), ('GOOGL', 'Hammer'), ('MSFT', 'Engulfing')]:
            event = env.simulator.publish_pattern_event(symbol, pattern)
            offline_events.append(event)

        env.wait_for_events(0.2)

        # Verify messages queued for offline user
        assert user_id in env.broadcaster.offline_message_queue
        assert len(env.broadcaster.offline_message_queue[user_id]) == 3

        # Now simulate user connecting
        client = env.add_mock_user(user_id, 'reconnection_session', ['Doji', 'Hammer', 'Engulfing'])

        # Trigger queued message delivery
        env.broadcaster._deliver_queued_messages(user_id, 'reconnection_session')

        # Verify all queued messages delivered
        assert len(client.received_messages) == 3
        assert user_id not in env.broadcaster.offline_message_queue

        # Verify message order preserved
        delivered_symbols = [msg['data']['symbol'] for msg in client.received_messages]
        assert delivered_symbols == ['AAPL', 'GOOGL', 'MSFT']

        # Send new event after reconnection - should deliver immediately
        env.simulator.publish_pattern_event('TSLA', 'Doji')
        env.wait_for_events(0.1)

        # Should now have 4 messages total
        assert len(client.received_messages) == 4

        env.stop_subscriber()

    def _handle_pattern_with_offline_queueing(self, env, event):
        """Helper to handle pattern events with offline user queueing."""
        pattern_data = event.data
        pattern_name = pattern_data.get('pattern')

        # Check if any users are interested in this pattern
        interested_users = []

        for session_id, connected_user in env.broadcaster.connected_users.items():
            if not connected_user.subscriptions or pattern_name in connected_user.subscriptions:
                interested_users.append(connected_user.user_id)

        # If no online users interested, queue for offline user
        if not interested_users:
            message = {
                'type': 'pattern_alert',
                'pattern': pattern_name,
                'symbol': pattern_data.get('symbol'),
                'event_data': event.to_websocket_dict()
            }
            env.broadcaster.queue_message_for_offline_user('offline_user', message)
        else:
            # Broadcast to online users
            env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())

    def test_high_throughput_event_processing(self, integration_test_environment, performance_timer):
        """Test high-throughput event processing under load."""
        env = integration_test_environment

        # Set up multiple clients
        clients = []
        for i in range(10):
            client = env.add_mock_user(f'load_user_{i}', f'load_session_{i}', ['TestPattern'])
            clients.append(client)

        # Connect subscriber to broadcaster
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )

        assert env.start_subscriber() is True

        # Publish high volume of events
        event_count = 100

        performance_timer.start()

        for i in range(event_count):
            symbol = f'LOAD_TEST_{i:03d}'
            env.simulator.publish_pattern_event(symbol, 'TestPattern', 0.85)

        # Wait for all events to process
        env.wait_for_events(1.0)
        performance_timer.stop()

        # Verify performance under load
        events_per_second = event_count / (performance_timer.elapsed_s)
        assert events_per_second > 50, f"Throughput too low: {events_per_second:.1f} events/sec"

        # Verify all events processed
        stats = env.subscriber.get_stats()
        assert stats['events_received'] == event_count
        assert stats['events_processed'] == event_count
        assert stats['events_dropped'] == 0

        # Verify all clients received all events
        for client in clients:
            assert len(client.received_messages) == event_count

        # Verify message integrity - check first and last messages
        first_client = clients[0]
        first_message = first_client.received_messages[0]
        last_message = first_client.received_messages[-1]

        assert first_message['data']['symbol'] == 'LOAD_TEST_000'
        assert last_message['data']['symbol'] == 'LOAD_TEST_099'

        env.stop_subscriber()

    def test_error_isolation_between_components(self, integration_test_environment):
        """Test that errors in one component don't crash others."""
        env = integration_test_environment

        # Set up client
        client = env.add_mock_user('resilient_user', 'resilient_session', ['Doji'])

        # Add failing event handler alongside working one
        successful_events = []

        def failing_handler(event):
            raise ValueError("Intentional test failure")

        def working_handler(event):
            successful_events.append(event.data['pattern'])

        env.subscriber.add_event_handler(EventType.PATTERN_DETECTED, failing_handler)
        env.subscriber.add_event_handler(EventType.PATTERN_DETECTED, working_handler)

        # Add broadcaster handler
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )

        assert env.start_subscriber() is True

        # Publish events
        for i in range(3):
            env.simulator.publish_pattern_event(f'RESILIENT_{i}', 'Doji')

        env.wait_for_events(0.3)

        # Verify that despite failing handler, working components continue
        assert len(successful_events) == 3  # Working handler succeeded
        assert len(client.received_messages) == 3  # WebSocket delivery succeeded

        # Verify subscriber is still running
        assert env.subscriber.is_running is True

        # Verify statistics show successful processing
        stats = env.subscriber.get_stats()
        assert stats['events_processed'] == 3

        env.stop_subscriber()

    def test_system_health_monitoring_integration(self, integration_test_environment):
        """Test integration of system health monitoring."""
        env = integration_test_environment

        # Set up monitoring client
        monitor_client = env.add_mock_user('monitor', 'monitor_session', [])

        # Connect health events to broadcaster
        env.subscriber.add_event_handler(
            EventType.SYSTEM_HEALTH,
            lambda event: env.broadcaster.broadcast_system_health(event.to_websocket_dict())
        )

        assert env.start_subscriber() is True

        # Publish various health states
        health_states = ['healthy', 'degraded', 'error', 'recovering', 'healthy']

        for state in health_states:
            env.simulator.publish_system_health(state)

        env.wait_for_events(0.3)

        # Verify all health updates received
        assert len(monitor_client.received_messages) == 5

        received_states = []
        for msg in monitor_client.received_messages:
            assert msg['event'] == 'system_health'
            received_states.append(msg['data']['health_data']['status'])

        assert received_states == health_states

        # Check subscriber health status
        subscriber_health = env.subscriber.get_health_status()
        assert subscriber_health['status'] == 'healthy'

        env.stop_subscriber()

    def test_graceful_system_shutdown(self, integration_test_environment):
        """Test graceful shutdown of integrated system."""
        env = integration_test_environment

        # Set up clients and connections
        client = env.add_mock_user('shutdown_user', 'shutdown_session', ['Doji'])

        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )

        assert env.start_subscriber() is True

        # Send events during normal operation
        env.simulator.publish_pattern_event('AAPL', 'Doji')
        env.wait_for_events(0.1)

        # Verify normal operation
        assert len(client.received_messages) == 1

        # Graceful shutdown
        env.stop_subscriber()

        # Verify subscriber stopped
        assert env.subscriber.is_running is False

        # Verify resources cleaned up
        assert env.subscriber.pubsub.closed is True

        # Verify final statistics
        final_stats = env.subscriber.get_stats()
        assert final_stats['events_processed'] == 1
        assert final_stats['is_running'] is False
