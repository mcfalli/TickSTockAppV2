# Massive API Per-Minute Aggregates Implementation

**Status**: ✅ Implemented (November 25, 2025)
**Sprint**: 54 - WebSocket Simplification
**Impact**: 98.6% reduction in database writes (60x improvement)

## Overview

TickStockAppV2 now subscribes to Massive API's **per-minute aggregates** (AM events) instead of per-second aggregates (A events), dramatically reducing database write frequency while maintaining data quality.

## Key Changes

### Subscription Format
```python
# Before (Per-Second):
formatted_tickers = [f"A.{ticker}" for ticker in tickers]  # A.AAPL, A.SPY, etc.

# After (Per-Minute):
formatted_tickers = [f"AM.{ticker}" for ticker in tickers]  # AM.AAPL, AM.SPY, etc.
```

### Event Types Handled
```python
# Event routing in _process_message (line 238):
elif msg.get('ev') in ['A', 'AM', 'T', 'Q']:  # Accepts both A and AM events
    self._process_tick_event(msg)

# Event processing in _process_tick_event (line 248):
if event_type in ('A', 'AM'):  # Per-second or per-minute aggregates
    self._process_aggregate_event(event)
```

## Performance Impact

### Database Write Frequency

| Metric | Per-Second (Old) | Per-Minute (New) | Improvement |
|--------|------------------|------------------|-------------|
| **Tickers** | 70 | 70 | - |
| **Write Frequency** | Every second | Every minute | 60x reduction |
| **Writes/Minute** | ~4,200 | ~70 | **98.6% reduction** |
| **Writes/Hour** | ~252,000 | ~4,200 | 60x reduction |
| **Writes/Day (6.5 hrs)** | ~1,638,000 | ~27,300 | 60x reduction |

### Data Characteristics

**Timestamp Precision**:
- All timestamps aligned to minute boundaries (`:00` seconds)
- Example: `2025-11-25T20:55:00.000Z`

**Bar Emission**:
- Bars arrive at the start of each minute (e.g., 14:50:00, 14:51:00, 14:52:00)
- Only emitted when qualifying trades occur during that minute
- No gaps - Massive API handles all edge cases

**Data Quality**:
- Complete OHLCV data maintained
- Volume aggregated across the full minute
- VWAP and average price included

## Event Format

### Per-Minute Aggregate Event
```json
{
  "ev": "AM",           // Event type: AM = per-minute aggregate
  "sym": "AAPL",        // Symbol
  "s": 1700000000000,   // Start timestamp (milliseconds)
  "e": 1700000060000,   // End timestamp (milliseconds)
  "o": 277.50,          // Open price
  "h": 277.85,          // High price
  "l": 277.45,          // Low price
  "c": 277.70,          // Close price
  "v": 91293,           // Volume
  "vw": 277.65,         // Volume-weighted average price
  "a": 277.60           // Average price
}
```

## Implementation Files

### Core Changes
- **`src/presentation/websocket/massive_client.py`**
  - Line 139: Subscription format `AM.{ticker}`
  - Line 167: Unsubscription format `AM.{ticker}`
  - Line 238: Event routing to include `'AM'`
  - Line 248: Event handler accepts `('A', 'AM')`
  - Line 222: Subscription confirmation parsing for both A and AM

### Testing
- **`scripts/dev_tools/test_am_minimal.py`**: Standalone diagnostic test
  - Confirms AM subscription works
  - Logs all message reception
  - Validates per-minute bar timing

## Configuration

No configuration changes required. The system automatically uses per-minute aggregates with existing settings:

```bash
# .env (unchanged)
USE_MASSIVE_API=true
MASSIVE_API_KEY=your_api_key_here
SYMBOL_UNIVERSE_KEY=market_leaders:top_100
```

## Database Schema

Uses existing `ohlcv_1min` table - no schema changes required:

```sql
CREATE TABLE ohlcv_1min (
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open NUMERIC(12,4),
    high NUMERIC(12,4),
    low NUMERIC(12,4),
    close NUMERIC(12,4),
    volume BIGINT,
    PRIMARY KEY (symbol, timestamp)
);
```

## Verification

### Check Data in Database
```sql
-- Verify per-minute spacing
SELECT
    symbol,
    timestamp,
    EXTRACT(SECOND FROM timestamp) as seconds,  -- Should always be 0
    close,
    volume
FROM ohlcv_1min
WHERE symbol = 'SPY'
AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

### Expected Results
- Timestamps end in `:00.000` (minute boundary)
- Gaps of exactly 1 minute between records (during market hours)
- Volume aggregated across full minute

## Troubleshooting

### No Data Arriving

**Symptom**: No database writes after several minutes

**Diagnosis**:
1. Check logs for "Message received" entries
2. Verify subscription confirmations: `grep "subscribed to: AM" logs/*.log`
3. Confirm event routing: `grep "AM BAR\|Processed tick" logs/*.log`

**Common Issues**:
- Event type not in routing list (line 238)
- Markets closed (per-minute bars only during trading hours)
- API key permissions (verify AM aggregate access)

### Run Diagnostic Test
```bash
python scripts/dev_tools/test_am_minimal.py
```

Expected output:
- Authentication success
- 3 subscription confirmations (SPY, AAPL, NVDA)
- AM bars received at minute boundaries
- Results logged to `scripts/dev_tools/test_am_output.txt`

## Migration Notes

### Backward Compatibility
The implementation maintains backward compatibility:
- Can handle both `'A'` and `'AM'` events
- Subscription confirmation parsing supports both formats
- No breaking changes to downstream consumers

### Rollback Procedure
To revert to per-second aggregates:

```python
# In src/presentation/websocket/massive_client.py

# Line 139:
formatted_tickers = [f"A.{ticker}" for ticker in new_tickers]

# Line 167:
formatted_tickers = [f"A.{ticker}" for ticker in existing_tickers]
```

Event handler (line 238) can remain unchanged as it accepts both types.

## Benefits

1. **Database Performance**: 60x reduction in write operations
2. **Storage Efficiency**: Smaller database footprint over time
3. **Network Efficiency**: Fewer messages to process
4. **Data Quality**: Same OHLCV accuracy with better aggregation
5. **Cost Reduction**: Lower database I/O costs
6. **Scalability**: Can monitor more tickers with same resources

## API Documentation

- **Massive API Docs**: https://massive.com/docs/websocket/stocks/aggregates-per-minute
- **Subscription Format**: `{"action": "subscribe", "params": "AM.AAPL,AM.SPY"}`
- **Event Type**: `ev: "AM"`
- **License Requirement**: Stocks Advanced (all tiers support per-minute)

## Commit History

1. **feat: Switch to per-minute aggregates** (6f15c5e)
   - Initial subscription format change
   - Event handler update to accept 'AM'

2. **debug: Add message logging and fix parsing** (46d0bf0)
   - Debug logging for message reception
   - Subscription confirmation parsing fix

3. **fix: Add 'AM' to event routing** (7811f25)
   - Critical fix: Added 'AM' to event routing list
   - Resolved silent message dropping issue

## Related Documentation

- [WebSocket Integration Guide](./websockets-integration.md)
- [Database Architecture](../database/database-architecture.md)
- [Massive API Configuration](./configuration.md)
