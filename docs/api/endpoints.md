# API Documentation

**Version**: 3.0.0
**Last Updated**: September 26, 2025
**Base URL**: `http://localhost:8501/api`

## Authentication

### Login
`POST /login`

Authenticate user and create session.

**Request Body:**
```json
{
  "username": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "user@example.com",
    "role": "user"
  }
}
```

### Logout
`POST /logout`

End user session.

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### Register
`POST /register`

Create new user account.

**Request Body:**
```json
{
  "username": "user@example.com",
  "password": "password123",
  "confirm_password": "password123"
}
```

## Pattern Discovery

### Get Available Patterns
`GET /pattern-discovery/patterns`

Retrieve list of available patterns with metadata.

**Query Parameters:**
- `use_cache` (boolean): Enable Redis caching (default: true)
- `category` (string): Filter by category (candlestick, momentum, volume)

**Response:**
```json
{
  "patterns": [
    {
      "id": "doji",
      "name": "Doji",
      "category": "candlestick",
      "description": "Indecision pattern",
      "timeframes": ["1min", "5min", "daily"],
      "confidence_threshold": 0.8
    }
  ],
  "cache_hit": true,
  "response_time_ms": 12
}
```

### Get Pattern Results
`GET /pattern-discovery/results`

Retrieve detected patterns for symbols.

**Query Parameters:**
- `symbol` (string): Stock symbol (e.g., AAPL)
- `pattern` (string): Pattern ID
- `timeframe` (string): Time period (1min, 5min, daily)
- `start_date` (string): ISO format date
- `end_date` (string): ISO format date
- `min_confidence` (float): Minimum confidence score (0-1)

**Response:**
```json
{
  "results": [
    {
      "symbol": "AAPL",
      "pattern": "bullish_engulfing",
      "timestamp": "2025-09-26T10:30:00Z",
      "timeframe": "daily",
      "confidence": 0.92,
      "price": 175.50,
      "volume": 50000000,
      "metadata": {
        "open": 174.00,
        "high": 176.00,
        "low": 173.50,
        "close": 175.50
      }
    }
  ],
  "count": 15,
  "cache_hit": false,
  "response_time_ms": 45
}
```

### Get Pattern Statistics
`GET /pattern-discovery/statistics`

Retrieve pattern performance statistics.

**Query Parameters:**
- `pattern` (string): Pattern ID
- `timeframe` (string): Analysis period
- `lookback_days` (integer): Days to analyze (default: 30)

**Response:**
```json
{
  "pattern": "doji",
  "statistics": {
    "total_occurrences": 245,
    "success_rate": 0.68,
    "avg_return": 0.023,
    "win_rate": 0.62,
    "risk_reward_ratio": 1.8,
    "best_performer": {
      "symbol": "NVDA",
      "return": 0.15
    }
  }
}
```

## Monitoring

### Health Check
`GET /health`

