name: "Sprint 69: Background Jobs & Integration - Pattern/Indicator Automation"
description: |
  Integrate migrated analysis capabilities with APScheduler background jobs, enable
  automated daily pattern/indicator calculation, establish Redis pub-sub consolidation,
  and create TickStockPL deprecation plan. Builds on Sprint 68 analysis migration.

---

## Goal

**Feature Goal**: Integrate Sprint 68 analysis capabilities with APScheduler-based background job infrastructure to enable automated daily pattern detection, indicator calculation, and post-import analysis workflows. Establish TickStockPL migration path by consolidating Redis channels and documenting deprecation strategy.

**Deliverable**:
- APScheduler singleton manager integrated with Flask app lifecycle
- 6 background jobs operational (Daily Indicator, Daily Pattern, Post-Import Analysis, Cache Maintenance, Database Cleanup, Health Monitoring)
- Automated pattern/indicator calculation (6:10 PM, 6:20 PM ET daily)
- Historical import → analysis trigger flow (Redis listener)
- Redis channel consolidation (AppV2 publishes patterns/indicators)
- Job monitoring API endpoints (status, history, trigger, pause/resume)
- Analysis Control Panel in Admin UI
- TickStockPL deprecation plan documented
- 50+ unit tests, 15+ integration tests

**Success Definition**:
- Background jobs execute successfully (>99% success rate) for 14 consecutive days
- Pattern detection automated and published to Redis (tickstock.events.patterns)
- Post-import analysis triggers automatically after TickStockPL data loads
- AppV2 runs standalone for analysis features (without TickStockPL)
- Job monitoring dashboard functional (real-time status, execution history)
- Performance: <10 minutes for 500 symbols (parallel processing)
- Zero regressions vs Sprint 68 baseline

## User Persona (if applicable)

**Target User**: TickStock Development Team + System Administrators

**Use Case**: Automate daily pattern/indicator analysis after market close, eliminate manual analysis triggers, monitor job execution health, and manage analysis workflows via Admin UI.

**User Journey** (Admin):
1. Navigate to Analysis Control Panel in Admin UI
2. View scheduled job status (next run times, execution history)
3. Manually trigger analysis for specific symbols/universes
4. Monitor job progress and view execution results
5. Pause/resume jobs during maintenance windows
6. Review job execution history (success rates, error logs)

**User Journey** (System):
1. Market closes at 4:00 PM ET
2. 6:10 PM ET: DailyIndicatorJob calculates indicators for all universe symbols
3. 6:20 PM ET: DailyPatternJob detects patterns using indicator results
4. Patterns published to Redis (tickstock.events.patterns)
5. WebSocket broadcasts patterns to connected clients
6. Weekly/daily maintenance jobs run during off-hours

**Pain Points Addressed**:
- Manual analysis trigger requirement (no automation exists)
- Pattern detection disabled in production (TickStockPL deprecated)
- No job execution monitoring (jobs run without visibility)
- Redis channel fragmentation (TickStockPL + AppV2 publish to different channels)
- No post-import analysis trigger (imported data not analyzed automatically)

## Why

- **Business Value**: Automate daily pattern/indicator analysis for 500+ symbols, reducing manual effort and enabling real-time alerts
- **Integration**: Completes Sprint 68 migration by adding production automation layer
- **Architecture**: Establishes AppV2 as standalone analysis platform (removes TickStockPL dependency)
- **Performance**: <10 minutes for 500 symbols (parallel ThreadPoolExecutor with 10 workers)
- **User Impact**: Enables automated pattern detection alerts, daily indicator refreshes, and post-import analysis

**Problems Solved**:
- Pattern detection automation currently disabled (no scheduler exists)
- Historical data imports not followed by analysis (manual trigger required)
- Job execution not monitored (no visibility into success/failure rates)
- Redis channel confusion (TickStockPL patterns:streaming vs AppV2 events.patterns)
- TickStockPL still deployed despite analysis migration to AppV2 (unclear deprecation path)

## What

### Technical Requirements

**APScheduler Infrastructure**:
- `SchedulerManager` singleton with BackgroundScheduler (timezone: America/New_York)
- Flask app lifecycle integration (start on create_app(), shutdown on teardown)
- Job executors: default (10 workers), analysis (5 workers for heavy analysis)
- Job defaults: coalesce=True, max_instances=1, misfire_grace_time=300s
- Event listeners for job execution tracking (EVENT_JOB_EXECUTED, EVENT_JOB_ERROR)

**Background Jobs (6 total)**:
1. **DailyIndicatorJob**: Calculate indicators for all universe symbols (6:10 PM ET, Mon-Fri)
   - Universes: nasdaq100, sp500, dow30 (distinct union via RelationshipCache)
   - Parallel processing: ThreadPoolExecutor with 10 workers
   - Output: indicator_results table storage
2. **DailyPatternJob**: Detect patterns for all universe symbols (6:20 PM ET, Mon-Fri)
   - Dependency: Runs 10 minutes after DailyIndicatorJob
   - Redis pub-sub: Publishes to tickstock.events.patterns
   - Output: daily_patterns table storage
3. **PostImportAnalysisJob**: Triggered by TickStockPL data load completion
   - Redis listener: tickstock.jobs.data_load channel
   - Full analysis: indicators + patterns for imported symbols
   - Parallel processing: ThreadPoolExecutor with 10 workers
4. **CacheMaintenanceJob**: Refresh RelationshipCache (Sunday 2 AM ET, weekly)
   - Clear cache, warm common queries (universes, ETFs)
   - Validate data quality (ETF count ≥24, universe count ≥3)
5. **DatabaseCleanupJob**: Purge old data (Daily 3 AM ET)
   - Remove old pattern detections (>90 days)
   - Remove old indicator results (>180 days)
6. **HealthMonitoringJob**: System health checks (Hourly)
   - Check Redis connectivity, database connections
   - Monitor job execution rates, error rates

**Redis Channel Consolidation**:
- **AppV2 Publishes** (post-Sprint 69):
  - `tickstock.events.patterns` - Pattern detections from DailyPatternJob
  - `tickstock.events.indicators` - Indicator results from DailyIndicatorJob
  - `tickstock:monitoring` - System health metrics
  - `tickstock:errors` - Error logging
- **TickStockPL Publishes** (Sprint 70 migration):
  - `tickstock.jobs.data_load` - Historical import completion events
  - `tickstock:market:ticks` - Raw tick forwarding (not used by AppV2)
- **Deprecated Channels** (safe to remove):
  - `tickstock:patterns:streaming` - Replaced by tickstock.events.patterns
  - `tickstock:indicators:streaming` - Replaced by tickstock.events.indicators

**Job Monitoring API Endpoints**:
- `GET /api/jobs/status` - List all scheduled jobs with next run times
- `GET /api/jobs/history?limit=50&job_name=daily_pattern_detection` - Execution history
- `POST /api/jobs/trigger/<job_id>` - Manually trigger job
- `POST /api/jobs/pause/<job_id>` - Pause scheduled job
- `POST /api/jobs/resume/<job_id>` - Resume paused job

**Admin UI Analysis Control Panel**:
- Scheduled Jobs Status table (job name, next run, last execution, actions)
- Manual Analysis form (symbol/universe input, analysis type selector)
- Recent Job Executions table (job name, duration, status, result)
- Real-time progress indicators for running jobs

**Database Tables**:
- `job_executions` table (job execution logging)
  - Columns: job_name, started_at, completed_at, duration_seconds, success, result, error
  - Indexes: (job_name), (started_at DESC)

### Success Criteria

- [ ] APScheduler integrated with Flask app (start/stop with app lifecycle)
- [ ] All 6 background jobs registered and operational
- [ ] DailyIndicatorJob calculates indicators for 500+ symbols in <10 minutes
- [ ] DailyPatternJob detects patterns and publishes to Redis successfully
- [ ] PostImportAnalysisJob triggers automatically after TickStockPL data loads
- [ ] CacheMaintenanceJob refreshes cache without errors (weekly)
- [ ] DatabaseCleanupJob purges old data successfully (daily)
- [ ] Job monitoring API endpoints functional (5 endpoints tested)
- [ ] Analysis Control Panel displays job status and execution history
- [ ] Manual job triggering works via Admin UI
- [ ] AppV2 runs standalone (analysis features work without TickStockPL)
- [ ] Integration tests pass: `python run_tests.py` (50+ unit, 15+ integration)
- [ ] Performance target: Background jobs complete within scheduled time windows
- [ ] Zero regressions vs Sprint 68 baseline (pattern/indicator accuracy maintained)

