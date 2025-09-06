-- Sprint 22 - Fix Function Parameter Name Conflict
-- Quick fix for calculate_pattern_success_rate function parameter naming issue

-- Drop and recreate the function with corrected parameter name
DROP FUNCTION IF EXISTS calculate_pattern_success_rate(VARCHAR, INTEGER);

-- Function to calculate real-time success rates (FIXED VERSION)
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

-- Grant execution permission
GRANT EXECUTE ON FUNCTION calculate_pattern_success_rate(VARCHAR, INTEGER) TO app_readwrite;

-- Test the fixed function
SELECT 'Function test:' as test_label;
SELECT * FROM calculate_pattern_success_rate('WeeklyBO', 30);

COMMIT;