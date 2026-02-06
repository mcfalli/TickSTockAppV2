# TickStockAppV2 Architecture

**Version**: 4.0.0-standalone
**Last Updated**: November 25, 2025 (Sprint 54)
**Status**: Production Ready
**Breaking Change**: TickStockPL integration removed - now standalone

## Overview

TickStockAppV2 is a **market state analysis platform** for real-time market insights. It provides user interface, authentication, market state dashboards, and database persistence for WebSocket tick data. TickStockPL handles data import and historical data management.

## Quick Links

- **[Service Dependencies & Startup](service-dependencies.md)** - Critical startup requirements, virtual environment setup, and inter-service communication
- **[Redis Integration](redis-integration.md)** - Pub-sub messaging patterns
- **[WebSocket Integration](websockets-integration.md)** - Real-time browser communication
- **[Massive Per-Minute Aggregates](massive-per-minute-aggregates.md)** - Per-minute OHLCV implementation (98.6% DB write reduction)
- **[Configuration](configuration.md)** - Environment variables and settings

## System Architecture

```
[Massive WebSocket] → [MarketDataService] → [TimescaleDB (ohlcv_1min)]
                              ↓
                    [Market State Analysis] → [Dashboards & Rankings]

[Browser UI] ← [REST API (/api/ticks/recent)] ← [TimescaleDB Query]

[TickStockPL] → [Historical Data Import] → [TimescaleDB Management]
```

### Core Responsibilities

**TickStockAppV2 (Market State Dashboard)**
- User authentication and session management
- WebSocket tick data ingestion from Massive API
- Direct database persistence (ohlcv_1min table)
- Market state analysis: rankings, sector rotation, stage classification
- Dashboard UI and trend visualizations
- REST API for frontend data polling
- Database read operations

**TickStockPL (Data Import & Management)**
- Historical data import from multiple providers
- EOD data processing and validation
- TimescaleDB schema management
- Database write operations and maintenance

## Component Architecture

### 1. Web Layer (`web/`)
- **Flask Application**: Main web server with authentication
- **WebSocket Server**: Real-time data broadcasting via Socket.IO
- **Dashboard Templates**: Jinja2-based UI components
- **Static Assets**: CSS, JavaScript, images

### 2. API Layer (`src/api/`)
- **REST Endpoints**: Market state queries, monitoring, admin functions
- **WebSocket Handlers**: Real-time data broadcasting
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

### Channel Structure (Updated Sprint 54 - MINIMAL)
```
# Internal Application Channels ONLY
tickstock:errors                  # Application error events (internal)
tickstock:monitoring              # Application health metrics (optional)

# ALL REMOVED (Sprint 54):
# ~~tickstock:patterns:streaming~~      # TickStockPL integration removed
# ~~tickstock:patterns:detected~~       # TickStockPL integration removed
# ~~tickstock:indicators:streaming~~    # TickStockPL integration removed
# ~~tickstock:streaming:health~~        # TickStockPL integration removed
# ~~tickstock.events.patterns~~         # TickStockPL integration removed
# ~~tickstock.events.indicators~~       # TickStockPL integration removed
# ~~tickstock:market:ticks~~            # No longer forwarding to TickStockPL
# ~~tickstock.jobs.*~~                  # No TickStockPL job submission
```

**Note**: Redis is now used ONLY for internal application features, NOT for cross-system communication.

### Message Flow (Current Architecture)

**Database-First Tick Processing:**
```
Massive WebSocket API ('A' aggregate events)
        ↓
MarketDataService._handle_tick_data()
        ├─ Database Write → ohlcv_1min table (async, <10ms)
        └─ Market State Analysis → rankings, sector rotation
                ↓
        Dashboard updates
```

**Frontend Data Access:**
```
Browser JavaScript
        ↓
Poll REST API: GET /api/ticks/recent?symbol=AAPL&limit=100
        ↓
TimescaleDB Query (ohlcv_1min table)
        ↓
JSON Response (OHLCV data)
        ↓
Browser Dashboard Update (rankings, trends, breadth)
```

**Key Architecture Features:**
- ✅ Real-time market state dashboards
- ✅ Direct database persistence (TimescaleDB)
- ✅ Market state analysis (rankings, sector rotation, stage classification)
- ✅ REST API for frontend polling
- ✅ Separated data import (TickStockPL) from UI (TickStockAppV2)
- ✅ Database-first data flow

## Performance Targets

| Operation | Target | Actual | Status | Sprint |
|-----------|--------|--------|--------|--------|
| Database Write (OHLCV) | <50ms | ~10ms | ✅ | 54 |
| Tick Processing | <1ms | <1ms | ✅ | 54 |
| REST API Response | <100ms | ~45ms | ✅ | 54 |
| Market State Refresh | <1 sec | ~0.5s | ✅ | 64 |
| WebSocket Connection | Active | 70 tickers | ✅ | 54 |
| Cache Hit Rate | >90% | 92% | ✅ | - |

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
- **Redis Channel Monitoring**: `scripts/diagnostics/monitor_redis_channels.py` (Sprint 43)
- **Live Streaming Dashboard**: `/streaming` - Raw Redis content display

### Diagnostic Tools (Sprint 43)
```bash
# Monitor Redis channels in real-time
python scripts/diagnostics/monitor_redis_channels.py

# View channel activity, message counts, and pattern/indicator flow
# Output: Channel counts, event types, health analysis
```

## Recent Architecture Changes

### Sprint 42 (October 12, 2025)
- **OHLCV Aggregation Moved**: From TickStockAppV2 → TickStockPL
- **Single Source of Truth**: TickStockPL owns all bar creation
- **Removed**: `src/infrastructure/database/ohlcv_persistence.py` (433 lines)
- **Result**: Zero duplicate bars, clean role separation

### Sprint 43 (October 17, 2025)
- **Pattern Delay Fix**: 5-8 minutes → 1-2 minutes
- **Root Cause**: TickStockPL enforced blanket 5-bar minimum
- **Solution**: Pattern-specific bar requirements
- **Diagnostics Added**: Redis channel monitoring, enhanced logging
- **UI Update**: Live Streaming dashboard shows raw Redis JSON

## Related Documentation

- [Redis Integration](./redis-integration.md): Detailed pub-sub patterns
- [WebSocket Integration](./websockets-integration.md): Real-time communication
- [Configuration Guide](./configuration.md): Environment setup
- [API Documentation](../api/endpoints.md): REST endpoint reference
- [Sprint 42 Complete](../planning/sprints/sprint42/SPRINT42_COMPLETE.md): OHLCV architecture
- [Sprint 43 Complete](../planning/sprints/sprint43/SPRINT43_COMPLETE.md): Pattern delay fix