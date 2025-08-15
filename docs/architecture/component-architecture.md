# TickStock Component Architecture

**Version:** 3.0  
**Last Updated:** June 2025  
**Architecture:** 17-Component System with WebSocket Extensions

## Overview

TickStock employs a sophisticated component-based architecture with 17 core components plus specialized WebSocket components for real-time data distribution. This document provides the complete technical specification for each component.

## Architecture Principles

1. **Single Responsibility**: Each component has one clearly defined purpose
2. **Dependency Injection**: Components use hybrid dependency injection for flexibility
3. **Memory-First Processing**: All operations prioritize in-memory processing
4. **Event-Driven Design**: Asynchronous processing with event-based communication
5. **Direct Component Access**: No delegation layers - components are accessed directly

## System Hierarchy

```
TickStock Application
├── Flask Application Layer
│   ├── Routes (app_routes_*.py)
│   └── WebSocket Handlers (app.py)
├── Market Data Service (Orchestrator)
│   ├── Core Processing Components (6)
│   ├── Event Processing Components (3)
│   ├── Universe Management Components (4)
│   └── Data Flow Components (4)
├── WebSocket Components
│   ├── WebSocketPublisher
│   ├── WebSocketUniverseCache
│   ├── WebSocketFilterCache
│   └── WebSocketDataFilter
└── Infrastructure Layer
    ├── Database (PostgreSQL)
    ├── Cache (Redis)
    └── Data Providers (Polygon/Simulated)
```

## Core Processing Components (6)

### 1. EventProcessor
**Location:** `market_data_service/event_processor.py`  
**Purpose:** Central orchestrator for all tick processing and event detection

```python
class EventProcessor:
    """
    Coordinates the entire tick processing pipeline with dual universe support.
    Uses extracted TickProcessor and EventDetector components.
    """
    def handle_tick(self, tick_data) -> EventProcessingResult
    def _process_tick_event(self, queue_data) -> EventProcessingResult
    def _process_dual_universe(self, ticker, events, in_core, in_user)
    def get_performance_report() -> Dict[str, Any]
    def reset_performance_stats() -> None
```

**Key Features:**
- Hybrid dependency injection pattern
- Comprehensive statistics tracking via `EventProcessorStats`
- Dual universe processing (core vs user)
- Integration with debug logging for CSV data export
- Performance monitoring with warnings for slow processing (>100ms)

**Statistics Tracked:**
```python
class EventProcessorStats:
    ticks_received: int
    ticks_processed: int
    events_detected: int
    events_published: int
    core_universe_hits: int
    user_universe_hits: int
    errors: int
```

### 2. DataPublisher
**Location:** `market_data_service/data_publisher.py`  
**Purpose:** Manages all data publishing and per-user routing

```python
class DataPublisher:
    """
    Handles data publishing with per-user filtering and WebSocket emission.
    """
    def publish_to_users() -> PublishingResult
    def start_publishing_loop() -> bool
    def stop_publishing_loop() -> None
    def _prepare_stock_data(recent_events: Dict) -> Dict
    def _update_event_buffer(events: Dict)
    def get_performance_report() -> Dict[str, Any]
```

**Key Features:**
- Dedicated publishing thread with configurable intervals
- Event buffering (30-second retention for late-joining users)
- Per-user authentication and routing
- Comprehensive data flow statistics
- Event deduplication tracking

**Publishing Flow:**
1. Collect events from various sources
2. Buffer events for reliability
3. Apply per-user filtering
5. Emit to authenticated users

### 3. UniverseCoordinator
**Location:** `market_data_service/universe_coordinator.py`  
**Purpose:** Thin coordination layer for all universe operations

```python
class UniverseCoordinator:
    """
    Delegates universe operations to 4 specialized managers.
    """
    def update_user_universe_selections(user_id, tracker_type, universes) -> UniverseOperationResult
    def check_universe_membership(ticker, user_id) -> Dict[str, Any]
    def get_user_universe_info(user_id) -> Dict[str, Any]
    def refresh_core_universe() -> bool
    def invalidate_user_universe_cache(user_id) -> bool
    def get_subscription_coverage() -> Dict[str, Any]
```

