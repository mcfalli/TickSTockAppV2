# TickStockPL Job Handler - Sprint 62 Multi-Timeframe Support Requirements

## 📋 **Document Purpose**
This document specifies the updated job format and requirements for TickStockPL's data loader to support Sprint 62's multi-timeframe historical data loading feature.

---

## 🎯 **Executive Summary**

**What Changed:**
- TickStockAppV2 admin UI now allows selecting **multiple OHLCV timeframes** via checkboxes (Sprint 62)
- Jobs are submitted with a `timeframes` array specifying which timeframes to load
- TickStockPL must load data for **ALL requested timeframes**, not just default/hardcoded ones

**Current Problem:**
- TickStockPL job handler ignores the `timeframes` parameter
- Only some timeframes are loaded (weekly/monthly work, daily/hourly/1min fail)
- Test load of DIA (30 symbols) for 1 day showed: 0% daily, 10% 1-min, 70% hourly

**Required Fix:**
- Update job handler to process `timeframes` array
- Load data for each specified timeframe
- Insert into correct database tables
- Report progress per timeframe

---

## 📊 **Sprint 62 Admin UI Overview**

### **Location:**
`TickStockAppV2 → Admin → Historical Data → Universe Data Loading`

### **User Workflow:**
1. **Select Universe** from dropdown (e.g., DIA, nasdaq100, SPY)
   - Populated from `definition_groups` table via RelationshipCache
   - Supports multi-universe joins (e.g., "SPY:nasdaq100")

2. **Select Timeframes** via checkboxes (ALL checked by default):
   ```
   ☑ 1-Minute
   ☑ Hourly
   ☑ Daily
   ☑ Weekly
   ☑ Monthly
   ```

3. **Select Duration** from dropdown:
   ```
   1 Day, 2 Days, 1 Week, 1 Month, 3 Months, 6 Months, 1 Year, 2 Years, 5 Years
   ```

4. **Click "📊 Load Universe Data"**
   - Job submitted to Redis channel: `tickstock.jobs.data_load`
   - Job appears in history/monitoring on the page

---

## 📡 **Job Message Format**

### **Redis Channel:**
```
tickstock.jobs.data_load
```

### **Message Payload (JSON):**

```json
{
  "job_id": "e33cca95-c71a-44ce-a377-3b232fa379ae",
  "job_type": "csv_universe_load",
  "source": "DIA",
  "universe_key": "DIA",
  "symbols": ["AAPL", "MSFT", "INTC", "..."],
  "timeframes": ["1min", "hour", "day", "week", "month"],
  "years": 0.003,
  "requested_by": "admin",
  "timestamp": "2025-12-23T12:15:13.634000"
}
```

### **Field Definitions:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `job_id` | string (UUID) | Unique job identifier | `"e33cca95-c71a-44ce-a377-3b232fa379ae"` |
| `job_type` | string | Job type identifier | `"csv_universe_load"` |
| `source` | string | Universe name | `"DIA"` or `"SPY:nasdaq100"` |
| `universe_key` | string | Same as source | `"DIA"` |
| `symbols` | array[string] | List of stock symbols to load | `["AAPL", "MSFT", ...]` |
| **`timeframes`** | **array[string]** | **🔥 NEW: Timeframes to load** | `["1min", "hour", "day", "week", "month"]` |
| `years` | float | Years of historical data | `0.003` (1 day), `1` (1 year), `2` (2 years) |
| `requested_by` | string | Username who submitted | `"admin"` |
| `timestamp` | string (ISO) | Submission timestamp | `"2025-12-23T12:15:13.634000"` |

---

## 🎯 **Timeframe Specifications**

### **Timeframe Mapping:**

| UI Label | `timeframes` Value | Target Table | Bar Interval | Bars/Day (Approx) |
|----------|-------------------|--------------|--------------|-------------------|
| "1-Minute" | `"1min"` | `ohlcv_1min` | 1 minute | 390 (6.5 hrs × 60 min) |
| "Hourly" | `"hour"` | `ohlcv_hourly` | 1 hour | 6-7 (market hours) |
| "Daily" | `"day"` | `ohlcv_daily` | 1 day | 1 |
| "Weekly" | `"week"` | `ohlcv_weekly` | 1 week | 0.2 (1 per week) |
| "Monthly" | `"month"` | `ohlcv_monthly` | 1 month | 0.05 (1 per month) |

