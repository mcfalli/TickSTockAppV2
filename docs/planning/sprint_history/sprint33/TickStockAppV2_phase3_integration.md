# TickStockAppV2 Integration - Phase 3: Daily Indicator Processing

**Sprint**: 33 (Phase 3)
**Date**: 2025-01-25
**Component**: Daily Indicator Processing Engine

## Overview

Phase 3 implements the daily technical indicator calculation engine that processes all enabled indicators from the database using the dynamic loading architecture from Sprint 27-31.

## Architecture

```
Daily Processing Pipeline:
4:10 PM ET Trigger
    ├── Phase 1: Schedule & Monitor (Active)
    ├── Phase 2: Data Import (Complete)
    ├── Phase 2.5: Cache Sync (Complete)
    ├── Phase 3: Indicator Processing (NEW) ← We are here
    └── Phase 4: Pattern Detection (Pending)
```

## Redis Events for TickStockAppV2

### 1. Indicator Processing Started

**Channel**: `tickstock:indicators:started`

```json
{
    "event": "indicator_processing_started",
    "timestamp": "2025-01-25T21:10:00Z",
    "source": "daily_indicator_job",
    "version": "1.0",
    "payload": {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "total_symbols": 505,
        "total_indicators": 15,
        "timeframes": ["daily", "weekly", "monthly"]
    }
}
```

### 2. Indicator Progress Update

**Channel**: `tickstock:indicators:progress`

```json
{
    "event": "indicator_progress",
    "timestamp": "2025-01-25T21:15:00Z",
    "source": "daily_indicator_job",
    "version": "1.0",
    "payload": {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "completed_symbols": 250,
        "total_symbols": 505,
        "percent_complete": 49.5,
        "current_symbol": "GOOGL",
        "eta_seconds": 300
    }
}
```

### 3. Indicator Processing Completed

**Channel**: `tickstock:indicators:completed`

```json
{
    "event": "indicator_processing_completed",
    "timestamp": "2025-01-25T21:25:00Z",
    "source": "daily_indicator_job",
    "version": "1.0",
    "payload": {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "total_symbols": 505,
        "successful_symbols": 500,
        "failed_symbols": 5,
        "total_indicators": 7575,  // 505 symbols × 15 indicators
        "successful_indicators": 7500,
        "failed_indicators": 75,
        "success_rate": 99.0,
        "duration_seconds": 900
    }
}
```

### 4. Individual Indicator Calculated

**Channel**: `tickstock:indicators:calculated`

```json
{
    "event": "indicator_calculated",
    "timestamp": "2025-01-25T21:15:30Z",
    "source": "indicator_calculation_engine",
    "version": "1.0",
    "payload": {
        "symbol": "AAPL",
        "indicator": "RSI",
        "timeframe": "daily",
        "values": {
            "rsi": 65.4,
            "signal": "overbought"
        },
        "metadata": {
            "period": 14,
            "data_points": 100
        }
    }
}
```

## Database Tables

### Daily Indicators Table

```sql
-- Already exists from Phase 1 migration
CREATE TABLE daily_indicators (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    indicator_name VARCHAR(100) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,
    values JSONB NOT NULL,
    metadata JSONB,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    run_id UUID,
    UNIQUE(symbol, indicator_name, timeframe, date(calculated_at))
);
```

### Sample Data Structure

```json
{
    "symbol": "AAPL",
    "indicator_name": "RSI",
    "timeframe": "daily",
    "values": {
        "rsi": 65.4,
        "rsi_ma": 60.2,
        "divergence": false
    },
    "metadata": {
        "parameters": {"period": 14},
        "lookback_days": 100,
        "data_points": 100,
        "calculation_time_ms": 25
    }
}
```

## API Endpoints (Future)

While Phase 3 runs automatically as part of the daily pipeline, these endpoints will be added for manual triggering and monitoring:

### Trigger Indicator Calculation (Coming Soon)

