# TickStockPL Integration Requirements

**Document Purpose**: Critical integration requirements for TickStockPL to successfully communicate with TickStockAppV2 through Redis pub-sub architecture.

**Status**: REQUIRED FOR INTEGRATION
**Date**: 2025-09-17
**Priority**: CRITICAL

---

## ⚠️ IMPORTANT DISCLAIMER

**This document provides REFERENCE IMPLEMENTATIONS and EXAMPLES.**

- **DO NOT** copy-paste code directly without understanding your specific architecture
- **DO** use these as templates and adapt to your actual implementation
- **DO** maintain your existing pattern detection logic and enhance it with integration logging
- **DO** test thoroughly with your actual service architecture

The code examples show the REQUIRED DATA STRUCTURES and INTEGRATION POINTS but should be integrated into your existing TickStockPL architecture, not replace it.

---

## Executive Summary

TickStockAppV2 (consumer) is fully operational and listening for pattern events. For successful integration, TickStockPL (producer) must implement database logging, Redis publishing with specific event structure, and heartbeat monitoring.

## Critical Requirements (MUST HAVE)

### These are NON-NEGOTIABLE for integration:

1. **Event Structure**: The `event_type`, `source`, and `data` fields with exact naming
2. **Pattern Field**: Must use `'pattern'` NOT `'pattern_name'` in the data payload
3. **Flow ID**: Must include UUID `flow_id` in data for tracking
4. **Redis Channel**: Must publish to `'tickstock.events.patterns'`
5. **Database Logging**: Must log `PATTERN_PUBLISHED` checkpoint to integration_events table

### These are FLEXIBLE based on your implementation:

1. **Pattern Detection Logic**: Use your existing algorithms
2. **Market Data Source**: Your choice (Polygon, synthetic, etc.)
3. **Service Architecture**: Adapt to your existing structure
4. **Timing/Intervals**: Adjust based on your requirements
5. **Error Handling**: Implement per your standards

## 1. Database Integration Logging (REQUIRED)

### Database Connection Configuration
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'tickstock',
    'user': 'app_readwrite',
    'password': 'LJI48rUEkUpe6e'  # TODO: Change for production
}
```

### Pattern Publishing with Database Logging
```python
import uuid
import psycopg2
import json
import time
import redis

def publish_pattern(symbol, pattern_name, confidence, tier='intraday', price_change=0.0, current_price=0.0):
    """Publish pattern to Redis and log to database for integration tracking"""

    # Generate unique flow ID for end-to-end tracking
    flow_id = str(uuid.uuid4())

    # Create pattern event with EXACT structure required
    pattern_event = {
        'event_type': 'pattern_detected',
        'source': 'TickStockPL',
        'timestamp': time.time(),
        'data': {
            'symbol': symbol,
            'pattern': pattern_name,      # CRITICAL: Use 'pattern' NOT 'pattern_name'
            'confidence': confidence,
            'flow_id': flow_id,          # REQUIRED for tracking
            'tier': tier,
            'price_change': price_change,
            'current_price': current_price
        }
    }

    # Log to database FIRST (for audit trail)
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT log_integration_event(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            flow_id,
            'pattern_detected',
            'TickStockPL',
            'PATTERN_PUBLISHED',
            'tickstock.events.patterns',
            symbol,
            pattern_name,
            confidence,
            None,  # user_count
            json.dumps({'tier': tier, 'timestamp': time.time()})
        ))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"[DB LOG] Pattern published: {pattern_name} @ {symbol}")
    except Exception as e:
        print(f"[DB ERROR] Failed to log pattern: {e}")

    # Publish to Redis
    try:
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        channel = 'tickstock.events.patterns'
        redis_client.publish(channel, json.dumps(pattern_event))
        print(f"[REDIS] Pattern published to channel: {channel}")
    except Exception as e:
        print(f"[REDIS ERROR] Failed to publish pattern: {e}")

    return flow_id
```

## 2. Heartbeat Monitoring (RECOMMENDED)

### Implementation
```python
import threading

