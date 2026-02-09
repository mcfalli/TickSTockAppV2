# TickStockAppV2 Product Backlog

**Last Updated**: 2026-02-09
**Purpose**: Track future enhancements, technical debt, and feature requests

## Sprint 69 Completed Items ✅

### ✅ High-Value Reversal Patterns (COMPLETE)
**Context**: Sprint 69 completed all 5 high-value patterns, extending pattern library from 3 to 8 patterns.

- ✅ **Morning Star** - Three-bar bullish reversal pattern (20 tests, 2.5h)
- ✅ **Evening Star** - Three-bar bearish reversal pattern (20 tests, 1.5h)
- ✅ **Harami** - Two-bar reversal pattern (21 tests, 2h)
- ✅ **Shooting Star** - Single-bar bearish reversal pattern (18 tests, 1h)
- ✅ **Hanging Man** - Single-bar bearish reversal pattern (21 tests, 1.5h)

**Actual Effort**: 8.5 hours (30% faster than 10-15h estimate)
**Status**: Pattern library now production-ready with 8 patterns, 155 tests

### Priority: Medium - Pattern Database Registration
**Context**: Sprint 68/69 patterns exist as code but not registered in `pattern_definitions` table.

- [ ] **Register Sprint 68/69 Patterns in Database**
  - Insert 8 patterns into `pattern_definitions` table
  - Patterns: Doji, Hammer, Engulfing, Shooting Star, Hanging Man, Harami, Morning Star, Evening Star
  - Set metadata: short_description, long_description, category, confidence_threshold
  - Enable patterns: `enabled = true`
  - Set display_order for UI
  - Expected effort: 1-2 hours (SQL inserts + testing)
  - Priority: Medium (enables UI pattern library display)

---

## Sprint 68/69 Deferred Items

### Priority: Medium - Additional Candlestick Patterns
**Context**: Sprint 68/69 implemented 8 patterns. Additional patterns from TickStockPL available for future enhancement if needed.
- [ ] **Piercing Line** - Two-bar bullish reversal
- [ ] **Dark Cloud Cover** - Two-bar bearish reversal
- [ ] **Three White Soldiers** - Three-bar bullish continuation
- [ ] **Three Black Crows** - Three-bar bearish continuation
- [ ] **Tweezer Top/Bottom** - Two-bar reversal patterns
- [ ] **Marubozu** - Single-bar strong trend indicator
- [ ] **Spinning Top** - Single-bar indecision pattern
- [ ] **8+ additional patterns** from TickStockPL library

**Total Effort**: 20-30 hours for complete pattern library
**Priority**: Medium (comprehensive pattern coverage)

---

### Sprint 70 Completed Items ✅

### ✅ Essential Technical Indicators (COMPLETE)
**Context**: Sprint 70 completed all 5 essential indicators, extending indicator library from 3 to 8 indicators.

- ✅ **EMA (Exponential Moving Average)** - Trend indicator (16 tests, 1.5h)
- ✅ **ATR (Average True Range)** - Volatility indicator (18 tests, 1.5h)
- ✅ **Bollinger Bands** - Volatility indicator (20 tests, 2h)
- ✅ **Stochastic Oscillator** - Momentum indicator (22 tests, 1.5h)
- ✅ **ADX (Average Directional Index)** - Trend strength indicator (20 tests, 2h)

**Actual Effort**: 8.5 hours (35% faster than 8-13h estimate)
**Status**: Indicator library now production-ready with 8 indicators, 145 tests
**Balanced**: 8 patterns (Sprint 68+69) + 8 indicators (Sprint 68+70)

---

## Sprint 71 Completed Items ✅

### ✅ REST API Endpoints (COMPLETE)
**Context**: Sprint 71 completed comprehensive REST API layer exposing analysis capabilities for external integrations.

#### ✅ Analysis Endpoints (3 endpoints)
- ✅ **POST /api/analysis/symbol** - Single symbol analysis
  - Indicators + patterns + metadata
  - Pydantic v2 validation
  - Response: <100ms (actual ~30ms mocked)
  - 3 tests passing

- ✅ **POST /api/analysis/universe** - Batch universe analysis
  - RelationshipCache integration for symbol loading
  - Summary statistics + individual results
  - Response: <500ms for 100 symbols (actual ~50ms mocked)
  - 2 tests passing

