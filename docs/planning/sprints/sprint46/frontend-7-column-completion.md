name: "Frontend 7-Column Pattern Flow Completion"
description: |
  Complete the Pattern Flow frontend to display all 7 timeframe columns
  (Intraday, Hourly, Daily, Weekly, Monthly, Daily-Intraday, Indicators)
  matching the backend API capabilities implemented in Sprint 46.

---

## Goal

**Change Type**: enhancement

**Current Behavior**:
- Pattern Flow displays **4 columns**: Daily, Intraday, Combo, Indicators
- Missing **3 timeframes**: Hourly, Weekly, Monthly
- Combo column shows old naming (should be Daily-Intraday)
- API calls use incorrect `tier` parameter (should use `timeframe`)

**Desired Behavior**:
- Pattern Flow displays **7 columns**: Intraday, Hourly, Daily, Weekly, Monthly, Daily-Intraday, Indicators
- All columns load data from corresponding backend API endpoints
- Responsive layout adapts: 7 columns (desktop) → 5 (large laptop) → 4 (laptop) → 3 (tablet) → 2 (mobile) → 1 (small mobile)
- 15-second auto-refresh works for all 7 columns
- API calls use correct `timeframe` parameter

**Success Definition**:
- ✅ 7 columns display in Pattern Flow UI
- ✅ All columns load data (or show "No patterns detected" if empty)
- ✅ 15-second auto-refresh updates all 7 columns
- ✅ Responsive layout adapts to screen size
- ✅ No JavaScript console errors
- ✅ Integration tests pass: `python run_tests.py`
- ✅ Performance target met: <600ms for 7 parallel API calls

**Breaking Changes**: No

---

## User Persona

**Target User**: Day traders and swing traders using TickStock.ai

**Current Pain Point**:
- Cannot see hourly, weekly, or monthly pattern signals in Pattern Flow
- Combo column has confusing naming (should be "Daily-Intraday")
- Pattern data fails to load due to incorrect API parameter (tier vs timeframe)

**Expected Improvement**:
- Complete multi-timeframe visibility in single view
- Clear column naming matches trading timeframes
- Reliable data loading from backend API

---

## Why This Change

- **Complete Feature**: Backend API supports 7 timeframes but frontend only shows 4 (50% incomplete)
- **User Value**: Traders need all timeframes for comprehensive pattern analysis
- **Fix Critical Bug**: Current API calls use wrong parameter (`tier` instead of `timeframe`), causing data load failures
- **Risk of NOT Changing**:
  - Backend implementation wasted (3 new endpoints unused)
  - User frustration with incomplete feature
  - Technical debt grows (frontend/backend mismatch)

---

## What Changes

### Success Criteria

- [x] Backend ready: All 5 new API endpoints functional (/hourly, /weekly, /monthly, /daily_intraday, /indicators/latest)
- [ ] Frontend state updated: 7 tier properties in pattern state
- [ ] Frontend columns updated: 7 column definitions with proper icons/colors
- [ ] Frontend data loading updated: Load 7 tiers instead of 4
- [ ] Frontend API bug fixed: Use `timeframe` parameter with correct mapping
- [ ] CSS responsive layout added: 7-column breakpoints defined
- [ ] Integration tests updated: Test all 7 tiers
- [ ] Manual testing verified: All columns display and refresh correctly

---

## Current Implementation Analysis

### Files to Modify

```yaml
- file: web/static/js/services/pattern_flow.js
  current_responsibility: "Pattern Flow service managing 4-column real-time pattern display"
  lines_to_modify:
    - "29-34: State management (add hourly, weekly, monthly, rename combo)"
    - "134-139: Column definitions (expand 4 → 7 columns)"
    - "631: Data loading (load 7 tiers instead of 4)"
    - "647: API call parameter (CRITICAL BUG: tier → timeframe)"
  current_pattern: "4 hardcoded tiers with polling refresh"
  reason_for_change: "Complete 7-tier support, fix API parameter bug"

- file: web/static/css/components/pattern-flow.css
  current_responsibility: "Responsive 4-column layout with light/dark theme support"
  lines_to_modify:
    - "78-82: Column wrapper sizing (25% → 14.28% for 7 columns)"
    - "85-118: Responsive breakpoints (add 7/5/4/3/2/1 column breakpoints)"
  current_pattern: "Fixed 25% width per column, 3 breakpoints"
  reason_for_change: "Support 7-column layout with graceful responsive degradation"

- file: tests/integration/test_pattern_flow_complete.py
  current_responsibility: "Integration tests for pattern flow system"
  lines_to_modify:
    - "95-133: Multi-tier test (test 7 tiers instead of 3)"
    - "Add: New endpoint tests for hourly, weekly, monthly, daily_intraday, indicators"
  current_pattern: "Tests 3 tiers (daily, intraday, combo)"
  reason_for_change: "Validate all 7 tiers work correctly"
```

### Current Code Patterns (What Exists Now)

```javascript
// FILE: web/static/js/services/pattern_flow.js

// CURRENT STATE MANAGEMENT (lines 28-39)
this.state = {
    patterns: {
        daily: [],           // ✅ Exists
        intraday: [],        // ✅ Exists
        combo: [],           // ❌ Should be daily_intraday
        indicators: []       // ✅ Exists
        // ❌ MISSING: hourly, weekly, monthly
    },
    lastRefresh: null,
    countdown: 15,
    isRefreshing: false,
    connectionStatus: 'disconnected'
};

// CURRENT COLUMN DEFINITIONS (lines 134-139)
const columns = [
    { id: 'daily', title: 'Daily', icon: '📊', color: '#007bff' },
    { id: 'intraday', title: 'Intraday', icon: '⚡', color: '#28a745' },
    { id: 'combo', title: 'Combo', icon: '🔗', color: '#17a2b8' },  // ❌ Old naming
    { id: 'indicators', title: 'Indicators', icon: '📈', color: '#fd7e14' }
    // ❌ MISSING: hourly, weekly, monthly columns
];

// CURRENT DATA LOADING (line 631)
const promises = ['daily', 'intraday', 'combo', 'indicators'].map(tier =>
    this.loadPatternsByTier(tier)
);
// ❌ Only loads 4 tiers, missing 3 new tiers

// CURRENT API CALL (line 647) - CRITICAL BUG
const response = await fetch(`/api/patterns/scan?tier=${tier}&limit=30&sort=timestamp_desc`);
// ❌ BUG: Backend expects `timeframe` parameter, not `tier`
// ❌ BUG: Backend expects PascalCase values (Daily, Hourly) not lowercase (daily, hourly)
```

