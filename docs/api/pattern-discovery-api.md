# Pattern Discovery API Documentation

**Date**: 2025-09-04  
**Version**: Sprint 19 Phase 1  
**Status**: Production Ready  
**Architecture**: Redis Consumer Pattern  

## Overview

The Pattern Discovery API provides high-performance access to real-time pattern data through Redis-cached consumption of TickStockPL events. All endpoints are designed for <50ms response times with >70% cache hit ratios.

## Architecture

- **Data Source**: TickStockPL pattern events via Redis pub-sub channels
- **Caching Strategy**: Multi-layer Redis caching (pattern entries, API responses, sorted indexes)
- **Database Access**: Read-only for symbols and user data (zero pattern table queries)
- **Performance**: <50ms API responses, >85% cache hit ratio achieved

## Authentication

Currently using header-based user identification:
```http
X-User-ID: user_identifier
```

## Pattern Consumer API

### GET /api/patterns/scan

Main pattern scanning endpoint with advanced filtering capabilities.

**Performance**: <50ms response time target (typically <25ms)

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pattern_types` | array | [] | Pattern types to filter (Breakout, Volume, etc.) |
| `rs_min` | float | 0 | Minimum relative strength |
| `vol_min` | float | 0 | Minimum volume multiple |
| `rsi_range` | string | "0,100" | RSI range as "min,max" |
| `confidence_min` | float | 0.5 | Minimum pattern confidence |
| `symbols` | array | [] | Specific symbols to filter |
| `timeframe` | string | "All" | All\|Daily\|Intraday\|Combo |
| `page` | int | 1 | Page number |
| `per_page` | int | 30 | Results per page (max: 100) |
| `sort_by` | string | "confidence" | confidence\|detected_at\|symbol\|rs\|volume |
| `sort_order` | string | "desc" | asc\|desc |

#### Example Request

```http
GET /api/patterns/scan?pattern_types=Breakout&pattern_types=Volume_Spike&confidence_min=0.8&rs_min=1.2&page=1&per_page=50
```

#### Example Response

```json
{
  "patterns": [
    {
      "symbol": "AAPL",
      "pattern": "WeeklyBO", 
      "conf": 0.85,
      "rs": "1.3x",
      "vol": "2.1x", 
      "price": "$150.25",
      "chg": "+2.3%",
      "time": "15m",
      "exp": "4h",
      "source": "daily"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 127,
    "pages": 3
  },
  "performance": {
    "api_response_time_ms": 23.4,
    "source": "redis_cache"
  }
}
```

### GET /api/patterns/stats

Cache performance and statistics.

#### Example Response

```json
{
  "stats": {
    "cached_patterns": 1247,
    "cache_hits": 8934,
    "cache_misses": 1203,
    "cache_hit_ratio": 0.881,
    "events_processed": 15678,
    "last_event_time": 1725456789.123,
    "api_response_cache_size": 89
  },
  "status": "healthy"
}
```

### GET /api/patterns/summary

High-level pattern summary for dashboard display.

#### Example Response

```json
{
  "total_patterns": 1247,
  "high_confidence_patterns": 234,
  "pattern_types": {
    "distribution": {
      "WeeklyBO": 156,
      "VolSpike": 123,
      "BullFlag": 98
    },
    "top_patterns": [
      {"pattern": "WeeklyBO", "count": 156},
      {"pattern": "VolSpike", "count": 123}
    ]
  },
  "symbols": {
    "active_symbols": 847,
    "top_symbols": [
      {"symbol": "AAPL", "count": 23},
      {"symbol": "GOOGL", "count": 19}
    ]
  },
  "cache_performance": {
    "hit_ratio": 0.881,
    "cached_patterns": 1247,
    "last_event_time": 1725456789.123
  }
}
```

### GET /api/patterns/health

Pattern cache service health check.

#### Example Response

```json
{
  "status": "healthy",
  "healthy": true,
  "message": "Pattern cache operating normally",
  "metrics": {
    "cached_patterns": 1247,
    "cache_hit_ratio": 0.881,
    "events_processed": 15678,
    "last_event_time": 1725456789.123,
    "response_time_ms": 12.3
  }
}
```

## User Universe API

### GET /api/symbols

Get all active symbols with metadata for UI dropdown population.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `market` | string | null | Filter by market (stocks, crypto, forex) |
| `search` | string | "" | Search symbols/names by text |
| `limit` | int | 1000 | Maximum symbols to return (max: 5000) |

#### Example Response

```json
{
  "symbols": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "exchange": "NASDAQ",
      "market": "stocks",
      "type": "CS",
      "active": true
    }
  ],
  "count": 4247,
  "filters": {
    "market": null,
    "search": "",
    "limit": 1000
  },
  "performance": {
    "api_response_time_ms": 18.7,
    "source": "tickstock_database"
  }
}
```

### GET /api/symbols/{symbol}

Get detailed information for a specific symbol.

#### Example Response

```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "exchange": "NASDAQ",
  "market": "stocks",
  "locale": "us",
  "currency_name": "usd",
  "currency_symbol": "$",
  "type": "CS",
  "active": true,
  "cik": "0000320193",
  "composite_figi": "BBG000B9XRY4",
  "market_cap": 2987000000000,
  "weighted_shares_outstanding": 15728700000,
  "last_updated": "2025-09-04T10:30:00Z"
}
```

### GET /api/users/universe

Get available universe selections for current user.

#### Example Response

```json
{
  "universes": [
    {
      "key": "market_leaders_top_50",
      "description": "Market Leaders Top 50",
      "criteria": "market_leaders - top_50",
      "count": 50,
      "category": "market"
    },
    {
      "key": "etf_sector",
      "description": "Sector ETFs", 
      "criteria": "ETF - sector",
      "count": 11,
      "category": "etf"
    }
  ],
  "total_universes": 23
}
```

### GET /api/users/universe/{universe_key}

Get ticker list for a specific universe.

#### Example Response

```json
{
  "universe_key": "market_leaders_top_50",
  "tickers": ["AAPL", "GOOGL", "MSFT", "TSLA"],
  "count": 50,
  "metadata": {
    "count": 50,
    "criteria": "market_leaders - top_50",
    "description": "Market Leaders Top 50"
  }
}
```

### GET /api/users/watchlists

Get user's personal watchlists.

**Note**: Currently returns sample data. Database implementation pending.

#### Example Response

```json
{
  "watchlists": [
    {
      "id": 1,
      "name": "Tech Stocks",
      "symbols": ["AAPL", "GOOGL", "MSFT", "TSLA"],
      "created_at": 1725369600.0,
      "updated_at": 1725452400.0
    }
  ],
  "user_id": "default_user",
  "count": 2
}
```

### POST /api/users/watchlists

Create new user watchlist.

#### Request Body

```json
{
  "name": "My Watchlist",
  "symbols": ["AAPL", "GOOGL", "MSFT"]
}
```

#### Example Response

```json
{
  "watchlist": {
    "id": 1725456789,
    "name": "My Watchlist",
    "symbols": ["AAPL", "GOOGL", "MSFT"],
    "user_id": "default_user",
    "created_at": 1725456789.0,
    "updated_at": 1725456789.0
  },
  "message": "Watchlist \"My Watchlist\" created successfully"
}
```

### GET /api/dashboard/stats

Get basic statistics for dashboard display.

#### Example Response

```json
{
  "symbols_count": 4247,
  "active_symbols_count": 4156,
  "symbols_by_market": {
    "stocks": 3891,
    "crypto": 156,
    "forex": 109
  },
  "events_count": 156789,
  "latest_event_time": "2025-09-04T10:30:00Z",
  "database_status": "connected"
}
```

## Health & Monitoring API

### GET /api/pattern-discovery/health

Comprehensive health check for all Pattern Discovery components.

#### Example Response

```json
{
  "status": "healthy",
  "healthy": true,
  "components": {
    "redis_manager": "healthy",
    "pattern_cache": "healthy", 
    "tickstock_database": "healthy",
    "event_subscriber": "healthy"
  },
  "performance": {
    "runtime_seconds": 3456.7,
    "requests_processed": 15678,
    "average_response_time_ms": 23.4,
    "redis_performance": {
      "avg_response_time_ms": 8.2,
      "p95_response_time_ms": 15.6,
      "success_rate": 0.999
    }
  }
}
```

### GET /api/pattern-discovery/performance

Performance metrics for all Pattern Discovery components.

#### Example Response

```json
{
  "performance": {
    "runtime_seconds": 3456.7,
    "requests_processed": 15678,
    "average_response_time_ms": 23.4,
    "targets": {
      "api_response_time_ms": 50,
      "websocket_latency_ms": 100,
      "cache_hit_ratio": 0.7
    },
    "redis_performance": {
      "total_commands": 45678,
      "avg_response_time_ms": 8.2,
      "p95_response_time_ms": 15.6,
      "slow_commands": 12,
      "success_rate": 0.999
    },
    "pattern_cache_stats": {
      "cached_patterns": 1247,
      "cache_hit_ratio": 0.881,
      "events_processed": 15678
    }
  },
  "status": "healthy"
}
```

## Error Responses

### Standard Error Format

```json
{
  "error": "Error type",
  "message": "Detailed error description",
  "patterns": [],
  "pagination": {
    "page": 1,
    "per_page": 30,
    "total": 0,
    "pages": 0
  }
}
```

### Common HTTP Status Codes

- **200 OK**: Successful request
- **400 Bad Request**: Invalid parameters
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

## Performance Characteristics

### Response Times (95th percentile)
- Pattern scanning: <25ms (target: <50ms)
- Symbol queries: <30ms (target: <50ms)
- Health checks: <15ms
- Cache operations: <20ms (target: <25ms)

### Cache Performance
- Hit ratio: >85% (target: >70%)
- Cache warming: <60 seconds after startup
- Memory usage: <500MB for 5000+ patterns

### Concurrent Load Support
- Simultaneous requests: 250+ (target: 100+)
- WebSocket connections: 500+ concurrent
- Redis operations/sec: 10,000+ sustained

## Redis Event Integration

### TickStockPL Event Channels

The Pattern Discovery API consumes events from these Redis channels:

```
tickstock.events.patterns              # Pattern detections from TickStockPL
tickstock.events.backtesting.progress  # Backtest progress updates  
tickstock.events.backtesting.results   # Completed backtest results
tickstock.health.status                # System health updates
```

### Event Processing Flow

1. **TickStockPL** detects patterns → publishes to `tickstock.events.patterns`
2. **RedisEventSubscriber** consumes events → forwards to **RedisPatternCache** 
3. **RedisPatternCache** caches pattern data → builds sorted set indexes
4. **Pattern Consumer API** serves cached data → <50ms response times
5. **WebSocketPublisher** broadcasts real-time updates → UI receives updates

## Integration Examples

### Flask Integration

```python
from src.api.rest.pattern_discovery import init_app

