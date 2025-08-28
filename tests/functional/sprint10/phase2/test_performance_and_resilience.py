"""
Performance and Resilience Tests
Comprehensive tests for <100ms message delivery and system resilience scenarios.

Sprint 10 Phase 2: Validate performance requirements and system resilience
under various failure conditions, connection issues, and high-load scenarios.
"""

import pytest
import threading
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch
import redis

from .fixtures import (
    MockRedisClient, MockSocketIO, TickStockPLSimulator,
    assert_performance_acceptable, assert_event_delivery_complete
)

# Import components under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from core.services.redis_event_subscriber import RedisEventSubscriber, EventType
from core.services.websocket_broadcaster import WebSocketBroadcaster


class TestPerformanceRequirements:
    """Test performance requirements and benchmarks."""

    def test_single_event_delivery_latency(self, integration_test_environment, performance_timer):
        """Test single event delivery meets <100ms requirement."""
        env = integration_test_environment
        
        # Set up single client
        client = env.add_mock_user('latency_user', 'latency_session', ['Doji'])
        
        # Connect subscriber to broadcaster
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )
        
        assert env.start_subscriber() is True
        
        # Measure multiple single events
        latencies = []
        
        for i in range(10):
            performance_timer.start()
            
            # Publish event
            env.simulator.publish_pattern_event(f'LATENCY_{i}', 'Doji', 0.85)
            
            # Wait for delivery and measure
            initial_count = len(client.received_messages)
            timeout_start = time.time()
            
            while len(client.received_messages) == initial_count:
                if time.time() - timeout_start > 0.2:  # 200ms timeout
                    break
                time.sleep(0.001)  # 1ms polling
            
            performance_timer.stop()
            latencies.append(performance_timer.elapsed_ms)
            
            # Verify message received
            assert len(client.received_messages) > initial_count
        
        # Analyze latency results
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        
        # Verify performance requirements
        assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms exceeds 100ms requirement"
        assert max_latency < 200, f"Max latency {max_latency:.2f}ms exceeds reasonable bounds"
        assert p95_latency < 150, f"95th percentile {p95_latency:.2f}ms exceeds expectations"
        
        # Log performance metrics for analysis
        print(f"\\nLatency Analysis:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Median: {statistics.median(latencies):.2f}ms")
        print(f"  95th Percentile: {p95_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")
        
        env.stop_subscriber()

    def test_burst_event_handling_performance(self, integration_test_environment, performance_timer):
        """Test performance under burst event conditions."""
        env = integration_test_environment
        
        # Set up multiple clients
        clients = []
        for i in range(5):
            client = env.add_mock_user(f'burst_user_{i}', f'burst_session_{i}', ['BurstPattern'])
            clients.append(client)
        
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )
        
        assert env.start_subscriber() is True
        
        # Generate burst of events
        burst_size = 50
        burst_start = time.perf_counter()
        
        performance_timer.start()
        
        for i in range(burst_size):
            env.simulator.publish_pattern_event(f'BURST_{i:03d}', 'BurstPattern', 0.8)
        
        # Wait for all events to be processed
        expected_messages = burst_size * len(clients)
        total_received = 0
        timeout_start = time.time()
        
        while total_received < expected_messages and (time.time() - timeout_start) < 5.0:
            total_received = sum(len(client.received_messages) for client in clients)
            time.sleep(0.01)
        
        performance_timer.stop()
        
        # Verify all events processed
        assert total_received == expected_messages, f"Expected {expected_messages}, got {total_received}"
        
        # Verify burst processing performance
        processing_time = performance_timer.elapsed_s
        events_per_second = burst_size / processing_time
        
        assert events_per_second > 20, f"Burst processing too slow: {events_per_second:.1f} events/sec"
        assert processing_time < 2.5, f"Burst processing took too long: {processing_time:.2f}s"
        
        # Verify event ordering preserved
        first_client = clients[0]
        first_symbols = [msg['data']['symbol'] for msg in first_client.received_messages]
        expected_symbols = [f'BURST_{i:03d}' for i in range(burst_size)]
        assert first_symbols == expected_symbols, "Event ordering not preserved during burst"
        
        env.stop_subscriber()

    def test_concurrent_user_performance(self, integration_test_environment, performance_timer):
        """Test performance with many concurrent users."""
        env = integration_test_environment
        
        # Set up many concurrent users with different subscriptions
        num_users = 50
        patterns = ['Doji', 'Hammer', 'Engulfing', 'Morning Star', 'Evening Star']
        clients = []
        
        for i in range(num_users):
            # Distribute patterns across users
            user_patterns = [patterns[j] for j in range(i % 3 + 1)]  # 1-3 patterns per user
            client = env.add_mock_user(f'concurrent_user_{i}', f'concurrent_session_{i}', user_patterns)
            clients.append(client)
        
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )
        
        assert env.start_subscriber() is True
        
        # Send pattern events
        performance_timer.start()
        
        sent_events = []
        for pattern in patterns:
            for i in range(3):  # 3 events per pattern
                symbol = f'{pattern}_CONCURRENT_{i}'
                event = env.simulator.publish_pattern_event(symbol, pattern, 0.85)
                sent_events.append(event)
        
        # Wait for processing
        time.sleep(0.8)
        performance_timer.stop()
        
        # Verify performance with many users
        assert_performance_acceptable(performance_timer.elapsed_ms, max_ms=800)
        
        # Verify targeted delivery efficiency
        total_messages_sent = sum(len(client.received_messages) for client in clients)
        
        # Each pattern has 3 events, each user subscribed to 1-3 patterns
        # Verify reasonable message distribution
        assert total_messages_sent > 0
        assert total_messages_sent < len(sent_events) * num_users  # Shouldn't be all users get all messages
        
        # Verify no client received wrong patterns
        for i, client in enumerate(clients):
            user_patterns = set([patterns[j] for j in range(i % 3 + 1)])
            for message in client.received_messages:
                received_pattern = message['data']['pattern']
                assert received_pattern in user_patterns, \
                    f"User {i} received {received_pattern} but only subscribed to {user_patterns}"
        
        env.stop_subscriber()

    def test_message_throughput_under_load(self, integration_test_environment, performance_timer):
        """Test message throughput under sustained load."""
        env = integration_test_environment
        
        # Set up moderate number of clients
        num_clients = 10
        clients = []
        for i in range(num_clients):
            client = env.add_mock_user(f'load_user_{i}', f'load_session_{i}', ['LoadTest'])
            clients.append(client)
        
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )
        
        assert env.start_subscriber() is True
        
        # Sustained load test
        load_duration = 3.0  # 3 seconds
        events_per_second = 30
        total_events = int(load_duration * events_per_second)
        
        performance_timer.start()
        
        # Send events at steady rate
        start_time = time.perf_counter()
        for i in range(total_events):
            env.simulator.publish_pattern_event(f'LOAD_{i:03d}', 'LoadTest', 0.8)
            
            # Maintain steady rate
            expected_time = start_time + (i + 1) / events_per_second
            current_time = time.perf_counter()
            if current_time < expected_time:
                time.sleep(expected_time - current_time)
        
        # Wait for final processing
        time.sleep(0.5)
        performance_timer.stop()
        
        # Verify throughput maintained
        actual_duration = performance_timer.elapsed_s - 0.5  # Subtract wait time
        actual_rate = total_events / actual_duration
        
        assert actual_rate >= events_per_second * 0.9, \
            f"Throughput degraded: {actual_rate:.1f} < {events_per_second * 0.9:.1f} events/sec"
        
        # Verify all messages delivered
        expected_total = total_events * num_clients
        actual_total = sum(len(client.received_messages) for client in clients)
        
        assert actual_total == expected_total, \
            f"Message delivery incomplete: {actual_total}/{expected_total}"
        
        # Verify subscriber statistics
        stats = env.subscriber.get_stats()
        assert stats['events_processed'] == total_events
        assert stats['events_dropped'] == 0
        
        env.stop_subscriber()