class HeartbeatMonitor:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.pattern_count = 0
        self.start_time = time.time()
        self.last_pattern_time = None

    def log_heartbeat(self):
        """Log heartbeat to Redis and database every 60 seconds"""
        try:
            # Update Redis heartbeat
            self.redis_client.set('tickstock:producer:heartbeat', time.time())

            # Log to database
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()

            uptime = int(time.time() - self.start_time)

            cursor.execute("""
                SELECT log_integration_event(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                str(uuid.uuid4()),
                'heartbeat',
                'TickStockPL',
                'PRODUCER_ALIVE',
                None,  # channel
                None,  # symbol
                None,  # pattern_name
                None,  # confidence
                None,  # user_count
                json.dumps({
                    'patterns_detected': self.pattern_count,
                    'uptime_seconds': uptime,
                    'last_pattern_time': self.last_pattern_time
                })
            ))
            conn.commit()
            cursor.close()
            conn.close()

            print(f"[HEARTBEAT] Alive - Patterns: {self.pattern_count}, Uptime: {uptime}s")

        except Exception as e:
            print(f"[HEARTBEAT ERROR] {e}")

        # Schedule next heartbeat
        threading.Timer(60.0, self.log_heartbeat).start()

    def start(self):
        """Start heartbeat monitoring"""
        self.log_heartbeat()
```

## 3. Redis Channel Configuration (CRITICAL)

### Required Channels
```python
REDIS_CHANNELS = {
    'patterns': 'tickstock.events.patterns',              # Pattern events
    'backtest_progress': 'tickstock.events.backtesting.progress',  # Progress updates
    'backtest_results': 'tickstock.events.backtesting.results',    # Results
    'health': 'tickstock.health.status'                   # System health
}
```

## 4. Event Structure Specification (EXACT FORMAT REQUIRED)

### Pattern Event Structure
```python
{
    'event_type': 'pattern_detected',  # MUST be this exact string
    'source': 'TickStockPL',          # MUST be this exact string
    'timestamp': 1234567890.123,      # Unix timestamp (float)
    'data': {                         # MUST be nested in 'data' field
        'symbol': 'AAPL',             # Stock symbol (string)
        'pattern': 'Volume_Spike',    # Pattern name - USE 'pattern' NOT 'pattern_name'!
        'confidence': 0.85,           # Confidence score (0.0 to 1.0)
        'flow_id': 'uuid-here',       # REQUIRED: UUID string for tracking

        # Optional fields:
        'tier': 'intraday',           # Pattern tier
        'price_change': 2.5,          # Price change percentage
        'current_price': 185.50,      # Current price
        'volume': 1000000,            # Volume
        'timestamp': 1234567890.123   # Pattern detection timestamp
    }
}
```

### Critical Field Requirements
- ✅ **event_type**: MUST be `'pattern_detected'`
- ✅ **source**: MUST be `'TickStockPL'`
- ✅ **data.pattern**: MUST use field name `'pattern'` (NOT `'pattern_name'`)
- ✅ **data.flow_id**: MUST include UUID for tracking
- ✅ **timestamp**: MUST be Unix timestamp (time.time())

## 5. Test Pattern Generator

Create file: `scripts/test_pattern_event.py`

```python
#!/usr/bin/env python3
"""Test pattern event generator for TickStockPL integration testing"""

import redis
import json
import time
import uuid
import psycopg2
import random

# Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'tickstock',
    'user': 'app_readwrite',
    'password': 'LJI48rUEkUpe6e'
}

def generate_test_pattern():
    """Generate a test pattern event"""
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
    patterns = ['Volume_Spike', 'Price_Breakout', 'Support_Test', 'Resistance_Break']

    symbol = random.choice(symbols)
    pattern_name = random.choice(patterns)
    confidence = round(random.uniform(0.7, 0.99), 2)
    price_change = round(random.uniform(-5.0, 5.0), 2)
    current_price = round(random.uniform(100, 500), 2)

    flow_id = str(uuid.uuid4())

    # Create event
    test_pattern = {
        'event_type': 'pattern_detected',
        'source': 'TickStockPL',
        'timestamp': time.time(),
        'data': {
            'symbol': symbol,
            'pattern': pattern_name,  # Use 'pattern' field
            'confidence': confidence,
            'flow_id': flow_id,
            'tier': 'test',
            'price_change': price_change,
            'current_price': current_price
        }
    }

    # Log to database
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT log_integration_event(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            flow_id,
            'pattern_detected',
            'TickStockPL',
            'PATTERN_PUBLISHED',
            'tickstock.events.patterns',
            symbol,
            pattern_name,
            confidence,
            None,
            json.dumps({'test': True, 'timestamp': time.time()})
        ))
        conn.commit()
        print(f"[DB] Logged test pattern: {pattern_name} @ {symbol}")
    except Exception as e:
        print(f"[DB ERROR] {e}")

    # Publish to Redis
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        channel = 'tickstock.events.patterns'
        subscribers = r.publish(channel, json.dumps(test_pattern))
        print(f"[REDIS] Published to {subscribers} subscribers")
        print(f"Pattern: {pattern_name} @ {symbol} (confidence: {confidence})")
        print(f"Flow ID: {flow_id}")
    except Exception as e:
        print(f"[REDIS ERROR] {e}")

    return flow_id

if __name__ == "__main__":
    print("TickStockPL Test Pattern Generator")
    print("=" * 50)

    # Generate single test pattern
    flow_id = generate_test_pattern()

    print("\nTest pattern published successfully!")
    print(f"Track this pattern with flow_id: {flow_id}")
    print("\nCheck integration with:")
    print("  python scripts/monitor_system_health.py")
```

## 6. Minimum Working Service Implementation

File: `scripts/services/run_pattern_detection_service.py`

```python
#!/usr/bin/env python3
"""TickStockPL Pattern Detection Service - Minimum Working Implementation"""

import redis
import psycopg2
import time
import threading
import uuid
import json
import signal
import sys
from datetime import datetime

class PatternDetectionService:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'tickstock',
            'user': 'app_readwrite',
            'password': 'LJI48rUEkUpe6e'
        }
        self.running = True
        self.pattern_count = 0
        self.start_time = time.time()
        self.last_pattern_time = None

    def detect_patterns(self):
        """Main pattern detection loop - implement your logic here"""
        while self.running:
            try:
                # TODO: Replace with actual pattern detection logic
                # patterns = self.analyze_market_data()

                # For now, generate synthetic patterns for testing
                if time.time() % 30 < 1:  # Every 30 seconds
                    self.publish_pattern({
                        'symbol': 'TEST',
                        'name': 'Synthetic_Pattern',
                        'confidence': 0.85,
                        'tier': 'synthetic',
                        'price_change': 1.5,
                        'current_price': 100.0
                    })

                time.sleep(1)

            except Exception as e:
                print(f"[ERROR] Pattern detection error: {e}")
                time.sleep(5)

    def publish_pattern(self, pattern_info):
        """Publish pattern to Redis and log to database"""
        flow_id = str(uuid.uuid4())

        # Create event with required structure
        event = {
            'event_type': 'pattern_detected',
            'source': 'TickStockPL',
            'timestamp': time.time(),
            'data': {
                'symbol': pattern_info['symbol'],
                'pattern': pattern_info['name'],  # Must be 'pattern' field
                'confidence': pattern_info['confidence'],
                'flow_id': flow_id,
                'tier': pattern_info.get('tier', 'unknown'),
                'price_change': pattern_info.get('price_change', 0),
                'current_price': pattern_info.get('current_price', 0)
            }
        }

        # Log to database
        self.log_to_database(flow_id, pattern_info)

        # Publish to Redis
        channel = 'tickstock.events.patterns'
        self.redis_client.publish(channel, json.dumps(event))

        self.pattern_count += 1
        self.last_pattern_time = time.time()

        print(f"[PATTERN] Published: {pattern_info['name']} @ {pattern_info['symbol']}")

    def log_to_database(self, flow_id, pattern_info):
        """Log pattern to integration_events table"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT log_integration_event(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                flow_id,
                'pattern_detected',
                'TickStockPL',
                'PATTERN_PUBLISHED',
                'tickstock.events.patterns',
                pattern_info['symbol'],
                pattern_info['name'],
                pattern_info['confidence'],
                None,
                json.dumps({'tier': pattern_info.get('tier', 'unknown')})
            ))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[DB ERROR] {e}")

    def log_heartbeat(self):
        """Send heartbeat every 60 seconds"""
        while self.running:
            try:
                # Update Redis heartbeat
                self.redis_client.set('tickstock:producer:heartbeat', time.time())

                # Log to database
                conn = psycopg2.connect(**self.db_config)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT log_integration_event(
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    str(uuid.uuid4()),
                    'heartbeat',
                    'TickStockPL',
                    'PRODUCER_ALIVE',
                    None, None, None, None, None,
                    json.dumps({
                        'patterns_detected': self.pattern_count,
                        'uptime_seconds': int(time.time() - self.start_time),
                        'last_pattern_time': self.last_pattern_time
                    })
                ))
                conn.commit()
                cursor.close()
                conn.close()

                print(f"[HEARTBEAT] Patterns: {self.pattern_count}, Uptime: {int(time.time() - self.start_time)}s")

            except Exception as e:
                print(f"[HEARTBEAT ERROR] {e}")

            time.sleep(60)

    def shutdown(self, signum=None, frame=None):
        """Graceful shutdown"""
        print("\n[SHUTDOWN] Stopping pattern detection service...")
        self.running = False
        sys.exit(0)

    def start(self):
        """Start the service"""
        print("="*60)
        print("TickStockPL Pattern Detection Service")
        print(f"Started: {datetime.now()}")
        print("="*60)

        # Register shutdown handler
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        # Test connections
        try:
            self.redis_client.ping()
            print("[OK] Redis connected")
        except Exception as e:
            print(f"[ERROR] Redis connection failed: {e}")
            return

        try:
            conn = psycopg2.connect(**self.db_config)
            conn.close()
            print("[OK] Database connected")
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return

        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.log_heartbeat, daemon=True)
        heartbeat_thread.start()
        print("[OK] Heartbeat started (60s interval)")

        # Start pattern detection
        print("[OK] Pattern detection started")
        print("="*60)
        print("Press Ctrl+C to stop")
        print("")

        self.detect_patterns()

