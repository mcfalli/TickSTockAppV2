-- Sprint 23: Test Data Population Script
-- Creates realistic pattern detection data for testing analytical functions
-- Execute in PGAdmin connected to 'tickstock' database

-- ==============================================================
-- Test Data Population for Sprint 23 Analytics Testing
-- ==============================================================

-- Clear existing test data (if any)
DELETE FROM pattern_detections WHERE detected_at >= CURRENT_TIMESTAMP - INTERVAL '90 days';
DELETE FROM daily_patterns WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '90 days';

-- ==============================================================
-- 1. Generate Realistic Pattern Detection Data
-- ==============================================================

-- Create a temporary function to generate test data
CREATE OR REPLACE FUNCTION generate_sprint23_test_data()
RETURNS TEXT AS $$
DECLARE
    pattern_record RECORD;
    symbol_list TEXT[] := ARRAY['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD', 'NFLX', 'CRM', 'ORCL', 'INTC', 'PYPL', 'DIS', 'UBER'];
    symbol_name TEXT;
    detection_date TIMESTAMP;
    i INTEGER;
    j INTEGER;
    confidence_val DECIMAL(4,3);
    outcome_1d DECIMAL(6,3);
    outcome_5d DECIMAL(6,3);
    outcome_30d DECIMAL(6,3);
    base_success_rate DECIMAL(3,2);
    detections_inserted INTEGER := 0;
BEGIN
    -- Get active pattern definitions
    FOR pattern_record IN 
        SELECT id, name, confidence_threshold FROM pattern_definitions WHERE enabled = true
    LOOP
        -- Set different success rates for different patterns (realistic)
        CASE pattern_record.name
            WHEN 'WeeklyBO' THEN base_success_rate := 0.65;
            WHEN 'DailyBO' THEN base_success_rate := 0.58;
            WHEN 'Doji' THEN base_success_rate := 0.52;
            WHEN 'Hammer' THEN base_success_rate := 0.61;
            WHEN 'EngulfingBull' THEN base_success_rate := 0.69;
            WHEN 'EngulfingBear' THEN base_success_rate := 0.63;
            WHEN 'MorningStar' THEN base_success_rate := 0.71;
            WHEN 'EveningStar' THEN base_success_rate := 0.67;
            ELSE base_success_rate := 0.55;
        END CASE;

        -- Generate detections for each symbol over last 60 days
        FOREACH symbol_name IN ARRAY symbol_list
        LOOP
            -- Generate 2-8 detections per symbol per pattern (realistic frequency)
            FOR i IN 1..(2 + FLOOR(RANDOM() * 7))
            LOOP
                -- Random detection time in last 60 days (business hours)
                detection_date := CURRENT_TIMESTAMP - (RANDOM() * INTERVAL '60 days');
                detection_date := detection_date + INTERVAL '9 hours' + (RANDOM() * INTERVAL '7 hours');
                
                -- Skip weekends (make it realistic)
                IF EXTRACT(dow FROM detection_date) IN (0, 6) THEN
                    CONTINUE;
                END IF;
                
                -- Generate realistic confidence (higher than threshold)
                confidence_val := pattern_record.confidence_threshold + (RANDOM() * (1.0 - pattern_record.confidence_threshold));
                
                -- Generate outcomes based on pattern success rate with some variance
                IF RANDOM() < base_success_rate THEN
                    -- Successful pattern
                    outcome_1d := 0.005 + (RANDOM() * 0.045);  -- 0.5% to 5% gain
                    outcome_5d := outcome_1d * (1.2 + RANDOM() * 0.8);  -- Compound effect
                    outcome_30d := outcome_5d * (0.8 + RANDOM() * 1.4);  -- More variance over time
                ELSE
                    -- Failed pattern
                    outcome_1d := -0.002 - (RANDOM() * 0.025);  -- -0.2% to -2.7% loss
                    outcome_5d := outcome_1d * (1.1 + RANDOM() * 0.6);  -- Losses can compound too
                    outcome_30d := outcome_5d * (0.7 + RANDOM() * 1.2);  -- Recovery possible over time
                END IF;
                
                -- Insert pattern detection
                INSERT INTO pattern_detections (
                    pattern_id, symbol, detected_at, confidence, 
                    price_at_detection, volume_at_detection,
                    outcome_1d, outcome_5d, outcome_30d, outcome_evaluated_at,
                    pattern_data
                ) VALUES (
                    pattern_record.id, 
                    symbol_name, 
                    detection_date, 
                    confidence_val,
                    100.0 + (RANDOM() * 300.0), -- Random stock price $100-400
                    1000000 + (RANDOM() * 5000000)::BIGINT, -- Random volume 1M-6M
                    outcome_1d,
                    outcome_5d, 
                    outcome_30d,
                    detection_date + INTERVAL '30 days',
                    jsonb_build_object(
                        'pattern_strength', confidence_val,
                        'market_condition', CASE 
                            WHEN RANDOM() < 0.3 THEN 'bull'
                            WHEN RANDOM() < 0.6 THEN 'bear' 
                            ELSE 'neutral' 
                        END,
                        'volume_spike', RANDOM() < 0.2
                    )
                );
                
                detections_inserted := detections_inserted + 1;
            END LOOP;
        END LOOP;
    END LOOP;
    
    RETURN FORMAT('Generated %s realistic pattern detections for testing', detections_inserted);
