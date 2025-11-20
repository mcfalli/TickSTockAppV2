# Sprint 33: Enhanced Requirements & Testing Protocol

**Document Version**: 1.0
**Created**: 2025-01-25
**Purpose**: Additional requirements for Sprint 33 implementation phases

## Core Requirements

### 1. Test Coverage Requirements

Every phase MUST include appropriate tests in the `tests/` folder structure:

#### Phase-Specific Test Requirements

**Phase 1: Foundation & Scheduler**
- Location: `tests/unit/services/sprint33/test_daily_processing_scheduler.py`
- Tests: Scheduler initialization, market calendar, timezone handling, Redis publishing
- Integration: `tests/integration/sprint33/test_scheduler_integration.py`

**Phase 2: Data Import Pipeline**
- Location: `tests/unit/jobs/sprint33/test_daily_import_job.py`
- Tests: Universe loading, Massive fetching, batch processing, retry logic
- Integration: `tests/integration/sprint33/test_import_pipeline.py`

**Phase 3: Indicator Processing**
- Location: `tests/unit/jobs/sprint33/test_indicator_processing.py`
- Tests: Dynamic loading, calculation accuracy, caching, storage
- Integration: `tests/integration/sprint33/test_indicator_pipeline.py`

**Phase 4: Pattern Detection**
- Location: `tests/unit/jobs/sprint33/test_pattern_detection.py`
- Tests: Pattern loading, detection logic, indicator integration, event publishing
- Integration: `tests/integration/sprint33/test_pattern_pipeline.py`

**Phase 5: Streaming Foundation**
- Location: `tests/unit/streaming/sprint33/test_websocket_manager.py`
- Tests: Connection management, aggregation, persistence, reconnection
- Integration: `tests/integration/sprint33/test_streaming_foundation.py`

**Phase 6: Streaming Indicators & Patterns**
- Location: `tests/unit/streaming/sprint33/test_realtime_processing.py`
- Tests: Real-time calculations, sliding windows, event throttling
- Integration: `tests/integration/sprint33/test_streaming_pipeline.py`

**Phase 7: Integration & Testing**
- Location: `tests/integration/sprint33/test_e2e_processing.py`
- Tests: Full system integration, performance benchmarks, failure recovery
- Performance: `tests/performance/sprint33/test_benchmark_suite.py`

### 2. Existing Test Verification

At EVERY phase checkpoint, the following existing tests MUST pass:

```bash
# Core pattern and indicator tests that must remain green
python -m pytest tests/integration/services/test_pattern_detection_service.py -v
python -m pytest tests/unit/indicators/test_all_indicators.py -v
python -m pytest tests/integration/test_pattern_service_comprehensive.py -v

# Run the main test suite
python run_tests.py
```

If any existing tests fail due to new changes:
1. STOP implementation
2. Document the conflict
3. Discuss enhancement requirements
4. Update tests only after approval

### 3. TickStockAppV2 Integration Requirements

#### Communication Protocol

TickStockPL and TickStockAppV2 communicate exclusively through Redis pub/sub channels.

#### Required Documentation per Phase

Each phase must document the following for TickStockAppV2:

**Phase 1 - Scheduler**
```yaml
# File: docs/api/sprint33/phase1_app_integration.md
Redis Channels:
  - tickstock:processing:status
  - tickstock:processing:schedule

Messages:
  daily_processing_started:
    channel: tickstock:processing:status
    payload:
      event: "daily_processing_started"
      timestamp: ISO8601
      run_id: UUID
      symbols_count: integer

  daily_processing_progress:
    channel: tickstock:processing:status
    payload:
      event: "daily_processing_progress"
      run_id: UUID
      symbols_completed: integer
      symbols_total: integer
      percent_complete: float
```

**Phase 2 - Data Import**
```yaml
# File: docs/api/sprint33/phase2_app_integration.md
Redis Channels:
  - tickstock:data:import:status
  - tickstock:data:import:errors

Messages:
  import_completed:
    channel: tickstock:data:import:status
    payload:
      event: "import_completed"
      timestamp: ISO8601
      timeframe: "daily|hourly|weekly|monthly"
      symbols_processed: integer
      symbols_failed: array
```

