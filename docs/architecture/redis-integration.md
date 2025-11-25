# Redis Integration - Standalone Architecture

**Version**: 3.0.0-standalone
**Last Updated**: November 25, 2025 (Sprint 54)
**Status**: Production Ready
**Breaking Change**: TickStockPL integration completely removed

## Overview

**Sprint 54 Update**: TickStockAppV2 now operates as a **standalone application** with NO TickStockPL integration. Redis is used only for internal application pub/sub, NOT for cross-system communication.

### Architecture Change

**Previous Architecture (Pre-Sprint 54)**:
```
TickStockAppV2 → Redis Pub-Sub → TickStockPL
     ↓              ↓              ↓
 Tick Data      Event Queue    Processing
 Publisher      Distribution   Consumer
```

**Current Architecture (Sprint 54+)**:
```
Massive WebSocket → MarketDataService → [Direct Database Persistence]
                                       → [FallbackPatternDetector (local)]

Frontend → REST API (/api/ticks/recent) → Database → JSON Response
```

**Key Changes**:
- ✅ **Database-First**: Tick data persists directly to TimescaleDB `ohlcv_1min` table
- ✅ **Standalone Operation**: No cross-system Redis pub/sub dependencies
- ✅ **Local Pattern Detection**: FallbackPatternDetector operates within AppV2
- ❌ **No TickStockPL Integration**: All Redis channels TO/FROM TickStockPL removed
- ❌ **No Tick Forwarding**: Tick data NOT published to Redis for external consumption

## Redis Usage (Internal Only)

### Current Redis Channels

Redis is now used **only for internal application features**, not for cross-system integration:

#### Internal Application Channels
- **`tickstock:errors`** - Application error events (internal monitoring)
- **`tickstock:monitoring`** - Application health metrics (optional)
- **`tickstock:cache:invalidation`** - Cache invalidation signals (future)

### Removed Channels (Sprint 54)

The following Redis channels have been **permanently removed**:

#### Outbound Channels (TO TickStockPL) - REMOVED
- ~~`tickstock.all_ticks`~~ - All tick data stream
- ~~`tickstock.ticks.{TICKER}`~~ - Per-ticker data streams
- ~~`tickstock:market:ticks`~~ - Raw tick forwarding
- ~~`tickstock.data.raw`~~ - Raw market data

#### Inbound Channels (FROM TickStockPL) - REMOVED
- ~~`tickstock.events.patterns`~~ - Pattern detection results
- ~~`tickstock:patterns:streaming`~~ - Real-time patterns
- ~~`tickstock:indicators:streaming`~~ - Technical indicators
- ~~`tickstock:streaming:health`~~ - TickStockPL health status

## Data Flow Architecture

### Tick Data Processing (Current)

```
1. WebSocket Reception
   └─ Massive WebSocket Client receives per-second aggregates ('A' events)

2. Data Transformation
   └─ Convert to TickData objects with OHLCV fields

3. Parallel Processing
   ├─ Database Persistence → ohlcv_1min table (TimescaleDB)
   └─ FallbackPatternDetector → Local pattern analysis

4. Frontend Access
   └─ REST API polling (/api/ticks/recent) → JSON response
```

**Performance**: Database writes are async and non-blocking (~10ms latency)

### Pattern Detection (Current)

```
FallbackPatternDetector (Standalone)
  ├─ Input: Real-time tick data from MarketDataService
  ├─ Processing: Local pattern analysis algorithms
  └─ Output: Pattern detections stored in database
```

**Note**: Pattern detection is now **entirely local** to TickStockAppV2. No external pattern services.

## Migration from Pre-Sprint 54

### What Changed

| Component | Before Sprint 54 | After Sprint 54 |
|-----------|------------------|-----------------|
| **Tick Distribution** | Redis pub/sub | Direct database write |
| **Pattern Source** | TickStockPL via Redis | FallbackPatternDetector (local) |
| **Frontend Updates** | WebSocket broadcast | REST API polling |
| **Cross-System Communication** | Redis channels | None (standalone) |
| **Data Persistence** | TickStockPL responsibility | TickStockAppV2 responsibility |

### Code Changes Required

**If you had custom TickStockPL consumers:**
```python
# OLD (Pre-Sprint 54) - NO LONGER WORKS
redis_client.subscribe('tickstock.all_ticks')  # Channel removed
redis_client.subscribe('tickstock.events.patterns')  # Channel removed

# NEW (Sprint 54+) - NOT SUPPORTED
# TickStockPL integration removed - no replacement
# AppV2 is now standalone with database persistence
```

**If you need tick data:**
```python
# NEW: Query database directly
from src.infrastructure.database.tickstock_db import TickStockDatabase

db = TickStockDatabase(config)
with db.get_connection() as conn:
    query = text("""
        SELECT symbol, timestamp, open, high, low, close, volume
        FROM ohlcv_1min
        WHERE symbol = :symbol
        AND timestamp > :since
        ORDER BY timestamp DESC
        LIMIT :limit
    """)
    result = conn.execute(query, {'symbol': 'AAPL', 'since': since_timestamp, 'limit': 100})
    ticks = result.fetchall()
```