**Manages 4 Sub-components:**
- **UserUniverseManager**: Per-user universe preferences
- **CoreUniverseManager**: System-wide core universe (~2,800 stocks)
- **SubscriptionManager**: WebSocket subscription tracking
- **UniverseAnalytics**: Coverage and efficiency metrics

### 4. AnalyticsCoordinator
**Location:** `market_data_service/analytics_coordinator.py`  
**Purpose:** Manages all analytics operations and database persistence

```python
class AnalyticsCoordinator:
    """
    Coordinates analytics generation and database synchronization.
    """
    def get_analytics_for_websocket() -> AnalyticsOperationResult
    def sync_accumulation_to_database_safe() -> AnalyticsOperationResult
    def get_session_accumulation_data_memory(tickers) -> AnalyticsOperationResult
    def initialize_session_accumulation() -> AnalyticsOperationResult
    def get_performance_report() -> Dict[str, Any]
```

**Key Features:**
- Real-time analytics generation
- 10-second database sync intervals
- Memory-first operations with periodic persistence
- Session accumulation tracking
- Thread-safe database operations

### 5. WorkerPoolManager
**Location:** `processing/worker_pool.py`  
**Purpose:** Manages worker threads and event distribution

```python
class WorkerPoolManager:
    """
    Dynamic worker pool management with priority-based distribution.
    """
    def start_workers(num_workers=4) -> WorkerPoolOperationResult
    def stop_workers() -> WorkerPoolOperationResult
    def adjust_worker_pool(target_size) -> WorkerPoolOperationResult
    def get_worker_pool_status() -> Dict[str, Any]
```

**Key Features:**
- Dynamic scaling (2-16 workers)
- Priority-based event distribution
- Queue depth monitoring
- Graceful shutdown handling
- Thread-safe operations

### 6. HealthMonitor
**Location:** `market_data_service/health_monitor.py`  
**Purpose:** System health monitoring and performance tracking

```python
class HealthMonitor:
    """
    Monitors system health and collects performance metrics.
    """
    def start() -> HealthMonitorOperationResult
    def stop() -> HealthMonitorOperationResult
    def get_health_status() -> Dict[str, Any]
    def log_system_metrics() -> HealthMonitorOperationResult
    def cleanup_stock_details() -> HealthMonitorOperationResult
```

**Key Features:**
- Real-time health monitoring
- MetricsCollector integration
- Session transition detection
- Resource cleanup operations
- Worker pool scaling coordination
- Periodic cleanup tasks

## Event Processing Components (3)

### 7. TickProcessor
**Location:** `processing/tick_processor.py`  
**Purpose:** Validates and enriches incoming tick data

```python
class TickProcessor:
    """
    First stage of tick processing - validation and enrichment.
    """
    def process_tick(tick_data) -> TickProcessingResult
    def _validate_tick_data(tick_data) -> bool
    def _apply_rate_limiting(ticker) -> bool
    def _enrich_tick_data(tick_data) -> Dict
```

**Processing Pipeline:**
1. Data validation (required fields, data types)
2. Rate limiting per ticker
3. VWAP calculation and enrichment
4. Volume analytics enrichment
5. Data format standardization

### 8. EventDetector
**Location:** `processing/event_detector.py`  
**Purpose:** Coordinates all event detection logic

```python
class EventDetector:
    """
    Detects market events from processed tick data.
    """
    def detect_events(tick_data, stock_state) -> EventDetectionResult
    def _detect_high_low_events(tick_data, stock_state) -> List[Event]
    def _detect_trend_changes(tick_data, stock_state) -> List[Event]
    def _detect_volume_surges(tick_data, stock_state) -> List[Event]
```

**Detected Event Types:**
- **High/Low Events**: New session highs and lows
- **Trend Changes**: Up/down trend detection across multiple timeframes
- **Volume Surges**: Abnormal volume spikes
- **Momentum Shifts**: Significant price movement patterns

