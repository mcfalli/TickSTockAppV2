# TimescaleDB Setup SQL for TickStockPL Sprint 10

**Run these SQL commands in pgAdmin to setup the TickStockPL schema**
*Assumes tickstock database and app_readwrite user already exist*

## Step 1: Connect to tickstock Database

**In pgAdmin: Right-click on tickstock database → Query Tool**

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Grant schema permissions to app_readwrite
GRANT ALL ON SCHEMA public TO app_readwrite;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_readwrite;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_readwrite;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO app_readwrite;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_readwrite;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_readwrite;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO app_readwrite;
```

## Step 2: Create TickStockPL Schema

```sql
-- 1. Symbols metadata table
CREATE TABLE IF NOT EXISTS symbols (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    exchange VARCHAR(20),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Ticks table (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS ticks (
    symbol VARCHAR(20) REFERENCES symbols(symbol),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC(12, 4) NOT NULL,
    volume BIGINT NOT NULL,
    PRIMARY KEY (symbol, timestamp)
);

-- Convert ticks to hypertable (only if not already converted)
SELECT create_hypertable('ticks', 'timestamp', 
                        partitioning_column => 'symbol', 
                        number_partitions => 100,
                        if_not_exists => TRUE);

-- 3. OHLCV 1-minute data (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS ohlcv_1min (
    symbol VARCHAR(20) REFERENCES symbols(symbol),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open NUMERIC(12, 4) NOT NULL,
    high NUMERIC(12, 4) NOT NULL,
    low NUMERIC(12, 4) NOT NULL,
    close NUMERIC(12, 4) NOT NULL,
    volume BIGINT NOT NULL,
    PRIMARY KEY (symbol, timestamp)
);

-- Convert ohlcv_1min to hypertable
SELECT create_hypertable('ohlcv_1min', 'timestamp', 
                        if_not_exists => TRUE);

-- 4. OHLCV daily data (regular table - smaller volume)
CREATE TABLE IF NOT EXISTS ohlcv_daily (
    symbol VARCHAR(20) REFERENCES symbols(symbol),
    date DATE NOT NULL,
    open NUMERIC(12, 4) NOT NULL,
    high NUMERIC(12, 4) NOT NULL,
    low NUMERIC(12, 4) NOT NULL,
    close NUMERIC(12, 4) NOT NULL,
    volume BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (symbol, date)
);

-- 5. Events table for pattern detection results
CREATE TABLE IF NOT EXISTS events (
    symbol VARCHAR(20) REFERENCES symbols(symbol),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    pattern VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) DEFAULT 'daily',
    details JSONB,
    confidence NUMERIC(5, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (symbol, timestamp, pattern, timeframe)
);
```

## Step 3: Create Performance Indexes

```sql
-- Ticks table indexes
CREATE INDEX IF NOT EXISTS idx_ticks_symbol_ts ON ticks (symbol, timestamp DESC);

-- OHLCV 1min indexes (covering indexes for pattern detection)
CREATE INDEX IF NOT EXISTS idx_1min_symbol_ts ON ohlcv_1min (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_1min_covering ON ohlcv_1min (symbol, timestamp DESC) 
    INCLUDE (open, high, low, close, volume);

-- OHLCV daily indexes (covering indexes for pattern detection)
CREATE INDEX IF NOT EXISTS idx_daily_symbol_date ON ohlcv_daily (symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_covering ON ohlcv_daily (symbol, date DESC) 
    INCLUDE (open, high, low, close, volume);

-- Events table indexes
CREATE INDEX IF NOT EXISTS idx_events_symbol_pattern ON events (symbol, pattern, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_timeframe ON events (timeframe, timestamp DESC);
```

## Step 4: Set up TimescaleDB Compression and Retention Policies

```sql
-- Enable compression on hypertables
ALTER TABLE ticks SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE ohlcv_1min SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- Add compression policies (compress data older than specified interval)
SELECT add_compression_policy('ticks', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_compression_policy('ohlcv_1min', INTERVAL '90 days', if_not_exists => TRUE);

-- Add retention policies (automatically drop old data)
SELECT add_retention_policy('ticks', INTERVAL '1 year', if_not_exists => TRUE);
-- Note: No retention policy on ohlcv_1min and ohlcv_daily - keep historical data
```

## Step 5: Add Sample Test Data

```sql
-- Insert sample symbols for testing
INSERT INTO symbols (symbol, name, exchange) VALUES 
    ('AAPL', 'Apple Inc.', 'NASDAQ'),
    ('TSLA', 'Tesla Inc.', 'NASDAQ'), 
    ('MSFT', 'Microsoft Corporation', 'NASDAQ'),
    ('GOOGL', 'Alphabet Inc.', 'NASDAQ'),
    ('AMZN', 'Amazon.com Inc.', 'NASDAQ')
ON CONFLICT (symbol) DO NOTHING;
```

## Step 6: Verification Queries

```sql
-- Verify TimescaleDB extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';

-- Verify hypertables
SELECT hypertable_name, num_dimensions FROM timescaledb_information.hypertables;

-- Verify tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Verify indexes
SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE 'idx_%' ORDER BY indexname;

-- Verify compression policies
SELECT application_name, schedule_interval, config 
FROM timescaledb_information.jobs 
WHERE proc_name = 'policy_compression';

-- Verify retention policies  
SELECT application_name, schedule_interval, config 
FROM timescaledb_information.jobs 
WHERE proc_name = 'policy_retention';

-- Test data
SELECT * FROM symbols;
```

## Expected Results

After running all steps, you should see:
- ✅ 5 tables created: symbols, ticks, ohlcv_1min, ohlcv_daily, events
- ✅ 2 hypertables: ticks, ohlcv_1min
- ✅ 6 performance indexes created
- ✅ Compression policies on ticks (30 days) and ohlcv_1min (90 days)
- ✅ Retention policy on ticks (1 year)
- ✅ 5 sample symbols inserted

**Ready for TickStockPL Phase 2: Historical Data Loading!**