name: "Change PRP Template v1 - Modification-Focused with Impact Analysis"
description: |

---

## Goal

**Change Type**: [enhancement | refactoring | bug_fix | deprecation | performance_optimization]

**Current Behavior**: [What the system does now - be specific]

**Desired Behavior**: [What the system should do after the change - be specific]

**Success Definition**: [How you'll know this change is complete and working correctly]

**Breaking Changes**: [Yes/No - If yes, list them and provide migration path]

## User Persona (if applicable)

**Target User**: [Specific user type affected by this change - developer, end user, admin, etc.]

**Current Pain Point**: [What's broken, slow, confusing, or limiting in current implementation]

**Expected Improvement**: [How this change improves their experience - faster, clearer, more reliable, etc.]

## Why This Change

- [Problem with current implementation - bugs, performance, maintainability, etc.]
- [Business value of making this change - user impact, system reliability, developer productivity]
- [Risks of NOT making this change - technical debt, cascading failures, user frustration]

## What Changes

[Detailed description of what will be modified in the system]

### Success Criteria

- [ ] [Specific measurable outcomes for the change]
- [ ] [Existing functionality continues to work (regression-free)]
- [ ] [Performance metrics maintained or improved]
- [ ] [All affected tests updated and passing]

## Current Implementation Analysis

### Files to Modify

```yaml
# List ALL files that will be changed with their current responsibility

- file: src/path/to/file1.py
  current_responsibility: "Current role and behavior of this file"
  lines_to_modify: "Approximate line ranges or function names"
  current_pattern: "Brief description of current implementation pattern"
  reason_for_change: "Why this file needs modification"

- file: src/path/to/file2.py
  current_responsibility: "Current role and behavior of this file"
  lines_to_modify: "Approximate line ranges or function names"
  current_pattern: "Brief description of current implementation pattern"
  reason_for_change: "Why this file needs modification"
```

### Current Code Patterns (What Exists Now)

```python
# CURRENT IMPLEMENTATION: What the code does NOW
# File: src/path/to/file.py (lines X-Y)

def current_function():
    # Current logic that will be MODIFIED or REPLACED
    # Document current behavior, parameters, return values
    # Note any known issues or limitations
    pass

# CURRENT DEPENDENCIES: What depends on this code
# - List functions/classes that call this code
# - List external systems that rely on current behavior
# - Note any database schema dependencies
```

### Dependency Analysis

```yaml
# What DEPENDS on the code being changed

upstream_dependencies:
  # Code that CALLS the functions/classes being modified
  - component: "src/path/to/caller.py"
    dependency: "Calls function_to_modify() in error handling path"
    impact: "Need to ensure error handling contract preserved"

  - component: "src/path/to/another_caller.py"
    dependency: "Uses ClassToModify for data transformation"
    impact: "Verify transformed data structure unchanged"

downstream_dependencies:
  # Code that is CALLED BY the functions/classes being modified
  - component: "src/path/to/service.py"
    dependency: "Provides data to function_to_modify()"
    impact: "May need parameter signature changes"

database_dependencies:
  # Database schema, tables, columns relied upon
  - table: "table_name"
    columns: ["col1", "col2"]
    impact: "Query modifications may be needed"
    migration_required: [Yes/No]

redis_dependencies:
  # Redis channels, keys, message formats
  - channel: "tickstock:domain:event"
    current_format: "{key1: value1, key2: value2}"
    impact: "Message format changes affect subscribers"

websocket_dependencies:
  # WebSocket event types, room patterns
  - event_type: "event_name"
    current_format: "{type: string, data: dict}"
    impact: "Frontend JavaScript expects this format"

external_api_dependencies:
  # External APIs, TickStockPL endpoints
  - api: "TickStockPL /api/v1/endpoint"
    current_contract: "Expects {param1, param2} in request"
    impact: "API contract changes affect TickStockPL"
```

### Test Coverage Analysis

```yaml
# Existing tests that cover code being modified

unit_tests:
  - test_file: "tests/unit/test_module.py"
    coverage: "Tests function_to_modify() happy path and error cases"
    needs_update: [Yes/No]
    update_reason: "Why test needs updating - new behavior, new edge cases, etc."

integration_tests:
  - test_file: "tests/integration/test_feature_flow.py"
    coverage: "End-to-end test for Redis → WebSocket flow"
    needs_update: [Yes/No]
    update_reason: "Why test needs updating"

missing_coverage:
  # Test gaps that should be filled during this change
  - scenario: "Edge case not currently tested"
    reason: "Why this matters now"
```

## Impact Analysis

### Potential Breakage Points

```yaml
# What could BREAK as a result of this change

high_risk:
  # Changes with high probability of breaking something
  - component: "WebSocket message delivery"
    risk: "Message format change could break frontend JavaScript"
    mitigation: "Add backward compatibility layer for 1 sprint"

  - component: "Database query performance"
    risk: "Query refactoring could degrade performance"
    mitigation: "Run EXPLAIN ANALYZE before/after, benchmark <50ms"

medium_risk:
  # Changes with moderate risk
  - component: "Error handling in service layer"
    risk: "New error types may not be caught by existing handlers"
    mitigation: "Audit all try-except blocks that call modified code"

low_risk:
  # Changes with low risk but worth noting
  - component: "Logging output format"
    risk: "Log parsing scripts may break"
    mitigation: "Verify log monitoring tools still work"
```

### Performance Impact

```yaml
# How this change affects system performance

expected_improvements:
  - metric: "WebSocket delivery latency"
    current: "120ms average"
    target: "<100ms average"
    measurement: "Browser DevTools Network tab, 100 message sample"

  - metric: "Database query time"
    current: "80ms average"
    target: "<50ms average"
    measurement: "EXPLAIN ANALYZE query before/after"

potential_regressions:
  - metric: "Redis operation latency"
    current: "5ms average"
    risk: "Could increase to 15ms with new logic"
    threshold: "<10ms acceptable, >10ms requires optimization"
    measurement: "Redis SLOWLOG, timing instrumentation"
```

### Backward Compatibility

```yaml
backward_compatibility:
  breaking_changes: [Yes/No]

  # If Yes, document migration path
  migration_required:
    - affected: "Frontend JavaScript code"
      change: "WebSocket message format updated"
      migration_path: |
        1. Deploy backend with backward compatibility layer
        2. Update frontend to handle new format
        3. Remove backward compatibility after 1 sprint

    - affected: "Database schema"
      change: "New column added to table_name"
      migration_path: |
        1. Run migration to add column (nullable initially)
        2. Backfill existing rows with default values
        3. Update code to populate new column
        4. Make column non-nullable in future migration

  # If No, explain why change is backward compatible
  compatibility_guarantee: |
    - All existing API contracts preserved
    - Database queries use SELECT with explicit columns (no schema changes)
    - Redis message formats unchanged (internal logic only)
    - WebSocket events maintain same structure
```

## All Needed Context

### Context Completeness Check

_Before writing this PRP, validate: "If someone knew nothing about this codebase OR the current implementation, would they have everything needed to make this change successfully without breaking anything?"_

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: [TickStockAppV2 | TickStockPL]
  role: [Consumer | Producer]

  redis_channels:
    # List all channels affected by this change
    - channel: "tickstock:patterns:streaming"
      change_type: [subscriber | publisher | message_format | none]
      current_behavior: "Current usage pattern"
      new_behavior: "How usage changes"

  database_access:
    mode: [read-only | read-write]
    tables_affected: [List tables modified by this change]
    queries_modified: [Describe query changes]
    schema_changes: [Yes/No - if yes, list in migration section]

  websocket_integration:
    affected: [Yes/No]
    broadcast_changes: [Describe changes to WebSocket broadcast logic]
    message_format_changes: [Describe changes to message structure]

  tickstockpl_api:
    affected: [Yes/No]
    endpoint_changes: [List any API contract changes]

  performance_targets:
    - metric: "Symbol processing"
      current: "Xms per symbol"
      target: "<1ms per symbol"

    - metric: "WebSocket delivery"
      current: "Xms end-to-end"
      target: "<100ms end-to-end"
```

### Documentation & References

```yaml
# MUST READ - Include these in your context window

# Current implementation references (CRITICAL for modifications)
- file: [exact/path/to/current/implementation.py]
  why: "Current logic that will be modified - MUST understand before changing"
  lines: [X-Y - specific line ranges to read]
  pattern: "Current implementation pattern to preserve or replace"
  gotcha: "Known issues, edge cases, workarounds in current code"

# Similar working features (for pattern consistency)
- file: [path/to/similar/feature.py]
  why: "Similar change was made here - follow this pattern"
  pattern: "Refactoring approach, error handling, testing strategy"
  gotcha: "Lessons learned from similar change"

# External documentation
- url: [Complete URL with section anchor]
  why: [Specific library methods/patterns needed for new implementation]
  critical: [Key insights that prevent common refactoring errors]

# TickStock-Specific References
- file: src/services/redis_event_subscriber.py
  why: "Pattern for Redis event handling (if modifying Redis code)"
  pattern: "Event parsing, error handling, message validation"
  gotcha: "Always convert typed events to dicts at Worker boundary"

- file: src/services/websocket_service.py
  why: "WebSocket broadcast patterns (if modifying WebSocket code)"
  pattern: "Room management, message formatting, error handling"
  gotcha: "Use emit() with broadcast=True for multi-client updates"

- file: tests/integration/run_integration_tests.py
  why: "Integration test structure (for updating affected tests)"
  pattern: "Test setup, mocking, assertions"
  gotcha: "Tests must complete in ~30 seconds"
```

### Current Codebase tree (files being modified)

```bash
# List directory structure of areas being changed
# Use `tree src/path/to/module` for specific modules

src/
├── module_being_modified/
│   ├── file1.py          # MODIFY: Current behavior X → New behavior Y
│   ├── file2.py          # MODIFY: Refactor function Z for performance
│   └── __init__.py       # PRESERVE: No changes
└── tests/
    ├── unit/
    │   └── test_module.py    # UPDATE: Modify assertions for new behavior
    └── integration/
        └── test_flow.py      # UPDATE: Add regression test for old behavior
```

### Known Gotchas of Current Code & Library Quirks

```python
# CRITICAL: Document existing gotchas that must be preserved or addressed

# Current Code Gotchas
# CRITICAL: [Describe tricky parts of current implementation]
# Example: Function X has undocumented side effect on global state
# Example: Class Y assumes input is always sorted (not validated)
# Example: Error handling swallows exceptions in edge case Z

# TickStock-Specific Gotchas (from prp-new.md)
# CRITICAL: Never mix typed events and dicts after Worker boundary
# CRITICAL: TickStockAppV2 is CONSUMER ONLY (no pattern detection logic)
# CRITICAL: Flask Application Context - use current_app, not module globals

# Library-Specific Quirks
# CRITICAL: [Library name] requires [specific pattern for modifications]
# Example: SQLAlchemy session must be closed in finally block
# Example: Redis pub-sub reconnect logic needed after connection loss
```

## Change Implementation Blueprint

### Pre-Change Preparation

```yaml
# Steps to take BEFORE modifying code

1_backup_current_state:
  - action: "Create git branch"
    command: "git checkout -b change/{feature-name}"

  - action: "Document current behavior"
    command: "Run affected features and capture output/screenshots"

  - action: "Run baseline tests"
    command: "python run_tests.py  # Verify all tests pass BEFORE changes"

2_analyze_dependencies:
  - action: "Find all callers of modified functions"
    command: "rg 'function_to_modify' src/ tests/"

  - action: "Identify database dependencies"
    command: "rg 'table_name' src/"

  - action: "Check Redis channel usage"
    command: "rg 'channel_pattern' src/"

3_create_regression_tests:
  - action: "Document current behavior in tests BEFORE changing code"
    why: "Ensures we don't accidentally break existing functionality"
    location: "tests/integration/test_{feature}_regression.py"
```

### Change Tasks (ordered by dependencies)

```yaml
# MODIFY verb instead of CREATE (since changing existing code)

Task 1: MODIFY src/path/to/primary_file.py
  - CURRENT: [Current implementation pattern - lines X-Y]
  - CHANGE: [What to modify and why]
  - PRESERVE: [What must stay the same - error handling, API contracts, etc.]
  - GOTCHA: [Known issues to avoid - edge cases, side effects]
  - VALIDATION: [How to verify change works - unit test to run]

Task 2: UPDATE src/path/to/dependent_file.py
  - CURRENT: [Current usage of code from Task 1]
  - CHANGE: [Updates needed due to Task 1 changes]
  - PRESERVE: [Behavior that must remain unchanged]
  - DEPENDENCIES: [Must complete Task 1 first]
  - VALIDATION: [How to verify compatibility]

Task 3: REFACTOR src/path/to/service_file.py (if extracting logic)
  - CURRENT: [Current coupled implementation]
  - EXTRACT: [Logic to extract into separate function/class]
  - NEW_STRUCTURE: [How code will be organized after refactoring]
  - PRESERVE: [Public interface unchanged]
  - VALIDATION: [Existing callers still work]

Task 4: UPDATE tests/unit/test_module.py
  - CURRENT: [Current test assertions]
  - MODIFY: [Test updates for new behavior]
  - ADD: [New tests for edge cases]
  - PRESERVE: [Tests for unchanged functionality]
  - ENSURE: [All tests pass - both old and new]

Task 5: UPDATE tests/integration/test_flow.py
  - ADD: [Regression test for old behavior if needed]
  - MODIFY: [Integration test for new behavior]
  - VERIFY: [End-to-end flow still works]

Task 6: UPDATE documentation/config (if needed)
  - MODIFY: [.env variables if defaults change]
  - UPDATE: [Code comments if API contracts change]
  - PRESERVE: [Existing configuration compatibility]
```

### Change Patterns & Key Details

```python
# MODIFICATION PATTERN: Show BEFORE and AFTER code

# ═══════════════════════════════════════════════════════════════
# Pattern 1: Refactoring for Performance
# ═══════════════════════════════════════════════════════════════

# BEFORE: Current implementation (slow)
# File: src/services/data_processor.py (lines 50-75)
def process_symbols(symbols: list[str]) -> dict:
    """Current: Processes symbols one-by-one in loop (slow)."""
    results = {}
    for symbol in symbols:
        conn = get_connection()  # ❌ Connection per symbol (slow)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM table WHERE symbol = %s", (symbol,))
        results[symbol] = cursor.fetchone()
        conn.close()
    return results

# AFTER: New implementation (fast)
# File: src/services/data_processor.py (lines 50-75)
def process_symbols(symbols: list[str]) -> dict:
    """New: Batch query with single connection (fast)."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # ✅ Single query with IN clause (fast)
        placeholders = ','.join(['%s'] * len(symbols))
        cursor.execute(f"SELECT * FROM table WHERE symbol IN ({placeholders})", symbols)
        rows = cursor.fetchall()
        return {row['symbol']: row for row in rows}
    finally:
        if conn:
            conn.close()

# CHANGE RATIONALE:
# - Current: N database connections for N symbols = N * connection_overhead
# - New: 1 database connection for N symbols = 1 * connection_overhead
# - Performance: 100 symbols: 500ms → 45ms (11x faster)

# PRESERVED BEHAVIOR:
# - Return type unchanged: dict[str, Any]
# - Error handling preserved: connection cleanup in finally
# - API contract unchanged: same parameters, same return structure

# GOTCHA:
# - Must handle empty symbols list (returns empty dict)
# - Must use RealDictCursor for dict-based results
# - IN clause has max 1000 items - chunk if needed


# ═══════════════════════════════════════════════════════════════
# Pattern 2: Enhancing Error Handling
# ═══════════════════════════════════════════════════════════════

# BEFORE: Current implementation (swallows errors)
# File: src/services/redis_subscriber.py (lines 120-130)
def handle_message(self, message: dict):
    """Current: Swallows all errors (bad)."""
    try:
        data = json.loads(message['data'])
        self.process_event(data)
    except Exception as e:
        pass  # ❌ Silently swallows errors (debugging nightmare)

# AFTER: New implementation (proper error handling)
# File: src/services/redis_subscriber.py (lines 120-140)
def handle_message(self, message: dict):
    """New: Specific error handling with logging."""
    try:
        data = json.loads(message['data'])
        self.process_event(data)
    except json.JSONDecodeError as e:
        # ✅ Specific error handling for JSON parsing
        self.logger.error(f"Invalid JSON in Redis message: {e}")
        self.logger.debug(f"Raw message: {message['data']}")
    except KeyError as e:
        # ✅ Specific error handling for missing keys
        self.logger.error(f"Missing required key in message: {e}")
        self.logger.debug(f"Message data: {data}")
    except Exception as e:
        # ✅ Catch-all with full context
        self.logger.error(f"Unexpected error processing message: {e}")
        self.logger.exception("Full traceback:")
        raise  # ✅ Re-raise unexpected errors for visibility

# CHANGE RATIONALE:
# - Current: Silent failures make debugging impossible
# - New: Specific error types with context enable quick debugging
# - Observability: Logs show exactly what went wrong and where

# PRESERVED BEHAVIOR:
# - Function signature unchanged
# - Successful message processing unchanged
# - Performance unchanged (error cases only)

# GOTCHA:
# - Must re-raise unexpected errors (don't silently fail)
# - Log levels matter: error for problems, debug for context
# - Avoid logging sensitive data (PII, credentials)


# ═══════════════════════════════════════════════════════════════
# Pattern 3: Adding Feature to Existing Function
# ═══════════════════════════════════════════════════════════════

# BEFORE: Current implementation
# File: src/api/routes.py (lines 45-60)
@app.route('/api/patterns/<symbol>')
@login_required
def get_patterns(symbol: str):
    """Current: Returns all patterns for symbol."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM daily_patterns WHERE symbol = %s ORDER BY detected_at DESC",
        (symbol,)
    )
    patterns = cursor.fetchall()
    conn.close()
    return jsonify({"patterns": patterns})

# AFTER: New implementation (with filtering)
# File: src/api/routes.py (lines 45-75)
@app.route('/api/patterns/<symbol>')
@login_required
def get_patterns(symbol: str):
    """New: Returns patterns with optional timeframe filtering."""
    # ✅ NEW: Optional timeframe filter from query params
    timeframe = request.args.get('timeframe')  # Added parameter

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # ✅ NEW: Dynamic query based on filter
        if timeframe:
            query = """
                SELECT * FROM daily_patterns
                WHERE symbol = %s AND timeframe = %s
                ORDER BY detected_at DESC
            """
            cursor.execute(query, (symbol, timeframe))
        else:
            # ✅ PRESERVED: Original query for backward compatibility
            query = """
                SELECT * FROM daily_patterns
                WHERE symbol = %s
                ORDER BY detected_at DESC
            """
            cursor.execute(query, (symbol,))

        patterns = cursor.fetchall()
        return jsonify({"patterns": patterns})

    finally:
        if conn:
            conn.close()

# CHANGE RATIONALE:
# - Current: Returns all patterns (slow for symbols with many patterns)
# - New: Optional filtering reduces payload size and response time
# - Backward compatible: No filter = same behavior as before

# PRESERVED BEHAVIOR:
# - URL route unchanged: /api/patterns/<symbol>
# - Response format unchanged: {"patterns": [...]}
# - Default behavior unchanged: No timeframe param = all patterns

# GOTCHA:
# - Must validate timeframe values (prevent SQL injection)
# - Frontend code works without changes (optional parameter)
# - Add index on (symbol, timeframe) for performance


# ═══════════════════════════════════════════════════════════════
# Pattern 4: Deprecating Old Code Path
# ═══════════════════════════════════════════════════════════════

# BEFORE: Current implementation (deprecated pattern)
# File: src/services/legacy_service.py (lines 100-150)
def legacy_process_data(data: dict) -> dict:
    """Current: Old synchronous processing (deprecated)."""
    # Old logic using deprecated library
    result = old_library.process(data)
    return result

# AFTER: New implementation (with deprecation warning)
# File: src/services/legacy_service.py (lines 100-170)
import warnings

def legacy_process_data(data: dict) -> dict:
    """
    DEPRECATED: Use new_process_data() instead.

    This function will be removed in Sprint 46.
    Migration guide: See docs/planning/sprints/sprint44/migration_guide.md
    """
    # ✅ Deprecation warning for developers
    warnings.warn(
        "legacy_process_data() is deprecated and will be removed in Sprint 46. "
        "Use new_process_data() instead.",
        DeprecationWarning,
        stacklevel=2
    )

    # ✅ Log usage for monitoring
    logger.warning(
        "legacy_process_data() called - migrate to new_process_data()",
        extra={"caller": inspect.stack()[1].function}
    )

    # ✅ PRESERVED: Original logic still works
    result = old_library.process(data)
    return result

# NEW: Replacement function
def new_process_data(data: dict) -> dict:
    """New: Modern async processing with better error handling."""
    # New logic using modern library
    result = new_library.process(data)
    return result

# CHANGE RATIONALE:
# - Current: Old library has performance issues, no longer maintained
# - New: Modern library is 3x faster, actively maintained
# - Deprecation: Gives developers time to migrate (1 sprint)

# PRESERVED BEHAVIOR:
# - Old function still works (no immediate breakage)
# - Return type unchanged
# - API contract preserved during deprecation period

# MIGRATION PATH:
# 1. Sprint 44: Add new_process_data(), deprecate legacy_process_data()
# 2. Sprint 45: Update all callers to use new_process_data()
# 3. Sprint 46: Remove legacy_process_data() entirely

# GOTCHA:
# - Must update all callers before removal sprint
# - Monitor logs to find usage of deprecated function
# - Document migration in sprint notes
```

### Integration Points (What Changes)

```yaml
# TickStock-Specific Integration Points Affected by Change

DATABASE:
  schema_changes: [Yes/No]

  # If schema changes needed
  migration:
    - file: "src/infrastructure/database/migrations/migration_045_{description}.sql"
    - content: |
        -- UP: Apply changes
        ALTER TABLE table_name MODIFY COLUMN col_name NEW_TYPE;
        CREATE INDEX idx_new ON table_name(col_name);

        -- DOWN: Rollback changes
        DROP INDEX IF EXISTS idx_new;
        ALTER TABLE table_name MODIFY COLUMN col_name OLD_TYPE;
    - validation: "Test on local DB, verify migration up/down works"

  query_changes:
    - location: "src/services/data_service.py"
    - before: "SELECT * FROM table WHERE old_condition"
    - after: "SELECT col1, col2 FROM table WHERE new_condition"
    - performance_impact: "EXPLAIN ANALYZE shows 50ms → 20ms improvement"

REDIS_CHANNELS:
  message_format_changes: [Yes/No]

  # If message format changes
  channel_updates:
    - channel: "tickstock:patterns:streaming"
    - current_format: "{pattern_name, symbol, timeframe, confidence}"
    - new_format: "{pattern_name, symbol, timeframe, confidence, metadata}"
    - backward_compatible: [Yes/No]
    - migration: |
        Phase 1: Add 'metadata' field (optional, default={})
        Phase 2: Update all publishers to include metadata
        Phase 3: Make metadata required after 1 sprint

WEBSOCKET:
  event_changes: [Yes/No]

  # If WebSocket events change
  event_updates:
    - event_type: "pattern_detected"
    - current_format: "{type: string, data: {pattern, symbol}}"
    - new_format: "{type: string, data: {pattern, symbol, metadata}}"
    - frontend_impact: "JavaScript must handle optional metadata field"
    - backward_compatible: [Yes/No]

TICKSTOCKPL_API:
  endpoint_changes: [Yes/No]

  # If TickStockPL API affected
  api_updates:
    - endpoint: "http://localhost:8080/api/v1/jobs"
    - current_contract: "{job_type, symbols[]}"
    - new_contract: "{job_type, symbols[], options{}}"
    - breaking: [Yes/No]
    - coordination: "Requires TickStockPL update in same sprint"
```

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# TickStock Standard: Ruff for linting and formatting
# Run after EACH file modification

# Modified files only
ruff check src/{modified_files} --fix
ruff format src/{modified_files}

# Full project validation
ruff check src/ --fix
ruff format src/

# Expected: Zero errors (same as before changes)
```

### Level 2: Unit Tests (Component Validation)

```bash
# TickStock Standard: pytest for all testing
# Test MODIFIED components specifically

# Test modified modules
python -m pytest tests/unit/test_{modified_module}.py -v

# Full unit test suite
python -m pytest tests/unit/ -v

# Expected: All tests pass (including UPDATED tests)
# If new failures: Either fix implementation OR update tests if behavior intentionally changed
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
# CRITICAL: Must run before ANY commit

python run_tests.py

# Expected Output:
# - All existing tests still pass (regression-free)
# - New/updated tests pass
# - ~30 second runtime
# - No new errors introduced

# Regression validation
# CRITICAL: Verify old functionality still works
python tests/integration/test_{feature}_regression.py -v

# Expected: Pre-change behavior preserved where intended
```

### Level 4: TickStock-Specific Validation

```bash
# Performance Validation
# CRITICAL: Verify performance NOT degraded

# If database queries modified
# BEFORE change: Run query and record time
# AFTER change: Run query and verify ≤ previous time

psql -U app_readwrite -d tickstock -c "EXPLAIN ANALYZE SELECT ..."

# Target: <50ms (no regression)

# If Redis operations modified
# Monitor Redis latency before/after change
redis-cli --latency

# Target: <10ms (no regression)

# If WebSocket delivery modified
# Test in browser DevTools Network tab
# Measure time from Redis event to browser display

# Target: <100ms (no regression)

# Backward Compatibility Validation
# CRITICAL: Verify no breaking changes for consumers

# Test old API contracts still work
curl -X GET http://localhost:5000/api/endpoint?old_param=value

# Expected: Same response format as before change

# Test new functionality
curl -X GET http://localhost:5000/api/endpoint?new_param=value

# Expected: New behavior works correctly

# Architecture Compliance Validation
# Run architecture-validation-specialist agent
# CRITICAL: Verify no role violations introduced

# Expected: Consumer/Producer boundaries preserved
```

### Level 5: Regression Testing (MANDATORY for Changes)

```bash
# Regression Test Suite
# CRITICAL: Ensure existing functionality unchanged

# Test scenarios that should NOT have changed
python tests/integration/test_existing_workflows.py -v

# Test edge cases that might be affected
python tests/unit/test_edge_cases.py -v

# Manual regression checklist
# - [ ] Feature X still works (unchanged component)
# - [ ] Feature Y still works (dependent component)
# - [ ] Error handling still works (unchanged paths)
# - [ ] Performance not degraded (metrics comparison)

# Before/After Comparison
# Document baseline metrics BEFORE change
# - Response times
# - Error rates
# - Resource usage

# Measure same metrics AFTER change
# Expected: No significant regressions

# Acceptance criteria:
# - All pre-existing tests pass
# - No new errors in logs
# - Performance metrics within acceptable range
# - Dependent features unaffected
```

## Final Validation Checklist

### Technical Validation

- [ ] All 5 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] Regression tests pass: All existing functionality preserved
- [ ] No linting errors: `ruff check src/`
- [ ] No formatting issues: `ruff format src/ --check`
- [ ] Unit tests pass (including updated tests)

