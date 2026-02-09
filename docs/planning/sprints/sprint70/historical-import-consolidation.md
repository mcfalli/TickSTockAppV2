name: "Sprint 70: Historical Import Consolidation - Single Source of Truth"
description: |
  Remove AppV2's duplicate historical loader, wire Admin UI to TickStockPL's Redis job
  queue for unified data import workflow, and establish TickStockPL as single source
  of truth for historical data loading. Final sprint in TickStockPL consolidation trilogy.

---

## Goal

**Feature Goal**: Establish single source of truth for historical data loading by removing AppV2's duplicate historical loader (architectural violation) and wiring Admin UI to TickStockPL's superior Redis job queue system. Complete TickStockPL consolidation with 30-day monitoring and archival plan.

**Deliverable**:
- Remove `src/data/historical_loader.py` (1,220 lines) - architectural violation
- Update Admin UI to use existing TickStockPLClient for job submission
- Unified data import workflow documentation
- Job status polling system (async workflow with progress bar)
- Single source of truth validation (TickStockPL owns data loading)
- TickStockPL archival plan (NOTE: Keep deployed for data loading microservice)
- 30-day monitoring dashboard
- 10+ unit tests, 10+ integration tests

**Success Definition**:
- Duplicate historical loader completely removed (zero references in codebase)
- Admin UI wired to TickStockPL Redis job queue (tickstock.jobs.data_load)
- Job submission workflow: Admin UI → Redis → TickStockPL (<100ms submission)
- Job status polling: Admin UI → Redis → Status display (<50ms polling)
- Single source of truth established (TickStockPL for data, AppV2 for analysis)
- Integration tests pass with zero regressions
- 30-day monitoring dashboard operational

## User Persona (if applicable)

**Target User**: TickStock Development Team + Administrators

**Use Case**: Load historical data for symbols/universes via Admin UI, delegating actual data loading to TickStockPL while AppV2 focuses on UI/analysis.

**User Journey** (Admin):
1. Navigate to Historical Data dashboard in Admin UI
2. Enter symbols or select universe for historical import
3. Specify date range and timeframe (daily, hourly, weekly)
4. Submit job → Admin UI sends to Redis job queue
5. TickStockPL picks up job from queue and starts data loading
6. Admin UI polls Redis for job status (progress updates)
7. On completion, TickStockPL publishes data_load_complete event
8. AppV2 PostImportAnalysisJob (Sprint 69) triggers automatically
9. View job completion status and analysis results

**User Journey** (System):
1. User submits historical data load request via Admin UI
2. AppV2 publishes job to Redis (tickstock.jobs.data_load)
3. TickStockPL job handler picks up job from queue
4. TickStockPL loads historical data (MassiveHistoricalLoader)
5. TickStockPL updates job status in Redis (running, progress, completed)
6. On completion, TickStockPL publishes data_load_complete event
7. AppV2 DataLoadListener (Sprint 69) receives event
8. AppV2 triggers PostImportAnalysisJob (indicators + patterns)
9. Analysis results stored and available in UI