```css
/* FILE: web/static/css/components/pattern-flow.css */

/* CURRENT COLUMN LAYOUT (lines 78-82) */
.pattern-column-wrapper {
    flex: 1 1 25%;       /* ❌ 4 columns = 25% each */
    min-width: 250px;
    max-width: calc(25% - 12px);
}

/* CURRENT RESPONSIVE (lines 85-118) */
/* Only 3 breakpoints: 1200px+ (4 cols), 768-1199px (2x2), <768px (stack) */
/* ❌ MISSING: 7-column breakpoints for desktop, 5 for large laptop */
```

### Dependency Analysis

```yaml
upstream_dependencies:
  # Code that CALLS PatternFlowService
  - component: "web/templates/dashboard/index.html"
    dependency: "Includes pattern-flow.css stylesheet (line 11)"
    impact: "No changes needed - CSS file path unchanged"

  - component: "web/templates/dashboard/index.html"
    dependency: "May instantiate PatternFlowService via JavaScript"
    impact: "No breaking changes - service interface unchanged"

downstream_dependencies:
  # Code that is CALLED BY PatternFlowService
  - component: "src/api/rest/pattern_consumer.py"
    dependency: "/api/patterns/scan endpoint validates timeframes (lines 75-78)"
    impact: "✅ Already supports all 7 timeframes: Daily, Hourly, Intraday, Weekly, Monthly, DailyIntraday"

  - component: "src/api/rest/tier_patterns.py"
    dependency: "5 new endpoints ready (/hourly, /weekly, /monthly, /daily_intraday, /indicators/latest)"
    impact: "✅ All endpoints functional and tested"

database_dependencies:
  - table: "hourly_patterns, weekly_patterns, monthly_patterns, daily_intraday_patterns, intraday_indicators"
    columns: "id, symbol, pattern_type, confidence, detection_timestamp, etc."
    impact: "✅ Tables exist, backend queries working"
    migration_required: No

redis_dependencies:
  - channel: "tickstock.events.patterns"
    current_format: "{event_type, source, flow_id, data: {tier, pattern, symbol, confidence}}"
    impact: "✅ No changes needed - WebSocket events unchanged"

websocket_dependencies:
  - event_type: "pattern_detected"
    current_format: "{tier: string, pattern: object}"
    impact: "✅ No changes needed - existing event handlers support all tiers"

external_api_dependencies:
  - api: "None (TickStockAppV2 internal only)"
    impact: "No external API changes"
```

### Test Coverage Analysis

```yaml
unit_tests:
  - test_file: "None (JavaScript service has no unit tests yet)"
    coverage: "N/A"
    needs_update: No
    update_reason: "Integration tests sufficient for this change"

integration_tests:
  - test_file: "tests/integration/test_pattern_flow_complete.py"
    coverage: "Tests 3 tiers (daily, intraday, combo) - lines 95-133"
    needs_update: Yes
    update_reason: "Must test all 7 tiers (add hourly, weekly, monthly, daily_intraday, indicators)"

missing_coverage:
  - scenario: "7-column responsive layout behavior"
    reason: "No automated tests for CSS responsive breakpoints (manual testing required)"

  - scenario: "API parameter timeframe mapping"
    reason: "No tests for tier → timeframe conversion (should add verification)"
```

---

## Impact Analysis

### Potential Breakage Points

```yaml
high_risk:
  # Changes with potential to break functionality
  # NONE - All changes are additive or bug fixes

medium_risk:
  - component: "pattern_flow.js data loading"
    risk: "If tier → timeframe mapping incorrect, API calls may fail"
    mitigation: "Use exact timeframe values from backend validation (pattern_consumer.py:76)"

  - component: "CSS responsive layout"
    risk: "7 columns may overflow on small screens"
    mitigation: "Test responsive breakpoints thoroughly, ensure flex-wrap enabled"

low_risk:
  - component: "Test updates"
    risk: "Tests may fail if tier names don't match backend expectations"
    mitigation: "Use exact tier names from backend endpoints"
```

### Performance Impact

```yaml
expected_improvements:
  - metric: "User visibility"
    current: "4/7 timeframes visible (57%)"
    target: "7/7 timeframes visible (100%)"
    measurement: "Visual inspection of Pattern Flow page"

  - metric: "Data completeness"
    current: "Missing hourly, weekly, monthly patterns"
    target: "All pattern data accessible"
    measurement: "Check all columns populate with data (or empty state)"

potential_regressions:
  - metric: "Total refresh time"
    current: "~400ms for 4 API calls"
    risk: "Could increase to ~700ms with 7 API calls"
    threshold: "<600ms acceptable per requirements"
    measurement: "Browser DevTools Network tab timing"

  - metric: "Memory usage"
    current: "4 pattern arrays in state"
    risk: "7 pattern arrays may increase memory slightly"
    threshold: "Minimal - each array max 30 patterns"
    measurement: "Browser DevTools Memory profiler"
```

### Backward Compatibility

```yaml
backward_compatibility:
  breaking_changes: No

  compatibility_guarantee: |
    - All existing 4 columns (Daily, Intraday, Combo/Daily-Intraday, Indicators) continue to work
    - WebSocket events unchanged
    - API contracts unchanged (fixing bug to match documented contract)
    - Theme system (light/dark) works for all 7 columns
    - No database schema changes
    - No configuration changes required
```

---

## All Needed Context

### Context Completeness Check

_Before executing this PRP, validate: "If someone knew nothing about this codebase OR the current implementation, would they have everything needed to make this change successfully without breaking anything?"_

**✅ Yes** - All necessary context provided:
- Exact file paths and line numbers
- BEFORE and AFTER code examples
- Backend API contract verified
- Dependencies mapped
- No breaking changes confirmed

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: TickStockAppV2
  role: Consumer

  redis_channels:
    - channel: "tickstock.events.patterns"
      change_type: none
      current_behavior: "Receives pattern_detected events with tier field"
      new_behavior: "✅ Unchanged - already supports all tiers"

  database_access:
    mode: read-only
    tables_affected:
      - "hourly_patterns (✅ exists)"
      - "weekly_patterns (✅ exists)"
      - "monthly_patterns (✅ exists)"
      - "daily_intraday_patterns (✅ exists)"
      - "intraday_indicators (✅ exists)"
    queries_modified: "No direct database queries in pattern_flow.js (uses API endpoints)"
    schema_changes: No

  websocket_integration:
    affected: No
    broadcast_changes: "None - WebSocket events already support all tiers"
    message_format_changes: "None"

  tickstockpl_api:
    affected: No
    endpoint_changes: "None - TickStockPL integration unchanged"

  performance_targets:
    - metric: "Total refresh time (7 parallel API calls)"
      current: "~400ms (4 calls)"
      target: "<600ms (7 calls)"

    - metric: "WebSocket delivery"
      current: "~50ms"
      target: "<100ms (unchanged)"

    - metric: "Per-API response"
      current: "~50ms per endpoint"
      target: "<50ms per endpoint (unchanged)"
