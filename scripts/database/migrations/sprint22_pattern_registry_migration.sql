-- TickStock Pattern Registry System - Sprint 22 Phase 1
-- Database Migration for Dynamic Pattern Management
-- Execute in PGAdmin connected to 'tickstock' database

-- ==============================================================
-- PHASE 1: Pattern Registry Core Tables
-- ==============================================================

-- Core table for pattern definitions with dynamic control
CREATE TABLE IF NOT EXISTS pattern_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,                    -- e.g., 'WeeklyBO', 'DailyBO', 'Doji'
    short_description VARCHAR(255) NOT NULL,              -- Brief explanation
    long_description TEXT,                                -- Detailed explanation
    basic_logic_description TEXT,                         -- Logic if different from long description
    code_reference VARCHAR(255),                          -- Points to detection code/class
    category VARCHAR(50) DEFAULT 'pattern',               -- 'pattern', 'indicator', 'signal'
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    enabled BOOLEAN DEFAULT true NOT NULL,                -- CRITICAL: Dynamic on/off control
    display_order INTEGER DEFAULT 0,                      -- UI ordering
    confidence_threshold DECIMAL(3,2) DEFAULT 0.50,       -- Minimum confidence for display
    risk_level VARCHAR(20) DEFAULT 'medium',              -- 'low', 'medium', 'high'
    typical_success_rate DECIMAL(5,2),                    -- Historical average (e.g., 67.50%)
    created_by VARCHAR(100) DEFAULT 'system',
    
    CONSTRAINT check_confidence_range CHECK (confidence_threshold BETWEEN 0.0 AND 1.0),
    CONSTRAINT check_success_rate_range CHECK (typical_success_rate BETWEEN 0.0 AND 100.0),
    CONSTRAINT check_risk_level CHECK (risk_level IN ('low', 'medium', 'high'))
);

-- Pattern detection history for real analytics
CREATE TABLE IF NOT EXISTS pattern_detections (
    id BIGSERIAL PRIMARY KEY,
    pattern_id INTEGER REFERENCES pattern_definitions(id),
    symbol VARCHAR(10) NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    confidence DECIMAL(4,3) NOT NULL,
    price_at_detection DECIMAL(10,4),
    volume_at_detection BIGINT,
    pattern_data JSONB,                                   -- Additional pattern-specific data
    outcome_1d DECIMAL(6,3),                             -- 1-day return after detection
    outcome_5d DECIMAL(6,3),                             -- 5-day return after detection  
    outcome_30d DECIMAL(6,3),                            -- 30-day return after detection
    outcome_evaluated_at TIMESTAMP,
    
    CONSTRAINT check_confidence_range CHECK (confidence BETWEEN 0.0 AND 1.0)
);

-- ==============================================================
-- PHASE 2: Performance Indexes
-- ==============================================================

-- Indexes for performance on pattern_definitions
CREATE INDEX IF NOT EXISTS idx_pattern_definitions_enabled ON pattern_definitions(enabled);
CREATE INDEX IF NOT EXISTS idx_pattern_definitions_category ON pattern_definitions(category);
CREATE INDEX IF NOT EXISTS idx_pattern_definitions_display_order ON pattern_definitions(display_order);
CREATE INDEX IF NOT EXISTS idx_pattern_definitions_name ON pattern_definitions(name);

-- Indexes for analytics queries on pattern_detections
CREATE INDEX IF NOT EXISTS idx_pattern_detections_symbol_date ON pattern_detections(symbol, detected_at);
CREATE INDEX IF NOT EXISTS idx_pattern_detections_pattern_id ON pattern_detections(pattern_id);
CREATE INDEX IF NOT EXISTS idx_pattern_detections_detected_at ON pattern_detections(detected_at);

-- Composite index for success rate calculations
CREATE INDEX IF NOT EXISTS idx_pattern_detections_analytics ON pattern_detections 
(pattern_id, detected_at DESC, outcome_evaluated_at)
WHERE outcome_evaluated_at IS NOT NULL;

-- ==============================================================
-- PHASE 3: Initial Data Population
-- ==============================================================

