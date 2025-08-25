# TickStock.ai Overview

## Vision
TickStock.ai is a comprehensive platform for algorithmic stock analysis, empowering users to detect patterns in OHLCV data for informed trading decisions. The goal is to build scalable, modular libraries for pattern detection, blending historical and real-time data, while keeping it bootstrap-friendly (lightweight deps like pandas, numpy, scipy, and Redis—no heavy funding needs). We focus on extensibility—starting with core patterns (candlesticks, charts, trends, breakouts) and evolving to custom/ML signals via composable conditions and multi-timeframe support. Ultimately, provide actionable signals via events to drive trades, alerts, visualizations, and backtests, all while ensuring loose coupling for independent scaling.

## High-Level Processing Flow
1. **Data Ingestion**: Pull OHLCV from APIs (e.g., Polygon or yfinance free tier), databases, or real-time feeds (WebSockets via TickStockApp).
2. **Preprocessing**: Clean, resample (e.g., to 1min/daily), and blend historical + live data using DataBlender for unified DataFrames.
3. **Pattern Scanning**: Analyze blended data in TickStockPL using modular classes (e.g., BasePattern, PatternScanner); detect patterns and publish events on finds via Redis pub-sub for loose coupling—TickStockPL feeds these events directly to TickStockApp without tight dependencies.
4. **Event Handling**: TickStockApp subscribes to Redis channels, consuming signals for user actions (e.g., UI alerts, automated trades, or DB logging).
5. **Output**: Generate visuals, backtest results, or responses in TickStockApp, with events persisted for auditing.

## Major Components
- **TickStock.ai**: Static front end (e.g., HTML/JS site) for user-facing info, demos, and access points.
- **TickStockApp**: Core application servicing users—handles subscriptions, UI, portfolio, and consumes events (e.g., via Redis pub-sub) for real-time alerts/trades.
- **TickStockPL** (Pattern Library Services): New microservices for pattern detection—includes scanner, data loaders, and event publishing. Runs separately for modularity/scalability, feeding signals to TickStockApp via Redis pub-sub.

This setup ensures decoupling: TickStockPL processes data independently, publishing events to Redis for TickStockApp to subscribe and act on, enabling resilient, scalable operations.