```

### Documentation & References

```yaml
# MUST READ - Critical context for this change

# Current implementation files (READ THESE)
- file: web/static/js/services/pattern_flow.js
  why: "Current 4-column implementation - MUST understand before changing"
  lines: "1-1085 (full file)"
  pattern: "Service class with state, columns, WebSocket, polling refresh"
  gotcha: "Uses 'combo' instead of 'daily_intraday', wrong API parameter"

- file: web/static/css/components/pattern-flow.css
  why: "Current 4-column responsive layout - MUST understand before adding 7-column breakpoints"
  lines: "1-493 (full file)"
  pattern: "Flexbox layout with theme support, 3 responsive breakpoints"
  gotcha: "flex-wrap must be enabled for responsive to work"

- file: tests/integration/test_pattern_flow_complete.py
  why: "Current test coverage - MUST update to test all 7 tiers"
  lines: "95-133 (multi-tier test function)"
  pattern: "Tests 3 tiers with Redis pub-sub simulation"
  gotcha: "Test uses 'combo' tier name (must change to 'daily_intraday')"

# Backend API documentation (VERIFY CONTRACTS)
- file: src/api/rest/tier_patterns.py
  why: "All 5 new endpoints implemented here - VERIFY timeframe parameter format"
  lines:
    - "354-449: /hourly endpoint"
    - "451-546: /weekly endpoint"
    - "548-643: /monthly endpoint"
    - "645-742: /daily_intraday endpoint"
    - "744-853: /indicators/latest endpoint"
  pattern: "Each endpoint queries specific table, returns standardized JSON"
  gotcha: "All endpoints tested and functional (✅ from pattern-flow-multi-table-display-RESULTS.md)"

- file: src/api/rest/pattern_consumer.py
  why: "/api/patterns/scan timeframe validation - CRITICAL for parameter fix"
  lines: "75-78: Valid timeframes list"
  critical: "✅ Valid timeframes: ['All', 'Daily', 'Hourly', 'Intraday', 'Weekly', 'Monthly', 'Combo', 'DailyIntraday']"
  gotcha: "Uses PascalCase (Daily, not daily) - must map tier names correctly"

# Similar working features (PATTERN REFERENCE)
- file: web/static/js/services/tier_pattern_service.js
  why: "Similar multi-tier pattern service - may have useful patterns"
  pattern: "Manages tier-based pattern data with API calls"
  gotcha: "May use different naming conventions"

# Sprint documentation (CONTEXT)
- file: docs/planning/sprints/sprint46/frontend-7-column-completion-SUMMARY.md
  why: "Comprehensive summary with exact code changes needed"
  pattern: "Detailed change specifications with line numbers"
  critical: "Contains EXACT before/after code for all 4 modifications"

- file: docs/planning/sprints/sprint46/pattern-flow-multi-table-display-RESULTS.md
  why: "Backend implementation results - confirms all endpoints working"
  pattern: "Validation results for backend API"
  critical: "✅ All 5 endpoints tested and functional"

# External documentation
- url: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flexible_Box_Layout/Basic_Concepts_of_Flexbox
  why: "Flexbox responsive layout patterns for 7-column design"
  critical: "Use flex-wrap: wrap for responsive behavior"

# TickStock-Specific Patterns
- file: web/CLAUDE.md
  why: "Web layer development guidelines and patterns"
  pattern: "WebSocket integration, theme system, performance targets"
  gotcha: "All WebSocket handlers must handle reconnection gracefully"
```

### Current Codebase tree (files being modified)

```bash
web/
├── static/
│   ├── css/
│   │   └── components/
│   │       └── pattern-flow.css         # MODIFY: Add 7-column responsive breakpoints
│   └── js/
│       └── services/
│           └── pattern_flow.js          # MODIFY: 4 changes (state, columns, loading, API param)
└── templates/
    └── dashboard/
        └── index.html                   # PRESERVE: No changes (includes pattern-flow.css)

tests/
└── integration/
    └── test_pattern_flow_complete.py    # UPDATE: Test all 7 tiers
```

### Known Gotchas of Current Code & Library Quirks

```javascript
// CRITICAL GOTCHAS

// 1. API PARAMETER BUG (line 647)
// CURRENT (BROKEN):
const response = await fetch(`/api/patterns/scan?tier=${tier}&limit=30`);
// ❌ Backend expects 'timeframe' parameter, not 'tier'
// ❌ Backend expects PascalCase (Daily), frontend uses lowercase (daily)

// FIX REQUIRED:
// Must map tier IDs to timeframe values:
// daily → Daily
// hourly → Hourly
// intraday → Intraday
// weekly → Weekly
// monthly → Monthly
// daily_intraday → DailyIntraday
// indicators → All

// 2. TIER NAMING INCONSISTENCY
// CURRENT: Uses 'combo' in state and columns
// CORRECT: Should be 'daily_intraday' to match backend

// 3. CSS FLEX-WRAP
// CRITICAL: .pattern-flow-columns MUST have flex-wrap: wrap for responsive
// Check line 72 - should be: flex-wrap: wrap !important;

// 4. WEBSOCKET EVENT HANDLING
// WebSocket events use tier names in data.tier field
// Must ensure all 7 tier names handled correctly

// TickStock-Specific Gotchas
// CRITICAL: TickStockAppV2 is CONSUMER ONLY
// - NO pattern detection logic in frontend
// - Read-only database access
// - All pattern data from backend API or Redis events

// CRITICAL: Performance Targets
// - <600ms total refresh for 7 API calls
// - <50ms per API endpoint
// - <100ms WebSocket delivery

// Library-Specific Quirks
// JavaScript Fetch API:
// - Always check response.ok before parsing JSON
// - Handle network errors with try-catch
// - Use AbortController for request timeout

// CSS Flexbox:
// - flex: 1 1 calc(14.28% - 13px) for 7 columns (100% / 7 = 14.28%)
// - Must account for gap width in calc() subtraction
// - Test in Chrome, Firefox, Safari for compatibility
```

---

## Change Implementation Blueprint

### Pre-Change Preparation

```yaml
1_backup_current_state:
  - action: "Create git branch"
    command: "git checkout -b change/pattern-flow-7-columns"

  - action: "Document current behavior"
    command: "Navigate to Pattern Flow page, take screenshots of 4-column layout"

  - action: "Run baseline tests"
    command: "python run_tests.py"
    expected: "All tests pass BEFORE changes"

