# TickStockAppV2 Phase 2 Integration Guide: Data Import Pipeline

## Overview

Phase 2 extends the daily processing infrastructure with actual data import capabilities from Massive API. This phase introduces the complete data pipeline for fetching and storing OHLCV data.

## New Components

### 1. Daily Import Job (`src/jobs/daily_import_job.py`)
Orchestrates the complete data import process for all configured symbols.

### 2. Universe Manager (`src/data/universe_manager.py`)
Manages symbol lists from multiple sources (database, CSV, predefined).

### 3. Enhanced Massive Fetcher (`src/data/massive_fetcher_enhanced.py`)
Handles Massive API interactions with rate limiting and retry logic.

### 4. OHLCV Storage Service (`src/data/ohlcv_storage_service.py`)
Efficient batch storage of market data using PostgreSQL.

### 5. Job Progress Tracker (`src/jobs/job_progress_tracker.py`)
Real-time progress tracking and estimation for long-running jobs.

## Redis Events - Phase 2 Additions

### Job Progress Updates

**Channel**: `tickstock:monitoring`

**Event**: `job_progress_update`
```json
{
  "event": "job_progress_update",
  "timestamp": "2025-01-20T16:15:00Z",
  "source": "job_progress_tracker",
  "version": "1.0",
  "payload": {
    "run_id": "uuid-here",
    "phase": "data_import",
    "total_symbols": 505,
    "completed": 250,
    "failed": 5,
    "processed": 255,
    "remaining": 250,
    "percentage": 50.49,
    "current_symbol": "MSFT",
    "estimated_completion": "2025-01-20T16:25:00Z",
    "avg_processing_time_ms": 120
  }
}
```

### Symbol Processing Events

**Event**: `symbol_processing_complete`
```json
{
  "event": "symbol_processing_complete",
  "timestamp": "2025-01-20T16:15:30Z",
  "source": "daily_import_job",
  "version": "1.0",
  "payload": {
    "run_id": "uuid-here",
    "symbol": "AAPL",
    "success": true,
    "timeframes_processed": ["hourly", "daily", "weekly", "monthly"],
    "records_imported": 365,
    "processing_time_ms": 150
  }
}
```

### Data Import Phase Events

**Event**: `data_import_started`
```json
{
  "event": "data_import_started",
  "timestamp": "2025-01-20T16:10:00Z",
  "source": "daily_import_job",
  "version": "1.0",
  "payload": {
    "run_id": "uuid-here",
    "universe_names": ["sp500"],
    "total_symbols": 505,
    "timeframes": ["hourly", "daily", "weekly", "monthly"],
    "lookback_days": {
      "hourly": 90,
      "daily": 365,
      "weekly": 730,
      "monthly": 1825
    }
  }
}
```

**Event**: `data_import_completed`
```json
{
  "event": "data_import_completed",
  "timestamp": "2025-01-20T16:45:00Z",
  "source": "daily_import_job",
  "version": "1.0",
  "payload": {
    "run_id": "uuid-here",
    "duration_seconds": 2100,
    "total_symbols": 505,
    "successful_symbols": 500,
    "failed_symbols": 5,
    "total_records_imported": 183250,
    "success_rate": 99.0
  }
}
```

## Database Updates

### Processing Progress Table
The `processing_progress` table is actively used to track import progress:
```sql
-- Query current import status
SELECT
    phase,
    total_items,
    completed_items,
    failed_items,
    percent_complete,
    current_item,
    estimated_completion
FROM processing_progress
WHERE run_id = 'current-run-id'
  AND phase = 'data_import';
```

### Symbol Processing Status
Track individual symbol processing:
```sql
-- Get failed symbols for retry
SELECT
    symbol,
    error_message,
    retry_count
FROM symbol_processing_status
WHERE run_id = 'current-run-id'
  AND phase = 'data_import'
  AND status = 'failed'
ORDER BY retry_count ASC;
```

## Configuration Requirements

### Add to TickStockAppV2 Configuration

```yaml
# Data Import Settings
data_import:
  polygon:
    api_key: "YOUR_MASSIVE_API_KEY"  # Required for market data
    rate_limit_ms: 12  # Respect API rate limits
    batch_size: 100
    timeout_seconds: 30

  storage:
    batch_size: 1000  # Records per batch insert
    use_copy: true  # Use COPY for performance

  universes:
    - sp500  # Default universe to process
    # - nasdaq100  # Additional universes

  lookback:
    hourly_days: 90
    daily_days: 365
    weekly_days: 730
    monthly_days: 1825

  processing:
    parallel_workers: 10
    continue_on_error: true
    success_threshold: 80  # Minimum % for success
```

## Integration Steps for TickStockAppV2

### 1. Subscribe to Progress Updates

```python
# Subscribe to job progress
def handle_job_progress(message):
    data = json.loads(message['data'])
    if data['event'] == 'job_progress_update':
        payload = data['payload']
        # Update UI with progress
        update_progress_bar(
            payload['percentage'],
            payload['current_symbol'],
            payload['estimated_completion']
        )

pubsub.subscribe('tickstock:monitoring')
```

### 2. Monitor Data Import Phase

```python
# Track data import completion
def handle_import_events(message):
    data = json.loads(message['data'])

    if data['event'] == 'data_import_started':
        # Show import starting UI
        show_import_notification("Data import started", data['payload'])

    elif data['event'] == 'data_import_completed':
        payload = data['payload']
        # Show completion with stats
        show_completion_dialog(
            f"Import completed: {payload['successful_symbols']}/{payload['total_symbols']} symbols",
            f"Records imported: {payload['total_records_imported']}",
            f"Success rate: {payload['success_rate']:.1f}%"
        )
```

