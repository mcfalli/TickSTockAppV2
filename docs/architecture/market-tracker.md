# MarketMetrics Module Documentation

## market_analytics/market_metrics.py

### Purpose
Centralized market metrics tracking module that consolidates all market activity measurements, session counts, tick-based activity calculations, and status metrics into a single, cohesive service.

### Current Use
The MarketMetrics class serves as the primary source of truth for:
- Real-time market activity levels based on tick flow
- Session high/low event counts with automatic reset handling
- Per-ticker momentum tracking within configurable time windows
- Market session state management (PRE, REGULAR, AFTER, CLOSED)
- WebSocket emission data preparation for frontend activity displays
- Simplified status updates and heartbeat metrics (Added in S37)

### Key Responsibilities

#### Tick Tracking
- Records every market tick for activity analysis
- Maintains rolling windows (10s, 30s, 60s, 300s) using efficient deque structures
- Calculates ticks per minute for activity level determination

#### Session Count Management
- Tracks total high/low events for the current trading session
- Provides cached totals with percentage calculations for UI visualization
- Handles session resets during market transitions (PRE→REGULAR, CLOSED→PRE)

#### Activity Level Calculation
- Determines market activity: Very Low, Low, Medium, High, Very High, Extreme
- Special handling for "Opening Bell" (first 15 min) and "Closing Bell" (last 15 min)
- Based on actual market tick rate rather than processed events

#### Per-Ticker Momentum
- Tracks high/low events per ticker within momentum windows
- Rate-limited to prevent spam (max 10 updates/second per ticker)
- Used for identifying rapidly moving stocks

#### Status Metrics Provider (Added in S37)
The MarketMetrics module now serves as the centralized provider for simplified WebSocket status updates and heartbeats:

**get_status_metrics(api_health)**
- Generates lean status update payloads (6 fields only)
- Determines "Test" vs "Production" provider based on config flags
- Calculates average API response time
- Uses internal `determine_market_status()` for accurate market state
- Returns standardized format for heartbeat/status emissions

Status Payload Format:
```json
{
  "status": "healthy",
  "connected": true,
  "provider": "Test|Production",
  "market_status": "PRE|REGULAR|AFTER|CLOSED",
  "timestamp": "ISO-8601 timestamp",
  "avg_response": 1.5
}
Integration Points

Called by event_processor.py on every tick via record_tick()
High/low counts updated by event_processor.py via update_high_low_tracking()
Activity metrics retrieved by core_service.py for WebSocket emissions
Session resets triggered by core_service.py during market transitions
Status metrics retrieved by websocket_publisher.py via get_status_metrics()
Provides unified provider determination logic (USE_SYNTHETIC_DATA → "Test", USE_POLYGON_API → "Production")
Eliminates duplicate provider logic across the codebase

Configuration

MOMENTUM_WINDOW_SECONDS: Time window for per-ticker momentum (default: 10)
DEBUG_TICK_TRACKING: Enable tick recording debug logs
DEBUG_COUNT_TRACKING: Enable count update debug logs
USE_SYNTHETIC_DATA: When true, provider shows as "Test"
USE_POLYGON_API: When true, provider shows as "Production"

Activity Thresholds

Very Low: < 30 ticks/minute
Low: 30-60 ticks/minute
Medium: 60-120 ticks/minute
High: 120-240 ticks/minute
Very High: 240-480 ticks/minute
Extreme: > 480 ticks/minute

Example Activity Output
json{
  "activity": {
    "total_highs": 46,
    "total_lows": 53,
    "activity_level": "Extreme",
    "activity_ratio": {
      "calculation_method": "ticks_per_minute",
      "current_rate": 678,
      "threshold_low": 30,
      "threshold_medium": 60,
      "threshold_high": 120,
      "threshold_very_high": 240
    },
    "ticks_10sec": 112,
    "ticks_30sec": 336,
    "ticks_60sec": 678,
    "ticks_300sec": 1014
  }
}
Metrics Validation
Count Validation

High/Low Balance: Slight bias either way is normal market behavior
Tick Window Progression: Each window should show appropriate accumulation

30s window ≈ 3x the 10s window
60s window ≈ 2x the 30s window
300s window < 5x the 60s window (due to aging)



Activity Level

Tick rate determines activity level based on thresholds
Special overrides for Opening Bell and Closing Bell periods

Tick Rate Analysis

Event-to-tick ratio typically 10-20% (not all ticks generate high/low events)
High tick rates (>10/second) indicate very active market periods

Migration Note
This module replaces the legacy metrics_tracker.py, providing cleaner separation of concerns and more accurate market activity measurements based on actual tick flow rather than processed events.
Version History

v1.0: Initial refactor from metrics_tracker.py
v1.1: Added get_status_metrics() for centralized status updates (Sprint S37)