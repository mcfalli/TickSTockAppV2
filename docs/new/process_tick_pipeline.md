# TickStock Process Pipeline Documentation
**Updated:** 2025-01-20 - Sprint 103 Architecture Review & Analysis
**Status:** ENHANCED - Complete end-to-end flow documentation

## Executive Summary

This document provides comprehensive documentation of TickStock's market data processing pipeline, from data ingestion through event detection to WebSocket client delivery. The system processes 4,000+ tickers in real-time with sub-millisecond event detection using a linear pipeline architecture.

## Current Pipeline Architecture (Linear Processing)

### Complete Data Flow Overview

**Data Source → Event Detection → Priority Queue → Data Publisher → WebSocket Publisher → Users**

### 1. Data Source Layer

**File:** `src/infrastructure/data_sources/adapters/realtime_adapter.py`
- **Classes:** RealTimeDataAdapter, SyntheticDataAdapter
- **Method:** `connect()` → establishes WebSocket connection or starts synthetic data generation
- **Method:** `_simulate_events()` (synthetic) → generates TickData objects
- **Callback:** Calls `tick_callback` (which is `handle_websocket_tick`)

**Data Format:** TickData objects with price, volume, VWAP, timestamp

### 2. Core Service Layer

**File:** `src/core/services/market_data_service.py`
- **Class:** MarketDataService
- **Method:** `handle_websocket_tick(tick_data: TickData)` ← **SINGLE ENTRY POINT BOTTLENECK**
  - Validates tick data
  - Updates market session if needed
  - Delegates to EventProcessor

**Critical Issue:** All data types (Tick, OHLCV, FMV) funnel through this single method

### 3. Event Processing Pipeline

**File:** `src/processing/pipeline/event_processor.py`
- **Class:** EventProcessor
- **Method:** `handle_tick(tick_data: TickData)` ← Called from MarketDataService
  - Validates TickData
  - Calls TickProcessor for validation/enrichment
  - Calls `_process_tick_event()` for main processing

**Method:** `_process_tick_event(queue_data: TickData)`
- Checks if ticker is in core universe
- Gets/creates StockData for ticker
- Calls EventDetector for event detection
- Routes detected events to priority manager

### 4. Event Detection Coordinator

**File:** `src/processing/pipeline/event_detector.py`
- **Class:** EventDetector
- **Method:** `detect_events(ticker, tick_data, stock_details)` ← Called from EventProcessor
  - Coordinates all event detection types
  - Calls individual detector methods:
    - `_detect_highlow_events()`
    - `_detect_trend_events()`
    - `_detect_surge_events()`

### 5. Individual Event Detectors

**File:** `src/processing/detectors/highlow_detector.py`
- **Class:** HighLowDetector
- **Method:** `detect_highlow(tick_data: TickData, stock_data: StockData)` ← Final detection logic
  - Performs actual high/low event detection
  - Creates HighLowEvent objects
  - Returns detection results

**Similar patterns for:** TrendDetector, SurgeDetector

### 6. Event Queuing & Priority Management

**Flow:** EventProcessor → `priority_manager.add_event(typed_event)`

**Event Transformation:** 
- **Input:** Typed events (HighLowEvent, TrendEvent, SurgeEvent)
- **Processing:** Events queued in priority_manager
- **Worker Pool:** Converts typed events to transport dicts
- **Output:** Dicts placed in display_queue

### 7. Data Publisher (Pull Model - Sprint 29)

**File:** `src/presentation/websocket/data_publisher.py`
- **Class:** DataPublisher
- **Method:** `publish_to_users()` ← Collection only, no direct emission
  - Calls `_collect_display_events_from_queue()`
  - Buffers events with overflow protection
  - Supports multi-frequency event types (Sprint 101)

**Key Features:**
- **Pull Model:** WebSocketPublisher controls when events are emitted
- **Multi-frequency buffers:** per_second, per_minute, fmv event types
- **Buffer Management:** 1000 event max per type with overflow protection

### 8. WebSocket Publisher (Pull Model - Sprint 29)

