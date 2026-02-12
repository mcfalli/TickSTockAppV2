name: "Sprint 73: Process Stock Analysis - Independent Analysis Admin Page"
description: |
  Create independent admin page for manually triggering pattern/indicator analysis
  on selected stocks/universes, with background job execution and real-time
  progress tracking. Unlocks Sprint 68-72 analysis capabilities for on-demand use.

---

## Goal

**Feature Goal**: Enable administrators to manually trigger pattern and indicator analysis for any universe or symbol list through a dedicated admin interface, with real-time progress tracking and result visualization.

**Deliverable**:
- Admin page at `/admin/process-analysis` with universe selector, analysis options, and progress tracking
- Background job execution system with real-time status polling
- Integration with Sprint 68-72 analysis services (patterns, indicators, database)
- Job history and active job monitoring

**Success Definition**:
- Administrators can analyze 100+ symbols via universe selection
- Real-time progress bar updates every 1-2 seconds
- Analysis results stored in database (`daily_patterns`, `indicator_results`)
- Job completion displays success summary (symbols analyzed, patterns detected, indicators calculated)
- Zero regressions in existing Sprint 68-72 functionality

## User Persona (if applicable)

**Target User**: TickStock Administrators

**Use Case**: On-demand analysis of stock universes to populate pattern/indicator data without waiting for scheduled processing or re-importing historical data

**User Journey**:
1. Navigate to **Process Stock Analysis** in admin navigation
2. Select universe (SPY, nasdaq100, dow30) OR enter comma-separated symbols
3. Choose analysis type: Patterns, Indicators, or Both (default)
4. Select timeframe: Daily, Hourly, Weekly, Monthly
5. Click "🔬 Run Analysis" button
6. Watch real-time progress bar with symbol updates
7. View completion summary: "102 symbols analyzed, 45 patterns detected, 816 indicators calculated"
8. Results immediately available in database for dashboards

**Pain Points Addressed**:
- **Manual data refresh**: No need to re-import historical data to run fresh analysis
- **Targeted processing**: Analyze specific universes without full system processing run
- **Testing & validation**: Quickly test pattern/indicator changes on sample universe
- **Data maintenance**: Backfill missing analysis results for specific symbols

## Why

- **Business Value**: Unlocks $100K+ investment in Sprint 68-72 analysis engine for immediate use
- **Integration**: Completes Sprint 68-72 migration by providing UI access to analysis services
- **User Impact**: Reduces analysis workflow from "import → wait → analyze" to "analyze now"
- **Architecture**: Consumer-side analysis execution (AppV2 role) with database result storage
- **Foundation**: Establishes pattern for Sprint 74 (Historical Import Integration)

**Problems Solved**:
- Sprint 68-72 analysis services have no UI trigger mechanism (orphaned APIs)
- No way to manually analyze symbols without re-importing historical data
- No visibility into analysis job progress (batch operations run silently)
- No admin interface for testing pattern/indicator implementations

## What

### User-Visible Behavior

**Admin Page Features**:
- **Universe Selector**: Dropdown with all available universes (SPY, nasdaq100, QQQ, dow30, etc.)
- **Symbol Input**: Alternative comma-separated symbol entry (AAPL, NVDA, TSLA)
- **Analysis Options**:
  - Patterns Only (8 patterns: Doji, Hammer, Engulfing, Shooting Star, Harami, Morning/Evening Star)
  - Indicators Only (8 indicators: SMA, RSI, MACD, EMA, ATR, Bollinger Bands, Stochastic, ADX)
  - Both (default): All patterns + indicators
- **Timeframe Selection**: Daily, Hourly, Weekly, Monthly (radio buttons)
- **Real-Time Progress**: Bootstrap progress bar with percentage and current symbol
- **Active Jobs List**: Card-based display of running jobs with cancel buttons
- **Recent Jobs History**: Last 10 completed jobs with success/failure summaries

**Technical Behavior**:
- Background thread processes symbols sequentially
- Progress updates every symbol (1-2 second intervals for typical symbol throughput)
- Results stored in `daily_patterns` and `indicator_results` tables
- Job lifecycle: Queued → Running → Completed/Failed/Cancelled
- In-memory job tracking (active_jobs dict, job_history list)

### Success Criteria

- [ ] Admin page accessible at `/admin/process-analysis` (admin-only)
- [ ] Universe selector populates from RelationshipCache
- [ ] Symbol input accepts comma-separated tickers (AAPL, NVDA, TSLA)
- [ ] Analysis type checkboxes: Patterns, Indicators, Both (default)
- [ ] Timeframe radio buttons: Daily, Hourly, Weekly, Monthly
- [ ] Job submission returns job_id and starts background thread
- [ ] Progress bar polls every 2 seconds via GET `/admin/process-analysis/job-status/<job_id>`
- [ ] Progress displays: percentage, current symbol, symbols_completed/symbols_total
- [ ] Completion notification shows: symbols analyzed, patterns detected, indicators calculated
- [ ] Analysis results stored in database with timestamps
- [ ] Active jobs display with real-time status updates
- [ ] Job cancellation stops processing and marks job cancelled
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] Pattern flow tests maintain Sprint 68-72 baseline (zero regressions)

## All Needed Context

### Context Completeness Check

_"If someone knew nothing about this codebase, would they have everything needed to implement this successfully?"_

**Answer**: YES - This PRP includes:
- ✅ Complete HTML template patterns from Historical Data dashboard
- ✅ Flask route patterns with background threading from existing admin routes
- ✅ JavaScript polling logic with progress bar updates (actual implementation)
- ✅ Sprint 68-72 service integration (AnalysisService, OHLCVDataService, RelationshipCache)
- ✅ Database result storage patterns
- ✅ Job lifecycle management (in-memory dict tracking)
- ✅ CSRF token handling patterns
- ✅ Error handling and validation patterns
- ✅ External Flask threading and Bootstrap documentation with URLs

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: TickStockAppV2
  role: Consumer + Analyzer (Sprint 68 established)

  redis_channels:
    subscribe:
      # NOT USED in Sprint 73 - Analysis runs directly (no Redis pub-sub)
      # Future Sprint 74 may publish completion events
    publish:
      # Future Sprint 74: tickstock:analysis:complete
      # Format: {job_id, symbols_analyzed, patterns_detected, indicators_calculated}

  database_access:
    mode: read-write
    read_tables:
      - ohlcv_daily, ohlcv_hourly, ohlcv_1min, ohlcv_weekly, ohlcv_monthly (OHLCV data)
      - definition_groups, group_memberships (universe symbol loading)
      - symbols (symbol metadata)
    write_tables:
      - daily_patterns (pattern detection results)
      - indicator_results (indicator calculation results)
      - job_executions (optional: job tracking table, Sprint 69 background jobs)
    queries:
      - OHLCV fetch: 5.59ms per symbol (Sprint 72 actual)
      - Universe symbols: <1ms cache hit (Sprint 61)
      - Result storage: INSERT INTO daily_patterns/indicator_results

  websocket_integration:
    broadcast_to: NONE (Sprint 73 scope)
    # Future Sprint 75+: Broadcast analysis completion to active admin sessions

  tickstockpl_api:
    endpoints: NONE (Sprint 73 operates independently)
    # Analysis runs entirely in AppV2 (Sprint 68 architecture)

  performance_targets:
    - metric: "Symbol analysis"
      target: "<2s per symbol (patterns + indicators)"

    - metric: "Universe analysis (100 symbols)"
      target: "<4 minutes total"

    - metric: "Job submission"
      target: "<100ms (thread spawn)"

    - metric: "Job status polling"
      target: "<50ms (dict lookup)"

    - metric: "Progress bar latency"
      target: "<2s update interval"
```

### Documentation & References

```yaml
# MUST READ - Critical for implementation

# 1. EXISTING ADMIN DASHBOARD PATTERNS (PRIMARY REFERENCE)
- file: web/templates/admin/historical_data_dashboard.html
  lines: "1-800 (complete template)"
  why: "Exact HTML structure, CSS, progress bar UI for Sprint 73"
  pattern: |
    - Admin navigation (lines 223-233)
    - Job controls form (lines 401-564)
    - Progress bar with polling (lines 550-563)
    - Active jobs display (lines 332-397)
    - Status badges and CSS (lines 158-218)
  gotcha: "Use csrf_token() for CSRF protection (line 405)"
  critical: "Progress bar: progress-bar-striped + progress-bar-animated classes"

