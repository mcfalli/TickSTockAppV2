# TickStockAppV2 Architecture

**Version**: 3.1.0
**Last Updated**: October 17, 2025 (Sprint 42/43)
**Status**: Production Ready

## Overview

TickStockAppV2 is the consumer-facing application in the TickStock.ai ecosystem. It provides the user interface, authentication, and real-time WebSocket delivery while consuming processed events from TickStockPL via Redis pub-sub architecture.

## Quick Links

- **[Service Dependencies & Startup](service-dependencies.md)** - Critical startup requirements, virtual environment setup, and inter-service communication
- **[Redis Integration](redis-integration.md)** - Pub-sub messaging patterns
- **[WebSocket Integration](websockets-integration.md)** - Real-time browser communication
- **[Configuration](configuration.md)** - Environment variables and settings

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

### Channel Structure (Updated Sprint 42/43)
```
# Streaming Events from TickStockPL (consumed by AppV2)
tickstock:patterns:streaming      # Real-time pattern detections (all confidence levels)
tickstock:patterns:detected       # High confidence patterns (≥80%)
tickstock:indicators:streaming    # Real-time indicator calculations
tickstock:streaming:health        # Streaming session health metrics

# Legacy Events (still supported)
tickstock.events.patterns         # Pattern detection results
tickstock.events.indicators       # Indicator calculations
tickstock.events.processing       # Processing status updates

# System Channels
tickstock:monitoring              # System metrics and health
tickstock:errors                  # Error messages

# Market Data Flow (Sprint 42)
tickstock:market:ticks            # Raw tick data (AppV2 → TickStockPL)

# Jobs to TickStockPL (published by AppV2)
tickstock.jobs.backtest           # Backtest requests
tickstock.jobs.processing         # Processing commands
```

### Message Flow (Sprint 42/43 Architecture)

**Real-time Streaming Flow:**
```
Market Data (Massive)
        ↓
TickStockAppV2: MarketDataService
        ↓
Redis: tickstock:market:ticks (raw ticks)
        ↓
TickStockPL: RedisTickSubscriber
        ↓
TickStockPL: TickAggregator (1-min bars)
        ↓
TickStockPL: StreamingPatternJob (bar 1-2 detection)
        ↓
Redis: tickstock:patterns:streaming (pattern events)
        ↓
TickStockAppV2: RedisEventSubscriber
        ↓
TickStockAppV2: StreamingBuffer (250ms flush)
        ↓
TickStockAppV2: WebSocket broadcast
        ↓
Browser: Live Streaming Dashboard
```

**Key Improvements (Sprint 42/43):**
- ✅ OHLCV aggregation moved to TickStockPL (single source of truth)
- ✅ Pattern detection at bar 1-2 (vs. old 5-bar minimum)
- ✅ Streaming buffer with 250ms flush cycles
- ✅ Pattern-specific bar requirements (no blanket delays)

## Performance Targets

| Operation | Target | Actual | Status | Sprint |
|-----------|--------|--------|--------|--------|
| Pattern Detection | <2 min | 1-2 min | ✅ | 43 |
| WebSocket Delivery | <100ms | ~50ms | ✅ | - |
| API Response | <50ms | ~30ms | ✅ | - |
| Redis Operation | <10ms | ~5ms | ✅ | - |
| Streaming Buffer Flush | 250ms | 250ms | ✅ | 42 |
| UI Update | <200ms | ~150ms | ✅ | - |
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