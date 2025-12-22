# Sprint 56: Historical Data Load Enhancement

**Sprint**: 56
**Priority**: CRITICAL
**Component**: TickStockPL Historical Data Loader
**Type**: Bug Fix + Architecture Enhancement
**Estimated Effort**: 2-3 days

---

## Executive Summary

### Current State
TickStockPL has a **mostly functional** historical data loading mechanism triggered by Redis job messages from TickStockAppV2. However, recent testing revealed that while symbols are registered successfully, **ZERO OHLCV bars** are being fetched and inserted for any timeframe.

**Example Failure**: SCHG & VUG 2-day load registered symbols but loaded 0 hourly, 0 daily, 0 weekly, 0 monthly bars.

### Root Cause
The job handler receives symbols from Redis messages but does not execute the API fetch and database insert operations for OHLCV data.

### Sprint Goal
**Enhance existing job handler** to:
1. Fetch pre-aggregated OHLCV data from Massive API Custom Bars endpoint (hourly, daily, weekly, monthly)
2. Insert all timeframe data into TimescaleDB
3. Eliminate manual aggregation logic (use API-aggregated bars)
4. Ensure 100% data completeness for all universe load jobs

### Success Criteria
- ✅ 2-day test load: SCHG & VUG get 13 hourly, 2 daily, 1 weekly, 1 monthly bars each
- ✅ 90-day test load: SPY gets ~13 hourly, ~63 daily, ~13 weekly, 3 monthly bars
- ✅ All timeframes populated for every symbol in a job
- ✅ Integration tests pass with real API calls

---

## Problem Analysis

### What Works Today
- ✅ Redis job message reception on `tickstock.jobs.data_load` channel
- ✅ Symbol metadata registration in `symbols` table
- ✅ Job status tracking and logging
- ✅ Database schema (tables exist and are correct)

### What's Broken
- ❌ OHLCV data fetching from Massive API (not implemented or not called)
- ❌ Hourly bar insertion (0 bars inserted)
- ❌ Daily bar insertion (0 bars inserted)
- ❌ Weekly bar insertion (0 bars inserted)
- ❌ Monthly bar insertion (0 bars inserted)

### Evidence
```sql
-- After SCHG/VUG 2-day load on Nov 30, 2025
SELECT symbol, COUNT(*) FROM ohlcv_hourly WHERE symbol IN ('SCHG', 'VUG') GROUP BY symbol;
-- Expected: 13 bars each | Actual: 0 bars

SELECT symbol, COUNT(*) FROM ohlcv_daily WHERE symbol IN ('SCHG', 'VUG') GROUP BY symbol;
-- Expected: 2 bars each | Actual: 0 bars
```

---

## Architecture Enhancement

### Before: Manual Aggregation Approach (Old/Broken)
```
1. Fetch hourly data from API
2. Fetch daily data from API
3. Manually aggregate daily → weekly in Python
4. Manually aggregate daily → monthly in Python
```

**Problems**:
- Complex aggregation logic (~150 lines)
- Edge case handling (holidays, partial weeks)
- May not match API conventions (week start Sunday vs Monday)
- Either not implemented or not being called

### After: API-Aggregated Approach (New/Enhanced)
```
1. Fetch hourly bars from Massive Custom Bars API (timespan='hour')
2. Fetch daily bars from Massive Custom Bars API (timespan='day')
3. Fetch weekly bars from Massive Custom Bars API (timespan='week') ← API aggregates
4. Fetch monthly bars from Massive Custom Bars API (timespan='month') ← API aggregates
```

**Benefits**:
- ✅ Simpler code (4 API calls instead of 2 calls + aggregation)
- ✅ API handles edge cases correctly
- ✅ Consistent with Massive API conventions (week starts Sunday 12:00 AM EST)
- ✅ Less code to maintain
- ✅ More reliable

---

## Implementation Plan

### Phase 1: API Integration (Day 1)

#### 1.1 Environment Configuration

**File**: `.env` or TickStockPL config

```bash
# Massive API Configuration
MASSIVE_API_KEY=your_api_key_here
MASSIVE_API_BASE_URL=https://api.polygon.io
MASSIVE_API_TIMEOUT=30

# Database Configuration (verify existing)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tickstock
DB_USER=postgres
DB_PASSWORD=your_password
```

#### 1.2 Massive API Client

**File**: `src/api/massive_client.py` (new or enhance existing)

