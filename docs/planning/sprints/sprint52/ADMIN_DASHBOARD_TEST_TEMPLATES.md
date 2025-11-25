# Admin Dashboard Test Templates - Copy & Paste Ready

Quick templates for common admin dashboard test scenarios.

---

## Template 1: WebSocket Connection Test

```python
import pytest
from unittest.mock import Mock
import time


@pytest.mark.websocket
@pytest.mark.admin
class TestAdminDashboardWebSocket:
    """Test WebSocket functionality for admin dashboard."""

    def test_admin_websocket_connection(self, mock_websocket):
        """Test WebSocket connection for admin user."""
        
        class AdminWebSocketHandler:
            def __init__(self):
                self.connected = False
                self.connected_admins = {}
                self.commands_queue = []

            def connect_admin(self, admin_id):
                """Register admin WebSocket connection."""
                self.connected = True
                self.connected_admins[admin_id] = {
                    'connected_at': time.time(),
                    'subscription_count': 0
                }
                return True

            def disconnect_admin(self, admin_id):
                """Unregister admin WebSocket connection."""
                if admin_id in self.connected_admins:
                    del self.connected_admins[admin_id]
                self.connected = len(self.connected_admins) > 0
                return True

            def send_command(self, admin_id, command):
                """Send admin command."""
                if self.connected and admin_id in self.connected_admins:
                    self.commands_queue.append({
                        'admin_id': admin_id,
                        'command': command,
                        'timestamp': time.time()
                    })
                    return True
                return False

        handler = AdminWebSocketHandler()

        # Test connection
        assert handler.connect_admin('admin_001')
        assert handler.connected
        assert 'admin_001' in handler.connected_admins

        # Test command sending
        cmd = {'action': 'restart_service', 'service': 'websocket'}
        assert handler.send_command('admin_001', cmd)
        assert len(handler.commands_queue) == 1
        assert handler.commands_queue[0]['command'] == cmd

        # Test disconnection
        assert handler.disconnect_admin('admin_001')
        assert not handler.connected
        assert 'admin_001' not in handler.connected_admins
```

---

## Template 2: Admin Authentication Test

```python
@pytest.mark.admin
@pytest.mark.security
class TestAdminAuthentication:
    """Test admin authentication and session management."""

    def test_admin_login_required(self, client):
        """Test that admin dashboard requires authentication."""
        # Access without login
        response = client.get('/admin/dashboard')
        # Should redirect to login (302) or return 401
        assert response.status_code in [301, 302, 401, 403]

    def test_admin_can_access_dashboard(self, client, admin_user):
        """Test that authenticated admin can access dashboard."""
        with client:
            # Login
            response = client.post('/login', data={
                'email': admin_user.email,
                'password': 'test_password'
            })
            
            # Access dashboard
            response = client.get('/admin/dashboard')
            assert response.status_code == 200
            assert b'admin-dashboard' in response.data or b'Admin' in response.data

    def test_regular_user_denied_admin_access(self, client, regular_user):
        """Test that regular users cannot access admin pages."""
        with client:
            # Login as regular user
            client.post('/login', data={
                'email': regular_user.email,
                'password': 'test_password'
            })
            
            # Try to access admin dashboard
            response = client.get('/admin/dashboard')
            # Should be denied (403) or redirected (302)
            assert response.status_code in [403, 302]

    @pytest.fixture
    def admin_user(self, app):
        """Create admin user fixture."""
        from src.infrastructure.database.models.base import User, db
        
        with app.app_context():
            user = User(
                email='admin@test.com',
                username='admin_test',
                role='admin'
            )
            user.set_password('test_password')
            db.session.add(user)
            db.session.commit()
            return user

    @pytest.fixture
    def regular_user(self, app):
        """Create regular user fixture."""
        from src.infrastructure.database.models.base import User, db
        
        with app.app_context():
            user = User(
                email='user@test.com',
                username='regular_test',
                role='user'
            )
            user.set_password('test_password')
            db.session.add(user)
            db.session.commit()
            return user
```

---

## Template 3: Admin Command Broadcasting Test

