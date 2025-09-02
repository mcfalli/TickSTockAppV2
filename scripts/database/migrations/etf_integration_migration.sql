-- TickStock Enhanced ETF Integration - Sprint 14 Phase 1
-- Database Migration for ETF-Specific Fields and Optimization
-- Execute in PGAdmin connected to 'tickstock' database

-- ==============================================================
-- PHASE 1: ETF Schema Enhancements
-- ==============================================================

-- Add ETF-specific columns to symbols table
ALTER TABLE symbols 
ADD COLUMN IF NOT EXISTS etf_type VARCHAR(50),                  -- ETF, ETMF, CEF, UIT etc.
ADD COLUMN IF NOT EXISTS aum_millions DECIMAL(12,2),           -- Assets Under Management in millions USD
ADD COLUMN IF NOT EXISTS expense_ratio DECIMAL(5,4),           -- Annual expense ratio (e.g., 0.0045 for 0.45%)
ADD COLUMN IF NOT EXISTS underlying_index VARCHAR(100),         -- Index tracked (e.g., 'S&P 500', 'NASDAQ 100')
ADD COLUMN IF NOT EXISTS correlation_reference VARCHAR(10),     -- Reference symbol for correlation (e.g., 'SPY', 'IWM')
ADD COLUMN IF NOT EXISTS fmv_supported BOOLEAN DEFAULT false,   -- Fair Market Value approximation support
ADD COLUMN IF NOT EXISTS creation_unit_size INTEGER,           -- Typical ETF creation unit size
ADD COLUMN IF NOT EXISTS dividend_frequency VARCHAR(20),       -- monthly, quarterly, semi-annual, annual
ADD COLUMN IF NOT EXISTS inception_date DATE,                  -- ETF launch date for maturity analysis
ADD COLUMN IF NOT EXISTS net_assets BIGINT,                    -- Net assets in USD (more precise than AUM)
ADD COLUMN IF NOT EXISTS primary_exchange VARCHAR(20),         -- Primary listing exchange for ETFs
ADD COLUMN IF NOT EXISTS issuer VARCHAR(100);                  -- ETF issuer/sponsor (e.g., 'BlackRock', 'Vanguard')

-- Add performance tracking columns for ETF-specific metrics
ALTER TABLE symbols
ADD COLUMN IF NOT EXISTS average_spread DECIMAL(8,6),          -- Average bid-ask spread
ADD COLUMN IF NOT EXISTS daily_volume_avg BIGINT,              -- 30-day average daily volume
ADD COLUMN IF NOT EXISTS premium_discount_avg DECIMAL(6,4),    -- Average premium/discount to NAV
ADD COLUMN IF NOT EXISTS tracking_error DECIMAL(8,6);          -- Tracking error vs underlying index

-- ==============================================================
-- PHASE 2: ETF Performance Indexes
-- ==============================================================

-- Composite index for ETF filtering and sorting queries
CREATE INDEX IF NOT EXISTS idx_etf_classification ON symbols 
(etf_type, market, active) 
WHERE etf_type IS NOT NULL;

-- Index for AUM-based queries (large-cap ETF filtering)
CREATE INDEX IF NOT EXISTS idx_etf_aum_size ON symbols 
(aum_millions DESC, active) 
WHERE etf_type IS NOT NULL AND aum_millions IS NOT NULL;

-- Index for expense ratio comparisons
CREATE INDEX IF NOT EXISTS idx_etf_expense_ratio ON symbols 
(expense_ratio ASC, etf_type, active)
WHERE etf_type IS NOT NULL AND expense_ratio IS NOT NULL;

-- Index for correlation analysis queries
CREATE INDEX IF NOT EXISTS idx_etf_correlation_ref ON symbols 
(correlation_reference, etf_type, active)
WHERE correlation_reference IS NOT NULL;

-- Index for issuer-based queries
CREATE INDEX IF NOT EXISTS idx_etf_issuer ON symbols 
(issuer, etf_type, active)
WHERE issuer IS NOT NULL;

-- Composite index for ETF performance metrics
CREATE INDEX IF NOT EXISTS idx_etf_performance ON symbols 
(average_spread ASC, daily_volume_avg DESC, active)
WHERE etf_type IS NOT NULL;

-- ==============================================================
-- PHASE 3: ETF Query Optimization Views
-- ==============================================================

-- ETF Summary View for Dashboard Queries
CREATE OR REPLACE VIEW v_etf_summary AS
SELECT 
    symbol,
    name,
    etf_type,
    aum_millions,
    expense_ratio,
    underlying_index,
    correlation_reference,
    issuer,
    average_spread,
    daily_volume_avg,
    premium_discount_avg,
    active,
    last_updated_utc
FROM symbols 
WHERE etf_type IS NOT NULL 
  AND active = true;

