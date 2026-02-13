# Sprint 74: Historical Import Integration - Auto-Analysis Checkbox

**Sprint Type**: Feature Enhancement - Integration
**Priority**: MEDIUM (Completes Sprint 73 workflow)
**Estimated Effort**: 1 day
**Dependencies**: Sprint 73 (Process Stock Analysis) - REQUIRED

---

## User Story

**As an** administrator
**I want** historical data imports to automatically trigger pattern/indicator analysis
**So that** newly imported data is immediately analyzed without manual intervention

---

## Acceptance Criteria

### 1. Historical Data Dashboard Enhancement

**Update**: `web/templates/admin/historical_data_dashboard.html`

**New Checkbox** (Always Checked by Default):
```html
<div class="form-group">
    <label>
        <input type="checkbox"
               name="run_analysis"
               value="true"
               checked
               id="run-analysis-checkbox">
        Run Analysis After Import (Patterns + Indicators)
    </label>
    <small class="form-text text-muted">
        Automatically analyzes imported symbols after data load completes.
        Uses Process Stock Analysis engine from Sprint 73.
    </small>
</div>
```

**Checkbox Behavior**:
- ✅ Checked by default (recommended workflow)
- ✅ User can uncheck to skip analysis (e.g., testing data imports only)
- ✅ Checkbox state included in form submission

---

### 2. Backend Integration

**Update**: `src/api/rest/admin_historical_data.py`

**Enhanced Job Request**:
```python
# After historical import completes successfully
if job_data['run_analysis'] and job_data['status'] == 'completed':
    # Trigger analysis job from Sprint 73
    analysis_job_id = trigger_analysis_job(
        symbols=job_data['successful_symbols'],
        analysis_type='both',  # patterns + indicators
        timeframe=job_data['timeframe'],  # daily, hourly, weekly
        source='historical_import'
    )
    job_data['analysis_job_id'] = analysis_job_id
```

**Job Lifecycle**:
1. **Historical Import**: Queued → Running → Completed (OHLCV data loaded)
2. **Auto-Trigger**: If `run_analysis=true`, create analysis job (Sprint 73)
3. **Analysis Execution**: Running → Completed (patterns + indicators calculated)
4. **Final Status**: "Import + Analysis Complete"

---

### 3. Progress Bar Enhancement

**Update**: `web/static/js/admin/historical_data.js`

**Two-Phase Progress**:
```javascript
// Phase 1: Historical Import (0-70%)
"Loading OHLCV data... (50/102 symbols) [50%]"

// Phase 2: Analysis (70-100%)
"Running analysis... (50/102 symbols) [85%]"

// Complete
"✅ Import + Analysis Complete
 - 102 symbols imported (5 years daily data)
 - 45 patterns detected
 - 816 indicators calculated"
```

**Progress Calculation**:
```javascript
// Import progress: 0-70%
const importProgress = (symbolsImported / symbolsTotal) * 70;

// Analysis progress: 70-100%
const analysisProgress = 70 + (symbolsAnalyzed / symbolsTotal) * 30;

// Total progress
const totalProgress = job.status === 'importing'
    ? importProgress
    : analysisProgress;
```

---

### 4. Job Status Updates

**Enhanced Status Messages**:
- `importing` - "Loading historical data from Massive API..."
- `import_complete` - "Historical data loaded successfully"
- `analyzing` - "Running pattern and indicator analysis..."
- `completed` - "Import and analysis complete"
- `failed` - "Import or analysis failed (see errors)"

**Database Storage** (Optional - Future):
- Store analysis job reference in `symbol_load_log` table
- Add `analysis_job_id` column
- Track end-to-end workflow

---

## Technical Requirements

### Files to Update

**Historical Data Routes** (1 file):
- `src/api/rest/admin_historical_data.py` (~50 lines modified)
  - Update `admin_trigger_historical_load()` - Accept `run_analysis` parameter
  - Update `run_load_job()` - Trigger analysis on completion
  - Import Sprint 73 analysis trigger function

**HTML Template** (1 file):
- `web/templates/admin/historical_data_dashboard.html` (~20 lines added)
  - Add "Run Analysis After Import" checkbox
  - Update form submission to include checkbox value

