# TickStock.ai Architecture Overview

## Application Role Clarity & Responsibilities

### TickStock.ai (Static Front End)
- **Purpose**: Public-facing entry point for marketing, docs, and basic demos
- **Tech Stack**: HTML/CSS/JS (hosted on GitHub Pages or Vercel free tier)
- **Operations**: Static serving—no backend. Links to TickStockApp for login/use
- **Primary Functionality**: Overview pages, pattern library docs, sign-up forms

### TickStockApp (User-Servicing Application) - Consumer Role
**Core Philosophy**: UI-focused event consumer that triggers jobs and displays results

**What TickStockApp DOES**:
- **User Management**: Authentication, registration, session handling
- **UI & Dashboard**: Real-time WebSocket updates, pattern alert notifications
- **Event Consumption**: Single RedisEventSubscriber with shared handlers (Sprint 25A fix)
- **Integration Logging**: ✅ **COMPLETE** - Comprehensive database logging with flow tracking (Sprint 25A)
- **Real-Time Pattern Events**: ✅ **COMPLETE** - Live WebSocket broadcasting of pattern detections from TickStockPL
- **TickStockPL Integration**: ✅ **VERIFIED** - Redis pub-sub with monitoring and heartbeat (60s intervals)
- **Live Data Processing**: ✅ **COMPLETE** - 70 tickers streaming Polygon → Redis → TickStockPL → OHLCV database
- **Pattern Discovery APIs**: REST endpoints consuming Redis cache (no direct DB queries for patterns)
- **Tier Pattern Dashboard**: Multi-tier pattern visualization (Daily, Intraday, Combo) with real-time updates (Sprint 25)
- **User Universe APIs**: Symbol management and watchlist APIs (`/api/symbols`, `/api/users/*`)
- **WebSocket Broadcasting**: Real-time pattern alerts to connected users (<100ms delivery)
- **Job Triggering**: Submits backtest/analysis jobs to TickStockPL via Redis
- **Result Display**: Visualizes TickStockPL-computed metrics and results
- **Basic Data Ingestion**: Receives raw market data, forwards to Redis for TickStockPL
- **Read-Only Database**: TimescaleDB queries for UI data only (symbols, users, NOT patterns)

**What TickStockApp DOES NOT DO**:
- ❌ **Pattern Detection**: No algorithm implementation - consumes TickStockPL events
- ❌ **Data Processing**: No StandardOHLCV conversion, normalization, or blending
- ❌ **Backtesting Engine**: No metrics computation - displays TickStockPL results
- ❌ **Multi-Provider Logic**: No API fallbacks or complex data provider management
- ❌ **Database Schema Management**: No table creation, migrations, or complex queries
- ❌ **Historical Analysis**: No pattern performance tracking - queries TickStockPL results

### TickStockPL (Pattern Library Services) - Producer Role
**Core Philosophy**: Heavy-lifting analytical engine that processes data and publishes events

**What TickStockPL DOES**:
- **Data Processing**: StandardOHLCV conversion, multi-provider integration, DataBlender
- **Pattern Detection**: All 11+ pattern algorithms with sub-millisecond performance
- **Backtesting Engine**: Complete framework with 20+ institutional metrics
- **Database Management**: Schema creation, TimescaleDB optimization, data loading
- **Event Publishing**: Publishes pattern detections, backtest results to Redis
- **Historical Analysis**: Pattern performance tracking, strategy validation
- **Job Processing**: Executes backtest jobs triggered by TickStockApp

For detailed TickStockPL architecture, performance metrics, and implementation specifications, see **[`tickstockpl-architecture.md`](tickstockpl-architecture.md)**.

### Automation Services (Background Processing) - Support Role
**Core Philosophy**: Independent background services for data maintenance and monitoring

**What Automation Services DO**:
- **IPO Monitoring**: Daily detection of new listings with 90-day historical backfill
- **Data Quality Monitoring**: Price anomaly detection (>20% moves), volume analysis
- **EOD Processing**: End-of-day data processing with market timing awareness
- **Cache Synchronization**: Daily universe updates and market cap recalculation
- **Enterprise Scheduling**: Production-scale historical data loading coordination
- **Market Calendar Management**: Multi-exchange holiday and schedule awareness