-- Insert initial pattern definitions with comprehensive metadata
INSERT INTO pattern_definitions (name, short_description, long_description, basic_logic_description, code_reference, risk_level, typical_success_rate, display_order) VALUES
('WeeklyBO', 'Weekly Breakout Pattern', 'Price breaks above weekly resistance with strong volume confirmation', 'Price > weekly high AND volume > avg_volume * 1.5', 'event_detector.WeeklyBreakoutDetector', 'medium', 72.50, 1),
('DailyBO', 'Daily Breakout Pattern', 'Price breaks above daily resistance level', 'Price > daily high AND momentum > 0', 'event_detector.DailyBreakoutDetector', 'medium', 61.25, 2),
('Doji', 'Doji Candlestick Pattern', 'Indecision candle with equal open/close prices', 'ABS(open - close) < (high - low) * 0.1', 'pattern_detector.DojiDetector', 'low', 42.75, 3),
('Hammer', 'Hammer Reversal Pattern', 'Bullish reversal with long lower shadow', 'Lower shadow > 2 * body AND upper shadow < 0.5 * body', 'pattern_detector.HammerDetector', 'medium', 66.80, 4),
('EngulfingBullish', 'Bullish Engulfing Pattern', 'Large bullish candle engulfs previous bearish candle', 'Current body > previous body AND bullish engulfs bearish', 'pattern_detector.EngulfingDetector', 'high', 74.20, 5),
('ShootingStar', 'Shooting Star Pattern', 'Bearish reversal with long upper shadow', 'Upper shadow > 2 * body AND lower shadow < 0.5 * body', 'pattern_detector.ShootingStarDetector', 'medium', 52.10, 6),
('Support', 'Support Level Pattern', 'Price bounces off established support level', 'Price >= support_level * 0.98 AND previous_decline >= 2%', 'pattern_detector.SupportDetector', 'low', 58.40, 7),
('Resistance', 'Resistance Level Pattern', 'Price tests but fails to break resistance', 'Price <= resistance_level * 1.02 AND previous_advance >= 2%', 'pattern_detector.ResistanceDetector', 'low', 55.30, 8),
('Triangle', 'Triangle Consolidation', 'Price consolidates in converging triangle pattern', 'Range narrowing AND volume declining', 'pattern_detector.TriangleDetector', 'medium', 63.75, 9),
('VolumeSpike', 'Volume Spike Signal', 'Abnormally high volume suggests institutional interest', 'Volume > avg_volume * 3.0', 'signal_detector.VolumeDetector', 'medium', 69.20, 10)
ON CONFLICT (name) DO NOTHING;

-- ==============================================================
-- PHASE 4: Analytics Views and Functions
-- ==============================================================

-- Pattern summary view for dashboard queries
CREATE OR REPLACE VIEW v_pattern_summary AS
SELECT 
    id,
    name,
    short_description,
    category,
    enabled,
    typical_success_rate,
    confidence_threshold,
    risk_level,
    display_order,
    created_date,
    updated_date
FROM pattern_definitions 
ORDER BY display_order, name;

-- Enabled patterns view for API consumption
CREATE OR REPLACE VIEW v_enabled_patterns AS
SELECT 
    id,
    name,
    short_description,
    long_description,
    basic_logic_description,
    category,
    confidence_threshold,
    risk_level,
    typical_success_rate,
    display_order
FROM pattern_definitions 
WHERE enabled = true
ORDER BY display_order, name;

-- Pattern performance analytics view
CREATE OR REPLACE VIEW v_pattern_performance AS
SELECT 
    pd.id,
    pd.name,
    pd.short_description,
    pd.category,
    pd.typical_success_rate as historical_rate,
    COUNT(det.id) as total_detections,
    COUNT(CASE WHEN det.outcome_1d > 0 THEN 1 END) as positive_1d,
    COUNT(CASE WHEN det.outcome_5d > 0 THEN 1 END) as positive_5d,
    COUNT(CASE WHEN det.outcome_30d > 0 THEN 1 END) as positive_30d,
    CASE 
        WHEN COUNT(CASE WHEN det.outcome_1d IS NOT NULL THEN 1 END) > 0 
        THEN ROUND((COUNT(CASE WHEN det.outcome_1d > 0 THEN 1 END) * 100.0 / COUNT(CASE WHEN det.outcome_1d IS NOT NULL THEN 1 END)), 2)
        ELSE NULL 
    END as actual_success_rate_1d,
    AVG(det.confidence) as avg_confidence,
    MAX(det.detected_at) as last_detection