**Pain Points Addressed**:
- Duplicate historical loader in AppV2 (architectural violation - Consumer shouldn't load data)
- Two implementations of historical loading logic (maintenance overhead)
- Unclear single source of truth for data loading
- TickStockPL unclear deployment status (deprecated or still needed?)

## Why

- **Business Value**: Simplify architecture by removing duplicate logic (1,220 lines) and establishing clear component boundaries
- **Integration**: Completes Sprint 68-69 migration by removing final architectural violation
- **Architecture**: Establishes TickStockPL as Data Producer microservice, AppV2 as Consumer/Analyzer
- **Performance**: TickStockPL's MassiveHistoricalLoader optimized for bulk imports (5 years × 500 symbols)
- **User Impact**: Unified data import workflow with better progress visibility and automatic post-import analysis

**Problems Solved**:
- Architectural violation: AppV2 (Consumer) has duplicate data loading logic
- Single source of truth unclear (two loaders do similar things)
- Maintenance overhead: Two historical loading implementations to maintain
- TickStockPL deployment confusion (is it deprecated or still needed?)
- No clear boundary between TickStockPL and AppV2 responsibilities

## What

### Technical Requirements

**Files to Remove** (1,220 lines total):
- `src/data/historical_loader.py` (1,220 lines) - Duplicate historical loading logic
- Associated test files (if exist)

**Files to Update**:
- `src/api/rest/admin_historical_data_redis.py` - Already uses Redis job queue (verify compatibility)
- `web/templates/admin/historical_data_dashboard.html` - Update UI for async workflow
- `web/static/js/admin/historical-data.js` - Add job status polling
- `CLAUDE.md` - Update with Sprint 70 completion status

**Redis Job Queue Integration**:
- **Job Submission Channel**: `tickstock.jobs.data_load` (TickStockPL subscribes)
- **Job Request Format**:
  ```json
  {
    "job_id": "uuid-string",
    "job_type": "symbol_load" | "universe_load",
    "symbol": "AAPL" (for symbol_load),
    "universe": "nasdaq100" (for universe_load),
    "start_date": "2021-01-01",
    "end_date": "2026-02-08",
    "timeframe": "daily",
    "run_analysis": true,
    "submitted_at": "2026-02-08T15:30:00",
    "submitted_by": "TickStockAppV2"
  }
  ```
- **Job Status Storage**: Redis key `tickstock:job:status:{job_id}` (JSON)
- **Status Format**:
  ```json
  {
    "job_id": "uuid-string",
    "status": "pending" | "running" | "completed" | "failed",
    "progress": 0-100,
    "current_symbol": "AAPL",
    "symbols_completed": 50,
    "symbols_total": 102,
    "started_at": "2026-02-08T15:30:05",
    "completed_at": "2026-02-08T15:35:22",
    "error": null | "error message"
  }
  ```
- **Completion Event**: Published to `tickstock.jobs.data_load` (AppV2 DataLoadListener subscribes)
  ```json
  {
    "event_type": "data_load_complete",
    "job_id": "uuid-string",
    "symbols": ["AAPL", "NVDA", "TSLA"],
    "timeframe": "daily",
    "run_analysis": true
  }
  ```

**Admin UI Async Workflow**:
- Job submission via existing `/admin/historical-data/trigger-load` endpoint (already uses Redis)
- New endpoint: `GET /admin/historical-data/job-status/<job_id>` (polling)
- JavaScript polling: Check job status every 2 seconds until completion
- Progress bar UI: Display progress percentage, current symbol, elapsed time
- Success notification: Show completion message with link to analysis results
- Error handling: Display error messages, retry button

**TickStockPL Archival Plan**:
- **IMPORTANT**: TickStockPL NOT fully deprecated - keeps data loading role
- **Remains Deployed**: TickStockPL continues as Data Producer microservice
- **Archival Action**: Archive repository as reference (read-only)
- **Rationale**: Single source of truth for historical data loading (13,099 lines remain)
- **Alternative Considered**: Migrate all data loading to AppV2 (rejected - increases AppV2 complexity)

**30-Day Monitoring Dashboard**:
- Track metrics: Job success rate, average load time, error rate, symbols loaded
- Alert conditions: Job failure rate >5%, load time >10 min for 100 symbols
- Comparison: AppV2 (Redis) vs TickStockPL (direct) performance
- Validation: Ensure zero data loss, zero accuracy regressions
- Outcome: If stable, finalize TickStockPL deployment status (kept as microservice)

### Success Criteria

- [ ] Duplicate historical loader removed (1,220 lines)
- [ ] Zero references to `src.data.historical_loader` in codebase
- [ ] Admin UI uses existing Redis job queue (no direct loading)
- [ ] Job status polling endpoint functional (<50ms response time)
- [ ] Progress bar UI displays real-time job progress
- [ ] Job submission workflow: Admin UI → Redis → TickStockPL (<100ms submission)
- [ ] Single source of truth validated (TickStockPL for data, AppV2 for analysis)
- [ ] Integration tests pass: `python run_tests.py` (10+ unit, 10+ integration)
- [ ] 30-day monitoring dashboard operational
- [ ] TickStockPL archival plan documented (NOTE: Keep deployed)
- [ ] Zero regressions vs Sprint 68-69 baseline

## Context (for AI Assistant)

### Architecture Context (TickStock-Specific)

```yaml
component_role: "Consumer + Analyzer (NOT Data Loader)"
description: |
  AppV2 consumes market data from TickStockPL, performs analysis, and displays results.
  Sprint 70 removes architectural violation (duplicate historical loader) and establishes
  TickStockPL as single source of truth for data loading.

database_access:
  read_tables:
    - ohlcv_daily, ohlcv_1hour, ohlcv_1week (read-only access)
    - definition_groups, group_memberships (RelationshipCache)
    - pattern_definitions, indicator_definitions (Sprint 17 registry)
    - indicator_results, daily_patterns (analysis results)
  write_tables:
    - job_executions (Sprint 69 background jobs)
    - indicator_results, daily_patterns (analysis results only)
  write_pattern: "INSERT only (no historical data loading)"
  constraint: "app_readwrite role, NO OHLCV writes (TickStockPL owns)"

redis_channels:
  publish:
    - "tickstock.jobs.data_load" (job submission to TickStockPL)
    - "tickstock.events.patterns" (Sprint 69 - pattern detection results)
    - "tickstock.events.indicators" (Sprint 69 - indicator calculation results)
    - "tickstock:monitoring" (health metrics)
    - "tickstock:errors" (error logging)
  subscribe:
    - "tickstock.jobs.data_load" (completion events from TickStockPL)
  pattern: "Job queue for async task delegation, pub-sub for cross-component events"

single_source_of_truth:
  historical_data_loading: "TickStockPL (MassiveHistoricalLoader)"
  analysis_calculation: "AppV2 (AnalysisService from Sprint 68)"
  pattern_detection: "AppV2 (PatternService from Sprint 68)"
  indicator_calculation: "AppV2 (IndicatorService from Sprint 68)"
  ui_dashboards: "AppV2 (Flask templates, WebSocket broadcasting)"

performance_targets:
  job_submission: "<100ms (Redis publish)"
  job_status_polling: "<50ms (Redis get)"
  admin_ui_load: "<200ms (page render)"
  redis_operations: "<10ms (publish/get)"

patterns_to_follow:
  - "Use existing TickStockPLClient (src/core/services/tickstockpl_api_client.py)"
  - "Use existing Redis job queue pattern (admin_historical_data_redis.py)"
  - "Follow Admin UI patterns (historical_data_dashboard.html)"
  - "JavaScript polling pattern (setInterval with 2s interval)"
  - "Progress bar UI with Bootstrap components"
  - "Job status lifecycle: pending → running → completed/failed"

anti_patterns:
  - "DO NOT create new historical loader in AppV2 (architectural violation)"
  - "DO NOT add OHLCV write operations to AppV2 (TickStockPL owns)"
  - "DO NOT bypass Redis job queue (direct API calls to TickStockPL)"
  - "DO NOT block Admin UI waiting for job completion (use async polling)"
  - "DO NOT archive TickStockPL completely (keep deployed as microservice)"
```

### Documentation & References

**Existing AppV2 Implementations** (already in place):
- `C:\Users\McDude\TickStockAppV2\src\core\services\tickstockpl_api_client.py` (lines 1-150)
  - TickStockPLAPIClient class with HTTP API methods
  - trigger_processing(), get_status(), get_history() methods
  - Request session management, error handling
- `C:\Users\McDude\TickStockAppV2\src\api\rest\admin_historical_data_redis.py` (lines 1-150)
  - Redis job queue integration already implemented
  - admin_trigger_historical_load() submits jobs to Redis
  - Job history tracking in memory
  - Redis client initialization
- `C:\Users\McDude\TickStockAppV2\src\jobs\data_load_listener.py` (Sprint 69)
  - DataLoadListener subscribes to tickstock.jobs.data_load
  - Triggers PostImportAnalysisJob on data_load_complete event
  - Already operational (Sprint 69 deliverable)

**File to Remove**:
- `C:\Users\McDude\TickStockAppV2\src\data\historical_loader.py` (1,220 lines)
  - Duplicate implementation of historical loading logic
  - Architectural violation: AppV2 (Consumer) shouldn't load data
  - Will be replaced by Redis job queue delegation to TickStockPL

**Admin UI Templates**:
- `C:\Users\McDude\TickStockAppV2\web\templates\admin\historical_data_dashboard.html`
  - Existing dashboard with job submission form
  - Update: Add progress bar UI for active jobs
  - Update: Add job status polling logic
- `C:\Users\McDude\TickStockAppV2\web\static\js\admin\historical-data.js` (if exists)
  - JavaScript for job submission
  - Update: Add polling function with 2s interval
  - Update: Add progress bar updates

**Sprint 69 Integration**:
- `C:\Users\McDude\TickStockAppV2\src\jobs\data_load_listener.py`
  - Already listens to tickstock.jobs.data_load for completion events
  - Triggers PostImportAnalysisJob automatically
  - No changes needed (already handles data_load_complete event)

**External Documentation**:
- Redis Pub-Sub Python: https://redis.readthedocs.io/en/stable/commands.html#redis.commands.core.CoreCommands.publish
- Redis GET/SET: https://redis.readthedocs.io/en/stable/commands.html#redis.commands.core.CoreCommands.get
- Flask Progress Bar: https://flask.palletsprojects.com/en/3.0.x/patterns/streaming/
- Bootstrap Progress Bar: https://getbootstrap.com/docs/5.0/components/progress/
- JavaScript setInterval: https://developer.mozilla.org/en-US/docs/Web/API/setInterval

### Desired Codebase Tree (Sprint 70 modifications)

```
TickStockAppV2/
├── src/
│   ├── data/
│   │   ├── historical_loader.py        # REMOVED (1,220 lines)
│   │   ├── eod_processor.py            # UPDATED (remove historical_loader import)
│   │   └── etf_universe_manager.py     # UPDATED (if references historical_loader)
│   ├── api/
│   │   └── rest/
│   │       ├── admin_historical_data_redis.py  # UPDATED (add job status polling)
│   │       └── admin.py                # UPDATED (if references historical_loader)
│   ├── core/
│   │   └── services/
│   │       └── tickstockpl_api_client.py  # EXISTING (no changes)
│   └── jobs/
│       └── data_load_listener.py       # EXISTING (Sprint 69 - no changes)
├── web/
│   ├── templates/
│   │   └── admin/
│   │       └── historical_data_dashboard.html  # UPDATED (add progress bar UI)
│   └── static/
│       └── js/
│           └── admin/
│               └── historical-data.js  # UPDATED (add polling logic)
├── tests/
│   ├── unit/
│   │   └── validation/
│   │       └── test_no_historical_loader.py  # NEW (verify removal)
│   └── integration/
│       ├── test_historical_import_workflow.py  # NEW (end-to-end)
│       └── test_single_source_of_truth.py  # NEW (validation)
├── docs/
│   ├── planning/
│   │   └── sprints/
│   │       └── sprint70/
│   │           ├── TICKSTOCKPL_ARCHIVAL.md  # NEW (deployment status)
│   │           └── SPRINT70_COMPLETE.md     # NEW (sprint completion)
│   └── architecture/
│       ├── single-source-of-truth.md   # NEW (component boundaries)
│       └── data-flow.md                # UPDATED (unified workflow)
└── CLAUDE.md                           # UPDATED (Sprint 70 completion)
```

### Known Gotchas (Critical Patterns)

1. **Remove File Completely, Not Just Imports**:
   ```python
   # WRONG: Only remove imports, leave file
   # from src.data.historical_loader import HistoricalLoader  # Commented out

   # CORRECT: Delete entire file src/data/historical_loader.py
   # Then update all references to use Redis job queue instead
   ```

2. **Redis Job Status Key Naming**:
   ```python
   # WRONG: Inconsistent key naming
   redis_client.set(f'job_status:{job_id}', status)  # Missing prefix

   # CORRECT: Follow existing pattern
   redis_client.set(f'tickstock:job:status:{job_id}', json.dumps(status))
   ```

3. **Job Status Polling Interval**:
   ```javascript
   // WRONG: Too frequent polling (overloads Redis)
   setInterval(pollJobStatus, 100);  // 100ms = 10 requests/second

   // CORRECT: 2 second interval (reasonable balance)
   const pollInterval = setInterval(pollJobStatus, 2000);  // 2s interval
   ```

4. **Job Status Polling Cleanup**:
   ```javascript
   // WRONG: Polling never stops (memory leak)
   setInterval(pollJobStatus, 2000);

   // CORRECT: Clear interval on completion
   const pollInterval = setInterval(pollJobStatus, 2000);
   if (status === 'completed' || status === 'failed') {
       clearInterval(pollInterval);
   }
   ```

5. **Redis Message Format Consistency**:
   ```python
   # WRONG: Inconsistent job request format
   job_request = {'id': job_id, 'type': 'load'}  # Doesn't match spec

   # CORRECT: Follow documented format
   job_request = {
       'job_id': job_id,
       'job_type': 'symbol_load',
       'symbol': symbol,
       'start_date': start_date,
       'end_date': end_date,
       'timeframe': timeframe,
       'run_analysis': True,
       'submitted_at': datetime.now().isoformat(),
       'submitted_by': 'TickStockAppV2'
   }
   ```

6. **TickStockPL Deployment Status** (CRITICAL):
   ```markdown
   # WRONG: Assume TickStockPL completely deprecated
   "Sprint 70 removes TickStockPL completely. Archive and undeployall services."

   # CORRECT: TickStockPL remains deployed as Data Producer microservice
   "Sprint 70 establishes TickStockPL as single source of truth for data loading.
    TickStockPL remains deployed and operational. Repository archived as reference."
   ```

7. **Progress Bar Percentage Calculation**:
   ```javascript
   // WRONG: Division by zero when symbols_total is 0
   const progress = (symbols_completed / symbols_total) * 100;

   // CORRECT: Handle edge cases
   const progress = symbols_total > 0
       ? Math.round((symbols_completed / symbols_total) * 100)
       : 0;
   ```

8. **Job Submission Error Handling**:
   ```python
   # WRONG: No error handling for Redis connection failure
   redis_client.publish('tickstock.jobs.data_load', json.dumps(job_request))

   # CORRECT: Handle Redis connection errors
   try:
       redis_client.ping()  # Test connection
       redis_client.publish('tickstock.jobs.data_load', json.dumps(job_request))
   except redis.ConnectionError:
       return {'success': False, 'error': 'Redis service unavailable'}
   ```

9. **Admin UI Progress Display** (avoid layout shift):
   ```html
   <!-- WRONG: Progress bar appears/disappears (layout shift) -->
   <div id="progress-container" style="display: none;">
       <div class="progress">...</div>
   </div>

   <!-- CORRECT: Reserve space, show/hide within container -->
   <div id="progress-container" style="height: 80px;">
       <div class="progress" id="job-progress" style="display: none;">...</div>
   </div>
   ```

10. **Validation: Check All Import Removal**:
    ```bash
    # WRONG: Only search for direct imports
    rg "from src.data.historical_loader"

    # CORRECT: Search for all references (imports, class names, comments)
    rg "historical_loader|HistoricalLoader" src/ web/ tests/
    # Expected: Zero matches
    ```

11. **Integration Test: Verify End-to-End Flow**:
    ```python
    # WRONG: Test job submission only (incomplete)
    def test_job_submission():
        result = submit_job(symbol='AAPL')
        assert result['success'] is True

    # CORRECT: Test full workflow (submission → status → completion)
    def test_historical_import_workflow():
        # 1. Submit job
        result = submit_job(symbol='AAPL')
        assert result['success'] is True
        job_id = result['job_id']

        # 2. Poll job status
        status = get_job_status(job_id)
        assert status['status'] in ['pending', 'running']

        # 3. Wait for completion (or mock)
        # ... poll until completed ...

        # 4. Verify data loaded
        # ... check ohlcv_daily table ...

        # 5. Verify post-import analysis triggered (Sprint 69)
        # ... check indicator_results, daily_patterns tables ...
    ```

12. **Documentation: Update Component Boundaries**:
    ```yaml
    # WRONG: Vague component responsibilities
    tickstockpl:
      - Processes data
      - Handles some imports

    # CORRECT: Clear single source of truth
    tickstockpl:
      role: "Data Producer"
      responsibilities:
        - Historical data loading (MassiveHistoricalLoader)
        - OHLCV bar persistence (all timeframes)
        - Redis job queue processing
      single_source_of_truth: "Historical data import"

    tickstockappv2:
      role: "Consumer + Analyzer"
      responsibilities:
        - Analysis (indicators, patterns - Sprint 68)
        - Background jobs (automation - Sprint 69)
        - UI/dashboards (visualization)
        - WebSocket broadcasting
      single_source_of_truth: "Analysis and visualization"
    ```

13. **Job Status Storage Duration**:
    ```python
    # WRONG: Job status stored forever (Redis bloat)
    redis_client.set(f'tickstock:job:status:{job_id}', status)

    # CORRECT: Set expiration (7 days sufficient for history)
    redis_client.setex(
        f'tickstock:job:status:{job_id}',
        7 * 24 * 60 * 60,  # 7 days in seconds
        json.dumps(status)
    )
    ```

14. **Admin UI: Handle Job Not Found**:
    ```javascript
    // WRONG: Assume job status always exists
    fetch(`/admin/historical-data/job-status/${jobId}`)
        .then(response => response.json())
        .then(data => updateProgressBar(data.progress));

    // CORRECT: Handle 404 (job not found)
    fetch(`/admin/historical-data/job-status/${jobId}`)
        .then(response => {
            if (response.status === 404) {
                showError('Job not found. May have expired.');
                return;
            }
            return response.json();
        })
        .then(data => {
            if (data) updateProgressBar(data.progress);
        });
    ```

15. **Monitoring Dashboard: Track Right Metrics**:
    ```python
    # WRONG: Track irrelevant metrics
    metrics = {
        'total_api_calls': 1234,  # Not meaningful for data loading
        'cache_hit_rate': 0.95    # Irrelevant to historical import
    }

    # CORRECT: Track data loading specific metrics
    metrics = {
        'job_success_rate': 0.99,           # % jobs completed successfully
        'average_load_time_per_symbol': 2.5, # seconds
        'symbols_loaded_per_day': 500,
        'error_rate': 0.01,                  # % jobs failed
        'data_loss_incidents': 0             # Critical: zero expected
    }
    ```

## How

### Data Models (Database & Redis)

**Redis Job Status Structure**:
```python
# Job status stored in Redis (expires after 7 days)
# Key: tickstock:job:status:{job_id}
# Value: JSON string

{
    "job_id": "abc123-uuid",
    "status": "running",  # pending, running, completed, failed
    "progress": 45,       # 0-100 percentage
    "current_symbol": "AAPL",
    "symbols_completed": 45,
    "symbols_total": 102,
    "started_at": "2026-02-08T15:30:05",
    "completed_at": null,
    "error": null
}
```

**No New Database Tables** (use existing):
- Job submission tracked in `job_executions` table (Sprint 69)
- Historical data stored in `ohlcv_daily`, `ohlcv_1hour`, etc. (by TickStockPL)
- Analysis results in `indicator_results`, `daily_patterns` (Sprint 68-69)

### Implementation Tasks (Dependency-Ordered, Information-Dense)

**Week 1: Historical Import Consolidation (Days 1-5)**

**Day 1: Audit & Remove Duplicate Historical Loader**
- Create audit script `scripts/audit_historical_loader_usage.py`
  - Use `rg` (ripgrep) to find all references to historical_loader
  - Search patterns: "from src.data.historical_loader", "HistoricalLoader", "MassiveHistoricalLoader"
  - Output: JSON file with all references (file, line number, text)
- Run audit script and document all references
  - Expected: 5-10 references across src/, web/, tests/
- Create migration checklist in docs/planning/sprints/sprint70/REMOVAL_CHECKLIST.md
  - List all files to remove (historical_loader.py, tests)
  - List all files to update (imports, direct calls)
  - Validation steps (zero references, integration tests pass)
- Remove `src/data/historical_loader.py` (1,220 lines)
- Remove associated test files (if exist): `tests/unit/data/test_historical_loader.py`
- Update files with historical_loader imports:
  - `src/data/eod_processor.py` - Remove import, replace with Redis job queue
  - `src/api/routes/admin.py` - Ensure uses Redis job queue (verify existing code)
  - Any other files identified in audit
- Create validation test: `tests/unit/validation/test_no_historical_loader.py`
  - Test: Zero references to historical_loader in codebase
  - Test: historical_loader.py file does not exist
- Run validation tests
- Success: historical_loader.py removed, zero references, 2+ validation tests pass

**Day 2: Admin UI Job Status Polling Endpoint**
- Create new endpoint in `src/api/rest/admin_historical_data_redis.py`
  - Route: `GET /admin/historical-data/job-status/<job_id>`
  - Logic: Fetch job status from Redis (key: tickstock:job:status:{job_id})
  - Return: JSON with job status, progress, symbols_completed, symbols_total, current_symbol, error
  - Error handling: Return 404 if job not found, 500 if Redis error
- Update existing `/admin/historical-data/trigger-load` endpoint (if needed)
  - Verify: Job submitted to Redis (tickstock.jobs.data_load)
  - Verify: Job status initialized in Redis (pending status)
  - Verify: Job ID returned to client
- Write integration test: `tests/integration/test_job_status_polling.py`
  - Test: Submit job, verify job_id returned
  - Test: Poll job status, verify format
  - Test: Handle job not found (404)
  - Test: Redis connection error handling
- Success: Job status polling endpoint functional, 4+ integration tests pass

**Day 3: Admin UI Progress Bar Implementation**
- Update `web/templates/admin/historical_data_dashboard.html`
  - Add progress container: `<div id="progress-container" style="height: 80px;">`
  - Add progress bar: Bootstrap `.progress` with `.progress-bar` inside
  - Add status text: Display current symbol, symbols completed/total, elapsed time
  - Add error alert: Bootstrap `.alert-danger` for job failures
- Create/update `web/static/js/admin/historical-data.js`
  - Add `submitJob()` function: POST to `/admin/historical-data/trigger-load`
  - Add `pollJobStatus()` function: GET from `/admin/historical-data/job-status/<job_id>`
  - Add `updateProgressBar()` function: Update UI with job status
  - Add polling logic: `setInterval(pollJobStatus, 2000)` (2s interval)
  - Add cleanup: `clearInterval()` on completion or failure
  - Add error handling: Display error messages in UI
- Test manually: Submit job, verify progress bar updates, verify completion notification
- Success: Progress bar UI functional, real-time updates working

**Day 4: Single Source of Truth Validation**
- Create validation test: `tests/integration/test_single_source_of_truth.py`
  - Test: AppV2 has NO OHLCV write operations (except TickStockPL)
  - Test: Historical import goes through Redis job queue (not direct)
  - Test: Admin UI uses existing TickStockPLClient (not duplicate loader)
  - Test: Job completion triggers PostImportAnalysisJob (Sprint 69 integration)
- Create integration test: `tests/integration/test_historical_import_workflow.py`
  - Test end-to-end: Submit job → Redis → TickStockPL → Data load → Completion event → Analysis trigger
  - Mock TickStockPL responses (or use test environment)
  - Verify: Data loaded to ohlcv_daily table
  - Verify: PostImportAnalysisJob triggered
  - Verify: Analysis results in indicator_results, daily_patterns tables
- Run integration test suite: `python run_tests.py`
- Success: Single source of truth validated, end-to-end workflow working, all tests pass

**Day 5: Week 1 Validation & Documentation**
- Run comprehensive integration tests: `python run_tests.py`
- Verify: Zero regressions vs Sprint 68-69 baseline
- Verify: Duplicate historical loader completely removed
- Verify: Admin UI uses Redis job queue exclusively
- Verify: Job status polling working (<50ms response time)
- Verify: Progress bar UI displays correctly
- Create `docs/architecture/single-source-of-truth.md`
  - Document: Component boundaries (TickStockPL = Data Producer, AppV2 = Consumer/Analyzer)
  - Document: Data flow diagram (Admin UI → Redis → TickStockPL → AppV2 Analysis)
  - Document: Single source of truth for each capability
- Update `docs/architecture/data-flow.md` with unified workflow
- Success: All tests pass, documentation updated, Week 1 complete

**Week 2: TickStockPL Archival & Monitoring (Days 6-10)**

**Day 6-7: TickStockPL Archival Plan**
- Create `docs/planning/sprints/sprint70/TICKSTOCKPL_ARCHIVAL.md`
  - **CRITICAL**: TickStockPL remains deployed (NOT fully deprecated)
  - Deployment status: TickStockPL kept as Data Producer microservice
  - Repository archival: Archive repo as reference (read-only)
  - Rationale: Single source of truth for historical data loading (13,099 lines)
  - Alternative considered: Migrate all to AppV2 (rejected - increases complexity)
  - Services to keep running: TickStockPL API, Redis job handler, MassiveHistoricalLoader
  - Services to deprecate: TickStockPL analysis features (migrated to AppV2 in Sprint 68-69)
- Document: Deployment architecture diagram
  - TickStockPL: Data Producer (historical import, Redis job processing)
  - AppV2: Consumer + Analyzer (analysis, UI, background jobs)
  - Redis: Communication layer (job queue, pub-sub events)
- Document: Rollback procedure (if issues found)
  - Step 1: Identify regression source
  - Step 2: Re-enable AppV2 historical loader (revert Sprint 70 changes)
  - Step 3: Fix TickStockPL integration issue
  - Step 4: Re-migrate after fix validated
- Success: Archival plan documented, deployment status clarified

**Day 8-9: 30-Day Monitoring Dashboard**
- Create monitoring queries in `scripts/monitoring/historical_import_monitoring.sql`
  - Query: Job success rate (last 30 days)
  - Query: Average load time per symbol
  - Query: Symbols loaded per day
  - Query: Error rate (failed jobs / total jobs)
  - Query: Data loss incidents (count discrepancies)
- Create monitoring script: `scripts/monitoring/generate_monitoring_report.py`
  - Run queries against database
  - Fetch job execution data from job_executions table (Sprint 69)
  - Calculate metrics: success rate, load time, error rate
  - Generate report: Markdown format with summary and trends
  - Output: `docs/planning/sprints/sprint70/MONITORING_REPORT.md` (updated daily)
- Create alert thresholds in script:
  - Alert: Job failure rate >5%
  - Alert: Average load time >10 min for 100 symbols
  - Alert: Data loss incidents >0 (critical)
- Setup automated monitoring (optional):
  - Cron job: Run monitoring script daily
  - Email alerts on threshold violations
- Success: Monitoring dashboard operational, reports generated

**Day 10: Sprint 70 Closure & Final Validation**
- Run full integration test suite: `python run_tests.py`
- Verify: All Sprint 68-69-70 tests pass (90+ tests total)
- Verify: Zero regressions vs baseline
- Verify: Performance targets met (<100ms job submission, <50ms polling)
- Create `docs/planning/sprints/sprint70/SPRINT70_COMPLETE.md`
  - Implementation results summary
  - Performance metrics (job submission, polling, load times)
  - Validation results (all 4 levels)
  - Files removed/updated (with line counts)
  - Lessons learned
  - Related commits/PRs
- Update `CLAUDE.md` with Sprint 70 completion
  - Add Sprint 70 summary under "Current Implementation Status"
  - Update "System Integration Points" with final architecture
  - Document TickStockPL deployment status (kept as microservice)
- Update `docs/planning/sprints/MIGRATION_ROADMAP.md` with completion status
- Commit all changes with proper commit message
- Tag sprint completion in git: `git tag sprint70-complete`
- Begin 30-day monitoring period
- Success: Sprint 70 complete, migration trilogy finished

### Implementation Patterns (Code Examples)

**Job Status Polling Endpoint** (`src/api/rest/admin_historical_data_redis.py`):
```python
@app.route('/admin/historical-data/job-status/<job_id>', methods=['GET'])
@login_required
@admin_required
def admin_get_job_status(job_id: str):
    """Get job status from Redis for polling."""
    try:
        # Get job status from Redis
        status_key = f'tickstock:job:status:{job_id}'
        status_data = redis_client.get(status_key)

        if not status_data:
            return jsonify({
                'success': False,
                'error': 'Job not found or expired'
            }), 404

        # Parse status JSON
        status = json.loads(status_data)

        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': status.get('status', 'unknown'),
            'progress': status.get('progress', 0),
            'current_symbol': status.get('current_symbol'),
            'symbols_completed': status.get('symbols_completed', 0),
            'symbols_total': status.get('symbols_total', 0),
            'started_at': status.get('started_at'),
            'completed_at': status.get('completed_at'),
            'error': status.get('error')
        }), 200

    except redis.ConnectionError:
        logger.error("Redis connection failed")
        return jsonify({
            'success': False,
            'error': 'Redis service unavailable'
        }), 500

    except Exception as e:
        logger.error(f"Error fetching job status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

**Progress Bar UI** (`web/templates/admin/historical_data_dashboard.html`):
```html
<!-- Progress Container (reserves space to avoid layout shift) -->
<div id="progress-container" style="height: 80px; margin-top: 20px;">
    <div id="job-progress" style="display: none;">
        <h5>Loading Historical Data</h5>
        <div class="progress" style="height: 30px;">
            <div class="progress-bar progress-bar-striped progress-bar-animated"
                 id="progress-bar"
                 role="progressbar"
                 style="width: 0%"
                 aria-valuenow="0"
                 aria-valuemin="0"
                 aria-valuemax="100">
                0%
            </div>
        </div>
        <p id="progress-text" class="mt-2 text-muted">
            Initializing...
        </p>
    </div>

    <div id="job-complete" class="alert alert-success" style="display: none;">
        <strong>Success!</strong> Historical data loaded successfully.
        <a href="/analysis-results">View analysis results</a>
    </div>

    <div id="job-error" class="alert alert-danger" style="display: none;">
        <strong>Error!</strong> <span id="error-message"></span>
        <button class="btn btn-sm btn-danger" onclick="retryJob()">Retry</button>
    </div>
</div>
```

**JavaScript Polling Logic** (`web/static/js/admin/historical-data.js`):
```javascript
let currentJobId = null;
let pollInterval = null;

// Submit job to TickStockPL via Redis
async function submitJob(symbols, startDate, endDate, timeframe) {
    const response = await fetch('/admin/historical-data/trigger-load', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            symbols: symbols,
            start_date: startDate,
            end_date: endDate,
            timeframe: timeframe,
            run_analysis: true
        })
    });

    const data = await response.json();

    if (data.success) {
        currentJobId = data.job_id;
        startPolling();
    } else {
        showError(data.error);
    }
}