```python
import requests
import os
from datetime import datetime
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


def call_massive_api(endpoint: str, params: Optional[Dict] = None) -> requests.Response:
    """
    Call Massive API with authentication and error handling

    Args:
        endpoint: API path without base URL (e.g., 'aggs/ticker/AAPL/range/1/day/2023-01-01/2023-12-31')
        params: Query parameters (e.g., {'adjusted': 'true', 'sort': 'asc'})

    Returns:
        requests.Response object

    Raises:
        ValueError: If API key not configured
        requests.exceptions.RequestException: On network/HTTP errors
    """
    base_url = os.getenv('MASSIVE_API_BASE_URL', 'https://api.polygon.io')
    api_key = os.getenv('MASSIVE_API_KEY')

    if not api_key:
        raise ValueError("MASSIVE_API_KEY environment variable not set")

    # Construct full URL
    url = f"{base_url}/v2/{endpoint}"

    # Add API key to params
    if params is None:
        params = {}
    params['apiKey'] = api_key

    # Make request with timeout
    timeout = int(os.getenv('MASSIVE_API_TIMEOUT', 30))

    logger.debug(f"Calling Massive API: {url}")
    response = requests.get(url, params=params, timeout=timeout)

    return response


def fetch_custom_bars(symbol: str, multiplier: int, timespan: str,
                     from_date, to_date, max_retries: int = 3) -> List[Dict]:
    """
    Fetch OHLCV bars using Massive Custom Bars API with retry logic

    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        multiplier: Size of timespan multiplier (typically 1)
        timespan: Time window - 'minute', 'hour', 'day', 'week', 'month'
        from_date: Start date (datetime or date object)
        to_date: End date (datetime or date object)
        max_retries: Maximum retry attempts (default: 3)

    Returns:
        List of bar dicts with keys: date, open, high, low, close, volume

    Example:
        >>> bars = fetch_custom_bars('AAPL', 1, 'day', date(2023,1,1), date(2023,12,31))
        >>> len(bars)
        252
    """
    import time

    # Format dates for API
    if hasattr(from_date, 'strftime'):
        from_str = from_date.strftime('%Y-%m-%d')
        to_str = to_date.strftime('%Y-%m-%d')
    else:
        from_str = str(from_date)
        to_str = str(to_date)

    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching {symbol} {timespan} bars (attempt {attempt + 1}/{max_retries})...")

            # Call Massive Custom Bars API
            # Endpoint: /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}
            endpoint = f'aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_str}/{to_str}'
            response = call_massive_api(
                endpoint=endpoint,
                params={'adjusted': 'true', 'sort': 'asc', 'limit': 50000}
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                logger.info(f"✓ API returned {len(results)} {timespan} bars for {symbol}")

                # Convert API response to standard format
                bars = []
                for bar in results:
                    bars.append({
                        'date': datetime.fromtimestamp(bar['t'] / 1000),  # Convert ms to datetime
                        'open': bar['o'],
                        'high': bar['h'],
                        'low': bar['l'],
                        'close': bar['c'],
                        'volume': bar['v']
                    })

                return bars

            elif response.status_code == 404:
                logger.warning(f"⚠ Symbol {symbol} not found (404)")
                return []

            elif response.status_code == 429:
                # Rate limit - wait longer
                wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                logger.warning(f"⚠ Rate limited (429), waiting {wait_time}s...")
                time.sleep(wait_time)
                continue

            else:
                logger.error(f"✗ API error {response.status_code}: {response.text}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return []

        except Exception as e:
            logger.error(f"✗ Exception fetching {symbol} {timespan} bars: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                raise

    return []
```

---

### Phase 2: Database Operations (Day 1-2)

#### 2.1 Database Helper Functions

**File**: `src/database/ohlcv_operations.py` (new or enhance existing)