```python
@pytest.mark.websocket
@pytest.mark.integration
class TestAdminCommandBroadcasting:
    """Test broadcasting admin commands to relevant services."""

    def test_broadcast_admin_command_to_all_admins(self):
        """Test that admin commands are broadcast to all connected admins."""
        from queue import Queue
        
        class AdminCommandBroadcaster:
            def __init__(self):
                self.admin_connections = {}
                self.broadcast_log = []

            def add_admin_connection(self, admin_id):
                self.admin_connections[admin_id] = {
                    'message_queue': Queue(),
                    'connected_at': time.time()
                }

            def broadcast_command(self, command):
                """Broadcast command to all admins."""
                broadcast_start = time.perf_counter()
                
                for admin_id, conn in self.admin_connections.items():
                    conn['message_queue'].put(command)
                
                broadcast_end = time.perf_counter()
                broadcast_time = (broadcast_end - broadcast_start) * 1000
                
                self.broadcast_log.append({
                    'command': command,
                    'broadcast_time_ms': broadcast_time,
                    'admin_count': len(self.admin_connections),
                    'timestamp': time.time()
                })
                
                return broadcast_time

            def get_messages(self, admin_id, count=10):
                """Get messages for admin."""
                messages = []
                try:
                    while len(messages) < count:
                        msg = self.admin_connections[admin_id]['message_queue'].get_nowait()
                        messages.append(msg)
                except:
                    pass
                return messages

        broadcaster = AdminCommandBroadcaster()
        
        # Add multiple admin connections
        for i in range(5):
            broadcaster.add_admin_connection(f'admin_{i:03d}')

        # Broadcast command
        command = {
            'action': 'update_config',
            'config': {'log_level': 'DEBUG'},
            'timestamp': time.time()
        }

        broadcast_time = broadcaster.broadcast_command(command)

        # Verify all admins received command
        for admin_id in broadcaster.admin_connections.keys():
            messages = broadcaster.get_messages(admin_id)
            assert len(messages) == 1
            assert messages[0] == command

        # Verify performance
        assert broadcast_time < 100, f"Broadcast took {broadcast_time}ms (target: <100ms)"

    def test_targeted_admin_command(self):
        """Test sending command to specific admin."""
        from queue import Queue
        
        class AdminCommandRouter:
            def __init__(self):
                self.admin_connections = {}

            def add_admin(self, admin_id):
                self.admin_connections[admin_id] = Queue()

            def send_to_admin(self, admin_id, command):
                """Send command to specific admin."""
                if admin_id in self.admin_connections:
                    self.admin_connections[admin_id].put(command)
                    return True
                return False

        router = AdminCommandRouter()
        router.add_admin('admin_001')
        router.add_admin('admin_002')

        # Send targeted command
        cmd1 = {'action': 'clear_cache', 'scope': 'patterns'}
        assert router.send_to_admin('admin_001', cmd1)
        
        # Verify only admin_001 received it
        messages_001 = []
        try:
            while True:
                messages_001.append(router.admin_connections['admin_001'].get_nowait())
        except:
            pass
        
        messages_002 = []
        try:
            while True:
                messages_002.append(router.admin_connections['admin_002'].get_nowait())
        except:
            pass
        
        assert len(messages_001) == 1
        assert len(messages_002) == 0
```

---

## Template 4: Admin Event Publishing to Redis

```python
@pytest.mark.integration
@pytest.mark.admin
class TestAdminEventPublishing:
    """Test publishing admin events to Redis."""

    def test_admin_action_published_to_redis(self, mock_redis):
        """Test that admin actions are published to Redis."""
        
        class AdminEventPublisher:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.admin_channel = 'admin:events'

            def publish_admin_action(self, admin_id, action):
                """Publish admin action to Redis."""
                import json
                event = {
                    'admin_id': admin_id,
                    'action': action,
                    'timestamp': time.time()
                }
                return self.redis.publish(self.admin_channel, json.dumps(event))

        # Create publisher with mock Redis
        publisher = AdminEventPublisher(mock_redis)
        
        # Publish action
        action = {
            'type': 'config_update',
            'component': 'websocket_broadcaster',
            'changes': {'max_connections': 1000}
        }
        
        publisher.publish_admin_action('admin_001', action)
        
        # Verify Redis publish was called
        mock_redis.publish.assert_called_once()
        
        # Verify channel
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == 'admin:events'

    def test_admin_audit_log_to_redis(self, mock_redis):
        """Test that admin actions are logged to audit Redis."""
        
        class AdminAuditLogger:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.audit_key = 'admin:audit_log'

            def log_action(self, admin_id, action, status='success'):
                """Log admin action."""
                import json
                log_entry = {
                    'admin_id': admin_id,
                    'action': action,
                    'status': status,
                    'timestamp': time.time()
                }
                return self.redis.lpush(self.audit_key, json.dumps(log_entry))

        logger = AdminAuditLogger(mock_redis)
        
        # Log action
        logger.log_action('admin_001', 'restart_service', status='success')
        
        # Verify lpush was called
        mock_redis.lpush.assert_called_once()
        assert mock_redis.lpush.call_args[0][0] == 'admin:audit_log'
```