### 3. Handle Failed Symbols

```python
# Query failed symbols from database
def get_failed_symbols(run_id):
    query = """
        SELECT symbol, error_message
        FROM symbol_processing_status
        WHERE run_id = %s
          AND phase = 'data_import'
          AND status = 'failed'
    """
    return execute_query(query, (run_id,))

# Display failures to user
failed = get_failed_symbols(current_run_id)
if failed:
    show_warning(f"{len(failed)} symbols failed to import")
```

### 4. Real-time Progress Display

```python
class ImportProgressWidget:
    def __init__(self):
        self.subscribe_to_progress()

    def handle_progress_update(self, data):
        payload = data['payload']

        # Update progress bar
        self.progress_bar.set_value(payload['percentage'])

        # Update current symbol
        self.current_symbol_label.set_text(
            f"Processing: {payload['current_symbol']}"
        )

        # Update stats
        self.stats_label.set_text(
            f"Completed: {payload['completed']} | "
            f"Failed: {payload['failed']} | "
            f"Remaining: {payload['remaining']}"
        )

        # Update ETA
        if 'estimated_completion' in payload:
            eta = parse_datetime(payload['estimated_completion'])
            self.eta_label.set_text(f"ETA: {eta.strftime('%I:%M %p')}")
```

## API Endpoints for Manual Control

### Trigger Manual Import
```http
POST /api/processing/import/trigger
Content-Type: application/json

{
  "universes": ["sp500", "dow30"],
  "timeframes": ["daily", "weekly"],
  "lookback_days": 30
}

Response:
{
  "success": true,
  "run_id": "uuid-here",
  "message": "Import job started",
  "estimated_duration_minutes": 35
}
```

### Get Import Status
```http
GET /api/processing/import/status/{run_id}

Response:
{
  "run_id": "uuid-here",
  "status": "in_progress",
  "phase": "data_import",
  "progress": {
    "percentage": 45.5,
    "symbols_completed": 230,
    "symbols_total": 505,
    "current_symbol": "GOOGL",
    "estimated_completion": "2025-01-20T16:45:00Z"
  },
  "stats": {
    "records_imported": 83950,
    "failed_symbols": ["SYMBOL1", "SYMBOL2"],
    "avg_symbol_time_ms": 145
  }
}
```

### Retry Failed Symbols
```http
POST /api/processing/import/retry
Content-Type: application/json

{
  "run_id": "uuid-here",
  "symbols": ["SYMBOL1", "SYMBOL2"]  // Optional, retries all failed if not specified
}

Response:
{
  "success": true,
  "retry_count": 2,
  "message": "Retry initiated for 2 symbols"
}
```

## Error Handling

### Import Errors
Monitor the `tickstock:errors` channel for import failures:

```json
{
  "event": "critical_error",
  "timestamp": "2025-01-20T16:20:00Z",
  "source": "daily_import_job",
  "version": "1.0",
  "payload": {
    "severity": "error",
    "component": "massive_fetcher",
    "error_code": "API_RATE_LIMIT",
    "message": "Rate limit exceeded, backing off",
    "context": {
      "symbol": "AAPL",
      "retry_after": 60
    },
    "recovery_action": "automatic_retry"
  }
}
```

### Common Error Codes

| Code | Description | Recovery |
|------|-------------|----------|
| `API_RATE_LIMIT` | Massive API rate limit hit | Automatic backoff and retry |
| `API_KEY_INVALID` | Invalid Massive API key | Manual configuration required |
| `SYMBOL_NOT_FOUND` | Symbol not available in Massive | Skip and continue |
| `STORAGE_FAILED` | Database storage error | Retry or manual intervention |
| `NETWORK_TIMEOUT` | Request timeout | Automatic retry |

## Performance Metrics

### Expected Performance
- **Symbols per minute**: 15-20 (with rate limiting)
- **Total import time**: 25-35 minutes for S&P 500
- **Memory usage**: < 500MB during import
- **Database writes**: Batched at 1000 records
- **Network bandwidth**: ~10-20 MB total

### Monitoring Queries

```sql
-- Import performance by timeframe
SELECT
    phase,
    COUNT(DISTINCT symbol) as symbols_processed,
    AVG(processing_time_ms) as avg_time_ms,
    MAX(processing_time_ms) as max_time_ms
FROM symbol_processing_status
WHERE run_id = 'current-run-id'
GROUP BY phase;

-- Data coverage check
SELECT
    COUNT(DISTINCT symbol) as unique_symbols,
    COUNT(*) as total_records,
    MIN(date) as earliest_date,
    MAX(date) as latest_date
FROM ohlcv_daily
WHERE created_at > NOW() - INTERVAL '1 hour';
```

## Testing Phase 2

Run the Phase 2 test suite:
```bash
python test_phase2.py
```

This validates:
- Universe manager functionality
- Massive API integration
- OHLCV storage operations
- Progress tracking
- Job execution
- Scheduler integration

## Next Steps (Phase 3)

After Phase 2 is integrated and tested:

1. **Phase 3**: Daily Indicator Processing
   - Calculate technical indicators on imported data
   - Store indicator values in database
   - Publish indicator completion events

2. **Phase 4**: Daily Pattern Detection
   - Run pattern detection on OHLCV + indicators
   - Store detected patterns
   - Generate pattern alerts

Continue monitoring the Redis channels and database tables as documented above for real-time updates and system status.