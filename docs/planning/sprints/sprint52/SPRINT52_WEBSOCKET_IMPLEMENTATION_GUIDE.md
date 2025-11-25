# Sprint 52 WebSocket Admin Monitoring Dashboard
## Implementation Guide: Multi-Connection WebSocket Architecture Data Source Reference

**Document Purpose**: Complete reference guide for implementing the `/admin/websockets` monitoring dashboard in Sprint 52.

**Status**: Ready for Implementation  
**Last Updated**: January 21, 2025

---

## Part 1: Core Data Source - WebSocketConnectionManager

### Primary File Location
```
C:\Users\McDude\TickStockAppV2\src\infrastructure\websocket\multi_connection_manager.py
```

### Class Definition: `MultiConnectionManager`

**Responsibility**: Manages up to 3 concurrent WebSocket connections to Massive API with unified interface.

**Drop-in Replacement Pattern**:
- Implements same interface as `MassiveWebSocketClient` for backward compatibility
- Seamless multi-connection scaling without changing consumer code
- Single entry point for all WebSocket operations

### Connection State Data: `ConnectionInfo` Dataclass

**Location in File**: Lines 21-32

```python
@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    
    connection_id: str                           # Format: "connection_1", "connection_2", "connection_3"
    name: str                                    # Display name: "primary", "secondary", "tertiary"
    client: MassiveWebSocketClient | None        # Actual WebSocket client instance
    assigned_tickers: set[str]                   # Set of ticker symbols on this connection
    status: str = "disconnected"                 # States: "disconnected", "connecting", "connected", "error"
    message_count: int = 0                       # Total ticks received from this connection
    error_count: int = 0                         # Total errors on this connection
    last_message_time: float = 0.0               # Unix timestamp of last tick received
```

---

## Part 2: Configuration Loading Pattern

### Configuration File Source
```
C:\Users\McDude\TickStockAppV2\.env  (checked via config dict)
```

### Configuration Keys

**Global Settings**:
```python
USE_MULTI_CONNECTION = true|false               # Enable/disable multi-connection mode
WEBSOCKET_CONNECTIONS_MAX = 3                   # Max concurrent connections (Massive API limit)
MASSIVE_API_KEY = "your_api_key"               # API key for Massive WebSocket
```

**Per-Connection Settings** (repeat for connections 1, 2, 3):
```python
# Connection 1
WEBSOCKET_CONNECTION_1_ENABLED = true|false     # Enable this connection
WEBSOCKET_CONNECTION_1_NAME = "primary"         # Display name
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY = "market_leaders:top_500"  # Universe source (preferred)
WEBSOCKET_CONNECTION_1_SYMBOLS = "AAPL,NVDA,TSLA"  # Direct symbols (fallback)

# Connection 2
WEBSOCKET_CONNECTION_2_ENABLED = true|false
WEBSOCKET_CONNECTION_2_NAME = "secondary"
WEBSOCKET_CONNECTION_2_UNIVERSE_KEY = "finance_sector:large_cap"
# ... repeat pattern ...

# Connection 3
WEBSOCKET_CONNECTION_3_ENABLED = false
WEBSOCKET_CONNECTION_3_NAME = "tertiary"
# ... repeat pattern ...
```

### Configuration Reading Implementation

**Method**: `_initialize_configured_connections()` (Lines 99-130)

```python
def _initialize_configured_connections(self):
    """Initialize connections based on config settings."""
    for conn_num in range(1, self.max_connections + 1):
        enabled_key = f"WEBSOCKET_CONNECTION_{conn_num}_ENABLED"
        name_key = f"WEBSOCKET_CONNECTION_{conn_num}_NAME"
        
        if self.config.get(enabled_key, False):  # Check if enabled
            # Load tickers via universe key or direct symbols
            tickers = self._load_tickers_for_connection(conn_num)
            
            # Store ConnectionInfo with configuration
            self.connections[connection_id] = ConnectionInfo(
                connection_id=connection_id,
                name=connection_name,
                assigned_tickers=set(tickers),
            )
```

**Ticker Loading Method**: `_load_tickers_for_connection()` (Lines 132-196)

