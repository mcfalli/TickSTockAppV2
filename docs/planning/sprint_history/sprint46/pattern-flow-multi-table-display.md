# Pattern Flow Multi-Table Display Enhancement (6 Pattern Tables + Indicators - 7 Columns) - Sprint 46

**PRP Type**: CHANGE
**Created**: 2025-10-19
**Updated: 2025-10-19 (MERGED with AMENDMENT - final specifications)**
**Sprint**: 46
**Change Type**: enhancement

---

## ⚠️ CRITICAL SPECIFICATIONS (READ FIRST - Supersedes Conflicting Info Below)

### Implementation Requirements

**Layout**: 7 columns total
- 6 pattern columns: intraday, hourly, daily, weekly, monthly, daily_intraday (combo)
- 1 indicators column: shows all timeframes from `intraday_indicators` table

**Recency-Focused Time Windows** (Live Monitoring Dashboard):

| Column | Table | Time Window | SQL Filter |
|--------|-------|-------------|------------|
| Intraday | `intraday_patterns` | Last **30 minutes** | `WHERE detection_timestamp > NOW() - INTERVAL '30 minutes'` |
| Hourly | `hourly_patterns` | Last **1 hour** | `WHERE detection_timestamp > NOW() - INTERVAL '1 hour'` |
| Daily | `daily_patterns` | Last **24 hours** | `WHERE detection_timestamp > NOW() - INTERVAL '1 day'` |
| Weekly | `weekly_patterns` | **This week** (since Monday) | `WHERE detection_timestamp >= date_trunc('week', NOW())` |
| Monthly | `monthly_patterns` | **This month** (since 1st) | `WHERE detection_timestamp >= date_trunc('month', NOW())` |
| Combo | `daily_intraday_patterns` | Last **30 minutes** | `WHERE detection_timestamp > NOW() - INTERVAL '30 minutes'` |
| Indicators | `intraday_indicators` | Last **30 minutes** | `WHERE calculation_timestamp > NOW() - INTERVAL '30 minutes'` |

**NEW API Endpoints Required** (5 total):
1. `/api/patterns/hourly` - Hourly patterns (INTERVAL '1 hour')
2. `/api/patterns/weekly` - Weekly patterns (date_trunc('week', NOW()))
3. `/api/patterns/monthly` - Monthly patterns (date_trunc('month', NOW()))
4. `/api/patterns/daily_intraday` - Combo patterns (INTERVAL '30 minutes')
5. `/api/patterns/indicators/latest` - **NEW** Indicators (INTERVAL '30 minutes', all timeframes)

**Performance Targets**:
- Per-endpoint: <50ms
- Total refresh: <**600ms** (7 parallel calls)
- WebSocket: <100ms

**Key Frontend Changes**:
- Expand to 7 columns in `pattern_flow.js` (lines 134-145)
- Add `loadIndicators()` method for indicators column
- Fix tier→timeframe parameter bug (line 647)
- CSS responsive breakpoints for 7 columns (14.28% width each on desktop)

**Database Reality Check**:
- ✅ Active: `intraday_patterns` (16,224 rows), `daily_patterns` (11,473 rows), `intraday_indicators` (24,099 rows)
- ⚠️ Empty (0 rows): `hourly_patterns`, `weekly_patterns`, `monthly_patterns`, `daily_intraday_patterns`
- Must handle empty tables gracefully with "No patterns detected" placeholders

**Reference**: Full implementation details in `pattern-flow-multi-table-display-AMENDMENT.md`

---


## Goal

**Change Type**: enhancement

**Current Behavior**: Pattern Flow page displays only 2 of 6 available pattern detection tables:
- ✅ `daily_patterns` (11,473 rows) - Displayed in "Daily" column
- ✅ `intraday_patterns` (16,224 rows) - Displayed in "Intraday" column
- ❌ `hourly_patterns` (0 rows) - NOT displayed
- ❌ `daily_intraday_patterns` (0 rows) - NOT displayed (combo patterns)
- ❌ `weekly_patterns` (0 rows) - NOT displayed
- ❌ `monthly_patterns` (0 rows) - NOT displayed

**Desired Behavior**: Pattern Flow page displays ALL 6 pattern detection tables with 15-second refresh:
- Display data from `intraday_patterns`, `hourly_patterns`, `daily_patterns`, `daily_intraday_patterns`, `weekly_patterns`, `monthly_patterns`
- Maintain 15-second auto-refresh cycle
- Preserve current hybrid polling + WebSocket architecture
- Support both real-time updates and bulk refresh

**Success Definition**:
- All 6 pattern tables + 1 indicators column (7 total) queryable via dedicated API endpoints
- Pattern Flow UI displays all 6 tables in organized columns
- 15-second refresh working for all tables
- Performance targets met: API <50ms, WebSocket <100ms, total refresh <600ms
- Integration tests pass with multi-table validation

**Breaking Changes**: No
- New API endpoints added (backward compatible)
- Frontend modifications maintain existing functionality
- Current 4-column display can coexist during transition

---

## User Persona

**Target User**: TickStock Traders / Analysts

**Current Pain Point**:
- Cannot see hourly, weekly, or monthly pattern detections in real-time
- Must query database directly to access 4 out of 6 pattern tables + 1 indicators column (7 total)
- Missing multi-timeframe pattern correlation (daily_intraday_patterns)
- No visibility into swing trading patterns (weekly/monthly)

**Expected Improvement**:
- Complete visibility across all timeframes (1-minute to monthly)
- Real-time updates for hourly/weekly/monthly pattern detections
- Better multi-timeframe analysis with all data in single view
- Faster pattern discovery across different trading strategies

---

## Why This Change

**Problems with Current Implementation**:
- **Incomplete Data Coverage**: Only 33% of available pattern tables displayed (2 of 6)
- **Manual Database Queries**: Users must query database for hourly/weekly/monthly patterns
- **Missing API Endpoints**: No REST endpoints for 4 pattern tables
- **Frontend Hardcoded**: Only 4 columns (Daily, Intraday, Combo, Indicators) - missing 3 real pattern tables

**Business Value**:
- **Complete Pattern Visibility**: All timeframes accessible in real-time
- **Better Trading Decisions**: Multi-timeframe analysis in single dashboard
- **Reduced Manual Work**: No need for custom database queries
- **System Completeness**: TickStockPL populates 6 tables, UI should display all 6