**File:** `src/presentation/websocket/publisher.py`
- **Class:** WebSocketPublisher
- **Method:** `run_emission_cycle()` ← Controls emission timing
  - Calls `data_publisher.get_buffered_events()` 
  - Applies per-user filtering
  - Emits to users via `websocket_mgr.emit_to_user()`

**Key Features:**
- **Timer-based emission:** Configurable intervals (default 1.0s)
- **Per-user filtering:** Based on universe subscriptions
- **Multi-frequency support:** Handles per-second, per-minute, FMV data

## Event Format Structures and Transport

### Event Type Boundary

**Critical Architecture Rule:**
- **Detection → Worker:** Typed Events (HighLowEvent, TrendEvent, SurgeEvent)
- **Worker → Display Queue:** Dict conversion via `to_transport_dict()`
- **Display Queue → Frontend:** Dict only
- **Never mix typed events and dicts after Worker conversion**

### BaseEvent Structure

**File:** `src/core/domain/events/base.py`

**Common Fields:**
```python
ticker: str           # Stock symbol
type: str            # Event type: 'high', 'low', 'trend', 'surge'
price: float         # Event price
time: float          # Event timestamp
event_id: str        # Unique event identifier
direction: str       # '↑', '↓', '→'
count: int          # Event count
percent_change: float # Price change percentage
vwap: float         # Volume weighted average price
volume: float       # Trade volume
```

**Transport Method:**
```python
def to_transport_dict(self) -> Dict[str, Any]:
    # Converts typed event to WebSocket-safe dictionary
```

### StockData Structure

**File:** `src/presentation/converters/transport_models.py`

**Key Fields:**
```python
ticker: str                    # Stock symbol
last_price: float             # Current price
highs: List[HighLowEvent]     # Stored high events
lows: List[HighLowEvent]      # Stored low events
event_counts: EventCounts     # Event statistics
trend_direction: str          # Current trend state
surge_active: bool           # Current surge state
```

**Transport Method:**
```python
def to_transport_dict(self) -> Dict[str, Any]:
    # Full stock data for WebSocket emission
```

## Configuration Management Patterns

### Configuration Architecture

**File:** `src/core/services/config_manager.py`
- **Class:** ConfigManager
- **Pattern:** Centralized configuration with environment variable override
- **Validation:** Type checking and constraint validation
- **Multi-frequency:** JSON configuration files for complex setups

### Configuration Sources (Priority Order)
1. **Environment Variables** (highest priority)
2. **JSON Configuration Files** 
   - `config/websocket_subscriptions.json`
   - `config/processing_config.json`
3. **Default Constants** (in ConfigManager.DEFAULTS)

### Key Configuration Patterns
- **Detection Parameters:** Market period-specific thresholds
- **Performance Settings:** Buffer sizes, timeouts, intervals  
- **Multi-frequency:** Channel enablement flags
- **Environment Interpolation:** `${VAR:default}` syntax in JSON

## Multi-Channel Architecture Requirements

Based on analysis of the current linear system, the following requirements define the path to multi-channel processing:

### Channel Abstraction Requirements

**Interface Definition:**
```python
class ProcessingChannel(ABC):
    def get_channel_type(self) -> str          # 'tick', 'ohlcv', 'fmv'
    def validate_data(self, data: Any) -> bool  # Input validation
    def process_data(self, data: Any) -> List[BaseEvent]  # Main processing
    def get_configuration(self) -> Dict[str, Any]  # Channel config
```

### Data Routing Requirements

**Router Interface:**
```python
class DataRouter:
    def route_data(self, data: Any, data_type: str) -> ProcessingChannel
    def get_active_channels(self) -> List[ProcessingChannel]
```

**Routing Strategy:**
- WebSocket tick data → **Tick Channel**
- Bar/aggregate data → **OHLCV Channel**
- FMV calculations → **FMV Channel**

### Performance Requirements

**Throughput Targets:**
- **Tick Channel:** Maintain current 4000+ tickers
- **OHLCV Channel:** 1000+ bars per minute
- **FMV Channel:** 500+ valuations per minute