// Start polling job status
function startPolling() {
    // Show progress UI
    document.getElementById('job-progress').style.display = 'block';

    // Poll every 2 seconds
    pollInterval = setInterval(pollJobStatus, 2000);

    // Initial poll
    pollJobStatus();
}

// Poll job status from server
async function pollJobStatus() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`/admin/historical-data/job-status/${currentJobId}`);

        if (response.status === 404) {
            stopPolling();
            showError('Job not found or expired');
            return;
        }

        const data = await response.json();

        if (!data.success) {
            stopPolling();
            showError(data.error);
            return;
        }

        // Update progress bar
        updateProgress(data);

        // Check if completed
        if (data.status === 'completed') {
            stopPolling();
            showSuccess();
        } else if (data.status === 'failed') {
            stopPolling();
            showError(data.error || 'Job failed');
        }

    } catch (error) {
        console.error('Polling error:', error);
        stopPolling();
        showError('Failed to fetch job status');
    }
}

// Update progress bar UI
function updateProgress(data) {
    const progress = data.progress || 0;
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    // Update progress bar
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', progress);
    progressBar.textContent = `${progress}%`;

    // Update status text
    const symbolsCompleted = data.symbols_completed || 0;
    const symbolsTotal = data.symbols_total || 0;
    const currentSymbol = data.current_symbol || 'N/A';

    progressText.textContent = `Processing ${currentSymbol} (${symbolsCompleted}/${symbolsTotal} symbols completed)`;
}