### **Table Schemas:**

#### **ohlcv_1min & ohlcv_hourly:**
```sql
CREATE TABLE ohlcv_1min (
    symbol VARCHAR NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,  -- Note: timestamp, not date
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    PRIMARY KEY (symbol, timestamp)
);
```

#### **ohlcv_daily, ohlcv_weekly, ohlcv_monthly:**
```sql
CREATE TABLE ohlcv_daily (
    symbol VARCHAR NOT NULL,
    date DATE NOT NULL,  -- Note: date, not timestamp
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, date)
);
```

---

## ⚙️ **Required Implementation**

### **Job Handler Pseudocode:**

```python
def process_universe_load_job(job_data):
    """
    Process historical data load job with multi-timeframe support.

    Args:
        job_data: Job message from Redis (dict)
    """
    job_id = job_data['job_id']
    symbols = job_data['symbols']
    timeframes = job_data.get('timeframes', ['day'])  # Default to daily if not specified
    years = job_data['years']

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)

    # Update job status
    update_job_status(job_id, 'running', 0, f'Loading {len(symbols)} symbols for {len(timeframes)} timeframes')

    total_tasks = len(symbols) * len(timeframes)
    completed_tasks = 0

    for symbol in symbols:
        for timeframe in timeframes:
            try:
                # Load data from Massive API
                data = fetch_ohlcv_data(symbol, timeframe, start_date, end_date)

                # Insert into appropriate table
                table_name = get_table_name(timeframe)  # Maps 'day' -> 'ohlcv_daily'
                insert_ohlcv_data(table_name, symbol, data)

                completed_tasks += 1
                progress = int((completed_tasks / total_tasks) * 100)
                update_job_status(job_id, 'running', progress,
                                f'Loaded {timeframe} for {symbol}')

            except Exception as e:
                log_error(f"Failed to load {timeframe} for {symbol}: {e}")
                # Continue with next symbol/timeframe (don't fail entire job)

    # Final status update
    update_job_status(job_id, 'completed', 100,
                     f'Loaded {len(symbols)} symbols × {len(timeframes)} timeframes')
```

### **Timeframe-to-Table Mapping Function:**

```python
def get_table_name(timeframe: str) -> str:
    """
    Map timeframe value to database table name.

    Args:
        timeframe: Timeframe identifier from job ('1min', 'hour', 'day', 'week', 'month')

    Returns:
        Database table name
    """
    mapping = {
        '1min': 'ohlcv_1min',
        'hour': 'ohlcv_hourly',
        'day': 'ohlcv_daily',
        'week': 'ohlcv_weekly',
        'month': 'ohlcv_monthly'
    }

    if timeframe not in mapping:
        raise ValueError(f"Unknown timeframe: {timeframe}")

    return mapping[timeframe]
```

### **Massive API Call Example:**

```python
def fetch_ohlcv_data(symbol: str, timeframe: str, start_date: datetime, end_date: datetime):
    """
    Fetch OHLCV data from Massive API.

    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        timeframe: Timeframe ('1min', 'hour', 'day', 'week', 'month')
        start_date: Start date for historical data
        end_date: End date for historical data

    Returns:
        List of OHLCV bars
    """
    # Map internal timeframe to Massive API timeframe parameter
    api_timeframe_map = {
        '1min': '1Min',
        'hour': '1Hour',
        'day': '1Day',
        'week': '1Week',
        'month': '1Month'
    }

    api_timeframe = api_timeframe_map.get(timeframe, '1Day')

    # Call Massive API
    response = massive_api_client.get_bars(
        symbol=symbol,
        timeframe=api_timeframe,
        start=start_date.isoformat(),
        end=end_date.isoformat()
    )

    return response.bars
```

---

## ✅ **Acceptance Criteria**

### **Functional Requirements:**