- file: src/api/rest/admin_historical_data.py
  lines: "1-935 (complete route file)"
  why: "Background job execution pattern, threading, job tracking"
  pattern: |
    - In-memory job tracking (lines 50-52)
    - Job submission route (lines 102-246)
    - Background thread function (lines 169-235)
    - Job status endpoint (lines 248-268)
    - Job cancellation (lines 270-287)
  gotcha: "Thread.daemon = True required for app shutdown (line 238)"
  critical: "Job data updated in-place, thread-safe under GIL for simple ops"

- file: web/static/js/admin/historical_data.js
  lines: "1-929 (complete JavaScript file)"
  why: "Complete polling logic, progress bar updates, form submission"
  pattern: |
    - Job polling with setTimeout (lines 180-247)
    - Progress bar updates (lines 249-286)
    - Universe dropdown loading (lines 497-587)
    - CSRF token retrieval (lines 465-492)
    - Form submission (lines 622-743)
  gotcha: "Poll interval: 1000ms (1 sec), max duration: 300000ms (5 min)"
  critical: "setTimeout > setInterval (ensures request completion before next poll)"

# 2. SPRINT 68-72 ANALYSIS INTEGRATION (SERVICE LAYER)
- file: src/analysis/services/analysis_service.py
  lines: "1-382 (complete service)"
  why: "Main orchestration for pattern/indicator analysis"
  pattern: |
    analyze_symbol(symbol, data, timeframe, indicators, patterns)
    Returns: {
      'indicators': {'sma': {'value': 150.5}, 'rsi': {'value': 65.3}},
      'patterns': {'doji': {'detected': True, 'confidence': 0.85}}
    }
  gotcha: "Pass pd.DataFrame with [open, high, low, close, volume] columns"
  critical: "NO FALLBACK policy - raises exceptions on missing indicator/pattern"

- file: src/analysis/data/ohlcv_data_service.py
  lines: "1-387 (complete service)"
  why: "Database OHLCV data access (Sprint 72)"
  pattern: |
    get_ohlcv_data(symbol, timeframe, limit=250) → pd.DataFrame
    get_universe_ohlcv_data(symbols, timeframe, limit=250) → dict[symbol, DataFrame]
  gotcha: "Timeframe: 'daily', 'hourly', '1min', 'weekly', 'monthly'"
  critical: "Actual performance: 5.59ms per symbol (Sprint 72 validated)"

- file: src/core/services/relationship_cache.py
  lines: "1-1024 (complete cache service)"
  why: "Universe symbol loading (Sprint 60-61)"
  pattern: |
    get_universe_symbols('nasdaq100') → list[str] (102 symbols)
    get_universe_symbols('SPY:nasdaq100') → list[str] (~518 distinct symbols)
  gotcha: "Multi-universe join: colon-separated (SPY:QQQ:dow30)"
  critical: "<1ms cache hit performance (Sprint 61 validated)"

- file: src/api/models/analysis_models.py
  lines: "1-263 (Pydantic v2 models)"
  why: "Request/response validation models (Sprint 71)"
  pattern: |
    SymbolAnalysisRequest(symbol, timeframe, indicators, patterns)
    SymbolAnalysisResponse(symbol, timeframe, indicators, patterns, metadata)
  gotcha: "Use Pydantic v2: BaseModel, Field, ConfigDict"
  critical: "Validation errors return 400, not 500"

# 3. FLASK THREADING & BACKGROUND JOBS (EXTERNAL DOCS)
- url: "https://flask.palletsprojects.com/en/stable/appcontext/"
  section: "The Application Context"
  why: "Flask app context must be passed to background threads"
  critical: |
    WRONG: Thread(target=task, args=(current_app,))
    CORRECT: Thread(target=task, args=(app,))
    Use: with app.app_context(): inside background function
  gotcha: "current_app is thread-local proxy, doesn't work across threads"

- url: "https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xxii-background-jobs"
  section: "Complete Tutorial"
  why: "Production Flask threading patterns"
  critical: "Use daemon=True for background threads (killed on app exit)"
  gotcha: "Database sessions are thread-local (don't share across threads)"

- url: "https://realpython.com/python-gil/"
  section: "Python GIL and Threading"
  why: "Understanding GIL impact on thread safety"
  critical: "GIL makes simple dict operations atomic, but not complex operations"
  gotcha: "I/O-bound operations (DB, API) release GIL - threading is appropriate"

# 4. BOOTSTRAP PROGRESS BAR (EXTERNAL DOCS)
- url: "https://getbootstrap.com/docs/5.3/components/progress/#animated-stripes"
  section: "Animated Stripes"
  why: "Official Bootstrap progress bar documentation"
  pattern: |
    <div class="progress">
      <div class="progress-bar progress-bar-striped progress-bar-animated"
           style="width: 0%">0%</div>
    </div>
  critical: "Classes: progress-bar-striped + progress-bar-animated for animation"
  gotcha: "CSS transition: width 0.6s ease (smooth updates)"

- url: "https://www.w3schools.com/howto/howto_js_progressbar.asp"
  section: "How TO - JavaScript Progress Bar"
  why: "JavaScript progress bar update patterns"
  pattern: |
    progressBar.style.width = percentage + '%';
    progressBar.textContent = percentage + '%';
    progressBar.setAttribute('aria-valuenow', percentage);
  critical: "Update width, text content, and aria-valuenow for accessibility"

# 5. EXISTING TEST PATTERNS (VALIDATION)
- file: tests/integration/run_integration_tests.py
  lines: "1-150"
  why: "Integration test runner (MANDATORY before commits)"
  pattern: "python run_tests.py (expected: 2+ tests passing, ~30s runtime)"
  critical: "Pattern flow tests MUST pass to validate zero regressions"

- file: tests/unit/api/test_analysis_routes.py
  lines: "1-424"
  why: "API endpoint testing patterns (Sprint 71)"
  pattern: "Mock AnalysisService, OHLCVDataService, test status codes"
  critical: "Use @patch decorators for service mocks"
```

### Current Codebase tree (relevant sections)

```
TickStockAppV2/
├── src/
│   ├── api/
│   │   ├── rest/
│   │   │   ├── admin_historical_data.py       # REFERENCE: Background job pattern
│   │   │   └── admin_monitoring.py
│   │   └── routes/
│   │       └── analysis_routes.py              # EXISTS: Sprint 71 analysis API
│   ├── analysis/
│   │   ├── services/
│   │   │   └── analysis_service.py             # EXISTS: Sprint 68 main service
│   │   ├── data/
│   │   │   └── ohlcv_data_service.py           # EXISTS: Sprint 72 database access
│   │   ├── patterns/                           # EXISTS: Sprint 68-69 (8 patterns)
│   │   ├── indicators/                         # EXISTS: Sprint 68, 70 (8 indicators)
│   │   └── exceptions.py                       # EXISTS: Exception hierarchy
│   ├── core/
│   │   └── services/
│   │       └── relationship_cache.py           # EXISTS: Sprint 60-61 universe loading
│   └── app.py                                  # UPDATE: Register new blueprint
├── web/
│   ├── templates/
│   │   └── admin/
│   │       ├── historical_data_dashboard.html  # REFERENCE: Complete UI pattern
│   │       └── base_admin.html                 # UPDATE: Add navigation link
│   └── static/
│       ├── js/
│       │   └── admin/
│       │       └── historical_data.js          # REFERENCE: Complete polling logic
│       └── css/
│           └── main.css                        # UPDATE: May need admin styles
└── tests/
    ├── integration/
    │   └── run_integration_tests.py            # VALIDATE: Run before commit
    └── unit/
        └── api/
            └── test_analysis_routes.py         # REFERENCE: Testing pattern
