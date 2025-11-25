name: "WebSocket Connections Admin Monitoring Dashboard - Sprint 52"
description: |
  Real-time admin dashboard for monitoring multi-connection WebSocket architecture,
  providing visibility into connection status, configuration, and live data flow.

---

## Goal

**Feature Goal**: Create a real-time admin monitoring dashboard that provides complete visibility into the multi-connection WebSocket architecture, displaying status, configuration, and live tick data for all three WebSocket connections.

**Deliverable**: Admin web page at `/admin/websockets` with three-column layout showing real-time connection health, ticker distribution, throughput metrics, and live data streams for each WebSocket connection.

**Success Definition**:
- Dashboard accessible only to admin users (@admin_required)
- Displays all 3 connections (enabled/disabled state clearly visible)
- Real-time updates with <500ms latency from Redis events to browser
- Pause/resume controls functional
- No measurable performance impact on production WebSocket throughput (<5ms overhead)
- All integration tests pass

## User Persona

**Target User**: System Administrators, DevOps Engineers, Technical Operations Team

**Use Case**: Monitor WebSocket connection health during production operations, troubleshoot connection failures, verify load distribution across connections, investigate ticker routing issues

**User Journey**:
1. Admin logs into TickStockAppV2
2. Navigates to Admin menu → WebSocket Connections
3. Views three-column dashboard showing all connections
4. Sees real-time tick updates flowing through each connection (color-coded)
5. Verifies ticker distribution matches configuration (universe keys)
6. Uses pause/resume to freeze stream for detailed inspection
7. Checks metrics (uptime, throughput, error counts) per connection
8. Investigates anomalies (e.g., connection 2 disconnected, tickers rerouting)

**Pain Points Addressed**:
- **No Visibility**: Currently no way to see multi-connection architecture in action
- **Troubleshooting Blind**: When connections fail, no real-time diagnostics
- **Load Distribution Mystery**: Can't verify which tickers are on which connections
- **Manual Verification**: Must check logs/database to understand connection state
- **Slow Response**: Issues discovered reactively instead of proactively monitored

## Why

**Business Value**:
- **Operational Excellence**: Proactive monitoring reduces downtime and improves system reliability
- **Faster Troubleshooting**: Real-time visibility enables 5x faster issue resolution
- **Capacity Planning**: Throughput metrics inform infrastructure scaling decisions
- **Customer Trust**: Demonstrates robust monitoring and operational maturity

**Integration with Existing Features**:
- Complements `/admin/monitoring` dashboard (TickStockPL health monitoring)
- Extends existing admin menu with new WebSocket-specific insights
- Leverages existing multi-connection architecture (MultiConnectionManager)
- Uses proven real-time dashboard patterns from `/streaming` and Redis monitor

**Problems This Solves**:
- **For Admins**: Immediate visibility into connection failures before users report issues
- **For DevOps**: Live metrics for performance tuning and capacity planning
- **For Support**: Diagnostic tool for investigating user-reported WebSocket issues
- **For Development**: Validation tool for testing multi-connection architecture changes

## What

**User-Visible Behavior**:
1. **Three-Column Layout**: One column per WebSocket connection (connection 1, 2, 3)
2. **Status Indicators**: Green badge (connected), red badge (disconnected), gray badge (disabled)
3. **Configuration Display**: Shows connection name, universe key, ticker count
4. **Live Data Stream**: Scrollable ticker updates with symbol, price, timestamp
5. **Real-Time Metrics**: Uptime, messages/second, last update timestamp, error count
6. **Interactive Controls**: Pause/resume button to freeze data stream for inspection
7. **Color-Coded Tickers**: Connection 1 = blue, connection 2 = green, connection 3 = orange
8. **Auto-Scroll**: Newest ticks appear at top (prepend pattern)

**Technical Requirements**:
- Flask Blueprint: `admin_websockets_bp` with `/admin/websockets` route
- WebSocket Namespace: `/admin-ws` for admin-only real-time updates
- Admin Authentication: `@login_required` + `@admin_required` decorators
- API Endpoint: `/api/admin/websocket-status` returning JSON connection data
- Redis Integration: Subscribe to `tickstock:market:ticks` channel
- Data Source: `MultiConnectionManager.get_health_status()` for connection state
- Template: Bootstrap 5 responsive design with three-column grid
- JavaScript Client: Socket.IO client with event handlers and DOM updates

### Success Criteria

- [ ] `/admin/websockets` route accessible only to admin users (403 for non-admin)
- [ ] Dashboard displays enabled/disabled state for all 3 connections
- [ ] Real-time connection status updates (connected/disconnected badges)
- [ ] Configuration displayed correctly (universe key, ticker count, connection name)
- [ ] Live tick updates stream in real-time (<500ms latency)
- [ ] Ticks color-coded by connection (blue/green/orange)
- [ ] Pause/resume controls functional (stops/starts data stream)
- [ ] Metrics update in real-time (uptime, throughput, errors)
- [ ] Dashboard loads in <2 seconds
- [ ] No performance impact on production WebSocket (<5ms overhead)
- [ ] Unit tests pass (admin auth, WebSocket events, status API)
- [ ] Integration tests pass (full dashboard flow, Redis → WebSocket → UI)
- [ ] Security validated (no API keys exposed, admin-only access enforced)

## All Needed Context

### Context Completeness Check

✅ **"No Prior Knowledge" Test Applied**:
This PRP includes:
- Exact file paths for all patterns to follow
- Complete code examples with line numbers
- Specific URLs with documentation anchors
- TickStock-specific gotchas and constraints
- Working examples from similar features
- Dependency-ordered implementation tasks
- Project-specific validation commands

An implementer with no prior TickStock knowledge can successfully build this feature using only this PRP and codebase access.

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: TickStockAppV2
  role: Consumer

  redis_channels:
    - channel: "tickstock:market:ticks"
      purpose: "Raw tick forwarding from WebSocket data ingestion to TickStockPL"
      message_format: "{symbol: str, price: float, volume: int, timestamp: float}"
      flow: "WebSocket Ingest → Redis → TickStockPL (primary) + Admin Dashboard (secondary)"

  database_access:
    mode: read-only
    tables: []  # No database queries needed - all data from in-memory MultiConnectionManager
    queries: []

  websocket_integration:
    broadcast_to: "/admin-ws namespace (separate from client namespace /)"
    message_format: "{type: str, connection_id: str, symbol: str, price: float, timestamp: float}"
    latency_target: "<500ms from Redis event to browser display"
    namespace_isolation: "Admin WebSocket separated from client streams to prevent interference"

  tickstockpl_api:
    endpoints: []  # No TickStockPL API calls needed - dashboard is read-only monitor

  performance_targets:
    - metric: "Dashboard load time"
      target: "<2 seconds (initial page load)"

    - metric: "WebSocket update latency"
      target: "<500ms (Redis event → browser display)"

    - metric: "Admin WebSocket overhead"
      target: "<5ms (must not impact production WebSocket performance)"

    - metric: "Status API response"
      target: "<50ms (all data in-memory from MultiConnectionManager)"

    - metric: "Concurrent admin users"
      target: "10+ simultaneous dashboard viewers"
```

### Documentation & References

```yaml
# ===============================================
# ADMIN AUTHENTICATION & ROUTE PATTERNS
# ===============================================

- file: src/api/rest/admin_users.py
  why: "Reference implementation for admin routes with proper authentication"
  pattern: |
    Blueprint creation: admin_users_bp = Blueprint('admin_users', __name__, url_prefix='/admin')
    Decorator order: @route → @login_required → @admin_required
    Template rendering: return render_template('admin/template.html')
  gotcha: "Decorator order matters - route decorator first, admin_required last (innermost)"
  lines: "9 (Blueprint), 15-18 (route with decorators)"

- file: src/utils/auth_decorators.py
  why: "admin_required decorator implementation - understand authorization logic"
  pattern: |
    Check authenticated: if not current_user.is_authenticated: abort(401)
    Check admin role: if not current_user.is_admin(): abort(403)
    Allows both 'admin' and 'super' roles
  gotcha: "Returns 403 for authenticated non-admin users (not 401)"
  lines: "36-54 (admin_required decorator)"

- file: src/infrastructure/database/models/base.py
  why: "User model with is_admin() method - understand role hierarchy"
  pattern: |
    def is_admin(self): return self.role in ['admin', 'super']
    Role hierarchy: user < moderator < admin < super
  gotcha: "Both 'admin' and 'super' roles have admin access"
  lines: "User model class definition"

- file: src/app.py
  why: "Blueprint registration pattern - how to register new admin routes"
  pattern: |
    Import: from src.api.rest.admin_users import admin_users_bp
    Register: app.register_blueprint(admin_users_bp)
  gotcha: "Registration happens in main() function, between lines 2233-2319"
  lines: "2308-2309 (admin_users_bp registration example)"

# ===============================================
# WEBSOCKET (FLASK-SOCKETIO) PATTERNS
# ===============================================

- file: src/app.py
  why: "SocketIO initialization pattern - critical for namespace registration"
  pattern: |
    eventlet.monkey_patch() at line 14 (BEFORE any imports)
    socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*',
                       message_queue=redis_url if redis_available else None,
                       max_http_buffer_size=5 * 1024 * 1024)
  gotcha: "monkey_patch() MUST be at top of file or WebSocket will fail"
  lines: "14 (monkey_patch), 2118-2125 (SocketIO init)"

- file: src/app.py
  why: "WebSocket event handler examples - pattern for @socketio.on() decorators"
  pattern: |
    @socketio.on('connect')
    def handle_connect():
        join_room(f'user_{current_user.id}')
        return True  # Accept connection

    @socketio.on('disconnect')
    def handle_disconnect():
        leave_room(f'user_{current_user.id}')
  gotcha: "Return False from connect handler to reject connection"
  lines: "1933-1957 (connect), 1959-1972 (disconnect)"

- file: WEBSOCKET_ARCHITECTURE.md
  why: "Comprehensive WebSocket architecture reference (created during PRP research)"
  pattern: |
    - Namespace organization (class-based vs decorator-based)
    - Room management (join_room, leave_room, emit to room)
    - Broadcasting patterns (broadcast=True, include_self=False)
    - Error handling (@socketio.on_error)
  critical: |
    - Use separate namespace /admin-ws to isolate admin dashboard from client streams
    - Namespace classes must inherit from flask_socketio.Namespace
    - Register with: socketio.on_namespace(AdminNamespace('/admin-ws'))

- url: https://flask-socketio.readthedocs.io/en/latest/getting_started.html#namespaces
  why: "Official Flask-SocketIO namespace documentation"
  critical: |
    - Namespaces multiplex independent connections on same physical socket
    - Class-based namespaces preferred for complex handlers
    - Event handlers prefixed with "on_" (e.g., on_connect, on_request_metrics)
  section: "Namespaces section"

- url: https://flask-socketio.readthedocs.io/en/latest/api.html#flask_socketio.emit
  why: "emit() function API reference for broadcasting"
  critical: |
    - broadcast=True sends to all clients in namespace
    - room='room_name' sends to specific room
    - include_self=False excludes sender from broadcast
    - to=request.sid sends to specific session ID
  section: "emit function documentation"

# ===============================================
# MULTI-CONNECTION MANAGER (DATA SOURCE)
# ===============================================