1. **Process Timeframes Array** ✅
   - Job handler reads `timeframes` field from job message
   - If `timeframes` is missing, defaults to `['day']`
   - Processes each timeframe in the array

2. **Load Data for ALL Timeframes** ✅
   - For each symbol, load data for ALL specified timeframes
   - Do not skip timeframes
   - Do not hardcode which timeframes to load

3. **Insert into Correct Tables** ✅
   - `'1min'` → `ohlcv_1min`
   - `'hour'` → `ohlcv_hourly`
   - `'day'` → `ohlcv_daily`
   - `'week'` → `ohlcv_weekly`
   - `'month'` → `ohlcv_monthly`

4. **Handle Failures Gracefully** ✅
   - If one symbol fails, continue with others
   - If one timeframe fails, continue with other timeframes
   - Log errors but don't mark entire job as failed

5. **Report Progress Accurately** ✅
   - Update job status via Redis: `tickstock.jobs.status:{job_id}`
   - Progress percentage: `(completed_symbols × completed_timeframes) / (total_symbols × total_timeframes) × 100`
   - Status message includes current symbol and timeframe

---

## 🧪 **Test Scenarios**

### **Test 1: Single Timeframe - Daily Only**

**Job Message:**
```json
{
  "job_id": "test-001",
  "job_type": "csv_universe_load",
  "symbols": ["AAPL"],
  "timeframes": ["day"],
  "years": 0.02
}
```

**Expected Result:**
- ✅ Exactly 5 rows inserted into `ohlcv_daily` (5 trading days)
- ✅ 0 rows in other timeframe tables
- ✅ Job status: `completed` with 100% progress

**SQL Verification:**
```sql
SELECT COUNT(*) FROM ohlcv_daily WHERE symbol = 'AAPL';
-- Expected: 5
```

---

### **Test 2: Multiple Timeframes - 3 Symbols**

**Job Message:**
```json
{
  "job_id": "test-002",
  "job_type": "csv_universe_load",
  "symbols": ["AAPL", "MSFT", "INTC"],
  "timeframes": ["hour", "day", "week"],
  "years": 0.02
}
```

**Expected Result:**
- ✅ `ohlcv_hourly`: ~105 rows (3 symbols × ~35 hourly bars/week)
- ✅ `ohlcv_daily`: 15 rows (3 symbols × 5 days)
- ✅ `ohlcv_weekly`: 3 rows (3 symbols × 1 week)
- ✅ Job status: `completed` with 100% progress

**SQL Verification:**
```sql
SELECT
    'hourly' as timeframe, COUNT(*) as rows, COUNT(DISTINCT symbol) as symbols
FROM ohlcv_hourly WHERE symbol IN ('AAPL', 'MSFT', 'INTC')
UNION ALL
SELECT 'daily', COUNT(*), COUNT(DISTINCT symbol)
FROM ohlcv_daily WHERE symbol IN ('AAPL', 'MSFT', 'INTC')
UNION ALL
SELECT 'weekly', COUNT(*), COUNT(DISTINCT symbol)
FROM ohlcv_weekly WHERE symbol IN ('AAPL', 'MSFT', 'INTC');

-- Expected:
-- hourly  | ~105 | 3
-- daily   | 15   | 3
-- weekly  | 3    | 3
```

---

### **Test 3: All Timeframes - Full DIA (30 symbols)**

**Job Message:**
```json
{
  "job_id": "test-003",
  "job_type": "csv_universe_load",
  "symbols": ["AAPL", "MSFT", "INTC", "..."],  // 30 DIA symbols
  "timeframes": ["1min", "hour", "day", "week", "month"],
  "years": 0.003
}
```

**Expected Result:**
- ✅ `ohlcv_1min`: ~11,700 rows (30 symbols × ~390 bars/day)
- ✅ `ohlcv_hourly`: ~195 rows (30 symbols × ~6.5 bars/day)
- ✅ `ohlcv_daily`: 30 rows (30 symbols × 1 day)
- ✅ `ohlcv_weekly`: 30 rows (30 symbols × 1 week bar)
- ✅ `ohlcv_monthly`: 30 rows (30 symbols × 1 month bar)
- ✅ Job status: `completed` with 100% progress

