# TickStockPL Historical Data Import Requirements

**Date**: 2025-11-30
**Sprint**: 55
**Priority**: CRITICAL
**Component**: TickStockPL Historical Data Loader

---

## Executive Summary

**Purpose**: Define complete requirements for TickStockPL historical data import to ensure ALL available data is loaded for the specified timeframe.

**Scope**: Universe load jobs (CSV files and cached universes) must import symbols metadata AND OHLCV data for hourly (max 2 days), daily, weekly, and monthly timeframes.

**Current Issue**: SCHG & VUG 2-day import loaded symbols but ZERO OHLCV bars. This document specifies what MUST be loaded.

---

## Data Import Requirements

### Implementation Strategy

**Use Massive API Custom Bars endpoint** for all timeframes (hourly, daily, weekly, monthly). This eliminates manual aggregation logic and ensures consistency with API-calculated bars.

**API Endpoint**: `/v2/aggs/ticker/{stocksTicker}/range/{multiplier}/{timespan}/{from}/{to}`

**Supported timespans**: `minute`, `hour`, `day`, `week`, `month`, `quarter`

**Reference**: https://massive.com/docs/rest/stocks/aggregates/custom-bars

### Supported Timeframes

TickStockPL MUST support the following timeframe parameters:

| Timeframe | Days | Expected Hourly Bars | Expected Daily Bars | Expected Weekly Bars | Expected Monthly Bars |
|-----------|------|----------------------|---------------------|----------------------|-----------------------|
| 1 day | 1 | ~6-7 (1 day only) | 1 | 0-1 (if week boundary) | 0-1 (if month boundary) |
| 2 days | 2 | ~13 (2 days max) | 2 | 0-1 | 0-1 |
| 1 week | 5-7 | ~13 (2 days max) | 5 (trading days) | 1 | 0-1 |
| 1 month | 30 | ~13 (2 days max) | ~21 (trading days) | ~4 | 1 |
| 3 months | 90 | ~13 (2 days max) | ~63 | ~13 | 3 |
| 6 months | 180 | ~13 (2 days max) | ~126 | ~26 | 6 |
| 1 year | 365 | ~13 (2 days max) | ~252 | ~52 | 12 |
| 2 years | 730 | ~13 (2 days max) | ~504 | ~104 | 24 |
| 5 years | 1825 | ~13 (2 days max) | ~1,260 | ~260 | 60 |

**Note**:
- Trading days assume 252 trading days/year (5 days/week minus holidays)
- Hourly data is LIMITED to maximum 2 days (most recent) regardless of timeframe
- For 1-day timeframe: load only prior 24 hours of hourly data
- For 2+ days timeframe: load maximum 2 days (48 hours) of hourly data

---

## Required Data Tables

For EVERY universe load job, TickStockPL MUST populate the following tables:

### 1. Symbols Table (MANDATORY)
**Table**: `symbols`

**Required for**: ALL jobs, ALL timeframes

**Fields to populate**:
```sql
INSERT INTO symbols (symbol, name, exchange, sector, industry, issuer, underlying_index)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (symbol) DO UPDATE SET
    name = EXCLUDED.name,
    exchange = EXCLUDED.exchange,
    sector = EXCLUDED.sector,
    industry = EXCLUDED.industry,
    issuer = EXCLUDED.issuer,
    underlying_index = EXCLUDED.underlying_index,
    last_updated = NOW();
```

**Data source**: Fetch from Massive API or other symbol metadata provider

**Logging required**:
```python
logger.info(f"✓ Symbol {symbol} registered: {name} ({issuer})")
```

---

### 2. Hourly OHLCV Data (MANDATORY)
**Table**: `ohlcv_hourly`

**Required for**: ALL jobs, ALL timeframes

**CRITICAL CONSTRAINT**: Maximum 2 days of hourly data, regardless of timeframe
- 1-day timeframe: Load only prior 24 hours
- 2+ days timeframe: Load maximum 2 days (48 hours) from most recent date

**Schema**:
```sql
CREATE TABLE ohlcv_hourly (
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open NUMERIC(10, 2),
    high NUMERIC(10, 2),
    low NUMERIC(10, 2),
    close NUMERIC(10, 2),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (symbol, timestamp)
);
```

