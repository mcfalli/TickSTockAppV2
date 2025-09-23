-- Create OHLCV tables for hourly, weekly, and monthly timeframes
-- Author: TickStock Development Team
-- Date: 2025-09-21
-- Description: Creates OHLCV aggregation tables matching existing 1min and daily table patterns

-- ============================================================================
-- HOURLY OHLCV TABLE (TimescaleDB Hypertable)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ohlcv_hourly (
    symbol VARCHAR(20) REFERENCES symbols(symbol),
    timestamp TIMESTAMP WITH TIME ZONE,
    open NUMERIC(10, 4),
    high NUMERIC(10, 4),
    low NUMERIC(10, 4),
    close NUMERIC(10, 4),
    volume BIGINT,
    PRIMARY KEY (symbol, timestamp)
);

-- Convert to TimescaleDB hypertable for time-series optimization
SELECT create_hypertable('ohlcv_hourly', 'timestamp', if_not_exists => TRUE);

-- Create index for optimal query performance
CREATE INDEX IF NOT EXISTS idx_hourly_symbol_ts ON ohlcv_hourly (symbol, timestamp DESC);

-- Add comment to table
COMMENT ON TABLE ohlcv_hourly IS 'Hourly OHLCV data aggregated from 1-minute bars';
COMMENT ON COLUMN ohlcv_hourly.symbol IS 'Stock ticker symbol';
COMMENT ON COLUMN ohlcv_hourly.timestamp IS 'Hour boundary timestamp (e.g., 2025-01-01 14:00:00)';
COMMENT ON COLUMN ohlcv_hourly.open IS 'Opening price of the hour';
COMMENT ON COLUMN ohlcv_hourly.high IS 'Highest price during the hour';
COMMENT ON COLUMN ohlcv_hourly.low IS 'Lowest price during the hour';
COMMENT ON COLUMN ohlcv_hourly.close IS 'Closing price of the hour';
COMMENT ON COLUMN ohlcv_hourly.volume IS 'Total volume traded during the hour';

-- ============================================================================
-- WEEKLY OHLCV TABLE (Regular Table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ohlcv_weekly (
    symbol VARCHAR(20) REFERENCES symbols(symbol),
    week_start DATE,
    open NUMERIC(10, 4),
    high NUMERIC(10, 4),
    low NUMERIC(10, 4),
    close NUMERIC(10, 4),
    volume BIGINT,
    PRIMARY KEY (symbol, week_start)
);

-- Create index for optimal query performance
CREATE INDEX IF NOT EXISTS idx_weekly_symbol_date ON ohlcv_weekly (symbol, week_start DESC);

-- Add comment to table
COMMENT ON TABLE ohlcv_weekly IS 'Weekly OHLCV data aggregated from daily bars';
COMMENT ON COLUMN ohlcv_weekly.symbol IS 'Stock ticker symbol';
COMMENT ON COLUMN ohlcv_weekly.week_start IS 'Monday of the week (ISO week start)';
COMMENT ON COLUMN ohlcv_weekly.open IS 'Opening price of the week (Monday open)';
COMMENT ON COLUMN ohlcv_weekly.high IS 'Highest price during the week';
COMMENT ON COLUMN ohlcv_weekly.low IS 'Lowest price during the week';
COMMENT ON COLUMN ohlcv_weekly.close IS 'Closing price of the week (Friday close)';
COMMENT ON COLUMN ohlcv_weekly.volume IS 'Total volume traded during the week';

-- ============================================================================
-- MONTHLY OHLCV TABLE (Regular Table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ohlcv_monthly (
    symbol VARCHAR(20) REFERENCES symbols(symbol),
    month_start DATE,
    open NUMERIC(10, 4),
    high NUMERIC(10, 4),
    low NUMERIC(10, 4),
    close NUMERIC(10, 4),
    volume BIGINT,
    PRIMARY KEY (symbol, month_start)
);

-- Create index for optimal query performance
CREATE INDEX IF NOT EXISTS idx_monthly_symbol_date ON ohlcv_monthly (symbol, month_start DESC);

-- Add comment to table
COMMENT ON TABLE ohlcv_monthly IS 'Monthly OHLCV data aggregated from daily bars';
COMMENT ON COLUMN ohlcv_monthly.symbol IS 'Stock ticker symbol';
COMMENT ON COLUMN ohlcv_monthly.month_start IS 'First day of the month';
COMMENT ON COLUMN ohlcv_monthly.open IS 'Opening price of the month (first trading day)';
COMMENT ON COLUMN ohlcv_monthly.high IS 'Highest price during the month';
COMMENT ON COLUMN ohlcv_monthly.low IS 'Lowest price during the month';
COMMENT ON COLUMN ohlcv_monthly.close IS 'Closing price of the month (last trading day)';
COMMENT ON COLUMN ohlcv_monthly.volume IS 'Total volume traded during the month';

-- ============================================================================
-- GRANTS (matching existing table permissions)
-- ============================================================================
-- Grant permissions to app_readwrite user (application access)
GRANT SELECT, INSERT, UPDATE, DELETE ON ohlcv_hourly TO app_readwrite;
GRANT SELECT, INSERT, UPDATE, DELETE ON ohlcv_weekly TO app_readwrite;
GRANT SELECT, INSERT, UPDATE, DELETE ON ohlcv_monthly TO app_readwrite;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these to verify tables were created successfully:
-- SELECT table_name, table_type FROM information_schema.tables
-- WHERE table_schema = 'public'
-- AND table_name IN ('ohlcv_hourly', 'ohlcv_weekly', 'ohlcv_monthly');

-- Check if hourly table is a hypertable:
-- SELECT hypertable_name FROM timescaledb_information.hypertables
-- WHERE hypertable_name = 'ohlcv_hourly';