**SQL Verification:**
```sql
SELECT
    '1min' as timeframe, COUNT(*) as rows, COUNT(DISTINCT symbol) as symbols
FROM ohlcv_1min
UNION ALL
SELECT 'hourly', COUNT(*), COUNT(DISTINCT symbol) FROM ohlcv_hourly
UNION ALL
SELECT 'daily', COUNT(*), COUNT(DISTINCT symbol) FROM ohlcv_daily
UNION ALL
SELECT 'weekly', COUNT(*), COUNT(DISTINCT symbol) FROM ohlcv_weekly
UNION ALL
SELECT 'monthly', COUNT(*), COUNT(DISTINCT symbol) FROM ohlcv_monthly;

-- Expected:
-- 1min    | ~11,700 | 30
-- hourly  | ~195    | 30
-- daily   | 30      | 30
-- weekly  | 30      | 30
-- monthly | 30      | 30
```

---

## 🐛 **Current Issues (From Test Results)**

### **Issue #1: Daily Timeframe Returns 0 Rows ❌**
**Symptom:**
```sql
SELECT COUNT(*) FROM ohlcv_daily;
-- Result: 0 (Expected: 30)
```

**Likely Causes:**
1. Job handler not processing `'day'` timeframe from array
2. Hardcoded to skip daily timeframe
3. API call for daily data failing silently
4. Insertion logic targeting wrong table

**Debug Steps:**
1. Add logging: `logger.info(f"Processing timeframe: {timeframe} for symbol: {symbol}")`
2. Verify `'day'` appears in logs
3. Check if API call is made for daily data
4. Verify insertion SQL targets `ohlcv_daily`

---

### **Issue #2: 1-Minute Timeframe Only Loads 3 Symbols ❌**
**Symptom:**
```sql
SELECT COUNT(DISTINCT symbol) FROM ohlcv_1min;
-- Result: 3 (Expected: 30)
-- Only AAPL, MSFT, INTC loaded
```

**Likely Causes:**
1. API rate limiting for 1-min data
2. Subscription tier doesn't allow 1-min for all symbols
3. Loop breaking early after 3 symbols
4. API timeout for remaining symbols

**Debug Steps:**
1. Check API response for all 30 symbols
2. Verify rate limiting isn't triggered
3. Check for exceptions in logs after 3rd symbol
4. Test with longer timeout for 1-min data requests

---

### **Issue #3: Hourly Timeframe Missing 9 Symbols ⚠️**
**Symptom:**
```sql
SELECT COUNT(DISTINCT symbol) FROM ohlcv_hourly;
-- Result: 21 (Expected: 30)
-- Missing: AMGN, CSCO, GS, HON, JNJ, MCD, MMM, TRV, WBA
```

**Likely Causes:**
1. Symbol-specific API failures
2. Network timeouts for certain symbols
3. Symbols delisted or unavailable
4. Exception handling skipping failed symbols without logging

**Debug Steps:**
1. Test each missing symbol individually
2. Check API response for missing symbols
3. Verify exception handling logs failures
4. Test WBA specifically (completely missing from all timeframes)

---

## 📝 **Job Status Updates**

### **Redis Key Format:**
```
tickstock.jobs.status:{job_id}
```

### **Status Fields (Hash):**

```python
{
    'status': 'running',           # 'submitted', 'running', 'completed', 'failed'
    'progress': '45',              # 0-100 (integer string)
    'message': 'Loading day for AAPL',  # Current operation
    'submitted_at': '2025-12-23T12:15:13',
    'started_at': '2025-12-23T12:15:14',
    'completed_at': '2025-12-23T12:18:45'  # Set when done
}
```

### **Update Frequency:**
- After each symbol × timeframe combination
- Or every 5 seconds if processing is slow

### **Example Update Sequence:**