```

### Desired Codebase tree with files to be added

```
TickStockAppV2/
├── src/
│   └── api/
│       └── rest/
│           └── admin_process_analysis.py       # NEW: ~350 lines
│               # Routes:
│               # - admin_process_analysis_dashboard() → renders page
│               # - admin_trigger_analysis() → POST job submission
│               # - admin_get_analysis_job_status() → GET polling endpoint
│               # - admin_cancel_analysis_job() → POST job cancellation
│               # Contains:
│               # - active_jobs = {} (in-memory job tracking)
│               # - job_history = [] (completed jobs list)
│               # - run_analysis_job(job_data) → background thread function
├── web/
│   ├── templates/
│   │   └── admin/
│   │       └── process_analysis_dashboard.html # NEW: ~450 lines
│   │           # Sections:
│   │           # - Admin navigation (copy from historical_data.html)
│   │           # - Universe selector dropdown
│   │           # - Symbol input field (comma-separated)
│   │           # - Analysis type checkboxes (patterns, indicators, both)
│   │           # - Timeframe radio buttons (daily, hourly, weekly, monthly)
│   │           # - Progress bar container (Bootstrap striped animated)
│   │           # - Active jobs list (card-based with cancel buttons)
│   │           # - Recent jobs history (last 10 jobs)
│   └── static/
│       └── js/
│           └── admin/
│               └── process_analysis.js         # NEW: ~350 lines
│                   # Functions:
│                   # - submitAnalysisJob() → form submission
│                   # - startPollingJobStatus(jobId) → recursive setTimeout polling
│                   # - updateJobStatus(jobId, status) → progress bar updates
│                   # - loadUniverses() → populate dropdown from RelationshipCache
│                   # - getCSRFToken() → CSRF token retrieval
│                   # - showNotification(message, type) → success/error alerts
└── tests/
    └── integration/
        └── test_process_analysis_workflow.py   # NEW: ~200 lines
            # Tests:
            # - test_job_submission() → POST returns job_id
            # - test_job_status_polling() → GET returns progress
            # - test_analysis_execution() → background thread completes
            # - test_results_stored() → database has pattern/indicator rows
            # - test_job_cancellation() → cancelled job stops processing
```

### Known Gotchas of our codebase & Library Quirks

```python
# CRITICAL: Flask Application Context (Sprint 73 MUST KNOW)
# Flask stores application state in current_app context at RUNTIME
# Background threads do NOT have access to current_app (thread-local proxy)
# PATTERN: Pass Flask `app` object (not current_app) to background threads

# WRONG: Will fail with "RuntimeError: Working outside of application context"
def background_task():
    from flask import current_app
    redis_client = current_app.redis_client  # ❌ FAILS - no context

# CORRECT: Pass app object and establish context
def background_task(app):
    with app.app_context():
        # Now Flask context is available
        redis_client = app.redis_client  # ✅ WORKS

# Thread creation pattern:
thread = Thread(target=run_analysis_job, args=(job, app))  # Pass app object
thread.daemon = True
thread.start()

# Inside run_analysis_job:
def run_analysis_job(job_data, app):
    with app.app_context():
        # Establish Flask context for this thread
        # Now can access database, services, etc.
        service = AnalysisService()
        # ...


# CRITICAL: Python GIL & Thread Safety
# Python's Global Interpreter Lock (GIL) makes SIMPLE dict operations atomic
# Safe: job_data['status'] = 'running' (single assignment)
# Safe: job_data['log_messages'].append(msg) (list append)
# Safe: job_data['progress'] = 50 (single value update)
# UNSAFE: if job_data['status'] != 'cancelled': job_data['status'] = 'running'
#         (check-then-act is NOT atomic, race condition possible)

# For Sprint 73 in-memory dict tracking, GIL provides sufficient safety
# Production would use Redis for distributed job tracking


# CRITICAL: Database Sessions are Thread-Local
# SQLAlchemy sessions are automatically thread-local (scoped_session)
# Each thread gets its own database connection from the pool
# DO NOT share database connections across threads
# PATTERN: Create fresh service instances in each thread

# Inside background thread:
def run_analysis_job(job_data, app):
    with app.app_context():
        # Each service call gets its own database connection
        data_service = OHLCVDataService()  # Creates new connection
        analysis_service = AnalysisService()

        for symbol in symbols:
            data = data_service.get_ohlcv_data(symbol, 'daily')
            result = analysis_service.analyze_symbol(data, symbol, 'daily')
            # ...


# CRITICAL: Thread.daemon = True (REQUIRED)
# Daemon threads are killed when main app exits
# Without daemon=True, background threads prevent Flask shutdown
thread = Thread(target=run_analysis_job, args=(job, app))
thread.daemon = True  # ✅ CRITICAL - allows clean shutdown
thread.start()


# CRITICAL: Timeframe Validation (Sprint 72 Pattern)
# Valid timeframes: 'daily', 'hourly', '1min', 'weekly', 'monthly'
# Database tables: ohlcv_daily, ohlcv_hourly, ohlcv_1min, ohlcv_weekly, ohlcv_monthly
# Invalid timeframe raises ValueError from OHLCVDataService

valid_timeframes = ['daily', 'hourly', '1min', 'weekly', 'monthly']
if timeframe not in valid_timeframes:
    return jsonify({'error': f'Invalid timeframe: {timeframe}'}), 400


# CRITICAL: OHLCV Data Format (Sprint 68 Pattern)
# DataFrame must have columns: [open, high, low, close, volume]
# Index: 'date' (timestamp), sorted ASCENDING (oldest first)
# Missing columns or wrong index raises DataValidationError

# Correct format from OHLCVDataService:
data = data_service.get_ohlcv_data('AAPL', 'daily', limit=250)
# Returns: pd.DataFrame indexed by 'date', columns [open, high, low, close, volume]


# CRITICAL: NO FALLBACK Policy (Sprint 68 Architecture)
# Pattern/indicator loaders raise exceptions on missing implementations
# DO NOT catch and ignore - this hides implementation errors
# Exceptions: InvalidIndicatorError, InvalidPatternError, DynamicLoadingError

try:
    result = analysis_service.analyze_symbol(data, symbol, timeframe,
                                            indicators=['invalid_name'])
except InvalidIndicatorError as e:
    # Handle gracefully - log error, mark symbol failed
    job_data['failed_symbols'].append(symbol)
    job_data['log_messages'].append(f"[FAIL] {symbol}: {str(e)}")


# CRITICAL: RelationshipCache Universe Loading (Sprint 61 Pattern)
# Single universe: get_universe_symbols('nasdaq100') → 102 symbols
# Multi-universe join: get_universe_symbols('SPY:nasdaq100') → ~518 distinct symbols
# Colon-separated for DISTINCT union of all universes

cache = get_relationship_cache()

# Single universe
symbols = cache.get_universe_symbols('SPY')  # 504 ETF holdings

# Multi-universe join (distinct union)
symbols = cache.get_universe_symbols('SPY:nasdaq100:dow30')  # ~522 distinct symbols


# CRITICAL: CSRF Token Handling (Sprint 62 Pattern)
# Primary: Hidden input field csrf_token
# Fallback: Meta tag csrf-token
# Fallback: Cookie csrf_token

# Template (Jinja2):
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>

# JavaScript retrieval:
function getCSRFToken() {
    const input = document.querySelector('input[name="csrf_token"]');
    if (input) return input.value;

    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.content;

    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrf_token='));
    return cookie ? cookie.split('=')[1] : '';
}


# CRITICAL: JavaScript Polling Best Practice
# Use setTimeout (recursive) instead of setInterval
# setInterval can queue requests if response takes longer than interval
# setTimeout ensures one request completes before next starts

// WRONG: setInterval can overflow with slow responses
setInterval(async () => {
    const response = await fetch('/api/status');
    updateUI(await response.json());
}, 1000);

// CORRECT: setTimeout waits for completion
async function poll(jobId) {
    try {
        const response = await fetch(`/api/status/${jobId}`);
        const data = await response.json();
        updateUI(data);

        if (data.progress < 100) {
            setTimeout(() => poll(jobId), 1000);  // Only after response
        }
    } catch (error) {
        console.error('Poll error:', error);
        setTimeout(() => poll(jobId), 2000);  // Longer delay on error
    }
}

poll('job-123');


# CRITICAL: Progress Bar Bootstrap Classes
# Required classes: progress-bar-striped + progress-bar-animated
# Without both, animation won't work

<div class="progress">
    <div class="progress-bar progress-bar-striped progress-bar-animated"
         id="progressBar" style="width: 0%">0%</div>
</div>

// Update via JavaScript
progressBar.style.width = '50%';
progressBar.textContent = '50%';
progressBar.setAttribute('aria-valuenow', 50);


# CRITICAL: Admin Route Decorators (Security)
# ALL admin routes MUST have @login_required and @admin_required

from flask_login import login_required
from src.utils.auth_decorators import admin_required

@app.route('/admin/process-analysis')
@login_required       # ✅ REQUIRED: Ensures user logged in
@admin_required      # ✅ REQUIRED: Ensures admin role
def admin_process_analysis_dashboard():
    # ...


# CRITICAL: Job ID Format (Sprint 62 Pattern)
# Format: {type}_{timestamp}_{counter}
# Example: analysis_1707654321_0
# Timestamp ensures uniqueness, counter handles same-second submissions

job_id = f"analysis_{int(time.time())}_{len(active_jobs)}"