### 9. PriorityManager
**Location:** `processing/priority_manager.py`  
**Purpose:** Manages event prioritization and queue operations

```python
class PriorityManager:
    """
    Priority-based queue management with circuit breaker protection.
    """
    def add_event(event_type, event_data, ticker=None) -> bool
    def get_queue_stats() -> QueueStats
    def collect_events(max_events=None, timeout=0.1) -> List[Tuple[str, Any]]
    def calculate_priority(event_type, ticker) -> int
```

**Priority Levels:**
1. Priority tickers (TSLA, NVDA) + surge events
2. High/Low events + important tickers
3. Trend events + regular tickers
4. Status updates and other events

**Features:**
- Circuit breaker protection
- Queue overflow handling
- Dynamic batch sizing
- Performance tracking

## Universe Management Components (4)

### 10. UserUniverseManager
**Location:** `universe/user_universe_manager.py`  
**Purpose:** Manages per-user universe selections

```python
class UserUniverseManager:
    """
    Handles user-specific universe preferences with caching.
    """
    def save_user_universe_selections(user_id, tracker_type, universes) -> bool
    def get_or_load_user_universes(user_id) -> Dict[str, List[str]]
    def get_all_user_universe_tickers(user_id) -> Set[str]
    def invalidate_user_universe_cache(user_id) -> bool
    def get_cache_status() -> Dict[str, Any]
```

**Features:**
- In-memory caching with 1-hour TTL
- Database persistence
- Thread-safe operations
- Support for multiple universe types per user

### 11. CoreUniverseManager
**Location:** `universe/core_universe_manager.py`  
**Purpose:** Manages the system-wide core universe

```python
class CoreUniverseManager:
    """
    Maintains the core universe of ~2,800 stocks.
    """
    def refresh_core_universe() -> bool
    def check_core_universe_membership(ticker) -> Dict[str, bool]
    def get_core_universe_info() -> Dict[str, Any]
    def is_ticker_in_core(ticker) -> bool
```

**Features:**
- Automatic refresh on startup
- Efficient membership checking
- Thread-safe operations
- Integration with market data providers

### 12. SubscriptionManager
**Location:** `universe/subscription_manager.py`  
**Purpose:** Tracks active WebSocket subscriptions

```python
class SubscriptionManager:
    """
    Monitors which tickers have active WebSocket subscribers.
    """
    def get_subscription_tickers() -> List[str]
    def update_subscriptions(connected_sids) -> bool
    def add_subscription(user_id, ticker) -> bool
    def remove_subscription(user_id, ticker) -> bool
```

### 13. UniverseAnalytics
**Location:** `universe/universe_analytics.py`  
**Purpose:** Provides universe coverage analytics

```python
class UniverseAnalytics:
    """
    Analyzes universe efficiency and coverage metrics.
    """
    def analyze_subscription_coverage(subscribed_tickers, universes, user_id) -> Dict
    def get_universe_metrics() -> UniverseMetrics
    def calculate_overlap_metrics(user_universes, core_universe) -> Dict
```

## Data Flow Components (4)


### 15. SessionManager
**Location:** `data_flow/session_manager.py`  
**Purpose:** Tracks market sessions and transitions

```python
class SessionManager:
    """
    Manages market session states and transitions.
    """
    def check_session_transition() -> Optional[SessionTransition]
    def get_current_session() -> MarketSession
    def register_session_callback(name, callback)
    def get_session_info() -> Dict[str, Any]
```

**Market Sessions (Eastern Time):**
- **PREMARKET**: 4:00 AM - 9:30 AM
- **REGULAR**: 9:30 AM - 4:00 PM
- **AFTERHOURS**: 4:00 PM - 8:00 PM
- **CLOSED**: All other times

### 16. MetricsCollector
**Location:** `data_flow/metrics_collector.py`  
**Purpose:** Centralizes system metrics collection