```python
# Job starts
redis.hset('tickstock.jobs.status:abc123', {
    'status': 'running',
    'progress': '0',
    'message': 'Starting load for 30 symbols × 5 timeframes',
    'started_at': datetime.now().isoformat()
})

# Progress updates (after each symbol×timeframe)
redis.hset('tickstock.jobs.status:abc123', {
    'status': 'running',
    'progress': '3',  # 5/150 tasks = 3%
    'message': 'Loaded 1min for AAPL'
})

redis.hset('tickstock.jobs.status:abc123', {
    'status': 'running',
    'progress': '7',  # 10/150 tasks = 7%
    'message': 'Loaded hour for AAPL'
})

# Job completes
redis.hset('tickstock.jobs.status:abc123', {
    'status': 'completed',
    'progress': '100',
    'message': 'Successfully loaded 30 symbols × 5 timeframes',
    'completed_at': datetime.now().isoformat()
})
```

---

## 🔍 **Verification Checklist**

After implementing changes, verify the following:

### **Code Review:**
- [ ] Job handler reads `timeframes` field from job message
- [ ] Each timeframe in array is processed
- [ ] Timeframe-to-table mapping function exists and is correct
- [ ] API calls include timeframe parameter
- [ ] Data insertion targets correct table based on timeframe
- [ ] Progress updates include timeframe information
- [ ] Error handling doesn't skip timeframes silently

### **Functionality Testing:**
- [ ] **Test 1** passes: Single timeframe loads correctly
- [ ] **Test 2** passes: Multiple timeframes load for all symbols
- [ ] **Test 3** passes: All 5 timeframes load for 30 symbols
- [ ] Daily timeframe no longer returns 0 rows
- [ ] 1-minute data loads for all symbols (not just 3)
- [ ] Hourly data loads for all symbols (not missing 9)

### **Database Verification:**
- [ ] All 5 OHLCV tables contain data
- [ ] Row counts match expectations (see test scenarios)
- [ ] No duplicate records (check PRIMARY KEY constraints)
- [ ] Timestamps/dates are within expected range
- [ ] No NULL values in critical fields (open, high, low, close)

### **Job Status Tracking:**
- [ ] Redis status updates throughout job execution
- [ ] Progress percentage accurately reflects completion
- [ ] Status message indicates current symbol and timeframe
- [ ] Completed jobs marked as 'completed' with 100% progress
- [ ] Failed operations logged but don't stop entire job

---

## 📞 **Communication Protocol**

### **Questions/Issues:**
Contact: TickStockAppV2 Developer (via this conversation)

### **Code Location:**
- **Job Handler**: `TickStockPL/src/workers/data_loader.py` (or similar)
- **Redis Subscriber**: Listening to `tickstock.jobs.data_load`

### **Testing Coordination:**
1. Developer implements changes
2. Developer runs **Test 1** (single timeframe) and shares results
3. If Test 1 passes, run **Test 2** (multiple timeframes)
4. If Test 2 passes, run **Test 3** (full load)
5. Report results for each test with SQL verification queries

---

## 📊 **Success Metrics**

**Definition of Done:**
1. ✅ All 3 test scenarios pass
2. ✅ SQL verification queries return expected row counts
3. ✅ 0% data loss (all symbols × all timeframes loaded)
4. ✅ Job status updates visible in TickStockAppV2 UI
5. ✅ No errors in TickStockPL logs during test runs

**Performance Targets:**
- 1-day load (30 symbols × 5 timeframes): < 5 minutes
- 1-week load (30 symbols × 5 timeframes): < 10 minutes
- 1-year load (30 symbols × 5 timeframes): < 30 minutes

---

## 📎 **Appendix: Example Job Handler Implementation**