## Context (for AI Assistant)

### Architecture Context (TickStock-Specific)

```yaml
component_role: "Consumer + Analyzer"
description: |
  AppV2 consumes market data, performs analysis (patterns/indicators), and publishes results.
  Sprint 69 adds background job automation layer on top of Sprint 68 analysis capabilities.

database_access:
  read_tables:
    - ohlcv_daily, ohlcv_1hour, ohlcv_1week
    - definition_groups, group_memberships (RelationshipCache)
    - pattern_definitions, indicator_definitions (Sprint 17 registry)
    - indicator_results (read for pattern confidence calculation)
  write_tables:
    - indicator_results (insert from DailyIndicatorJob)
    - daily_patterns (insert from DailyPatternJob)
    - job_executions (insert from BaseJob._log_execution)
  write_pattern: "INSERT only (no UPDATE/DELETE of historical data)"
  constraint: "app_readwrite role with limited write permissions"

redis_channels:
  publish:
    - "tickstock.events.patterns" (DailyPatternJob publishes)
    - "tickstock.events.indicators" (DailyIndicatorJob publishes - optional)
    - "tickstock:monitoring" (health metrics)
    - "tickstock:errors" (error logging)
  subscribe:
    - "tickstock.jobs.data_load" (PostImportAnalysisJob listens)
  pattern: "Pub-sub for cross-component events, job queue for async tasks"

background_jobs:
  scheduler: "APScheduler BackgroundScheduler (timezone: America/New_York)"
  executors:
    - "default: ThreadPoolExecutor(max_workers=10)"
    - "analysis: ThreadPoolExecutor(max_workers=5)"
  job_defaults:
    coalesce: true
    max_instances: 1
    misfire_grace_time: 300
  lifecycle: "Start with Flask app, shutdown on teardown"

performance_targets:
  indicator_calculation: "<1s per symbol (Sprint 68 baseline)"
  pattern_detection: "<1s per symbol (Sprint 68 baseline)"
  daily_indicator_job: "<10 min for 500 symbols (parallel processing)"
  daily_pattern_job: "<10 min for 500 symbols (parallel processing)"
  post_import_analysis: "<10 min for 50 symbols (typical import size)"
  job_monitoring_api: "<50ms per request"
  redis_publish: "<10ms per message"

patterns_to_follow:
  - "Use AnalysisService from Sprint 68 (analyze_symbol, analyze_universe)"
  - "Follow TickStockPL job patterns (BaseJob, JobProgressTracker, ProcessingMonitor)"
  - "Use RelationshipCache for universe symbol resolution (Sprint 60/61)"
  - "Parallel processing with ThreadPoolExecutor (TickStockPL proven pattern)"
  - "Job execution logging to job_executions table (monitoring requirement)"
  - "Redis pub-sub for pattern events (existing WebSocket subscribers)"
  - "Flask Blueprint pattern for API endpoints (existing pattern)"
  - "Admin UI follows base_admin.html template structure"

anti_patterns:
  - "DO NOT use synchronous analysis in Flask request handlers (use background jobs)"
  - "DO NOT create new Redis channels without documentation update"
  - "DO NOT skip job execution logging (required for monitoring)"
  - "DO NOT hardcode schedule times (use environment variables)"
  - "DO NOT run analysis during market hours (scheduled for after close)"
  - "DO NOT block Flask app startup waiting for jobs (run in background)"
```

### Documentation & References

**TickStockPL Reference Implementations** (patterns to follow):
- `C:\Users\McDude\TickStockPL\src\services\daily_processing_scheduler.py` (lines 1-200)
  - APScheduler singleton pattern with BackgroundScheduler
  - CronTrigger configuration (America/New_York timezone)
  - Event listeners (EVENT_JOB_EXECUTED, EVENT_JOB_ERROR)
  - Flask app lifecycle integration (start/shutdown hooks)
- `C:\Users\McDude\TickStockPL\src\jobs\daily_pattern_job.py` (lines 1-200)
  - BaseJob pattern with execute() method
  - ThreadPoolExecutor parallel processing (max_workers=15)
  - Dataclass result objects (PatternResult, SymbolPatternResult, JobPatternResult)
  - JobProgressTracker integration for monitoring
  - ProcessingMonitor for error publishing
- `C:\Users\McDude\TickStockPL\src\jobs\daily_indicator_job.py` (similar structure to pattern job)
  - Indicator calculation with parallel processing
  - Database storage to indicator_results table
  - Progress tracking and error handling

**AppV2 Existing Patterns**:
- `C:\Users\McDude\TickStockAppV2\src\jobs\enterprise_production_scheduler.py` (lines 1-200)
  - Redis job queue management (Redis Streams pattern)
  - Job priority and status management (JobPriority, JobStatus enums)
  - Dataclass job structures (EnterpriseSchedulingJob)
  - System metrics monitoring (psutil integration)
- `C:\Users\McDude\TickStockAppV2\src\core\services\relationship_cache.py`
  - get_universe_symbols(universe_key) for symbol resolution
  - Multi-universe join support: "sp500:nasdaq100" creates distinct union
- `C:\Users\McDude\TickStockAppV2\src\core\services\analysis_service.py` (Sprint 68)
  - analyze_symbol(symbol, calculate_indicators=True, detect_patterns=True)
  - analyze_universe(universe, symbols=None, parallel=True, max_workers=10)
- `C:\Users\McDude\TickStockAppV2\web\templates\admin\historical_data_dashboard_redis.html`
  - Admin UI pattern with job status tables
  - Manual trigger forms with progress indicators

**External Documentation**:
- APScheduler: https://apscheduler.readthedocs.io/en/stable/userguide.html#schedulers
  - BackgroundScheduler: https://apscheduler.readthedocs.io/en/stable/modules/schedulers/background.html
  - CronTrigger: https://apscheduler.readthedocs.io/en/stable/modules/triggers/cron.html
  - Event Listeners: https://apscheduler.readthedocs.io/en/stable/userguide.html#scheduler-events
- Flask Lifecycle Hooks: https://flask.palletsprojects.com/en/3.0.x/appcontext/#storing-data
  - teardown_appcontext: https://flask.palletsprojects.com/en/3.0.x/api/#flask.Flask.teardown_appcontext
- Redis Pub-Sub Python: https://redis.readthedocs.io/en/stable/commands.html#redis.commands.core.CoreCommands.publish
  - Listener pattern: https://redis-py.readthedocs.io/en/stable/examples/redis-pubsub.html
- ThreadPoolExecutor: https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor
  - as_completed: https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.as_completed

### Desired Codebase Tree (Sprint 69 additions)

```
TickStockAppV2/
├── src/
│   ├── jobs/                               # NEW DIRECTORY
│   │   ├── __init__.py                     # Job registration function
│   │   ├── scheduler.py                    # SchedulerManager singleton
│   │   ├── base_job.py                     # BaseJob abstract class
│   │   ├── daily_indicator_job.py          # Indicator calculation job
│   │   ├── daily_pattern_job.py            # Pattern detection job
│   │   ├── post_import_analysis_job.py     # Post-import analysis trigger
│   │   ├── data_load_listener.py           # Redis listener for import events
│   │   ├── cache_maintenance_job.py        # Weekly cache refresh
│   │   ├── database_cleanup_job.py         # Daily old data purging
│   │   └── health_monitoring_job.py        # Hourly system health checks
│   ├── api/
│   │   └── routes/
│   │       └── jobs.py                     # Job monitoring API endpoints
│   ├── core/
│   │   └── services/
│   │       ├── analysis_service.py         # EXISTING (Sprint 68)
│   │       ├── indicator_service.py        # EXISTING (Sprint 68)
│   │       ├── pattern_service.py          # EXISTING (Sprint 68)
│   │       └── relationship_cache.py       # EXISTING (Sprint 60)
├── web/
│   ├── templates/
│   │   └── admin/
│   │       └── analysis_control.html       # NEW - Job monitoring UI
│   └── static/
│       └── js/
│           └── components/
│               └── analysis-control-panel.js  # NEW - Job UI logic
├── tests/
│   ├── unit/
│   │   └── jobs/                           # NEW DIRECTORY
│   │       ├── test_scheduler.py           # Scheduler tests
│   │       ├── test_base_job.py            # BaseJob tests
│   │       ├── test_daily_indicator_job.py # Indicator job tests
│   │       ├── test_daily_pattern_job.py   # Pattern job tests
│   │       └── test_cache_maintenance.py   # Cache job tests
│   └── integration/
│       ├── test_jobs_api.py                # Job API endpoint tests
│       ├── test_post_import_analysis.py    # Post-import flow tests
│       └── test_appv2_standalone.py        # Standalone operation tests
├── docs/
│   ├── planning/
│   │   └── sprints/
│   │       └── sprint69/
│   │           ├── TICKSTOCKPL_DEPRECATION.md  # NEW - Deprecation plan
│   │           └── SPRINT69_COMPLETE.md        # Sprint completion doc
│   └── architecture/
│       ├── background-jobs.md              # NEW - Background jobs architecture
│       └── redis-channels.md               # UPDATED - Redis consolidation
└── config/
    └── redis_config.py                     # UPDATED - Channel consolidation
```

