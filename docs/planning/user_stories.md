# TickStock.ai User Stories

These stories define key user needs for our pattern detection libraries, prioritized for bootstrap-friendly implementation. They tie into non-functional reqs (e.g., <50ms latency) and support extensibility for ML/custom signals.

### User Story 1: As a trader, I want to detect a Doji pattern in real-time on 1min data so I can get an alert for potential reversals.
- **Acceptance Criteria**: The system must process incoming 1min OHLCV data via WebSockets, run the Doji detection (with tolerance param), and publish an event within 50ms; alerts should appear in TickStockApp's UI with symbol, timestamp, and price details.
- **Tied-in Components**: Integrates with RealTimeScanner in TickStockPL for incremental scans, EventPublisher for Redis pub-sub, and TickStockApp's event subscriber for UI updates.
- **Edge Cases**: Handle cases where candle range is zero (e.g., no trades—fallback to non-detection); ensure detection ignores low-volume bars (< average volume threshold) to avoid false positives.
- **Priority**: High—This is a quick-win candlestick pattern to validate real-time flow early.

### User Story 2: As a developer, I want to add a new breakout pattern easily so I can extend the library without refactoring the scanner.
- **Acceptance Criteria**: Subclass BasePattern, implement detect() method, add to PatternScanner via add_pattern(), and test with sample data; no changes needed to scanner core logic, with event output auto-generated.
- **Tied-in Components**: Relies on BasePattern abstraction in src/patterns/base.py, PatternScanner in src/analysis/scanner.py, and examples/ for demo scripts.
- **Edge Cases**: Support patterns with custom params (e.g., consolidation_window for Day1Breakout); ensure vectorized pandas ops for efficiency even with added complexity.
- **Priority**: Medium-High—Extensibility is key for future ML patterns, but we can prototype with 3-5 basics first.

### User Story 3: As an analyst, I want blended historical + live data for scans so patterns like HeadAndShoulders work across timeframes.
- **Acceptance Criteria**: DataBlender must concatenate DB historical data (e.g., from ohlcv_daily) with live WebSockets feeds, resample to target timeframe (e.g., daily), and feed a unified DataFrame to the scanner without gaps or duplicates.
- **Tied-in Components**: Involves HistoricalLoader and DataBlender in src/data/, plus nightly aggregator.py for roll-ups; ties to database_architecture.md schema.
- **Edge Cases**: Manage timezone mismatches (all UTC) or partial days (e.g., append live 1min to historical daily without overlapping); handle missing data by forward-filling or skipping detections.
- **Priority**: High—Blending is foundational for accurate multi-bar patterns like reversals.

### User Story 4: As a trader, I want backtesting support for patterns so I can evaluate historical performance before live trading.
- **Acceptance Criteria**: Provide a backtester.py that loads historical data, runs scans over date ranges, and outputs metrics (e.g., win rate, ROI) via pandas; integrate with PatternScanner for batch mode.
- **Tied-in Components**: Uses HistoricalLoader for DB pulls, metrics.py in src/utils/ for calculations, and visuals.py for optional charts (e.g., matplotlib equity curves).
- **Edge Cases**: Simulate slippage or commissions in metrics; handle varying timeframes (e.g., backtest Doji on 1min vs. daily) with param overrides.
- **Priority**: Medium—Core for validation, but we can add after initial patterns in Sprint 7.

### User Story 5: As a trader, I want customizable parameters for patterns so I can tune tolerances based on market conditions.
- **Acceptance Criteria**: Each pattern (e.g., Hammer) accepts a params dict (like {'shadow_ratio': 2.5}) at init; UI in TickStockApp allows per-user overrides, persisting to DB if needed.
- **Tied-in Components**: Built into BasePattern init; scanner.add_pattern() passes params; TickStockApp dashboard for input forms.
- **Edge Cases**: Validate param ranges (e.g., tolerance >0); default to safe values if invalid; ensure real-time scans use updated params without restart.
- **Priority**: Medium—Enhances usability, tie to Sprint 5 for core patterns.