```
POST /api/processing/indicators/calculate
{
    "symbols": ["AAPL", "GOOGL"],  // Optional, defaults to all
    "indicators": ["RSI", "MACD"],  // Optional, defaults to all
    "timeframe": "daily"
}
```

### Get Indicator Status (Coming Soon)

```
GET /api/processing/indicators/status/{run_id}
```

## Integration Code for TickStockAppV2

### 1. Subscribe to Indicator Events

```python
# Add to your Redis subscriber in TickStockAppV2

class IndicatorEventListener:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.pubsub = self.redis.pubsub()

    def start(self):
        """Start listening for indicator events."""
        self.pubsub.subscribe([
            'tickstock:indicators:started',
            'tickstock:indicators:progress',
            'tickstock:indicators:completed',
            'tickstock:indicators:calculated'
        ])

        thread = threading.Thread(target=self._listen)
        thread.daemon = True
        thread.start()

    def _listen(self):
        """Process indicator events."""
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    event = json.loads(message['data'])
                    self._handle_event(event)
                except json.JSONDecodeError:
                    pass

    def _handle_event(self, event):
        """Route events to handlers."""
        event_type = event.get('event')

        if event_type == 'indicator_processing_started':
            self._on_indicators_started(event['payload'])
        elif event_type == 'indicator_progress':
            self._on_progress_update(event['payload'])
        elif event_type == 'indicator_processing_completed':
            self._on_indicators_completed(event['payload'])
        elif event_type == 'indicator_calculated':
            self._on_indicator_calculated(event['payload'])

    def _on_indicators_started(self, payload):
        """Handle start of indicator processing."""
        # Update UI to show processing started
        socketio.emit('indicators_started', {
            'run_id': payload['run_id'],
            'total_symbols': payload['total_symbols']
        }, namespace='/admin')

    def _on_progress_update(self, payload):
        """Handle progress updates."""
        # Update progress bar in UI
        socketio.emit('indicators_progress', {
            'percent': payload['percent_complete'],
            'current_symbol': payload['current_symbol'],
            'eta_seconds': payload['eta_seconds']
        }, namespace='/admin')

    def _on_indicators_completed(self, payload):
        """Handle completion of indicator processing."""
        # Update UI and refresh indicator data
        socketio.emit('indicators_completed', {
            'success_rate': payload['success_rate'],
            'duration': payload['duration_seconds']
        }, namespace='/admin')

        # Trigger local data refresh if needed
        self._refresh_indicator_cache()

    def _on_indicator_calculated(self, payload):
        """Handle individual indicator calculation."""
        # Update real-time displays if showing this symbol
        if self.is_symbol_displayed(payload['symbol']):
            self._update_indicator_display(payload)
```

### 2. Query Calculated Indicators

```python
# Add to your data service in TickStockAppV2

def get_latest_indicators(symbol: str, indicator_names: List[str] = None):
    """
    Fetch latest calculated indicators for a symbol.

    Args:
        symbol: Stock symbol
        indicator_names: List of indicator names (None = all)

    Returns:
        Dictionary of indicator values
    """
    query = """
        SELECT DISTINCT ON (indicator_name)
            indicator_name,
            timeframe,
            values,
            metadata,
            calculated_at
        FROM daily_indicators
        WHERE symbol = %s
        AND calculated_at >= CURRENT_DATE
        ORDER BY indicator_name, calculated_at DESC
    """

    with db.cursor() as cursor:
        cursor.execute(query, (symbol,))
        results = cursor.fetchall()

    indicators = {}
    for row in results:
        if indicator_names is None or row['indicator_name'] in indicator_names:
            indicators[row['indicator_name']] = {
                'values': row['values'],
                'metadata': row['metadata'],
                'calculated_at': row['calculated_at']
            }

    return indicators
```

### 3. Display in Admin Dashboard