### Known Gotchas (Critical Patterns)

1. **APScheduler Timezone Requirement**:
   ```python
   # WRONG: No timezone specified (uses system timezone)
   scheduler = BackgroundScheduler()

   # CORRECT: Always specify America/New_York for market-aligned schedules
   scheduler = BackgroundScheduler(timezone='America/New_York')
   ```

2. **Flask App Lifecycle Integration**:
   ```python
   # WRONG: Scheduler not stopped on app teardown (zombie threads)
   def create_app():
       scheduler = get_scheduler()
       scheduler.start()
       return app

   # CORRECT: Register teardown hook
   def create_app():
       scheduler = get_scheduler()
       scheduler.start()

       @app.teardown_appcontext
       def shutdown_scheduler(exception=None):
           scheduler.shutdown()  # Graceful shutdown

       return app
   ```

3. **Job Singleton Pattern** (prevent duplicate instances):
   ```python
   # WRONG: Creates new job instance every time
   scheduler.add_job(DailyIndicatorJob().execute, ...)

   # CORRECT: Job instantiation inside execute() is fine (APScheduler handles)
   job_instance = DailyIndicatorJob()  # Create once
   scheduler.add_job(job_instance.execute, ...)
   ```

4. **Redis Listener Thread Management**:
   ```python
   # WRONG: Blocking listen() in main thread
   def start_listener():
       for message in pubsub.listen():  # Blocks Flask app startup
           handle_message(message)

   # CORRECT: Run listener in daemon background thread
   def start_listener():
       def listen_loop():
           for message in pubsub.listen():
               handle_message(message)

       thread = threading.Thread(target=listen_loop, daemon=True)
       thread.start()
   ```

5. **Job Coalesce and Max Instances**:
   ```python
   # WRONG: Multiple concurrent runs of same job possible
   scheduler.add_job(func=analyze_job, trigger=...)

   # CORRECT: Enforce single instance with coalesce
   job_defaults = {
       'coalesce': True,      # Combine missed runs into one
       'max_instances': 1,    # Only one instance at a time
       'misfire_grace_time': 300  # 5 min grace for late starts
   }
   scheduler = BackgroundScheduler(job_defaults=job_defaults)
   ```

6. **ThreadPoolExecutor Context Manager** (prevent resource leaks):
   ```python
   # WRONG: Executor not properly closed
   executor = ThreadPoolExecutor(max_workers=10)
   futures = [executor.submit(process, symbol) for symbol in symbols]
   # ... executor never closed, threads leak

   # CORRECT: Use context manager for automatic cleanup
   with ThreadPoolExecutor(max_workers=10) as executor:
       futures = [executor.submit(process, symbol) for symbol in symbols]
       for future in as_completed(futures):
           result = future.result()
   ```

7. **Job Execution Logging** (required for monitoring):
   ```python
   # WRONG: Job runs without database logging
   def execute(self):
       result = self.run()
       return result

   # CORRECT: Always log execution to job_executions table
   def execute(self):
       self.start_time = datetime.now()
       try:
           result = self.run()
           self._log_execution(success=True, result=result)
       except Exception as e:
           self._log_execution(success=False, error=str(e))
           raise
   ```

8. **Redis Pub-Sub Channel Naming** (consistency with existing channels):
   ```python
   # WRONG: Inconsistent channel naming
   redis_client.publish('patterns_detected', data)  # Doesn't match existing

   # CORRECT: Follow existing channel naming convention
   redis_client.publish('tickstock.events.patterns', data)  # Matches Sprint 43
   ```

9. **Job Dependency Scheduling** (indicator before pattern):
   ```python
   # WRONG: Jobs scheduled at same time (race condition)
   scheduler.add_job(DailyIndicatorJob().execute, CronTrigger(hour=18, minute=10))
   scheduler.add_job(DailyPatternJob().execute, CronTrigger(hour=18, minute=10))

   # CORRECT: Pattern job runs AFTER indicator job (10 min buffer)
   scheduler.add_job(DailyIndicatorJob().execute, CronTrigger(hour=18, minute=10))
   scheduler.add_job(DailyPatternJob().execute, CronTrigger(hour=18, minute=20))
   ```

10. **AnalysisService Integration** (use Sprint 68 service):
    ```python
    # WRONG: Directly instantiating pattern/indicator services
    indicator_service = IndicatorService()
    pattern_service = PatternService()
    indicators = indicator_service.calculate_all_indicators(symbol, df)
    patterns = pattern_service.detect_all_patterns(symbol, df)

    # CORRECT: Use AnalysisService orchestration layer
    analysis_service = AnalysisService()
    result = analysis_service.analyze_symbol(
        symbol=symbol,
        calculate_indicators=True,
        detect_patterns=True
    )
    indicators = result['indicators']
    patterns = result['patterns']
    ```

11. **RelationshipCache Universe Resolution** (Sprint 60/61 integration):
    ```python
    # WRONG: Querying database for universe symbols (slow, bypasses cache)
    query = "SELECT symbol FROM group_memberships WHERE group_id = ..."
    symbols = db.execute_read(query)

    # CORRECT: Use RelationshipCache for sub-millisecond access
    cache = get_relationship_cache()
    symbols = cache.get_universe_symbols('nasdaq100')  # <1ms cache hit

    # CORRECT: Multi-universe join (distinct union)
    symbols = cache.get_universe_symbols('sp500:nasdaq100')  # ~518 symbols
    ```

12. **Job Result Dataclass Serialization** (database storage):
    ```python
    # WRONG: Storing dataclass directly (not JSON serializable)
    result = PatternResult(symbol='AAPL', pattern_name='Doji', ...)
    query = "INSERT INTO job_executions (result) VALUES (%s)"
    db.execute_write(query, (result,))  # TypeError: not serializable

    # CORRECT: Convert dataclass to string or dict
    from dataclasses import asdict
    result_str = str(result)  # Simple string representation
    # OR
    result_dict = asdict(result)  # Full dict representation
    db.execute_write(query, (str(result),))
    ```

13. **Environment Variable Configuration** (avoid hardcoded schedules):
    ```python
    # WRONG: Hardcoded schedule times
    scheduler.add_job(func=job, trigger=CronTrigger(hour=18, minute=10))

    # CORRECT: Use environment variables for configuration
    import os
    indicator_time = os.getenv('JOB_INDICATOR_CALC_TIME', '18:10')
    hour, minute = indicator_time.split(':')
    scheduler.add_job(
        func=job,
        trigger=CronTrigger(hour=int(hour), minute=int(minute))
    )
    ```

14. **Redis Message Serialization** (pattern event format):
    ```python
    # WRONG: Inconsistent event format
    redis_client.publish('tickstock.events.patterns', pattern_name)

    # CORRECT: Structured event with all required fields
    event = {
        'symbol': symbol,
        'pattern_name': pattern['pattern_name'],
        'confidence': pattern.get('confidence', 0),
        'timeframe': pattern.get('timeframe', 'daily'),
        'detected_at': pattern.get('detected_at'),
        'metadata': pattern.get('metadata', {})
    }
    redis_client.publish('tickstock.events.patterns', str(event))
    ```

15. **Post-Import Analysis Event Validation**:
    ```python
    # WRONG: Processing all messages without validation
    def _handle_message(self, data: bytes):
        event = json.loads(data.decode('utf-8'))
        job = PostImportAnalysisJob(event['symbols'], event['timeframe'])
        job.execute()

    # CORRECT: Validate event structure before processing
    def _handle_message(self, data: bytes):
        event = json.loads(data.decode('utf-8'))

        # Validate event type
        if event.get('event_type') != 'data_load_complete':
            return

        # Validate required fields
        symbols = event.get('symbols', [])
        run_analysis = event.get('run_analysis', False)

        if run_analysis and symbols:
            job = PostImportAnalysisJob(symbols, event.get('timeframe', 'daily'))
            job.execute()
    ```

