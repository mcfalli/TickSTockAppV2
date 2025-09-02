-- =====================================================================
-- Script 1: Create symbols_related_tickers table
-- Purpose: Replace stock_related_tickers to align with symbols table
-- =====================================================================

-- Create symbols_related_tickers table to replace stock_related_tickers
CREATE TABLE IF NOT EXISTS symbols_related_tickers (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    related_symbol VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraint to symbols table
    CONSTRAINT fk_symbols_related_symbol 
        FOREIGN KEY (symbol) 
        REFERENCES symbols(symbol) 
        ON DELETE CASCADE,
        
    -- Unique constraint to prevent duplicates
    CONSTRAINT uk_symbols_related_tickers 
        UNIQUE (symbol, related_symbol)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_symbols_related_tickers_symbol 
    ON symbols_related_tickers(symbol);
CREATE INDEX IF NOT EXISTS idx_symbols_related_tickers_related_symbol 
    ON symbols_related_tickers(related_symbol);

-- Add comment
COMMENT ON TABLE symbols_related_tickers IS 
    'Stores related ticker relationships from Polygon API, aligned with symbols table structure';

-- Verify table creation
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'symbols_related_tickers' 
ORDER BY ordinal_position;

-- Check constraints
SELECT 
    constraint_name,
    constraint_type,
    table_name
FROM information_schema.table_constraints
WHERE table_name = 'symbols_related_tickers';

ANALYZE symbols_related_tickers;