### Change Validation

- [ ] All success criteria from "What Changes" section met
- [ ] Current behavior documented in tests (regression baseline)
- [ ] New behavior working as specified
- [ ] Performance targets met or improved (no regressions)
- [ ] Backward compatibility preserved (or migration path provided)

### Impact Validation

- [ ] All identified breakage points addressed
- [ ] Dependency analysis complete (upstream/downstream verified)
- [ ] Affected tests updated and passing
- [ ] Integration points tested (database, Redis, WebSocket, etc.)
- [ ] No unintended side effects observed

### TickStock Architecture Validation

- [ ] Component role preserved (Consumer vs Producer)
- [ ] Redis pub-sub patterns correct (if affected)
- [ ] Database access mode followed (read-only where applicable)
- [ ] WebSocket latency target met (<100ms if affected)
- [ ] Performance targets achieved (see performance impact section)
- [ ] No architectural violations detected

### Code Quality Validation

- [ ] Follows existing codebase patterns
- [ ] File structure limits followed (max 500 lines/file, 50 lines/function)
- [ ] Naming conventions preserved
- [ ] Anti-patterns avoided
- [ ] Code is self-documenting
- [ ] No "Generated by Claude" comments

### Documentation & Deployment

- [ ] Migration guide created (if breaking changes)
- [ ] Configuration changes documented (if new env vars)
- [ ] Deprecation warnings added (if deprecating code)
- [ ] Sprint notes updated with change details