**Fetch logic** (using Custom Bars API):
```python
from datetime import datetime, timedelta

def calculate_hourly_date_range(years):
    """Calculate hourly data date range with 2-day maximum"""
    end_date = datetime.now()

    if years <= 0.0027:  # 1 day or less
        # Load only prior 24 hours
        start_date = end_date - timedelta(hours=24)
    else:  # 2+ days
        # Load maximum 2 days (48 hours)
        start_date = end_date - timedelta(hours=48)

    return start_date, end_date

# Fetch hourly data using Custom Bars API
hourly_start, hourly_end = calculate_hourly_date_range(years)
hourly_bars = fetch_custom_bars(
    symbol=symbol,
    multiplier=1,
    timespan='hour',
    from_date=hourly_start,
    to_date=hourly_end
)

for bar in hourly_bars:
    insert_hourly_bar(
        symbol=symbol,
        timestamp=bar['timestamp'],
        open=bar['open'],
        high=bar['high'],
        low=bar['low'],
        close=bar['close'],
        volume=bar['volume']
    )
```

**Logging required**:
```python
logger.info(f"Fetching hourly data for {symbol}: {hourly_start} to {hourly_end} (max 2 days)")
logger.info(f"✓ Fetched {len(hourly_bars)} hourly bars from API")
logger.info(f"✓ Inserted {inserted_count} hourly bars into ohlcv_hourly")
```

**Expected bar counts**:
- 1 day: ~6-7 bars (1 trading day × 6.5 hours)
- 2+ days: ~13 bars (2 trading days × 6.5 hours) - MAXIMUM
- 1 week: ~13 bars (2 days max, NOT full week)
- 1 month: ~13 bars (2 days max, NOT full month)
- 3 months: ~13 bars (2 days max, NOT full 3 months)
- All longer timeframes: ~13 bars (2 days maximum)

**IMPORTANT**: Hourly data does NOT scale with timeframe - always capped at 2 days maximum.

---

### 3. Daily OHLCV Data (MANDATORY)
**Table**: `ohlcv_daily`

**Required for**: ALL jobs, ALL timeframes

**Schema**:
```sql
CREATE TABLE ohlcv_daily (
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(10, 2),
    high NUMERIC(10, 2),
    low NUMERIC(10, 2),
    close NUMERIC(10, 2),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (symbol, date)
);
```

**Fetch logic** (using Custom Bars API):
```python
# Fetch daily data using Custom Bars API
daily_bars = fetch_custom_bars(
    symbol=symbol,
    multiplier=1,
    timespan='day',
    from_date=start_date,
    to_date=end_date
)

for bar in daily_bars:
    insert_daily_bar(
        symbol=symbol,
        date=bar['date'],
        open=bar['open'],
        high=bar['high'],
        low=bar['low'],
        close=bar['close'],
        volume=bar['volume']
    )
```

**Logging required**:
```python
logger.info(f"Fetching daily data for {symbol}: {start_date} to {end_date}")
logger.info(f"✓ Fetched {len(daily_bars)} daily bars from API")
logger.info(f"✓ Inserted {inserted_count} daily bars into ohlcv_daily")
```

**Expected bar counts**:
- 1 day: 1 bar
- 2 days: 2 bars
- 1 week: ~5 bars (5 trading days)
- 1 month: ~21 bars
- 3 months: ~63 bars
- 6 months: ~126 bars
- 1 year: ~252 bars
- 2 years: ~504 bars
- 5 years: ~1,260 bars

---

### 4. Weekly OHLCV Data (MANDATORY)
**Table**: `ohlcv_weekly`

**Required for**: ALL jobs, ALL timeframes

**Schema**:
```sql
CREATE TABLE ohlcv_weekly (
    symbol VARCHAR(10) NOT NULL,
    week_start DATE NOT NULL,  -- Sunday of the week (Massive API convention)
    open NUMERIC(10, 2),
    high NUMERIC(10, 2),
    low NUMERIC(10, 2),
    close NUMERIC(10, 2),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (symbol, week_start)
);
```

**Fetch logic** (using Custom Bars API - NO manual aggregation):
```python
# Fetch weekly data using Custom Bars API
# API handles aggregation: weeks start Sunday 12:00 AM EST
weekly_bars = fetch_custom_bars(
    symbol=symbol,
    multiplier=1,
    timespan='week',
    from_date=start_date,
    to_date=end_date
)

for bar in weekly_bars:
    insert_weekly_bar(
        symbol=symbol,
        week_start=bar['date'],  # Sunday of the week
        open=bar['open'],
        high=bar['high'],
        low=bar['low'],
        close=bar['close'],
        volume=bar['volume']
    )
```

