# Sprint 52: WebSocket Connections Admin Monitoring Dashboard

**Status**: Planning - Ready for Implementation
**Priority**: MEDIUM
**Estimated Duration**: 1-2 days
**Complexity**: MEDIUM (UI + real-time event handling)

## Overview

Create a new admin web page that provides real-time visibility into the multi-connection WebSocket architecture. This dashboard will display the status, configuration, and live data flow for each of the three WebSocket connections, enabling administrators to monitor connection health, ticker distribution, and real-time market data streaming.

## What's Being Built

### New Admin Page: `/admin/websockets`

A real-time monitoring dashboard with three columns (one per WebSocket connection) displaying:

1. **Connection Status**
   - Enabled/Disabled state
   - Connected/Disconnected status
   - Connection uptime
   - Last heartbeat timestamp

2. **Configuration Display**
   - Connection name (primary/secondary/tertiary)
   - Universe key or direct symbols list
   - Number of subscribed tickers
   - Priority tier assignment

3. **Live Data Stream**
   - Real-time stock symbols and prices
   - Event updates as they arrive
   - Message throughput metrics (msgs/sec)
   - Last update timestamp per ticker

### Technical Architecture

**Frontend**:
- Template: `web/templates/admin/websockets.html`
- Real-time updates via WebSocket connection to TickStockAppV2
- Three-column responsive layout
- Auto-refresh data streams
- Visual indicators for connection health (green/red status)

**Backend**:
- New route in `src/api/routes/admin.py` → `/admin/websockets`
- WebSocket event handler for real-time updates
- Query multi-connection manager for status/config
- Stream tick events from Redis channels to frontend

**Data Sources**:
- Configuration: Read from environment variables (`WEBSOCKET_CONNECTION_*`)
- Status: Query `WebSocketConnectionManager` state
- Live data: Subscribe to `tickstock:market:ticks` Redis channel
- Metrics: Connection statistics from manager

## Requirements

### Functional Requirements

1. **Real-Time Connection Monitoring**
   - Display connection state for all 3 potential connections
   - Show enabled/disabled per `.env` configuration
   - Indicate active/inactive connection status
   - Display connection errors/warnings

2. **Configuration Transparency**
   - Show universe key or symbol list per connection
   - Display ticker count per connection
   - Show connection name/identifier
   - Indicate priority routing rules

3. **Live Data Visualization**
   - Stream real-time ticker updates as they arrive
   - Display symbol and current price
   - Show update frequency/throughput
   - Color-code by connection (connection 1 = blue, 2 = green, 3 = orange)

4. **Health Metrics**
   - Connection uptime
   - Messages received per second
   - Last successful update timestamp
   - Error counts and last error message

### Non-Functional Requirements

1. **Performance**
   - Dashboard loads in <2 seconds
   - Real-time updates with <500ms latency
   - Handle 300+ concurrent ticker updates
   - No impact on production WebSocket performance

2. **Usability**
   - Clear visual hierarchy (columns for connections)
   - Responsive design (desktop/tablet)
   - Auto-reconnect on connection loss
   - Pause/resume data stream controls

3. **Security**
   - Restrict to authenticated admin users only
   - No sensitive API keys displayed
   - Rate limiting on WebSocket endpoint
   - Audit logging for access

## Implementation Tasks

### Phase 1: Backend Setup (3-4 hours)

1. **Create Admin Route**
   - Add `/admin/websockets` route in `src/api/routes/admin.py`
   - Implement admin authentication check
   - Create endpoint to serve template

2. **WebSocket Status API**
   - Create `/api/admin/websocket-status` endpoint
   - Query `WebSocketConnectionManager` for state
   - Return JSON: enabled, connected, config, metrics per connection
   - Add Redis subscription for live tick data

3. **Real-Time Event Handler**
   - Create WebSocket namespace `/admin-ws`
   - Subscribe to `tickstock:market:ticks` channel
   - Route events to frontend by connection ID
   - Add connection health heartbeat

### Phase 2: Frontend Development (4-5 hours)

1. **Create Dashboard Template**
   - File: `web/templates/admin/websockets.html`
   - Three-column layout (Bootstrap grid)
   - Connection status cards with health indicators
   - Configuration display sections
   - Live data stream areas

2. **Implement WebSocket Client**
   - JavaScript: Connect to `/admin-ws` namespace
   - Handle connection status updates
   - Process live tick events
   - Update DOM in real-time with minimal flicker

3. **Visual Design**
   - Color-coded connection headers (blue/green/orange)
   - Status badges (Connected=green, Disconnected=red)
   - Ticker list with scrolling updates
   - Metrics counters with auto-update

4. **Interactive Features**
   - Pause/resume data stream button
   - Auto-scroll toggle for ticker lists
   - Connection detail expand/collapse
   - Refresh configuration button

### Phase 3: Testing & Validation (2-3 hours)

1. **Unit Tests**
   - Test admin route authentication
   - Test WebSocket status API accuracy
   - Test event routing logic
   - Mock Redis connections

2. **Integration Tests**
   - Full dashboard load test
   - WebSocket connection lifecycle
   - Multi-connection data flow
   - Configuration edge cases (0, 1, 2, 3 connections)