```python
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict

logger = logging.getLogger(__name__)

class UniverseLoadJobHandler:
    """Handles historical data load jobs with multi-timeframe support."""

    TIMEFRAME_TABLE_MAP = {
        '1min': 'ohlcv_1min',
        'hour': 'ohlcv_hourly',
        'day': 'ohlcv_daily',
        'week': 'ohlcv_weekly',
        'month': 'ohlcv_monthly'
    }

    TIMEFRAME_API_MAP = {
        '1min': '1Min',
        'hour': '1Hour',
        'day': '1Day',
        'week': '1Week',
        'month': '1Month'
    }

    def process(self, job_data: Dict):
        """Process universe load job with multi-timeframe support."""
        job_id = job_data['job_id']
        symbols = job_data['symbols']
        timeframes = job_data.get('timeframes', ['day'])
        years = job_data['years']

        logger.info(f"Job {job_id}: Processing {len(symbols)} symbols × {len(timeframes)} timeframes")
        logger.info(f"Job {job_id}: Timeframes requested: {timeframes}")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=int(years * 365))

        # Update job status
        self.update_status(job_id, 'running', 0,
                          f'Loading {len(symbols)} symbols for {len(timeframes)} timeframes')

        total_tasks = len(symbols) * len(timeframes)
        completed_tasks = 0
        errors = []

        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    logger.info(f"Job {job_id}: Loading {timeframe} for {symbol}")

                    # Fetch data from Massive API
                    data = self.fetch_ohlcv(symbol, timeframe, start_date, end_date)

                    # Get target table
                    table_name = self.TIMEFRAME_TABLE_MAP[timeframe]

                    # Insert data
                    rows_inserted = self.insert_ohlcv(table_name, symbol, data, timeframe)

                    logger.info(f"Job {job_id}: Inserted {rows_inserted} rows into {table_name} for {symbol}")

                    completed_tasks += 1
                    progress = int((completed_tasks / total_tasks) * 100)
                    self.update_status(job_id, 'running', progress,
                                     f'Loaded {timeframe} for {symbol} ({completed_tasks}/{total_tasks})')

                except Exception as e:
                    error_msg = f"Failed to load {timeframe} for {symbol}: {str(e)}"
                    logger.error(f"Job {job_id}: {error_msg}")
                    errors.append(error_msg)
                    # Continue with next symbol/timeframe

        # Final status
        if completed_tasks == total_tasks:
            status = 'completed'
            message = f'Successfully loaded {len(symbols)} symbols × {len(timeframes)} timeframes'
        else:
            status = 'completed_with_errors'
            message = f'Loaded {completed_tasks}/{total_tasks} tasks. {len(errors)} errors.'

        self.update_status(job_id, status, 100, message)

        if errors:
            logger.warning(f"Job {job_id}: Completed with {len(errors)} errors:\n" + "\n".join(errors[:10]))

    def fetch_ohlcv(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch OHLCV data from Massive API."""
        api_timeframe = self.TIMEFRAME_API_MAP[timeframe]

        # Make API call (implement based on your API client)
        response = self.massive_api_client.get_bars(
            symbol=symbol,
            timeframe=api_timeframe,
            start=start_date.isoformat(),
            end=end_date.isoformat()
        )

        return response.bars

    def insert_ohlcv(self, table_name: str, symbol: str, data: List[Dict], timeframe: str) -> int:
        """Insert OHLCV data into database."""
        if not data:
            return 0

        # Build INSERT query based on timeframe
        if timeframe in ['1min', 'hour']:
            # Use timestamp column
            query = f"""
                INSERT INTO {table_name} (symbol, timestamp, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, timestamp) DO NOTHING
            """
            values = [(symbol, bar['timestamp'], bar['open'], bar['high'],
                      bar['low'], bar['close'], bar['volume']) for bar in data]
        else:
            # Use date column
            query = f"""
                INSERT INTO {table_name} (symbol, date, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, date) DO NOTHING
            """
            values = [(symbol, bar['date'], bar['open'], bar['high'],
                      bar['low'], bar['close'], bar['volume']) for bar in data]

        # Execute batch insert
        cursor = self.db_connection.cursor()
        cursor.executemany(query, values)
        self.db_connection.commit()

        return len(values)

    def update_status(self, job_id: str, status: str, progress: int, message: str):
        """Update job status in Redis."""
        key = f'tickstock.jobs.status:{job_id}'
        self.redis_client.hset(key, mapping={
            'status': status,
            'progress': str(progress),
            'message': message
        })

        if status == 'completed' or status == 'completed_with_errors' or status == 'failed':
            self.redis_client.hset(key, 'completed_at', datetime.now().isoformat())
```

---

**End of Requirements Document**

**Document Version:** 1.0
**Date:** December 23, 2025
**Author:** TickStockAppV2 Sprint 62 Team
**Status:** Ready for Implementation