**Logging required**:
```python
logger.info(f"Fetching weekly data from Massive API...")
logger.info(f"✓ Fetched {len(weekly_bars)} weekly bars from API")
logger.info(f"✓ Inserted {inserted_count} weekly bars into ohlcv_weekly")
```

**Expected bar counts**:
- 1 day: 0-1 bar (1 if crossing week boundary)
- 2 days: 0-1 bar
- 1 week: 1 bar
- 1 month: ~4 bars
- 3 months: ~13 bars
- 6 months: ~26 bars
- 1 year: ~52 bars
- 2 years: ~104 bars
- 5 years: ~260 bars

---

### 5. Monthly OHLCV Data (MANDATORY)
**Table**: `ohlcv_monthly`

**Required for**: ALL jobs, ALL timeframes

**Schema**:
```sql
CREATE TABLE ohlcv_monthly (
    symbol VARCHAR(10) NOT NULL,
    month_start DATE NOT NULL,  -- 1st of the month
    open NUMERIC(10, 2),
    high NUMERIC(10, 2),
    low NUMERIC(10, 2),
    close NUMERIC(10, 2),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (symbol, month_start)
);
```

**Fetch logic** (using Custom Bars API - NO manual aggregation):
```python
# Fetch monthly data using Custom Bars API
# API handles aggregation: months start on 1st of month
monthly_bars = fetch_custom_bars(
    symbol=symbol,
    multiplier=1,
    timespan='month',
    from_date=start_date,
    to_date=end_date
)

for bar in monthly_bars:
    insert_monthly_bar(
        symbol=symbol,
        month_start=bar['date'],  # 1st of the month
        open=bar['open'],
        high=bar['high'],
        low=bar['low'],
        close=bar['close'],
        volume=bar['volume']
    )
```

**Logging required**:
```python
logger.info(f"Fetching monthly data from Massive API...")
logger.info(f"✓ Fetched {len(monthly_bars)} monthly bars from API")
logger.info(f"✓ Inserted {inserted_count} monthly bars into ohlcv_monthly")
```

**Expected bar counts**:
- 1 day: 0-1 bar (1 if crossing month boundary)
- 2 days: 0-1 bar
- 1 week: 0-1 bar
- 1 month: 1 bar
- 3 months: 3 bars
- 6 months: 6 bars
- 1 year: 12 bars
- 2 years: 24 bars
- 5 years: 60 bars

---

## Complete Implementation Flow

### Redis Message Format (Input)

TickStockPL receives job via Redis channel `tickstock.jobs.data_load`:

```json
{
  "job_id": "universe_load_1764505476_6849",
  "job_type": "csv_universe_load",
  "source": "etf_universe:etf_core",
  "symbols": ["SCHG", "VUG"],
  "years": 0.005479,
  "submitted_at": "2025-11-30T17:58:49.123456"
}
```

**Key fields**:
- `symbols`: Array of ticker symbols to load (REQUIRED - use this first!)
- `years`: Timeframe in years (e.g., 0.0027 = 1 day, 0.005479 = 2 days, 0.0192 = 1 week, 1.0 = 1 year)
- `source`: Description of where symbols came from (for logging)
- `csv_file`: Legacy field (fallback if symbols not provided)

---

### Job Handler Implementation (REQUIRED)

