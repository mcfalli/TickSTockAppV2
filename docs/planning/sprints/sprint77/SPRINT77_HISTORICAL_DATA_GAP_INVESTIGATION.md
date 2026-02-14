# Sprint 77: Historical Data Gap Investigation - Daily vs Intraday Discrepancy

**Created**: February 14, 2026
**Priority**: High
**Type**: Bug Investigation & Fix
**Component**: TickStockPL Historical Data Loader

---

## Problem Statement

Historical import jobs are successfully populating 1-minute and hourly data through Feb 14, 2026, but daily data stops at Feb 12, 2026 - creating a **2-day gap** between intraday and daily timeframes.

### Observed Behavior (TSLA Example)

**Import Job Details**:
- **Job Triggered**: 2026-02-14 10:44:04 CT (QQQ universe import)
- **Symbol**: TSLA (included in QQQ)
- **Expected**: Daily data through Feb 14, 2026 (or at least Feb 13)
- **Actual**: Daily data stops at Feb 12, 2026

**Database State**:
```sql
-- ohlcv_1min: ✅ HAS FEB 14 DATA
SELECT symbol, MAX(timestamp) as latest, COUNT(*) as bars
FROM ohlcv_1min WHERE symbol = 'TSLA';
-- Result: Latest = 2026-02-14 01:00:00, 5,473 bars

-- ohlcv_hourly: ✅ HAS FEB 14 DATA
SELECT symbol, MAX(timestamp) as latest, COUNT(*) as bars
FROM ohlcv_hourly WHERE symbol = 'TSLA';
-- Result: Latest = 2026-02-14 00:00:00, 744 bars

-- ohlcv_daily: ❌ MISSING FEB 13-14
SELECT symbol, MAX(date) as latest, COUNT(*) as bars
FROM ohlcv_daily WHERE symbol = 'TSLA';
-- Result: Latest = 2026-02-12 06:00:00, 534 bars

-- ohlcv_weekly: Latest = 2026-02-07 (112 bars) - expected lag
-- ohlcv_monthly: Latest = 2026-01-31 (27 bars) - expected lag
```

---

## Root Cause Investigation

### 1. Architecture Context

**Historical Import Flow**:
```
User UI (TickStockAppV2)
  → POST /admin/historical-data/trigger-universe-load
    → Redis Publish: tickstock.jobs.data_load
      → TickStockPL Subscriber
        → Massive API Fetch
          → TimescaleDB Insert
```

**Key Files**:
1. **TickStockAppV2** (Job Submission Only):
   - `src/api/rest/admin_historical_data_redis.py:300-426` - Publishes job to Redis
   - `src/data/historical_loader.py` - Utility module (NOT used by universe imports)

2. **TickStockPL** (Actual Data Fetching):
   - Location: `C:\Users\McDude\TickStockPL\` (separate codebase)
   - Subscribes to `tickstock.jobs.data_load` channel
   - Calls Massive API `/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start}/{end}`
   - Inserts into TimescaleDB hypertables

### 2. Date Range Calculation Hypotheses

**Hypothesis A: TickStockPL Date Cutoff Logic**
- TickStockPL may use different `end_date` calculations per timeframe
- Possible logic: `end_date = today() - N_days` where N varies by timeframe
- Evidence: Daily stops at Feb 12 (2 days ago), intraday continues to Feb 14 (today)

**Hypothesis B: Massive API Data Availability Lag**
- Massive API publishes daily bars with 1-2 day delay
- Intraday bars (1min, hourly) available in real-time
- Evidence: Common pattern for financial APIs (daily bars finalized after market close)

**Hypothesis C: Market Calendar / Holiday Issue**
- Feb 13, 2026 might be a market holiday or weekend
- Evidence: Need to verify 2026 market calendar
- Counter-evidence: Feb 13, 2026 is a Friday (trading day unless holiday)

**Hypothesis D: Timezone Conversion Issue**
- Daily bar timestamp: `2026-02-12 06:00:00` (note 6am time)
- Possible UTC→CT conversion artifact
- Evidence: 06:00:00 timestamp unusual for daily bars (typically midnight or market open)

### 3. Investigation Tasks (TickStockPL Codebase)

**Task 1: Review TickStockPL Date Range Logic**
```python
# Expected location: TickStockPL/src/data/historical_loader.py or similar
# Find the code that sets start_date and end_date for Massive API calls
# Questions:
# - Is end_date hardcoded or dynamic (datetime.now())?
# - Is there a "safety buffer" (end_date = today - 2 days)?
# - Does date calculation differ between daily vs intraday?
```

**Task 2: Check Massive API Call Parameters**
```python
# Expected endpoint call:
# GET /v2/aggs/ticker/TSLA/range/1/day/{start_date}/{end_date}?apikey=xxx
#
# Verify:
# - What end_date value is actually sent to Massive API?
# - Are there different parameters for daily vs minute/hourly?
# - Is "adjusted=true" affecting data availability?
```

**Task 3: Test Massive API Directly**
```bash
# Manual API test to isolate TickStockPL from Massive API
curl "https://api.massive.com/v2/aggs/ticker/TSLA/range/1/day/2026-02-10/2026-02-14?adjusted=true&sort=asc&apikey=YOUR_KEY"