if __name__ == "__main__":
    service = PatternDetectionService()
    service.start()
```

## 7. Startup Checklist

When starting `run_pattern_detection_service.py`, verify:

- [ ] Redis connection established (localhost:6379)
- [ ] Database connection established (localhost:5432)
- [ ] Startup event logged to `integration_events` table
- [ ] Heartbeat timer started (60-second interval)
- [ ] Market data source connected (Polygon.io API or synthetic)
- [ ] Pattern detection loop running
- [ ] Test pattern successfully published and logged

## 8. Verification Commands

### Check Pattern Publishing
```bash
# Monitor Redis channel for patterns
redis-cli
> SUBSCRIBE tickstock.events.patterns
```

### Check Database Logging
```bash
# View TickStockPL events
PGPASSWORD=LJI48rUEkUpe6e psql -h localhost -p 5432 -U app_readwrite -d tickstock -c "SELECT timestamp, checkpoint, symbol, pattern_name FROM integration_events WHERE source_system='TickStockPL' ORDER BY timestamp DESC LIMIT 10;"
```

### Check Heartbeat
```bash
# Get last heartbeat timestamp
redis-cli GET tickstock:producer:heartbeat
```

### Monitor Integration
```bash
# From TickStockAppV2 directory
cd C:/Users/McDude/TickStockAppV2
python scripts/monitor_system_health.py --watch
```

## 9. Troubleshooting Guide

### Issue: No Patterns Detected
**Symptoms**: Service running but no patterns published
**Solutions**:
- Verify market data connection (API key, network)
- Check if market is open (or enable synthetic data)
- Verify pattern detection algorithms are enabled
- Test with `scripts/test_pattern_event.py`

### Issue: Patterns Not Received by TickStockAppV2
**Symptoms**: Patterns published but not processed
**Solutions**:
- Verify channel name exactly: `'tickstock.events.patterns'`
- Ensure `'pattern'` field used (NOT `'pattern_name'`)
- Check `flow_id` is valid UUID
- Confirm TickStockAppV2 is running

### Issue: Database Logging Fails
**Symptoms**: Patterns work but no database records
**Solutions**:
- Check PostgreSQL on port 5432
- Verify `log_integration_event` function exists
- Ensure UUID format for flow_id
- Check database credentials

### Issue: No Heartbeat
**Symptoms**: No heartbeat in Redis or database
**Solutions**:
- Verify heartbeat thread started
- Check Redis connection
- Verify 60-second timer running
- Check for thread exceptions

## 10. Success Criteria

Integration is successful when:

1. ✅ TickStockPL heartbeats appear every 60 seconds in database
2. ✅ Pattern events show in `integration_events` with `PATTERN_PUBLISHED` checkpoint
3. ✅ TickStockAppV2 logs `EVENT_RECEIVED`, `EVENT_PARSED`, `WEBSOCKET_DELIVERED`
4. ✅ `pattern_flow_analysis` view shows complete flows with <100ms latency
5. ✅ Monitor script shows both systems active and patterns flowing

## 11. Historical Data Import Integration (NEW - CRITICAL)

### Overview
TickStockAppV2 submits historical data import jobs via Redis pub-sub. TickStockPL must subscribe and process these jobs to populate the OHLCV tables.

### 11.1 Job Subscription Required

**Channel to Subscribe**: `tickstock.jobs.data_load`

**Current Status**: **0 subscribers detected** - TickStockPL is NOT listening

### 11.2 Job Message Format

When TickStockAppV2 submits a CSV universe load job:

```json
{
    "job_id": "job_20241030_145623_abc123",
    "job_type": "csv_universe_load",
    "csv_file": "sp_500.csv",
    "universe_type": "sp_500",
    "years": 1,
    "include_ohlcv": true,
    "requested_by": "admin",
    "timestamp": "2024-10-30T14:56:23.123456"
}
```

### 11.3 Expected Processing Workflow

1. **Subscribe to Redis Channel**:
   ```python
   pubsub = redis_client.pubsub()
   pubsub.subscribe('tickstock.jobs.data_load')
   ```

2. **Parse CSV Universe**:
   - Load symbols from `csv_file` (e.g., sp_500.csv, nasdaq_100.csv)
   - Universe files located in standard data directory

3. **Fetch Historical Data from Polygon.io**:
   - Use specified `years` parameter for timeframe
   - Respect API rate limits (5 calls/minute for free tier)
   - Implement exponential backoff for rate limit errors

4. **Load Data into ALL Timeframe Tables**:
   ```sql
   -- Required tables (all must be populated):
   ohlcv_1min    -- Minute-level data (TIMESTAMPTZ)
   ohlcv_hourly  -- Hourly aggregations (TIMESTAMPTZ)
   ohlcv_daily   -- Daily OHLCV (DATE)
   ohlcv_weekly  -- Weekly aggregations (DATE for week_ending)
   ohlcv_monthly -- Monthly aggregations (DATE for month_ending)
   ```

### 11.4 Job Status Updates

Publish status updates to Redis for UI tracking:

**Key Pattern**: `tickstock.jobs.status:{job_id}`

```python
status_update = {
    "job_id": "job_20241030_145623_abc123",
    "status": "running",  # running|completed|failed
    "progress": 45,  # Percentage complete
    "total_symbols": 500,
    "processed_symbols": 225,
    "successful_symbols": ["AAPL", "MSFT", "GOOGL"],
    "failed_symbols": ["XYZ"],
    "error_message": None,  # Or error details
    "started_at": "2024-10-30T14:56:30",
    "completed_at": None  # Set when complete
}

