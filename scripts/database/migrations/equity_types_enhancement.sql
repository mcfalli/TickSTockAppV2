-- TickStock Equity Types Enhancement - Sprint 14 Phase 2
-- Enhanced equity_types table for processing rules and configuration management
-- Execute in PGAdmin connected to 'tickstock' database

-- ==============================================================
-- PHASE 1: Equity Types Schema Enhancement
-- ==============================================================

-- Check if equity_types table exists, create if needed
CREATE TABLE IF NOT EXISTS equity_types (
    id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add processing configuration columns
ALTER TABLE equity_types 
ADD COLUMN IF NOT EXISTS update_frequency VARCHAR(20) DEFAULT 'daily',
ADD COLUMN IF NOT EXISTS processing_rules JSONB,
ADD COLUMN IF NOT EXISTS requires_eod_validation BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS additional_data_fields JSONB,
ADD COLUMN IF NOT EXISTS priority_level INTEGER DEFAULT 50,
ADD COLUMN IF NOT EXISTS batch_size INTEGER DEFAULT 100,
ADD COLUMN IF NOT EXISTS rate_limit_ms INTEGER DEFAULT 12000;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_equity_types_frequency ON equity_types (update_frequency);
CREATE INDEX IF NOT EXISTS idx_equity_types_priority ON equity_types (priority_level DESC);
CREATE INDEX IF NOT EXISTS idx_equity_types_active ON equity_types (type_name) 
WHERE processing_rules IS NOT NULL;

-- ==============================================================
-- PHASE 2: Initial Equity Types Configuration
-- ==============================================================

-- Insert or update initial equity types with processing rules
INSERT INTO equity_types (
    type_name, 
    description, 
    update_frequency, 
    processing_rules, 
    requires_eod_validation, 
    additional_data_fields, 
    priority_level, 
    batch_size, 
    rate_limit_ms
) VALUES 
-- ETF Processing Configuration
(
    'ETF',
    'Exchange Traded Funds requiring enhanced metadata',
    'daily',
    '{
        "aum_required": true,
        "expense_ratio_required": true,
        "correlation_tracking": true,
        "fmv_support": true,
        "issuer_identification": true,
        "sector_classification": true
    }'::jsonb,
    true,
    '{
        "correlation_tracking": true,
        "premium_discount_monitoring": true,
        "liquidity_scoring": true,
        "nav_comparison": true
    }'::jsonb,
    90,
    50,
    12000
),

-- Real-time Stock Processing
(
    'STOCK_REALTIME',
    'High-priority stocks with real-time data requirements',
    'realtime',
    '{
        "eod_validation": true,
        "intraday_processing": true,
        "pattern_detection": true,
        "volume_monitoring": true
    }'::jsonb,
    true,
    '{
        "intraday_priority": "high",
        "pattern_alerts": true,
        "volume_threshold_monitoring": true
    }'::jsonb,
    100,
    25,
    6000
),

-- Standard EOD Stock Processing
(
    'STOCK_EOD',
    'Standard stocks with end-of-day processing',
    'daily',
    '{
        "bulk_processing": true,
        "batch_optimization": true,
        "standard_validation": true
    }'::jsonb,
    true,
    '{
        "batch_size": 100,
        "processing_window": "after_market_close"
    }'::jsonb,
    50,
    100,
    12000
),

-- ETN Processing (Exchange Traded Notes)
(
    'ETN',
    'Exchange Traded Notes with special processing requirements',
    'daily',
    '{
        "issuer_risk_monitoring": true,
        "credit_risk_tracking": true,
        "underlying_index_correlation": true
    }'::jsonb,
    true,
    '{
        "credit_rating_monitoring": true,
        "issuer_financial_health": true
    }'::jsonb,
    70,
    25,
    15000
),

-- Penny Stock Processing
(
    'PENNY_STOCK',
    'Low-priced stocks requiring special handling',
    'daily',
    '{
        "volatility_monitoring": true,
        "volume_validation": true,
        "fraud_detection": true,
        "spread_monitoring": true
    }'::jsonb,
    true,
    '{
        "volatility_threshold": 0.30,
        "minimum_volume": 10000,
        "spread_alert_threshold": 0.10
    }'::jsonb,
    30,
    50,
    20000
),