**What TickStockPL DOES NOT DO**:
- ❌ **User Interface**: No UI components or WebSocket client management
- ❌ **Authentication**: No user management or session handling
- ❌ **Alert Delivery**: No email/SMS notifications to users
- ❌ **Real-Time UI Updates**: No direct WebSocket emission to browsers

## Communication Architecture

### Redis Pub-Sub Channels (Loose Coupling)
**TickStockApp → TickStockPL** (Job Submission):
- `tickstock.jobs.backtest` - Backtest job requests
- `tickstock.jobs.alerts` - Alert subscription changes
- `tickstock.data.raw` - Raw market data forwarding

**TickStockPL → TickStockApp** (Event Publishing):
- `tickstock.events.patterns` - Real-time pattern detections (supports nested data structure)
- `tickstock.events.backtesting.progress` - Backtest progress updates
- `tickstock.events.backtesting.results` - Completed backtest results
- `tickstock.health.status` - System health and heartbeat events

**Automation Services → System** (Notifications):
- `eod_processing_complete` - End-of-day processing completion notifications
- `ipo_detected` - New IPO discovery alerts  
- `data_quality_alert` - Data anomaly and quality issue notifications
- `cache_sync_complete` - Universe synchronization completion status

### Database Architecture (Single "tickstock" Database)
**Shared TimescaleDB Database**: `tickstock`
- **Tables**: `symbols`, `ohlcv_daily`, `ohlcv_1min`, `ticks` (hypertables), `events`, `cache_entries`
- **Enhanced Schema**: 16 new ETF-specific columns, JSONB processing rules, equity types
- **TickStockPL Role**: Full read/write access, schema management, data loading
- **TickStockApp Role**: Read-only access for UI queries only
- **Automation Services Role**: Background data maintenance, schema updates, quality monitoring

### Data Flow Architecture
```
[External Sources: Polygon WebSocket, Alpha Vantage APIs]
                        ↓
[TickStockApp: Raw Data Ingestion → Redis (tickstock.data.raw)]
                        ↓
[TickStockPL: DataBlender + PatternScanner + EventPublisher]
                        ↓
    [Redis Pub-Sub: Pattern Events + Backtest Results]
                        ↓
[TickStockApp: Event Consumption → WebSocket → Browser UI]
                        ↓
            [User: Alerts, Dashboards, Results]

[Automation Services: Background Processing]
    ↓ (IPO Monitor, Data Quality, EOD Processing)
    ↓ (Cache Sync, Enterprise Scheduling, Market Calendar)
[Redis Pub-Sub: Automation Notifications]

[Shared Database "tickstock": TimescaleDB]
    ↕ (TickStockPL: Read/Write)
    ↕ (TickStockApp: Read-Only)
    ↕ (Automation Services: Maintenance & Monitoring)
```

## Key Architectural Principles

### 1. Separation of Concerns
- **TickStockApp**: User experience and interface management
- **TickStockPL**: Data processing and analytical algorithms
- **Automation Services**: Background data maintenance and monitoring
- **Redis**: Loose coupling communication layer
- **Database**: Shared persistence layer with role-based access

### 2. Event-Driven Architecture
- All inter-application communication via Redis pub-sub
- No direct API calls between applications
- Asynchronous processing for scalability
- Event sourcing for audit trails

### 3. Performance Optimization
- **TickStockPL**: Sub-millisecond pattern detection (1.12ms achieved)
- **TickStockApp**: <100ms UI responsiveness via WebSocket
- **Database**: TimescaleDB optimization for time-series queries
- **Redis**: In-memory messaging for real-time communication

### 4. Maintainability & Scalability
- **Loose Coupling**: Applications can be developed, deployed, and scaled independently
- **Clear Boundaries**: No functionality overlap between applications
- **Bootstrap Philosophy**: Minimal dependencies, maximum flexibility
- **Horizontal Scaling**: Redis pub-sub enables multiple instances of each application

## Related Documentation

- **[`database-architecture.md`](database-architecture.md)** - Detailed database schema and optimization
- **[`../planning/project-overview.md`](../planning/project-overview.md)** - Complete project vision and requirements
- **[`../guides/integration-guide.md`](../guides/integration-guide.md)** - TickStockPL integration instructions