---

## Anti-Patterns to Avoid (Change-Specific)

### Modification Anti-Patterns

- ❌ **Don't change code without understanding current behavior**
  - Read current implementation thoroughly
  - Document current behavior in tests FIRST
  - Violation: "I'll just change this and see what breaks"

- ❌ **Don't skip dependency analysis**
  - Find all callers before modifying function signatures
  - Check database schema dependencies
  - Violation: "Nobody else uses this function" (without verification)

- ❌ **Don't ignore backward compatibility**
  - Provide migration path for breaking changes
  - Add deprecation warnings before removal
  - Violation: "Just update all the callers at once"

- ❌ **Don't skip regression testing**
  - Test that old functionality still works
  - Verify dependent features unaffected
  - Violation: "I only tested the new behavior"

- ❌ **Don't modify without baseline metrics**
  - Measure performance BEFORE and AFTER
  - Document current behavior before changing
  - Violation: "I think it's faster now" (without data)

### TickStock-Specific Change Anti-Patterns

- ❌ **Don't break Redis message contracts**
  - Ensure message format changes are backward compatible
  - Coordinate with TickStockPL if changing shared events
  - Violation: Changing event structure without backward compatibility layer

- ❌ **Don't degrade performance during refactoring**
  - Benchmark before/after
  - Verify targets still met (<1ms, <10ms, <50ms, <100ms)
  - Violation: "Cleaner code" that's 10x slower

- ❌ **Don't change database queries without EXPLAIN ANALYZE**
  - Verify query performance before/after
  - Ensure indexes are used
  - Violation: "Simpler query" that does table scan

- ❌ **Don't modify WebSocket events without frontend coordination**
  - JavaScript expects specific message format
  - Breaking changes require frontend updates
  - Violation: Changing event structure without updating frontend

- ❌ **Don't remove code without checking for hidden callers**
  - Search entire codebase for usage
  - Check for dynamic imports, eval(), reflection
  - Violation: "No results in my IDE search" (incomplete search)
