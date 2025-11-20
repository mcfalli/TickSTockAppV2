name: "Streaming Dashboard UI Consolidation - CHANGE PRP"
description: |
  Consolidate Live Streaming page display to show pattern/indicator info
  and raw Redis content inline (single row) instead of expanded multi-row view.

---

## Goal

**Change Type**: enhancement

**Current Behavior**: The Live Streaming dashboard displays each pattern or indicator detection in an expanded multi-row format:
- **Row 1**: Event header (pattern badge, symbol, confidence/value, timestamp)
- **Row 2**: "Raw Redis Content:" label
- **Row 3+**: Full JSON content in a code block

This creates a vertically-stretched view where each event takes significant vertical space.

**Desired Behavior**: Display each pattern or indicator detection in a consolidated single-row format:
- **Single Row**: Event info (badge, symbol, confidence/value) + abbreviated timestamp + condensed JSON inline
- Compact view showing more events in the same vertical space
- Abbreviated timestamp (e.g., "14:23:45" instead of full date-time display)
- JSON content condensed to single line or key fields only

**Success Definition**:
- Each pattern/indicator displays in a single compact row
- More events visible in the same viewport height (estimated 2-3x more events visible)
- Timestamp abbreviated to time-only format
- Raw JSON content present but condensed/abbreviated
- No loss of critical information (symbol, pattern type, confidence, timestamp)

**Breaking Changes**: No
- This is purely a frontend display change
- No API contracts affected
- No WebSocket message formats changed
- No database queries modified

## User Persona

**Target User**: TickStock.ai end users monitoring real-time streaming patterns and indicators

**Current Pain Point**:
- Live Streaming dashboard shows too few events in viewport due to expanded multi-row display
- Excessive scrolling required to see recent pattern/indicator history
- Visual clutter from full JSON display makes it hard to scan events quickly
- Timestamp takes unnecessary horizontal space with full date-time format

**Expected Improvement**:
- 2-3x more events visible without scrolling
- Faster visual scanning of recent detections
- Cleaner, more professional appearance
- Reduced horizontal space usage with abbreviated timestamps
- Easier to spot patterns and trends at a glance

## Why This Change

- **User Experience**: Current expanded view requires excessive scrolling, making it difficult to see event history and spot trends quickly
- **Information Density**: Single-row format increases information density, showing more events in limited viewport space
- **Visual Clarity**: Inline JSON reduces visual clutter while preserving technical transparency
- **Professional Polish**: Consolidated view looks more refined and production-ready
- **Performance**: Fewer DOM elements per event may improve rendering performance (minor benefit)
- **Risks of NOT making this change**: Users frustrated by poor visibility of event history, reduced effectiveness of real-time monitoring

## What Changes

We will modify the `StreamingDashboardService` JavaScript class to consolidate the event display from multi-row expanded format to single-row inline format.

**Specific Changes**:
1. Modify `addPatternEvent()` method to create single-row event display
2. Modify `addIndicatorEvent()` method to create single-row event display
3. Update CSS styling for inline event items
4. Abbreviate timestamp format from full datetime to time-only
5. Condense JSON content to inline format (single line or key fields)

### Success Criteria

- [x] Pattern events display in single row with abbreviated timestamp
- [x] Indicator events display in single row with abbreviated timestamp
- [x] JSON content condensed to inline format
- [x] 2-3x more events visible in same viewport height
- [x] All existing WebSocket event handling unchanged
- [x] No performance degradation
- [x] Theme system (light/dark) continues to work correctly

## Current Implementation Analysis

### Files to Modify

```yaml
- file: web/static/js/services/streaming-dashboard.js
  current_responsibility: "Streaming Dashboard Service - manages real-time pattern and indicator display via WebSocket events"
  lines_to_modify: |
    - Lines 501-548: addPatternEvent() method (multi-row display creation)
    - Lines 592-635: addIndicatorEvent() method (multi-row display creation)
    - Lines 167-315: CSS styling (event-item-expanded, event-header, redis-content, redis-json)
  current_pattern: |
    - Creates div.event-item-expanded for each event
    - Separate div.event-header for pattern/indicator info
    - Separate div.redis-content with <pre> block for JSON
    - Full JSON display with JSON.stringify(data, null, 2)
  reason_for_change: "Consolidate to single-row inline display for better UX and information density"
```

### Current Code Patterns (What Exists Now)