// Stop polling
function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// Show success message
function showSuccess() {
    document.getElementById('job-progress').style.display = 'none';
    document.getElementById('job-complete').style.display = 'block';
}

// Show error message
function showError(message) {
    document.getElementById('job-progress').style.display = 'none';
    document.getElementById('error-message').textContent = message;
    document.getElementById('job-error').style.display = 'block';
}

// Retry failed job
function retryJob() {
    document.getElementById('job-error').style.display = 'none';
    // Re-submit with same parameters
    // ... implementation ...
}
```

**Validation Test: No Historical Loader** (`tests/unit/validation/test_no_historical_loader.py`):
```python
"""
Validation tests to ensure historical_loader is completely removed.
Sprint 70 - Historical Import Consolidation
"""

import os
import subprocess


def test_no_historical_loader_file():
    """Verify historical_loader.py file is deleted."""
    path = 'src/data/historical_loader.py'
    assert not os.path.exists(path), f"File {path} still exists (should be removed)"


def test_no_historical_loader_references():
    """Verify zero references to historical_loader in codebase."""
    # Search for any references to historical_loader
    result = subprocess.run(
        ['rg', 'historical_loader', 'src/', 'web/', 'tests/', '--type', 'py'],
        capture_output=True,
        text=True
    )

    # Filter out this test file itself
    references = [
        line for line in result.stdout.strip().split('\n')
        if line and 'test_no_historical_loader.py' not in line
    ]

    assert len(references) == 0, (
        f"Found {len(references)} references to historical_loader:\n"
        + "\n".join(references[:10])  # Show first 10 references
    )