---

## Template 5: Admin WebSocket Resilience Test

```python
@pytest.mark.websocket
@pytest.mark.integration
class TestAdminWebSocketResilience:
    """Test WebSocket resilience for admin connections."""

    def test_admin_reconnection_after_disconnect(self):
        """Test admin reconnection handling."""
        
        class ResilientAdminWebSocket:
            def __init__(self):
                self.connected = False
                self.reconnect_attempts = 0
                self.max_reconnects = 5
                self.message_buffer = []

            def connect(self):
                """Connect to WebSocket."""
                self.connected = True
                self.reconnect_attempts = 0
                return True

            def disconnect(self):
                """Disconnect from WebSocket."""
                self.connected = False

            def handle_disconnect(self):
                """Handle disconnection with auto-reconnect."""
                recovery_start = time.perf_counter()
                self.disconnect()

                while not self.connected and self.reconnect_attempts < self.max_reconnects:
                    self.reconnect_attempts += 1
                    time.sleep(0.05 * self.reconnect_attempts)  # Exponential backoff
                    self.connect()

                recovery_end = time.perf_counter()
                return {
                    'recovered': self.connected,
                    'attempts': self.reconnect_attempts,
                    'recovery_time_ms': (recovery_end - recovery_start) * 1000
                }

        ws = ResilientAdminWebSocket()
        
        # Initial connection
        assert ws.connect()
        
        # Simulate disconnect and recovery
        recovery_info = ws.handle_disconnect()
        
        assert recovery_info['recovered']
        assert recovery_info['attempts'] <= 5
        assert recovery_info['recovery_time_ms'] < 1000  # Should recover quickly

    def test_admin_message_buffering_during_disconnect(self):
        """Test that messages are buffered during admin disconnection."""
        from queue import Queue
        
        class AdminMessageBuffer:
            def __init__(self, max_buffer_size=100):
                self.connected = False
                self.message_buffer = Queue(maxsize=max_buffer_size)
                self.dropped_messages = 0

            def buffer_message(self, message):
                """Buffer message when disconnected."""
                try:
                    self.message_buffer.put_nowait(message)
                    return True
                except:
                    self.dropped_messages += 1
                    return False

            def get_buffered_messages(self, max_count=50):
                """Get buffered messages."""
                messages = []
                try:
                    while len(messages) < max_count:
                        msg = self.message_buffer.get_nowait()
                        messages.append(msg)
                except:
                    pass
                return messages

        buffer = AdminMessageBuffer(max_buffer_size=20)
        
        # Buffer messages while disconnected
        for i in range(15):
            assert buffer.buffer_message({'id': i, 'data': f'message_{i}'})
        
        # Verify buffered
        messages = buffer.get_buffered_messages()
        assert len(messages) == 15
        assert buffer.dropped_messages == 0
        
        # Test buffer overflow
        for i in range(15, 25):
            buffer.buffer_message({'id': i, 'data': f'message_{i}'})
        
        # Some should be dropped
        assert buffer.dropped_messages > 0
```

---

## Template 6: Admin API Response Performance Test

