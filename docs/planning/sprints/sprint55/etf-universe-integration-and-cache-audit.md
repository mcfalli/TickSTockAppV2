name: "Sprint 55 CHANGE PRP - ETF Universe Integration & Cache Entries Audit"
description: |
  Enhance Historical Data admin page with ETF universe bulk loading and clean up cache_entries table data quality issues.

---

## Goal

**Change Type**: enhancement

**Current Behavior**:
- Historical Data admin page (`/admin/historical-data`) supports:
  - Single symbol loading via manual input
  - CSV file universe loading (dow_30.csv, nasdaq_100.csv, sp_500.csv, curated-etfs.csv, russell_3000_part*.csv)
  - Bulk operations for S&P 500, NASDAQ 100, ETFs (hardcoded triggers)
- Cache_entries table contains 290 entries with 21 ETF universe definitions
- ETF universes created on Nov 25, 2025: `etf_core` (3), `etf_sector` (21), `etf_equal_weight_sectors` (12), `stock_etf_group` (36)
- NO dedicated UI for selecting and loading ETF universes by name
- Data quality issues: missing updated_at timestamps, naming inconsistencies, asymmetric entry pairs

**Desired Behavior**:
- Historical Data admin page includes:
  - **NEW**: ETF Universe Selector dropdown showing available ETF groups from cache_entries
  - **NEW**: Symbol count preview before bulk load trigger
  - **NEW**: Bulk universe load endpoint that processes all symbols in selected ETF group
  - **NEW**: Per-symbol progress tracking for universe loads
  - **PRESERVED**: All existing functionality (single symbol, CSV, bulk operations)
- Cache_entries table has:
  - All entries with valid updated_at timestamps
  - Consistent Title Case naming convention
  - Complete metadata for all active universes
  - Documented audit trail of cleanup actions

**Success Definition**:
1. Users can select ETF universes from dropdown (e.g., "Core ETFs (3)", "Sector ETFs (21)")
2. Users can trigger bulk load for entire universe with one click
3. Progress tracking shows N/Total symbols loaded with individual failures reported
4. Existing single-symbol and CSV load functionality continues working unchanged
5. Cache_entries table has zero data quality issues (missing timestamps, naming inconsistencies)
6. All 4 new ETF universes (created Nov 25) are fully integrated and loadable

**Breaking Changes**: No

## User Persona

**Target User**: TickStock Admin / Data Operations Team

**Current Pain Point**:
- To load all symbols in an ETF universe (e.g., 21 Sector ETFs), admin must:
  - Open database and query cache_entries for symbols
  - Copy symbol list manually
  - Paste into CSV file
  - Upload CSV file to Historical Data page
  - Trigger load
- This is **time-consuming** (5-10 minutes per universe) and **error-prone** (copy/paste mistakes)

**Expected Improvement**:
- Click dropdown → Select "Sector ETFs (21)" → Click "Load Universe" → Done (30 seconds)
- Progress tracking shows real-time status per symbol
- Failed symbols reported individually for quick debugging
- ETF universe updates automatically reflected in dropdown (no manual file maintenance)

## Why This Change

**Problems with Current Implementation**:
- **Manual Process**: Loading ETF universes requires database access + CSV file creation (admin friction)
- **No Discovery**: Users can't see available ETF universes without querying database directly
- **Brittle**: CSV files require manual updates when ETF lists change (maintenance burden)
- **Data Quality**: Cache_entries has incomplete metadata (missing timestamps, naming inconsistencies)
- **No Validation**: No automated validation of universe data integrity

**Business Value**:
- **Time Savings**: Reduce ETF universe loading from 5-10 minutes to <30 seconds (90%+ reduction)
- **Reduced Errors**: Eliminate copy/paste mistakes in manual symbol list creation
- **Improved Discovery**: Users can browse available universes and symbol counts before loading
- **Better Monitoring**: Per-symbol progress tracking enables quick identification of problematic symbols
- **Data Quality**: Clean cache_entries enables reliable universe management and future automation

**Risks of NOT Making This Change**:
- **Technical Debt**: Incomplete metadata in cache_entries will cause issues as universe count grows (currently 21 ETF + 36 stock universes)
- **Scaling**: Manual CSV workflow doesn't scale beyond ~10 universes (already have 57 total)
- **User Frustration**: Admins waste time on manual data wrangling instead of analysis
- **Data Drift**: Manual processes lead to stale CSV files not matching database reality

## What Changes

### Task 1: ETF Universe Integration to Historical Data Page

**Enhancement**: Add ETF universe selection UI with bulk loading capability

**New Features**:
1. Dropdown selector populated from cache_entries (etf_universe + stock_etf_combo types)
2. Symbol count preview (e.g., "This will load 21 symbols")
3. Bulk load endpoint that processes all symbols in universe
4. Real-time progress tracking (N/Total completed)
5. Individual failure reporting with error messages

**Technical Changes**:
- Add 2 new API endpoints to `admin_historical_data_redis.py`
- Update `historical_data_dashboard_redis.html` template with new UI section
- Extend `historical_data.js` with universe selection and bulk load logic
- NO changes to existing endpoints or database schema

### Task 2: Cache Entries Audit and Cleanup

**Data Quality**: Fix incomplete metadata and standardize naming

**Cleanup Actions**:
1. Set updated_at = created_at for 3 entries with NULL timestamps (IDs 1335, 1337, 1338)
2. Rename "complete" to "Complete" for Title Case consistency
3. Document whether detailed ETF entries needed for etf_core, etf_sector, etf_equal_weight_sectors
4. Create audit report documenting all changes
5. Create maintenance procedures for future universe additions

### Success Criteria

**Task 1 (ETF Universe Integration)**:
- [ ] Dropdown displays all ETF + stock_etf_combo universes from cache_entries
- [ ] Symbol count shown for each universe (e.g., "(21 symbols)")
- [ ] "Load Universe" button triggers bulk load for all symbols
- [ ] Progress indicator shows N/Total symbols processed
- [ ] Failed symbols displayed individually with error messages
- [ ] Existing single-symbol/CSV functionality unchanged and passing tests
- [ ] Universe loads tracked in job history with status

**Task 2 (Cache Entries Audit)**:
- [ ] All cache_entries have non-NULL updated_at timestamps
- [ ] All names follow Title Case convention
- [ ] Zero duplicate entries (already confirmed via research)
- [ ] Audit report documents all changes made
- [ ] Maintenance procedures created for future universe updates
- [ ] All 4 new ETF universes (Nov 25) verified loadable

## Current Implementation Analysis

### Files to Modify

```yaml
# Task 1: ETF Universe Integration

- file: src/api/rest/admin_historical_data_redis.py
  current_responsibility: "Historical data admin routes (Redis-based job submission)"
  lines_to_modify: "Add 2 new endpoints after line 680"
  current_pattern: "Flask blueprint routes returning JSON or rendering templates"
  reason_for_change: "Add endpoints for universe listing and bulk universe load submission"

- file: web/templates/admin/historical_data_dashboard_redis.html
  current_responsibility: "Historical data admin dashboard template (active version)"
  lines_to_modify: "Add new UI section around line 350 (after CSV loading section)"
  current_pattern: "Jinja2 template with Bootstrap forms and JavaScript integration"
  reason_for_change: "Add ETF universe selector dropdown and bulk load UI"

- file: web/static/js/admin/historical_data.js
  current_responsibility: "Frontend JavaScript for historical data page interactions"
  lines_to_modify: "Add new methods after line 485"
  current_pattern: "HistoricalDataManager class with AJAX polling and progress tracking"
  reason_for_change: "Add universe selection handler and bulk load submission logic"

# Task 2: Cache Entries Audit

- file: scripts/sql/cache_entries_cleanup_sprint55.sql
  current_responsibility: "DOES NOT EXIST - will create new file"
  lines_to_modify: "N/A (new file)"
  current_pattern: "N/A"
  reason_for_change: "SQL cleanup script for cache_entries data quality fixes"

- file: docs/database/cache_entries_audit_report_sprint55.md
  current_responsibility: "DOES NOT EXIST - will create new file"
  lines_to_modify: "N/A (new file)"
  current_pattern: "N/A"
  reason_for_change: "Document audit findings and cleanup actions"

- file: docs/database/cache_entries_maintenance.md
  current_responsibility: "DOES NOT EXIST - will create new file"
  lines_to_modify: "N/A (new file)"
  current_pattern: "N/A"
  reason_for_change: "Procedures for adding/updating cache_entries in future"
```

### Current Code Patterns (What Exists Now)