```javascript
// CURRENT IMPLEMENTATION: Pattern Event Display
// File: web/static/js/services/streaming-dashboard.js (lines 501-548)

addPatternEvent(detection) {
    const stream = document.getElementById('patternStream');
    if (!stream) return;

    const eventItem = document.createElement('div');
    eventItem.className = 'event-item-expanded';  // ← Multi-row expanded format

    const confidence = detection.confidence || 0;
    const confClass = confidence >= 0.8 ? 'confidence-high' :
                     confidence >= 0.5 ? 'confidence-medium' : 'confidence-low';

    const patternType = detection.pattern_type || detection.pattern || detection.pattern_name || 'Unknown';

    // Format raw Redis content (FULL JSON)
    const rawContent = JSON.stringify(detection, null, 2);  // ← Multi-line formatted

    eventItem.innerHTML = `
        <div class="event-header">  <!-- Row 1: Event info -->
            <div>
                <span class="pattern-badge">${patternType}</span>
                <strong class="ms-2">${detection.symbol || 'N/A'}</strong>
            </div>
            <div>
                <span class="${confClass}">${(confidence * 100).toFixed(1)}%</span>
                <small class="ms-2 text-muted">${new Date(detection.timestamp || Date.now()).toLocaleTimeString()}</small>
            </div>
        </div>
        <div class="redis-content">  <!-- Row 2+: Raw JSON -->
            <strong>Raw Redis Content:</strong>
            <pre class="redis-json">${rawContent}</pre>  <!-- Separate code block -->
        </div>
    `;

    stream.insertBefore(eventItem, stream.firstChild);

    // Limit to 50 items
    while (stream.children.length > 50) {
        stream.removeChild(stream.lastChild);
    }

    // Update counter
    const counter = document.getElementById('patternCount');
    if (counter) {
        counter.textContent = `${this.patternCount} patterns`;
    }
}

// CURRENT IMPLEMENTATION: Indicator Event Display
// File: web/static/js/services/streaming-dashboard.js (lines 592-635)

addIndicatorEvent(calculation) {
    const stream = document.getElementById('alertStream');
    if (!stream) return;

    const indicatorType = calculation.indicator || calculation.indicator_type || 'Unknown';
    const symbol = calculation.symbol || 'N/A';
    const value = calculation.value !== undefined ? calculation.value :
                 (calculation.values ? JSON.stringify(calculation.values) : 'N/A');

    // Format raw Redis content (FULL JSON)
    const rawContent = JSON.stringify(calculation, null, 2);  // ← Multi-line formatted

    const indicatorItem = document.createElement('div');
    indicatorItem.className = 'event-item-expanded';  // ← Multi-row expanded format
    indicatorItem.innerHTML = `
        <div class="event-header">  <!-- Row 1: Event info -->
            <div>
                <span class="pattern-badge" style="background: #17a2b8;">${indicatorType}</span>
                <strong class="ms-2">${symbol}</strong>
            </div>
            <div>
                <span class="text-primary">${typeof value === 'object' ? JSON.stringify(value) : value}</span>
                <small class="ms-2 text-muted">${new Date(calculation.timestamp || Date.now()).toLocaleTimeString()}</small>
            </div>
        </div>
        <div class="redis-content">  <!-- Row 2+: Raw JSON -->
            <strong>Raw Redis Content:</strong>
            <pre class="redis-json">${rawContent}</pre>  <!-- Separate code block -->
        </div>
    `;

    stream.insertBefore(indicatorItem, stream.firstChild);

    // Limit to 30 items
    while (stream.children.length > 30) {
        stream.removeChild(stream.lastChild);
    }

    // Update counter
    const counter = document.getElementById('alertCount');
    if (counter) {
        counter.textContent = `${this.alertCount} alerts`;
    }
}

// CURRENT DEPENDENCIES: What depends on this code
// - WebSocket event handlers call addPatternEvent() and addIndicatorEvent()
//   - handleStreamingPattern() at line 377
//   - handleStreamingPatternsBatch() at line 389
//   - handleStreamingIndicator() at line 416
//   - handleStreamingIndicatorsBatch() at line 434
// - DOM elements: patternStream, alertStream containers (rendered in render() method)
// - CSS classes: event-item-expanded, event-header, redis-content, redis-json
// - No external systems rely on this display logic (frontend-only)
// - No database dependencies (display only, no data persistence)
```

### Current CSS Patterns

```css
/* CURRENT CSS: Multi-row expanded event styling */
/* File: web/static/js/services/streaming-dashboard.js (lines 218-259) */

.event-item-expanded {
    padding: 15px;
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 5px;
    margin-bottom: 10px;
    background: var(--bg-secondary, #f8f9fa);
}

.event-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;         /* ← Spacing between header and content */
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-color, #dee2e6);  /* ← Visual separator */
}

.redis-content {
    margin-top: 10px;  /* ← Separate section for JSON */
}

.redis-content strong {
    display: block;
    margin-bottom: 5px;
    color: var(--text-primary, #333);
}

.redis-json {
    background: #282c34;
    color: #abb2bf;
    border: 1px solid #3e4451;
    border-radius: 4px;
    padding: 12px;
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    max-height: 300px;
    overflow-y: auto;
    overflow-x: auto;
    white-space: pre;    /* ← Preserves multi-line formatting */
    line-height: 1.4;
    margin: 0;
}
```

### Dependency Analysis

