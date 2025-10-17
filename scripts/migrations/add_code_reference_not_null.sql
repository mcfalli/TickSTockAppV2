-- Migration: Add NOT NULL constraint to code_reference columns
-- Purpose: Prevent NULL values in code_reference which causes issues in application
-- Date: 2025-10-15
-- Author: Database Migration Script

-- This migration adds NOT NULL constraints to code_reference columns
-- in pattern_definitions and indicator_definitions tables.

BEGIN;

-- Step 1: Verify no NULL values exist before applying constraint
DO $$
DECLARE
    null_patterns INTEGER;
    null_indicators INTEGER;
BEGIN
    -- Check for NULL code_reference in pattern_definitions
    SELECT COUNT(*) INTO null_patterns
    FROM pattern_definitions
    WHERE code_reference IS NULL;

    -- Check for NULL code_reference in indicator_definitions
    SELECT COUNT(*) INTO null_indicators
    FROM indicator_definitions
    WHERE code_reference IS NULL;

    -- Report findings
    IF null_patterns > 0 THEN
        RAISE NOTICE 'WARNING: Found % rows with NULL code_reference in pattern_definitions', null_patterns;
        RAISE EXCEPTION 'Cannot apply NOT NULL constraint - pattern_definitions has NULL values';
    END IF;

    IF null_indicators > 0 THEN
        RAISE NOTICE 'WARNING: Found % rows with NULL code_reference in indicator_definitions', null_indicators;
        RAISE EXCEPTION 'Cannot apply NOT NULL constraint - indicator_definitions has NULL values';
    END IF;

    RAISE NOTICE 'Validation passed: No NULL code_reference values found';
END $$;

-- Step 2: Add NOT NULL constraint to pattern_definitions.code_reference
ALTER TABLE pattern_definitions
    ALTER COLUMN code_reference SET NOT NULL;

RAISE NOTICE 'Added NOT NULL constraint to pattern_definitions.code_reference';

-- Step 3: Add NOT NULL constraint to indicator_definitions.code_reference
ALTER TABLE indicator_definitions
    ALTER COLUMN code_reference SET NOT NULL;

RAISE NOTICE 'Added NOT NULL constraint to indicator_definitions.code_reference';

-- Step 4: Verify constraints were applied
DO $$
DECLARE
    pattern_nullable VARCHAR;
    indicator_nullable VARCHAR;
BEGIN
    -- Check pattern_definitions constraint
    SELECT is_nullable INTO pattern_nullable
    FROM information_schema.columns
    WHERE table_name = 'pattern_definitions'
    AND column_name = 'code_reference';

    -- Check indicator_definitions constraint
    SELECT is_nullable INTO indicator_nullable
    FROM information_schema.columns
    WHERE table_name = 'indicator_definitions'
    AND column_name = 'code_reference';

    IF pattern_nullable = 'NO' AND indicator_nullable = 'NO' THEN
        RAISE NOTICE 'SUCCESS: NOT NULL constraints applied successfully';
    ELSE
        RAISE EXCEPTION 'Constraint verification failed';
    END IF;
END $$;

COMMIT;

-- Summary
SELECT
    'pattern_definitions' as table_name,
    column_name,
    is_nullable,
    data_type
FROM information_schema.columns
WHERE table_name = 'pattern_definitions'
AND column_name = 'code_reference'

UNION ALL

SELECT
    'indicator_definitions' as table_name,
    column_name,
    is_nullable,
    data_type
FROM information_schema.columns
WHERE table_name = 'indicator_definitions'
AND column_name = 'code_reference';
