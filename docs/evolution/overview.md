# TickStock.ai Overview

## Vision
TickStock.ai is a comprehensive platform for algorithmic stock analysis, empowering users to detect patterns in OHLCV data for informed trading decisions. The goal is to build scalable, modular libraries for pattern detection, blending historical and real-time data, while keeping it bootstrap-friendly (lightweight deps, no heavy funding needs). We focus on extensibility—starting with core patterns (candlesticks, charts, trends, breakouts) and evolving to custom/ML signals. Ultimately, provide actionable signals via events to drive trades, alerts, and visualizations.

## High-Level Processing Flow
1. **Data Ingestion**: Pull OHLCV from APIs (e.g., yfinance free tier), databases, or real-time feeds (WebSockets).
2. **Preprocessing**: Clean, resample (e.g., to 1min/daily), blend historical + live data.
3. **Pattern Scanning**: Analyze for detections using modular classes; publish events on finds.
4. **Event Handling**: Signals flagged to the main app for user actions (e.g., UI updates, trades).
5. **Output**: Visuals, backtests, or automated responses.

## Major Components
- **TickStock.ai**: Static front end (e.g., HTML/JS site) for user-facing info, demos, and access points.
- **TickStockApp**: Core application servicing users—handles subscriptions, UI, portfolio, and consumes events (e.g., via Redis pub-sub) for real-time alerts/trades.
- **TickStockPL** (Pattern Library Services): New microservices for pattern detection—includes scanner, data loaders, and event publishing. Runs separately for modularity/scalability, feeding signals to TickStockApp.

This setup ensures decoupling: TickStockPL processes data independently, while TickStockApp subscribes to its outputs.