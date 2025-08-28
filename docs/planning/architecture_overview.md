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
- **Event Consumption**: Subscribes to TickStockPL events via Redis pub-sub
- **Job Triggering**: Submits backtest/analysis jobs to TickStockPL via Redis
- **Result Display**: Visualizes TickStockPL-computed metrics and results
- **Basic Data Ingestion**: Receives raw market data, forwards to Redis for TickStockPL
- **Read-Only Database**: Simple queries for UI data (symbols, user preferences, alert history)

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
- `tickstock.events.patterns` - Real-time pattern detections
- `tickstock.events.backtesting.progress` - Backtest progress updates
- `tickstock.events.backtesting.results` - Completed backtest results

### Database Architecture (Single "tickstock" Database)
**Shared TimescaleDB Database**: `tickstock`
- **Tables**: `symbols`, `ohlcv_daily`, `ohlcv_1min`, `ticks` (hypertables), `events`
- **TickStockPL Role**: Full read/write access, schema management, data loading
- **TickStockApp Role**: Read-only access for UI queries only

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

[Shared Database "tickstock": TimescaleDB]
    ↕ (TickStockPL: Read/Write)
    ↕ (TickStockApp: Read-Only)
```

## Key Architectural Principles

### 1. Separation of Concerns
- **TickStockApp**: User experience and interface management
- **TickStockPL**: Data processing and analytical algorithms
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