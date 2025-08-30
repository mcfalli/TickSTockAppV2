# Getting Historical Data for TickStock.ai

## Overview
This document outlines the process to seed the TickStock.ai database with historical OHLCV data using Polygon.io's REST API (since you have a subscription for premium access). This initial load populates tables like `ohlcv_daily` and `ohlcv_1min` (or even `ticks` for high-granularity), providing a solid foundation for pattern scanning and backtesting. Once seeded, real-time WebSockets (handled in TickStockApp) append live data for ongoing operations.

Key considerations:
- **Timeframe**: Start with 5-10 years for depth (e.g., from 2015-01-01 to current date) on daily aggregates—sufficient for long-term patterns like reversals or trends. For intraday (1min), limit to 1-2 years to manage volume and API costs/limits.
- **How Much Data**: Per-symbol basis; batch by date ranges to respect Polygon's rate limits (e.g., 5 calls/min on free tier, higher on paid). Aim for top symbols first (e.g., AAPL, TSLA) before scaling to 1000+. Data volume: ~2-5MB per symbol/year for daily; much larger (~GBs) for 1min—use compression in TimescaleDB.
- **Where It Resides**: Data fetched via Polygon's REST endpoints (e.g., https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2015-01-01/2025-08-23). Stored in our PostgreSQL DB per the schema in database_architecture.md.
- **Tools**: Python script with polygon's official client (pip install polygon-api-client; lightweight, no extra deps). Run manually or via cron for initial/backfill.

## Prerequisites
- Polygon API key (from your subscription; store in env var `POLYGON_API_KEY`).
- DB connection (SQLAlchemy engine from `src/data/loader.py`).
- Symbols list (from `symbols` table or a CSV).