Check application health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-26T10:00:00Z",
  "version": "3.0.0",
  "components": {
    "database": "connected",
    "redis": "connected",
    "websocket": "active"
  }
}
```

### Metrics
`GET /monitoring/metrics`

Retrieve system performance metrics.

**Response:**
```json
{
  "metrics": {
    "api_response_time_ms": 28,
    "websocket_connections": 42,
    "redis_latency_ms": 3,
    "cache_hit_rate": 0.92,
    "patterns_processed_per_minute": 1250,
    "memory_usage_mb": 256,
    "cpu_usage_percent": 15
  },
  "timestamp": "2025-09-26T10:00:00Z"
}
```

### System Status
`GET /monitoring/status`

Get detailed system status.

**Response:**
```json
{
  "services": {
    "pattern_processor": "running",
    "redis_subscriber": "connected",
    "websocket_server": "active",
    "cache_manager": "healthy"
  },
  "queues": {
    "pattern_queue": 0,
    "processing_queue": 5
  },
  "errors_last_hour": 2
}
```

## Admin Endpoints

### Historical Data Loading
`POST /admin/historical-data/load`

Load historical data for specified symbols.

**Request Body:**
```json
{
  "symbols": ["AAPL", "GOOGL", "MSFT"],
  "start_date": "2025-01-01",
  "end_date": "2025-09-26",
  "timeframes": ["daily", "hourly"],
  "provider": "polygon"
}
```

**Response:**
```json
{
  "job_id": "load_20250926_100000",
  "status": "processing",
  "symbols_queued": 3,
  "estimated_time_seconds": 120
}
```

### Processing Control
`POST /admin/processing/trigger`

Trigger processing job in TickStockPL.

**Request Body:**
```json
{
  "command": "START_DAILY_PROCESSING",
  "parameters": {
    "symbols": ["ALL"],
    "patterns": ["ALL"],
    "force": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "daily_20250926",
  "message": "Processing job submitted to TickStockPL"
}
```

### Cache Management
`POST /admin/cache/clear`

Clear Redis cache entries.

**Request Body:**
```json
{
  "cache_type": "patterns",  // patterns | indicators | all
  "pattern": "doji*"         // Optional pattern matching
}
```

**Response:**
```json
{
  "cleared_keys": 156,
  "cache_type": "patterns",
  "success": true
}
```

## WebSocket Events

### Connection
`ws://localhost:8501/socket.io/`

Establish WebSocket connection for real-time updates.

### Subscribe to Symbols
**Event:** `subscribe`
```json
{
  "symbols": ["AAPL", "GOOGL"],
  "events": ["patterns", "indicators"]
}
```

### Pattern Detection Event
**Event:** `pattern_detected`
```json
{
  "symbol": "AAPL",
  "pattern": "bullish_engulfing",
  "timestamp": "2025-09-26T10:30:00Z",
  "confidence": 0.92,
  "timeframe": "daily",
  "action": "BUY_SIGNAL"
}
```

### Indicator Update
**Event:** `indicator_update`
```json
{
  "symbol": "GOOGL",
  "indicator": "RSI",
  "value": 72.5,
  "timestamp": "2025-09-26T10:30:00Z",
  "timeframe": "hourly",
  "signal": "OVERBOUGHT"
}
```

### System Alert
**Event:** `system_alert`
```json
{
  "level": "warning",
  "message": "High latency detected",
  "component": "redis",
  "timestamp": "2025-09-26T10:30:00Z"
}
```

## Data Endpoints

### Get Symbols
`GET /data/symbols`

Retrieve available symbols.

**Query Parameters:**
- `type` (string): Filter by type (stock, etf, crypto)
- `exchange` (string): Filter by exchange
- `active` (boolean): Only active symbols
- `limit` (integer): Max results (default: 100)
- `offset` (integer): Pagination offset

**Response:**
```json
{
  "symbols": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "type": "stock",
      "exchange": "NASDAQ",
      "sector": "Technology",
      "active": true
    }
  ],
  "total": 4500,
  "limit": 100,
  "offset": 0
}
```

### Get OHLCV Data
`GET /data/ohlcv`

Retrieve OHLCV data for symbol.

**Query Parameters:**
- `symbol` (string, required): Stock symbol
- `timeframe` (string): 1min, 5min, hourly, daily
- `start` (string): ISO format start date
- `end` (string): ISO format end date
- `limit` (integer): Max bars (default: 100)

**Response:**
```json
{
  "symbol": "AAPL",
  "timeframe": "daily",
  "data": [
    {
      "timestamp": "2025-09-26T00:00:00Z",
      "open": 174.00,
      "high": 176.00,
      "low": 173.50,
      "close": 175.50,
      "volume": 50000000
    }
  ],
  "count": 100
}
```

## Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "INVALID_SYMBOL",
    "message": "Symbol 'XYZ' not found",
    "details": {
      "field": "symbol",
      "value": "XYZ"
    }
  },
  "status": 400,
  "timestamp": "2025-09-26T10:00:00Z"
}
```

### Common Error Codes
| Code | Status | Description |
|------|--------|-------------|
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `INVALID_PARAMS` | 400 | Invalid request parameters |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## Rate Limiting

API endpoints are rate limited to prevent abuse:

- **Unauthenticated**: 60 requests/minute
- **Authenticated**: 600 requests/minute
- **Admin**: 1000 requests/minute

Rate limit headers:
```
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 543
X-RateLimit-Reset: 1695721800
```

## Pagination

List endpoints support pagination:

```
GET /api/data/symbols?limit=50&offset=100

Response headers:
X-Total-Count: 4500
X-Page-Count: 90
Link: <.../symbols?offset=150>; rel="next",
      <.../symbols?offset=50>; rel="prev"
```

## Versioning

API version is included in response headers:
```
X-API-Version: 3.0.0
```

Future versions may use path versioning:
```
/api/v2/patterns
```

## CORS

CORS headers are configured for cross-origin requests:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

Production should restrict origins:
```
Access-Control-Allow-Origin: https://app.yourdomain.com
```