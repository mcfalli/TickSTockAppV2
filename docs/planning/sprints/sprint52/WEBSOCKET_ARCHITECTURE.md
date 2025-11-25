# Flask-SocketIO Architecture - TickStockAppV2

## Executive Summary

TickStockAppV2 implements a **three-tier WebSocket architecture** using Flask-SocketIO with Redis integration for real-time browser communication. The system supports 500+ concurrent users with <100ms delivery latency through batching, rate limiting, and intelligent event routing.

---

## 1. SocketIO Initialization

### Configuration
**File**: `C:\Users\McDude\TickStockAppV2\config\app_config.py` (lines 138-175)

```python
def initialize_socketio(app, cache_control, config):
    """Initialize SocketIO with Redis configuration."""
    
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',           # Greenlet-based async for performance
        ping_timeout=60,                 # 60-second client timeout
        ping_interval=10,                # 10-second ping interval
        max_http_buffer_size=5*1024*1024,  # 5MB max message size
        message_queue=redis_url if use_redis else None  # Optional Redis queue
    )
    return socketio
```

### Key Configuration Details
- **async_mode**: 'eventlet' (greenlet-based, requires monkey patching in app.py line 14)
- **CORS**: Allows all origins (`cors_allowed_origins="*"`)
- **Message Queue**: Uses Redis if available, falls back to in-memory
- **Connection Monitoring**: Ping/pong every 10 seconds, timeout after 60 seconds

### Monkey Patching (Critical!)
**File**: `C:\Users\McDude\TickStockAppV2\src\app.py` (lines 13-22)

```python
# CRITICAL: eventlet monkey patch must be FIRST before any other imports
import eventlet

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=True,
    time=True
)
```

---

## 2. Event Handlers

### Core Event Handlers
**File**: `C:\Users\McDude\TickStockAppV2\src\app.py` (lines 382-490)

#### 2.1 Connection Management

```python
@socketio.on('connect')
def handle_connect():
    """Handle client connection with user authentication."""
    logger.info("CLIENT-CONNECT: User connected")
    if hasattr(market_service, 'websocket_publisher'):
        user_id = getattr(current_user, 'id', 'anonymous')
        market_service.websocket_publisher.add_user(user_id, request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("CLIENT-DISCONNECT: User disconnected")
    if hasattr(market_service, 'websocket_publisher'):
        user_id = getattr(current_user, 'id', 'anonymous')
        market_service.websocket_publisher.remove_user(user_id)
```

**Context**: 
- `request.sid` = SocketIO session ID (unique per connection)
- `current_user.id` = Flask-Login authenticated user ID
- WebSocket publisher tracks users for subscription management

#### 2.2 Ticker Subscriptions

```python
@socketio.on('subscribe_tickers')
def handle_subscribe_tickers(data):
    """Handle ticker subscription requests."""
    try:
        tickers = data.get('tickers', [])  # List of symbols like ['AAPL', 'TSLA']
        user_id = getattr(current_user, 'id', 'anonymous')

        if hasattr(market_service, 'websocket_publisher'):
            market_service.websocket_publisher.update_user_subscriptions(user_id, tickers)
            emit('subscription_updated', {'tickers': tickers})
            logger.info(f"USER-SUBSCRIPTION: Updated for {user_id}: {len(tickers)} tickers")
    except Exception as e:
        logger.error(f"SUBSCRIPTION-ERROR: {e}")
        emit('error', {'message': 'Subscription failed'})
```

**Pattern**: Client sends list of tickers, server updates user's subscription set

#### 2.3 TickStockPL Integration

```python
@socketio.on('subscribe_tickstockpl_watchlist')
def handle_subscribe_watchlist(data):
    """Handle watchlist subscription for TickStockPL updates."""
    try:
        symbols = data.get('symbols', [])
        user_id = data.get('user_id') or getattr(current_user, 'id', 'anonymous')
        subscription_types = data.get('subscription_types', ['price_update', 'pattern_alert'])

        if hasattr(market_service, 'market_data_subscriber'):
            market_service.market_data_subscriber.subscribe_user_to_symbols(
                user_id, symbols, subscription_types
            )
            emit('tickstockpl_subscription_confirmed', {
                'symbols': symbols,
                'types': subscription_types
            })
```

#### 2.4 Unsubscription