```python
import psycopg2
from psycopg2.extras import execute_batch
from contextlib import contextmanager
import os
import logging

logger = logging.getLogger(__name__)


@contextmanager
def get_db_connection():
    """Get database connection from environment configuration"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'tickstock'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_hourly_bars(symbol: str, bars: list) -> int:
    """
    Insert hourly OHLCV bars in batch

    Args:
        symbol: Stock ticker
        bars: List of dicts with keys: date (datetime), open, high, low, close, volume

    Returns:
        Number of bars inserted
    """
    if not bars:
        return 0

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Prepare data tuples
        data = [
            (
                symbol,
                bar['date'],  # datetime object for timestamp column
                float(bar['open']),
                float(bar['high']),
                float(bar['low']),
                float(bar['close']),
                int(bar['volume'])
            )
            for bar in bars
        ]

        # Batch insert with ON CONFLICT
        execute_batch(cursor, """
            INSERT INTO ohlcv_hourly (symbol, timestamp, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timestamp) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                created_at = NOW()
        """, data)

        cursor.close()
        return len(data)


def insert_daily_bars(symbol: str, bars: list) -> int:
    """Insert daily OHLCV bars in batch"""
    if not bars:
        return 0

    with get_db_connection() as conn:
        cursor = conn.cursor()

        data = [
            (
                symbol,
                bar['date'].date() if hasattr(bar['date'], 'date') else bar['date'],  # Convert to date
                float(bar['open']),
                float(bar['high']),
                float(bar['low']),
                float(bar['close']),
                int(bar['volume'])
            )
            for bar in bars
        ]

        execute_batch(cursor, """
            INSERT INTO ohlcv_daily (symbol, date, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, date) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                created_at = NOW()
        """, data)

        cursor.close()
        return len(data)


def insert_weekly_bars(symbol: str, bars: list) -> int:
    """Insert weekly OHLCV bars in batch"""
    if not bars:
        return 0

    with get_db_connection() as conn:
        cursor = conn.cursor()

        data = [
            (
                symbol,
                bar['date'].date() if hasattr(bar['date'], 'date') else bar['date'],
                float(bar['open']),
                float(bar['high']),
                float(bar['low']),
                float(bar['close']),
                int(bar['volume'])
            )
            for bar in bars
        ]

        execute_batch(cursor, """
            INSERT INTO ohlcv_weekly (symbol, week_start, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, week_start) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                created_at = NOW()
        """, data)

        cursor.close()
        return len(data)


def insert_monthly_bars(symbol: str, bars: list) -> int:
    """Insert monthly OHLCV bars in batch"""
    if not bars:
        return 0

    with get_db_connection() as conn:
        cursor = conn.cursor()

        data = [
            (
                symbol,
                bar['date'].date() if hasattr(bar['date'], 'date') else bar['date'],
                float(bar['open']),
                float(bar['high']),
                float(bar['low']),
                float(bar['close']),
                int(bar['volume'])
            )
            for bar in bars
        ]

        execute_batch(cursor, """
            INSERT INTO ohlcv_monthly (symbol, month_start, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, month_start) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                created_at = NOW()
        """, data)

        cursor.close()
        return len(data)
```

---

### Phase 3: Job Handler Enhancement (Day 2)

#### 3.1 Enhanced Job Handler

**File**: `src/jobs/universe_load_handler.py` (enhance existing)

**Key Changes**:
1. Add imports for new API and database functions
2. Replace missing OHLCV fetch logic with Custom Bars API calls
3. Call all 4 insert functions (hourly, daily, weekly, monthly)
4. Add comprehensive logging

