# Sprint 73: Process Stock Analysis - Independent Analysis Page

**Sprint Type**: Feature Implementation - Admin UI Integration
**Priority**: HIGH (Unlocks Sprints 68-72 capabilities)
**Estimated Effort**: 2-3 days
**Dependencies**: Sprint 68-72 (Core Analysis Engine) - COMPLETE ✅

---

## User Story

**As an** administrator
**I want** an independent "Process Stock Analysis" admin page
**So that** I can manually trigger pattern/indicator analysis for selected stocks or universes without needing to re-import historical data

---

## Acceptance Criteria

### 1. New Admin Page: `/admin/process-analysis`

**Navigation**:
- ✅ Add to admin navigation bar (alongside Historical Data, User Management, Health Monitor)
- ✅ Icon: 🔬 or 📊 "Process Stock Analysis"
- ✅ Admin-only access (requires @admin_required decorator)

**Page Layout** (Similar to Historical Data Dashboard):
```
┌─────────────────────────────────────────────────────┐
│  Process Stock Analysis                              │
├─────────────────────────────────────────────────────┤
│                                                       │
│  [Universe Selector ▼]  OR  [Enter Symbols: AAPL, NVDA, TSLA] │
│                                                       │
│  Analysis Type:                                       │
│  [ ] Patterns Only                                    │
│  [ ] Indicators Only                                  │
│  [X] Both (default)                                   │
│                                                       │
│  Timeframe:                                           │
│  (•) Daily   ( ) Hourly   ( ) Weekly   ( ) Monthly   │
│                                                       │
│  [🔬 Run Analysis]                                    │
│                                                       │
│  ┌─────────────────────────────────────────────┐     │
│  │ Progress Bar (0%)                            │     │
│  │ Status: Analyzing AAPL (5/102 symbols)      │     │
│  └─────────────────────────────────────────────┘     │
│                                                       │
│  Active Jobs                 Recent Jobs              │
│  ├─ Job abc123 (50%)        ├─ Job xyz789 (✅)       │
│  └─ Running...              └─ 102 symbols, 45 patterns│
└─────────────────────────────────────────────────────┘
```

### 2. Universe Selector Integration

**Requirements**:
- ✅ Dropdown populated from RelationshipCache (Sprint 60)
- ✅ Universe options: SPY, QQQ, nasdaq100, dow30, russell3000, etc.
- ✅ Multi-universe join support: "SPY:nasdaq100" (518 distinct symbols)
- ✅ Manual symbol entry: "AAPL, NVDA, TSLA" (comma-separated)
- ✅ Preview: "Selected: 102 symbols from nasdaq100"

### 3. Analysis Options

**Analysis Type**:
- ✅ Patterns Only: Run 8 patterns (Doji, Hammer, Engulfing, etc.)
- ✅ Indicators Only: Run 8 indicators (SMA, RSI, MACD, etc.)
- ✅ Both (default): Run all patterns + indicators

**Timeframe Selection**:
- ✅ Daily (default)
- ✅ Hourly (if data available)
- ✅ Weekly (if data available)
- ✅ Monthly (if data available)

### 4. Backend API Endpoint

**Route**: `POST /admin/process-analysis/trigger`

**Request Format**:
```json
{
  "universe_key": "nasdaq100",           // OR null if using symbols
  "symbols": ["AAPL", "NVDA", "TSLA"],   // OR null if using universe
  "analysis_type": "both",               // "patterns", "indicators", "both"
  "timeframe": "daily",                  // "daily", "hourly", "weekly", "monthly"
  "submitted_by": "admin_username"
}
```

**Response Format**:
```json
{
  "success": true,
  "job_id": "analysis_abc123def456",
  "symbols_count": 102,
  "analysis_type": "both",
  "timeframe": "daily",
  "estimated_time_seconds": 180
}
```

**Error Handling**:
- ✅ 400: Invalid universe key or symbols
- ✅ 400: No symbols selected
- ✅ 404: No OHLCV data found for symbols
- ✅ 500: Database/analysis engine error

### 5. Background Job Execution

**Job Lifecycle**:
1. **Queued**: Job created, added to active_jobs dict
2. **Running**: Iterating through symbols, calling AnalysisService
3. **Completed**: All symbols processed, results stored
4. **Failed**: Error occurred during processing