**Risks of NOT Making This Change**:
- Users miss swing trading opportunities (weekly/monthly patterns not visible)
- Incomplete product (backend has data, frontend doesn't show it)
- User frustration (expecting all pattern detections, only seeing 33%)
- Technical debt (pattern tables exist but unused)

---

## What Changes

### High-Level Overview

1. **Backend API**: Create 4 new REST endpoints for missing pattern tables
2. **Frontend Service**: Update Pattern Flow JavaScript to query all 6 tables
3. **UI Layout**: Adjust column layout to display 6 tables efficiently
4. **Performance**: Optimize refresh cycle to support 6 parallel API calls
5. **Testing**: Add integration tests for multi-table refresh

### Success Criteria

- [ ] All 6 pattern tables + 1 indicators column (7 total) have dedicated API endpoints (`/api/patterns/{table}`)
- [ ] Pattern Flow UI displays all 6 tables (with proper labeling)
- [ ] 15-second auto-refresh working for all 6 tables
- [ ] Existing functionality continues to work (regression-free)
- [ ] Performance metrics maintained: Total refresh <500ms
- [ ] Integration tests pass (`python run_tests.py`)
- [ ] Manual testing confirms all tables refresh correctly

---

## Current Implementation Analysis

### Files to Modify

```yaml
# Frontend Files

- file: web/static/js/services/pattern_flow.js
  current_responsibility: "Pattern Flow service - manages 4-column display with 15-second refresh"
  lines_to_modify: |
    Lines 134-139: Column definitions (add 2 new columns for hourly/weekly)
    Lines 631-642: loadInitialData() - expand to 6 table load
    Lines 644-666: loadPatternsByTier() - update tier→table mapping
    Lines 867-894: generateMockPatterns() - add hourly/weekly mock data
  current_pattern: |
    - 4 hardcoded columns: daily, intraday, combo, indicators
    - Polls /api/patterns/scan with tier parameter
    - Hybrid 15-second polling + WebSocket
  reason_for_change: "Need to support 6 tables instead of 4"

- file: web/static/css/components/pattern-flow.css
  current_responsibility: "Pattern Flow styling - 4-column layout (25% width each)"
  lines_to_modify: |
    Lines 195-207: .pattern-flow-columns flex layout (change from 4 to 7 columns)
    Lines 204-207: .pattern-column-wrapper (change from 25% to 16.67% width)
  current_pattern: "Fixed 4-column grid (flex: 1 1 25%)"
  reason_for_change: "Need responsive 6-column layout"

# Backend API Files

- file: src/api/rest/tier_patterns.py
  current_responsibility: "Tier-specific pattern API endpoints - currently has 3 endpoints"
  lines_to_modify: |
    Lines 28-123: get_daily_patterns() - keep unchanged
    Lines 125-212: get_intraday_patterns() - keep unchanged
    Lines 214-309: get_combo_patterns() - keep unchanged
    ADD NEW: get_hourly_patterns() endpoint
    ADD NEW: get_weekly_patterns() endpoint
    ADD NEW: get_monthly_patterns() endpoint
    ADD NEW: get_daily_intraday_patterns() endpoint
  current_pattern: |
    - 3 endpoints: /api/patterns/daily, /intraday, /combo
    - Query database with confidence filtering
    - Time windows: 7 days (daily), 24 hours (intraday), 3 days (combo)
  reason_for_change: "Need 4 additional endpoints for missing tables"

- file: src/api/rest/pattern_consumer.py
  current_responsibility: "Unified pattern scan API - Redis-based caching"
  lines_to_modify: |
    Lines 74-78: timeframe validation (add Hourly, Weekly, Monthly, DailyIntraday)
    Lines 113-188: scan_patterns() - update tier→timeframe mapping
  current_pattern: "Valid timeframes: All, Daily, Intraday, Combo"
  reason_for_change: "Need to support 4 new timeframes in Redis cache queries"

# Infrastructure Files

- file: src/infrastructure/cache/redis_pattern_cache.py
  current_responsibility: "Redis pattern cache - stores patterns from TickStockPL events"
  lines_to_modify: |
    Lines 50-60: source_tier enum (add hourly, weekly, monthly, daily_intraday)
    Lines 100-150: scan_patterns() - filter logic for new tiers
  current_pattern: "Caches patterns with source_tier: daily, intraday, combo"
  reason_for_change: "Need to cache patterns from 4 new tables"
```

### Current Code Patterns (What Exists Now)

```javascript
// CURRENT IMPLEMENTATION: Pattern Flow 4-Column Layout
// File: web/static/js/services/pattern_flow.js (lines 134-139)

const columns = [
    { id: 'daily', title: 'Daily', icon: '📊', color: '#007bff' },
    { id: 'intraday', title: 'Intraday', icon: '⚡', color: '#28a745' },
    { id: 'combo', title: 'Combo', icon: '🔗', color: '#17a2b8' },
    { id: 'indicators', title: 'Indicators', icon: '📈', color: '#fd7e14' }
];

// CURRENT DEPENDENCIES: What depends on this code
// - renderPatterns() expects these 4 tier IDs (lines 668-693)
// - loadInitialData() creates promises for these 4 tiers (lines 631-635)
// - state.patterns object has keys for these 4 tiers (lines 28-34)
// - WebSocket handlers subscribe to these 4 channels (line 570)

// LIMITATION: Only displays 2 real pattern tables (daily_patterns, intraday_patterns)
// - 'combo' tier queries pattern_detections (different table structure)
// - 'indicators' tier has no backend implementation (mock data only)
```

```python
# CURRENT IMPLEMENTATION: Tier Patterns API Endpoints
# File: src/api/rest/tier_patterns.py (lines 28-309)

# Existing endpoints:
@tier_patterns_bp.route('/daily', methods=['GET'])
def get_daily_patterns():
    """Query daily_patterns table with 7-day window."""
    # Lines 28-123
    pass

@tier_patterns_bp.route('/intraday', methods=['GET'])
def get_intraday_patterns():
    """Query intraday_patterns table with 24-hour window."""
    # Lines 125-212
    pass

@tier_patterns_bp.route('/combo', methods=['GET'])
def get_combo_patterns():
    """Query pattern_detections + pattern_definitions JOIN."""
    # Lines 214-309
    pass

# MISSING ENDPOINTS (need to create):
# - /hourly → hourly_patterns table
# - /weekly → weekly_patterns table
# - /monthly → monthly_patterns table
# - /daily_intraday → daily_intraday_patterns table (multi-timeframe correlations)

# CURRENT DEPENDENCIES: Who calls these endpoints
# - pattern_flow.js calls /api/patterns/scan (pattern_consumer.py) NOT these endpoints directly
# - tier_patterns.py endpoints currently UNUSED by Pattern Flow (fallback only)
```

```python
# CURRENT IMPLEMENTATION: Pattern Consumer API
# File: src/api/rest/pattern_consumer.py (lines 74-78)

# Valid timeframes (controls filtering)
timeframe = args.get('timeframe', 'All')
valid_timeframes = ['All', 'Daily', 'Intraday', 'Combo']  # ❌ Missing 4 timeframes

if timeframe != 'All' and timeframe not in valid_timeframes:
    return jsonify({'status': 'error', 'message': 'Invalid timeframe'}), 400

# CURRENT DEPENDENCIES:
# - pattern_flow.js sends tier parameter (NOT timeframe) - BUG (line 647)
# - Redis cache filters by source_tier field
# - Expects patterns cached from TickStockPL events

# LIMITATION: Only supports 3 timeframes + All
```

### Dependency Analysis

```yaml
# What DEPENDS on the code being changed

upstream_dependencies:
  # Code that CALLS the functions/classes being modified

  - component: "web/static/js/services/pattern_flow.js:loadInitialData()"
    dependency: "Creates promises for 4 tiers: daily, intraday, combo, indicators"
    impact: "Need to expand to 6 tiers (add hourly, weekly, monthly)"

  - component: "web/static/js/services/pattern_flow.js:renderPatterns()"
    dependency: "Renders patterns for each tier in state.patterns object"
    impact: "Must support 6 tier keys instead of 4"

  - component: "web/static/js/services/pattern_flow.js:setupWebSocketHandlers()"
    dependency: "Subscribes to 4 channels: patterns.daily, patterns.intraday, patterns.combo, indicators"
    impact: "May need to add channels for hourly/weekly/monthly (if TickStockPL broadcasts them)"

  - component: "web/templates/dashboard/index.html"
    dependency: "Loads pattern_flow.js service"
    impact: "No changes needed (service-based rendering)"

downstream_dependencies:
  # Code that is CALLED BY the functions/classes being modified

  - component: "src/api/rest/pattern_consumer.py:scan_patterns()"
    dependency: "Called by pattern_flow.js via /api/patterns/scan endpoint"
    impact: "Must support 4 new timeframe values"

  - component: "src/infrastructure/cache/redis_pattern_cache.py:scan_patterns()"
    dependency: "Filters cached patterns by source_tier"
    impact: "Must recognize 4 new source_tier values"

  - component: "src/core/services/redis_event_subscriber.py"
    dependency: "Receives pattern events from TickStockPL and caches them"
    impact: "May need to handle new event types (if TickStockPL sends hourly/weekly/monthly)"

database_dependencies:
  # Database schema, tables, columns relied upon

  - table: "daily_patterns"
    columns: ["id", "symbol", "pattern_type", "confidence", "pattern_data", "detection_timestamp", "expiration_date", "levels", "metadata", "timeframe"]
    impact: "Query existing - no schema changes needed"
    migration_required: No

  - table: "intraday_patterns"
    columns: ["id", "symbol", "pattern_type", "confidence", "pattern_data", "detection_timestamp", "expiration_timestamp", "levels", "metadata", "timeframe", "session_id", "bar_open", "bar_high", "bar_low", "bar_close", "bar_volume", "created_at"]
    impact: "Query existing - no schema changes needed"
    migration_required: No

  - table: "hourly_patterns"
    columns: ["id", "symbol", "pattern_type", "confidence", "pattern_data", "detection_timestamp", "expiration_timestamp", "levels", "metadata", "timeframe"]
    impact: "NEW queries needed - table exists but EMPTY (0 rows)"
    migration_required: No
    note: "TickStockPL may not populate this table - verify before implementing"

  - table: "weekly_patterns"
    columns: ["id", "symbol", "pattern_type", "confidence", "pattern_data", "detection_timestamp", "expiration_date", "levels", "metadata", "timeframe"]
    impact: "NEW queries needed - table exists but EMPTY (0 rows)"
    migration_required: No
    note: "TickStockPL may not populate this table - verify before implementing"

  - table: "monthly_patterns"
    columns: ["id", "symbol", "pattern_type", "confidence", "pattern_data", "detection_timestamp", "expiration_date", "levels", "metadata", "timeframe"]
    impact: "NEW queries needed - table exists but EMPTY (0 rows)"
    migration_required: No
    note: "TickStockPL may not populate this table - verify before implementing"

  - table: "daily_intraday_patterns"
    columns: ["id", "symbol", "pattern_type", "confidence", "pattern_data", "daily_pattern_id", "daily_pattern_timestamp", "intraday_signal", "detection_timestamp", "expiration_timestamp", "levels", "metadata", "timeframe"]
    impact: "NEW queries needed - combo pattern table (correlates daily + intraday)"
    migration_required: No
    note: "Special table structure with foreign key to daily_patterns"

redis_dependencies:
  # Redis channels, keys, message formats

  - channel: "tickstock:patterns:streaming"
    current_format: "{symbol, pattern_type, confidence, timeframe, source_tier, ...}"
    impact: "source_tier field must support 4 new values: hourly, weekly, monthly, daily_intraday"

  - channel: "tickstock:patterns:detected"
    current_format: "{symbol, pattern_type, confidence, source_tier, ...}"
    impact: "Same as above - source_tier expansion"

  - key_pattern: "patterns:cache:{tier}:*"
    current_format: "tier = daily | intraday | combo"
    impact: "Need to cache 4 new tiers"

websocket_dependencies:
  # WebSocket event types, room patterns

  - event_type: "pattern_detected"
    current_format: "{tier: string, pattern: object}"
    impact: "tier field must support 4 new values"
    frontend_handling: "pattern_flow.js:handleNewPattern() (line 742)"

  - event_type: "indicator_update"
    current_format: "{tier: 'indicators', data: object}"
    impact: "No changes needed (indicators column separate)"

  - subscription_channels: "patterns.daily, patterns.intraday, patterns.combo, indicators"
    current_format: "4 channels subscribed"
    impact: "May need to add: patterns.hourly, patterns.weekly, patterns.monthly"

external_api_dependencies:
  # External APIs, TickStockPL endpoints

  - api: "TickStockPL Pattern Detection Engine"
    current_contract: "Publishes pattern events to Redis with source_tier field"
    impact: "Need to verify TickStockPL populates hourly/weekly/monthly_patterns tables"
    coordination_required: Yes
    note: "If TickStockPL doesn't populate these tables, frontend will show empty columns"
```

### Test Coverage Analysis

```yaml
# Existing tests that cover code being modified

unit_tests:
  - test_file: "tests/unit/test_pattern_flow_service.py"
    coverage: "NOT EXISTS - no unit tests for pattern_flow.js currently"
    needs_update: N/A
    update_reason: "No existing unit tests to update"

integration_tests:
  - test_file: "tests/integration/test_pattern_flow_complete.py"
    coverage: "Tests Pattern Flow service initialization and data loading"
    needs_update: Yes
    update_reason: "Must verify 6-table refresh instead of 4"

  - test_file: "tests/integration/run_integration_tests.py"
    coverage: "Runs all integration tests including Pattern Flow"
    needs_update: Yes
    update_reason: "Update assertions for 6 tables"

  - test_file: "tests/integration/test_tickstockpl_integration.py"
    coverage: "Tests TickStockPL API integration"
    needs_update: Possibly
    update_reason: "May need to test new pattern table endpoints"

missing_coverage:
  # Test gaps that should be filled during this change

  - scenario: "Multi-table refresh performance (6 parallel API calls)"
    reason: "Need to verify <500ms total refresh time"
    test_file: "tests/integration/test_pattern_flow_performance.py (NEW)"

  - scenario: "Empty table handling (hourly/weekly/monthly may have 0 rows)"
    reason: "Frontend must gracefully handle empty responses"
    test_file: "tests/integration/test_pattern_flow_complete.py (ADD)"

  - scenario: "API endpoint parameter validation (all 6 timeframes)"
    reason: "Ensure invalid timeframe values rejected"
    test_file: "tests/unit/test_tier_patterns_api.py (ADD)"
```

---

## Impact Analysis

### Potential Breakage Points

```yaml
# What could BREAK as a result of this change

high_risk:
  # Changes with high probability of breaking something

  - component: "Pattern Flow UI layout (CSS grid)"
    risk: "7 columns may not fit on smaller screens - responsive design issue"
    mitigation: |
      - Add responsive breakpoints: 6 cols (desktop), 3 cols (tablet), 1-2 cols (mobile)
      - Test on multiple screen sizes before deployment
      - Consider tabbed interface for mobile

  - component: "API performance (6 parallel requests)"
    risk: "6 concurrent API calls could exceed backend connection pool limits"
    mitigation: |
      - Verify connection pool size can handle 6 concurrent queries
      - Monitor database connection usage during testing
      - Target: <500ms total (6 × <50ms in parallel)

  - component: "Redis cache memory usage"
    risk: "Caching 6 tables instead of 3 could increase memory usage 2x"
    mitigation: |
      - Monitor Redis memory usage before/after change
      - Implement TTL on cached patterns (1 hour default)
      - Set max cache size limits per tier

medium_risk:
  # Changes with moderate risk

  - component: "Frontend state management (this.state.patterns)"
    risk: "Expanding from 4 to 6 tier keys could cause undefined errors if not initialized"
    mitigation: |
      - Initialize all 6 tier keys in constructor (lines 28-34)
      - Add defensive checks: if (!this.state.patterns[tier]) return;
      - Test with missing tiers gracefully handled

  - component: "WebSocket subscription channels"
    risk: "Adding 3 new subscription channels could increase backend broadcast overhead"
    mitigation: |
      - Verify TickStockPL actually broadcasts hourly/weekly/monthly events
      - Only subscribe to channels that exist
      - Monitor WebSocket connection count and message throughput

  - component: "Test suite execution time"
    risk: "Testing 6 tables instead of 4 could increase test runtime"
    mitigation: |
      - Keep target: ~30 seconds total for integration tests
      - Use mocking for empty tables (hourly/weekly/monthly)
      - Parallelize test execution where possible

low_risk:
  # Changes with low risk but worth noting

  - component: "Pattern Flow CSS animations"
    risk: "Staggered animation (50ms/row × 30 rows × 7 columns = 9 seconds) too slow"
    mitigation: |
      - Reduce animation delay: 50ms → 20ms
      - Limit to top 20 patterns per column (reduce from 30)
      - Make animation delay configurable

  - component: "Browser memory usage (DOM elements)"
    risk: "7 columns × 30 patterns = 180 DOM elements vs current 120"
    mitigation: |
      - Implement virtual scrolling for columns with >20 patterns
      - Clean up old pattern rows when refresh occurs
      - Monitor browser memory in DevTools
```

### Performance Impact

```yaml
# How this change affects system performance

expected_improvements:
  - metric: "Pattern data completeness"
    current: "33% of tables displayed (2 of 6)"
    target: "100% of tables displayed (6 of 6)"
    measurement: "Visual verification in UI"

  - metric: "User workflow efficiency"
    current: "Must query database manually for 4 tables"
    target: "All tables visible in UI"
    measurement: "User feedback, reduced database query load"

potential_regressions:
  - metric: "Total refresh time"
    current: "~200ms (4 parallel API calls × 50ms each)"
    risk: "Could increase to 300ms (6 parallel calls × 50ms each)"
    threshold: "<500ms acceptable, >500ms requires optimization"
    measurement: "Browser DevTools Network tab, timing instrumentation"

  - metric: "Backend API concurrency"
    current: "4 concurrent requests every 15 seconds"
    risk: "Could increase to 6 concurrent requests (50% more load)"
    threshold: "Connection pool limit = 20, using 6 is acceptable"
    measurement: "Database connection count, pg_stat_activity"

  - metric: "Redis memory usage"
    current: "~100MB for 3 tiers (daily, intraday, combo)"
    risk: "Could increase to 200MB for 6 tiers"
    threshold: "<500MB acceptable (Redis max memory = 2GB)"
    measurement: "Redis INFO memory command"

  - metric: "Frontend rendering time"
    current: "1.5 seconds (30 patterns × 50ms animation × 4 columns)"
    risk: "Could increase to 2.25 seconds (30 × 50ms × 7 columns)"
    threshold: "<3 seconds acceptable"
    measurement: "Browser DevTools Performance profiler"
    optimization: "Reduce animation delay to 20ms → 1.2 seconds total"
```

### Backward Compatibility

```yaml
backward_compatibility:
  breaking_changes: No

  # Why change is backward compatible
  compatibility_guarantee: |
    - All existing API endpoints preserved (/api/patterns/daily, /intraday, /combo)
    - New endpoints ADDED, none removed (/api/patterns/hourly, /weekly, /monthly)
    - Frontend JavaScript changes are additive (4 columns → 7 columns)
    - Current 4-column layout can coexist during transition
    - Database queries use SELECT with explicit columns (no schema changes)
    - Redis message formats unchanged (internal source_tier field expanded)
    - WebSocket event structure unchanged (tier field values expanded)

  phased_rollout:
    # Optional: Deploy in phases to reduce risk

    phase_1: "Backend API endpoints (safe to deploy independently)"
      - Add 4 new endpoints to tier_patterns.py
      - Update pattern_consumer.py timeframe validation
      - Deploy and verify via Postman/curl

    phase_2: "Frontend UI update (depends on Phase 1)"
      - Update pattern_flow.js to query 6 tables
      - Update CSS for 6-column layout
      - Deploy and verify in browser

    phase_3: "Redis cache expansion (optional enhancement)"
      - Update redis_pattern_cache.py to support new tiers
      - Verify TickStockPL populates new tables
      - Enable WebSocket subscriptions for new channels
```

---

## All Needed Context

### Context Completeness Check

✅ **Passes "No Prior Knowledge" Test**

_Someone unfamiliar with TickStock codebase would have:_
- Complete file list with line numbers
- BEFORE/AFTER code examples
- Dependency map (what calls what)
- Database schema for all 6 tables
- API endpoint specifications
- Performance targets and measurements
- Testing requirements

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: TickStockAppV2
  role: Consumer

  redis_channels:
    - channel: "tickstock:patterns:streaming"
      change_type: message_format
      current_behavior: "source_tier field has values: daily, intraday, combo"
      new_behavior: "source_tier field expanded: daily, hourly, intraday, weekly, monthly, daily_intraday"

    - channel: "tickstock:patterns:detected"
      change_type: message_format
      current_behavior: "Same as streaming channel"
      new_behavior: "Same expansion as above"

  database_access:
    mode: read-only
    tables_affected:
      - daily_patterns (existing, no changes)
      - intraday_patterns (existing, no changes)
      - hourly_patterns (new queries)
      - weekly_patterns (new queries)
      - monthly_patterns (new queries)
      - daily_intraday_patterns (new queries)
    queries_modified: "Add 4 new SELECT queries for missing tables"
    schema_changes: No

  websocket_integration:
    affected: Yes
    broadcast_changes: "No changes to broadcast logic"
    message_format_changes: "tier field accepts 4 new values (hourly, weekly, monthly, daily_intraday)"

  tickstockpl_api:
    affected: Possibly
    endpoint_changes: None
    coordination_required: Yes
    note: |
      CRITICAL: Verify TickStockPL actually populates hourly/weekly/monthly/daily_intraday_patterns tables.
      If TickStockPL doesn't populate these tables, frontend will display empty columns.
      Check with TickStockPL team before finalizing implementation.

  performance_targets:
    - metric: "API response time"
      current: "<50ms per endpoint"
      target: "<50ms per endpoint (unchanged)"

    - metric: "Total refresh time"
      current: "~200ms (4 parallel calls)"
      target: "<500ms (6 parallel calls)"

    - metric: "WebSocket delivery"
      current: "<100ms end-to-end"
      target: "<100ms end-to-end (unchanged)"

    - metric: "Database query time"
      current: "<50ms per query"
      target: "<50ms per query (unchanged)"
```

### Documentation & References

```yaml
# MUST READ - Include these in your context window

# Current implementation references (CRITICAL for modifications)

- file: web/static/js/services/pattern_flow.js
  why: "Current Pattern Flow service - MUST understand before modifying"
  lines: |
    17-24: Configuration (refresh interval, polling, WebSocket)
    28-39: State management (patterns object with 4 tiers)
    134-139: Column definitions (MUST expand to 6)
    576-603: Auto-refresh mechanism (polling logic)
    626-666: Data loading (MUST expand to 6 tables)
    742-757: Real-time pattern handling (WebSocket)
  pattern: "Hybrid polling (15s) + WebSocket (real-time) architecture"
  gotcha: |
    - Line 647: Uses wrong parameter (tier vs timeframe) - BUG to fix
    - Staggered animation (50ms/row) can be slow with 7 columns
    - Mock data fallback if API fails (lines 660-664)

- file: src/api/rest/tier_patterns.py
  why: "Existing tier patterns API - template for new endpoints"
  lines: |
    28-123: get_daily_patterns() - COPY pattern for new endpoints
    125-212: get_intraday_patterns() - COPY pattern
    214-309: get_combo_patterns() - Different (JOIN query, not template)
  pattern: |
    - Query database with confidence_min filter (default 0.6)
    - Time window filtering (7 days daily, 24 hours intraday)
    - Returns JSON: {patterns: [...], metadata: {...}}
    - Error handling: try-except-finally with connection cleanup
  gotcha: |
    - daily_patterns uses expiration_date, intraday uses expiration_timestamp (column name difference)
    - Composite primary key on daily_patterns: (id, detection_timestamp)
    - Simple primary key on hourly/weekly/monthly: (id)

- file: src/api/rest/pattern_consumer.py
  why: "Unified pattern scan API - handles timeframe parameter"
  lines: |
    74-78: timeframe validation (MUST add 4 new values)
    113-188: scan_patterns() endpoint logic
  pattern: "Validates timeframe, queries Redis cache, returns patterns with pagination"
  gotcha: |
    - Uses 'timeframe' parameter (not 'tier')
    - Frontend sends 'tier' parameter (BUG - needs fix in pattern_flow.js)
    - Response includes performance metrics (api_response_time_ms)

# Similar working features (for pattern consistency)

- file: web/static/js/services/pattern-discovery.js
  why: "Similar pattern service - multi-tier pattern display"
  pattern: "Service-based architecture with API polling and WebSocket"
  gotcha: "Uses TierPatternService for data abstraction"

- file: src/infrastructure/cache/redis_pattern_cache.py
  why: "Redis caching layer - must support new tiers"
  pattern: "Caches patterns with source_tier field, scan_patterns() filters by tier"
  gotcha: "TTL management, cache eviction, memory limits"

# External documentation

- url: https://flask.palletsprojects.com/en/2.3.x/patterns/blueprints/
  why: "Blueprint registration pattern for new API endpoints"
  critical: "Register new endpoints in src/api/rest/main.py"

- url: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout/Basic_Concepts_of_Flexbox
  why: "CSS flexbox for 6-column layout"
  critical: "Change flex: 1 1 25% to flex: 1 1 16.67% (100% / 7)"

- url: https://socket.io/docs/v4/client-api/
  why: "SocketIO client API for WebSocket subscriptions"
  critical: "May need to add new channel subscriptions (patterns.hourly, etc.)"

# TickStock-Specific References

- file: docs/PRPs/ai_docs/flask_patterns.md
  why: "Flask patterns and gotchas specific to TickStockAppV2"
  pattern: |
    - Blueprint Registration Pattern (#2)
    - Error Handling Pattern (#5)
    - Database Connection Pattern (#6)
  gotcha: |
    - Use Flask current_app context for runtime state
    - Always close database connections in finally block
    - Use parameterized queries (prevent SQL injection)

- file: docs/PRPs/ai_docs/redis_patterns.md
  why: "Redis pub-sub patterns for TickStock"
  pattern: "Event subscription, message parsing, WebSocket broadcasting"
  gotcha: "Always convert typed events to dicts at Worker boundary"

- file: tests/integration/run_integration_tests.py
  why: "Integration test structure - for adding new tests"
  pattern: "Test setup, mocking, assertions, ~30 second target"
  gotcha: "Must complete in ~30 seconds total"

# Database Schema References (from earlier research)

- database_schema: |
    All 6 tables exist in database:

    1. intraday_patterns (16,224 rows) - ACTIVE
       - Columns: id, symbol, pattern_type, confidence, pattern_data, detection_timestamp, expiration_timestamp, levels, metadata, timeframe, session_id, bar_open, bar_high, bar_low, bar_close, bar_volume, created_at
       - Primary Key: (id, detection_timestamp) - composite
       - Time range: Last 30 minutes

    2. hourly_patterns (0 rows) - EMPTY
       - Columns: id, symbol, pattern_type, confidence, pattern_data, detection_timestamp, expiration_timestamp, levels, metadata, timeframe
       - Primary Key: (id) - simple
       - Time range: Last 1 hour (recommended)

    3. daily_patterns (11,473 rows) - ACTIVE
       - Columns: id, symbol, pattern_type, confidence, pattern_data, detection_timestamp, expiration_date, levels, metadata, timeframe
       - Primary Key: (id, detection_timestamp) - composite
       - Time range: Last 1 hour
       - NOTE: Uses expiration_date (not expiration_timestamp)

    4. daily_intraday_patterns (0 rows) - EMPTY
       - Columns: id, symbol, pattern_type, confidence, pattern_data, daily_pattern_id, daily_pattern_timestamp, intraday_signal, detection_timestamp, expiration_timestamp, levels, metadata, timeframe
       - Primary Key: (id, detection_timestamp) - composite
       - Foreign Key: (daily_pattern_id, daily_pattern_timestamp) → daily_patterns
       - Time range: Last 14 days (recommended)
       - Special: Contains intraday_signal JSONB field for correlation data

    5. weekly_patterns (0 rows) - EMPTY
       - Columns: id, symbol, pattern_type, confidence, pattern_data, detection_timestamp, expiration_date, levels, metadata, timeframe
       - Primary Key: (id) - simple
       - Time range: This week (since Monday) (recommended)

    6. monthly_patterns (0 rows) - EMPTY
       - Columns: id, symbol, pattern_type, confidence, pattern_data, detection_timestamp, expiration_date, levels, metadata, timeframe
       - Primary Key: (id) - simple
       - Time range: This month (since 1st) (recommended)
```

### Current Codebase Tree (files being modified)

```bash
TickStockAppV2/
├── web/
│   ├── static/
│   │   ├── js/
│   │   │   └── services/
│   │   │       └── pattern_flow.js          # MODIFY: Expand to 6 tables
│   │   └── css/
│   │       └── components/
│   │           ├── pattern-flow.css         # MODIFY: 6-column layout
│   │           └── pattern-flow-override.css # PRESERVE: Theme overrides
│   └── templates/
│       └── dashboard/
│           └── index.html                   # PRESERVE: No changes needed
│
├── src/
│   ├── api/
│   │   └── rest/
│   │       ├── tier_patterns.py             # MODIFY: Add 4 new endpoints
│   │       ├── pattern_consumer.py          # MODIFY: Add 4 timeframes
│   │       └── main.py                      # PRESERVE: Blueprint registration already exists
│   │
│   └── infrastructure/
│       └── cache/
│           └── redis_pattern_cache.py       # MODIFY: Support 4 new tiers
│
├── tests/
│   └── integration/
│       ├── test_pattern_flow_complete.py    # UPDATE: Test 6 tables
│       └── run_integration_tests.py         # UPDATE: Add multi-table tests
│
└── docs/
    └── planning/
        └── sprints/
            └── sprint46/
                └── pattern-flow-multi-table-display.md  # THIS FILE
```

### Known Gotchas of Current Code & Library Quirks

```python
# CRITICAL: Document existing gotchas that must be preserved or addressed

# Current Code Gotchas

# GOTCHA 1: Frontend Parameter Mismatch (BUG)
# File: web/static/js/services/pattern_flow.js (line 647)
# Issue: Sends 'tier' parameter to API, but API expects 'timeframe'
async loadPatternsByTier(tier) {
    const response = await fetch(`/api/patterns/scan?tier=${tier}&limit=30&sort=timestamp_desc`);
    # ❌ API doesn't recognize 'tier' parameter
    # ✅ Should use 'timeframe' parameter with mapped values
}

# FIX REQUIRED:
const timeframeMap = {
    daily: 'Daily',
    hourly: 'Hourly',
    intraday: 'Intraday',
    weekly: 'Weekly',
    monthly: 'Monthly',
    daily_intraday: 'DailyIntraday'
};
const timeframe = timeframeMap[tier] || 'All';
const response = await fetch(`/api/patterns/scan?timeframe=${timeframe}&limit=30&sort_by=detected_at&sort_order=desc`);


# GOTCHA 2: Database Column Name Inconsistency
# Daily patterns use 'expiration_date', others use 'expiration_timestamp'
# File: src/api/rest/tier_patterns.py (lines 90, 175)

# daily_patterns:
cursor.execute("SELECT ... expiration_date ... FROM daily_patterns")

# intraday_patterns, hourly_patterns:
cursor.execute("SELECT ... expiration_timestamp ... FROM intraday_patterns")

# PRESERVE: Use correct column name per table


# GOTCHA 3: Primary Key Differences
# Some tables have composite keys, others have simple keys
# Impact: Pagination, ordering, uniqueness constraints

# Composite: daily_patterns, intraday_patterns, daily_intraday_patterns
PRIMARY KEY (id, detection_timestamp)

# Simple: hourly_patterns, weekly_patterns, monthly_patterns
PRIMARY KEY (id)

# PRESERVE: Query patterns must account for PK structure


# GOTCHA 4: Empty Tables (TickStockPL Dependency)
# hourly, weekly, monthly, daily_intraday tables currently have 0 rows
# Risk: Frontend displays empty columns if TickStockPL doesn't populate

# MITIGATION:
# - Add "No patterns detected" placeholder in UI
# - Check with TickStockPL team: Do they populate these tables?
# - Consider mock data for testing/demo


# TickStock-Specific Gotchas (from CLAUDE.md)

# CRITICAL: Never mix typed events and dicts after Worker boundary
# File: src/core/services/redis_event_subscriber.py
# Pattern events from Redis must be converted to dicts before WebSocket broadcast

# CRITICAL: TickStockAppV2 is CONSUMER ONLY (no pattern detection logic)
# Pattern detection happens in TickStockPL, AppV2 only displays results
# Don't add pattern detection algorithms to AppV2

# CRITICAL: Flask Application Context - use current_app, not module globals
# File: docs/PRPs/ai_docs/flask_patterns.md (Pattern #1)
from flask import current_app
redis_subscriber = getattr(current_app, 'redis_subscriber', None)


# Library-Specific Quirks

# SQLAlchemy/psycopg2: Connection cleanup in finally block
# File: docs/PRPs/ai_docs/flask_patterns.md (Pattern #6)
conn = None
try:
    conn = get_connection()
    # ... use connection
finally:
    if conn:
        conn.close()  # MANDATORY

# Flask-SocketIO: broadcast=True required for multi-client delivery
# File: docs/PRPs/ai_docs/flask_patterns.md (Pattern #3)
emit('pattern_detected', message, room=room, broadcast=True)

# Redis TTL: Patterns cached with 1-hour expiration
# File: src/infrastructure/cache/redis_pattern_cache.py
# Must ensure old patterns expire to prevent stale data
```

---

## Change Implementation Blueprint

### Pre-Change Preparation

```yaml
# Steps to take BEFORE modifying code

1_backup_current_state:
  - action: "Create git branch"
    command: "git checkout -b sprint46/pattern-flow-multi-table-display"

  - action: "Document current behavior"
    command: |
      # Open Pattern Flow page in browser
      # Take screenshots of current 4-column layout
      # Note refresh timing (15 seconds)
      # Verify only Daily and Intraday columns have data

  - action: "Run baseline tests"
    command: "python run_tests.py"
    expected: "2 tests passing, ~30 seconds runtime"

2_analyze_dependencies:
  - action: "Find all uses of pattern_flow.js functions"
    command: "rg 'PatternFlowService|loadPatternsByTier|renderPatterns' web/"

  - action: "Find all API endpoint callers"
    command: "rg '/api/patterns/(scan|daily|intraday|combo)' web/"

  - action: "Identify database queries to pattern tables"
    command: "rg '(daily|intraday|hourly|weekly|monthly)_patterns' src/"

  - action: "Check Redis channel usage"
    command: "rg 'patterns\\.(daily|intraday|combo)' src/"

3_verify_tickstockpl_integration:
  - action: "Check if TickStockPL populates all 6 tables"
    command: |
      psql -U app_readwrite -d tickstock -c "
      SELECT
        'daily_patterns' as table_name, COUNT(*) as row_count FROM daily_patterns
      UNION ALL
      SELECT 'intraday_patterns', COUNT(*) FROM intraday_patterns
      UNION ALL
      SELECT 'hourly_patterns', COUNT(*) FROM hourly_patterns
      UNION ALL
      SELECT 'weekly_patterns', COUNT(*) FROM weekly_patterns
      UNION ALL
      SELECT 'monthly_patterns', COUNT(*) FROM monthly_patterns
      UNION ALL
      SELECT 'daily_intraday_patterns', COUNT(*) FROM daily_intraday_patterns;
      "
    expected: |
      daily_patterns: 11,473
      intraday_patterns: 16,224
      hourly_patterns: 0 (EMPTY - verify with TickStockPL team)
      weekly_patterns: 0 (EMPTY - verify with TickStockPL team)
      monthly_patterns: 0 (EMPTY - verify with TickStockPL team)
      daily_intraday_patterns: 0 (EMPTY - verify with TickStockPL team)

  - action: "Coordinate with TickStockPL team"
    note: |
      CRITICAL: Before implementing, confirm:
      1. Does TickStockPL populate hourly_patterns?
      2. Does TickStockPL populate weekly_patterns?
      3. Does TickStockPL populate monthly_patterns?
      4. Does TickStockPL populate daily_intraday_patterns?

      If NO → Consider phased implementation (skip empty tables for now)
      If YES → Proceed with full 6-table implementation

4_create_regression_baseline:
  - action: "Document current Pattern Flow behavior"
    location: "tests/integration/test_pattern_flow_regression.py (NEW)"
    content: |
      # Baseline test: Verify current 4-column behavior works
      # - Daily column shows data from daily_patterns
      # - Intraday column shows data from intraday_patterns
      # - 15-second refresh interval maintained
      # - WebSocket events handled correctly
```

### Change Tasks (ordered by dependencies)

```yaml
# Task order ensures dependencies resolved before usage

Task 1: ADD new API endpoints to tier_patterns.py
  PRIORITY: 1 (Backend first, frontend depends on it)

  FILE: src/api/rest/tier_patterns.py

  CURRENT: |
    - 3 endpoints: /api/patterns/daily, /intraday, /combo
    - Pattern: Query database, filter by confidence, return JSON

  ADD_ENDPOINTS:
    # 1. Hourly patterns endpoint
    - route: /api/patterns/hourly
      table: hourly_patterns
      time_window: "1 hour"
      primary_key: "id (simple)"
      expiration_column: "expiration_timestamp"
      template: "Copy from get_intraday_patterns() (lines 125-212)"

    # 2. Weekly patterns endpoint
    - route: /api/patterns/weekly
      table: weekly_patterns
      time_window: "This week (since Monday)"
      primary_key: "id (simple)"
      expiration_column: "expiration_date"
      template: "Similar to get_daily_patterns() (lines 28-123)"

    # 3. Monthly patterns endpoint
    - route: /api/patterns/monthly
      table: monthly_patterns
      time_window: "This month (since 1st)"
      primary_key: "id (simple)"
      expiration_column: "expiration_date"
      template: "Similar to get_daily_patterns() (lines 28-123)"

    # 4. Daily-intraday combo patterns endpoint
    - route: /api/patterns/daily_intraday
      table: daily_intraday_patterns
      time_window: "30 minutes"
      primary_key: "(id, detection_timestamp) composite"
      expiration_column: "expiration_timestamp"
      special: "Includes intraday_signal JSONB field"
      template: "Similar to get_intraday_patterns() but add intraday_signal column"

    # 5. Indicators endpoint (NEW - not a pattern table)
    - route: /api/patterns/indicators/latest
      table: intraday_indicators
      time_window: "30 minutes"
      timeframe_handling: "Single table with 'timeframe' column (1min, 5min, hourly, daily)"
      primary_key: "id (simple)"
      expiration_column: "expiration_timestamp"
      special: "Returns indicators across ALL timeframes in single response"
      template: "NEW endpoint - see AMENDMENT for full implementation"


  CODE_PATTERN:
    ```python
    @tier_patterns_bp.route('/hourly', methods=['GET'])
    @login_required
    def get_hourly_patterns():
        """
        Get hourly tier patterns from hourly_patterns table.

        Query Parameters:
            symbols: Comma-separated symbol list (optional)
            confidence_min: Minimum confidence (default: 0.6)
            limit: Max patterns (default: 50, max: 200)

        Returns:
            JSON: {patterns: [...], metadata: {...}}
        """
        conn = None
        try:
            # Parse query params
            symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else None
            confidence_min = float(request.args.get('confidence_min', 0.6))
            limit = min(int(request.args.get('limit', 50)), 200)

            # Database connection
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build query (7-day window for hourly)
            query = """
                SELECT id, symbol, pattern_type, confidence, pattern_data,
                       detection_timestamp, expiration_timestamp, levels, metadata
                FROM hourly_patterns
                WHERE confidence >= %s
                  AND detection_timestamp > NOW() - INTERVAL '1 hour'
            """
            params = [confidence_min]

            if symbols:
                query += " AND symbol IN %s"
                params.append(tuple(symbols))

            query += " ORDER BY confidence DESC, detection_timestamp DESC LIMIT %s"
            params.append(limit)

            # Execute
            cursor.execute(query, params)
            patterns = cursor.fetchall()

            # Format response
            return jsonify({
                'patterns': [dict(p) for p in patterns],
                'metadata': {
                    'count': len(patterns),
                    'tier': 'hourly',
                    'confidence_min': confidence_min,
                    'response_time_ms': round((time.time() - start_time) * 1000, 2)
                }
            }), 200

        except Exception as e:
            logger.error(f"Error fetching hourly patterns: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

        finally:
            if conn:
                conn.close()
    ```

  PRESERVE:
    - @login_required decorator (authentication required)
    - Error handling pattern (try-except-finally)
    - Connection cleanup (finally block)
    - Response format: {patterns: [...], metadata: {...}}

  GOTCHA:
    - hourly_patterns uses expiration_timestamp (not expiration_date)
    - Primary key is simple (id) not composite
    - Table currently empty (0 rows) - verify TickStockPL populates

  VALIDATION:
    command: "curl -X GET http://localhost:5000/api/patterns/hourly -H 'Cookie: session=...'"
    expected: "200 OK, {patterns: [], metadata: {tier: 'hourly', count: 0}}"

  DEPENDENCIES: None (can implement independently)

---

Task 2: UPDATE pattern_consumer.py to support new timeframes
  PRIORITY: 2 (Depends on Task 1 completion)

  FILE: src/api/rest/pattern_consumer.py

  CURRENT: |
    # Lines 74-78: timeframe validation
    valid_timeframes = ['All', 'Daily', 'Intraday', 'Combo']

  CHANGE:
    ```python
    # BEFORE
    valid_timeframes = ['All', 'Daily', 'Intraday', 'Combo']

    # AFTER
    valid_timeframes = [
        'All',
        'Daily',
        'Hourly',        # NEW
        'Intraday',
        'Weekly',        # NEW
        'Monthly',       # NEW
        'Combo',
        'DailyIntraday'  # NEW (combo pattern table)
    ]
    ```

  PRESERVE:
    - 'All' timeframe (returns all patterns)
    - Existing 3 timeframes (Daily, Intraday, Combo)
    - Error handling for invalid timeframes

  GOTCHA:
    - Case-sensitive: 'Hourly' not 'hourly'
    - Redis cache must have patterns with these source_tier values
    - If TickStockPL doesn't send events, cache will be empty

  VALIDATION:
    command: "curl -X GET 'http://localhost:5000/api/patterns/scan?timeframe=Hourly&limit=10'"
    expected: "200 OK, {patterns: [], ...} (empty if TickStockPL not populating)"

  DEPENDENCIES: Task 1 (new endpoints available)

---

Task 3: UPDATE redis_pattern_cache.py to support new tiers
  PRIORITY: 2 (Parallel with Task 2, both update backend)

  FILE: src/infrastructure/cache/redis_pattern_cache.py

  CURRENT: |
    # source_tier enum/validation
    valid_tiers = ['daily', 'intraday', 'combo']

  CHANGE:
    ```python
    # BEFORE
    valid_tiers = ['daily', 'intraday', 'combo']

    # AFTER
    valid_tiers = [
        'daily',
        'hourly',         # NEW
        'intraday',
        'weekly',         # NEW
        'monthly',        # NEW
        'daily_intraday'  # NEW (underscore, not camelCase)
    ]
    ```

  PRESERVE:
    - TTL management (1 hour default)
    - Cache eviction logic
    - Event parsing from Redis pub-sub

  GOTCHA:
    - Lowercase tier names (daily_intraday not DailyIntraday)
    - Must match TickStockPL event source_tier field
    - Memory usage increases with 6 tiers vs 3

  VALIDATION:
    - Monitor Redis memory: redis-cli INFO memory
    - Verify patterns cached with new tier values

  DEPENDENCIES: Task 1 (tier values defined)

---

Task 4: MODIFY pattern_flow.js frontend service
  PRIORITY: 3 (Depends on backend Tasks 1-3)

  FILE: web/static/js/services/pattern_flow.js

  CURRENT: |
    # Lines 28-39: State with 4 tiers
    state: {
        patterns: {
            daily: [],
            intraday: [],
            combo: [],
            indicators: []
        }
    }

    # Lines 134-139: 4 column definitions
    columns = [
        { id: 'daily', title: 'Daily', icon: '📊', color: '#007bff' },
        { id: 'intraday', title: 'Intraday', icon: '⚡', color: '#28a745' },
        { id: 'combo', title: 'Combo', icon: '🔗', color: '#17a2b8' },
        { id: 'indicators', title: 'Indicators', icon: '📈', color: '#fd7e14' }
    ];

  CHANGE_1_STATE:
    ```javascript
    // AFTER: 6 tier state
    state: {
        patterns: {
            daily: [],
            hourly: [],          // NEW
            intraday: [],
            weekly: [],          // NEW
            monthly: [],         // NEW
            daily_intraday: []   // NEW (replace 'combo')
        }
    }
    ```

  CHANGE_2_COLUMNS:
    ```javascript
    // AFTER: 6 column definitions
    columns = [
        { id: 'daily', title: 'Daily', icon: '📊', color: '#007bff' },
        { id: 'hourly', title: 'Hourly', icon: '⏰', color: '#6f42c1' },      // NEW
        { id: 'intraday', title: 'Intraday', icon: '⚡', color: '#28a745' },
        { id: 'weekly', title: 'Weekly', icon: '📈', color: '#20c997' },      // NEW
        { id: 'monthly', title: 'Monthly', icon: '📅', color: '#e83e8c' },    // NEW
        { id: 'daily_intraday', title: 'Combo', icon: '🔗', color: '#17a2b8' } // RENAME (combo → daily_intraday)
    ];
    ```

  CHANGE_3_DATA_LOADING:
    ```javascript
    // BEFORE (lines 631-635)
    async loadInitialData() {
        const promises = ['daily', 'intraday', 'combo', 'indicators'].map(tier =>
            this.loadPatternsByTier(tier)
        );
        await Promise.all(promises);
    }

    // AFTER: 6 tiers
    async loadInitialData() {
        const promises = [
            'daily', 'hourly', 'intraday',
            'weekly', 'monthly', 'daily_intraday'
        ].map(tier => this.loadPatternsByTier(tier));

        await Promise.all(promises);
    }
    ```

  CHANGE_4_FIX_PARAMETER_BUG:
    ```javascript
    // BEFORE (line 647) - BUG: Uses 'tier' parameter
    async loadPatternsByTier(tier) {
        const response = await fetch(`/api/patterns/scan?tier=${tier}&limit=30&sort=timestamp_desc`);
        // ❌ API doesn't recognize 'tier' parameter
    }

    // AFTER: Fix parameter mapping
    async loadPatternsByTier(tier) {
        // Map tier IDs to API timeframe values
        const timeframeMap = {
            daily: 'Daily',
            hourly: 'Hourly',
            intraday: 'Intraday',
            weekly: 'Weekly',
            monthly: 'Monthly',
            daily_intraday: 'DailyIntraday'
        };

        const timeframe = timeframeMap[tier] || 'All';

        // ✅ Use correct parameter names
        const response = await fetch(
            `/api/patterns/scan?timeframe=${timeframe}&limit=30&sort_by=detected_at&sort_order=desc`
        );

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        this.state.patterns[tier] = data.patterns || [];
        this.renderPatterns(tier);
    }
    ```

  PRESERVE:
    - 15-second refresh interval (line 18)
    - Hybrid polling + WebSocket architecture
    - Pattern row creation logic (lines 695-724)
    - Error handling with mock data fallback

  GOTCHA:
    - Fix tier→timeframe parameter mapping (BUG in current code)
    - Add empty state handling for hourly/weekly/monthly (tables may be empty)
    - Staggered animation: 50ms × 30 rows × 7 columns = 9 seconds (too slow)
    - Recommendation: Reduce to 20ms or limit to 20 patterns/column

  VALIDATION:
    - Open Pattern Flow page in browser
    - Verify 7 columns displayed
    - Check browser console for API errors
    - Confirm 15-second refresh working
    - Verify empty tables show "No patterns detected" message

  DEPENDENCIES: Tasks 1-3 (backend API ready)

---

Task 5: MODIFY pattern-flow.css for 6-column layout
  PRIORITY: 3 (Parallel with Task 4, both frontend)

  FILE: web/static/css/components/pattern-flow.css

  CURRENT: |
    # Lines 195-207: 4-column grid layout
    .pattern-flow-columns {
        display: flex;
        gap: 15px;
    }

    .pattern-column-wrapper {
        flex: 1 1 25%;  /* 100% / 4 = 25% */
    }

  CHANGE:
    ```css
    /* AFTER: 6-column responsive layout */
    .pattern-flow-columns {
        display: flex;
        flex-wrap: wrap;  /* NEW: Allow wrapping on small screens */
        gap: 15px;
    }

    /* Desktop: 7 columns */
    @media (min-width: 1600px) {
        .pattern-column-wrapper {
            flex: 1 1 calc(14.28% - 13px);  /* 100% / 7 */
        }
    }

    /* Laptop: 4 columns */
    @media (min-width: 992px) and (max-width: 1399px) {
        .pattern-column-wrapper {
            flex: 1 1 calc(25% - 15px);  /* 100% / 4 */
        }
    }

    /* Tablet: 3 columns */
    @media (min-width: 768px) and (max-width: 991px) {
        .pattern-column-wrapper {
            flex: 1 1 calc(33.33% - 15px);  /* 100% / 3 */
        }
    }

    /* Mobile: 1 column */
    @media (max-width: 767px) {
        .pattern-column-wrapper {
            flex: 1 1 100%;
        }
    }
    ```

  PRESERVE:
    - Column gap (15px)
    - Flexbox layout
    - Smooth transitions (var(--transition-base))
    - Theme-specific overrides (lines 399-495)

  GOTCHA:
    - Must account for gap in width calculation: calc(14.28% - 13px)
    - Test on multiple screen sizes (desktop, laptop, tablet, mobile)
    - Dark theme overrides must still work

  VALIDATION:
    - Resize browser window to test breakpoints
    - Verify columns stack properly on mobile
    - Check spacing and alignment at each breakpoint

  DEPENDENCIES: Task 4 (frontend JavaScript ready)

---

Task 6: UPDATE integration tests for 6-table validation
  PRIORITY: 4 (After implementation, before deployment)

  FILE: tests/integration/test_pattern_flow_complete.py

  CURRENT: |
    # Tests 4-column Pattern Flow initialization

  MODIFY:
    ```python
    # BEFORE
    def test_pattern_flow_initialization():
        """Test Pattern Flow service initializes with 4 columns."""
        assert len(columns) == 4
        assert 'daily' in columns
        assert 'intraday' in columns
        assert 'combo' in columns
        assert 'indicators' in columns

    # AFTER
    def test_pattern_flow_initialization():
        """Test Pattern Flow service initializes with 7 columns."""
        assert len(columns) == 6
        assert 'daily' in columns
        assert 'hourly' in columns
        assert 'intraday' in columns
        assert 'weekly' in columns
        assert 'monthly' in columns
        assert 'daily_intraday' in columns
    ```

  ADD_NEW:
    ```python
    def test_all_pattern_tables_queryable():
        """Test all 6 pattern tables + 1 indicators column (7 total) have API endpoints."""
        tables = ['daily', 'hourly', 'intraday', 'weekly', 'monthly', 'daily_intraday']

        for table in tables:
            response = client.get(f'/api/patterns/{table}')
            assert response.status_code in [200, 401]  # 200 or auth required

    def test_multi_table_refresh_performance():
        """Test 6-table refresh completes within 500ms target."""
        import time
        start = time.time()

        # Simulate parallel API calls
        promises = []
        for tier in ['daily', 'hourly', 'intraday', 'weekly', 'monthly', 'daily_intraday']:
            response = client.get(f'/api/patterns/scan?timeframe={tier.title()}&limit=30')
            promises.append(response)

        duration = (time.time() - start) * 1000
        assert duration < 500, f"Refresh took {duration}ms, target <500ms"

    def test_empty_table_handling():
        """Test graceful handling of empty pattern tables."""
        # hourly, weekly, monthly tables currently empty
        response = client.get('/api/patterns/hourly')
        assert response.status_code == 200
        data = response.json()
        assert data['patterns'] == []
        assert data['metadata']['count'] == 0
    ```

  PRESERVE:
    - Existing test fixtures
    - ~30 second total test runtime
    - Mock data patterns

  VALIDATION:
    command: "python run_tests.py"
    expected: "All tests passing, including new 6-table tests"

  DEPENDENCIES: Tasks 1-5 (all implementation complete)

---

Task 7: ADD WebSocket subscriptions for new channels (OPTIONAL)
  PRIORITY: 5 (Enhancement, not critical)

  FILE: web/static/js/services/pattern_flow.js

  CURRENT: |
    # Lines 569-571: Subscribe to 4 channels
    this.socket.emit('subscribe', {
        channels: ['patterns.daily', 'patterns.intraday', 'patterns.combo', 'indicators']
    });

  CHANGE:
    ```javascript
    // AFTER: Subscribe to 6 channels (if TickStockPL broadcasts them)
    this.socket.emit('subscribe', {
        channels: [
            'patterns.daily',
            'patterns.hourly',         // NEW (verify TickStockPL sends)
            'patterns.intraday',
            'patterns.weekly',         // NEW (verify TickStockPL sends)
            'patterns.monthly',        // NEW (verify TickStockPL sends)
            'patterns.daily_intraday'  // NEW (combo patterns)
        ]
    });
    ```

  PREREQUISITE:
    - Verify TickStockPL broadcasts pattern events for hourly/weekly/monthly
    - Check src/core/services/redis_event_subscriber.py for channel subscriptions
    - Coordinate with TickStockPL team

  GOTCHA:
    - If TickStockPL doesn't broadcast these channels, subscription is harmless but useless
    - May increase WebSocket connection overhead (6 channels vs 4)

  VALIDATION:
    - Monitor browser WebSocket messages in DevTools
    - Verify real-time updates for new channels

  DEPENDENCIES: Task 4 (frontend ready), TickStockPL coordination
```

### Change Patterns & Key Details

```python
# ═══════════════════════════════════════════════════════════════
# Pattern 1: Adding New API Endpoint (Hourly Patterns Example)
# ═══════════════════════════════════════════════════════════════

# BEFORE: No hourly endpoint exists
# File: src/api/rest/tier_patterns.py

# AFTER: New hourly endpoint added
# File: src/api/rest/tier_patterns.py (NEW LINES ~312-380)

@tier_patterns_bp.route('/hourly', methods=['GET'])
@login_required
def get_hourly_patterns():
    """
    Get hourly tier patterns from hourly_patterns table.

    Query Parameters:
        symbols: Comma-separated list of symbols (optional)
        confidence_min: Minimum confidence threshold (default: 0.6)
        limit: Maximum number of patterns to return (default: 50, max: 200)

    Returns:
        JSON: {
            patterns: [
                {
                    id: int,
                    symbol: str,
                    pattern_type: str,
                    confidence: float,
                    pattern_data: dict,
                    detection_timestamp: str,
                    expiration_timestamp: str,
                    levels: list,
                    metadata: dict
                }
            ],
            metadata: {
                count: int,
                tier: "hourly",
                confidence_min: float,
                response_time_ms: float
            }
        }

    HTTP Status Codes:
        200: Success, patterns returned
        400: Invalid parameters (confidence_min, limit)
        500: Database error
        503: Database unavailable
    """
    start_time = time.time()
    conn = None

    try:
        # 1. Parse and validate query parameters
        symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else None

        try:
            confidence_min = float(request.args.get('confidence_min', 0.6))
            if not 0.0 <= confidence_min <= 1.0:
                return jsonify({
                    'status': 'error',
                    'message': 'confidence_min must be between 0.0 and 1.0'
                }), 400
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid confidence_min value'
            }), 400

        try:
            limit = min(int(request.args.get('limit', 50)), 200)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid limit value'
            }), 400

        # 2. Database connection
        from src.infrastructure.database.connection_pool import get_connection
        from psycopg2.extras import RealDictCursor

        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 3. Build query
        # Time window: 7 days for hourly patterns
        query = """
            SELECT
                id,
                symbol,
                pattern_type,
                confidence,
                pattern_data,
                detection_timestamp,
                expiration_timestamp,
                levels,
                metadata
            FROM hourly_patterns
            WHERE confidence >= %s
              AND detection_timestamp > NOW() - INTERVAL '1 hour'
        """
        params = [confidence_min]

        # Optional symbol filter
        if symbols:
            query += " AND symbol IN %s"
            params.append(tuple(symbols))

        # Order and limit
        query += " ORDER BY confidence DESC, detection_timestamp DESC LIMIT %s"
        params.append(limit)

        # 4. Execute query
        cursor.execute(query, params)
        patterns = cursor.fetchall()

        # 5. Calculate response time
        response_time = (time.time() - start_time) * 1000

        # 6. Log slow queries
        if response_time > 50:
            logger.warning(
                f"Slow hourly patterns query: {response_time:.2f}ms for {len(patterns)} patterns"
            )

        # 7. Format response
        return jsonify({
            'patterns': [dict(p) for p in patterns],
            'metadata': {
                'count': len(patterns),
                'tier': 'hourly',
                'confidence_min': confidence_min,
                'response_time_ms': round(response_time, 2)
            }
        }), 200

    except DatabaseError as e:
        logger.error(f"Database error in get_hourly_patterns: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Database unavailable'
        }), 503

    except Exception as e:
        logger.error(f"Unexpected error in get_hourly_patterns: {e}")
        logger.exception("Full traceback:")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

    finally:
        # CRITICAL: Always close connection
        if conn:
            conn.close()


