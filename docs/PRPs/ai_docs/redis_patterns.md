# Redis Patterns for TickStock

> Redis pub-sub, caching, and integration patterns for TickStockAppV2 ↔ TickStockPL communication

## Quick Reference

| Pattern | When to Use | File Reference |
|---------|-------------|----------------|
| Redis Pub-Sub Subscriber | Consuming events from TickStockPL | `src/core/services/redis_event_subscriber.py` |
| Redis Channel Patterns | Understanding message flow | `src/config/redis_config.py` |
| Message Parsing | Handling typed events vs dicts | `src/core/services/processing_event_subscriber.py` |
| WebSocket Broadcasting | Redis event → browser delivery | `src/core/services/websocket_broadcaster.py` |
| Connection Management | Initialization and error handling | `src/app.py:115-140` |

---

## 1. TickStock Redis Architecture

### Component Roles

```
┌─────────────────┐                      ┌─────────────────┐
│  TickStockPL    │                      │ TickStockAppV2  │
│  (Producer)     │                      │  (Consumer)     │
├─────────────────┤                      ├─────────────────┤
│                 │                      │                 │
│ Pattern         │  Redis Pub-Sub       │  Subscribe      │
│ Detection   ────┼─────────────────────>│  Channels       │
│                 │  tickstock:patterns  │                 │
│ Indicator       │  tickstock:indicators│  Parse          │
│ Calculation ────┼─────────────────────>│  Messages       │
│                 │                      │                 │
│ OHLCV           │                      │  Broadcast      │
│ Aggregation     │  tickstock:market    │  via            │
│             <───┼──────────────────────│  WebSocket      │
│                 │  (tick forwarding)   │                 │
└─────────────────┘                      └─────────────────┘
```

### Channel Architecture

| Channel Pattern | Direction | Purpose | Message Format |
|-----------------|-----------|---------|----------------|
| `tickstock:patterns:streaming` | PL → AppV2 | Real-time pattern detections | `{pattern_name, symbol, timeframe, confidence, ...}` |
| `tickstock:patterns:detected` | PL → AppV2 | High-confidence patterns (≥80%) | `{pattern_name, symbol, timeframe, confidence, ...}` |
| `tickstock:indicators:streaming` | PL → AppV2 | Real-time indicator calculations | `{indicator_name, symbol, timeframe, value, ...}` |
| `tickstock:market:ticks` | AppV2 → PL | Raw tick forwarding | `{symbol, price, volume, timestamp, ...}` |
| `tickstock:streaming:health` | PL → AppV2 | Health metrics | `{status, uptime, symbols_processed, ...}` |
| `tickstock:errors` | Bi-directional | System errors | `{severity, message, component, timestamp, ...}` |

---

## 2. Redis Pub-Sub Subscriber Pattern

### Basic Subscriber Pattern

```python
# File: src/core/services/my_event_subscriber.py

import redis
import json
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class MyEventSubscriber:
    """
    Redis pub-sub subscriber for TickStock events.

    Pattern: Subscribe to Redis channels and invoke callback for each message
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize subscriber.

        Args:
            redis_client: Configured Redis client instance
        """
        self.redis_client = redis_client
        self.pubsub = None
        self.is_running = False

    def subscribe(self, callback: Callable[[dict], None]):
        """
        Subscribe to Redis channels and process messages.

        Args:
            callback: Function to call with parsed message dict

        Pattern:
            1. Subscribe to channel pattern
            2. Listen for messages
            3. Parse JSON
            4. Convert typed events to dicts (CRITICAL)
            5. Invoke callback
        """
        try:
            # Step 1: Create pubsub instance
            self.pubsub = self.redis_client.pubsub()

            # Step 2: Subscribe to channel pattern
            # Use psubscribe for patterns (tickstock:domain:*)
            # Use subscribe for exact channels (tickstock:domain:event)
            self.pubsub.psubscribe('tickstock:patterns:*')
            logger.info("Subscribed to tickstock:patterns:*")

            self.is_running = True

            # Step 3: Listen for messages
            for message in self.pubsub.listen():
                if not self.is_running:
                    break

                # Filter out subscription confirmation messages
                if message['type'] == 'pmessage':
                    try:
                        # Step 4: Parse JSON message
                        data = json.loads(message['data'])

                        # CRITICAL: Convert typed events to dicts
                        # After Worker boundary, always use dict
                        event_dict = dict(data) if not isinstance(data, dict) else data

                        # Step 5: Invoke callback with parsed dict
                        callback(event_dict)

                    except json.JSONDecodeError as e:
                        # Specific error: Invalid JSON
                        logger.error(f"Invalid JSON in Redis message: {e}")
                        logger.debug(f"Raw message: {message['data']}")

                    except KeyError as e:
                        # Specific error: Missing required key
                        logger.error(f"Missing key in message: {e}")
                        logger.debug(f"Message data: {data}")

                    except Exception as e:
                        # Catch-all for unexpected errors
                        logger.error(f"Error processing Redis message: {e}")
                        logger.exception("Full traceback:")
                        # Don't re-raise - keep subscription alive

        except redis.ConnectionError as e:
            logger.error(f"Redis connection lost: {e}")
            self.is_running = False
            raise

        finally:
            self.stop()

    def stop(self):
        """Unsubscribe and cleanup."""
        self.is_running = False
        if self.pubsub:
            try:
                self.pubsub.unsubscribe()
                self.pubsub.close()
            except Exception as e:
                logger.error(f"Error closing pubsub: {e}")
            self.pubsub = None
```

