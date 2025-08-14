```markdown
# REST API Endpoints

## Overview

TickStock provides REST endpoints for configuration, user management, and data queries. All endpoints require authentication unless specified otherwise.

## Base URL
https://your-domain.com/api

## Authentication

All API requests require authentication via session cookies or API tokens.

### Session Authentication
Obtained through login endpoint. Cookie-based for web clients.

### API Token
For programmatic access:
Authorization: Bearer <your-api-token>

## Endpoints

### Authentication

#### POST `/auth/login`
User login endpoint.

**Request:**
```json
{
    "email": "user@example.com",
    "password": "secure-password"
}
Response:
json{
    "success": true,
    "user": {
        "id": 123,
        "email": "user@example.com",
        "username": "johndoe"
    }
}
POST /auth/logout
Terminate user session.
Response:
json{
    "success": true,
    "message": "Logged out successfully"
}
POST /auth/register
Create new user account.
Request:
json{
    "email": "new@example.com",
    "username": "newuser",
    "password": "secure-password",
    "phone": "+1234567890"
}
Universe Management
GET /api/user/universe-selections
Get current user's universe selections.
Response:
json{
    "success": true,
    "selections": {
        "market": ["DEFAULT_UNIVERSE"],
        "highlow": ["DEFAULT_UNIVERSE", "TECH_UNIVERSE"]
    },
    "user_id": 123
}
POST /api/universes/select
Update user's universe selections.
Request:
json{
    "tracker": "market",
    "universes": ["DEFAULT_UNIVERSE", "LARGE_CAP_UNIVERSE"]
}
Response:
json{
    "status": "success",
    "tracker": "market",
    "universes": ["DEFAULT_UNIVERSE", "LARGE_CAP_UNIVERSE"],
    "cache_invalidated": true,
    "user_id": 123
}
GET /api/user/universe-cache-status
Debug endpoint for cache status.
Response:
json{
    "cached_users": [1, 2, 3],
    "cache_size": 3,
    "cache_hits": 150,
    "cache_misses": 10,
    "hit_rate": 93.75
}
User Filters
GET /api/user-filters
Get current user's filter settings.
Response:
json{
    "success": true,
    "filter_data": {
        "filter_name": "default",
        "filters": {
            "highlow": {
                "min_count": 25,
                "min_volume": 100000
            },
            "trends": {
                "strength": "moderate",
                "vwap_position": "any_vwap_position"
            },
            "surges": {
                "magnitude_threshold": 2.0,
                "trigger_types": ["price", "volume"]
            }
        },
        "version": "1.0"
    },
    "user_id": 123
}
POST /api/user-filters
Save user's filter settings.
Request:
json{
    "filter_data": {
        "filters": {
            "highlow": {
                "min_count": 50,
                "min_volume": 500000
            }
        }
    }
}
Response:
json{
    "success": true,
    "message": "Filters saved successfully",
    "user_id": 123,
    "cache_invalidated": true
}
POST /api/user-filters/cache/invalidate
Force cache invalidation for user filters.
Response:
json{
    "success": true,
    "cache_invalidated": true
}
System Status
GET /api/health
System health check endpoint.
Response:
json{
    "status": "healthy",
    "components": {
        "database": "healthy",
        "redis": "healthy",
        "websocket": "healthy"
    },
    "timestamp": "2024-12-19T14:30:00Z"
}
GET /api/metrics
System metrics endpoint.
Response:
json{
    "processing": {
        "ticks_processed": 1500000,
        "events_detected": 3200,
        "active_users": 45
    },
    "performance": {
        "avg_tick_processing_ms": 0.8,
        "avg_publishing_ms": 7.2
    },
    "resources": {
        "memory_mb": 512,
        "cpu_percent": 35,
        "worker_pool_size": 8
    }
}
Available Universes
GET /api/universes/available
List all available universes.
Response:
json{
    "universes": [
        {
            "id": "DEFAULT_UNIVERSE",
            "name": "Default Universe",
            "description": "Balanced selection across sectors",
            "stock_count": 762
        },
        {
            "id": "LARGE_CAP_UNIVERSE",
            "name": "Large Cap Universe",
            "description": "Large capitalization stocks",
            "stock_count": 545
        }
    ]
}
Error Responses
All errors follow consistent format:
json{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid universe selection",
        "details": {
            "field": "universes",
            "issue": "TECH_UNIVERSE not available"
        }
    }
}
Common Error Codes
CodeHTTP StatusDescriptionUNAUTHORIZED401Authentication requiredFORBIDDEN403Insufficient permissionsNOT_FOUND404Resource not foundVALIDATION_ERROR400Invalid request dataRATE_LIMITED429Too many requestsSERVER_ERROR500Internal server error
Rate Limiting

Default limit: 100 requests per minute per user
Filter updates: 10 per minute
Universe updates: 10 per minute

Rate limit headers:
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1703001234
Request Examples
cURL
bash# Get universe selections
curl -X GET https://your-domain.com/api/user/universe-selections \
  -H "Authorization: Bearer your-token"

# Update filters
curl -X POST https://your-domain.com/api/user-filters \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"filter_data":{"filters":{"highlow":{"min_count":25}}}}'
Python
pythonimport requests

# Setup session
session = requests.Session()
session.headers.update({'Authorization': 'Bearer your-token'})

# Get universe selections
response = session.get('https://your-domain.com/api/user/universe-selections')
data = response.json()

# Update filters
filter_data = {
    'filter_data': {
        'filters': {
            'highlow': {'min_count': 25}
        }
    }
}
response = session.post('https://your-domain.com/api/user-filters', json=filter_data)
JavaScript
javascript// Get universe selections
fetch('/api/user/universe-selections', {
    credentials: 'include'
})
.then(res => res.json())
.then(data => console.log(data));

// Update filters
fetch('/api/user-filters', {
    method: 'POST',
    credentials: 'include',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        filter_data: {
            filters: {
                highlow: { min_count: 25 }
            }
        }
    })
})
.then(res => res.json())
.then(data => console.log(data));
Versioning
API version is included in response headers:
X-API-Version: 1.0
Future versions will use URL versioning:
/api/v2/endpoint

For WebSocket real-time API, see WebSocket Events