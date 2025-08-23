# TickStock.ai Database Architecture

## Overview
PostgreSQL with TimescaleDB extension powers time-series efficiency for OHLCV data. The schema uses a hybrid approach: a raw, deep table for tick data and aggregated tables for higher timeframes (e.g., 1min, daily). Partitioning by time/symbol ensures scalability, with nightly jobs aggregating data to higher timeframes. This supports both high-frequency intraday patterns (e.g., Day1Breakout) and long-term patterns (e.g., HeadAndShoulders).

## Prototype Design
Below is the detailed schema from initial design discussions, tailored for TickStockPL’s pattern scanning and real-time/historical data blending.

### Schema
- **symbols**: Metadata for traded instruments.
  ```sql
  CREATE TABLE IF NOT EXISTS symbols (
      symbol VARCHAR(20) PRIMARY KEY,
      name VARCHAR(100),
      exchange VARCHAR(20),
      last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```
- **ticks**: Raw trade data for high-frequency analysis.
  ```sql
  CREATE TABLE IF NOT EXISTS ticks (
      symbol VARCHAR(20) REFERENCES symbols(symbol),
      timestamp TIMESTAMP WITH TIME ZONE,
      price NUMERIC(10, 4),
      volume BIGINT,
      PRIMARY KEY (symbol, timestamp)
  );
  SELECT create_hypertable('ticks', 'timestamp', partitioning_column => 'symbol', number_partitions => 100);
  CREATE INDEX idx_ticks_symbol_ts ON ticks (symbol, timestamp DESC);
  ```
- **ohlcv_1min**: Intraday bars for short-term patterns.
  ```sql
  CREATE TABLE IF NOT EXISTS ohlcv_1min (
      symbol VARCHAR(20) REFERENCES symbols(symbol),
      timestamp TIMESTAMP WITH TIME ZONE,
      open NUMERIC(10, 4),
      high NUMERIC(10, 4),
      low NUMERIC(10, 4),
      close NUMERIC(10, 4),
      volume BIGINT,
      PRIMARY KEY (symbol, timestamp)
  );
  SELECT create_hypertable('ohlcv_1min', 'timestamp');
  CREATE INDEX idx_1min_symbol_ts ON ohlcv_1min (symbol, timestamp DESC);
  ```
- **ohlcv_daily**: Daily aggregates for long-term patterns.
  ```sql
  CREATE TABLE IF NOT EXISTS ohlcv_daily (
      symbol VARCHAR(20) REFERENCES symbols(symbol),
      date DATE,
      open NUMERIC(10, 4),
      high NUMERIC(10, 4),
      low NUMERIC(10, 4),
      close NUMERIC(10, 4),
      volume BIGINT,
      PRIMARY KEY (symbol, date)
  );
  CREATE INDEX idx_daily_symbol_date ON ohlcv_daily (symbol, date DESC);
  ```
- **events** (optional): Stores pattern detections for auditing.
  ```sql
  CREATE TABLE IF NOT EXISTS events (
      symbol VARCHAR(20) REFERENCES symbols(symbol),
      timestamp TIMESTAMP WITH TIME ZONE,
      pattern VARCHAR(50),
      details JSONB,
      PRIMARY KEY (symbol, timestamp, pattern)
  );
  ```

### Indexes/Constraints
- **Indexes**: Composite (symbol, timestamp/date) DESC for fast range queries.
- **Foreign Keys**: Link to `symbols` for data integrity.
- **Unique Constraints**: Prevent duplicates (symbol, timestamp/date).
- **TimescaleDB**: Hypertables (`ticks`, `ohlcv_1min`) partition by time; `ticks` also by symbol (100 partitions).

### Aggregation Processes
- **Real-Time**: WebSockets data (from TickStockApp) inserts to `ticks` or `ohlcv_1min`. In-memory aggregation (pandas) for 1min bars if needed.
- **Nightly Jobs**: Python/SQL cron (e.g., `aggregator.py`) rolls up `ohlcv_1min` to `ohlcv_daily`:
  ```python
  # Sample aggregator logic
  query = """
  SELECT symbol, DATE(timestamp) as date,
         FIRST_VALUE(open) OVER w AS open,
         MAX(high) OVER w AS high,
         MIN(low) OVER w AS low,
         LAST_VALUE(close) OVER w AS close,
         SUM(volume) OVER w AS volume
  FROM ohlcv_1min
  WHERE timestamp >= CURRENT_DATE - INTERVAL '1 day' AND timestamp < CURRENT_DATE
  WINDOW w AS (PARTITION BY symbol, DATE(timestamp) ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
  GROUP BY symbol, date
  """
  ```
- **Compression**: TimescaleDB compresses old partitions (e.g., `ticks` > 30 days) to save space.

### Ties to Data Needs
- **Frequencies**: `ticks` for intraday (e.g., Day1Breakout); `ohlcv_1min` for short-term; `ohlcv_daily` for trends/reversals.
- **Integration**: `HistoricalLoader` (src/data/loader.py) pulls via SQLAlchemy to pandas for scanning. Real-time WebSockets feed `DataBlender` (websockets_integration.md).
- **Scalability**: Partitioning/compression supports millions of rows; batch inserts for efficiency.

[Add existing database content here.]