-- ETF Performance Ranking View
CREATE OR REPLACE VIEW v_etf_performance_ranking AS
SELECT 
    symbol,
    name,
    etf_type,
    aum_millions,
    expense_ratio,
    average_spread,
    daily_volume_avg,
    -- Performance score: lower expense ratio + tighter spread + higher volume = better
    (
        CASE WHEN expense_ratio IS NOT NULL THEN (1.0 - expense_ratio) * 0.3 ELSE 0 END +
        CASE WHEN average_spread IS NOT NULL THEN (1.0 - LEAST(average_spread * 1000, 1.0)) * 0.3 ELSE 0 END +
        CASE WHEN daily_volume_avg IS NOT NULL THEN LEAST(daily_volume_avg / 10000000.0, 1.0) * 0.4 ELSE 0 END
    ) as performance_score,
    active
FROM symbols 
WHERE etf_type IS NOT NULL 
  AND active = true
ORDER BY performance_score DESC;

-- ETF Correlation Groups View
CREATE OR REPLACE VIEW v_etf_correlation_groups AS
SELECT 
    correlation_reference,
    COUNT(*) as etf_count,
    AVG(expense_ratio) as avg_expense_ratio,
    AVG(aum_millions) as avg_aum,
    STRING_AGG(symbol, ', ' ORDER BY aum_millions DESC) as symbols
FROM symbols 
WHERE etf_type IS NOT NULL 
  AND correlation_reference IS NOT NULL
  AND active = true
GROUP BY correlation_reference
ORDER BY etf_count DESC, avg_aum DESC;

-- ==============================================================
-- PHASE 4: FMV Support Table (Fair Market Value Approximation)
-- ==============================================================

-- Table for storing intraday fair market value approximations
CREATE TABLE IF NOT EXISTS etf_fmv_cache (
    symbol VARCHAR(20) REFERENCES symbols(symbol),
    timestamp TIMESTAMP WITH TIME ZONE,
    nav_estimate DECIMAL(12,4),              -- Net Asset Value estimate
    premium_discount DECIMAL(6,4),           -- Premium/discount to NAV
    confidence_score DECIMAL(3,2),           -- Confidence in FMV calculation (0.0-1.0)
    component_symbols TEXT[],                -- Array of underlying symbols used
    calculation_method VARCHAR(50),          -- 'weighted_average', 'index_proxy', 'sector_avg'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, timestamp)
);

-- Convert to hypertable for time-series efficiency
SELECT create_hypertable('etf_fmv_cache', 'timestamp', 
    partitioning_column => 'symbol', 
    number_partitions => 50,
    if_not_exists => true
);

-- Index for FMV lookup queries
CREATE INDEX IF NOT EXISTS idx_etf_fmv_symbol_time ON etf_fmv_cache 
(symbol, timestamp DESC);

-- Index for recent FMV data queries (partial index without time filter)
CREATE INDEX IF NOT EXISTS idx_etf_fmv_recent ON etf_fmv_cache 
(timestamp DESC, confidence_score DESC);

-- Compression and retention policies for FMV cache
ALTER TABLE etf_fmv_cache SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- Compress FMV data older than 4 hours
SELECT add_compression_policy('etf_fmv_cache', INTERVAL '4 hours');

-- Retain FMV data for 30 days only (high frequency data)
SELECT add_retention_policy('etf_fmv_cache', INTERVAL '30 days');

-- ==============================================================
-- PHASE 5: ETF Sector Classification Table
-- ==============================================================

-- Table for ETF sector/theme classification
CREATE TABLE IF NOT EXISTS etf_classifications (
    symbol VARCHAR(20) REFERENCES symbols(symbol),
    classification_type VARCHAR(50),         -- 'sector', 'theme', 'strategy', 'geography'
    classification_value VARCHAR(100),       -- 'Technology', 'ESG', 'Growth', 'International'
    weight_percentage DECIMAL(5,2),          -- Percentage allocation (for multi-sector ETFs)
    source VARCHAR(50),                      -- 'polygon', 'manual', 'third_party'
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, classification_type, classification_value)
);

-- Index for sector-based ETF filtering
CREATE INDEX IF NOT EXISTS idx_etf_sector_class ON etf_classifications 
(classification_type, classification_value, weight_percentage DESC);

-- Index for ETF multi-classification queries
CREATE INDEX IF NOT EXISTS idx_etf_symbol_class ON etf_classifications 
(symbol, classification_type);

-- ==============================================================
-- PHASE 6: Data Migration and Default Values
-- ==============================================================

