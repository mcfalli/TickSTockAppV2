# TickStock Data, Process, Key Components Documentation

## Purpose
This document describes the primary aspects of TickStock data processing and display, outlining both primary data usage/display and user-selected data usage/display.

## TickStock Core Universe ("Core Universe")

### Overview
A superset of all stocks we subscribe to and receive from our data provider. This is defined in `cache_control.py` and the `cache_entries` table.

## Supporting Documentation
### data-flow-pipeline.md
### JSON.md

### Data Flow
When the data provider raises events for any of these stocks, we receive that stock's data via subscription to their WebSockets interface.

**Note**: For testing and development, we simulate this with synthetic data manufacturing, which is seamless to our processing. A standard data interface abstracts the core logic from knowing the data source. Synthetic data can be more random and volatile.

### Processing Pipeline
The Core Universe drives data processing through these common entry points and processing points:

event_processor.py._initialize_real_time_adapter
    ↓
event_processor.py.handle_websocket_tick
    ↓
event_processor.py.handle_tick
    ↓
tick_processor.py.process_tick 
    ↓
event_processor.py._process_tick_event
    ├── Universe Management
    ├── Queue Size Priority
    └── event_detector.py.detect_events
        ├── High/Low Detection
        ├── Trend Detection
        └── Surge Detection

## Data Flow Stages (see data-flow-pipeline.md)

### Stage 1: Data Ingestion
Data Source → MarketDataService.handle_websocket_tick() → CoreService.handle_websocket_tick() → EventProcessor.handle_tick()
Real-time tick data arrives via WebSocket and is validated by the CoreService before delegation to EventProcessor. The CoreService tracks API health and generates IDs for debug logging.

### Stage 2: Event Processing
EventProcessor → TickProcessor (validation) → EventDetector (detection) → State Updates
Validated ticks undergo event detection for highs, lows, trends, and surges using configurable thresholds. The EventProcessor manages dual universe processing for efficient filtering.

### Stage 3: Queue Management
PriorityManager → WorkerPoolManager → Worker Threads → Event Processing
Events are prioritized (P0-P4) and distributed across worker threads for parallel processing. Dynamic scaling adjusts worker count based on queue depth.

### Stage 5: User Distribution
DataPublisher → WebSocketPublisher → Per-User Filtering → WebSocket Emission → Client Delivery
Data is filtered based on user preferences (universe and filters) and delivered via authenticated WebSocket connections.


## Core Universe
### Core Universe Analytics
The Core Universe data is processed for displaying analytics (aggregated data and text) to visually and textually describe the overall market view:

#### Components
- **Visual Elements**: Gauge and vertical pressure indicator
- **Text Elements**: Activity text and percentages demonstrating overall market activity and direction (buying or selling pressure)

#### Data
- **Filtering**: Can be filtered by system limitations (rate limiting or queue overload) at the `handle_websocket_tick` level
- **Result Structure**: `core_universe_analytics` containing:
  - `gauge_analytics`
  - `vertical_analytics`
  - `current_state` (and sub-elements noted in JSON.md)
- **Storage**: This is the only data currently stored in the database by design

#### Key Tests
Test that values are calculated accurately and portray high-quality information based on stocks processed within the calculation time period.


## User Universe

### Definition
The stocks that users have selected to be processed, calculated, and rendered. The User Universe can be all or some of the Core Universe, selected through the "universe filter" where users can select all or some of four individual universes.

### User Universe Analytics

#### Components
- **Visual Elements**: Gauge and vertical pressure indicator
- **Text Elements**: Activity text and percentages demonstrating the user universe's activity and direction (buying or selling pressure)

#### Data
- **Filtering**: No additional filtering applied
- **Result Structure**: `user_universe_analytics` containing:
  - `gauge_analytics`
  - `vertical_analytics`
  - `current_state` (and sub-elements)

#### Key Tests
Test that values are calculated accurately and portray high-quality information based on stocks processed from the user's universe within the calculation time period.

#### 1. New Lows and New Highs Grids

**Display**: Two grids (one for highs, one for lows) showing:
- Count
- Ticker
- Change %
- Distance from VWAP %
- Price
- Volume
- Time
- Label

**Data Structure**: Array of `highs` elements with child elements:
- `ticker`
- `price`
- `time`
- `market_status`
- `percent_change`
- `vwap`
- `volume`
- `vwap_distance`
- `session_high_count`
- `session_low_count`
- `session_total_events`

**Key Tests**:
- Validate high/low detection for the session
- Verify calculations for: `percent_change`, `vwap_distance`, `session_high_count`, `session_low_count`, `session_total_events`

#### 2. New Lows and New Highs Percentage Bar

**Display**: Dynamic percentage bar representing data from high/low grids, showing overall percentage of highs vs lows.

**Data Structure** (to be confirmed): Located in `counts` element with:
- `highs`
- `lows`
- `total_highs`
- `total_lows`
- `session_low_count`
- `session_high_count`
- `session_total_events`

**Key Test**: Confirm calculated values accurately represent percent high and low relative to the user universe.

#### 3. Uptrend and Downtrend Stocks Grids

**Display**: Two grids showing:
- Ticker
- Change %
- Distance from VWAP %
- Price
- Strength
- Updated

**Data Structure**: Array of `trending` with `up` or `down` children containing:
- `ticker`
- `price`
- `trend_strength`
- `trend_score`
- `vwap_position`
- `vwap_divergence`
- `last_trend_update`
- `trend_age`

**Key Tests**:
- Verify trend event triggers (uptrend/downtrend criteria)
- Validate calculations for: `trend_strength`, `trend_score`, `vwap_position`, `vwap_divergence`, `last_trend_update`, `trend_age`

#### 4. Surging Up and Down Stocks Grids

**Display**: Two grids showing:
- Ticker
- Change %
- Price
- Magnitude
- Score
- Trigger
- Updated

**Data Structure**: Array of `surging` stocks with elements:
- `ticker`
- `price`
- `direction`
- `magnitude`
- `score`
- `strength`
- `trigger_type`
- `description`
- `time`
- `volume_multiplier`
- `surge_age`

**Key Tests**:
- Verify surge event triggers (up/down criteria)
- Validate calculations for: `direction`, `magnitude`, `score`, `strength`, `trigger_type`, `description`, `volume_multiplier`, `surge_age`


## The user may also apply filters (“User Filters”) to the User Universe data that filters the data after event processing to limit data delivered to UI. 
**Key Tests: To Do**

