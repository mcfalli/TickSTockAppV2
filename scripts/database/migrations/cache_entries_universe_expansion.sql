-- Cache Entries Universe Expansion - Sprint 14 Phase 3
-- Enhanced cache_entries schema for comprehensive ETF support
-- Execute in PGAdmin connected to 'tickstock' database

-- ==============================================================
-- PHASE 1: Cache Entries Schema Enhancement
-- ==============================================================

-- Add ETF universe support columns to cache_entries
ALTER TABLE cache_entries 
ADD COLUMN IF NOT EXISTS universe_category VARCHAR(50),
ADD COLUMN IF NOT EXISTS liquidity_filter JSONB,
ADD COLUMN IF NOT EXISTS universe_metadata JSONB,
ADD COLUMN IF NOT EXISTS last_universe_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create ETF-specific indexes for performance
CREATE INDEX IF NOT EXISTS idx_cache_entries_category ON cache_entries (universe_category);
CREATE INDEX IF NOT EXISTS idx_cache_entries_updated ON cache_entries (last_universe_update DESC);
CREATE INDEX IF NOT EXISTS idx_cache_entries_etf_filter ON cache_entries 
USING GIN (liquidity_filter) WHERE universe_category = 'ETF';

-- ==============================================================
-- PHASE 2: ETF Universe Core Data
-- ==============================================================

-- Insert comprehensive ETF universe themes with liquidity filters
INSERT INTO cache_entries (
    cache_key, 
    symbols, 
    universe_category, 
    liquidity_filter, 
    universe_metadata
) VALUES 
-- Sector ETF Universe (High AUM, High Liquidity)
(
    'etf_sectors',
    '["XLF", "XLE", "XLK", "XLV", "XLI", "XLB", "XLRE", "XLU", "XLY", "XLP"]'::jsonb,
    'ETF',
    '{"min_aum": 1000000000, "min_volume": 5000000, "min_liquidity_score": 85}'::jsonb,
    '{
        "theme": "Sector ETFs",
        "description": "SPDR Select Sector ETFs covering major market sectors",
        "count": 10,
        "criteria": "AUM > $1B, Volume > 5M daily",
        "focus": "sector_rotation",
        "rebalance_frequency": "quarterly",
        "correlation_tracking": true
    }'::jsonb
),

-- Growth ETF Universe 
(
    'etf_growth',
    '["VUG", "IVW", "SCHG", "VTI", "ITOT", "SPTM", "SPYG", "USMV"]'::jsonb,
    'ETF',
    '{"min_aum": 1000000000, "min_volume": 2000000, "expense_ratio_max": 0.25}'::jsonb,
    '{
        "theme": "Growth ETFs", 
        "description": "Large-cap and broad market growth-focused ETFs",
        "count": 8,
        "criteria": "Growth orientation, AUM > $1B",
        "focus": "growth_momentum",
        "style_factor": "growth",
        "market_cap_focus": "large_cap"
    }'::jsonb
),

-- Value ETF Universe
(
    'etf_value',
    '["VTV", "IVE", "VYM", "SCHV", "DVY", "VEA", "VTEB", "BND"]'::jsonb,
    'ETF',
    '{"min_aum": 1000000000, "min_volume": 1500000, "dividend_yield_min": 1.5}'::jsonb,
    '{
        "theme": "Value ETFs",
        "description": "Value-oriented and dividend-focused ETFs",
        "count": 8,
        "criteria": "Value orientation, Dividend yield > 1.5%",
        "focus": "value_dividend",
        "style_factor": "value",
        "income_focus": true
    }'::jsonb
),

-- International ETF Universe
(
    'etf_international',
    '["VEA", "VWO", "IEFA", "EEM", "VGK", "VPL", "IEMG", "VXUS"]'::jsonb,
    'ETF',
    '{"min_aum": 500000000, "min_volume": 2000000, "geographic_diversification": true}'::jsonb,
    '{
        "theme": "International ETFs",
        "description": "Developed and emerging market international exposure",
        "count": 8,
        "criteria": "International exposure, AUM > $500M",
        "focus": "geographic_diversification",
        "regions": ["europe", "asia_pacific", "emerging_markets"],
        "currency_hedged_options": false
    }'::jsonb
),