```python
def _load_tickers_for_connection(self, connection_num: int) -> list[str]:
    """
    Load ticker list for a connection using SYMBOL_UNIVERSE_KEY approach.
    
    Priority:
    1. Universe Key (WEBSOCKET_CONNECTION_N_UNIVERSE_KEY) - Preferred method
    2. Direct Symbols (WEBSOCKET_CONNECTION_N_SYMBOLS) - Fallback
    
    Returns:
        list[str]: Ticker symbols
    """
    universe_key_config = f"WEBSOCKET_CONNECTION_{connection_num}_UNIVERSE_KEY"
    symbols_config = f"WEBSOCKET_CONNECTION_{connection_num}_SYMBOLS"
    
    # 1. Try universe key first (queries cache for ticker list)
    if universe_key:
        from src.infrastructure.cache.cache_control import CacheControl
        cache = CacheControl()
        universe_tickers = cache.get_universe_tickers(universe_key)
        return universe_tickers  # Returns loaded tickers
    
    # 2. Fallback to direct symbols
    if direct_symbols:
        tickers = [s.strip() for s in direct_symbols.split(",")]
        return tickers
    
    return []  # No configuration found
```

---

## Part 3: Health Status & Metrics API

### Primary Method: `get_health_status()`

**Location**: Lines 385-411  
**Return Type**: `dict`

```python
def get_health_status(self) -> dict:
    """
    Get health status of all connections.
    
    Returns:
        {
            "total_connections": 3,           # Total configured connections
            "connected_count": 2,              # How many are currently connected
            "total_ticks_received": 1000,      # Aggregate ticks across all connections
            "total_errors": 5,                 # Aggregate errors across all connections
            "connections": {
                "connection_1": {
                    "name": "primary",
                    "status": "connected",                    # disconnected|connecting|connected|error
                    "assigned_tickers": 150,                  # Count of tickers on this connection
                    "message_count": 750,                     # Total ticks received on this connection
                    "error_count": 0,
                    "last_message_time": 1705853696.123,      # Unix timestamp (seconds since epoch)
                },
                "connection_2": {
                    "name": "secondary",
                    "status": "connected",
                    "assigned_tickers": 85,
                    "message_count": 250,
                    "error_count": 5,
                    "last_message_time": 1705853695.456,
                },
                "connection_3": {
                    "name": "tertiary",
                    "status": "disconnected",
                    "assigned_tickers": 0,
                    "message_count": 0,
                    "error_count": 0,
                    "last_message_time": 0.0,
                }
            }
        }
    """
```

### Per-Connection Status Tracking

**ConnectionInfo Fields** (stored in `connections` dict):
- `status`: One of: `"disconnected"`, `"connecting"`, `"connected"`, `"error"`
- `message_count`: Incremented in `_aggregate_tick_callback()` (Line 340)
- `error_count`: Incremented in `_aggregate_status_callback()` (Line 369)
- `last_message_time`: Updated in `_aggregate_tick_callback()` (Line 341)

**Status State Transitions**:
- Initialization: `"disconnected"` (default)
- During connection: `"connecting"` (Line 232)
- Success: `"connected"` (Line 235)
- Failure: `"error"` (Lines 247, 251)
- Manual disconnect: `"disconnected"` (Line 278)

---

## Part 4: Additional Utility Methods

### Method: `get_ticker_assignment()`

**Location**: Lines 450-460  
**Purpose**: Find which connection a ticker is routed to

```python
def get_ticker_assignment(self, ticker: str) -> str | None:
    """
    Get which connection a ticker is assigned to.
    
    Args:
        ticker: Ticker symbol (e.g., "AAPL")
    
    Returns:
        str: Connection ID (e.g., "connection_1") or None if not assigned
    
    Example:
        conn_id = manager.get_ticker_assignment("AAPL")
        # Returns: "connection_1"
    """
    return self.ticker_to_connection.get(ticker)
```

### Method: `get_connection_tickers()`

**Location**: Lines 462-474  
**Purpose**: Get all tickers on a specific connection