```python
@socketio.on('unsubscribe_tickstockpl_symbol')
def handle_unsubscribe_symbol(data):
    """Handle unsubscription from specific symbol."""
    symbol = data.get('symbol')
    user_id = data.get('user_id') or getattr(current_user, 'id', 'anonymous')

    if hasattr(market_service, 'market_data_subscriber'):
        market_service.market_data_subscriber.unsubscribe_user_from_symbol(user_id, symbol)
        emit('tickstockpl_unsubscription_confirmed', {'symbol': symbol})
```

#### 2.5 Chart Data Requests

```python
@socketio.on('request_tickstockpl_chart_data')
def handle_chart_data_request(data):
    """Handle chart data requests via WebSocket."""
    symbol = data.get('symbol')
    timeframe = data.get('timeframe', '1d')  # '1m', '5m', '1h', '1d', etc.
    
    if hasattr(market_service, 'market_data_subscriber'):
        chart_data = market_service.market_data_subscriber.get_historical_data(symbol, timeframe)
        
        emit('tickstockpl_chart_data_response', {
            'symbol': symbol,
            'timeframe': timeframe,
            'chart_data': chart_data
        })
```

---

## 3. Room Management

### Room Naming Convention
```
user_{user_id}  - User-specific delivery room
system_health_room  - System-wide health updates
backtest_results_room  - Backtest completion notifications
```

### Room Operations (via SocketIO Server)

**File**: `C:\Users\McDude\TickStockAppV2\src\core\services\websocket_subscription_manager.py` (lines 181-184)

```python
# Join user to their room
self.socketio.server.enter_room(connection_id, room_name)

# Remove user from room
self.socketio.server.leave_room(connection_id, room_name)
```

### Room-Specific Broadcasting

**File**: `C:\Users\McDude\TickStockAppV2\src\core\services\websocket_broadcaster.py` (line 252)

```python
def broadcast_pattern_alert(self, pattern_event: dict[str, Any]):
    """Broadcast pattern alert to subscribed users."""
    # Find subscribed users
    target_sessions = []
    for session_id, connected_user in self.connected_users.items():
        if pattern_name in connected_user.subscriptions:
            target_sessions.append(session_id)
    
    # Emit to target sessions (rooms)
    for session_id in target_sessions:
        self.socketio.emit('pattern_alert', websocket_message, room=session_id)
        self.stats['messages_sent'] += 1
```

---

## 4. Broadcasting Patterns

### 4.1 Direct User Emission (Simple)
**File**: `C:\Users\McDude\TickStockAppV2\src\presentation\websocket\publisher.py` (lines 182-188)

```python
def _emit_to_user(self, user_id: str, event: str, data: dict[str, Any]):
    """Emit data to a specific user."""
    try:
        self.socketio.emit(event, data, room=user_id)
        logger.debug(f"WEBSOCKET-PUBLISHER: Emitted {event} to user {user_id}")
    except Exception as e:
        logger.error(f"WEBSOCKET-PUBLISHER: Error emitting to user {user_id}: {e}")
```

### 4.2 Global Broadcast (All Connected Users)
**File**: `C:\Users\McDude\TickStockAppV2\src\presentation\websocket\publisher.py` (lines 251-257)

```python
def broadcast_message(self, event: str, data: dict[str, Any]):
    """Broadcast a message to all connected users."""
    try:
        self.socketio.emit(event, data, broadcast=True)
        logger.info(f"WEBSOCKET-PUBLISHER: Broadcasted {event} to all users")
    except Exception as e:
        logger.error(f"WEBSOCKET-PUBLISHER: Error broadcasting: {e}")
```

### 4.3 Filtered Broadcast (Subscribed Users Only)
**File**: `C:\Users\McDude\TickStockAppV2\src\core\services\websocket_broadcaster.py` (lines 201-266)

```python
def broadcast_pattern_alert(self, pattern_event: dict[str, Any]):
    """Broadcast pattern alert to subscribed users only."""
    pattern_name = pattern_event.get('data', {}).get('pattern')
    
    # Find subscribed users
    target_sessions = []
    for session_id, connected_user in self.connected_users.items():
        if not connected_user.subscriptions or pattern_name in connected_user.subscriptions:
            target_sessions.append(session_id)
    
    # Broadcast to target sessions
    for session_id in target_sessions:
        self.socketio.emit('pattern_alert', websocket_message, room=session_id)
```

### 4.4 Batched Broadcasting (High Performance)
**File**: `C:\Users\McDude\TickStockAppV2\src\infrastructure\websocket\scalable_broadcaster.py` (lines 141-702)

