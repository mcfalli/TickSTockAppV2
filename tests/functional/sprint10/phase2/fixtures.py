"""
Integration Test Fixtures for Sprint 10 Phase 2
Comprehensive fixtures for Redis Event Consumption and WebSocket Broadcasting tests.
"""

import pytest
import threading
import time
import json
import redis
from unittest.mock import Mock, MagicMock, patch, create_autospec
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from flask import Flask
from flask_socketio import SocketIO
import eventlet

# Import TickStockApp components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from core.services.redis_event_subscriber import RedisEventSubscriber, EventType, TickStockEvent
from core.services.websocket_broadcaster import WebSocketBroadcaster, ConnectedUser


@dataclass
class MockRedisMessage:
    """Mock Redis pub-sub message for testing."""
    channel: str
    data: str
    type: str = 'message'
    
    def __getitem__(self, key):
        """Allow dictionary-style access."""
        return getattr(self, key)


class MockRedisClient:
    """Enhanced mock Redis client with pub-sub simulation."""
    
    def __init__(self):
        self.connected = True
        self.channels = {}
        self.pubsub_instance = None
        self.published_messages = []
        
    def ping(self):
        """Mock ping method."""
        if not self.connected:
            raise redis.ConnectionError("Mock Redis connection failed")
        return True
    
    def pubsub(self):
        """Create mock pubsub instance."""
        if self.pubsub_instance is None:
            self.pubsub_instance = MockPubSub(self)
        return self.pubsub_instance
    
    def publish(self, channel: str, message: str):
        """Mock publish - stores messages for verification."""
        message_data = {
            'channel': channel,
            'message': message,
            'timestamp': time.time()
        }
        self.published_messages.append(message_data)
        
        # Deliver to subscribers if any
        if self.pubsub_instance and channel in self.pubsub_instance.subscribed_channels:
            mock_message = MockRedisMessage(
                channel=channel,
                data=message,
                type='message'
            )
            self.pubsub_instance.message_queue.append(mock_message)
    
    def simulate_connection_failure(self):
        """Simulate Redis connection failure."""
        self.connected = False
        
    def restore_connection(self):
        """Restore Redis connection."""
        self.connected = True


class MockPubSub:
    """Mock Redis pub-sub client."""
    
    def __init__(self, redis_client: MockRedisClient):
        self.redis_client = redis_client
        self.subscribed_channels = set()
        self.message_queue = []
        self.closed = False
        
    def subscribe(self, channels):
        """Mock subscribe to channels."""
        if isinstance(channels, str):
            channels = [channels]
        
        for channel in channels:
            self.subscribed_channels.add(channel)
        
        # Add subscription confirmation messages
        for channel in channels:
            confirm_msg = MockRedisMessage(
                channel=channel,
                data=1,  # Subscription count
                type='subscribe'
            )
            self.message_queue.append(confirm_msg)
    
    def unsubscribe(self):
        """Mock unsubscribe from all channels."""
        self.subscribed_channels.clear()
        
    def close(self):
        """Mock close pubsub connection."""
        self.closed = True
        
    def get_message(self, timeout=None):
        """Mock get message with timeout."""
        if not self.redis_client.connected:
            raise redis.ConnectionError("Mock connection error")
            
        if self.message_queue:
            return self.message_queue.pop(0)
            
        return None


class MockSocketIOClient:
    """Mock SocketIO client for testing broadcasts."""
    
    def __init__(self, user_id: str = "test_user", session_id: str = "test_session"):
        self.user_id = user_id
        self.session_id = session_id
        self.received_messages = []
        self.connected = True
        self.subscriptions = set()
        
    def emit(self, event: str, data: Dict[str, Any]):
        """Mock emit - store received messages."""
        self.received_messages.append({
            'event': event,
            'data': data,
            'timestamp': time.time()
        })


class MockSocketIO:
    """Enhanced mock SocketIO for integration testing."""
    
    def __init__(self):
        self.clients = {}
        self.broadcast_messages = []
        self.room_messages = {}
        self.event_handlers = {}
        self.server = MockSocketIOServer()
        
    def emit(self, event: str, data: Dict[str, Any], broadcast: bool = False, room: str = None):
        """Mock emit with broadcast and room support."""
        message = {
            'event': event,
            'data': data,
            'broadcast': broadcast,
            'room': room,
            'timestamp': time.time()
        }
        
        if broadcast:
            self.broadcast_messages.append(message)
            # Deliver to all connected clients
            for client in self.clients.values():
                client.emit(event, data)
        elif room:
            if room not in self.room_messages:
                self.room_messages[room] = []
            self.room_messages[room].append(message)
            # Deliver to client in that room (session)
            if room in self.clients:
                self.clients[room].emit(event, data)
        
    def on(self, event_name: str):
        """Mock decorator for event handlers."""
        def decorator(handler):
            self.event_handlers[event_name] = handler
            return handler
        return decorator
        
    def add_client(self, session_id: str, client: MockSocketIOClient):
        """Add mock client for testing."""
        self.clients[session_id] = client
        
    def remove_client(self, session_id: str):
        """Remove mock client."""
        if session_id in self.clients:
            del self.clients[session_id]
            
    def trigger_event(self, event_name: str, *args, **kwargs):
        """Manually trigger event handler for testing."""
        if event_name in self.event_handlers:
            return self.event_handlers[event_name](*args, **kwargs)
            
    def disconnect(self, session_id: str):
        """Mock disconnect client."""
        if session_id in self.clients:
            self.clients[session_id].connected = False