**Job Tracking** (In-Memory for Sprint 73):
```python
active_jobs[job_id] = {
    'id': job_id,
    'status': 'running',  # queued, running, completed, failed
    'symbols': ['AAPL', 'NVDA', ...],
    'analysis_type': 'both',
    'timeframe': 'daily',
    'progress': 45,  # percentage
    'current_symbol': 'AAPL',
    'symbols_completed': 45,
    'symbols_total': 102,
    'patterns_detected': 12,
    'indicators_calculated': 45,
    'errors': [],
    'started_at': '2026-02-11T10:00:00',
    'completed_at': None
}
```

### 6. Progress Polling

**Route**: `GET /admin/process-analysis/job-status/<job_id>`

**Response Format**:
```json
{
  "success": true,
  "job_id": "analysis_abc123",
  "status": "running",
  "progress": 45,
  "current_symbol": "AAPL",
  "symbols_completed": 45,
  "symbols_total": 102,
  "patterns_detected": 12,
  "indicators_calculated": 45,
  "errors": [],
  "elapsed_seconds": 45,
  "estimated_remaining_seconds": 90
}
```

**JavaScript Polling**:
- ✅ Poll every 2 seconds (like historical import)
- ✅ Update progress bar with percentage
- ✅ Display current symbol being processed
- ✅ Show completion notification
- ✅ Clear interval on completion/failure

### 7. Analysis Results Display

**On Completion**:
```
✅ Analysis Complete!

Results:
- 102 symbols analyzed
- 45 patterns detected (12 Doji, 8 Hammer, 25 Engulfing, ...)
- 816 indicators calculated (102 × 8 indicators)
- 3 errors (TSLA: insufficient data, ...)

[View Pattern Results] [View Indicator Results] [Download Report]
```

**Results Storage**:
- ✅ Patterns → `daily_patterns` table
- ✅ Indicators → `indicator_results` table
- ✅ Timestamps for auditability
- ✅ Analysis run metadata

---

## Technical Requirements

### Files to Create

**Admin Route** (1 file):
- `src/api/rest/admin_process_analysis.py` (~300 lines)
  - `admin_process_analysis_dashboard()` - Render page
  - `admin_trigger_analysis()` - POST endpoint for job submission
  - `admin_get_analysis_job_status()` - GET endpoint for polling
  - `admin_cancel_analysis_job()` - POST endpoint for cancellation

**HTML Template** (1 file):
- `web/templates/admin/process_analysis_dashboard.html` (~400 lines)
  - Universe selector dropdown
  - Symbol input field
  - Analysis type checkboxes
  - Timeframe radio buttons
  - Progress bar UI
  - Active jobs list
  - Recent jobs history

**JavaScript** (1 file):
- `web/static/js/admin/process_analysis.js` (~300 lines)
  - `submitAnalysisJob()` - Form submission
  - `pollJobStatus()` - Status polling (2s interval)
  - `updateProgressBar()` - UI updates
  - `showResults()` - Completion display

### Files to Update

**App Registration**:
- `src/app.py` - Register admin_process_analysis routes

**Admin Navigation**:
- `web/templates/admin/base_admin.html` - Add "Process Stock Analysis" link

**Integration Points**:
- `src/analysis/services/analysis_service.py` - Use existing (no changes)
- `src/core/services/relationship_cache.py` - Use get_universe_symbols() (no changes)
- `src/analysis/data/ohlcv_data_service.py` - Use get_universe_ohlcv_data() (no changes)

---

## Implementation Approach

### Phase 1: Admin Route & Job Management (Day 1)
1. Create `src/api/rest/admin_process_analysis.py`
2. Implement job submission endpoint (POST /admin/process-analysis/trigger)
3. Implement job status endpoint (GET /admin/process-analysis/job-status/<job_id>)
4. In-memory job tracking (active_jobs dict, job_history list)
5. Background thread for analysis execution

### Phase 2: HTML Template & UI (Day 1-2)
1. Create `web/templates/admin/process_analysis_dashboard.html`
2. Universe selector with RelationshipCache integration
3. Symbol input field with validation
4. Analysis type checkboxes (patterns, indicators, both)
5. Timeframe radio buttons
6. Progress bar container