# CRITICAL: Job Status Lifecycle States
# Valid states: 'queued', 'running', 'completed', 'failed', 'cancelled'
# State transitions:
#   'queued' → 'running' (thread starts)
#   'running' → 'completed' (all symbols processed successfully)
#   'running' → 'failed' (unhandled exception)
#   'running' → 'cancelled' (user cancels via API)

# Cancellation check in background thread:
for symbol in symbols:
    if job_data['status'] == 'cancelled':
        break  # Stop processing
    # Process symbol...


# CRITICAL: Log Messages Truncation
# Keep only last 20 log messages to prevent memory bloat
# Job status endpoint returns truncated logs

return jsonify({
    'log_messages': job.get('log_messages', [])[-20:]  # Last 20 only
})


# CRITICAL: TickStockAppV2 Role Separation (Sprint 68 Architecture)
# AppV2 = Consumer + Analyzer (Sprint 68 established)
# Analysis runs IN AppV2 (Sprint 68-72 services)
# Results written to database (daily_patterns, indicator_results)
# NO REDIS PUB-SUB for analysis execution (runs directly)

# This is CORRECT for Sprint 73:
# - Analysis runs synchronously in background thread
# - Results written directly to database
# - No TickStockPL involvement (Sprint 68 migrated logic to AppV2)
```

## Implementation Blueprint

### Data models and structure

**Job Data Structure** (Python dict):
```python
job = {
    'id': 'analysis_1707654321_0',        # Unique job identifier
    'status': 'queued',                    # queued, running, completed, failed, cancelled
    'type': 'analysis',                    # Job type for filtering
    'universe_key': 'nasdaq100',           # Universe selected (or None if symbols)
    'symbols': ['AAPL', 'NVDA', 'TSLA'],  # List of symbols to analyze
    'analysis_type': 'both',               # 'patterns', 'indicators', 'both'
    'timeframe': 'daily',                  # 'daily', 'hourly', '1min', 'weekly', 'monthly'
    'created_at': datetime.now(),          # Timestamp when job created
    'created_by': 'admin_username',        # Who initiated the job
    'progress': 0,                         # 0-100 percentage complete
    'current_symbol': None,                # Currently processing symbol (for UI)
    'symbols_completed': 0,                # Count of symbols processed
    'symbols_total': 102,                  # Total symbols to process
    'patterns_detected': 0,                # Cumulative pattern count
    'indicators_calculated': 0,            # Cumulative indicator count
    'failed_symbols': [],                  # List of failed symbols with reasons
    'log_messages': [],                    # Progress log (last 20 messages)
    'completed_at': None                   # Timestamp when finished (or None)
}
```

**Job Status API Response** (JSON):
```json
{
  "id": "analysis_1707654321_0",
  "status": "running",
  "progress": 45,
  "current_symbol": "NVDA",
  "symbols_completed": 45,
  "symbols_total": 102,
  "patterns_detected": 12,
  "indicators_calculated": 360,
  "failed_symbols": [],
  "log_messages": [
    "Started analyzing 102 symbols",
    "[OK] AAPL: 8 patterns, 8 indicators calculated",
    "[OK] NVDA: 2 patterns, 8 indicators calculated",
    "..."
  ],
  "completed_at": null
}
```

**Database Result Storage**:
```python
# Sprint 68-72 tables (already exist)
# 1. daily_patterns table
INSERT INTO daily_patterns (
    symbol, pattern_name, timeframe, detected_at,
    confidence, metadata, created_at
) VALUES (%s, %s, %s, %s, %s, %s, %s);

