# TickStockAppV2 Quick Reference - Phase 1

## Redis Channels (NEW)
```
tickstock:processing:status    # Processing events
tickstock:processing:schedule  # Schedule changes
```

## Key Events to Handle

### 1. Processing Started
```json
{
  "event": "daily_processing_started",
  "payload": {
    "run_id": "uuid",
    "symbols_count": 505,
    "trigger_type": "automatic|manual"
  }
}
```
**Action**: Show processing indicator, initialize progress bar

### 2. Processing Progress
```json
{
  "event": "daily_processing_progress",
  "payload": {
    "run_id": "uuid",
    "phase": "data_import",
    "percent_complete": 50.0,
    "current_symbol": "AAPL"
  }
}
```
**Action**: Update progress bar, show current phase

### 3. Processing Completed
```json
{
  "event": "daily_processing_completed",
  "payload": {
    "status": "success|failed",
    "duration_seconds": 1800,
    "symbols_processed": 505
  }
}
```
**Action**: Show completion notification, clear progress

## API Endpoints

### Get Status
```
GET /api/processing/daily/status
```

### Trigger Manual Run (Admin)
```
POST /api/processing/daily/trigger
Headers: X-API-Key: {api_key}
Body: {"skip_market_check": false}
```

### Get History
```
GET /api/processing/daily/history?days=7
```

### Get Market Status
```
GET /api/processing/market/status
```

## Quick Test

```bash
# Monitor all processing events
redis-cli PSUBSCRIBE "tickstock:processing:*"

# Trigger test event
redis-cli PUBLISH tickstock:processing:status '{"event":"test"}'
```

## UI Checklist

- [ ] Progress bar component
- [ ] Processing status indicator
- [ ] Manual trigger button (admin only)
- [ ] Next run time display
- [ ] Error notifications
- [ ] History table

## Error Severity Levels

- **critical**: System failure, immediate attention
- **error**: Processing failure, needs review
- **warning**: Non-critical issue
- **info**: Informational only

## Support

- Full Guide: `TickStockAppV2_Phase1_Integration_Guide.md`
- Test Script: `tests/integration/processing/test_phase1_components.py`
- Redis Protocol: `docs/api/redis_protocol.md`