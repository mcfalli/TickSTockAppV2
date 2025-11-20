-- Quick Phase 3 Validation - Sprint 42
-- Check if TickStockPL TickAggregator is creating bars

-- Test 1: Recent OHLCV bars (last 5 minutes)
SELECT
    COUNT(*) as total_bars,
    COUNT(DISTINCT symbol) as unique_symbols,
    MIN(timestamp) as earliest,
    MAX(timestamp) as latest
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '5 minutes';

-- Test 2: Bar distribution by minute
SELECT
    DATE_TRUNC('minute', timestamp) as minute,
    COUNT(DISTINCT symbol) as symbols,
    COUNT(*) as bars
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY minute
ORDER BY minute DESC;

-- Test 3: Check for duplicates (should be 0)
SELECT COUNT(*) as duplicate_bar_count
FROM (
    SELECT symbol, timestamp, COUNT(*) as cnt
    FROM ohlcv_1min
    WHERE timestamp > NOW() - INTERVAL '10 minutes'
    GROUP BY symbol, timestamp
    HAVING COUNT(*) > 1
) subq;

-- Test 4: Recent patterns detected from bars
SELECT
    pattern_type,
    COUNT(*) as count,
    MAX(detection_timestamp) as latest
FROM intraday_patterns
WHERE detection_timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY pattern_type;

-- Test 5: Recent indicators calculated from bars
SELECT
    indicator_name,
    COUNT(*) as count,
    MAX(calculation_timestamp) as latest
FROM intraday_indicators
WHERE calculation_timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY indicator_name;