**JavaScript** (1 file):
- `web/static/js/admin/historical_data.js` (~50 lines modified)
  - Update progress calculation (two-phase: import 0-70%, analysis 70-100%)
  - Update status messages for two-phase workflow
  - Handle analysis job status polling

**Integration** (1 file):
- `src/api/rest/admin_process_analysis.py` (Sprint 73)
  - Extract analysis trigger logic to reusable function
  - `trigger_analysis_job(symbols, analysis_type, timeframe, source)`

---

## Implementation Approach

### Phase 1: Checkbox UI (30 minutes)
1. Add checkbox to Historical Data dashboard
2. Update form submission to include `run_analysis` value
3. Test: Submit with checkbox checked/unchecked

### Phase 2: Backend Integration (2 hours)
1. Update historical import endpoint to accept `run_analysis` parameter
2. After import completes, check `run_analysis` flag
3. If true, trigger analysis job (Sprint 73 logic)
4. Store analysis job ID in job metadata

### Phase 3: Progress Bar Enhancement (2 hours)
1. Update JavaScript to calculate two-phase progress (0-70%, 70-100%)
2. Update status messages for import vs analysis phases
3. Poll both import job status and analysis job status
4. Display final results (import + analysis summary)

### Phase 4: Testing (2 hours)
1. Manual testing: Import 10 symbols with checkbox checked
2. Verify: OHLCV data loaded → analysis triggered → results stored
3. Manual testing: Import with checkbox unchecked
4. Verify: OHLCV data loaded → analysis NOT triggered
5. Integration test: End-to-end workflow

---

## Success Metrics

### Functional
- ✅ Checkbox displayed on Historical Data dashboard
- ✅ Checkbox checked by default
- ✅ Analysis triggered automatically after import (when checked)
- ✅ Analysis NOT triggered when unchecked
- ✅ Progress bar shows two-phase progress (import + analysis)
- ✅ Final results display import + analysis summary

### Performance
- ✅ No performance impact on import (analysis runs after, not during)
- ✅ Two-phase workflow completes in expected time (import + analysis)
- ✅ Progress updates smoothly (no jumps or freezes)

### Quality
- ✅ Zero regressions (historical import still works standalone)
- ✅ Clean separation (import job vs analysis job)
- ✅ Backward compatible (checkbox can be unchecked for old behavior)

---

## Integration with Existing System

### Sprint 73 Integration
- ✅ Reuses Sprint 73 analysis trigger logic
- ✅ No duplication of analysis code
- ✅ Analysis job runs in background (same as manual trigger)

### Historical Import
- ✅ Minimal changes to existing import workflow
- ✅ Analysis trigger only after successful import
- ✅ Errors in import do not trigger analysis

---

## Future Enhancements (Sprint 75+)

**Analysis Configuration**:
- ⚙️ Dropdown: "Analyze: [ Patterns Only | Indicators Only | Both ]"
- ⚙️ Advanced: Select specific patterns/indicators to run

**Notification System**:
- 📧 Email notification on completion
- 📱 WebSocket notification to active admin sessions

**Scheduling**:
- 🕐 Schedule nightly imports with auto-analysis
- 🕐 Cron-like: "Import + Analyze daily at 9 PM"

---

## Risk Assessment

**Risk Level**: VERY LOW
**Confidence**: 98/100

**Why Very Low Risk?**
- ✅ Minimal changes to existing historical import workflow
- ✅ Analysis trigger is separate job (failure doesn't break import)
- ✅ Checkbox can be unchecked (preserves old behavior)
- ✅ Sprint 73 analysis engine already tested

**No Anticipated Issues**

---

## Definition of Done

- ✅ Checkbox added to Historical Data dashboard
- ✅ Checkbox checked by default
- ✅ Form submission includes `run_analysis` value
- ✅ Analysis triggered after successful import (when checked)
- ✅ Analysis NOT triggered when unchecked
- ✅ Progress bar shows two-phase progress
- ✅ Final results display import + analysis summary
- ✅ Manual testing: Import 10 symbols, verify analysis runs
- ✅ Integration tests pass
- ✅ CLAUDE.md updated with Sprint 74 completion

---

**Status**: USER STORY ONLY (Sprint 73 must complete first)
**Implementation**: Sprint 74 execution begins after Sprint 73 completion