```python
from datetime import datetime, timedelta
from src.api.massive_client import fetch_custom_bars
from src.database.ohlcv_operations import (
    insert_hourly_bars,
    insert_daily_bars,
    insert_weekly_bars,
    insert_monthly_bars
)
import logging

logger = logging.getLogger(__name__)


def handle_csv_universe_load(job_data):
    """
    Handle universe load job - imports symbols + hourly/daily/weekly/monthly OHLCV data

    ENHANCEMENTS (Sprint 56):
    - Uses Massive Custom Bars API for all timeframes (eliminates manual aggregation)
    - Fetches hourly (max 2 days), daily, weekly, monthly bars from API
    - Inserts all 4 timeframes into TimescaleDB

    Args:
        job_data: Redis job message with keys:
            - job_id: Unique job identifier
            - symbols: List of ticker symbols
            - years: Timeframe in years (e.g., 0.005479 = 2 days)
            - source: Job source description
    """

    # ========================================
    # STEP 1: Extract Job Parameters
    # ========================================
    job_id = job_data.get('job_id')
    source = job_data.get('source', 'unknown')
    years = job_data.get('years', 1)

    logger.info(f"=== PROCESSING JOB {job_id} ===")
    logger.info(f"Job type: {job_data.get('job_type')}")
    logger.info(f"Source: {source}")
    logger.info(f"Years: {years}")

    # Extract symbols (PRIORITY 1: from message, PRIORITY 2: from CSV)
    symbols = job_data.get('symbols')

    if not symbols:
        csv_file = job_data.get('csv_file')
        if csv_file:
            logger.info(f"No symbols array found, reading from CSV: {csv_file}")
            symbols = load_symbols_from_csv(csv_file)
        else:
            logger.error(f"Job {job_id}: No symbols array or csv_file provided")
            update_job_status(job_id, 'failed', error='No symbols provided')
            return

    logger.info(f"Symbols in message: {symbols}")
    logger.info(f"Symbol count: {len(symbols)}")

    # ========================================
    # STEP 2: Calculate Date Ranges
    # ========================================
    # Daily/Weekly/Monthly: Full timeframe
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=int(years * 365))

    logger.info(f"Daily date range: {start_date} to {end_date}")

    # Hourly: Max 2 days
    hourly_end = datetime.now()
    if years <= 0.0027:  # 1 day or less
        hourly_start = hourly_end - timedelta(hours=24)
        logger.info(f"Hourly date range: {hourly_start} to {hourly_end} (1 day)")
    else:  # 2+ days
        hourly_start = hourly_end - timedelta(hours=48)
        logger.info(f"Hourly date range: {hourly_start} to {hourly_end} (2 days max)")

    # Update job status
    update_job_status(job_id, 'processing',
                     progress=0,
                     total_symbols=len(symbols),
                     message=f"Starting load of {len(symbols)} symbols")

    # ========================================
    # STEP 3: Process Each Symbol
    # ========================================
    results = {
        'symbols_loaded': 0,
        'symbols_failed': 0,
        'hourly_bars': 0,
        'daily_bars': 0,
        'weekly_bars': 0,
        'monthly_bars': 0,
        'errors': []
    }

    for i, symbol in enumerate(symbols, 1):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing {symbol} ({i}/{len(symbols)})")
        logger.info(f"{'=' * 60}")

        try:
            # ------------------------------
            # 3A. Register Symbol Metadata
            # ------------------------------
            logger.info(f"Fetching metadata for {symbol}...")
            metadata = fetch_symbol_metadata(symbol)

            if metadata:
                register_symbol(
                    symbol=symbol,
                    name=metadata.get('name'),
                    exchange=metadata.get('exchange'),
                    sector=metadata.get('sector'),
                    industry=metadata.get('industry'),
                    issuer=metadata.get('issuer'),
                    underlying_index=metadata.get('underlying_index')
                )
                logger.info(f"✓ Symbol registered: {metadata.get('name')} ({metadata.get('issuer')})")
            else:
                logger.warning(f"⚠ No metadata found for {symbol}, registering with symbol only")
                register_symbol(symbol=symbol)

            # ------------------------------
            # 3B. Fetch Hourly OHLCV Data (ENHANCED - Sprint 56)
            # ------------------------------
            logger.info(f"Fetching hourly bars via Custom Bars API: {hourly_start} to {hourly_end}...")
            hourly_bars = fetch_custom_bars(
                symbol=symbol,
                multiplier=1,
                timespan='hour',
                from_date=hourly_start,
                to_date=hourly_end
            )

            if hourly_bars and len(hourly_bars) > 0:
                logger.info(f"✓ Fetched {len(hourly_bars)} hourly bars from API")
                inserted_hourly = insert_hourly_bars(symbol, hourly_bars)
                logger.info(f"✓ Inserted {inserted_hourly} bars into ohlcv_hourly")
                results['hourly_bars'] += inserted_hourly
            else:
                logger.warning(f"⚠ No hourly data returned from API for {symbol}")
                inserted_hourly = 0

            # ------------------------------
            # 3C. Fetch Daily OHLCV Data (ENHANCED - Sprint 56)
            # ------------------------------
            logger.info(f"Fetching daily bars via Custom Bars API: {start_date} to {end_date}...")
            daily_bars = fetch_custom_bars(
                symbol=symbol,
                multiplier=1,
                timespan='day',
                from_date=start_date,
                to_date=end_date
            )

            if not daily_bars or len(daily_bars) == 0:
                logger.error(f"✗ No daily data returned from API for {symbol}")
                results['errors'].append(f"{symbol}: No daily data available")
                results['symbols_failed'] += 1
                continue

            logger.info(f"✓ Fetched {len(daily_bars)} daily bars from API")
            inserted_daily = insert_daily_bars(symbol, daily_bars)
            logger.info(f"✓ Inserted {inserted_daily} bars into ohlcv_daily")
            results['daily_bars'] += inserted_daily

            # ------------------------------
            # 3D. Fetch Weekly OHLCV Data (NEW - Sprint 56)
            # ------------------------------
            logger.info(f"Fetching weekly bars via Custom Bars API: {start_date} to {end_date}...")
            weekly_bars = fetch_custom_bars(
                symbol=symbol,
                multiplier=1,
                timespan='week',
                from_date=start_date,
                to_date=end_date
            )

            if weekly_bars and len(weekly_bars) > 0:
                logger.info(f"✓ Fetched {len(weekly_bars)} weekly bars from API")
                inserted_weekly = insert_weekly_bars(symbol, weekly_bars)
                logger.info(f"✓ Inserted {inserted_weekly} bars into ohlcv_weekly")
                results['weekly_bars'] += inserted_weekly
            else:
                logger.info(f"⚠ No weekly bars returned (timeframe too short)")
                inserted_weekly = 0

            # ------------------------------
            # 3E. Fetch Monthly OHLCV Data (NEW - Sprint 56)
            # ------------------------------
            logger.info(f"Fetching monthly bars via Custom Bars API: {start_date} to {end_date}...")
            monthly_bars = fetch_custom_bars(
                symbol=symbol,
                multiplier=1,
                timespan='month',
                from_date=start_date,
                to_date=end_date
            )

            if monthly_bars and len(monthly_bars) > 0:
                logger.info(f"✓ Fetched {len(monthly_bars)} monthly bars from API")
                inserted_monthly = insert_monthly_bars(symbol, monthly_bars)
                logger.info(f"✓ Inserted {inserted_monthly} bars into ohlcv_monthly")
                results['monthly_bars'] += inserted_monthly
            else:
                logger.info(f"⚠ No monthly bars returned (timeframe too short)")
                inserted_monthly = 0

            # Success!
            logger.info(f"✓ Completed {symbol}:")
            logger.info(f"  Hourly: {inserted_hourly} bars")
            logger.info(f"  Daily: {inserted_daily} bars")
            logger.info(f"  Weekly: {inserted_weekly} bars")
            logger.info(f"  Monthly: {inserted_monthly} bars")

            results['symbols_loaded'] += 1

            # Update job progress
            progress_pct = int((i / len(symbols)) * 100)
            update_job_status(job_id, 'processing',
                             progress=progress_pct,
                             current_symbol=symbol,
                             message=f"Processed {i}/{len(symbols)} symbols")

        except Exception as e:
            logger.error(f"✗ Failed to process {symbol}: {e}", exc_info=True)
            results['errors'].append(f"{symbol}: {str(e)}")
            results['symbols_failed'] += 1

    # ========================================
    # STEP 4: Finalize Job
    # ========================================
    logger.info(f"\n{'=' * 60}")
    logger.info(f"JOB COMPLETE: {job_id}")
    logger.info(f"{'=' * 60}")
    logger.info(f"Symbols loaded: {results['symbols_loaded']}/{len(symbols)}")
    logger.info(f"Symbols failed: {results['symbols_failed']}")
    logger.info(f"Hourly bars inserted: {results['hourly_bars']}")
    logger.info(f"Daily bars inserted: {results['daily_bars']}")
    logger.info(f"Weekly bars inserted: {results['weekly_bars']}")
    logger.info(f"Monthly bars inserted: {results['monthly_bars']}")

    if results['errors']:
        logger.error(f"Errors encountered:")
        for error in results['errors']:
            logger.error(f"  - {error}")

    # Update final job status
    if results['symbols_failed'] == 0:
        update_job_status(job_id, 'completed',
                         progress=100,
                         results=results,
                         message=f"Successfully loaded {results['symbols_loaded']} symbols")
    else:
        update_job_status(job_id, 'completed_with_errors',
                         progress=100,
                         results=results,
                         message=f"Loaded {results['symbols_loaded']} symbols, {results['symbols_failed']} failed")
```