```python
def get_connection_tickers(self, connection_id: str) -> set[str]:
    """
    Get all tickers assigned to a specific connection.
    
    Args:
        connection_id: Connection identifier (e.g., "connection_1")
    
    Returns:
        set[str]: Set of ticker symbols
    
    Example:
        tickers = manager.get_connection_tickers("connection_1")
        # Returns: {"AAPL", "NVDA", "TSLA", ...}
    """
    if connection_id in self.connections:
        return self.connections[connection_id].assigned_tickers.copy()
    return set()
```

### Method: `subscribe()`

**Location**: Lines 283-323  
**Purpose**: Add tickers to connections dynamically

```python
def subscribe(self, tickers: list[str]) -> bool:
    """
    Subscribe to additional tickers (routes across connections).
    
    Args:
        tickers: List of ticker symbols
    
    Returns:
        bool: True if at least one subscription succeeds
    
    Note:
        Currently uses first-available routing strategy
        TODO: Implement load-balanced routing
    """
```

---

## Part 5: Data Access from Flask Routes

### Integration Path: Flask Route → MarketDataService → RealTimeDataAdapter → MultiConnectionManager

**Full Integration Chain**:

```
Flask Route
  ↓
from src.app import market_service (global)
  ↓
market_service.data_adapter (RealTimeDataAdapter instance)
  ↓
market_service.data_adapter.client (MultiConnectionManager instance)
  ↓
client.get_health_status() / get_connection_tickers() / etc.
```

### Step 1: Access Global MarketDataService

**In Flask Route** (e.g., `src/api/routes/admin.py`):

```python
from src.app import market_service

def get_websocket_status():
    """Get WebSocket connection status."""
    if not market_service:
        return {"error": "Service not initialized"}, 500
    
    if not market_service.data_adapter:
        return {"error": "Data adapter not initialized"}, 500
    
    # Continue to next step...
```

### Step 2: Access the MultiConnectionManager

**From RealTimeDataAdapter**:

```python
# Get the client (which is MultiConnectionManager if multi-connection enabled)
client = market_service.data_adapter.client

# Check if it's a MultiConnectionManager
if hasattr(client, 'get_health_status'):  # Duck typing check
    # It's either MultiConnectionManager or single MassiveWebSocketClient
    health = client.get_health_status()
    # Use health data...
else:
    # Single-connection mode (backward compat)
    pass
```

### Step 3: Query Connection Status

**Complete Example Route**:

```python
@app.route('/api/admin/websocket-status')
@login_required
@admin_required  # Add admin auth decorator
def get_websocket_status():
    """
    GET /api/admin/websocket-status
    
    Returns detailed status of all WebSocket connections.
    """
    from src.app import market_service
    
    try:
        if not market_service or not market_service.data_adapter:
            return jsonify({"error": "Services not initialized"}), 500
        
        # Get the WebSocket client
        client = market_service.data_adapter.client
        
        # Query health status
        if hasattr(client, 'get_health_status'):
            health = client.get_health_status()
            
            # Transform for frontend
            response = {
                "connections": [],
                "summary": {
                    "total": health['total_connections'],
                    "connected": health['connected_count'],
                    "ticks_total": health['total_ticks_received'],
                    "errors_total": health['total_errors']
                }
            }
            
            # Build per-connection data
            for conn_id, conn_info in health['connections'].items():
                connection_num = int(conn_id.split('_')[1])
                
                response['connections'].append({
                    "id": connection_num,
                    "connection_id": conn_id,
                    "name": conn_info['name'],
                    "enabled": client.connections[conn_id].client is not None,
                    "connected": conn_info['status'] == 'connected',
                    "status": conn_info['status'],
                    "config": {
                        "ticker_count": conn_info['assigned_tickers'],
                        "tickers": sorted(list(
                            client.get_connection_tickers(conn_id)
                        ))
                    },
                    "metrics": {
                        "messages_per_second": calculate_mps(
                            conn_info['message_count'],
                            start_time
                        ),
                        "last_update": conn_info['last_message_time'],
                        "error_count": conn_info['error_count']
                    }
                })
            
            return jsonify(response)
        else:
            # Single connection mode
            return jsonify({"error": "Not in multi-connection mode"})
    
    except Exception as e:
        logger.error(f"Failed to get WebSocket status: {e}")
        return jsonify({"error": str(e)}), 500
```