# CHANGE RATIONALE:
# - BEFORE: No API endpoint for hourly_patterns table
# - AFTER: Dedicated endpoint matching existing daily/intraday pattern
# - Enables frontend to query hourly patterns with consistent interface

# PRESERVED BEHAVIOR:
# - Authentication required (@login_required)
# - Error handling pattern (try-except-finally)
# - Connection cleanup (finally block)
# - Response format matches daily/intraday endpoints
# - Performance logging for slow queries (>50ms)

# GOTCHA:
# - hourly_patterns table currently EMPTY (0 rows)
# - Must verify TickStockPL populates this table
# - Uses expiration_timestamp (not expiration_date like daily)
# - Primary key is simple id (not composite like daily)
# - 7-day time window (balance between data volume and relevance)


# ═══════════════════════════════════════════════════════════════
# Pattern 2: Expanding Frontend State Management
# ═══════════════════════════════════════════════════════════════

# BEFORE: 4-tier state object
# File: web/static/js/services/pattern_flow.js (lines 28-39)

this.state = {
    patterns: {
        daily: [],
        intraday: [],
        combo: [],
        indicators: []
    },
    lastRefresh: null,
    countdown: 15,
    isRefreshing: false,
    connectionStatus: 'disconnected'
};


# AFTER: 6-tier state object
# File: web/static/js/services/pattern_flow.js (lines 28-43)