```python
class ScalableBroadcaster:
    """
    High-performance WebSocket broadcasting with:
    - Event batching (100ms window default)
    - Per-user rate limiting (100 events/sec)
    - Priority-based delivery
    - <100ms delivery latency
    """

    def broadcast_to_users(self, event_type: str, event_data: dict,
                          user_ids: set[str], 
                          priority: DeliveryPriority = DeliveryPriority.MEDIUM) -> int:
        """Queue event for batched delivery to specific users."""
        # Creates EventMessage, applies rate limiting, queues for delivery
        # Returns count of users queued for delivery
        
    def broadcast_to_room(self, room_name: str, event_type: str, 
                         event_data: dict) -> bool:
        """Broadcast directly to room with batching."""
```

**Batching Example**:
```python
# Multiple events queued within 100ms window
broadcast_to_users('tick_data', {'price': 150.25}, {'user_1', 'user_2'})
broadcast_to_users('alert', {'symbol': 'AAPL'}, {'user_1'})

# Batched together and delivered in single message
# Message structure:
{
    'type': 'event_batch',
    'batch_id': 'tick_data_user_1_1234567890',
    'events': [
        {'type': 'tick_data', 'data': {...}, 'priority': 'medium'},
        {'type': 'alert', 'data': {...}, 'priority': 'medium'}
    ]
}
```

---

## 5. WebSocket Services Architecture

### 5.1 WebSocketManager (Connection Tracking)
**File**: `C:\Users\McDude\TickStockAppV2\src\presentation\websocket\manager.py`

```python
class WebSocketManager:
    """Simplified connection manager with user-to-connection mapping."""
    
    def register_user(self, user_id: str, client_id: str):
        """Register user with specific client connection."""
        self.user_connections[user_id].add(client_id)
        self.connection_users[client_id] = user_id
    
    def get_user_connections(self, user_id: str) -> set[str]:
        """Get all connection IDs for a user."""
        return self.user_connections.get(user_id, set()).copy()
    
    def is_user_connected(self, user_id: str) -> bool:
        """Check if user has active connections."""
        return user_id in self.user_connections
```

**Data Structure**:
```python
self.clients = {'sid1', 'sid2', 'sid3'}  # All connection IDs
self.user_connections = {
    'user_123': {'sid1', 'sid2'},  # Multiple connections per user (multi-tab)
    'user_456': {'sid3'}
}
self.connection_users = {
    'sid1': 'user_123',  # Reverse mapping
    'sid2': 'user_123',
    'sid3': 'user_456'
}
```

### 5.2 WebSocketBroadcaster (Event Broadcasting)
**File**: `C:\Users\McDude\TickStockAppV2\src\core\services\websocket_broadcaster.py`

```python
class WebSocketBroadcaster:
    """
    Enhanced broadcasting service with:
    - Pattern subscription management
    - Offline message queuing (100 message limit)
    - Backtest progress/result broadcasting
    - System health updates
    - Connection heartbeat monitoring
    """
    
    def broadcast_pattern_alert(self, pattern_event: dict):
        """Broadcast to users subscribed to specific pattern."""
    
    def broadcast_backtest_progress(self, progress_event: dict):
        """Broadcast to all users."""
    
    def broadcast_system_health(self, health_event: dict):
        """Broadcast to all users."""
    
    def queue_message_for_offline_user(self, user_id: str, message: dict):
        """Queue messages for users that disconnect (max 100 per user)."""
    
    def cleanup_stale_connections(self, max_idle_seconds: int = 300):
        """Remove idle connections (5 minutes default)."""
```

**Connection Data**:
```python
@dataclass
class ConnectedUser:
    user_id: str
    session_id: str
    connected_at: float
    last_seen: float
    subscriptions: set[str]  # Pattern subscriptions
```

### 5.3 UniversalWebSocketManager (Subscription Routing)
**File**: `C:\Users\McDude\TickStockAppV2\src\core\services\websocket_subscription_manager.py` (lines 76-717)

```python
class UniversalWebSocketManager:
    """
    Core manager for all TickStockAppV2 features with:
    - Multi-feature subscription types
    - High-performance indexing (O(log n) lookups)
    - Scalable broadcasting (100ms batching)
    - Intelligent event routing
    - Performance optimization
    """
    
    def subscribe_user(self, user_id: str, subscription_type: str, 
                      filters: dict) -> bool:
        """Subscribe user to feature with filters."""
        # Examples:
        # - 'tier_patterns': {'pattern_types': ['BreakoutBO'], 'symbols': ['AAPL']}
        # - 'market_insights': {'tiers': ['daily', 'intraday']}
        # - 'backtest': {'job_ids': ['job_123']}
    
    def broadcast_event(self, event_type: str, event_data: dict,
                       targeting_criteria: dict) -> int:
        """Broadcast to subscribed users with intelligent routing."""
        # Uses SubscriptionIndexManager for O(log n) user filtering
        # Uses ScalableBroadcaster for batched delivery
        # Uses EventRouter for sophisticated routing rules
```