```yaml
upstream_dependencies:
  # Code that CALLS the functions being modified
  - component: "web/static/js/services/streaming-dashboard.js::handleStreamingPattern()"
    dependency: "Calls addPatternEvent(detection) at line 378"
    impact: "No change - function signature unchanged, only display logic modified"

  - component: "web/static/js/services/streaming-dashboard.js::handleStreamingPatternsBatch()"
    dependency: "Calls addPatternEvent(pattern) at line 389"
    impact: "No change - function signature unchanged"

  - component: "web/static/js/services/streaming-dashboard.js::handleStreamingIndicator()"
    dependency: "Calls addIndicatorEvent(calculation) at line 416"
    impact: "No change - function signature unchanged"

  - component: "web/static/js/services/streaming-dashboard.js::handleStreamingIndicatorsBatch()"
    dependency: "Calls addIndicatorEvent(calculation) at line 434"
    impact: "No change - function signature unchanged"

downstream_dependencies:
  # Code that is CALLED BY the functions being modified
  - component: "DOM API (document.getElementById, createElement, etc.)"
    dependency: "addPatternEvent() and addIndicatorEvent() manipulate DOM"
    impact: "No change to API usage - different HTML structure but same DOM methods"

  - component: "Browser rendering engine"
    dependency: "Renders HTML structure created by event methods"
    impact: "Different HTML/CSS but no browser API changes"

database_dependencies:
  # No database dependencies - this is pure frontend display logic
  - impact: "None"

redis_dependencies:
  # No Redis channel or message format changes
  - impact: "None - only displaying existing Redis event data differently"

websocket_dependencies:
  # WebSocket event handling unchanged
  - event_type: "streaming_pattern"
    current_format: "{detection: {...}}"
    impact: "None - only display changes, event handling unchanged"

  - event_type: "streaming_indicator"
    current_format: "{calculation: {...}}"
    impact: "None - only display changes, event handling unchanged"

external_api_dependencies:
  # No external API dependencies
  - impact: "None"
```

### Test Coverage Analysis

```yaml
unit_tests:
  # No dedicated unit tests for frontend JavaScript (manual testing only)
  - test_file: "None"
    coverage: "Frontend JavaScript not unit tested"
    needs_update: "No"

integration_tests:
  - test_file: "tests/integration/test_streaming_quick.py"
    coverage: "Tests WebSocket event flow, does NOT validate specific DOM structure"
    needs_update: "No"
    update_reason: "Integration tests do not assert on HTML structure"

  - test_file: "tests/integration/test_streaming_complete.py"
    coverage: "End-to-end streaming test, does NOT validate DOM"
    needs_update: "No"

missing_coverage:
  - scenario: "Visual regression testing for UI changes"
    reason: "No automated visual testing - requires manual verification"
```

## Impact Analysis

### Potential Breakage Points

```yaml
high_risk:
  # None - this is a low-risk frontend-only change

medium_risk:
  # None

low_risk:
  - component: "CSS theme integration"
    risk: "New CSS classes may not inherit theme variables correctly"
    mitigation: "Test in both light and dark themes, verify var() CSS variables work"

  - component: "Browser compatibility"
    risk: "Inline styles may render differently across browsers"
    mitigation: "Test in Chrome, Firefox, Edge (standard modern browsers)"

  - component: "Long pattern names or symbols"
    risk: "Inline format may overflow or wrap awkwardly with very long text"
    mitigation: "Use CSS text-overflow: ellipsis or word-break for long content"
```

### Performance Impact

```yaml
expected_improvements:
  - metric: "DOM elements per event"
    current: "~6 elements (event-item-expanded, event-header, 2 divs, redis-content, pre)"
    target: "~3-4 elements (event-item-inline, 1-2 spans)"
    measurement: "Browser DevTools Elements panel inspection"
    benefit: "Fewer DOM nodes = slightly faster rendering"

  - metric: "Viewport efficiency"
    current: "~5-8 events visible in 500px height viewport"
    target: "~15-20 events visible in 500px height viewport"
    measurement: "Manual visual inspection"
    benefit: "2-3x more events visible without scrolling"

potential_regressions:
  - metric: "Event rendering time"
    current: "~2-5ms per event (estimated)"
    risk: "Could increase slightly if condensing JSON is expensive"
    threshold: "<10ms acceptable per event"
    measurement: "Browser DevTools Performance profiler"
    mitigation: "Use simple truncation/substring for JSON condensing (not complex parsing)"
```

### Backward Compatibility

```yaml
backward_compatibility:
  breaking_changes: No

  compatibility_guarantee: |
    - No API contracts affected (frontend display only)
    - WebSocket event handling unchanged
    - No database schema changes
    - No Redis message format changes
    - All existing WebSocket event handlers work unchanged
    - Function signatures for addPatternEvent() and addIndicatorEvent() unchanged
    - Theme system integration preserved
```

## All Needed Context

### Context Completeness Check

_If someone knew nothing about this codebase or the current implementation, would they have everything needed to make this change successfully without breaking anything?_

**Answer**: Yes - all current code patterns, dependencies, CSS, and WebSocket integration documented above.

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: TickStockAppV2
  role: Consumer (UI/UX, WebSocket client, read-only database)

  redis_channels:
    - channel: "tickstock:patterns:streaming"
      change_type: none
      current_behavior: "Publishes pattern detections, consumed via WebSocket"
      new_behavior: "Unchanged - only display changes"

    - channel: "tickstock:indicators:streaming"
      change_type: none
      current_behavior: "Publishes indicator calculations, consumed via WebSocket"
      new_behavior: "Unchanged - only display changes"

  database_access:
    mode: read-only
    tables_affected: []
    queries_modified: "None - this is frontend display only"
    schema_changes: No

  websocket_integration:
    affected: No
    broadcast_changes: "None - event handling unchanged, only display modified"
    message_format_changes: "None"

  tickstockpl_api:
    affected: No
    endpoint_changes: "None"

  performance_targets:
    - metric: "WebSocket delivery"
      current: "~50ms end-to-end"
      target: "<100ms end-to-end (unchanged)"
      impact: "No change - display modification only"

    - metric: "Event rendering"
      current: "~2-5ms per event"
      target: "<10ms per event"
      impact: "Should remain similar or improve slightly (fewer DOM elements)"