def test_no_historicalloader_class_references():
    """Verify zero references to HistoricalLoader class name."""
    result = subprocess.run(
        ['rg', 'HistoricalLoader|MassiveHistoricalLoader', 'src/', 'web/', 'tests/', '--type', 'py'],
        capture_output=True,
        text=True
    )

    # Filter out this test file
    references = [
        line for line in result.stdout.strip().split('\n')
        if line and 'test_no_historical_loader.py' not in line
    ]

    assert len(references) == 0, (
        f"Found {len(references)} references to HistoricalLoader class:\n"
        + "\n".join(references[:10])
    )
```

**Integration Test: Historical Import Workflow** (`tests/integration/test_historical_import_workflow.py`):
```python
"""
Integration test for end-to-end historical import workflow.
Sprint 70 - Historical Import Consolidation
"""

import json
import time
import pytest
from unittest.mock import patch, MagicMock


def test_historical_import_workflow_end_to_end(client, mock_redis, mock_db):
    """
    Test full historical import workflow:
    1. Submit job via Admin UI
    2. Job published to Redis
    3. TickStockPL processes job (mocked)
    4. Job status updates in Redis
    5. Admin UI polls for status
    6. Job completion triggers PostImportAnalysisJob (Sprint 69)
    """

    # Step 1: Submit job via Admin UI
    response = client.post('/admin/historical-data/trigger-load', json={
        'symbols': ['AAPL', 'NVDA'],
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
        'timeframe': 'daily',
        'run_analysis': True
    })

    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    job_id = data['job_id']
    assert job_id is not None

    # Step 2: Verify job published to Redis
    # (Check mock_redis.publish was called with correct channel and payload)
    assert mock_redis.publish.called
    call_args = mock_redis.publish.call_args
    assert call_args[0][0] == 'tickstock.jobs.data_load'  # Channel
    job_request = json.loads(call_args[0][1])  # Payload
    assert job_request['job_id'] == job_id
    assert job_request['job_type'] == 'symbol_load'

    # Step 3: Mock TickStockPL processing (update job status in Redis)
    mock_redis.set(f'tickstock:job:status:{job_id}', json.dumps({
        'job_id': job_id,
        'status': 'running',
        'progress': 50,
        'current_symbol': 'AAPL',
        'symbols_completed': 1,
        'symbols_total': 2
    }))

    # Step 4: Admin UI polls for status
    response = client.get(f'/admin/historical-data/job-status/{job_id}')
    assert response.status_code == 200
    status = response.json
    assert status['success'] is True
    assert status['status'] == 'running'
    assert status['progress'] == 50

    # Step 5: Mock job completion
    mock_redis.set(f'tickstock:job:status:{job_id}', json.dumps({
        'job_id': job_id,
        'status': 'completed',
        'progress': 100,
        'symbols_completed': 2,
        'symbols_total': 2,
        'completed_at': '2026-02-08T15:35:22'
    }))

    # Mock data_load_complete event (TickStockPL publishes)
    completion_event = {
        'event_type': 'data_load_complete',
        'job_id': job_id,
        'symbols': ['AAPL', 'NVDA'],
        'timeframe': 'daily',
        'run_analysis': True
    }
    # DataLoadListener (Sprint 69) would pick this up and trigger PostImportAnalysisJob

    # Step 6: Verify job completion
    response = client.get(f'/admin/historical-data/job-status/{job_id}')
    assert response.status_code == 200
    status = response.json
    assert status['success'] is True
    assert status['status'] == 'completed'
    assert status['progress'] == 100

    # Step 7: Verify data loaded (check database)
    query = "SELECT COUNT(*) FROM ohlcv_daily WHERE symbol IN ('AAPL', 'NVDA')"
    count = mock_db.execute_read(query)[0][0]
    assert count > 0, "No data loaded to ohlcv_daily table"

    # Step 8: Verify PostImportAnalysisJob triggered (Sprint 69 integration)
    # (Check that analysis results exist in indicator_results and daily_patterns tables)
    query = "SELECT COUNT(*) FROM indicator_results WHERE symbol IN ('AAPL', 'NVDA')"
    indicator_count = mock_db.execute_read(query)[0][0]
    assert indicator_count > 0, "PostImportAnalysisJob did not run indicators"

    query = "SELECT COUNT(*) FROM daily_patterns WHERE symbol IN ('AAPL', 'NVDA')"
    pattern_count = mock_db.execute_read(query)[0][0]
    # Pattern count may be 0 (no patterns detected) - that's OK
    # Just verify query succeeds