# 2. indicator_results table
INSERT INTO indicator_results (
    symbol, indicator_name, timeframe, calculated_at,
    value, value_data, indicator_type, created_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
```

### Implementation Tasks (ordered by dependencies)

```yaml
# PHASE 1: Backend Foundation (Day 1)
Task 1: CREATE src/api/rest/admin_process_analysis.py
  - IMPLEMENT: Flask route file with blueprint
  - FOLLOW pattern: src/api/rest/admin_historical_data.py (lines 1-935)
  - NAMING: admin_process_analysis_bp Blueprint
  - ROUTES:
    - GET /admin/process-analysis → admin_process_analysis_dashboard()
    - POST /admin/process-analysis/trigger → admin_trigger_analysis()
    - GET /admin/process-analysis/job-status/<job_id> → admin_get_analysis_job_status()
    - POST /admin/process-analysis/job/<job_id>/cancel → admin_cancel_analysis_job()
  - PLACEMENT: src/api/rest/ directory
  - IN-MEMORY TRACKING:
    - active_jobs = {} (module-level dict)
    - job_history = [] (module-level list)
  - GOTCHA: Use @login_required and @admin_required decorators
  - CRITICAL: Pass Flask app object to background threads (not current_app)

Task 2: IMPLEMENT background thread function (run_analysis_job)
  - LOCATION: Inside src/api/rest/admin_process_analysis.py
  - SIGNATURE: def run_analysis_job(job_data: dict, app: Flask)
  - PATTERN: admin_historical_data.py lines 169-235 (complete pattern)
  - FLOW:
    1. Mark job as 'running'
    2. with app.app_context(): establish Flask context
    3. Initialize services (AnalysisService, OHLCVDataService)
    4. Loop through symbols with cancellation check
    5. Fetch OHLCV data via OHLCVDataService
    6. Call AnalysisService.analyze_symbol()
    7. Store results to database (daily_patterns, indicator_results)
    8. Update progress: job_data['progress'] = int((i / total) * 100)
    9. Append log messages: job_data['log_messages'].append(...)
    10. Mark as 'completed' when done
    11. Move to job_history and delete from active_jobs
  - GOTCHA: Check job_data['status'] == 'cancelled' in loop
  - CRITICAL: Each symbol ~2s (patterns + indicators), total ~4min for 100 symbols

Task 3: IMPLEMENT job submission route (admin_trigger_analysis)
  - LOCATION: src/api/rest/admin_process_analysis.py
  - HTTP: POST /admin/process-analysis/trigger
  - REQUEST: JSON with {universe_key, symbols, analysis_type, timeframe, submitted_by}
  - VALIDATION:
    - Require universe_key XOR symbols (not both)
    - Validate timeframe in ['daily', 'hourly', '1min', 'weekly', 'monthly']
    - Validate analysis_type in ['patterns', 'indicators', 'both']
  - FLOW:
    1. Parse request parameters
    2. Load symbols from RelationshipCache if universe_key provided
    3. Create job dict with job_id, status='queued', timestamps
    4. Add to active_jobs dict
    5. Spawn Thread(target=run_analysis_job, args=(job, app), daemon=True)
    6. Start thread: thread.start()
    7. Return JSON: {success: true, job_id: '...', symbols_count: 102}
  - GOTCHA: Universe join: cache.get_universe_symbols('SPY:nasdaq100')
  - CRITICAL: thread.daemon = True (allows clean shutdown)

Task 4: IMPLEMENT job status polling route (admin_get_analysis_job_status)
  - LOCATION: src/api/rest/admin_process_analysis.py
  - HTTP: GET /admin/process-analysis/job-status/<job_id>
  - PATTERN: admin_historical_data.py lines 248-268
  - FLOW:
    1. Check active_jobs for job_id
    2. If not found, check job_history
    3. If still not found, return 404
    4. Return JSON with progress, status, current_symbol, log_messages[-20:]
  - RESPONSE: {id, status, progress, current_symbol, symbols_completed, symbols_total, patterns_detected, indicators_calculated, log_messages, completed_at}
  - GOTCHA: Only return last 20 log messages (prevent large responses)
  - CRITICAL: <50ms response time (simple dict lookup)

Task 5: IMPLEMENT job cancellation route (admin_cancel_analysis_job)
  - LOCATION: src/api/rest/admin_process_analysis.py
  - HTTP: POST /admin/process-analysis/job/<job_id>/cancel
  - PATTERN: admin_historical_data.py lines 270-287
  - FLOW:
    1. Check active_jobs for job_id
    2. If found and status='running', set status='cancelled'
    3. Background thread checks this flag and stops
    4. Move to job_history, delete from active_jobs
    5. Return JSON: {success: true}
  - GOTCHA: Only running jobs can be cancelled
  - CRITICAL: Immediate response (don't wait for thread to stop)

# PHASE 2: HTML Template (Day 1-2)
Task 6: CREATE web/templates/admin/process_analysis_dashboard.html
  - IMPLEMENT: Complete admin page template
  - FOLLOW pattern: web/templates/admin/historical_data_dashboard.html (lines 1-800)
  - STRUCTURE:
    - Admin navigation bar (copy from historical_data.html lines 223-233)
    - Page header: "🔬 Process Stock Analysis"
    - Job controls form:
      - Universe selector dropdown (<select id="universe-select">)
      - Symbol input field (<input type="text" placeholder="AAPL, NVDA, TSLA">)
      - Analysis type checkboxes (Patterns, Indicators, Both - default checked)
      - Timeframe radio buttons (Daily, Hourly, Weekly, Monthly)
      - Submit button: "🔬 Run Analysis"
    - Progress bar container:
      - Bootstrap progress bar (progress-bar-striped progress-bar-animated)
      - Status text: "Analyzing AAPL (45/102 symbols)"
    - Active jobs list (card-based display)
    - Recent jobs history (last 10 jobs)
  - PLACEMENT: web/templates/admin/
  - GOTCHA: Include csrf_token() in form: <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
  - CRITICAL: Copy CSS styles from historical_data.html (lines 8-218)

# PHASE 3: JavaScript Client (Day 2)
Task 7: CREATE web/static/js/admin/process_analysis.js
  - IMPLEMENT: JavaScript polling and UI updates
  - FOLLOW pattern: web/static/js/admin/historical_data.js (lines 1-929)
  - FUNCTIONS:
    - submitAnalysisJob() → form submission via fetch POST
    - startPollingJobStatus(jobId) → recursive setTimeout polling (1s interval)
    - updateJobStatus(jobId, status) → progress bar + status text updates
    - loadUniverses() → fetch GET /admin/historical-data/universes (reuse endpoint)
    - getCSRFToken() → retrieve CSRF token (input → meta → cookie fallback)
    - showNotification(message, type) → success/error alerts
  - PLACEMENT: web/static/js/admin/
  - GOTCHA: setTimeout > setInterval (wait for response before next poll)
  - CRITICAL:
    - Poll interval: 1000ms (1 second)
    - Max poll duration: 300000ms (5 minutes)
    - Clear interval on completion/failure

Task 8: IMPLEMENT form submission handler (submitAnalysisJob)
  - LOCATION: web/static/js/admin/process_analysis.js
  - PATTERN: historical_data.js lines 622-743
  - FLOW:
    1. Get form values (universe_key OR symbols, analysis_type, timeframe)
    2. Validate: require universe OR symbols (not empty)
    3. Build request: {universe_key, symbols, analysis_type, timeframe}
    4. POST to /admin/process-analysis/trigger with CSRF token
    5. On success: show notification, start polling with job_id
    6. On error: show error notification
  - GOTCHA: Get selected checkboxes: document.querySelectorAll('input[name="analysis_type"]:checked')
  - CRITICAL: Disable submit button during request

Task 9: IMPLEMENT polling handler (startPollingJobStatus)
  - LOCATION: web/static/js/admin/process_analysis.js
  - PATTERN: historical_data.js lines 180-247
  - FLOW:
    1. Show progress bar container
    2. Recursive setTimeout poll: fetch GET /admin/process-analysis/job-status/<job_id>
    3. Update progress bar: width, textContent, aria-valuenow
    4. Update status text: "Analyzing NVDA (45/102 symbols)"
    5. Check if complete: status in ['completed', 'failed', 'cancelled']
    6. If complete: clear interval, show notification, remove job after 5s
    7. If not complete: setTimeout(poll, 1000) after response
  - GOTCHA: Handle 404 (expired job), retry with 2s delay on error
  - CRITICAL: Max 300 polls (5 minutes), then timeout

Task 10: IMPLEMENT progress bar updates (updateJobStatus)
  - LOCATION: web/static/js/admin/process_analysis.js
  - PATTERN: historical_data.js lines 249-286
  - UPDATES:
    - progressBar.style.width = status.progress + '%'
    - progressBar.textContent = status.progress + '%'
    - progressBar.setAttribute('aria-valuenow', status.progress)
    - statusText.textContent = `Analyzing ${status.current_symbol} (${status.symbols_completed}/${status.symbols_total})`
  - GOTCHA: Update job card in active jobs list if exists
  - CRITICAL: Smooth CSS transition (width 0.6s ease)

# PHASE 4: Integration & Registration (Day 2)
Task 11: MODIFY src/app.py (register blueprint)
  - LOCATION: src/app.py
  - PATTERN: Existing blueprint registrations
  - ADD:
    from src.api.rest.admin_process_analysis import admin_process_analysis_bp
    app.register_blueprint(admin_process_analysis_bp)
  - PLACEMENT: After other admin blueprint registrations
  - GOTCHA: Import at top of file, register in main() or create_app()

Task 12: MODIFY web/templates/admin/base_admin.html (add navigation link)
  - LOCATION: web/templates/admin/base_admin.html (or inline in each template)
  - PATTERN: historical_data_dashboard.html lines 223-233 (admin nav)
  - ADD:
    <a href="{{ url_for('admin_process_analysis.admin_process_analysis_dashboard') }}"
       class="btn btn-warning">🔬 Process Stock Analysis</a>
  - PLACEMENT: Admin navigation bar alongside Historical Data, User Management, Health Monitor
  - GOTCHA: Use Blueprint-qualified URL: 'admin_process_analysis.route_name'

# PHASE 5: Testing & Validation (Day 3)
Task 13: CREATE tests/integration/test_process_analysis_workflow.py
  - IMPLEMENT: End-to-end integration test
  - PATTERN: tests/unit/api/test_analysis_routes.py (lines 1-424)
  - TESTS:
    - test_job_submission() → POST returns job_id, job in active_jobs
    - test_job_status_polling() → GET returns correct format
    - test_analysis_execution() → background thread completes (mock services)
    - test_results_stored() → database has rows in daily_patterns, indicator_results
    - test_job_cancellation() → cancelled job stops processing
  - MOCKING:
    - @patch('src.api.rest.admin_process_analysis.AnalysisService')
    - @patch('src.api.rest.admin_process_analysis.OHLCVDataService')
    - @patch('src.api.rest.admin_process_analysis.get_relationship_cache')
  - GOTCHA: Use Flask test client: self.client.post('/admin/process-analysis/trigger', ...)
  - CRITICAL: Tests must pass without live database (use mocks)

Task 14: RUN integration tests (MANDATORY)
  - COMMAND: python run_tests.py
  - EXPECTED: All Sprint 68-72 tests pass + new Sprint 73 tests pass
  - VALIDATE: Pattern flow test maintains baseline (zero regressions)
  - RUNTIME: ~30 seconds total
  - GOTCHA: RLock warning can be ignored (known asyncio quirk)
  - CRITICAL: MUST pass before commit

Task 15: MANUAL testing (validation)
  - STEPS:
    1. Start app: python start_all_services.py
    2. Navigate: http://localhost:5000/admin/process-analysis
    3. Select universe: nasdaq100 (102 symbols)
    4. Select analysis: Both (patterns + indicators)
    5. Select timeframe: Daily
    6. Click: "🔬 Run Analysis"
    7. Observe: Progress bar updates every 1-2 seconds
    8. Wait: ~3-4 minutes for completion (102 symbols × 2s/symbol)
    9. Verify: Completion notification shows "102 symbols analyzed, X patterns detected, 816 indicators calculated"
    10. Check database: SELECT COUNT(*) FROM daily_patterns WHERE created_at > NOW() - INTERVAL '5 minutes';
    11. Check database: SELECT COUNT(*) FROM indicator_results WHERE created_at > NOW() - INTERVAL '5 minutes';
  - EXPECTED:
    - Progress bar animates smoothly
    - Status text updates with current symbol
    - Completion shows correct counts
    - Database has pattern/indicator rows with recent timestamps
  - GOTCHA: First symbol may take longer (service initialization)
  - CRITICAL: Verify zero regressions (existing dashboards still work)
```

### Implementation Patterns & Key Details

```python
# PATTERN 1: Background Thread Function (Complete Implementation)
# File: src/api/rest/admin_process_analysis.py

def run_analysis_job(job_data: dict, app: Flask):
    """
    Background thread function for analyzing symbols.

    Args:
        job_data: Job dict (updated in-place)
        app: Flask app object (for context)
    """
    try:
        # Establish Flask context (CRITICAL)
        with app.app_context():
            # Mark as running
            job_data['status'] = 'running'
            job_data['log_messages'].append(
                f"Started analyzing {len(job_data['symbols'])} symbols"
            )

            # Initialize services (Sprint 68-72)
            from src.analysis.services.analysis_service import AnalysisService
            from src.analysis.data.ohlcv_data_service import OHLCVDataService

            analysis_service = AnalysisService()
            data_service = OHLCVDataService()

            # Process each symbol
            for i, symbol in enumerate(job_data['symbols']):
                # Cancellation check (CRITICAL)
                if job_data['status'] == 'cancelled':
                    break

                # Update progress (for UI polling)
                job_data['current_symbol'] = symbol
                job_data['progress'] = int((i / len(job_data['symbols'])) * 100)
                job_data['symbols_completed'] = i

                try:
                    # Fetch OHLCV data (Sprint 72)
                    data = data_service.get_ohlcv_data(
                        symbol=symbol,
                        timeframe=job_data['timeframe'],
                        limit=250  # 250 bars for indicator calculations
                    )

                    if data.empty:
                        job_data['failed_symbols'].append(symbol)
                        job_data['log_messages'].append(
                            f"[SKIP] {symbol}: No OHLCV data available"
                        )
                        continue

                    # Determine which analysis to run
                    indicators_list = None
                    patterns_list = None

                    if job_data['analysis_type'] == 'indicators':
                        indicators_list = None  # None = all available
                        patterns_list = []       # Empty = skip patterns
                    elif job_data['analysis_type'] == 'patterns':
                        indicators_list = []     # Empty = skip indicators
                        patterns_list = None     # None = all available
                    else:  # 'both'
                        indicators_list = None   # All indicators
                        patterns_list = None     # All patterns

                    # Run analysis (Sprint 68)
                    result = analysis_service.analyze_symbol(
                        symbol=symbol,
                        data=data,
                        timeframe=job_data['timeframe'],
                        indicators=indicators_list,
                        patterns=patterns_list,
                        calculate_all=(job_data['analysis_type'] == 'both')
                    )

                    # Store results to database
                    # (Sprint 68 services handle database writes)
                    # Count results
                    patterns_count = sum(
                        1 for p in result.get('patterns', {}).values()
                        if p.get('detected', False)
                    )
                    indicators_count = len(result.get('indicators', {}))

                    job_data['patterns_detected'] += patterns_count
                    job_data['indicators_calculated'] += indicators_count

                    job_data['log_messages'].append(
                        f"[OK] {symbol}: {patterns_count} patterns, "
                        f"{indicators_count} indicators"
                    )

                except Exception as e:
                    job_data['failed_symbols'].append(symbol)
                    job_data['log_messages'].append(f"[FAIL] {symbol}: {str(e)}")

            # Complete job
            job_data['progress'] = 100
            job_data['current_symbol'] = None
            job_data['status'] = 'completed'
            job_data['completed_at'] = datetime.now()

            job_data['log_messages'].append(
                f"Analysis complete: {job_data['symbols_completed']} symbols, "
                f"{job_data['patterns_detected']} patterns detected, "
                f"{job_data['indicators_calculated']} indicators calculated, "
                f"{len(job_data['failed_symbols'])} failed"
            )

            # Move to history
            job_history.append(job_data.copy())
            job_id = job_data['id']
            if job_id in active_jobs:
                del active_jobs[job_id]

    except Exception as e:
        # Error handling
        job_data['status'] = 'failed'
        job_data['completed_at'] = datetime.now()
        job_data['log_messages'].append(f"Job failed: {str(e)}")

        # Move to history
        job_history.append(job_data.copy())
        job_id = job_data['id']
        if job_id in active_jobs:
            del active_jobs[job_id]


# PATTERN 2: Job Submission Route (Flask Blueprint)
# File: src/api/rest/admin_process_analysis.py

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from src.utils.auth_decorators import admin_required
from threading import Thread
import time
from datetime import datetime

admin_process_analysis_bp = Blueprint('admin_process_analysis', __name__)

# In-memory job tracking (module-level)
active_jobs = {}
job_history = []

@admin_process_analysis_bp.route('/admin/process-analysis')
@login_required
@admin_required
def admin_process_analysis_dashboard():
    """Main admin dashboard for process stock analysis"""
    try:
        # Get available universes for dropdown
        from src.core.services.relationship_cache import get_relationship_cache
        cache = get_relationship_cache()
        available_universes = cache.get_available_universes()

        # Get job statistics
        job_stats = {
            'active_jobs': len([j for j in active_jobs.values() if j['status'] == 'running']),
            'completed_today': len([j for j in job_history
                                   if j.get('completed_at') and
                                   j['completed_at'].date() == datetime.now().date()])
        }

        return render_template('admin/process_analysis_dashboard.html',
                             available_universes=available_universes,
                             job_stats=job_stats,
                             active_jobs=active_jobs,
                             recent_jobs=job_history[-10:])

    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('admin/process_analysis_dashboard.html',
                             available_universes=[],
                             job_stats={},
                             active_jobs={},
                             recent_jobs=[])


@admin_process_analysis_bp.route('/admin/process-analysis/trigger', methods=['POST'])
@login_required
@admin_required
def admin_trigger_analysis():
    """Trigger background analysis job"""
    try:
        # Parse request (JSON or form data)
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        universe_key = data.get('universe_key', '').strip()
        symbols_input = data.get('symbols', '').strip()
        analysis_type = data.get('analysis_type', 'both')
        timeframe = data.get('timeframe', 'daily')

        # Validate: require universe XOR symbols
        if not universe_key and not symbols_input:
            return jsonify({'success': False, 'error': 'Must provide universe or symbols'}), 400

        # Validate timeframe
        valid_timeframes = ['daily', 'hourly', '1min', 'weekly', 'monthly']
        if timeframe not in valid_timeframes:
            return jsonify({'success': False, 'error': f'Invalid timeframe: {timeframe}'}), 400

        # Validate analysis type
        valid_types = ['patterns', 'indicators', 'both']
        if analysis_type not in valid_types:
            return jsonify({'success': False, 'error': f'Invalid analysis_type: {analysis_type}'}), 400

        # Get symbols list
        from src.core.services.relationship_cache import get_relationship_cache
        cache = get_relationship_cache()

        if universe_key:
            symbols = cache.get_universe_symbols(universe_key)
            if not symbols:
                return jsonify({'success': False, 'error': f'No symbols found in universe: {universe_key}'}), 404
        else:
            symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
            if not symbols:
                return jsonify({'success': False, 'error': 'No valid symbols provided'}), 400

        # Create job
        job_id = f"analysis_{int(time.time())}_{len(active_jobs)}"
        job = {
            'id': job_id,
            'status': 'queued',
            'type': 'analysis',
            'universe_key': universe_key if universe_key else None,
            'symbols': symbols,
            'analysis_type': analysis_type,
            'timeframe': timeframe,
            'created_at': datetime.now(),
            'created_by': current_user.username if hasattr(current_user, 'username') else 'admin',
            'progress': 0,
            'current_symbol': None,
            'symbols_completed': 0,
            'symbols_total': len(symbols),
            'patterns_detected': 0,
            'indicators_calculated': 0,
            'failed_symbols': [],
            'log_messages': [],
            'completed_at': None
        }

        active_jobs[job_id] = job

        # Start background thread
        from flask import current_app
        thread = Thread(target=run_analysis_job, args=(job, current_app._get_current_object()))
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'job_id': job_id,
            'symbols_count': len(symbols),
            'analysis_type': analysis_type,
            'timeframe': timeframe
        }), 202  # 202 Accepted (async operation)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_process_analysis_bp.route('/admin/process-analysis/job-status/<job_id>')