```python
# ═══════════════════════════════════════════════════════════════
# CURRENT IMPLEMENTATION: admin_historical_data_redis.py
# File: src/api/rest/admin_historical_data_redis.py (lines 45-112)
# ═══════════════════════════════════════════════════════════════

@admin_bp.route('/admin/historical-data')
@login_required
def admin_historical_dashboard():
    """
    CURRENT: Renders historical data dashboard

    Provides:
    - Hardcoded symbol list: ['AAPL', 'MSFT', 'GOOGL', ...]
    - Hardcoded universes: {'SP500': 'S&P 500 Components', 'NASDAQ100': ...}
    - Job statistics from Redis
    """
    # CURRENT: Hardcoded symbols (line 74)
    available_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
                         'META', 'NVDA', 'SPY', 'QQQ', 'DIA']

    # CURRENT: Hardcoded universes (lines 77-82)
    available_universes = {
        'SP500': 'S&P 500 Components',
        'NASDAQ100': 'NASDAQ 100 Components',
        'ETF': 'Major ETFs',
        'CUSTOM': 'Custom Symbol List'
    }

    # CURRENT: Get job stats from Redis
    job_stats = get_recent_jobs_from_redis(redis_client, limit=10)

    return render_template(
        'admin/historical_data_dashboard_redis.html',
        available_symbols=available_symbols,
        available_universes=available_universes,  # ← MODIFY: Replace with DB query
        job_stats=job_stats
    )


# CURRENT: Bulk operations endpoint (lines 374-433)
@admin_bp.route('/admin/historical-data/bulk-operations', methods=['POST'])
@login_required
def admin_bulk_operations():
    """
    CURRENT: Hardcoded bulk operations

    Triggers:
    - SP500 load
    - NASDAQ100 load
    - ETF refresh
    """
    operation_type = request.form.get('operation_type')

    # CURRENT: Hardcoded operation mapping (lines 384-398)
    if operation_type == 'sp500':
        universe_key = 'SP500'
        job_type = 'bulk_sp500_load'
    elif operation_type == 'nasdaq100':
        universe_key = 'NASDAQ100'
        job_type = 'bulk_nasdaq100_load'
    elif operation_type == 'etf_refresh':
        universe_key = 'ETF'
        job_type = 'bulk_etf_refresh'

    # CURRENT: Publish to Redis (lines 407-417)
    message = {
        'job_id': job_id,
        'job_type': job_type,
        'universe_key': universe_key,
        'years': 1,
        'submitted_at': datetime.now().isoformat()
    }
    redis_client.publish('tickstock.jobs.data_load', json.dumps(message))

    return jsonify({'success': True, 'job_id': job_id})


# ═══════════════════════════════════════════════════════════════
# CURRENT IMPLEMENTATION: cache_entries table access
# File: src/infrastructure/cache/cache_control.py (lines 365-375)
# ═══════════════════════════════════════════════════════════════

def get_universe_tickers(self, universe_key: str) -> list:
    """
    CURRENT: Retrieves symbol list from universe key

    Args:
        universe_key: Format "universe_type:key" e.g. "etf_universe:etf_core"

    Returns:
        List of ticker symbols
    """
    # CURRENT: Parse universe key (line 367)
    parts = universe_key.split(':')
    if len(parts) != 2:
        return []

    universe_type, key = parts

    # CURRENT: Look up in cached dictionary (lines 370-375)
    if universe_type in self.cache and key in self.cache[universe_type]:
        value = self.cache[universe_type][key]
        if isinstance(value, dict) and 'symbols' in value:
            return value['symbols']
        elif isinstance(value, list):
            return value

    return []


# ═══════════════════════════════════════════════════════════════
# CURRENT DEPENDENCIES: What calls the historical data endpoints
# ═══════════════════════════════════════════════════════════════

# CALLER 1: Frontend JavaScript
# File: web/static/js/admin/historical_data.js (lines 85-177)
# Calls: POST /api/admin/historical-data/load
# Format: JSON body with {job_type, symbols, years, timespan}

# CALLER 2: Template form submissions
# File: web/templates/admin/historical_data_dashboard_redis.html (line 101)
# Calls: POST /admin/historical-data/trigger-load
# Format: Form data with load_type, symbols, years

# CALLER 3: Bulk operation buttons
# File: web/templates/admin/historical_data_dashboard_redis.html (implied)
# Calls: POST /admin/historical-data/bulk-operations
# Format: Form data with operation_type
```

### Dependency Analysis

```yaml
# What DEPENDS on the code being changed

upstream_dependencies:
  # Code that CALLS the functions/classes being modified

  - component: "web/static/js/admin/historical_data.js"
    dependency: "Calls POST /api/admin/historical-data/load (line 85)"
    impact: "NEW endpoints won't break this; it will continue working"

  - component: "web/templates/admin/historical_data_dashboard_redis.html"
    dependency: "Renders available_universes dict in dropdown (line 165-188)"
    impact: "Changing available_universes structure requires template update"

  - component: "tests/sprint15/test_admin_menu.py"
    dependency: "Tests /admin/historical-data route access (line 90)"
    impact: "Route path unchanged; tests will continue passing"

  - component: "tests/integration/test_historical_import.py"
    dependency: "Tests Redis job submission flow"
    impact: "New universe load endpoint will use same Redis pattern; no impact"

downstream_dependencies:
  # Code that is CALLED BY the functions/classes being modified

  - component: "src/infrastructure/cache/cache_control.py"
    dependency: "get_universe_tickers() reads cache_entries data (line 365)"
    impact: "NEW endpoints will call this to expand universe keys; no changes needed"

  - component: "src/infrastructure/database/models/base.py"
    dependency: "CacheEntry model defines cache_entries schema (line 285)"
    impact: "No schema changes; will query existing JSONB columns"

  - component: "Redis pub-sub channel: tickstock.jobs.data_load"
    dependency: "Receives job submission messages (line 407-417)"
    impact: "NEW endpoint will publish same message format; no changes"

database_dependencies:
  - table: "cache_entries"
    columns: ["type", "name", "key", "value", "environment"]
    impact: "SELECT query to fetch ETF universes; read-only"
    migration_required: No

  - table: "symbol_load_log"
    columns: ["csv_filename", "symbol_count", "load_status"]
    impact: "Possible INSERT for universe load tracking (optional enhancement)"
    migration_required: No

redis_dependencies:
  - channel: "tickstock.jobs.data_load"
    current_format: "{job_id, job_type, universe_key, symbols[], years, submitted_at}"
    impact: "NEW endpoint publishes to same channel with universe_key populated"

  - channel: "tickstock.jobs.status:{job_id}"
    current_format: "{status, progress, message, symbols_processed, symbols_failed}"
    impact: "Frontend will poll this for universe load progress; no format change"

websocket_dependencies:
  affected: No

external_api_dependencies:
  - api: "TickStockPL (receives Redis jobs)"
    current_contract: "Processes tickstock.jobs.data_load messages"
    impact: "No API contract changes; TickStockPL already handles universe loads"
```

### Test Coverage Analysis

```yaml
# Existing tests that cover code being modified

unit_tests:
  - test_file: "tests/sprint15/test_admin_menu.py"
    coverage: "Tests /admin/historical-data route access and admin menu rendering"
    needs_update: No
    update_reason: "Route path unchanged; new features are additive"

integration_tests:
  - test_file: "tests/integration/test_historical_import.py"
    coverage: "Tests Redis job submission and status polling"
    needs_update: No
    update_reason: "New universe endpoint uses same Redis pattern"

missing_coverage:
  # Test gaps that should be filled during this change

  - scenario: "Universe dropdown populated from database"
    reason: "Need to verify cache_entries query returns correct ETF universes"

  - scenario: "Bulk universe load submits correct Redis message"
    reason: "Need to verify universe_key and symbol expansion works correctly"

  - scenario: "Failed universe load reports per-symbol errors"
    reason: "Need to verify error handling matches existing CSV load pattern"
```

## Impact Analysis

### Potential Breakage Points

```yaml
# What could BREAK as a result of this change

high_risk:
  # NONE - This is an additive change with no modifications to existing endpoints

medium_risk:
  - component: "Template rendering if available_universes structure changes"
    risk: "If we change available_universes from dict to list of dicts, template breaks"
    mitigation: "Keep dict structure OR update template simultaneously in same commit"

  - component: "Cache_entries table query performance"
    risk: "Querying cache_entries on page load could slow dashboard render"
    mitigation: "Use CacheControl singleton (already in-memory); cache refresh on deploy"

low_risk:
  - component: "Redis job processing in TickStockPL"
    risk: "If universe_key format unexpected, job may fail"
    mitigation: "Use existing universe_key format ('etf_universe:etf_core'); already supported"
```

### Performance Impact

```yaml
# How this change affects system performance

expected_improvements:
  - metric: "Admin workflow time (ETF universe loading)"
    current: "5-10 minutes (database query + CSV creation + upload)"
    target: "<30 seconds (dropdown select + click)"
    measurement: "Manual timing of admin workflow before/after"

potential_regressions:
  - metric: "Dashboard page load time"
    current: "<500ms (hardcoded universes)"
    risk: "Could increase to ~600ms with database query"
    threshold: "<1000ms acceptable"
    measurement: "Browser DevTools Network tab, 10-page-load average"
    mitigation: "Use CacheControl singleton (already loads cache_entries at startup)"
```

