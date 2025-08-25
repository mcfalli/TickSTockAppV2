# REST API Endpoints - Simplified Architecture

**Version**: 2.0.0-simplified  
**Last Updated**: August 25, 2025  
**Status**: Post-Cleanup API Documentation

## Overview

TickStock's simplified architecture provides essential REST endpoints for system monitoring, user management, and basic configuration. Many complex analytics and trace endpoints have been removed as part of the system simplification.

## Base URL
```
http://localhost:5000
```

## Core System Endpoints

### Health and Monitoring

#### GET `/health`
Basic system health check endpoint.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-08-25T14:30:00Z"
}
```

#### GET `/stats`  
System statistics for simplified components.

**Response:**
```json
{
    "market_data": {
        "ticks_processed": 1500,
        "events_published": 1200,
        "data_source": "synthetic"
    },
    "websocket": {
        "active_connections": 3,
        "messages_sent": 850
    },
    "redis": {
        "connected": true,
        "published_messages": 1200
    }
}
```

#### GET `/api/health`
Extended health check with component status.

**Response:**
```json
{
    "status": "healthy",
    "components": {
        "database": "healthy",
        "redis": "healthy", 
        "websocket": "healthy",
        "market_data_service": "healthy"
    },
    "timestamp": "2025-08-25T14:30:00Z"
}
```

## User Management Endpoints

### Authentication
Basic user authentication endpoints (preserved from original system):

- `POST /register` - User registration
- `POST /login` - User login  
- `POST /logout` - User logout
- `POST /change_password` - Change password
- `GET /account` - Account management

### User Settings
Simplified user settings management:

#### GET `/api/user/settings`
Get user settings.

#### POST `/api/user/settings`
Update user settings.

#### GET `/api/user/universe-selections`
Get current user's universe selections.

**Response:**
```json
{
    "success": true,
    "selections": {
        "market": ["DEFAULT_UNIVERSE"]
    },
    "user_id": 123
}
```

## WebSocket Events

### Connection Events
- `connect` - Client connection established
- `disconnect` - Client disconnection
- `subscribe_tickers` - Subscribe to specific ticker updates

### Data Events  
- Real-time tick data broadcast to connected clients
- Market status updates
- System notifications

## Removed Endpoints

The following endpoint categories have been **removed** during simplification:

### Analytics Endpoints (REMOVED)
- `/api/analytics/summary` ❌
- `/api/analytics/pressure-data` ❌ 
- `/api/analytics/performance` ❌

### Trace System Endpoints (REMOVED)
- `/api/trace/status` ❌
- `/api/trace/enable` ❌
- `/api/trace/export/*` ❌

### Quality Metrics Endpoints (REMOVED)  
- `/api/quality/metrics/*` ❌
- `/api/quality/validate/*` ❌
- `/api/quality/summary` ❌

### Complex Filter Endpoints (REMOVED)
- Advanced filter endpoints have been simplified or removed

## Error Responses

Standard error format:
```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Error description"
    }
}
```

## Rate Limiting

Basic rate limiting in place:
- **Default**: 100 requests per minute per user
- **Settings updates**: 10 per minute

## Request Examples

### cURL Examples
```bash
# Health check
curl -X GET http://localhost:5000/health

# System stats
curl -X GET http://localhost:5000/stats

# User settings (requires authentication)
curl -X GET http://localhost:5000/api/user/settings \
  -H "Cookie: session=your-session-cookie"
```

### Python Example
```python
import requests

# Check system health
response = requests.get('http://localhost:5000/health')
print(response.json())

# Get system stats  
response = requests.get('http://localhost:5000/stats')
print(response.json())
```

## Integration Notes

### TickStockPL Integration
- **Primary interface**: Redis pub-sub channels, not REST endpoints
- **Monitoring**: Use `/health` and `/stats` for system status
- **Configuration**: Via environment variables, not API endpoints

### Real-time Data Access
- **WebSocket**: Connect to root URL for real-time tick data
- **Subscribe**: Use `subscribe_tickers` event to specify tickers
- **Data format**: Standardized tick data objects

---

**Note**: This simplified API focuses on essential functionality. Complex analytics and trace systems that provided extensive REST endpoints have been removed in favor of a cleaner, more maintainable architecture.