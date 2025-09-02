-- =====================================================================
-- Script 2: Add SIC code and sector/industry fields to symbols table
-- Purpose: Enable sector/industry classification using SIC codes from Polygon API
-- =====================================================================

-- Add SIC code and classification fields to symbols table
ALTER TABLE symbols 
ADD COLUMN IF NOT EXISTS sic_code VARCHAR(10),
ADD COLUMN IF NOT EXISTS sic_description TEXT,
ADD COLUMN IF NOT EXISTS sector VARCHAR(50),
ADD COLUMN IF NOT EXISTS industry VARCHAR(100),
ADD COLUMN IF NOT EXISTS country VARCHAR(5) DEFAULT 'US',
ADD COLUMN IF NOT EXISTS total_employees INTEGER,
ADD COLUMN IF NOT EXISTS list_date DATE,
ADD COLUMN IF NOT EXISTS sic_updated_at TIMESTAMP;

-- Create indexes for performance on new classification fields
CREATE INDEX IF NOT EXISTS idx_symbols_sic_code 
    ON symbols(sic_code) WHERE sic_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_symbols_sector 
    ON symbols(sector) WHERE sector IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_symbols_industry 
    ON symbols(industry) WHERE industry IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_symbols_country 
    ON symbols(country);

-- Create composite index for sector/industry queries
CREATE INDEX IF NOT EXISTS idx_symbols_sector_industry 
    ON symbols(sector, industry) WHERE sector IS NOT NULL AND industry IS NOT NULL;

-- Create composite index for market cap + sector analysis
CREATE INDEX IF NOT EXISTS idx_symbols_market_cap_sector 
    ON symbols(market_cap DESC, sector) WHERE active = true AND type = 'CS' AND market_cap IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN symbols.sic_code IS 
    'SIC (Standard Industrial Classification) code from Polygon API for sector/industry mapping';
COMMENT ON COLUMN symbols.sic_description IS 
    'Human readable description of the SIC code classification';
COMMENT ON COLUMN symbols.sector IS 
    'Primary business sector derived from SIC code (Technology, Healthcare, Financial Services, etc.)';
COMMENT ON COLUMN symbols.industry IS 
    'Specific industry classification within the sector';
COMMENT ON COLUMN symbols.country IS 
    'Country of incorporation, defaults to US for US market stocks';
COMMENT ON COLUMN symbols.total_employees IS 
    'Total number of employees reported by the company';
COMMENT ON COLUMN symbols.list_date IS 
    'Date when the stock was first listed on the exchange';
COMMENT ON COLUMN symbols.sic_updated_at IS 
    'Timestamp when SIC data was last updated from Polygon API';

-- Verify the new columns were added successfully
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'symbols' 
  AND column_name IN ('sic_code', 'sic_description', 'sector', 'industry', 'country', 'total_employees', 'list_date', 'sic_updated_at')
ORDER BY ordinal_position;

-- Check current symbols count and new field status
SELECT 
    COUNT(*) as total_symbols,
    COUNT(sic_code) as symbols_with_sic,
    COUNT(sector) as symbols_with_sector,
    COUNT(industry) as symbols_with_industry,
    COUNT(CASE WHEN active = true AND type = 'CS' THEN 1 END) as active_stocks
FROM symbols;

ANALYZE symbols;