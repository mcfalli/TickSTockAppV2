# Data Integration Overview

## Flows
- **Historical**: DB queries (SQLAlchemy) to pandas; from ohlcv_daily/1min.
- **Real-Time**: WebSockets/APIs append ticks; incremental scan.
- **Blending**: DataBlender concatenates/resamples (e.g., daily history + 1min live).

## Classes
- **HistoricalLoader**: Load by symbol/date.
- **DataBlender**: Append/resample for unified DataFrame.
- **Aggregator**: Nightly scripts for roll-ups.

## Frequency Handling
- Resample on-the-fly (pandas.agg for OHLC).
- Patterns adapt via params (e.g., window scaled to timeframe).

Ties to scanner: Feed prepped DataFrame for detections/events.