FROM pattern_definitions pd
LEFT JOIN pattern_detections det ON pd.id = det.pattern_id
WHERE pd.enabled = true
GROUP BY pd.id, pd.name, pd.short_description, pd.category, pd.typical_success_rate
ORDER BY pd.display_order;

-- ==============================================================
-- PHASE 5: Pattern Management Functions
-- ==============================================================

-- Function to toggle pattern enabled status
CREATE OR REPLACE FUNCTION toggle_pattern_enabled(pattern_name VARCHAR(100))
RETURNS BOOLEAN AS $$
DECLARE
    current_status BOOLEAN;
    new_status BOOLEAN;
BEGIN
    -- Get current status
    SELECT enabled INTO current_status
    FROM pattern_definitions 
    WHERE name = pattern_name;
    
    -- Return false if pattern not found
    IF current_status IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Toggle status
    new_status := NOT current_status;
    
    -- Update pattern
    UPDATE pattern_definitions 
    SET enabled = new_status, updated_date = CURRENT_TIMESTAMP
    WHERE name = pattern_name;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate real-time success rates
CREATE OR REPLACE FUNCTION calculate_pattern_success_rate(input_pattern_name VARCHAR(100), days_back INTEGER DEFAULT 30)
RETURNS TABLE (
    pattern_name VARCHAR(100),
    total_detections INTEGER,
    success_rate_1d DECIMAL(5,2),
    success_rate_5d DECIMAL(5,2),
    success_rate_30d DECIMAL(5,2),
    avg_confidence DECIMAL(4,3)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pd.name,
        COUNT(det.id)::INTEGER as total_detections,
        CASE 
            WHEN COUNT(CASE WHEN det.outcome_1d IS NOT NULL THEN 1 END) > 0 
            THEN ROUND((COUNT(CASE WHEN det.outcome_1d > 0 THEN 1 END) * 100.0 / COUNT(CASE WHEN det.outcome_1d IS NOT NULL THEN 1 END)), 2)
            ELSE NULL 
        END as success_rate_1d,
        CASE 
            WHEN COUNT(CASE WHEN det.outcome_5d IS NOT NULL THEN 1 END) > 0 
            THEN ROUND((COUNT(CASE WHEN det.outcome_5d > 0 THEN 1 END) * 100.0 / COUNT(CASE WHEN det.outcome_5d IS NOT NULL THEN 1 END)), 2)
            ELSE NULL 
        END as success_rate_5d,
        CASE 
            WHEN COUNT(CASE WHEN det.outcome_30d IS NOT NULL THEN 1 END) > 0 
            THEN ROUND((COUNT(CASE WHEN det.outcome_30d > 0 THEN 1 END) * 100.0 / COUNT(CASE WHEN det.outcome_30d IS NOT NULL THEN 1 END)), 2)
            ELSE NULL 
        END as success_rate_30d,
        ROUND(AVG(det.confidence), 3) as avg_confidence
    FROM pattern_definitions pd
    LEFT JOIN pattern_detections det ON pd.id = det.pattern_id
        AND det.detected_at >= CURRENT_TIMESTAMP - INTERVAL '1 day' * days_back
    WHERE pd.name = input_pattern_name
    GROUP BY pd.id, pd.name;
END;
$$ LANGUAGE plpgsql;

-- Function to get pattern distribution for analytics
CREATE OR REPLACE FUNCTION get_pattern_distribution(days_back INTEGER DEFAULT 7)
RETURNS TABLE (
    pattern_name VARCHAR(100),
    detection_count INTEGER,
    percentage DECIMAL(5,2)
) AS $$
BEGIN
    RETURN QUERY
    WITH pattern_counts AS (
        SELECT 
            pd.name,
            COUNT(det.id) as count
        FROM pattern_definitions pd
        LEFT JOIN pattern_detections det ON pd.id = det.pattern_id
            AND det.detected_at >= CURRENT_TIMESTAMP - INTERVAL '1 day' * days_back
        WHERE pd.enabled = true
        GROUP BY pd.id, pd.name
    ),
    total_count AS (
        SELECT SUM(count) as total FROM pattern_counts
    )
    SELECT 
        pc.name,
        pc.count::INTEGER,
        CASE 
            WHEN tc.total > 0 
            THEN ROUND((pc.count * 100.0 / tc.total), 2)
            ELSE 0.0 
        END as percentage
    FROM pattern_counts pc, total_count tc
    ORDER BY pc.count DESC;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================
-- PHASE 6: Pattern Configuration Triggers
-- ==============================================================

-- Trigger to update updated_date on pattern changes
CREATE OR REPLACE FUNCTION update_pattern_updated_date()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_date = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_pattern_definitions_updated_date
    BEFORE UPDATE ON pattern_definitions
    FOR EACH ROW
    EXECUTE FUNCTION update_pattern_updated_date();

-- ==============================================================
-- PHASE 7: Grant Permissions
-- ==============================================================

-- Grant permissions to app_readwrite user for all new structures
GRANT ALL PRIVILEGES ON TABLE pattern_definitions TO app_readwrite;
GRANT ALL PRIVILEGES ON TABLE pattern_detections TO app_readwrite;
GRANT ALL PRIVILEGES ON SEQUENCE pattern_definitions_id_seq TO app_readwrite;
GRANT ALL PRIVILEGES ON SEQUENCE pattern_detections_id_seq TO app_readwrite;

-- Grant access to views
GRANT SELECT ON v_pattern_summary TO app_readwrite;
GRANT SELECT ON v_enabled_patterns TO app_readwrite;
GRANT SELECT ON v_pattern_performance TO app_readwrite;

-- Grant function execution
GRANT EXECUTE ON FUNCTION toggle_pattern_enabled(VARCHAR) TO app_readwrite;
GRANT EXECUTE ON FUNCTION calculate_pattern_success_rate(VARCHAR, INTEGER) TO app_readwrite;
GRANT EXECUTE ON FUNCTION get_pattern_distribution(INTEGER) TO app_readwrite;

-- ==============================================================
-- PHASE 8: Verification Queries
-- ==============================================================

-- Verify pattern_definitions table exists and has correct structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'pattern_definitions' 
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- Verify pattern_detections table exists
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'pattern_detections' 
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- Verify indexes were created
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename IN ('pattern_definitions', 'pattern_detections')
ORDER BY tablename, indexname;

-- Verify views exist
SELECT 
    viewname, 
    definition 
FROM pg_views 
WHERE schemaname = 'public' 
  AND viewname LIKE 'v_pattern%'
ORDER BY viewname;

-- Verify functions exist
SELECT 
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name LIKE '%pattern%'
ORDER BY routine_name;

-- Display initial pattern data
SELECT 
    id,
    name, 
    short_description,
    category,
    enabled,
    typical_success_rate,
    risk_level,
    display_order
FROM pattern_definitions 
ORDER BY display_order;

-- Test pattern management functions
SELECT * FROM calculate_pattern_success_rate('WeeklyBO', 30);
SELECT * FROM get_pattern_distribution(7);

-- ==============================================================
-- Migration Complete - Sprint 22 Phase 1
-- ==============================================================

-- This migration provides:
-- 1. ✅ Pattern Registry Database Table (pattern_definitions)
-- 2. ✅ Pattern Detection History Table (pattern_detections) 
-- 3. ✅ Performance Indexes for <100ms queries
-- 4. ✅ Initial data with 10 comprehensive patterns
-- 5. ✅ Analytics views and functions for real-time calculations
-- 6. ✅ Pattern management functions (toggle, success rates, distribution)
-- 7. ✅ Proper permissions for app_readwrite user
-- 8. ✅ Verification queries to ensure successful migration

COMMIT;