### Working Example
**File**: `src/core/services/redis_event_subscriber.py` - Full subscriber implementation
**File**: `src/core/services/processing_event_subscriber.py` - Event handling patterns

---

## 3. Message Parsing Patterns

### The Typed Events vs Dicts Problem

**CRITICAL GOTCHA**: Never mix typed events and dicts after Worker boundary

```python
# ❌ WRONG: Passing TypedDict across multiprocessing Worker
from typing import TypedDict

class PatternEvent(TypedDict):
    pattern_name: str
    symbol: str
    confidence: float

def process_event(event: PatternEvent):
    # This WILL fail if event crosses Worker boundary
    name = event['pattern_name']


# ✅ CORRECT: Always convert to dict at Worker boundary
def handle_redis_message(message):
    """Parse and convert to dict immediately."""
    data = json.loads(message['data'])

    # Convert to dict if typed
    event_dict = dict(data) if not isinstance(data, dict) else data

    # Now safe to pass around
    process_event(event_dict)


def process_event(event: dict):
    """Accept plain dict, not typed."""
    name = event.get('pattern_name')
    symbol = event.get('symbol')
    confidence = event.get('confidence', 0.0)
```

### Message Validation Pattern

```python
def validate_pattern_event(event: dict) -> bool:
    """
    Validate pattern event has required fields.

    Args:
        event: Pattern event dict from Redis

    Returns:
        True if valid, False otherwise
    """
    required_fields = ['pattern_name', 'symbol', 'timeframe', 'confidence']

    for field in required_fields:
        if field not in event:
            logger.warning(f"Pattern event missing required field: {field}")
            logger.debug(f"Event: {event}")
            return False

    # Type validation
    if not isinstance(event['confidence'], (int, float)):
        logger.warning(f"Invalid confidence type: {type(event['confidence'])}")
        return False

    if not 0.0 <= event['confidence'] <= 100.0:
        logger.warning(f"Confidence out of range: {event['confidence']}")
        return False

    return True


def handle_pattern_event(event: dict):
    """Handle pattern event with validation."""
    if not validate_pattern_event(event):
        logger.error(f"Invalid pattern event: {event}")
        return

    # Process valid event
    pattern_name = event['pattern_name']
    symbol = event['symbol']
    confidence = event['confidence']

    logger.info(f"Pattern detected: {pattern_name} on {symbol} ({confidence}% confidence)")
```

---

## 4. WebSocket Broadcasting Pattern

### Redis Event → WebSocket Flow