### 5.4 ScalableBroadcaster (High-Performance Delivery)
**File**: `C:\Users\McDude\TickStockAppV2\src\infrastructure\websocket\scalable_broadcaster.py` (lines 141-702)

**Batching System**:
```python
class ScalableBroadcaster:
    """
    Performance targets:
    - <100ms delivery latency (target)
    - 100 events/sec per user (rate limit)
    - 50 events per batch (max)
    - 100ms batch window (default)
    """
    
    # Pending batches per room
    self.pending_batches: dict[str, EventBatch] = {}
    
    # Timer for each room's batch
    self.batch_timers: dict[str, threading.Timer] = {}
    
    # Per-user rate limiters
    self.user_rate_limiters: dict[str, RateLimiter] = {}
```

**Batch Lifecycle**:
1. Event queued → added to batch for user's room
2. Timer starts (100ms)
3. More events added to batch
4. Timer expires → batch flushed
5. Batch delivered to room
6. Statistics recorded

---

## 6. Redis Integration

### Redis Event Subscriber
**File**: `C:\Users\McDude\TickStockAppV2\src\core\services\redis_event_subscriber.py`

```python
# Subscribes to TickStockPL events
self.redis_subscriber.subscribe('tickstock.all_ticks')

# Listens in background thread
for message in self.redis_subscriber.listen():
    if message['type'] == 'message':
        event_data = json.loads(message['data'])
        self._handle_tickstock_event(event_data)

# Emits to SocketIO
self.socketio.emit('pattern_alert', websocket_data, room=f'user_{user_id}')
```

### Redis Message Flow
```
TickStockPL (pattern detected)
    ↓
Redis pub-sub: tickstock.events.patterns
    ↓
RedisEventSubscriber (listening in thread)
    ↓
WebSocketBroadcaster.broadcast_pattern_alert()
    ↓
SocketIO.emit('pattern_alert', data, room='user_X')
    ↓
Browser Client (WebSocket)
```

---

## 7. Event Handler Diagram

```
Client Connect
    ↓
@socketio.on('connect')
    ├→ Get current_user.id from Flask-Login
    ├→ Track in WebSocketManager
    └→ Deliver queued messages

Client Subscribes to Tickers
    ↓
@socketio.on('subscribe_tickers')
    ├→ Get tickers list from client
    ├→ Update WebSocketPublisher.user_subscriptions
    ├→ Emit 'subscription_updated' back to client
    └→ Log subscription

TickStockPL Publishes Pattern
    ↓
Redis: tickstock.events.patterns
    ↓
RedisEventSubscriber (thread)
    ├→ Parse JSON event
    ├→ Find users subscribed to pattern
    ├→ Call WebSocketBroadcaster.broadcast_pattern_alert()
    └→ Queue in ScalableBroadcaster

ScalableBroadcaster Batches Events
    ├→ Group by user room
    ├→ Create EventBatch
    ├→ Start 100ms timer
    └→ On timer: flush_batch()

Batch Delivery
    ↓
SocketIO.emit('pattern_alert', data, room='user_123')
    ├→ Delivered to user_123's WebSocket session(s)
    ├→ Can reach multiple connections (multi-tab)
    └→ Track delivery stats

Client Disconnect
    ↓
@socketio.on('disconnect')
    ├→ Get current_user.id
    ├→ Remove from WebSocketManager
    ├→ Clear subscriptions
    └→ Queue messages if needed
```

---

## 8. Subscription Flow Example

### Client-Side (JavaScript)
```javascript
// Connect
io.on('connect', function() {
    console.log('Connected');
});

// Subscribe to tickers
socket.emit('subscribe_tickers', {
    tickers: ['AAPL', 'TSLA', 'NVDA']
});

// Listen for updates
socket.on('tick_data', function(data) {
    console.log('Received tick:', data);
});

// Listen for pattern alerts
socket.on('pattern_alert', function(data) {
    console.log('Pattern detected:', data.pattern, 'on', data.symbol);
});

// Disconnect
socket.on('disconnect', function() {
    console.log('Disconnected');
});
```