### Phase 3: JavaScript Polling Logic (Day 2)
1. Create `web/static/js/admin/process_analysis.js`
2. Form submission handler
3. Job status polling (2s interval)
4. Progress bar updates
5. Completion/error notifications

### Phase 4: Analysis Execution Loop (Day 2)
1. Iterate through symbols
2. Call AnalysisService.analyze_symbol() for each
3. Store results to database (daily_patterns, indicator_results)
4. Update job status in active_jobs dict
5. Handle errors gracefully (continue processing remaining symbols)

### Phase 5: Testing & Validation (Day 3)
1. Manual testing: Submit job, verify progress updates
2. Integration test: End-to-end workflow (submit → poll → complete)
3. Error handling: Invalid universe, no data, analysis failures
4. Performance: 100 symbols in <3 minutes

---

## Success Metrics

### Functional
- ✅ Admin page accessible at `/admin/process-analysis`
- ✅ Universe selector loads from RelationshipCache
- ✅ Job submission creates background job
- ✅ Progress bar updates every 2 seconds
- ✅ Analysis results stored in database
- ✅ Completion notification displayed

### Performance
- ✅ Job submission: <100ms (thread spawn)
- ✅ Job status polling: <50ms (dict lookup)
- ✅ Analysis throughput: >30 symbols/minute (~2s per symbol)
- ✅ 100 symbols complete in <4 minutes

### Quality
- ✅ Zero regressions (pattern flow tests still pass)
- ✅ Error handling for all edge cases
- ✅ Admin-only access enforced
- ✅ Clean, maintainable code (<500 lines per file)

---

## Integration with Existing System

### Sprint 68-72 Integration
- ✅ Uses AnalysisService (Sprint 68) - NO changes needed
- ✅ Uses OHLCVDataService (Sprint 72) - NO changes needed
- ✅ Uses RelationshipCache (Sprint 60) - NO changes needed
- ✅ Stores to daily_patterns, indicator_results tables

### Admin UI Patterns
- ✅ Follows Historical Data dashboard patterns
- ✅ Similar job submission workflow
- ✅ Similar progress bar UI
- ✅ Consistent navigation and styling

---

## Future Enhancements (Sprint 74+)

**Sprint 74**: Historical Import Integration
- Add "Run Analysis After Import" checkbox to Historical Data dashboard
- Automatically trigger analysis after OHLCV import completes
- Unified workflow: Import → Analyze → Complete

**Future**:
- Redis job queue for distributed processing
- Job history persistence (database table)
- Analysis scheduling (cron-like)
- Email notifications on completion
- Detailed analysis reports (PDF/CSV export)

---

## Risk Assessment

**Risk Level**: LOW
**Confidence**: 95/100

**Why Low Risk?**
- ✅ All underlying services already tested (Sprints 68-72)
- ✅ Similar patterns to existing Historical Data dashboard
- ✅ In-memory job tracking (simple, no external dependencies)
- ✅ Background threads (no complex async/await)

**Potential Issues**:
- ⚠️ Large universe (1000+ symbols) may take >10 minutes
  - **Mitigation**: Display estimated time, allow cancellation
- ⚠️ Concurrent jobs may overwhelm database
  - **Mitigation**: Limit to 1 active job per user (Sprint 73), add job queue (Sprint 75+)

---

## Definition of Done

- ✅ Admin page renders at `/admin/process-analysis`
- ✅ Universe selector loads from RelationshipCache
- ✅ Symbol input accepts comma-separated tickers
- ✅ Job submission creates background job
- ✅ Progress bar polls every 2 seconds
- ✅ Analysis results stored in database
- ✅ Completion notification displayed
- ✅ Integration tests pass (`python run_tests.py`)
- ✅ Pattern flow tests maintain baseline
- ✅ Manual testing: 100 symbols analyzed successfully
- ✅ CLAUDE.md updated with Sprint 73 completion
- ✅ Sprint completion document created

---

**Ready for PRP Creation**: This user story is complete and ready for PRP generation with `/prp-new-create process-stock-analysis`
