# Flask Patterns for TickStock

> Essential Flask patterns and gotchas specific to TickStockAppV2 architecture

## Quick Reference

| Pattern | When to Use | File Reference |
|---------|-------------|----------------|
| Flask Application Context | Accessing runtime state in routes | `src/api/streaming_routes.py:43-44` |
| Blueprint Registration | Creating new API endpoints | `src/api/rest/main.py` |
| SocketIO Event Handlers | WebSocket communication | `src/presentation/websocket/manager.py` |
| Authentication Decorators | Protecting endpoints | `src/utils/auth_decorators.py` |
| Error Handling | Consistent error responses | `src/api/rest/tier_patterns.py` |

---

## 1. Flask Application Context Pattern

### The Problem
Flask stores application state in `current_app` context at **RUNTIME**, not in module-level globals. This is the #1 source of confusion when adding features.

### The Pattern

```python
# ❌ WRONG: Module-level globals don't work in routes
from src.app import redis_client  # This will be None in routes!

@app.route('/health')
def health_check():
    # redis_client is None here - it was assigned in main() after import
    status = redis_client.ping()  # AttributeError!
```

```python
# ✅ CORRECT: Use Flask's current_app context
from flask import current_app

@app.route('/health')
def health_check():
    # Access runtime state via current_app
    redis_subscriber = getattr(current_app, 'redis_subscriber', None)
    current_redis_client = redis_subscriber.redis_client if redis_subscriber else None

    if current_redis_client:
        status = current_redis_client.ping()
    else:
        status = "Redis not configured"
```

### Working Example
**File**: `src/api/streaming_routes.py` (lines 43-44)

```python
@streaming_bp.route('/api/streaming/redis-status')
@login_required
def get_redis_status():
    """Get current Redis connection status."""
    # Pattern: Access app-level state via current_app
    redis_subscriber = getattr(current_app, 'redis_subscriber', None)
    current_redis_client = redis_subscriber.redis_client if redis_subscriber else None

    if not current_redis_client:
        return jsonify({
            'status': 'disconnected',
            'message': 'Redis client not initialized'
        }), 503

    # Use the client
    try:
        current_redis_client.ping()
        return jsonify({'status': 'connected'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
```

### Global Variable Declaration in main()

If `main()` assigns to module-level variables, you MUST declare them as global:

```python
# src/app.py - Module level
app = None
socketio = None
redis_client = None

def main():
    # ❌ WRONG: Creates LOCAL variables, module-level stays None
    app = Flask(__name__)
    socketio = SocketIO(app)
    redis_client = redis.Redis()

def main():
    # ✅ CORRECT: Declare as global before assignment
    global app, socketio, redis_client
    app = Flask(__name__)
    socketio = SocketIO(app)
    redis_client = redis.Redis()

    # Then attach to current_app for runtime access
    app.redis_client = redis_client
```

**File**: `src/app.py` (line 2102) - Check for complete global declaration

### When to Use
- ✅ Accessing Redis clients, database connections, or other app-level state
- ✅ Any route that needs runtime configuration
- ✅ Background services initialized in `main()`

### Common Gotchas
- ❌ Don't assume `from src.app import X` gives you runtime state
- ❌ Don't create new instances - reuse app-level singletons
- ✅ Always use `getattr(current_app, 'attr', None)` for safety
- ✅ Check for None before using (handle case where service not initialized)

---

## 2. Blueprint Registration Pattern

### The Pattern

```python
# Step 1: CREATE Blueprint file
# File: src/api/rest/my_feature.py

from flask import Blueprint, jsonify, request
from src.utils.auth_decorators import login_required

# Naming: {feature}_bp
my_feature_bp = Blueprint('my_feature', __name__)

@my_feature_bp.route('/api/my-feature/endpoint', methods=['GET'])
@login_required
def get_feature_data():
    """Feature endpoint with authentication."""
    return jsonify({"status": "success", "data": []})


# Step 2: REGISTER Blueprint in main.py
# File: src/api/rest/main.py

from src.api.rest.my_feature import my_feature_bp

def register_blueprints(app):
    """Register all Flask blueprints."""
    # ... existing blueprints
    app.register_blueprint(my_feature_bp)  # Add new blueprint
```

### Working Example
**File**: `src/api/rest/tier_patterns.py` - Blueprint structure
**File**: `src/api/rest/main.py` - Registration pattern

### When to Use
- ✅ Creating new REST API endpoints
- ✅ Organizing routes by feature area
- ✅ Separating concerns (authentication, patterns, streaming, etc.)