2_analyze_dependencies:
  - action: "Verify backend endpoints ready"
    command: "Review docs/planning/sprints/sprint46/pattern-flow-multi-table-display-RESULTS.md"
    expected: "✅ All 5 endpoints tested and functional"

  - action: "Check HTML includes CSS"
    command: "rg 'pattern-flow.css' web/templates/"
    expected: "✅ Found in dashboard/index.html line 11"

  - action: "Verify no other JS dependencies"
    command: "rg 'PatternFlowService' web/static/js/"
    expected: "✅ Only pattern_flow.js and sidebar-navigation-controller.js"

3_create_regression_baseline:
  - action: "Document current state in tests"
    why: "Ensure existing 4 columns continue working after changes"
    location: "Manual testing checklist: Verify Daily, Intraday, Combo, Indicators columns work"
```

### Change Tasks (ordered by dependencies)

```yaml
Task 1: MODIFY web/static/js/services/pattern_flow.js (State Management)
  location: "Lines 28-39"
  CURRENT: |
    this.state = {
        patterns: {
            daily: [],
            intraday: [],
            combo: [],          // ❌ Old naming
            indicators: []
            // ❌ Missing: hourly, weekly, monthly
        },
        // ... other state properties
    };

  CHANGE: |
    this.state = {
        patterns: {
            daily: [],
            hourly: [],          // ✅ NEW
            intraday: [],
            weekly: [],          // ✅ NEW
            monthly: [],         // ✅ NEW
            daily_intraday: [],  // ✅ RENAMED from combo
            indicators: []
        },
        // ... other state properties (unchanged)
    };

  PRESERVE: "All other state properties (lastRefresh, countdown, isRefreshing, connectionStatus)"
  GOTCHA: "Rename 'combo' to 'daily_intraday' for consistency with backend"
  VALIDATION: "Check browser console for state initialization errors"

Task 2: EXPAND web/static/js/services/pattern_flow.js (Column Definitions)
  location: "Lines 134-139"
  CURRENT: |
    const columns = [
        { id: 'daily', title: 'Daily', icon: '📊', color: '#007bff' },
        { id: 'intraday', title: 'Intraday', icon: '⚡', color: '#28a745' },
        { id: 'combo', title: 'Combo', icon: '🔗', color: '#17a2b8' },
        { id: 'indicators', title: 'Indicators', icon: '📈', color: '#fd7e14' }
    ];

  CHANGE: |
    const columns = [
        { id: 'intraday', title: 'Intraday', icon: '⚡', color: '#28a745' },
        { id: 'hourly', title: 'Hourly', icon: '⏰', color: '#6f42c1' },      // ✅ NEW
        { id: 'daily', title: 'Daily', icon: '📊', color: '#007bff' },
        { id: 'weekly', title: 'Weekly', icon: '📈', color: '#20c997' },      // ✅ NEW
        { id: 'monthly', title: 'Monthly', icon: '📅', color: '#e83e8c' },    // ✅ NEW
        { id: 'daily_intraday', title: 'Combo', icon: '🔗', color: '#17a2b8' }, // ✅ RENAMED
        { id: 'indicators', title: 'Indicators', icon: '📊', color: '#fd7e14' }
    ];

  PRESERVE: "Column structure (id, title, icon, color properties)"
  GOTCHA: "Order matters for display: Intraday → Hourly → Daily → Weekly → Monthly → Combo → Indicators"
  VALIDATION: "Verify 7 columns render in correct order"

Task 3: MODIFY web/static/js/services/pattern_flow.js (Data Loading)
  location: "Line 631 (loadInitialData function)"
  CURRENT: |
    const promises = ['daily', 'intraday', 'combo', 'indicators'].map(tier =>
        this.loadPatternsByTier(tier)
    );

  CHANGE: |
    const promises = ['intraday', 'hourly', 'daily', 'weekly', 'monthly', 'daily_intraday', 'indicators'].map(tier =>
        this.loadPatternsByTier(tier)
    );

  PRESERVE: "Promise.all() pattern for parallel loading"
  DEPENDENCIES: "Must complete Task 1 (state) first so all tier arrays exist"
  VALIDATION: "Check Network tab shows 7 API calls, not 4"