this.state = {
    patterns: {
        daily: [],
        hourly: [],          // NEW
        intraday: [],
        weekly: [],          // NEW
        monthly: [],         // NEW
        daily_intraday: []   // NEW (replaces 'combo')
    },
    lastRefresh: null,
    countdown: 15,
    isRefreshing: false,
    connectionStatus: 'disconnected'
};


# CHANGE RATIONALE:
# - BEFORE: State only tracks 4 tiers
# - AFTER: State tracks all 6 pattern tables + 1 indicators column (7 total)
# - Enables renderPatterns() to work with all tiers

# PRESERVED BEHAVIOR:
# - lastRefresh tracking (for countdown display)
# - countdown state (15-second timer)
# - isRefreshing flag (prevent duplicate refreshes)
# - connectionStatus (WebSocket connection state)

# GOTCHA:
# - All 6 tier keys must be initialized as empty arrays []
# - renderPatterns() expects these exact key names
# - handleNewPattern() uses tier key to update state
# - WebSocket handlers reference these tier keys


# ═══════════════════════════════════════════════════════════════
# Pattern 3: Fixing Frontend API Parameter Bug
# ═══════════════════════════════════════════════════════════════

# BEFORE: Incorrect parameter mapping
# File: web/static/js/services/pattern_flow.js (line 647)

