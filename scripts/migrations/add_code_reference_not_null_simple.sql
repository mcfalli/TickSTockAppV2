-- Migration: Add NOT NULL constraint to code_reference columns
-- Purpose: Prevent NULL values in code_reference which causes issues in application
-- Date: 2025-10-15
-- Run with: psql -U postgres -d tickstock -f add_code_reference_not_null_simple.sql

-- Add NOT NULL constraint to pattern_definitions.code_reference
ALTER TABLE pattern_definitions
    ALTER COLUMN code_reference SET NOT NULL;

-- Add NOT NULL constraint to indicator_definitions.code_reference
ALTER TABLE indicator_definitions
    ALTER COLUMN code_reference SET NOT NULL;

-- Verify constraints were applied
SELECT
    table_name,
    column_name,
    is_nullable,
    data_type
FROM information_schema.columns
WHERE table_name IN ('pattern_definitions', 'indicator_definitions')
AND column_name = 'code_reference'
ORDER BY table_name;