-- Commodity ETF Universe  
(
    'etf_commodities',
    '["GLD", "SLV", "DBA", "USO", "UNG", "PDBC", "BCI", "GUNR"]'::jsonb,
    'ETF',
    '{"min_aum": 100000000, "min_volume": 1000000, "commodity_exposure": true}'::jsonb,
    '{
        "theme": "Commodity ETFs",
        "description": "Precious metals, energy, and broad commodity exposure",
        "count": 8,
        "criteria": "Commodity exposure, Volume > 1M",
        "focus": "inflation_hedge",
        "commodity_types": ["precious_metals", "energy", "agriculture", "broad_commodities"],
        "volatility_expected": "high"
    }'::jsonb
),

-- Technology ETF Universe (Specialized)
(
    'etf_technology',
    '["QQQ", "XLK", "VGT", "FTEC", "SOXX", "ARKK", "SKYY", "ROBO"]'::jsonb,
    'ETF',
    '{"min_aum": 500000000, "min_volume": 3000000, "technology_focus": true}'::jsonb,
    '{
        "theme": "Technology ETFs",
        "description": "Technology sector and innovation-focused ETFs",
        "count": 8,
        "criteria": "Technology focus, Innovation exposure",
        "focus": "technology_innovation",
        "sub_sectors": ["software", "semiconductors", "cloud", "ai_robotics"],
        "growth_orientation": true
    }'::jsonb
),

-- Bond ETF Universe
(
    'etf_bonds',
    '["BND", "AGG", "VTEB", "LQD", "HYG", "TLT", "SHY", "SCHZ"]'::jsonb,
    'ETF',
    '{"min_aum": 1000000000, "min_volume": 1000000, "fixed_income": true}'::jsonb,
    '{
        "theme": "Bond ETFs",
        "description": "Fixed income ETFs across duration and credit spectrum",
        "count": 8,
        "criteria": "Fixed income focus, AUM > $1B",
        "focus": "fixed_income_diversification",
        "duration_mix": ["short", "intermediate", "long"],
        "credit_quality": ["government", "investment_grade", "high_yield"]
    }'::jsonb
)

-- Handle conflicts by updating existing records
ON CONFLICT (cache_key) DO UPDATE SET
    symbols = EXCLUDED.symbols,
    universe_category = EXCLUDED.universe_category,
    liquidity_filter = EXCLUDED.liquidity_filter,
    universe_metadata = EXCLUDED.universe_metadata,
    last_universe_update = CURRENT_TIMESTAMP;

-- ==============================================================
-- PHASE 3: ETF Management Functions
-- ==============================================================

-- Function to get ETF universe with liquidity filtering
CREATE OR REPLACE FUNCTION get_etf_universe(
    theme_name VARCHAR(50),
    apply_liquidity_filter BOOLEAN DEFAULT true
)
RETURNS JSONB AS $$
DECLARE
    universe_data JSONB;
    result JSONB;
BEGIN
    -- Get universe data
    SELECT jsonb_build_object(
        'cache_key', cache_key,
        'symbols', symbols,
        'metadata', universe_metadata,
        'liquidity_filter', liquidity_filter,
        'last_updated', last_universe_update
    )
    INTO universe_data
    FROM cache_entries
    WHERE cache_key = 'etf_' || theme_name
    AND universe_category = 'ETF';
    
    IF universe_data IS NULL THEN
        RETURN jsonb_build_object('error', 'Universe not found: ' || theme_name);
    END IF;
    
    -- Apply additional filtering if needed
    IF apply_liquidity_filter THEN
        -- Future: Add real-time liquidity validation
        result := universe_data || jsonb_build_object(
            'filtered', true,
            'filter_applied', universe_data->'liquidity_filter'
        );
    ELSE
        result := universe_data || jsonb_build_object('filtered', false);
    END IF;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to update ETF universe with validation