redis_client.set(
    f"tickstock.jobs.status:{job_id}",
    json.dumps(status_update),
    ex=86400  # 24-hour TTL
)
```

### 11.5 Database Schema Requirements

```sql
-- Minute data (market hours only)
CREATE TABLE IF NOT EXISTS ohlcv_1min (
    symbol VARCHAR(10),
    timestamp TIMESTAMPTZ,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    volume BIGINT,
    PRIMARY KEY (symbol, timestamp)
);

-- Hourly aggregations
CREATE TABLE IF NOT EXISTS ohlcv_hourly (
    symbol VARCHAR(10),
    timestamp TIMESTAMPTZ,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    volume BIGINT,
    PRIMARY KEY (symbol, timestamp)
);

-- Daily data (most important)
CREATE TABLE IF NOT EXISTS ohlcv_daily (
    symbol VARCHAR(10),
    date DATE,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    volume BIGINT,
    PRIMARY KEY (symbol, date)
);

-- Weekly aggregations
CREATE TABLE IF NOT EXISTS ohlcv_weekly (
    symbol VARCHAR(10),
    week_ending DATE,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    volume BIGINT,
    PRIMARY KEY (symbol, week_ending)
);

-- Monthly aggregations
CREATE TABLE IF NOT EXISTS ohlcv_monthly (
    symbol VARCHAR(10),
    month_ending DATE,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    volume BIGINT,
    PRIMARY KEY (symbol, month_ending)
);
```

### 11.6 Current Database State (NEEDS FIXING)

```
ohlcv_daily:   23,779 records (STALE - last update Sept 18)
ohlcv_1min:    0 records (EMPTY - never populated)
ohlcv_hourly:  0 records (EMPTY - never populated)
ohlcv_weekly:  0 records (EMPTY - never populated)
ohlcv_monthly: 0 records (EMPTY - never populated)
```

### 11.7 Implementation Checklist

- [ ] Subscribe to `tickstock.jobs.data_load` Redis channel
- [ ] Parse incoming job messages correctly
- [ ] Load CSV universe files (sp_500.csv, nasdaq_100.csv, etc.)
- [ ] Implement Polygon.io API client with rate limiting
- [ ] Create data aggregation functions:
  - [ ] Minute → Hourly aggregation
  - [ ] Hourly → Daily aggregation
  - [ ] Daily → Weekly aggregation
  - [ ] Daily → Monthly aggregation
- [ ] Batch insert data efficiently (use COPY or bulk inserts)
- [ ] Publish job status updates to Redis
- [ ] Handle errors gracefully with detailed logging
- [ ] Respect market calendars (skip weekends/holidays)

### 11.8 Performance Requirements

- **Processing Speed**: ~100-200 symbols per minute (API limited)
- **Batch Size**: Process in chunks of 50-100 symbols
- **Database Inserts**: Use bulk operations (1000+ records at once)
- **Memory Management**: Stream data, don't load all in memory
- **Status Updates**: Every 10 symbols or 30 seconds

### 11.9 Error Handling

Handle these scenarios gracefully:

1. **API Rate Limits** (429 errors):
   ```python
   if response.status_code == 429:
       wait_time = int(response.headers.get('X-RateLimit-Reset', 60))
       time.sleep(wait_time)
   ```

2. **Invalid Symbols**: Log and continue with remaining symbols

3. **Network Failures**: Implement retry with exponential backoff

4. **Database Errors**: Use transactions, rollback on failure

5. **Memory Issues**: Process in batches, clear data after insert

### 11.10 Testing the Job Processor

1. **Check Redis Subscription**:
   ```bash
   redis-cli PUBSUB NUMSUB tickstock.jobs.data_load
   # Should return: tickstock.jobs.data_load 1 (or more)
   ```

2. **Submit Test Job** (from TickStockAppV2):
   - Navigate to Admin → Historical Data
   - Select "sp_500.csv" and "1 year"
   - Click "Load CSV Universe"

3. **Monitor Job Progress**:
   ```bash
   # Watch for job messages
   redis-cli SUBSCRIBE tickstock.jobs.data_load

   # Check job status
   redis-cli GET "tickstock.jobs.status:job_*"
   ```

4. **Verify Database Population**:
   ```sql
   -- Check record counts
   SELECT COUNT(*) FROM ohlcv_daily WHERE date > CURRENT_DATE - INTERVAL '7 days';
   SELECT COUNT(*) FROM ohlcv_1min WHERE timestamp > NOW() - INTERVAL '1 day';
   SELECT COUNT(*) FROM ohlcv_hourly;
   ```

### 11.11 Expected Data Coverage

For each symbol requested:

| Timeframe | Records Expected | Time Range | Storage |
|-----------|-----------------|------------|---------|
| 1-minute | ~390 per day | Market hours only | ~100KB/symbol/day |
| Hourly | ~7 per day | Aggregated | ~2KB/symbol/day |
| Daily | ~252 per year | Trading days only | ~10KB/symbol/year |
| Weekly | ~52 per year | Week endings | ~2KB/symbol/year |
| Monthly | ~12 per year | Month endings | ~500B/symbol/year |

### 11.12 Success Metrics

Job processing is successful when:

1. ✅ Redis subscription shows 1+ subscribers on `tickstock.jobs.data_load`
2. ✅ Job status updates appear in Redis with progress
3. ✅ All 5 OHLCV tables contain recent data
4. ✅ Daily table has data within 1 business day
5. ✅ No "0 records" in minute/hourly tables
6. ✅ Job completes in reasonable time (~5 min for 100 symbols)

## Contact & Support

**TickStockAppV2 Integration**: Ready and listening
**Required Actions**:
- Implement sections 1-6 for pattern detection
- **URGENT**: Implement section 11 for historical data loading
**Testing**: Use test pattern generator to verify integration
**Monitoring**: Use `monitor_system_health.py` for real-time status

---

*Document Generated: 2025-09-17*
*Document Updated: 2024-10-30 - Added Historical Data Import Requirements*
*Purpose: Enable successful TickStockPL → TickStockAppV2 integration*
*Status: Awaiting TickStockPL implementation (Pattern Detection + Historical Data Import)*