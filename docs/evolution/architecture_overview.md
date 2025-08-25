# TickStock.ai Architecture Overview

## TickStock.ai (Static Front End)
- **Purpose**: Public-facing entry point for marketing, docs, and basic demos.
- **Tech Stack**: HTML/CSS/JS (e.g., hosted on GitHub Pages or Vercel free tier).
- **Operations**: Static serving—no backend. Links to TickStockApp for login/use.
- **Primary Functionality**: Overview pages, pattern library docs, sign-up forms.

## TickStockApp (User-Servicing Application)
- **Purpose**: Handles user interactions, portfolio management, and event consumption for signals.
- **Tech Stack**: Python (Flask/Django for backend), optional JS frontend; integrates with DB for user data.
- **Operations**: Runs as a web app; subscribes to events from TickStockPL (e.g., via Redis). Processes signals for alerts, trades, or UI updates.
- **Primary Functionality**: User auth, dashboard with pattern visuals, event logging (e.g., insert detections to app DB), backtesting interface.

## TickStockPL (Pattern Library Services)
- **Purpose**: Dedicated to data analysis, pattern detection, and event generation—keeps heavy compute separate.
- **Tech Stack**: Python (pandas, numpy, scipy for core; Redis for pub-sub); modular package structure.
- **Operations**: Batch mode for historical scans (DB pulls); real-time mode via incremental updates (WebSockets/feeds). Publishes events on detections.
- **Primary Functionality**: Data loading/preprocessing, pattern scanning (batch/real-time), event publishing to TickStockApp. Extensible for new patterns.

Overall: Event-driven (pub-sub) for loose coupling; DB-centric for persistence. Scales via microservices (e.g., Docker later).

### Architecture Diagram (Text-Based)
[External Data Sources: Polygon APIs/WebSockets, yfinance]
|
v
[TickStockApp: Ingestion (WS Handler) --> Redis (Data Channel: e.g., "tickstock_data")]
|
v
[TickStockPL: DataBlender (Blend Historical DB + Live) --> PatternScanner (Detect via BasePattern) --> EventPublisher]
|
v
[Redis (Patterns Channel: e.g., "tickstock_patterns")]
|
v
[TickStockApp: Event Subscriber --> Processing (Alerts, Trades, UI Updates, DB Logging)]
|
v
[User Outputs: Dashboard Visuals, Backtests]
[Shared DB: PostgreSQL/TimescaleDB for symbols, ohlcv_*, events persistence]

This diagram illustrates the loose coupling: TickStockPL publishes events to Redis independently, while TickStockApp subscribes for consumption—perfect for our modular Python setup!