```javascript
// Add to admin dashboard JavaScript

function setupIndicatorMonitoring() {
    // Listen for indicator events
    socket.on('indicators_started', function(data) {
        $('#indicator-status').text('Processing indicators...');
        $('#indicator-progress').show();
        $('#indicator-progress-bar').css('width', '0%');
    });

    socket.on('indicators_progress', function(data) {
        $('#indicator-progress-bar').css('width', data.percent + '%');
        $('#indicator-current').text('Processing: ' + data.current_symbol);

        // Update ETA
        if (data.eta_seconds > 0) {
            const minutes = Math.floor(data.eta_seconds / 60);
            const seconds = data.eta_seconds % 60;
            $('#indicator-eta').text(`ETA: ${minutes}:${seconds.toString().padStart(2, '0')}`);
        }
    });

    socket.on('indicators_completed', function(data) {
        $('#indicator-status').text(`Indicators calculated (${data.success_rate.toFixed(1)}% success)`);
        $('#indicator-progress').hide();

        // Refresh indicator displays
        refreshIndicatorTables();
    });
}

function refreshIndicatorTables() {
    // Refresh any indicator-based UI components
    $('.indicator-value').each(function() {
        const symbol = $(this).data('symbol');
        const indicator = $(this).data('indicator');

        $.get(`/api/indicators/${symbol}/${indicator}`, function(data) {
            $(this).text(data.value);
            $(this).removeClass('stale').addClass('fresh');
        });
    });
}
```

## Performance Expectations

- **Processing Time**: 10-20 minutes for 500 symbols × 15 indicators
- **Throughput**: ~10-15 indicators/second
- **Cache Hit Rate**: >90% after warm-up
- **Memory Usage**: <500MB for indicator calculations
- **Database Storage**: ~100KB per symbol per day

## Monitoring

### Key Metrics to Track

1. **Success Rate**: Should be >95%
2. **Processing Time**: Should be <30 minutes
3. **Cache Hit Rate**: Should be >90%
4. **Failed Indicators**: Should be <5%

### Alert Thresholds

```yaml
alerts:
  - name: indicator_processing_slow
    condition: duration > 1800  # 30 minutes
    severity: warning

  - name: indicator_failure_high
    condition: success_rate < 90
    severity: critical

  - name: indicator_job_failed
    condition: status == "failed"
    severity: critical
```

## Testing

To verify Phase 3 integration:

1. **Check Redis Events**:
```bash
redis-cli SUBSCRIBE "tickstock:indicators:*"
```

2. **Query Database**:
```sql
-- Check latest indicators
SELECT symbol, indicator_name, calculated_at
FROM daily_indicators
WHERE calculated_at >= CURRENT_DATE
ORDER BY calculated_at DESC
LIMIT 10;

-- Check indicator coverage
SELECT indicator_name, COUNT(DISTINCT symbol) as symbol_count
FROM daily_indicators
WHERE calculated_at >= CURRENT_DATE
GROUP BY indicator_name;
```

3. **Monitor Logs**:
```bash
tail -f /var/log/tickstockpl/indicator_processing.log
```

## Troubleshooting

### Common Issues

1. **No indicators calculated**:
   - Check if indicator definitions exist in database
   - Verify dynamic loader is working
   - Check OHLCV data availability

2. **Slow processing**:
   - Check cache hit rate
   - Verify parallel processing settings
   - Monitor database query performance

3. **High failure rate**:
   - Check individual indicator implementations
   - Verify data quality
   - Review error logs for patterns

## Next Steps

After Phase 3 is working:
1. Phase 4: Pattern Detection will follow similar architecture
2. Consider adding real-time indicator updates for streaming data
3. Implement indicator alerting based on thresholds

## Notes

- Indicators are calculated using the dynamic loading system from Sprint 27-31
- All indicator logic is stubbed currently and returns empty results
- Actual indicator calculations will be implemented in future sprints
- The infrastructure is fully ready for real calculations once logic is added

## Integration Checklist for TickStockAppV2 Developer

### Prerequisites
- [ ] Redis connection configured and working
- [ ] Database connection to tickstock database
- [ ] Access to `daily_indicators` table (SELECT permissions)
- [ ] Access to `indicator_processing_stats` table (SELECT permissions)