-- Development Testing Symbols
(
    'DEV_TESTING',
    'Development and testing symbols with minimal processing',
    'manual',
    '{
        "minimal_validation": true,
        "test_data_acceptable": true,
        "fast_processing": true
    }'::jsonb,
    false,
    '{
        "development_mode": true,
        "mock_data_allowed": true
    }'::jsonb,
    10,
    10,
    6000
)

-- Handle conflicts by updating existing records
ON CONFLICT (type_name) DO UPDATE SET
    description = EXCLUDED.description,
    update_frequency = EXCLUDED.update_frequency,
    processing_rules = EXCLUDED.processing_rules,
    requires_eod_validation = EXCLUDED.requires_eod_validation,
    additional_data_fields = EXCLUDED.additional_data_fields,
    priority_level = EXCLUDED.priority_level,
    batch_size = EXCLUDED.batch_size,
    rate_limit_ms = EXCLUDED.rate_limit_ms,
    updated_at = CURRENT_TIMESTAMP;

-- ==============================================================
-- PHASE 3: Processing Rules Functions
-- ==============================================================

-- Function to get processing configuration for equity type
CREATE OR REPLACE FUNCTION get_equity_processing_config(equity_type_name VARCHAR(50))
RETURNS JSONB AS $$
DECLARE
    config_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'type_name', type_name,
        'update_frequency', update_frequency,
        'processing_rules', processing_rules,
        'requires_eod_validation', requires_eod_validation,
        'additional_data_fields', additional_data_fields,
        'priority_level', priority_level,
        'batch_size', batch_size,
        'rate_limit_ms', rate_limit_ms
    )
    INTO config_result
    FROM equity_types
    WHERE type_name = equity_type_name;
    
    RETURN COALESCE(config_result, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql;

-- Function to get symbols by equity type for processing
CREATE OR REPLACE FUNCTION get_symbols_for_processing(
    equity_type_name VARCHAR(50),
    limit_count INTEGER DEFAULT 100
)
RETURNS TABLE (
    symbol VARCHAR(20),
    name VARCHAR(500),
    exchange VARCHAR(50),
    market_cap BIGINT,
    processing_priority INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.symbol,
        s.name,
        s.exchange,
        s.market_cap,
        et.priority_level as processing_priority
    FROM symbols s
    JOIN equity_types et ON s.type = et.type_name
    WHERE et.type_name = equity_type_name
    AND s.active = true
    ORDER BY et.priority_level DESC, s.market_cap DESC NULLS LAST
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update processing statistics
CREATE OR REPLACE FUNCTION update_processing_stats(
    equity_type_name VARCHAR(50),
    symbols_processed INTEGER,
    symbols_failed INTEGER,
    processing_duration_seconds INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    current_stats JSONB;
    updated_stats JSONB;
BEGIN
    -- Get current additional_data_fields
    SELECT additional_data_fields INTO current_stats
    FROM equity_types
    WHERE type_name = equity_type_name;
    
    -- Update statistics
    updated_stats = COALESCE(current_stats, '{}'::jsonb) || jsonb_build_object(
        'last_processing_date', CURRENT_TIMESTAMP,
        'symbols_processed', symbols_processed,
        'symbols_failed', symbols_failed,
        'processing_duration_seconds', processing_duration_seconds,
        'success_rate', 
        CASE 
            WHEN symbols_processed + symbols_failed > 0 
            THEN symbols_processed::float / (symbols_processed + symbols_failed)
            ELSE 1.0 
        END,
        'processing_history', 
        COALESCE((current_stats->'processing_history')::jsonb, '[]'::jsonb) || 
        jsonb_build_array(jsonb_build_object(
            'date', CURRENT_TIMESTAMP,
            'processed', symbols_processed,
            'failed', symbols_failed,
            'duration', processing_duration_seconds
        ))
    );
    
    -- Update the equity_types table
    UPDATE equity_types 
    SET additional_data_fields = updated_stats,
        updated_at = CURRENT_TIMESTAMP
    WHERE type_name = equity_type_name;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================
-- PHASE 4: Processing Queue Management
-- ==============================================================

-- Create processing queue table for equity types
CREATE TABLE IF NOT EXISTS equity_processing_queue (
    id SERIAL PRIMARY KEY,
    equity_type VARCHAR(50) REFERENCES equity_types(type_name),
    symbol VARCHAR(20),
    processing_priority INTEGER DEFAULT 50,
    scheduled_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes for queue management
CREATE INDEX IF NOT EXISTS idx_equity_queue_status ON equity_processing_queue (status, processing_priority DESC);
CREATE INDEX IF NOT EXISTS idx_equity_queue_scheduled ON equity_processing_queue (scheduled_time);
CREATE INDEX IF NOT EXISTS idx_equity_queue_type ON equity_processing_queue (equity_type, status);

-- Function to queue symbols for processing
CREATE OR REPLACE FUNCTION queue_symbols_for_processing(
    equity_type_name VARCHAR(50),
    symbol_list TEXT[] DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    queued_count INTEGER := 0;
    symbol_record RECORD;
    processing_priority INTEGER;
BEGIN
    -- Get priority level for equity type
    SELECT priority_level INTO processing_priority
    FROM equity_types
    WHERE type_name = equity_type_name;
    
    -- Queue specific symbols or all symbols of the type
    IF symbol_list IS NOT NULL THEN
        -- Queue specific symbols
        FOR symbol_record IN
            SELECT s.symbol
            FROM symbols s
            WHERE s.symbol = ANY(symbol_list)
            AND s.active = true
        LOOP
            INSERT INTO equity_processing_queue (
                equity_type, symbol, processing_priority
            ) VALUES (
                equity_type_name, symbol_record.symbol, processing_priority
            )
            ON CONFLICT DO NOTHING;
            
            queued_count := queued_count + 1;
        END LOOP;
    ELSE
        -- Queue all symbols of the equity type
        FOR symbol_record IN
            SELECT s.symbol
            FROM symbols s
            WHERE s.type = equity_type_name
            AND s.active = true
        LOOP
            INSERT INTO equity_processing_queue (
                equity_type, symbol, processing_priority
            ) VALUES (
                equity_type_name, symbol_record.symbol, processing_priority
            )
            ON CONFLICT DO NOTHING;
            
            queued_count := queued_count + 1;
        END LOOP;
    END IF;
    
    RETURN queued_count;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================
-- PHASE 5: Grant Permissions
-- ==============================================================

-- Grant permissions to app_readwrite user
GRANT ALL PRIVILEGES ON TABLE equity_types TO app_readwrite;
GRANT ALL PRIVILEGES ON TABLE equity_processing_queue TO app_readwrite;
GRANT USAGE, SELECT ON SEQUENCE equity_types_id_seq TO app_readwrite;
GRANT USAGE, SELECT ON SEQUENCE equity_processing_queue_id_seq TO app_readwrite;

-- Grant function execution permissions
GRANT EXECUTE ON FUNCTION get_equity_processing_config(VARCHAR) TO app_readwrite;
GRANT EXECUTE ON FUNCTION get_symbols_for_processing(VARCHAR, INTEGER) TO app_readwrite;
GRANT EXECUTE ON FUNCTION update_processing_stats(VARCHAR, INTEGER, INTEGER, INTEGER) TO app_readwrite;
GRANT EXECUTE ON FUNCTION queue_symbols_for_processing(VARCHAR, TEXT[]) TO app_readwrite;

-- ==============================================================
-- PHASE 6: Verification Queries
-- ==============================================================

-- Verify equity types configuration
SELECT 
    type_name,
    update_frequency,
    priority_level,
    batch_size,
    requires_eod_validation,
    processing_rules->>'aum_required' as aum_required,
    additional_data_fields->>'batch_size' as configured_batch_size
FROM equity_types
ORDER BY priority_level DESC;

-- Test processing configuration function
SELECT get_equity_processing_config('ETF');

-- Show available symbols by equity type
SELECT 
    et.type_name,
    COUNT(s.symbol) as symbol_count,
    et.priority_level,
    et.batch_size
FROM equity_types et
LEFT JOIN symbols s ON s.type = et.type_name AND s.active = true
GROUP BY et.type_name, et.priority_level, et.batch_size
ORDER BY et.priority_level DESC;

-- Test queue management
SELECT queue_symbols_for_processing('ETF', ARRAY['SPY', 'QQQ', 'VTI']);

-- Verify processing queue
SELECT 
    equity_type,
    COUNT(*) as queued_symbols,
    AVG(processing_priority) as avg_priority
FROM equity_processing_queue
WHERE status = 'pending'
GROUP BY equity_type
ORDER BY avg_priority DESC;