---

## Part 6: RealTimeDataAdapter Integration

### File Location
```
C:\Users\McDude\TickStockAppV2\src\infrastructure\data_sources\adapters\realtime_adapter.py
```

### Multi-Connection Detection (Lines 33-48)

```python
def __init__(self, config: dict, tick_callback: Callable, status_callback: Callable):
    self.config = config
    self.tick_callback = tick_callback
    self.status_callback = status_callback
    self.client = None
    
    # Check for multi-connection mode (Sprint 51)
    use_multi_connection = config.get("USE_MULTI_CONNECTION", False)
    
    if use_multi_connection:
        # MULTI-CONNECTION MODE (up to 3 connections)
        from src.infrastructure.websocket.multi_connection_manager import (
            MultiConnectionManager,
        )
        
        self.client = MultiConnectionManager(
            config=config,
            on_tick_callback=self.tick_callback,
            on_status_callback=self.status_callback,
            max_connections=config.get("WEBSOCKET_CONNECTIONS_MAX", 3),
        )
        logger.info("REAL-TIME-ADAPTER: Initialized with Multi-Connection Manager")
    else:
        # SINGLE CONNECTION MODE (backward compatible)
        self.client = MassiveWebSocketClient(...)
        logger.info("REAL-TIME-ADAPTER: Initialized with single Massive WebSocket client")
```

**Key Property**: `self.client` can be either:
- `MultiConnectionManager` (if `USE_MULTI_CONNECTION=true`)
- `MassiveWebSocketClient` (if `USE_MULTI_CONNECTION=false`)

Both implement same interface, so code is backward compatible.

---

## Part 7: MarketDataService Connection

### File Location
```
C:\Users\McDude\TickStockAppV2\src\core\services\market_data_service.py
```

### Data Adapter Initialization (Lines 107-125)

```python
def _init_data_adapter(self):
    """Initialize the appropriate data adapter."""
    use_synthetic = self.config.get('USE_SYNTHETIC_DATA', False)
    use_massive = self.config.get('USE_MASSIVE_API', False)
    
    if use_massive and self.config.get('MASSIVE_API_KEY'):
        logger.info("MARKET-DATA-SERVICE: Initializing Massive WebSocket adapter")
        self.data_adapter = RealTimeDataAdapter(
            config=self.config,
            tick_callback=self._handle_tick_data,
            status_callback=self._handle_status_update
        )
    else:
        # Fallback to synthetic data
        self.data_adapter = SyntheticDataAdapter(...)
```

### Global Access Point

**In `src/app.py`** (Line 79):
```python
# Global application components
app = None
market_service = None  # <-- This is the global reference
redis_client = None
socketio = None
```

The `market_service` is set during Flask app initialization and is accessible globally via:
```python
from src.app import market_service
```

---

## Part 8: Real-Time Data Flow for Dashboard

### Redis Tick Channel

**Channel**: `tickstock:market:ticks`  
**Source**: MarketDataService publishes raw ticks (Line 241-244)
**Publish Pattern**:

```python
market_tick = {
    'type': 'market_tick',
    'symbol': tick_data.ticker,
    'price': tick_data.price,
    'volume': tick_data.volume or 0,
    'timestamp': tick_data.timestamp,
    'source': 'massive'
}
self.data_publisher.redis_client.publish(
    'tickstock:market:ticks',
    json.dumps(market_tick)
)
```

**Dashboard Usage**: Subscribe to this channel to display live ticker updates in real-time.

---

## Part 9: Testing Reference

### Unit Tests Location
```
C:\Users\McDude\TickStockAppV2\tests\data_source\unit\test_multi_connection_manager.py
```

### Test Class Hierarchy

**TestMultiConnectionManagerInit** (Lines 18-102)
- Tests configuration loading
- Tests ticker distribution
- Tests multi-connection setup

**TestMultiConnectionManagerConnect** (Lines 104-176)
- Tests connection lifecycle
- Tests partial failures
- Tests status transitions

**TestMultiConnectionManagerCallbacks** (Lines 178-243)
- Tests tick/status aggregation
- Tests callback routing

