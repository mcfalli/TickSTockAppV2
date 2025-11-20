-- Sprint 42 Phase 3 - Post-Implementation Validation
-- Purpose: Verify TickStockPL TickAggregator is the ONLY source of OHLCV bars
-- Expected: Bars created by TickStockPL, none by TickStockAppV2

\echo '======================================================================'
\echo 'Sprint 42 Phase 3 - Architectural Realignment Validation'
\echo '======================================================================'
\echo ''

-- ============================================================================
-- Test 1: Verify OHLCV bars are being created (last 10 minutes)
-- Expected: 400-700 bars (10 minutes × 40-70 symbols/minute)
-- ============================================================================

\echo '----------------------------------------------------------------------'
\echo 'Test 1: OHLCV Bar Creation (Last 10 Minutes)'
\echo '----------------------------------------------------------------------'

SELECT
    COUNT(*) as total_bars,
    COUNT(DISTINCT symbol) as unique_symbols,
    MIN(timestamp) as earliest_bar,
    MAX(timestamp) as latest_bar
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '10 minutes';

\echo ''
\echo 'Bar distribution per minute:'

SELECT
    DATE_TRUNC('minute', timestamp) as minute,
    COUNT(DISTINCT symbol) as symbols_with_bars,
    COUNT(*) as total_bars,
    ROUND(AVG(volume)::numeric, 0) as avg_volume
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY minute
ORDER BY minute DESC
LIMIT 10;

-- ============================================================================
-- Test 2: Verify NO duplicate bars (architectural violation check)
-- Expected: 0 rows (single source of truth enforced)
-- ============================================================================

\echo ''
\echo '----------------------------------------------------------------------'
\echo 'Test 2: Duplicate Bar Check (CRITICAL - Should be 0)'
\echo '----------------------------------------------------------------------'

SELECT
    symbol,
    timestamp,
    COUNT(*) as duplicate_count
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '30 minutes'
GROUP BY symbol, timestamp
HAVING COUNT(*) > 1
LIMIT 10;

\echo ''
\echo 'If no rows returned: PASS (single source of truth verified)'
\echo 'If rows returned: FAIL (multiple writers still active - investigate)'

-- ============================================================================
-- Test 3: Verify pattern detection triggered by bars
-- Expected: >0 patterns detected from intraday bars
-- ============================================================================

\echo ''
\echo '----------------------------------------------------------------------'
\echo 'Test 3: Pattern Detection from OHLCV Bars'
\echo '----------------------------------------------------------------------'

SELECT
    pattern_type,
    COUNT(*) as detections,
    ROUND(AVG(confidence)::numeric, 2) as avg_confidence,
    MAX(detection_timestamp) as latest_detection
FROM intraday_patterns
WHERE detection_timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY pattern_type
ORDER BY detections DESC;

\echo ''
\echo 'Note: 0 patterns is acceptable if market conditions do not trigger patterns'

-- ============================================================================
-- Test 4: Verify indicator calculations from bars
-- Expected: >0 calculations from intraday bars
-- ============================================================================

\echo ''
\echo '----------------------------------------------------------------------'
\echo 'Test 4: Indicator Calculations from OHLCV Bars'
\echo '----------------------------------------------------------------------'

SELECT
    indicator_name,
    COUNT(*) as calculations,
    COUNT(DISTINCT symbol) as symbols_calculated,
    MAX(calculation_timestamp) as latest_calculation
FROM intraday_indicators
WHERE calculation_timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY indicator_name
ORDER BY calculations DESC;

-- ============================================================================
-- Test 5: Bar creation consistency (should have data for most recent minutes)
-- Expected: 8-10 minutes with data (accounting for minute rollover)
-- ============================================================================

\echo ''
\echo '----------------------------------------------------------------------'
\echo 'Test 5: Bar Creation Consistency'
\echo '----------------------------------------------------------------------'

SELECT
    COUNT(*) as minutes_with_data,
    MIN(minute) as earliest_minute,
    MAX(minute) as latest_minute
FROM (
    SELECT DATE_TRUNC('minute', timestamp) as minute
    FROM ohlcv_1min
    WHERE timestamp > NOW() - INTERVAL '10 minutes'
    GROUP BY minute
) subq;

\echo ''
\echo 'Expected: 8-10 minutes with data'

-- ============================================================================
-- Test 6: Verify bar data quality (no null critical fields)
-- Expected: 0 bars with null OHLCV values
-- ============================================================================

\echo ''
\echo '----------------------------------------------------------------------'
\echo 'Test 6: Bar Data Quality Check'
\echo '----------------------------------------------------------------------'

SELECT
    COUNT(*) as bars_with_nulls,
    SUM(CASE WHEN open IS NULL THEN 1 ELSE 0 END) as null_open,
    SUM(CASE WHEN high IS NULL THEN 1 ELSE 0 END) as null_high,
    SUM(CASE WHEN low IS NULL THEN 1 ELSE 0 END) as null_low,
    SUM(CASE WHEN close IS NULL THEN 1 ELSE 0 END) as null_close,
    SUM(CASE WHEN volume IS NULL THEN 1 ELSE 0 END) as null_volume
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '10 minutes';

\echo ''
\echo 'Expected: All null counts = 0'

-- ============================================================================
-- SUMMARY
-- ============================================================================

\echo ''
\echo '======================================================================'
\echo 'SPRINT 42 PHASE 3 SUCCESS CRITERIA'
\echo '======================================================================'
\echo ''
\echo 'Phase 2 (TickStockAppV2 Changes):'
\echo '  [✓] OHLCVPersistenceService removed from AppV2'
\echo '  [✓] market_data_service.py updated (no persistence references)'
\echo '  [✓] Health endpoint updated (no persistence checks)'
\echo '  [✓] Application starts without errors'
\echo ''
\echo 'Phase 3 (Integration Validation):'
\echo '  Test 1: >= 400 bars created (CRITICAL)'
\echo '  Test 2: 0 duplicate bars (CRITICAL)'
\echo '  Test 3: Patterns detected (optional - data dependent)'
\echo '  Test 4: Indicators calculated (optional - data dependent)'
\echo '  Test 5: 8-10 minutes with data (CRITICAL)'
\echo '  Test 6: 0 bars with null values (CRITICAL)'
\echo ''
\echo 'If ALL critical tests pass:'
\echo '  → Sprint 42 Phase 2+3 COMPLETE'
\echo '  → Architectural realignment successful'
\echo '  → Ready to merge sprint42-remove-ohlcv-persistence to main'
\echo ''
\echo 'If ANY critical test fails:'
\echo '  → Review TickStockPL streaming logs'
\echo '  → Verify Redis channel: tickstock:market:ticks'
\echo '  → Check TickAggregator in TickStockPL'
\echo ''
\echo '======================================================================'
