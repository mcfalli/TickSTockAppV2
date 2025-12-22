# Redis Pub-Sub Integration Pattern Guide

**Complete Analysis of TickStockAppV2's Redis Integration**  
*Comprehensive reference for understanding how Redis events flow from TickStockPL through TickStockAppV2 to WebSocket clients*

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Redis Subscribers](#redis-subscribers)
3. [Channel Patterns](#channel-patterns)
4. [Message Parsing & Validation](#message-parsing--validation)
5. [Redis to WebSocket Flow](#redis-to-websocket-flow)
6. [Error Handling](#error-handling)
7. [Performance Monitoring](#performance-monitoring)
8. [Code Patterns & Examples](#code-patterns--examples)

---

## Architecture Overview

### High-Level Flow

```
TickStockPL (Producer)
    ↓
    Publishes to Redis Channels
    ↓
Redis Server (Message Broker)
    ↓
    Multiple Subscribers
    ↓
TickStockAppV2 (Consumer)
    ├── RedisEventSubscriber (Primary)
    ├── MarketDataSubscriber (Market Data)
    ├── MonitoringSubscriber (Monitoring)
    └── ErrorSubscriber (Error Handling)
    ↓
    WebSocket Broadcasting
    ↓
Browser Clients (Real-time UI Updates)
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| **RedisEventSubscriber** | `src/core/services/redis_event_subscriber.py` | Main event consumer, pattern/backtest/streaming events |
| **MarketDataSubscriber** | `src/core/services/market_data_subscriber.py` | Extended subscriber for market data filtering |
| **MonitoringSubscriber** | `src/services/monitoring_subscriber.py` | TickStockPL system health & monitoring events |
| **ErrorSubscriber** | `src/core/services/error_subscriber.py` | TickStockPL error event processing |
| **RedisConnectionManager** | `src/infrastructure/redis/redis_connection_manager.py` | Connection pooling & health monitoring |
| **StreamingBuffer** | `src/core/services/streaming_buffer.py` | Smart batching for high-frequency events |
| **RedisValidator** | `src/core/services/redis_validator.py` | Startup validation & diagnostics |
| **RedisMonitor** | `src/core/services/redis_monitor.py` | Debug message monitoring (Sprint 43) |

---

## Redis Subscribers

### 1. RedisEventSubscriber (Primary)

**File:** `src/core/services/redis_event_subscriber.py` (899 lines)

**Initialization Pattern:**

```python
from src.core.services.redis_event_subscriber import RedisEventSubscriber

# Create subscriber with dependencies
redis_client = get_redis_client()
socketio = SocketIO(app)
config = {'buffer_settings': {...}}

subscriber = RedisEventSubscriber(
    redis_client=redis_client,
    socketio=socketio,
    config=config,
    backtest_manager=backtest_manager,  # Optional
    flask_app=app  # For app context execution
)

# Start subscription service
success = subscriber.start()
```

**Key Methods:**

- **`start()`** - Initializes pubsub connection, subscribes to all channels, starts subscriber thread
- **`stop()`** - Gracefully shuts down subscriber and cleans up resources
- **`_subscriber_loop()`** - Main thread loop that receives messages with 1-second timeout
- **`_process_message(channel, data)`** - Parses Redis message and routes to handler
- **`_handle_event(event)`** - Dispatches to event-specific handler
- **`add_event_handler(event_type, callback)`** - Custom handler registration
- **`get_stats()`** - Returns runtime statistics
- **`get_health_status()`** - Health monitoring for dashboards

**Event Types:**

```python
class EventType(Enum):
    PATTERN_DETECTED = "pattern_detected"
    BACKTEST_PROGRESS = "backtest_progress"
    BACKTEST_RESULT = "backtest_result"
    SYSTEM_HEALTH = "system_health"
    STREAMING_SESSION_STARTED = "streaming_session_started"
    STREAMING_SESSION_STOPPED = "streaming_session_stopped"
    STREAMING_HEALTH = "streaming_health"
    STREAMING_PATTERN = "streaming_pattern"
    STREAMING_INDICATOR = "streaming_indicator"
    INDICATOR_ALERT = "indicator_alert"
    CRITICAL_ALERT = "critical_alert"
```

**Thread Management:**

```python
# Single daemon thread running _subscriber_loop()
self.subscriber_thread = threading.Thread(
    target=self._subscriber_loop,
    name="RedisEventSubscriber",
    daemon=True
)
self.subscriber_thread.start()

# PubSub object manages subscriptions
self.pubsub = self.redis_client.pubsub()
self.pubsub.subscribe(channel_list)  # Subscribe to multiple channels
```

---

### 2. MarketDataSubscriber

**File:** `src/core/services/market_data_subscriber.py` (387 lines)

**Purpose:** Extends RedisEventSubscriber for real-time market data with user-specific filtering

**Extended Channels:**

```python
self.market_channels = {
    'tickstock.market.prices': MarketEventType.PRICE_UPDATE,
    'tickstock.market.ohlcv': MarketEventType.OHLCV_UPDATE,
    'tickstock.market.volume': MarketEventType.VOLUME_SPIKE,
    'tickstock.market.summary': MarketEventType.MARKET_SUMMARY,
    'tickstock.market.symbols': MarketEventType.SYMBOL_METADATA,
    'tickstock.dashboard.watchlist': MarketEventType.WATCHLIST_UPDATE,
    'tickstock.dashboard.alerts': MarketEventType.DASHBOARD_ALERT,
    'tickstock.dashboard.summary': MarketEventType.DASHBOARD_SUMMARY
}

# Merge with parent channels
self.channels.update(self.market_channels)
```

**Watchlist Caching:**

```python
# Cache user watchlists for fast filtering
self.user_watchlists: dict[str, list[str]] = {}  # user_id -> [symbols]
self.watchlist_cache_expiry = time.time() + 300  # 5 minute TTL

# Filter price updates to interested users only
interested_users = self._get_users_for_symbol(symbol)
if interested_users:
    # Send only to users with symbol in watchlist
    self.socketio.emit('dashboard_price_update', data, broadcast=True)
```

**Performance Tracking:**

```python
# Monitor processing latency
processing_time_ms = (time.time() - start_time) * 1000
if processing_time_ms > 50:  # Warn if >50ms
    logger.warning(f"Slow processing {processing_time_ms:.1f}ms")
```

---

### 3. MonitoringSubscriber

**File:** `src/services/monitoring_subscriber.py` (339 lines)

**Purpose:** Subscribes to system monitoring events from TickStockPL

**Subscription Pattern:**

```python
class MonitoringSubscriber:
    def __init__(self, app_url: str = 'http://localhost:5000'):
        self.channel = 'tickstock:monitoring'
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe(self.channel)
```

**Event Types Handled:**

- `METRIC_UPDATE` - System metrics (CPU, memory)
- `ALERT_TRIGGERED` - Alerts with severity levels
- `ALERT_RESOLVED` - Alert resolution
- `HEALTH_CHECK` - Component health status
- `SYSTEM_STATUS` - Overall system state

**HTTP Forwarding:**

```python
def _forward_to_app(self, event: dict[str, Any]):
    """Forward event to Flask app via HTTP"""
    response = requests.post(
        f"{self.app_url}/api/admin/monitoring/store-event",
        json=event,
        timeout=5
    )
```

**Global Instance:**

```python
# Global singleton
_subscriber = None

def start_monitoring_subscriber(app_url: str = 'http://localhost:5000'):
    global _subscriber
    if _subscriber is None:
        _subscriber = MonitoringSubscriber(app_url)
        _subscriber.start()
```

---

### 4. ErrorSubscriber

**File:** `src/core/services/error_subscriber.py` (347 lines)

**Purpose:** Processes error messages from TickStockPL

**Configuration:**

```python
class ErrorSubscriber:
    def __init__(
        self,
        redis_client: redis.Redis,
        enhanced_logger: EnhancedLogger,
        config: LoggingConfig
    ):
        # Uses config.redis_error_channel (from .env)
        # Typical: 'tickstock:errors'
```

**Reconnection with Exponential Backoff:**

```python
def _handle_reconnection(self):
    """Exponential backoff: 5s → 7.5s → 11.25s ... max 60s"""
    self.reconnect_delay = min(
        self.reconnect_delay * 1.5,  # 1.5x multiplier
        self.max_reconnect_delay  # Cap at 60s
    )
```

**Message Processing:**

```python
def _process_message(self, message: dict[str, Any]):
    """Process error message and route to enhanced logger"""
    message_data = message['data']
    self.enhanced_logger.log_from_redis_message(message_data)
```

---

## Channel Patterns

### Complete Channel List

**TickStockPL Event Channels:**

```
tickstock.events.patterns           → Pattern detections
tickstock.events.backtesting.progress → Backtest job progress
tickstock.events.backtesting.results  → Backtest job results
tickstock.health.status             → System health updates
```

**Sprint 5 Streaming Channels:**

```
tickstock:streaming:session_started  → Session started event
tickstock:streaming:session_stopped  → Session stopped event
tickstock:streaming:health          → Streaming health metrics
tickstock:patterns:streaming        → Real-time pattern detections
tickstock:patterns:detected         → High confidence patterns (≥80%)
tickstock:indicators:streaming      → Real-time indicator calculations
tickstock:alerts:indicators         → Indicator alerts (RSI, MACD, BB)
tickstock:alerts:critical           → Critical system alerts
```

**Market Data Channels:**

```
tickstock.market.prices             → Real-time price updates
tickstock.market.ohlcv              → OHLCV bar updates
tickstock.market.volume             → Volume spike alerts
tickstock.market.summary            → Market-wide summary
tickstock.market.symbols            → Symbol metadata
tickstock.dashboard.watchlist       → Watchlist change notifications
tickstock.dashboard.alerts          → Dashboard alerts
tickstock.dashboard.summary         → Dashboard summary statistics
```

**Monitoring Channels:**

```
tickstock:monitoring                → System monitoring metrics
```

**Error Channels:**

```
tickstock:errors                    → Error events (from .env: REDIS_ERROR_CHANNEL)
```

### Channel Subscription at Startup

```python
def start(self) -> bool:
    """Start Redis event subscription"""
    # Subscribe to all channels
    channel_list = list(self.channels.keys())
    self.pubsub.subscribe(channel_list)
    
    logger.info(f"Subscribed to {len(channel_list)} channels: {channel_list}")
    
    # Start daemon thread
    self.subscriber_thread = threading.Thread(
        target=self._subscriber_loop,
        name="RedisEventSubscriber",
        daemon=True
    )
    self.subscriber_thread.start()
```

---

## Message Parsing & Validation

### Message Structure

**Redis Message Format (from pubsub.get_message()):**

```python
message = {
    'type': 'subscribe' | 'unsubscribe' | 'message',  # Message type
    'channel': b'tickstock:patterns:streaming',        # Channel (bytes)
    'data': b'{"pattern":"Doji",...}',                 # Payload (bytes)
    'pattern': None                                     # For pattern subscriptions
}
```

### Parsing Pipeline

**Step 1: Extract Channel & Data**

```python
channel = message['channel']
if isinstance(channel, bytes):
    channel = channel.decode('utf-8')

data = message['data']
if isinstance(data, bytes):
    data = data.decode('utf-8')
```

**Step 2: Parse JSON**

```python
try:
    event_data = json.loads(data)
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON from {channel}: {e}")
    self.stats['events_dropped'] += 1
    return
```

**Step 3: Map to EventType**

```python
# Map channel name to event type
event_type = self.channels.get(channel)

if not event_type:
    logger.warning(f"Unknown channel: {channel}")
    self.stats['events_dropped'] += 1
    return
```

**Step 4: Create Structured Event**

```python
event = TickStockEvent(
    event_type=event_type,
    source=event_data.get('source', 'unknown'),
    timestamp=event_data.get('timestamp', time.time()),
    data=event_data,
    channel=channel
)
```

### Pattern Message Validation

**Multi-level Nesting Handling:**

```python
def _handle_pattern_event(self, event: TickStockEvent):
    """Handle double/triple nested pattern data"""
    
    # Double-nested: event.data.data.data
    if 'data' in event.data and 'data' in event.data.get('data', {}):
        pattern_data = event.data['data']['data']
    
    # Single-nested: event.data.data
    elif 'data' in event.data:
        pattern_data = event.data['data']
    
    # Direct: event.data
    else:
        pattern_data = event.data
    
    # Field name variations (TickStockPL inconsistency)
    pattern_name = pattern_data.get('pattern')  # New format
    if not pattern_name:
        pattern_name = pattern_data.get('pattern_name')  # Old format
    
    symbol = pattern_data.get('symbol')
    confidence = pattern_data.get('confidence', 0)
    
    # Validate required fields
    if not pattern_name or not symbol:
        logger.warning("Pattern missing required fields")
        return
```

### Indicator Message Validation

```python
def _handle_streaming_indicator(self, event: TickStockEvent):
    """Handle indicator calculation messages"""
    
    calculation = event.data.get('calculation', event.data)
    
    # TickStockPL uses 'indicator' field
    indicator_type = (calculation.get('indicator') or 
                      calculation.get('indicator_type'))
    
    symbol = calculation.get('symbol')
    values = calculation.get('values', {})
    timestamp = calculation.get('timestamp')
    
    if not symbol or not indicator_type:
        logger.warning("Indicator missing required fields")
        return
```

### Message Validation Stats

```python
self.stats = {
    'events_received': 0,      # Total messages from Redis
    'events_processed': 0,     # Successfully parsed
    'events_forwarded': 0,     # Sent to WebSocket
    'events_dropped': 0,       # Parse/validation errors
    'connection_errors': 0,    # Redis connection issues
    'last_event_time': None,   # Last successful event
    'start_time': time.time()
}
```

---

## Redis to WebSocket Flow

### Complete Flow Diagram

```
Redis Subscriber Loop
    ↓
get_message(timeout=1.0)
    ↓
[Decode bytes → UTF-8]
    ↓
[Parse JSON]
    ↓
[Create TickStockEvent]
    ↓
_handle_event()
    ├─ Check event type
    ├─ Route to specific handler
    └─ Execute handler
         ↓
    [Filter (e.g., user subscriptions)]
         ↓
    [Convert to WebSocket format]
         ↓
socketio.emit()
    ↓
Browser Clients (Real-time Update)
```

### Pattern Alert Forwarding

```python
def _handle_pattern_event(self, event: TickStockEvent):
    """Send pattern alerts to interested users"""
    
    # Get users who subscribed to this pattern
    pattern_alert_manager = self.flask_app.pattern_alert_manager
    interested_users = pattern_alert_manager.get_users_for_alert(
        pattern_name, symbol, confidence
    )
    
    # Create WebSocket payload
    websocket_data = {
        'type': 'pattern_alert',
        'event': event.to_websocket_dict()
    }
    
    # Send to user-specific rooms
    if self.socketio:
        for user_id in interested_users:
            self.socketio.emit(
                'pattern_alert',
                websocket_data,
                room=f'user_{user_id}'  # User-specific room
            )
        
        self.stats['events_forwarded'] += len(interested_users)
```

### Streaming Pattern with Buffering

```python
def _handle_streaming_pattern(self, event: TickStockEvent):
    """Handle real-time pattern with optional buffering"""
    
    detection = event.data.get('detection', event.data)
    pattern_type = detection.get('pattern') or detection.get('pattern_type')
    symbol = detection.get('symbol')
    
    # Create WebSocket payload
    websocket_data = {
        'type': 'streaming_pattern',
        'detection': {
            'pattern_type': pattern_type,
            'symbol': symbol,
            'confidence': detection.get('confidence'),
            'timestamp': detection.get('timestamp'),
            'parameters': detection.get('parameters', {})
        }
    }
    
    # Route through streaming buffer if available
    if hasattr(self, 'streaming_buffer') and self.streaming_buffer:
        logger.info(f"Sending {pattern_type}@{symbol} to StreamingBuffer")
        self.streaming_buffer.add_pattern(websocket_data)
    else:
        # Direct broadcast without buffering
        logger.info(f"Direct broadcast {pattern_type}@{symbol}")
        self.socketio.emit('streaming_pattern', websocket_data, namespace='/')
    
    self.stats['events_forwarded'] += 1
```

### Streaming Indicator Handling

```python
def _handle_streaming_indicator(self, event: TickStockEvent):
    """Forward real-time indicator calculations"""
    
    calculation = event.data.get('calculation', event.data)
    
    # Create WebSocket payload
    websocket_data = {
        'type': 'streaming_indicator',
        'calculation': {
            'indicator_type': calculation.get('indicator') or calculation.get('indicator_type'),
            'symbol': calculation.get('symbol'),
            'values': calculation.get('values', {}),
            'timestamp': calculation.get('timestamp'),
            'timeframe': calculation.get('timeframe', '1min')
        }
    }
    
    # Buffer or send directly
    if hasattr(self, 'streaming_buffer') and self.streaming_buffer:
        self.streaming_buffer.add_indicator(websocket_data)
    else:
        self.socketio.emit('streaming_indicator', websocket_data, namespace='/')
    
    self.stats['events_forwarded'] += 1
```

### Broadcasting to All Users

```python
def _handle_backtest_progress(self, event: TickStockEvent):
    """Broadcast backtest progress to all users"""
    
    progress_data = event.data
    job_id = progress_data.get('job_id')
    progress = progress_data.get('progress', 0)
    
    # Broadcast without filtering
    websocket_data = {
        'type': 'backtest_progress',
        'event': event.to_websocket_dict()
    }
    
    self.socketio.emit('backtest_progress', websocket_data, namespace='/')
    self.stats['events_forwarded'] += 1
```

---

## Error Handling

### Connection Error Recovery

**Automatic Reconnection:**

```python
def _subscriber_loop(self):
    """Main loop with connection error handling"""
    
    while self.is_running:
        try:
            message = self.pubsub.get_message(timeout=1.0)
            
            if message and message['type'] == 'message':
                self._process_message(message)
        
        except redis.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            self.stats['connection_errors'] += 1
            self._handle_connection_error()  # Reconnect logic
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(1)  # Prevent tight error loop
```

**Reconnection with Exponential Backoff:**

```python
def _handle_connection_error(self):
    """Attempt reconnection with exponential backoff"""
    
    logger.warning("Attempting to reconnect to Redis...")
    
    for attempt in range(3):
        try:
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
            
            if self._test_redis_connection():
                logger.info("Reconnected successfully")
                return
        
        except Exception as e:
            logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
    
    logger.error("Failed to reconnect after 3 attempts")
```

### Message Parsing Errors

```python
def _process_message(self, message: dict[str, Any]):
    """Handle parsing errors gracefully"""
    
    try:
        self.stats['events_received'] += 1
        
        # ... parsing logic ...
        
        event_data = json.loads(data)
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from {channel}: {e}")
        self.stats['events_dropped'] += 1
        return  # Skip this message, continue processing
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        self.stats['events_dropped'] += 1
```

### Graceful Degradation

```python
def _handle_pattern_event(self, event: TickStockEvent):
    """Fallback to broadcast on filtering error"""
    
    try:
        # Try targeted user filtering
        interested_users = pattern_alert_manager.get_users_for_alert(...)
        
        for user_id in interested_users:
            self.socketio.emit('pattern_alert', websocket_data, room=f'user_{user_id}')
    
    except Exception as e:
        logger.error(f"Error in pattern filtering: {e}")
        
        # Fallback: broadcast to all users
        try:
            self.socketio.emit('pattern_alert', websocket_data, namespace='/')
            self.stats['events_forwarded'] += 1
        except Exception as emit_error:
            logger.error(f"Failed to emit pattern alert: {emit_error}")
```

---

## Performance Monitoring

### Statistics Tracking

**Real-time Stats:**

```python
def get_stats(self) -> dict[str, Any]:
    """Get runtime statistics"""
    
    runtime = time.time() - self.stats['start_time']
    
    return {
        **self.stats,
        'runtime_seconds': round(runtime, 1),
        'events_per_second': round(
            self.stats['events_received'] / max(runtime, 1), 2
        ),
        'is_running': self.is_running,
        'subscribed_channels': list(self.channels.keys()),
        'active_thread': self.subscriber_thread and self.subscriber_thread.is_alive()
    }
```

**Health Monitoring:**

```python
def get_health_status(self) -> dict[str, Any]:
    """Get comprehensive health status"""
    
    stats = self.get_stats()
    tickstock_pl_online = self._check_tickstock_pl_status()
    
    # Determine health status
    if not self.is_running:
        status = 'error'
    elif stats['connection_errors'] > 5:
        status = 'degraded'
    elif not tickstock_pl_online:
        status = 'warning'
    elif stats['last_event_time'] and (time.time() - stats['last_event_time']) > 300:
        status = 'warning'
    else:
        status = 'healthy'
    
    return {
        'status': status,
        'message': '...',
        'stats': stats,
        'tickstock_pl_online': tickstock_pl_online
    }
```

### Heartbeat Logging

```python
def _log_heartbeat(self):
    """Log periodic heartbeat every 60 seconds"""
    
    #logger.info(
    #    f"REDIS-SUBSCRIBER HEARTBEAT: "
    #    f"Alive on {len(self.channels)} channels | "
    #    f"Events: {self.stats['events_received']} received, "
    #    f"{self.stats['events_processed']} processed | "
    #    f"Uptime: {round(time.time() - self.stats['start_time'])}s"
    #)
    
    self.stats['last_heartbeat'] = time.time()
```

### Market Data Stats

```python
self.market_stats = {
    'price_updates_processed': 0,
    'price_updates_filtered': 0,
    'price_updates_sent': 0,
    'ohlcv_updates_processed': 0,
    'watchlist_cache_hits': 0,
    'watchlist_cache_misses': 0,
    'avg_processing_time_ms': 0
}

# Monitor performance
if processing_time_ms > 50:  # >50ms is concerning
    logger.warning(f"Slow processing {processing_time_ms:.1f}ms for {channel}")
```

### Streaming Buffer Stats

```python
def get_stats(self) -> dict[str, Any]:
    """Get buffer efficiency metrics"""
    
    runtime = time.time() - self.stats['start_time']
    
    return {
        **self.stats,
        'runtime_seconds': round(runtime, 1),
        'buffer_efficiency': round(
            self.stats['events_deduplicated'] / 
            max(self.stats['events_buffered'], 1) * 100,
            1
        ),
        'flush_rate': round(self.stats['flush_cycles'] / max(runtime, 1), 1),
        'current_pattern_buffer': len(self.pattern_buffer),
        'current_indicator_buffer': len(self.indicator_buffer),
        'enabled': self.enabled,
        'buffer_interval_ms': self.buffer_interval_ms
    }
```

---

## Code Patterns & Examples

### Pattern 1: Subscriber Initialization in Flask App

**File:** Flask app initialization (typically `app.py`)

```python
from flask import Flask
from flask_socketio import SocketIO
from src.config.redis_config import get_redis_client
from src.core.services.redis_event_subscriber import RedisEventSubscriber

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Redis subscriber
redis_client = get_redis_client()
app.redis_subscriber = RedisEventSubscriber(
    redis_client=redis_client,
    socketio=socketio,
    config=app.config,
    backtest_manager=backtest_manager,
    flask_app=app
)

# Start subscriber in background thread
success = app.redis_subscriber.start()
if success:
    logger.info("Redis event subscriber started successfully")
else:
    logger.error("Failed to start Redis event subscriber")

# Graceful shutdown
def shutdown():
    if hasattr(app, 'redis_subscriber'):
        app.redis_subscriber.stop()

atexit.register(shutdown)
```

### Pattern 2: Custom Event Handler Registration

```python
# Register handler for pattern events
def on_pattern_detected(event):
    logger.info(f"Custom handler: Pattern {event.data['pattern']} on {event.data['symbol']}")
    # Custom logic here
    send_notification(event)

app.redis_subscriber.add_event_handler(
    EventType.PATTERN_DETECTED,
    on_pattern_detected
)
```

### Pattern 3: Real-time Dashboard Updates

**JavaScript Client:**

```javascript
// Connect to Flask-SocketIO
const socket = io();

// Listen for pattern alerts
socket.on('pattern_alert', (data) => {
    console.log('Pattern alert received:', data.event);
    
    const {
        event_type,
        data: patternData,
        timestamp
    } = data.event;
    
    // Update UI
    updateDashboard(patternData);
});

// Listen for streaming patterns (buffered batches)
socket.on('streaming_patterns_batch', (batch) => {
    console.log(`Received batch of ${batch.count} patterns`);
    
    batch.patterns.forEach(pattern => {
        addPatternToChart(pattern);
    });
});

// Listen for streaming indicators
socket.on('streaming_indicators_batch', (batch) => {
    console.log(`Received batch of ${batch.count} indicators`);
    
    batch.indicators.forEach(indicator => {
        updateIndicatorPanel(indicator);
    });
});
```

### Pattern 4: Filter Events by User Subscription

```python
# Pattern alert manager filters events
class PatternAlertManager:
    def get_users_for_alert(self, pattern_name, symbol, confidence):
        """Get users who subscribed to this pattern"""
        
        users = []
        
        # Query subscriptions
        subscriptions = self.db.query(PatternSubscription).filter(
            PatternSubscription.pattern_name == pattern_name,
            PatternSubscription.is_active == True
        ).all()
        
        # Filter by confidence threshold
        for sub in subscriptions:
            if confidence >= sub.min_confidence:
                users.append(sub.user_id)
        
        return users

# In RedisEventSubscriber
pattern_alert_manager = getattr(self.flask_app, 'pattern_alert_manager', None)
interested_users = pattern_alert_manager.get_users_for_alert(
    pattern_name, symbol, confidence
)

# Send only to interested users
for user_id in interested_users:
    self.socketio.emit('pattern_alert', websocket_data, room=f'user_{user_id}')
```

### Pattern 5: Streaming Buffer Configuration

```python
# Environment variables (.env)
STREAMING_BUFFER_ENABLED=true
STREAMING_BUFFER_INTERVAL=250  # ms
STREAMING_MAX_BUFFER_SIZE=100

# Initialize streaming buffer
from src.core.services.streaming_buffer import StreamingBuffer

streaming_buffer = StreamingBuffer(
    socketio=socketio,
    config={
        'STREAMING_BUFFER_ENABLED': True,
        'STREAMING_BUFFER_INTERVAL': 250,
        'STREAMING_MAX_BUFFER_SIZE': 100
    }
)

streaming_buffer.start()

# Add to Redis subscriber
app.redis_subscriber.streaming_buffer = streaming_buffer

# Messages are buffered and flushed every 250ms
# Reduces browser load: 100 individual events → 5 batches
```

### Pattern 6: Redis Validation at Startup

**File:** App initialization

```python
from src.core.services.redis_validator import initialize_redis_mandatory

try:
    # Mandatory Redis validation
    redis_client = initialize_redis_mandatory(
        config=app.config,
        environment='PRODUCTION'  # or 'DEVELOPMENT'
    )
    
    logger.info("Redis validation successful")
    
except RedisConfigurationError as e:
    logger.error(f"Redis configuration error: {e}")
    report = generate_redis_failure_report('config', str(e))
    print(report)
    sys.exit(1)

except RedisConnectionError as e:
    logger.error(f"Redis connection error: {e}")
    report = generate_redis_failure_report('connection', str(e))
    print(report)
    sys.exit(1)

except RedisChannelError as e:
    logger.error(f"Redis pub-sub error: {e}")
    report = generate_redis_failure_report('channels', str(e))
    print(report)
    sys.exit(1)

except RedisPerformanceError as e:
    logger.error(f"Redis performance error: {e}")
    report = generate_redis_failure_report('performance', str(e))
    print(report)
    sys.exit(1)
```

### Pattern 7: Debug Message Monitoring (Sprint 43)

```python
from src.core.services.redis_monitor import RedisMonitor

# Create monitor
redis_monitor = RedisMonitor(max_messages=500)

# Capture messages in subscriber
redis_monitor.capture_message(
    channel=channel,
    message_data=event_data,
    event_type=event_type.value
)

# Get recent messages for debugging
recent = redis_monitor.get_recent_messages(limit=50)
for msg in recent:
    print(f"{msg['timestamp']}: {msg['channel']} - {msg['event_type']}")

# Analyze field naming inconsistencies
report = redis_monitor.get_field_name_report()
print(report['recommendation'])
```

---

## Summary Table

| Aspect | Implementation | Key Files |
|--------|---|---|
| **Main Subscriber** | Background thread, pubsub.get_message() with 1s timeout | `redis_event_subscriber.py` |
| **Channels** | 16+ channels, mapped to EventType enum | `redis_event_subscriber.py:109-123` |
| **Message Parsing** | JSON decode, multi-level nesting handling | `redis_event_subscriber.py:276-336` |
| **Redis→WebSocket** | socketio.emit() with optional buffering | `redis_event_subscriber.py:338-785` |
| **Error Handling** | Exponential backoff reconnection, graceful degradation | `redis_event_subscriber.py:787-802` |
| **Performance** | Stats tracking, heartbeat logging, latency monitoring | `redis_event_subscriber.py:817-875` |
| **Smart Buffering** | 250ms batch window, deduplication by symbol-type | `streaming_buffer.py:74-207` |
| **User Filtering** | Watchlist caching, pattern subscriptions | `market_data_subscriber.py:327-343` |
| **Validation** | Startup checks, pub-sub test, performance thresholds | `redis_validator.py:25-336` |
| **Monitoring** | Message capture, field name analysis, diagnostics | `redis_monitor.py:19-264` |

---

## Configuration Reference

### Environment Variables (.env)

```bash
# Redis Connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Logging
LOG_FILE_ENABLED=true
LOG_DB_ENABLED=true
LOG_DB_SEVERITY_THRESHOLD=error

# Redis Channels
REDIS_ERROR_CHANNEL=tickstock:errors

# Streaming Buffer
STREAMING_BUFFER_ENABLED=true
STREAMING_BUFFER_INTERVAL=250  # milliseconds
STREAMING_MAX_BUFFER_SIZE=100

# Trace Settings (Debug)
TRACE_ENABLED=true
TRACE_TICKERS=NVDA,TSLA,AAPL
TRACE_LEVEL=VERBOSE
```

### Performance Targets

| Operation | Target | Status |
|-----------|--------|--------|
| Redis Ping | <50ms | ✅ |
| Message Parse | <5ms | ✅ |
| WebSocket Delivery | <100ms | ✅ |
| Buffer Flush | 250ms | ✅ |
| Pattern Detection | <2min | ✅ |

---

**Document Version:** 1.0  
**Last Updated:** Sprint 50  
**Author:** Architecture Analysis  