def test_job_status_polling_not_found(client):
    """Test job status endpoint returns 404 for non-existent job."""
    response = client.get('/admin/historical-data/job-status/non-existent-job-id')
    assert response.status_code == 404
    data = response.json
    assert data['success'] is False
    assert 'not found' in data['error'].lower()
```

### Integration Points

**Sprint 69 Integration** (PostImportAnalysisJob):
- DataLoadListener (Sprint 69) subscribes to tickstock.jobs.data_load
- On data_load_complete event: Triggers PostImportAnalysisJob
- PostImportAnalysisJob calculates indicators + patterns for imported symbols
- Results stored in indicator_results, daily_patterns tables
- **No changes needed** in Sprint 70 (integration already working)

**TickStockPL Integration** (Redis Job Queue):
- AppV2 publishes job requests to tickstock.jobs.data_load
- TickStockPL job handler subscribes to tickstock.jobs.data_load
- TickStockPL updates job status in Redis (tickstock:job:status:{job_id})
- TickStockPL publishes completion event to tickstock.jobs.data_load
- **Existing integration** - Sprint 70 leverages this (no changes to TickStockPL)

**Admin UI Integration** (Existing Pattern):
- `/admin/historical-data/trigger-load` endpoint already uses Redis job queue
- **New**: `/admin/historical-data/job-status/<job_id>` endpoint for polling
- **New**: JavaScript polling logic with progress bar updates
- **Existing**: TickStockPLClient for job submission (used by endpoint)

## Validation

### Level 1: Syntax & Style Validation

**Tools**: ruff (linting)

**Commands**:
```bash
# Lint updated files
ruff check src/api/rest/admin_historical_data_redis.py
ruff check web/static/js/admin/historical-data.js