### Server-Side Flow
1. `@socketio.on('subscribe_tickers')` → updates subscriptions
2. `WebSocketPublisher.update_user_subscriptions(['AAPL', 'TSLA', 'NVDA'])` → stores
3. Client emits 'subscription_updated' confirmation
4. Redis delivers market data for subscribed tickers
5. `WebSocketPublisher._get_users_for_ticker('AAPL')` → finds subscribers
6. `SocketIO.emit('tick_data', data, room='user_123')` → delivers to user

---

## 9. Key Data Structures

### UserSubscription (WebSocket Model)
**File**: `C:\Users\McDude\TickStockAppV2\src\core\models\websocket_models.py`

```python
@dataclass
class UserSubscription:
    user_id: str                    # 'user_123'
    subscription_type: str          # 'tier_patterns', 'market_insights'
    filters: dict[str, Any]         # {'symbols': ['AAPL'], 'tiers': ['daily']}
    room_name: str                  # 'user_123'
    active: bool = True
    created_at: datetime
    last_activity: datetime
    
    def matches_criteria(self, criteria: dict) -> bool:
        """Check if event matches subscription filters."""
        # Example: subscription with filters {'symbols': ['AAPL']}
        # matches event criteria {'symbol': 'AAPL'}
```

### EventMessage (Batching)
**File**: `C:\Users\McDude\TickStockAppV2\src\infrastructure\websocket\scalable_broadcaster.py`

```python
@dataclass
class EventMessage:
    event_type: str              # 'pattern_alert', 'tick_data'
    event_data: dict[str, Any]   # Actual event payload
    target_users: set[str]       # User IDs to send to
    priority: DeliveryPriority   # LOW, MEDIUM, HIGH, CRITICAL
    timestamp: float
    message_id: str
    attempts: int = 0
    delivered_users: set[str] = field(default_factory=set)
    failed_users: set[str] = field(default_factory=set)
```

### EventBatch (Delivery Container)
**File**: `C:\Users\McDude\TickStockAppV2\src\infrastructure\websocket\scalable_broadcaster.py`

```python
@dataclass
class EventBatch:
    room_name: str                   # 'user_123'
    events: list[EventMessage]       # Multiple events batched
    batch_id: str
    created_at: float
    priority: DeliveryPriority
    
    def get_total_size(self) -> int:
        """Get total size for memory management."""
```

---

## 10. Performance Characteristics

### Latency Targets
| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| WebSocket Delivery | <100ms | ~50ms | ✅ |
| Pattern Detection → Broadcast | <2 min | 1-2 min | ✅ |
| Rate Limiting | 100 events/sec | Per user | ✅ |
| Batch Processing | 100ms window | 100ms | ✅ |
| Indexing (user lookup) | <5ms | <2ms | ✅ |

### Concurrency Support
- **Concurrent Users**: 500+
- **Connections per User**: Multiple (multi-tab support)
- **Events per Second**: 1000+ aggregated
- **Batch Size**: Max 50 events per batch
- **Memory per User**: ~1-2KB (subscription metadata)

### Rate Limiting
```python
class RateLimiter:
    """Per-user rate limiting."""
    max_events_per_second = 100  # Default
    window_size_seconds = 1
    
    # Tracks timestamps in deque
    # Drops events exceeding limit
    # Cleaned up for inactive users (>1 hour)
```

---

## 11. Emit Patterns Summary

### Emit to Single User (Room)
```python
socketio.emit('event_name', data, room=f'user_{user_id}')
```
- **Use**: User-specific notifications
- **Delivery**: Only to that user's connections
- **Example**: Backtest completion, pattern alert for subscribed user

### Emit to All Users (Broadcast)
```python
socketio.emit('event_name', data, broadcast=True)
```
- **Use**: System-wide notifications
- **Delivery**: All connected clients
- **Example**: System health, global announcements

### Emit to Specific Room
```python
socketio.emit('event_name', data, room='backtest_results_room')
```
- **Use**: Feature-specific messaging
- **Delivery**: All connections in that room
- **Example**: Backtest progress to interested users

### Emit with Namespace (Advanced)
```python
socketio.emit('event_name', data, namespace='/', broadcast=True)
```
- **Use**: Multi-namespace isolation
- **Current**: All events use default namespace '/'

---

## 12. Common Gotchas & Solutions