## Steps to Load Historical Data
1. **Install Dependencies**: Add `polygon-api-client` to `requirements.txt` if not present. (Bootstrap-friendly: It's lightweight and handles auth/rate limiting.)
   
2. **Prepare Symbols**: Query `symbols` table or use a list (e.g., ['AAPL', 'GOOGL']).

3. **Fetch Data via REST**:
   - Use Polygon's Aggregates API for OHLCV bars (supports multipliers like 1/minute, 1/day).
   - Endpoint: `/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from}/{to}`.
   - Params: `adjusted=true` for splits/dividends; `sort=asc`; `limit=50000` (max per call).
   - Batch fetches: Loop over date ranges if >50k results (e.g., yearly chunks).

4. **Process and Insert to DB**:
   - Convert API response to pandas DataFrame.
   - Resample/aggregate if needed (e.g., minute to daily).
   - Upsert to appropriate tables (e.g., `ohlcv_daily` for daily data).
   - Handle errors: Rate limits (sleep/retry), duplicates (use ON CONFLICT).

5. **Run the Script**: Execute as a one-off (python get_historical.py) or integrate into `HistoricalLoader` class.

## Sample Python Script
```python
# In src/data/get_historical.py (or extend loader.py)
import os
import pandas as pd
from polygon import RESTClient
from sqlalchemy import create_engine
from datetime import datetime, timedelta

API_KEY = os.getenv('POLYGON_API_KEY')
DB_URL = 'postgresql://user:pass@localhost/tickstock_db'
engine = create_engine(DB_URL)
client = RESTClient(API_KEY)

def fetch_historical(symbol: str, start_date: str, end_date: str, timespan: str = 'day', multiplier: int = 1):
    """Fetch OHLCV from Polygon; timespan='minute' for intraday."""
    data = []
    current_start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    while current_start < end:
        current_end = min(current_start + timedelta(days=365), end)  # Yearly batches
        aggs = client.get_aggs(symbol, multiplier, timespan, current_start.strftime('%Y-%m-%d'), current_end.strftime('%Y-%m-%d'))
        for agg in aggs:
            data.append({
                'symbol': symbol,
                'timestamp': pd.to_datetime(agg.timestamp, unit='ms'),
                'open': agg.open,
                'high': agg.high,
                'low': agg.low,
                'close': agg.close,
                'volume': agg.volume
            })
        current_start = current_end + timedelta(days=1)
    return pd.DataFrame(data)

def load_to_db(df: pd.DataFrame, table: str = 'ohlcv_daily'):
    """Upsert to DB; adjust table for timeframe."""
    df.to_sql(table, engine, if_exists='append', index=False, method='multi')  # Use ON CONFLICT if needed

# Example Usage
symbols = ['AAPL', 'TSLA']
start = '2015-01-01'  # 10 years for daily
end = datetime.now().strftime('%Y-%m-%d')
for sym in symbols:
    df_daily = fetch_historical(sym, start, end, 'day')
    load_to_db(df_daily, 'ohlcv_daily')
    # For 1min: fetch_historical(sym, '2023-01-01', end, 'minute'), load to 'ohlcv_1min'
```

## Timeframe and Volume Guidelines
- **Daily (ohlcv_daily)**: 5-10 years (e.g., 2015-present); ~2500 rows/symbol; low volume, fast load.
- **1min (ohlcv_1min)**: 1-2 years (e.g., 2023-present); ~100k+ rows/symbol/year; batch carefully to avoid API throttling.
- **Ticks**: Only if needed for HFT patterns; use Polygon's `/v3/trades` but limit to recent days (high volume!).
- **Scaling**: Start with 10-20 symbols; monitor API usage (your subscription likely allows 100k+ calls/day). For more history, paginate or use bulk endpoints.

## Integration with Real-Time Flow
- After seeding, TickStockApp's WebSockets (from Polygon) append live data to `ticks` or `ohlcv_1min`.
- Nightly aggregator (from aggregator.py) rolls up to define/complete "the day" in `ohlcv_daily`.
- Blending: Historical from DB + live from WS ensures continuous scanning.

## Production Implementation

### Historical Data Loader
TickStock now includes a production-ready historical data loader at `src/data/historical_loader.py` with the following features:

- **Polygon.io Integration**: Direct REST API calls with proper rate limiting
- **Batch Processing**: Yearly chunks for daily data, monthly for 1-minute data
- **Smart Conflict Resolution**: ON CONFLICT DO UPDATE for seamless data updates
- **Symbol Universe Support**: Load from cache_entries (e.g., top_50 universe)
- **Progress Tracking**: Detailed logging and error handling
- **Flexible Timeframes**: Daily, 1-minute, or custom intervals

### Usage Examples

#### 1. Load Top 50 Stocks (1 Year Daily Data)
```bash
# Set API key first
export POLYGON_API_KEY="your_api_key_here"

# Load 1 year of daily data for all top 50 stocks
python -m src.data.historical_loader --universe top_50 --years 1 --timespan day

# Expected: ~18,250 records (50 symbols × ~365 days)
# Duration: ~15-20 minutes (rate limited to 5 calls/min)
```

#### 2. Load Specific Symbols
```bash
# Load 2 years for specific high-priority stocks
python -m src.data.historical_loader --symbols NVDA,AAPL,MSFT,TSLA --years 2

# Load 1-minute data (last 6 months to manage volume)
python -m src.data.historical_loader --symbols AAPL,SPY --years 0.5 --timespan minute
```

#### 3. Check Current Data Status
```bash
# View daily data summary
python -m src.data.historical_loader --summary

# View 1-minute data summary  
python -m src.data.historical_loader --summary --timespan minute
```

#### 4. Incremental Updates
```bash
# Add more symbols to existing dataset
python -m src.data.historical_loader --symbols GOOGL,AMZN,META --years 1

# Refresh existing data (will update with latest values)
python -m src.data.historical_loader --universe top_50 --years 1
```

### Data Handling Behavior

#### **IMPORTANT: Upsert Strategy (Not Overwrite)**
The loader uses `ON CONFLICT DO UPDATE` which means:

✅ **Safe Operations:**
- **New Records**: Inserted normally
- **Existing Records**: Updated with latest values (price corrections, volume adjustments)
- **Missing Records**: Previous data remains untouched
- **No Data Loss**: Never deletes existing records

❌ **What Does NOT Happen:**
- No table truncation or bulk deletion
- No overwrite of entire date ranges
- No loss of data outside the requested date range

#### **Example Behavior:**
```
Existing DB: AAPL 2023-01-01 to 2023-12-31 (365 records)
Load Command: --symbols AAPL --years 1 (loads 2024-01-01 to 2024-12-31)

Result:
✓ 2023 data: UNCHANGED (still 365 records)
✓ 2024 data: INSERTED (365 new records) 
✓ Total: 730 records for AAPL
```

#### **Overlap Handling:**
```
Existing: AAPL 2024-01-01: Open=150.00, Close=155.00
New Load: AAPL 2024-01-01: Open=150.50, Close=154.80

Result: UPDATED to new values (Open=150.50, Close=154.80)
Reason: Handles price corrections, adjusted closes, etc.
```

### Production Deployment

#### **1. Environment Setup**
```bash
# Required environment variables
export POLYGON_API_KEY="your_polygon_key"
export DATABASE_URI="postgresql://user:pass@host:port/tickstock"

# Optional: Override rate limiting
export POLYGON_RATE_LIMIT_DELAY=10  # seconds between calls
```

#### **2. Initial Data Load Strategy**
```bash
# Phase 1: Core symbols (5-10 stocks, test API limits)
python -m src.data.historical_loader --symbols AAPL,MSFT,NVDA,GOOGL,TSLA --years 2

# Phase 2: Top 20 expansion
python -m src.data.historical_loader --universe top_50 --years 1

# Phase 3: Full universe
python -m src.data.historical_loader --universe top_50 --years 5  # Full historical depth
```

#### **3. Monitoring and Maintenance**
```bash
# Weekly refresh (updates recent data)
python -m src.data.historical_loader --universe top_50 --years 0.1  # ~36 days

# Monthly full refresh
python -m src.data.historical_loader --universe top_50 --years 1

# Check data quality
python -m src.data.historical_loader --summary
```

### Performance Characteristics

| Data Type | Volume per Symbol | API Calls | Estimated Duration |
|-----------|-------------------|-----------|-------------------|
| 1 Year Daily | ~252 records | 1-2 calls | 12-24 seconds |
| 1 Year 1-Minute | ~100,000 records | 12-20 calls | 2-4 minutes |
| 5 Years Daily | ~1,260 records | 5-8 calls | 1-2 minutes |

**Rate Limiting**: 12-second delay between API calls (5 calls/minute safe limit)
**Batch Size**: 1,000 records per database insert
**Error Recovery**: Continues with other symbols if one fails

### Database Schema Compatibility

The loader works with the existing TickStock schema:

```sql
-- Daily data table
ohlcv_daily (
    symbol VARCHAR,    -- Must exist in symbols table (FK constraint)
    date DATE,         -- Primary key component
    open NUMERIC,
    high NUMERIC, 
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    created_at TIMESTAMP
);

-- 1-minute data table  
ohlcv_1min (
    symbol VARCHAR,    -- Must exist in symbols table (FK constraint)
    timestamp TIMESTAMP, -- Primary key component
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT
);
```

### Troubleshooting

#### **Common Issues:**
1. **"Symbol not found in symbols table"** → Add symbol to symbols table first
2. **Rate limit exceeded** → Increase POLYGON_RATE_LIMIT_DELAY 
3. **API key invalid** → Check POLYGON_API_KEY environment variable
4. **Database connection failed** → Verify DATABASE_URI

#### **Test Mode:**
```bash
# Test with small dataset first
python -m src.data.historical_loader --symbols AAPL --years 0.1  # ~25 days
```

Run this during Sprint 10+ for comprehensive historical data foundation supporting pattern analysis and backtesting operations.

## Related Documentation

- **[`../architecture/database-architecture.md`](../architecture/database-architecture.md)** - Database schema and table structures
- **[`../architecture/websockets-integration.md`](../architecture/websockets-integration.md)** - Real-time data integration after historical seeding
- **[`administration-system.md`](administration-system.md)** - System administration and monitoring