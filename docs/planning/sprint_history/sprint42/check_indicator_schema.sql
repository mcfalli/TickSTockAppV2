-- Check intraday_indicators table schema and existence

-- Test A: Check if table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name = 'intraday_indicators'
) as table_exists;

-- Test B: If exists, show column names
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'intraday_indicators'
ORDER BY ordinal_position;

-- Test C: Count total indicators (any time)
SELECT COUNT(*) as total_indicators
FROM intraday_indicators;

-- Test D: Show sample row structure
SELECT *
FROM intraday_indicators
ORDER BY id DESC
LIMIT 1;