@login_required
def admin_get_analysis_job_status(job_id):
    """Get real-time job status via AJAX polling"""
    job = active_jobs.get(job_id)
    if not job:
        # Check history
        job = next((j for j in job_history if j['id'] == job_id), None)
        if not job:
            return jsonify({'error': 'Job not found'}), 404

    return jsonify({
        'id': job.get('id', job_id),
        'status': job.get('status', 'unknown'),
        'progress': job.get('progress', 0),
        'current_symbol': job.get('current_symbol', ''),
        'symbols_completed': job.get('symbols_completed', 0),
        'symbols_total': job.get('symbols_total', 0),
        'patterns_detected': job.get('patterns_detected', 0),
        'indicators_calculated': job.get('indicators_calculated', 0),
        'failed_symbols': job.get('failed_symbols', []),
        'log_messages': job.get('log_messages', [])[-20:],  # Last 20 only
        'completed_at': job['completed_at'].isoformat() if job.get('completed_at') else None
    }), 200


@admin_process_analysis_bp.route('/admin/process-analysis/job/<job_id>/cancel', methods=['POST'])
@login_required
@admin_required
def admin_cancel_analysis_job(job_id):
    """Cancel a running analysis job"""
    job = active_jobs.get(job_id)
    if job and job['status'] == 'running':
        job['status'] = 'cancelled'
        job['completed_at'] = datetime.now()
        job['log_messages'].append('Job cancelled by user')

        # Move to history (background thread will see cancelled status)
        job_history.append(job.copy())
        del active_jobs[job_id]

        return jsonify({'success': True}), 200

    return jsonify({'error': 'Job not found or not running'}), 404


