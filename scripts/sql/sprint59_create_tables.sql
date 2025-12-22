-- ============================================================
-- Sprint 59: Create definition_groups and group_memberships
-- ============================================================
-- Purpose: Migrate from JSONB cache_entries to relational structure
-- Created: 2025-12-20
-- ============================================================

-- Drop tables if exists (for clean re-run in development)
-- WARNING: Only uncomment in development/test environments
-- DROP TABLE IF EXISTS public.group_memberships CASCADE;
-- DROP TABLE IF EXISTS public.definition_groups CASCADE;

-- Create the definition_groups table
CREATE TABLE IF NOT EXISTS public.definition_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('ETF', 'THEME', 'SECTOR', 'SEGMENT', 'CUSTOM')),
    description TEXT,
    metadata JSONB,
    liquidity_filter JSONB,
    environment VARCHAR(10) NOT NULL CHECK (environment IN ('DEFAULT', 'TEST', 'UAT', 'PROD')),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_update TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_group UNIQUE (name, type, environment)
);

-- Create indexes for definition_groups
CREATE INDEX IF NOT EXISTS idx_definition_groups_type
    ON public.definition_groups(type);
CREATE INDEX IF NOT EXISTS idx_definition_groups_environment
    ON public.definition_groups(environment);
CREATE INDEX IF NOT EXISTS idx_definition_groups_name
    ON public.definition_groups(name);
CREATE INDEX IF NOT EXISTS idx_definition_groups_type_env
    ON public.definition_groups(type, environment);

-- Create the group_memberships table
CREATE TABLE IF NOT EXISTS public.group_memberships (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES public.definition_groups(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    weight NUMERIC(5,4),
    metadata JSONB,
    added_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_membership UNIQUE (group_id, symbol)
);

-- Create indexes for group_memberships
CREATE INDEX IF NOT EXISTS idx_group_memberships_group_id
    ON public.group_memberships(group_id);
CREATE INDEX IF NOT EXISTS idx_group_memberships_symbol
    ON public.group_memberships(symbol);
CREATE INDEX IF NOT EXISTS idx_group_memberships_symbol_group
    ON public.group_memberships(symbol, group_id);

-- Add comments for documentation
COMMENT ON TABLE public.definition_groups IS
    'Stores definitions for ETFs, themes, sectors, segments, and custom groupings';
COMMENT ON TABLE public.group_memberships IS
    'Many-to-many relationships between groups and stock symbols';

COMMENT ON COLUMN public.definition_groups.type IS
    'Group type: ETF, THEME, SECTOR, SEGMENT, or CUSTOM';
COMMENT ON COLUMN public.definition_groups.liquidity_filter IS
    'JSONB filters like {"min_volume": 1000000, "min_market_cap": 1000000000}';
COMMENT ON COLUMN public.group_memberships.weight IS
    'Optional weight/percentage (e.g., 0.0650 = 6.5% of ETF)';

-- Grant permissions (adjust based on your user roles)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON public.definition_groups TO app_readwrite;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON public.group_memberships TO app_readwrite;
-- GRANT USAGE, SELECT ON SEQUENCE definition_groups_id_seq TO app_readwrite;
-- GRANT USAGE, SELECT ON SEQUENCE group_memberships_id_seq TO app_readwrite;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Tables created successfully: definition_groups, group_memberships';
END $$;