**If you need pattern data:**
```python
# NEW: Query pattern detections from database
from src.infrastructure.database.tickstock_db import TickStockDatabase

db = TickStockDatabase(config)
with db.get_connection() as conn:
    query = text("""
        SELECT pd.symbol, pd.pattern_name, pd.confidence, pd.detected_at
        FROM pattern_detections pd
        WHERE pd.symbol = :symbol
        AND pd.detected_at > :since
        ORDER BY pd.detected_at DESC
    """)
    result = conn.execute(query, {'symbol': 'AAPL', 'since': since_timestamp})
    patterns = result.fetchall()
```

## Configuration

### Redis Connection (Minimal)

Redis is still used for internal application features:

```python
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'decode_responses': True,
    'socket_timeout': 30,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30
}
```

### Environment Variables

```bash
# Redis Connection (Internal Use Only)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Removed (Sprint 54)
# TICKSTOCKPL_CONSUMER_ID=...  # No longer needed
# TICKSTOCKPL_BATCH_SIZE=...   # No longer needed
```

## REST API Endpoint (New)

### Get Recent Ticks

**Endpoint**: `GET /api/ticks/recent`

**Query Parameters**:
- `symbol` (required): Stock ticker symbol (e.g., "AAPL")
- `since` (optional): Unix timestamp - return records after this time
- `limit` (optional): Max records to return (default: 100, max: 1000)

**Example Request**:
```bash
curl "http://localhost:5000/api/ticks/recent?symbol=AAPL&limit=10"
```

**Example Response**:
```json
{
  "symbol": "AAPL",
  "count": 10,
  "ticks": [
    {
      "symbol": "AAPL",
      "timestamp": 1700925617.736925,
      "open": 150.25,
      "high": 151.50,
      "low": 149.75,
      "close": 150.80,
      "volume": 1000000
    },
    ...
  ]
}
```

## Performance Characteristics

### Database Write Performance
- **Write Latency**: ~10ms per tick (async, non-blocking)
- **Throughput**: 100+ ticks/second sustained
- **Storage**: TimescaleDB hypertable with automatic compression

### REST API Performance
- **Response Time**: <100ms for 100 records
- **Caching**: None (queries database directly)
- **Scalability**: Database connection pooling supports 100+ concurrent requests

## Monitoring

### Health Checks

```python
# Check Redis connectivity (internal features)
def check_redis_health():
    try:
        redis_client.ping()
        return {"redis": "healthy", "latency_ms": measure_latency()}
    except Exception as e:
        return {"redis": "unhealthy", "error": str(e)}

# Check database write capability
def check_database_health():
    try:
        db = TickStockDatabase(config)
        with db.get_connection() as conn:
            conn.execute(text("SELECT 1"))
        return {"database": "healthy"}
    except Exception as e:
        return {"database": "unhealthy", "error": str(e)}
```

### Key Metrics

| Metric | Target | Monitoring |
|--------|--------|------------|
| Database Write Latency | <50ms | Log slow writes >50ms |
| REST API Response Time | <100ms | Flask logging |
| Tick Processing Rate | >50/sec | MarketDataService stats |
| Database Connection Pool | <80% utilized | SQLAlchemy metrics |

## Troubleshooting

### No Tick Data in Database

**Symptom**: `ohlcv_1min` table is empty

**Possible Causes**:
1. **Markets Closed** - WebSocket only sends ticks during market hours (9:30 AM - 4:00 PM ET weekdays)
2. **Foreign Key Constraint** - Symbol must exist in `symbols` table first
3. **Database Connection** - Check database connectivity

**Diagnosis**:
```bash
# Check if application is running
ps aux | grep "flask run"

# Check logs for database writes
grep "TICKSTOCK-DB: Wrote OHLCV" logs/*.log

# Verify symbols exist
psql -d tickstock -c "SELECT symbol FROM symbols WHERE symbol = 'AAPL';"
```

### REST API Returns Empty Array

**Symptom**: `/api/ticks/recent` returns `{"count": 0, "ticks": []}`

**Possible Causes**:
1. No data in database (see above)
2. Time filter excluding all records
3. Symbol parameter incorrect (case-sensitive)

**Diagnosis**:
```bash
# Test endpoint
curl "http://localhost:5000/api/ticks/recent?symbol=AAPL&limit=10"

# Check database directly
psql -d tickstock -c "SELECT COUNT(*) FROM ohlcv_1min WHERE symbol = 'AAPL';"
```

## Deprecated Features

The following features are **permanently removed** and will not be supported:

- ❌ Redis pub/sub for tick distribution
- ❌ TickStockPL integration (all channels)
- ❌ WebSocket real-time tick broadcasting
- ❌ Pattern/indicator consumption from TickStockPL
- ❌ Cross-system Redis event streaming

**Migration Path**: Use database queries and REST API endpoints instead.

---

## Summary

**Sprint 54** transformed TickStockAppV2 into a standalone application with:
- ✅ Direct database persistence (TimescaleDB)
- ✅ Local pattern detection (FallbackPatternDetector)
- ✅ REST API for frontend data access
- ❌ No external system dependencies
- ❌ No Redis cross-system communication

This architecture is simpler, more maintainable, and provides clear data ownership boundaries.