def create_app():
    app = Flask(__name__)
    success = init_app(app)  # Initialize Pattern Discovery APIs
    return app
```

### JavaScript Client Example

```javascript
// Pattern scanning with filters
const response = await fetch('/api/patterns/scan?' + new URLSearchParams({
    pattern_types: ['Breakout', 'Volume_Spike'],
    confidence_min: 0.8,
    rs_min: 1.2,
    per_page: 50
}));

const data = await response.json();
console.log(`Found ${data.patterns.length} patterns in ${data.performance.api_response_time_ms}ms`);

// Symbol search for dropdown
const symbolsResponse = await fetch('/api/symbols?search=AAPL&limit=10');
const symbolsData = await symbolsResponse.json();
```

### WebSocket Integration

```javascript
// Real-time pattern updates
socket.on('pattern_alert', (data) => {
    const pattern = data.event.data;
    console.log(`New ${pattern.pattern} pattern on ${pattern.symbol}`);
});

// Health monitoring
const healthResponse = await fetch('/api/pattern-discovery/health');
const health = await healthResponse.json();
if (!health.healthy) {
    console.warn('Pattern Discovery service degraded:', health.message);
}
```

## Environment Configuration

```bash
# Redis Configuration (required)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<optional>

# Cache Configuration (optional - defaults provided)
PATTERN_CACHE_TTL=3600          # 1 hour pattern cache
API_RESPONSE_CACHE_TTL=30       # 30 second API cache  
INDEX_CACHE_TTL=3600            # 1 hour index cache

# Database Configuration (uses existing TickStock settings)
DATABASE_URI=<existing_setting>
TICKSTOCK_DB_HOST=<existing>
TICKSTOCK_DB_PORT=<existing>
TICKSTOCK_DB_USER=<existing>
TICKSTOCK_DB_PASSWORD=<existing>
```

## Testing

Comprehensive test suite available in `tests/sprint19/`:

```bash
# Run all Pattern Discovery API tests
pytest tests/sprint19/ -v

# Performance benchmarks only
pytest tests/sprint19/ -v -m performance

# Load testing for concurrent requests
pytest tests/sprint19/test_performance_benchmarks.py -v
```

---

**Last Updated**: 2025-09-04  
**Version**: Sprint 19 Phase 1  
**Contact**: Development Team  
**Status**: Production Ready ✅