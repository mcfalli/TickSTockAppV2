# WebSocket Admin Dashboard - Test Patterns Guide

This guide documents the key test patterns used in the TickStock test suite that you should follow when testing the WebSocket admin dashboard.

---

## 1. WebSocket Test Pattern Examples

### Basic WebSocket Connection Test

**Source**: `tests/web_interface/sprint12/test_websocket_updates.py`

```python
@pytest.mark.websocket
@pytest.mark.unit
class TestWebSocketEventHandlers:
    """Test WebSocket event handling for dashboard updates."""

    def test_websocket_connection_handling(self, mock_websocket):
        """Test WebSocket connection state management."""

        class MockWebSocketHandler:
            def __init__(self):
                self.connected = False
                self.reconnect_attempts = 0
                self.max_reconnect_attempts = 3
                self.event_handlers = {}

            def connect(self):
                self.connected = True
                return True

            def disconnect(self):
                self.connected = False

            def on(self, event, handler):
                """Register event handler"""
                if event not in self.event_handlers:
                    self.event_handlers[event] = []
                self.event_handlers[event].append(handler)

            def emit(self, event, data):
                """Emit event if connected"""
                if not self.connected:
                    return False
                return True

        ws_handler = MockWebSocketHandler()

        # Test initial connection
        assert not ws_handler.connected
        ws_handler.connect()
        assert ws_handler.connected

        # Test event handler registration
        def price_handler(data):
            return f"Price update: {data}"

        ws_handler.on('price_update', price_handler)
        assert 'price_update' in ws_handler.event_handlers
        assert len(ws_handler.event_handlers['price_update']) == 1

        # Test event emission when connected
        assert ws_handler.emit('price_update', {'symbol': 'AAPL', 'price': 175.50})

        # Test disconnection
        ws_handler.disconnect()
        assert not ws_handler.connected
        assert not ws_handler.emit('price_update', {})
```

**Key Pattern**:
- Use Mock objects from `unittest.mock`
- Track connection state with boolean flags
- Test handler registration with event dictionaries
- Verify emit returns False when disconnected

### WebSocket Message Broadcasting Test

**Source**: `tests/web_interface/sprint12/test_websocket_updates.py`

```python
def test_concurrent_websocket_connections_performance(self, performance_timer):
    """Test performance with multiple concurrent WebSocket connections."""

    class MockConnectionManager:
        def __init__(self):
            self.connections = {}
            self.message_counts = {}

        def add_connection(self, connection_id):
            self.connections[connection_id] = {
                'connected': True,
                'subscriptions': set(),
                'message_queue': Queue()
            }
            self.message_counts[connection_id] = 0

        def broadcast_message(self, message):
            broadcast_start = time.perf_counter()

            for conn_id, conn in self.connections.items():
                if conn['connected']:
                    conn['message_queue'].put(message)
                    self.message_counts[conn_id] += 1

            broadcast_end = time.perf_counter()
            return (broadcast_end - broadcast_start) * 1000

    conn_manager = MockConnectionManager()

    # Add multiple connections
    num_connections = 100
    for i in range(num_connections):
        conn_manager.add_connection(f"conn_{i}")

    # Broadcast message and verify
    test_message = {
        'type': 'admin_command',
        'action': 'update_config'
    }

    performance_timer.start()
    for _ in range(10):
        broadcast_time = conn_manager.broadcast_message(test_message)
    performance_timer.stop()

    # Verify all connections received messages
    for conn_id in conn_manager.message_counts:
        assert conn_manager.message_counts[conn_id] == 10
```

**Key Pattern**:
- Use `Queue()` from queue module for message buffering
- Track message delivery to each connection
- Measure performance with `time.perf_counter()`
- Verify broadcast to all connected clients

---

## 2. Admin Route Authentication & Authorization Tests

### Admin User Permission Test

**Source**: `tests/sprint15/test_admin_menu.py`

```python
class TestAdminMenuFunctionality:
    """Test suite for admin dropdown menu functionality."""

    def test_admin_menu_visible_for_admin_user(self, client, admin_user):
        """Test that admin menu is visible for users with admin role."""
        # Login as admin
        with client:
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'test_password'
            })

            # Get dashboard page
            response = client.get('/')
            assert response.status_code == 200

            # Check for admin menu elements
            assert b'Admin' in response.data
            assert b'adminMenuBtn' in response.data
            assert b'Historical Data' in response.data

    def test_admin_menu_hidden_for_regular_user(self, client, regular_user):
        """Test that admin menu is hidden for regular users."""
        with client:
            client.post('/login', data={
                'email': regular_user.email,
                'password': 'test_password'
            })

            response = client.get('/')
            assert response.status_code == 200
            
            # Verify menu NOT present
            assert b'adminMenuBtn' not in response.data
            assert b'admin-menu' not in response.data
```