### Common Gotchas
- ❌ Don't forget to register in `main.py` (route won't exist!)
- ✅ Use `url_prefix='/api'` for consistent routing
- ✅ Keep blueprints focused (one feature area per blueprint)

---

## 3. SocketIO Event Handlers Pattern

### The Pattern

```python
# File: src/presentation/websocket/manager.py

from flask_socketio import emit, join_room, leave_room
from flask import request

@socketio.on('subscribe_patterns')
def handle_subscribe_patterns(data):
    """
    WebSocket event handler for pattern subscriptions.

    Client sends: {'symbol': 'AAPL'}
    Server response: Joins room and broadcasts pattern updates
    """
    symbol = data.get('symbol')
    session_id = request.sid  # SocketIO session ID

    if symbol:
        # Pattern: Room-based subscriptions for symbol filtering
        room = f"patterns:{symbol}"
        join_room(room)

        # Track subscription in database (optional)
        from src.core.services.websocket_subscription_manager import track_subscription
        track_subscription(session_id, symbol, 'patterns')

        # Confirm subscription
        emit('subscribed', {
            'symbol': symbol,
            'type': 'patterns',
            'message': f'Subscribed to {symbol} patterns'
        })


@socketio.on('disconnect')
def handle_disconnect():
    """Clean up subscriptions on disconnect."""
    session_id = request.sid
    # Remove all subscriptions for this session
    cleanup_subscriptions(session_id)
```

### Broadcasting Pattern

```python
# File: src/core/services/websocket_broadcaster.py

from flask_socketio import emit

def broadcast_pattern_detected(pattern_data: dict, symbol: str):
    """
    Broadcast pattern detection to subscribed clients.

    Args:
        pattern_data: Pattern detection event from Redis
        symbol: Stock symbol (for room routing)
    """
    room = f"patterns:{symbol}"

    message = {
        'type': 'pattern_detected',
        'timestamp': time.time(),
        'data': pattern_data
    }

    # broadcast=True sends to ALL clients in room
    emit('pattern_detected', message, room=room, broadcast=True)
```

### Working Example
**File**: `src/presentation/websocket/manager.py` - Event handlers
**File**: `src/core/services/websocket_broadcaster.py` - Broadcast patterns

### When to Use
- ✅ Real-time updates to browser clients
- ✅ Symbol-based filtering (room pattern)
- ✅ Bi-directional communication (client → server events)

### Common Gotchas
- ❌ Don't forget `broadcast=True` for multi-client delivery
- ❌ Don't block in event handlers (use async or background tasks)
- ✅ Always clean up rooms on disconnect
- ✅ Target: <100ms from Redis event to WebSocket delivery

---

## 4. Authentication Decorator Pattern

### The Pattern

```python
from src.utils.auth_decorators import login_required

# Public endpoint (no auth)
@app.route('/health')
def health_check():
    """Public health check - NO @login_required."""
    return jsonify({"status": "healthy"})


# Protected endpoint (requires auth)
@app.route('/api/patterns/<symbol>')
@login_required  # Must be logged in
def get_patterns(symbol: str):
    """Protected endpoint - requires authentication."""
    return jsonify({"patterns": []})


# Admin-only endpoint
@app.route('/api/admin/users')
@login_required
@admin_required  # Additional check for admin role
def get_users():
    """Admin-only endpoint."""
    return jsonify({"users": []})
```

### Working Example
**File**: `src/utils/auth_decorators.py` - Decorator definitions
**File**: `src/api/rest/tier_patterns.py` - Usage examples

### TickStock Auth Policy
**ALL endpoints require authentication EXCEPT**:
- `/health` (for monitoring systems - debated, but current policy requires auth)
- Static files (CSS, JS, images)

### When to Use
- ✅ Any endpoint that returns user-specific or sensitive data
- ✅ API endpoints that trigger processing jobs
- ✅ WebSocket event handlers (where applicable)

### Common Gotchas
- ❌ Don't remove `@login_required` without explicit security review
- ✅ Place decorators in correct order: `@route` → `@login_required` → `@admin_required`
- ✅ Health checks: Current policy requires auth (external monitoring not primary use case)

---

## 5. Error Handling Pattern

### The Pattern