-- Set default values for existing symbols based on type
UPDATE symbols 
SET 
    etf_type = CASE 
        WHEN type IN ('ETF', 'ETP') THEN 'ETF'
        WHEN type = 'CEF' THEN 'CEF'
        ELSE NULL 
    END,
    fmv_supported = CASE 
        WHEN type IN ('ETF', 'ETP') THEN true 
        ELSE false 
    END,
    dividend_frequency = CASE 
        WHEN type IN ('ETF', 'ETP') THEN 'quarterly' 
        ELSE NULL 
    END,
    primary_exchange = exchange
WHERE type IN ('ETF', 'ETP', 'CEF');

-- ==============================================================
-- PHASE 7: Performance Monitoring Functions
-- ==============================================================

-- Function to get ETF performance summary
CREATE OR REPLACE FUNCTION get_etf_performance_summary()
RETURNS TABLE (
    total_etfs INTEGER,
    avg_expense_ratio DECIMAL(5,4),
    avg_aum_millions DECIMAL(12,2),
    top_issuer VARCHAR(100),
    most_common_type VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_etfs,
        AVG(s.expense_ratio) as avg_expense_ratio,
        AVG(s.aum_millions) as avg_aum_millions,
        (SELECT issuer FROM symbols WHERE etf_type IS NOT NULL GROUP BY issuer ORDER BY COUNT(*) DESC LIMIT 1) as top_issuer,
        (SELECT etf_type FROM symbols WHERE etf_type IS NOT NULL GROUP BY etf_type ORDER BY COUNT(*) DESC LIMIT 1) as most_common_type
    FROM symbols s
    WHERE s.etf_type IS NOT NULL AND s.active = true;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate ETF liquidity score
CREATE OR REPLACE FUNCTION calculate_etf_liquidity_score(symbol_input VARCHAR(20))
RETURNS DECIMAL(3,2) AS $$
DECLARE
    liquidity_score DECIMAL(3,2) := 0.0;
    vol_score DECIMAL(3,2);
    spread_score DECIMAL(3,2);
    aum_score DECIMAL(3,2);
BEGIN
    SELECT 
        -- Volume component (40% weight)
        CASE WHEN daily_volume_avg IS NULL THEN 0
             WHEN daily_volume_avg >= 1000000 THEN 0.4
             ELSE (daily_volume_avg / 1000000.0) * 0.4
        END +
        -- Spread component (35% weight)  
        CASE WHEN average_spread IS NULL THEN 0
             WHEN average_spread <= 0.001 THEN 0.35
             ELSE (1.0 - LEAST(average_spread * 100, 1.0)) * 0.35
        END +
        -- AUM component (25% weight)
        CASE WHEN aum_millions IS NULL THEN 0
             WHEN aum_millions >= 1000 THEN 0.25
             ELSE (aum_millions / 1000.0) * 0.25
        END
    INTO liquidity_score
    FROM symbols
    WHERE symbol = symbol_input AND etf_type IS NOT NULL;
    
    RETURN COALESCE(liquidity_score, 0.0);
END;
$$ LANGUAGE plpgsql;

-- ==============================================================
-- PHASE 8: Grant Permissions
-- ==============================================================

-- Grant permissions to app_readwrite user for all new structures
GRANT ALL PRIVILEGES ON TABLE symbols TO app_readwrite;
GRANT ALL PRIVILEGES ON TABLE etf_fmv_cache TO app_readwrite;
GRANT ALL PRIVILEGES ON TABLE etf_classifications TO app_readwrite;

-- Grant access to views
GRANT SELECT ON v_etf_summary TO app_readwrite;
GRANT SELECT ON v_etf_performance_ranking TO app_readwrite;
GRANT SELECT ON v_etf_correlation_groups TO app_readwrite;

-- Grant function execution
GRANT EXECUTE ON FUNCTION get_etf_performance_summary() TO app_readwrite;
GRANT EXECUTE ON FUNCTION calculate_etf_liquidity_score(VARCHAR) TO app_readwrite;

-- ==============================================================
-- PHASE 9: Verification Queries
-- ==============================================================

-- Verify new columns exist
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'symbols' 
  AND table_schema = 'public'
  AND column_name LIKE '%etf%' OR column_name LIKE '%aum%' OR column_name LIKE '%expense%'
ORDER BY ordinal_position;

-- Verify indexes were created
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'symbols' 
  AND indexname LIKE '%etf%'
ORDER BY indexname;

-- Verify views exist
SELECT 
    viewname, 
    definition 
FROM pg_views 
WHERE schemaname = 'public' 
  AND viewname LIKE 'v_etf%'
ORDER BY viewname;

-- Test performance function
SELECT * FROM get_etf_performance_summary();

-- Display sample ETF data
SELECT 
    symbol, 
    name, 
    etf_type, 
    aum_millions, 
    expense_ratio, 
    underlying_index,
    correlation_reference,
    active
FROM symbols 
WHERE etf_type IS NOT NULL 
ORDER BY aum_millions DESC NULLS LAST
LIMIT 10;