### Admin Route Access Control Test

```python
class TestAdminRouteAccess:
    """Test suite for admin route access permissions."""

    def test_admin_can_access_admin_routes(self, client, admin_user):
        """Test that admin users can access admin routes."""
        with client:
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'test_password'
            })

            response = client.get('/admin/dashboard')
            assert response.status_code in [200, 302]

    def test_regular_user_cannot_access_admin_routes(self, client, regular_user):
        """Test that regular users cannot access admin routes."""
        with client:
            client.post('/login', data={
                'email': regular_user.email,
                'password': 'test_password'
            })

            # Try to access admin route - should fail
            response = client.get('/admin/dashboard')
            assert response.status_code in [403, 302]  # Forbidden or redirect
```

**Key Pattern**:
- Use Flask test client's `with client:` context
- Login before accessing protected routes
- Check response status codes (200, 403, 302)
- Verify HTML content NOT present for unauthorized users

### User Fixtures for Admin Testing

```python
@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
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
def regular_user(app):
    """Create a regular user for testing."""
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

**Key Pattern**:
- Create fixtures with `app.app_context()` for database access
- Set different roles for permission testing
- Use consistent test data (emails, passwords)

---

## 3. Integration Test Structure

### Redis Message Publishing for WebSocket

**Source**: `tests/integration/test_websocket_patterns.py`

```python
def test_websocket_pattern_integration():
    """Test the complete pattern event flow: Redis -> WebSocket -> Frontend"""
    
    # Connect to Redis
    config_manager = ConfigManager()
    redis_url = config_manager.config.get('REDIS_URL', 'redis://localhost:6379/0')
    redis_client = redis.Redis.from_url(redis_url, decode_responses=False)
    
    # Verify connection
    redis_client.ping()
    
    # Create test event
    test_pattern_event = {
        "source": "TickStockPL-Test",
        "timestamp": time.time(),
        "pattern": "BreakoutBO",
        "symbol": "AAPL",
        "confidence": 0.95,
        "tier": "daily",
        "price_at_detection": 150.25,
        "metadata": {
            "test": True,
            "description": "Test pattern event"
        }
    }
    
    # Publish to Redis
    channel = 'tickstock.events.patterns'
    message = json.dumps(test_pattern_event)
    redis_client.publish(channel, message)
    
    print(f"SUCCESS: Pattern event published to {channel}")
```

**Key Pattern**:
- Create ConfigManager and get Redis URL from config
- Use `redis.Redis.from_url()` for connection
- Call `redis_client.ping()` to verify connection
- Publish JSON-serialized events to channels
- Use consistent channel names

### Integration Test Environment Setup

**Source**: `tests/integration/sprint_14_phase2/conftest.py`

```python
@pytest.fixture(scope="session")
def integration_test_env():
    """Session-scoped integration test environment"""
    
    env = IntegrationTestEnvironment()

    # Setup Redis connection
    try:
        env.redis_client = redis.Redis(
            host=TEST_REDIS_HOST,
            port=TEST_REDIS_PORT,
            db=TEST_REDIS_DB,  # Separate test DB
            decode_responses=True,
            socket_timeout=5.0
        )
        env.redis_client.ping()
        print(f"✓ Redis connected: {TEST_REDIS_HOST}:{TEST_REDIS_PORT}/{TEST_REDIS_DB}")
    except Exception as e:
        pytest.skip(f"Redis connection failed: {e}")

    yield env

    # Cleanup
    if env.redis_client:
        try:
            env.redis_client.flushdb()  # Clean test data
            env.redis_client.close()
        except:
            pass

@pytest.fixture(scope="function")
def clean_redis(integration_test_env):
    """Function-scoped Redis cleanup"""
    # Clear test database before test
    integration_test_env.redis_client.flushdb()
    
    yield integration_test_env.redis_client
    
    # Clear test database after test
    try:
        integration_test_env.redis_client.flushdb()
    except:
        pass
