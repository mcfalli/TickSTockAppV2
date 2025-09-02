#### ui_architecture_overview.md

# TickStock.ai UI Architecture Overview

**Document**: Overview of Front-End in Ecosystem  
**Last Updated**: 2025-08-30  
**Status**: Sprint 12 Reference  
**Related**: architecture_overview.md, project-overview.md.

---

## Overview
The UI extends our decoupled architecture: TickStock.ai (static docs), TickStockApp (dynamic consumer for index.html). Focus: Event-driven, modular for scalability.

## Component Diagram (Text-Based)
```
[User Browser: Index.html Tabs/Grids] ← WebSockets → [TickStockApp: Event Consumer]
                                                ↓
[Redis Pub-Sub: tickstock.events.patterns] ← Events → [TickStockPL: PatternScanner/DataBlender]
                                                ↓
[TimescaleDB: ohlcv_tables, user_prefs] ← Historical Loads (0.1)
```

## Principles
- **Event-Driven**: WS updates from Redis for alerts/charts (sub-200ms).
- **Modular**: Tabs → Grids/pop-outs for customization (1000+ symbols).
- **Decoupling**: UI consumes events; no direct calls to TickStockPL.
- **Scalability**: Lightweight JS; horizontal scaling via multiple TickStockApp instances.

## Integration Points
- Historical: Data from 0.1 feeds dashboards/charts.
- Real-Time: Blending for future sprints (14+).
- Extensibility: Add tabs for new features (e.g., backtesting).

## Future-Proofing
Migrate to frameworks if needed; maintain <1s loads.
