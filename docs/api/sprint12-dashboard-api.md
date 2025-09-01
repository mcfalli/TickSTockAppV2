# Sprint 12 Dashboard API Endpoints

**Date**: 2025-08-30  
**Sprint**: 12  
**Status**: Implemented

## Overview

This document describes the newly implemented API endpoints for the Sprint 12 dashboard functionality. These endpoints provide watchlist management and symbol data for the TickStockAppV2 UI.

## Architecture Notes

- **Database Pattern**: Read-only queries to shared 'tickstock' database via `TickStockDatabase` class
- **Watchlist Storage**: Uses existing `UserSettings` table with JSONB key 'watchlist'
- **Performance Target**: <50ms query latency for UI responsiveness
- **Authentication**: All endpoints require `@login_required` decorator
- **Response Format**: Consistent `{"success": true/false, "data": ...}` pattern

## API Endpoints

### 1. Symbol Search
**Endpoint**: `GET /api/symbols/search`  
**Parameters**: `query` (optional) - Filter symbols by symbol code or company name  
**Response**: List of symbols for dropdown population  

```json
GET /api/symbols/search?query=AAPL
{
  "success": true,
  "symbols": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc"
    }
  ]
}
```

**Features**:
- Searches both symbol code and company name
- Case-insensitive filtering
- Limited to 100 results for UI performance
- Uses read-only connection to TickStock database

### 2. Get User Watchlist
**Endpoint**: `GET /api/watchlist`  
**Response**: User's watchlist symbols with metadata  

```json
GET /api/watchlist
{
  "success": true,
  "symbols": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc",
      "last_price": 0.00
    },
    {
      "symbol": "MSFT", 
      "name": "Microsoft Corporation",
      "last_price": 0.00
    }
  ]
}
```

**Features**:
- Retrieves watchlist from UserSettings table
- Enriches symbols with company names from database
- Mock prices (0.00) - ready for TickStockPL integration
- Handles missing symbols gracefully

### 3. Add to Watchlist
**Endpoint**: `POST /api/watchlist/add`  
**Body**: `{"symbol": "AAPL"}`  
**Response**: Success confirmation  

```json
POST /api/watchlist/add
{
  "symbol": "AAPL"
}

Response:
{
  "success": true,
  "message": "Added AAPL to watchlist"
}
```

**Features**:
- Validates symbol exists in database
- Prevents duplicate additions
- Updates UserSettings atomically
- Uppercase normalization

### 4. Remove from Watchlist
**Endpoint**: `POST /api/watchlist/remove`  
**Body**: `{"symbol": "AAPL"}`  
**Response**: Success confirmation  

```json
POST /api/watchlist/remove
{
  "symbol": "AAPL" 
}

Response:
{
  "success": true,
  "message": "Removed AAPL from watchlist"
}
```

**Features**:
- Safe removal (no error if symbol not in watchlist)
- Updates UserSettings atomically
- Handles non-existent symbols gracefully

### 5. Chart Data
**Endpoint**: `GET /api/chart-data/<symbol>`  
**Parameters**: `timeframe` (optional) - '1d', '1h', or other timeframe  
**Response**: OHLCV chart data for symbol  

```json
GET /api/chart-data/AAPL?timeframe=1d
{
  "success": true,
  "chart_data": [
    {
      "timestamp": "2025-08-01T10:00:00Z",
      "open": 150.00,
      "high": 155.00, 
      "low": 148.00,
      "close": 152.00,
      "volume": 1000000
    }
  ],
  "symbol": "AAPL",
  "timeframe": "1d"
}
```

**Features**:
- Validates symbol exists in database
- Mock data generation with realistic price movements
- Timeframe-aware timestamp generation
- Ready for TickStockPL OHLCV integration

## Error Handling

All endpoints follow consistent error response format:

```json
{
  "success": false,
  "error": "Error message description"
}
```

**Common Error Codes**:
- `400`: Bad Request (missing required parameters)
- `404`: Symbol not found
- `500`: Internal server error (database connection, etc.)

## Database Integration

### TickStock Database Connection
- **Service**: `TickStockDatabase` class in `src/infrastructure/database/tickstock_db.py`
- **Connection Pool**: 5 connections, 2 max overflow, 10s timeout
- **Database**: Shared 'tickstock' TimescaleDB 
- **Role**: Read-only access for UI queries

### User Settings Storage
- **Table**: `user_settings` 
- **Key**: `'watchlist'`
- **Value**: JSON array of symbol strings `["AAPL", "MSFT", "GOOGL"]`
- **Service**: `UserSettingsService` for atomic updates

## Performance Considerations

- **Query Limits**: Symbol search limited to 100 results
- **Connection Pooling**: Optimized for concurrent UI requests
- **Caching Ready**: UserSettingsService includes caching layer
- **Mock Data**: Chart data uses efficient generation for 30 data points

## Future Integration Points

### TickStockPL Integration
- **Real-time Prices**: Watchlist endpoint ready for live price updates
- **OHLCV Data**: Chart endpoint ready for real historical data
- **Performance Analytics**: Framework ready for pattern detection results

### Redis Integration  
- **WebSocket Updates**: Real-time watchlist price updates
- **Pattern Alerts**: Integration with pattern detection system
- **Caching**: Enhanced performance for frequently accessed data

## Testing

Basic logic validation completed for:
- Watchlist add/remove operations
- Symbol search filtering
- Chart data generation
- Error handling patterns

## File Locations

- **API Implementation**: `/src/api/rest/api.py` (lines 140-413)
- **Database Service**: `/src/infrastructure/database/tickstock_db.py`
- **User Settings Service**: `/src/core/services/user_settings_service.py`
- **Documentation**: `/docs/api/sprint12-dashboard-api.md`