**TestMultiConnectionManagerSubscription** (Lines 245-287)
- Tests dynamic ticker subscription
- Tests routing logic

**TestMultiConnectionManagerHealth** (Lines 289-334)
- Tests `get_health_status()` accuracy
- Tests metrics collection

### Key Test Patterns

```python
# 1. Mock configuration
config = {
    'USE_MULTI_CONNECTION': True,
    'MASSIVE_API_KEY': 'test_key',
    'WEBSOCKET_CONNECTION_1_ENABLED': True,
    'WEBSOCKET_CONNECTION_1_SYMBOLS': 'AAPL,NVDA,TSLA',
    'WEBSOCKET_CONNECTION_2_ENABLED': False,
    'WEBSOCKET_CONNECTION_3_ENABLED': False
}

# 2. Create manager
manager = MultiConnectionManager(config, Mock(), Mock())

# 3. Assert configuration
assert len(manager.connections) == 1
assert 'connection_1' in manager.connections
conn = manager.connections['connection_1']
assert conn.assigned_tickers == {'AAPL', 'NVDA', 'TSLA'}

# 4. Query health
health = manager.get_health_status()
assert health['total_connections'] == 1
assert health['connections']['connection_1']['status'] == 'connected'
```

---

## Part 10: Implementation Checklist for Sprint 52

### Phase 1: Backend Setup

- [ ] Create `/api/admin/websocket-status` endpoint
  - Query `market_service.data_adapter.client.get_health_status()`
  - Format response per Sprint 52 README spec
  - Add admin authentication check

- [ ] Create `/admin/websockets` route
  - Serve template `web/templates/admin/websockets.html`
  - Add admin authentication check

- [ ] Create WebSocket namespace `/admin-ws`
  - Subscribe to `tickstock:market:ticks` Redis channel
  - Route tick events to frontend by connection ID
  - Broadcast connection status updates

### Phase 2: Frontend Implementation

- [ ] Create `web/templates/admin/websockets.html`
  - Three-column layout (connections 1, 2, 3)
  - Real-time status indicators
  - Live ticker display with scrolling
  - Metrics counters

- [ ] Implement JavaScript WebSocket client
  - Connect to `/admin-ws` namespace
  - Handle `connection_status_update` events
  - Handle `tick_update` events
  - Update DOM with minimal flicker

### Phase 3: Testing

- [ ] Unit tests for admin routes
- [ ] Integration tests for full dashboard
- [ ] Manual testing with single/multi-connection modes
- [ ] Performance validation (no impact on production)

### Phase 4: Documentation

- [ ] Update `docs/guides/admin.md`
- [ ] Create `SPRINT52_COMPLETE.md`
- [ ] Update `CLAUDE.md` with completion status

---

## Part 11: Key Code Snippets for Reference

### Accessing MultiConnectionManager from Route

```python
from src.app import market_service

def query_websocket_status():
    client = market_service.data_adapter.client
    
    # Check if multi-connection or single
    if hasattr(client, 'get_health_status'):
        health = client.get_health_status()
        return format_response(health)
```

### Computing Metrics

```python
def calculate_messages_per_second(conn_info, elapsed_seconds):
    """Calculate messages/sec from connection info."""
    if elapsed_seconds > 0:
        return conn_info['message_count'] / elapsed_seconds
    return 0.0

def calculate_uptime(conn_info, start_time):
    """Calculate connection uptime."""
    if conn_info['last_message_time'] > 0:
        elapsed = time.time() - conn_info['last_message_time']
        return elapsed  # Seconds since last message
    return 0.0

def get_connection_status_color(status_str):
    """Map status to color for UI."""
    colors = {
        'connected': 'green',
        'disconnected': 'red',
        'connecting': 'yellow',
        'error': 'red'
    }
    return colors.get(status_str, 'gray')
```

### Thread-Safe Metrics Reading

```python
# get_health_status() already uses self._lock (RLock) for thread safety
health = manager.get_health_status()  # Safe to call from any thread

# ConnectionInfo fields are updated atomically within the lock
# by _aggregate_tick_callback() and _aggregate_status_callback()
```

---