```python
# File: src/core/services/websocket_broadcaster.py

from flask_socketio import emit
import time
import logging

logger = logging.getLogger(__name__)


class WebSocketBroadcaster:
    """Broadcast Redis events to WebSocket clients."""

    def __init__(self, socketio):
        """
        Initialize broadcaster.

        Args:
            socketio: Flask-SocketIO instance
        """
        self.socketio = socketio

    def broadcast_pattern(self, pattern_data: dict):
        """
        Broadcast pattern detection to WebSocket clients.

        Args:
            pattern_data: Pattern event from Redis

        Performance Target: <100ms from Redis event to browser delivery
        """
        start_time = time.time()

        try:
            # Extract symbol for room routing
            symbol = pattern_data.get('symbol')

            if not symbol:
                logger.warning("Pattern event missing symbol - cannot route to room")
                return

            # Room-based routing (only clients subscribed to this symbol)
            room = f"patterns:{symbol}"

            # Prepare WebSocket message
            message = {
                'type': 'pattern_detected',
                'timestamp': time.time(),
                'data': pattern_data
            }

            # Broadcast to room
            # broadcast=True sends to ALL clients in room (not just sender)
            emit('pattern_detected', message, room=room, broadcast=True)

            # Performance monitoring
            latency_ms = (time.time() - start_time) * 1000
            if latency_ms > 100:
                logger.warning(
                    f"Slow WebSocket broadcast: {latency_ms:.2f}ms (target: <100ms)"
                )

        except Exception as e:
            logger.error(f"Error broadcasting pattern: {e}")
            logger.exception("Full traceback:")


    def broadcast_to_all(self, event_type: str, data: dict):
        """
        Broadcast to ALL connected WebSocket clients.

        Args:
            event_type: Event name (e.g., 'system_alert')
            data: Event data dict
        """
        message = {
            'type': event_type,
            'timestamp': time.time(),
            'data': data
        }

        # No room specified = broadcast to all clients
        emit(event_type, message, broadcast=True)
```

### Buffered Broadcasting Pattern

For high-frequency events, buffer and batch:

```python
import time
from collections import defaultdict

class BufferedBroadcaster:
    """Buffer Redis events and broadcast in batches."""

    def __init__(self, socketio, flush_interval=0.25):
        """
        Args:
            socketio: Flask-SocketIO instance
            flush_interval: Seconds between flushes (default: 250ms)
        """
        self.socketio = socketio
        self.flush_interval = flush_interval
        self.buffer = defaultdict(list)
        self.last_flush = time.time()

    def add_event(self, event_type: str, symbol: str, data: dict):
        """Add event to buffer."""
        key = f"{event_type}:{symbol}"
        self.buffer[key].append(data)

        # Auto-flush if interval elapsed
        if time.time() - self.last_flush >= self.flush_interval:
            self.flush()

    def flush(self):
        """Broadcast all buffered events."""
        if not self.buffer:
            return

        for key, events in self.buffer.items():
            event_type, symbol = key.split(':', 1)
            room = f"{event_type}:{symbol}"

            message = {
                'type': f'{event_type}_batch',
                'timestamp': time.time(),
                'count': len(events),
                'data': events
            }

            emit(f'{event_type}_batch', message, room=room, broadcast=True)

        # Clear buffer
        self.buffer.clear()
        self.last_flush = time.time()
```

**Working Example**: Sprint 43 implemented 250ms streaming buffer for pattern/indicator events

---

## 5. Connection Management Pattern

### Redis Client Initialization

```python
# File: src/config/redis_config.py

import redis
import os
import logging

logger = logging.getLogger(__name__)


def get_redis_client() -> redis.Redis | None:
    """
    Create Redis client from environment configuration.

    Returns:
        Configured Redis client or None if not configured

    Environment Variables:
        REDIS_URL: Full Redis URL (e.g., redis://localhost:6379/0)
    """
    redis_url = os.getenv('REDIS_URL')

    if not redis_url:
        logger.warning("REDIS_URL not configured - Redis features disabled")
        return None

    try:
        client = redis.from_url(
            redis_url,
            decode_responses=True,  # Auto-decode bytes to strings
            socket_connect_timeout=5,  # Connection timeout
            socket_timeout=5,  # Read/write timeout
            retry_on_timeout=True,  # Retry on timeout
            health_check_interval=30  # Background health check
        )

        # Test connection
        client.ping()
        logger.info(f"Redis connected: {redis_url}")

        return client

    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error connecting to Redis: {e}")
        return None
```

### Connection Pool Pattern

```python
# Advanced: Connection pool for high-throughput applications

import redis

def get_redis_pool(max_connections=50):
    """
    Create Redis connection pool.

    Args:
        max_connections: Maximum connections in pool

    Returns:
        Redis connection pool
    """
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    pool = redis.ConnectionPool.from_url(
        redis_url,
        max_connections=max_connections,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True
    )

    return pool


# Usage
pool = get_redis_pool()
client = redis.Redis(connection_pool=pool)
```

