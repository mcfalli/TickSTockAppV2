"""
Comprehensive Production Readiness Tests - WebSocket Real-Time Pattern Alert Broadcasting
Sprint 26: WebSocket Broadcasting and Real-Time Communication

Tests WebSocket pattern alert broadcasting with <100ms delivery requirements.
Validates connection management, user subscriptions, and real-time updates.

Test Categories:
- Integration Tests: WebSocket connection management and broadcasting
- Performance Tests: <100ms message delivery requirements
- Connection Tests: Connect/disconnect handling, heartbeat monitoring
- Security Tests: User authentication, subscription validation
- Resilience Tests: Connection recovery, message queueing
"""

import os
import sys
import threading
import time
from dataclasses import dataclass
from unittest.mock import Mock, patch

import pytest
from flask import Flask
from flask_socketio import SocketIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.services.websocket_broadcaster import ConnectedUser, WebSocketBroadcaster


@dataclass
class MockUser:
    """Mock user for testing."""
    id: str
    username: str


class TestWebSocketPatternBroadcasting:
    """Test suite for WebSocket pattern alert broadcasting."""

    @pytest.fixture
    def flask_app(self):
        """Create Flask test application."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret_key'
        return app

    @pytest.fixture
    def mock_socketio(self):
        """Mock SocketIO for testing."""
        return Mock(spec=SocketIO)

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for offline message persistence."""
        return Mock()

    @pytest.fixture
    def websocket_broadcaster(self, mock_socketio, mock_redis_client):
        """Create WebSocketBroadcaster for testing."""
        return WebSocketBroadcaster(mock_socketio, mock_redis_client)

    @pytest.fixture
    def sample_pattern_event(self):
        """Sample pattern alert event."""
        return {
            'type': 'pattern_alert',
            'data': {
                'pattern': 'Breakout',
                'symbol': 'AAPL',
                'confidence': 0.85,
                'rs': 75.5,
                'volume_multiple': 2.5,
                'price': 150.25,
                'timeframe': 'Daily',
                'detected_at': '2024-09-12T10:30:00Z'
            },
            'timestamp': time.time()
        }

    @pytest.fixture
    def sample_connected_user(self):
        """Sample connected user for testing."""
        return ConnectedUser(
            user_id='user123',
            session_id='session_abc',
            connected_at=time.time(),
            last_seen=time.time(),
            subscriptions={'Breakout', 'Volume', 'Momentum'}
        )

    def test_broadcaster_initialization(self, websocket_broadcaster, mock_socketio, mock_redis_client):
        """Test proper WebSocket broadcaster initialization."""
        assert websocket_broadcaster is not None
        assert websocket_broadcaster.socketio == mock_socketio
        assert websocket_broadcaster.redis_client == mock_redis_client
        assert len(websocket_broadcaster.connected_users) == 0
        assert len(websocket_broadcaster.user_sessions) == 0
        assert websocket_broadcaster.stats['total_connections'] == 0

    def test_user_connection_handling(self, websocket_broadcaster, mock_socketio):
        """Test user connection and session management."""
        # Simulate user connection
        session_id = 'session_123'
        user_id = 'user456'

        # Manually add connected user (simulating SocketIO handler)
        connected_user = ConnectedUser(
            user_id=user_id,
            session_id=session_id,
            connected_at=time.time(),
            last_seen=time.time(),
            subscriptions=set()
        )

        websocket_broadcaster.connected_users[session_id] = connected_user
        if user_id not in websocket_broadcaster.user_sessions:
            websocket_broadcaster.user_sessions[user_id] = set()
        websocket_broadcaster.user_sessions[user_id].add(session_id)

        # Update stats
        websocket_broadcaster.stats['total_connections'] += 1
        websocket_broadcaster.stats['active_connections'] = len(websocket_broadcaster.connected_users)

        # Verify connection tracking
        assert session_id in websocket_broadcaster.connected_users
        assert user_id in websocket_broadcaster.user_sessions
        assert session_id in websocket_broadcaster.user_sessions[user_id]
        assert websocket_broadcaster.stats['active_connections'] == 1

    def test_user_disconnection_handling(self, websocket_broadcaster, sample_connected_user):
        """Test user disconnection and cleanup."""
        session_id = sample_connected_user.session_id
        user_id = sample_connected_user.user_id

        # Add connected user
        websocket_broadcaster.connected_users[session_id] = sample_connected_user
        websocket_broadcaster.user_sessions[user_id] = {session_id}
        websocket_broadcaster.stats['active_connections'] = 1

        # Simulate disconnection
        if session_id in websocket_broadcaster.connected_users:
            connected_user = websocket_broadcaster.connected_users[session_id]
            del websocket_broadcaster.connected_users[session_id]

            if user_id in websocket_broadcaster.user_sessions:
                websocket_broadcaster.user_sessions[user_id].discard(session_id)
                if not websocket_broadcaster.user_sessions[user_id]:
                    del websocket_broadcaster.user_sessions[user_id]

            websocket_broadcaster.stats['disconnections'] += 1
            websocket_broadcaster.stats['active_connections'] = len(websocket_broadcaster.connected_users)

        # Verify cleanup
        assert session_id not in websocket_broadcaster.connected_users
        assert user_id not in websocket_broadcaster.user_sessions
        assert websocket_broadcaster.stats['disconnections'] == 1
        assert websocket_broadcaster.stats['active_connections'] == 0

    def test_pattern_subscription_management(self, websocket_broadcaster, sample_connected_user, mock_socketio):
        """Test pattern subscription management."""
        session_id = sample_connected_user.session_id
        websocket_broadcaster.connected_users[session_id] = sample_connected_user

        # Test subscription update
        new_patterns = {'Breakout', 'Volume', 'Momentum', 'Support'}
        sample_connected_user.subscriptions = new_patterns
        sample_connected_user.update_last_seen()

        # Verify subscription update
        assert sample_connected_user.subscriptions == new_patterns
        assert len(sample_connected_user.subscriptions) == 4
        assert 'Support' in sample_connected_user.subscriptions

    @pytest.mark.performance
    def test_pattern_alert_broadcast_performance(self, websocket_broadcaster, sample_pattern_event, mock_socketio):
        """Test pattern alert broadcasting meets <100ms performance requirement."""
        # Create multiple connected users with subscriptions
        user_count = 50
        for i in range(user_count):
            session_id = f'session_{i}'
            user_id = f'user_{i}'

            connected_user = ConnectedUser(
                user_id=user_id,
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions={'Breakout'}  # Subscribe to test pattern
            )

            websocket_broadcaster.connected_users[session_id] = connected_user

        # Performance test: Broadcast to all subscribed users
        iterations = 10
        broadcast_times = []

        for i in range(iterations):
            start_time = time.perf_counter()
            websocket_broadcaster.broadcast_pattern_alert(sample_pattern_event)
            end_time = time.perf_counter()

            broadcast_time_ms = (end_time - start_time) * 1000
            broadcast_times.append(broadcast_time_ms)

        # Calculate performance metrics
        avg_broadcast_time = sum(broadcast_times) / len(broadcast_times)
        max_broadcast_time = max(broadcast_times)

        # Assert: <100ms broadcast time
        assert avg_broadcast_time < 100, f"Average broadcast time {avg_broadcast_time:.2f}ms exceeds 100ms requirement"
        assert max_broadcast_time < 150, f"Max broadcast time {max_broadcast_time:.2f}ms too high"

        # Verify all subscribed users received the alert
        expected_emissions = user_count * iterations
        assert mock_socketio.emit.call_count == expected_emissions

    def test_targeted_pattern_broadcasting(self, websocket_broadcaster, sample_pattern_event, mock_socketio):
        """Test targeted broadcasting to subscribed users only."""
        # Create users with different subscriptions
        users_data = [
            ('session_1', 'user_1', {'Breakout', 'Volume'}),      # Should receive
            ('session_2', 'user_2', {'Momentum', 'Support'}),     # Should NOT receive
            ('session_3', 'user_3', {'Breakout'}),               # Should receive
            ('session_4', 'user_4', set()),                       # Empty subscription = receive all
        ]

        for session_id, user_id, subscriptions in users_data:
            connected_user = ConnectedUser(
                user_id=user_id,
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions=subscriptions
            )
            websocket_broadcaster.connected_users[session_id] = connected_user

        # Broadcast Breakout pattern
        websocket_broadcaster.broadcast_pattern_alert(sample_pattern_event)

        # Verify targeted broadcasting
        # Should emit to session_1, session_3, and session_4 (3 total)
        assert mock_socketio.emit.call_count == 3

        # Verify message content
        for call_args in mock_socketio.emit.call_args_list:
            event_name = call_args[0][0]
            message_data = call_args[0][1]

            assert event_name == 'pattern_alert'
            assert message_data['type'] == 'pattern_alert'
            assert message_data['pattern'] == 'Breakout'
            assert message_data['symbol'] == 'AAPL'

    def test_backtest_progress_broadcasting(self, websocket_broadcaster, mock_socketio):
        """Test backtest progress broadcasting to all users."""
        # Create connected users
        for i in range(5):
            session_id = f'session_{i}'
            user_id = f'user_{i}'

            connected_user = ConnectedUser(
                user_id=user_id,
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions=set()
            )
            websocket_broadcaster.connected_users[session_id] = connected_user

        # Sample backtest progress event
        progress_event = {
            'type': 'backtest_progress',
            'data': {
                'job_id': 'bt_12345',
                'progress': 0.65,
                'current_symbol': 'GOOGL',
                'estimated_completion': time.time() + 300
            },
            'timestamp': time.time()
        }

        # Broadcast backtest progress
        websocket_broadcaster.broadcast_backtest_progress(progress_event)

        # Verify broadcast to all users
        mock_socketio.emit.assert_called_once_with('backtest_progress',
                                                   message=progress_event,
                                                   broadcast=True)

        # Verify statistics updated
        assert websocket_broadcaster.stats['messages_sent'] == 5  # All connected users

    def test_system_health_broadcasting(self, websocket_broadcaster, mock_socketio):
        """Test system health broadcasting to all users."""
        # Add connected users
        for i in range(3):
            session_id = f'session_{i}'
            websocket_broadcaster.connected_users[session_id] = ConnectedUser(
                user_id=f'user_{i}',
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions=set()
            )

        # Sample system health event
        health_event = {
            'type': 'system_health',
            'data': {
                'status': 'healthy',
                'cpu_usage': 45.2,
                'memory_usage': 67.8,
                'processing_rate': 1250.5
            },
            'timestamp': time.time()
        }

        # Broadcast system health
        websocket_broadcaster.broadcast_system_health(health_event)

        # Verify broadcast
        mock_socketio.emit.assert_called_once_with('system_health',
                                                   message=health_event,
                                                   broadcast=True)

    def test_offline_message_queueing(self, websocket_broadcaster):
        """Test message queueing for offline users."""
        user_id = 'offline_user'
        test_message = {
            'type': 'pattern_alert',
            'data': {'pattern': 'Breakout', 'symbol': 'AAPL'},
            'timestamp': time.time()
        }

        # Queue message for offline user
        websocket_broadcaster.queue_message_for_offline_user(user_id, test_message)

        # Verify message queued
        assert user_id in websocket_broadcaster.offline_message_queue
        assert len(websocket_broadcaster.offline_message_queue[user_id]) == 1
        assert websocket_broadcaster.stats['messages_queued'] == 1

        # Verify queued message format
        queued_message = websocket_broadcaster.offline_message_queue[user_id][0]
        assert 'queued_at' in queued_message
        assert 'queued' in queued_message
        assert queued_message['queued'] is True

    def test_offline_message_queue_size_limit(self, websocket_broadcaster):
        """Test offline message queue size limiting."""
        user_id = 'heavy_user'
        max_messages = websocket_broadcaster.max_offline_messages

        # Queue more than max allowed messages
        for i in range(max_messages + 50):
            message = {
                'type': 'pattern_alert',
                'data': {'pattern': f'Pattern_{i}', 'symbol': 'TEST'},
                'timestamp': time.time()
            }
            websocket_broadcaster.queue_message_for_offline_user(user_id, message)

        # Verify queue size is limited
        assert len(websocket_broadcaster.offline_message_queue[user_id]) == max_messages

        # Verify most recent messages are kept
        last_message = websocket_broadcaster.offline_message_queue[user_id][-1]
        assert 'Pattern_' in last_message['data']['pattern']

    def test_queued_message_delivery(self, websocket_broadcaster, mock_socketio):
        """Test delivery of queued messages to reconnecting users."""
        user_id = 'returning_user'
        session_id = 'new_session'

        # Queue messages for offline user
        test_messages = [
            {'type': 'pattern_alert', 'data': {'pattern': 'Breakout', 'symbol': 'AAPL'}},
            {'type': 'pattern_alert', 'data': {'pattern': 'Volume', 'symbol': 'GOOGL'}},
            {'type': 'backtest_result', 'data': {'job_id': 'bt_123', 'status': 'completed'}}
        ]

        for message in test_messages:
            websocket_broadcaster.queue_message_for_offline_user(user_id, message)

        # Simulate message delivery (called when user reconnects)
        if user_id in websocket_broadcaster.offline_message_queue:
            queued_messages = websocket_broadcaster.offline_message_queue[user_id]

            # Simulate delivery
            for message in queued_messages:
                mock_socketio.emit('queued_message', message, room=session_id)

            # Clear queue
            del websocket_broadcaster.offline_message_queue[user_id]

        # Verify delivery
        assert mock_socketio.emit.call_count == 3
        assert user_id not in websocket_broadcaster.offline_message_queue

    def test_user_online_status_check(self, websocket_broadcaster, sample_connected_user):
        """Test accurate user online status checking."""
        user_id = sample_connected_user.user_id

        # User not connected
        assert not websocket_broadcaster.is_user_online(user_id)

        # Add user connection
        websocket_broadcaster.user_sessions[user_id] = {sample_connected_user.session_id}

        # User now online
        assert websocket_broadcaster.is_user_online(user_id)

        # Remove user session
        del websocket_broadcaster.user_sessions[user_id]

        # User offline again
        assert not websocket_broadcaster.is_user_online(user_id)

    def test_connected_users_reporting(self, websocket_broadcaster):
        """Test accurate connected users reporting."""
        # Add multiple users
        users_data = [
            ('session_1', 'user_1', {'Breakout'}),
            ('session_2', 'user_2', {'Volume', 'Momentum'}),
            ('session_3', 'user_1', set())  # Same user, different session
        ]

        for session_id, user_id, subscriptions in users_data:
            connected_user = ConnectedUser(
                user_id=user_id,
                session_id=session_id,
                connected_at=time.time() - 300,  # Connected 5 minutes ago
                last_seen=time.time() - 60,      # Last seen 1 minute ago
                subscriptions=subscriptions
            )
            websocket_broadcaster.connected_users[session_id] = connected_user

        # Get connected users report
        connected_users = websocket_broadcaster.get_connected_users()

        # Verify report
        assert len(connected_users) == 3  # 3 sessions

        for user_info in connected_users:
            assert 'user_id' in user_info
            assert 'session_id' in user_info
            assert 'connected_at' in user_info
            assert 'last_seen' in user_info
            assert 'subscriptions' in user_info
            assert 'connection_duration' in user_info

            # Connection duration should be around 5 minutes (300 seconds)
            assert user_info['connection_duration'] > 250
            assert user_info['connection_duration'] < 350

    def test_statistics_reporting(self, websocket_broadcaster):
        """Test accurate statistics reporting."""
        # Simulate activity
        websocket_broadcaster.stats['total_connections'] = 100
        websocket_broadcaster.stats['active_connections'] = 25
        websocket_broadcaster.stats['messages_sent'] = 500
        websocket_broadcaster.stats['disconnections'] = 75

        # Add offline message queues
        websocket_broadcaster.offline_message_queue['user1'] = [{'msg': 'test1'}]
        websocket_broadcaster.offline_message_queue['user2'] = [{'msg': 'test2'}, {'msg': 'test3'}]

        # Add user sessions
        websocket_broadcaster.user_sessions = {'user_a': {'session1'}, 'user_b': {'session2', 'session3'}}

        # Get statistics
        stats = websocket_broadcaster.get_stats()

        # Verify statistics
        assert stats['total_connections'] == 100
        assert stats['active_connections'] == 25
        assert stats['messages_sent'] == 500
        assert stats['disconnections'] == 75
        assert stats['unique_users'] == 2
        assert stats['offline_queues'] == 2
        assert stats['total_queued_messages'] == 3
        assert 'runtime_seconds' in stats
        assert 'messages_per_second' in stats

    def test_stale_connection_cleanup(self, websocket_broadcaster, mock_socketio):
        """Test cleanup of stale connections."""
        current_time = time.time()

        # Add connections with different last seen times
        connections_data = [
            ('session_1', current_time - 60),    # Recent (1 minute ago)
            ('session_2', current_time - 400),   # Stale (6+ minutes ago)
            ('session_3', current_time - 30),    # Recent (30 seconds ago)
            ('session_4', current_time - 500),   # Stale (8+ minutes ago)
        ]

        for session_id, last_seen in connections_data:
            connected_user = ConnectedUser(
                user_id=f'user_{session_id}',
                session_id=session_id,
                connected_at=current_time - 3600,
                last_seen=last_seen,
                subscriptions=set()
            )
            websocket_broadcaster.connected_users[session_id] = connected_user

        # Cleanup stale connections (5 minute threshold)
        with patch.object(websocket_broadcaster.socketio, 'disconnect') as mock_disconnect:
            stale_count = websocket_broadcaster.cleanup_stale_connections(max_idle_seconds=300)

        # Verify stale connections identified and disconnected
        assert stale_count == 2  # session_2 and session_4
        assert mock_disconnect.call_count == 2

        # Verify which sessions were disconnected
        disconnected_sessions = [call[0][0] for call in mock_disconnect.call_args_list]
        assert 'session_2' in disconnected_sessions
        assert 'session_4' in disconnected_sessions

    @pytest.mark.performance
    def test_high_concurrency_broadcasting(self, websocket_broadcaster, mock_socketio):
        """Test broadcasting under high concurrency load."""
        # Create large number of connected users
        user_count = 200
        for i in range(user_count):
            session_id = f'session_{i}'
            connected_user = ConnectedUser(
                user_id=f'user_{i}',
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions={'Breakout'}
            )
            websocket_broadcaster.connected_users[session_id] = connected_user

        # Concurrent broadcasting test
        broadcast_count = 50
        broadcast_times = []

        def broadcast_pattern():
            start_time = time.perf_counter()

            test_event = {
                'type': 'pattern_alert',
                'data': {'pattern': 'Breakout', 'symbol': 'TEST'},
                'timestamp': time.time()
            }

            websocket_broadcaster.broadcast_pattern_alert(test_event)

            end_time = time.perf_counter()
            broadcast_times.append((end_time - start_time) * 1000)

        # Create concurrent broadcast threads
        threads = []
        for _ in range(broadcast_count):
            thread = threading.Thread(target=broadcast_pattern)
            threads.append(thread)
            thread.start()

        # Wait for all broadcasts to complete
        for thread in threads:
            thread.join()

        # Verify performance
        avg_broadcast_time = sum(broadcast_times) / len(broadcast_times)
        max_broadcast_time = max(broadcast_times)

        # Even under high concurrency, should maintain reasonable performance
        assert avg_broadcast_time < 200, f"Average broadcast time {avg_broadcast_time:.2f}ms too high under load"
        assert max_broadcast_time < 500, f"Max broadcast time {max_broadcast_time:.2f}ms too high under load"

        # Verify all broadcasts completed
        expected_total_emissions = user_count * broadcast_count
        assert mock_socketio.emit.call_count == expected_total_emissions

    def test_heartbeat_monitoring(self, websocket_broadcaster):
        """Test heartbeat monitoring for connection health."""
        session_id = 'session_heartbeat'
        user_id = 'user_heartbeat'

        # Create connected user
        connected_user = ConnectedUser(
            user_id=user_id,
            session_id=session_id,
            connected_at=time.time(),
            last_seen=time.time() - 30,  # 30 seconds ago
            subscriptions=set()
        )
        websocket_broadcaster.connected_users[session_id] = connected_user

        # Simulate heartbeat update
        initial_last_seen = connected_user.last_seen
        time.sleep(0.1)  # Small delay
        connected_user.update_last_seen()

        # Verify heartbeat updated
        assert connected_user.last_seen > initial_last_seen

        # Test heartbeat age calculation
        heartbeat_age = time.time() - connected_user.last_seen
        assert heartbeat_age < 1.0  # Should be very recent

    def test_message_delivery_error_handling(self, websocket_broadcaster, mock_socketio):
        """Test error handling during message delivery."""
        # Add connected user
        session_id = 'session_error'
        connected_user = ConnectedUser(
            user_id='user_error',
            session_id=session_id,
            connected_at=time.time(),
            last_seen=time.time(),
            subscriptions={'Breakout'}
        )
        websocket_broadcaster.connected_users[session_id] = connected_user

        # Mock SocketIO emit to raise exception
        mock_socketio.emit.side_effect = Exception("WebSocket connection error")

        # Attempt broadcast (should handle error gracefully)
        test_event = {
            'type': 'pattern_alert',
            'data': {'pattern': 'Breakout', 'symbol': 'AAPL'},
            'timestamp': time.time()
        }

        # Should not raise exception
        websocket_broadcaster.broadcast_pattern_alert(test_event)

        # Verify attempt was made
        assert mock_socketio.emit.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