class MockSocketIOServer:
    """Mock SocketIO server for session management."""
    
    def __init__(self):
        self.current_sid = "test_session_123"
        
    def get_sid(self):
        """Return current session ID."""
        return self.current_sid


class TickStockPLSimulator:
    """Simulate TickStockPL publishing events for integration testing."""
    
    def __init__(self, redis_client: MockRedisClient):
        self.redis_client = redis_client
        
    def publish_pattern_event(self, symbol: str, pattern: str, confidence: float = 0.85):
        """Simulate TickStockPL publishing pattern detection event."""
        event_data = {
            'event_type': 'pattern_detected',
            'source': 'tickstock_pl',
            'timestamp': time.time(),
            'pattern': pattern,
            'symbol': symbol,
            'confidence': confidence,
            'details': {
                'detection_method': 'ML_model_v2',
                'historical_accuracy': 0.78
            }
        }
        
        channel = 'tickstock.events.patterns'
        message = json.dumps(event_data)
        self.redis_client.publish(channel, message)
        return event_data
        
    def publish_backtest_progress(self, job_id: str, progress: float, status: str = 'processing'):
        """Simulate TickStockPL publishing backtest progress."""
        progress_data = {
            'event_type': 'backtest_progress',
            'source': 'tickstock_pl', 
            'timestamp': time.time(),
            'job_id': job_id,
            'progress': progress,
            'status': status,
            'estimated_completion': time.time() + (1 - progress) * 300,  # Estimate based on remaining
            'current_symbol': 'AAPL',
            'processed_symbols': int(progress * 100)
        }
        
        channel = 'tickstock.events.backtesting.progress'
        message = json.dumps(progress_data)
        self.redis_client.publish(channel, message)
        return progress_data
        
    def publish_backtest_result(self, job_id: str, status: str = 'completed'):
        """Simulate TickStockPL publishing backtest completion."""
        result_data = {
            'event_type': 'backtest_result',
            'source': 'tickstock_pl',
            'timestamp': time.time(),
            'job_id': job_id,
            'status': status,
            'results': {
                'win_rate': 0.65,
                'total_trades': 150,
                'winning_trades': 98,
                'roi': 0.12,
                'sharpe_ratio': 1.8,
                'max_drawdown': 0.05,
                'duration_days': 252
            },
            'processing_time_seconds': 45.2
        }
        
        channel = 'tickstock.events.backtesting.results'
        message = json.dumps(result_data)
        self.redis_client.publish(channel, message)
        return result_data
        
    def publish_system_health(self, status: str = 'healthy'):
        """Simulate TickStockPL publishing system health update."""
        health_data = {
            'event_type': 'system_health',
            'source': 'tickstock_pl',
            'timestamp': time.time(),
            'status': status,
            'metrics': {
                'cpu_usage': 0.35,
                'memory_usage': 0.62,
                'disk_usage': 0.28,
                'active_jobs': 3,
                'queue_depth': 12,
                'uptime_hours': 72.5
            }
        }
        
        channel = 'tickstock.health.status'
        message = json.dumps(health_data)
        self.redis_client.publish(channel, message)
        return health_data


# Pytest Fixtures

@pytest.fixture
def mock_redis_client():
    """Provide mock Redis client for testing."""
    return MockRedisClient()


@pytest.fixture
def mock_socketio():
    """Provide mock SocketIO for testing."""
    return MockSocketIO()


@pytest.fixture
def mock_flask_app():
    """Provide mock Flask app for SocketIO integration."""
    app = Mock(spec=Flask)
    app.config = {'TESTING': True}
    return app


@pytest.fixture
def tickstockpl_simulator(mock_redis_client):
    """Provide TickStockPL simulator for testing."""
    return TickStockPLSimulator(mock_redis_client)


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': 6379,
        'REDIS_DB': 15,  # Test database
        'REDIS_URL': 'redis://localhost:6379/15',
        'TESTING': True,
        'LOG_LEVEL': 'DEBUG'
    }