# Lint test files
ruff check tests/unit/validation/test_no_historical_loader.py
ruff check tests/integration/test_historical_import_workflow.py

# Expected: Zero errors, zero warnings
```

**Success Criteria**:
- Zero linting errors
- File naming conventions followed
- No "Generated by Claude" comments in code

### Level 2: Unit Tests

**Test Coverage**: 10+ unit tests

**Commands**:
```bash
# Run validation tests
pytest tests/unit/validation/test_no_historical_loader.py -v

# Run job status tests
pytest tests/unit/api/test_admin_historical_data.py -v

# Expected: All tests pass
```

**Test Cases**:
- `test_no_historical_loader_file()` - Verify historical_loader.py deleted
- `test_no_historical_loader_references()` - Verify zero references in codebase
- `test_no_historicalloader_class_references()` - Verify zero class name references
- `test_job_status_endpoint_success()` - Verify job status polling works
- `test_job_status_endpoint_not_found()` - Verify 404 for non-existent job
- `test_job_status_endpoint_redis_error()` - Verify Redis error handling

**Success Criteria**:
- All 10+ unit tests pass
- Validation tests confirm complete removal
- Code coverage >80% for updated files

### Level 3: Integration Tests

**Test Coverage**: 10+ integration tests

**Commands**:
```bash
# Run full integration test suite (MANDATORY before commits)
python run_tests.py

# Run historical import workflow test
pytest tests/integration/test_historical_import_workflow.py -v

# Run single source of truth validation
pytest tests/integration/test_single_source_of_truth.py -v

# Expected: All tests pass, pattern flow tests maintain baseline
```

**Test Cases**:
- `test_historical_import_workflow_end_to_end()` - Full workflow (submission → status → completion)
- `test_job_submission_via_admin_ui()` - Verify Admin UI job submission
- `test_job_status_polling_workflow()` - Verify polling updates progress bar
- `test_job_completion_triggers_analysis()` - Verify PostImportAnalysisJob integration
- `test_single_source_of_truth_data_loading()` - Verify TickStockPL owns data loading
- `test_single_source_of_truth_analysis()` - Verify AppV2 owns analysis
- `test_no_ohlcv_writes_in_appv2()` - Verify AppV2 has no OHLCV INSERT operations
- `test_redis_job_queue_integration()` - Verify Redis communication
- `test_progress_bar_ui_updates()` - Verify JavaScript polling and UI updates
- `test_error_handling_job_failure()` - Verify error display in UI

**Success Criteria**:
- All 10+ integration tests pass
- Pattern flow tests maintain Sprint 68-69 baseline (zero regressions)
- End-to-end workflow validated (Admin UI → TickStockPL → Analysis)
- Performance targets met (<100ms submission, <50ms polling)

### Level 4: TickStock-Specific Validation

**Architecture Compliance**:
```yaml
single_source_of_truth_validation:
  - ✅ TickStockPL owns historical data loading (no AppV2 duplicates)
  - ✅ AppV2 owns analysis (indicators, patterns - Sprint 68)
  - ✅ Admin UI uses Redis job queue (no direct loading)
  - ✅ Job completion triggers PostImportAnalysisJob (Sprint 69)

component_boundary_validation:
  - ✅ AppV2 has NO OHLCV INSERT operations (Consumer role enforced)
  - ✅ TickStockPL is Data Producer (historical import only)
  - ✅ Redis pub-sub for cross-component events
  - ✅ Clear separation of concerns (data loading vs analysis)

performance_validation:
  - ✅ Job submission: <100ms (Redis publish)
  - ✅ Job status polling: <50ms (Redis get)
  - ✅ Admin UI page load: <200ms
  - ✅ Redis operations: <10ms

deployment_validation:
  - ✅ TickStockPL remains deployed (Data Producer microservice)
  - ✅ AppV2 runs standalone for analysis features
  - ✅ Repository archival documented (read-only)
  - ✅ 30-day monitoring plan established

regression_validation:
  - ✅ Pattern detection accuracy maintained (Sprint 68 baseline)
  - ✅ Indicator calculation values maintained (Sprint 68 baseline)
  - ✅ Background jobs working (Sprint 69 baseline)
  - ✅ Integration tests pass identically
```

**Validation Commands**:
```bash
# Architecture validation
python run_tests.py  # Must pass all Sprint 68-69-70 tests