```python
@pytest.mark.performance
@pytest.mark.admin
class TestAdminAPIPerformance:
    """Test performance of admin API endpoints."""

    def test_admin_dashboard_api_latency(self, performance_timer):
        """Test admin dashboard API response latency."""
        
        class MockAdminAPI:
            def __init__(self):
                self.response_times = []

            def get_admin_stats(self):
                """Get admin dashboard statistics."""
                start = time.perf_counter()
                
                # Simulate API work
                data = {
                    'connected_users': 150,
                    'websocket_connections': 45,
                    'active_patterns': 320,
                    'redis_memory_mb': 256,
                    'uptime_hours': 72
                }
                
                end = time.perf_counter()
                response_time = (end - start) * 1000
                self.response_times.append(response_time)
                
                return data, response_time

        api = MockAdminAPI()
        
        # Make 10 requests
        performance_timer.start()
        for _ in range(10):
            data, response_time = api.get_admin_stats()
        performance_timer.stop()

        # Verify performance
        avg_response_time = sum(api.response_times) / len(api.response_times)
        max_response_time = max(api.response_times)

        # Performance targets
        assert avg_response_time < 50, f"Avg {avg_response_time}ms (target: <50ms)"
        assert max_response_time < 100, f"Max {max_response_time}ms (target: <100ms)"
        assert performance_timer.elapsed < 1000, f"Total {performance_timer.elapsed}ms"

    def test_admin_bulk_command_latency(self, performance_timer):
        """Test latency of bulk admin commands."""
        
        class AdminCommandExecutor:
            def __init__(self):
                self.command_times = []

            def execute_bulk_command(self, commands):
                """Execute multiple admin commands."""
                start = time.perf_counter()
                
                results = []
                for cmd in commands:
                    # Simulate command execution
                    results.append({'command': cmd, 'status': 'success'})
                
                end = time.perf_counter()
                exec_time = (end - start) * 1000
                self.command_times.append(exec_time)
                
                return results, exec_time

        executor = AdminCommandExecutor()
        
        # Create bulk commands
        commands = [
            {'action': 'clear_cache', 'type': 'patterns'},
            {'action': 'update_config', 'key': 'log_level', 'value': 'DEBUG'},
            {'action': 'restart_module', 'module': 'websocket'},
            {'action': 'dump_stats', 'component': 'redis'},
            {'action': 'health_check', 'endpoints': ['api', 'db', 'redis']}
        ]

        performance_timer.start()
        results, exec_time = executor.execute_bulk_command(commands)
        performance_timer.stop()

        assert len(results) == 5
        assert exec_time < 200, f"Bulk command took {exec_time}ms (target: <200ms)"
```

---

## Template 7: Admin Authorization Decorator Test

```python
@pytest.mark.admin
@pytest.mark.security
class TestAdminAuthorizationDecorator:
    """Test @require_admin decorator functionality."""

    def test_require_admin_decorator_blocks_non_admin(self, client, regular_user):
        """Test that @require_admin blocks non-admin users."""
        with client:
            # Login as regular user
            client.post('/login', data={
                'email': regular_user.email,
                'password': 'test_password'
            })
            
            # Try to access @require_admin endpoint
            response = client.get('/api/admin/stats')
            
            # Should be denied
            assert response.status_code in [403, 401, 302]

    def test_require_admin_decorator_allows_admin(self, client, admin_user):
        """Test that @require_admin allows admin users."""
        with client:
            # Login as admin
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'test_password'
            })
            
            # Access @require_admin endpoint
            response = client.get('/api/admin/stats')
            
            # Should be allowed
            assert response.status_code == 200

    def test_require_admin_with_specific_permissions(self, client, admin_user):
        """Test @require_admin with permission levels."""
        with client:
            # Login as admin with limited permissions
            admin_user.permissions = ['read_only']
            
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'test_password'
            })
            
            # Access read-only endpoint
            response = client.get('/api/admin/logs')
            assert response.status_code == 200
            
            # Access write endpoint (should fail)
            response = client.post('/api/admin/restart')
            assert response.status_code in [403, 401]
```

---

## How to Use These Templates

1. **Copy** the relevant template class
2. **Paste** into your test file (`tests/admin_dashboard/test_*.py`)
3. **Import** required modules at the top
4. **Adjust** data/endpoints to match your implementation
5. **Run** with `pytest -m admin` or specific test file

Example:
```bash
# Run all admin tests
pytest tests/admin_dashboard/ -v

# Run specific test class
pytest tests/admin_dashboard/test_websocket_connection.py::TestAdminDashboardWebSocket -v

# Run with markers
pytest -m "admin and not performance" -v
```

---

## Key Imports for All Templates

```python
import pytest
import time
import json
from unittest.mock import Mock, patch
from queue import Queue
from datetime import datetime

# Your app imports
from src.core.services.websocket_broadcaster import WebSocketBroadcaster
from src.infrastructure.database.models.base import User, db
```