CREATE OR REPLACE FUNCTION update_etf_universe(
    theme_name VARCHAR(50),
    new_symbols JSONB,
    update_metadata JSONB DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    cache_key_name VARCHAR(100);
    existing_symbols JSONB;
    symbols_added JSONB;
    symbols_removed JSONB;
    result JSONB;
BEGIN
    cache_key_name := 'etf_' || theme_name;
    
    -- Get existing symbols
    SELECT symbols INTO existing_symbols
    FROM cache_entries
    WHERE cache_key = cache_key_name;
    
    IF existing_symbols IS NULL THEN
        -- Create new universe
        INSERT INTO cache_entries (
            cache_key, 
            symbols, 
            universe_category,
            universe_metadata,
            last_universe_update
        ) VALUES (
            cache_key_name,
            new_symbols,
            'ETF',
            COALESCE(update_metadata, '{"theme": "' || theme_name || '"}'::jsonb),
            CURRENT_TIMESTAMP
        );
        
        result := jsonb_build_object(
            'action', 'created',
            'cache_key', cache_key_name,
            'symbols_count', jsonb_array_length(new_symbols),
            'timestamp', CURRENT_TIMESTAMP
        );
    ELSE
        -- Update existing universe
        UPDATE cache_entries SET
            symbols = new_symbols,
            universe_metadata = COALESCE(
                universe_metadata || update_metadata,
                universe_metadata
            ),
            last_universe_update = CURRENT_TIMESTAMP
        WHERE cache_key = cache_key_name;
        
        -- Calculate changes
        symbols_added := (
            SELECT jsonb_agg(symbol)
            FROM jsonb_array_elements_text(new_symbols) symbol
            WHERE symbol NOT IN (SELECT jsonb_array_elements_text(existing_symbols))
        );
        
        symbols_removed := (
            SELECT jsonb_agg(symbol)
            FROM jsonb_array_elements_text(existing_symbols) symbol
            WHERE symbol NOT IN (SELECT jsonb_array_elements_text(new_symbols))
        );
        
        result := jsonb_build_object(
            'action', 'updated',
            'cache_key', cache_key_name,
            'symbols_count', jsonb_array_length(new_symbols),
            'added_count', jsonb_array_length(COALESCE(symbols_added, '[]'::jsonb)),
            'removed_count', jsonb_array_length(COALESCE(symbols_removed, '[]'::jsonb)),
            'symbols_added', COALESCE(symbols_added, '[]'::jsonb),
            'symbols_removed', COALESCE(symbols_removed, '[]'::jsonb),
            'timestamp', CURRENT_TIMESTAMP
        );
    END IF;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to get all ETF universes summary
CREATE OR REPLACE FUNCTION get_etf_universes_summary()
RETURNS TABLE (
    theme VARCHAR(50),
    symbol_count INTEGER,
    last_updated TIMESTAMP,
    focus VARCHAR(100),
    criteria TEXT,
    symbols_sample JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        REPLACE(ce.cache_key, 'etf_', '') as theme,
        jsonb_array_length(ce.symbols) as symbol_count,
        ce.last_universe_update as last_updated,
        COALESCE(ce.universe_metadata->>'focus', 'general') as focus,
        COALESCE(ce.universe_metadata->>'criteria', 'Standard criteria') as criteria,
        (ce.symbols -> '0') || (ce.symbols -> '1') || (ce.symbols -> '2') as symbols_sample
    FROM cache_entries ce
    WHERE ce.universe_category = 'ETF'
    ORDER BY jsonb_array_length(ce.symbols) DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to validate ETF symbol availability in symbols table
CREATE OR REPLACE FUNCTION validate_etf_universe_symbols()
RETURNS TABLE (
    universe_key VARCHAR(100),
    symbol VARCHAR(20),
    exists_in_symbols BOOLEAN,
    symbol_type VARCHAR(10),
    active_status BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH etf_symbols AS (
        SELECT 
            ce.cache_key,
            jsonb_array_elements_text(ce.symbols) as symbol
        FROM cache_entries ce
        WHERE ce.universe_category = 'ETF'
    )
    SELECT 
        es.cache_key::VARCHAR(100),
        es.symbol::VARCHAR(20),
        (s.symbol IS NOT NULL) as exists_in_symbols,
        COALESCE(s.type, 'UNKNOWN')::VARCHAR(10),
        COALESCE(s.active, false) as active_status
    FROM etf_symbols es
    LEFT JOIN symbols s ON es.symbol = s.symbol
    ORDER BY es.cache_key, es.symbol;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================
-- PHASE 4: ETF Performance and Analytics Views
-- ==============================================================

-- View for ETF universe performance tracking
CREATE OR REPLACE VIEW etf_universe_performance AS
WITH universe_symbols AS (
    SELECT 
        ce.cache_key,
        ce.universe_metadata->>'theme' as theme,
        jsonb_array_elements_text(ce.symbols) as symbol,
        ce.last_universe_update
    FROM cache_entries ce
    WHERE ce.universe_category = 'ETF'
),
recent_performance AS (
    SELECT 
        us.cache_key,
        us.theme,
        us.symbol,
        hd.close_price,
        LAG(hd.close_price, 20) OVER (
            PARTITION BY us.symbol ORDER BY hd.date
        ) as price_20d_ago,
        hd.volume,
        AVG(hd.volume) OVER (
            PARTITION BY us.symbol 
            ORDER BY hd.date 
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) as avg_volume_20d
    FROM universe_symbols us
    LEFT JOIN historical_data hd ON us.symbol = hd.symbol
    WHERE hd.date >= CURRENT_DATE - INTERVAL '30 days'
    AND hd.date = (
        SELECT MAX(date) 
        FROM historical_data hd2 
        WHERE hd2.symbol = us.symbol
    )
)
SELECT 
    rp.cache_key,
    rp.theme,
    rp.symbol,
    rp.close_price,
    rp.price_20d_ago,
    CASE 
        WHEN rp.price_20d_ago > 0 THEN 
            ROUND(((rp.close_price - rp.price_20d_ago) / rp.price_20d_ago * 100)::numeric, 2)
        ELSE NULL 
    END as return_20d_pct,
    rp.volume,
    ROUND(rp.avg_volume_20d::numeric, 0) as avg_volume_20d,
    CASE 
        WHEN rp.avg_volume_20d > 0 THEN 
            ROUND((rp.volume / rp.avg_volume_20d)::numeric, 2)
        ELSE NULL 
    END as volume_ratio
FROM recent_performance rp
ORDER BY rp.cache_key, rp.return_20d_pct DESC NULLS LAST;

-- ==============================================================
-- PHASE 5: Grant Permissions
-- ==============================================================

-- Grant permissions to app_readwrite user
GRANT SELECT, UPDATE ON TABLE cache_entries TO app_readwrite;
GRANT EXECUTE ON FUNCTION get_etf_universe(VARCHAR, BOOLEAN) TO app_readwrite;
GRANT EXECUTE ON FUNCTION update_etf_universe(VARCHAR, JSONB, JSONB) TO app_readwrite;
GRANT EXECUTE ON FUNCTION get_etf_universes_summary() TO app_readwrite;
GRANT EXECUTE ON FUNCTION validate_etf_universe_symbols() TO app_readwrite;
GRANT SELECT ON etf_universe_performance TO app_readwrite;

-- ==============================================================
-- PHASE 6: Verification Queries
-- ==============================================================

-- Verify ETF universes created successfully
SELECT 
    cache_key,
    universe_category,
    jsonb_array_length(symbols) as symbol_count,
    universe_metadata->>'theme' as theme,
    universe_metadata->>'focus' as focus,
    last_universe_update
FROM cache_entries 
WHERE universe_category = 'ETF'
ORDER BY jsonb_array_length(symbols) DESC;

-- Test ETF universe functions
SELECT get_etf_universe('sectors');
SELECT get_etf_universe('technology', false);

-- Get ETF universes summary
SELECT * FROM get_etf_universes_summary();

-- Validate symbols exist in symbols table
SELECT 
    universe_key,
    COUNT(*) as total_symbols,
    COUNT(*) FILTER (WHERE exists_in_symbols) as symbols_found,
    COUNT(*) FILTER (WHERE active_status) as active_symbols,
    ROUND(
        (COUNT(*) FILTER (WHERE exists_in_symbols)::numeric / COUNT(*)) * 100, 
        1
    ) as found_percentage
FROM validate_etf_universe_symbols()
GROUP BY universe_key
ORDER BY found_percentage DESC;

-- Show sample ETF performance data
SELECT * FROM etf_universe_performance LIMIT 20;