```

### Documentation & References

```yaml
# MUST READ - Include these in your context window

# Current implementation references (CRITICAL for modifications)
- file: web/static/js/services/streaming-dashboard.js
  why: "Contains current multi-row event display logic to be modified"
  lines: 501-548 (addPatternEvent), 592-635 (addIndicatorEvent), 167-315 (CSS)
  pattern: "Multi-row expanded format with separate header and JSON sections"
  gotcha: |
    - JSON.stringify(data, null, 2) creates multi-line formatted JSON
    - event-item-expanded class has margin-bottom: 10px for vertical spacing
    - Stream limits: 50 patterns, 30 indicators (must preserve)
    - insertBefore(stream.firstChild) adds newest events at top

# Similar working features (for pattern consistency)
- file: web/static/js/services/streaming-dashboard.js
  why: "addAlertEvent() method (lines 553-586) shows alternative compact alert display"
  pattern: "alert-rsi-overbought/oversold classes with inline info"
  gotcha: "Uses template literals for HTML creation - same approach for new inline format"

# External documentation
- url: https://developer.mozilla.org/en-US/docs/Web/API/Date/toLocaleTimeString
  why: "For abbreviating timestamp to time-only format"
  critical: "Use toLocaleTimeString() for consistent time formatting across browsers"

- url: https://developer.mozilla.org/en-US/docs/Web/CSS/text-overflow
  why: "For handling long text in inline format"
  critical: "Use text-overflow: ellipsis to prevent layout breaking with long pattern names"

# TickStock-Specific References
- file: web/CLAUDE.md
  why: "Web layer development guidelines and patterns"
  pattern: "Frontend integration patterns, theme system usage"
  gotcha: "Use var(--css-variable) for theme-aware styling"

- file: web/static/js/services/streaming-dashboard.js
  why: "Theme system CSS variables (lines 302-314)"
  pattern: "body.dark-theme selectors for dark mode support"
  gotcha: "New CSS must support both light and dark themes"
```

### Current Codebase Tree (files being modified)

```bash
web/
└── static/
    └── js/
        └── services/
            └── streaming-dashboard.js    # MODIFY: addPatternEvent(), addIndicatorEvent(), CSS
```

### Known Gotchas of Current Code & Library Quirks

```python
# CRITICAL: Current Code Gotchas

# Gotcha 1: Event Stream Limits
# - patternStream limited to 50 items (line 539)
# - alertStream limited to 30 items (line 625)
# - Must preserve these limits in modified code

# Gotcha 2: Newest Events at Top
# - stream.insertBefore(eventItem, stream.firstChild) adds to top (lines 536, 623)
# - Must preserve this behavior for chronological ordering

# Gotcha 3: Multiple Field Name Variations
# - Pattern type: detection.pattern_type || detection.pattern || detection.pattern_name (line 513)
# - Indicator type: calculation.indicator || calculation.indicator_type (line 596)
# - Must preserve all fallback checks

# Gotcha 4: Theme System Integration
# - CSS uses var(--border-color), var(--bg-secondary), var(--text-primary)
# - Must use same CSS variable pattern for new styles
# - body.dark-theme overrides (lines 302-314) must work with new classes

# Gotcha 5: Counter Updates
# - Pattern counter: getElementById('patternCount') at line 545
# - Alert counter: getElementById('alertCount') at line 631
# - Must preserve counter updates

# TickStock-Specific Gotchas
# - Flask Application Context: Not applicable (frontend only)
# - Worker Boundaries: Not applicable (no backend changes)
# - Redis Message Formats: Unchanged (display only)

# Library-Specific Quirks
# - JSON.stringify(): null parameter creates multi-line output, remove for single-line
# - Date.toLocaleTimeString(): Returns time portion only (e.g., "2:45:30 PM")
# - Template literals: Use ${} for dynamic content, escape backticks if needed
# - DOM manipulation: insertBefore() adds before specified node, removeChild() removes from parent
```

## Change Implementation Blueprint

### Pre-Change Preparation

```yaml
1_backup_current_state:
  - action: "Create git branch"
    command: "git checkout -b change/streaming-ui-consolidation"

  - action: "Document current behavior"
    command: "Open http://localhost:5000/streaming in browser, take screenshots of current multi-row display"

  - action: "Test current functionality"
    command: "Verify patterns and indicators display correctly in current expanded format"

2_analyze_dependencies:
  - action: "Confirm no external callers"
    command: "rg 'addPatternEvent|addIndicatorEvent' web/"
    expected: "Only streaming-dashboard.js references found"

  - action: "Check CSS usage"
    command: "rg 'event-item-expanded|redis-content|redis-json' web/"
    expected: "Only streaming-dashboard.js inline styles found"

3_create_regression_baseline:
  - action: "Document current display"
    why: "Ensure new format shows same information, just reorganized"
    location: "Take screenshots showing pattern badge, symbol, confidence, timestamp, JSON content"