### Backward Compatibility

```yaml
backward_compatibility:
  breaking_changes: No

  compatibility_guarantee: |
    - All existing API endpoints preserved (/admin/historical-data, /admin/historical-data/trigger-load, etc.)
    - Existing form submissions continue working (single symbol, CSV upload)
    - available_universes template variable maintains dict structure (may have more entries)
    - Redis job message format unchanged (same fields: job_id, job_type, symbols[], years)
    - Database schema unchanged (read-only queries only)
```

## All Needed Context

### Context Completeness Check

_Before implementing: "If someone knew nothing about this codebase OR the current implementation, would they have everything needed to make this change successfully without breaking anything?"_

**Answer**: YES - This PRP provides:
- ✅ Current implementation code with line numbers
- ✅ All callers identified (JavaScript, templates, tests)
- ✅ Complete dependency analysis (Redis, database, cache)
- ✅ BEFORE/AFTER code examples
- ✅ Performance baseline (dashboard load <500ms)
- ✅ Existing patterns to follow (bulk operations, CSV loading, job polling)

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: TickStockAppV2
  role: Consumer

  redis_channels:
    - channel: "tickstock.jobs.data_load"
      change_type: publisher
      current_behavior: "Publishes job submissions with hardcoded universe keys"
      new_behavior: "Publishes job submissions with database-sourced universe keys"

    - channel: "tickstock.jobs.status:{job_id}"
      change_type: subscriber
      current_behavior: "Frontend polls for job status every 1 second"
      new_behavior: "Same polling pattern for universe loads"

  database_access:
    mode: read-only
    tables_affected: ["cache_entries"]
    queries_modified: ["Add SELECT for ETF universes on dashboard page load"]
    schema_changes: No

  websocket_integration:
    affected: No

  tickstockpl_api:
    affected: No
    note: "TickStockPL receives jobs via Redis pub-sub; no HTTP API changes"

  performance_targets:
    - metric: "Dashboard page load"
      current: "<500ms"
      target: "<1000ms (with DB query for universes)"

    - metric: "Bulk universe load submission"
      current: "N/A (doesn't exist)"
      target: "<100ms (publish to Redis)"
```

### Documentation & References

```yaml
# MUST READ - Include these in your context window

# Current implementation references (CRITICAL for modifications)

- file: src/api/rest/admin_historical_data_redis.py
  why: "Current active implementation - will add 2 new endpoints here"
  lines: [45-112, 374-433, 680]
  pattern: "Flask blueprint routes with Redis job submission"
  gotcha: "Uses hardcoded universes dict; replace with DB query"

- file: src/infrastructure/cache/cache_control.py
  why: "Singleton that loads cache_entries at startup - use for universe lookup"
  lines: [365-375, 40-59]
  pattern: "get_universe_tickers(universe_key) expands to symbol list"
  gotcha: "Universe key format: 'universe_type:key' (e.g., 'etf_universe:etf_core')"

- file: src/infrastructure/database/models/base.py
  why: "CacheEntry ORM model - use for querying cache_entries"
  lines: [285-299]
  pattern: "SQLAlchemy model with JSONB value column"
  gotcha: "value column can be array ['AAPL', 'NVDA'] or object {'symbols': [...]}"

# Similar working features (for pattern consistency)

- file: src/api/rest/admin_historical_data_redis.py
  why: "CSV universe load pattern (lines 595-680) - follow this for bulk universe load"
  pattern: "Accept universe key, expand to symbols, publish to Redis, track job"
  gotcha: "CSV loads use symbol_load_log table for tracking (optional for universes)"

- file: src/jobs/enterprise_production_scheduler.py
  why: "Enterprise scheduler shows job progress pattern (lines 66-296)"
  pattern: "Track completed_symbols, failed_symbols, success_rate in Redis"
  gotcha: "Use Redis sets for resume capability: enterprise:job:{job_id}:completed"

- file: src/data/bulk_universe_seeder.py
  why: "BulkLoadRequest/Result pattern for universe operations (lines 53-71)"
  pattern: "Dataclass with symbols_loaded, symbols_failed, errors list"
  gotcha: "Return statistics for frontend display"

# External documentation

- url: https://flask.palletsprojects.com/en/3.0.x/blueprints/
  why: "Flask blueprint route registration patterns"
  critical: "Use @admin_bp.route() decorator for new endpoints"

- url: https://jinja.palletsprojects.com/en/3.1.x/templates/#for
  why: "Jinja2 template loops for rendering universe dropdown"
  critical: "Use {% for %} with loop.index, loop.first for dropdown options"

- url: https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.dialects.postgresql.JSONB
  why: "SQLAlchemy JSONB query patterns for cache_entries.value"
  critical: "Use .has_key('symbols') and .contains() for filtering"

# TickStock-Specific References

- file: web/static/js/admin/historical_data.js
  why: "Frontend polling pattern for job status (lines 179-246)"
  pattern: "Poll /api/admin/job-status/{jobId} every 1 second, max 5 minutes"
  gotcha: "Stop polling when status is completed|failed|cancelled|timeout"

- file: web/templates/admin/historical_data_dashboard_redis.html
  why: "Template structure for adding new form sections (lines 352-441)"
  pattern: "Bootstrap form with dropdown, button, preview area"
  gotcha: "Use form-group class, include CSRF token, add to existing grid layout"
```

### Current Codebase Tree (Files Being Modified)

```bash
# Task 1: ETF Universe Integration

src/
├── api/
│   └── rest/
│       ├── admin_historical_data_redis.py  # MODIFY: Add 2 endpoints (lines ~682-750)
│       └── admin_historical_data.py        # PRESERVE: Legacy file, do NOT modify
│
├── infrastructure/
│   ├── cache/
│   │   └── cache_control.py                # REFERENCE: Use get_universe_tickers()
│   └── database/
│       └── models/
│           └── base.py                     # REFERENCE: CacheEntry model
│
└── app.py                                  # PRESERVE: Route registration unchanged

web/
├── templates/
│   └── admin/
│       ├── historical_data_dashboard_redis.html  # MODIFY: Add universe UI (~line 350)
│       └── base_admin.html                       # PRESERVE: Navigation unchanged
│
└── static/
    └── js/
        └── admin/
            └── historical_data.js          # MODIFY: Add universe methods (~line 485)

# Task 2: Cache Entries Audit

scripts/
└── sql/
    └── cache_entries_cleanup_sprint55.sql  # CREATE: SQL cleanup script

docs/
└── database/
    ├── cache_entries_audit_report_sprint55.md    # CREATE: Audit report
    └── cache_entries_maintenance.md              # CREATE: Maintenance procedures
```

### Known Gotchas of Current Code & Library Quirks

```python
# ═══════════════════════════════════════════════════════════════
# CRITICAL: Current Code Gotchas
# ═══════════════════════════════════════════════════════════════

# GOTCHA 1: Dual Implementation Confusion
# File: src/api/rest/admin_historical_data.py vs admin_historical_data_redis.py
# CRITICAL: admin_historical_data_redis.py is the ACTIVE version (registered in app.py:2276)
# CRITICAL: Do NOT modify admin_historical_data.py (legacy, not used)
# Verify: grep "register_admin_historical" src/app.py shows ONLY redis version

# GOTCHA 2: Universe Key Format
# File: src/infrastructure/cache/cache_control.py (line 367)
# CRITICAL: Universe keys have format "universe_type:key"
# Examples:
#   - "etf_universe:etf_core" → ["SPY", "QQQ", "IWM"]
#   - "stock_etf_combo:stock_etf_group" → [36 symbols]
# Wrong format "etf_core" (missing type prefix) returns empty list

# GOTCHA 3: JSONB Value Structure Variability
# File: src/infrastructure/cache/cache_control.py (lines 370-375)
# CRITICAL: cache_entries.value can be:
#   - Array: ["AAPL", "NVDA", "TSLA"]
#   - Object: {"symbols": ["AAPL", "NVDA"], "count": 2}
# Must handle both formats when extracting symbols
# Use: if isinstance(value, dict) and 'symbols' in value: return value['symbols']

# GOTCHA 4: CacheControl Singleton Initialization
# File: src/infrastructure/cache/cache_control.py (lines 40-59)
# CRITICAL: CacheControl loads cache_entries ONCE at application startup
# New cache entries added to database won't appear until app restart or cache refresh
# Workaround: Call cache_control.load_settings_from_db() to refresh

# GOTCHA 5: Frontend Polling Timeout
# File: web/static/js/admin/historical_data.js (lines 10-11, 234-241)
# CRITICAL: Job status polling has 5-minute timeout
# Long-running universe loads (>5 min) will show "timeout" status in UI
# Backend job continues running; only frontend stops polling
# Mitigation: Show "Still processing..." message instead of "Failed"