# PATTERN 3: JavaScript Polling (Complete Implementation)
# File: web/static/js/admin/process_analysis.js

class ProcessAnalysisManager {
    constructor() {
        this.pollIntervals = new Map();
        this.pollFrequency = 1000;      // Poll every 1 second
        this.maxPollDuration = 300000;  // 5 minutes max
        this.initializeElements();
        this.attachEventListeners();
    }

    initializeElements() {
        this.progressBar = document.getElementById('progressBar');
        this.statusText = document.getElementById('statusText');
        this.submitButton = document.getElementById('submitAnalysisBtn');
        this.universeSelect = document.getElementById('universe-select');
        this.symbolsInput = document.getElementById('symbols-input');
    }

    attachEventListeners() {
        if (this.submitButton) {
            this.submitButton.addEventListener('click', () => this.submitAnalysisJob());
        }

        // Load universes on page load
        this.loadUniverses();
    }

    async loadUniverses() {
        try {
            // Reuse existing endpoint from historical data
            const response = await fetch('/admin/historical-data/universes?types=UNIVERSE,ETF');
            const data = await response.json();

            if (data.universes && data.universes.length > 0) {
                this.populateUniverseDropdown(data.universes);
            }
        } catch (error) {
            console.error('Failed to load universes:', error);
        }
    }

    populateUniverseDropdown(universes) {
        this.universeSelect.innerHTML = '';

        // Group by type
        const grouped = universes.reduce((acc, u) => {
            if (!acc[u.type]) acc[u.type] = [];
            acc[u.type].push(u);
            return acc;
        }, {});

        // Add optgroups
        Object.keys(grouped).sort().forEach(type => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = `${type} (${grouped[type].length})`;

            grouped[type].forEach(universe => {
                const option = document.createElement('option');
                option.value = universe.name;
                option.textContent = `${universe.name} (${universe.member_count} stocks)`;
                optgroup.appendChild(option);
            });

            this.universeSelect.appendChild(optgroup);
        });
    }

    async submitAnalysisJob() {
        // Get form values
        const universeKey = this.universeSelect.value;
        const symbolsInput = this.symbolsInput.value.trim();
        const analysisType = document.querySelector('input[name="analysis_type"]:checked')?.value || 'both';
        const timeframe = document.querySelector('input[name="timeframe"]:checked')?.value || 'daily';

        // Validate: require universe OR symbols
        if (!universeKey && !symbolsInput) {
            this.showNotification('Please select a universe or enter symbols', 'error');
            return;
        }

        try {
            this.submitButton.disabled = true;
            this.submitButton.textContent = 'Submitting...';

            const response = await fetch('/admin/process-analysis/trigger', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    universe_key: universeKey,
                    symbols: symbolsInput,
                    analysis_type: analysisType,
                    timeframe: timeframe
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(
                    `Analysis job submitted! (${data.symbols_count} symbols)`,
                    'success'
                );
                this.startPollingJobStatus(data.job_id);
            } else {
                this.showNotification(data.error || 'Failed to submit job', 'error');
            }

        } catch (error) {
            console.error('Error submitting job:', error);
            this.showNotification('Failed to submit job: ' + error.message, 'error');
        } finally {
            this.submitButton.disabled = false;
            this.submitButton.textContent = '🔬 Run Analysis';
        }
    }

    startPollingJobStatus(jobId) {
        // Show progress bar
        if (this.progressBar) {
            this.progressBar.parentElement.style.display = 'block';
        }

        // Clear any existing interval
        if (this.pollIntervals.has(jobId)) {
            clearInterval(this.pollIntervals.get(jobId));
        }

        let pollCount = 0;
        const maxPolls = this.maxPollDuration / this.pollFrequency;

        const poll = async () => {
            pollCount++;

            try {
                const response = await fetch(`/admin/process-analysis/job-status/${jobId}`);
                const status = await response.json();

                if (status.id) {
                    this.updateJobStatus(jobId, status);

                    // Stop polling if job complete
                    if (['completed', 'failed', 'cancelled'].includes(status.status)) {
                        clearInterval(interval);
                        this.pollIntervals.delete(jobId);

                        if (status.status === 'completed') {
                            this.showNotification(
                                `Analysis complete! ${status.symbols_completed} symbols, ` +
                                `${status.patterns_detected} patterns, ` +
                                `${status.indicators_calculated} indicators`,
                                'success'
                            );
                        } else if (status.status === 'failed') {
                            this.showNotification(`Analysis failed: ${status.log_messages.slice(-1)}`, 'error');
                        }
                    }
                } else if (response.status === 404) {
                    clearInterval(interval);
                    this.pollIntervals.delete(jobId);
                    this.showNotification('Job not found or expired', 'error');
                }
            } catch (error) {
                console.error(`Poll error for ${jobId}:`, error);
            }

            // Stop polling after max duration
            if (pollCount >= maxPolls) {
                clearInterval(interval);
                this.pollIntervals.delete(jobId);
                this.showNotification('Polling timeout', 'error');
            }
        };

        // Start polling with setTimeout (recursive)
        const interval = setInterval(poll, this.pollFrequency);
        this.pollIntervals.set(jobId, interval);

        // Initial poll
        poll();
    }

    updateJobStatus(jobId, status) {
        if (this.progressBar && status.progress >= 0) {
            this.progressBar.style.width = status.progress + '%';
            this.progressBar.textContent = Math.round(status.progress) + '%';
            this.progressBar.setAttribute('aria-valuenow', status.progress);
        }

        if (this.statusText) {
            const text = status.current_symbol
                ? `Analyzing ${status.current_symbol} (${status.symbols_completed}/${status.symbols_total})`
                : `Progress: ${status.symbols_completed}/${status.symbols_total}`;
            this.statusText.textContent = text;
        }
    }

    getCSRFToken() {
        const input = document.querySelector('input[name="csrf_token"]');
        if (input) return input.value;

        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.content;

        const cookie = document.cookie.split('; ').find(row => row.startsWith('csrf_token='));
        return cookie ? cookie.split('=')[1] : '';
    }

    showNotification(message, type) {
        let notification = document.getElementById('notification');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'notification';
            notification.style.position = 'fixed';
            notification.style.top = '20px';
            notification.style.right = '20px';
            notification.style.padding = '15px 20px';
            notification.style.borderRadius = '8px';
            notification.style.zIndex = '1000';
            notification.style.maxWidth = '400px';
            notification.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            document.body.appendChild(notification);
        }

        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.display = 'block';

        if (type === 'success') {
            notification.style.background = '#d4edda';
            notification.style.color = '#155724';
            notification.style.border = '1px solid #c3e6cb';
        } else {
            notification.style.background = '#f8d7da';
            notification.style.color = '#721c24';
            notification.style.border = '1px solid #f5c6cb';
        }

        setTimeout(() => {
            notification.style.display = 'none';
        }, 5000);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('/admin/process-analysis')) {
        new ProcessAnalysisManager();
    }
});
```

### Integration Points

```yaml
# Sprint 68-72 Service Integration (NO CHANGES NEEDED)
ANALYSIS_SERVICE:
  - service: src/analysis/services/analysis_service.py
  - method: analyze_symbol(symbol, data, timeframe, indicators, patterns)
  - usage: Called for each symbol in background thread
  - performance: ~2s per symbol (patterns + indicators combined)
  - result: {indicators: {...}, patterns: {...}}

OHLCV_DATA_SERVICE:
  - service: src/analysis/data/ohlcv_data_service.py
  - method: get_ohlcv_data(symbol, timeframe, limit=250)
  - usage: Fetch OHLCV data before analysis
  - performance: 5.59ms per symbol (Sprint 72 actual)
  - result: pd.DataFrame[open, high, low, close, volume]

RELATIONSHIP_CACHE:
  - service: src/core/services/relationship_cache.py
  - method: get_universe_symbols(universe_key)
  - usage: Load symbols for universe selection
  - performance: <1ms cache hit (Sprint 61)
  - result: list[str] (symbol list)

