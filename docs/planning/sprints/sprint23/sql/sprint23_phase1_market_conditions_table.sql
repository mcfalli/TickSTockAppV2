-- Sprint 23 Phase 1: Market Conditions Table Creation
-- Advanced Analytics Foundation - Market Environment Tracking
-- Execute in PGAdmin connected to 'tickstock' database

-- ==============================================================
-- PHASE 1A: Market Conditions Core Table
-- ==============================================================

-- Table to track market environment for pattern correlation analysis
CREATE TABLE IF NOT EXISTS market_conditions (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    
    -- Market volatility metrics
    market_volatility DECIMAL(6,4),         -- VIX-like volatility measure (e.g., 18.45)
    volatility_percentile DECIMAL(5,2),     -- Percentile ranking (0-100)
    
    -- Volume and liquidity metrics  
    overall_volume BIGINT,                  -- Total market volume
    volume_vs_average DECIMAL(6,3),         -- Volume ratio vs 30-day average
    
    -- Market direction and trend
    market_trend VARCHAR(20) NOT NULL,      -- 'bullish', 'bearish', 'neutral'
    trend_strength DECIMAL(4,2),            -- Trend strength 0-10 scale
    
    -- Trading session context
    session_type VARCHAR(20) NOT NULL,      -- 'pre_market', 'regular', 'after_hours'
    day_of_week INTEGER NOT NULL,           -- 1-7 (Monday=1) for temporal analysis
    
    -- Market breadth indicators
    advancing_count INTEGER,                -- Number of advancing stocks
    declining_count INTEGER,                -- Number of declining stocks
    advance_decline_ratio DECIMAL(6,3),     -- A/D ratio
    
    -- Index performance context
    sp500_change DECIMAL(6,3),              -- S&P 500 % change from previous close
    nasdaq_change DECIMAL(6,3),             -- NASDAQ % change from previous close
    dow_change DECIMAL(6,3),                -- DOW % change from previous close
    
    -- Metadata
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_source VARCHAR(50) DEFAULT 'tickstock_pl',
    
    -- Constraints
    CONSTRAINT check_day_of_week CHECK (day_of_week BETWEEN 1 AND 7),
    CONSTRAINT check_volatility_positive CHECK (market_volatility >= 0),
    CONSTRAINT check_trend_values CHECK (market_trend IN ('bullish', 'bearish', 'neutral')),
    CONSTRAINT check_session_values CHECK (session_type IN ('pre_market', 'regular', 'after_hours')),
    CONSTRAINT check_trend_strength CHECK (trend_strength BETWEEN 0 AND 10)
);

-- ==============================================================
-- PHASE 1B: Performance Indexes for Market Conditions
-- ==============================================================

-- Primary index for time-based queries (most common access pattern)
CREATE INDEX IF NOT EXISTS idx_market_conditions_timestamp 
ON market_conditions(timestamp DESC);

-- Index for pattern correlation analysis (timestamp + volatility)
CREATE INDEX IF NOT EXISTS idx_market_conditions_analysis 
ON market_conditions(timestamp, market_volatility, session_type);

-- Index for temporal analysis by day of week
CREATE INDEX IF NOT EXISTS idx_market_conditions_temporal 
ON market_conditions(day_of_week, session_type, timestamp);

-- Index for trend analysis
CREATE INDEX IF NOT EXISTS idx_market_conditions_trend 
ON market_conditions(market_trend, trend_strength, timestamp);

-- Composite index for advanced analytics queries
-- Composite index for advanced analytics queries (non-partial version)
CREATE INDEX IF NOT EXISTS idx_market_conditions_analytics
ON market_conditions (session_type, day_of_week, market_volatility);

-- ==============================================================
-- PHASE 1C: Market Conditions Utility View
-- ==============================================================

-- View for easy access to current market conditions
CREATE OR REPLACE VIEW v_current_market_conditions AS
SELECT 
    timestamp,
    market_volatility,
    volatility_percentile,
    overall_volume,
    market_trend,
    trend_strength,
    session_type,
    day_of_week,
    advance_decline_ratio,
    sp500_change,
    nasdaq_change,
    calculated_at,
    -- Derived fields
    CASE 
        WHEN market_volatility < 15 THEN 'Low'
        WHEN market_volatility < 25 THEN 'Medium'
        ELSE 'High'
    END as volatility_level,
    
    CASE 
        WHEN volume_vs_average > 1.5 THEN 'High Volume'
        WHEN volume_vs_average > 0.8 THEN 'Normal Volume'
        ELSE 'Low Volume'
    END as volume_level,
    
    CASE 
        WHEN day_of_week IN (1,5) THEN 'Week Boundary'
        WHEN day_of_week IN (2,3,4) THEN 'Mid Week' 
        ELSE 'Weekend'
    END as week_period