# ═══════════════════════════════════════════════════════════════
# CRITICAL: TickStock-Specific Gotchas
# ═══════════════════════════════════════════════════════════════

# GOTCHA 6: Flask Application Context in Admin Routes
# CRITICAL: Use current_app for config access, not module-level globals
from flask import current_app

@admin_bp.route('/admin/endpoint')
def endpoint():
    redis_host = current_app.config.get('REDIS_HOST')  # ✅ Correct
    # NOT: redis_host = config['REDIS_HOST']          # ❌ Wrong

# GOTCHA 7: Redis Job Submission Pattern
# CRITICAL: Job ID format must be: {job_type}_{timestamp}_{random}
# Example: universe_load_1732550400_7
# Used for: Redis status key (tickstock.jobs.status:{job_id})
import time
import random
job_id = f"universe_load_{int(time.time())}_{random.randint(0, 9999)}"

# ═══════════════════════════════════════════════════════════════
# CRITICAL: Library-Specific Quirks
# ═══════════════════════════════════════════════════════════════

# GOTCHA 8: SQLAlchemy JSONB Filtering
# CRITICAL: Use .has_key() not 'in' operator for JSONB key checks
from sqlalchemy.dialects.postgresql import JSONB

# ✅ Correct
entries = CacheEntry.query.filter(
    CacheEntry.value.has_key('symbols')
).all()

# ❌ Wrong
entries = CacheEntry.query.filter(
    'symbols' in CacheEntry.value  # Doesn't work with JSONB
).all()

