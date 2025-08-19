# TickStock Technical Architecture

*Real-time market data processing system with WebSocket distribution*

## Executive Summary

### System Overview
Real-time financial data processing system with:
- **128** Python modules across `src/` and `config/`
- **172** classes implementing the architecture
- **12** WebSocket components for real-time distribution
- **10** event detection engines

### Core Capabilities
- **Event Detection**: HighLow, Surge, and Trend detection in real-time
- **Universe Filtering**: Core universe and user-specific stock filtering
- **Session Management**: Market session state tracking (pre-market, market, after-hours)
- **Priority Processing**: Queue-based priority management for event handling
- **Analytics**: Real-time accumulation and aggregation of market metrics

### Key Technologies
- **Backend**: Python 3.x, Flask, Flask-SocketIO
- **Real-time Data**: Polygon.io WebSocket API, Socket.IO
- **Processing**: Multi-threaded event detection pipeline with priority queues
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: In-memory caching with CacheControl

## Data Flow Architecture

### Primary Data Pipeline
```
[Polygon WebSocket API]
         ↓
  RealTimeDataAdapter
         ↓
   MarketDataService ←→ [CacheControl]
         ↓
    EventProcessor
         ↓
  ┌──────┴──────┐
  │  Detectors  │
  ├─ HighLow ───┤
  ├─ Surge ─────┤
  └─ Trend ─────┘
         ↓
   PriorityManager
         ↓
   DataPublisher
         ↓
 WebSocketPublisher
         ↓
  [User Clients]
```

### Key Processing Stages
1. **Data Ingestion**: WebSocket connection to Polygon for real-time ticks
2. **Event Detection**: Pattern recognition for market events
3. **Priority Queuing**: Event prioritization based on universe membership
4. **Accumulation**: Session-based event counting and analytics
5. **Distribution**: WebSocket emission to connected clients

## Component Interactions

### Session Management Flow
```
SessionManager determines market session
    ↓
MarketDataService.handle_market_session_change()
    ↓
Resets: Detectors, Accumulation, Analytics
```

### Universe Filtering Flow
```
User selects universes → UserUniverseManager
                              ↓
                    UniverseCoordinator
                              ↓
           Updates: BuySellTracker, WebSocketPublisher
```

### Event Lifecycle
```
Tick → Detection → Priority Queue → Collection → Filter → Emit
```

## Component Layers

### API Layer