- file: src/infrastructure/websocket/multi_connection_manager.py
  why: "Source of truth for all connection status and metrics - PRIMARY DATA SOURCE"
  pattern: |
    Class: MultiConnectionManager (lines 35-475)

    Method: get_health_status() → dict (lines 385-411)
    Returns:
      {
        "total_connections": int,
        "connected_count": int,
        "total_ticks_received": int,
        "total_errors": int,
        "connections": {
          "connection_1": {
            "name": str,
            "status": str,  # "connected" | "disconnected" | "error"
            "assigned_tickers": int,
            "message_count": int,
            "error_count": int,
            "last_message_time": float
          }
        }
      }

    Method: get_ticker_assignment(symbol: str) → str (returns connection_id)
    Method: get_connection_tickers(connection_id: str) → set[str]

  gotcha: |
    - Thread-safe with RLock - safe to call from Flask routes
    - All data in-memory (no database queries needed)
    - Access via: market_service.data_adapter.client

  critical: |
    - This is the ONLY source of connection status (no database fallback)
    - Returns current state, updated in real-time as ticks arrive
    - Connection IDs: "connection_1", "connection_2", "connection_3"

  lines: "35-475 (full class), 385-411 (get_health_status), 413-424 (get_ticker_assignment)"

- file: src/app.py
  why: "Access pattern for MultiConnectionManager via market_service"
  pattern: |
    # market_service is global variable (line 79)
    market_service = MarketDataService(...)

    # Access MultiConnectionManager:
    client = market_service.data_adapter.client
    health = client.get_health_status()
  gotcha: "market_service declared as global in main() - must import from src.app"
  lines: "79 (declaration), 2102 (global assignment in main())"

- file: tests/data_source/unit/test_multi_connection_manager.py
  why: "Usage examples and test patterns for MultiConnectionManager"
  pattern: |
    - Mock connection setup
    - Testing get_health_status() return structure
    - Simulating connection state changes
    - Verifying ticker assignment logic
  lines: "Full file (334 lines) - comprehensive test suite"

# ===============================================
# REDIS PUB-SUB INTEGRATION
# ===============================================

- file: src/services/redis_event_subscriber.py
  why: "Redis pub-sub subscriber pattern - how to listen to Redis channels"
  pattern: |
    Subscribe: pubsub.psubscribe('tickstock:patterns:*')
    Listen loop: for message in pubsub.listen():
    Parse: data = json.loads(message['data'])
    Handle: callback(data)
  gotcha: |
    - Always validate JSON before parsing (try-except block)
    - Use psubscribe for pattern matching (wildcards)
    - Use subscribe for exact channel names
  lines: "Full file - production Redis subscriber example"

- file: REDIS_PUBSUB_INTEGRATION_GUIDE.md
  why: "Complete Redis pub-sub reference (created during PRP research)"
  pattern: |
    - Channel organization (16+ channels by category)
    - Message format for tickstock:market:ticks
    - JSON parsing and validation patterns
    - Error handling and connection recovery
  critical: |
    tickstock:market:ticks format:
      {
        "symbol": "AAPL",
        "price": 178.23,
        "volume": 1000,
        "timestamp": 1705853696.123
      }
    NOTE: connection_id NOT in Redis message - must add from MultiConnectionManager

- url: https://redis.io/docs/manual/pubsub/
  why: "Official Redis pub-sub documentation"
  critical: "Use SUBSCRIBE for exact channels, PSUBSCRIBE for patterns"
  section: "Pub/Sub commands"

# ===============================================
# REAL-TIME DASHBOARD EXAMPLES
# ===============================================

- file: web/templates/redis_monitor.html
  why: "Production real-time dashboard - BEST REFERENCE for UI patterns"
  pattern: |
    - Stats cards at top (4 metrics in row)
    - Filter controls (channel, type, limit)
    - Auto-refresh toggle with pause/resume
    - Scrollable message stream (max-height: 600px, overflow-y: auto)
    - Prepend pattern (newest first)
  gotcha: |
    - Use insertBefore(element, firstChild) to prepend
    - Limit items (remove lastChild when count > 50)
    - clearInterval() when pausing auto-refresh
  lines: "Full file - complete working dashboard"

- file: web/static/js/services/streaming-dashboard.js
  why: "Production WebSocket client pattern - how to handle real-time events"
  pattern: |
    class StreamingDashboardService {
      constructor() {
        this.socket = window.socket || io();
        this.setupEventHandlers();
      }

      setupEventHandlers() {
        this.socket.on('streaming_pattern', (data) => {
          this.addPatternEvent(data.detection);
          this.updateMetrics();
        });
      }

      addPatternEvent(detection) {
        const stream = document.getElementById('patternStream');
        const eventItem = document.createElement('div');
        // Build eventItem HTML...
        stream.insertBefore(eventItem, stream.firstChild);  // Prepend

        // Memory management
        while (stream.children.length > 50) {
          stream.removeChild(stream.lastChild);
        }
      }
    }

  gotcha: |
    - ALWAYS limit displayed items to prevent memory leaks
    - Use prepend pattern (newest first) for log-style streams
    - Update counters separately from stream updates (performance)

  lines: "Full file - production WebSocket client"

- file: web/static/js/services/pattern_flow.js
  why: "Hybrid polling + WebSocket pattern for reliability"
  pattern: |
    - WebSocket for real-time updates (primary)
    - Polling every 15 seconds (fallback/reliability)
    - Countdown timer showing "Next refresh in: 15s"
    - Pause/resume controls that stop both WebSocket and polling
  gotcha: "Clear both timers on pause: clearInterval(refreshTimer) AND clearInterval(countdownTimer)"
  lines: "Full file - production hybrid pattern"

# ===============================================
# BOOTSTRAP 5 UI PATTERNS
# ===============================================

- url: https://getbootstrap.com/docs/5.3/layout/grid/
  why: "Bootstrap 5 grid system for three-column layout"
  pattern: |
    Three equal columns:
      <div class="row">
        <div class="col-md-4">Column 1</div>
        <div class="col-md-4">Column 2</div>
        <div class="col-md-4">Column 3</div>
      </div>

    Responsive behavior:
      - Mobile (< 768px): Stacks vertically
      - Medium+ (≥ 768px): Three columns side-by-side
  critical: "Use col-md-4 (not col-4) for responsive stacking on mobile"

- url: https://getbootstrap.com/docs/5.3/components/badge/
  why: "Status badge patterns for connection health indicators"
  pattern: |
    <span class="badge rounded-pill text-bg-success">Connected</span>
    <span class="badge rounded-pill text-bg-danger">Disconnected</span>
    <span class="badge rounded-pill text-bg-secondary">Disabled</span>
    <span class="badge rounded-pill text-bg-warning">Warning</span>
  critical: "Use text-bg-{color} (not bg-{color}) for proper text contrast"

- url: https://getbootstrap.com/docs/5.3/components/card/
  why: "Card component for connection status containers"
  pattern: |
    <div class="card">
      <div class="card-header">Connection 1</div>
      <div class="card-body">
        <h5 class="card-title">Primary</h5>
        <p class="card-text">Status: Connected</p>
      </div>
    </div>

- url: https://getbootstrap.com/docs/5.3/utilities/overflow/
  why: "Overflow utilities for scrollable ticker streams"
  pattern: |
    <div class="overflow-y-auto" style="max-height: 400px;">
      <!-- Scrollable content -->
    </div>
  critical: "Combine overflow-y-auto with max-height for vertical scrolling"

# ===============================================
# TESTING PATTERNS
# ===============================================

- file: tests/sprint15/test_admin_menu.py
  why: "Admin authentication testing pattern - how to test @admin_required"
  pattern: |
    # Test admin access allowed
    def test_admin_menu_visible_for_admin_user(client, admin_user):
        with client:
            client.post('/login', data={'email': admin_user.email, 'password': 'test_password'})
            response = client.get('/admin/websockets')
            assert response.status_code == 200

    # Test non-admin access denied
    def test_admin_menu_hidden_for_regular_user(client, regular_user):
        with client:
            client.post('/login', data={'email': regular_user.email, 'password': 'test_password'})
            response = client.get('/admin/websockets')
            assert response.status_code == 403  # Forbidden

  gotcha: "Use 'with client:' context manager to maintain session across requests"
  lines: "Full file - admin auth test examples"

- file: tests/web_interface/sprint12/test_websocket_updates.py
  why: "WebSocket testing pattern - how to test SocketIO events"
  pattern: |
    class MockWebSocketHandler:
        def __init__(self):
            self.connected = False
            self.event_handlers = {}

        def on(self, event, handler):
            self.event_handlers[event].append(handler)

        def emit(self, event, data):
            return True if self.connected else False

  lines: "Full file (800+ lines) - comprehensive WebSocket test patterns"

- file: tests/integration/test_websocket_patterns.py
  why: "Integration testing with real Redis - end-to-end flow validation"
  pattern: |
    # Use real Redis (test database)
    redis_client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)

    # Publish test message
    redis_client.publish('tickstock:market:ticks', json.dumps(tick_data))

    # Verify WebSocket received it
    time.sleep(0.5)  # Allow message propagation
    assert len(received_events) > 0

  gotcha: "Use db=15 for tests to avoid interfering with production Redis (db=0)"
  lines: "Full file - integration test examples"

- file: ADMIN_DASHBOARD_TEST_TEMPLATES.md
  why: "Copy-paste test templates (created during PRP research)"
  pattern: "7 ready-to-use test templates for admin routes, WebSocket, Redis integration"
```

### Current Codebase Tree (Key Directories)

```bash
C:\Users\McDude\TickStockAppV2\
├── src/
│   ├── api/
│   │   └── rest/
│   │       ├── admin_users.py              # Admin route reference
│   │       ├── admin_monitoring.py         # Admin monitoring dashboard
│   │       ├── admin_daily_processing.py   # Admin processing dashboard
│   │       └── (NEW) admin_websockets.py   # ← Create here
│   │
│   ├── infrastructure/
│   │   ├── websocket/
│   │   │   └── multi_connection_manager.py # PRIMARY data source (lines 35-475)
│   │   └── database/
│   │       └── models/
│   │           └── base.py                 # User model with is_admin()
│   │
│   ├── services/
│   │   └── redis_event_subscriber.py       # Redis pub-sub pattern reference
│   │
│   ├── utils/
│   │   └── auth_decorators.py              # admin_required decorator (lines 36-54)
│   │
│   └── app.py                               # SocketIO init, blueprint registration
│                                            # market_service global (line 79)
│
├── web/
│   ├── templates/
│   │   └── admin/
│   │       ├── users_dashboard.html        # Admin template reference
│   │       ├── redis_monitor.html          # Real-time dashboard BEST reference
│   │       └── (NEW) websockets_monitor.html # ← Create here
│   │
│   └── static/
│       └── js/
│           ├── services/
│           │   ├── streaming-dashboard.js   # WebSocket client reference
│           │   └── pattern_flow.js          # Polling + WebSocket hybrid
│           └── (NEW) admin-websocket-monitor.js # ← Create here
│
├── tests/
│   ├── admin/
│   │   └── (NEW) test_websocket_dashboard.py # ← Create here (unit tests)
│   │
│   ├── integration/
│   │   ├── test_websocket_patterns.py       # Integration test reference
│   │   └── (NEW) test_admin_websocket_integration.py # ← Create here
│   │
│   └── sprint15/
│       └── test_admin_menu.py               # Admin auth test reference
│
└── docs/
    └── planning/
        └── sprints/
            └── sprint52/
                ├── README.md                # Sprint requirements
                └── websocket-connections-admin-monitoring.md # This PRP