3. **Manual Testing**
   - Test with single connection enabled
   - Test with multi-connection mode
   - Test connection failure scenarios
   - Test with 100+ tickers per connection
   - Verify no performance impact on production

### Phase 4: Documentation (1 hour)

1. **User Guide**
   - Add section to `docs/guides/admin.md`
   - Screenshot of dashboard
   - Interpretation of metrics
   - Troubleshooting tips

2. **Code Documentation**
   - Docstrings for new endpoints
   - Inline comments for complex logic
   - Architecture diagram update

## Success Criteria

Sprint 52 is **DONE** when:

1. ✅ **Dashboard Accessible**: `/admin/websockets` loads successfully for admin users
2. ✅ **Status Accurate**: Connection state reflects actual WebSocket manager state
3. ✅ **Config Display**: Shows enabled state and universe keys/symbols per connection
4. ✅ **Live Data Flowing**: Real-time ticker updates display as events arrive
5. ✅ **All Tests Pass**: Unit and integration tests succeed (`python run_tests.py`)
6. ✅ **Performance Validated**: No measurable impact on WebSocket throughput
7. ✅ **Documentation Complete**: Admin guide updated with dashboard usage
8. ✅ **Security Verified**: Only admin users can access, no secrets exposed

## Technical Specifications

### API Endpoints

```python
# Route: GET /admin/websockets
@admin_bp.route('/websockets')
@require_admin
def websockets_dashboard():
    """Render WebSocket monitoring dashboard"""
    return render_template('admin/websockets.html')

# Route: GET /api/admin/websocket-status
@admin_bp.route('/api/admin/websocket-status')
@require_admin
def get_websocket_status():
    """
    Returns:
    {
        "connections": [
            {
                "id": 1,
                "name": "primary",
                "enabled": true,
                "connected": true,
                "uptime_seconds": 3600,
                "config": {
                    "universe_key": "market_leaders:top_500",
                    "symbols": ["AAPL", "NVDA", ...],
                    "ticker_count": 150
                },
                "metrics": {
                    "messages_per_second": 25.3,
                    "last_update": "2025-01-21T12:34:56Z",
                    "error_count": 0
                }
            },
            ...
        ]
    }
    """
```

### WebSocket Events

```javascript
// Frontend subscribes to:
socket.on('connection_status_update', (data) => {
    // Update connection status indicators
    // data = { connection_id, status, timestamp }
});

socket.on('tick_update', (data) => {
    // Display live ticker update
    // data = { connection_id, symbol, price, timestamp }
});

socket.on('metrics_update', (data) => {
    // Update throughput metrics
    // data = { connection_id, msgs_per_sec, uptime }
});
```

### Configuration Sources

```bash
# Read from environment variables:
USE_MULTI_CONNECTION=true|false
WEBSOCKET_CONNECTIONS_MAX=3

# Per connection:
WEBSOCKET_CONNECTION_1_ENABLED=true|false
WEBSOCKET_CONNECTION_1_NAME=primary
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=market_leaders:top_500
WEBSOCKET_CONNECTION_1_SYMBOLS=AAPL,NVDA,TSLA  # fallback

# Repeat for connections 2 and 3
```

## UI Mockup (ASCII)

```
╔═════════════════════════════════════════════════════════════════════════╗
║                   WebSocket Connections Monitor                          ║
╠═══════════════════╦═══════════════════╦═══════════════════════════════════╣
║  Connection 1     ║  Connection 2     ║  Connection 3                     ║
║  [●] Connected    ║  [●] Connected    ║  [○] Disabled                     ║
║  primary          ║  secondary        ║  tertiary                         ║
╠═══════════════════╬═══════════════════╬═══════════════════════════════════╣
║ Configuration:    ║ Configuration:    ║ Configuration:                    ║
║ Universe Key:     ║ Universe Key:     ║ Universe Key:                     ║
║ market_leaders:   ║ finance_sector:   ║ N/A                               ║
║   top_500         ║   large_cap       ║                                   ║
║ Tickers: 150      ║ Tickers: 85       ║ Tickers: 0                        ║
╠═══════════════════╬═══════════════════╬═══════════════════════════════════╣
║ Live Data:        ║ Live Data:        ║ Live Data:                        ║
║ AAPL    $178.23 ↑ ║ JPM     $156.89 ↓ ║ (No data)                         ║
║ NVDA    $495.67 ↑ ║ BAC     $34.12 ↑  ║                                   ║
║ TSLA    $248.91 → ║ WFC     $52.34 ↓  ║                                   ║
║ MSFT    $412.56 ↑ ║ C       $61.78 ↑  ║                                   ║
║ ... (scrolling)   ║ ... (scrolling)   ║                                   ║
╠═══════════════════╬═══════════════════╬═══════════════════════════════════╣
║ Metrics:          ║ Metrics:          ║ Metrics:                          ║
║ Uptime: 1h 23m    ║ Uptime: 1h 22m    ║ Uptime: N/A                       ║
║ Rate: 25.3 msg/s  ║ Rate: 18.7 msg/s  ║ Rate: 0 msg/s                     ║
║ Errors: 0         ║ Errors: 0         ║ Errors: N/A                       ║
║ Last: 12:34:56    ║ Last: 12:34:55    ║ Last: N/A                         ║
╚═══════════════════╩═══════════════════╩═══════════════════════════════════╝
[⏸ Pause Updates] [↻ Refresh Config] [📊 Full Metrics]
```