```

### Change Tasks (ordered by dependencies)

```yaml
Task 1: MODIFY web/static/js/services/streaming-dashboard.js::addPatternEvent()
  - CURRENT: Lines 501-548, creates multi-row event-item-expanded with separate header and redis-content sections
  - CHANGE: |
      - Replace event-item-expanded with event-item-inline class
      - Combine header and JSON into single row
      - Abbreviate timestamp using toLocaleTimeString()
      - Condense JSON to single line using JSON.stringify(detection) or selective key display
      - Remove separate redis-content div
  - PRESERVE: |
      - Function signature: addPatternEvent(detection)
      - Stream container: patternStream
      - insertBefore(stream.firstChild) for newest-first ordering
      - 50-item limit
      - Pattern counter update
      - Pattern type fallback: pattern_type || pattern || pattern_name
  - GOTCHA: |
      - Must handle long pattern names (use text-overflow: ellipsis)
      - JSON may be large - truncate or show key fields only
      - Theme variables (var(--color)) must work with new structure
  - VALIDATION: |
      - Open Live Streaming page
      - Verify pattern events display in single row
      - Verify timestamp abbreviated (time only)
      - Verify JSON content visible inline (abbreviated)

Task 2: MODIFY web/static/js/services/streaming-dashboard.js::addIndicatorEvent()
  - CURRENT: Lines 592-635, creates multi-row event-item-expanded with separate header and redis-content sections
  - CHANGE: |
      - Replace event-item-expanded with event-item-inline class
      - Combine header and JSON into single row
      - Abbreviate timestamp using toLocaleTimeString()
      - Condense JSON to single line
      - Remove separate redis-content div
  - PRESERVE: |
      - Function signature: addIndicatorEvent(calculation)
      - Stream container: alertStream
      - insertBefore(stream.firstChild) for newest-first ordering
      - 30-item limit
      - Alert counter update
      - Indicator type fallback: indicator || indicator_type
  - GOTCHA: |
      - Indicator values can be objects or primitives (handle both)
      - Must handle long indicator names
      - Theme variables must work
  - VALIDATION: |
      - Open Live Streaming page
      - Verify indicator events display in single row
      - Verify timestamp abbreviated
      - Verify value and JSON visible inline

Task 3: UPDATE web/static/js/services/streaming-dashboard.js CSS styling
  - CURRENT: Lines 218-259, styles for event-item-expanded, event-header, redis-content, redis-json
  - MODIFY: |
      - Rename .event-item-expanded to .event-item-inline
      - Remove margin-bottom, border-bottom from .event-header (no separation needed)
      - Change .redis-json from multi-line block to inline code style
      - Add text-overflow: ellipsis for long content
      - Ensure flex layout works for inline display
  - ADD: |
      - .event-item-inline styles (single row, flexbox, compact padding)
      - .inline-json or .json-condensed for inline JSON display
      - Responsive behavior for smaller screens (optional)
  - PRESERVE: |
      - Theme variable usage: var(--border-color), var(--bg-secondary), var(--text-primary)
      - Dark theme support: body.dark-theme overrides
      - Hover effects (if any)
  - GOTCHA: |
      - Must test in both light and dark themes
      - Long text must not break layout (use overflow, ellipsis)
      - Ensure adequate spacing between inline elements
  - VALIDATION: |
      - Toggle between light and dark themes
      - Verify new styles look good in both modes
      - Check with long pattern names and symbols
      - Verify no layout breaking

Task 4: TEST in browser manually
  - ACTION: "Start TickStockPL and TickStockAppV2 services"
  - ACTION: "Open http://localhost:5000/streaming in browser"
  - VERIFY: |
      - Pattern events display in single compact row
      - Indicator events display in single compact row
      - Timestamps abbreviated (time only, no date)
      - JSON content visible but condensed
      - More events visible in viewport (2-3x improvement)
      - Light theme looks good
      - Dark theme looks good
      - No JavaScript console errors
  - ACTION: "Monitor WebSocket events flowing in"
  - VERIFY: |
      - New patterns appear at top
      - New indicators appear at top
      - Counters update correctly
      - Stream limits work (50 patterns, 30 indicators)
```

### Change Patterns & Key Details

```javascript
// ═══════════════════════════════════════════════════════════════
// Pattern: Multi-row to Single-row Event Display Consolidation
// ═══════════════════════════════════════════════════════════════

// BEFORE: Multi-row expanded format
// File: web/static/js/services/streaming-dashboard.js (lines 501-548)
addPatternEvent(detection) {
    const stream = document.getElementById('patternStream');
    if (!stream) return;

    const eventItem = document.createElement('div');
    eventItem.className = 'event-item-expanded';  // ❌ Multi-row expanded

    const confidence = detection.confidence || 0;
    const confClass = confidence >= 0.8 ? 'confidence-high' :
                     confidence >= 0.5 ? 'confidence-medium' : 'confidence-low';

    const patternType = detection.pattern_type || detection.pattern || detection.pattern_name || 'Unknown';
    const rawContent = JSON.stringify(detection, null, 2);  // ❌ Multi-line formatted

    eventItem.innerHTML = `
        <div class="event-header">  <!-- ❌ Separate header row -->
            <div>
                <span class="pattern-badge">${patternType}</span>
                <strong class="ms-2">${detection.symbol || 'N/A'}</strong>
            </div>
            <div>
                <span class="${confClass}">${(confidence * 100).toFixed(1)}%</span>
                <small class="ms-2 text-muted">${new Date(detection.timestamp || Date.now()).toLocaleTimeString()}</small>
            </div>
        </div>
        <div class="redis-content">  <!-- ❌ Separate JSON row -->
            <strong>Raw Redis Content:</strong>
            <pre class="redis-json">${rawContent}</pre>
        </div>
    `;

    stream.insertBefore(eventItem, stream.firstChild);

    // Limit to 50 items
    while (stream.children.length > 50) {
        stream.removeChild(stream.lastChild);
    }

    const counter = document.getElementById('patternCount');
    if (counter) {
        counter.textContent = `${this.patternCount} patterns`;
    }
}