```

### Desired Codebase Tree with New Files

```bash
# Files to CREATE:
1. src/api/rest/admin_websockets.py          (150-200 lines)
   - AdminWebSocketNamespace class
   - admin_websockets_bp Blueprint
   - /admin/websockets route
   - /api/admin/websocket-status route

2. web/templates/admin/websockets_monitor.html (200-250 lines)
   - Three-column responsive layout
   - Status cards, config display, live ticker streams
   - Pause/resume controls
   - Bootstrap 5 + Font Awesome icons

3. web/static/js/admin-websocket-monitor.js  (150-200 lines)
   - WebSocket client (Socket.IO)
   - Event handlers (tick_update, connection_status_update, metrics_update)
   - DOM manipulation (prepend ticks, update counters)
   - Pause/resume logic

4. tests/admin/test_websocket_dashboard.py   (100-150 lines)
   - Unit tests for admin route (@admin_required)
   - Unit tests for WebSocket handlers
   - Unit tests for status API endpoint
   - Mocks for MultiConnectionManager, Redis

5. tests/integration/test_admin_websocket_integration.py (100-150 lines)
   - Integration test for full dashboard flow
   - Real Redis pub-sub testing
   - End-to-end latency validation (<500ms)

# Files to MODIFY:
1. src/app.py (2 line additions at lines 2233-2319)
   - Import admin_websockets_bp and AdminWebSocketNamespace
   - Register blueprint: app.register_blueprint(admin_websockets_bp)
   - Register namespace: socketio.on_namespace(AdminWebSocketNamespace('/admin-ws'))
```

### Known Gotchas of TickStock Codebase & Library Quirks

```python
# ===============================================
# TICKSTOCK-SPECIFIC GOTCHAS (CRITICAL)
# ===============================================

# CRITICAL: Flask Application Context
# Flask stores application state in current_app context at RUNTIME
# Don't assume module-level globals are accessible in routes
# PATTERN: Use getattr(current_app, 'attr_name') or import from src.app
# Example: market_service is global in src/app.py (line 79)
#          Access via: from src.app import market_service

# CRITICAL: eventlet Monkey Patching
# MUST call eventlet.monkey_patch() at line 14 of src/app.py
# This MUST be before any imports that use threading/networking
# Without this, WebSocket will fail with mysterious errors
# Location: src/app.py line 14
# Pattern: import eventlet; eventlet.monkey_patch()

# CRITICAL: TickStockAppV2 is CONSUMER ONLY
# - Read from Redis pub-sub channels (patterns, indicators, ticks)
# - Query database READ-ONLY (no writes except user/session data)
# - No OHLCV aggregation (belongs in TickStockPL)
# - No pattern detection logic (belongs in TickStockPL)
# This dashboard is MONITOR ONLY - no control plane operations

# CRITICAL: MultiConnectionManager Access Pattern
# Access via: market_service.data_adapter.client
# market_service is GLOBAL variable in src/app.py (line 79)
# Thread-safe with RLock - safe to call from Flask routes
# All data in-memory (no database queries)
# Returns real-time state updated as ticks arrive

# CRITICAL: Redis Pub-Sub Message Handling
# - Subscribe to tickstock:market:ticks (exact channel, not pattern)
# - Message format: {symbol, price, volume, timestamp}
# - connection_id NOT in Redis message - add from MultiConnectionManager.get_ticker_assignment()
# - Always validate JSON before processing (try-except)
# - Use decode_responses=True for automatic UTF-8 decoding

# CRITICAL: WebSocket Namespace Isolation
# - Admin namespace MUST be separate: /admin-ws (not default /)
# - Prevents admin dashboard from interfering with client WebSocket streams
# - Register namespace: socketio.on_namespace(AdminWebSocketNamespace('/admin-ws'))
# - Reject non-admin connections in on_connect: return False

# CRITICAL: WebSocket Delivery Requirements
# - Target: <500ms from Redis event to browser delivery (admin dashboard)
# - Production target: <100ms (client streams) - don't degrade this!
# - Use SocketIO rooms for efficient broadcasting (room='admin_monitoring')
# - Batch updates if >100 ticks/sec (250ms buffer)

# CRITICAL: Flask-SocketIO emit() Patterns
# - emit() sends to sender ONLY by default (broadcast=False)
# - emit(broadcast=True) sends to ALL clients in namespace
# - emit(room='room_name') sends to specific room
# - emit(to=request.sid) sends to specific session (same as default)
# - include_self=False excludes sender from broadcast

# CRITICAL: Admin Authentication Decorator Order
# Decorators are applied bottom-up (last decorator wraps innermost)
# Correct order:
#   @route_path              # Applied first (outermost)
#   @login_required          # Applied second
#   @admin_required          # Applied last (innermost - runs first)
# Pattern in code:
#   @admin_websockets_bp.route('/websockets')
#   @login_required
#   @admin_required
#   def websockets_dashboard():

# CRITICAL: Performance Monitoring
# - Admin WebSocket overhead MUST be <5ms (measured)
# - Dashboard load time MUST be <2s (initial page load)
# - Status API response MUST be <50ms (in-memory data)
# - No database queries in hot path (all from MultiConnectionManager)

# CRITICAL: Bootstrap 5 Class Names (Breaking Changes from BS4)
# - Use text-bg-{color} NOT bg-{color} for badges with text
# - Use rounded-pill for pill badges (NOT badge-pill)
# - Use overflow-y-auto (NOT overflow-auto if only vertical scroll needed)
# - Grid breakpoints: col-md-4 (≥768px), col-sm-6 (≥576px)

# CRITICAL: Memory Management in JavaScript
# - ALWAYS limit displayed items (max 50 tickers per connection)
# - Remove oldest items: while (stream.children.length > 50) stream.removeChild(stream.lastChild)
# - Clear intervals on page unload: window.addEventListener('beforeunload', cleanup)
# - Prepend pattern prevents scroll jump: stream.insertBefore(item, stream.firstChild)

# CRITICAL: Testing with Redis
# - Use separate test database: redis.Redis(db=15) for tests, db=0 for production
# - Always flushdb() after tests to clean up
# - Allow 100-500ms for message propagation in integration tests (time.sleep)
# - Mock Redis for unit tests, real Redis for integration tests

# ===============================================
# FLASK-SOCKETIO LIBRARY QUIRKS
# ===============================================

# QUIRK: Flask-SocketIO requires single worker with Gunicorn
# - Use -w 1 flag (only one worker process)
# - OR configure Redis message queue for multi-worker setup
# - Pattern: socketio = SocketIO(app, message_queue='redis://')

# QUIRK: WebSocket namespace event handlers must be named "on_<event>"
# - Class-based namespaces: def on_connect(self):, def on_request_metrics(self):
# - Event name derived from method name (strips "on_" prefix)
# - Cannot use reserved names: message, json, connect, disconnect for custom events

# QUIRK: Connection rejection must happen in on_connect
# - Return False to reject connection
# - Raise ConnectionRefusedError with arguments for client error message
# - After connection accepted, cannot revoke (must disconnect from server side)

# QUIRK: emit() context matters
# - Inside event handler: emit() automatically has request context (room, namespace)
# - Outside event handler: must specify namespace and room explicitly
# - Pattern: socketio.emit('event', data, namespace='/admin-ws', room='admin_monitoring')

# ===============================================
# REDIS LIBRARY QUIRKS
# ===============================================

# QUIRK: redis-py decode_responses behavior
# - decode_responses=True: Returns strings (auto UTF-8 decode)
# - decode_responses=False: Returns bytes (must manually .decode('utf-8'))
# - ALWAYS use decode_responses=True for JSON messages
# - Pattern: redis.Redis(decode_responses=True)

# QUIRK: pubsub.listen() blocks indefinitely
# - listen() is blocking generator (infinite loop)
# - Run in background thread: threading.Thread(target=_subscribe_loop, daemon=True)
# - Use daemon=True so thread exits when main process exits
# - Cannot gracefully stop - thread termination happens at process exit

# QUIRK: subscribe vs psubscribe
# - subscribe('channel_name'): Exact channel match only
# - psubscribe('channel*'): Pattern matching with wildcards
# - tickstock:market:ticks: Use subscribe (exact channel)
# - tickstock:patterns:*: Use psubscribe (pattern)
```

## Implementation Blueprint

### Data Models and Structure

This feature uses existing data structures from `MultiConnectionManager`. No new database models or Pydantic schemas required.

**Existing Data Structure (Reference Only)**:

```python
# From src/infrastructure/websocket/multi_connection_manager.py

@dataclass
class ConnectionInfo:
    """Per-connection state tracking"""
    connection_id: str        # "connection_1", "connection_2", "connection_3"
    name: str                 # "primary", "secondary", "tertiary"
    status: str               # "disconnected", "connecting", "connected", "error"
    assigned_tickers: set     # Set of ticker symbols assigned to this connection
    message_count: int        # Total messages received
    error_count: int          # Total errors encountered
    last_message_time: float  # Unix timestamp of last message

# get_health_status() returns:
{
    "total_connections": 3,
    "connected_count": 2,
    "total_ticks_received": 15000,
    "total_errors": 5,
    "connections": {
        "connection_1": {
            "name": "primary",
            "status": "connected",
            "assigned_tickers": 150,
            "message_count": 10000,
            "error_count": 0,
            "last_message_time": 1705853696.123
        },
        "connection_2": {...},
        "connection_3": {...}
    }
}
```

**WebSocket Event Format (New - Defined for /admin-ws namespace)**:

```python
# Client → Server Events

# 1. Client requests current metrics
{
    "event": "request_metrics",
    "data": {}  # No parameters needed
}

# 2. Client requests to pause stream
{
    "event": "pause_stream",
    "data": {}
}

# 3. Client requests to resume stream
{
    "event": "resume_stream",
    "data": {}
}


# Server → Client Events

# 1. Connection status update (sent on connect, on status change)
{
    "event": "connection_status_update",
    "data": {
        "total_connections": 3,
        "connected_count": 2,
        "connections": {...}  # Full health status dict
    }
}

# 2. Real-time tick update (forwarded from Redis tickstock:market:ticks)
{
    "event": "tick_update",
    "data": {
        "symbol": "AAPL",
        "price": 178.23,
        "volume": 1000,
        "timestamp": 1705853696.123,
        "connection_id": "connection_1"  # Added by server
    }
}

# 3. Metrics update (periodic updates every 5 seconds)
{
    "event": "metrics_update",
    "data": {
        "connection_1": {
            "message_count": 10050,
            "messages_per_second": 25.3,
            "uptime_seconds": 3600,
            "error_count": 0
        },
        "connection_2": {...},
        "connection_3": {...}
    }
}
```

### Implementation Tasks (Ordered by Dependencies)

```yaml
# ===============================================
# PHASE 1: BACKEND ROUTES & API (3-4 hours)
# ===============================================