### Required Implementation Steps

#### 1. Redis Event Subscription
- [ ] Subscribe to `tickstock:indicators:started` channel
- [ ] Subscribe to `tickstock:indicators:progress` channel
- [ ] Subscribe to `tickstock:indicators:completed` channel
- [ ] Subscribe to `tickstock:indicators:calculated` channel (optional for real-time updates)
- [ ] Implement event handlers for each channel

#### 2. Database Integration
- [ ] Add query for fetching latest indicators by symbol
- [ ] Add query for fetching indicator statistics
- [ ] Add query for checking processing status

#### 3. Admin Dashboard Updates
- [ ] Add indicator processing status display
- [ ] Add progress bar for indicator calculations
- [ ] Add success rate display
- [ ] Add ETA display during processing

#### 4. Frontend Updates
- [ ] Update indicator display components to show latest values
- [ ] Add loading states during processing
- [ ] Add error states for failed indicators
- [ ] Implement auto-refresh after completion event

### Testing Verification

#### Redis Event Testing
```bash
# Subscribe to test events
redis-cli SUBSCRIBE "tickstock:indicators:*"

# In another terminal, trigger manual processing
curl -X POST http://localhost:8080/api/processing/trigger-manual \
  -H "Content-Type: application/json" \
  -d '{"skip_market_check": true}'
```

#### Database Query Testing
```sql
-- Verify indicators are being stored
SELECT COUNT(*) FROM daily_indicators
WHERE date(calculated_at) = CURRENT_DATE;

-- Check processing stats
SELECT * FROM indicator_processing_stats
ORDER BY created_at DESC LIMIT 5;

-- Verify phase tracking
SELECT run_id, indicator_processing_complete, indicators_calculated, indicators_failed
FROM daily_processing_runs
WHERE run_date = CURRENT_DATE;
```

### Expected Behavior

1. **At 4:10 PM ET (or manual trigger)**:
   - Receive `indicator_processing_started` event
   - UI shows "Processing indicators..." status

2. **During Processing**:
   - Receive `indicator_progress` events every 5 seconds
   - Progress bar updates with percent_complete
   - Current symbol display updates
   - ETA countdown shows remaining time

3. **After Completion**:
   - Receive `indicator_processing_completed` event
   - UI shows success rate and duration
   - Indicator values auto-refresh in display
   - Admin dashboard updates with statistics

### Configuration Required

Add to TickStockAppV2 configuration:
```python
# Redis channels for indicator events
INDICATOR_CHANNELS = {
    'started': 'tickstock:indicators:started',
    'progress': 'tickstock:indicators:progress',
    'completed': 'tickstock:indicators:completed',
    'calculated': 'tickstock:indicators:calculated'
}

# Polling interval for manual status checks (if not using Redis)
INDICATOR_STATUS_POLL_INTERVAL = 5  # seconds
```

### Success Criteria

- [ ] Events received and processed correctly
- [ ] UI updates in real-time during processing
- [ ] Indicator values displayed after completion
- [ ] No errors in console or logs
- [ ] Performance metrics displayed in admin dashboard

### Support & Debugging

**Log Locations**:
- TickStockPL: `/var/log/tickstockpl/indicator_processing.log`
- TickStockAppV2: Check your configured log location

**Common Issues**:
- If no events received: Check Redis connection and channel names
- If indicators not showing: Verify database queries and permissions
- If progress not updating: Check event handler implementation

**Contact**:
- Check TickStockPL monitoring channel: `tickstock:monitoring`
- Review error channel: `tickstock:errors`
- Database health: Check `indicator_processing_stats` table

## Status: READY FOR INTEGRATION

This document is complete and ready for TickStockAppV2 developer integration. The infrastructure is fully operational with:
- ✅ All database tables created and verified
- ✅ Redis event publishing implemented
- ✅ API endpoints functional (manual trigger available)
- ✅ Progress tracking operational
- ✅ Error handling in place
- ✅ Monitoring active