# GOTCHA 9: Jinja2 Loop Variables
# CRITICAL: loop.index is 1-based, loop.index0 is 0-based
{% for item in items %}
    {{ loop.index }}   {# 1, 2, 3, ... #}
    {{ loop.index0 }}  {# 0, 1, 2, ... #}
{% endfor %}

# GOTCHA 10: Redis Publish Returns Subscriber Count
# CRITICAL: redis.publish() returns number of subscribers who received message
# Return value 0 means NO subscribers (TickStockPL might be down)
subscriber_count = redis_client.publish('tickstock.jobs.data_load', message)
if subscriber_count == 0:
    logger.warning("No subscribers on tickstock.jobs.data_load - is TickStockPL running?")
```

## Change Implementation Blueprint

### Pre-Change Preparation

```yaml
# Steps to take BEFORE modifying code

1_backup_current_state:
  - action: "Create git branch"
    command: "git checkout -b sprint55/etf-universe-integration"

  - action: "Document current dashboard behavior"
    command: "Screenshot /admin/historical-data page, note available universes"

  - action: "Run baseline tests"
    command: "python run_tests.py  # Verify all tests pass BEFORE changes"

2_analyze_dependencies:
  - action: "Find all references to available_universes"
    command: "rg 'available_universes' src/ web/"

  - action: "Find all cache_entries queries"
    command: "rg 'cache_entries' src/"

  - action: "Check CacheControl usage patterns"
    command: "rg 'CacheControl' src/ | head -20"

3_create_regression_baseline:
  - action: "Test current single-symbol load"
    why: "Ensure existing functionality preserved after changes"
    steps:
      - "Navigate to /admin/historical-data"
      - "Enter symbol: AAPL"
      - "Select years: 1"
      - "Click Load"
      - "Verify job submits and polls correctly"

  - action: "Test current CSV load"
    why: "Ensure CSV loading unchanged"
    steps:
      - "Select dow_30.csv"
      - "Click trigger load"
      - "Verify 30 symbols loaded"

  - action: "Measure dashboard load time"
    command: "Browser DevTools → Network tab → Load /admin/historical-data 10 times → Average time"
    baseline: "<500ms"
```

### Change Tasks (Ordered by Dependencies)

```yaml
# Task 1: ETF Universe Integration

Task_1A: ADD endpoint to fetch available universes from cache_entries
  LOCATION: src/api/rest/admin_historical_data_redis.py (after line 680)
  CURRENT: "File ends at line 680; no universe listing endpoint exists"
  CHANGE: "Add GET /admin/historical-data/universes endpoint"
  PRESERVE: "All existing endpoints unchanged"
  GOTCHA: "Use CacheControl singleton, not direct DB query (already in-memory)"
  VALIDATION: "curl /admin/historical-data/universes returns JSON with ETF universes"

  CODE:
    ```python
    @admin_bp.route('/admin/historical-data/universes', methods=['GET'])
    @login_required
    def get_available_universes():
        """Return list of available ETF and stock_etf_combo universes for dropdown."""
        try:
            from src.infrastructure.cache.cache_control import CacheControl
            cache_control = CacheControl()

            universes = []

            # Get ETF universes
            if 'etf_universes' in cache_control.cache:
                for key, value in cache_control.cache['etf_universes'].items():
                    symbol_count = len(value) if isinstance(value, list) else len(value.get('symbols', []))
                    universes.append({
                        'key': f'etf_universe:{key}',
                        'name': key.replace('_', ' ').title(),
                        'type': 'etf_universe',
                        'symbol_count': symbol_count
                    })

            # Get stock_etf_combo universes
            if 'stock_etf_combos' in cache_control.cache:
                for key, value in cache_control.cache['stock_etf_combos'].items():
                    symbol_count = len(value) if isinstance(value, list) else len(value.get('symbols', []))
                    universes.append({
                        'key': f'stock_etf_combo:{key}',
                        'name': key.replace('_', ' ').title(),
                        'type': 'stock_etf_combo',
                        'symbol_count': symbol_count
                    })

            return jsonify({'universes': universes})

        except Exception as e:
            logger.error(f"Failed to fetch universes: {e}")
            return jsonify({'error': str(e)}), 500
    ```

Task_1B: ADD endpoint to trigger bulk universe load
  LOCATION: src/api/rest/admin_historical_data_redis.py (after Task_1A endpoint)
  CURRENT: "Bulk operations exist (line 374) but hardcoded; no dynamic universe load"
  CHANGE: "Add POST /admin/historical-data/trigger-universe-load endpoint"
  PRESERVE: "Existing bulk-operations endpoint unchanged (backward compatibility)"
  DEPENDENCIES: "Must complete Task_1A first (uses same CacheControl pattern)"
  VALIDATION: "POST with universe_key returns job_id, publishes to Redis"

  CODE:
    ```python
    @admin_bp.route('/admin/historical-data/trigger-universe-load', methods=['POST'])
    @login_required
    def trigger_universe_load():
        """Submit bulk load job for all symbols in a universe."""
        try:
            universe_key = request.form.get('universe_key')
            years = request.form.get('years', 1, type=int)

            if not universe_key:
                return jsonify({'error': 'universe_key required'}), 400

            # Expand universe to symbol list
            from src.infrastructure.cache.cache_control import CacheControl
            cache_control = CacheControl()
            symbols = cache_control.get_universe_tickers(universe_key)

            if not symbols:
                return jsonify({'error': f'No symbols found for universe: {universe_key}'}), 404

            # Generate job ID
            import time, random
            job_id = f"universe_load_{int(time.time())}_{random.randint(0, 9999)}"

            # Publish to Redis
            message = {
                'job_id': job_id,
                'job_type': 'universe_bulk_load',
                'universe_key': universe_key,
                'symbols': symbols,
                'years': years,
                'submitted_at': datetime.now().isoformat()
            }

            redis_client = get_redis_client()
            subscriber_count = redis_client.publish('tickstock.jobs.data_load', json.dumps(message))

            if subscriber_count == 0:
                logger.warning("No subscribers on tickstock.jobs.data_load")

            # Store job status in Redis
            job_key = f"tickstock.jobs.status:{job_id}"
            redis_client.hset(job_key, mapping={
                'status': 'submitted',
                'progress': 0,
                'message': f'Submitted {len(symbols)} symbols from {universe_key}',
                'total_symbols': len(symbols),
                'submitted_at': datetime.now().isoformat()
            })
            redis_client.expire(job_key, 86400)  # 24-hour TTL

            return jsonify({
                'success': True,
                'job_id': job_id,
                'symbol_count': len(symbols),
                'universe_key': universe_key
            })

        except Exception as e:
            logger.error(f"Failed to submit universe load: {e}")
            return jsonify({'error': str(e)}), 500
    ```

Task_1C: UPDATE template with ETF universe selector UI
  LOCATION: web/templates/admin/historical_data_dashboard_redis.html (around line 350)
  CURRENT: "CSV loading section exists (lines 352-441); no universe selector"
  CHANGE: "Add new section after CSV loading with universe dropdown + preview + trigger button"
  PRESERVE: "All existing sections unchanged (CSV, bulk operations, job history)"
  DEPENDENCIES: "Must complete Task_1A, Task_1B first (endpoints must exist)"
  VALIDATION: "Dropdown populated on page load, shows symbol counts, triggers load"

  CODE:
    ```html
    <!-- NEW SECTION: ETF Universe Loading (add after line 441) -->
    <div class="card mb-4">
        <div class="card-header bg-info text-white">
            <h5 class="mb-0">
                <i class="fas fa-layer-group"></i> ETF Universe Loading
            </h5>
        </div>
        <div class="card-body">
            <form id="universe-load-form">
                <div class="row">
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="universe-select">Select Universe</label>
                            <select id="universe-select" name="universe_key" class="form-control" required>
                                <option value="">Loading universes...</option>
                            </select>
                            <small class="form-text text-muted">
                                Select an ETF or combined universe to load all symbols
                            </small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="universe-years">Historical Data Duration</label>
                            <select id="universe-years" name="years" class="form-control">
                                <option value="1">1 Year</option>
                                <option value="2">2 Years</option>
                                <option value="5">5 Years</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label>&nbsp;</label>
                            <button type="submit" id="trigger-universe-load" class="btn btn-info btn-block" disabled>
                                <i class="fas fa-play"></i> Load Universe
                            </button>
                        </div>
                    </div>
                </div>

                <div id="universe-preview" class="alert alert-info" style="display: none;">
                    <strong>Preview:</strong> <span id="preview-text"></span>
                </div>

                <div id="universe-progress" style="display: none;">
                    <div class="progress">
                        <div id="universe-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated"
                             role="progressbar" style="width: 0%">
                            0%
                        </div>
                    </div>
                    <p id="universe-status" class="mt-2 mb-0"></p>
                </div>
            </form>
        </div>
    </div>
    ```

Task_1D: UPDATE JavaScript to handle universe selection and loading
  LOCATION: web/static/js/admin/historical_data.js (after line 485)
  CURRENT: "HistoricalDataManager class handles CSV and single-symbol loads"
  CHANGE: "Add methods: loadUniverses(), handleUniverseChange(), submitUniverseLoad()"
  PRESERVE: "All existing methods unchanged (submitDataLoad, startPollingJobStatus, etc.)"
  DEPENDENCIES: "Must complete Task_1A-C first (template elements must exist)"
  VALIDATION: "Universe dropdown populates, preview updates, load submits and polls"

  CODE:
    ```javascript
    // ADD to HistoricalDataManager class (after line 485)

    /**
     * Load available universes from backend and populate dropdown
     */
    async loadUniverses() {
        try {
            const response = await fetch('/admin/historical-data/universes');
            const data = await response.json();

            const select = document.getElementById('universe-select');
            select.innerHTML = '<option value="">Select a universe...</option>';

            data.universes.forEach(universe => {
                const option = document.createElement('option');
                option.value = universe.key;
                option.textContent = `${universe.name} (${universe.symbol_count} symbols)`;
                option.dataset.symbolCount = universe.symbol_count;
                select.appendChild(option);
            });

            document.getElementById('trigger-universe-load').disabled = false;

        } catch (error) {
            console.error('Failed to load universes:', error);
            document.getElementById('universe-select').innerHTML =
                '<option value="">Error loading universes</option>';
        }
    }

    /**
     * Handle universe selection change - show preview
     */
    handleUniverseChange(event) {
        const select = event.target;
        const selectedOption = select.options[select.selectedIndex];
        const symbolCount = selectedOption.dataset.symbolCount;
        const universeName = selectedOption.textContent;

        if (select.value) {
            const preview = document.getElementById('universe-preview');
            const previewText = document.getElementById('preview-text');
            previewText.textContent = `This will load ${symbolCount} symbols from ${universeName}`;
            preview.style.display = 'block';
        } else {
            document.getElementById('universe-preview').style.display = 'none';
        }
    }

    /**
     * Submit universe bulk load
     */
    async submitUniverseLoad(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const universeKey = formData.get('universe_key');
        const years = formData.get('years');

        if (!universeKey) {
            this.showNotification('Please select a universe', 'error');
            return;
        }

        try {
            const response = await fetch('/admin/historical-data/trigger-universe-load', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(`Universe load submitted! Job ID: ${data.job_id}`, 'success');

                // Show progress container
                document.getElementById('universe-progress').style.display = 'block';
                document.getElementById('universe-status').textContent =
                    `Loading ${data.symbol_count} symbols...`;

                // Start polling
                this.startPollingJobStatus(data.job_id);

            } else {
                this.showNotification(`Failed: ${data.error}`, 'error');
            }

        } catch (error) {
            console.error('Universe load submission failed:', error);
            this.showNotification('Failed to submit universe load', 'error');
        }
    }

    // ADD event listeners in constructor (modify existing init method)
    init() {
        // ... existing event listeners ...

        // NEW: Universe selection events
        document.getElementById('universe-select').addEventListener('change',
            (e) => this.handleUniverseChange(e));
        document.getElementById('universe-load-form').addEventListener('submit',
            (e) => this.submitUniverseLoad(e));

        // Load universes on page load
        this.loadUniverses();
    }
    ```

# Task 2: Cache Entries Audit

Task_2A: CREATE SQL cleanup script for cache_entries
  LOCATION: scripts/sql/cache_entries_cleanup_sprint55.sql (NEW FILE)
  CURRENT: "File does not exist"
  CHANGE: "Create SQL script with UPDATE statements for data quality fixes"
  PRESERVE: "N/A (new file)"
  VALIDATION: "Run script against dev database, verify 3 entries updated"

  CODE:
    ```sql
    -- Sprint 55: Cache Entries Audit and Cleanup
    -- Date: 2025-11-26
    -- Purpose: Fix data quality issues in cache_entries table

    -- Issue #1: Set updated_at for entries with NULL timestamps (created Nov 25, 2025)
    UPDATE cache_entries
    SET updated_at = created_at
    WHERE id IN (1335, 1337, 1338)  -- etf_core, etf_equal_weight_sectors, stock_etf_group
    AND updated_at IS NULL;

    -- Verification
    SELECT id, type, name, key, created_at, updated_at
    FROM cache_entries
    WHERE id IN (1335, 1337, 1338);

    -- Issue #2: Rename "complete" to "Complete" for Title Case consistency
    UPDATE cache_entries
    SET name = 'Complete'
    WHERE name = 'complete'
    AND type IN ('etf_universe', 'stock_universe');

    -- Verification
    SELECT id, type, name, key
    FROM cache_entries
    WHERE name = 'Complete';

    -- Issue #3 (Optional): Add universe_category metadata
    UPDATE cache_entries
    SET universe_metadata = jsonb_set(
        COALESCE(universe_metadata, '{}'::jsonb),
        '{category}',
        '"broad_market"'
    )
    WHERE key = 'etf_core'
    AND type = 'etf_universe';

    UPDATE cache_entries
    SET universe_metadata = jsonb_set(
        COALESCE(universe_metadata, '{}'::jsonb),
        '{category}',
        '"sector"'
    )
    WHERE key IN ('etf_sector', 'etf_equal_weight_sectors')
    AND type = 'etf_universe';

    -- Final verification: Check all entries are clean
    SELECT
        COUNT(*) as total_entries,
        COUNT(*) FILTER (WHERE updated_at IS NULL) as missing_updated_at,
        COUNT(*) FILTER (WHERE name ~ '[a-z]' AND name !~ '^[A-Z]') as lowercase_names
    FROM cache_entries;

    -- Expected: total_entries=290, missing_updated_at=0, lowercase_names=0
    ```

Task_2B: CREATE audit report documenting findings and changes
  LOCATION: docs/database/cache_entries_audit_report_sprint55.md (NEW FILE)
  CURRENT: "File does not exist"
  CHANGE: "Create markdown report with audit findings, cleanup actions, results"
  PRESERVE: "N/A (new file)"
  VALIDATION: "Report includes before/after counts, SQL script execution results"

Task_2C: CREATE maintenance procedures document
  LOCATION: docs/database/cache_entries_maintenance.md (NEW FILE)
  CURRENT: "File does not exist"
  CHANGE: "Create procedures for adding/updating cache_entries in future"
  PRESERVE: "N/A (new file)"
  VALIDATION: "Document includes examples, validation checklist, naming conventions"
```

### Change Patterns & Key Details

```python
# ═══════════════════════════════════════════════════════════════
# Pattern 1: Adding New Flask Route to Existing Blueprint
# ═══════════════════════════════════════════════════════════════

# BEFORE: Blueprint registration in admin_historical_data_redis.py
# File: src/api/rest/admin_historical_data_redis.py (line 680 - end of file)

# ... existing routes end at line 680 ...


# AFTER: New universe listing endpoint added
# File: src/api/rest/admin_historical_data_redis.py (lines 682-720)

@admin_bp.route('/admin/historical-data/universes', methods=['GET'])
@login_required
def get_available_universes():
    """
    NEW ENDPOINT: Return available ETF and stock_etf_combo universes.

    Returns:
        JSON: {'universes': [{'key': 'etf_universe:etf_core', 'name': 'Etf Core', 'symbol_count': 3}, ...]}
    """
    try:
        # ✅ Use CacheControl singleton (already in-memory, fast)
        from src.infrastructure.cache.cache_control import CacheControl
        cache_control = CacheControl()

        universes = []

        # Extract ETF universes
        if 'etf_universes' in cache_control.cache:
            for key, value in cache_control.cache['etf_universes'].items():
                # ✅ Handle both array and object JSONB formats
                symbol_count = len(value) if isinstance(value, list) else len(value.get('symbols', []))
                universes.append({
                    'key': f'etf_universe:{key}',
                    'name': key.replace('_', ' ').title(),
                    'type': 'etf_universe',
                    'symbol_count': symbol_count
                })

        return jsonify({'universes': universes})

    except Exception as e:
        logger.error(f"Failed to fetch universes: {e}")
        return jsonify({'error': str(e)}), 500

# CHANGE RATIONALE:
# - Current: Hardcoded universes dict in admin_historical_dashboard() (line 77-82)
# - New: Dynamic universes from database via CacheControl
# - Performance: No DB query (CacheControl loads once at startup, cached in-memory)

# PRESERVED BEHAVIOR:
# - Existing routes unchanged (/admin/historical-data, /admin/historical-data/trigger-load, etc.)
# - Backward compatible: Old hardcoded universes still work in template
# - No database schema changes

# GOTCHA:
# - Must use CacheControl singleton, not direct DB query (performance)
# - Universe key format: "universe_type:key" (e.g., "etf_universe:etf_core")
# - JSONB value can be array or object with 'symbols' key - handle both


# ═══════════════════════════════════════════════════════════════
# Pattern 2: Jinja2 Template - Dynamic Dropdown from AJAX
# ═══════════════════════════════════════════════════════════════

# BEFORE: Hardcoded universe dropdown (if it existed)
# File: web/templates/admin/historical_data_dashboard_redis.html
# (Doesn't actually exist in current template - this is new feature)

# AFTER: Dynamic universe dropdown populated via AJAX
# File: web/templates/admin/historical_data_dashboard_redis.html (NEW section after line 441)

<div class="card mb-4">
    <div class="card-header bg-info text-white">
        <h5 class="mb-0">
            <i class="fas fa-layer-group"></i> ETF Universe Loading
        </h5>
    </div>
    <div class="card-body">
        <form id="universe-load-form">
            <div class="row">
                <!-- ✅ Dynamic dropdown - populated by JavaScript -->
                <div class="col-md-6">
                    <div class="form-group">
                        <label for="universe-select">Select Universe</label>
                        <select id="universe-select" name="universe_key" class="form-control" required>
                            <!-- ✅ Placeholder while loading -->
                            <option value="">Loading universes...</option>
                        </select>
                        <small class="form-text text-muted">
                            Select an ETF or combined universe to load all symbols
                        </small>
                    </div>
                </div>

                <div class="col-md-3">
                    <div class="form-group">
                        <label for="universe-years">Duration</label>
                        <select id="universe-years" name="years" class="form-control">
                            <option value="1">1 Year</option>
                            <option value="2">2 Years</option>
                            <option value="5">5 Years</option>
                        </select>
                    </div>
                </div>

                <div class="col-md-3">
                    <div class="form-group">
                        <label>&nbsp;</label>
                        <!-- ✅ Disabled until universes loaded -->
                        <button type="submit" id="trigger-universe-load"
                                class="btn btn-info btn-block" disabled>
                            <i class="fas fa-play"></i> Load Universe
                        </button>
                    </div>
                </div>
            </div>

            <!-- ✅ Preview area - shows symbol count -->
            <div id="universe-preview" class="alert alert-info" style="display: none;">
                <strong>Preview:</strong> <span id="preview-text"></span>
            </div>

            <!-- ✅ Progress tracking - same pattern as existing CSV loads -->
            <div id="universe-progress" style="display: none;">
                <div class="progress">
                    <div id="universe-progress-bar"
                         class="progress-bar progress-bar-striped progress-bar-animated"
                         role="progressbar" style="width: 0%">
                        0%
                    </div>
                </div>
                <p id="universe-status" class="mt-2 mb-0"></p>
            </div>
        </form>
    </div>
</div>

# CHANGE RATIONALE:
# - Current: No UI for ETF universe selection (must use CSV files)
# - New: Dropdown populated from database, symbol count preview, progress tracking
# - User Experience: Reduced from 5-10 minutes (manual CSV) to <30 seconds (dropdown select)

# PRESERVED BEHAVIOR:
# - All existing template sections unchanged (CSV loading, bulk operations, job history)
# - Same Bootstrap classes and layout structure
# - Same progress tracking pattern as existing CSV loads

# GOTCHA:
# - Must wait for JavaScript to populate dropdown before enabling button
# - Use data-* attributes to store symbol_count for preview (dataset.symbolCount)
# - Progress bar uses same classes as existing loads (progress-bar-striped, progress-bar-animated)


# ═══════════════════════════════════════════════════════════════
# Pattern 3: jQuery AJAX - Load Dropdown Options on Page Load
# ═══════════════════════════════════════════════════════════════

# BEFORE: No universe loading logic (feature doesn't exist)

# AFTER: Load universes from backend and populate dropdown
# File: web/static/js/admin/historical_data.js (NEW method after line 485)

/**
 * Load available universes from backend and populate dropdown
 */
async loadUniverses() {
    try {
        // ✅ Fetch universes from new endpoint
        const response = await fetch('/admin/historical-data/universes');
        const data = await response.json();

        const select = document.getElementById('universe-select');
        select.innerHTML = '<option value="">Select a universe...</option>';

        // ✅ Populate dropdown with symbol counts
        data.universes.forEach(universe => {
            const option = document.createElement('option');
            option.value = universe.key;  // "etf_universe:etf_core"
            option.textContent = `${universe.name} (${universe.symbol_count} symbols)`;
            option.dataset.symbolCount = universe.symbol_count;  // Store for preview
            select.appendChild(option);
        });

        // ✅ Enable load button after successful population
        document.getElementById('trigger-universe-load').disabled = false;

    } catch (error) {
        console.error('Failed to load universes:', error);
        select.innerHTML = '<option value="">Error loading universes</option>';
    }
}

/**
 * Handle universe selection change - show symbol count preview
 */
handleUniverseChange(event) {
    const select = event.target;
    const selectedOption = select.options[select.selectedIndex];
    const symbolCount = selectedOption.dataset.symbolCount;
    const universeName = selectedOption.textContent;

    if (select.value) {
        // ✅ Show preview with symbol count
        const preview = document.getElementById('universe-preview');
        const previewText = document.getElementById('preview-text');
        previewText.textContent = `This will load ${symbolCount} symbols from ${universeName}`;
        preview.style.display = 'block';
    } else {
        document.getElementById('universe-preview').style.display = 'none';
    }
}

/**
 * Submit universe bulk load to backend
 */
async submitUniverseLoad(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const universeKey = formData.get('universe_key');

    try {
        // ✅ Submit to new trigger-universe-load endpoint
        const response = await fetch('/admin/historical-data/trigger-universe-load', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken()  // ✅ Include CSRF token
            },
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            this.showNotification(`Universe load submitted! Job ID: ${data.job_id}`, 'success');

            // ✅ Use existing polling infrastructure
            this.startPollingJobStatus(data.job_id);

        } else {
            this.showNotification(`Failed: ${data.error}`, 'error');
        }

    } catch (error) {
        console.error('Universe load failed:', error);
        this.showNotification('Failed to submit universe load', 'error');
    }
}

// ✅ Wire up event listeners in constructor
init() {
    // ... existing listeners ...

    document.getElementById('universe-select').addEventListener('change',
        (e) => this.handleUniverseChange(e));
    document.getElementById('universe-load-form').addEventListener('submit',
        (e) => this.submitUniverseLoad(e));

    // ✅ Load universes on page load
    this.loadUniverses();
}

# CHANGE RATIONALE:
# - Current: No frontend logic for universe selection (feature doesn't exist)
# - New: AJAX load → populate dropdown → preview → submit → poll (existing pattern)
# - Reuses existing: polling (startPollingJobStatus), notifications (showNotification), CSRF handling

# PRESERVED BEHAVIOR:
# - All existing methods unchanged (submitDataLoad, testRedisConnection, etc.)
# - Same polling pattern (1-second interval, 5-minute timeout)
# - Same notification system

# GOTCHA:
# - Must call loadUniverses() after page load (existing DOMContentLoaded event)
# - Use dataset.symbolCount to store symbol count on <option> element
# - Reuse existing startPollingJobStatus() method - no need to duplicate polling logic
# - CSRF token required for POST requests (getCSRFToken() already exists)


# ═══════════════════════════════════════════════════════════════
# Pattern 4: Redis Job Submission Pattern
# ═══════════════════════════════════════════════════════════════

# BEFORE: Hardcoded bulk operations
# File: src/api/rest/admin_historical_data_redis.py (lines 407-417)

# Current bulk operations endpoint
message = {
    'job_id': job_id,
    'job_type': 'bulk_sp500_load',  # ← Hardcoded
    'universe_key': 'SP500',        # ← Hardcoded
    'years': 1,
    'submitted_at': datetime.now().isoformat()
}
redis_client.publish('tickstock.jobs.data_load', json.dumps(message))


# AFTER: Dynamic universe load with symbol expansion
# File: src/api/rest/admin_historical_data_redis.py (NEW endpoint)

@admin_bp.route('/admin/historical-data/trigger-universe-load', methods=['POST'])
@login_required
def trigger_universe_load():
    """Submit bulk load job for universe with symbol expansion."""
    universe_key = request.form.get('universe_key')  # ← Dynamic from dropdown
    years = request.form.get('years', 1, type=int)

    # ✅ Expand universe to symbol list using CacheControl
    from src.infrastructure.cache.cache_control import CacheControl
    cache_control = CacheControl()
    symbols = cache_control.get_universe_tickers(universe_key)

    if not symbols:
        return jsonify({'error': f'No symbols found for: {universe_key}'}), 404

    # ✅ Generate job ID with timestamp + random
    import time, random
    job_id = f"universe_load_{int(time.time())}_{random.randint(0, 9999)}"

    # ✅ Publish to Redis (same channel as existing bulk operations)
    message = {
        'job_id': job_id,
        'job_type': 'universe_bulk_load',  # ← New job type
        'universe_key': universe_key,      # ← From dropdown
        'symbols': symbols,                # ← Expanded symbol list
        'years': years,
        'submitted_at': datetime.now().isoformat()
    }

    redis_client = get_redis_client()
    subscriber_count = redis_client.publish('tickstock.jobs.data_load', json.dumps(message))

    # ✅ Check if TickStockPL is listening
    if subscriber_count == 0:
        logger.warning("No subscribers on tickstock.jobs.data_load - is TickStockPL running?")

    # ✅ Store job status in Redis (same pattern as existing jobs)
    job_key = f"tickstock.jobs.status:{job_id}"
    redis_client.hset(job_key, mapping={
        'status': 'submitted',
        'progress': 0,
        'message': f'Submitted {len(symbols)} symbols from {universe_key}',
        'total_symbols': len(symbols),
        'submitted_at': datetime.now().isoformat()
    })
    redis_client.expire(job_key, 86400)  # ✅ 24-hour TTL

    return jsonify({
        'success': True,
        'job_id': job_id,
        'symbol_count': len(symbols),
        'universe_key': universe_key
    })

# CHANGE RATIONALE:
# - Current: Hardcoded universe keys (SP500, NASDAQ100, ETF) in bulk operations
# - New: Dynamic universe selection from database with symbol expansion
# - Same Redis channel, same message format (backward compatible with TickStockPL)

# PRESERVED BEHAVIOR:
# - Redis channel unchanged: tickstock.jobs.data_load
# - Message format compatible: job_id, job_type, symbols[], years
# - Job status tracking: tickstock.jobs.status:{job_id}
# - Frontend polling: uses existing startPollingJobStatus() method

# GOTCHA:
# - Must check subscriber_count == 0 (TickStockPL might be down)
# - Job ID format: {job_type}_{timestamp}_{random} (required for status key)
# - Must expand universe_key to symbols[] using CacheControl.get_universe_tickers()
# - Must handle empty symbol list (universe not found)
```

### Integration Points (What Changes)

```yaml
# TickStock-Specific Integration Points Affected by Change

DATABASE:
  schema_changes: No

  query_changes:
    - location: "src/api/rest/admin_historical_data_redis.py (NEW endpoint)"
    - before: "N/A (no database query in dashboard render)"
    - after: "SELECT type, name, key, value FROM cache_entries WHERE type IN ('etf_universe', 'stock_etf_combo')"
    - performance_impact: "CacheControl already loads cache_entries at startup; no additional query"
    - note: "Using CacheControl singleton (in-memory), not direct DB query"

REDIS_CHANNELS:
  message_format_changes: No

  channel_updates:
    - channel: "tickstock.jobs.data_load"
    - current_format: "{job_id, job_type, universe_key, symbols[], years, submitted_at}"
    - new_format: "SAME - no format change"
    - backward_compatible: Yes
    - note: "New job_type value: 'universe_bulk_load' (TickStockPL treats same as existing bulk loads)"

    - channel: "tickstock.jobs.status:{job_id}"
    - current_format: "{status, progress, message, symbols_processed, symbols_failed, total_symbols}"
    - new_format: "SAME - no format change"
    - backward_compatible: Yes

WEBSOCKET:
  event_changes: No
  note: "Historical data loading does not use WebSocket; uses HTTP polling only"

TICKSTOCKPL_API:
  endpoint_changes: No
  note: "TickStockPL receives jobs via Redis pub-sub; no HTTP API contract changes"
  coordination: "None required - message format unchanged"
```

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# TickStock Standard: Ruff for linting and formatting
# Run after EACH file modification

# Modified files only
ruff check src/api/rest/admin_historical_data_redis.py --fix
ruff format src/api/rest/admin_historical_data_redis.py

ruff check web/static/js/admin/historical_data.js --fix
ruff format web/static/js/admin/historical_data.js

# Full project validation
ruff check src/ web/static/js/ --fix
ruff format src/ web/static/js/

# Expected: Zero errors (same as before changes)
```

### Level 2: Unit Tests (Component Validation)

```bash
# TickStock Standard: pytest for all testing
# Test MODIFIED components specifically

# Test admin routes (if unit tests exist)
python -m pytest tests/unit/test_admin_routes.py -v -k historical

# Test cache_control module
python -m pytest tests/unit/test_cache_control.py -v

# Full unit test suite
python -m pytest tests/unit/ -v

# Expected: All tests pass (including any NEW tests for universe endpoints)
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
# CRITICAL: Must run before ANY commit

python run_tests.py

# Expected Output:
# - All existing tests still pass (regression-free)
# - ~30 second runtime
# - No new errors introduced

# Manual integration test checklist:
# 1. Navigate to /admin/historical-data
# 2. Verify universe dropdown populates with ETF universes
# 3. Select "Core ETFs (3)" from dropdown
# 4. Verify preview shows "This will load 3 symbols..."
# 5. Click "Load Universe"
# 6. Verify job submits and starts polling
# 7. Verify progress bar updates (0% → 100%)
# 8. Verify existing single-symbol load still works
# 9. Verify existing CSV load still works
# 10. Verify bulk operations buttons still work
```

### Level 4: TickStock-Specific Validation

```bash
# Performance Validation
# CRITICAL: Verify performance NOT degraded

# Dashboard page load time (before change: <500ms)
# Measure in browser DevTools Network tab, 10-page-load average
# Target: <1000ms (with CacheControl query)

# Universe dropdown population time
# Measure AJAX request: /admin/historical-data/universes
# Target: <100ms (CacheControl is in-memory)

# Universe load submission time
# Measure POST: /admin/historical-data/trigger-universe-load
# Target: <200ms (Redis publish is fast)

# Backward Compatibility Validation
# CRITICAL: Verify existing functionality unchanged

# Test 1: Single-symbol load
curl -X POST http://localhost:5000/api/admin/historical-data/load \
  -H "Content-Type: application/json" \
  -d '{"job_type": "historical_load", "symbols": ["AAPL"], "years": 1}'

# Expected: {"success": true, "job_id": "load_1732550400_1234"}

# Test 2: CSV load
# Upload dow_30.csv via form
# Expected: 30 symbols loaded, job tracked

# Test 3: Bulk operations
# Click "Refresh All ETFs" button
# Expected: Job submitted, same as before changes

# Architecture Compliance Validation
# CRITICAL: Verify Consumer role preserved

# Verify: TickStockAppV2 only PUBLISHES to Redis (Consumer role)
# Verify: No pattern detection logic added (TickStockPL handles processing)
# Verify: Database queries are read-only (SELECT only, no INSERT/UPDATE)

# Redis Connectivity Validation
# CRITICAL: Verify Redis pub-sub working

# Test Redis connection
curl http://localhost:5000/admin/historical-data/test-redis

# Expected: {"redis_connected": true, "tickstockpl_status": "connected"}

# Monitor Redis channel
# In terminal:
redis-cli
SUBSCRIBE tickstock.jobs.data_load

# In browser: Submit universe load
# Expected: Message appears in redis-cli with job details
```

### Level 5: Regression Testing (MANDATORY for Changes)

```bash
# Regression Test Suite
# CRITICAL: Ensure existing functionality unchanged

# Test 1: Existing routes still accessible
curl -I http://localhost:5000/admin/historical-data
# Expected: 200 OK (if logged in), 302 Redirect (if not logged in)

curl -I http://localhost:5000/admin/historical-data/jobs/status
# Expected: 200 OK

# Test 2: Existing templates render without errors
# Navigate to /admin/historical-data
# Expected: No JavaScript errors in console, all sections visible

# Test 3: Job polling still works for existing job types
# Submit single-symbol load via form
# Expected: Progress bar updates, polling completes, job marked complete

# Test 4: Cache_entries cleanup doesn't break CacheControl
# Run SQL cleanup script
psql -U app_readwrite -d tickstock -f scripts/sql/cache_entries_cleanup_sprint55.sql

# Restart Flask app
python src/app.py

# Expected: App starts successfully, CacheControl loads cache_entries, no errors

# Test 5: Admin navigation menu unchanged
# Navigate to /admin
# Expected: "Historical Data" link present and functional

# Before/After Comparison
# Document baseline metrics BEFORE change:
# - Dashboard page load time: <500ms
# - Single-symbol load success rate: 100%
# - CSV load success rate: >95%

# Measure same metrics AFTER change:
# Expected: No significant regressions (within ±10% variance)

# Acceptance criteria:
# - All pre-existing tests pass
# - No new JavaScript errors in console
# - Performance metrics within acceptable range
# - Dependent features (CSV, bulk ops, single-symbol) unaffected
```

## Final Validation Checklist

### Technical Validation

- [ ] All 5 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] Regression tests pass: Existing functionality preserved
- [ ] No linting errors: `ruff check src/ web/static/js/`
- [ ] No formatting issues: `ruff format src/ web/static/js/ --check`
- [ ] Unit tests pass (if unit tests exist for admin routes)