### Gotcha 1: Connection ID vs User ID
```python
# WRONG: Confusing request.sid (connection ID) with user ID
@socketio.on('connect')
def handle_connect():
    emit('user_id', request.sid)  # This is connection ID, not user ID!

# RIGHT: Map connection ID to user ID
@socketio.on('connect')
def handle_connect():
    user_id = getattr(current_user, 'id', 'anonymous')
    websocket_manager.register_user(user_id, request.sid)
```

### Gotcha 2: Rooms vs Broadcast
```python
# WRONG: Using room when you meant broadcast
socketio.emit('update', data, room='all')  # Creates actual room, doesn't broadcast

# RIGHT: For true broadcast
socketio.emit('update', data, broadcast=True)

# RIGHT: For targeted delivery
socketio.emit('update', data, room=f'user_{user_id}')
```

### Gotcha 3: Missing Flask Context in Threads
```python
# WRONG: Redis subscriber thread loses Flask context
def _redis_subscription_loop(self):
    for message in self.redis_subscriber.listen():
        socketio.emit('event', data)  # May fail!

# RIGHT: Use app context
def _redis_subscription_loop(self):
    for message in self.redis_subscriber.listen():
        with app.app_context():
            socketio.emit('event', data)
```

### Gotcha 4: Not Handling Disconnects
```python
# WRONG: No cleanup on disconnect
@socketio.on('disconnect')
def handle_disconnect():
    pass  # Memory leak!

# RIGHT: Clean up state
@socketio.on('disconnect')
def handle_disconnect():
    user_id = getattr(current_user, 'id', 'anonymous')
    websocket_publisher.remove_user(user_id)
```

### Gotcha 5: Rate Limiting Breaks During Spikes
```python
# Solution: Use ScalableBroadcaster with rate limiting
broadcaster.broadcast_to_users(
    'event_type',
    event_data,
    user_ids={'user_1', 'user_2'},
    priority=DeliveryPriority.HIGH  # High priority bypasses some limits
)
```

---

## 13. Testing WebSocket Connections

### Health Check Endpoint
```bash
curl http://localhost:5000/health
```

### Check Connected Users
```python
from src.core.services.websocket_broadcaster import websocket_broadcaster

stats = websocket_broadcaster.get_stats()
# Returns: {'total_connections', 'active_connections', 'messages_sent'}
```

### Monitor Live Events
```bash
python scripts/diagnostics/monitor_redis_channels.py
```

### WebSocket Client Test
```python
import socketio

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected')
    sio.emit('subscribe_tickers', {'tickers': ['AAPL', 'TSLA']})

@sio.on('tick_data')
def on_tick_data(data):
    print('Received:', data)

sio.connect('http://localhost:5000')
sio.wait()
```

---

## 14. File Reference Guide

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `config/app_config.py` | SocketIO initialization | `initialize_socketio()` |
| `src/app.py` | Event handler registration | `@socketio.on(...)` handlers |
| `src/presentation/websocket/manager.py` | Connection tracking | `WebSocketManager` |
| `src/presentation/websocket/publisher.py` | Simple emission | `WebSocketPublisher` |
| `src/core/services/websocket_broadcaster.py` | Enhanced broadcasting | `WebSocketBroadcaster` |
| `src/core/services/websocket_subscription_manager.py` | Multi-feature subscriptions | `UniversalWebSocketManager` |
| `src/core/services/redis_event_subscriber.py` | Redis integration | `RedisEventSubscriber` |
| `src/infrastructure/websocket/scalable_broadcaster.py` | High-performance batching | `ScalableBroadcaster` |
| `src/core/models/websocket_models.py` | Data structures | `UserSubscription` |

---

## 15. Future Enhancements

### Potential Improvements
1. **WebSocket Compression**: Enable per_message_deflate for bandwidth savings
2. **Namespace Isolation**: Use separate namespaces for different feature areas
3. **Message Encryption**: Add TLS/SSL for sensitive data
4. **Load Balancing**: Distribute WebSocket connections across multiple workers
5. **Event Versioning**: Support backward-compatible event schema evolution
6. **Metrics Export**: Prometheus integration for monitoring
7. **Connection Pool Exhaustion**: Handle graceful degradation under load

---

## Summary

TickStockAppV2's WebSocket architecture provides:
- **Real-time delivery** with <100ms latency
- **Scalable subscriptions** supporting 500+ concurrent users  
- **Intelligent batching** for efficient network utilization
- **Redis integration** for distributed messaging
- **Comprehensive event routing** with pattern and tier-based filtering
- **Production-ready** error handling and monitoring

The three-tier design (Manager → Broadcaster → ScalableBroadcaster) provides flexibility while maintaining high performance.