**Phase 3 - Indicators**
```yaml
# File: docs/api/sprint33/phase3_app_integration.md
Redis Channels:
  - tickstock:indicators:daily
  - tickstock:indicators:updates

Messages:
  indicator_calculated:
    channel: tickstock:indicators:daily
    payload:
      event: "indicator_calculated"
      symbol: string
      indicator: string
      value: object
      timestamp: ISO8601
```

**Phase 4 - Patterns**
```yaml
# File: docs/api/sprint33/phase4_app_integration.md
Redis Channels:
  - tickstock:patterns:daily
  - tickstock:patterns:alerts

Messages:
  pattern_detected:
    channel: tickstock:patterns:daily
    payload:
      event: "pattern_detected"
      symbol: string
      pattern_type: string
      confidence: float
      levels: array
      timestamp: ISO8601
```

**Phase 5 & 6 - Streaming**
```yaml
# File: docs/api/sprint33/phase5_6_app_integration.md
Redis Channels:
  - tickstock:streaming:status
  - tickstock:data:realtime
  - tickstock:indicators:intraday
  - tickstock:patterns:intraday

Messages:
  realtime_update:
    channel: tickstock:data:realtime
    payload:
      event: "realtime_update"
      symbol: string
      ohlcv: object
      timestamp: ISO8601

  intraday_pattern:
    channel: tickstock:patterns:intraday
    payload:
      event: "intraday_pattern"
      symbol: string
      pattern: object
      confidence: float
      timestamp: ISO8601
```

### 4. Phase Gate Checklist

Before marking ANY phase as complete:

#### Code Requirements
- [ ] All code implemented according to phase specification
- [ ] Type hints on all functions
- [ ] Docstrings on all classes and public methods
- [ ] No hardcoded values (use config)

#### Test Requirements
- [ ] Unit tests written and passing (>80% coverage)
- [ ] Integration tests written and passing
- [ ] Existing core tests still passing
- [ ] Performance benchmarks met

#### Documentation Requirements
- [ ] API documentation for TickStockAppV2 created
- [ ] Redis message formats documented
- [ ] Configuration examples provided
- [ ] Error codes defined

#### Integration Requirements
- [ ] Redis channels publishing correctly
- [ ] Message formats validated
- [ ] TickStockAppV2 integration tested (if available)
- [ ] Monitoring metrics publishing

### 5. TickStockAppV2 Notification Protocol

When changes affect TickStockAppV2:

1. **Create Integration Notice**
```markdown
# File: docs/api/sprint33/integration_notice_YYYY-MM-DD.md

## Integration Notice for TickStockAppV2

### Changes in Phase X
- New Redis channels: [list]
- Modified message formats: [list]
- Breaking changes: [list]
- Migration required: Yes/No

### Action Required
- Update WebSocket handlers for new channels
- Modify message parsers for new formats
- Test with sample messages provided

### Testing
Sample messages available in: tests/fixtures/sprint33/sample_messages.json
```

2. **Provide Test Fixtures**
```python
# File: tests/fixtures/sprint33/sample_messages.json
{
  "daily_processing_started": {
    "channel": "tickstock:processing:status",
    "message": {
      "event": "daily_processing_started",
      "timestamp": "2025-01-25T21:10:00Z",
      "run_id": "550e8400-e29b-41d4-a716-446655440000",
      "symbols_count": 505
    }
  }
}
```

3. **Update Shared Documentation**
```markdown
# File: docs/api/redis_protocol.md
# Keep this file always current with ALL Redis channels and message formats
```

### 6. Performance Validation

Each phase must validate performance doesn't degrade:

```python
# File: tests/performance/sprint33/phase_X_benchmarks.py

def test_phase_performance():
    """Ensure phase implementation meets performance targets"""

    # Memory baseline
    assert memory_usage() < 2_000_000_000  # 2GB

    # Processing time
    assert processing_time(1000_symbols) < 60  # seconds

    # Cache performance
    assert cache_hit_rate() > 0.8  # 80%

    # Database connections
    assert active_connections() < 50
```

