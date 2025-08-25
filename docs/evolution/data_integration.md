# Data Integration Overview

## Flows
- **Historical**: DB queries (SQLAlchemy) to pandas; from ohlcv_daily/1min. (Ties to User Story 12 for seeding.)
- **Real-Time**: WebSockets/APIs append ticks; incremental scan.
- **Blending**: DataBlender concatenates/resamples (e.g., daily history + 1min live). Handles gaps via forward-fill or skips (per User Story 13 edges).


## Classes
- **HistoricalLoader**: Load by symbol/date. (Modular for sources per User Story 6.) see src/data/loader.py (Pseudocode)
- **DataBlender**: Append/resample for unified DataFrame. see src/data/preprocessor.py (Pseudocode)
- **Aggregator**: Nightly scripts for roll-ups. see src/data/aggregator.py (Pseudocode)

## Frequency Handling
- Resample on-the-fly (pandas.agg for OHLC). Patterns adapt via params (e.g., window scaled to timeframe per User Story 8; e.g., tighter Doji tolerance on 1min from patterns_library_patterns.md).
- Ties to scanner: Feed prepped DataFrame for detections/events.

## Data Flow Diagram (Text-Based)

[Polygon REST/yfinance] --> [HistoricalLoader --> DB (Insert/Upsert to ohlcv_*)]
[Polygon WS] --> [TickStockApp --> Redis --> DataBlender (Append/Resample historical from DB)]
                                      |
                                      v
[Blended DF --> PatternScanner.detect() --> Events (Publish to Redis/DB)]
[Nightly: Aggregator (1min --> daily) via cron]


### Optional Early Validation Notes
Spun up local Docker (docker run -p 5432:5432 -e POSTGRES_PASSWORD=pass timescale/timescaledb:latest-pg16). Ran schema SQL—hypertables create fine, compression policy adds without issues. Sample insert/query: Fast on 10k rows, but test partitioning with 1M+ in Sprint 9 perf (ties to User Story 7 scalability). Gotcha: Ensure TZ=UTC in connections to avoid mismatches.