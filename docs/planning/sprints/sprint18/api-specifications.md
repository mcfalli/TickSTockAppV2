# API Specifications - Pattern Discovery Dashboard

**Date**: 2025-09-04  
**Sprint**: 18 - Planning Phase  
**Status**: Technical API Documentation  
**Source**: Enhanced with concrete implementation examples from feedback  

## Overview

This document provides detailed API specifications for the Pattern Discovery Dashboard, incorporating the technical implementation patterns from the backend integration guide. All endpoints target sub-50ms response times and include comprehensive error handling.

## REST API Endpoints

### 1. Pattern Scanner API

#### GET /api/patterns/scan
**Description**: Unified pattern search across all timeframes with advanced filtering

**Query Parameters**:
```typescript
interface ScanParams {
  // Pattern Filtering
  pattern_types?: string[];        // ['Breakouts', 'Volume', 'Trendlines', 'Gaps']
  timeframe?: 'All' | 'Daily' | 'Intraday' | 'Combo';
  
  // Indicator Filtering  
  rs_min?: number;                // Minimum relative strength (e.g., 1.0)
  vol_min?: number;               // Minimum volume multiple (e.g., 1.5)
  confidence_min?: number;        // Minimum pattern confidence (0.5-1.0)
  rsi_min?: number;               // RSI lower bound (0-100)
  rsi_max?: number;               // RSI upper bound (0-100)
  
  // Symbol Filtering
  symbols?: string[];             // Specific symbols to include
  sectors?: string[];             // ['Technology', 'Healthcare', 'Finance']
  market_cap?: 'Large' | 'Mid' | 'Small';
  
  // Time Filtering
  detected_after?: string;        // ISO datetime
  expires_after?: string;         // ISO datetime
  
  // Pagination & Sorting
  page?: number;                  // Default: 1
  per_page?: number;              // Default: 30, Max: 100
  sort_by?: 'confidence' | 'time' | 'rs' | 'volume';
  sort_order?: 'asc' | 'desc';    // Default: desc
}
```

**Response Format**:
```typescript
interface ScanResponse {
  patterns: PatternData[];
  pagination: {
    total: number;
    page: number;
    per_page: number;
    pages: number;
  };
  performance: {
    query_time_ms: number;
    cache_hit: boolean;
  };
  filters_applied: FilterSummary;
}

interface PatternData {
  symbol: string;
  pattern: string;              // Abbreviated name (e.g., "WeeklyBO")
  conf: number;                 // 0.50 - 0.99
  rs: number;                   // Relative strength multiplier
  vol: number;                  // Volume multiplier  
  price: number;                // Current price
  chg: number;                  // Price change %
  time: string;                 // Relative time (e.g., "2h", "30m")
  exp: string;                  // Expiration time
  source: 'daily' | 'intraday' | 'combo';
  fundamental_boost?: boolean;  // EPS surprise boost applied
  accuracy_validated?: boolean; // FMV accuracy check passed
}
```

**Example Request**:
```bash
GET /api/patterns/scan?pattern_types=Breakouts&pattern_types=Volume&rs_min=1.2&vol_min=1.5&per_page=50&sort_by=confidence
```

**Example Response**:
```json
{
  "patterns": [
    {
      "symbol": "AAPL",
      "pattern": "WeeklyBO",
      "conf": 0.92,
      "rs": 1.4,
      "vol": 2.1,
      "price": 185.50,
      "chg": 2.3,
      "time": "2h",
      "exp": "3d",
      "source": "daily",
      "fundamental_boost": true,
      "accuracy_validated": true
    }
  ],
  "pagination": {
    "total": 1247,
    "page": 1,
    "per_page": 50,
    "pages": 25
  },
  "performance": {
    "query_time_ms": 38,
    "cache_hit": false
  }
}
```

### 2. Market Breadth API

#### GET /api/market/breadth  
**Description**: Comprehensive market analysis including indices, sectors, and breadth indicators

**Response Format**:
```typescript
interface MarketBreadthResponse {
  major_indices: IndexData[];
  sector_heatmap: SectorData[];
  breadth_indicators: BreadthIndicators;
  index_patterns: PatternData[];
  performance: {
    query_time_ms: number;
    last_updated: string;
  };
}

interface IndexData {
  symbol: string;              // 'SPY', 'QQQ', etc.
  name: string;                // 'S&P 500 ETF'
  price: number;
  change_pct: number;
  volume_ratio: number;        // vs 20-day average
  strength_indicator: number;  // 1-4 (●●●○)
  support_level: number;
  resistance_level: number;
}

interface SectorData {
  etf_symbol: string;          // 'XLK', 'XLF', etc.
  sector_name: string;
  performance_1d: number;      // 1-day return %
  performance_5d: number;      // 5-day return %
  relative_strength: number;   // vs SPY
  volume_ratio: number;
  money_flow: 'In' | 'Out' | 'Neutral';
}

interface BreadthIndicators {
  advance_decline_line: 'Bullish' | 'Bearish' | 'Neutral';
  new_highs_lows: 'Bullish' | 'Bearish' | 'Neutral';
  up_down_volume: 'Strong' | 'Weak' | 'Neutral';
  mcclellan_oscillator: number;
}
```

### 3. Watchlist Management API

#### GET /api/watchlists/{user_id}
**Description**: Get all watchlists for a user

#### POST /api/watchlists  
**Description**: Create new watchlist

