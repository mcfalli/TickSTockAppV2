-- Test 1 & 2 ONLY - Critical bar creation validation

-- Test 1: Total bars in last 5 minutes
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
ORDER BY minute DESC
LIMIT 10;