## Part 12: Common Issues & Solutions

### Issue 1: MultiConnectionManager not available

**Symptom**: `AttributeError: 'MassiveWebSocketClient' has no attribute 'get_health_status'`

**Cause**: Single-connection mode enabled, but code expects multi-connection

**Solution**:
```python
client = market_service.data_adapter.client

# Duck typing check
if hasattr(client, 'get_health_status'):
    health = client.get_health_status()
else:
    # Single connection mode - create compatible response
    health = create_single_connection_response(client)
```

### Issue 2: Configuration not loading

**Symptom**: All connections show as disabled

**Cause**: Environment variables not set or config dict not loaded

**Solution**:
```python
# Verify config loading
print(config.get('USE_MULTI_CONNECTION'))
print(config.get('WEBSOCKET_CONNECTION_1_ENABLED'))

# Check if using CacheControl correctly
cache = CacheControl()
tickers = cache.get_universe_tickers('market_leaders:top_500')
print(f"Universe loaded: {len(tickers)} tickers")
```

### Issue 3: Metrics always zero

**Symptom**: `message_count`, `error_count` always 0

**Cause**: Connections initialized but never connected/subscribed

**Solution**:
```python
# Ensure connections are actually connected
client.connect()  # Establishes WebSocket connections
client.subscribe(tickers)  # Subscribes to receive tick data

# Then metrics will be populated as ticks arrive
```

---

## Part 13: Performance Characteristics

### Expected Metrics Range

| Metric | Typical Range | Notes |
|--------|---------------|-------|
| `message_count` | 0-100/sec per connection | Depends on ticker count and market activity |
| `error_count` | 0-2 during normal operation | Should remain low; investigate if increasing |
| `last_message_time` | Should be recent (< 1 sec ago) | Indicates if connection is active |
| `status` transition time | < 1 second | Connection should establish quickly |

### Memory Impact

- **Per ConnectionInfo**: ~500 bytes + size of ticker set
- **Per connection**: ~1KB base + (# tickers × 10 bytes)
- **For 3 connections with 150 tickers each**: ~4.5 KB total

### Thread Safety

- `get_health_status()` uses `threading.RLock()` (reentrant lock)
- Safe to call from multiple threads simultaneously
- Dashboard polling won't block WebSocket data reception

---

## Part 14: Related Files for Reference

### WebSocket Infrastructure
- `src/presentation/websocket/massive_client.py` - Single connection client
- `src/infrastructure/websocket/event_router.py` - Event routing logic
- `src/infrastructure/websocket/scalable_broadcaster.py` - Message broadcasting

### Data Publishing
- `src/presentation/websocket/data_publisher.py` - Redis tick publishing
- `src/presentation/websocket/publisher.py` - WebSocket event publishing

### Configuration
- `src/core/services/config_manager.py` - Configuration management
- `.env` - Environment variables

### Tests
- `tests/data_source/unit/test_realtime_adapter.py` - Adapter tests
- `tests/integration/test_websocket_patterns.py` - Integration tests

---

## Part 15: Deployment Checklist

- [ ] Verify `USE_MULTI_CONNECTION` setting in `.env`
- [ ] Verify `WEBSOCKET_CONNECTION_*` settings configured correctly
- [ ] Verify `MASSIVE_API_KEY` is set
- [ ] Run `python run_tests.py` to validate system
- [ ] Test dashboard access as admin user
- [ ] Verify no performance degradation
- [ ] Check logs for WebSocket connection messages
- [ ] Verify real-time ticker updates flowing

---

## Summary

The multi-connection WebSocket architecture is fully implemented and ready for the Sprint 52 monitoring dashboard. The `MultiConnectionManager` class provides:

1. **Configuration Management**: Reads connection settings from environment variables
2. **State Tracking**: Maintains status, metrics, and ticker assignments per connection
3. **Health Reporting**: `get_health_status()` returns comprehensive connection status
4. **Thread-Safe Access**: Uses RLock for concurrent access from Flask routes

The dashboard will query this manager to display real-time connection status, configuration, and live ticker data.

---

**Questions?** Refer to the specific line numbers and method signatures provided above, or check the test file for concrete usage examples.