16. **Admin UI Job Control Error Handling**:
    ```python
    # WRONG: No error handling for job not found
    @jobs_bp.route('/trigger/<job_id>', methods=['POST'])
    def trigger_job(job_id: str):
        scheduler = get_scheduler()
        job = scheduler._scheduler.get_job(job_id)
        job.modify(next_run_time=datetime.now())  # AttributeError if job is None
        return jsonify({'success': True})

    # CORRECT: Check job exists before modifying
    @jobs_bp.route('/trigger/<job_id>', methods=['POST'])
    def trigger_job(job_id: str):
        try:
            scheduler = get_scheduler()
            job = scheduler._scheduler.get_job(job_id)

            if not job:
                return jsonify({
                    'success': False,
                    'error': f'Job {job_id} not found'
                }), 404

            job.modify(next_run_time=datetime.now())
            return jsonify({'success': True}), 200

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    ```

17. **Job Execution Timeout Handling**:
    ```python
    # WRONG: No timeout protection (job could hang indefinitely)
    def execute(self):
        result = self.run()  # Could hang forever
        return result

    # CORRECT: Use timeout or monitoring for long-running jobs
    def execute(self):
        self.start_time = datetime.now()
        max_duration = timedelta(hours=2)  # Job-specific timeout

        try:
            result = self.run()

            duration = datetime.now() - self.start_time
            if duration > max_duration:
                logger.warning(f"Job {self.name} exceeded timeout ({duration})")

            return result
        except Exception as e:
            logger.error(f"Job {self.name} failed: {e}")
            raise
    ```

## How

### Data Models (Dataclasses & SQLAlchemy)

**Job Execution Logging**:
```python
# Database table for job execution tracking
CREATE TABLE IF NOT EXISTS job_executions (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds NUMERIC(10, 3),
    success BOOLEAN NOT NULL,
    result TEXT,
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_job_executions_job_name ON job_executions(job_name);
CREATE INDEX idx_job_executions_started_at ON job_executions(started_at DESC);
CREATE INDEX idx_job_executions_success ON job_executions(success);
```

**Job Result Dataclasses**:
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

@dataclass
class IndicatorJobResult:
    """Result of indicator calculation job."""
    total_symbols: int
    successful: int
    failed: int
    indicators_calculated: int
    errors: List[Dict[str, str]] = field(default_factory=list)
    duration_seconds: float = 0.0

@dataclass
class PatternJobResult:
    """Result of pattern detection job."""
    total_symbols: int
    successful: int
    failed: int
    patterns_detected: int
    errors: List[Dict[str, str]] = field(default_factory=list)
    duration_seconds: float = 0.0

@dataclass
class PostImportJobResult:
    """Result of post-import analysis job."""
    total_symbols: int
    successful: int
    failed: int
    indicators_calculated: int
    patterns_detected: int
    errors: List[Dict[str, str]] = field(default_factory=list)
    duration_seconds: float = 0.0
