# Sprint 52: Quick Reference Guide
## WebSocket Admin Dashboard Implementation

---

## TL;DR - The Data Source

**What**: `MultiConnectionManager` class manages up to 3 concurrent WebSocket connections  
**Where**: `src/infrastructure/websocket/multi_connection_manager.py`  
**How to Access**: 
```python
from src.app import market_service
client = market_service.data_adapter.client  # This is the MultiConnectionManager
health = client.get_health_status()  # Get all connection status/metrics
```

---

## File Map

```
✅ CORE IMPLEMENTATION
  src/infrastructure/websocket/multi_connection_manager.py
     ├─ MultiConnectionManager (main class)
     ├─ ConnectionInfo (per-connection state)
     ├─ get_health_status() - PRIMARY METHOD FOR DASHBOARD
     ├─ get_ticker_assignment() - Find which connection a ticker is on
     └─ get_connection_tickers() - Get all tickers on a connection

✅ DATA ADAPTER (Integration Layer)
  src/infrastructure/data_sources/adapters/realtime_adapter.py
     ├─ RealTimeDataAdapter.__init__ - Creates MultiConnectionManager if enabled
     └─ self.client - Points to MultiConnectionManager or MassiveWebSocketClient

✅ SERVICE LAYER (Global Access)
  src/core/services/market_data_service.py
     └─ Initializes and owns the data_adapter

✅ APP (Global Access Point)
  src/app.py
     └─ market_service (global) - Access point for routes

✅ TESTS (Reference Implementation)
  tests/data_source/unit/test_multi_connection_manager.py
     └─ Complete usage examples

✅ SPRINT 52 REQUIREMENTS
  docs/planning/sprints/sprint52/README.md
     └─ Dashboard specification and requirements
```

---

## Configuration Reference

**Enable Multi-Connection Mode**:
```env
USE_MULTI_CONNECTION=true
WEBSOCKET_CONNECTIONS_MAX=3
MASSIVE_API_KEY=your_api_key_here
```

**Configure Each Connection** (repeat for 1, 2, 3):
```env
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=primary
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=market_leaders:top_500
WEBSOCKET_CONNECTION_1_SYMBOLS=AAPL,NVDA,TSLA  # fallback if universe fails
```

---

## Data Structure Reference

### get_health_status() Response

```python
{
    "total_connections": 3,
    "connected_count": 2,
    "total_ticks_received": 1000,
    "total_errors": 5,
    "connections": {
        "connection_1": {
            "name": "primary",
            "status": "connected",  # disconnected|connecting|connected|error
            "assigned_tickers": 150,  # count
            "message_count": 750,  # total ticks from this connection
            "error_count": 0,
            "last_message_time": 1705853696.123,  # unix timestamp
        },
        "connection_2": {...},
        "connection_3": {...}
    }
}
```

### ConnectionInfo Fields

```python
connection_id: str           # "connection_1", "connection_2", "connection_3"
name: str                    # "primary", "secondary", "tertiary"
status: str                  # "disconnected", "connecting", "connected", "error"
assigned_tickers: set[str]   # {"AAPL", "NVDA", "TSLA", ...}
message_count: int           # Total ticks received
error_count: int             # Total errors
last_message_time: float     # Unix timestamp (seconds)
```

---

## API Endpoints to Implement

### Endpoint 1: Get WebSocket Status
```
GET /api/admin/websocket-status
Content-Type: application/json
Authorization: Admin only

Response:
{
    "connections": [
        {
            "id": 1,
            "name": "primary",
            "enabled": true,
            "connected": true,
            "status": "connected",
            "config": {
                "ticker_count": 150,
                "universe_key": "market_leaders:top_500",
                "tickers": ["AAPL", "NVDA", ...]
            },
            "metrics": {
                "messages_per_second": 25.3,
                "last_update": 1705853696.123,
                "error_count": 0
            }
        },
        {...},
        {...}
    ],
    "summary": {
        "total": 3,
        "connected": 2,
        "ticks_total": 1000,
        "errors_total": 5
    }
}
```

### Endpoint 2: Render Dashboard
```
GET /admin/websockets
Content-Type: text/html
Authorization: Admin only

Response: HTML page from web/templates/admin/websockets.html
```

---

## WebSocket Events (Browser → Backend)

**Connect**:
```javascript
socket.emit('connect', {})
```

**Subscribe to Updates**:
```javascript
socket.on('connection_status_update', (data) => {
    // data = {connection_id, status, timestamp}
    updateStatusIndicator(data.connection_id, data.status)
})

socket.on('tick_update', (data) => {
    // data = {connection_id, symbol, price, timestamp}
    displayTickInColumn(data.connection_id, data.symbol, data.price)
})

socket.on('metrics_update', (data) => {
    // data = {connection_id, msgs_per_sec, uptime}
    updateMetrics(data.connection_id, data)
})
```

---

## Implementation Steps

### Step 1: Create Backend Endpoint (2 hours)

```python
# In src/api/routes/admin.py (or create new file)

from src.app import market_service
from flask import jsonify, render_template
from flask_login import login_required

@app.route('/api/admin/websocket-status')
@login_required
@admin_required
def get_websocket_status():
    """Query MultiConnectionManager for current status."""
    client = market_service.data_adapter.client
    
    if hasattr(client, 'get_health_status'):
        health = client.get_health_status()
        # Format and return
        return jsonify(transform_health_to_response(health))
    
    return jsonify({"error": "Multi-connection not enabled"}), 400

@app.route('/admin/websockets')
@login_required
@admin_required
def websockets_dashboard():
    """Render dashboard template."""
    return render_template('admin/websockets.html')
```