```python
class MetricsCollector:
    """
    Aggregates metrics from all system components.
    """
    def register_metrics_source(name, collector_func)
    def collect_all_metrics() -> MetricsReport
    def get_system_metrics_summary() -> Dict[str, Any]
    def export_metrics_for_monitoring() -> Dict
```

**Collected Metrics:**
- Component health status
- Processing performance
- Queue depths
- Memory usage
- Error rates

### 17. PerformanceMonitor
**Location:** `data_flow/performance_monitor.py`  
**Purpose:** Tracks performance and generates alerts

```python
class PerformanceMonitor:
    """
    Monitors system performance and triggers alerts.
    """
    def record_operation_time(component, operation, start_time, success)
    def check_thresholds() -> List[PerformanceAlert]
    def get_performance_summary() -> Dict[str, Any]
    def set_alert_threshold(metric, threshold)
```

## WebSocket Components

### WebSocketPublisher
**Location:** `websocket_publisher.py`  
**Purpose:** Main WebSocket emission coordinator

```python
class WebSocketPublisher:
    """
    Coordinates WebSocket data emission with per-user filtering.
    Contains specialized cache components for universe and filter management.
    """
    # Direct component access
    self.universe_cache: WebSocketUniverseCache
    self.filter_cache: WebSocketFilterCache
    self.data_filter: WebSocketDataFilter
    self.analytics: WebSocketAnalytics
    self.statistics: WebSocketStatistics
    
    def emit_stock_data_with_per_user_filtering(data, event_type='stock_update')
    def send_status_update(status, extra_info=None, user_id=None)
    def start_heartbeat() -> bool
    def stop_heartbeat() -> bool
```

### WebSocketUniverseCache
**Location:** `websocket_universe_cache.py`  
**Purpose:** Manages per-user universe caching for WebSocket operations

```python
class WebSocketUniverseCache:
    """
    Caches user universe selections for efficient WebSocket filtering.
    """
    def get_or_load_user_universes(user_id) -> Dict[str, List[str]]
    def update_cache(user_id, selections) -> bool
    def invalidate_cache(user_id) -> bool
    def get_cache_status() -> Dict[str, Any]
    def clear_all_cache() -> None
```

**Cache Features:**
- LRU caching strategy
- 1-hour TTL per user
- Lazy loading from database
- Thread-safe operations

### WebSocketFilterCache
**Location:** `websocket_filter_cache.py`  
**Purpose:** Manages per-user filter caching

```python
class WebSocketFilterCache:
    """
    Caches user filter preferences for WebSocket operations.
    """
    def get_or_load_user_filters(user_id) -> Dict[str, Any]
    def update_cache(user_id, filter_data) -> bool
    def invalidate_cache(user_id) -> bool
    def get_cache_status() -> Dict[str, Any]
```

### WebSocketDataFilter
**Location:** `websocket_data_filter.py`  
**Purpose:** Applies filtering logic to data streams

```python
class WebSocketDataFilter:
    """
    Filters data based on universe and user preferences.
    """
    def apply_universe_filtering(data, user_universes) -> Dict
    def apply_user_filters(data, user_filters) -> Dict
    def should_include_ticker(ticker, user_config) -> bool
```

## Component Communication Patterns

### Direct Component Access Pattern
```python
# Correct - Direct access through parent
market_service.event_processor.handle_tick(tick_data)
market_service.websocket_publisher.universe_cache.invalidate_cache(user_id)
market_service.universe_coordinator.user_universe_manager.get_cache_status()

# Incorrect - Old delegation pattern (removed)
market_service.handle_tick(tick_data)  # NO LONGER EXISTS
```

### Standardized Result Objects
All components return standardized result objects:
```python
@dataclass
class OperationResult:
    success: bool = True
    data: Optional[Any] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0
    operation_type: str = "unknown"
```

### Event Flow Example
```
1. Tick arrives → MarketDataService receives
2. Routes to EventProcessor.handle_tick()
3. TickProcessor validates and enriches
4. EventDetector identifies events
5. PriorityManager queues events
6. WorkerPool processes in parallel
7. DataPublisher formats and routes
8. WebSocketPublisher applies filtering
9. Users receive personalized data
```

