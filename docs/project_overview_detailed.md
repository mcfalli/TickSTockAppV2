# TickStock.ai Overview (Version 3.0)

*High-Performance Multi-Channel Real-Time Market Data Processing System*

**Version**: 3.0  
**Date**: 2025-08-23  
**Coverage**: Sprints 1-11 (Pre-Production Redesign)  
**Status**: Pre-Production, Third Versioning Effort

## Complete System Data Flow (Version 3.0)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            DATA SOURCE LAYER (TickStockApp)                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│  [Polygon WebSocket]    [Polygon REST]    [FMV Provider]    [Synthetic Data]   │
│         │                    │               │                  │               │
│         ▼                    ▼               ▼                  ▼               │
│  RealTimeAdapter      OHLCVAdapter      FMVAdapter      SyntheticAdapter       │
│         │                    │               │                  │               │
│         └────────────────────┼───────────────┼──────────────────┘               │
│                              │               │                                  │
└──────────────────────────────┼───────────────┼──────────────────────────────────┘
                               │               │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        CHANNEL ROUTING LAYER (TickStockApp)                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                         MarketDataService                                      │
│                               │                                                 │
│                               ▼                                                 │
│                     📋 DataChannelRouter                                       │
│                     ┌─────────────────────┐                                    │
│                     │   Data Type ID      │                                    │
│                     │   Health Monitoring │                                    │
│                     │   Load Balancing    │                                    │
│                     │   Circuit Breakers  │                                    │
│                     └─────────────────────┘                                    │
│                               │                                                 │
│               ┌───────────────┼───────────────┐                                │
│               │               │               │                                │
└───────────────┼───────────────┼───────────────┼────────────────────────────────┘
                │               │               │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       PROCESSING CHANNELS (TickStockApp)                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│         ▼               ▼               ▼                                       │
│   🎯 TickChannel   📊 OHLCVChannel   💰 FMVChannel                            │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                           │
│   │ Tick Data   │  │ OHLCV Data  │  │ FMV Data    │                           │
│   │ Processing  │  │ Processing  │  │ Processing  │                           │
│   │ Queue: 1000 │  │ Queue: 8000 │  │ Queue: 500  │                           │
│   │ Timeout:25ms│  │ Timeout:50ms│  │ Timeout:50ms│                           │
│   └─────────────┘  └─────────────┘  └─────────────┘                           │
│         │               │               │                                       │
│         └───────────────┼───────────────┼──────────────────┐                    │
│                         │               │                  │                    │
└─────────────────────────┴───────────────┴──────────────────┘                    │
                                                         │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    DB STORAGE LAYER (TickStockPL)                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                         ▼                                                       │
│                  📁 Database (PostgreSQL/TimescaleDB)                          │
│             ┌─────────────────────────┐                                        │
│             │ Tables: symbols, ticks  │                                        │
│             │ ohlcv_1min, ohlcv_daily│                                        │
│             │ events (optional)       │                                        │
│             │ Nightly Aggregations    │                                        │
│             └─────────────────────────┘                                        │
│                         │                                                       │
└─────────────────────────┼───────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    PATTERN PROCESSING LAYER (TickStockPL)                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                         ▼                                                       │
│                    📊 DataBlender                                              │
│             ┌─────────────────────────┐                                        │
│             │ Blend Historical + Live │                                        │
│             │ Resample Timeframes     │                                        │
│             │ Data Validation         │                                        │
│             └─────────────────────────┘                                        │
│                         │                                                       │
│                         ▼                                                       │
│                    🔍 PatternScanner                                           │
│             ┌─────────────────────────┐                                        │
│             │ Detect Patterns         │                                        │
│             │ (Doji, Day1Breakout,    │                                        │
│             │  HeadAndShoulders, etc.)│                                        │
│             │ Batch/Real-Time Modes   │                                        │
│             └─────────────────────────┘                                        │
│                         │                                                       │
└─────────────────────────┼───────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    EVENT DISTRIBUTION LAYER (TickStockPL)                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                         ▼                                                       │
│                    📤 EventPublisher                                           │
│             ┌─────────────────────────┐                                        │
│             │ Redis Pub-Sub           │                                        │
│             │ Event Formatting        │                                        │
│             │ (Pattern, Symbol,       │                                        │
│             │  Timestamp, Timeframe) │                                        │
│             └─────────────────────────┘                                        │
│                         │                                                       │
└─────────────────────────┼───────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       CLIENT LAYER (TickStockApp)                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                         ▼                                                       │
│                    🌐 EventSubscriber                                          │
│             ┌─────────────────────────┐                                        │
│             │ Subscribe to Events     │                                        │
│             │ Log to DB (events)      │                                        │
│             │ Update UI (Signals)     │                                        │
│             │ Trigger Trades          │                                        │
│             └─────────────────────────┘                                        │
│                         │                                                       │
│    [WebSocket Clients] [Mobile Apps] [Web Dashboard] [API Consumers]          │
│           │                │              │               │                     │
│           └────────────────┼──────────────┼───────────────┘                     │
│                            │              │                                     │
│                      [User Experience Layer]                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Notes on Data Flow
- **Data Source Layer (TickStockApp)**: Leverages existing Polygon WebSockets/REST for per-minute OHLCV, ticks, and FMV data. Adapters format data for routing (websockets_integration.md, get_historical_data.md).
- **Channel Routing Layer (TickStockApp)**: `DataChannelRouter` directs data to appropriate channels with health-based load balancing, unchanged from v2.0.
- **Processing Channels (TickStockApp)**: Validates and preprocesses data (e.g., volume filters, latency checks), feeding to DB and TickStockPL.
- **DB Storage Layer (TickStockPL)**: Stores live data in `ticks`/`ohlcv_1min`; nightly jobs aggregate to `ohlcv_daily` (database_architecture.md).
- **Pattern Processing Layer (TickStockPL)**: `DataBlender` merges historical (DB) and live (WebSockets) data, resamples for timeframes, and feeds `PatternScanner` for pattern detection (patterns.md).
- **Event Distribution Layer (TickStockPL)**: `EventPublisher` sends pattern events (e.g., {"pattern": "Day1Breakout", "symbol": "AAPL"}) via Redis pub-sub (pattern_library_architecture.md).
- **Client Layer (TickStockApp)**: `EventSubscriber` consumes events, logs to `events` table, updates UI with actionable signals, or triggers trades.

This flow replaces v2.0’s complex event processing, priority, and distribution layers with a streamlined, pattern-focused pipeline, aligning with Sprint 4 cleanup (sprint_plan.md).