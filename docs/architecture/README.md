# TickStockAppV2 Architecture

**Version**: 3.0.0
**Last Updated**: September 26, 2025
**Status**: Production Ready

## Overview

TickStockAppV2 is the consumer-facing application in the TickStock.ai ecosystem. It provides the user interface, authentication, and real-time WebSocket delivery while consuming processed events from TickStockPL via Redis pub-sub architecture.

## System Architecture

```
[Market Data] → [TickStockAppV2: Ingestion] → [Redis] → [TickStockPL: Processing]
                                                   ↓
[Browser UI] ← [TickStockAppV2: WebSocket] ← [Redis] ← [TickStockPL: Events]
```

### Core Responsibilities

**TickStockAppV2 (This Application)**
- User authentication and session management
- Real-time WebSocket broadcasting to browsers
- Dashboard UI and visualizations
- Redis event consumption from TickStockPL
- Job submission to TickStockPL via Redis
- Read-only database queries for UI elements

**TickStockPL (Processing Engine)**
- Pattern detection and indicator calculations
- Heavy data processing and backtesting
- Database schema management
- Event publishing to Redis channels
- OHLCV data management

## Component Architecture

### 1. Web Layer (`web/`)
- **Flask Application**: Main web server with authentication
- **WebSocket Server**: Real-time data broadcasting via Socket.IO
- **Dashboard Templates**: Jinja2-based UI components
- **Static Assets**: CSS, JavaScript, images

### 2. API Layer (`src/api/`)
- **REST Endpoints**: Pattern discovery, monitoring, admin functions
- **WebSocket Handlers**: Real-time event broadcasting
- **Authentication**: Session-based user management
- **Rate Limiting**: API throttling and protection

### 3. Core Services (`src/core/services/`)
- **Startup Service**: Application initialization and health checks
- **Config Manager**: Environment-based configuration
- **Processing Publisher**: Job submission to TickStockPL
- **Event Subscriber**: Redis event consumption

### 4. Infrastructure (`src/infrastructure/`)
- **Database**: Read-only TimescaleDB access
- **Redis**: Pub-sub messaging and caching
- **Cache Control**: In-memory and Redis caching strategies
- **Logging**: Unified error and event logging

### 5. Data Layer (`src/data/`)
- **EOD Processor**: End-of-day data handling
- **Historical Loader**: Backfill data management
- **ETF Universe**: Symbol and metadata management
- **Test Scenarios**: Synthetic data generation

## Redis Integration

### Channel Structure
```
# Events from TickStockPL (consumed by AppV2)
tickstock.events.patterns         # Pattern detection results
tickstock.events.indicators       # Indicator calculations
tickstock.events.processing       # Processing status updates
tickstock:monitoring              # System metrics and health
tickstock:errors                  # Error messages

# Jobs to TickStockPL (published by AppV2)
tickstock.jobs.backtest           # Backtest requests
tickstock.jobs.processing         # Processing commands
tickstock.data.raw                # Raw market data
```

### Message Flow
1. AppV2 receives market data or user requests
2. Publishes jobs/data to Redis channels
3. TickStockPL processes and publishes results
4. AppV2 consumes results and updates UI
5. WebSocket broadcasts to connected clients

## Performance Targets

| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| WebSocket Delivery | <100ms | ~50ms | ✅ |
| API Response | <50ms | ~30ms | ✅ |
| Redis Operation | <10ms | ~5ms | ✅ |
| UI Update | <200ms | ~150ms | ✅ |
| Cache Hit Rate | >90% | 92% | ✅ |

## Configuration

### Environment Variables
```bash
# Database (Read-only access)
DATABASE_URL=postgresql://app_readwrite:password@localhost:5432/tickstock

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PATTERN_CHANNEL=tickstock.events.patterns
REDIS_ERROR_CHANNEL=tickstock:errors

# Logging
LOG_FILE_ENABLED=true
LOG_DB_ENABLED=true
LOG_DB_SEVERITY_THRESHOLD=error

# WebSocket
WEBSOCKET_CORS_ORIGINS=*
WEBSOCKET_MAX_CONNECTIONS=1000
```

### Key Configuration Files
- `.env`: Environment variables
- `config/database_config.py`: Database settings
- `config/redis_config.py`: Redis pub-sub configuration
- `config/logging_config.py`: Logging thresholds

## Security Considerations

- **Authentication**: Session-based with secure cookies
- **Authorization**: Role-based access control (admin/user)
- **Input Validation**: All API inputs validated
- **SQL Injection**: Parameterized queries only
- **XSS Protection**: Template escaping enabled
- **CORS**: Configurable origin restrictions
- **Rate Limiting**: API throttling per user/IP

## Deployment Architecture

```
Production Environment:
├── Load Balancer (optional)
├── TickStockAppV2 Instance(s)
│   ├── Flask/Gunicorn
│   ├── Socket.IO Server
│   └── Redis Client
├── Redis Server (shared)
├── TimescaleDB (shared)
└── TickStockPL Instance(s)
```

## Monitoring & Observability

- **Health Endpoints**: `/health`, `/ready`
- **Metrics Channel**: `tickstock:monitoring`
- **Error Tracking**: Centralized via Redis
- **Performance Metrics**: Real-time KPIs
- **Database Monitoring**: Query performance tracking

## Related Documentation

- [Redis Integration](./redis-integration.md): Detailed pub-sub patterns
- [WebSocket Integration](./websockets-integration.md): Real-time communication
- [Configuration Guide](./configuration.md): Environment setup
- [API Documentation](../api/endpoints.md): REST endpoint reference