```python
def handle_csv_universe_load(job_data):
    """
    Handle universe load job - imports symbols + hourly/daily/weekly/monthly OHLCV data.

    REQUIREMENTS:
    1. Extract symbols array from Redis message
    2. Calculate date ranges from 'years' parameter
    3. Register symbols in symbols table
    4. Fetch and insert hourly OHLCV data (max 2 days) - Custom Bars API
    5. Fetch and insert daily OHLCV data (full timeframe) - Custom Bars API
    6. Fetch and insert weekly OHLCV data - Custom Bars API (NO manual aggregation)
    7. Fetch and insert monthly OHLCV data - Custom Bars API (NO manual aggregation)
    8. Log comprehensive progress
    9. Update job status in Redis

    NOTE: Uses Massive API Custom Bars endpoint for all timeframes.
    This eliminates manual aggregation and ensures API-consistent calculations.
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

    # FIX: Use symbols array from message (PRIORITY 1)
    symbols = job_data.get('symbols')

    # Fallback: Read from CSV file if symbols not provided (PRIORITY 2)
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
    from datetime import datetime, timedelta

    # Daily date range (full timeframe)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=int(years * 365))

    logger.info(f"Daily date range: {start_date} to {end_date}")
    logger.info(f"Expected trading days: ~{calculate_trading_days(start_date, end_date)}")

    # Hourly date range (max 2 days)
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
            # 3B. Fetch Hourly OHLCV Data (max 2 days) - Custom Bars API
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
            # 3C. Fetch Daily OHLCV Data - Custom Bars API
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
            # 3D. Fetch Weekly OHLCV Data - Custom Bars API (NO aggregation)
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
            # 3E. Fetch Monthly OHLCV Data - Custom Bars API (NO aggregation)
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

## Data Validation Requirements

### Daily Bar Validation

Before inserting, validate EACH bar:

```python
def validate_daily_bar(bar, symbol):
    """Validate daily OHLCV bar before insertion"""
    errors = []

    # Check required fields exist
    if 'date' not in bar or not bar['date']:
        errors.append("Missing date")
    if 'open' not in bar or bar['open'] is None:
        errors.append("Missing open")
    if 'high' not in bar or bar['high'] is None:
        errors.append("Missing high")
    if 'low' not in bar or bar['low'] is None:
        errors.append("Missing low")
    if 'close' not in bar or bar['close'] is None:
        errors.append("Missing close")
    if 'volume' not in bar or bar['volume'] is None:
        errors.append("Missing volume")

    # Check OHLC logic
    if bar.get('high') and bar.get('low') and bar['high'] < bar['low']:
        errors.append(f"High ({bar['high']}) < Low ({bar['low']})")

    if bar.get('open') and bar.get('high') and bar['open'] > bar['high']:
        errors.append(f"Open ({bar['open']}) > High ({bar['high']})")

    if bar.get('close') and bar.get('high') and bar['close'] > bar['high']:
        errors.append(f"Close ({bar['close']}) > High ({bar['high']})")

    if bar.get('open') and bar.get('low') and bar['open'] < bar['low']:
        errors.append(f"Open ({bar['open']}) < Low ({bar['low']})")

    if bar.get('close') and bar.get('low') and bar['close'] < bar['low']:
        errors.append(f"Close ({bar['close']}) < Low ({bar['low']})")

    # Check for negative prices
    if bar.get('open', 0) <= 0 or bar.get('high', 0) <= 0 or bar.get('low', 0) <= 0 or bar.get('close', 0) <= 0:
        errors.append(f"Negative or zero prices detected")

    # Check for negative volume
    if bar.get('volume', 0) < 0:
        errors.append(f"Negative volume: {bar['volume']}")

    if errors:
        logger.error(f"{symbol} [{bar.get('date')}] validation failed: {', '.join(errors)}")
        logger.error(f"Raw bar: {bar}")
        return False

    return True
