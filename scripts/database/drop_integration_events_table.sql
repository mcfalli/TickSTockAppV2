-- Sprint 32 Part 1: Remove Integration Events Table
-- Purpose: Drop the integration_events table and related database objects
-- This improves performance by eliminating 5-10ms latency per event
-- Created: 2025-09-25
--
-- IMPORTANT: Run this AFTER deploying the code changes that remove DatabaseIntegrationLogger
--
-- Execution Order:
-- 1. Deploy code without DatabaseIntegrationLogger references
-- 2. Verify application is running without errors
-- 3. Run this script to drop the database objects
-- 4. Verify removal with the verification queries at the bottom

-- Step 1: Drop the stored function (depends on the table)
DROP FUNCTION IF EXISTS log_integration_event CASCADE;

-- Step 2: Drop the view (depends on the table)
DROP VIEW IF EXISTS pattern_flow_analysis CASCADE;

-- Step 3: Drop the table
DROP TABLE IF EXISTS integration_events CASCADE;

-- Step 4: Verification Queries
-- Run these to confirm successful removal:

-- Check that table no longer exists
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name = 'integration_events'
) as table_still_exists;

-- Check that function no longer exists
SELECT EXISTS (
    SELECT FROM pg_proc
    WHERE proname = 'log_integration_event'
) as function_still_exists;

-- Check that view no longer exists
SELECT EXISTS (
    SELECT FROM information_schema.views
    WHERE table_schema = 'public'
    AND table_name = 'pattern_flow_analysis'
) as view_still_exists;

-- Expected results: All three queries should return 'false'

-- Optional: Archive the table before dropping (run this BEFORE the DROP commands above)
-- pg_dump -U postgres -d tickstock_dev -t integration_events > integration_events_backup_$(date +%Y%m%d).sql