END;
$$ LANGUAGE plpgsql;

-- Execute the test data generation
SELECT generate_sprint23_test_data();

-- Clean up the temporary function
DROP FUNCTION generate_sprint23_test_data();

-- ==============================================================
-- 2. Populate daily_patterns table (if needed by functions)
-- ==============================================================

-- Insert into daily_patterns based on pattern_detections
INSERT INTO daily_patterns (pattern_name, symbol, timestamp, outcome_1d, outcome_5d, confidence, volume)
SELECT 
    pd_def.name,
    det.symbol,
    det.detected_at,
    det.outcome_1d,
    det.outcome_5d,
    det.confidence,
    det.volume_at_detection
FROM pattern_detections det
JOIN pattern_definitions pd_def ON det.pattern_id = pd_def.id
WHERE det.detected_at >= CURRENT_TIMESTAMP - INTERVAL '90 days';

-- ==============================================================
-- 3. Add Market Conditions Data
-- ==============================================================

-- Generate market conditions data for correlation analysis
INSERT INTO market_conditions (timestamp, condition_type, condition_value, created_at)
SELECT 
    day_timestamp,
    'volatility',
    CASE 
        WHEN RANDOM() < 0.2 THEN 'high'
        WHEN RANDOM() < 0.7 THEN 'medium'
        ELSE 'low'
    END,
    CURRENT_TIMESTAMP
FROM generate_series(
    CURRENT_TIMESTAMP - INTERVAL '60 days',
    CURRENT_TIMESTAMP,
    INTERVAL '1 day'
) day_timestamp
WHERE EXTRACT(dow FROM day_timestamp) BETWEEN 1 AND 5;

-- Add trend market conditions
INSERT INTO market_conditions (timestamp, condition_type, condition_value, created_at)
SELECT 
    day_timestamp,
    'trend',
    CASE 
        WHEN RANDOM() < 0.35 THEN 'bullish'
        WHEN RANDOM() < 0.7 THEN 'bearish'
        ELSE 'sideways'
    END,
    CURRENT_TIMESTAMP
FROM generate_series(
    CURRENT_TIMESTAMP - INTERVAL '60 days',
    CURRENT_TIMESTAMP,
    INTERVAL '1 day'
) day_timestamp
WHERE EXTRACT(dow FROM day_timestamp) BETWEEN 1 AND 5;

-- Add volume conditions
INSERT INTO market_conditions (timestamp, condition_type, condition_value, created_at)
SELECT 
    day_timestamp,
    'volume',
    CASE 
        WHEN RANDOM() < 0.25 THEN 'high'
        WHEN RANDOM() < 0.75 THEN 'normal'
        ELSE 'low'
    END,
    CURRENT_TIMESTAMP
FROM generate_series(
    CURRENT_TIMESTAMP - INTERVAL '60 days',
    CURRENT_TIMESTAMP,
    INTERVAL '1 day'
) day_timestamp
WHERE EXTRACT(dow FROM day_timestamp) BETWEEN 1 AND 5;

-- ==============================================================
-- 4. Test Database Functions with Real Data
-- ==============================================================

-- Test pattern correlations function
SELECT 'Testing pattern correlations function...' as test_step;
SELECT * FROM calculate_pattern_correlations(30, 0.1) LIMIT 5;

-- Test advanced pattern metrics
SELECT 'Testing advanced pattern metrics function...' as test_step;  
SELECT * FROM calculate_advanced_pattern_metrics('WeeklyBO') LIMIT 1;

-- Test temporal analysis
SELECT 'Testing temporal analysis function...' as test_step;
SELECT * FROM analyze_temporal_performance('WeeklyBO', 'hourly', 30) LIMIT 5;

-- Test market context analysis
SELECT 'Testing market context analysis function...' as test_step;
SELECT * FROM analyze_pattern_market_context('WeeklyBO', 30) LIMIT 5;

