-- TickStock Symbols Table Enhancement
-- Add additional columns from Polygon.io ticker data
-- Execute this SQL in pgAdmin connected to the 'tickstock' database

-- Add new columns to symbols table
ALTER TABLE symbols 
ADD COLUMN IF NOT EXISTS market VARCHAR(20),                    -- stocks, options, crypto, forex
ADD COLUMN IF NOT EXISTS locale VARCHAR(10),                    -- us, global
ADD COLUMN IF NOT EXISTS currency_name VARCHAR(10),             -- USD, EUR, etc.
ADD COLUMN IF NOT EXISTS currency_symbol VARCHAR(5),            -- $, €, etc.
ADD COLUMN IF NOT EXISTS type VARCHAR(20),                      -- CS = Common Stock, ADRC = ADR, etc.
ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT true,           -- is symbol actively traded
ADD COLUMN IF NOT EXISTS cik VARCHAR(20),                       -- SEC CIK identifier  
ADD COLUMN IF NOT EXISTS composite_figi VARCHAR(50),            -- Financial Instrument Global Identifier
ADD COLUMN IF NOT EXISTS share_class_figi VARCHAR(50),          -- Share class FIGI
ADD COLUMN IF NOT EXISTS last_updated_utc TIMESTAMP WITH TIME ZONE, -- more precise timestamp from API
ADD COLUMN IF NOT EXISTS market_cap BIGINT,                     -- market capitalization if available
ADD COLUMN IF NOT EXISTS weighted_shares_outstanding BIGINT;    -- shares outstanding

-- Add indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_symbols_market_active ON symbols (market, active);
CREATE INDEX IF NOT EXISTS idx_symbols_exchange_active ON symbols (exchange, active);  
CREATE INDEX IF NOT EXISTS idx_symbols_type_active ON symbols (type, active);
CREATE INDEX IF NOT EXISTS idx_symbols_last_updated ON symbols (last_updated_utc DESC);

-- Update existing records to set default values
UPDATE symbols 
SET 
    market = 'stocks',
    locale = 'us', 
    active = true,
    last_updated_utc = last_updated
WHERE market IS NULL;

-- Grant permissions to app_readwrite user
GRANT ALL PRIVILEGES ON TABLE symbols TO app_readwrite;

-- Verification query - run after ALTER to confirm changes
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'symbols' 
AND table_schema = 'public'
ORDER BY ordinal_position;