### Change Validation

- [ ] Universe dropdown populated from cache_entries (Task 1A endpoint working)
- [ ] Symbol count preview shown before load trigger
- [ ] Bulk universe load submits to Redis successfully
- [ ] Progress tracking shows N/Total symbols with individual failures
- [ ] Existing single-symbol load still works (regression-free)
- [ ] Existing CSV load still works (regression-free)
- [ ] Existing bulk operations still work (regression-free)
- [ ] Cache_entries cleanup script executed successfully (Task 2A)
- [ ] All updated_at timestamps now non-NULL
- [ ] All names follow Title Case convention

### Impact Validation

- [ ] Dashboard page load time <1000ms (within performance target)
- [ ] Universe dropdown population <100ms (CacheControl in-memory)
- [ ] No breakage points triggered (template rendering, Redis pub-sub working)
- [ ] Dependency analysis verified (all callers still work)
- [ ] Affected tests updated and passing (if any)
- [ ] Integration points tested (Redis channels, cache_entries queries)

### TickStock Architecture Validation

- [ ] Component role preserved (TickStockAppV2 = Consumer)
- [ ] Redis pub-sub patterns correct (tickstock.jobs.data_load channel working)
- [ ] Database access mode followed (read-only for cache_entries)
- [ ] Dashboard load latency target met (<1000ms)
- [ ] No architectural violations detected (no pattern detection logic added)

