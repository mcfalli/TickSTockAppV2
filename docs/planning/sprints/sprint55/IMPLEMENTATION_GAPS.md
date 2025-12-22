# Implementation Gaps - SCHG_VUG_IMPORT_FAILURE_ANALYSIS.md

**Purpose**: Missing helper functions and configuration details needed by TickStockPL developer

---

## 1. Massive API Client Implementation

### Required Environment Variables
```bash
# .env or environment configuration
MASSIVE_API_KEY=your_api_key_here
MASSIVE_API_BASE_URL=https://api.polygon.io  # Or correct Massive URL
MASSIVE_API_TIMEOUT=30  # seconds
```

### API Client Function
```python
import requests
import os
from typing import Dict, Optional

def call_massive_api(endpoint: str, params: Optional[Dict] = None) -> requests.Response:
    """
    Call Massive API with authentication and error handling

    Args:
        endpoint: API path without base URL (e.g., 'aggs/ticker/AAPL/range/1/day/2023-01-01/2023-12-31')
        params: Query parameters (e.g., {'adjusted': 'true', 'sort': 'asc'})

    Returns:
        requests.Response object

    Raises:
        requests.exceptions.RequestException on network/HTTP errors
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
```

**Note**: Verify if Massive uses `apiKey` query param or `Authorization` header. Adjust accordingly.

---

## 2. Database Helper Functions

### Database Connection Setup
```python
import psycopg2
from psycopg2.extras import execute_batch
from contextlib import contextmanager

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
```

### Insert Functions (Batch Optimized)
```python
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
                bar['date'],  # datetime object
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

## 3. Symbol Metadata Functions

### Fetch Symbol Metadata
```python
def fetch_symbol_metadata(symbol: str) -> Optional[Dict]:
    """
    Fetch symbol metadata from Massive API

    Args:
        symbol: Stock ticker

    Returns:
        Dict with keys: name, exchange, sector, industry, issuer, underlying_index
        None if not found
    """
    try:
        # Massive API endpoint for ticker details
        response = call_massive_api(f'reference/tickers/{symbol}')

        if response.status_code == 200:
            data = response.json()
            result = data.get('results', {})

            return {
                'name': result.get('name'),
                'exchange': result.get('primary_exchange'),
                'sector': result.get('sic_description'),  # Or appropriate field
                'industry': result.get('industry'),
                'issuer': result.get('issuer'),  # May not be in API
                'underlying_index': None  # May need separate lookup for ETFs
            }
        elif response.status_code == 404:
            logger.warning(f"Symbol {symbol} not found in Massive API")
            return None
        else:
            logger.error(f"Metadata fetch failed for {symbol}: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error fetching metadata for {symbol}: {e}")
        return None


def register_symbol(symbol: str, name: str = None, exchange: str = None,
                   sector: str = None, industry: str = None,
                   issuer: str = None, underlying_index: str = None) -> None:
    """
    Register symbol in database with metadata

    Args:
        symbol: Stock ticker (REQUIRED)
        name: Company/ETF name (optional)
        exchange: Exchange code (optional)
        sector: Sector classification (optional)
        industry: Industry classification (optional)
        issuer: ETF issuer (optional)
        underlying_index: ETF underlying index (optional)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO symbols (symbol, name, exchange, sector, industry, issuer, underlying_index)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol) DO UPDATE SET
                name = COALESCE(EXCLUDED.name, symbols.name),
                exchange = COALESCE(EXCLUDED.exchange, symbols.exchange),
                sector = COALESCE(EXCLUDED.sector, symbols.sector),
                industry = COALESCE(EXCLUDED.industry, symbols.industry),
                issuer = COALESCE(EXCLUDED.issuer, symbols.issuer),
                underlying_index = COALESCE(EXCLUDED.underlying_index, symbols.underlying_index),
                last_updated = NOW()
        """, (symbol, name, exchange, sector, industry, issuer, underlying_index))

        cursor.close()
        logger.info(f"✓ Symbol {symbol} registered: {name or 'N/A'} ({issuer or 'N/A'})")
```

---

## 4. Redis Job Status Functions

### Redis Client Setup
```python
import redis
import json

def get_redis_client():
    """Get Redis client from environment configuration"""
    return redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        decode_responses=True
    )


def update_job_status(job_id: str, status: str, **kwargs) -> None:
    """
    Update job status in Redis

    Args:
        job_id: Job identifier
        status: One of 'processing', 'completed', 'completed_with_errors', 'failed'
        **kwargs: Additional fields (progress, message, results, etc.)
    """
    redis_client = get_redis_client()

    # Prepare status update
    status_data = {
        'job_id': job_id,
        'status': status,
        'updated_at': datetime.now().isoformat(),
        **kwargs
    }

    # Store in Redis hash (for querying)
    redis_client.hset(f"job:{job_id}", mapping=status_data)

    # Publish status update to channel (for real-time monitoring)
    redis_client.publish('tickstock.jobs.status', json.dumps(status_data))

    logger.info(f"Job {job_id} status updated: {status}")
```

---

## 5. CSV Symbol Loading (Fallback)

```python
import csv

def load_symbols_from_csv(csv_file: str) -> list:
    """
    Load symbols from CSV file

    Args:
        csv_file: Path to CSV file with 'symbol' column

    Returns:
        List of symbol strings
    """
    symbols = []

    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                symbol = row.get('symbol') or row.get('Symbol')
                if symbol:
                    symbols.append(symbol.strip().upper())

        logger.info(f"Loaded {len(symbols)} symbols from {csv_file}")
        return symbols

    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_file}")
        return []
    except Exception as e:
        logger.error(f"Error reading CSV {csv_file}: {e}")
        return []
```

---

## 6. Environment Configuration Summary

### Required Environment Variables
```bash
# Massive API
MASSIVE_API_KEY=your_api_key
MASSIVE_API_BASE_URL=https://api.polygon.io
MASSIVE_API_TIMEOUT=30

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tickstock
DB_USER=postgres
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Logging
LOG_LEVEL=INFO
```

---

## 7. Dependencies Required

```python
# requirements.txt additions for TickStockPL
requests>=2.31.0
psycopg2-binary>=2.9.9
redis>=5.0.0
python-dotenv>=1.0.0  # For .env file support
```

---

## Integration Checklist

Before implementation:
- [ ] Verify Massive API authentication method (query param vs header)
- [ ] Confirm Massive API base URL
- [ ] Test API rate limits (requests per minute/second)
- [ ] Verify database schema matches (ohlcv_hourly.timestamp vs date?)
- [ ] Confirm Redis job status channel name
- [ ] Set up environment variables in TickStockPL environment
- [ ] Install required dependencies
- [ ] Test `call_massive_api()` with sample request
- [ ] Test database insert with sample data
- [ ] Verify Redis connection and pub/sub channels

---

**Status**: Implementation guide ready for TickStockPL developer
**Next Step**: Add these helper functions to TickStockPL codebase, then follow SCHG_VUG_IMPORT_FAILURE_ANALYSIS.md