```python
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

@app.route('/api/feature/<param>')
@login_required
def feature_endpoint(param: str):
    """Feature endpoint with comprehensive error handling."""
    conn = None
    try:
        # Step 1: Input validation
        if not param or len(param) > 10:
            return jsonify({
                'status': 'error',
                'message': 'Invalid parameter length'
            }), 400  # Bad Request

        # Step 2: Database operation
        from src.infrastructure.database.connection_pool import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM table WHERE col = %s", (param,))
        results = cursor.fetchall()

        # Step 3: Success response
        return jsonify({
            'status': 'success',
            'data': results
        }), 200

    except ValueError as e:
        # Specific error: Bad input
        logger.warning(f"Invalid input in feature_endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Invalid input format'
        }), 400

    except DatabaseError as e:
        # Specific error: Database issue
        logger.error(f"Database error in feature_endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Database unavailable'
        }), 503  # Service Unavailable

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in feature_endpoint: {e}")
        logger.exception("Full traceback:")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

    finally:
        # Step 4: Resource cleanup (ALWAYS runs)
        if conn:
            conn.close()
```

### HTTP Status Code Standards

| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Successful request, data returned |
| 400 | Bad Request | Invalid input, validation failed |
| 401 | Unauthorized | Not logged in, missing auth |
| 403 | Forbidden | Logged in, but insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 500 | Internal Server Error | Unexpected server-side error |
| 503 | Service Unavailable | Database, Redis, or external service down |

### Working Example
**File**: `src/api/rest/tier_patterns.py` - Comprehensive error handling

### When to Use
- ✅ Every API endpoint (no exceptions)
- ✅ Database operations (always use try-finally for cleanup)
- ✅ External service calls (Redis, TickStockPL API)

### Common Gotchas
- ❌ Don't swallow exceptions silently (`except: pass`)
- ❌ Don't return 200 with `{"status": "error"}` in body
- ✅ Use specific exception types (ValueError, DatabaseError, etc.)
- ✅ Always close database connections in `finally` block
- ✅ Log with context (include parameter values for debugging)

---

## 6. Database Connection Pattern

### The Pattern

```python
from src.infrastructure.database.connection_pool import get_connection
from psycopg2.extras import RealDictCursor

@app.route('/api/data/<symbol>')
@login_required
def get_data(symbol: str):
    """Endpoint with proper database connection handling."""
    conn = None
    try:
        # Step 1: Get connection from pool
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)  # Returns dicts

        # Step 2: Parameterized query (prevent SQL injection)
        query = """
            SELECT col1, col2, col3
            FROM table_name
            WHERE symbol = %s
            ORDER BY created_at DESC
            LIMIT 100
        """
        cursor.execute(query, (symbol,))  # Tuple for parameters

        # Step 3: Fetch results
        results = cursor.fetchall()

        # Step 4: Convert to JSON-serializable format
        data = [dict(row) for row in results]

        return jsonify({'status': 'success', 'data': data}), 200

    except Exception as e:
        logger.error(f"Database error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        # CRITICAL: Always close connection
        if conn:
            conn.close()
```

### TickStock Database Constraints

**TickStockAppV2 is READ-ONLY for pattern data**:
- ✅ SELECT queries: Pattern data, indicator data (via Redis cache preferred)
- ✅ INSERT/UPDATE: user_sessions, ws_subscriptions, error_logs
- ❌ INSERT/UPDATE/DELETE: daily_patterns, indicators (belongs in TickStockPL)

**Performance Targets**:
- Database queries: <50ms
- Use explicit column lists (no `SELECT *`)
- Add indexes for common queries
- Use `EXPLAIN ANALYZE` to verify performance

### Working Example
**File**: `src/core/services/universe_service.py` - Service layer pattern

### When to Use
- ✅ Reading historical data for dashboards
- ✅ User session management
- ✅ WebSocket subscription tracking

### Common Gotchas
- ❌ Don't forget `cursor_factory=RealDictCursor` if you need dicts
- ❌ Don't use `SELECT *` (specify columns explicitly)
- ✅ Always use parameterized queries (%s placeholders)
- ✅ Close connections in finally block (prevents connection leaks)
- ✅ Target: <50ms query time (use EXPLAIN ANALYZE)

---

## 7. Configuration Access Pattern

### The Pattern

```python
from src.core.services.config_manager import get_config

@app.route('/api/feature')
@login_required
def feature_endpoint():
    """Endpoint using application configuration."""
    config = get_config()

    # Access config values
    redis_url = config.get('REDIS_URL')
    log_level = config.get('LOG_LEVEL', 'INFO')  # Default value
    feature_enabled = config.get('FEATURE_ENABLED', False)

    if not feature_enabled:
        return jsonify({'status': 'error', 'message': 'Feature disabled'}), 403

    # Use config...
    return jsonify({'status': 'success'})
```

### Environment Variables Pattern

```python
# .env file
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=DEBUG
FEATURE_TIMEOUT=30
TICKSTOCKPL_API_URL=http://localhost:8080

# Access in code
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file

redis_url = os.getenv('REDIS_URL')
api_url = os.getenv('TICKSTOCKPL_API_URL', 'http://localhost:8080')
```