### Reconnection Pattern

```python
import time

def subscribe_with_reconnect(subscriber, callback, max_retries=None):
    """
    Subscribe with automatic reconnection.

    Args:
        subscriber: RedisEventSubscriber instance
        callback: Message handler callback
        max_retries: Maximum retry attempts (None = infinite)
    """
    retry_count = 0
    backoff_seconds = 1

    while max_retries is None or retry_count < max_retries:
        try:
            logger.info("Starting Redis subscription...")
            subscriber.subscribe(callback)

        except redis.ConnectionError as e:
            retry_count += 1
            logger.error(f"Redis connection lost (attempt {retry_count}): {e}")

            if max_retries and retry_count >= max_retries:
                logger.error("Max retries exceeded - giving up")
                raise

            # Exponential backoff
            logger.info(f"Retrying in {backoff_seconds}s...")
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 60)  # Cap at 60s

        except Exception as e:
            logger.error(f"Unexpected error in Redis subscription: {e}")
            raise
```

---

## 6. Channel-Specific Patterns

### Pattern Events

```python
# Channel: tickstock:patterns:streaming
# Message Format:
{
    "pattern_name": "doji",
    "symbol": "AAPL",
    "timeframe": "1min",
    "confidence": 85.5,
    "detected_at": 1234567890.123,
    "bar_count": 5,
    "metadata": {
        "open": 150.0,
        "high": 151.0,
        "low": 149.5,
        "close": 150.2
    }
}

def handle_pattern_event(event: dict):
    """Handle pattern detection event."""
    pattern_name = event.get('pattern_name')
    symbol = event.get('symbol')
    timeframe = event.get('timeframe')
    confidence = event.get('confidence', 0.0)

    logger.info(
        f"Pattern: {pattern_name} | Symbol: {symbol} | "
        f"Timeframe: {timeframe} | Confidence: {confidence}%"
    )

    # Broadcast to WebSocket clients subscribed to this symbol
    broadcast_pattern(event)
```

### Indicator Events

```python
# Channel: tickstock:indicators:streaming
# Message Format:
{
    "indicator_name": "RSI",
    "symbol": "AAPL",
    "timeframe": "1min",
    "value": 68.5,
    "calculated_at": 1234567890.123,
    "metadata": {
        "period": 14,
        "source": "close"
    }
}

def handle_indicator_event(event: dict):
    """Handle indicator calculation event."""
    indicator_name = event.get('indicator_name')
    symbol = event.get('symbol')
    value = event.get('value')

    logger.info(
        f"Indicator: {indicator_name} | Symbol: {symbol} | Value: {value}"
    )

    # Broadcast to WebSocket
    broadcast_indicator(event)
```

### Health Metrics Events

```python
# Channel: tickstock:streaming:health
# Message Format:
{
    "status": "healthy",
    "uptime_seconds": 3600,
    "symbols_processed": 4200,
    "patterns_detected": 156,
    "indicators_calculated": 8400,
    "timestamp": 1234567890.123
}

def handle_health_event(event: dict):
    """Handle TickStockPL health metrics."""
    status = event.get('status')
    symbols_processed = event.get('symbols_processed', 0)

    logger.info(
        f"TickStockPL Health: {status} | "
        f"Symbols Processed: {symbols_processed}"
    )

    # Update health dashboard
    update_health_metrics(event)
```

---

## 7. Error Handling Patterns

### Redis Operation Error Handling

```python
import redis

def safe_redis_operation(client: redis.Redis, operation: str, *args, **kwargs):
    """
    Execute Redis operation with error handling.

    Args:
        client: Redis client
        operation: Operation name (get, set, publish, etc.)
        *args, **kwargs: Operation arguments

    Returns:
        Operation result or None on error
    """
    try:
        # Get operation method
        op = getattr(client, operation)

        # Execute operation
        result = op(*args, **kwargs)

        return result

    except redis.ConnectionError as e:
        logger.error(f"Redis connection error during {operation}: {e}")
        return None

    except redis.TimeoutError as e:
        logger.error(f"Redis timeout during {operation}: {e}")
        return None

    except redis.RedisError as e:
        logger.error(f"Redis error during {operation}: {e}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error during {operation}: {e}")
        logger.exception("Full traceback:")
        return None


# Usage
value = safe_redis_operation(client, 'get', 'my_key')
if value:
    process(value)
else:
    logger.warning("Redis operation failed - using fallback")
    fallback()
```

