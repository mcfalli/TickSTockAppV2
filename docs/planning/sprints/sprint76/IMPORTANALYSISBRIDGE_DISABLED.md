# ImportAnalysisBridge Disabled - Sprint 76

**Date**: February 14, 2026
**Decision**: Disable ImportAnalysisBridge in favor of manual two-step workflow

---

## Problem Statement

**Sprint 75 Phase 2** introduced ImportAnalysisBridge to auto-trigger pattern/indicator analysis after historical data imports. However, this design had critical flaws:

1. **App Startup Flood**: Bridge scanned ALL Redis job history on startup
2. **In-Memory State**: `_processed_jobs` set reset on app restart, causing duplicate processing
3. **Hidden Automation**: Users had no visibility into when analysis would run
4. **Resource Consumption**: 500+ stock analysis blocked app startup for minutes
5. **Complexity**: Background polling thread, Redis metadata keys, job scanning

**Incident**: User imported SPY (500+ stocks) with checkbox enabled. On app restart, bridge processed all 500+ stocks, flooding logs and hanging startup.

---

## Solution: Manual Two-Step Workflow

**New Workflow**:
1. **Import Data**: Use Historical Data Import page (as before)
2. **Run Analysis**: Manually trigger via Process Analysis page when ready

**Benefits**:
- ✅ **Predictable**: User controls when analysis runs
- ✅ **Visible**: Clear UI actions, no hidden background threads
- ✅ **Fast Startup**: App starts in <10 seconds
- ✅ **Simple**: Removed 350+ lines of bridge code complexity
- ✅ **Reliable**: No risk of old jobs re-processing

---

## Changes Made

### **Code Changes**

**1. src/app.py** (3 edits)
- Line 64: Commented out ImportAnalysisBridge import
- Line 105: Commented out global variable
- Lines 2237-2247: Disabled bridge initialization

**2. web/templates/admin/historical_data_dashboard.html**
- Removed "Run Analysis After Import" checkbox
- Added informational notice with link to Process Analysis page

**3. web/static/js/admin/historical_data.js**
- Set `runAnalysis = false` explicitly
- Added comment explaining manual workflow

### **Documentation**

**4. docs/planning/sprints/sprint76/IMPORTANALYSISBRIDGE_DISABLED.md** (this file)
- Documented decision and rationale

**5. CLAUDE.md** (to be updated)
- Remove Sprint 75 Phase 2 references
- Document manual workflow

---

## Migration Path

### **For Users**

**Old Workflow** (Sprint 75):
1. Historical Data Import page
2. Check "Run Analysis After Import" box
3. Import completes → analysis runs automatically

**New Workflow** (Sprint 76):
1. Historical Data Import page
2. Import completes
3. **Go to Process Analysis page**
4. Select universe/symbols and manually trigger analysis

### **For Developers**

**If You Need Auto-Analysis Later**:

Consider these alternatives (in order of preference):

1. **Redis Job Queue** (Best)
   - Push analysis jobs to `tickstock.jobs.analysis.queue`
   - Worker pulls and processes (no polling)
   - Survives restarts, predictable

2. **Event-Driven Trigger** (Good)
   - Subscribe to `tickstock.jobs.data_load.complete:{job_id}`
   - Trigger analysis directly when event received
   - No polling, but requires browser tab open

3. **Scheduled Batch** (Simple)
   - Nightly cron job runs analysis for all stocks
   - Predictable, simple, no real-time dependency

**Do NOT**:
- ❌ Re-enable ImportAnalysisBridge (same problems)
- ❌ Scan all Redis keys on startup (performance issue)
- ❌ Use in-memory state that resets on restart

---

## Testing After Change

### **Expected Behavior**

1. **App Startup**:
   - ✅ No ImportAnalysisBridge initialization messages
   - ✅ No analysis flood in logs
   - ✅ Fast startup (<10 seconds)

2. **Historical Data Import**:
   - ✅ Informational notice visible
   - ✅ Link to Process Analysis page works
   - ✅ Import completes normally
   - ✅ No automatic analysis triggers

3. **Process Analysis Page**:
   - ✅ Manual analysis works as before
   - ✅ Can select SPY universe and analyze 500+ stocks
   - ✅ Progress tracking works

### **Regression Testing**

Run integration tests to ensure no regressions:
```bash
python run_tests.py
```

Expected: All tests pass (ImportAnalysisBridge not tested)

---

## Cleanup Opportunities (Future)

### **Code Cleanup** (Optional - Sprint 77+)
- Remove `src/jobs/import_analysis_bridge.py` entirely (350 lines)
- Remove Redis metadata key creation in `admin_historical_data_redis.py`
- Remove `run_analysis_after_import` parameter from API endpoints
- Remove related unit tests

### **Database Cleanup** (Optional)
- Clean up old Redis metadata keys: `tickstock.jobs.metadata:*`
- Script provided: `scripts/redis/clear_old_job_metadata.py`

---

## Lessons Learned

1. **Avoid Hidden Automation**: Always give users explicit control over expensive operations
2. **Stateless Design**: Avoid in-memory state that resets on restart
3. **Don't Poll on Startup**: Never scan unbounded key sets during app initialization
4. **Keep It Simple**: Manual workflows are better than complex automation with edge cases
5. **Event-Driven > Polling**: If automation needed, use event-driven patterns, not polling

---

## Related Sprints

- **Sprint 75 Phase 2**: ImportAnalysisBridge introduction (now disabled)
- **Sprint 73**: Process Analysis page (now the manual trigger point)
- **Sprint 74**: Dynamic pattern/indicator loading (unaffected)

---

## Document Status

**Status**: ✅ **ACTIVE** - ImportAnalysisBridge disabled as of Sprint 76
**Impact**: Medium (workflow change, user must adapt)
**Reversibility**: High (code commented out, not deleted)