class TestResilienceScenarios:
    """Test system resilience under various failure conditions."""

    def test_redis_connection_failure_recovery(self, integration_test_environment):
        """Test Redis connection failure and automatic recovery."""
        env = integration_test_environment
        
        # Set up client
        client = env.add_mock_user('resilient_user', 'resilient_session', ['Doji'])
        
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )
        
        assert env.start_subscriber() is True
        
        # Send initial event to verify normal operation
        env.simulator.publish_pattern_event('INITIAL', 'Doji')
        time.sleep(0.1)
        assert len(client.received_messages) == 1
        
        # Simulate Redis connection failure
        env.redis_client.simulate_connection_failure()
        
        # Attempt to send events during failure
        failure_events = 3
        for i in range(failure_events):
            try:
                env.simulator.publish_pattern_event(f'FAILURE_{i}', 'Doji')
            except redis.ConnectionError:
                pass  # Expected during failure
        
        time.sleep(0.3)  # Allow error detection and recovery attempts
        
        # Verify connection error tracked
        error_stats = env.subscriber.get_stats()
        assert error_stats['connection_errors'] > 0
        
        # Restore Redis connection
        env.redis_client.restore_connection()
        time.sleep(0.2)  # Allow reconnection
        
        # Send recovery event
        env.simulator.publish_pattern_event('RECOVERY', 'Doji')
        time.sleep(0.1)
        
        # Verify recovery - should have 2 messages (initial + recovery)
        # Events during failure may be lost, which is acceptable
        assert len(client.received_messages) >= 2
        
        # Verify last message is recovery event
        last_message = client.received_messages[-1]
        assert last_message['data']['symbol'] == 'RECOVERY'
        
        # Verify subscriber still running
        assert env.subscriber.is_running is True
        
        env.stop_subscriber()

    def test_websocket_client_disconnection_recovery(self, integration_test_environment):
        """Test WebSocket client disconnection and reconnection."""
        env = integration_test_environment
        
        user_id = 'disconnect_user'
        session_id = 'disconnect_session'
        
        # Set up initial connection
        client = env.add_mock_user(user_id, session_id, ['Doji'])
        
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )
        
        assert env.start_subscriber() is True
        
        # Send initial event
        env.simulator.publish_pattern_event('BEFORE_DISCONNECT', 'Doji')
        time.sleep(0.1)
        assert len(client.received_messages) == 1
        
        # Simulate client disconnection
        env.socketio.remove_client(session_id)
        if session_id in env.broadcaster.connected_users:
            del env.broadcaster.connected_users[session_id]
        if user_id in env.broadcaster.user_sessions:
            env.broadcaster.user_sessions[user_id].discard(session_id)
        
        # Send events while disconnected (should be queued)
        disconnect_events = []
        for i in range(3):
            event = env.simulator.publish_pattern_event(f'DISCONNECTED_{i}', 'Doji')
            disconnect_events.append(event)
            # Manually queue since no handler will catch it
            message = {
                'type': 'pattern_alert',
                'pattern': 'Doji',
                'symbol': f'DISCONNECTED_{i}',
                'timestamp': time.time()
            }
            env.broadcaster.queue_message_for_offline_user(user_id, message)
        
        time.sleep(0.2)
        
        # Verify messages queued
        assert user_id in env.broadcaster.offline_message_queue
        assert len(env.broadcaster.offline_message_queue[user_id]) == 3
        
        # Simulate reconnection
        new_session_id = 'reconnect_session'
        new_client = env.add_mock_user(user_id, new_session_id, ['Doji'])
        
        # Deliver queued messages
        env.broadcaster._deliver_queued_messages(user_id, new_session_id)
        
        # Verify queued messages delivered
        assert len(new_client.received_messages) == 3
        assert user_id not in env.broadcaster.offline_message_queue
        
        # Send new event after reconnection
        env.simulator.publish_pattern_event('AFTER_RECONNECT', 'Doji')
        time.sleep(0.1)
        
        # Should have 4 messages total (3 queued + 1 new)
        assert len(new_client.received_messages) == 4
        
        env.stop_subscriber()

    def test_high_error_rate_resilience(self, integration_test_environment):
        """Test system resilience under high error rates."""
        env = integration_test_environment
        
        # Set up client
        client = env.add_mock_user('error_resilient', 'error_session', ['TestPattern'])
        
        # Add multiple handlers - some that fail
        successful_events = []
        
        def failing_handler_1(event):
            if 'FAIL_1' in event.data.get('symbol', ''):
                raise ValueError("Handler 1 failure")
            
        def failing_handler_2(event):
            if 'FAIL_2' in event.data.get('symbol', ''):
                raise ConnectionError("Handler 2 failure")
            
        def working_handler(event):
            successful_events.append(event.data['symbol'])
            
        # Add broadcaster handler
        def broadcaster_handler(event):
            env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        
        env.subscriber.add_event_handler(EventType.PATTERN_DETECTED, failing_handler_1)
        env.subscriber.add_event_handler(EventType.PATTERN_DETECTED, failing_handler_2)
        env.subscriber.add_event_handler(EventType.PATTERN_DETECTED, working_handler)
        env.subscriber.add_event_handler(EventType.PATTERN_DETECTED, broadcaster_handler)
        
        assert env.start_subscriber() is True
        
        # Send mix of events - some cause handler failures
        test_events = [
            'NORMAL_EVENT_1',
            'FAIL_1_EVENT',    # Causes handler 1 to fail
            'NORMAL_EVENT_2', 
            'FAIL_2_EVENT',    # Causes handler 2 to fail
            'FAIL_1_EVENT_2',  # Another handler 1 failure
            'NORMAL_EVENT_3'
        ]
        
        for symbol in test_events:
            env.simulator.publish_pattern_event(symbol, 'TestPattern')
        
        time.sleep(0.3)
        
        # Verify system continued despite failures
        assert len(successful_events) == 6  # Working handler should process all
        assert len(client.received_messages) == 6  # All should be broadcast
        
        # Verify subscriber still running
        assert env.subscriber.is_running is True
        
        # Verify events processed correctly
        stats = env.subscriber.get_stats()
        assert stats['events_processed'] == 6
        
        env.stop_subscriber()

    def test_memory_pressure_handling(self, integration_test_environment):
        """Test handling of memory pressure conditions."""
        env = integration_test_environment
        
        # Set up offline user to build up message queue
        offline_user = 'memory_pressure_user'
        
        # Reduce queue limit for testing
        original_limit = env.broadcaster.max_offline_messages
        env.broadcaster.max_offline_messages = 10
        
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.queue_message_for_offline_user(
                offline_user, 
                {'type': 'pattern_alert', 'data': event.data}
            )
        )
        
        assert env.start_subscriber() is True
        
        # Send many events to build up queue
        for i in range(25):  # More than queue limit
            env.simulator.publish_pattern_event(f'MEMORY_{i:03d}', 'MemoryTest')
        
        time.sleep(0.3)
        
        # Verify queue limited properly
        assert len(env.broadcaster.offline_message_queue[offline_user]) == 10
        
        # Verify oldest messages were dropped (should have last 10)
        queued_messages = env.broadcaster.offline_message_queue[offline_user]
        symbols = [msg['data']['symbol'] for msg in queued_messages]
        expected_symbols = [f'MEMORY_{i:03d}' for i in range(15, 25)]  # Last 10
        assert symbols == expected_symbols
        
        # Restore original limit
        env.broadcaster.max_offline_messages = original_limit
        
        env.stop_subscriber()

    def test_concurrent_failure_scenarios(self, integration_test_environment):
        """Test handling of multiple concurrent failures."""
        env = integration_test_environment
        
        # Set up multiple clients
        clients = []
        for i in range(3):
            client = env.add_mock_user(f'concurrent_user_{i}', f'concurrent_session_{i}', ['Doji'])
            clients.append(client)
        
        # Add handler that sometimes fails based on symbol
        processed_events = []
        
        def sometimes_failing_handler(event):
            symbol = event.data.get('symbol', '')
            if 'CONCURRENT_FAIL' in symbol:
                raise RuntimeError("Concurrent failure simulation")
            processed_events.append(symbol)
        
        env.subscriber.add_event_handler(EventType.PATTERN_DETECTED, sometimes_failing_handler)
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )
        
        assert env.start_subscriber() is True
        
        # Simulate concurrent failures
        def failure_scenario():
            # Redis connection intermittent
            env.redis_client.simulate_connection_failure()
            time.sleep(0.1)
            env.redis_client.restore_connection()
            
        def client_disconnect_scenario():
            # Simulate client disconnect/reconnect
            if len(clients) > 0:
                session_id = clients[0].session_id
                env.socketio.remove_client(session_id)
                time.sleep(0.1)
                # Reconnect
                new_client = env.add_mock_user('concurrent_user_0', 'new_concurrent_session_0', ['Doji'])
                clients[0] = new_client
        
        # Start concurrent scenarios
        failure_thread = threading.Thread(target=failure_scenario)
        disconnect_thread = threading.Thread(target=client_disconnect_scenario)
        
        failure_thread.start()
        disconnect_thread.start()
        
        # Send events during concurrent failures
        test_events = [
            'NORMAL_1',
            'CONCURRENT_FAIL_1',  # Handler failure
            'NORMAL_2',
            'CONCURRENT_FAIL_2',  # Another handler failure
            'NORMAL_3'
        ]
        
        for symbol in test_events:
            env.simulator.publish_pattern_event(symbol, 'Doji')
            time.sleep(0.05)  # Small delay between events
        
        # Wait for threads to complete
        failure_thread.join()
        disconnect_thread.join()
        
        time.sleep(0.3)  # Allow processing to complete
        
        # Verify system remained stable
        assert env.subscriber.is_running is True
        
        # Verify some events processed (may not be all due to failures)
        stats = env.subscriber.get_stats()
        assert stats['events_processed'] >= 3  # At least the non-failing events
        assert stats['connection_errors'] > 0   # Should have detected connection issues
        
        # Verify at least some messages delivered
        total_received = sum(len(client.received_messages) for client in clients)
        assert total_received > 0
        
        env.stop_subscriber()

    def test_graceful_degradation_under_load(self, integration_test_environment):
        """Test graceful degradation when system is overloaded."""
        env = integration_test_environment
        
        # Set up many clients
        num_clients = 20
        clients = []
        for i in range(num_clients):
            client = env.add_mock_user(f'load_user_{i}', f'load_session_{i}', ['LoadTest'])
            clients.append(client)
        
        env.subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: env.broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )
        
        assert env.start_subscriber() is True
        
        # Send high volume of events rapidly
        rapid_events = 200
        start_time = time.perf_counter()
        
        for i in range(rapid_events):
            env.simulator.publish_pattern_event(f'RAPID_{i:03d}', 'LoadTest', 0.8)
        
        # Allow processing time
        time.sleep(2.0)
        
        # Verify system handled load gracefully
        stats = env.subscriber.get_stats()
        
        # Should process most events (allow some loss under extreme load)
        processed_ratio = stats['events_processed'] / rapid_events
        assert processed_ratio > 0.8, f"Too many events dropped: {processed_ratio:.2%} processed"
        
        # Verify system still responsive
        assert env.subscriber.is_running is True
        
        # Test responsiveness with new event
        env.simulator.publish_pattern_event('RESPONSIVE_TEST', 'LoadTest')
        time.sleep(0.2)
        
        # Should still be able to process new events
        final_stats = env.subscriber.get_stats()
        assert final_stats['events_processed'] > stats['events_processed']
        
        env.stop_subscriber()