Task 4: FIX web/static/js/services/pattern_flow.js (API Parameter - CRITICAL BUG)
  location: "Line 647 (loadPatternsByTier function)"
  CURRENT: |
    async loadPatternsByTier(tier) {
        try {
            const response = await fetch(`/api/patterns/scan?tier=${tier}&limit=30&sort=timestamp_desc`);
            // ❌ BUG: Backend expects 'timeframe' parameter (not 'tier')
            // ❌ BUG: Backend expects PascalCase values (Daily not daily)
        }
    }

  CHANGE: |
    async loadPatternsByTier(tier) {
        try {
            // ✅ FIX: Map tier IDs to timeframe values
            const timeframeMap = {
                daily: 'Daily',
                hourly: 'Hourly',
                intraday: 'Intraday',
                weekly: 'Weekly',
                monthly: 'Monthly',
                daily_intraday: 'DailyIntraday',
                indicators: 'All'
            };
            const timeframe = timeframeMap[tier] || 'All';

            // ✅ FIX: Use 'timeframe' parameter (not 'tier')
            const response = await fetch(`/api/patterns/scan?timeframe=${timeframe}&limit=30&sort_by=detected_at&sort_order=desc`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            // ... rest of function
        }
    }

  PRESERVE: "Error handling, mock data fallback, renderPatterns() call"
  GOTCHA: "CRITICAL - This fixes the API call bug preventing data from loading"
  VALIDATION: "Verify API calls succeed (status 200, not 400 Bad Request)"

Task 5: ADD web/static/css/components/pattern-flow.css (Responsive Breakpoints)
  location: "After line 118 (existing responsive section)"
  CURRENT: |
    /* Only 3 breakpoints: 1200px+ (4 cols), 768-1199px (2x2), <768px (stack) */

  CHANGE: |
    /* Desktop (1600px+): 7 columns */
    @media (min-width: 1600px) {
        .pattern-column-wrapper {
            flex: 1 1 calc(14.28% - 13px);  /* 100% / 7 = 14.28% */
        }
    }

    /* Large Laptop (1200px-1599px): 5 columns */
    @media (min-width: 1200px) and (max-width: 1599px) {
        .pattern-column-wrapper {
            flex: 1 1 calc(20% - 12px);  /* 100% / 5 = 20% */
        }
    }

    /* Laptop (992px-1199px): 4 columns */
    @media (min-width: 992px) and (max-width: 1199px) {
        .pattern-column-wrapper {
            flex: 1 1 calc(25% - 11.25px);  /* 100% / 4 = 25% */
        }
    }

    /* Tablet (768px-991px): 3 columns */
    @media (min-width: 768px) and (max-width: 991px) {
        .pattern-column-wrapper {
            flex: 1 1 calc(33.33% - 10px);  /* 100% / 3 = 33.33% */
        }
    }

    /* Mobile (480px-767px): 2 columns */
    @media (min-width: 480px) and (max-width: 767px) {
        .pattern-column-wrapper {
            flex: 1 1 calc(50% - 7.5px);  /* 100% / 2 = 50% */
        }
    }

    /* Small Mobile (<480px): 1 column */
    @media (max-width: 479px) {
        .pattern-column-wrapper {
            flex: 1 1 100%;
        }
    }

  PRESERVE: "Existing theme styles, animation styles, scrollbar styles"
  GOTCHA: "Must ensure .pattern-flow-columns has flex-wrap: wrap (check line 72)"
  VALIDATION: "Test responsive behavior by resizing browser window"

Task 6: UPDATE tests/integration/test_pattern_flow_complete.py (Test Coverage)
  location: "Lines 95-133 (test_multi_tier_patterns function)"
  CURRENT: |
    def test_multi_tier_patterns(self):
        """Test patterns for all three tiers (Daily/Intraday/Combo)."""
        tiers = [
            ('daily', 'HeadShoulders', 'TSLA', 0.90),
            ('intraday', 'VolumeSurge', 'NVDA', 0.75),
            ('combo', 'SupportBreakout', 'AAPL', 0.82)
        ]

  CHANGE: |
    def test_multi_tier_patterns(self):
        """Test patterns for all seven tiers."""
        tiers = [
            ('daily', 'HeadShoulders', 'TSLA', 0.90),
            ('hourly', 'MomentumShift', 'AMD', 0.85),      # ✅ NEW
            ('intraday', 'VolumeSurge', 'NVDA', 0.75),
            ('weekly', 'TrendReversal', 'SPY', 0.88),      # ✅ NEW
            ('monthly', 'BreakoutPattern', 'QQQ', 0.92),   # ✅ NEW
            ('daily_intraday', 'SupportBreakout', 'AAPL', 0.82),  # ✅ RENAMED
            ('indicators', 'RSI_Oversold', 'MSFT', 0.78)   # ✅ NEW
        ]

  PRESERVE: "Test structure (event format, Redis pub-sub logic, assertions)"
  DEPENDENCIES: "Must complete Tasks 1-4 first so frontend handles all 7 tiers"
  VALIDATION: "Run python run_tests.py - should pass with 7 tiers"

Task 7: VERIFY web/static/css/components/pattern-flow.css (flex-wrap check)
  location: "Line 70-76 (.pattern-flow-columns section)"
  CHECK: |
    .pattern-flow-columns {
        display: flex !important;
        flex-wrap: wrap !important;   // ✅ MUST BE PRESENT for responsive
        gap: 15px;
        margin: 0;
        overflow-x: auto;
    }

  PRESERVE: "All properties if correct"
  MODIFY_IF_NEEDED: "Add flex-wrap: wrap !important; if not present"
  GOTCHA: "Without flex-wrap, columns won't wrap on smaller screens"
  VALIDATION: "Test responsive wrapping behavior"
```

### Change Patterns & Key Details

```javascript
// ═══════════════════════════════════════════════════════════════
// Pattern 1: State Management Expansion (4 tiers → 7 tiers)
// ═══════════════════════════════════════════════════════════════

// BEFORE: Current state with 4 tiers
// File: web/static/js/services/pattern_flow.js (lines 28-39)
this.state = {
    patterns: {
        daily: [],
        intraday: [],
        combo: [],           // ❌ Old naming
        indicators: []
        // ❌ Missing: hourly, weekly, monthly
    },
    lastRefresh: null,
    countdown: 15,
    isRefreshing: false,
    connectionStatus: 'disconnected'
};

// AFTER: New state with 7 tiers
// File: web/static/js/services/pattern_flow.js (lines 28-39)
this.state = {
    patterns: {
        daily: [],
        hourly: [],          // ✅ NEW - Hourly patterns
        intraday: [],
        weekly: [],          // ✅ NEW - Weekly patterns
        monthly: [],         // ✅ NEW - Monthly patterns
        daily_intraday: [],  // ✅ RENAMED from 'combo' for clarity
        indicators: []
    },
    lastRefresh: null,
    countdown: 15,
    isRefreshing: false,
    connectionStatus: 'disconnected'
};

// CHANGE RATIONALE:
// - Current: Only 4 tiers tracked (daily, intraday, combo, indicators) = 57% coverage
// - New: All 7 timeframes tracked = 100% coverage
// - Naming: 'combo' → 'daily_intraday' matches backend terminology

// PRESERVED BEHAVIOR:
// - State structure unchanged (patterns object with tier arrays)
// - Other state properties unchanged (lastRefresh, countdown, etc.)
// - Pattern array initialization unchanged (empty arrays)

// GOTCHA:
// - Must rename 'combo' to 'daily_intraday' consistently across entire file
// - All methods that access state.patterns.combo must be updated


// ═══════════════════════════════════════════════════════════════
// Pattern 2: Column Definitions Expansion (4 columns → 7 columns)
// ═══════════════════════════════════════════════════════════════

// BEFORE: 4 column definitions
// File: web/static/js/services/pattern_flow.js (lines 134-139)
const columns = [
    { id: 'daily', title: 'Daily', icon: '📊', color: '#007bff' },
    { id: 'intraday', title: 'Intraday', icon: '⚡', color: '#28a745' },
    { id: 'combo', title: 'Combo', icon: '🔗', color: '#17a2b8' },
    { id: 'indicators', title: 'Indicators', icon: '📈', color: '#fd7e14' }
];

// AFTER: 7 column definitions (ordered by timeframe)
// File: web/static/js/services/pattern_flow.js (lines 134-147)
const columns = [
    { id: 'intraday', title: 'Intraday', icon: '⚡', color: '#28a745' },    // Shortest timeframe
    { id: 'hourly', title: 'Hourly', icon: '⏰', color: '#6f42c1' },        // ✅ NEW
    { id: 'daily', title: 'Daily', icon: '📊', color: '#007bff' },
    { id: 'weekly', title: 'Weekly', icon: '📈', color: '#20c997' },        // ✅ NEW
    { id: 'monthly', title: 'Monthly', icon: '📅', color: '#e83e8c' },      // ✅ NEW
    { id: 'daily_intraday', title: 'Combo', icon: '🔗', color: '#17a2b8' }, // ✅ RENAMED ID
    { id: 'indicators', title: 'Indicators', icon: '📊', color: '#fd7e14' }  // Longest timeframe
];

// CHANGE RATIONALE:
// - Current: 4 columns displayed
// - New: 7 columns with logical left-to-right timeframe ordering
// - Order: Intraday → Hourly → Daily → Weekly → Monthly → Combo → Indicators

// PRESERVED BEHAVIOR:
// - Column structure unchanged (id, title, icon, color properties)
// - Existing columns retain their icons and colors
// - Column rendering logic unchanged

// GOTCHA:
// - Array order determines UI display order (left to right)
// - 'id' must match state.patterns keys EXACTLY
// - Color choices matter for visual distinction (6 distinct colors chosen)


// ═══════════════════════════════════════════════════════════════
// Pattern 3: Parallel Data Loading (4 API calls → 7 API calls)
// ═══════════════════════════════════════════════════════════════

// BEFORE: Load 4 tiers in parallel
// File: web/static/js/services/pattern_flow.js (line 631)
const promises = ['daily', 'intraday', 'combo', 'indicators'].map(tier =>
    this.loadPatternsByTier(tier)
);

await Promise.all(promises);

// AFTER: Load 7 tiers in parallel
// File: web/static/js/services/pattern_flow.js (line 631)
const promises = ['intraday', 'hourly', 'daily', 'weekly', 'monthly', 'daily_intraday', 'indicators'].map(tier =>
    this.loadPatternsByTier(tier)
);

await Promise.all(promises);

// CHANGE RATIONALE:
// - Current: 4 parallel API calls (~400ms total)
// - New: 7 parallel API calls (~550ms estimated, <600ms target)
// - Parallel loading maintains performance (NOT sequential)

// PRESERVED BEHAVIOR:
// - Promise.all() pattern for parallel execution
// - Error handling per tier (one failure doesn't block others)
// - Loading state management unchanged

// GOTCHA:
// - All 7 API calls fire simultaneously (check backend can handle load)
// - Total time = MAX(individual call times), not SUM
// - Failed calls fall back to mock data (graceful degradation)


// ═══════════════════════════════════════════════════════════════
// Pattern 4: API Parameter Fix (CRITICAL BUG)
// ═══════════════════════════════════════════════════════════════

// BEFORE: Incorrect API call (uses wrong parameter)
// File: web/static/js/services/pattern_flow.js (line 647)
async loadPatternsByTier(tier) {
    try {
        const response = await fetch(`/api/patterns/scan?tier=${tier}&limit=30&sort=timestamp_desc`);
        // ❌ BUG 1: Backend expects 'timeframe' parameter (not 'tier')
        // ❌ BUG 2: Backend expects PascalCase (Daily, not daily)
        // ❌ BUG 3: sort parameter wrong (should be sort_by & sort_order)

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

// AFTER: Correct API call (matches backend contract)
// File: web/static/js/services/pattern_flow.js (line 647)
async loadPatternsByTier(tier) {
    try {
        // ✅ FIX: Map tier IDs to timeframe values
        const timeframeMap = {
            daily: 'Daily',
            hourly: 'Hourly',
            intraday: 'Intraday',
            weekly: 'Weekly',
            monthly: 'Monthly',
            daily_intraday: 'DailyIntraday',
            indicators: 'All'
        };
        const timeframe = timeframeMap[tier] || 'All';

        // ✅ FIX: Use correct parameters (timeframe, sort_by, sort_order)
        const response = await fetch(`/api/patterns/scan?timeframe=${timeframe}&limit=30&sort_by=detected_at&sort_order=desc`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        // Update state and UI
        this.state.patterns[tier] = data.patterns || [];
        this.renderPatterns(tier);

    } catch (error) {
        console.warn(`[PatternFlowService] Using mock data for ${tier}:`, error);

        // Use mock data as fallback
        this.state.patterns[tier] = this.generateMockPatterns(tier, 10);
        this.renderPatterns(tier);
    }
}

// CHANGE RATIONALE:
// - Current: API calls fail with 400 Bad Request (wrong parameter name)
// - Current: Even if parameter name fixed, values wrong (daily vs Daily)
// - New: Uses correct 'timeframe' parameter with PascalCase values
// - New: Matches backend validation (pattern_consumer.py:75-78)

// PRESERVED BEHAVIOR:
// - Error handling structure unchanged
// - Mock data fallback unchanged
// - renderPatterns() call unchanged
// - State update logic unchanged

// GOTCHA:
// - CRITICAL FIX: This is the root cause of "no data loading" bug
// - Backend expects: Daily, Hourly, Intraday, Weekly, Monthly, DailyIntraday, All
// - Frontend uses: daily, hourly, intraday, weekly, monthly, daily_intraday, indicators
// - Mapping table bridges this naming difference


// ═══════════════════════════════════════════════════════════════
// Pattern 5: Responsive 7-Column CSS Layout
// ═══════════════════════════════════════════════════════════════

// BEFORE: Fixed 4-column layout with 3 breakpoints
// File: web/static/css/components/pattern-flow.css (lines 78-118)

// Default: 4 columns
.pattern-column-wrapper {
    flex: 1 1 25%;       // 100% / 4 = 25%
    min-width: 250px;
    max-width: calc(25% - 12px);
}

// 1200px+: 4 columns in one row
@media (min-width: 1200px) {
    .pattern-column-wrapper {
        flex: 1 1 calc(25% - 12px);
        max-width: calc(25% - 12px);
    }
}

// 768-1199px: 2x2 grid
@media (min-width: 768px) and (max-width: 1199px) {
    .pattern-column-wrapper {
        flex: 1 1 calc(50% - 8px);
        max-width: calc(50% - 8px);
    }
}

// <768px: Vertical stack
@media (max-width: 767px) {
    .pattern-column-wrapper {
        flex: 1 1 100%;
        max-width: 100%;
    }
}

// AFTER: Responsive 7-column layout with 6 breakpoints
// File: web/static/css/components/pattern-flow.css (new section after line 118)

/* Desktop (1600px+): 7 columns */
@media (min-width: 1600px) {
    .pattern-column-wrapper {
        flex: 1 1 calc(14.28% - 13px);  /* 100% / 7 = 14.28% */
    }
}

/* Large Laptop (1200px-1599px): 5 columns */
@media (min-width: 1200px) and (max-width: 1599px) {
    .pattern-column-wrapper {
        flex: 1 1 calc(20% - 12px);  /* 100% / 5 = 20% */
    }
}

/* Laptop (992px-1199px): 4 columns */
@media (min-width: 992px) and (max-width: 1199px) {
    .pattern-column-wrapper {
        flex: 1 1 calc(25% - 11.25px);  /* 100% / 4 = 25% */
    }
}

/* Tablet (768px-991px): 3 columns */
@media (min-width: 768px) and (max-width: 991px) {
    .pattern-column-wrapper {
        flex: 1 1 calc(33.33% - 10px);  /* 100% / 3 = 33.33% */
    }
}

/* Mobile (480px-767px): 2 columns */
@media (min-width: 480px) and (max-width: 767px) {
    .pattern-column-wrapper {
        flex: 1 1 calc(50% - 7.5px);  /* 100% / 2 = 50% */
    }
}

/* Small Mobile (<480px): 1 column */
@media (max-width: 479px) {
    .pattern-column-wrapper {
        flex: 1 1 100%;
    }
}

// CHANGE RATIONALE:
// - Current: Fixed 4-column layout, only 3 breakpoints
// - New: Responsive 7→5→4→3→2→1 column layout, 6 breakpoints
// - Ensures usability across all screen sizes (4K desktop → small phone)

// PRESERVED BEHAVIOR:
// - Flexbox layout system unchanged
// - Column height and content styles unchanged
// - Theme support (light/dark) unchanged
// - Animations and transitions unchanged

// GOTCHA:
// - calc() adjusts for gap width: (percentage - gap_adjustment)
// - Must test on actual devices (not just browser resize)
// - Requires flex-wrap: wrap on .pattern-flow-columns container


// ═══════════════════════════════════════════════════════════════
// Pattern 6: Integration Test Updates (3 tiers → 7 tiers)
// ═══════════════════════════════════════════════════════════════

// BEFORE: Test 3 tiers
// File: tests/integration/test_pattern_flow_complete.py (lines 95-133)
def test_multi_tier_patterns(self):
    """Test patterns for all three tiers (Daily/Intraday/Combo)."""
    tiers = [
        ('daily', 'HeadShoulders', 'TSLA', 0.90),
        ('intraday', 'VolumeSurge', 'NVDA', 0.75),
        ('combo', 'SupportBreakout', 'AAPL', 0.82)
    ]

    flow_ids = []
    for tier, pattern, symbol, confidence in tiers:
        flow_id = str(uuid.uuid4())
        flow_ids.append(flow_id)

        event = {
            'event_type': 'pattern_detected',
            'source': 'TickStockPL',
            'flow_id': flow_id,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'flow_id': flow_id,
                'tier': tier,
                'data': {
                    'pattern': pattern,
                    'symbol': symbol,
                    'confidence': confidence,
                    'current_price': 100.0 + (confidence * 100),
                    'source': tier
                }
            }
        }

        self.redis_client.publish('tickstock.events.patterns', json.dumps(event))
        print(f"[OK] Published {tier} tier pattern: {pattern} for {symbol}")

    return flow_ids

// AFTER: Test all 7 tiers
// File: tests/integration/test_pattern_flow_complete.py (lines 95-133)
def test_multi_tier_patterns(self):
    """Test patterns for all seven tiers."""
    tiers = [
        ('daily', 'HeadShoulders', 'TSLA', 0.90),
        ('hourly', 'MomentumShift', 'AMD', 0.85),         # ✅ NEW
        ('intraday', 'VolumeSurge', 'NVDA', 0.75),
        ('weekly', 'TrendReversal', 'SPY', 0.88),         # ✅ NEW
        ('monthly', 'BreakoutPattern', 'QQQ', 0.92),      # ✅ NEW
        ('daily_intraday', 'SupportBreakout', 'AAPL', 0.82),  # ✅ RENAMED
        ('indicators', 'RSI_Oversold', 'MSFT', 0.78)      # ✅ NEW
    ]

    flow_ids = []
    for tier, pattern, symbol, confidence in tiers:
        flow_id = str(uuid.uuid4())
        flow_ids.append(flow_id)

        event = {
            'event_type': 'pattern_detected',
            'source': 'TickStockPL',
            'flow_id': flow_id,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'flow_id': flow_id,
                'tier': tier,
                'data': {
                    'pattern': pattern,
                    'symbol': symbol,
                    'confidence': confidence,
                    'current_price': 100.0 + (confidence * 100),
                    'source': tier
                }
            }
        }

        self.redis_client.publish('tickstock.events.patterns', json.dumps(event))
        print(f"[OK] Published {tier} tier pattern: {pattern} for {symbol}")

    return flow_ids

// CHANGE RATIONALE:
// - Current: Only tests 3 tiers (43% coverage)
// - New: Tests all 7 tiers (100% coverage)
// - Validates Redis → WebSocket flow for each tier

// PRESERVED BEHAVIOR:
// - Event structure unchanged
// - Redis pub-sub mechanism unchanged
// - Test assertions unchanged (just more data)

// GOTCHA:
// - Must use 'daily_intraday' not 'combo' (matches frontend state keys)
// - Pattern names should be realistic (not test-only placeholders)
// - Confidence values varied to test priority calculations
```

### Integration Points (What Changes)

```yaml
DATABASE:
  schema_changes: No
  query_changes: "No direct database queries in pattern_flow.js (uses API endpoints)"

REDIS_CHANNELS:
  message_format_changes: No
  channel_updates: "None - WebSocket events already support all tiers"

WEBSOCKET:
  event_changes: No
  event_updates: "None - pattern_detected and indicator_update events work for all tiers"

TICKSTOCKPL_API:
  endpoint_changes: No
  api_updates: "None - TickStockPL integration unchanged"

FRONTEND_API:
  endpoint_changes: No
  note: "Backend endpoints already exist and functional - frontend just needs to call them"
```

---

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# JavaScript linting (if available)
# Note: TickStock project may not have JS linting configured
# Manual syntax check via browser console

# CSS linting
ruff check web/static/css/components/pattern-flow.css  # If ruff supports CSS
# OR manual validation via browser DevTools

# Expected: Zero syntax errors
```

### Level 2: Unit Tests (Component Validation)

```bash
# No JavaScript unit tests exist for pattern_flow.js
# Validation happens at integration test level

# Python integration tests
python -m pytest tests/integration/test_pattern_flow_complete.py -v

# Expected: All tests pass with 7 tiers
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
python run_tests.py

# Expected Output:
# - All existing tests still pass (regression-free)
# - Pattern flow tests validate 7 tiers
# - ~30 second runtime
# - No new errors introduced

# Alternative command
python tests/integration/run_integration_tests.py

# Expected: Same results, more detailed output
```

### Level 4: TickStock-Specific Validation

```bash
# Performance Validation
# CRITICAL: Verify 7 parallel API calls <600ms total

# Test in browser DevTools:
# 1. Open Pattern Flow page
# 2. Open DevTools Network tab
# 3. Filter by "scan" to see API calls
# 4. Check timing for all 7 calls
# 5. Verify total < 600ms

# Expected:
# - 7 API calls fire in parallel
# - Each call <50ms
# - Total time <600ms (likely ~550ms)

# Responsive Layout Validation
# Test breakpoints by resizing browser:
# - 1600px+: Should show 7 columns
# - 1200-1599px: Should show 5 columns
# - 992-1199px: Should show 4 columns
# - 768-991px: Should show 3 columns
# - 480-767px: Should show 2 columns
# - <480px: Should show 1 column

# Expected: Smooth wrapping, no horizontal overflow

# WebSocket Validation
# Verify real-time updates work for all 7 columns:
# 1. Keep Pattern Flow page open
# 2. Wait for pattern detection events (or use Test Mode)
# 3. Verify new patterns appear in correct columns
# 4. Check 15-second auto-refresh updates all columns

# Expected: Real-time updates for all 7 tiers
```

### Level 5: Regression Testing (MANDATORY for Changes)

```bash
# Regression Test Suite
# CRITICAL: Ensure existing 4 columns still work

# Manual Regression Checklist:
# - [ ] Daily column loads and displays patterns
# - [ ] Intraday column loads and displays patterns
# - [ ] Daily-Intraday (formerly Combo) column loads and displays patterns
# - [ ] Indicators column loads and displays patterns
# - [ ] 15-second auto-refresh updates all columns
# - [ ] WebSocket events update columns in real-time
# - [ ] Light/Dark theme works for all columns
# - [ ] Pattern click shows details modal
# - [ ] Responsive layout works (test on mobile, tablet, desktop)
# - [ ] No JavaScript console errors
# - [ ] No CSS rendering issues

# Before/After Performance Comparison:
# BEFORE (4 columns):
#   - API calls: 4
#   - Total refresh time: ~400ms
#   - Memory usage: ~15MB

# AFTER (7 columns):
#   - API calls: 7
#   - Total refresh time: <600ms target (likely ~550ms)
#   - Memory usage: ~20MB estimated

# Acceptance criteria:
# - All 7 columns display correctly
# - Performance <600ms (within target)
# - No regressions in existing functionality
# - Responsive layout works across devices
```

---

## Final Validation Checklist

### Technical Validation

- [ ] All 5 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] Regression tests pass: All existing 4 columns still work
- [ ] No JavaScript console errors
- [ ] No CSS rendering issues
- [ ] Pattern Flow page loads without errors

### Change Validation

- [ ] All 7 columns display (Intraday, Hourly, Daily, Weekly, Monthly, Daily-Intraday, Indicators)
- [ ] Each column loads data (or shows "No patterns detected" if empty)
- [ ] 15-second auto-refresh updates all 7 columns
- [ ] API parameter bug fixed (timeframe mapping works correctly)
- [ ] Performance target met: <600ms for 7 parallel API calls
- [ ] Responsive layout verified across all breakpoints

### Impact Validation

- [ ] No breaking changes to existing functionality
- [ ] WebSocket events work for all 7 tiers
- [ ] Light/Dark theme applies to all 7 columns
- [ ] Pattern click modal works for all columns
- [ ] Test coverage updated (7 tiers tested)

### TickStock Architecture Validation

- [ ] Consumer role preserved (TickStockAppV2)
- [ ] Read-only database access (no writes)
- [ ] Redis pub-sub events handled for all tiers
- [ ] WebSocket latency <100ms
- [ ] Performance targets achieved (<600ms total refresh)
- [ ] No architectural violations detected

### Code Quality Validation

- [ ] Follows existing JavaScript patterns (ES6 class, async/await)
- [ ] Follows existing CSS patterns (Flexbox, CSS variables, responsive)
- [ ] Naming conventions consistent (snake_case for tiers, PascalCase for timeframes)
- [ ] No code duplication
- [ ] Comments updated where needed
- [ ] No "Generated by Claude" comments

### Documentation & Deployment

- [ ] Manual testing completed and documented
- [ ] Screenshots captured for 7-column layout
- [ ] Sprint notes updated with completion details
- [ ] No configuration changes required
- [ ] Ready for production deployment

---

## Anti-Patterns to Avoid (Change-Specific)

### Modification Anti-Patterns

- ❌ **Don't add columns without updating state**
  - Risk: Columns render but have no data
  - Solution: Always update state.patterns first

- ❌ **Don't change tier names without global search/replace**
  - Risk: 'combo' → 'daily_intraday' must change everywhere
  - Solution: Search entire file for 'combo', replace all instances

- ❌ **Don't forget API parameter fix**
  - Risk: API calls fail with 400 Bad Request
  - Solution: CRITICAL - map tier IDs to timeframe values (daily → Daily)

- ❌ **Don't skip responsive breakpoints**
  - Risk: 7 columns overflow on smaller screens
  - Solution: Add all 6 responsive breakpoints (7/5/4/3/2/1 columns)

- ❌ **Don't test only on desktop**
  - Risk: Mobile users see broken layout
  - Solution: Test on actual mobile devices, not just browser resize

### TickStock-Specific Change Anti-Patterns

- ❌ **Don't add backend logic to pattern_flow.js**
  - Risk: Violates Consumer role separation
  - Solution: All pattern detection happens in TickStockPL

- ❌ **Don't make synchronous API calls**
  - Risk: Blocks UI for 7 sequential calls (~350ms × 7 = 2.45 seconds)
  - Solution: Use Promise.all() for parallel loading

- ❌ **Don't ignore performance targets**
  - Risk: Slow refresh frustrates users
  - Solution: Measure actual timing, optimize if >600ms

- ❌ **Don't skip integration tests**
  - Risk: Breaks existing functionality silently
  - Solution: ALWAYS run `python run_tests.py` before committing

- ❌ **Don't hardcode tier lists**
  - Risk: Changes require multiple file updates
  - Solution: (Future improvement) Consider config-driven tier list

---

## Success Metrics

**Confidence Score**: 9/10 for one-pass modification success likelihood

**Justification**:
- ✅ **Backend Complete**: All 5 API endpoints functional and tested
- ✅ **Clear Requirements**: Exact line numbers and code changes specified
- ✅ **Low Risk**: Frontend-only changes, no breaking changes
- ✅ **Strong Context**: BEFORE/AFTER code examples for all changes
- ✅ **Comprehensive Testing**: Integration tests cover all 7 tiers
- ⚠️ **Manual Testing Required**: Responsive layout needs device testing (-1 point)

**Validation**: This PRP enables an AI agent unfamiliar with the codebase to complete the 7-column frontend enhancement successfully, matching the existing backend capabilities.

---

**END OF PRP**
