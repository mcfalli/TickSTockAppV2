-- Check if TickStockPL streaming pipeline is working end-to-end

-- Step 1: Verify bars exist (we know this works - 220 bars)
SELECT
    COUNT(*) as total_bars,
    MIN(timestamp) as earliest,
    MAX(timestamp) as latest,
    COUNT(DISTINCT symbol) as symbols
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '10 minutes';

-- Step 2: Check if intraday_patterns table exists and has ANY data (ever)
SELECT COUNT(*) as total_patterns_ever
FROM intraday_patterns;

-- Step 3: Check if intraday_indicators table exists and has ANY data (ever)
SELECT COUNT(*) as total_indicators_ever
FROM intraday_indicators;

-- Step 4: Check for recent bars (last minute) - should have ~70
SELECT
    DATE_TRUNC('minute', timestamp) as minute,
    COUNT(*) as bars,
    COUNT(DISTINCT symbol) as symbols,
    STRING_AGG(DISTINCT symbol, ', ' ORDER BY symbol) as sample_symbols
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '2 minutes'
GROUP BY minute
ORDER BY minute DESC;

-- Step 5: Sample a few bars to see data quality
SELECT
    symbol,
    timestamp,
    open,
    high,
    low,
    close,
    volume
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '2 minutes'
ORDER BY timestamp DESC, symbol
LIMIT 5;
