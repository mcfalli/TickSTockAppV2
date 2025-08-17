# TickStock V2 - Project Structure Documentation
*Generated: 2025-08-17T11:44:34.999580*
*Version: 2.0*
*Architecture: Modular Architecture (src/)*

## Table of Contents
1. [Application Overview](#application-overview)
2. [System Architecture](#system-architecture)
3. [Module Structure](#module-structure)
4. [Core Domains](#core-domains)
5. [Data Flows](#data-flows)
6. [Component Inventory](#component-inventory)
7. [WebSocket Architecture](#websocket-architecture)
8. [Event Processing](#event-processing)
9. [External Dependencies](#external-dependencies)
10. [Configuration](#configuration)
11. [Testing Strategy](#testing-strategy)
12. [Frontend Architecture](#frontend-architecture)
13. [Quality Metrics](#quality-metrics)
14. [Sprint Tracking](#sprint-tracking)

## Application Overview
**TickStock V2** - High-performance market data processing with sub-millisecond event detection

- **Type**: Real-time Market Data Processing System
- **Backend**: Flask with Flask-SocketIO
- **Frontend**: JavaScript SPA with WebSocket
- **Architecture**: Component-based with Pull Model Event Distribution
- **Data Flow**: WebSocket → Core Services → Event Processing → User Distribution

### Key Features
- Real-time market data processing (4,000+ tickers)
- Sub-millisecond event detection
- Pull-based event distribution (zero event loss)
- Per-user data isolation and filtering
- Modular component architecture

## System Architecture
**Pattern**: Modular Component Architecture

### Architectural Layers
- **Presentation**: WebSocket & API Layer (src/presentation, src/api)
- **Business**: Core Services & Domain Logic (src/core)
- **Processing**: Event Detection & Processing (src/processing)
- **Infrastructure**: Data Sources & External Services (src/infrastructure)
- **Shared**: Utilities & Constants (src/shared)

### Design Patterns
- Dependency Injection
- Event-Driven Architecture
- Pull Model Distribution
- Memory-First Processing
- Per-User Isolation

## Module Structure
### Core Business Logic
*Core Business Logic*

- **Files**: 37
- **Components**: 45
- **Key Components**: AnalyticsCoordinator, AnalyticsManager, AnalyticsOperationResult, AnalyticsSyncService, BaseEvent

### External Integrations & Data Layer
*External Integrations & Data Layer*

- **Files**: 25
- **Components**: 32
- **Key Components**: AppSettings, BillingInfo, CacheControl, CacheEntry, CommunicationLog

### User Interface & WebSocket Layer
*User Interface & WebSocket Layer*

- **Files**: 16
- **Components**: 50
- **Key Components**: ActivityMetrics, ActivityWindow, AggregationInfo, BuySellMetrics, ChangePasswordForm

### Event Detection & Processing Pipeline
*Event Detection & Processing Pipeline*

- **Files**: 20
- **Components**: 36
- **Key Components**: BuySellMarketTracker, BuySellTracker, DataFlowStats, EventDetectionManager, EventDetectionResult

### REST & WebSocket API Endpoints
*REST & WebSocket API Endpoints*

- **Files**: 7
- **Components**: 4
- **Key Components**: register_api_routes, register_auth_routes, register_main_routes, register_universe_api_routes

### Authentication & Authorization
*Authentication & Authorization*

- **Files**: 4
- **Components**: 6
- **Key Components**: AuthenticationManager, RegistrationManager, SessionManager, create_session, detect_concurrent_login

### System Monitoring & Metrics
*System Monitoring & Metrics*

- **Files**: 7
- **Components**: 17
- **Key Components**: DataFlowStats, DiagnosticCollector, HealthMonitor, HealthMonitorOperationResult, MetricSnapshot

### Shared Utilities & Constants
*Shared Utilities & Constants*

- **Files**: 9
- **Components**: 5
- **Key Components**: DataFlowValidator, EventFactory, EventValidator, FieldValidator, detect_market_status

### Root
*Root level files and scripts*

- **Files**: 203
- **Components**: 61
- **Key Components**: ComponentAnalyzer, ComprehensiveTestRunner, CreateProjectStructureDocumentation, DependencyCreator, DocumentationExtractor

## Core Domains
### Market Data Processing
**Purpose**: Real-time market data ingestion and processing

**Data Sources**:
- Polygon.io WebSocket
- Synthetic Data Generator
**Processing Capacity**: 4,000+ tickers with sub-millisecond processing

**Key Components**:
- `handle_market_session_change`
- `create_cache_database_engine`
- `initialize_cache_with_database`
- `TickStockUniverseManager`
- `UserSettingsService`
- `handle_websocket_status`
- `DatabaseSyncService`
- `register_with_app`

### Event Detection
**Purpose**: Identify market patterns and significant events

**Detection Types**:
- High/Low Detection (0.1% threshold)
- Trend Analysis (180/360/600s windows)
- Volume Surge Detection (3x average)

**Key Components**:
- `EventDetector`
- `detect_events`
- `process_tick`
- `TickProcessor`
- `handle_market_status_change`
- `QueuedEvent`
- `TypedEventQueue`
- `EventProcessingResult`

### Websocket Communication
**Purpose**: Real-time data distribution to clients

**Architecture**: Pull-based model with zero event loss
**Features**:
- Per-user filtering
- Event buffering (1000 events/type)
- Independent emission timers

**Key Components**:
- `SimpleAverages`
- `register_user_connection`
- `WebSocketPublisher`
- `DataPublisher`
- `PerformanceMetrics`
- `SessionAccumulation`
- `VerticalAnalytics`
- `ActivityWindow`

### Authentication
**Purpose**: User authentication and session management

**Features**:
- Email/SMS verification
- Session tracking
- Rate limiting
- Password reset flows

**Key Components**:
- `create_session`
- `SessionManager`
- `detect_concurrent_login`
- `AuthenticationManager`
- `register_user`
- `RegistrationManager`

### Monitoring
**Purpose**: System health and performance monitoring

**Metrics**:
- Processing latency
- Queue depths
- Event rates
- API health

**Key Components**:
- `PerformanceLevel`
- `MonitoringConfig`
- `HealthMonitorOperationResult`
- `register_metrics_source`
- `PerformanceMetric`
- `DataFlowStats`
- `MetricsCollector`
- `DiagnosticCollector`

## Data Flows
### Market Data Pipeline
**Stages**:
1. Data Source (Polygon/Synthetic)
2. WebSocket Ingestion
3. MarketDataService.handle_tick()
4. EventProcessor.process_tick()
5. Event Detection (HighLow/Trend/Surge)
6. Priority Queue Management
7. Worker Pool Processing
8. Display Queue (for UI events)
9. DataPublisher Collection
10. WebSocketPublisher Pull & Emit

**Processing Time**: Sub-millisecond per tick

### Pull Model Event Distribution
*Zero event loss architecture (Sprint 29)*

**Flow**:
- Workers → Convert typed events to dicts
- Display Queue → Buffer events
- DataPublisher → Collect & buffer (up to 1000/type)
- WebSocketPublisher → Pull on timer
- Per-user filtering
- WebSocket emission to clients
**Benefits**: Eliminates 37% event loss from push model

### User Authentication Flow
**Stages**:
1. Registration/Login Request
2. Credential Validation
3. Email/SMS Verification
4. Session Creation
5. JWT Token Generation
6. WebSocket Authentication

## Component Inventory
### Core Processing
*Heart of data processing pipeline*

- **AnalyticsManager** (class)
  - Market Analytics Manager with accumulation-based processing.
- **ConfigManager** (class)
  - Centralized configuration management with validation.
- **MarketDataService** (class)
  - Clean orchestration layer for market data processing.
- **SessionManager** (class)

### Event Processing
*Event detection and management*

- **BuySellTracker** (class)
  - Base class for buy/sell pressure trackers.
- **EventDetectionManager** (class)
  - Unified manager for all event detection types
- **EventProcessor** (class)
  - Handles all event processing logic with clean dependency injection.
- **EventProcessorStats** (class)
- **HighLowDetector** (class)
- **SurgeDetector** (class)
- **TickProcessor** (class)
  - Handles core tick processing logic.
- **TrendDetector** (class)
  - Enhanced trend detection for stock price movements.

### Websocket Layer
*Real-time communication*

- **DataPublisher** (class)
  - Handles all data publishing logic with clean separation of concerns.
- **PolygonWebSocketClient** (class)
  - PHASE 4 COMPLIANCE for polygon_websocket_client.py:
- **WebSocketAnalytics** (class)
  - Prepares analytics data for WebSocket emission.
- **WebSocketDataFilter** (class)
  - Handles all data filtering operations for WebSocket emissions.
- **WebSocketManager** (class)
- **WebSocketPublisher** (class)
  - Enhanced WebSocket publisher with comprehensive universe filtering logging.

### Data Providers
*Data source integrations*

- **DataProvider** (class)
  - Abstract base class for stock market data providers.
- **DataProviderFactory** (class)
  - Factory for creating data provider instances with a registry pattern.
- **PolygonDataProvider** (class)
  - Class to handle Polygon.io API interactions with enhanced rate limiting and caching
- **RealTimeDataAdapter** (class)
  - Adapter for handling real-time data streams from WebSocket providers.
- **SimulatedDataProvider** (class)
  - Provider that generates simulated stock market data with comprehensive tracing.

### Infrastructure
*Supporting services*

- **CacheControl** (class)
  - Singleton class to manage cached stock lists and metadata.
- **DatabaseSyncService** (class)
  - Handles database synchronization for session accumulation.
- **HealthMonitor** (class)
  - Monitors system health and collects performance metrics.
- **HealthMonitorOperationResult** (class)
  - Result object for health monitor operations.
- **MetricsCollector** (class)
  - Centralized metrics collection and aggregation system.
- **PerformanceMonitor** (class)
  - Unified performance monitoring and alerting system.

## WebSocket Architecture
**Architecture**: Pull-based distribution model
**Components**: 11

### Features
- Per-user data isolation
- Event buffering (1000 events/type)
- Independent emission timers
- LRU cache with 1-hour TTL
- User filter preferences

### Event Types
- `filters_updated`
- `test_event`
- `request_filtered_data_refresh`
- `session_reset`
- `disconnect`
- `connect`
- `dual_universe_stock_data`
- `user_status_response`
- `universe_updated`
- `status_update`

## Event Processing
**Detectors**: 8
**Processing Model**: Typed events → Worker conversion → Dict transport

### Event Types
- HighLowEvent (0.1% threshold)
- TrendEvent (180/360/600s windows)
- SurgeEvent (3x volume average)
- ControlEvent (system events)

### Queue Priorities
- P0: Control events
- P1: High priority market events
- P2: Standard market events
- P3: Low priority events
- P4: Background tasks

## External Dependencies
### Data Sources
- Polygon.io WebSocket API
- Synthetic Data Generator (development)

### Databases
- PostgreSQL (user data, analytics)
- Redis (caching, session storage)

### Messaging
- Twilio (SMS verification)
- SMTP (email notifications)

### Infrastructure
- Docker (containerization)
- Nginx (reverse proxy)
- Prometheus (metrics)
- Eventlet (async processing)

### Frontend
- Socket.IO (real-time communication)
- Chart.js (data visualization)
- GridStack (layout management)

## Configuration
### Environment
*Environment-specific settings*
- `.env`
- `config/environments/dev.py`
- `config/environments/prod.py`
- `config/environments/__init__.py`

### Application
*Application configuration modules*
- `config/app_config.py`
- `config/logging_config.py`
- `config/__init__.py`
- `config/environments/dev.py`
- `config/environments/prod.py`

### Deployment
*Container and server configuration*
- `docker/docker-compose.yml`
- `docker/Dockerfile`
- `docker/nginx.conf`

### Monitoring
*Logging and metrics configuration*
- `config/logging_config.py`
- `config/prometheus.yml`

## Testing Strategy
**Total Tests**: 47

### Coverage
- **Unit Tests**: 2
- **Integration Tests**: 18
- **Performance Tests**: 1

## Frontend Architecture
### JavaScript
- **Files**: 7
- **Modular Files**: 7
- **Key Modules**:
  - app-core.js (Foundation)
  - app-universe.js (Universe management)
  - app-gauges.js (Visualizations)
  - app-events.js (Event handling)
  - app-filters.js (Data filtering)

### CSS
- **Files**: 17
- **Architecture**: Modular component-based

## Quality Metrics
- **Modularity Score**: Excellent
- **Test Coverage**: 19.7%
- **Documentation Files**: 33
- **Critical Components**: 35
- **Component Documentation**: 234

## Sprint Tracking
- **Latest Sprint**: Sprint 54
- **Total References**: 141
- **Unique Sprints**: 1, 2, 6, 17, 21, 26, 27, 28, 29, 32, 36, 41, 48, 54

## Statistics
- **Total Files**: 328
- **Python Files**: 213
- **JavaScript Files**: 7
- **CSS Files**: 17
- **Test Files**: 42
- **Config Files**: 16

---
*This documentation was automatically generated from the project structure.*