### 7. Error Recovery Testing

Each phase must handle failures gracefully:

```python
# Required failure scenarios per phase
FAILURE_SCENARIOS = {
    "phase1": ["scheduler_crash", "redis_disconnect", "db_timeout"],
    "phase2": ["massive_api_down", "rate_limit_hit", "partial_import"],
    "phase3": ["indicator_calculation_error", "cache_failure", "oom"],
    "phase4": ["pattern_detection_timeout", "invalid_indicator_data"],
    "phase5": ["websocket_disconnect", "buffer_overflow", "network_loss"],
    "phase6": ["streaming_backpressure", "calculation_lag"],
    "phase7": ["tier_coordination_failure", "state_sync_error"]
}
```

### 8. Rollback Plan

Each phase must be independently rollback-able:

1. Database migrations must have DOWN scripts
2. Configuration changes must be feature-flagged
3. Redis channels must be versioned (e.g., `tickstock:v2:patterns`)
4. Previous version must remain functional

### 9. Monitoring Requirements

Each phase adds monitoring metrics:

```python
# Required metrics per phase
MONITORING_METRICS = {
    "phase1": ["scheduler_health", "trigger_success_rate", "processing_queue_size"],
    "phase2": ["import_rate", "symbols_per_second", "api_latency"],
    "phase3": ["indicators_per_second", "cache_hit_rate", "calculation_errors"],
    "phase4": ["patterns_detected", "detection_latency", "confidence_distribution"],
    "phase5": ["websocket_connections", "reconnection_rate", "data_lag"],
    "phase6": ["streaming_throughput", "pattern_detection_rate", "memory_usage"],
    "phase7": ["e2e_latency", "tier_coordination_time", "overall_success_rate"]
}
```

### 10. Sign-off Requirements

Each phase requires sign-off before proceeding:

```yaml
Phase_X_Signoff:
  code_complete: [developer_name, date]
  tests_passing: [test_results_link]
  documentation_complete: [doc_reviewer, date]
  integration_tested: [app_team_member, date]
  performance_validated: [benchmark_results]
  rollback_tested: [yes/no]
  approved_to_proceed: [approver, date]
```

## Communication Checklist

Before implementing ANY phase:

- [ ] Review this enhanced requirements document
- [ ] Confirm TickStockAppV2 team is aware of timeline
- [ ] Verify Redis channel naming with App team
- [ ] Share message format proposals for feedback
- [ ] Schedule integration testing windows

## Test Execution Protocol

### Daily During Development
```bash
# Quick validation
python -m pytest tests/unit/[current_phase]/ -v

# Core tests must always pass
python run_tests.py
```

### At Phase Completion
```bash
# Full test suite
python -m pytest tests/ -v --cov=src --cov-report=html

# Performance validation
python -m pytest tests/performance/sprint33/ -v

# Integration with TickStockAppV2 (if available)
python tests/integration/sprint33/test_app_communication.py
```

### Before Phase Sign-off
```bash
# Complete validation suite
./scripts/validate_phase.sh [phase_number]

# This script should:
# 1. Run all tests
# 2. Check code coverage
# 3. Validate documentation
# 4. Test Redis communications
# 5. Run performance benchmarks
# 6. Generate sign-off report
```

## Questions to Address

Before starting implementation:

1. Is TickStockAppV2 ready to handle new Redis channels?
2. Should we version the Redis channels (v1, v2)?
3. What's the rollback strategy if issues arise?
4. How do we coordinate testing between PL and App?
5. Should we implement feature flags for gradual rollout?

## Success Criteria Updates

Original success criteria PLUS:

- All existing tests remain green throughout implementation
- TickStockAppV2 successfully receives and processes all events
- Documentation enables App team to integrate independently
- Performance benchmarks show no degradation
- Rollback procedure tested and documented
- Monitoring dashboard shows all metrics