- ✅ **POST /api/analysis/validate-data** - OHLCV data validation
  - CSV/JSON format support
  - OHLC consistency checks, NaN detection
  - Response: <50ms (actual ~20ms)
  - 3 tests passing

- ✅ **GET /api/analysis/health** - Health check
  - 1 test passing

#### ✅ Discovery Endpoints (3 endpoints)
- ✅ **GET /api/indicators/available** - List 8 indicators by category
  - Categories: trend, momentum, volatility, volume, directional
  - Response: <10ms (actual ~5ms)
  - 3 tests passing

- ✅ **GET /api/patterns/available** - List 8 patterns by type
  - Categories: candlestick, daily, combo
  - Response: <10ms (actual ~5ms)
  - 3 tests passing

- ✅ **GET /api/analysis/capabilities** - System metadata
  - Version, indicator/pattern counts, performance stats
  - Supported timeframes: daily, weekly, hourly, intraday, monthly, 1min
  - Response: <15ms (actual ~8ms)
  - 2 tests passing

- ✅ **GET /api/discovery/health** - Discovery health check
  - 1 test passing

**Actual Effort**: ~6 hours
**Test Coverage**: 18/18 tests passing (100%)
**Architecture**:
- Pydantic v2 models (10 models, 265 lines)
- Service layer (3 files, 470 lines): AnalysisService, PatternDetectionService, IndicatorLoader
- Flask blueprints (2 blueprints, 512 lines): analysis_bp, discovery_bp
**Status**: API layer production-ready, foundation for external integrations

**Future Enhancements** (Post-Sprint 71):
- [ ] Database integration (replace mock OHLCV with TimescaleDB)
- [ ] JWT authentication middleware
- [ ] Rate limiting (Flask-Limiter)
- [ ] OpenAPI/Swagger documentation generation
- [ ] API versioning (/api/v1/ prefix)
- [ ] WebSocket streaming for real-time analysis results
- [ ] Caching layer (Redis for repeated requests)

---

### Priority: Medium - Additional Indicator Library Extension
**Context**: Sprint 68/70 implemented 8 core indicators. 7+ additional indicators from TickStockPL available for future enhancement.

#### 1. Volume & Price Indicators
- [ ] **OBV (On-Balance Volume)** - Volume-based trend indicator
- [ ] **Volume SMA** - Volume trend analysis
- [ ] **Relative Volume** - Volume comparison to average
- [ ] **VWAP (Volume Weighted Average Price)** - Institutional benchmark
- [ ] **Momentum** - Rate of price change
- [ ] **ROC (Rate of Change)** - Percentage price change
- [ ] **Williams %R** - Momentum oscillator (overbought/oversold)

**Total Effort**: 7-14 hours for 7 volume/price indicators
**Priority**: Medium (comprehensive technical analysis)

---

### Priority: Medium - Background Job Integration
**Context**: Analysis service ready for async processing but not yet integrated with Redis job queue.

#### 1. Job Queue Integration
- [ ] **Universe Analysis Jobs** - Async batch processing
  - Integrate with Redis `tickstock.jobs.analysis` channel
  - Job status tracking (queued, running, completed, failed)
  - Result caching with TTL
  - Progress updates via WebSocket
  - Effort: 3-4 hours

- [ ] **Scheduled Analysis Jobs** - Periodic batch analysis
  - Daily EOD analysis for configured universes
  - Weekly/monthly analysis for long-term trends
  - Job scheduling via Redis or Celery
  - Effort: 2-3 hours

- [ ] **Job Notification System** - Completion alerts
  - WebSocket notifications for job completion
  - Email notifications (optional)
  - Result retrieval endpoints
  - Effort: 1-2 hours

**Total Effort**: 6-9 hours for complete job integration
**Priority**: Medium (required for production universe analysis)

---

### Priority: Low - Performance Optimization
**Context**: Current performance meets targets (pattern <10ms, indicator <10ms, complete analysis <50ms) but can be improved for large-scale operations.

#### 1. Parallel Processing
- [ ] **Multiprocessing for Pattern Detection** - Parallel pattern analysis
  - Use multiprocessing.Pool for independent pattern detection
  - Expected: 2-3x speedup for 10+ patterns
  - Effort: 2-3 hours (implementation + benchmarking)

- [ ] **Async Indicator Calculation** - Concurrent indicator processing
  - asyncio for I/O-bound operations (database queries)
  - Expected: 30-50% speedup for batch operations
  - Effort: 3-4 hours (async refactoring)