-- Test pattern comparison
SELECT 'Testing pattern comparison function...' as test_step;
SELECT * FROM compare_pattern_performance('WeeklyBO', 'DailyBO') LIMIT 1;

-- ==============================================================
-- 5. Populate Cache Tables with Real Data
-- ==============================================================

-- Refresh all cache tables with the new test data
SELECT 'Refreshing correlation cache...' as cache_step;
SELECT refresh_correlations_cache() as correlations_refreshed;

SELECT 'Refreshing temporal cache...' as cache_step;
SELECT refresh_temporal_cache() as temporal_refreshed;

SELECT 'Refreshing advanced metrics cache...' as cache_step;  
SELECT refresh_advanced_metrics_cache() as advanced_refreshed;

SELECT 'Refreshing materialized views...' as cache_step;
SELECT refresh_analytics_views() as views_refreshed;

-- ==============================================================
-- 6. Validation and Performance Testing
-- ==============================================================

-- Verify data was populated correctly
SELECT 'Data Population Summary:' as summary_step;

SELECT 
    'Pattern Detections' as table_name,
    COUNT(*) as record_count,
    MIN(detected_at) as earliest_detection,
    MAX(detected_at) as latest_detection,
    COUNT(DISTINCT symbol) as unique_symbols,
    COUNT(DISTINCT pattern_id) as unique_patterns
FROM pattern_detections;

SELECT 
    'Daily Patterns' as table_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT pattern_name) as unique_patterns,
    COUNT(DISTINCT symbol) as unique_symbols
FROM daily_patterns;

SELECT 
    'Market Conditions' as table_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT condition_type) as condition_types,
    MIN(timestamp) as earliest_date,
    MAX(timestamp) as latest_date
FROM market_conditions;

-- Test cache table population
SELECT 'Cache Tables Population:' as cache_summary;

SELECT 
    'Correlations Cache' as cache_table,
    COUNT(*) as records,
    COUNT(*) FILTER (WHERE valid_until > CURRENT_TIMESTAMP) as valid_records
FROM pattern_correlations_cache;

SELECT 
    'Temporal Cache' as cache_table,
    COUNT(*) as records, 
    COUNT(*) FILTER (WHERE valid_until > CURRENT_TIMESTAMP) as valid_records
FROM temporal_performance_cache;

SELECT 
    'Advanced Metrics Cache' as cache_table,
    COUNT(*) as records,
    COUNT(*) FILTER (WHERE valid_until > CURRENT_TIMESTAMP) as valid_records
FROM advanced_metrics_cache;

-- Test performance of key queries
\timing on
SELECT 'Performance Test: Pattern Correlations' as test_name;
SELECT * FROM calculate_pattern_correlations(30, 0.3) LIMIT 10;

SELECT 'Performance Test: Top Performing Patterns' as test_name;
SELECT * FROM mv_active_patterns_summary ORDER BY success_rate_30d DESC LIMIT 10;

SELECT 'Performance Test: Cached Correlations' as test_name;
SELECT * FROM pattern_correlations_cache WHERE ABS(correlation_coefficient) > 0.5 LIMIT 10;
\timing off

-- Display success rates by pattern
SELECT 'Pattern Success Rates from Test Data:' as results_summary;
SELECT 
    pd.name as pattern_name,
    COUNT(det.id) as total_detections,
    COUNT(det.id) FILTER (WHERE det.outcome_1d > 0) as successful_outcomes,
    ROUND(
        (COUNT(det.id) FILTER (WHERE det.outcome_1d > 0) * 100.0 / COUNT(det.id))::numeric, 2
    ) as success_rate_percent,
    ROUND(AVG(det.outcome_1d)::numeric, 4) as avg_return_1d,
    ROUND(AVG(det.confidence)::numeric, 3) as avg_confidence
FROM pattern_definitions pd
LEFT JOIN pattern_detections det ON pd.id = det.pattern_id
WHERE pd.enabled = true
  AND det.detected_at IS NOT NULL
GROUP BY pd.id, pd.name
ORDER BY success_rate_percent DESC;

-- ==============================================================
-- Test Data Population Complete
-- ==============================================================

SELECT 'Sprint 23 Test Data Population Complete!' as completion_status;
SELECT FORMAT(
    'Ready for Phase 1.2: Database functions now have %s pattern detections across %s patterns and %s symbols for realistic testing.',
    (SELECT COUNT(*) FROM pattern_detections),
    (SELECT COUNT(DISTINCT pattern_id) FROM pattern_detections), 
    (SELECT COUNT(DISTINCT symbol) FROM pattern_detections)
) as summary_message;

COMMIT;