-- Clear symbols table for fresh start
-- This will force the historical loader to recreate all symbols with proper metadata

-- First, you may need to temporarily disable foreign key constraints
-- or delete dependent data first

-- Option 1: Delete all symbols (this may fail if there are foreign key references)
-- DELETE FROM symbols;

-- Option 2: Truncate table (faster, but may fail with foreign keys)
-- TRUNCATE TABLE symbols;

-- Option 3: Drop and recreate constraints temporarily (safest)
-- 1. Drop foreign key constraints
ALTER TABLE ohlcv_daily DROP CONSTRAINT IF EXISTS ohlcv_daily_symbol_fkey;
ALTER TABLE ohlcv_1min DROP CONSTRAINT IF EXISTS ohlcv_1min_symbol_fkey;
ALTER TABLE ticks DROP CONSTRAINT IF EXISTS ticks_symbol_fkey;
ALTER TABLE events DROP CONSTRAINT IF EXISTS events_symbol_fkey;

-- 2. Clear symbols table
TRUNCATE TABLE symbols;

-- 3. Recreate foreign key constraints
ALTER TABLE ohlcv_daily 
ADD CONSTRAINT ohlcv_daily_symbol_fkey 
FOREIGN KEY (symbol) REFERENCES symbols(symbol);

ALTER TABLE ohlcv_1min 
ADD CONSTRAINT ohlcv_1min_symbol_fkey 
FOREIGN KEY (symbol) REFERENCES symbols(symbol);

-- Only add these if the tables exist
-- ALTER TABLE ticks 
-- ADD CONSTRAINT ticks_symbol_fkey 
-- FOREIGN KEY (symbol) REFERENCES symbols(symbol);

-- ALTER TABLE events 
-- ADD CONSTRAINT events_symbol_fkey 
-- FOREIGN KEY (symbol) REFERENCES symbols(symbol);

-- Verify symbols table is empty
SELECT COUNT(*) as symbol_count FROM symbols;