Task 1: CREATE src/api/rest/admin_websockets.py (Flask Blueprint + Routes)
  - IMPLEMENT: Flask Blueprint with admin routes
  - FOLLOW pattern: src/api/rest/admin_users.py (lines 9-18 for blueprint structure)
  - NAMING: admin_websockets_bp = Blueprint('admin_websockets', __name__, url_prefix='/admin')
  - ROUTES:
    - GET /admin/websockets → websockets_dashboard() → render_template('admin/websockets_monitor.html')
    - GET /api/admin/websocket-status → get_websocket_status() → jsonify(connection data)
  - DECORATORS: @login_required, @admin_required (in this order)
  - PLACEMENT: src/api/rest/admin_websockets.py
  - IMPORTS:
    - from flask import Blueprint, render_template, jsonify
    - from flask_login import login_required
    - from src.utils.auth_decorators import admin_required
    - from src.app import market_service
  - GOTCHA: market_service is global variable (src/app.py line 79)

Task 2: CREATE AdminWebSocketNamespace class in src/api/rest/admin_websockets.py
  - IMPLEMENT: Flask-SocketIO Namespace for /admin-ws
  - FOLLOW pattern: WEBSOCKET_ARCHITECTURE.md (namespace creation)
  - NAMING: class AdminWebSocketNamespace(Namespace):
  - EVENT HANDLERS:
    - on_connect() → Check admin auth, join room, send initial status
    - on_disconnect() → Leave room, cleanup
    - on_request_metrics() → Send current metrics to requester
  - ROOM: 'admin_monitoring' (all admin clients join this room)
  - AUTHENTICATION: Reject non-admin connections (return False in on_connect)
  - PLACEMENT: Same file as blueprint (src/api/rest/admin_websockets.py)
  - IMPORTS:
    - from flask_socketio import Namespace, emit, join_room, leave_room
    - from flask import request
    - from flask_login import current_user
  - GOTCHA: on_connect must return False to reject, True to accept
  - CRITICAL: Check current_user.is_authenticated AND current_user.is_admin()

Task 3: IMPLEMENT /api/admin/websocket-status endpoint (JSON API)
  - IMPLEMENT: GET endpoint returning connection status and metrics
  - FOLLOW pattern: src/api/rest/admin_monitoring.py (JSON API structure)
  - ENDPOINT: @admin_websockets_bp.route('/api/admin/websocket-status')
  - DECORATORS: @login_required, @admin_required
  - DATA SOURCE: market_service.data_adapter.client.get_health_status()
  - RESPONSE FORMAT:
    {
      "total_connections": int,
      "connected_count": int,
      "total_ticks_received": int,
      "total_errors": int,
      "connections": {
        "connection_1": {...},
        "connection_2": {...},
        "connection_3": {...}
      }
    }
  - PERFORMANCE: <50ms (all in-memory, no database)
  - ERROR HANDLING: Return 500 with error message if MultiConnectionManager unavailable
  - GOTCHA: Access via market_service global (from src.app import market_service)

# ===============================================
# PHASE 2: REDIS INTEGRATION (2-3 hours)
# ===============================================

Task 4: IMPLEMENT Redis tick subscriber in AdminWebSocketNamespace
  - IMPLEMENT: Background thread subscribing to tickstock:market:ticks
  - FOLLOW pattern: src/services/redis_event_subscriber.py (Redis pub-sub pattern)
  - METHOD: _subscribe_to_ticks(self) → background thread listening to Redis
  - CHANNEL: tickstock:market:ticks (exact channel, not pattern)
  - MESSAGE FORMAT: {"symbol": str, "price": float, "volume": int, "timestamp": float}
  - PROCESSING:
    1. Parse JSON from Redis message
    2. Get connection_id from MultiConnectionManager.get_ticker_assignment(symbol)
    3. Add connection_id to tick data
    4. Emit to /admin-ws clients: socketio.emit('tick_update', tick, namespace='/admin-ws', room='admin_monitoring')
  - THREAD: daemon=True (exits when main process exits)
  - START: Call start_redis_subscriber() in on_connect (first client only)
  - PLACEMENT: Method of AdminWebSocketNamespace class
  - IMPORTS:
    - import threading
    - import redis
    - import json
    - from src.app import socketio (for emitting outside event handler context)
  - GOTCHA: Use socketio.emit() (not self.emit()) for background thread emissions
  - GOTCHA: Must specify namespace='/admin-ws' when emitting from background thread
  - ERROR HANDLING: Try-except around JSON parsing, log errors but don't crash thread

Task 5: IMPLEMENT connection status broadcaster (periodic updates)
  - IMPLEMENT: Background task sending metrics every 5 seconds
  - METHOD: _broadcast_metrics(self) → periodic metrics updates
  - FREQUENCY: Every 5 seconds
  - DATA SOURCE: market_service.data_adapter.client.get_health_status()
  - BROADCAST: socketio.emit('metrics_update', metrics, namespace='/admin-ws', room='admin_monitoring')
  - START: Call in separate daemon thread from on_connect (first client only)
  - PLACEMENT: Method of AdminWebSocketNamespace class
  - PATTERN: while True loop with time.sleep(5)
  - GOTCHA: Check if any clients in room before emitting (optimize when no admins watching)

# ===============================================
# PHASE 3: FRONTEND TEMPLATE (4-5 hours)
# ===============================================