**Latency Targets:**
- **Tick processing:** <100ms (current maintained)
- **OHLCV processing:** <500ms per bar
- **FMV processing:** <200ms per calculation

## Architecture Gaps and Issues

### Current Issues Identified

1. **Single Entry Point Bottleneck**
   - All data funnels through `MarketDataService.handle_websocket_tick()`
   - No differentiation between data types
   - **Priority:** HIGH

2. **Tight Coupling**
   - MarketDataService directly coupled to EventProcessor
   - Configuration scattered across multiple files
   - **Priority:** MEDIUM

3. **Limited Data Type Support**
   - Only tick data processing currently implemented
   - No native support for OHLCV or FMV data types
   - **Priority:** HIGH

4. **Configuration Complexity**
   - Multiple inheritance patterns in ConfigManager
   - Environment variable explosion (365+ config values)
   - **Priority:** LOW

### Migration Strategy (Sprints 104-108)

**Phase 1 - Channel Infrastructure (Sprint 104)**
- Implement ProcessingChannel interface
- Create DataRouter with tick channel only
- Modify MarketDataService to use router
- **Risk:** Maintain current performance

**Phase 2 - Multi-Channel Implementation (Sprint 105-106)** 
- Add OHLCV and FMV channels
- Implement channel-specific configurations
- Enhanced priority management
- **Risk:** Channel interaction complexity

**Phase 3 - Integration & Optimization (Sprint 107-108)**
- Performance tuning per channel
- Channel-specific monitoring
- Advanced routing strategies
- **Risk:** Performance regression testing

## File Hierarchy Reference

**Complete Processing Pipeline Files:**

1. `src/infrastructure/data_sources/adapters/realtime_adapter.py`
2. `src/core/services/market_data_service.py` ← **ENTRY POINT**
3. `src/processing/pipeline/event_processor.py`
4. `src/processing/pipeline/event_detector.py`
5. `src/processing/detectors/highlow_detector.py` (+ trend, surge)
6. `src/processing/queues/priority_manager.py` ← **EVENT QUEUING**
7. `src/presentation/websocket/data_publisher.py` ← **COLLECTION**
8. `src/presentation/websocket/publisher.py` ← **EMISSION**

## Method Call Chain Summary

**Complete Flow:**
1. `RealTimeDataAdapter.connect()` / `SyntheticDataAdapter._simulate_events()`
2. `MarketDataService.handle_websocket_tick()` ← **BOTTLENECK**
3. `EventProcessor.handle_tick()`
4. `EventProcessor._process_tick_event()`
5. `EventDetector.detect_events()`
6. `Individual detectors` (HighLow, Trend, Surge)
7. `priority_manager.add_event()` ← **EVENT QUEUING**
8. `Worker pool conversion` (typed events → dicts)
9. `DataPublisher._collect_display_events_from_queue()` ← **COLLECTION**
10. `WebSocketPublisher.run_emission_cycle()` ← **EMISSION CONTROL**
11. `websocket_mgr.emit_to_user()` ← **USER DELIVERY**

## Key Architectural Strengths to Preserve

1. **Pull Model Event Distribution** (Sprint 29)
2. **Typed Event System** (Phase 4) 
3. **Multi-frequency Buffer Support** (Sprint 101)
4. **Per-user Filtering** (WebSocket Publisher)
5. **Universe Management** (Core/User universes)
6. **Priority Queue System** (Event ordering)

## Next Steps for Multi-Channel Implementation

1. **Identify Refactoring Opportunities** → Priority: `MarketDataService.handle_websocket_tick()`
2. **Design Channel Interfaces** → Based on ProcessingChannel requirements
3. **Implement Data Router** → Route by data type to appropriate channel
4. **Create Migration Plan** → Preserve existing functionality during transition
5. **Performance Testing** → Validate no regression in current tick processing

---
*This documentation provides the foundation for Sprints 104-108 multi-channel architecture implementation.*