**src/api/rest/**
- *api.py* - 40 functions
- *auth.py* - 12 functions
- *main.py* - 7 functions

### Core Services

**src/core/services/**
- **SessionAccumulationManager** (10 methods)
- **DataFlowStats** (3 methods)
- **AnalyticsOperationResult** (0 methods)
- **AnalyticsCoordinator** (5 methods)
- **AnalyticsManager** (10 methods)
- **AnalyticsSyncService** (4 methods)
- **ConfigManager** (5 methods)
- **DatabaseSyncService** (7 methods)
- **CoreServiceStats** (4 methods)
- **CoreServiceResult** (0 methods)
- **MarketDataService** (10 methods)
- **MarketMetrics** (10 methods)
- **InMemorySessionAccumulation** (10 methods)
- **InMemoryAnalytics** (8 methods)
- **MarketSession** ← Enum (0 methods)
- **SessionTransition** (0 methods)
- **SessionManager** (5 methods)
- *startup_service.py* - 5 functions
- **UniverseOperationResult** (0 methods)
- **UniverseCoordinator** (10 methods)
- **TickStockUniverseManager** (9 methods)
- **UserFiltersService** (7 methods)
- **UserSettingsService** (10 methods)

**src/core/services/universe/**
- **UniverseMetrics** (0 methods)
- **UniverseAnalytics** (8 methods)
- **CoreUniverseManager** (6 methods)
- **SubscriptionManager** (6 methods)
- **UserUniverseManager** (10 methods)

### Processing Pipeline

**src/processing/detectors/**
- **BuySellTracker** (3 methods)
- **BuySellMarketTracker** ← BuySellTracker (9 methods)
- **HighLowDetectionEngine** (1 methods)
- **SurgeDetectionEngine** (5 methods)
- **TrendDetectionEngine** (7 methods)
- **HighLowDetector** (5 methods)
- **EventDetectionResult** (0 methods)
- **EventDetectionManager** (6 methods)
- **SurgeDetector** (4 methods)
- **TrendDetector** (8 methods)
- *utils.py* - 22 functions

**src/processing/pipeline/**
- **DataFlowStats** (3 methods)
- **EventDetector** (4 methods)
- **EventProcessorStats** (4 methods)
- **EventProcessingResult** (0 methods)
- **EventProcessor** (10 methods)
- **TickProcessingResult** (0 methods)
- **TickProcessor** (4 methods)

**src/processing/queues/**
- **QueuedEvent** (2 methods)
- **TypedEventQueue** (7 methods)
- **QueueDiagnostics** (4 methods)
- **PriorityManager** (10 methods)

**src/processing/workers/**
- **WorkerPoolOperationResult** (0 methods)
- **StopEvent** ← BaseEvent (5 methods)
- **WorkerPoolManager** (8 methods)

### Data Infrastructure

**src/infrastructure/data_sources/**
- **DataProviderFactory** (2 methods)

**src/infrastructure/data_sources/adapters/**
- **RealTimeDataAdapter** (3 methods)
- **SyntheticDataAdapter** ← RealTimeDataAdapter (3 methods)

**src/infrastructure/data_sources/polygon/**
- **PolygonAPI** (6 methods)
- **PolygonDataProvider** ← DataProvider (10 methods)

**src/infrastructure/data_sources/synthetic/**
- **SyntheticDataGenerator** (3 methods)
- **SyntheticDataLoader** (5 methods)
- **SimulatedDataProvider** ← DataProvider (8 methods)

**src/infrastructure/database/models/**
- **TickerAnalytics** (1 methods)
- **UniverseAnalytics** (1 methods)
- **GaugeAnalytics** (1 methods)
- **User** ← Model (4 methods)
- **UserSettings** ← Model (0 methods)
- **UserHistory** ← Model (0 methods)
- **StockData** ← Model (0 methods)
- **AppSettings** ← Model (0 methods)
- **TaggedStock** ← Model (0 methods)
- **Session** ← Model (4 methods)
- **CommunicationLog** ← Model (0 methods)
- **VerificationCode** ← Model (0 methods)
- **Subscription** ← Model (3 methods)
- **BillingInfo** ← Model (1 methods)
- **PaymentHistory** ← Model (0 methods)
- **CacheEntry** ← Model (0 methods)
- **EventSession** ← Model (6 methods)
- **MarketAnalytics** ← Model (1 methods)
- **UserFilters** ← Model (3 methods)

### Presentation

**src/presentation/websocket/**
- **WebSocketAnalytics** (2 methods)
- **WebSocketDataFilter** (2 methods)
- **DataFlowStats** (3 methods)
- **PublishingResult** (0 methods)
- **DataPublisher** (10 methods)
- **WebSocketDisplayConverter** (3 methods)
- **WebSocketFilterCache** (4 methods)
- **WebSocketManager** (10 methods)
- **PolygonWebSocketClient** (6 methods)
- **EmissionMetrics** (2 methods)
- **WebSocketPublisher** (10 methods)
- **EmissionStats** (3 methods)
- **WebSocketStatistics** (6 methods)
- **WebSocketUniverseCache** (4 methods)

### Monitoring

**src/monitoring/**
- **HealthMonitorOperationResult** (0 methods)
- **HealthMonitor** (10 methods)
- **DataFlowStats** (3 methods)
- **MetricSnapshot** (0 methods)
- **MetricsReport** (0 methods)
- **MetricsCollector** (5 methods)
- **PerformanceLevel** ← Enum (0 methods)
- **PerformanceMetric** (1 methods)
- **PerformanceAlert** (0 methods)
- **PerformanceMonitor** (5 methods)
- **QueryDebugFilter** ← Filter (1 methods)
- **MonitoringConfig** (0 methods)
- **MetricsBuffer** (3 methods)
- **DiagnosticCollector** (3 methods)
- **SystemMonitor** (7 methods)
- **TraceLevel** ← Enum (0 methods)
- **ProcessingStep** (1 methods)
- **UserConnectionInfo** (0 methods)
- **TickerTrace** (3 methods)
- **DebugTracer** (10 methods)

## Critical Components

### Core Processing

#### MarketDataService
*Central orchestrator for market data flow*

Location: `src/core/services/market_data_service.py`

Key Methods:
- `register_with_app(app)`
- `start_processing()`
- `handle_websocket_tick(tick_data, ticker, timestamp)`
- `handle_websocket_status(status, extra_info)`
- `update_user_universe_selections(user_id, tracker_type, universes)`

#### EventProcessor
*Processes ticks and triggers event detection*

Location: `src/processing/pipeline/event_processor.py`

Key Methods:
- `generate_event_key(ticker, price, event_type...)`
- `handle_tick(tick_data)`
- `get_performance_report()`

#### PriorityManager
*Manages event queue with priority logic*

Location: `src/processing/queues/priority_manager.py`

Key Methods:
- `add_event(event)`
- `collect_typed_events(max_events, timeout, event_types...)`
- `collect_events(max_events, timeout)`
- `get_queue_status()`
- `shutdown()`

### Event Detection

#### HighLowDetector
*Detects session highs/lows with configurable thresholds*

Location: `src/processing/detectors/highlow_detector.py`

Key Methods:
- `reset_for_new_market_session(market_status)`
- `initialize_highlow_event_data(ticker, session_high, session_low...)`
- `detect_highlow(tick_data, stock_data)`
- `get_ticker_details(ticker)`

#### SurgeDetector
*Identifies volume/price surges with adaptive thresholds*

Location: `src/processing/detectors/surge_detector.py`

Key Methods:
- `detect_surge(stock_data, ticker, price...)`
- `reset_surge_quality_tracking()`
- `reset_daily_counts()`

#### TrendDetector
*Multi-window trend analysis with retracement detection*

Location: `src/processing/detectors/trend_detector.py`

Key Methods:
- `detect_trend(stock_data, ticker, price...)`
- `reset_daily_counts()`
- `get_trend_diagnostics(ticker, stock_data)`
- `cleanup_trend_tracking(max_age)`

### Data Distribution

#### DataPublisher
*Collects and buffers events for emission*

Location: `src/presentation/websocket/data_publisher.py`

Key Methods:
- `start_publishing_loop()`
- `stop_publishing_loop()`
- `publish_to_users()`
- `get_buffered_events(clear_buffer)`
- `get_buffer_status()`

#### WebSocketPublisher
*Manages WebSocket emissions to users*

Location: `src/presentation/websocket/publisher.py`

Key Methods:
- `set_data_publisher(data_publisher)`
- `start_emission_timer()`
- `run_emission_cycle()`
- `send_status_update(status, extra_info, user_id)`
- `prepare_heartbeat(api_health, market_status, user_id)`

#### WebSocketManager
*Handles client connections and rooms*

Location: `src/presentation/websocket/manager.py`

Key Methods:
- `register_client(client_id)`
- `unregister_client(client_id)`
- `register_user_connection(user_id, connection_id)`
- `unregister_user_connection(connection_id)`
- `emit_to_user(data, user_id, event_name)`

### Universe Management

#### UniverseCoordinator
*Coordinates universe filtering across components*

Location: `src/core/services/universe_coordinator.py`

Key Methods:
- `update_user_universe_selections(user_id, tracker_type, universes)`
- `get_user_universe_info(user_id)`
- `invalidate_user_universe_cache(user_id)`
- `get_core_universe_info()`
- `refresh_core_universe()`

#### CoreUniverseManager
*Manages core stock universe*

Location: `src/core/services/universe/core_manager.py`

Key Methods:
- `get_core_universe_info()`
- `refresh_core_universe()`
- `check_core_universe_membership(ticker)`
- `perform_health_check()`
- `check_data_flow_health()`

#### UserUniverseManager
*Handles user-specific universe selections*

Location: `src/core/services/universe/user_manager.py`

Key Methods:
- `get_or_load_user_universes(user_id)`
- `update_user_universe_cache(user_id, universe_selections)`
- `invalidate_user_universe_cache(user_id)`
- `get_all_user_universe_tickers(user_id)`
- `check_data_flow_health()`

## Configuration & Deployment

### Environment Variables
- `POLYGON_API_KEY`: Required for real-time data
- `USE_REAL_DATA`: Toggle between real/simulated data
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Optional Redis cache

### Key Configuration Files
- `config/app_config.py`: Main configuration loader
- `config/environments/`: Environment-specific settings
- `config/logging_config.py`: Logging configuration

### Performance Tuning
- Worker pool size: Configurable based on load
- Queue sizes: Adjustable for memory/latency tradeoff
- Emission intervals: Balance between latency and efficiency
- Cache TTLs: Optimize for data freshness vs API calls

## Configuration Components

**config/__init__.py**

**config/app_config.py**
- Functions: 5

**config/environments/__init__.py**

**config/environments/dev.py**
- Constants: DEBUG, TESTING, LOG_LEVEL, DATABASE_URI, REDIS_URL

**config/environments/prod.py**
- Constants: DEBUG, TESTING, LOG_LEVEL, DATABASE_URI, REDIS_URL

**config/logging_config.py**
- Classes: LogDomain, DomainLogFilter, QueryDebugFilter, LoggingManager
- Functions: 5
- Constants: SESSION_ID, CORE, AUTH_SESSION, USER_SETTINGS, UNIVERSE_TRACKING

## Key Dependencies

| Service | Dependencies |
|---------|-------------|
| MarketDataService | UniverseCoordinator, UserSettingsService, WebSocketPublisher, DataPublisher, SessionAccumulationManager |
| UniverseCoordinator | SubscriptionManager, UserUniverseManager, CoreUniverseManager |
| WebSocketPublisher | UserSettingsService, UserFiltersService |

## Quick Reference Index

### Services
- `AnalyticsSyncService` → src/core/services/analytics_sync.py
- `CoreServiceResult` → src/core/services/market_data_service.py
- `CoreServiceStats` → src/core/services/market_data_service.py
- `DatabaseSyncService` → src/core/services/database_sync.py
- `MarketDataService` → src/core/services/market_data_service.py
- `UserFiltersService` → src/core/services/user_filters_service.py
- `UserSettingsService` → src/core/services/user_settings_service.py

### Detectors
- `EventDetector` → src/processing/pipeline/event_detector.py
- `HighLowDetector` → src/processing/detectors/highlow_detector.py
- `SurgeDetector` → src/processing/detectors/surge_detector.py
- `TrendDetector` → src/processing/detectors/trend_detector.py

### Managers
- `AnalyticsManager` → src/core/services/analytics_manager.py
- `AuthenticationManager` → src/auth/authentication.py
- `ConfigManager` → src/core/services/config_manager.py
- `CoreUniverseManager` → src/core/services/universe/core_manager.py
- `EmailManager` → src/infrastructure/messaging/email_service.py
- `EventDetectionManager` → src/processing/detectors/manager.py
- `LoggingManager` → config/logging_config.py
- `PriorityManager` → src/processing/queues/priority_manager.py
- `RegistrationManager` → src/auth/registration.py
- `SMSManager` → src/infrastructure/messaging/sms_service.py
- `SessionAccumulationManager` → src/core/services/accumulation_manager.py
- `SessionManager` → src/auth/session.py
- `SessionManager` → src/core/services/session_manager.py
- `SubscriptionManager` → src/core/services/universe/subscription_manager.py
- `TickStockUniverseManager` → src/core/services/universe_service.py

### Models
- `AppSettings` → src/infrastructure/database/models/base.py
- `BillingInfo` → src/infrastructure/database/models/base.py
- `CacheEntry` → src/infrastructure/database/models/base.py
- `CommunicationLog` → src/infrastructure/database/models/base.py
- `EventSession` → src/infrastructure/database/models/base.py
- `GaugeAnalytics` → src/infrastructure/database/models/analytics.py
- `MarketAnalytics` → src/infrastructure/database/models/base.py
- `PaymentHistory` → src/infrastructure/database/models/base.py
- `Session` → src/infrastructure/database/models/base.py
- `StockData` → src/infrastructure/database/models/base.py
- `Subscription` → src/infrastructure/database/models/base.py
- `TaggedStock` → src/infrastructure/database/models/base.py
- `TickerAnalytics` → src/infrastructure/database/models/analytics.py
- `UniverseAnalytics` → src/infrastructure/database/models/analytics.py
- `User` → src/infrastructure/database/models/base.py

### Utils
- `DataFlowValidator` → src/shared/utils/validation.py
- `EventFactory` → src/shared/utils/event_factory.py
- `EventValidator` → src/shared/utils/validation.py
- `FieldValidator` → src/shared/utils/validation.py

