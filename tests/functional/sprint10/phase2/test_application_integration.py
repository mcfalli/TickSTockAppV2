"""
Application Integration Tests
Integration tests for service initialization and startup sequence in Flask application.

Sprint 10 Phase 2: Validate complete application startup, service integration,
graceful shutdown, and proper error handling during initialization.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock, create_autospec
from flask import Flask
from flask_socketio import SocketIO

from .fixtures import MockRedisClient, MockSocketIO

# Import components under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from core.services.redis_event_subscriber import RedisEventSubscriber
from core.services.websocket_broadcaster import WebSocketBroadcaster


class TestApplicationStartupIntegration:
    """Test complete application startup and service integration."""

    def test_successful_service_initialization_sequence(self, mock_redis_client, test_config):
        """Test successful initialization of all services."""
        
        # Mock Flask and SocketIO
        mock_app = Mock(spec=Flask)
        mock_socketio = MockSocketIO()
        
        # Initialize services in order
        services = {}
        
        # 1. Initialize WebSocket broadcaster
        services['broadcaster'] = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        assert services['broadcaster'] is not None
        
        # 2. Initialize Redis event subscriber
        services['subscriber'] = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        assert services['subscriber'] is not None
        
        # 3. Connect services together
        from core.services.redis_event_subscriber import EventType
        
        # Register broadcaster handlers with subscriber
        services['subscriber'].add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: services['broadcaster'].broadcast_pattern_alert(event.to_websocket_dict())
        )
        services['subscriber'].add_event_handler(
            EventType.BACKTEST_PROGRESS,
            lambda event: services['broadcaster'].broadcast_backtest_progress(event.to_websocket_dict())
        )
        services['subscriber'].add_event_handler(
            EventType.BACKTEST_RESULT,
            lambda event: services['broadcaster'].broadcast_backtest_result(event.to_websocket_dict())
        )
        services['subscriber'].add_event_handler(
            EventType.SYSTEM_HEALTH,
            lambda event: services['broadcaster'].broadcast_system_health(event.to_websocket_dict())
        )
        
        # 4. Start services
        subscriber_started = services['subscriber'].start()
        assert subscriber_started is True
        
        # Verify services are operational
        assert services['subscriber'].is_running is True
        assert services['subscriber'].subscriber_thread is not None
        assert services['subscriber'].subscriber_thread.is_alive()
        
        # Verify event handlers registered
        for event_type in EventType:
            assert len(services['subscriber'].event_handlers[event_type]) > 0
        
        # Verify broadcaster ready
        broadcaster_stats = services['broadcaster'].get_stats()
        assert broadcaster_stats['active_connections'] == 0  # No clients yet
        
        # Cleanup
        services['subscriber'].stop()

    def test_redis_unavailable_during_startup(self, test_config):
        """Test graceful handling when Redis is unavailable during startup."""
        
        # Create Redis client that fails connection
        failed_redis = MockRedisClient()
        failed_redis.simulate_connection_failure()
        
        mock_socketio = MockSocketIO()
        
        # Initialize broadcaster (should succeed even with Redis down)
        broadcaster = WebSocketBroadcaster(mock_socketio, failed_redis)
        assert broadcaster is not None
        
        # Initialize subscriber (should fail gracefully)
        subscriber = RedisEventSubscriber(failed_redis, mock_socketio, test_config)
        assert subscriber is not None
        
        # Attempt to start subscriber
        start_success = subscriber.start()
        assert start_success is False  # Should fail gracefully
        assert subscriber.is_running is False
        
        # Verify error handling didn't crash
        health_status = subscriber.get_health_status()
        assert health_status['status'] == 'error'
        assert 'not running' in health_status['message'].lower()

    def test_partial_service_initialization(self, mock_redis_client, test_config):
        """Test handling when some services fail to initialize."""
        
        mock_socketio = MockSocketIO()
        
        # Initialize broadcaster successfully
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        
        # Create subscriber that will fail after partial initialization
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        
        # Start subscriber
        assert subscriber.start() is True
        
        # Simulate failure after startup
        mock_redis_client.simulate_connection_failure()
        
        time.sleep(0.2)  # Allow error detection
        
        # Verify subscriber detects failure but doesn't crash
        assert subscriber.is_running is True  # Still running, attempting recovery
        
        stats = subscriber.get_stats()
        assert stats['connection_errors'] > 0
        
        # Verify broadcaster still functional
        broadcaster_stats = broadcaster.get_stats()
        assert broadcaster_stats is not None
        
        # Cleanup
        subscriber.stop()

    def test_service_dependency_validation(self, mock_redis_client, test_config):
        """Test validation of service dependencies."""
        
        mock_socketio = MockSocketIO()
        
        # Test subscriber requires valid Redis client
        with pytest.raises(AttributeError):
            RedisEventSubscriber(None, mock_socketio, test_config)
        
        # Test subscriber requires valid SocketIO
        with pytest.raises(AttributeError):
            RedisEventSubscriber(mock_redis_client, None, test_config)
        
        # Test broadcaster requires valid SocketIO
        with pytest.raises(AttributeError):
            WebSocketBroadcaster(None, mock_redis_client)
        
        # Test valid initialization
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        
        assert subscriber is not None
        assert broadcaster is not None

    def test_configuration_validation(self, mock_redis_client, mock_socketio):
        """Test configuration validation during service initialization."""
        
        # Test with missing configuration
        empty_config = {}
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, empty_config)
        
        # Should initialize with defaults
        assert subscriber is not None
        assert len(subscriber.channels) == 4
        
        # Test with partial configuration
        partial_config = {
            'REDIS_HOST': 'test_host',
            'REDIS_PORT': 6380
        }
        subscriber2 = RedisEventSubscriber(mock_redis_client, mock_socketio, partial_config)
        assert subscriber2 is not None
        
        # Test with complete configuration
        full_config = {
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': 6379,
            'REDIS_DB': 15,
            'REDIS_URL': 'redis://localhost:6379/15',
            'TESTING': True,
            'LOG_LEVEL': 'DEBUG'
        }
        subscriber3 = RedisEventSubscriber(mock_redis_client, mock_socketio, full_config)
        assert subscriber3 is not None

    def test_service_health_monitoring_integration(self, mock_redis_client, mock_socketio, test_config):
        """Test integrated health monitoring across services."""
        
        # Initialize services
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        
        # Test initial health states
        initial_health = subscriber.get_health_status()
        assert initial_health['status'] == 'error'  # Not started yet
        
        initial_stats = broadcaster.get_stats()
        assert initial_stats['active_connections'] == 0
        
        # Start services
        assert subscriber.start() is True
        
        # Test healthy state
        healthy_state = subscriber.get_health_status()
        assert healthy_state['status'] == 'healthy'
        assert 'operating normally' in healthy_state['message']
        
        # Simulate degraded state
        for _ in range(6):  # Trigger degraded state
            subscriber.stats['connection_errors'] += 1
        
        degraded_health = subscriber.get_health_status()
        assert degraded_health['status'] == 'degraded'
        
        # Test integrated health check
        def get_system_health():
            return {
                'subscriber': subscriber.get_health_status(),
                'broadcaster': {
                    'active_connections': broadcaster.get_stats()['active_connections'],
                    'status': 'healthy' if len(broadcaster.connected_users) >= 0 else 'error'
                }
            }
        
        system_health = get_system_health()
        assert 'subscriber' in system_health
        assert 'broadcaster' in system_health
        
        subscriber.stop()

    def test_graceful_service_shutdown_sequence(self, mock_redis_client, mock_socketio, test_config):
        """Test graceful shutdown of all services."""
        
        # Initialize and start services
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        
        assert subscriber.start() is True
        
        # Verify services running
        assert subscriber.is_running is True
        assert subscriber.subscriber_thread.is_alive()
        
        # Add some mock clients to broadcaster
        from core.services.websocket_broadcaster import ConnectedUser
        
        for i in range(3):
            user = ConnectedUser(
                user_id=f'shutdown_user_{i}',
                session_id=f'shutdown_session_{i}',
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions=set()
            )
            broadcaster.connected_users[f'shutdown_session_{i}'] = user
        
        # Verify initial state
        assert len(broadcaster.connected_users) == 3
        
        # Graceful shutdown sequence
        shutdown_start = time.time()
        
        # 1. Stop Redis subscriber
        subscriber.stop()
        
        # Verify subscriber stopped
        assert subscriber.is_running is False
        
        # 2. Cleanup connections (in real app, this would be done by Flask-SocketIO)
        for session_id in list(broadcaster.connected_users.keys()):
            # Simulate disconnect cleanup
            if session_id in broadcaster.connected_users:
                user = broadcaster.connected_users[session_id]
                del broadcaster.connected_users[session_id]
                
                if user.user_id in broadcaster.user_sessions:
                    broadcaster.user_sessions[user.user_id].discard(session_id)
                    if not broadcaster.user_sessions[user.user_id]:
                        del broadcaster.user_sessions[user.user_id]
        
        # Verify cleanup
        assert len(broadcaster.connected_users) == 0
        assert len(broadcaster.user_sessions) == 0
        
        shutdown_time = time.time() - shutdown_start
        assert shutdown_time < 2.0  # Should shutdown quickly

    def test_service_restart_capability(self, mock_redis_client, mock_socketio, test_config):
        """Test ability to restart services without full application restart."""
        
        # Initialize services
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        
        # First startup
        assert subscriber.start() is True
        initial_stats = subscriber.get_stats()
        
        # Stop service
        subscriber.stop()
        assert subscriber.is_running is False
        
        # Restart service
        time.sleep(0.1)  # Brief pause
        assert subscriber.start() is True
        
        # Verify restart successful
        assert subscriber.is_running is True
        restart_stats = subscriber.get_stats()
        
        # Stats should be reset
        assert restart_stats['start_time'] > initial_stats['start_time']
        
        # Verify functionality after restart
        received_events = []
        subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: received_events.append(event)
        )
        
        # Simulate event
        mock_redis_client.publish(
            'tickstock.events.patterns',
            '{"event_type": "pattern_detected", "source": "tickstock_pl", "timestamp": ' + 
            str(time.time()) + ', "pattern": "Doji", "symbol": "RESTART_TEST"}'
        )
        
        time.sleep(0.1)
        
        # Verify event processed after restart
        assert len(received_events) == 1
        assert received_events[0].data['symbol'] == 'RESTART_TEST'
        
        subscriber.stop()

    def test_concurrent_service_operations(self, mock_redis_client, mock_socketio, test_config):
        """Test concurrent operations across services."""
        
        # Initialize services
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        
        # Connect services
        subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )
        
        assert subscriber.start() is True
        
        # Add multiple clients concurrently
        def add_clients():
            for i in range(5):
                session_id = f'concurrent_session_{i}'
                user = ConnectedUser(
                    user_id=f'concurrent_user_{i}',
                    session_id=session_id,
                    connected_at=time.time(),
                    last_seen=time.time(),
                    subscriptions={'ConcurrentTest'}
                )
                broadcaster.connected_users[session_id] = user
                time.sleep(0.01)  # Small delay between additions
        
        # Send events concurrently
        def send_events():
            for i in range(10):
                event_data = {
                    'event_type': 'pattern_detected',
                    'source': 'tickstock_pl',
                    'timestamp': time.time(),
                    'pattern': 'ConcurrentTest',
                    'symbol': f'CONCURRENT_{i}'
                }
                mock_redis_client.publish('tickstock.events.patterns', str(event_data).replace("'", '"'))
                time.sleep(0.02)
        
        # Start concurrent operations
        client_thread = threading.Thread(target=add_clients)
        event_thread = threading.Thread(target=send_events)
        
        client_thread.start()
        event_thread.start()
        
        # Wait for completion
        client_thread.join()
        event_thread.join()
        
        time.sleep(0.3)  # Allow processing
        
        # Verify system handled concurrent operations
        assert len(broadcaster.connected_users) == 5
        
        stats = subscriber.get_stats()
        assert stats['events_processed'] > 0  # Some events should be processed
        assert subscriber.is_running is True
        
        subscriber.stop()

    def test_error_propagation_and_isolation(self, mock_redis_client, mock_socketio, test_config):
        """Test error propagation and isolation between services."""
        
        # Initialize services
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        
        # Add error-prone handler
        error_count = 0
        
        def error_prone_handler(event):
            nonlocal error_count
            error_count += 1
            if error_count % 2 == 1:  # Fail every other call
                raise RuntimeError("Simulated handler error")
        
        # Add both error-prone and broadcaster handlers
        subscriber.add_event_handler(EventType.PATTERN_DETECTED, error_prone_handler)
        subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )
        
        assert subscriber.start() is True
        
        # Add client to broadcaster
        session_id = 'error_isolation_session'
        user = ConnectedUser(
            user_id='error_test_user',
            session_id=session_id,
            connected_at=time.time(),
            last_seen=time.time(),
            subscriptions={'ErrorTest'}
        )
        broadcaster.connected_users[session_id] = user
        mock_socketio.add_client(session_id, Mock())
        
        # Send events that will trigger errors
        for i in range(4):
            event_data = {
                'event_type': 'pattern_detected',
                'source': 'tickstock_pl',
                'timestamp': time.time(),
                'pattern': 'ErrorTest',
                'symbol': f'ERROR_TEST_{i}'
            }
            mock_redis_client.publish('tickstock.events.patterns', str(event_data).replace("'", '"'))
        
        time.sleep(0.3)
        
        # Verify error isolation
        # - Subscriber should still be running despite handler errors
        assert subscriber.is_running is True
        
        # - Events should still be processed by non-failing handlers
        assert len(mock_socketio.broadcast_messages) > 0 or len(mock_socketio.room_messages) > 0
        
        # - Statistics should show processing occurred
        stats = subscriber.get_stats()
        assert stats['events_processed'] == 4  # All events processed despite errors
        
        subscriber.stop()


class TestServiceIntegrationPatterns:
    """Test specific integration patterns and best practices."""

    def test_loose_coupling_validation(self, mock_redis_client, mock_socketio, test_config):
        """Validate loose coupling between services."""
        
        # Initialize services independently
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        
        # Verify services can operate independently
        assert broadcaster is not None
        assert subscriber is not None
        
        # Verify no direct references between services
        assert not hasattr(subscriber, 'broadcaster')
        assert not hasattr(broadcaster, 'subscriber')
        
        # Verify communication only through event handlers (loose coupling)
        assert len(subscriber.event_handlers[EventType.PATTERN_DETECTED]) == 0  # No handlers initially
        
        # Add handler (this creates coupling but through interface, not direct reference)
        subscriber.add_event_handler(
            EventType.PATTERN_DETECTED,
            lambda event: broadcaster.broadcast_pattern_alert(event.to_websocket_dict())
        )
        
        # Verify coupling is through interface only
        assert len(subscriber.event_handlers[EventType.PATTERN_DETECTED]) == 1

    def test_event_driven_architecture_validation(self, mock_redis_client, mock_socketio, test_config):
        """Validate event-driven architecture principles."""
        
        # Initialize services
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        
        # Track event flow
        event_flow = []
        
        # Add tracking handlers for each event type
        for event_type in EventType:
            subscriber.add_event_handler(
                event_type,
                lambda event, et=event_type: event_flow.append(f"processed_{et.value}")
            )
        
        assert subscriber.start() is True
        
        # Send different event types
        events_to_send = [
            ('tickstock.events.patterns', 'pattern_detected'),
            ('tickstock.events.backtesting.progress', 'backtest_progress'),
            ('tickstock.events.backtesting.results', 'backtest_result'),
            ('tickstock.health.status', 'system_health')
        ]
        
        for channel, event_type in events_to_send:
            event_data = {
                'event_type': event_type,
                'source': 'tickstock_pl',
                'timestamp': time.time()
            }
            mock_redis_client.publish(channel, str(event_data).replace("'", '"'))
        
        time.sleep(0.2)
        
        # Verify event-driven flow
        assert len(event_flow) == 4
        expected_events = [f"processed_{event_type}" for _, event_type in events_to_send]
        assert set(event_flow) == set(expected_events)
        
        subscriber.stop()

    def test_scalability_patterns(self, mock_redis_client, mock_socketio, test_config):
        """Test scalability patterns in service integration."""
        
        # Initialize services
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        
        # Test multiple event handlers (fan-out pattern)
        handler_calls = {'handler1': 0, 'handler2': 0, 'handler3': 0}
        
        def create_handler(name):
            def handler(event):
                handler_calls[name] += 1
            return handler
        
        # Add multiple handlers for same event type
        for handler_name in handler_calls.keys():
            subscriber.add_event_handler(
                EventType.PATTERN_DETECTED,
                create_handler(handler_name)
            )
        
        assert subscriber.start() is True
        
        # Send events
        for i in range(5):
            event_data = {
                'event_type': 'pattern_detected',
                'source': 'tickstock_pl',
                'timestamp': time.time(),
                'pattern': 'ScalabilityTest',
                'symbol': f'SCALE_{i}'
            }
            mock_redis_client.publish('tickstock.events.patterns', str(event_data).replace("'", '"'))
        
        time.sleep(0.2)
        
        # Verify fan-out pattern worked
        for handler_name, call_count in handler_calls.items():
            assert call_count == 5, f"Handler {handler_name} called {call_count} times, expected 5"
        
        subscriber.stop()

    def test_resource_management_patterns(self, mock_redis_client, mock_socketio, test_config):
        """Test proper resource management in service integration."""
        
        # Track resource allocation
        resources = {'threads': 0, 'connections': 0}
        
        # Initialize services
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
        subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
        
        # Track initial resources
        initial_thread_count = threading.active_count()
        
        # Start services (should create threads)
        assert subscriber.start() is True
        
        # Verify resource allocation
        assert threading.active_count() > initial_thread_count
        assert subscriber.subscriber_thread is not None
        assert subscriber.subscriber_thread.is_alive()
        
        # Add connections to test connection management
        for i in range(10):
            session_id = f'resource_session_{i}'
            user = ConnectedUser(
                user_id=f'resource_user_{i}',
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions=set()
            )
            broadcaster.connected_users[session_id] = user
        
        # Verify resource tracking
        assert len(broadcaster.connected_users) == 10
        
        # Test resource cleanup
        subscriber.stop()
        
        # Verify resource deallocation
        time.sleep(0.1)  # Allow cleanup
        assert subscriber.is_running is False
        assert not subscriber.subscriber_thread.is_alive()
        
        # Verify connection cleanup (manual for test)
        broadcaster.connected_users.clear()
        broadcaster.user_sessions.clear()
        
        assert len(broadcaster.connected_users) == 0
        assert len(broadcaster.user_sessions) == 0