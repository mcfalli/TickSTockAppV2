-- Test 5: Fixed - Recent indicators calculated from bars
SELECT
    indicator_type,  -- Fixed: was indicator_name
    COUNT(*) as count,
    MAX(calculation_timestamp) as latest
FROM intraday_indicators
WHERE calculation_timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY indicator_type;