@pytest.fixture
def redis_subscriber(mock_redis_client, mock_socketio, test_config):
    """Provide RedisEventSubscriber instance for testing."""
    return RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)


@pytest.fixture
def websocket_broadcaster(mock_socketio, mock_redis_client):
    """Provide WebSocketBroadcaster instance for testing."""
    return WebSocketBroadcaster(mock_socketio, mock_redis_client)


@pytest.fixture
def mock_connected_users():
    """Provide mock connected users for testing."""
    users = []
    
    for i in range(3):
        user = ConnectedUser(
            user_id=f"user_{i}",
            session_id=f"session_{i}",
            connected_at=time.time() - 300,  # Connected 5 minutes ago
            last_seen=time.time() - 10,      # Last seen 10 seconds ago
            subscriptions=set(['Doji', 'Hammer']) if i % 2 == 0 else set(['Engulfing'])
        )
        users.append(user)
        
    return users


@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = time.perf_counter()
            
        def stop(self):
            self.end_time = time.perf_counter()
            
        @property
        def elapsed_ms(self) -> float:
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return 0.0
            
        @property
        def elapsed_s(self) -> float:
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0.0
            
    return PerformanceTimer()


@pytest.fixture
def integration_test_environment(mock_redis_client, mock_socketio, test_config):
    """Set up complete integration test environment."""
    class IntegrationEnvironment:
        def __init__(self):
            self.redis_client = mock_redis_client
            self.socketio = mock_socketio
            self.config = test_config
            self.simulator = TickStockPLSimulator(mock_redis_client)
            
            # Initialize components
            self.subscriber = RedisEventSubscriber(mock_redis_client, mock_socketio, test_config)
            self.broadcaster = WebSocketBroadcaster(mock_socketio, mock_redis_client)
            
            # Track all events for verification
            self.received_events = []
            
        def setup_event_tracking(self):
            """Set up event tracking for verification."""
            for event_type in EventType:
                self.subscriber.add_event_handler(
                    event_type, 
                    lambda event, et=event_type: self.received_events.append((et, event))
                )
                
        def add_mock_user(self, user_id: str, session_id: str, subscriptions: List[str] = None):
            """Add mock user to WebSocket broadcaster."""
            client = MockSocketIOClient(user_id, session_id)
            if subscriptions:
                client.subscriptions = set(subscriptions)
                
            self.socketio.add_client(session_id, client)
            
            # Add to broadcaster's tracking
            connected_user = ConnectedUser(
                user_id=user_id,
                session_id=session_id,
                connected_at=time.time(),
                last_seen=time.time(),
                subscriptions=set(subscriptions) if subscriptions else set()
            )
            self.broadcaster.connected_users[session_id] = connected_user
            
            if user_id not in self.broadcaster.user_sessions:
                self.broadcaster.user_sessions[user_id] = set()
            self.broadcaster.user_sessions[user_id].add(session_id)
            
            return client
            
        def start_subscriber(self):
            """Start Redis event subscriber."""
            return self.subscriber.start()
            
        def stop_subscriber(self):
            """Stop Redis event subscriber."""
            self.subscriber.stop()
            
        def wait_for_events(self, timeout: float = 1.0):
            """Wait for events to be processed."""
            time.sleep(timeout)
            
    return IntegrationEnvironment()


# Helper functions for assertions

def assert_redis_message_valid(message: Dict[str, Any]):
    """Assert Redis message has valid structure."""
    assert 'event_type' in message
    assert 'source' in message
    assert 'timestamp' in message
    assert message['source'] == 'tickstock_pl'


def assert_websocket_message_valid(message: Dict[str, Any]):
    """Assert WebSocket message has valid structure."""
    assert 'type' in message
    assert 'timestamp' in message
    if 'event_data' in message:
        assert isinstance(message['event_data'], dict)


def assert_performance_acceptable(duration_ms: float, max_ms: int = 100):
    """Assert performance meets requirements."""
    assert duration_ms <= max_ms, f"Performance requirement failed: {duration_ms:.2f}ms > {max_ms}ms"


def assert_event_delivery_complete(
    sent_events: List[Dict[str, Any]], 
    received_events: List[Dict[str, Any]], 
    tolerance_ms: int = 100
):
    """Assert all events were delivered within tolerance."""
    assert len(received_events) == len(sent_events), \
        f"Event count mismatch: sent {len(sent_events)}, received {len(received_events)}"
    
    for sent, received in zip(sent_events, received_events):
        delivery_time_ms = (received['timestamp'] - sent['timestamp']) * 1000
        assert delivery_time_ms <= tolerance_ms, \
            f"Delivery time {delivery_time_ms:.2f}ms exceeds tolerance {tolerance_ms}ms"