FROM market_conditions 
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 day'
ORDER BY timestamp DESC;

-- ==============================================================
-- PHASE 1D: Sample Data Population (For Testing)
-- ==============================================================

-- Insert sample market conditions for testing (last 7 days)
INSERT INTO market_conditions (
    timestamp, market_volatility, volatility_percentile, overall_volume, 
    volume_vs_average, market_trend, trend_strength, session_type, 
    day_of_week, advancing_count, declining_count, advance_decline_ratio,
    sp500_change, nasdaq_change, dow_change
) VALUES 
-- Monday Regular Session
('2024-09-02 10:00:00', 18.45, 42.3, 1250000000, 1.12, 'bullish', 6.2, 'regular', 1, 2845, 1678, 1.695, 0.85, 1.23, 0.67),
('2024-09-02 14:30:00', 19.12, 45.8, 1180000000, 1.05, 'neutral', 3.1, 'regular', 1, 2234, 2289, 0.976, -0.12, -0.45, -0.23),

-- Tuesday Regular Session  
('2024-09-03 09:45:00', 16.78, 38.9, 1340000000, 1.19, 'bullish', 7.8, 'regular', 2, 3122, 1401, 2.228, 1.34, 1.89, 1.12),
('2024-09-03 15:15:00', 17.23, 41.2, 1290000000, 1.14, 'bullish', 6.9, 'regular', 2, 2967, 1556, 1.906, 0.78, 1.23, 0.89),

-- Wednesday Regular Session
('2024-09-04 11:30:00', 21.45, 58.7, 980000000, 0.87, 'bearish', 5.4, 'regular', 3, 1789, 2734, 0.654, -0.67, -1.12, -0.78),
('2024-09-04 13:45:00', 20.89, 55.3, 1050000000, 0.93, 'bearish', 4.8, 'regular', 3, 1923, 2600, 0.740, -0.45, -0.89, -0.56),

-- Thursday Pre-market & Regular
('2024-09-05 08:30:00', 19.34, 47.6, 450000000, 0.65, 'neutral', 2.3, 'pre_market', 4, 1245, 1387, 0.898, 0.12, 0.23, 0.08),
('2024-09-05 12:15:00', 18.67, 44.1, 1160000000, 1.03, 'bullish', 5.7, 'regular', 4, 2456, 2067, 1.188, 0.34, 0.67, 0.45),

-- Friday Regular Session
('2024-09-06 10:45:00', 22.15, 62.4, 1420000000, 1.26, 'bearish', 6.8, 'regular', 5, 1567, 2956, 0.530, -1.23, -1.78, -1.45),
('2024-09-06 16:00:00', 20.45, 52.9, 1380000000, 1.22, 'neutral', 3.9, 'regular', 5, 2123, 2400, 0.885, -0.56, -0.89, -0.67)

ON CONFLICT DO NOTHING;

-- ==============================================================
-- PHASE 1E: Grant Permissions
-- ==============================================================

-- Grant permissions to app_readwrite user
GRANT ALL PRIVILEGES ON TABLE market_conditions TO app_readwrite;
GRANT ALL PRIVILEGES ON SEQUENCE market_conditions_id_seq TO app_readwrite;
GRANT SELECT ON v_current_market_conditions TO app_readwrite;

-- ==============================================================
-- PHASE 1F: Verification Queries
-- ==============================================================

-- Verify table creation and structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'market_conditions' 
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- Verify indexes were created
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'market_conditions'
ORDER BY indexname;

-- Verify sample data was inserted
SELECT 
    COUNT(*) as total_records,
    MIN(timestamp) as earliest_record,
    MAX(timestamp) as latest_record,
    COUNT(DISTINCT day_of_week) as unique_days,
    COUNT(DISTINCT session_type) as unique_sessions
FROM market_conditions;

-- Test the view functionality
SELECT * FROM v_current_market_conditions LIMIT 5;

-- Performance test - should be <10ms
EXPLAIN ANALYZE 
SELECT * FROM market_conditions 
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days' 
ORDER BY timestamp DESC;

-- ==============================================================
-- Phase 1A Complete: Market Conditions Foundation
-- ==============================================================

-- This script provides:
-- ✅ market_conditions table with comprehensive market environment tracking
-- ✅ Performance indexes for <50ms analytics queries
-- ✅ Sample data for testing and validation
-- ✅ Utility view for easy access to current conditions
-- ✅ Proper permissions for app_readwrite user
-- ✅ Verification queries to ensure successful creation

COMMIT;