#### 2. Caching Optimization
- [ ] **Indicator Result Caching** - TTL-based result cache
  - Redis cache for indicator results (5-minute TTL)
  - Cache key: symbol + timeframe + indicator + params hash
  - Expected: 90%+ cache hit rate for repeated queries
  - Effort: 2-3 hours

- [ ] **DataFrame Pre-validation Cache** - Validation result cache
  - Cache validation results to avoid repeated OHLC checks
  - Expected: 20-30% speedup for repeated data validation
  - Effort: 1-2 hours

#### 3. API Optimization
- [ ] **Streaming Batch Responses** - Server-Sent Events for large results
  - Stream analysis results as they complete
  - Reduce perceived latency for batch operations
  - Effort: 2-3 hours

**Total Effort**: 10-15 hours for complete optimization
**Priority**: Low (current performance acceptable for production)

---

## Sprint 55 Deferred Items

### Priority: Medium - Admin Workflow Enhancements
**Context**: Sprint 55 implemented ETF Universe Integration with optional future enhancements deferred

#### 1. CacheControl Refresh API
- [ ] **Create refresh endpoint** for cache_entries reload without app restart
  - Endpoint: `POST /admin/cache/refresh`
  - Reloads CacheControl singleton from database
  - Returns count of universes refreshed
  - Enables dynamic universe management

**Implementation**:
```python
@app.route('/admin/cache/refresh', methods=['POST'])
@login_required
@admin_required
def refresh_cache():
    from src.infrastructure.cache.cache_control import CacheControl
    cache_control = CacheControl()
    cache_control.load_settings_from_db()
    return jsonify({'success': True, 'message': 'Cache refreshed'})
```

#### 2. Database Triggers for Data Quality
- [ ] **Create updated_at trigger** to auto-set timestamp on INSERT/UPDATE
  ```sql
  CREATE OR REPLACE FUNCTION update_updated_at_column()
  RETURNS TRIGGER AS $$
  BEGIN
      NEW.updated_at = NOW();
      RETURN NEW;
  END;
  $$ language 'plpgsql';

  CREATE TRIGGER update_cache_entries_updated_at
  BEFORE INSERT OR UPDATE ON cache_entries
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  ```

- [ ] **Add naming validation constraint** for Title Case enforcement
  ```sql
  ALTER TABLE cache_entries
  ADD CONSTRAINT name_title_case_check
  CHECK (name ~ '^[A-Z]');
  ```

#### 3. Real-Time Progress Updates
- [ ] **Replace HTTP polling with WebSocket** for universe load progress
  - Emit progress events via `tickstock.jobs.progress` channel
  - Update frontend to listen for WebSocket events
  - Remove 1-second polling interval
  - Expected: <50ms latency for progress updates

#### 4. Universe Management UI
- [ ] **Create CRUD interface** for universe management
  - List all universes with edit/delete actions
  - Add new universe form with symbol picker
  - Inline editing for symbol lists
  - Bulk universe operations
  - Symbol validation against available tickers

**Effort**: 3-4 hours total
**Priority**: Low (current manual management sufficient)

---

## Enhanced Error Logging Integration (Sprint 32 Follow-up)

### Priority: High - Quick Wins
**Context**: Sprint 32 enhanced error handling is fully operational but not yet integrated into critical code paths

#### 1. Add Enhanced Logging to Critical System Components
- [ ] **Redis Event Subscriber** (`src/core/services/redis_event_subscriber.py`)
  - Add enhanced logging for Redis connection failures
  - Track subscription drops and reconnection attempts
  - Log pattern event processing errors with context

- [ ] **WebSocket Publisher** (`src/presentation/websocket/publisher.py`)
  - Log client disconnections with session duration
  - Track WebSocket broadcast failures
  - Monitor room join/leave events for debugging

- [ ] **Massive Client** (`src/presentation/websocket/massive_client.py`)
  - Enhanced logging for market data feed interruptions
  - Track symbols affected by connection issues
  - Log authentication failures and retry attempts

- [ ] **Database Connection Pool** (`src/infrastructure/database/connection_pool.py`)
  - Critical logging for connection pool exhaustion
  - Track connection timeout events
  - Log transaction rollback reasons

- [ ] **Pattern Detection Service** (`src/core/services/pattern_detection_service.py`)
  - Log pattern detection failures with symbol context
  - Track performance violations (>100ms processing)
  - Enhanced logging for data quality issues