**Request Body**:
```json
{
  "name": "Tech Leaders",
  "description": "High-growth technology stocks",
  "symbols": ["AAPL", "NVDA", "MSFT"],
  "user_id": "user123"
}
```

#### GET /api/watchlists/{watchlist_id}/patterns
**Description**: Get active patterns for watchlist symbols

**Response Format**:
```typescript
interface WatchlistPatternsResponse {
  watchlist_info: {
    id: string;
    name: string;
    symbol_count: number;
  };
  patterns: PatternData[];
  performance_summary: {
    patterns_triggered_today: number;
    avg_confidence: number;
    win_rate: number;
    best_performer: string;
    worst_performer: string;
  };
}
```

### 4. User Preferences API

#### GET /api/users/{user_id}/saved-filters
**Description**: Get user's saved filter sets

#### POST /api/users/{user_id}/saved-filters
**Description**: Save new filter configuration

**Request Body**:
```json
{
  "name": "High Momentum Breakouts",
  "description": "Breakouts with high RS and volume",
  "filters": {
    "pattern_types": ["Breakouts"],
    "rs_min": 1.2,
    "vol_min": 2.0,
    "confidence_min": 0.85
  }
}
```

## WebSocket Events

### Client → Server Events

#### subscribe_watchlist
**Description**: Subscribe to real-time updates for a watchlist

**Payload**:
```json
{
  "user_id": "user123",
  "watchlist_id": "wl456", 
  "symbols": ["AAPL", "NVDA", "MSFT"]
}
```

#### unsubscribe_watchlist
**Description**: Unsubscribe from watchlist updates

#### subscribe_pattern_alerts  
**Description**: Subscribe to new pattern detection alerts

**Payload**:
```json
{
  "user_id": "user123",
  "filters": {
    "pattern_types": ["Breakouts"],
    "symbols": ["AAPL", "NVDA"],
    "confidence_min": 0.90
  }
}
```

### Server → Client Events

#### pattern_update
**Description**: Real-time pattern updates for subscribed symbols

**Payload**:
```json
{
  "watchlist_id": "wl456",
  "patterns": [
    {
      "symbol": "AAPL",
      "pattern": "WeeklyBO",
      "conf": 0.94,
      "event_type": "confidence_updated"
    }
  ],
  "timestamp": "2025-09-04T15:30:00Z"
}
```

#### new_pattern_alert
**Description**: Alert for newly detected high-confidence patterns

**Payload**:
```json
{
  "symbol": "NVDA",
  "pattern": "BullFlag",
  "conf": 0.96,
  "rs": 1.8,
  "vol": 3.2,
  "entry_signal": true,
  "target_price": 510.00,
  "timestamp": "2025-09-04T15:32:15Z"
}
```

#### pattern_expiration_warning
**Description**: Warning for patterns approaching expiration

**Payload**:
```json
{
  "symbol": "MSFT",
  "pattern": "TrendHold", 
  "expires_in_minutes": 45,
  "timestamp": "2025-09-04T15:35:00Z"
}
```

## Error Handling

### Standard Error Response Format
```typescript
interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: any;
  };
  request_id: string;
  timestamp: string;
}
```

### Common Error Codes
- `INVALID_PARAMETERS`: Invalid query parameters provided
- `RATE_LIMIT_EXCEEDED`: Too many requests in time window  
- `DATA_UNAVAILABLE`: Pattern data temporarily unavailable
- `PERFORMANCE_TIMEOUT`: Query exceeded 50ms timeout
- `WEBSOCKET_CONNECTION_FAILED`: Real-time connection issue

## Performance Specifications

### Response Time Targets
- **Pattern Scan**: <50ms for 1,000+ patterns
- **Market Breadth**: <25ms for all index data
- **Watchlist Updates**: <10ms for 50 symbols
- **WebSocket Events**: <5ms propagation

### Rate Limiting
- **REST APIs**: 1000 requests/minute per user
- **WebSocket**: 100 subscriptions per connection
- **Bulk Operations**: 50 requests/minute for exports

### Caching Strategy
- **Pattern Data**: 30-60 second Redis cache
- **Market Breadth**: 15-30 second cache
- **User Preferences**: 5-minute cache
- **Cache Keys**: `pattern:{filters_hash}`, `breadth:latest`, `user:{user_id}:prefs`

## Authentication & Authorization

### API Key Authentication
```bash
Authorization: Bearer <api_key>
```

### WebSocket Authentication  
```json
{
  "auth": {
    "api_key": "<api_key>",
    "user_id": "user123"
  }
}
```

### Permission Levels
- **Read-Only**: Pattern scanning, market breadth viewing
- **Standard**: Watchlist management, saved filters
- **Premium**: Advanced analytics, unlimited watchlists, priority WebSocket

## Data Validation

### Pattern Data Quality
- **Confidence Range**: 0.50 - 0.99 (patterns below 0.50 filtered out)
- **Price Validation**: Current prices within 5% of market data
- **Timestamp Validation**: Pattern detection times within reasonable bounds
- **FMV Accuracy**: Patterns validated against <5% prediction error when available

### Input Sanitization
- **SQL Injection Prevention**: Parameterized queries only
- **XSS Protection**: All user inputs sanitized
- **Rate Limiting**: Per-IP and per-user limits enforced
- **Data Size Limits**: Max 100 symbols per watchlist, 1000 patterns per response

This API specification provides the technical foundation for implementing the high-density pattern discovery dashboard with real-time updates, comprehensive filtering, and sub-50ms performance targets.