### Working Example
**File**: `src/core/services/config_manager.py` - Configuration service
**File**: `.env` - Environment variables

### When to Use
- ✅ Any value that changes between environments (dev, prod)
- ✅ Feature flags, timeouts, URLs
- ✅ Credentials (but NEVER commit to git)

### Common Gotchas
- ❌ Don't hardcode URLs, timeouts, or environment-specific values
- ❌ Don't commit `.env` to version control (use `.env.example`)
- ✅ Use `get_config()` for runtime access
- ✅ Provide sensible defaults for optional config

---

## Cross-Reference Guide

### "I need to add a new..."

| Task | Patterns to Use | Files to Reference |
|------|-----------------|-------------------|
| REST API endpoint | Blueprint Registration (#2), Authentication (#4), Error Handling (#5) | `src/api/rest/tier_patterns.py` |
| WebSocket event | SocketIO Handlers (#3), Flask Context (#1) | `src/presentation/websocket/manager.py` |
| Background service | Flask Context (#1), Global Variables (#1) | `src/app.py:2102` |
| Database query | Database Connection (#6), Error Handling (#5) | `src/core/services/universe_service.py` |
| Health check | Flask Context (#1), Error Handling (#5) | `src/app.py:527-574` (Sprint 44) |
| Feature flag | Configuration Access (#7) | `src/core/services/config_manager.py` |

### "I'm seeing this error..."

| Error | Likely Cause | Pattern to Use |
|-------|--------------|----------------|
| `AttributeError: 'NoneType' has no attribute 'ping'` | Module-level global is None | Flask Context (#1) |
| `404 Not Found` on new endpoint | Blueprint not registered | Blueprint Registration (#2) |
| `401 Unauthorized` on health check | `@login_required` on public endpoint | Authentication (#4) |
| `psycopg2.InterfaceError: connection already closed` | Connection not properly managed | Database Connection (#6) |
| WebSocket not broadcasting | Missing `broadcast=True` | SocketIO Handlers (#3) |

---

## Testing Patterns

### Flask Test Client Pattern

```python
# tests/integration/test_my_feature.py

import pytest
from unittest.mock import Mock, patch

class TestMyFeature:
    """Integration tests for my feature."""

    @pytest.fixture
    def client(self, app):
        """Flask test client."""
        return app.test_client()

    def test_endpoint_authenticated(self, client, auth_headers):
        """Test endpoint requires authentication."""
        # Without auth
        response = client.get('/api/my-feature/data')
        assert response.status_code == 401

        # With auth
        response = client.get('/api/my-feature/data', headers=auth_headers)
        assert response.status_code == 200

    def test_endpoint_with_mock_redis(self, client, auth_headers):
        """Test endpoint with mocked Redis."""
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.ping.return_value = True

        with patch('src.app.redis_client', mock_redis):
            response = client.get('/api/my-feature/status', headers=auth_headers)
            assert response.status_code == 200
            assert response.json['redis_status'] == 'connected'
```

**File**: `tests/integration/test_health_endpoint.py` - Test patterns

---

## Performance Best Practices

### Response Time Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Health check | <50ms | `time curl http://localhost:5000/health` |
| API endpoint | <100ms | Browser DevTools Network tab |
| Database query | <50ms | `EXPLAIN ANALYZE` in psql |
| WebSocket delivery | <100ms | Redis event → browser delivery |

### Optimization Patterns

```python
# ❌ N+1 query problem (slow)
results = []
for symbol in symbols:
    conn = get_connection()
    cursor.execute("SELECT * FROM table WHERE symbol = %s", (symbol,))
    results.append(cursor.fetchone())
    conn.close()

# ✅ Batch query (fast)
conn = get_connection()
placeholders = ','.join(['%s'] * len(symbols))
cursor.execute(f"SELECT * FROM table WHERE symbol IN ({placeholders})", symbols)
results = cursor.fetchall()
conn.close()
```

---

## Summary Checklist

When adding a new Flask feature, use this checklist:

- [ ] Used Flask `current_app` context for runtime state (#1)
- [ ] Registered Blueprint in `main.py` (#2)
- [ ] Added `@login_required` decorator (unless public endpoint) (#4)
- [ ] Implemented proper error handling with try-except-finally (#5)
- [ ] Closed database connections in finally block (#6)
- [ ] Used parameterized queries (no SQL injection) (#6)
- [ ] Returned correct HTTP status codes (200, 400, 500, 503) (#5)
- [ ] Logged errors with context (#5)
- [ ] Tested with Flask test client (#Testing)
- [ ] Verified performance targets met (<50ms, <100ms) (#Performance)
