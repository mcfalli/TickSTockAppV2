-- Insert ETF Groups into cache_entries
-- Created: November 25, 2025
-- Purpose: Add core, sector, and equal-weight sector ETF groups

-- ============================================================================
-- 1. Core ETFs (3 symbols)
-- ============================================================================
INSERT INTO cache_entries (type, name, key, value, environment)
VALUES (
    'etf_universe',
    'Core ETFs',
    'etf_core',
    '["SPY", "QQQ", "IWM"]'::jsonb,
    'DEFAULT'
)
ON CONFLICT (type, name, key, environment) DO UPDATE
SET value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 2. Sector ETFs (21 symbols)
-- ============================================================================
INSERT INTO cache_entries (type, name, key, value, environment)
VALUES (
    'etf_universe',
    'Sector ETFs',
    'etf_sector',
    '[
        "XRT", "KRE", "GDX", "XHB", "XBI", "XTL", "IBB",
        "LABU", "KBE", "XLB", "XLV", "SMH", "XLF", "XLK",
        "XLE", "XLI", "XLP", "XME", "XOP", "XLY", "XLU"
    ]'::jsonb,
    'DEFAULT'
)
ON CONFLICT (type, name, key, environment) DO UPDATE
SET value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 3. Equal Weight Sector ETFs (12 symbols)
-- ============================================================================
INSERT INTO cache_entries (type, name, key, value, environment)
VALUES (
    'etf_universe',
    'Equal Weight Sectors',
    'etf_equal_weight_sectors',
    '[
        "RSPT", "RSPG", "RSPR", "RSP", "RSPS", "RSPU",
        "RSPC", "RSPD", "RSPH", "RSPF", "RSPM", "RSPN"
    ]'::jsonb,
    'DEFAULT'
)
ON CONFLICT (type, name, key, environment) DO UPDATE
SET value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 4. Combined Stock + ETF Group (all 36 symbols)
-- ============================================================================
INSERT INTO cache_entries (type, name, key, value, environment)
VALUES (
    'stock_etf_combo',
    'Stock ETF Group',
    'stock_etf_group',
    '[
        "SPY", "QQQ", "IWM",
        "XRT", "KRE", "GDX", "XHB", "XBI", "XTL", "IBB",
        "LABU", "KBE", "XLB", "XLV", "SMH", "XLF", "XLK",
        "XLE", "XLI", "XLP", "XME", "XOP", "XLY", "XLU",
        "RSPT", "RSPG", "RSPR", "RSP", "RSPS", "RSPU",
        "RSPC", "RSPD", "RSPH", "RSPF", "RSPM", "RSPN"
    ]'::jsonb,
    'DEFAULT'
)
ON CONFLICT (type, name, key, environment) DO UPDATE
SET value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Verify all 4 entries were created
SELECT
    type,
    name,
    key,
    jsonb_array_length(value) as symbol_count,
    value
FROM cache_entries
WHERE key IN ('etf_core', 'etf_sector', 'etf_equal_weight_sectors', 'stock_etf_group')
ORDER BY
    CASE
        WHEN key = 'etf_core' THEN 1
        WHEN key = 'etf_sector' THEN 2
        WHEN key = 'etf_equal_weight_sectors' THEN 3
        WHEN key = 'stock_etf_group' THEN 4
    END;

-- Count total symbols across all groups
SELECT
    'Total unique symbols' as description,
    COUNT(DISTINCT symbol) as count
FROM (
    SELECT jsonb_array_elements_text(value) as symbol
    FROM cache_entries
    WHERE key IN ('etf_core', 'etf_sector', 'etf_equal_weight_sectors')
) symbols;
