# Sprint 75 Summary: Pattern/Indicator Processing Integration

**Created**: 2026-02-12
**Status**: 📋 Planning
**Estimated Effort**: 8-12 hours

---

## 🎯 Goal

Connect Sprint 68-74 pattern/indicator analysis to live data flows:
1. **Real-time**: WebSocket bar updates → automatic analysis
2. **Historical**: Admin imports → automatic analysis (optional checkbox)
3. **Backfill**: Process existing bars missing analysis

---

## 📊 Research Summary

### WebSocket Real-Time Flow (Current)
```
Massive API → MassiveWebSocketClient → MarketDataService
    ↓
TickStockDatabase.write_ohlcv_1min() ← SUCCESS (line 234)
    ↓
✅ Bar in database
❌ NO analysis triggered (MISSING INTEGRATION)
```

### Proposed Integration Point
**File**: `src/core/services/market_data_service.py` (line ~240)

**Add after database write**:
```python
if success:
    # Existing tracking code...

    # NEW: Trigger analysis in background thread (non-blocking)
    self._trigger_bar_analysis_async(symbol, timestamp)
```

---

## 🔧 Implementation Phases

### Phase 1: Real-Time WebSocket (3-4 hours)

**What**:
- Add async analysis trigger to `market_data_service.py`
- Spawn background thread when bar created
- Fetch last 200 bars, run AnalysisService
- Persist results to daily_patterns/daily_indicators
- Publish Redis event for UI updates

**Performance Target**: <100ms per bar (non-blocking)

**Key Files**:
- `src/core/services/market_data_service.py` (integration hook)
- `src/analysis/services/analysis_service.py` (existing service)
- `src/analysis/data/ohlcv_data_service.py` (data fetcher)

---

### Phase 2: Historical Import Integration (3-4 hours)

**What**:
- Add checkbox to Historical Data Import page: "Run Analysis After Import"
- Store flag in job metadata when submitting import
- Create `ImportAnalysisBridge` service (background monitor)
- Poll job status every 5 seconds
- When import completes AND flag=true → auto-submit analysis job

**UI Enhancement**:
```
Historical Data Import Page
    ├─ [x] Run Analysis After Import  ← NEW CHECKBOX
    └─ Progress: "Importing (60%) → Analyzing (0%)"
```

**Key Files**:
- `web/templates/admin/historical_data_dashboard.html` (checkbox UI)
- `src/api/rest/admin_historical_data_redis.py` (store flag)
- `src/jobs/import_analysis_bridge.py` (NEW - job monitor)
- `src/app.py` (start bridge on app init)

---

### Phase 3: Backfill Analysis (2-3 hours)

**What**:
- Add "Backfill Analysis" button to Admin Process Analysis page
- Query bars missing patterns: `LEFT JOIN WHERE patterns.id IS NULL`
- Process in batches of 100 bars
- Show progress: "Processed 500 / 10,000 bars"

**Key Files**:
- `src/api/rest/admin_process_analysis.py` (backfill endpoint)
- `web/templates/admin/process_analysis_dashboard.html` (UI button)

---

## 🎯 Success Criteria

### Functional ✅
- [ ] WebSocket bar inserts trigger analysis automatically
- [ ] Historical import checkbox triggers analysis on completion
- [ ] Backfill processes missing bars successfully
- [ ] Results persist to database tables
- [ ] Redis events published for UI updates

### Performance ✅
- [ ] Real-time analysis: <100ms per bar (non-blocking)
- [ ] WebSocket tick ingestion: No degradation (<50ms per tick)
- [ ] Throughput: 100 symbols/minute sustained
- [ ] Memory footprint: <50MB for background threads

### Quality ✅
- [ ] 80%+ test coverage (35 tests planned)
- [ ] Zero regressions (Sprint 73 manual analysis still works)
- [ ] Error resilience (analysis failures don't break WebSocket)

---

## 🏗️ Architecture Lessons from TickStockPL

Based on codebase research, TickStockPL uses:

1. **Subscriber Pattern** (Recommended)
   - Bar completion → notify subscribers
   - Decoupled, extensible, error-isolated
   - Used for: StreamingPatternJob, StreamingIndicatorJob

2. **Real-Time Processing** (No Batching)
   - Process each bar immediately upon completion
   - Low latency: <100ms from bar → pattern detection
   - Trade-off: Higher CPU usage vs batching

3. **Pattern-Specific Bar Requirements** (Sprint 43 lesson)
   - Single-bar patterns detect at bar 1 (1 minute)
   - Multi-bar patterns detect when sufficient history
   - No blanket 5-bar minimum (caused 5-8 min delay)

4. **Hybrid Approach for Production**
   - Primary: Real-time processing (immediate)
   - Safety net: Batch catch-up job (every 5 minutes)
   - Resilient + low latency

---

## ⚠️ Risks & Mitigations

### Risk 1: Processing Slows WebSocket Ingestion
**Mitigation**: Async threads (non-blocking), timeout controls, circuit breaker

### Risk 2: Database Write Contention
**Mitigation**: Sprint 74 DELETE + INSERT (no constraints), connection pooling

### Risk 3: Missed Bars During Processing
**Mitigation**: Batch catch-up job (every 5 min), idempotent processing

### Risk 4: Analysis Errors Break WebSocket
**Mitigation**: try/except isolation, log errors but continue ticks

---

## 🔄 Rollback Plan

If Sprint 75 causes issues:

1. **Disable Real-Time**: Comment out `_trigger_bar_analysis_async()` call
2. **Disable Import Auto-Analysis**: Uncheck checkbox (default=false)
3. **Stop Bridge**: Set `ENABLE_IMPORT_ANALYSIS_BRIDGE=false` in .env
4. **Full Rollback**: `git revert <commit-hash>`

---

## 📋 Next Steps

1. ✅ Review user story with stakeholders
2. ✅ Confirm integration points are correct
3. ✅ Approve Phase 1 implementation (WebSocket)
4. Begin coding Phase 1 (3-4 hours)

---

## 📁 Documentation

**Full User Story**: `/docs/planning/sprints/sprint75/PATTERN_INDICATOR_INTEGRATION_USER_STORY.md`

**Related Sprints**:
- Sprint 68: AnalysisService, PatternDetectionService
- Sprint 72: OHLCVDataService (database queries)
- Sprint 73: Admin Process Analysis (manual workflow)
- Sprint 74: Dynamic loading, min_bars_required validation

**Research Reports**:
- WebSocket data flow (agent research completed)
- Historical import flow (agent research completed)
- TickStockPL architecture (agent research completed)

---

**Status**: 📋 Ready for User Review & Approval