# Expected questions:
# - Does Massive API return Feb 13 data?
# - Does Massive API return Feb 14 data?
# - What timestamp format is returned (Unix ms, ISO string)?
```

**Task 4: Review TimescaleDB Insert Logic**
```sql
-- Check if data exists but isn't visible due to query issues
SELECT date, COUNT(*)
FROM ohlcv_daily
WHERE symbol = 'TSLA'
  AND date >= '2026-02-10'
GROUP BY date
ORDER BY date DESC;

-- Verify no duplicates or constraint violations blocking inserts
SELECT symbol, date, COUNT(*) as occurrences
FROM ohlcv_daily
WHERE symbol = 'TSLA' AND date >= '2026-02-10'
GROUP BY symbol, date
HAVING COUNT(*) > 1;
```

---

## Proposed Fix Strategies

### Strategy 1: Remove Date Cutoff (If Hypothesis A Correct)
```python
# TickStockPL/src/data/historical_loader.py (or equivalent)

# BEFORE (suspected):
end_date = datetime.now() - timedelta(days=2)  # Safety buffer for daily

# AFTER:
if timespan == 'day':
    # Use yesterday as end date (today's bar not finalized until market close)
    end_date = (datetime.now() - timedelta(days=1)).date()
else:
    # Intraday: use current time
    end_date = datetime.now()
```

### Strategy 2: Align with Massive API Availability (If Hypothesis B Correct)
```python
# Accept 1-2 day lag as normal for daily data
# Update documentation to clarify expected lag
# Add UI indicator showing latest available date per timeframe
```

### Strategy 3: Fix Timezone Handling (If Hypothesis D Correct)
```python
# Ensure consistent timezone handling across timeframes
from datetime import timezone

# Convert to market timezone (Eastern Time)
market_tz = pytz.timezone('America/New_York')
end_date = datetime.now(tz=market_tz)

# For daily bars, use market close time
if timespan == 'day':
    end_date = end_date.replace(hour=16, minute=0, second=0)
```

---

## Impact Assessment

### User Impact
- **Severity**: Medium
- **Affected Users**: Any user relying on daily OHLCV data for analysis
- **Workflow Impact**: Pattern/indicator analysis runs on daily data, missing latest 2 days

### System Impact
- **Sprint 73 Process Analysis**: Uses daily data, will miss Feb 13-14 detections
- **Sprint 76 SMA/EMA Calculations**: Values accurate but 2 days stale
- **Market Overview Dashboard**: Shows outdated daily metrics

### Data Quality Impact
```
Current State:
├─ Intraday Analysis: ✅ Real-time (Feb 14)
├─ Hourly Analysis: ✅ Real-time (Feb 14)
├─ Daily Analysis: ⚠️ 2-day lag (Feb 12)
└─ Weekly/Monthly: ✅ Expected lag (normal)
```

---

## Acceptance Criteria

1. **Root Cause Identified**:
   - [ ] TickStockPL date calculation logic reviewed
   - [ ] Massive API direct test completed
   - [ ] Hypothesis confirmed (A, B, C, or D)

2. **Fix Implemented**:
   - [ ] TickStockPL code updated (if code issue)
   - [ ] Documentation updated (if API lag expected)
   - [ ] Timezone handling standardized

3. **Validation**:
   - [ ] Run full SPY import (504 symbols)
   - [ ] Verify daily data includes yesterday's date (today - 1 day)
   - [ ] Confirm 1min/hourly/daily alignment within 1-day tolerance

4. **Regression Testing**:
   - [ ] Existing daily data not affected (Feb 12 and earlier)
   - [ ] No duplicate bars created
   - [ ] Pattern flow tests still pass

---

## Testing Plan

### Test Case 1: Single Symbol Historical Import
```bash
# Trigger import for AAPL (2 years daily + 1min + hourly)
# Expected:
# - ohlcv_daily: Latest = yesterday (2026-02-13 if run on Feb 14)
# - ohlcv_hourly: Latest = today 00:00 or latest full hour
# - ohlcv_1min: Latest = today latest minute
```

### Test Case 2: Universe Import (QQQ)
```bash
# Trigger QQQ universe import (102 symbols)
# Sample 5 random symbols
# Verify all have daily data through yesterday
```

### Test Case 3: Multi-Timeframe Consistency
```sql
-- For each symbol, verify latest dates are within tolerance:
SELECT
    symbol,
    (SELECT MAX(date) FROM ohlcv_daily WHERE symbol = s.symbol) as latest_daily,
    (SELECT MAX(DATE(timestamp)) FROM ohlcv_hourly WHERE symbol = s.symbol) as latest_hourly,
    (SELECT MAX(DATE(timestamp)) FROM ohlcv_1min WHERE symbol = s.symbol) as latest_1min