```

---

## Error Handling Requirements

### API Failures

```python
def fetch_custom_bars(symbol, multiplier, timespan, from_date, to_date, max_retries=3):
    """
    Fetch OHLCV bars using Massive Custom Bars API with retry logic

    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        multiplier: Size of timespan multiplier (e.g., 1)
        timespan: Time window - 'minute', 'hour', 'day', 'week', 'month'
        from_date: Start date (datetime or date object)
        to_date: End date (datetime or date object)
        max_retries: Maximum retry attempts (default: 3)

    Returns:
        List of OHLCV bar dicts with keys: date, open, high, low, close, volume
    """
    import time

    # Format dates for API
    if hasattr(from_date, 'isoformat'):
        from_str = from_date.strftime('%Y-%m-%d')
        to_str = to_date.strftime('%Y-%m-%d')
    else:
        from_str = str(from_date)
        to_str = str(to_date)

    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching {symbol} {timespan} bars (attempt {attempt + 1}/{max_retries})...")

            # Call Massive Custom Bars API
            # /v2/aggs/ticker/{stocksTicker}/range/{multiplier}/{timespan}/{from}/{to}
            response = call_massive_api(
                endpoint=f'aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_str}/{to_str}',
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

### Database Insert Failures

```python
def insert_daily_bars(symbol, bars):
    """Insert daily bars with error handling"""
    from psycopg2 import IntegrityError

    inserted_count = 0

    for bar in bars:
        try:
            # Validate first
            if not validate_daily_bar(bar, symbol):
                continue

            # Insert with ON CONFLICT handling
            cursor.execute("""
                INSERT INTO ohlcv_daily (symbol, date, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    created_at = NOW()
            """, (symbol, bar['date'], bar['open'], bar['high'], bar['low'], bar['close'], bar['volume']))

            inserted_count += 1

        except IntegrityError as e:
            logger.error(f"Database integrity error for {symbol} [{bar['date']}]: {e}")
            conn.rollback()
            continue

        except Exception as e:
            logger.error(f"Database error for {symbol} [{bar['date']}]: {e}")
            conn.rollback()
            continue

    conn.commit()
    return inserted_count
```

---

## Post-Import Verification (MANDATORY)

After loading data, TickStockPL MUST verify completeness:

```python
def verify_import_completeness(symbol, start_date, end_date, expected_daily_bars, expected_hourly_bars):
    """Verify that data was loaded correctly"""

    verification = {
        'symbol': symbol,
        'date_range': f"{start_date} to {end_date}",
        'hourly': {'expected': expected_hourly_bars, 'actual': 0, 'success': False},
        'daily': {'expected': expected_daily_bars, 'actual': 0, 'success': False},
        'weekly': {'expected': 0, 'actual': 0, 'success': False},
        'monthly': {'expected': 0, 'actual': 0, 'success': False},
        'overall': False
    }

    # Check hourly data (last 2 days max)
    from datetime import datetime, timedelta
    hourly_start = datetime.now() - timedelta(hours=48)
    hourly_end = datetime.now()
    actual_hourly = count_bars('ohlcv_hourly', symbol, hourly_start, hourly_end)
    verification['hourly']['actual'] = actual_hourly
    verification['hourly']['success'] = actual_hourly >= expected_hourly_bars * 0.9  # 90% tolerance

    # Check daily data
    actual_daily = count_bars('ohlcv_daily', symbol, start_date, end_date)
    verification['daily']['actual'] = actual_daily
    verification['daily']['success'] = actual_daily >= expected_daily_bars * 0.9  # 90% tolerance

    # Check weekly data
    expected_weekly = calculate_expected_weekly_bars(start_date, end_date)
    actual_weekly = count_bars('ohlcv_weekly', symbol, start_date, end_date)
    verification['weekly']['expected'] = expected_weekly
    verification['weekly']['actual'] = actual_weekly
    verification['weekly']['success'] = actual_weekly >= expected_weekly * 0.9

    # Check monthly data
    expected_monthly = calculate_expected_monthly_bars(start_date, end_date)
    actual_monthly = count_bars('ohlcv_monthly', symbol, start_date, end_date)
    verification['monthly']['expected'] = expected_monthly
    verification['monthly']['actual'] = actual_monthly
    verification['monthly']['success'] = actual_monthly >= expected_monthly * 0.9

    # Overall success
    verification['overall'] = (
        verification['hourly']['success'] and
        verification['daily']['success'] and
        verification['weekly']['success'] and
        verification['monthly']['success']
    )

    # Log results
    if verification['overall']:
        logger.info(f"✓ VERIFICATION PASSED for {symbol}")
        logger.info(f"  Hourly: {actual_hourly}/{expected_hourly_bars} bars")
        logger.info(f"  Daily: {actual_daily}/{expected_daily_bars} bars")
        logger.info(f"  Weekly: {actual_weekly}/{expected_weekly} bars")
        logger.info(f"  Monthly: {actual_monthly}/{expected_monthly} bars")
    else:
        logger.error(f"✗ VERIFICATION FAILED for {symbol}")
        if not verification['hourly']['success']:
            logger.error(f"  Hourly: {actual_hourly}/{expected_hourly_bars} bars (INSUFFICIENT)")
        if not verification['daily']['success']:
            logger.error(f"  Daily: {actual_daily}/{expected_daily_bars} bars (INSUFFICIENT)")
        if not verification['weekly']['success']:
            logger.error(f"  Weekly: {actual_weekly}/{expected_weekly} bars (INSUFFICIENT)")
        if not verification['monthly']['success']:
            logger.error(f"  Monthly: {actual_monthly}/{expected_monthly} bars (INSUFFICIENT)")

    return verification
```

---

## Testing Instructions

### Test 1: 2-Day Import (SCHG, VUG)

**Setup**:
```bash
# Clear old failed data
psql -d tickstock -c "DELETE FROM ohlcv_hourly WHERE symbol IN ('SCHG', 'VUG') AND timestamp >= NOW() - INTERVAL '2 days';"
psql -d tickstock -c "DELETE FROM ohlcv_daily WHERE symbol IN ('SCHG', 'VUG') AND date >= '2025-11-28';"
psql -d tickstock -c "DELETE FROM ohlcv_weekly WHERE symbol IN ('SCHG', 'VUG') AND week_start >= '2025-11-25';"
psql -d tickstock -c "DELETE FROM ohlcv_monthly WHERE symbol IN ('SCHG', 'VUG') AND month_start >= '2025-11-01';"
```

**Submit Job** (from TickStockAppV2):
- Navigate to `/admin/historical-data`
- Select cached universe: "Core ETFs" OR enter "SCHG,VUG" manually
- Duration: 2 days
- Click "Load Universe Data"

**Expected TickStockPL Logs** (using Custom Bars API):
```
=== PROCESSING JOB universe_load_XXXXX ===
Source: etf_universe:etf_core (or manual entry)
Symbols in message: ['SCHG', 'VUG']
Symbol count: 2
Date range: 2025-11-28 to 2025-11-30
Expected trading days: ~2

============================================================
Processing SCHG (1/2)
============================================================
Fetching metadata for SCHG...
✓ Symbol registered: Schwab U.S. Large-Cap Growth ETF (Schwab)

Fetching hourly bars via Custom Bars API: 2025-11-28 12:00:00 to 2025-11-30 12:00:00...
Fetching SCHG hour bars (attempt 1/3)...
✓ API returned 13 hour bars for SCHG
✓ Fetched 13 hourly bars from API
✓ Inserted 13 bars into ohlcv_hourly

Fetching daily bars via Custom Bars API: 2025-11-28 to 2025-11-30...
Fetching SCHG day bars (attempt 1/3)...
✓ API returned 2 day bars for SCHG
✓ Fetched 2 daily bars from API
✓ Inserted 2 bars into ohlcv_daily

Fetching weekly bars via Custom Bars API: 2025-11-28 to 2025-11-30...
Fetching SCHG week bars (attempt 1/3)...
✓ API returned 1 week bars for SCHG
✓ Fetched 1 weekly bars from API
✓ Inserted 1 bars into ohlcv_weekly

Fetching monthly bars via Custom Bars API: 2025-11-28 to 2025-11-30...
Fetching SCHG month bars (attempt 1/3)...
✓ API returned 1 month bars for SCHG
✓ Fetched 1 monthly bars from API
✓ Inserted 1 bars into ohlcv_monthly

✓ Completed SCHG:
  Hourly: 13 bars
  Daily: 2 bars
  Weekly: 1 bars
  Monthly: 1 bars

============================================================
Processing VUG (2/2)
============================================================
[Same pattern as SCHG]

============================================================
JOB COMPLETE: universe_load_XXXXX
============================================================
Symbols loaded: 2/2
Symbols failed: 0
Hourly bars inserted: 26 (13 each via Custom Bars API)
Daily bars inserted: 4 (2 each via Custom Bars API)
Weekly bars inserted: 2 (1 each via Custom Bars API)
Monthly bars inserted: 2 (1 each via Custom Bars API)
```

**Verification**:
```sql
-- Should return ~13 bars each (2 days of hourly data)
SELECT symbol, COUNT(*) FROM ohlcv_hourly
WHERE symbol IN ('SCHG', 'VUG') AND timestamp >= NOW() - INTERVAL '2 days'
GROUP BY symbol;

-- Should return 2 bars each
SELECT symbol, COUNT(*) FROM ohlcv_daily
WHERE symbol IN ('SCHG', 'VUG') AND date >= '2025-11-28'
GROUP BY symbol;

-- Should return 1 bar each (week of Nov 25)
SELECT symbol, COUNT(*) FROM ohlcv_weekly
WHERE symbol IN ('SCHG', 'VUG') AND week_start >= '2025-11-25'
GROUP BY symbol;

-- Should return 1 bar each (November 2025)
SELECT symbol, COUNT(*) FROM ohlcv_monthly
WHERE symbol IN ('SCHG', 'VUG') AND month_start >= '2025-11-01'
GROUP BY symbol;
```

---

### Test 2: 90-Day Import (SPY)

**Submit Job**:
- Symbol: SPY
- Duration: 3 months
- Expected hourly bars: ~13 (2 days max, NOT 90 days)
- Expected daily bars: ~63 (3 months × 21 trading days)
- Expected weekly bars: ~13
- Expected monthly bars: 3

**Verification**:
```sql
-- Hourly data (max 2 days regardless of timeframe)
SELECT COUNT(*) FROM ohlcv_hourly
WHERE symbol = 'SPY' AND timestamp >= NOW() - INTERVAL '2 days';
-- Expected: ~13 bars (2 days × 6.5 hours)

SELECT COUNT(*) FROM ohlcv_daily
WHERE symbol = 'SPY' AND date >= CURRENT_DATE - INTERVAL '90 days';
-- Expected: ~63 bars

SELECT COUNT(*) FROM ohlcv_weekly
WHERE symbol = 'SPY' AND week_start >= CURRENT_DATE - INTERVAL '90 days';
-- Expected: ~13 bars

SELECT COUNT(*) FROM ohlcv_monthly
WHERE symbol = 'SPY' AND month_start >= CURRENT_DATE - INTERVAL '90 days';
-- Expected: 3 bars
```

---

## Success Criteria Checklist

For EVERY universe load job, verify:

### Minimum Requirements (MUST PASS):
- [ ] Symbols registered in `symbols` table with last_updated timestamp
- [ ] Hourly bars inserted for ALL symbols (max 2 days)
- [ ] Daily bars inserted for ALL symbols for the full date range
- [ ] Weekly bars created and inserted (if timeframe ≥ 1 week)
- [ ] Monthly bars created and inserted (if timeframe ≥ 1 month)
- [ ] TickStockPL logs show: "Symbols in message: [...]"
- [ ] TickStockPL logs show: "Fetching X hour bars via Custom Bars API"
- [ ] TickStockPL logs show: "Fetching X day bars via Custom Bars API"
- [ ] TickStockPL logs show: "Fetching X week bars via Custom Bars API"
- [ ] TickStockPL logs show: "Fetching X month bars via Custom Bars API"
- [ ] TickStockPL logs show: "✓ API returned X hour/day/week/month bars" where X > 0
- [ ] TickStockPL logs show: "✓ Inserted X bars into ohlcv_hourly/daily/weekly/monthly" where X > 0
- [ ] No API errors (404, 500, etc.) for valid symbols
- [ ] No database errors during insertion

### Full Requirements (MUST ACHIEVE):
- [ ] Hourly bar count ≥ 90% of expected (6-13 bars depending on 1 or 2 days)
- [ ] Daily bar count ≥ 90% of expected trading days
- [ ] Weekly bar count ≥ 90% of expected weeks
- [ ] Monthly bar count = expected months
- [ ] Job status updated to "completed" in Redis
- [ ] All data passes OHLC validation (High ≥ Low, Open/Close within High/Low)
- [ ] Verification logging shows "✓ VERIFICATION PASSED"

---

## Current Status: SCHG & VUG 2-Day Import

**Actual Results** (Nov 30, 2025):

| Timeframe | Expected | SCHG Actual | VUG Actual | Status |
|-----------|----------|-------------|------------|--------|
| Symbols | 2 | ✓ Registered | ✓ Registered | ✅ PASS |
| Hourly | ~13 bars each | 0 bars | 0 bars | ❌ FAIL |
| Daily | 2 bars each | 0 bars | 0 bars | ❌ FAIL |
| Weekly | 1 bar each | 0 bars | 0 bars | ❌ FAIL |
| Monthly | 1 bar each | 0 bars | 0 bars | ❌ FAIL |

**Diagnosis**: TickStockPL received symbols but did NOT fetch or insert ANY OHLCV data.

**Action Required**: Implement complete flow above to ensure hourly, daily, weekly, and monthly data is loaded.

---

**Status**: 🔴 IMPLEMENTATION REQUIRED
**Expected After Fix**: 🟢 ALL timeframes populated with complete data
