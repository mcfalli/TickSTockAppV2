# TickStock.ai Documentation Evolution Index

This index lists the core Markdown files defining TickStock.ai's third versioning effort (pre-production). Each file captures a critical aspect of the system, guiding development and ensuring alignment.

- **overview.md**: Outlines the vision, high-level processing flow, and major components (TickStock.ai front end, TickStockApp, TickStockPL). Purpose: Sets the project's north star for actionable market signals.
- **architecture_overview.md**: Details components' purpose, tech stack (Python, pandas, Redis), operations, and functionality. Purpose: Defines system structure and interactions.
- **database_architecture.md**: Specifies PostgreSQL/TimescaleDB schema (symbols, ticks, ohlcv_1min/daily), aggregations, and data needs. Purpose: Guides DB setup for historical/real-time pattern analysis.
- **pattern_library_overview.md**: Introduces the pattern library, its goals, categories (candlestick, chart, trend, breakout), and integration. Purpose: Frames the pattern detection scope.
- **pattern_library_architecture.md**: Describes the pattern library's folder structure, key classes (BasePattern, PatternScanner), and batch/real-time processes. Purpose: Technical blueprint for pattern implementation.
- **sprint_plan.md**: Outlines phased sprints (design, cleanup, implementation, testing, data integration). Purpose: Roadmap for development, including TickStockApp cleanup.
- **data_integration.md**: Covers data flows, loaders, preprocessors, and blending for historical/real-time data. Purpose: Ensures seamless data pipeline to scanner.
- **get_historical_data.md**: Details steps to seed the DB with historical OHLCV via Polygon REST API. Purpose: Guides initial data loading for backtesting.
- **websockets_integration.md**: Describes TickStockApp’s WebSockets (Polygon per-minute), feeding DataBlender in TickStockPL for events. Purpose: Defines real-time data pipeline.

These files evolve as we iterate, stored in `docs/evolution` for version control and reference.