---

## 8. Performance Patterns

### Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Redis ping | <10ms | `client.ping()` with timing |
| Pub-sub message delivery | <10ms | Redis → callback timing |
| WebSocket broadcast | <100ms | Redis → browser delivery |
| Pattern event processing | <50ms | Receive → store → broadcast |

### Performance Monitoring Pattern

```python
import time

def monitor_redis_latency(client: redis.Redis):
    """Monitor Redis operation latency."""
    operations = ['ping', 'get', 'set']

    for operation in operations:
        start_time = time.time()

        if operation == 'ping':
            client.ping()
        elif operation == 'get':
            client.get('test_key')
        elif operation == 'set':
            client.set('test_key', 'test_value', ex=60)

        latency_ms = (time.time() - start_time) * 1000

        if latency_ms > 10:
            logger.warning(
                f"Slow Redis {operation}: {latency_ms:.2f}ms (target: <10ms)"
            )
        else:
            logger.debug(f"Redis {operation}: {latency_ms:.2f}ms")
```

---

## 9. Testing Patterns

### Mock Redis for Testing

```python
import pytest
from unittest.mock import Mock
import redis

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock = Mock(spec=redis.Redis)
    mock.ping.return_value = True
    mock.get.return_value = 'test_value'
    mock.set.return_value = True
    mock.publish.return_value = 1  # Number of subscribers
    return mock


def test_redis_subscriber(mock_redis):
    """Test Redis subscriber with mock."""
    from src.core.services.redis_event_subscriber import RedisEventSubscriber

    subscriber = RedisEventSubscriber(mock_redis)

    # Mock pubsub
    mock_pubsub = Mock()
    mock_redis.pubsub.return_value = mock_pubsub

    # Simulate message
    mock_pubsub.listen.return_value = [
        {'type': 'pmessage', 'data': '{"pattern_name": "doji", "symbol": "AAPL"}'}
    ]

    # Subscribe
    events_received = []
    subscriber.subscribe(lambda e: events_received.append(e))

    # Verify
    assert len(events_received) == 1
    assert events_received[0]['pattern_name'] == 'doji'
```

### Integration Testing with Real Redis

```python
import pytest
import redis
import os

@pytest.fixture(scope='module')
def redis_client():
    """Real Redis client for integration tests."""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/1')  # Test DB 1
    client = redis.from_url(redis_url, decode_responses=True)

    # Clean test database
    client.flushdb()

    yield client

    # Cleanup
    client.flushdb()
    client.close()


def test_pubsub_integration(redis_client):
    """Test Redis pub-sub with real Redis."""
    pubsub = redis_client.pubsub()
    pubsub.subscribe('test_channel')

    # Publish message
    redis_client.publish('test_channel', 'test_message')

    # Receive message
    message = pubsub.get_message(timeout=1)
    assert message is not None
    assert message['data'] == 'test_message'
```

---

## Summary Checklist

When working with Redis in TickStock, verify:

- [ ] Used correct channel pattern (tickstock:domain:event)
- [ ] Converted typed events to dicts at Worker boundary
- [ ] Handled JSON parsing errors (try-except JSONDecodeError)
- [ ] Validated message format (required fields present)
- [ ] Used `broadcast=True` for WebSocket multi-client delivery
- [ ] Implemented reconnection logic for subscribers
- [ ] Logged errors with context (channel, message data)
- [ ] Met performance targets (<10ms Redis, <100ms WebSocket)
- [ ] Cleaned up subscriptions on disconnect
- [ ] Tested with both mock and real Redis

---

## Common Gotchas

❌ **Don't mix typed events and dicts** - Always convert to dict at Worker boundary
❌ **Don't forget broadcast=True** - WebSocket won't reach all clients
❌ **Don't swallow JSON parse errors** - Log and continue subscription
❌ **Don't block in event handlers** - Keep processing fast (<50ms)
❌ **Don't hardcode channel names** - Use constants from redis_config.py

✅ **Do validate message format** - Check required fields before processing
✅ **Do implement reconnection** - Redis connections can drop
✅ **Do monitor performance** - Log slow operations (>10ms)
✅ **Do use room-based routing** - Send events only to interested clients
✅ **Do clean up subscriptions** - Prevent memory leaks on disconnect
