# Sprint 75: Pattern/Indicator Processing Integration

**Status**: 📋 Planning
**Created**: 2026-02-12
**Priority**: High
**Complexity**: Medium-High
**Estimated Effort**: 8-12 hours

---

## Executive Summary

Integrate Sprint 68-74 pattern/indicator analysis services with real-time WebSocket updates and admin historical data imports. This connects the analysis capabilities to live market data and historical backfills, enabling automatic pattern detection on new OHLCV bars.

**Goal**: When a stock updates (via WebSocket or historical import), automatically run pattern/indicator analysis and persist results.

---

## User Stories

### Story 1: Real-Time Pattern Detection on WebSocket Updates
**As a** market analyst
**I want** patterns and indicators to be detected automatically when new 1-minute bars arrive via WebSocket
**So that** I see pattern detections within seconds of bar completion (not hours later)

**Acceptance Criteria**:
- ✅ When ohlcv_1min row inserted via WebSocket → patterns/indicators calculated within <100ms
- ✅ Results stored in daily_patterns and daily_indicators tables
- ✅ Redis events published for UI updates
- ✅ Processing is async (doesn't block WebSocket tick ingestion)
- ✅ Handles 100+ symbols/minute throughput

### Story 2: Automatic Analysis After Historical Import
**As a** system administrator
**I want** patterns and indicators to be calculated automatically after historical data import completes
**So that** I don't have to manually run analysis as a separate step

**Acceptance Criteria**:
- ✅ Checkbox on Historical Data Import page: "Run Analysis After Import"
- ✅ When checked, analysis job auto-submits after import completes
- ✅ Supports both individual symbol imports and universe imports
- ✅ Shows unified progress: "Importing → Analyzing → Complete"
- ✅ Option to run per-symbol (progressive) or batch (end of import)

### Story 3: Backfill Missing Analysis
**As a** system administrator
**I want** to backfill pattern/indicator analysis for existing OHLCV data
**So that** historical bars imported before Sprint 75 get analyzed retroactively

**Acceptance Criteria**:
- ✅ Admin page shows count of "bars without analysis"
- ✅ "Backfill Analysis" button processes all missing bars
- ✅ Batch processing with progress tracking
- ✅ Resumes from last processed bar on restart

---

## Current State (Sprint 74 Baseline)

### ✅ Completed Components (Sprints 68-74)

#### Analysis Services (Sprint 68, 70, 71)
- **AnalysisService**: Orchestrates pattern/indicator analysis
- **PatternDetectionService**: Detects 8 patterns (doji, hammer, engulfing, shooting_star, hanging_man, harami, morning_star, evening_star)
- **IndicatorLoader**: Loads 18 indicators (sma, ema variants, rsi, macd, bollinger_bands, stochastic, atr, adx)
- **OHLCVDataService**: Fetches OHLCV data from TimescaleDB

#### Admin Process Analysis (Sprint 73)
- **Page**: `/admin/process-analysis`
- **Capabilities**: Manual pattern/indicator analysis on demand
- **Job Tracking**: Background jobs with progress polling
- **Database Persistence**: Stores results in daily_patterns and daily_indicators tables
- **DELETE + INSERT Strategy**: Bounded database growth (Sprint 74 enhancement)

#### Dynamic Loading (Sprint 74)
- **Table-Driven Configuration**: Enable/disable patterns/indicators via database
- **min_bars_required Validation**: Prevents errors from insufficient data
- **Performance**: <20ms pattern detection, <20ms indicator calculation
- **Database State**: 18 indicators, 8 patterns enabled

### ⚠️ Missing Integration

#### Real-Time WebSocket Processing
- **Current**: WebSocket ticks → ohlcv_1min inserts (NO analysis triggered)
- **Gap**: No connection between bar creation and analysis service
- **Impact**: Patterns detected only when user manually runs analysis

#### Historical Import Processing
- **Current**: Historical import → ohlcv_daily/hourly/1min inserts (NO analysis triggered)
- **Gap**: User must manually trigger analysis as separate step
- **Impact**: Two-step workflow (import → then manually analyze)

---

## Technical Architecture

### Integration Point 1: WebSocket Real-Time Processing

#### Current Flow (Sprint 54)
```
Massive WebSocket → MassiveWebSocketClient._process_aggregate_event()
    ↓
MarketDataService._handle_tick_data()
    ↓
TickStockDatabase.write_ohlcv_1min() ← **SUCCESS** (line 234)
    ↓
✅ Bar persisted to database
❌ NO pattern/indicator processing triggered
```

#### Proposed Flow (Sprint 75)
```
Massive WebSocket → MassiveWebSocketClient._process_aggregate_event()
    ↓
MarketDataService._handle_tick_data()
    ↓
TickStockDatabase.write_ohlcv_1min() ← **SUCCESS**
    ↓
✅ Bar persisted to database
    ↓
**NEW**: _trigger_bar_analysis(symbol, timestamp) ← **INTEGRATION HOOK**
    ├─ Spawns async task (non-blocking)
    ├─ Fetches last N bars from OHLCVDataService
    ├─ Runs AnalysisService.analyze_symbol()
    ├─ Persists results (patterns/indicators tables)
    └─ Publishes Redis event (tickstock:events:analysis_complete)
```

**Key Files**:
- `src/core/services/market_data_service.py` (line ~240, after database write)
- `src/analysis/services/analysis_service.py` (existing AnalysisService)
- `src/analysis/data/ohlcv_data_service.py` (Sprint 72 data fetcher)

---

### Integration Point 2: Historical Import Completion

#### Current Flow
```
Admin Historical Data Page → POST /admin/historical-data/trigger-load
    ↓
Redis: tickstock.jobs.data_load (job_id, symbols, years, timespan)
    ↓
TickStockPL DataLoader
    ├─ Fetches data from Massive API
    ├─ Inserts to ohlcv_daily/hourly/1min
    └─ Updates job status: 'completed'
    ↓
User polls: GET /admin/historical-data/job/<job_id>/status
    ↓
✅ "Import complete!"
❌ User must manually go to /admin/process-analysis to run analysis
```

#### Proposed Flow (Sprint 75)
```
Admin Historical Data Page → POST /admin/historical-data/trigger-load
    ├─ Parameters: symbols, years, timespan
    └─ **NEW**: run_analysis_after_import=true (checkbox)
    ↓
Redis: tickstock.jobs.data_load (job_id, symbols, years, timespan, **run_analysis_after_import**)
    ↓
TickStockPL DataLoader (completes import)
    ↓
**NEW**: JobCompletionMonitor (TickStockAppV2 background thread)
    ├─ Polls job status every 5 seconds
    ├─ Detects: status='completed' AND run_analysis_after_import=true
    └─ Auto-submits analysis job:
        POST /admin/process-analysis/trigger (internal API call)
        ├─ Parameters: symbols (from import job), analysis_type='both', timeframe='daily'
        └─ Unified progress: "Importing (60%) → Analyzing (0%)"
    ↓
✅ "Import complete! Analysis complete!"
```

**Key Files**:
- `src/api/rest/admin_historical_data_redis.py` (add checkbox parameter, line ~150)
- `web/templates/admin/historical_data_dashboard.html` (add checkbox UI)
- `static/js/admin_historical_data.js` (pass checkbox value to API)
- **NEW**: `src/jobs/import_analysis_bridge.py` (job completion monitor)

---

### Integration Point 3: Batch Backfill

#### Proposed Feature
```
Admin Process Analysis Page → "Backfill Missing Analysis" button
    ↓
Query: Find bars without analysis
    SELECT o.symbol, o.timestamp
    FROM ohlcv_daily o
    LEFT JOIN daily_patterns p ON o.symbol = p.symbol AND o.timestamp = p.detection_timestamp
    WHERE p.id IS NULL
    LIMIT 1000
    ↓
Batch processing (100 bars at a time)
    ├─ Fetch OHLCV data for each bar
    ├─ Run AnalysisService.analyze_symbol()
    ├─ Persist results
    └─ Update progress: "Processed 500 / 10,000 bars"
    ↓
✅ "Backfill complete! 10,000 bars analyzed."
```

**Key Files**:
- `src/api/rest/admin_process_analysis.py` (add backfill endpoint)
- **NEW**: `src/jobs/backfill_analysis_job.py` (backfill logic)

---

## Implementation Plan

### Phase 1: Real-Time WebSocket Integration (3-4 hours)

#### Task 1.1: Add Bar Analysis Trigger to MarketDataService
**File**: `src/core/services/market_data_service.py`

**Changes** (after line 240, inside `_handle_tick_data()`):
```python
if success:
    # Track successful writes (existing code, lines 238-240)
    if not hasattr(self.stats, 'database_writes_completed'):
        self.stats.database_writes_completed = 0
    self.stats.database_writes_completed += 1

    # **NEW**: Trigger pattern/indicator analysis asynchronously
    self._trigger_bar_analysis_async(symbol, timestamp)

else:
    logger.warning(f"MARKET-DATA-SERVICE: Database write failed for {symbol} at {timestamp}")
```

#### Task 1.2: Implement Async Analysis Trigger
**File**: `src/core/services/market_data_service.py`

**Add method**:
```python
def _trigger_bar_analysis_async(self, symbol: str, timestamp: datetime):
    """
    Trigger pattern/indicator analysis for newly created bar.
    Runs in background thread to avoid blocking tick ingestion.

    Performance target: <100ms total (non-blocking)
    """
    from threading import Thread

    def run_analysis():
        try:
            # Import here to avoid circular dependency
            from src.analysis.services.analysis_service import AnalysisService
            from src.analysis.data.ohlcv_data_service import OHLCVDataService

            # Fetch last 200 bars (sufficient for all patterns/indicators)
            ohlcv_service = OHLCVDataService()
            data = ohlcv_service.get_ohlcv_data(
                symbol=symbol,
                timeframe='1min',
                limit=200
            )

            if data is None or len(data) == 0:
                logger.warning(f"No OHLCV data for {symbol} - skipping analysis")
                return

            # Run analysis
            analysis_service = AnalysisService()
            results = analysis_service.analyze_symbol(
                symbol=symbol,
                data=data,
                timeframe='1min',
                indicators=None,  # Use all available
                patterns=None,  # Use all available
                calculate_all=True
            )

            # Persist results (reuse Sprint 73 persistence logic)
            from src.api.rest.admin_process_analysis import _persist_pattern_results, _persist_indicator_results

            _persist_pattern_results(symbol, '1min', results['patterns'])
            _persist_indicator_results(symbol, '1min', results['indicators'])

            # Publish Redis event for UI updates
            from src.infrastructure.redis.redis_connection_manager import get_redis_manager
            redis_manager = get_redis_manager()
            if redis_manager:
                redis_manager.publish_message('tickstock:events:analysis_complete', {
                    'symbol': symbol,
                    'timestamp': timestamp.isoformat(),
                    'timeframe': '1min',
                    'patterns_detected': len([p for p in results['patterns'].values() if p['detected']]),
                    'indicators_calculated': len(results['indicators'])
                })

            logger.info(f"Bar analysis complete for {symbol} at {timestamp}: "
                       f"{len(results['patterns'])} patterns, {len(results['indicators'])} indicators")

        except Exception as e:
            logger.error(f"Bar analysis failed for {symbol} at {timestamp}: {e}", exc_info=True)

    # Spawn background thread (non-blocking)
    thread = Thread(target=run_analysis, daemon=True, name=f"BarAnalysis-{symbol}")
    thread.start()
```

#### Task 1.3: Testing
- **Unit Test**: Mock database write success → verify analysis triggered
- **Integration Test**: End-to-end tick → bar → analysis → persistence
- **Performance Test**: Verify <100ms latency (non-blocking)
- **Load Test**: 100 symbols/minute throughput

---

### Phase 2: Historical Import Integration (3-4 hours)

#### Task 2.1: Add Checkbox to Historical Data Dashboard
**File**: `web/templates/admin/historical_data_dashboard.html`

**Add checkbox** (after "Timespan" dropdown):
```html
<div class="form-group">
    <label class="inline-flex items-center">
        <input type="checkbox" id="run-analysis-checkbox" name="run_analysis" checked>
        <span class="ml-2">Run Pattern/Indicator Analysis After Import</span>
    </label>
    <p class="text-sm text-gray-500 mt-1">
        Automatically analyzes imported data for patterns and indicators.
        Uncheck to only import OHLCV data (analysis can be run manually later).
    </p>
</div>
```

#### Task 2.2: Pass Checkbox Value to API
**File**: `static/js/admin_historical_data.js`

**Update** `submitUniverseLoad()` function:
```javascript
function submitUniverseLoad(universeKey) {
    const years = parseFloat(document.getElementById('years-input').value) || 1;
    const runAnalysis = document.getElementById('run-analysis-checkbox').checked;

    fetch('/admin/historical-data/trigger-universe-load', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            universe_key: universeKey,
            timeframes: ['daily'],
            years: years,
            run_analysis_after_import: runAnalysis  // **NEW**
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            pollJobStatus(data.job_id, runAnalysis);  // Pass flag for progress display
        }
    });
}
```

#### Task 2.3: Store Flag in Job Metadata
**File**: `src/api/rest/admin_historical_data_redis.py`

**Update** `admin_trigger_universe_load()` (line ~360):
```python
@admin_bp.route('/admin/historical-data/trigger-universe-load', methods=['POST'])
@login_required
@admin_required
def admin_trigger_universe_load():
    data = request.get_json()
    universe_key = data.get('universe_key')
    years = data.get('years', 1)
    timeframes = data.get('timeframes', ['daily'])
    run_analysis = data.get('run_analysis_after_import', False)  # **NEW**

    # ... existing code ...

    # Store in job metadata
    job_data = {
        'job_id': job_id,
        'job_type': 'csv_universe_load',
        'universe_key': universe_key,
        'symbols': symbols,
        'years': years,
        'timeframes': timeframes,
        'run_analysis_after_import': run_analysis,  # **NEW**
        'submitted_at': datetime.now().isoformat(),
        'submitted_by': current_user.username
    }

    # ... rest of function ...
```

#### Task 2.4: Create Job Completion Monitor
**File**: `src/jobs/import_analysis_bridge.py` (NEW)

**Create service**:
```python
"""
Import-Analysis Bridge: Monitors historical import jobs and auto-triggers analysis.

Sprint 75: Connects historical data imports to pattern/indicator analysis.
"""

import logging
import time
from threading import Thread
from datetime import datetime
from typing import Dict, Any

from src.infrastructure.redis.redis_connection_manager import get_redis_manager
from src.api.rest.admin_process_analysis import admin_trigger_analysis

logger = logging.getLogger(__name__)


class ImportAnalysisBridge:
    """
    Monitors historical import job completion and auto-triggers analysis if requested.

    Architecture:
    - Background thread polls job status every 5 seconds
    - When import completes AND run_analysis_after_import=true
    - Submits analysis job via internal API call
    """

    def __init__(self):
        self.redis_manager = get_redis_manager()
        self.monitored_jobs: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.monitor_thread = None

    def start(self):
        """Start background monitoring thread."""
        if self.running:
            logger.warning("ImportAnalysisBridge already running")
            return

        self.running = True
        self.monitor_thread = Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ImportAnalysisBridge"
        )
        self.monitor_thread.start()
        logger.info("ImportAnalysisBridge started")

    def stop(self):
        """Stop background monitoring thread."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("ImportAnalysisBridge stopped")

    def register_job(self, job_id: str, job_metadata: Dict[str, Any]):
        """Register an import job for monitoring."""
        if not job_metadata.get('run_analysis_after_import'):
            logger.debug(f"Job {job_id} does not require analysis - not monitoring")
            return

        self.monitored_jobs[job_id] = {
            'job_id': job_id,
            'symbols': job_metadata.get('symbols', []),
            'universe_key': job_metadata.get('universe_key'),
            'timeframe': job_metadata.get('timeframes', ['daily'])[0],
            'analysis_type': 'both',
            'registered_at': datetime.now(),
            'status': 'monitoring'
        }
        logger.info(f"Registered job {job_id} for post-import analysis")

    def _monitor_loop(self):
        """Background loop: poll job status and trigger analysis on completion."""
        while self.running:
            try:
                # Check each monitored job
                for job_id in list(self.monitored_jobs.keys()):
                    job_meta = self.monitored_jobs[job_id]

                    # Get job status from Redis
                    status_key = f"tickstock.jobs.status:{job_id}"
                    status_data = self.redis_manager.get_hash(status_key)

                    if not status_data:
                        logger.warning(f"No status found for job {job_id} - removing from monitoring")
                        del self.monitored_jobs[job_id]
                        continue

                    current_status = status_data.get('status')

                    # If import completed, trigger analysis
                    if current_status == 'completed':
                        logger.info(f"Import job {job_id} completed - triggering analysis")
                        self._trigger_analysis(job_meta)
                        del self.monitored_jobs[job_id]

                    # If import failed, remove from monitoring
                    elif current_status in ['failed', 'cancelled']:
                        logger.warning(f"Import job {job_id} {current_status} - not triggering analysis")
                        del self.monitored_jobs[job_id]

                # Sleep before next poll
                time.sleep(5)

            except Exception as e:
                logger.error(f"ImportAnalysisBridge error: {e}", exc_info=True)
                time.sleep(5)

    def _trigger_analysis(self, job_meta: Dict[str, Any]):
        """Trigger analysis job for imported symbols."""
        try:
            # Use internal API call to trigger analysis
            # This reuses Sprint 73 admin_process_analysis infrastructure
            from flask import Flask
            from flask.ctx import AppContext

            # Create Flask app context (needed for internal API call)
            app = Flask.current_app or Flask(__name__)

            with app.app_context():
                # Call admin_trigger_analysis() directly
                result = admin_trigger_analysis(
                    symbols=job_meta.get('symbols'),
                    universe_key=job_meta.get('universe_key'),
                    analysis_type=job_meta['analysis_type'],
                    timeframe=job_meta['timeframe']
                )

                analysis_job_id = result.get('job_id')
                logger.info(f"Analysis job {analysis_job_id} triggered for import {job_meta['job_id']}")

        except Exception as e:
            logger.error(f"Failed to trigger analysis for job {job_meta['job_id']}: {e}", exc_info=True)


# Singleton instance
_bridge_instance = None


def get_import_analysis_bridge() -> ImportAnalysisBridge:
    """Get singleton ImportAnalysisBridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = ImportAnalysisBridge()
    return _bridge_instance
```

#### Task 2.5: Register Jobs with Bridge
**File**: `src/api/rest/admin_historical_data_redis.py`

**Update** `admin_trigger_universe_load()`:
```python
# After publishing to Redis (line ~380)
redis_manager.publish_message('tickstock.jobs.data_load', job_data)

# **NEW**: Register with ImportAnalysisBridge
if job_data.get('run_analysis_after_import'):
    from src.jobs.import_analysis_bridge import get_import_analysis_bridge
    bridge = get_import_analysis_bridge()
    bridge.register_job(job_id, job_data)
```

#### Task 2.6: Start Bridge on App Initialization
**File**: `src/app.py`

**Add** (after Flask app creation):
```python
# Start ImportAnalysisBridge for post-import analysis
from src.jobs.import_analysis_bridge import get_import_analysis_bridge
bridge = get_import_analysis_bridge()
bridge.start()
logger.info("ImportAnalysisBridge monitoring started")
```

#### Task 2.7: Testing
- **UI Test**: Checkbox appears and stores value correctly
- **Integration Test**: Import job with checkbox → analysis auto-triggered
- **Progress Test**: Unified progress display (import → analysis)

---

### Phase 3: Backfill Analysis (2-3 hours)

#### Task 3.1: Add Backfill Endpoint
**File**: `src/api/rest/admin_process_analysis.py`

**Add route**:
```python
@admin_analysis_bp.route('/admin/process-analysis/backfill', methods=['POST'])
@login_required
@admin_required
def admin_backfill_analysis():
    """
    Backfill pattern/indicator analysis for OHLCV bars missing analysis.

    Queries ohlcv_daily for bars without corresponding entries in daily_patterns,
    then processes them in batches of 100.
    """
    data = request.get_json()
    timeframe = data.get('timeframe', 'daily')
    batch_size = data.get('batch_size', 100)
    max_bars = data.get('max_bars', 10000)

    # Find bars without analysis
    from src.infrastructure.database.connection_pool import get_connection_pool
    pool = get_connection_pool()

    with pool.get_connection() as conn:
        # Query bars missing patterns
        result = conn.execute(text(f"""
            SELECT DISTINCT o.symbol, o.timestamp
            FROM ohlcv_{timeframe} o
            LEFT JOIN daily_patterns p
                ON o.symbol = p.symbol
                AND DATE(o.timestamp) = DATE(p.detection_timestamp)
                AND p.timeframe = :timeframe
            WHERE p.id IS NULL
            ORDER BY o.timestamp DESC
            LIMIT :max_bars
        """), {'timeframe': timeframe, 'max_bars': max_bars})

        missing_bars = result.fetchall()

    if not missing_bars:
        return jsonify({
            'success': True,
            'message': 'No bars missing analysis',
            'bars_processed': 0
        })

    # Create background job
    job_id = f"backfill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def run_backfill_job():
        # Process in batches
        total = len(missing_bars)
        processed = 0

        for i in range(0, total, batch_size):
            batch = missing_bars[i:i+batch_size]

            for symbol, timestamp in batch:
                try:
                    # Fetch OHLCV data
                    ohlcv_service = OHLCVDataService()
                    data = ohlcv_service.get_ohlcv_data(
                        symbol=symbol,
                        timeframe=timeframe,
                        limit=200
                    )

                    # Run analysis
                    analysis_service = AnalysisService()
                    results = analysis_service.analyze_symbol(
                        symbol=symbol,
                        data=data,
                        timeframe=timeframe,
                        calculate_all=True
                    )

                    # Persist results
                    _persist_pattern_results(symbol, timeframe, results['patterns'])
                    _persist_indicator_results(symbol, timeframe, results['indicators'])

                    processed += 1

                except Exception as e:
                    logger.error(f"Backfill error for {symbol} at {timestamp}: {e}")

            # Update progress
            active_jobs[job_id]['progress'] = int((processed / total) * 100)
            logger.info(f"Backfill progress: {processed}/{total} bars")

        # Mark complete
        active_jobs[job_id]['status'] = 'completed'
        active_jobs[job_id]['completed_at'] = datetime.now()
        logger.info(f"Backfill job {job_id} completed: {processed} bars analyzed")

    # Track job
    active_jobs[job_id] = {
        'job_id': job_id,
        'type': 'backfill',
        'status': 'running',
        'progress': 0,
        'total_bars': len(missing_bars),
        'started_at': datetime.now()
    }

    # Start background thread
    thread = Thread(target=run_backfill_job, daemon=True, name=f"Backfill-{job_id}")
    thread.start()

    return jsonify({
        'success': True,
        'job_id': job_id,
        'bars_to_process': len(missing_bars),
        'message': f'Backfill started for {len(missing_bars)} bars'
    })
```

#### Task 3.2: Add UI Button
**File**: `web/templates/admin/process_analysis_dashboard.html`

**Add section**:
```html
<div class="card mt-4">
    <h3>Backfill Analysis</h3>
    <p>Analyze historical OHLCV bars that are missing pattern/indicator analysis.</p>

    <div class="form-row">
        <label>Timeframe:</label>
        <select id="backfill-timeframe">
            <option value="daily">Daily</option>
            <option value="hourly">Hourly</option>
            <option value="1min">1-Minute</option>
        </select>
    </div>

    <div class="form-row">
        <label>Max Bars:</label>
        <input type="number" id="backfill-max-bars" value="10000" min="100" max="100000">
    </div>

    <button id="backfill-btn" class="btn btn-primary">
        Start Backfill
    </button>

    <div id="backfill-status" class="mt-2"></div>
</div>
```

#### Task 3.3: Testing
- **Query Test**: Correctly identifies bars without analysis
- **Batch Test**: Processes 1000 bars in batches of 100
- **Progress Test**: Progress updates correctly

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Real-time bar analysis** | <100ms | Time from ohlcv_1min insert → results persisted |
| **WebSocket tick ingestion** | No degradation | Verify still <50ms per tick |
| **Throughput** | 100 symbols/minute | Sustained real-time processing rate |
| **Historical import** | +10% overhead | Import time with analysis vs without |
| **Backfill processing** | 500 bars/minute | Batch backfill throughput |
| **Memory footprint** | <50MB | Memory used by background threads |

---

## Success Criteria

### Functional ✅
- [ ] WebSocket bars trigger analysis automatically
- [ ] Historical import checkbox triggers analysis on completion
- [ ] Backfill processes missing bars successfully
- [ ] Results persist to daily_patterns and daily_indicators tables
- [ ] Redis events published for UI updates

### Performance ✅
- [ ] Real-time analysis: <100ms per bar (non-blocking)
- [ ] WebSocket tick ingestion: No degradation (<50ms)
- [ ] Throughput: 100 symbols/minute sustained
- [ ] Memory: <50MB footprint

### Quality ✅
- [ ] 80%+ test coverage (unit + integration)
- [ ] Zero regressions (Sprint 73 analysis still works)
- [ ] Error handling (database failures, invalid OHLCV data)
- [ ] Monitoring (logs, metrics, Redis events)

---

## Dependencies

### Sprint Prerequisites
- ✅ Sprint 68: AnalysisService, PatternDetectionService
- ✅ Sprint 70: IndicatorLoader with 18 indicators
- ✅ Sprint 72: OHLCVDataService (TimescaleDB queries)
- ✅ Sprint 73: Admin Process Analysis (persistence logic)
- ✅ Sprint 74: Dynamic loading, min_bars_required validation

### External Dependencies
- ✅ TickStockPL: Historical data import (port 8080)
- ✅ Massive WebSocket: Real-time tick ingestion
- ✅ TimescaleDB: OHLCV tables (ohlcv_daily, ohlcv_1min)
- ✅ Redis: Job status tracking, event pub/sub

---

## Risks & Mitigations

### Risk 1: Processing Overhead Slows WebSocket Ingestion
**Mitigation**:
- Async processing (background threads, non-blocking)
- Timeout controls (max 100ms per bar)
- Circuit breaker (disable if CPU >80%)
- Performance monitoring (log slow analyses)

### Risk 2: Database Write Contention
**Mitigation**:
- Sprint 74 DELETE + INSERT strategy (no UPSERT constraints)
- Connection pooling (separate pool for analysis writes)
- Batch commits (100 bars per transaction for backfill)

### Risk 3: Missed Bars During Processing
**Mitigation**:
- Batch catch-up job (every 5 minutes, query missing bars)
- Job completion monitoring (retry failed analyses)
- Idempotent processing (DELETE + INSERT allows re-runs)

### Risk 4: Analysis Errors Break WebSocket Flow
**Mitigation**:
- try/except around analysis trigger
- Log errors but continue tick processing
- Alert on error rate >10/minute

---

## Testing Strategy

### Unit Tests (20 tests)
- `test_bar_analysis_trigger()` - Verify analysis triggered on bar insert
- `test_async_processing()` - Verify non-blocking behavior
- `test_import_completion_monitor()` - Verify job status polling
- `test_backfill_query()` - Verify missing bars query
- `test_error_handling()` - Verify resilience to analysis failures

### Integration Tests (10 tests)
- `test_end_to_end_websocket_flow()` - Tick → bar → analysis → persistence
- `test_historical_import_flow()` - Import → analysis auto-trigger
- `test_backfill_flow()` - Backfill missing bars
- `test_concurrent_processing()` - 10 symbols simultaneously

### Performance Tests (5 tests)
- `test_real_time_latency()` - <100ms per bar
- `test_throughput()` - 100 symbols/minute
- `test_memory_footprint()` - <50MB
- `test_websocket_no_degradation()` - Still <50ms per tick
- `test_backfill_throughput()` - 500 bars/minute

---

## Rollback Plan

If Sprint 75 causes issues:

1. **Disable Real-Time Processing**:
   - Comment out `_trigger_bar_analysis_async()` call (line ~240 in market_data_service.py)
   - Restart Flask app
   - WebSocket ingestion continues, no analysis triggered

2. **Disable Import Auto-Analysis**:
   - Uncheck "Run Analysis After Import" checkbox (default to false)
   - Users manually trigger analysis as before (Sprint 73)

3. **Stop ImportAnalysisBridge**:
   - Set `ENABLE_IMPORT_ANALYSIS_BRIDGE=false` in .env
   - Bridge won't start, no auto-triggering

4. **Full Rollback**:
   - `git revert <sprint75-commit-hash>`
   - Restart services
   - Sprint 73 manual analysis workflow restored

---

## Future Enhancements (Post-Sprint 75)

### Sprint 76: Pattern Alert System
- Real-time alerts when high-confidence patterns detected
- Email/Slack notifications
- Customizable alert rules per user

### Sprint 77: Performance Dashboard
- Pattern detection success rates
- Indicator calculation performance
- Cache hit rates by timeframe
- Most frequently detected patterns

### Sprint 78: Historical Pattern Backtesting
- Analyze pattern performance over time
- Risk/reward metrics per pattern
- Pattern combination optimization

---

## Related Documentation

- **Sprint 68**: Core Analysis Migration (AnalysisService, PatternDetectionService)
- **Sprint 72**: Database Integration (OHLCVDataService)
- **Sprint 73**: Admin Process Analysis (manual analysis workflow)
- **Sprint 74**: Dynamic Loading (table-driven configuration)
- **Sprint 42**: OHLCV Aggregation Architecture (TickStockPL → AppV2 migration)
- **Sprint 43**: Pattern Display Delay Fix (min_bars_required concept)

---

**Status**: 📋 Ready for Review
**Next Steps**:
1. Review user story with stakeholders
2. Refine integration points based on feedback
3. Begin Phase 1 implementation (WebSocket integration)