### Step 2: Create Frontend Template (3 hours)

```html
<!-- web/templates/admin/websockets.html -->
<div class="websocket-dashboard">
  <div class="container">
    <h1>WebSocket Connections Monitor</h1>
    
    <!-- Three columns, one per connection -->
    <div class="row">
      <div class="col-md-4">
        <div class="connection-card" id="connection-1">
          <!-- Status indicator -->
          <!-- Configuration display -->
          <!-- Live ticker data -->
          <!-- Metrics counters -->
        </div>
      </div>
      <!-- Repeat for connection-2, connection-3 -->
    </div>
  </div>
</div>

<script>
// Connect to WebSocket
const socket = io.connect('http://localhost:5000', {
  namespace: '/admin-ws'
});

// Load initial status
fetch('/api/admin/websocket-status')
  .then(r => r.json())
  .then(data => {
    updateDashboard(data);
    subscribeToUpdates();
  });

// Handle real-time updates
socket.on('tick_update', (data) => {
  displayTick(data.connection_id, data.symbol, data.price);
});
</script>
```

### Step 3: Create WebSocket Handler (2 hours)

```python
# In src/app.py or new file

@socketio.on('connect', namespace='/admin-ws')
@login_required
@admin_required
def admin_ws_connect():
    """Admin WebSocket connection handler."""
    logger.info(f"Admin dashboard connected: {request.sid}")
    
    # Subscribe to Redis tick channel
    # Broadcast connection status updates every second
    
@socketio.on('disconnect', namespace='/admin-ws')
def admin_ws_disconnect():
    logger.info(f"Admin dashboard disconnected: {request.sid}")

def broadcast_connection_updates():
    """Background task to broadcast status updates."""
    while True:
        client = market_service.data_adapter.client
        health = client.get_health_status()
        
        socketio.emit('connection_status_update', 
                     {'health': health},
                     namespace='/admin-ws')
        
        time.sleep(1)  # Update every second
```

### Step 4: Test & Validate (2 hours)

```bash
# Run all tests
python run_tests.py

# Test single connection mode
USE_MULTI_CONNECTION=false python app.py
# Dashboard should show only connection 1 as enabled

# Test multi-connection mode
USE_MULTI_CONNECTION=true python app.py
# Dashboard should show all 3 connections with their status
```

---

## Key Methods Cheat Sheet

| Method | Returns | Use Case |
|--------|---------|----------|
| `get_health_status()` | `dict` | Get all connection status and metrics |
| `get_ticker_assignment(ticker)` | `str` or `None` | Find which connection has a ticker |
| `get_connection_tickers(conn_id)` | `set[str]` | List all tickers on a connection |
| `connect()` | `bool` | Establish all connections (auto-called) |
| `disconnect()` | `None` | Close all connections |
| `subscribe(tickers)` | `bool` | Add tickers dynamically |

---

## Common Gotchas

### ❌ Wrong: Direct import of MultiConnectionManager
```python
from src.infrastructure.websocket.multi_connection_manager import MultiConnectionManager
```

### ✅ Right: Access through service chain
```python
from src.app import market_service
client = market_service.data_adapter.client  # This IS the manager
```

---

### ❌ Wrong: Assuming single-connection always has get_health_status()
```python
health = market_service.data_adapter.client.get_health_status()  # May fail if not multi-connection
```

### ✅ Right: Duck-type check
```python
client = market_service.data_adapter.client
if hasattr(client, 'get_health_status'):
    health = client.get_health_status()
else:
    # Single connection mode fallback
    pass
```

---

### ❌ Wrong: Assuming tickers are loaded immediately
```python
manager = MultiConnectionManager(config, callback, callback)
# manager.connections['connection_1'].assigned_tickers is empty!
```

### ✅ Right: Tickers loaded during init
```python
manager = MultiConnectionManager(config, callback, callback)
# Tickers already loaded from universe key or direct symbols
print(manager.connections['connection_1'].assigned_tickers)  # Has tickers
```

---

## Testing Quick Start

```python
import pytest
from unittest.mock import Mock, patch

def test_dashboard_status():
    """Test getting WebSocket status for dashboard."""
    config = {
        'USE_MULTI_CONNECTION': True,
        'MASSIVE_API_KEY': 'test',
        'WEBSOCKET_CONNECTION_1_ENABLED': True,
        'WEBSOCKET_CONNECTION_1_SYMBOLS': 'AAPL,NVDA'
    }
    
    manager = MultiConnectionManager(config, Mock(), Mock())
    health = manager.get_health_status()
    
    assert health['total_connections'] == 1
    assert health['connections']['connection_1']['assigned_tickers'] == 2
    assert 'name' in health['connections']['connection_1']
```

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Dashboard Load Time | <2 seconds |
| Status Update Latency | <500ms |
| Concurrent Tickers Displayed | 300+ |
| Messages/sec Peak | 100+ |

---

## Rollback Plan

If issues arise:

```bash
# Remove the admin route
git revert <commit-hash>

# OR disable via environment
ADMIN_WEBSOCKET_DASHBOARD_ENABLED=false
```

Recovery time: < 5 minutes (simple route removal)

---

## Questions?

Refer to the full implementation guide: `SPRINT52_WEBSOCKET_IMPLEMENTATION_GUIDE.md`

Key sections:
- **Part 3**: Health Status API details
- **Part 5**: Data access from Flask routes
- **Part 8**: Real-time data flow
- **Part 10**: Implementation checklist