## Agent Usage Recommendations

1. **architecture-validation-specialist**: Review multi-connection architecture compliance
2. **appv2-integration-specialist**: Implement Flask routes and WebSocket handlers
3. **redis-integration-specialist**: Handle Redis tick channel subscription
4. **database-query-specialist**: If storing connection metrics to database
5. **tickstock-test-specialist**: Create comprehensive test coverage
6. **integration-testing-specialist**: Validate end-to-end data flow

## Risk Assessment

### Technical Risks: LOW-MEDIUM

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| WebSocket performance impact | Low | High | Use separate namespace, add rate limiting |
| Real-time update lag | Medium | Medium | Optimize Redis subscription, batch updates |
| Configuration parsing errors | Low | Medium | Comprehensive validation, fallback defaults |
| Browser compatibility | Low | Low | Use standard WebSocket API, polyfills |

### Deployment Risks: LOW

- No production code changes required (new admin feature only)
- Can be deployed independently
- Easy rollback (remove route)
- No database migrations needed

## Performance Targets

| Metric | Target | Critical? |
|--------|--------|-----------|
| Dashboard Load Time | <2s | No |
| WebSocket Update Latency | <500ms | No |
| Admin WebSocket Overhead | <5ms | Yes |
| Concurrent Admin Users | 10+ | No |
| Ticker Display Capacity | 300+ | No |

## Validation Strategy

### Automated Tests

```bash
# Unit tests
pytest tests/admin/test_websocket_dashboard.py -v

# Integration tests
python run_tests.py

# Syntax check
ruff check . --fix
```

### Manual Tests

1. **Single Connection Mode** (`USE_MULTI_CONNECTION=false`)
   - Verify only connection 1 shows as enabled
   - Verify connections 2 and 3 show as disabled
   - Verify live data flows through connection 1

2. **Multi-Connection Mode** (`USE_MULTI_CONNECTION=true`)
   - Enable all 3 connections via `.env`
   - Verify all show as connected
   - Verify tickers route to correct connections
   - Verify independent data streams

3. **Failure Scenarios**
   - Disconnect connection 2
   - Verify dashboard shows disconnected state
   - Verify no data in connection 2 column
   - Verify connections 1 and 3 unaffected

4. **Security**
   - Access as non-admin user (should reject)
   - Access as admin user (should allow)
   - Verify no API keys visible in HTML

## Related Documentation

- **Architecture**: `docs/architecture/README.md`
- **Configuration**: `docs/guides/configuration.md`
- **Admin Guide**: `docs/guides/admin.md` (to be updated)
- **WebSocket Integration**: `docs/architecture/websocket-integration.md`
- **Multi-Connection Architecture**: `docs/PRPs/multi-connection-websocket.md` (if exists)

## Post-Sprint Actions

1. **Update Admin Documentation**
   - Add dashboard usage guide to `docs/guides/admin.md`
   - Include screenshots
   - Document metric interpretation

2. **Create Sprint Summary**
   - `SPRINT52_COMPLETE.md` (using POST_SPRINT_CHECKLIST.md)
   - Update `CLAUDE.md` with completion status
   - Update `BACKLOG.md` if needed

3. **Monitor Production**
   - Watch for admin dashboard access logs
   - Monitor WebSocket overhead
   - Check for browser compatibility issues

## Rollback Plan

If critical issues arise:

```bash
# Remove admin route
git revert <commit-hash>

# Or disable route in config
ADMIN_WEBSOCKET_DASHBOARD_ENABLED=false
```

**Recovery Time**: <5 minutes (simple route removal)

## Questions & Considerations

- **What if a connection has 100+ tickers?**: Implement scrolling with virtual scrolling for performance
- **How often should metrics update?**: Every 1 second (configurable)
- **Should we store connection history?**: Optional - Phase 2 enhancement
- **What about mobile view?**: Vertical stacking of columns (responsive)
- **Can we export metrics?**: Optional - Phase 2 enhancement (CSV export)

## Sprint Timeline

- **Sprint Start**: TBD
- **Backend Complete**: Day 1 (3-4 hours)
- **Frontend Complete**: Day 1-2 (4-5 hours)
- **Testing Complete**: Day 2 (2-3 hours)
- **Documentation Complete**: Day 2 (1 hour)
- **Sprint End**: Day 2

## Sign-Off Checklist

- [ ] Technical Lead Review
- [ ] Code Review (1+ reviewer)
- [ ] QA Validation (manual testing complete)
- [ ] Security Review (admin auth verified)
- [ ] Performance Validation (no production impact)
- [ ] Documentation Complete
- [ ] Sprint Complete Summary Created

---

**Last Updated**: January 21, 2025
**Sprint Owner**: TBD
**Status**: Planning - Ready for Implementation ✅
