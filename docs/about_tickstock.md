# About TickStock.ai

**TickStock.ai** is a high-performance platform for real-time and batch processing of market data, empowering traders and analysts with precise technical pattern detection and indicator calculations across multiple timeframes (intraday, hourly, daily, weekly, monthly). Built on a robust **three-tiered architecture**—Daily Batch Processing, Intraday Streaming, and Combo Hybrid Intelligence—TickStock processes over 4,000 stock symbols with sub-millisecond efficiency, leveraging Python's core libraries (pandas, NumPy, SciPy) for vectorized, rule-based algorithms. The platform comprises two core components: **TickStockAppV2** (consumer and UI management) and **TickStockPL** (producer and processing engine), integrated via a Redis pub-sub architecture for loose coupling and scalability.

## Key Capabilities

- **Real-Time Intraday Processing**: Ingests live data streams from providers like Polygon API, processing thousands of symbols per minute to detect short-term patterns (e.g., volume spikes, momentum shifts) and calculate indicators (e.g., RSI, relative volume) on 1-minute to hourly bars, enabling immediate identification of trading opportunities.
- **Daily Batch Analysis**: Performs end-of-day computations on stored universes, analyzing daily, weekly, and monthly OHLCV data to uncover longer-term patterns (e.g., head-and-shoulders, breakouts) and indicators (e.g., MACD crossovers, SMA trends). Results are stored in TimescaleDB for historical querying and backtesting.
- **Hybrid Combo Detection**: Correlates intraday signals with daily/weekly setups, enhancing confidence through multi-timeframe validation and fundamental integrations (e.g., EPS surprises, news sentiment >0.5 from Polygon APIs) to achieve <5% false positives (inspired by FMV Whitepaper metrics).
- **Modular Extensibility**: Utilizes a dynamic loading system (NO FALLBACK policy) configured via database tables (`pattern_definitions`, `indicator_definitions`) for seamless expansion of 11+ patterns and 15+ indicators. Supports optional scikit-learn enhancements for machine learning-refined detections.
- **Performance & Scalability**: Achieves >300 symbols/second throughput, >92% cache hit rates, and sub-millisecond pattern detection, integrated with Flask for web services, SQLAlchemy for DB operations, and Matplotlib for visualizations within a Windows-based VSCode/Python/PostgreSQL ecosystem.

## System Components

### TickStockAppV2: Consumer & UI Management
**Primary Purpose**: A lean user interface application that consumes events, triggers jobs, and delivers real-time insights to users.

**Core Responsibilities**:
- **User Experience**: Manages authentication, dashboards, and real-time WebSocket updates to browsers for seamless pattern and indicator visualization.
- **Event Consumer**: Subscribes to a single Redis channel to consume pattern detection events and backtest results from TickStockPL.
- **Job Triggering**: Submits backtest and analysis requests to TickStockPL via Redis job channels.
- **Result Display**: Visualizes TickStockPL-computed patterns, indicators, and backtest results in the UI.
- **Basic Data Ingestion**: Receives raw market data and forwards it to Redis for TickStockPL processing.
- **Read-Only Database Access**: Queries TimescaleDB for UI elements (e.g., symbol dropdowns) without accessing pattern/indicator data.

**Boundaries**:
- ❌ Does not perform pattern detection or heavy data processing.
- ❌ Does not manage database schemas or perform backtesting computations.

### TickStockPL: Producer & Processing Engine
**Primary Purpose**: A high-performance computational engine for pattern detection, indicator calculations, and backtesting.

**Core Responsibilities**:
- **Pattern Detection**: Executes 11+ pattern algorithms (e.g., Doji, Hammer) with sub-millisecond performance across multiple timeframes.
- **Data Processing**: Converts raw data into StandardOHLCV format and integrates multi-provider data (e.g., Polygon, Alpha Vantage).
- **Backtesting Engine**: Provides a comprehensive framework with institutional-grade metrics for validating patterns and indicators.
- **Database Management**: Maintains full read/write access to TimescaleDB, including schema creation and optimization for hypertables (e.g., `ohlcv_1min`, `daily_patterns`).
- **Event Publishing**: Publishes pattern detections and backtest results to Redis channels for consumption by TickStockAppV2.

**Boundaries**:
- ❌ Does not manage user interfaces, WebSocket broadcasting, or authentication/sessions.

## Integration: Redis Pub-Sub Architecture

**Communication Flow**:
```
[Market Data] → [TickStockAppV2: Raw Ingestion] → [Redis] → [TickStockPL: Processing]
                                                      ↓
[Browser UI] ← [TickStockAppV2: WebSocket] ← [Redis] ← [TickStockPL: Event Publishing]
```

**Key Redis Channels**:
- `tickstock.events.patterns`: Real-time pattern detection events (e.g., bullish engulfing on AAPL).
- `tickstock.events.backtesting.results`: Completed backtest results for UI display.
- `tickstock.jobs.backtest`: Job submissions from TickStockAppV2 to TickStockPL.
- `tickstock.data.raw`: Raw market data forwarded from TickStockAppV2 to TickStockPL.
- `tickstock:monitoring`: Real-time system performance metrics and alerts.

This Redis pub-sub architecture ensures loose coupling, enabling independent development, scaling, and deployment of TickStockAppV2 and TickStockPL while maintaining <100ms event latency.

## Processing Hierarchy
The following Mermaid graph illustrates TickStock’s three-tiered processing flow:

```mermaid
graph TD
    A[Start: Market Data Ingest] --> B[Query Data Sources]
    B --> C{Timeframe?}
    C -->|Intraday| D[Tier 2: Streaming Engine]
    D --> E[Calculate Intraday Indicators (e.g., RSI on ohlcv_1min)]
    E --> F[Detect Patterns (e.g., Volume Spike)]
    C -->|Daily/Weekly/Monthly| G[Tier 1: Batch Engine]
    G --> H[Calculate Indicators (e.g., MACD on ohlcv_daily)]
    H --> I[Detect Patterns (e.g., Bullish Engulfing)]
    F --> J[Tier 3: Combo Hybrid]
    I --> J
    J --> K[Correlate Signals + Fundamentals (Polygon API)]
    K --> L[Store Results (e.g., daily_patterns, intraday_indicators)]
    L --> M[Publish Events via Redis (tickstock:monitoring)]
    M --> N[End: Alert/Visualize Outputs]
```

## Next Steps
- **Validation**: Test performance claims (e.g., >300 symbols/second, sub-millisecond detection) using Polygon API data for symbols like AAPL across daily and intraday timeframes.
- **Enhancements**: Prioritize fundamental correlations (e.g., EPS surprise >0 or news sentiment >0.5) to refine pattern confidence or expand to new patterns (e.g., Doji) with multi-timeframe logic.
- **Visualization**: Develop Matplotlib-based visualizations for detected patterns and indicators, stored in `daily_patterns` or `intraday_indicators`.