-- Sprint 42 Phase 1 - Integration Validation Queries
-- Run these queries to validate TickStockPL TickAggregator is working

-- ============================================================================
-- Test 1: Verify OHLCV bars created (last 5 minutes)
-- Expected: 200-350 bars (5 minutes × 40-70 symbols)
-- ============================================================================

\echo '===================================================================='
\echo 'Test 1: OHLCV Bars Created (Last 5 Minutes)'
\echo '===================================================================='

SELECT COUNT(*) as total_bars
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '5 minutes';

\echo ''
\echo 'Bar distribution per minute:'

SELECT
    DATE_TRUNC('minute', timestamp) as minute,
    COUNT(DISTINCT symbol) as symbols_with_bars,
    COUNT(*) as total_bars
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY minute
ORDER BY minute DESC
LIMIT 10;

-- ============================================================================
-- Test 2: Check pattern detections
-- Expected: >0 patterns (if patterns exist in data)
-- ============================================================================

\echo ''
\echo '===================================================================='
\echo 'Test 2: Pattern Detections (Last 5 Minutes)'
\echo '===================================================================='

SELECT
    pattern_type,
    COUNT(*) as detections,
    ROUND(AVG(confidence)::numeric, 2) as avg_confidence
FROM intraday_patterns
WHERE detection_timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY pattern_type
ORDER BY detections DESC;

-- ============================================================================
-- Test 3: Check indicator calculations
-- Expected: >0 calculations
-- ============================================================================

\echo ''
\echo '===================================================================='
\echo 'Test 3: Indicator Calculations (Last 5 Minutes)'
\echo '===================================================================='

SELECT
    indicator_name,
    COUNT(*) as calculations
FROM intraday_indicators
WHERE calculation_timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY indicator_name
ORDER BY calculations DESC;

-- ============================================================================
-- Test 4: Verify NO duplicate bars
-- Expected: 0 rows
-- ============================================================================

\echo ''
\echo '===================================================================='
\echo 'Test 4: Duplicate Bars Check'
\echo '===================================================================='

SELECT
    symbol,
    timestamp,
    COUNT(*) as duplicate_count
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY symbol, timestamp
HAVING COUNT(*) > 1
LIMIT 10;

\echo ''
\echo 'If no rows returned above: PASS (no duplicates)'
\echo 'If rows returned: FAIL (duplicates found - investigate)'

-- ============================================================================
-- Test 5: Verify bar creation consistency
-- Expected: 4-5 minutes with data
-- ============================================================================

\echo ''
\echo '===================================================================='
\echo 'Test 5: Bar Creation Consistency'
\echo '===================================================================='

SELECT COUNT(*) as minutes_with_data
FROM (
    SELECT DATE_TRUNC('minute', timestamp) as minute
    FROM ohlcv_1min
    WHERE timestamp > NOW() - INTERVAL '5 minutes'
    GROUP BY minute
) subq;

\echo ''
\echo 'Expected: 4-5 minutes with data'

-- ============================================================================
-- Summary
-- ============================================================================

\echo ''
\echo '===================================================================='
\echo 'VALIDATION SUMMARY'
\echo '===================================================================='
\echo ''
\echo 'Phase 1 Success Criteria:'
\echo '  - Test 1: >= 200 bars created'
\echo '  - Test 2: Patterns detected (optional)'
\echo '  - Test 3: Indicators calculated (optional)'
\echo '  - Test 4: 0 duplicate bars (CRITICAL)'
\echo '  - Test 5: 4-5 minutes with data'
\echo ''
\echo 'If all critical tests pass: Proceed to Phase 2'
\echo 'If any fail: Review TickStockPL logs and retry'
\echo ''