```

### Implementation Tasks (Dependency-Ordered, Information-Dense)

**Week 1: Background Job Infrastructure (Days 1-5)**

**Day 1: APScheduler Setup**
- Install APScheduler: `pip install apscheduler`
- Create `src/jobs/` directory structure
- Create `SchedulerManager` singleton in `src/jobs/scheduler.py`
  - BackgroundScheduler with timezone=America/New_York
  - Executors: default (ThreadPoolExecutor, max_workers=10), analysis (max_workers=5)
  - Job defaults: coalesce=True, max_instances=1, misfire_grace_time=300
- Create `BaseJob` abstract class in `src/jobs/base_job.py`
  - Abstract run() method (job-specific logic)
  - execute() wrapper with error handling, timing, database logging
  - _log_execution() to job_executions table
- Integrate scheduler with Flask app lifecycle in `src/app.py`
  - Start scheduler in create_app()
  - Register teardown_appcontext hook for graceful shutdown
- Add environment variables to .env
  - JOB_SCHEDULER_ENABLED=true
  - JOB_DAILY_ANALYSIS_TIME=18:00
  - JOB_INDICATOR_CALC_TIME=18:10
  - JOB_PATTERN_DETECTION_TIME=18:20
  - JOB_MAINTENANCE_TIME=02:00
  - JOB_MAX_WORKERS=10
- Create database migration for job_executions table
  - Run `python model_migrations_run.py migrate "Add job_executions table"`
  - Run `python model_migrations_run.py upgrade`
- Write unit tests: `tests/unit/jobs/test_scheduler.py`, `test_base_job.py`
  - Test scheduler singleton
  - Test scheduler initialization with correct timezone
  - Test BaseJob error handling
  - Test job execution logging
- Success: APScheduler initialized, BaseJob working, 3+ tests pass

**Day 2: Daily Indicator Calculation Job**
- Create `DailyIndicatorJob` in `src/jobs/daily_indicator_job.py`
  - Extends BaseJob
  - run() method: Get universe symbols via RelationshipCache
  - Parallel processing with ThreadPoolExecutor (max_workers=10)
  - Call AnalysisService.analyze_symbol(calculate_indicators=True, detect_patterns=False)
  - Return IndicatorJobResult dataclass
- Create job registration in `src/jobs/__init__.py`
  - register_jobs(scheduler) function
  - Add DailyIndicatorJob with CronTrigger (Mon-Fri, 6:10 PM ET)
  - Job ID: 'daily_indicator_calculation'
  - Executor: 'analysis' (dedicated for heavy analysis)
- Update Flask app to call register_jobs(scheduler) after scheduler.start()
- Write unit tests: `tests/unit/jobs/test_daily_indicator_job.py`
  - Test job execution with mock universe
  - Test parallel processing completes faster than sequential
  - Test error handling for failed symbols
  - Test result dataclass structure
- Success: DailyIndicatorJob calculates indicators for all universe symbols, 2+ tests pass

**Day 3: Daily Pattern Detection Job**
- Create `DailyPatternJob` in `src/jobs/daily_pattern_job.py`
  - Extends BaseJob
  - run() method: Get universe symbols via RelationshipCache
  - Parallel processing with ThreadPoolExecutor (max_workers=10)
  - Call AnalysisService.analyze_symbol(calculate_indicators=False, detect_patterns=True)
  - Publish detected patterns to Redis (tickstock.events.patterns)
  - Return PatternJobResult dataclass
- Add _publish_patterns() helper method
  - Redis publish to tickstock.events.patterns channel
  - Event format: {symbol, pattern_name, confidence, timeframe, detected_at, metadata}
- Update job registration in `src/jobs/__init__.py`
  - Add DailyPatternJob with CronTrigger (Mon-Fri, 6:20 PM ET)
  - 10 minute delay after DailyIndicatorJob (dependency enforcement)
  - Job ID: 'daily_pattern_detection'
  - Executor: 'analysis'
- Write unit tests: `tests/unit/jobs/test_daily_pattern_job.py`
  - Test job execution with mock universe
  - Test pattern Redis publishing
  - Test dependency on indicator job (scheduled 10 min after)
  - Test result dataclass structure
- Success: DailyPatternJob detects patterns and publishes to Redis, 2+ tests pass

**Day 4: Historical Import Integration**
- Create `DataLoadListener` in `src/jobs/data_load_listener.py`
  - Redis pubsub listener on tickstock.jobs.data_load channel
  - start() method with message loop in daemon background thread
  - _handle_message() validates event_type='data_load_complete'
  - Triggers PostImportAnalysisJob if run_analysis=True
- Create `PostImportAnalysisJob` in `src/jobs/post_import_analysis_job.py`
  - Extends BaseJob
  - Constructor: Takes symbols list and timeframe
  - run() method: Full analysis (indicators + patterns) for imported symbols
  - Parallel processing with ThreadPoolExecutor (max_workers=10)
  - Return PostImportJobResult dataclass
- Integrate DataLoadListener with Flask app lifecycle
  - Start listener in create_app() via start_data_load_listener()
  - Stop listener in teardown_appcontext via stop_data_load_listener()
- Write integration test: `tests/integration/test_post_import_analysis.py`
  - Mock Redis publish of data_load_complete event
  - Verify PostImportAnalysisJob triggers automatically
  - Verify indicators + patterns calculated for imported symbols
  - Verify results stored in database
- Success: Post-import analysis triggered by TickStockPL data load events, 1+ integration test passes

**Day 5: Job Monitoring & Admin UI**
- Create job monitoring API in `src/api/routes/jobs.py`
  - Blueprint: jobs_bp with url_prefix='/api/jobs'
  - GET /status: List all scheduled jobs with next run times
  - GET /history?limit=50&job_name=...: Job execution history
  - POST /trigger/<job_id>: Manually trigger job
  - POST /pause/<job_id>: Pause scheduled job
  - POST /resume/<job_id>: Resume paused job
- Register jobs_bp blueprint in `src/app.py`
- Write integration tests: `tests/integration/test_jobs_api.py`
  - Test GET /api/jobs/status returns job list
  - Test GET /api/jobs/history returns execution history
  - Test POST /api/jobs/trigger/<job_id> triggers job
  - Test 404 error for non-existent job_id
- Success: Job monitoring API functional, 4+ integration tests pass

**Week 2: TickStockPL Dependency Removal (Days 6-10)**

**Day 6: Redis Channel Consolidation**
- Update `config/redis_config.py` with channel consolidation
  - Active channels (AppV2 owns): tickstock.events.patterns, tickstock.events.indicators, tickstock:monitoring, tickstock:errors
  - Data flow channels (TickStockPL owns): tickstock.jobs.data_load, tickstock:market:ticks
  - Deprecated channels (safe to remove): tickstock:patterns:streaming, tickstock:indicators:streaming
- Create Redis channel migration checklist in `docs/architecture/redis-channels.md`
  - Channels migrated to AppV2 (Sprint 69)
  - Channels still owned by TickStockPL (Sprint 70 migration)
  - Deprecated channels (safe to remove)
- Write integration test: `tests/integration/test_redis_channels.py`
  - Test AppV2 publishes to tickstock.events.patterns
  - Test no references to deprecated channels in codebase
- Success: Redis channels consolidated, documentation updated, 2+ tests pass

**Day 7-8: Remaining Background Jobs Migration**
- Create `CacheMaintenanceJob` in `src/jobs/cache_maintenance_job.py`
  - Extends BaseJob
  - run() method: Clear RelationshipCache, warm common queries, validate data quality
  - Validation: ETF count ≥24, universe count ≥3
  - Return cache stats
- Create `DatabaseCleanupJob` in `src/jobs/database_cleanup_job.py`
  - Extends BaseJob
  - run() method: Delete old pattern detections (>90 days), old indicator results (>180 days)
  - Return purge stats (rows deleted)
- Create `HealthMonitoringJob` in `src/jobs/health_monitoring_job.py`
  - Extends BaseJob
  - run() method: Check Redis connectivity, database connections, job execution rates
  - Publish health metrics to tickstock:monitoring channel
  - Return health status
- Update job registration in `src/jobs/__init__.py`
  - Add CacheMaintenanceJob with CronTrigger (Sunday 2 AM ET, weekly)
  - Add DatabaseCleanupJob with CronTrigger (Daily 3 AM ET)
  - Add HealthMonitoringJob with IntervalTrigger (hourly)
- Write unit tests for all 3 jobs
- Success: All 6 background jobs operational, 3+ tests pass

**Day 9: TickStockPL Deprecation Plan**
- Create `docs/planning/TICKSTOCKPL_DEPRECATION.md`
  - Migration summary (migrated vs remaining components)
  - Deprecation timeline (Phase 1: Sprint 69, Phase 2: Sprint 70, Phase 3: Cleanup)
  - Rollback procedure (redeploy TickStockPL, disable AppV2 jobs, re-enable PL Redis)
  - Success criteria for full deprecation
- Update deployment scripts to skip TickStockPL (optional step)
- Write integration test: `tests/integration/test_appv2_standalone.py`
  - Test AppV2 runs without TickStockPL
  - Test analysis services work standalone
  - Test background jobs execute without TickStockPL
- Success: Deprecation plan documented, standalone operation validated, 1+ test passes

**Day 10: Week 2 Validation & Testing**
- Run comprehensive integration test suite: `python run_tests.py`
- Verify all 6 background jobs execute successfully
- Test Redis channel consolidation (verify publishing/subscribing)
- Performance regression testing (compare to Sprint 68 baseline)
- Update sprint documentation
- Success: All tests pass (50+ unit, 15+ integration), zero regressions

**Week 3: Final Integration & Documentation (Days 11-15)**

**Day 11-12: Admin UI Analysis Control Panel**
- Create `web/templates/admin/analysis_control.html`
  - Extends base_admin.html template
  - Scheduled Jobs Status section (table with job name, next run, last execution, actions)
  - Manual Analysis section (form with symbol/universe input, analysis type selector)
  - Recent Job Executions section (table with job name, duration, status, result)
- Create `web/static/js/components/analysis-control-panel.js`
  - fetchJobStatus() - GET /api/jobs/status
  - fetchJobHistory() - GET /api/jobs/history
  - triggerJob(job_id) - POST /api/jobs/trigger/<job_id>
  - pauseJob(job_id) - POST /api/jobs/pause/<job_id>
  - resumeJob(job_id) - POST /api/jobs/resume/<job_id>
  - runManualAnalysis() - Custom analysis trigger
  - Auto-refresh job status every 30 seconds
- Add route in `src/app.py`
  - @app.route('/admin/analysis-control')
  - Render analysis_control.html template
- Success: Analysis control panel functional, manual triggers working

**Day 13-14: Documentation & Knowledge Transfer**
- Update `CLAUDE.md` with Sprint 69 completion
  - Add Sprint 69 summary under "Current Implementation Status"
  - Update "System Integration Points" with new Redis channels
  - Update "Common Commands" with job monitoring commands
- Create `docs/architecture/background-jobs.md`
  - APScheduler architecture overview
  - Job dependency diagram (indicator → pattern)
  - Job execution flow diagram
  - Troubleshooting common issues
- Update `docs/guides/troubleshooting.md`
  - Section: "Background Jobs Not Running"
  - Section: "Pattern Detection Missing"
  - Section: "Post-Import Analysis Not Triggered"
- Create `docs/planning/sprints/sprint69/SPRINT69_COMPLETE.md`
  - Implementation results summary
  - Performance metrics (vs targets)
  - Validation results (all 4 levels)
  - Lessons learned
  - Related commits/PRs
- Success: All documentation updated, knowledge transfer complete

**Day 15: Final Validation & Sprint Closure**
- Run full integration test suite: `python run_tests.py`
- Performance regression testing (compare to Sprint 68 baseline)
- User acceptance testing (manual job triggers, Admin UI navigation)
- Create sprint summary in SPRINT69_COMPLETE.md
- Update BACKLOG.md with deferred Sprint 70 items
- Commit all changes with proper commit message
- Tag sprint completion in git: `git tag sprint69-complete`
- Success: All validation gates pass, sprint documented, code committed

### Implementation Patterns (Code Examples)

**SchedulerManager Singleton** (`src/jobs/scheduler.py`):
```python
"""
APScheduler integration for TickStockAppV2.
Handles automated pattern detection, indicator calculation, and maintenance tasks.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SchedulerManager:
    """Singleton manager for APScheduler background jobs."""

    _instance: Optional['SchedulerManager'] = None
    _scheduler: Optional[BackgroundScheduler] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._scheduler is None:
            self._initialize_scheduler()

    def _initialize_scheduler(self):
        """Initialize APScheduler with TickStock-specific configuration."""
        jobstores = {
            'default': MemoryJobStore()
        }

        executors = {
            'default': ThreadPoolExecutor(max_workers=10),
            'analysis': ThreadPoolExecutor(max_workers=5)  # Dedicated for heavy analysis
        }

        job_defaults = {
            'coalesce': True,  # Combine multiple pending runs
            'max_instances': 1,  # Prevent concurrent runs of same job
            'misfire_grace_time': 300  # 5 minute grace period
        }

        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='America/New_York'  # Market timezone
        )

        logger.info("APScheduler initialized for TickStockAppV2")

    def start(self):
        """Start the scheduler (called during Flask app initialization)."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("APScheduler started")

    def shutdown(self):
        """Graceful shutdown (called during Flask app teardown)."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=True)
            logger.info("APScheduler shutdown complete")

    def add_job(self, func, trigger, **kwargs):
        """Add job to scheduler."""
        return self._scheduler.add_job(func, trigger, **kwargs)

    def get_jobs(self):
        """Get all scheduled jobs."""
        return self._scheduler.get_jobs()

    def pause_job(self, job_id: str):
        """Pause specific job."""
        self._scheduler.pause_job(job_id)

    def resume_job(self, job_id: str):
        """Resume paused job."""
        self._scheduler.resume_job(job_id)

# Global singleton instance
def get_scheduler() -> SchedulerManager:
    """Get scheduler singleton instance."""
    return SchedulerManager()
```

**BaseJob Abstract Class** (`src/jobs/base_job.py`):
```python
"""
Base class for all background jobs in TickStockAppV2.
Follows TickStockPL job pattern with logging, error handling, and metrics.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import traceback