**Implementation Pattern**:
```python
# Add alongside existing error handling
enhanced_logger = get_enhanced_logger()
if enhanced_logger:
    enhanced_logger.log_error(
        severity='error',
        message=f"Specific error: {e}",
        category='appropriate_category',
        component=self.__class__.__name__,
        context={'relevant': 'context'}
    )
```

### Priority: Medium - System-Wide Enhancement
**Effort**: 1 hour

#### 2. Implement Global Database Error Handler
- [ ] Add `DatabaseLogHandler` to app.py for automatic database logging
- [ ] Configure to capture all ERROR and CRITICAL level logs
- [ ] Add environment variable to enable/disable: `AUTO_DB_LOGGING=true`
- [ ] Test performance impact with high error rates

**Implementation**:
```python
# Add to app.py after enhanced logger initialization
if config.get('AUTO_DB_LOGGING').lower() == 'true':
    class DatabaseLogHandler(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.ERROR:
                enhanced_logger = get_enhanced_logger()
                if enhanced_logger:
                    enhanced_logger.log_error(
                        severity=record.levelname.lower(),
                        message=record.getMessage(),
                        category='auto',
                        component=record.name,
                        context={'auto_captured': True}
                    )

    logging.getLogger().addHandler(DatabaseLogHandler())
    logger.info("Automatic database error logging enabled")
```

### Priority: Low - Monitoring & Analytics
**Effort**: 2-3 hours

#### 3. Error Analytics Dashboard
- [ ] Create admin dashboard page for error log viewing
- [ ] Add error trend charts (errors over time by component)
- [ ] Implement error search and filtering
- [ ] Add export functionality for error reports
- [ ] Create alert rules for critical error patterns

#### 4. Error Monitoring Automation
- [ ] Implement error rate alerting (>X errors/minute)
- [ ] Add component health scoring based on error rates
- [ ] Create daily error summary reports
- [ ] Implement error pattern detection (repeated errors)
- [ ] Add Slack/email notifications for critical errors

## Technical Debt

### Database Optimization
- [ ] Add partitioning to error_logs table for better performance
- [ ] Implement automatic old error log cleanup (>30 days)
- [ ] Create materialized views for error statistics
- [ ] Optimize indexes based on query patterns

### Code Quality
- [ ] Add type hints to enhanced logger methods
- [ ] Create error handling best practices documentation
- [ ] Add performance benchmarks for error logging paths
- [ ] Implement error sampling for high-frequency events

## Future Enhancements

### Cross-System Error Correlation
- [ ] Link TickStockPL and TickStockAppV2 errors by flow_id
- [ ] Create unified error timeline view
- [ ] Implement root cause analysis tools
- [ ] Add error impact assessment (affected users/symbols)

### Advanced Error Features
- [ ] Machine learning for error pattern detection
- [ ] Predictive alerting based on error trends
- [ ] Auto-remediation for known error patterns
- [ ] Error deduplication and grouping

### Integration Extensions
- [ ] Integrate with external monitoring tools (Datadog, New Relic)
- [ ] Add OpenTelemetry support
- [ ] Implement distributed tracing
- [ ] Create error replay functionality for debugging

## Quick Tasks (< 30 minutes each)

1. [ ] Add enhanced logging to app startup sequence
2. [ ] Log configuration validation errors to database
3. [ ] Add enhanced logging to user authentication failures
4. [ ] Track WebSocket message processing errors
5. [ ] Log Redis pub/sub message parsing failures
6. [ ] Add context to existing database query timeouts
7. [ ] Enhanced logging for file I/O operations
8. [ ] Track API rate limit violations
9. [ ] Log cache miss reasons with context
10. [ ] Add performance timing to critical paths

## Notes

### Why These Enhancements Matter
1. **Critical Area Logging**: The identified components are the most likely failure points in production
2. **Global Handler**: Would provide instant visibility into all errors without code changes
3. **Analytics**: Would help identify patterns and prevent future issues
4. **Cross-System**: TickStockPL integration provides unique opportunity for unified monitoring

### Implementation Priority
1. Start with critical components (Redis, WebSocket, Database)
2. Monitor for a week to establish baseline
3. Implement global handler if error volume justifies it
4. Build analytics once sufficient data collected

### Success Metrics
- Reduce mean time to error detection by 50%
- Capture 100% of critical system errors in database
- Achieve <2ms overhead for enhanced logging
- Enable root cause analysis for 90% of production issues