# API Documentation

**Version**: 4.0.0
**Last Updated**: February 5, 2026
**Base URL**: `http://localhost:5000/api`

## Overview

TickStockAppV2 provides REST APIs for market state analysis, including threshold bars, market data access, and administrative functions. All endpoints return JSON responses.

## Authentication

Most endpoints require session-based authentication via Flask-Login. Login through the web UI at `/login` to establish a session.

## Core Endpoints

### Health Check
`GET /api/health`

Check application health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-05T10:00:00Z",
  "version": "4.0.0",
  "components": {
    "database": "connected",
    "redis": "connected"
  }
}
```

### Threshold Bars (Sprint 64)
`GET /api/threshold-bars`

Calculate threshold bar segments for market sentiment visualization.

**Query Parameters:**
- `data_source` (string, required): Universe key (e.g., 'sp500', 'nasdaq100'), ETF symbol (e.g., 'SPY'), or multi-universe join (e.g., 'sp500:nasdaq100')
- `bar_type` (string): 'DivergingThresholdBar' or 'SimpleDivergingBar' (default: 'DivergingThresholdBar')
- `timeframe` (string): '1min', 'hourly', 'daily', 'weekly', 'monthly' (default: 'daily')
- `threshold` (float): Threshold value 0.0-1.0 (default: 0.10 = 10%)
- `period_days` (integer): Days to look back, 1-365 (default: 1)

**Response:**
```json
{
  "metadata": {
    "data_source": "sp500",
    "bar_type": "DivergingThresholdBar",
    "timeframe": "daily",
    "threshold": 0.10,
    "period_days": 1,
    "symbol_count": 503,
    "calculated_at": "2026-02-05T10:30:00Z"
  },
  "segments": {
    "significant_decline": 0.12,
    "minor_decline": 0.23,
    "minor_advance": 0.45,
    "significant_advance": 0.20
  }
}
```

### Recent Tick Data
`GET /api/ticks/recent`

Retrieve recent OHLCV tick data from TimescaleDB.

**Query Parameters:**
- `symbol` (string, required): Stock symbol (e.g., 'AAPL')
- `since` (integer, optional): Unix timestamp - return records after this time
- `limit` (integer, optional): Max records to return (default: 100, max: 1000)

**Response:**
```json
{
  "symbol": "AAPL",
  "count": 10,
  "ticks": [
    {
      "symbol": "AAPL",
      "timestamp": 1738752000.123,
      "open": 150.25,
      "high": 151.50,
      "low": 149.75,
      "close": 150.80,
      "volume": 1000000
    }
  ]
}
```

### Chart Data
`GET /api/chart-data/<symbol>`

Get historical OHLCV data for charting.

**Path Parameters:**
- `symbol` (string): Stock symbol

**Query Parameters:**
- `timeframe` (string): '1min', 'hourly', 'daily' (default: 'daily')
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
      "timestamp": "2026-02-05T00:00:00Z",
      "open": 174.00,
      "high": 176.00,
      "low": 173.50,
      "close": 175.50,
      "volume": 50000000
    }
  ]
}
```

## User Endpoints

### User Settings
`GET /api/user/settings`

Get current user's settings.

**Authentication:** Required

**Response:**
```json
{
  "theme": "dark",
  "default_timeframe": "daily",
  "watchlist_symbols": ["AAPL", "GOOGL", "MSFT"]
}
```

`POST /api/user/settings`

Update user settings.

**Authentication:** Required

**Request Body:**
```json
{
  "theme": "light",
  "default_timeframe": "hourly"
}
```

### Symbol Search
`GET /api/symbols/search`

Search for symbols by name or ticker.

**Query Parameters:**
- `q` (string): Search query
- `limit` (integer): Max results (default: 20)

**Response:**
```json
{
  "results": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "type": "stock",
      "exchange": "NASDAQ"
    }
  ]
}
```

### Watchlist
`GET /api/watchlist`

Get user's watchlist symbols.

**Authentication:** Required

`POST /api/watchlist/add`

Add symbol to watchlist.

**Authentication:** Required

**Request Body:**
```json
{
  "symbol": "AAPL"
}
```

`POST /api/watchlist/remove`

Remove symbol from watchlist.

**Authentication:** Required

**Request Body:**
```json
{
  "symbol": "AAPL"
}
```

## Admin Endpoints

Admin endpoints require admin role authentication. Access via web UI at `/admin/*`.

### Cache Management
- `GET /admin/cache/stats` - View cache statistics
- `POST /admin/cache/refresh` - Invalidate and refresh cache
- `POST /admin/cache/warm` - Pre-populate cache

### Historical Data Loading
- `POST /admin/historical-data/trigger-load` - Trigger data load job
- `GET /admin/historical-data/job/<job_id>/status` - Check job status
- `POST /admin/historical-data/trigger-universe-load` - Load universe data
- `GET /admin/historical-data/universes` - List available universes

### WebSocket Management
- Admin endpoints for WebSocket connection monitoring
- See `/admin/websockets` page for UI

## Error Responses

### Standard Error Format
```json
{
  "error": "ValidationError",
  "message": "Invalid request parameters",
  "details": {
    "field": "symbol",
    "value": "INVALID"
  },
  "timestamp": "2026-02-05T10:00:00Z"
}
```

### Common HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

## Rate Limiting

API endpoints have rate limiting to prevent abuse:
- Standard endpoints: 100 requests/minute per IP
- Admin endpoints: 30 requests/minute per user
- Threshold bars: 20 requests/minute (calculation intensive)

## CORS

CORS is enabled for development. In production, configure allowed origins via:
```bash
FLASK_CORS_ORIGINS=https://yourdomain.com
```

## WebSocket Events

For real-time updates, use WebSocket connection at `ws://localhost:5000/socket.io/`

See `/streaming` dashboard for live event monitoring.

## Related Documentation

- **[Architecture Overview](../architecture/README.md)** - System design
- **[WebSocket Integration](../architecture/websockets-integration.md)** - Real-time data
- **[Configuration Guide](../guides/configuration.md)** - Environment setup
- **[Sprint 64 Complete](../planning/sprints/sprint64/threshold-bars.md)** - Threshold bars implementation