// AFTER: Single-row inline format
// File: web/static/js/services/streaming-dashboard.js (lines 501-548)
addPatternEvent(detection) {
    const stream = document.getElementById('patternStream');
    if (!stream) return;

    const eventItem = document.createElement('div');
    eventItem.className = 'event-item-inline';  // ✅ Single-row inline

    const confidence = detection.confidence || 0;
    const confClass = confidence >= 0.8 ? 'confidence-high' :
                     confidence >= 0.5 ? 'confidence-medium' : 'confidence-low';

    const patternType = detection.pattern_type || detection.pattern || detection.pattern_name || 'Unknown';

    // ✅ Abbreviated timestamp (time only)
    const timestamp = new Date(detection.timestamp || Date.now()).toLocaleTimeString();

    // ✅ Condensed JSON (single line, max 60 chars)
    const rawContent = JSON.stringify(detection);
    const condensedJson = rawContent.length > 60 ? rawContent.substring(0, 60) + '...' : rawContent;

    // ✅ Single row with inline JSON
    eventItem.innerHTML = `
        <span class="pattern-badge">${patternType}</span>
        <strong class="ms-2">${detection.symbol || 'N/A'}</strong>
        <span class="${confClass} ms-2">${(confidence * 100).toFixed(1)}%</span>
        <small class="text-muted ms-2">${timestamp}</small>
        <code class="inline-json ms-2">${condensedJson}</code>
    `;

    stream.insertBefore(eventItem, stream.firstChild);  // ✅ Preserved

    // ✅ Preserved: Limit to 50 items
    while (stream.children.length > 50) {
        stream.removeChild(stream.lastChild);
    }

    // ✅ Preserved: Counter update
    const counter = document.getElementById('patternCount');
    if (counter) {
        counter.textContent = `${this.patternCount} patterns`;
    }
}

// CHANGE RATIONALE:
// - Current: Multi-row format uses ~80-100px vertical space per event
// - New: Single-row format uses ~30-40px vertical space per event
// - Result: 2-3x more events visible in same viewport height
// - UX: Easier to scan recent event history without scrolling
// - Performance: Fewer DOM elements (6 → 3-4 per event)

// PRESERVED BEHAVIOR:
// - Function signature unchanged: addPatternEvent(detection)
// - Stream container unchanged: patternStream
// - Newest-first ordering preserved: insertBefore(stream.firstChild)
// - Stream limit preserved: 50 patterns max
// - Counter update preserved
// - Pattern type fallbacks preserved
// - All information displayed (just reorganized)

// GOTCHA:
// - Long pattern names: Use CSS text-overflow: ellipsis to prevent overflow
// - Large JSON: Truncate to reasonable length (60 chars) with "..." indicator
// - Theme support: Use var(--text-muted) for consistent theming
// - Timestamp format: toLocaleTimeString() is browser-locale-aware


// ═══════════════════════════════════════════════════════════════
// Pattern: CSS Styling for Inline Event Display
// ═══════════════════════════════════════════════════════════════

// BEFORE: Multi-row expanded event CSS
// File: web/static/js/services/streaming-dashboard.js (lines 218-259)
.event-item-expanded {
    padding: 15px;
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 5px;
    margin-bottom: 10px;
    background: var(--bg-secondary, #f8f9fa);
}

.event-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;         // ❌ Spacing for separate sections
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-color, #dee2e6);  // ❌ Visual separator
}

.redis-content {
    margin-top: 10px;  // ❌ Separate JSON section
}

.redis-json {
    background: #282c34;
    color: #abb2bf;
    border: 1px solid #3e4451;
    border-radius: 4px;
    padding: 12px;
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    max-height: 300px;
    overflow-y: auto;
    overflow-x: auto;
    white-space: pre;    // ❌ Multi-line formatting
    line-height: 1.4;
    margin: 0;
}