### Code Quality Validation

- [ ] Follows existing codebase patterns (bulk operations, CSV loading, polling)
- [ ] File structure limits followed (admin_historical_data_redis.py <1000 lines)
- [ ] Function limits followed (new functions <50 lines each)
- [ ] Naming conventions preserved (snake_case, meaningful names)
- [ ] Anti-patterns avoided (no hardcoded credentials, no direct DB queries in routes)
- [ ] Code is self-documenting (clear function names, docstrings)
- [ ] No "Generated by Claude" comments

### Documentation & Deployment

- [ ] Audit report created: `docs/database/cache_entries_audit_report_sprint55.md`
- [ ] Maintenance procedures created: `docs/database/cache_entries_maintenance.md`
- [ ] SQL cleanup script tested: `scripts/sql/cache_entries_cleanup_sprint55.sql`
- [ ] Sprint 55 README updated with completion status
- [ ] No breaking changes introduced (backward compatibility verified)

---

## Anti-Patterns to Avoid (Change-Specific)

### Modification Anti-Patterns

- ❌ **Don't modify legacy admin_historical_data.py**
  - admin_historical_data_redis.py is the ACTIVE version (registered in app.py:2276)
  - Legacy file exists but is NOT used
  - Violation: Adding endpoints to wrong file (changes won't be accessible)

- ❌ **Don't query cache_entries directly in route handler**
  - Use CacheControl singleton (already loads cache_entries at startup)
  - Direct DB query adds latency to page load (500ms → 1000ms+)
  - Violation: `CacheEntry.query.filter_by(type='etf_universe').all()` in route

- ❌ **Don't break universe key format**
  - Must use "universe_type:key" format (e.g., "etf_universe:etf_core")
  - CacheControl.get_universe_tickers() expects this format
  - Violation: Passing "etf_core" without type prefix → returns empty list

- ❌ **Don't assume JSONB value structure**
  - cache_entries.value can be array OR object with 'symbols' key
  - Must handle both formats when extracting symbols
  - Violation: `value['symbols']` without checking `isinstance(value, dict)`

- ❌ **Don't skip CSRF token in AJAX POST**
  - Flask CSRF protection requires token in POST headers
  - Missing token → 400 Bad Request
  - Violation: `fetch('/endpoint', {method: 'POST'})` without X-CSRFToken header

### TickStock-Specific Change Anti-Patterns

- ❌ **Don't change Redis message format**
  - TickStockPL expects specific fields: job_id, job_type, symbols[], years
  - Breaking message format requires coordinated TickStockPL update
  - Violation: Adding required fields not expected by TickStockPL

- ❌ **Don't skip subscriber count check**
  - redis.publish() returns 0 if no subscribers (TickStockPL down)
  - Silent failure → admin thinks job submitted but nothing happens
  - Violation: Not logging warning when subscriber_count == 0

- ❌ **Don't modify available_universes template variable structure**
  - Template expects dict: {key: display_name}
  - Changing to list breaks existing template rendering
  - Violation: `available_universes = [{'key': 'SP500', ...}]` (should be dict)

- ❌ **Don't add database writes to TickStockAppV2**
  - TickStockAppV2 is CONSUMER role (read-only database access)
  - Pattern detection, data processing = TickStockPL (PRODUCER role)
  - Violation: INSERT/UPDATE queries in admin routes

- ❌ **Don't duplicate polling logic**
  - startPollingJobStatus() already exists in historical_data.js
  - Reuse existing method for universe load polling
  - Violation: Writing new polling function with different interval/timeout

- ❌ **Don't skip performance baseline documentation**
  - Must measure dashboard load time BEFORE changes (<500ms)
  - Measure again AFTER changes to verify <1000ms target
  - Violation: "It feels fast enough" without actual measurements

- ❌ **Don't modify SQL cleanup script after execution**
  - Document executed SQL in audit report for reproducibility
  - Version control tracks changes for future reference
  - Violation: Running ad-hoc SQL without documenting in script file

---

## Confidence Score: 9/10

**Rationale**:
- ✅ **Complete Context**: All current implementation analyzed (routes, templates, JavaScript, database)
- ✅ **Dependency Mapping**: All callers identified (tests, templates, JavaScript, Redis)
- ✅ **Impact Analysis**: Breakage points documented (low risk, additive change)
- ✅ **Pattern Consistency**: Following existing bulk operations and CSV loading patterns
- ✅ **Performance Baseline**: Current metrics documented (<500ms dashboard, 1-sec polling)
- ✅ **Backward Compatibility**: No breaking changes (all endpoints preserved)
- ⚠️ **Minor Uncertainty**: CacheControl singleton behavior during cache refresh (need to verify app restart required or refresh API exists)

**One-Pass Success Likelihood**: HIGH (95%+)
- Additive change (no modifications to existing endpoints)
- Following established patterns (bulk operations, CSV loading, Redis job submission)
- Comprehensive dependency analysis (all callers identified)
- Clear BEFORE/AFTER code examples for all changes
- Validation gates at 5 levels (syntax, unit, integration, TickStock-specific, regression)

**Potential Issues**:
1. CacheControl refresh: May need app restart to see new cache_entries (minor - documented in gotchas)
2. TickStockPL job processing: Assumes TickStockPL handles 'universe_bulk_load' job_type (likely safe - processes same as bulk loads)
3. Template rendering: If available_universes structure changes, template breaks (mitigated - keeping dict structure)

**Mitigation**:
- All potential issues documented in "Known Gotchas" section
- Regression testing includes verification of TickStockPL connectivity
- Template changes preserve backward compatibility (dict structure maintained)
