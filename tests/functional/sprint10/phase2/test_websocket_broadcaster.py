"""
WebSocketBroadcaster Integration Tests
Comprehensive integration tests for WebSocket broadcasting and user connection management.

Sprint 10 Phase 2: Validate real-time event broadcasting, user subscription management,
connection handling, and message queuing functionality.
"""

import os

# Import components under test
import sys
import time
from unittest.mock import Mock, patch

from .fixtures import ConnectedUser, MockSocketIOClient, assert_performance_acceptable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from core.services.websocket_broadcaster import WebSocketBroadcaster


class TestWebSocketBroadcasterIntegration:
    """Integration tests for WebSocketBroadcaster service."""

    def test_broadcaster_initialization(self, mock_socketio, mock_redis_client):
        """Test WebSocket broadcaster initialization."""
        broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)

        # Verify initialization state
        assert broadcaster.socketio == mock_socketio
        assert broadcaster.redis_client == mock_redis_client
        assert len(broadcaster.connected_users) == 0
        assert len(broadcaster.user_sessions) == 0
        assert len(broadcaster.offline_message_queue) == 0

        # Verify initial statistics
        stats = broadcaster.get_stats()
        assert stats['total_connections'] == 0
        assert stats['active_connections'] == 0
        assert stats['messages_sent'] == 0
        assert stats['messages_queued'] == 0

        # Verify SocketIO handlers registered
        expected_handlers = ['connect', 'disconnect', 'subscribe_patterns', 'heartbeat']
        for handler in expected_handlers:
            assert handler in mock_socketio.event_handlers

    def test_user_connection_flow(self, websocket_broadcaster):
        """Test user connection and tracking."""
        # Simulate user connection
        mock_user = Mock()
        mock_user.id = 'test_user_123'

        with patch('flask_login.current_user', mock_user):
            websocket_broadcaster.socketio.server.current_sid = 'session_abc'

            # Trigger connect event
            connect_handler = websocket_broadcaster.socketio.event_handlers['connect']
            connect_handler()

        # Verify user tracked
        assert len(websocket_broadcaster.connected_users) == 1
        assert 'session_abc' in websocket_broadcaster.connected_users

        connected_user = websocket_broadcaster.connected_users['session_abc']
        assert connected_user.user_id == 'test_user_123'
        assert connected_user.session_id == 'session_abc'
        assert len(connected_user.subscriptions) == 0

        # Verify user sessions tracked
        assert 'test_user_123' in websocket_broadcaster.user_sessions
        assert 'session_abc' in websocket_broadcaster.user_sessions['test_user_123']

        # Verify statistics updated
        stats = websocket_broadcaster.get_stats()
        assert stats['total_connections'] == 1
        assert stats['active_connections'] == 1

    def test_anonymous_user_connection(self, websocket_broadcaster):
        """Test anonymous user connection handling."""
        # Simulate anonymous connection (no current_user)
        with patch('flask_login.current_user', None):
            websocket_broadcaster.socketio.server.current_sid = 'anon_session'

            connect_handler = websocket_broadcaster.socketio.event_handlers['connect']
            connect_handler()

        # Verify anonymous user tracked
        assert 'anon_session' in websocket_broadcaster.connected_users
        connected_user = websocket_broadcaster.connected_users['anon_session']
        assert connected_user.user_id == 'anonymous'

    def test_user_disconnection_flow(self, websocket_broadcaster):
        """Test user disconnection and cleanup."""
        # Set up connected user
        user_id = 'test_user_456'
        session_id = 'session_def'

        connected_user = ConnectedUser(
            user_id=user_id,
            session_id=session_id,
            connected_at=time.time(),
            last_seen=time.time(),
            subscriptions={'Doji', 'Hammer'}
        )

        websocket_broadcaster.connected_users[session_id] = connected_user
        websocket_broadcaster.user_sessions[user_id] = {session_id}
        websocket_broadcaster.stats['active_connections'] = 1

        # Simulate disconnection
        websocket_broadcaster.socketio.server.current_sid = session_id
        disconnect_handler = websocket_broadcaster.socketio.event_handlers['disconnect']
        disconnect_handler()

        # Verify cleanup
        assert session_id not in websocket_broadcaster.connected_users
        assert user_id not in websocket_broadcaster.user_sessions
        assert websocket_broadcaster.stats['active_connections'] == 0
        assert websocket_broadcaster.stats['disconnections'] == 1

    def test_pattern_subscription_management(self, websocket_broadcaster):
        """Test user pattern subscription handling."""
        # Set up connected user
        session_id = 'session_ghi'
        user_id = 'test_user_789'

        connected_user = ConnectedUser(
            user_id=user_id,
            session_id=session_id,
            connected_at=time.time(),
            last_seen=time.time(),
            subscriptions=set()
        )

        websocket_broadcaster.connected_users[session_id] = connected_user
        websocket_broadcaster.socketio.server.current_sid = session_id

        # Test pattern subscription
        subscription_data = {
            'patterns': ['Doji', 'Hammer', 'Engulfing']
        }

        subscribe_handler = websocket_broadcaster.socketio.event_handlers['subscribe_patterns']
        subscribe_handler(subscription_data)

        # Verify subscriptions updated
        updated_user = websocket_broadcaster.connected_users[session_id]
        assert updated_user.subscriptions == {'Doji', 'Hammer', 'Engulfing'}

        # Verify last seen updated
        assert updated_user.last_seen > connected_user.last_seen

    def test_invalid_subscription_data(self, websocket_broadcaster):
        """Test handling of invalid subscription data."""
        session_id = 'session_jkl'
        websocket_broadcaster.connected_users[session_id] = ConnectedUser(
            user_id='test_user',
            session_id=session_id,
            connected_at=time.time(),
            last_seen=time.time(),
            subscriptions=set()
        )
        websocket_broadcaster.socketio.server.current_sid = session_id

        # Test invalid patterns format
        invalid_data = {'patterns': 'not_a_list'}

        subscribe_handler = websocket_broadcaster.socketio.event_handlers['subscribe_patterns']
        subscribe_handler(invalid_data)

        # Verify error emitted and subscriptions unchanged
        # In real implementation, this would emit an error
        assert len(websocket_broadcaster.connected_users[session_id].subscriptions) == 0

    def test_heartbeat_handling(self, websocket_broadcaster):
        """Test client heartbeat processing."""
        session_id = 'session_mno'
        initial_time = time.time() - 100

        connected_user = ConnectedUser(
            user_id='test_user',
            session_id=session_id,
            connected_at=initial_time,
            last_seen=initial_time,
            subscriptions=set()
        )

        websocket_broadcaster.connected_users[session_id] = connected_user
        websocket_broadcaster.socketio.server.current_sid = session_id

        # Process heartbeat
        heartbeat_handler = websocket_broadcaster.socketio.event_handlers['heartbeat']
        heartbeat_handler()

        # Verify last seen updated
        updated_user = websocket_broadcaster.connected_users[session_id]
        assert updated_user.last_seen > initial_time

    def test_pattern_alert_broadcasting(self, websocket_broadcaster, performance_timer):
        """Test pattern alert broadcasting with user filtering."""
        # Set up multiple users with different subscriptions
        users_config = [
            ('user1', 'session1', {'Doji', 'Hammer'}),
            ('user2', 'session2', {'Engulfing'}),
            ('user3', 'session3', {'Doji'}),  # Should receive
            ('user4', 'session4', set()),     # All patterns (empty = all)
        ]

        # Add clients and users
        for user_id, session_id, subscriptions in users_config:
            client = MockSocketIOClient(user_id, session_id)
            websocket_broadcaster.socketio.add_client(session_id, client)

            connected_user = ConnectedUser(
                user_id=user_id,
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions=subscriptions
            )
            websocket_broadcaster.connected_users[session_id] = connected_user

        # Broadcast pattern alert
        pattern_event = {
            'event_type': 'pattern_detected',
            'source': 'tickstock_pl',
            'timestamp': time.time(),
            'data': {
                'pattern': 'Doji',
                'symbol': 'AAPL',
                'confidence': 0.85
            }
        }

        performance_timer.start()
        websocket_broadcaster.broadcast_pattern_alert(pattern_event)
        performance_timer.stop()

        # Verify performance
        assert_performance_acceptable(performance_timer.elapsed_ms, max_ms=100)

        # Verify targeted delivery
        # Users 1, 3, and 4 should receive (subscribed to Doji or all patterns)
        # User 2 should not receive (only subscribed to Engulfing)

        user1_client = websocket_broadcaster.socketio.clients['session1']
        user3_client = websocket_broadcaster.socketio.clients['session3']
        user4_client = websocket_broadcaster.socketio.clients['session4']

        assert len(user1_client.received_messages) == 1
        assert len(user3_client.received_messages) == 1
        assert len(user4_client.received_messages) == 1

        # Verify message content
        message = user1_client.received_messages[0]
        assert message['event'] == 'pattern_alert'
        assert message['data']['pattern'] == 'Doji'
        assert message['data']['symbol'] == 'AAPL'

    def test_backtest_progress_broadcasting(self, websocket_broadcaster):
        """Test backtest progress broadcasting to all users."""
        # Set up multiple connected users
        for i in range(3):
            user_id = f'user{i}'
            session_id = f'session{i}'

            client = MockSocketIOClient(user_id, session_id)
            websocket_broadcaster.socketio.add_client(session_id, client)

            connected_user = ConnectedUser(
                user_id=user_id,
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions=set()
            )
            websocket_broadcaster.connected_users[session_id] = connected_user

        # Broadcast backtest progress
        progress_event = {
            'event_type': 'backtest_progress',
            'source': 'tickstock_pl',
            'timestamp': time.time(),
            'data': {
                'job_id': 'test_job_123',
                'progress': 0.65,
                'status': 'processing'
            }
        }

        websocket_broadcaster.broadcast_backtest_progress(progress_event)

        # Verify all users received broadcast
        for i in range(3):
            client = websocket_broadcaster.socketio.clients[f'session{i}']
            assert len(client.received_messages) == 1

            message = client.received_messages[0]
            assert message['event'] == 'backtest_progress'
            assert message['data']['job_id'] == 'test_job_123'
            assert message['data']['progress'] == 0.65

    def test_backtest_result_broadcasting(self, websocket_broadcaster):
        """Test backtest result broadcasting."""
        # Set up connected user
        client = MockSocketIOClient('test_user', 'test_session')
        websocket_broadcaster.socketio.add_client('test_session', client)

        connected_user = ConnectedUser(
            user_id='test_user',
            session_id='test_session',
            connected_at=time.time(),
            last_seen=time.time(),
            subscriptions=set()
        )
        websocket_broadcaster.connected_users['test_session'] = connected_user

        # Broadcast backtest result
        result_event = {
            'event_type': 'backtest_result',
            'source': 'tickstock_pl',
            'timestamp': time.time(),
            'data': {
                'job_id': 'test_job_456',
                'status': 'completed',
                'results': {
                    'win_rate': 0.72,
                    'roi': 0.15
                }
            }
        }

        websocket_broadcaster.broadcast_backtest_result(result_event)

        # Verify result received
        assert len(client.received_messages) == 1
        message = client.received_messages[0]
        assert message['event'] == 'backtest_result'
        assert message['data']['job_id'] == 'test_job_456'
        assert message['data']['status'] == 'completed'

    def test_system_health_broadcasting(self, websocket_broadcaster):
        """Test system health update broadcasting."""
        # Set up connected user
        client = MockSocketIOClient('health_user', 'health_session')
        websocket_broadcaster.socketio.add_client('health_session', client)

        connected_user = ConnectedUser(
            user_id='health_user',
            session_id='health_session',
            connected_at=time.time(),
            last_seen=time.time(),
            subscriptions=set()
        )
        websocket_broadcaster.connected_users['health_session'] = connected_user

        # Broadcast health update
        health_event = {
            'event_type': 'system_health',
            'source': 'tickstock_pl',
            'timestamp': time.time(),
            'data': {
                'status': 'healthy',
                'cpu_usage': 0.45,
                'memory_usage': 0.68
            }
        }

        websocket_broadcaster.broadcast_system_health(health_event)

        # Verify health update received
        assert len(client.received_messages) == 1
        message = client.received_messages[0]
        assert message['event'] == 'system_health'
        assert message['data']['health_data']['status'] == 'healthy'

    def test_offline_message_queueing(self, websocket_broadcaster):
        """Test message queuing for offline users."""
        user_id = 'offline_user'

        # User not connected, should queue message
        test_message = {
            'type': 'pattern_alert',
            'pattern': 'Doji',
            'symbol': 'AAPL'
        }

        websocket_broadcaster.queue_message_for_offline_user(user_id, test_message)

        # Verify message queued
        assert user_id in websocket_broadcaster.offline_message_queue
        assert len(websocket_broadcaster.offline_message_queue[user_id]) == 1

        queued_message = websocket_broadcaster.offline_message_queue[user_id][0]
        assert queued_message['type'] == 'pattern_alert'
        assert queued_message['pattern'] == 'Doji'
        assert 'queued_at' in queued_message
        assert queued_message['queued'] is True

    def test_offline_message_delivery_on_connect(self, websocket_broadcaster):
        """Test delivery of queued messages when user connects."""
        user_id = 'reconnect_user'
        session_id = 'reconnect_session'

        # Queue some messages for offline user
        messages = [
            {'type': 'pattern_alert', 'pattern': 'Doji'},
            {'type': 'backtest_progress', 'job_id': 'test_123'},
            {'type': 'system_health', 'status': 'healthy'}
        ]

        for msg in messages:
            websocket_broadcaster.queue_message_for_offline_user(user_id, msg)

        # Verify messages queued
        assert len(websocket_broadcaster.offline_message_queue[user_id]) == 3

        # Simulate user connection
        client = MockSocketIOClient(user_id, session_id)
        websocket_broadcaster.socketio.add_client(session_id, client)

        # Trigger message delivery
        websocket_broadcaster._deliver_queued_messages(user_id, session_id)

        # Verify messages delivered
        assert len(client.received_messages) == 3
        assert user_id not in websocket_broadcaster.offline_message_queue

        # Verify message order preserved
        delivered_types = [msg['data']['type'] for msg in client.received_messages]
        expected_types = ['pattern_alert', 'backtest_progress', 'system_health']
        assert delivered_types == expected_types

    def test_offline_message_queue_limits(self, websocket_broadcaster):
        """Test offline message queue size limits."""
        user_id = 'heavy_user'
        websocket_broadcaster.max_offline_messages = 5  # Set low limit for testing

        # Queue more messages than limit
        for i in range(8):
            message = {'type': 'test', 'sequence': i}
            websocket_broadcaster.queue_message_for_offline_user(user_id, message)

        # Verify queue limited to max size
        assert len(websocket_broadcaster.offline_message_queue[user_id]) == 5

        # Verify oldest messages removed (should have sequences 3, 4, 5, 6, 7)
        sequences = [msg['sequence'] for msg in websocket_broadcaster.offline_message_queue[user_id]]
        assert sequences == [3, 4, 5, 6, 7]

    def test_user_online_status_checking(self, websocket_broadcaster):
        """Test online status checking."""
        user_id = 'status_user'
        session_id = 'status_session'

        # User not connected
        assert websocket_broadcaster.is_user_online(user_id) is False

        # Add user session
        websocket_broadcaster.user_sessions[user_id] = {session_id}

        # User now online
        assert websocket_broadcaster.is_user_online(user_id) is True

        # Remove session
        websocket_broadcaster.user_sessions[user_id].clear()

        # User offline again
        assert websocket_broadcaster.is_user_online(user_id) is False

    def test_connected_users_listing(self, websocket_broadcaster):
        """Test getting list of connected users."""
        # Add multiple connected users
        users_data = [
            ('user1', 'session1', ['Doji']),
            ('user2', 'session2', ['Hammer', 'Engulfing']),
            ('user3', 'session3', [])
        ]

        base_time = time.time()

        for i, (user_id, session_id, subscriptions) in enumerate(users_data):
            connected_user = ConnectedUser(
                user_id=user_id,
                session_id=session_id,
                connected_at=base_time - (i * 100),  # Different connection times
                last_seen=base_time - (i * 10),      # Different last seen times
                subscriptions=set(subscriptions)
            )
            websocket_broadcaster.connected_users[session_id] = connected_user

        # Get connected users list
        connected_list = websocket_broadcaster.get_connected_users()

        # Verify list structure
        assert len(connected_list) == 3

        for user_info in connected_list:
            required_keys = ['user_id', 'session_id', 'connected_at', 'last_seen',
                           'subscriptions', 'connection_duration']
            assert all(key in user_info for key in required_keys)
            assert user_info['connection_duration'] > 0

    def test_stale_connection_cleanup(self, websocket_broadcaster):
        """Test cleanup of stale WebSocket connections."""
        # Add active and stale connections
        current_time = time.time()

        # Active connection (recent last_seen)
        active_user = ConnectedUser(
            user_id='active_user',
            session_id='active_session',
            connected_at=current_time - 100,
            last_seen=current_time - 10,  # 10 seconds ago
            subscriptions=set()
        )

        # Stale connection (old last_seen)
        stale_user = ConnectedUser(
            user_id='stale_user',
            session_id='stale_session',
            connected_at=current_time - 1000,
            last_seen=current_time - 400,  # 400 seconds ago
            subscriptions=set()
        )

        websocket_broadcaster.connected_users['active_session'] = active_user
        websocket_broadcaster.connected_users['stale_session'] = stale_user

        # Run cleanup with 300 second threshold
        cleaned_count = websocket_broadcaster.cleanup_stale_connections(max_idle_seconds=300)

        # Verify stale connection cleaned up
        assert cleaned_count == 1
        # Note: In real implementation, this would trigger disconnect which removes from connected_users

    def test_broadcaster_statistics(self, websocket_broadcaster):
        """Test statistics tracking and reporting."""
        # Initial statistics
        initial_stats = websocket_broadcaster.get_stats()
        assert initial_stats['total_connections'] == 0
        assert initial_stats['messages_sent'] == 0
        assert initial_stats['unique_users'] == 0

        # Add some users and send messages
        for i in range(3):
            user_id = f'stats_user_{i}'
            session_id = f'stats_session_{i}'

            # Add to user sessions
            websocket_broadcaster.user_sessions[user_id] = {session_id}

            # Add to connected users
            connected_user = ConnectedUser(
                user_id=user_id,
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions=set()
            )
            websocket_broadcaster.connected_users[session_id] = connected_user

        # Update statistics
        websocket_broadcaster.stats['total_connections'] = 10
        websocket_broadcaster.stats['messages_sent'] = 50
        websocket_broadcaster.stats['messages_queued'] = 5

        # Queue some offline messages
        websocket_broadcaster.offline_message_queue['offline_user'] = [{'test': 'msg'}]

        final_stats = websocket_broadcaster.get_stats()

        # Verify calculated statistics
        assert final_stats['active_connections'] == 3
        assert final_stats['unique_users'] == 3
        assert final_stats['offline_queues'] == 1
        assert final_stats['total_queued_messages'] == 1
        assert final_stats['messages_per_second'] > 0

    def test_broadcast_error_handling(self, websocket_broadcaster):
        """Test error handling during message broadcasting."""
        # Set up user that will cause emission error
        session_id = 'error_session'
        connected_user = ConnectedUser(
            user_id='error_user',
            session_id=session_id,
            connected_at=time.time(),
            last_seen=time.time(),
            subscriptions={'Doji'}
        )
        websocket_broadcaster.connected_users[session_id] = connected_user

        # Mock SocketIO to raise exception on emit
        original_emit = websocket_broadcaster.socketio.emit

        def failing_emit(*args, **kwargs):
            if kwargs.get('room') == session_id:
                raise Exception("Mock emission failure")
            return original_emit(*args, **kwargs)

        websocket_broadcaster.socketio.emit = failing_emit

        # Attempt to broadcast pattern alert
        pattern_event = {
            'data': {
                'pattern': 'Doji',
                'symbol': 'TEST'
            }
        }

        # Should not crash despite emission failure
        websocket_broadcaster.broadcast_pattern_alert(pattern_event)

        # Restore original emit
        websocket_broadcaster.socketio.emit = original_emit

    def test_anonymous_user_message_queueing(self, websocket_broadcaster):
        """Test that messages are not queued for anonymous users."""
        # Try to queue message for anonymous user
        test_message = {'type': 'test', 'data': 'test'}

        websocket_broadcaster.queue_message_for_offline_user('anonymous', test_message)

        # Verify no queue created for anonymous users
        assert 'anonymous' not in websocket_broadcaster.offline_message_queue
        assert websocket_broadcaster.stats['messages_queued'] == 0