## Initialization and Dependencies

### Component Initialization Order
```python
# 1. Infrastructure Components
session_manager = SessionManager(config)
metrics_collector = MetricsCollector(config)
performance_monitor = PerformanceMonitor(config)

# 2. Processing Components  
tick_processor = TickProcessor(config)
event_detector = EventDetector(config, detectors)
priority_manager = PriorityManager(config)

# 3. Core Processing Components
event_processor = EventProcessor(config, market_service, dependencies)
worker_pool_manager = WorkerPoolManager(config, priority_manager)
health_monitor = HealthMonitor(config, market_service)

# 4. Universe Components
user_universe_manager = UserUniverseManager(config)
core_universe_manager = CoreUniverseManager(config)
subscription_manager = SubscriptionManager(config)
universe_analytics = UniverseAnalytics(config)
universe_coordinator = UniverseCoordinator(config, managers)

# 5. Analytics & Publishing
analytics_coordinator = AnalyticsCoordinator(config, market_service)
data_publisher = DataPublisher(config, market_service)

# 6. WebSocket Components
websocket_publisher = WebSocketPublisher(websocket_mgr, config)
```

### Dependency Injection Pattern
Components use a hybrid dependency injection pattern:
```python
def __init__(self, config, market_service, specific_dep=None):
    # Required dependencies
    self.config = config
    self.market_service = market_service
    
    # Optional with fallback
    self.specific_dep = specific_dep or market_service.specific_dep
    
    # Extract component-specific config
    self.component_config = self._extract_config(config)
```

## Performance Characteristics

### Processing Metrics
| Operation | Target | Typical | Max |
|-----------|--------|---------|-----|
| Tick Validation | < 0.5ms | 0.2ms | 1ms |
| Event Detection | < 5ms | 2-3ms | 10ms |
| Queue Addition | < 0.1ms | 0.05ms | 0.5ms |
| Publishing/User | < 10ms | 5-8ms | 20ms |
| DB Sync | 10s interval | 10s | 30s |

### Resource Utilization
- **Memory**: ~500MB base + 100MB per 1000 active users
- **CPU**: 2-4 cores typical, scales with worker pool
- **Network**: 10-50 Mbps depending on market activity
- **Database**: 500:1 write reduction through batching

## Configuration Parameters

### Core Processing
```python
UPDATE_INTERVAL = 0.5           # Publishing interval (seconds)
WORKER_POOL_SIZE = 4           # Default worker threads
MAX_WORKER_POOL_SIZE = 16      # Maximum worker threads
MIN_WORKER_POOL_SIZE = 2       # Minimum worker threads
```

### Event Detection
```python
HIGH_LOW_LOOKBACK_SECONDS = 2400    # 40 minutes
TREND_SHORT_WINDOW = 180            # 3 minutes
SURGE_VOLUME_THRESHOLD = 1.5        # 1.5x average
EVENT_RATE_LIMIT = 0.1              # Min seconds between events
```

### Caching
```python
UNIVERSE_CACHE_TTL = 3600          # 1 hour
FILTER_CACHE_TTL = 1800            # 30 minutes
EVENT_BUFFER_DURATION = 30         # 30 seconds
MAX_EVENTS_PER_TICKER = 50         # Event history limit
```

## Recent Architecture Changes (June 2025)

### Removed Features
- All delegation methods from MarketDataService
- Legacy monolithic processing functions
- Redundant caching layers

### Added Features
- Direct component access pattern
- Standardized result objects across all components
- Enhanced performance monitoring
- Comprehensive debug logging with CSV export

### Migration Notes
- Components now accessed directly through parents
- All operations return standardized result objects
- WebSocket components manage their own caches
- Performance tracking integrated at all levels

---
*This architecture enables TickStock to process 4,000+ tickers in real-time with sub-second latency while maintaining complete per-user data isolation and personalization.*