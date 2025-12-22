-- Sprint 55: Cache Entries Audit and Cleanup
-- Date: 2025-11-26
-- Purpose: Fix data quality issues in cache_entries table
--
-- Issues identified:
-- 1. 20 entries with NULL updated_at timestamps (baseline: 2025-11-26)
-- 2. 4 entries with lowercase "complete" instead of Title Case "Complete"
--
-- References:
-- - docs/planning/sprints/sprint55/etf-universe-integration-and-cache-audit.md
-- - docs/database/cache_entries_audit_report_sprint55.md

-- =============================================================================
-- Issue #1: Set updated_at for entries with NULL timestamps
-- =============================================================================

-- First, identify affected entries
SELECT
    id,
    type,
    name,
    key,
    created_at,
    updated_at,
    CASE
        WHEN updated_at IS NULL THEN 'NEEDS UPDATE'
        ELSE 'OK'
    END as status
FROM cache_entries
WHERE updated_at IS NULL
ORDER BY created_at DESC;

-- Update: Set updated_at = created_at for all entries with NULL updated_at
UPDATE cache_entries
SET updated_at = created_at
WHERE updated_at IS NULL;

-- Verification query
SELECT
    COUNT(*) as total_entries,
    COUNT(*) FILTER (WHERE updated_at IS NULL) as still_missing_updated_at,
    COUNT(*) FILTER (WHERE updated_at IS NOT NULL) as has_updated_at
FROM cache_entries;
-- Expected: still_missing_updated_at = 0

-- =============================================================================
-- Issue #2: Rename "complete" to "Complete" for Title Case consistency
-- =============================================================================

-- Identify entries with lowercase "complete"
SELECT id, type, name, key
FROM cache_entries
WHERE name = 'complete'
ORDER BY type, id;

-- Update: Change lowercase "complete" to Title Case "Complete"
UPDATE cache_entries
SET name = 'Complete'
WHERE name = 'complete';

-- Verification query
SELECT
    COUNT(*) as total_complete_entries,
    COUNT(*) FILTER (WHERE name = 'complete') as lowercase_count,
    COUNT(*) FILTER (WHERE name = 'Complete') as titlecase_count
FROM cache_entries
WHERE LOWER(name) = 'complete';
-- Expected: lowercase_count = 0, titlecase_count > 0

-- =============================================================================
-- Issue #3 (Optional): Verify ETF universes are properly structured
-- =============================================================================

-- Check all ETF and stock_etf_combo universe entries
SELECT
    id,
    type,
    name,
    key,
    jsonb_typeof(value) as value_type,
    CASE
        WHEN jsonb_typeof(value) = 'array' THEN jsonb_array_length(value)
        WHEN jsonb_typeof(value) = 'object' AND value ? 'symbols' THEN jsonb_array_length(value->'symbols')
        ELSE 0
    END as symbol_count,
    created_at,
    updated_at
FROM cache_entries
WHERE type IN ('etf_universe', 'stock_etf_combo')
ORDER BY type, name;

-- =============================================================================
-- Final Verification: Comprehensive Data Quality Check
-- =============================================================================

SELECT
    'Cache Entries Quality Report' as report_title,
    COUNT(*) as total_entries,
    COUNT(*) FILTER (WHERE updated_at IS NULL) as missing_updated_at,
    COUNT(*) FILTER (WHERE name ~ '[a-z]' AND name !~ '^[A-Z]') as lowercase_names,
    COUNT(*) FILTER (WHERE type IN ('etf_universe', 'stock_etf_combo')) as etf_related_entries
FROM cache_entries;

-- Expected results after cleanup:
-- - total_entries: 290 (or current count)
-- - missing_updated_at: 0
-- - lowercase_names: 0
-- - etf_related_entries: 24

-- =============================================================================
-- Rollback Instructions (if needed)
-- =============================================================================

-- To rollback Issue #1 (updated_at changes):
-- UPDATE cache_entries
-- SET updated_at = NULL
-- WHERE id IN (SELECT id FROM ... WHERE updated_at was changed);
-- Note: Not recommended - better to keep updated_at set

-- To rollback Issue #2 (name changes):
-- UPDATE cache_entries
-- SET name = 'complete'
-- WHERE id IN (1328, 1329, 1330, 1331);

-- =============================================================================
-- Execution Notes
-- =============================================================================

-- To run this script:
-- psql -U app_readwrite -d tickstock -f scripts/sql/cache_entries_cleanup_sprint55.sql

-- Or via PGPASSWORD:
-- PGPASSWORD=your_password psql -U app_readwrite -h localhost -d tickstock -f scripts/sql/cache_entries_cleanup_sprint55.sql

-- Note: This script uses read-write user 'app_readwrite' because it performs UPDATE operations
-- The read-only user cannot execute UPDATE statements