Task 6: CREATE web/templates/admin/websockets_monitor.html
  - IMPLEMENT: Three-column responsive dashboard template
  - FOLLOW pattern: web/templates/redis_monitor.html (real-time dashboard structure)
  - LAYOUT: Bootstrap 5 grid system (col-md-4 for three columns)
  - STRUCTURE:
    1. Header with page title and controls (pause/resume button)
    2. Three-column row (one per connection)
    3. Each column contains:
       - Card header (connection name + status badge)
       - Configuration section (universe key, ticker count)
       - Metrics section (uptime, throughput, errors)
       - Live ticker stream (scrollable, max-height: 400px)
  - STATUS BADGES:
    - Connected: <span class="badge rounded-pill text-bg-success">Connected</span>
    - Disconnected: <span class="badge rounded-pill text-bg-danger">Disconnected</span>
    - Disabled: <span class="badge rounded-pill text-bg-secondary">Disabled</span>
  - SCROLLABLE STREAM:
    - <div class="overflow-y-auto" style="max-height: 400px;" id="tickerStream1">
    - Newest ticks prepended (appear at top)
  - PLACEMENT: web/templates/admin/websockets_monitor.html
  - IMPORTS (CDN):
    - Bootstrap 5.3: https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css
    - Font Awesome 6: https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css
    - Socket.IO client: https://cdn.socket.io/4.5.4/socket.io.min.js
  - COLOR CODING:
    - Connection 1: Blue (#007bff)
    - Connection 2: Green (#28a745)
    - Connection 3: Orange (#fd7e14)
  - GOTCHA: Use text-bg-{color} (not bg-{color}) for badges with proper text contrast
  - RESPONSIVE: Columns stack vertically on mobile (<768px)

Task 7: CREATE web/static/js/admin-websocket-monitor.js (WebSocket Client)
  - IMPLEMENT: JavaScript WebSocket client and UI controller
  - FOLLOW pattern: web/static/js/services/streaming-dashboard.js (WebSocket client structure)
  - CLASS: class AdminWebSocketMonitor
  - INITIALIZATION:
    - Connect to /admin-ws namespace: this.socket = io('/admin-ws')
    - Setup event handlers
    - Request initial metrics
  - EVENT HANDLERS:
    - socket.on('connect') → Update connection indicator (green badge)
    - socket.on('disconnect') → Update connection indicator (red badge)
    - socket.on('connection_status_update') → Update all connection cards
    - socket.on('tick_update') → Prepend tick to appropriate stream (by connection_id)
    - socket.on('metrics_update') → Update metrics displays
  - UI UPDATES:
    - Prepend ticks: stream.insertBefore(tickElement, stream.firstChild)
    - Limit items: while (stream.children.length > 50) stream.removeChild(stream.lastChild)
    - Update counters: document.getElementById('throughput1').textContent = ticks_per_sec
  - PAUSE/RESUME:
    - Pause: Set paused flag, stop prepending ticks (buffer in memory)
    - Resume: Clear buffer, resume prepending
  - PLACEMENT: web/static/js/admin-websocket-monitor.js
  - LOAD IN TEMPLATE: <script src="{{ url_for('static', filename='js/admin-websocket-monitor.js') }}"></script>
  - GOTCHA: ALWAYS limit displayed items to prevent memory leaks
  - GOTCHA: Use insertBefore (not appendChild) to prepend newest first

# ===============================================
# PHASE 4: FLASK APP INTEGRATION (1 hour)
# ===============================================

Task 8: MODIFY src/app.py - Register admin WebSocket blueprint and namespace
  - INTEGRATE: Register admin_websockets_bp and AdminWebSocketNamespace
  - FIND pattern: Lines 2233-2319 (existing blueprint registrations)
  - ADD IMPORTS (near line 2200):
    - from src.api.rest.admin_websockets import admin_websockets_bp, AdminWebSocketNamespace
  - ADD REGISTRATIONS (near line 2308):
    - app.register_blueprint(admin_websockets_bp)
    - socketio.on_namespace(AdminWebSocketNamespace('/admin-ws'))
  - PLACEMENT: Between lines 2233-2319 (admin blueprint section)
  - GOTCHA: Must register AFTER app and socketio are initialized
  - GOTCHA: Namespace registration uses on_namespace (not register_namespace)
  - PRESERVE: Existing blueprint registrations (don't remove or modify)

# ===============================================
# PHASE 5: TESTING (2-3 hours)
# ===============================================

Task 9: CREATE tests/admin/test_websocket_dashboard.py (Unit Tests)
  - IMPLEMENT: Unit tests for admin routes and WebSocket handlers
  - FOLLOW pattern: tests/sprint15/test_admin_menu.py (admin auth tests)
  - TEST COVERAGE:
    1. test_websockets_dashboard_requires_admin() → Non-admin gets 403
    2. test_websockets_dashboard_accessible_to_admin() → Admin gets 200
    3. test_websocket_status_api_returns_correct_structure() → JSON validation
    4. test_admin_websocket_rejects_non_admin_connections() → WebSocket auth
    5. test_admin_websocket_accepts_admin_connections() → WebSocket connection
    6. test_tick_update_includes_connection_id() → Tick enrichment
  - MOCKS:
    - Mock MultiConnectionManager.get_health_status()
    - Mock Redis client
  - FIXTURES:
    - admin_user (fixture with role='admin')
    - regular_user (fixture with role='user')
  - ASSERTIONS:
    - Status codes (200, 403)
    - JSON structure (assert 'connections' in response.json)
    - WebSocket connection accepted/rejected
  - PLACEMENT: tests/admin/test_websocket_dashboard.py
  - RUN: pytest tests/admin/test_websocket_dashboard.py -v
  - GOTCHA: Use 'with client:' context manager to maintain session

Task 10: CREATE tests/integration/test_admin_websocket_integration.py (Integration Tests)
  - IMPLEMENT: End-to-end integration test for full dashboard flow
  - FOLLOW pattern: tests/integration/test_websocket_patterns.py (Redis integration)
  - TEST FLOW:
    1. Login as admin user
    2. Connect to /admin-ws WebSocket namespace
    3. Publish tick to Redis tickstock:market:ticks channel
    4. Verify tick received via WebSocket with connection_id added
    5. Verify latency <500ms from Redis publish to WebSocket receive
  - REAL SERVICES:
    - Real Redis (db=15 for testing)
    - Real SocketIO connection
    - Real MultiConnectionManager (mocked if needed)
  - SETUP:
    - redis_client = redis.Redis(db=15, decode_responses=True)
    - redis_client.flushdb() in teardown
  - ASSERTIONS:
    - Tick received within 500ms
    - connection_id present in received tick
    - Correct connection_id (matches MultiConnectionManager.get_ticker_assignment())
  - PLACEMENT: tests/integration/test_admin_websocket_integration.py
  - RUN: python run_tests.py (includes integration tests)
  - GOTCHA: Allow 100-500ms for message propagation (time.sleep or polling with timeout)

# ===============================================
# PHASE 6: DOCUMENTATION (1 hour)
# ===============================================

Task 11: UPDATE docs/guides/admin.md (if it exists, otherwise skip)
  - ADD SECTION: "WebSocket Connections Monitoring"
  - CONTENT:
    - Purpose: Monitor multi-connection WebSocket architecture
    - Access: /admin/websockets (admin users only)
    - Features: Real-time status, ticker distribution, throughput metrics
    - Metrics explanation: What each metric means
    - Troubleshooting tips: Common issues and solutions
  - SCREENSHOTS: (Optional) Include dashboard screenshot
  - PLACEMENT: Add section to existing docs/guides/admin.md
  - SKIP IF: File doesn't exist (not critical for PRP success)
```

### Implementation Patterns & Key Details

```python
# ===============================================
# PATTERN 1: Admin Route with Authentication
# File: src/api/rest/admin_websockets.py
# ===============================================

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from src.utils.auth_decorators import admin_required
from src.app import market_service
import logging

logger = logging.getLogger(__name__)

# Blueprint creation
admin_websockets_bp = Blueprint('admin_websockets', __name__, url_prefix='/admin')


@admin_websockets_bp.route('/websockets')
@login_required
@admin_required
def websockets_dashboard():
    """
    Render WebSocket monitoring dashboard.
    Admin users only - displays real-time connection status.
    """
    return render_template('admin/websockets_monitor.html')


@admin_websockets_bp.route('/api/admin/websocket-status')
@login_required
@admin_required
def get_websocket_status():
    """
    Get real-time WebSocket connection status and metrics.

    Returns:
        JSON with structure:
        {
            "total_connections": int,
            "connected_count": int,
            "total_ticks_received": int,
            "total_errors": int,
            "connections": {
                "connection_1": {
                    "name": str,
                    "status": str,
                    "assigned_tickers": int,
                    "message_count": int,
                    "error_count": int,
                    "last_message_time": float
                },
                ...
            }
        }
    """
    try:
        # PATTERN: Access MultiConnectionManager via market_service global
        # CRITICAL: market_service is defined in src/app.py line 79
        client = market_service.data_adapter.client

        # PATTERN: get_health_status() returns complete connection state
        # PERFORMANCE: <50ms (all in-memory, no database queries)
        health = client.get_health_status()

        return jsonify({
            "status": "success",
            "data": health,
            "timestamp": time.time()
        })

    except AttributeError as e:
        # Handle case where MultiConnectionManager not available
        logger.error(f"MultiConnectionManager not available: {e}")
        return jsonify({
            "status": "error",
            "message": "WebSocket connection manager not available"
        }), 500

    except Exception as e:
        logger.error(f"Error fetching WebSocket status: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ===============================================
# PATTERN 2: Admin WebSocket Namespace
# File: src/api/rest/admin_websockets.py (continued)
# ===============================================

from flask_socketio import Namespace, emit, join_room, leave_room
from flask import request as flask_request
from flask_login import current_user
import threading
import redis
import json
import time

# Import socketio from app for background emissions
from src.app import socketio


class AdminWebSocketNamespace(Namespace):
    """
    Admin monitoring namespace at /admin-ws.
    Provides real-time WebSocket connection status and tick data.
    Admin users only - non-admin connections rejected.
    """

    def __init__(self, namespace):
        super().__init__(namespace)

        # Redis client for tick subscription
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True  # Auto UTF-8 decoding
        )

        # Background threads (started on first client connect)
        self.redis_subscriber_thread = None
        self.metrics_broadcaster_thread = None

        # Thread control
        self.active_clients = 0
        self._lock = threading.Lock()

    def on_connect(self):
        """
        Handle admin connection.

        CRITICAL: Reject non-admin users (return False).
        PATTERN: Join room for admin broadcasts.
        """
        # CRITICAL: Check authentication AND admin role
        if not current_user.is_authenticated:
            logger.warning(f"Unauthenticated user attempted /admin-ws connection")
            return False  # Reject connection

        if not current_user.is_admin():
            logger.warning(f"Non-admin user {current_user.email} attempted /admin-ws connection")
            return False  # Reject connection

        # Join admin monitoring room
        join_room('admin_monitoring')
        logger.info(f"Admin user {current_user.email} connected to /admin-ws")

        # Track active clients
        with self._lock:
            self.active_clients += 1
            first_client = (self.active_clients == 1)

        # Start background threads on first client
        if first_client:
            self._start_background_threads()

        # Send initial status to connecting client
        try:
            client = market_service.data_adapter.client
            health = client.get_health_status()

            # PATTERN: emit to specific session (to=request.sid)
            emit('connection_status_update', health, to=flask_request.sid)
        except Exception as e:
            logger.error(f"Error sending initial status: {e}")

        return True  # Accept connection

    def on_disconnect(self):
        """Handle admin disconnection and cleanup."""
        leave_room('admin_monitoring')

        with self._lock:
            self.active_clients -= 1

        logger.info(f"Admin user disconnected from /admin-ws ({self.active_clients} remaining)")

    def on_request_metrics(self, data):
        """
        Handle metrics request from admin client.
        Responds with current connection status and metrics.
        """
        try:
            client = market_service.data_adapter.client
            health = client.get_health_status()

            # PATTERN: Reply only to requester (to=request.sid)
            emit('metrics_update', health, to=flask_request.sid)

        except Exception as e:
            logger.error(f"Error handling metrics request: {e}")
            emit('error', {'message': 'Failed to fetch metrics'}, to=flask_request.sid)

    def _start_background_threads(self):
        """Start background threads for Redis subscription and metrics broadcasting."""
        # Start Redis tick subscriber
        if self.redis_subscriber_thread is None or not self.redis_subscriber_thread.is_alive():
            self.redis_subscriber_thread = threading.Thread(
                target=self._subscribe_to_ticks,
                daemon=True
            )
            self.redis_subscriber_thread.start()
            logger.info("Started Redis tick subscriber thread")

        # Start metrics broadcaster
        if self.metrics_broadcaster_thread is None or not self.metrics_broadcaster_thread.is_alive():
            self.metrics_broadcaster_thread = threading.Thread(
                target=self._broadcast_metrics,
                daemon=True
            )
            self.metrics_broadcaster_thread.start()
            logger.info("Started metrics broadcaster thread")

    def _subscribe_to_ticks(self):
        """
        Background thread: Subscribe to tickstock:market:ticks and forward to /admin-ws clients.

        CRITICAL: Runs in daemon thread (exits when main process exits).
        PATTERN: Add connection_id from MultiConnectionManager.get_ticker_assignment().
        """
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe('tickstock:market:ticks')

        logger.info("Subscribed to tickstock:market:ticks for admin dashboard")

        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    # Parse JSON tick data
                    tick = json.loads(message['data'])

                    # CRITICAL: Add connection_id from MultiConnectionManager
                    # This tells admin dashboard which connection handled this tick
                    symbol = tick.get('symbol')
                    if symbol:
                        client = market_service.data_adapter.client
                        connection_id = client.get_ticker_assignment(symbol)
                        tick['connection_id'] = connection_id

                    # GOTCHA: Must use socketio.emit() (not self.emit()) from background thread
                    # GOTCHA: Must specify namespace='/admin-ws' explicitly
                    socketio.emit(
                        'tick_update',
                        tick,
                        namespace='/admin-ws',
                        room='admin_monitoring'
                    )

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tick JSON: {e}")
                except Exception as e:
                    logger.error(f"Error processing tick: {e}")

    def _broadcast_metrics(self):
        """
        Background thread: Broadcast metrics every 5 seconds.

        PATTERN: Periodic updates to keep dashboard current.
        """
        while True:
            try:
                time.sleep(5)  # Update every 5 seconds

                # Skip if no clients watching
                with self._lock:
                    if self.active_clients == 0:
                        continue

                # Fetch current metrics
                client = market_service.data_adapter.client
                health = client.get_health_status()

                # Calculate messages per second for each connection
                metrics = {}
                connections = health.get('connections', {})
                for conn_id, conn_data in connections.items():
                    msg_count = conn_data.get('message_count', 0)
                    # Simple rate calculation (could be smoothed with moving average)
                    metrics[conn_id] = {
                        'message_count': msg_count,
                        'messages_per_second': round(msg_count / 5, 1),  # Simplified
                        'error_count': conn_data.get('error_count', 0),
                        'status': conn_data.get('status', 'unknown')
                    }

                # Broadcast to all admin clients
                socketio.emit(
                    'metrics_update',
                    metrics,
                    namespace='/admin-ws',
                    room='admin_monitoring'
                )

            except Exception as e:
                logger.error(f"Error broadcasting metrics: {e}")
                time.sleep(5)  # Continue even on error


# ===============================================
# PATTERN 3: Bootstrap 5 Template (Three-Column Layout)
# File: web/templates/admin/websockets_monitor.html
# ===============================================

"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket Connections Monitor - TickStock Admin</title>

    <!-- Bootstrap 5.3 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
          rel="stylesheet">

    <!-- Font Awesome 6 -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
          rel="stylesheet">

    <style>
        /* Connection-specific colors */
        .conn-1-border { border-left: 4px solid #007bff; }  /* Blue */
        .conn-2-border { border-left: 4px solid #28a745; }  /* Green */
        .conn-3-border { border-left: 4px solid #fd7e14; }  /* Orange */

        .conn-1-bg { background-color: #e7f3ff; }
        .conn-2-bg { background-color: #e7f7e7; }
        .conn-3-bg { background-color: #fff3e7; }

        /* Ticker stream styling */
        .ticker-stream {
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
        }

        .ticker-item {
            padding: 0.5rem;
            border-bottom: 1px solid #e0e0e0;
        }

        .ticker-item:hover {
            background-color: #f8f9fa;
        }

        /* Metrics styling */
        .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
        }

        .metric-label {
            font-size: 0.85rem;
            color: #6c757d;
        }

        /* Status indicator pulse animation */
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        .status-pulse {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">
                <i class="fas fa-chart-line"></i> TickStock Admin
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/admin/monitoring">Monitoring</a>
                <a class="nav-link" href="/admin/users">Users</a>
                <a class="nav-link active" href="/admin/websockets">WebSocket Connections</a>
            </div>
        </div>
    </nav>

    <div class="container-fluid py-4">
        <!-- Header with Controls -->
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>WebSocket Connections Monitor</h2>
            <div>
                <button class="btn btn-warning" id="pauseBtn">
                    <i class="fas fa-pause"></i> Pause Updates
                </button>
                <button class="btn btn-secondary" id="refreshBtn">
                    <i class="fas fa-sync"></i> Refresh
                </button>
            </div>
        </div>

        <!-- Connection Status Indicator -->
        <div class="alert alert-info mb-4" role="alert">
            <i class="fas fa-circle status-pulse" id="statusIndicator"></i>
            <span id="statusText">Connecting to WebSocket...</span>
        </div>

        <!-- Three-Column Layout (One per Connection) -->
        <div class="row">
            <!-- Connection 1 -->
            <div class="col-md-4 mb-4">
                <div class="card conn-1-border">
                    <div class="card-header d-flex justify-content-between align-items-center conn-1-bg">
                        <h5 class="mb-0">
                            <i class="fas fa-plug"></i> Connection 1
                        </h5>
                        <span class="badge rounded-pill text-bg-secondary" id="status1">Unknown</span>
                    </div>
                    <div class="card-body">
                        <!-- Configuration -->
                        <h6 class="text-muted">Configuration</h6>
                        <p class="mb-2">
                            <strong>Name:</strong> <span id="name1">-</span><br>
                            <strong>Universe Key:</strong> <span id="universe1">-</span><br>
                            <strong>Tickers:</strong> <span id="tickerCount1">0</span>
                        </p>

                        <!-- Metrics -->
                        <h6 class="text-muted mt-3">Metrics</h6>
                        <div class="row text-center">
                            <div class="col-6">
                                <div class="metric-value" id="msgCount1">0</div>
                                <div class="metric-label">Messages</div>
                            </div>
                            <div class="col-6">
                                <div class="metric-value" id="throughput1">0</div>
                                <div class="metric-label">msg/sec</div>
                            </div>
                        </div>
                        <div class="row text-center mt-2">
                            <div class="col-6">
                                <div class="metric-value" id="errors1">0</div>
                                <div class="metric-label">Errors</div>
                            </div>
                            <div class="col-6">
                                <div class="metric-value" id="uptime1">-</div>
                                <div class="metric-label">Uptime</div>
                            </div>
                        </div>

                        <!-- Live Ticker Stream -->
                        <h6 class="text-muted mt-3">Live Data Stream</h6>
                        <div class="ticker-stream" id="tickerStream1">
                            <p class="text-center text-muted py-4">Waiting for ticks...</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Connection 2 (same structure, different IDs) -->
            <div class="col-md-4 mb-4">
                <div class="card conn-2-border">
                    <!-- Same structure as Connection 1, with id suffixes "2" -->
                </div>
            </div>

            <!-- Connection 3 (same structure, different IDs) -->
            <div class="col-md-4 mb-4">
                <div class="card conn-3-border">
                    <!-- Same structure as Connection 1, with id suffixes "3" -->
                </div>
            </div>
        </div>
    </div>

    <!-- Socket.IO Client -->
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

    <!-- Admin WebSocket Monitor JS -->
    <script src="{{ url_for('static', filename='js/admin-websocket-monitor.js') }}"></script>

    <script>
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', () => {
            const monitor = new AdminWebSocketMonitor();
            monitor.initialize();
        });
    </script>
</body>
</html>
"""


# ===============================================
# PATTERN 4: JavaScript WebSocket Client
# File: web/static/js/admin-websocket-monitor.js
# ===============================================

"""
class AdminWebSocketMonitor {
    constructor() {
        this.socket = null;
        this.isPaused = false;
        this.tickBuffer = [];  // Buffer for paused ticks
        this.maxTicksPerStream = 50;  // Memory management
    }

    initialize() {
        // Connect to /admin-ws namespace
        this.socket = io('/admin-ws');

        // Setup event handlers
        this.setupSocketHandlers();
        this.setupUIControls();

        console.log('Admin WebSocket Monitor initialized');
    }

    setupSocketHandlers() {
        // Connection events
        this.socket.on('connect', () => {
            this.updateConnectionStatus(true);
            console.log('Connected to /admin-ws');
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus(false);
            console.log('Disconnected from /admin-ws');
        });

        // Data events
        this.socket.on('connection_status_update', (data) => {
            this.handleConnectionStatusUpdate(data);
        });

        this.socket.on('tick_update', (tick) => {
            if (!this.isPaused) {
                this.handleTickUpdate(tick);
            } else {
                this.tickBuffer.push(tick);
            }
        });

        this.socket.on('metrics_update', (metrics) => {
            this.handleMetricsUpdate(metrics);
        });

        // Error events
        this.socket.on('error', (error) => {
            console.error('WebSocket error:', error);
        });
    }

    setupUIControls() {
        // Pause/Resume button
        const pauseBtn = document.getElementById('pauseBtn');
        pauseBtn.addEventListener('click', () => {
            this.togglePause();
        });

        // Refresh button
        const refreshBtn = document.getElementById('refreshBtn');
        refreshBtn.addEventListener('click', () => {
            this.socket.emit('request_metrics');
        });
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');

        if (connected) {
            indicator.style.color = '#28a745';  // Green
            statusText.textContent = 'Connected to WebSocket';
        } else {
            indicator.style.color = '#dc3545';  // Red
            statusText.textContent = 'Disconnected from WebSocket';
        }
    }

    handleConnectionStatusUpdate(data) {
        const connections = data.connections || {};

        // Update each connection (1, 2, 3)
        ['connection_1', 'connection_2', 'connection_3'].forEach((connId, index) => {
            const suffix = index + 1;
            const conn = connections[connId] || {};

            // Update status badge
            this.updateStatusBadge(suffix, conn.status);

            // Update configuration
            document.getElementById(`name${suffix}`).textContent = conn.name || '-';
            document.getElementById(`universe${suffix}`).textContent =
                conn.universe_key || conn.symbols?.join(', ') || '-';
            document.getElementById(`tickerCount${suffix}`).textContent =
                conn.assigned_tickers || 0;

            // Update metrics
            document.getElementById(`msgCount${suffix}`).textContent =
                conn.message_count || 0;
            document.getElementById(`errors${suffix}`).textContent =
                conn.error_count || 0;

            // Update uptime
            this.updateUptime(suffix, conn.last_message_time);
        });
    }

    updateStatusBadge(suffix, status) {
        const badge = document.getElementById(`status${suffix}`);

        // Remove existing classes
        badge.className = 'badge rounded-pill';

        // Add appropriate class based on status
        if (status === 'connected') {
            badge.classList.add('text-bg-success');
            badge.textContent = 'Connected';
        } else if (status === 'disconnected') {
            badge.classList.add('text-bg-danger');
            badge.textContent = 'Disconnected';
        } else if (status === 'error') {
            badge.classList.add('text-bg-warning');
            badge.textContent = 'Error';
        } else {
            badge.classList.add('text-bg-secondary');
            badge.textContent = 'Disabled';
        }
    }

    handleTickUpdate(tick) {
        const connId = tick.connection_id || 'connection_1';
        const suffix = connId.replace('connection_', '');
        const stream = document.getElementById(`tickerStream${suffix}`);

        if (!stream) return;

        // Create tick element
        const tickEl = document.createElement('div');
        tickEl.className = 'ticker-item';

        const timestamp = new Date(tick.timestamp * 1000).toLocaleTimeString();
        const price = typeof tick.price === 'number' ? tick.price.toFixed(2) : tick.price;

        tickEl.innerHTML = `
            <strong>${tick.symbol}</strong>
            <span class="float-end text-muted">${timestamp}</span><br>
            <span>$${price}</span>
            <span class="text-muted ms-2">Vol: ${tick.volume || 0}</span>
        `;

        // PATTERN: Prepend (newest first) using insertBefore
        if (stream.firstChild) {
            stream.insertBefore(tickEl, stream.firstChild);
        } else {
            stream.appendChild(tickEl);
        }

        // CRITICAL: Memory management - limit to 50 items
        while (stream.children.length > this.maxTicksPerStream) {
            stream.removeChild(stream.lastChild);
        }

        // Remove "Waiting for ticks" message if present
        const waitingMsg = stream.querySelector('.text-muted.py-4');
        if (waitingMsg) {
            waitingMsg.remove();
        }
    }

    handleMetricsUpdate(metrics) {
        Object.keys(metrics).forEach(connId => {
            const suffix = connId.replace('connection_', '');
            const conn = metrics[connId];

            // Update throughput
            document.getElementById(`throughput${suffix}`).textContent =
                conn.messages_per_second?.toFixed(1) || '0';

            // Update message count
            document.getElementById(`msgCount${suffix}`).textContent =
                conn.message_count || 0;

            // Update error count
            document.getElementById(`errors${suffix}`).textContent =
                conn.error_count || 0;
        });
    }

    updateUptime(suffix, lastMessageTime) {
        if (!lastMessageTime) {
            document.getElementById(`uptime${suffix}`).textContent = '-';
            return;
        }

        const now = Date.now() / 1000;
        const uptimeSeconds = now - lastMessageTime;

        if (uptimeSeconds < 60) {
            document.getElementById(`uptime${suffix}`).textContent = `${Math.floor(uptimeSeconds)}s`;
        } else if (uptimeSeconds < 3600) {
            document.getElementById(`uptime${suffix}`).textContent = `${Math.floor(uptimeSeconds / 60)}m`;
        } else {
            document.getElementById(`uptime${suffix}`).textContent =
                `${Math.floor(uptimeSeconds / 3600)}h ${Math.floor((uptimeSeconds % 3600) / 60)}m`;
        }
    }

    togglePause() {
        this.isPaused = !this.isPaused;
        const pauseBtn = document.getElementById('pauseBtn');

        if (this.isPaused) {
            pauseBtn.innerHTML = '<i class="fas fa-play"></i> Resume Updates';
            pauseBtn.classList.remove('btn-warning');
            pauseBtn.classList.add('btn-success');
        } else {
            pauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause Updates';
            pauseBtn.classList.remove('btn-success');
            pauseBtn.classList.add('btn-warning');

            // Process buffered ticks
            this.tickBuffer.forEach(tick => this.handleTickUpdate(tick));
            this.tickBuffer = [];
        }
    }
}
"""


# ===============================================
# PATTERN 5: Flask App Integration
# File: src/app.py (modifications)
# ===============================================

"""
# Near line 2200 (with other admin imports)
from src.api.rest.admin_websockets import admin_websockets_bp, AdminWebSocketNamespace

# Between lines 2233-2319 (admin blueprint registration section)
# Add these two lines:
app.register_blueprint(admin_websockets_bp)
socketio.on_namespace(AdminWebSocketNamespace('/admin-ws'))
"""
```

### Integration Points

```yaml
# ===============================================
# FLASK BLUEPRINTS
# ===============================================

FLASK_BLUEPRINTS:
  - blueprint_file: src/api/rest/admin_websockets.py
  - blueprint_name: admin_websockets_bp
  - register_in: src/app.py (lines 2233-2319)
  - registration_pattern: |
      # Import (near line 2200)
      from src.api.rest.admin_websockets import admin_websockets_bp, AdminWebSocketNamespace

      # Register blueprint (near line 2308)
      app.register_blueprint(admin_websockets_bp)

      # Register namespace (after blueprint)
      socketio.on_namespace(AdminWebSocketNamespace('/admin-ws'))


# ===============================================
# REDIS CHANNELS
# ===============================================

REDIS_CHANNELS:
  - subscribe_in: AdminWebSocketNamespace._subscribe_to_ticks()
  - channel_name: tickstock:market:ticks (exact channel, not pattern)
  - subscription_method: pubsub.subscribe('tickstock:market:ticks')
  - message_format: |
      {
        "symbol": "AAPL",
        "price": 178.23,
        "volume": 1000,
        "timestamp": 1705853696.123
      }
  - enrichment: Add connection_id from MultiConnectionManager.get_ticker_assignment(symbol)
  - output_format: |
      {
        "symbol": "AAPL",
        "price": 178.23,
        "volume": 1000,
        "timestamp": 1705853696.123,
        "connection_id": "connection_1"  # Added by server
      }
  - consumption: Forward to /admin-ws clients via socketio.emit('tick_update', tick)


# ===============================================
# WEBSOCKET NAMESPACE
# ===============================================

WEBSOCKET:
  - namespace: /admin-ws
  - class: AdminWebSocketNamespace
  - registration: socketio.on_namespace(AdminWebSocketNamespace('/admin-ws'))
  - room: admin_monitoring (all admin clients)

  - event_handlers:
    - on_connect: Authenticate admin, join room, send initial status
    - on_disconnect: Leave room, decrement client count
    - on_request_metrics: Send current metrics to requester

  - broadcast_events:
    - tick_update: Real-time tick from Redis (with connection_id)
    - connection_status_update: Connection status changes
    - metrics_update: Periodic metrics (every 5 seconds)

  - authentication:
    - Check: current_user.is_authenticated AND current_user.is_admin()
    - Reject: return False in on_connect
    - Accept: return True in on_connect

  - background_threads:
    - _subscribe_to_ticks: Daemon thread for Redis subscription
    - _broadcast_metrics: Daemon thread for periodic metrics (5s interval)


# ===============================================
# MULTI-CONNECTION MANAGER
# ===============================================

MULTI_CONNECTION_MANAGER:
  - file: src/infrastructure/websocket/multi_connection_manager.py
  - class: MultiConnectionManager (lines 35-475)
  - access_pattern: market_service.data_adapter.client
  - import: from src.app import market_service

  - methods_used:
    - get_health_status() → dict
      Returns: Complete connection state (status, tickers, metrics)
      Performance: <50ms (in-memory)
      Thread-safe: Yes (RLock)

    - get_ticker_assignment(symbol: str) → str
      Returns: "connection_1" | "connection_2" | "connection_3"
      Usage: Determine which connection handles specific ticker

    - get_connection_tickers(connection_id: str) → set[str]
      Returns: Set of ticker symbols on specified connection
      Usage: Display ticker list per connection

  - data_structure:
      ConnectionInfo dataclass (lines 21-32):
        - connection_id: str
        - name: str
        - status: str ("connected" | "disconnected" | "error")
        - assigned_tickers: set[str]
        - message_count: int
        - error_count: int
        - last_message_time: float


# ===============================================
# CONFIG
# ===============================================

CONFIG:
  - no new environment variables required
  - reads existing WebSocket config:
    - USE_MULTI_CONNECTION (true/false)
    - WEBSOCKET_CONNECTION_1_ENABLED
    - WEBSOCKET_CONNECTION_1_NAME
    - WEBSOCKET_CONNECTION_1_UNIVERSE_KEY
    - WEBSOCKET_CONNECTION_1_SYMBOLS
    - (repeat for connections 2, 3)

  - config access:
    - MultiConnectionManager reads .env on initialization
    - Dashboard queries MultiConnectionManager for runtime state
    - No direct .env access needed in dashboard code


# ===============================================
# STARTUP
# ===============================================

STARTUP:
  - no startup modifications needed
  - MultiConnectionManager already initialized by market_service
  - AdminWebSocketNamespace starts background threads on first client connect
  - Threads are daemon threads (auto-cleanup on process exit)
  - No health check changes needed (read-only monitoring feature)
```

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# TickStock Standard: Ruff for linting and formatting
# Run after creating each file - fix before proceeding

# File-specific validation (as you create files)
ruff check src/api/rest/admin_websockets.py --fix
ruff format src/api/rest/admin_websockets.py

ruff check web/static/js/admin-websocket-monitor.js --fix
ruff format web/static/js/admin-websocket-monitor.js

# Project-wide validation (before commit)
ruff check src/ --fix
ruff format src/

# Expected: Zero errors
# Note: TickStock does not use mypy - Python typing is runtime-checked via tests
```

### Level 2: Unit Tests (Component Validation)

```bash
# TickStock Standard: pytest for all testing
# Test each component as it's created

# Unit tests for admin WebSocket dashboard
pytest tests/admin/test_websocket_dashboard.py -v

# Expected output:
# test_websockets_dashboard_requires_admin PASSED
# test_websockets_dashboard_accessible_to_admin PASSED
# test_websocket_status_api_returns_correct_structure PASSED
# test_admin_websocket_rejects_non_admin_connections PASSED
# test_admin_websocket_accepts_admin_connections PASSED
# test_tick_update_includes_connection_id PASSED

# Full unit test suite (optional - verify no regressions)
pytest tests/unit/ -v

# Coverage validation (optional)
pytest tests/admin/test_websocket_dashboard.py --cov=src/api/rest/admin_websockets --cov-report=term-missing

# Expected: >80% coverage on admin_websockets.py
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
# CRITICAL: Must run before ANY commit

# Primary integration test runner
python run_tests.py

# Expected output:
# - 2+ tests passing (existing + new admin WebSocket test)
# - ~30-40 second runtime
# - Pattern flow tests passing (existing)
# - Admin WebSocket integration passing (new)
# - Core integration may fail if services not running (acceptable in dev)

# Alternative detailed runner
python tests/integration/run_integration_tests.py

# Admin WebSocket-specific integration test
pytest tests/integration/test_admin_websocket_integration.py -v

# Expected:
# test_admin_dashboard_full_flow PASSED
# test_tick_latency_under_500ms PASSED
# test_connection_status_updates PASSED

# NOTE: RLock warning can be ignored (known asyncio quirk)


# ===============================================
# MANUAL VALIDATION (Dashboard Functionality)
# ===============================================

# 1. Start all services
python start_all_services.py &
sleep 5  # Allow services to initialize

# 2. Verify services healthy
curl -f http://localhost:5000/health || echo "TickStockAppV2 health check failed"
curl -f http://localhost:8080/health || echo "TickStockPL health check failed"

# 3. Test admin dashboard access
# 3a. Login as admin user (use browser)
# URL: http://localhost:5000/login
# Email: admin@example.com (your admin user)
# Password: (your admin password)

# 3b. Navigate to WebSocket dashboard
# URL: http://localhost:5000/admin/websockets
# Expected: Dashboard loads, shows 3 connection columns

# 3c. Verify non-admin access denied
# Logout, login as regular user
# Navigate to /admin/websockets
# Expected: 403 Forbidden error

# 4. Verify real-time tick updates
# With admin dashboard open:
# - Open browser DevTools → Console tab
# - Watch for "Connected to /admin-ws" message
# - Observe tick updates appearing in connection streams
# - Verify ticks color-coded by connection (blue/green/orange)

# 5. Verify pause/resume controls
# - Click "Pause Updates" button
# - Verify tickers stop appearing (stream frozen)
# - Click "Resume Updates" button
# - Verify tickers resume appearing

# 6. Verify metrics updates
# - Watch metrics counters (messages, throughput, errors)
# - Verify they update every 5 seconds
# - Verify uptime incrementing

# 7. Performance validation
# - Measure dashboard load time (should be <2 seconds)
# - Check WebSocket latency in DevTools Network tab (should be <500ms)
# - Verify no lag in production /streaming dashboard (no impact from admin)

# Expected: All manual tests pass, no errors in browser console
```

### Level 4: TickStock-Specific Validation

```bash
# ===============================================
# ARCHITECTURE COMPLIANCE VALIDATION
# ===============================================

# Run architecture-validation-specialist agent (if available)
# Verify:
# - Admin dashboard is Consumer role (no data writes)
# - WebSocket namespace isolated (/admin-ws separate from /)
# - No pattern detection logic in dashboard (read-only monitoring)

# Manual architecture checks:
# 1. Verify no database writes in admin_websockets.py
grep -r "INSERT INTO\|UPDATE\|DELETE FROM" src/api/rest/admin_websockets.py
# Expected: No matches (dashboard is read-only)

# 2. Verify using MultiConnectionManager (not direct WebSocket access)
grep "get_health_status\|get_ticker_assignment" src/api/rest/admin_websockets.py
# Expected: Matches found (correct data source)

# 3. Verify namespace isolation
grep "/admin-ws" src/api/rest/admin_websockets.py
# Expected: Matches in namespace registration and emit calls


# ===============================================
# SECURITY VALIDATION
# ===============================================

# 1. Verify admin authentication enforced
grep "@admin_required" src/api/rest/admin_websockets.py
# Expected: Decorators on all routes

# 2. Test non-admin WebSocket connection rejection
# (Covered in unit tests, verify manually if needed)

# 3. Check for hardcoded credentials
grep -r "password\|secret\|api_key" src/api/rest/admin_websockets.py
# Expected: No hardcoded secrets

# 4. Verify no API keys in HTML template
grep -r "api_key\|secret" web/templates/admin/websockets_monitor.html
# Expected: No secrets exposed


# ===============================================
# PERFORMANCE VALIDATION
# ===============================================

# 1. Dashboard load time
# Use browser DevTools Performance tab
# Measure: Initial page load to "Interactive"
# Target: <2 seconds
# How: Open http://localhost:5000/admin/websockets with DevTools open

# 2. WebSocket update latency
# Use browser DevTools Console
# Add timing logs in admin-websocket-monitor.js:
# console.time('tick_update'); ... console.timeEnd('tick_update');
# Target: <500ms from Redis publish to DOM update

# 3. Status API response time
# Terminal: time curl -X GET http://localhost:5000/api/admin/websocket-status \
#                -H "Cookie: session=YOUR_SESSION_COOKIE"
# Target: <50ms

# 4. Admin WebSocket overhead
# Measure production WebSocket performance before and after admin dashboard
# Production metric: WebSocket delivery latency at /streaming
# Target: <5ms difference (no measurable impact)
# How: Check logs for WebSocket delivery times, compare before/after


# ===============================================
# REDIS CHANNEL MONITORING
# ===============================================

# Monitor Redis tick channel (verify messages flowing)
redis-cli SUBSCRIBE tickstock:market:ticks
# Expected: See tick messages in real-time
# Format: {"symbol": "AAPL", "price": 178.23, "volume": 1000, "timestamp": 1705853696.123}

# Monitor admin dashboard receiving ticks
# Open admin dashboard, check browser console
# Expected: Console shows tick_update events with connection_id added


# ===============================================
# WEBSOCKET CONNECTION VALIDATION
# ===============================================

# 1. Verify /admin-ws namespace registered
grep "on_namespace.*admin-ws" src/app.py
# Expected: Match found (namespace registered)

# 2. Test WebSocket connection in browser
# Open http://localhost:5000/admin/websockets
# Open DevTools → Network tab → WS filter
# Expected: See WebSocket connection to /admin-ws

# 3. Verify namespace isolation
# Open /streaming dashboard (client namespace /)
# Open /admin/websockets dashboard (admin namespace /admin-ws)
# Verify both work independently (no interference)


# ===============================================
# EXPECTED RESULTS SUMMARY
# ===============================================

# All validations pass:
# ✅ Syntax/style: ruff reports zero errors
# ✅ Unit tests: 6+ tests passing (admin auth, WebSocket, API)
# ✅ Integration tests: python run_tests.py passes (2+ tests)
# ✅ Manual dashboard: Loads, updates in real-time, pause/resume works
# ✅ Architecture: Read-only consumer, namespace isolated, uses MultiConnectionManager
# ✅ Security: Admin-only access, no hardcoded secrets, connection rejection works
# ✅ Performance: <2s load, <500ms WebSocket latency, <50ms API, <5ms overhead
# ✅ Redis: Ticks flowing on tickstock:market:ticks channel
# ✅ WebSocket: /admin-ws namespace working, isolated from / namespace
```

## Final Validation Checklist

### Technical Validation

- [ ] All 4 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] No linting errors: `ruff check src/` returns zero errors
- [ ] No formatting issues: `ruff format src/ --check` passes
- [ ] Unit tests pass: `pytest tests/admin/test_websocket_dashboard.py -v` (6+ tests)
- [ ] Integration test passes: `pytest tests/integration/test_admin_websocket_integration.py -v`

### Feature Validation

- [ ] `/admin/websockets` route accessible to admin users (200 OK)
- [ ] Non-admin users get 403 Forbidden
- [ ] Dashboard displays all 3 connections (enabled/disabled state visible)
- [ ] Real-time connection status updates (green/red badges change)
- [ ] Configuration displayed correctly (universe key, ticker count, connection name)
- [ ] Live tick updates stream in real-time (<500ms latency measured)
- [ ] Ticks color-coded by connection (blue/green/orange)
- [ ] Pause/resume button functional (stops/starts data stream)
- [ ] Metrics update in real-time (uptime, throughput, message count, errors)
- [ ] Dashboard loads in <2 seconds (measured in browser DevTools)
- [ ] WebSocket update latency <500ms (measured from Redis publish to DOM update)
- [ ] Status API responds in <50ms (measured with `time curl`)

### TickStock Architecture Validation

- [ ] Component role respected (TickStockAppV2 = Consumer, read-only monitoring)
- [ ] No database writes in admin dashboard code (grep verification passed)
- [ ] Uses MultiConnectionManager as data source (not direct WebSocket access)
- [ ] WebSocket namespace isolated (/admin-ws separate from / client namespace)
- [ ] Redis pub-sub used correctly (subscribes to tickstock:market:ticks)
- [ ] connection_id added from MultiConnectionManager.get_ticker_assignment()
- [ ] No performance impact on production (<5ms overhead measured)
- [ ] Performance targets achieved:
  - [ ] Dashboard load: <2 seconds ✓
  - [ ] WebSocket latency: <500ms ✓
  - [ ] Status API: <50ms ✓
  - [ ] Admin overhead: <5ms ✓

### Code Quality Validation

- [ ] Follows admin route patterns from src/api/rest/admin_users.py
- [ ] Decorator order correct: @route → @login_required → @admin_required
- [ ] WebSocket patterns follow WEBSOCKET_ARCHITECTURE.md guidance
- [ ] JavaScript follows streaming-dashboard.js client patterns
- [ ] Template follows redis_monitor.html real-time dashboard structure
- [ ] File placement matches desired codebase tree
- [ ] Blueprint registered in src/app.py (lines 2233-2319)
- [ ] Namespace registered: socketio.on_namespace(AdminWebSocketNamespace('/admin-ws'))
- [ ] Anti-patterns avoided (see Anti-Patterns section below)
- [ ] Code structure limits followed:
  - [ ] Files <500 lines (admin_websockets.py ~200 lines)
  - [ ] Functions <50 lines (largest method ~40 lines)
  - [ ] Line length <100 characters
- [ ] Naming conventions followed:
  - [ ] snake_case functions (websockets_dashboard, get_websocket_status)
  - [ ] PascalCase classes (AdminWebSocketNamespace)
  - [ ] UPPER_SNAKE_CASE constants (if any)

### Documentation & Deployment

- [ ] Code is self-documenting with clear function/variable names
- [ ] Docstrings present on all public methods
- [ ] Logs are informative but not verbose (INFO level for connections, ERROR for failures)
- [ ] No "Generated by Claude" comments in code
- [ ] No "Generated by Claude" text in commit messages
- [ ] Template has proper HTML structure and accessibility (alt tags, semantic HTML)
- [ ] JavaScript has error handling (try-catch blocks, error events)

---

## Anti-Patterns to Avoid

### Generic Anti-Patterns

- ❌ Don't create new patterns when existing ones work (follow admin_users.py structure)
- ❌ Don't skip validation because "it should work" (run ALL validation levels)
- ❌ Don't ignore failing tests - fix them before proceeding
- ❌ Don't use sync database calls in async WebSocket handlers (not applicable - no DB calls)
- ❌ Don't hardcode values that should be config (use MultiConnectionManager, not hardcoded connection count)
- ❌ Don't catch all exceptions without logging (always log errors with context)

### TickStock-Specific Anti-Patterns (CRITICAL)

#### Architecture Violations

- ❌ **Don't mix TickStockApp and TickStockPL roles**
  - AppV2 = Consumer (reads from Redis, queries DB read-only, displays data)
  - PL = Producer (writes to Redis, writes to DB, processes data)
  - Violation: Adding pattern detection logic to admin dashboard
  - ✅ Correct: Dashboard only displays data from MultiConnectionManager and Redis

- ❌ **Don't query pattern tables directly in TickStockAppV2**
  - Pattern data comes via Redis pub-sub from TickStockPL
  - Exception: Dashboard historical queries (not applicable here - no DB queries)
  - Violation: SELECT FROM daily_patterns in admin dashboard
  - ✅ Correct: All data from MultiConnectionManager (in-memory)

- ❌ **Don't use database writes in TickStockAppV2 for pattern data**
  - Pattern/indicator data writes belong in TickStockPL
  - Allowed writes in AppV2: user_sessions, ws_subscriptions, error_logs
  - Violation: INSERT INTO daily_patterns from admin dashboard
  - ✅ Correct: No database writes in this feature (read-only monitoring)

#### WebSocket & Namespace

- ❌ **Don't mix admin and client WebSocket namespaces**
  - Admin namespace MUST be separate: /admin-ws
  - Client namespace: / (default)
  - Violation: Using default namespace for admin dashboard (causes interference)
  - ✅ Correct: AdminWebSocketNamespace('/admin-ws')

- ❌ **Don't forget eventlet.monkey_patch()**
  - MUST be at line 14 of src/app.py before any imports
  - Violation: Adding imports before monkey_patch() call
  - ✅ Correct: Leave monkey_patch() at line 14, don't modify order

- ❌ **Don't use self.emit() from background threads**
  - Background threads must use socketio.emit() with explicit namespace
  - Violation: self.emit('tick_update', tick) in _subscribe_to_ticks()
  - ✅ Correct: socketio.emit('tick_update', tick, namespace='/admin-ws', room='admin_monitoring')

#### Authentication & Security

- ❌ **Don't skip admin authentication checks**
  - MUST check both is_authenticated AND is_admin()
  - Violation: Only checking is_authenticated (allows non-admin users)
  - ✅ Correct: if not current_user.is_authenticated or not current_user.is_admin(): return False

- ❌ **Don't use wrong decorator order**
  - Decorators applied bottom-up (last decorator runs first)
  - Violation: @admin_required above @login_required
  - ✅ Correct: @route → @login_required → @admin_required (top to bottom)

#### Data Handling

- ❌ **Don't access MultiConnectionManager directly**
  - Must access via market_service.data_adapter.client
  - Violation: from src.infrastructure.websocket.multi_connection_manager import MultiConnectionManager; manager = MultiConnectionManager()
  - ✅ Correct: from src.app import market_service; client = market_service.data_adapter.client

- ❌ **Don't forget to add connection_id to ticks**
  - Redis message lacks connection_id - must add from MultiConnectionManager
  - Violation: Forwarding Redis tick directly without enrichment
  - ✅ Correct: tick['connection_id'] = client.get_ticker_assignment(tick['symbol'])

#### Performance

- ❌ **Don't create blocking operations in WebSocket path**
  - Target: <500ms latency for admin dashboard updates
  - Violation: Synchronous database query in on_request_metrics()
  - ✅ Correct: Use in-memory data from MultiConnectionManager (<1ms)

- ❌ **Don't skip memory management in JavaScript**
  - MUST limit displayed items to prevent memory leaks
  - Violation: Appending ticks without removing old ones
  - ✅ Correct: while (stream.children.length > 50) stream.removeChild(stream.lastChild)

- ❌ **Don't use blocking Redis listen() in main thread**
  - Redis pubsub.listen() blocks indefinitely
  - Violation: Calling listen() in Flask route handler
  - ✅ Correct: Run in daemon background thread: threading.Thread(target=_subscribe_to_ticks, daemon=True)

#### Testing & Validation

- ❌ **Don't skip integration tests before commits**
  - `python run_tests.py` is MANDATORY before any commit
  - Violation: Committing code without running integration tests
  - ✅ Correct: Run tests, verify all pass, then commit

- ❌ **Don't test with production Redis database**
  - Use separate test database to avoid interfering with production
  - Violation: redis.Redis(db=0) in tests (production database)
  - ✅ Correct: redis.Redis(db=15) in tests (test database)

#### Code Quality

- ❌ **Don't exceed structure limits**
  - Max 500 lines per file, 50 lines per function
  - Violation: 600-line admin_websockets.py file
  - ✅ Correct: Keep admin_websockets.py ~150-200 lines (well under limit)

- ❌ **Don't add "Generated by Claude" to code or commits**
  - Keep code and commits clean
  - Violation: Comments like "# Generated with Claude Code"
  - ✅ Correct: Professional code comments explaining logic, not attribution

- ❌ **Don't use old Bootstrap class names**
  - Bootstrap 5 changed class names from v4
  - Violation: Using .badge-pill (Bootstrap 4)
  - ✅ Correct: Using .rounded-pill (Bootstrap 5)
  - Violation: Using .bg-success (text may be unreadable)
  - ✅ Correct: Using .text-bg-success (proper text contrast)

---

**End of PRP**

**Confidence Score for One-Pass Implementation**: 9/10

This PRP provides:
- ✅ Complete context (admin patterns, WebSocket patterns, MultiConnectionManager API)
- ✅ Exact file paths with line numbers for all references
- ✅ Dependency-ordered implementation tasks
- ✅ Copy-paste-ready code examples
- ✅ Specific URLs with section anchors
- ✅ TickStock-specific gotchas and constraints
- ✅ 4-level validation with project-specific commands
- ✅ Anti-patterns section to avoid common pitfalls

The implementer has everything needed to build this feature successfully without debugging iterations or architectural pivots.