DATABASE_WRITES:
  - tables: daily_patterns, indicator_results
  - pattern: AnalysisService handles INSERT operations internally
  - timing: After each symbol analysis completes
  - note: Sprint 68 services handle all database writes

ADMIN_NAVIGATION:
  - template: web/templates/admin/base_admin.html OR inline in each template
  - pattern: Add new nav link with Blueprint-qualified URL
  - url: {{ url_for('admin_process_analysis.admin_process_analysis_dashboard') }}
  - placement: Between Historical Data and Health Monitor

BLUEPRINT_REGISTRATION:
  - file: src/app.py
  - import: from src.api.rest.admin_process_analysis import admin_process_analysis_bp
  - register: app.register_blueprint(admin_process_analysis_bp)
  - placement: After other admin blueprint registrations
```

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# TickStock Standard: Ruff for linting and formatting
# Run after each file creation - fix before proceeding

# File-specific validation
ruff check src/api/rest/admin_process_analysis.py --fix
ruff check web/static/js/admin/process_analysis.js --fix

# Project-wide validation
ruff check src/ --fix
ruff format src/

# Expected: Zero errors. If errors exist, READ output and fix before proceeding.
```

### Level 2: Unit Tests (Component Validation)

```bash
# Sprint 73 Unit Tests
python -m pytest tests/integration/test_process_analysis_workflow.py -v

# Expected: 5+ tests passing
# Tests:
# - test_job_submission (POST returns job_id)
# - test_job_status_polling (GET returns correct format)
# - test_analysis_execution (background thread completes)
# - test_results_stored (database has rows)
# - test_job_cancellation (cancelled job stops)
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
# CRITICAL: Must run before ANY commit

# Primary integration test runner
python run_tests.py

# Expected Output:
# - 2+ tests passing (existing Sprint 68-72 tests)
# - ~30 second runtime
# - Pattern flow tests passing (zero regressions)

# NOTE: RLock warning can be ignored (known asyncio quirk)
```

### Level 4: TickStock-Specific Validation

```bash
# Manual Testing Validation (REQUIRED)
# Start services
python start_all_services.py

# Wait for initialization
sleep 5

# Open browser
# Navigate to: http://localhost:5000/admin/process-analysis

# Test workflow:
# 1. Select universe: nasdaq100 (102 symbols)
# 2. Select analysis: Both (patterns + indicators)
# 3. Select timeframe: Daily
# 4. Click "🔬 Run Analysis"
# 5. Observe progress bar updates every 1-2 seconds
# 6. Wait ~3-4 minutes for completion
# 7. Verify completion notification shows correct counts

# Verify database results
PGPASSWORD=your_password psql -U app_readwrite -d tickstock -c \
  "SELECT COUNT(*) FROM daily_patterns WHERE created_at > NOW() - INTERVAL '5 minutes';"
# Expected: >0 rows

PGPASSWORD=your_password psql -U app_readwrite -d tickstock -c \
  "SELECT COUNT(*) FROM indicator_results WHERE created_at > NOW() - INTERVAL '5 minutes';"
# Expected: >0 rows (ideally ~816 for 102 symbols × 8 indicators)

# Performance Benchmarking
# Single symbol analysis: ~2 seconds (patterns + indicators)
# 100 symbols: ~3-4 minutes total
# Job submission: <100ms
# Job status polling: <50ms

# Zero Regressions Check
# Verify existing dashboards still work:
# - http://localhost:5000/ (main dashboard)
# - http://localhost:5000/admin/historical-data (historical data dashboard)
# - http://localhost:5000/streaming (live streaming dashboard)

# Expected: All pages load without errors, no broken functionality
```

## Final Validation Checklist

### Technical Validation

- [ ] All 4 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] No linting errors: `ruff check src/`
- [ ] No formatting issues: `ruff format src/ --check`
- [ ] Unit tests pass: `python -m pytest tests/integration/test_process_analysis_workflow.py -v`

### Feature Validation

- [ ] Admin page accessible at `/admin/process-analysis` (admin-only)
- [ ] Universe selector populates from RelationshipCache
- [ ] Symbol input accepts comma-separated tickers
- [ ] Analysis type checkboxes: Patterns, Indicators, Both (default)
- [ ] Timeframe radio buttons: Daily, Hourly, Weekly, Monthly
- [ ] Job submission returns job_id and starts background thread
- [ ] Progress bar polls every 1-2 seconds
- [ ] Progress displays: percentage, current symbol, symbols completed/total
- [ ] Completion notification shows: symbols analyzed, patterns detected, indicators calculated
- [ ] Analysis results stored in database (daily_patterns, indicator_results)
- [ ] Active jobs display with real-time status updates
- [ ] Job cancellation stops processing

### TickStock Architecture Validation

- [ ] Sprint 68-72 services integrated correctly (AnalysisService, OHLCVDataService, RelationshipCache)
- [ ] Database writes use Sprint 68 patterns (no direct INSERT in Sprint 73 code)
- [ ] Background threads use Flask app context correctly
- [ ] GIL-safe in-memory job tracking (simple dict operations)
- [ ] Performance targets achieved (~2s per symbol, <4min for 100 symbols)
- [ ] Zero regressions in Sprint 68-72 functionality

### Code Quality Validation

- [ ] Follows existing codebase patterns (Historical Data dashboard patterns)
- [ ] File placement matches desired codebase tree
- [ ] Code structure limits: <500 lines/file, <50 lines/function
- [ ] Naming conventions: snake_case functions, PascalCase classes
- [ ] CSRF protection implemented (csrf_token())
- [ ] Admin route decorators: @login_required + @admin_required
- [ ] No "Generated by Claude" comments

### Documentation & Deployment

- [ ] Code is self-documenting with clear variable/function names
- [ ] Logs are informative (job progress, errors)
- [ ] No new environment variables needed
- [ ] Sprint 73 completion document created
- [ ] CLAUDE.md updated with Sprint 73 status

---

## Anti-Patterns to Avoid

### Generic Anti-Patterns
- ❌ Don't create new patterns when existing ones work
- ❌ Don't skip validation because "it should work"
- ❌ Don't ignore failing tests - fix them
- ❌ Don't use setInterval for polling (use setTimeout recursive)
- ❌ Don't catch all exceptions - be specific
- ❌ Don't hardcode values that should be config

### TickStock-Specific Anti-Patterns (CRITICAL)

#### Architecture Violations
- ❌ **Don't query TickStockPL API for analysis**
  - Sprint 68 migrated analysis to AppV2 - run locally
  - Violation: Calling TickStockPL /api/analysis endpoints

- ❌ **Don't use Redis pub-sub for analysis trigger**
  - Sprint 73 runs analysis directly in background thread
  - Violation: Publishing to tickstock:analysis:trigger channel

- ❌ **Don't create duplicate analysis logic**
  - Use existing Sprint 68-72 services (AnalysisService, etc.)
  - Violation: Reimplementing pattern detection or indicator calculation

#### Data Handling
- ❌ **Don't share database connections across threads**
  - Each thread gets its own connection from pool
  - Violation: Passing db connection object to background thread

- ❌ **Don't use current_app in background threads**
  - Pass Flask app object and use with app.app_context()
  - Violation: `from flask import current_app` in run_analysis_job()

- ❌ **Don't forget thread.daemon = True**
  - Without daemon, background threads prevent Flask shutdown
  - Violation: Thread(target=..., daemon=False)

#### Performance
- ❌ **Don't block main thread waiting for analysis**
  - Background threads allow immediate response
  - Violation: Synchronous analysis in POST endpoint

- ❌ **Don't poll too frequently**
  - 1-2 second intervals are sufficient
  - Violation: 100ms polling interval (overloads server)

#### Testing & Validation
- ❌ **Don't skip integration tests before commits**
  - `python run_tests.py` is MANDATORY
  - Violation: Committing without running tests

- ❌ **Don't test with live database only**
  - Use mocks for unit tests
  - Violation: No @patch decorators in tests

#### Code Quality
- ❌ **Don't exceed structure limits**
  - Max 500 lines per file, 50 lines per function
  - Violation: 800-line route file

- ❌ **Don't add "Generated by Claude" to code or commits**
  - Keep code and commits clean
  - Violation: Comments like "# Sprint 73 by Claude Code"

---

**One-Pass Implementation Confidence**: 95/100

**Risk Assessment**: LOW (leverages proven Sprint 68-72 services + existing admin patterns)

**Estimated Implementation Time**: 2-3 days

**Next Sprint**: Sprint 74 - Historical Import Integration (auto-trigger analysis after data import)