// AFTER: Single-row inline event CSS
// File: web/static/js/services/streaming-dashboard.js (lines 218-259)
.event-item-inline {
    padding: 8px 12px;  // ✅ Reduced padding for compact display
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 4px;
    margin-bottom: 5px;  // ✅ Reduced margin (10px → 5px)
    background: var(--bg-secondary, #f8f9fa);
    display: flex;       // ✅ Flexbox for inline layout
    align-items: center; // ✅ Vertical center alignment
    gap: 8px;           // ✅ Spacing between inline elements
    flex-wrap: wrap;    // ✅ Wrap on narrow screens
    transition: background 0.2s;
}

.event-item-inline:hover {
    background: var(--hover-bg, rgba(0,0,0,0.05));  // ✅ Hover effect preserved
}

.inline-json {
    font-family: 'Courier New', monospace;
    font-size: 0.75em;
    color: var(--text-muted, #6c757d);
    background: rgba(0,0,0,0.05);
    padding: 2px 6px;
    border-radius: 3px;
    white-space: nowrap;     // ✅ Single line (no wrap)
    overflow: hidden;        // ✅ Hide overflow
    text-overflow: ellipsis; // ✅ Show "..." for long JSON
    max-width: 300px;        // ✅ Limit width
    flex-shrink: 1;          // ✅ Allow shrinking in flexbox
}

/* ✅ Preserved: Dark theme support */
body.dark-theme .event-item-inline {
    background: var(--bg-secondary);
    border-color: var(--border-color);
}

body.dark-theme .inline-json {
    background: rgba(255,255,255,0.05);
    color: var(--text-muted);
}

// CHANGE RATIONALE:
// - Current: Vertical stacking with visual separators (border-bottom, margin-top)
// - New: Horizontal inline layout with flexbox
// - Result: Compact single-row display, responsive wrapping on small screens
// - Consistency: Uses same theme variables for light/dark mode support

// PRESERVED BEHAVIOR:
// - Theme variables: var(--border-color), var(--bg-secondary), var(--text-muted)
// - Dark theme support: body.dark-theme overrides
// - Hover effects: Slight background change on hover
// - Border radius: Consistent rounded corners

// GOTCHA:
// - flex-wrap: wrap ensures responsive behavior on narrow screens
// - text-overflow: ellipsis prevents layout breaking with long JSON
// - max-width: 300px on inline-json keeps it from dominating row
// - gap: 8px provides spacing without manual margins
```

### Integration Points (What Changes)

```yaml
DATABASE:
  schema_changes: No
  query_changes: "None - frontend display only"

REDIS_CHANNELS:
  message_format_changes: No
  channel_updates: "None - display only"

WEBSOCKET:
  event_changes: No
  event_updates: "None - event handling unchanged, only display modified"

TICKSTOCKPL_API:
  endpoint_changes: No
  api_updates: "None"
```

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# TickStock Standard: Ruff for linting and formatting
# JavaScript files not checked by Ruff (Python-only)

# No Python changes in this task
# Validation: Manual JavaScript syntax check in browser console
```

### Level 2: Unit Tests (Component Validation)

```bash
# No JavaScript unit tests exist for frontend services
# Validation: Manual browser testing

# Expected: No JavaScript console errors when loading streaming dashboard
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
# These tests validate WebSocket event flow, not specific DOM structure

python run_tests.py

# Expected Output:
# - All tests pass (no changes to backend or WebSocket handling)
# - ~30 second runtime
# - Tests do NOT validate DOM structure (no breakage expected)
```

### Level 4: TickStock-Specific Validation

```bash
# Manual Browser Testing (CRITICAL for UI changes)

# 1. Start services
python start_all_services.py
# Expected: TickStockPL and TickStockAppV2 running

# 2. Open Live Streaming page
# URL: http://localhost:5000/streaming
# Action: Click "Live Streaming" in sidebar

# 3. Verify pattern events
# Expected:
# - Pattern events display in single row
# - Pattern badge, symbol, confidence visible
# - Timestamp abbreviated (e.g., "2:45:30 PM", not full date)
# - JSON content visible inline (abbreviated if long)
# - New patterns appear at top
# - Pattern counter updates

# 4. Verify indicator events
# Expected:
# - Indicator events display in single row
# - Indicator badge, symbol, value visible
# - Timestamp abbreviated
# - JSON content visible inline
# - New indicators appear at top
# - Indicator counter updates

# 5. Test theme switching
# Action: Click theme toggle button (🌙/☀️ icon)
# Expected:
# - Light theme: event-item-inline background light, text dark
# - Dark theme: event-item-inline background dark, text light
# - Both themes display correctly
# - Smooth transition (0.3s)

# 6. Test with many events
# Expected:
# - More events visible in viewport (2-3x improvement over old format)
# - Scrolling works smoothly
# - Stream limits enforced (50 patterns, 30 indicators)
# - Oldest events removed when limit reached

# 7. Test with long content
# Expected:
# - Long pattern names use ellipsis (no overflow)
# - Long JSON truncated with "..." indicator
# - Layout does not break

# Performance Validation
# - Open DevTools Performance tab
# - Record event rendering
# - Expected: <10ms per event rendering time
# - No layout thrashing or excessive reflows

# WebSocket Delivery Validation
# - DevTools Network tab → WS connection
# - Measure time from server message to DOM update
# - Expected: <100ms (should be unchanged from before)
```

### Level 5: Regression Testing (MANDATORY for Changes)

```bash
# Regression Test: Existing Functionality Preserved

# Test 1: WebSocket event handling still works
# Action: Trigger pattern/indicator events from TickStockPL
# Expected: Events received and displayed (just in new format)

# Test 2: Counters still update
# Expected: Pattern count and indicator count increment correctly

# Test 3: Stream limits still enforced
# Expected: Max 50 patterns, max 30 indicators in DOM

# Test 4: Newest-first ordering preserved
# Expected: New events appear at top of list

# Test 5: Session status display unchanged
# Expected: Session indicator, session info, health status all work

# Test 6: Metrics display unchanged
# Expected: Active symbols, events/second, patterns/indicators metrics update

# Manual Regression Checklist:
# - [ ] Pattern events display correctly (new format)
# - [ ] Indicator events display correctly (new format)
# - [ ] Theme switching works (light and dark)
# - [ ] WebSocket connection stable
# - [ ] Counters update correctly
# - [ ] Stream limits enforced
# - [ ] No JavaScript console errors
# - [ ] Performance acceptable (<10ms rendering, <100ms WebSocket)

# Before/After Comparison:
# BEFORE metrics (baseline):
# - Events visible in 500px viewport: ~5-8
# - Vertical space per event: ~80-100px
# - DOM elements per event: ~6

# AFTER metrics (target):
# - Events visible in 500px viewport: ~15-20 (2-3x improvement)
# - Vertical space per event: ~30-40px (60% reduction)
# - DOM elements per event: ~3-4 (33% reduction)

# Acceptance Criteria:
# - At least 2x more events visible in viewport
# - All information still displayed (badge, symbol, confidence/value, timestamp, JSON)
# - No JavaScript errors
# - Both themes work correctly
# - Performance not degraded
```

## Final Validation Checklist

### Technical Validation

- [ ] Manual browser testing completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] No JavaScript console errors
- [ ] Pattern events display in single row
- [ ] Indicator events display in single row
- [ ] Timestamps abbreviated correctly

### Change Validation

- [ ] Success criteria met: 2-3x more events visible in viewport
- [ ] Current behavior documented (screenshots taken before change)
- [ ] New single-row format working as specified
- [ ] Performance target met: <10ms event rendering
- [ ] Backward compatibility: N/A (frontend display only, no API changes)

### Impact Validation

- [ ] All identified breakage points addressed (theme system tested)
- [ ] No unintended side effects (WebSocket handling unchanged)
- [ ] Long content handled gracefully (ellipsis for overflow)
- [ ] Both light and dark themes display correctly

### TickStock Architecture Validation

- [ ] Component role preserved: Consumer (UI/UX) - yes, frontend only
- [ ] Redis pub-sub patterns correct: N/A (no Redis changes)
- [ ] Database access mode followed: N/A (no database access)
- [ ] WebSocket latency target met: <100ms (unchanged)
- [ ] Performance targets achieved: <10ms rendering, 2-3x viewport efficiency
- [ ] No architectural violations detected

### Code Quality Validation

- [ ] Follows existing codebase patterns (template literals, DOM manipulation)
- [ ] File structure limits followed (streaming-dashboard.js stays under 1000 lines)
- [ ] Naming conventions preserved (camelCase for JavaScript)
- [ ] Anti-patterns avoided (no eval(), no inline event handlers)
- [ ] Code is self-documenting (clear variable names, comments where needed)
- [ ] No "Generated by Claude" comments

### Documentation & Deployment

- [ ] Migration guide created: N/A (no breaking changes, frontend only)
- [ ] Configuration changes documented: N/A (no config changes)
- [ ] Deprecation warnings added: N/A (no code deprecated)
- [ ] Sprint notes updated with change details

---

## Anti-Patterns to Avoid (Change-Specific)

### Modification Anti-Patterns

- ❌ **Don't change code without understanding current behavior**
  - ✅ Read current implementation thoroughly (lines 501-548, 592-635)
  - ✅ Document current multi-row display structure
  - Violation: "I'll just make it inline and see what happens"

- ❌ **Don't skip dependency analysis**
  - ✅ Verified only streaming-dashboard.js uses addPatternEvent/addIndicatorEvent
  - ✅ Confirmed no backend or database dependencies
  - Violation: "It's just CSS, nothing can break"

- ❌ **Don't ignore backward compatibility**
  - ✅ N/A for frontend-only changes (no API contracts)
  - ✅ Theme system preserved (var() CSS variables)
  - Violation: "Old themes don't matter"

- ❌ **Don't skip regression testing**
  - ✅ Test WebSocket event flow still works
  - ✅ Verify counters, limits, ordering preserved
  - Violation: "I only tested the new inline display"

- ❌ **Don't modify without baseline metrics**
  - ✅ Measure events visible in viewport before/after
  - ✅ Document vertical space per event before/after
  - Violation: "It looks better now" (without data)

### TickStock-Specific Change Anti-Patterns

- ❌ **Don't break theme system**
  - ✅ Use var(--css-variables) for all colors
  - ✅ Test both light and dark themes
  - Violation: Hardcoded colors (e.g., color: #333)

- ❌ **Don't degrade WebSocket performance**
  - ✅ Only display logic changed, event handling unchanged
  - ✅ Verify <100ms WebSocket delivery still met
  - Violation: Adding expensive JSON parsing in display code

- ❌ **Don't break responsive layout**
  - ✅ Use flex-wrap: wrap for small screens
  - ✅ Test with long pattern names and symbols
  - Violation: Fixed widths that overflow on mobile

- ❌ **Don't remove critical information**
  - ✅ All fields preserved: badge, symbol, confidence/value, timestamp, JSON
  - ✅ JSON abbreviated but still visible
  - Violation: Removing timestamp or JSON to save space

- ❌ **Don't forget browser compatibility**
  - ✅ Test in Chrome, Firefox, Edge (modern browsers)
  - ✅ Use standard CSS (no experimental features)
  - Violation: Using CSS features not widely supported
