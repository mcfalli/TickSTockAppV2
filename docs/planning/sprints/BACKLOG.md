# TickStockAppV2 Product Backlog

**Last Updated**: 2025-11-27
**Purpose**: Track future enhancements, technical debt, and feature requests

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