from src.core.services.tickstock_database import TickStockDatabase

logger = logging.getLogger(__name__)

class BaseJob(ABC):
    """Base class for all scheduled jobs."""

    def __init__(self):
        self.name = self.__class__.__name__
        self.db = TickStockDatabase()
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def execute(self) -> Dict[str, Any]:
        """
        Execute job with error handling and logging.
        This is the entry point called by APScheduler.
        """
        self.start_time = datetime.now()
        logger.info(f"Job {self.name} started at {self.start_time}")

        try:
            # Execute job-specific logic
            result = self.run()

            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()

            logger.info(
                f"Job {self.name} completed in {duration:.2f}s. "
                f"Result: {result}"
            )

            # Log to database
            self._log_execution(success=True, result=result)

            return {
                'success': True,
                'duration': duration,
                'result': result
            }

        except Exception as e:
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()

            error_msg = f"Job {self.name} failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())

            # Log error to database
            self._log_execution(success=False, error=str(e))

            return {
                'success': False,
                'duration': duration,
                'error': str(e)
            }

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """
        Job-specific logic (implemented by subclasses).
        Must return dict with execution results.
        """
        pass

    def _log_execution(self, success: bool, result: Dict[str, Any] = None, error: str = None):
        """Log job execution to database for monitoring."""
        try:
            duration = (self.end_time - self.start_time).total_seconds()

            query = """
                INSERT INTO job_executions
                (job_name, started_at, completed_at, duration_seconds, success, result, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            self.db.execute_write(
                query,
                (
                    self.name,
                    self.start_time,
                    self.end_time,
                    duration,
                    success,
                    str(result) if result else None,
                    error
                )
            )

        except Exception as e:
            logger.error(f"Failed to log job execution: {e}")
```

**DailyIndicatorJob** (`src/jobs/daily_indicator_job.py`):
```python
"""
Daily Indicator Calculation Job.
Runs after market close (6:10 PM ET) to calculate all indicators for active universes.
"""

from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from src.jobs.base_job import BaseJob
from src.core.services.analysis_service import AnalysisService
from src.core.services.relationship_cache import get_relationship_cache

logger = logging.getLogger(__name__)

class DailyIndicatorJob(BaseJob):
    """Calculate indicators for all symbols in active universes."""

    def __init__(self):
        super().__init__()
        self.analysis_service = AnalysisService()
        self.cache = get_relationship_cache()
        self.universes = ['nasdaq100', 'sp500', 'dow30']  # Active universes
        self.max_workers = 10

    def run(self) -> Dict[str, Any]:
        """Execute daily indicator calculation."""
        results = {
            'total_symbols': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        # Get all symbols from active universes (distinct)
        all_symbols = self._get_universe_symbols()
        results['total_symbols'] = len(all_symbols)

        logger.info(f"Calculating indicators for {len(all_symbols)} symbols")

        # Parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._calculate_symbol, symbol): symbol
                for symbol in all_symbols
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result()
                    if result['success']:
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'symbol': symbol,
                            'error': result.get('error')
                        })
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'symbol': symbol,
                        'error': str(e)
                    })

        logger.info(
            f"Indicator calculation complete: "
            f"{results['successful']}/{results['total_symbols']} successful"
        )

        return results

    def _get_universe_symbols(self) -> List[str]:
        """Get distinct symbols from all active universes."""
        symbols = set()
        for universe in self.universes:
            universe_symbols = self.cache.get_universe_symbols(universe)
            symbols.update(universe_symbols)
        return list(symbols)

    def _calculate_symbol(self, symbol: str) -> Dict[str, Any]:
        """Calculate all indicators for single symbol."""
        try:
            result = self.analysis_service.analyze_symbol(
                symbol=symbol,
                calculate_indicators=True,
                detect_patterns=False  # Indicators only
            )

            return {
                'success': True,
                'symbol': symbol,
                'indicators_calculated': len(result.get('indicators', {}))
            }

        except Exception as e:
            logger.error(f"Failed to calculate indicators for {symbol}: {e}")
            return {
                'success': False,
                'symbol': symbol,
                'error': str(e)
            }
```

**DailyPatternJob** (`src/jobs/daily_pattern_job.py`):
```python
"""
Daily Pattern Detection Job.
Runs after indicator calculation (6:20 PM ET) to detect patterns for active universes.
"""

from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import redis

from src.jobs.base_job import BaseJob
from src.core.services.analysis_service import AnalysisService
from src.core.services.relationship_cache import get_relationship_cache
from config.redis_config import get_redis_client

logger = logging.getLogger(__name__)

class DailyPatternJob(BaseJob):
    """Detect patterns for all symbols in active universes."""

    def __init__(self):
        super().__init__()
        self.analysis_service = AnalysisService()
        self.cache = get_relationship_cache()
        self.redis_client = get_redis_client()
        self.universes = ['nasdaq100', 'sp500', 'dow30']
        self.max_workers = 10

    def run(self) -> Dict[str, Any]:
        """Execute daily pattern detection."""
        results = {
            'total_symbols': 0,
            'successful': 0,
            'failed': 0,
            'patterns_detected': 0,
            'errors': []
        }

        # Get all symbols
        all_symbols = self._get_universe_symbols()
        results['total_symbols'] = len(all_symbols)

        logger.info(f"Detecting patterns for {len(all_symbols)} symbols")

        # Parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._detect_symbol, symbol): symbol
                for symbol in all_symbols
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result()
                    if result['success']:
                        results['successful'] += 1
                        results['patterns_detected'] += result.get('pattern_count', 0)

                        # Publish patterns to Redis
                        if result.get('patterns'):
                            self._publish_patterns(symbol, result['patterns'])
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'symbol': symbol,
                            'error': result.get('error')
                        })
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'symbol': symbol,
                        'error': str(e)
                    })

        logger.info(
            f"Pattern detection complete: "
            f"{results['patterns_detected']} patterns detected across "
            f"{results['successful']}/{results['total_symbols']} symbols"
        )

        return results

    def _get_universe_symbols(self) -> List[str]:
        """Get distinct symbols from all active universes."""
        symbols = set()
        for universe in self.universes:
            universe_symbols = self.cache.get_universe_symbols(universe)
            symbols.update(universe_symbols)
        return list(symbols)

    def _detect_symbol(self, symbol: str) -> Dict[str, Any]:
        """Detect all patterns for single symbol."""
        try:
            result = self.analysis_service.analyze_symbol(
                symbol=symbol,
                calculate_indicators=False,  # Already calculated
                detect_patterns=True
            )

            patterns = result.get('patterns', {})
            detected_patterns = [
                p for p in patterns.values()
                if p.get('detected') is True
            ]

            return {
                'success': True,
                'symbol': symbol,
                'pattern_count': len(detected_patterns),
                'patterns': detected_patterns
            }

        except Exception as e:
            logger.error(f"Failed to detect patterns for {symbol}: {e}")
            return {
                'success': False,
                'symbol': symbol,
                'error': str(e)
            }

    def _publish_patterns(self, symbol: str, patterns: List[Dict[str, Any]]):
        """Publish detected patterns to Redis pub-sub."""
        try:
            for pattern in patterns:
                event = {
                    'symbol': symbol,
                    'pattern_name': pattern['pattern_name'],
                    'confidence': pattern.get('confidence', 0),
                    'timeframe': pattern.get('timeframe', 'daily'),
                    'detected_at': pattern.get('detected_at'),
                    'metadata': pattern.get('metadata', {})
                }

                # Publish to patterns channel
                self.redis_client.publish(
                    'tickstock.events.patterns',
                    str(event)  # JSON serialization happens in Redis handler
                )

        except Exception as e:
            logger.error(f"Failed to publish patterns for {symbol}: {e}")
```

**Job Registration** (`src/jobs/__init__.py`):
```python
"""Job registration for APScheduler."""

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from src.jobs.daily_indicator_job import DailyIndicatorJob
from src.jobs.daily_pattern_job import DailyPatternJob
from src.jobs.cache_maintenance_job import CacheMaintenanceJob
from src.jobs.database_cleanup_job import DatabaseCleanupJob
from src.jobs.health_monitoring_job import HealthMonitoringJob
import os
import logging

logger = logging.getLogger(__name__)

def register_jobs(scheduler):
    """Register all scheduled jobs."""

    # Daily Indicator Calculation (6:10 PM ET, Mon-Fri)
    indicator_time = os.getenv('JOB_INDICATOR_CALC_TIME', '18:10')
    hour, minute = indicator_time.split(':')

    scheduler.add_job(
        func=DailyIndicatorJob().execute,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=int(hour),
            minute=int(minute),
            timezone='America/New_York'
        ),
        id='daily_indicator_calculation',
        name='Daily Indicator Calculation',
        replace_existing=True,
        executor='analysis'  # Use dedicated analysis executor
    )

    logger.info(f"Registered job: daily_indicator_calculation at {indicator_time} ET")

    # Daily Pattern Detection (6:20 PM ET, Mon-Fri)
    # Runs 10 minutes after indicator calculation
    pattern_time = os.getenv('JOB_PATTERN_DETECTION_TIME', '18:20')
    hour, minute = pattern_time.split(':')

    scheduler.add_job(
        func=DailyPatternJob().execute,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=int(hour),
            minute=int(minute),
            timezone='America/New_York'
        ),
        id='daily_pattern_detection',
        name='Daily Pattern Detection',
        replace_existing=True,
        executor='analysis'
    )

    logger.info(f"Registered job: daily_pattern_detection at {pattern_time} ET")

    # Cache Maintenance (Sunday 2 AM ET, weekly)
    scheduler.add_job(
        func=CacheMaintenanceJob().execute,
        trigger=CronTrigger(
            day_of_week='sun',
            hour=2,
            minute=0,
            timezone='America/New_York'
        ),
        id='weekly_cache_maintenance',
        name='Weekly Cache Maintenance',
        replace_existing=True
    )

    logger.info("Registered job: weekly_cache_maintenance at 2:00 AM ET (Sunday)")

    # Database Cleanup (Daily 3 AM ET)
    scheduler.add_job(
        func=DatabaseCleanupJob().execute,
        trigger=CronTrigger(
            hour=3,
            minute=0,
            timezone='America/New_York'
        ),
        id='daily_database_cleanup',
        name='Daily Database Cleanup',
        replace_existing=True
    )

    logger.info("Registered job: daily_database_cleanup at 3:00 AM ET")

    # Health Monitoring (Hourly)
    scheduler.add_job(
        func=HealthMonitoringJob().execute,
        trigger=IntervalTrigger(hours=1),
        id='hourly_health_monitoring',
        name='Hourly Health Monitoring',
        replace_existing=True
    )

    logger.info("Registered job: hourly_health_monitoring (every hour)")

    logger.info("All background jobs registered (AppV2 owns scheduling)")
```

**Flask App Integration** (`src/app.py` modifications):
```python
# In create_app() function:

from src.jobs.scheduler import get_scheduler
from src.jobs import register_jobs
from src.jobs.data_load_listener import start_data_load_listener, stop_data_load_listener

def create_app():
    app = Flask(__name__)

    # ... existing initialization ...

    # Initialize scheduler
    scheduler = get_scheduler()
    scheduler.start()

    # Register jobs
    register_jobs(scheduler)

    # Start data load listener (Redis pub-sub for post-import analysis)
    start_data_load_listener()

    # Shutdown hooks
    @app.teardown_appcontext
    def shutdown_services(exception=None):
        scheduler.shutdown()
        stop_data_load_listener()

    return app
```

### Integration Points

**Sprint 68 Integration** (AnalysisService):
- DailyIndicatorJob calls `AnalysisService.analyze_symbol(calculate_indicators=True, detect_patterns=False)`
- DailyPatternJob calls `AnalysisService.analyze_symbol(calculate_indicators=False, detect_patterns=True)`
- PostImportAnalysisJob calls `AnalysisService.analyze_symbol(calculate_indicators=True, detect_patterns=True)`

**Sprint 60/61 Integration** (RelationshipCache):
- All jobs use `RelationshipCache.get_universe_symbols(universe)` for symbol resolution
- Multi-universe join: `cache.get_universe_symbols('sp500:nasdaq100')` creates distinct union
- Performance: <1ms cache hit (vs 30-50ms database query)

**Redis Pub-Sub Integration**:
- DailyPatternJob publishes to `tickstock.events.patterns` (existing WebSocket subscribers)
- DataLoadListener subscribes to `tickstock.jobs.data_load` (TickStockPL publishes)
- Event format consistency: {symbol, pattern_name, confidence, timeframe, detected_at, metadata}

**Database Integration**:
- Job execution logging: INSERT INTO job_executions table
- Pattern storage: INSERT INTO daily_patterns table (via PatternService)
- Indicator storage: INSERT INTO indicator_results table (via IndicatorService)

## Validation

### Level 1: Syntax & Style Validation

**Tools**: ruff (linting)

**Commands**:
```bash
# Lint new job files
ruff check src/jobs/

# Lint API routes
ruff check src/api/routes/jobs.py

# Lint test files
ruff check tests/unit/jobs/
ruff check tests/integration/test_jobs_api.py

# Expected: Zero errors, zero warnings
```

**Success Criteria**:
- Zero linting errors
- File naming conventions followed (snake_case)
- File placement matches desired codebase tree
- No "Generated by Claude" comments in code

### Level 2: Unit Tests

**Test Coverage**: 50+ unit tests

**Commands**:
```bash
# Run scheduler tests
pytest tests/unit/jobs/test_scheduler.py -v

# Run base job tests
pytest tests/unit/jobs/test_base_job.py -v

# Run daily indicator job tests
pytest tests/unit/jobs/test_daily_indicator_job.py -v

# Run daily pattern job tests
pytest tests/unit/jobs/test_daily_pattern_job.py -v

# Run cache maintenance tests
pytest tests/unit/jobs/test_cache_maintenance.py -v

# Expected: All tests pass, >80% code coverage
```

**Test Cases**:
- `test_scheduler_singleton()` - Verify SchedulerManager is singleton
- `test_scheduler_initialization()` - Verify correct timezone, executors, job defaults
- `test_base_job_error_handling()` - Verify BaseJob catches exceptions
- `test_base_job_logging()` - Verify job execution logged to database
- `test_daily_indicator_job_execution()` - Verify indicators calculated for all symbols
- `test_daily_indicator_job_parallel_processing()` - Verify parallel faster than sequential
- `test_daily_pattern_job_execution()` - Verify patterns detected for all symbols
- `test_daily_pattern_job_redis_publishing()` - Verify patterns published to Redis
- `test_cache_maintenance_job_execution()` - Verify cache cleared and warmed
- `test_cache_maintenance_job_validation()` - Verify data quality checks

**Success Criteria**:
- All 50+ unit tests pass
- Code coverage >80% for src/jobs/ directory
- Test execution time <30 seconds

### Level 3: Integration Tests

**Test Coverage**: 15+ integration tests

**Commands**:
```bash
# Run full integration test suite (MANDATORY before commits)
python run_tests.py

# Run jobs API tests
pytest tests/integration/test_jobs_api.py -v

# Run post-import analysis flow test
pytest tests/integration/test_post_import_analysis.py -v

# Run AppV2 standalone test
pytest tests/integration/test_appv2_standalone.py -v

# Run Redis channel tests
pytest tests/integration/test_redis_channels.py -v

# Expected: All tests pass, pattern flow tests maintain baseline
```

**Test Cases**:
- `test_get_job_status()` - Verify /api/jobs/status endpoint
- `test_get_job_history()` - Verify /api/jobs/history endpoint
- `test_trigger_job()` - Verify manual job triggering
- `test_pause_resume_job()` - Verify job pause/resume
- `test_post_import_analysis_flow()` - Verify data load event triggers analysis
- `test_appv2_runs_without_tickstockpl()` - Verify standalone operation
- `test_appv2_pattern_publishing()` - Verify AppV2 publishes to correct channel
- `test_deprecated_channels_not_used()` - Verify no references to old channels
- `test_job_execution_logging()` - Verify all jobs log to job_executions table
- `test_daily_indicator_job_integration()` - End-to-end indicator calculation
- `test_daily_pattern_job_integration()` - End-to-end pattern detection with Redis

**Success Criteria**:
- All 15+ integration tests pass
- Pattern flow tests maintain Sprint 68 baseline (zero regressions)
- Background jobs execute without errors
- Job execution logged to database
- Redis pub-sub working end-to-end

### Level 4: TickStock-Specific Validation

**Architecture Compliance**:
```yaml
component_role_validation:
  - AppV2 operates standalone for analysis features (without TickStockPL)
  - Background jobs use AnalysisService from Sprint 68
  - Redis channel consolidation complete (AppV2 publishes patterns/indicators)
  - No database writes outside INSERT operations
  - Performance targets met (<10 min for 500 symbols)

integration_validation:
  - APScheduler integrated with Flask app lifecycle
  - Scheduler starts with app, stops on teardown
  - All 6 jobs registered and scheduled correctly
  - Job execution logged to database
  - DataLoadListener subscribes to TickStockPL events

redis_validation:
  - AppV2 publishes to tickstock.events.patterns
  - AppV2 publishes to tickstock.events.indicators (optional)
  - No references to deprecated channels (tickstock:patterns:streaming)
  - DataLoadListener subscribes to tickstock.jobs.data_load

performance_validation:
  - DailyIndicatorJob: <10 min for 500 symbols
  - DailyPatternJob: <10 min for 500 symbols
  - Job monitoring API: <50ms per request
  - Redis publish: <10ms per message
  - Parallel processing faster than sequential (ThreadPoolExecutor)

regression_validation:
  - Pattern detection accuracy matches Sprint 68 baseline
  - Indicator calculation values match Sprint 68 baseline
  - Integration tests pass identically to Sprint 68
  - Zero data loss or corruption
```

**Validation Commands**:
```bash
# Architecture validation
python run_tests.py  # Must pass pattern flow tests

# Performance validation (manual)
# 1. Trigger DailyIndicatorJob manually via Admin UI
# 2. Monitor execution time (target: <10 min for 500 symbols)
# 3. Trigger DailyPatternJob manually
# 4. Monitor execution time (target: <10 min for 500 symbols)

# Redis validation
python scripts/diagnostics/monitor_redis_channels.py
# Expected: See pattern events on tickstock.events.patterns

# Job execution validation
# Check job_executions table
SELECT job_name, COUNT(*) as executions, AVG(duration_seconds) as avg_duration, SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
FROM job_executions
GROUP BY job_name
ORDER BY job_name;
# Expected: All jobs have executions, success rate >99%
```

**Success Criteria**:
- AppV2 runs standalone (analysis features work without TickStockPL)
- All background jobs execute successfully (>99% success rate)
- Performance targets met (<10 min for 500 symbols)
- Redis channel consolidation complete (AppV2 publishes)
- Job execution logged to database (monitoring data available)
- Zero regressions vs Sprint 68 baseline

## Anti-Patterns (What NOT to Do)

### Architecture Violations
1. ❌ Running analysis in Flask request handlers (blocks request)
   - ✅ Always use background jobs for analysis (non-blocking)
2. ❌ Blocking Flask app startup waiting for jobs
   - ✅ Jobs run in background threads (daemon=True)
3. ❌ Creating new Redis channels without documentation
   - ✅ Follow existing channel naming (tickstock.events.*)
4. ❌ Skipping job execution logging
   - ✅ Always log to job_executions table (monitoring requirement)

### Data Handling Mistakes
5. ❌ Querying database for universe symbols in jobs
   - ✅ Use RelationshipCache.get_universe_symbols() (<1ms)
6. ❌ Mixing job result types (dataclass vs dict vs string)
   - ✅ Use consistent dataclass result objects (IndicatorJobResult, PatternJobResult)
7. ❌ Not handling job execution timeouts
   - ✅ Monitor duration, warn if exceeds threshold (2 hours)
8. ❌ Storing job results without serialization
   - ✅ Convert dataclass to string or dict before database storage

### Performance Anti-Patterns
9. ❌ Sequential processing of symbols (slow)
   - ✅ Use ThreadPoolExecutor for parallel processing (10 workers)
10. ❌ No context manager for ThreadPoolExecutor
    - ✅ Use `with ThreadPoolExecutor() as executor:` (automatic cleanup)
11. ❌ Hardcoded schedule times in code
    - ✅ Use environment variables (JOB_INDICATOR_CALC_TIME=18:10)
12. ❌ Running analysis during market hours
    - ✅ Schedule jobs after market close (6:10 PM, 6:20 PM ET)

### Testing Errors
13. ❌ Not testing job execution end-to-end
    - ✅ Integration tests for each job (execute + verify results)
14. ❌ Not testing Redis pub-sub flow
    - ✅ Test pattern publishing from DailyPatternJob to WebSocket subscribers
15. ❌ Not testing job pause/resume functionality
    - ✅ Test job control via Admin UI and API endpoints
16. ❌ Skipping integration tests before commits
    - ✅ ALWAYS run `python run_tests.py` (MANDATORY)

### Documentation Errors
17. ❌ Not documenting job dependencies (indicator → pattern)
    - ✅ Clear documentation of job execution order and dependencies
18. ❌ Not updating CLAUDE.md with Sprint 69 completion
    - ✅ Update all documentation (CLAUDE.md, architecture docs, sprint completion)
19. ❌ Not documenting Redis channel consolidation
    - ✅ Redis channel migration checklist with active/deprecated channels
20. ❌ Not creating TickStockPL deprecation plan
    - ✅ Comprehensive deprecation document with rollback procedure

## Final Validation Checklist

Before marking Sprint 69 complete, verify:

### Code Quality
- [ ] All ruff linting passes (zero errors)
- [ ] No "Generated by Claude" comments in code
- [ ] File naming conventions followed (snake_case)
- [ ] File placement matches desired codebase tree
- [ ] Code coverage >80% for src/jobs/

### Functionality
- [ ] APScheduler integrated with Flask app lifecycle
- [ ] All 6 background jobs registered and operational
- [ ] DailyIndicatorJob calculates indicators for 500+ symbols
- [ ] DailyPatternJob detects patterns and publishes to Redis
- [ ] PostImportAnalysisJob triggers on TickStockPL data loads
- [ ] CacheMaintenanceJob refreshes cache without errors
- [ ] DatabaseCleanupJob purges old data successfully
- [ ] Job monitoring API endpoints functional (5 endpoints)
- [ ] Analysis Control Panel displays job status
- [ ] Manual job triggering works via Admin UI

### Testing
- [ ] 50+ unit tests pass (src/jobs/)
- [ ] 15+ integration tests pass
- [ ] Integration tests maintain Sprint 68 baseline (zero regressions)
- [ ] Background jobs execute without errors
- [ ] Job execution logged to database
- [ ] Redis pub-sub working end-to-end

### Performance
- [ ] DailyIndicatorJob: <10 min for 500 symbols
- [ ] DailyPatternJob: <10 min for 500 symbols
- [ ] Job monitoring API: <50ms per request
- [ ] Redis publish: <10ms per message
- [ ] Parallel processing faster than sequential

### Architecture
- [ ] AppV2 runs standalone (analysis features work without TickStockPL)
- [ ] Redis channel consolidation complete (AppV2 publishes)
- [ ] TickStockPL deprecation plan documented
- [ ] Job dependencies enforced (indicator before pattern)
- [ ] No database writes outside INSERT operations

### Documentation
- [ ] CLAUDE.md updated with Sprint 69 completion
- [ ] docs/architecture/background-jobs.md created
- [ ] docs/architecture/redis-channels.md updated
- [ ] docs/planning/TICKSTOCKPL_DEPRECATION.md created
- [ ] docs/planning/sprints/sprint69/SPRINT69_COMPLETE.md created
- [ ] Troubleshooting guide updated

### Deployment Readiness
- [ ] Environment variables documented (.env)
- [ ] Database migration applied (job_executions table)
- [ ] Flask app lifecycle hooks tested (start/teardown)
- [ ] Rollback procedure documented and tested
- [ ] Sprint 70 planning ready

---

**Estimated Implementation Time**: 3 weeks (15 working days)
- Week 1: Background job infrastructure (Days 1-5)
- Week 2: TickStockPL dependency removal (Days 6-10)
- Week 3: Final integration & documentation (Days 11-15)

**Dependencies**: Sprint 68 complete (indicators, patterns, analysis engines migrated)

**Risk Level**: MEDIUM (rollback plan mitigates risk)

**One-Pass Implementation Confidence**: 90/100

**Next Sprint**: Sprint 70 - Historical Import Consolidation (remove duplicate loader, wire Admin UI to TickStockPL Redis queue)