# Single source of truth validation (manual)
# 1. Search for OHLCV INSERT in AppV2 (should be zero)
rg "INSERT INTO ohlcv" src/ --type py
# Expected: Zero matches

# 2. Search for historical_loader references (should be zero)
rg "historical_loader" src/ web/ tests/ --type py
# Expected: Zero matches (except test_no_historical_loader.py)

# 3. Verify Admin UI uses Redis (should use existing endpoint)
rg "admin_trigger_historical_load" src/api/rest/admin_historical_data_redis.py
# Expected: Function uses redis_client.publish()

# 30-day monitoring (execute after Sprint 70 complete)
python scripts/monitoring/generate_monitoring_report.py
# Expected: Report generated with job metrics
```

**Success Criteria**:
- Single source of truth validated (TickStockPL for data, AppV2 for analysis)
- Component boundaries enforced (no architectural violations)
- Performance targets met (<100ms, <50ms)
- TickStockPL deployment status clarified (kept as microservice)
- Zero regressions vs Sprint 68-69 baseline

## Anti-Patterns (What NOT to Do)

### Architecture Violations
1. ❌ Creating new historical loader in AppV2
   - ✅ Use Redis job queue to delegate to TickStockPL
2. ❌ Adding OHLCV INSERT operations to AppV2
   - ✅ TickStockPL owns historical data loading exclusively
3. ❌ Bypassing Redis job queue (direct TickStockPL API calls)
   - ✅ Always use Redis job queue for async workflow
4. ❌ Assuming TickStockPL fully deprecated
   - ✅ TickStockPL remains deployed as Data Producer microservice

### Data Handling Mistakes
5. ❌ Not validating job status expiration (7 days)
   - ✅ Use Redis SETEX with 7-day TTL
6. ❌ Polling too frequently (overloads Redis)
   - ✅ Use 2 second interval (reasonable balance)
7. ❌ Not clearing polling interval on completion
   - ✅ Always clearInterval() on completed/failed status
8. ❌ Not handling 404 for expired jobs
   - ✅ Display "Job not found or expired" message

### Performance Anti-Patterns
9. ❌ Blocking Admin UI waiting for job completion
   - ✅ Use async polling with progress bar
10. ❌ Not reserving space for progress bar (layout shift)
    - ✅ Reserve container height (80px) to avoid layout jump
11. ❌ Submitting large jobs synchronously
    - ✅ Always use Redis job queue (async by design)
12. ❌ Not tracking job metrics for monitoring
    - ✅ Log all job executions to job_executions table (Sprint 69)

### Testing Errors
13. ❌ Not testing end-to-end workflow
    - ✅ Test full flow: submission → status → completion → analysis
14. ❌ Not validating single source of truth
    - ✅ Test that AppV2 has NO OHLCV writes
15. ❌ Not testing JavaScript polling logic
    - ✅ Test progress bar updates, completion handling, error display
16. ❌ Skipping integration tests before commits
    - ✅ ALWAYS run `python run_tests.py` (MANDATORY)

### Documentation Errors
17. ❌ Not documenting component boundaries clearly
    - ✅ Single source of truth documented (data loading vs analysis)
18. ❌ Not updating CLAUDE.md with Sprint 70 completion
    - ✅ Update all documentation (CLAUDE.md, architecture docs, sprint completion)
19. ❌ Not documenting TickStockPL deployment status
    - ✅ Clear documentation: TickStockPL kept as Data Producer microservice
20. ❌ Not creating 30-day monitoring plan
    - ✅ Monitoring dashboard with metrics, alerts, success criteria

## Final Validation Checklist

Before marking Sprint 70 complete, verify:

### Code Quality
- [ ] All ruff linting passes (zero errors)
- [ ] No "Generated by Claude" comments in code
- [ ] File naming conventions followed
- [ ] Code coverage >80% for updated files

### Functionality
- [ ] Duplicate historical loader removed (1,220 lines)
- [ ] Zero references to historical_loader in codebase
- [ ] Admin UI uses Redis job queue exclusively
- [ ] Job status polling endpoint functional (<50ms)
- [ ] Progress bar UI displays real-time updates
- [ ] Job submission workflow working (Admin UI → Redis → TickStockPL)
- [ ] Single source of truth validated (TickStockPL for data, AppV2 for analysis)

### Testing
- [ ] 10+ unit tests pass (validation, job status)
- [ ] 10+ integration tests pass (workflow, single source of truth)
- [ ] Integration tests maintain Sprint 68-69 baseline (zero regressions)
- [ ] End-to-end workflow validated (submission → status → completion → analysis)

### Performance
- [ ] Job submission: <100ms (Redis publish)
- [ ] Job status polling: <50ms (Redis get)
- [ ] Admin UI page load: <200ms
- [ ] Redis operations: <10ms

### Architecture
- [ ] Single source of truth established (TickStockPL for data, AppV2 for analysis)
- [ ] Component boundaries enforced (no OHLCV writes in AppV2)
- [ ] TickStockPL deployment status clarified (kept as microservice)
- [ ] Redis job queue working end-to-end
- [ ] PostImportAnalysisJob integration verified (Sprint 69)

### Documentation
- [ ] CLAUDE.md updated with Sprint 70 completion
- [ ] docs/architecture/single-source-of-truth.md created
- [ ] docs/architecture/data-flow.md updated
- [ ] docs/planning/sprints/sprint70/TICKSTOCKPL_ARCHIVAL.md created
- [ ] docs/planning/sprints/sprint70/SPRINT70_COMPLETE.md created
- [ ] docs/planning/sprints/MIGRATION_ROADMAP.md updated (completion status)

### Monitoring
- [ ] 30-day monitoring dashboard operational
- [ ] Monitoring script generates reports daily
- [ ] Alert thresholds configured (failure rate >5%, load time >10 min)
- [ ] Success criteria defined (job success rate >99%, error rate <1%)

### Deployment Readiness
- [ ] TickStockPL remains deployed (Data Producer microservice)
- [ ] AppV2 runs standalone for analysis features
- [ ] Repository archival plan documented (read-only)
- [ ] Rollback procedure tested (if needed)
- [ ] All Sprint 68-69-70 tests pass (90+ tests)

---

**Estimated Implementation Time**: 2 weeks (10 working days)
- Week 1: Historical import consolidation (Days 1-5)
- Week 2: TickStockPL archival & monitoring (Days 6-10)

**Dependencies**: Sprint 69 complete (background jobs, pattern/indicator automation)

**Risk Level**: LOW (Redis job queue already in place, Sprint 69 integration working)

**One-Pass Implementation Confidence**: 92/100

**Next Steps**:
- Begin 30-day monitoring period (post-Sprint 70)
- Finalize TickStockPL deployment status (kept as microservice)
- Archive TickStockPL repository (read-only reference)
- Update deployment documentation

**Migration Trilogy Complete**: Sprint 68 (Analysis) → Sprint 69 (Jobs) → Sprint 70 (Data Loading)