```

**Key Pattern**:
- Use session-scoped fixture for environment setup
- Use function-scoped fixture for cleanup
- Call `flushdb()` to clean test data between tests
- Skip tests if connections fail
- Use separate test databases (db=15)

---

## 4. Redis Mocking Patterns

### Mock Redis Connection (conftest.py)

**Source**: `tests/conftest.py`

```python
@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing"""
    redis_mock = Mock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = False
    redis_mock.expire.return_value = True
    return redis_mock
```

**Key Pattern**:
- Use `Mock()` from `unittest.mock`
- Configure return values for common methods
- Mock pub/sub methods separately if needed

### Real Redis for Integration Tests

For integration tests that need real Redis:

```python
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=15,  # Test database
    decode_responses=True
)

# Subscribe to channel
pubsub = redis_client.pubsub()
pubsub.subscribe('admin:commands')

# Receive messages
for message in pubsub.listen():
    if message['type'] == 'message':
        print(f"Received: {message['data']}")
```

**Key Pattern**:
- Use separate Redis database (db=15) for testing
- Use `decode_responses=True` for string handling
- Use pubsub for event testing
- Call `flushdb()` after tests to cleanup

---

## 5. Performance Testing Pattern

### WebSocket Latency Measurement

**Source**: `tests/web_interface/sprint12/test_websocket_updates.py`

```python
def test_high_frequency_updates_performance(self, performance_timer):
    """Test performance under high-frequency updates."""

    class MockHighFrequencyHandler:
        def __init__(self):
            self.update_count = 0
            self.processing_times = []

        def handle_price_stream(self, updates_per_second=100, duration_seconds=1):
            total_updates = updates_per_second * duration_seconds
            start_time = time.perf_counter()

            for i in range(total_updates):
                update_start = time.perf_counter()
                
                # Simulate update
                symbol = f"SYM{i % 10}"
                self.price_data[symbol] = {'price': 100.0 + i}
                self.update_count += 1

                update_end = time.perf_counter()
                self.processing_times.append((update_end - update_start) * 1000)

                if i < total_updates - 1:
                    time.sleep(1.0 / updates_per_second)

            end_time = time.perf_counter()
            return (end_time - start_time) * 1000

    handler = MockHighFrequencyHandler()
    
    performance_timer.start()
    total_time = handler.handle_price_stream(updates_per_second=50, duration_seconds=2)
    performance_timer.stop()

    # Performance assertions
    avg_processing_time = sum(handler.processing_times) / len(handler.processing_times)
    max_processing_time = max(handler.processing_times)

    assert avg_processing_time < 5, f"Avg processing time {avg_processing_time}ms too slow"
    assert max_processing_time < 20, f"Max processing time {max_processing_time}ms too slow"
```

**Key Pattern**:
- Use `time.perf_counter()` for nanosecond precision
- Convert to milliseconds with `* 1000`
- Track individual operation times
- Calculate avg, max, percentile metrics
- Compare against performance targets

---

## 6. Fixture Reference

### Available Fixtures in conftest.py

```python
@pytest.fixture
def app():
    """Create Flask application for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app

@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()

@pytest.fixture
def mock_websocket():
    """Mock WebSocket client for testing."""
    socket = Mock()
    socket.emit = Mock()
    socket.on = Mock()
    socket.connected = True
    return socket

@pytest.fixture
def performance_timer():
    """Timer utility for performance tests."""
    class Timer:
        def start(self):
            self.start_time = time.perf_counter()
        def stop(self):
            self.end_time = time.perf_counter()
        @property
        def elapsed(self) -> float:
            return (self.end_time - self.start_time) * 1000
    return Timer()

@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing."""
    redis_mock = Mock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    return redis_mock
```

---

## 7. Test Markers for Organization

Add markers to organize tests:

```python
@pytest.mark.websocket        # WebSocket functionality tests
@pytest.mark.admin            # Admin-specific tests
@pytest.mark.integration      # Integration tests (needs services)
@pytest.mark.unit             # Unit tests (isolated)
@pytest.mark.performance      # Performance/load tests
@pytest.mark.security         # Security/auth tests
```

Example usage:
```python
@pytest.mark.websocket
@pytest.mark.integration
def test_admin_dashboard_websocket():
    """Test WebSocket for admin dashboard."""
    pass

# Run specific tests:
# pytest -m websocket          # Only WebSocket tests
# pytest -m "admin and not performance"  # Admin but not performance
```

---

## 8. Recommended Test Organization for Admin Dashboard

```
tests/
├── admin_dashboard/
│   ├── conftest.py                      # Admin-specific fixtures
│   ├── test_websocket_connection.py     # Connection lifecycle
│   ├── test_websocket_messaging.py      # Message handling
│   ├── test_admin_auth.py               # Authentication
│   ├── test_admin_authorization.py      # Role-based access
│   ├── test_admin_performance.py        # Latency targets
│   └── test_admin_integration.py        # End-to-end flows
```

---

## Summary Checklist

When testing the WebSocket admin dashboard:

- [ ] Use Mock from `unittest.mock` for isolated tests
- [ ] Use real Redis (db=15) for integration tests
- [ ] Test connection state with boolean flags
- [ ] Test event handlers with registration pattern
- [ ] Test broadcasting to multiple connections
- [ ] Create admin/regular user fixtures
- [ ] Test admin routes with 403/302 assertions
- [ ] Measure performance with `time.perf_counter()`
- [ ] Use pytest markers (@pytest.mark.websocket, etc.)
- [ ] Cleanup Redis with `flushdb()` after tests
- [ ] Follow performance targets (<100ms WebSocket latency)