async loadPatternsByTier(tier) {
    try {
        // ❌ BUG: API doesn't accept 'tier' parameter
        const response = await fetch(`/api/patterns/scan?tier=${tier}&limit=30&sort=timestamp_desc`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        this.state.patterns[tier] = data.patterns || [];
        this.renderPatterns(tier);

    } catch (error) {
        console.warn(`[PatternFlowService] Using mock data for ${tier}:`, error);
        this.state.patterns[tier] = this.generateMockPatterns(tier, 10);
        this.renderPatterns(tier);
    }
}


# AFTER: Correct parameter mapping with timeframe
# File: web/static/js/services/pattern_flow.js (lines 647-680)

async loadPatternsByTier(tier) {
    try {
        // ✅ FIX: Map tier IDs to API timeframe values
        const timeframeMap = {
            daily: 'Daily',
            hourly: 'Hourly',
            intraday: 'Intraday',
            weekly: 'Weekly',
            monthly: 'Monthly',
            daily_intraday: 'DailyIntraday'
        };

        const timeframe = timeframeMap[tier];

        if (!timeframe) {
            console.error(`[PatternFlowService] Unknown tier: ${tier}`);
            this.state.patterns[tier] = [];
            this.renderPatterns(tier);
            return;
        }

        // ✅ FIX: Use correct parameter names
        const response = await fetch(
            `/api/patterns/scan?timeframe=${timeframe}&limit=30&sort_by=detected_at&sort_order=desc`
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        // Update state and render
        this.state.patterns[tier] = data.patterns || [];
        this.renderPatterns(tier);

    } catch (error) {
        console.warn(`[PatternFlowService] API error for ${tier}, using mock data:`, error);

        // Fallback to mock data
        this.state.patterns[tier] = this.generateMockPatterns(tier, 10);
        this.renderPatterns(tier);
    }
}


# CHANGE RATIONALE:
# - BEFORE: Sent 'tier' parameter (not recognized by API)
# - AFTER: Sends 'timeframe' parameter with proper capitalization
# - BEFORE: Used invalid 'sort=timestamp_desc' parameter
# - AFTER: Uses correct 'sort_by=detected_at' and 'sort_order=desc'
# - Fixes existing bug that prevented real API data from loading

# PRESERVED BEHAVIOR:
# - Fallback to mock data on API failure
# - Error logging for debugging
# - State update and re-render after data load
# - Limit of 30 patterns per tier

# GOTCHA:
# - Timeframe values are PascalCase: 'Daily', 'Hourly', 'DailyIntraday'
# - Tier IDs are lowercase: 'daily', 'hourly', 'daily_intraday'
# - Must map between frontend tier IDs and backend timeframe values
# - Empty tables will return {patterns: []} not error


# ═══════════════════════════════════════════════════════════════
# Pattern 4: Responsive 6-Column CSS Layout
# ═══════════════════════════════════════════════════════════════

# BEFORE: Fixed 4-column layout
# File: web/static/css/components/pattern-flow.css (lines 195-207)

.pattern-flow-columns {
    display: flex !important;
    flex-wrap: nowrap !important;
    gap: 15px;
    margin: 0;
    padding: 0;
}

.pattern-column-wrapper {
    flex: 1 1 25%;  /* 100% / 4 = 25% per column */
    min-width: 0;
}


# AFTER: Responsive 6-column layout with breakpoints
# File: web/static/css/components/pattern-flow.css (lines 195-245)

.pattern-flow-columns {
    display: flex !important;
    flex-wrap: wrap !important;  /* ✅ CHANGED: Allow wrapping */
    gap: 15px;
    margin: 0;
    padding: 0;
}

/* Desktop (1400px+): 7 columns */
@media (min-width: 1600px) {
    .pattern-column-wrapper {
        flex: 1 1 calc(14.28% - 13px);  /* 100% / 7, adjusted for gap */
        min-width: 0;
    }
}

/* Laptop (992px - 1399px): 4 columns (same as current) */
@media (min-width: 992px) and (max-width: 1399px) {
    .pattern-column-wrapper {
        flex: 1 1 calc(25% - 11.25px);  /* 100% / 4, adjusted for gap */
        min-width: 0;
    }
}

/* Tablet (768px - 991px): 3 columns */
@media (min-width: 768px) and (max-width: 991px) {
    .pattern-column-wrapper {
        flex: 1 1 calc(33.33% - 10px);  /* 100% / 3, adjusted for gap */
        min-width: 0;
    }
}

/* Mobile (<768px): 2 columns */
@media (min-width: 480px) and (max-width: 767px) {
    .pattern-column-wrapper {
        flex: 1 1 calc(50% - 7.5px);  /* 100% / 2, adjusted for gap */
        min-width: 0;
    }
}

/* Small mobile (<480px): 1 column */
@media (max-width: 479px) {
    .pattern-column-wrapper {
        flex: 1 1 100%;
        min-width: 0;
    }
}


# CHANGE RATIONALE:
# - BEFORE: Fixed 4 columns (doesn't scale to 6)
# - AFTER: Responsive layout adapts to screen size
# - Desktop users see all 7 columns
# - Mobile users see stacked columns for readability
# - Maintains usability across all device sizes

# PRESERVED BEHAVIOR:
# - 15px gap between columns
# - Flexbox layout (maintains alignment)
# - min-width: 0 (prevents flex item overflow)

# GOTCHA:
# - Gap calculation: calc(X% - gap_adjustment)
# - Gap adjustment = (gap * (columns - 1)) / columns
# - Example for 6 cols: (15px * 5) / 6 = 12.5px
# - Must test at each breakpoint in browser
# - Dark theme overrides still need to work


# ═══════════════════════════════════════════════════════════════
# Pattern 5: Integration Test Updates for 6 Tables
# ═══════════════════════════════════════════════════════════════

# BEFORE: Tests 4-column initialization
# File: tests/integration/test_pattern_flow_complete.py

def test_pattern_flow_service_initialization():
    """Test Pattern Flow service initializes correctly."""
    service = PatternFlowService()
    assert len(service.columns) == 4
    assert 'daily' in service.state.patterns
    assert 'intraday' in service.state.patterns


# AFTER: Tests 6-column initialization with performance validation
# File: tests/integration/test_pattern_flow_complete.py

def test_pattern_flow_service_initialization():
    """Test Pattern Flow service initializes with all 6 pattern tables + 1 indicators column (7 total)."""
    service = PatternFlowService()

    # Verify 7 columns configured
    assert len(service.columns) == 6, "Expected 7 columns (daily, hourly, intraday, weekly, monthly, daily_intraday)"

    # Verify all tier state initialized
    expected_tiers = ['daily', 'hourly', 'intraday', 'weekly', 'monthly', 'daily_intraday']
    for tier in expected_tiers:
        assert tier in service.state.patterns, f"Missing tier '{tier}' in state.patterns"
        assert isinstance(service.state.patterns[tier], list), f"Tier '{tier}' should be list"


def test_all_pattern_table_endpoints_exist():
    """Test all 6 pattern tables + 1 indicators column (7 total) have dedicated API endpoints."""
    import requests

    endpoints = [
        '/api/patterns/daily',
        '/api/patterns/hourly',
        '/api/patterns/intraday',
        '/api/patterns/weekly',
        '/api/patterns/monthly',
        '/api/patterns/daily_intraday'
    ]

    for endpoint in endpoints:
        response = requests.get(f'http://localhost:5000{endpoint}')
        # Accept 200 (success) or 401 (auth required, but endpoint exists)
        assert response.status_code in [200, 401], f"Endpoint {endpoint} returned {response.status_code}"


def test_multi_table_refresh_performance():
    """Test 6-table parallel refresh meets <500ms performance target."""
    import time
    import asyncio

    async def fetch_all_tiers():
        """Simulate parallel API calls for all 6 tiers."""
        start_time = time.time()

        # Parallel requests
        tiers = ['daily', 'hourly', 'intraday', 'weekly', 'monthly', 'daily_intraday']
        responses = await asyncio.gather(*[
            fetch_tier_data(tier) for tier in tiers
        ])

        duration_ms = (time.time() - start_time) * 1000
        return duration_ms, responses

    # Run test
    duration, responses = asyncio.run(fetch_all_tiers())

    # Assertions
    assert duration < 500, f"Refresh took {duration:.2f}ms, target <500ms"
    assert len(responses) == 6, "Expected 6 tier responses"


def test_empty_table_graceful_handling():
    """Test frontend handles empty pattern tables gracefully."""
    import requests

    # hourly, weekly, monthly tables likely empty (0 rows)
    empty_tables = ['hourly', 'weekly', 'monthly']

    for table in empty_tables:
        response = requests.get(f'http://localhost:5000/api/patterns/{table}')
        assert response.status_code == 200, f"Endpoint /{table} should return 200 even if empty"

        data = response.json()
        assert 'patterns' in data, f"Response should have 'patterns' key"
        assert isinstance(data['patterns'], list), f"'patterns' should be list (even if empty)"
        assert 'metadata' in data, f"Response should have 'metadata' key"
        assert data['metadata']['count'] == len(data['patterns']), "Count should match patterns length"


# CHANGE RATIONALE:
# - BEFORE: Only tested 4-column initialization
# - AFTER: Tests all 6 tables, endpoints, performance, empty handling
# - Comprehensive validation prevents regressions

# PRESERVED BEHAVIOR:
# - ~30 second total test runtime target
# - Mock data fallback if services unavailable
# - Clear assertion messages for debugging

# GOTCHA:
# - Empty tables (hourly/weekly/monthly) should NOT fail tests
# - Performance test depends on local system (adjust threshold if needed)
# - Auth may be required for endpoints (test with login fixture)
```

### Integration Points (What Changes)

```yaml
# TickStock-Specific Integration Points Affected by Change

DATABASE:
  schema_changes: No

  query_changes:
    - location: "src/api/rest/tier_patterns.py"
      before: "3 endpoints querying 3 tables (daily_patterns, intraday_patterns, pattern_detections)"
      after: "7 endpoints querying 6 tables (add hourly, weekly, monthly, daily_intraday)"
      performance_impact: "6 parallel queries vs 4 (50% increase), still <500ms total"

    - query_example_hourly:
        sql: |
          SELECT id, symbol, pattern_type, confidence, pattern_data,
                 detection_timestamp, expiration_timestamp, levels, metadata
          FROM hourly_patterns
          WHERE confidence >= 0.6
            AND detection_timestamp > NOW() - INTERVAL '1 hour'
          ORDER BY confidence DESC, detection_timestamp DESC
          LIMIT 50
        performance: "<50ms target (table currently empty, instant response)"

REDIS_CHANNELS:
  message_format_changes: Yes

  channel_updates:
    - channel: "tickstock:patterns:streaming"
      current_format: "{symbol, pattern_type, confidence, source_tier: 'daily'|'intraday'|'combo', ...}"
      new_format: "{symbol, pattern_type, confidence, source_tier: 'daily'|'hourly'|'intraday'|'weekly'|'monthly'|'daily_intraday', ...}"
      backward_compatible: Yes
      migration: |
        - Old source_tier values (daily, intraday, combo) still work
        - New values added for 4 missing tables
        - Frontend handles unknown tier values gracefully (ignores)
        - No breaking changes to existing Redis consumers

WEBSOCKET:
  event_changes: Yes

  event_updates:
    - event_type: "pattern_detected"
      current_format: "{tier: 'daily'|'intraday'|'combo'|'indicators', pattern: {...}}"
      new_format: "{tier: 'daily'|'hourly'|'intraday'|'weekly'|'monthly'|'daily_intraday', pattern: {...}}"
      frontend_impact: "handleNewPattern() must support 6 tier values instead of 4"
      backward_compatible: Yes
      note: "Existing 4 tier values still work, 3 new values added"

TICKSTOCKPL_API:
  endpoint_changes: No

  coordination_required: Yes

  verification_needed:
    - question: "Does TickStockPL populate hourly_patterns table?"
      check: "SELECT COUNT(*) FROM hourly_patterns"
      current: "0 rows"
      action: "If YES → implement endpoint, If NO → defer until TickStockPL ready"

    - question: "Does TickStockPL populate weekly_patterns table?"
      check: "SELECT COUNT(*) FROM weekly_patterns"
      current: "0 rows"
      action: "If YES → implement endpoint, If NO → defer until TickStockPL ready"

    - question: "Does TickStockPL populate monthly_patterns table?"
      check: "SELECT COUNT(*) FROM monthly_patterns"
      current: "0 rows"
      action: "If YES → implement endpoint, If NO → defer until TickStockPL ready"

    - question: "Does TickStockPL populate daily_intraday_patterns table?"
      check: "SELECT COUNT(*) FROM daily_intraday_patterns"
      current: "0 rows"
      action: "If YES → implement endpoint, If NO → defer until TickStockPL ready"

  recommendation: |
    CRITICAL: Coordinate with TickStockPL team BEFORE implementing.
    Options:
    1. If TickStockPL populates all tables → Full 6-table implementation
    2. If TickStockPL populates some tables → Phased implementation (implement only populated tables)
    3. If TickStockPL populates none → Defer feature until TickStockPL ready

    Empty tables in UI = poor user experience. Only implement for tables TickStockPL actively populates.
```

---

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# TickStock Standard: Ruff for linting and formatting
# Run after EACH file modification

# Modified files only
ruff check src/api/rest/tier_patterns.py --fix
ruff check src/api/rest/pattern_consumer.py --fix
ruff check src/infrastructure/cache/redis_pattern_cache.py --fix
ruff format src/api/rest/tier_patterns.py
ruff format src/api/rest/pattern_consumer.py
ruff format src/infrastructure/cache/redis_pattern_cache.py

# JavaScript linting (if available)
# eslint web/static/js/services/pattern_flow.js --fix

# CSS validation
# stylelint web/static/css/components/pattern-flow.css --fix

# Full project validation
ruff check src/ --fix
ruff format src/

# Expected: Zero errors
```

### Level 2: Unit Tests (Component Validation)

```bash
# TickStock Standard: pytest for all testing

# Test new API endpoints individually
python -m pytest tests/unit/test_tier_patterns_api.py -v -k "hourly"
python -m pytest tests/unit/test_tier_patterns_api.py -v -k "weekly"
python -m pytest tests/unit/test_tier_patterns_api.py -v -k "monthly"

# Test pattern_consumer timeframe validation
python -m pytest tests/unit/test_pattern_consumer.py -v -k "timeframe"

# Full unit test suite
python -m pytest tests/unit/ -v

# Expected: All tests pass (including new endpoint tests)
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
# CRITICAL: Must run before ANY commit

python run_tests.py

# Expected Output:
# - All existing tests still pass (regression-free)
# - New multi-table tests pass
# - ~30 second runtime (may increase slightly with more tests)
# - No new errors introduced

# Specific integration tests for this change
python -m pytest tests/integration/test_pattern_flow_complete.py -v
python -m pytest tests/integration/test_pattern_flow_performance.py -v

# Expected:
# - 6-table initialization working
# - All API endpoints responding
# - Performance <500ms for 6 parallel calls
# - Empty table handling graceful
```

### Level 4: TickStock-Specific Validation

```bash
# Performance Validation
# CRITICAL: Verify performance NOT degraded

# 1. Database Query Performance
# Test each new endpoint individually
psql -U app_readwrite -d tickstock -c "
EXPLAIN ANALYZE
SELECT id, symbol, pattern_type, confidence, pattern_data,
       detection_timestamp, expiration_timestamp, levels, metadata
FROM hourly_patterns
WHERE confidence >= 0.6
  AND detection_timestamp > NOW() - INTERVAL '1 hour'
ORDER BY confidence DESC, detection_timestamp DESC
LIMIT 50;
"

# Target: <50ms execution time
# NOTE: Empty tables return instantly, verify performance when populated


# 2. API Response Time Validation
# Test single endpoint
time curl -X GET 'http://localhost:5000/api/patterns/hourly?limit=30' \
  -H 'Cookie: session=...'

# Target: <50ms


# 3. Multi-Table Refresh Performance
# Test parallel API calls (simulate Pattern Flow refresh)
time (
  curl -X GET 'http://localhost:5000/api/patterns/scan?timeframe=Daily&limit=30' &
  curl -X GET 'http://localhost:5000/api/patterns/scan?timeframe=Hourly&limit=30' &
  curl -X GET 'http://localhost:5000/api/patterns/scan?timeframe=Intraday&limit=30' &
  curl -X GET 'http://localhost:5000/api/patterns/scan?timeframe=Weekly&limit=30' &
  curl -X GET 'http://localhost:5000/api/patterns/scan?timeframe=Monthly&limit=30' &
  curl -X GET 'http://localhost:5000/api/patterns/scan?timeframe=DailyIntraday&limit=30' &
  wait
)

# Target: <500ms total (6 parallel calls)


# 4. Redis Memory Usage (before/after change)
redis-cli INFO memory | grep used_memory_human

# Before: ~100MB (3 tiers cached)
# After: ~200MB (6 tiers cached) - acceptable if <500MB


# 5. Frontend Performance (Browser DevTools)
# Open Pattern Flow page
# Network tab → Filter by XHR
# Verify:
# - 6 API calls to /api/patterns/scan
# - Total time <500ms
# - No failed requests


# Backward Compatibility Validation
# CRITICAL: Verify no breaking changes for consumers

# Test old API contracts still work
curl -X GET 'http://localhost:5000/api/patterns/daily?limit=10'
# Expected: 200 OK, same response format as before

curl -X GET 'http://localhost:5000/api/patterns/intraday?limit=10'
# Expected: 200 OK, same response format as before

curl -X GET 'http://localhost:5000/api/patterns/scan?timeframe=Daily&limit=10'
# Expected: 200 OK, patterns returned

# Test new functionality
curl -X GET 'http://localhost:5000/api/patterns/hourly?limit=10'
# Expected: 200 OK, {patterns: [], metadata: {tier: "hourly", count: 0}}

curl -X GET 'http://localhost:5000/api/patterns/scan?timeframe=Hourly&limit=10'
# Expected: 200 OK, patterns returned (likely empty if table unpopulated)


# Architecture Compliance Validation
# Verify Consumer/Producer boundaries preserved

# Pattern Flow (Consumer) should:
# - Query pattern data via API (✓)
# - NOT perform pattern detection (✓)
# - Display results from TickStockPL (✓)

# No pattern detection logic added to AppV2 (Consumer role preserved)
```

### Level 5: Regression Testing (MANDATORY for Changes)

```bash
# Regression Test Suite
# CRITICAL: Ensure existing functionality unchanged

# Test existing 4-column layout still works (before expanding to 6)
# Manual test:
# 1. Open Pattern Flow page
# 2. Verify Daily and Intraday columns show data
# 3. Verify 15-second refresh countdown working
# 4. Verify WebSocket connection indicator shows "Connected"

# Automated regression tests
python -m pytest tests/integration/test_pattern_flow_regression.py -v

# Test scenarios that should NOT have changed:
# - [ ] Daily patterns still load correctly
# - [ ] Intraday patterns still load correctly
# - [ ] 15-second refresh interval maintained
# - [ ] WebSocket events still trigger real-time updates
# - [ ] Pattern row click shows modal with details
# - [ ] Connection status indicator works
# - [ ] Theme switching (light/dark) still works

# Before/After Comparison
# Document baseline metrics BEFORE change:
# - Daily patterns API response time: ___ms
# - Intraday patterns API response time: ___ms
# - Total refresh time (4 tables): ___ms
# - Browser memory usage: ___MB
# - Redis memory usage: ___MB

# Measure same metrics AFTER change:
# - Daily patterns API response time: ___ms (should be same)
# - Intraday patterns API response time: ___ms (should be same)
# - Hourly patterns API response time: ___ms (new)
# - Weekly patterns API response time: ___ms (new)
# - Monthly patterns API response time: ___ms (new)
# - Daily-intraday patterns API response time: ___ms (new)
# - Total refresh time (6 tables): ___ms (target <500ms)
# - Browser memory usage: ___MB (acceptable if <10% increase)
# - Redis memory usage: ___MB (acceptable if <2x increase)

# Acceptance criteria:
# - All pre-existing functionality works exactly as before
# - No errors in browser console
# - No errors in backend logs
# - Performance metrics within acceptable range
# - Empty tables display gracefully (no errors)
```

---

## Final Validation Checklist

### Technical Validation

- [ ] All 5 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] Regression tests pass: Existing 4-column functionality preserved
- [ ] No linting errors: `ruff check src/`
- [ ] No formatting issues: `ruff format src/ --check`
- [ ] Unit tests pass (including new endpoint tests)
- [ ] Browser console shows no JavaScript errors

### Change Validation

- [ ] All 6 pattern tables + 1 indicators column (7 total) have dedicated API endpoints
- [ ] Pattern Flow UI displays 7 columns (responsive layout)
- [ ] 15-second auto-refresh working for all 6 tables
- [ ] Empty tables handled gracefully ("No patterns detected" message)
- [ ] Performance targets met: Total refresh <500ms
- [ ] Frontend parameter bug fixed (tier → timeframe mapping)
- [ ] Backward compatibility preserved (existing endpoints unchanged)

### Impact Validation

- [ ] No breaking changes introduced
- [ ] All identified dependencies tested (routes, templates, JavaScript)
- [ ] Database queries optimized (<50ms per query)
- [ ] Redis memory usage acceptable (<500MB total)
- [ ] Browser memory usage acceptable (<10% increase)
- [ ] WebSocket subscriptions working (if applicable)

### TickStock Architecture Validation

- [ ] Component role preserved (Consumer - no pattern detection logic added)
- [ ] Redis message format expanded (source_tier supports 6 values)
- [ ] Database access mode followed (read-only queries)
- [ ] Performance targets achieved (<50ms API, <100ms WebSocket, <500ms refresh)
- [ ] No architectural violations detected

### Code Quality Validation

- [ ] Follows existing codebase patterns (tier_patterns.py template)
- [ ] File structure limits followed (tier_patterns.py <500 lines after additions)
- [ ] Function size limits followed (<50 lines per endpoint function)
- [ ] Naming conventions preserved (snake_case Python, camelCase JavaScript)
- [ ] Error handling comprehensive (try-except-finally)
- [ ] Connection cleanup in finally blocks (database connections)
- [ ] No "Generated by Claude" comments

### Coordination & Deployment

- [ ] TickStockPL team contacted: Confirmed which tables are populated
- [ ] Migration plan documented (if tables currently empty)
- [ ] Configuration changes documented (no new env vars needed)
- [ ] Sprint notes updated with implementation details
- [ ] Empty table placeholders added to UI (graceful degradation)
- [ ] Manual testing completed across all screen sizes (desktop, tablet, mobile)

---

## Anti-Patterns to Avoid (Change-Specific)

### Modification Anti-Patterns

- ❌ **Don't implement endpoints for unpopulated tables without user feedback**
  - Empty columns create poor user experience
  - Verify TickStockPL populates tables BEFORE implementing
  - Violation: "Build it and they will come" (empty UI columns)

- ❌ **Don't skip responsive design for 7 columns**
  - 7 columns don't fit on mobile/tablet screens
  - Must implement breakpoints for different screen sizes
  - Violation: "Works on my 4K monitor" (ignoring mobile users)

- ❌ **Don't ignore the existing parameter bug (tier vs timeframe)**
  - Bug prevents real API data from loading currently
  - Must fix mapping during this change
  - Violation: "That's a separate bug, not my problem"

- ❌ **Don't forget to initialize all 6 state keys**
  - Missing keys cause JavaScript errors (this.state.patterns[tier] undefined)
  - Initialize all tier keys as empty arrays []
  - Violation: "Forgot to add hourly: [] to state" (runtime error)

- ❌ **Don't copy-paste endpoints without adjusting table-specific details**
  - expiration_date vs expiration_timestamp column names differ
  - Primary key structure differs (simple vs composite)
  - Time windows differ (24h vs 7d vs 30d)
  - Violation: "Copy-paste from daily endpoint" (wrong column names)

### TickStock-Specific Change Anti-Patterns

- ❌ **Don't add pattern detection logic to AppV2**
  - AppV2 is CONSUMER (display only)
  - TickStockPL is PRODUCER (pattern detection)
  - Violation: Adding pattern scoring/filtering logic to AppV2

- ❌ **Don't modify database schema**
  - Tables already exist, no schema changes needed
  - Read-only queries only
  - Violation: "ALTER TABLE to add index" (unnecessary)

- ❌ **Don't break WebSocket message format**
  - Frontend JavaScript expects specific tier field values
  - Backward compatibility required (old values still work)
  - Violation: Renaming 'daily' to 'daily_patterns' (breaks frontend)

- ❌ **Don't ignore empty table performance**
  - Empty tables return instantly (0ms)
  - Must still optimize queries for future data
  - Violation: "Table is empty, performance doesn't matter"

- ❌ **Don't skip coordination with TickStockPL**
  - They control which tables are populated
  - Implementing endpoints for empty tables wastes effort
  - Violation: "I'll build it, TickStockPL will populate later"

---

**END OF CHANGE PRP**

---

## Next Steps

1. **User Review**: Review this PRP and confirm:
   - Current sprint number is correct (Sprint 46)
   - TickStockPL team confirmation on table population status
   - Approval to proceed with implementation

2. **Implementation**: Use `/prp-change-execute` command with this PRP path:
   ```
   /prp-change-execute "docs/planning/sprints/sprint46/pattern-flow-multi-table-display.md"
   ```

3. **Testing**: Run comprehensive validation after implementation:
   ```bash
   python run_tests.py
   ```

4. **Deployment**: Follow phased rollout (backend → frontend → Redis cache)

---

**PRP Confidence Score**: 8/10

**Rationale**:
- ✅ Complete dependency analysis (6 files, all dependencies mapped)
- ✅ BEFORE/AFTER code examples for all changes
- ✅ Performance impact quantified (<500ms target)
- ✅ Regression testing requirements specified
- ✅ Backward compatibility guaranteed (no breaking changes)
- ⚠️ Dependency on TickStockPL table population (external coordination needed)
- ⚠️ Empty tables may result in poor UX (mitigation: placeholders added)

**Recommendation**: Proceed with implementation AFTER confirming TickStockPL table population status.