---

### Phase 4: Testing & Validation (Day 3)

#### 4.1 Test Case 1: 2-Day Load (SCHG, VUG)

**Objective**: Verify all 4 timeframes populated correctly

**Setup**:
```sql
-- Clear old data
DELETE FROM ohlcv_hourly WHERE symbol IN ('SCHG', 'VUG') AND timestamp >= NOW() - INTERVAL '2 days';
DELETE FROM ohlcv_daily WHERE symbol IN ('SCHG', 'VUG') AND date >= CURRENT_DATE - INTERVAL '2 days';
DELETE FROM ohlcv_weekly WHERE symbol IN ('SCHG', 'VUG') AND week_start >= CURRENT_DATE - INTERVAL '7 days';
DELETE FROM ohlcv_monthly WHERE symbol IN ('SCHG', 'VUG') AND month_start >= CURRENT_DATE - INTERVAL '1 month';
```

**Trigger Job** (from TickStockAppV2 admin UI):
- Navigate to `/admin/historical-data`
- Select cached universe: "Core ETFs" OR enter "SCHG,VUG"
- Duration: 2 days
- Click "Load Universe Data"

**Expected Logs**:
```
=== PROCESSING JOB universe_load_XXXXX ===
Symbols in message: ['SCHG', 'VUG']

Processing SCHG (1/2)
✓ Symbol registered: Schwab U.S. Large-Cap Growth ETF
Fetching hourly bars via Custom Bars API...
Fetching SCHG hour bars (attempt 1/3)...
✓ API returned 13 hour bars for SCHG
✓ Inserted 13 bars into ohlcv_hourly
Fetching daily bars via Custom Bars API...
✓ API returned 2 day bars for SCHG
✓ Inserted 2 bars into ohlcv_daily
Fetching weekly bars via Custom Bars API...
✓ API returned 1 week bars for SCHG
✓ Inserted 1 bars into ohlcv_weekly
Fetching monthly bars via Custom Bars API...
✓ API returned 1 month bars for SCHG
✓ Inserted 1 bars into ohlcv_monthly

JOB COMPLETE
Hourly bars inserted: 26 (13 per symbol)
Daily bars inserted: 4 (2 per symbol)
Weekly bars inserted: 2 (1 per symbol)
Monthly bars inserted: 2 (1 per symbol)
```