### User Story 6: As a developer, I want modular data loaders so I can switch sources (e.g., from Polygon to yfinance) easily for flexibility.
- **Acceptance Criteria**: Abstract Loader interface with load() method; implement HistoricalLoader for DB/Polygon (fed from TickStockApp's ingestion) and a FallbackLoader for yfinance; swap via config without code changes, ensuring seamless handoff to TickStockPL's DataBlender.
- **Tied-in Components**: In src/data/loader.py within TickStockPL for core loading/blending; integrates with get_historical_data.md scripts, websockets_integration.md for live feeds from TickStockApp, and DataBlender for downstream processing.
- **Edge Cases**: Handle API rate limits (retry/sleep); normalize data formats (e.g., timestamp conversion) across sources; test fallback during Polygon outages without disrupting TickStockPL scans.
- **Priority**: Medium—Bootstrap-friendly for free-tier testing, implement in Sprint 10, with emphasis on TickStockPL's role in consuming the modular feeds.

### User Story 7: As an admin, I want scalability for scanning multiple symbols so the system handles high load without crashing.
- **Acceptance Criteria**: PatternScanner supports parallel processing (e.g., via multiprocessing for 100+ symbols); memory usage <2GB for 1k symbols; benchmark in perf tests.
- **Tied-in Components**: Uses Redis for pub-sub to distribute load; optional Docker for microservices in architecture_overview.md.
- **Edge Cases**: Throttle real-time updates during high-volume periods (e.g., market open); partition DB queries by symbol for efficiency.
- **Priority**: Medium-Low—Scale later, but design for it now to avoid rework.

### User Story 8: As a developer, I want to support multiple timeframes for some to all of the patterns when end users select intra-day versus daily or other timeframes.
- **Acceptance Criteria**: Patterns (e.g., Doji, Day1Breakout) must adapt via a 'timeframe' param (e.g., '1min', 'daily') in BasePattern, with DataBlender resampling input data accordingly; end-user selection in TickStockApp UI triggers scanner reconfig and publishes events with timeframe metadata.
- **Tied-in Components**: Enhances BasePattern and detect() methods in src/patterns/ to scale params (e.g., window sizes); integrates with DataBlender in src/data/ for on-the-fly resampling (pandas.resample); TickStockApp dashboard for timeframe dropdowns, feeding to PatternScanner via Redis.
- **Edge Cases**: For non-adaptable patterns (e.g., intraday-only like Day1Breakout), gracefully disable or warn; handle mixed data (e.g., resample 1min to daily mid-scan without losing precision); ensure performance stays under 50ms even for longer windows on daily data.
- **Priority**: High—This unlocks versatility across user needs, tie it to Sprint 2 for class blueprints and Sprint 3 for data flows.

### User Story 9: As a developer, I want to build an architecture for multi-pattern selection where conditions like "and price above 50 day exponential moving average" or "relative volume >= 1.5 times the daily average" are written in a core library and able to be referenced in other relative patterns.
- **Acceptance Criteria**: Implement a BaseCondition class for atomic indicators/filters (e.g., EMA crossover or relative volume check) that return boolean Series; allow CompositePattern to combine them with AND/OR logic via operators or methods; patterns in src/patterns/ can reference these for enhanced detection, with vectorized pandas/numpy ops for efficiency.
- **Tied-in Components**: New src/conditions/ folder for BaseCondition and implementations (e.g., EMACondition.py using pandas ewm() for exponential moving average, RelativeVolumeCondition.py calculating vs. rolling average); integrates with BasePattern's detect() to compose (e.g., Doji & EMACondition); PatternScanner supports composite adds; ties to backtester.py for testing combos.
- **Edge Cases**: Handle incompatible timeframes in composites (e.g., daily EMA with 1min pattern—auto-resample via DataBlender); manage computation overhead for complex chains (e.g., cap depth or optimize with caching); validate condition params at runtime to prevent errors like invalid periods.
- **Priority**: High—This boosts composability for advanced signals, prototype in Sprint 5 alongside core patterns and expand in Sprint 7 for reversals/breakouts.

### User Story 10: As a trader, I want visualizations of detected patterns so I can see graphical representations in the dashboard for better decision-making.
- **Acceptance Criteria**: On event receipt, TickStockApp generates charts (e.g., candlestick plots with pattern highlights) using matplotlib or similar; integrate with UI for interactive views, supporting zoom/export.
- **Tied-in Components**: Ties to visuals.py in src/utils/ for chart generation; EventPublisher includes details JSON for rendering; TickStockApp dashboard consumes events and displays (per architecture_overview.md).
- **Edge Cases**: Handle large datasets (e.g., downsample for daily views); support mobile-friendly rendering; fallback to text descriptions if visuals fail.
- **Priority**: Medium—Enhances user experience, implement post-core in Sprint 6 or 11.

### User Story 11: As an admin, I want event logging and auditing so I can review past pattern detections for compliance or debugging.
- **Acceptance Criteria**: Events published to Redis are also inserted to the 'events' DB table with JSON details; provide query interface in TickStockApp for filtering by symbol/pattern/timestamp.
- **Tied-in Components**: Extends EventPublisher to handle DB inserts (via SQLAlchemy); uses events table schema from database_architecture.md; TickStockApp for logging/UI.
- **Edge Cases**: Manage high event volume (e.g., batch inserts); retain data for configurable periods (e.g., compress old entries via TimescaleDB); secure access for admins only.
- **Priority**: Medium-Low—Important for production, but defer to Sprint 9 for testing/integration.

### User Story 12: As a developer, I want automated data seeding and aggregation processes so the DB is populated and maintained for reliable scanning.
- **Acceptance Criteria**: Scripts like get_historical.py seed initial data via Polygon; nightly aggregator.py rolls up 1min to daily; configurable for symbols/time ranges, with logging for failures.
- **Tied-in Components**: Builds on get_historical_data.md and websockets_integration.md; uses Aggregator class in data_integration.md; cron/scheduler integration for automation.
- **Edge Cases**: Handle partial loads (e.g., resume on interrupt); validate data integrity post-agg (e.g., check for gaps); fallback to yfinance if Polygon limits hit.
- **Priority**: High—Foundational for backtesting/live ops, tie to Sprint 10 for data integration.

### User Story 13: As a developer, I want robust error handling in data and scanning flows so the system recovers gracefully from failures like API outages or invalid data.
- **Acceptance Criteria**: Implement try-except in loaders/scanners with retries (e.g., exponential backoff); log errors to events table or console; skip faulty symbols without halting the batch.
- **Tied-in Components**: Enhances HistoricalLoader, DataBlender, and PatternScanner in src/data/ and src/analysis/; ties to Redis for fallback queuing; test with mock failures in tests/.
- **Edge Cases**: Recover from DB disconnects (reconnect); handle NaN/incomplete OHLCV (impute or skip); alert on persistent issues via events.
- **Priority**: Medium—Boosts reliability, weave into Sprint 8-9 for testing.