FROM (SELECT DISTINCT symbol FROM ohlcv_daily LIMIT 10) s;

-- Expected: latest_daily >= (latest_1min - 1 day)
```

---

## Related Context

### Sprint 75 Phase 2 (Historical Import Auto-Analysis)
- **Now Disabled** (Sprint 76): ImportAnalysisBridge removed
- Pattern/indicator analysis NOT auto-triggered after import
- Gap issue affects manual analysis runs via Process Analysis page

### Sprint 76 (SMA/EMA Calculations)
- Verified calculations are **accurate** for available data
- Missing Feb 13-14 data means SMA/EMA values 2 days stale
- User confirmed TSLA/NVDA values match 3rd party on Feb 12 data

### Database Schema
- All OHLCV tables use TimescaleDB hypertables
- Unique constraints: `(symbol, date)` for daily, `(symbol, timestamp)` for intraday
- ON CONFLICT DO UPDATE strategy prevents duplicates

---

## Next Steps

1. **Immediate** (Feb 14, 2026):
   - [ ] Access TickStockPL codebase
   - [ ] Locate historical data loader module
   - [ ] Review date range calculation code

2. **Investigation** (1-2 hours):
   - [ ] Test Massive API directly for Feb 13-14 daily data
   - [ ] Compare TickStockPL code vs TickStockAppV2 historical_loader.py
   - [ ] Confirm hypothesis (A, B, C, or D)

3. **Implementation** (2-4 hours):
   - [ ] Apply fix to TickStockPL
   - [ ] Run validation tests
   - [ ] Update documentation

4. **Deployment**:
   - [ ] Restart TickStockPL service
   - [ ] Run SPY universe import
   - [ ] Verify daily data now includes Feb 13

---

## Open Questions

1. **Is Feb 13, 2026 a market holiday?**
   - Need to check 2026 NYSE/NASDAQ calendar
   - If yes, Feb 12 is correct latest date

2. **What is Massive API's SLA for daily data availability?**
   - Real-time? End of day? Next day?
   - Check Massive API documentation

3. **Should we implement a "data staleness" warning in UI?**
   - Show user: "Daily data last updated: Feb 12, 2026 (2 days ago)"
   - Alert if lag exceeds 3 days

4. **Does this affect ALL symbols or just TSLA?**
   - Query: `SELECT symbol, MAX(date) FROM ohlcv_daily GROUP BY symbol ORDER BY MAX(date) DESC LIMIT 50`
   - Verify if Feb 12 cutoff is universal

---

## References

- **TickStockAppV2**: `src/api/rest/admin_historical_data_redis.py:300-426`
- **TickStockAppV2**: `src/data/historical_loader.py:714-780` (reference only, not used by universe imports)
- **TickStockPL**: `C:\Users\McDude\TickStockPL\` (requires investigation)
- **Massive API Docs**: https://polygon.io/docs/stocks/get_v2_aggs_ticker__stocksticker__range__multiplier___timespan___from___to
- **Sprint 76 Discussion**: `docs/planning/sprints/sprint76/q and a.md`

---

**Status**: 🔍 Investigation Required
**Owner**: TBD
**Estimated Effort**: 4-6 hours
**Dependencies**: TickStockPL codebase access
