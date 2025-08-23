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

Run this script during setup (e.g., Sprint 9). If Polygon limits hit, fallback to yfinance for free symbols. Let's test on AAPL first—what timeframe/symbols to prioritize?