**Verification Queries**:
```sql
-- Hourly: Should return ~13 bars each
SELECT symbol, COUNT(*) as hourly_bars
FROM ohlcv_hourly
WHERE symbol IN ('SCHG', 'VUG')
  AND timestamp >= NOW() - INTERVAL '2 days'
GROUP BY symbol;

-- Daily: Should return 2 bars each
SELECT symbol, COUNT(*) as daily_bars
FROM ohlcv_daily
WHERE symbol IN ('SCHG', 'VUG')
  AND date >= CURRENT_DATE - INTERVAL '2 days'
GROUP BY symbol;

-- Weekly: Should return 1 bar each
SELECT symbol, COUNT(*) as weekly_bars
FROM ohlcv_weekly
WHERE symbol IN ('SCHG', 'VUG')
  AND week_start >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY symbol;

-- Monthly: Should return 1 bar each
SELECT symbol, COUNT(*) as monthly_bars
FROM ohlcv_monthly
WHERE symbol IN ('SCHG', 'VUG')
  AND month_start >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY symbol;
```

#### 4.2 Test Case 2: 90-Day Load (SPY)

**Expected**:
- Hourly: ~13 bars (max 2 days, NOT 90 days)
- Daily: ~63 bars (3 months × 21 trading days)
- Weekly: ~13 bars
- Monthly: 3 bars

**Verification**:
```sql
SELECT
    'hourly' as timeframe,
    COUNT(*) as bars
FROM ohlcv_hourly
WHERE symbol = 'SPY'
  AND timestamp >= NOW() - INTERVAL '2 days'

UNION ALL

SELECT
    'daily',
    COUNT(*)
FROM ohlcv_daily
WHERE symbol = 'SPY'
  AND date >= CURRENT_DATE - INTERVAL '90 days'

UNION ALL

SELECT
    'weekly',
    COUNT(*)
FROM ohlcv_weekly
WHERE symbol = 'SPY'
  AND week_start >= CURRENT_DATE - INTERVAL '90 days'

UNION ALL

SELECT
    'monthly',
    COUNT(*)
FROM ohlcv_monthly
WHERE symbol = 'SPY'
  AND month_start >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '90 days');
```

---

## Success Criteria

### Minimum Requirements (MUST PASS)
- [ ] Symbols registered in `symbols` table with `last_updated` timestamp
- [ ] Hourly bars inserted for ALL symbols (max 2 days)
- [ ] Daily bars inserted for ALL symbols for full date range
- [ ] Weekly bars created and inserted (if timeframe ≥ 1 week)
- [ ] Monthly bars created and inserted (if timeframe ≥ 1 month)
- [ ] TickStockPL logs show: "Symbols in message: [...]"
- [ ] TickStockPL logs show: "Fetching X hour/day/week/month bars via Custom Bars API"
- [ ] TickStockPL logs show: "✓ API returned X bars" where X > 0
- [ ] TickStockPL logs show: "✓ Inserted X bars" where X > 0
- [ ] No API errors (404, 500) for valid symbols
- [ ] No database errors during insertion

### Full Requirements (MUST ACHIEVE)
- [ ] 2-day test: SCHG & VUG get expected bar counts (±10%)
- [ ] 90-day test: SPY gets expected bar counts (±10%)
- [ ] Bar counts ≥ 90% of expected values
- [ ] All data passes OHLC validation (High ≥ Low, Open/Close within range)
- [ ] Job status updated to "completed" in Redis
- [ ] Zero regression on existing functionality

---

## Expected Timeframes & Bar Counts

| Timeframe | Days | Hourly Bars | Daily Bars | Weekly Bars | Monthly Bars |
|-----------|------|-------------|------------|-------------|--------------|
| 1 day     | 1    | 6-7         | 1          | 0-1         | 0-1          |
| 2 days    | 2    | ~13         | 2          | 0-1         | 0-1          |
| 1 week    | 7    | ~13 (max)   | 5          | 1           | 0-1          |
| 1 month   | 30   | ~13 (max)   | ~21        | ~4          | 1            |
| 3 months  | 90   | ~13 (max)   | ~63        | ~13         | 3            |
| 6 months  | 180  | ~13 (max)   | ~126       | ~26         | 6            |
| 1 year    | 365  | ~13 (max)   | ~252       | ~52         | 12           |

**Key Constraint**: Hourly data is ALWAYS capped at 2 days maximum, regardless of timeframe.

---

## Rollout Plan

### Pre-Implementation
- [ ] Review this document with team
- [ ] Verify Massive API key is configured
- [ ] Verify database credentials
- [ ] Create backup of existing job handler code
- [ ] Set up test environment

### Implementation
- [ ] Day 1: Add API client (`massive_client.py`)
- [ ] Day 1: Add database operations (`ohlcv_operations.py`)
- [ ] Day 2: Enhance job handler (`universe_load_handler.py`)
- [ ] Day 2: Add logging and error handling
- [ ] Day 3: Test with SCHG/VUG (2 days)
- [ ] Day 3: Test with SPY (90 days)
- [ ] Day 3: Verify all success criteria

### Post-Implementation
- [ ] Document any API rate limit issues encountered
- [ ] Update monitoring dashboards
- [ ] Create runbook for troubleshooting
- [ ] Mark Sprint 56 complete

---

## Dependencies

### Required Python Packages
```
requests>=2.31.0
psycopg2-binary>=2.9.9
redis>=5.0.0
python-dotenv>=1.0.0
```

### Environment Variables
```bash
MASSIVE_API_KEY=<your_key>
MASSIVE_API_BASE_URL=https://api.polygon.io
DB_HOST=localhost
DB_NAME=tickstock
DB_USER=postgres
DB_PASSWORD=<your_password>
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API rate limits | Exponential backoff, retry logic, batch processing |
| Missing bars from API | Log warnings, continue with partial data |
| Database connection failures | Context manager ensures rollback, retry logic |
| Large universe loads timeout | Process in batches, update progress frequently |
| Massive API schema changes | Version API calls, add response validation |

---

## Sprint Completion Checklist

- [ ] All code committed to TickStockPL repository
- [ ] All tests passing (SCHG/VUG 2-day, SPY 90-day)
- [ ] Documentation updated (this file, code comments)
- [ ] Integration tests added/updated
- [ ] Monitoring alerts configured
- [ ] Team demo completed
- [ ] Sprint retrospective conducted
- [ ] Sprint 56 marked complete in tracking system

---

**Status**: Ready for Implementation
**Owner**: TickStockPL Team
**Review Date**: Upon completion
**Related**: Sprint 55 (ETF Universe Integration)
