# Database Schema Documentation

## Sprint 59: Relationship Tables

### definition_groups

**Purpose**: Store definitions for ETFs, themes, sectors, segments, and custom groupings

**Schema**:
```sql
CREATE TABLE definition_groups (
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
```

**Indexes**:
- `idx_definition_groups_type` ON (type)
- `idx_definition_groups_environment` ON (environment)
- `idx_definition_groups_name` ON (name)
- `idx_definition_groups_type_env` ON (type, environment)

**Example Data**:
| id | name | type | description | environment |
|----|------|------|-------------|-------------|
| 1 | SPY | ETF | SPDR S&P 500 ETF Trust | DEFAULT |
| 2 | crypto_miners | THEME | Bitcoin & Cryptocurrency Miners | DEFAULT |
| 3 | information_technology | SECTOR | Information Technology Sector | DEFAULT |

---

### group_memberships

**Purpose**: Many-to-many relationships between groups and stock symbols

**Schema**:
```sql
CREATE TABLE group_memberships (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES definition_groups(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    weight NUMERIC(5,4),
    metadata JSONB,
    added_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_membership UNIQUE (group_id, symbol)
);
```

**Indexes**:
- `idx_group_memberships_group_id` ON (group_id)
- `idx_group_memberships_symbol` ON (symbol)
- `idx_group_memberships_symbol_group` ON (symbol, group_id)

**Example Data**:
| id | group_id | symbol | weight |
|----|----------|--------|--------|
| 1 | 1 | AAPL | 0.0650 |
| 2 | 1 | MSFT | 0.0550 |
| 3 | 2 | MARA | NULL |

---

### Common Queries

#### Get ETF Holdings
```sql
SELECT gm.symbol
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.name = 'SPY'
  AND dg.type = 'ETF'
  AND dg.environment = 'DEFAULT'
ORDER BY gm.symbol;
```

#### Get Stock's ETF Memberships
```sql
SELECT dg.name
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE gm.symbol = 'AAPL'
  AND dg.type = 'ETF'
  AND dg.environment = 'DEFAULT'
ORDER BY dg.name;
```

#### Get Theme Members
```sql
SELECT gm.symbol
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.name = 'crypto_miners'
  AND dg.type = 'THEME'
  AND dg.environment = 'DEFAULT'
ORDER BY gm.symbol;
```

#### Count Stocks by Sector
```sql
SELECT
    dg.name as sector,
    COUNT(DISTINCT gm.symbol) as stock_count
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.type = 'SECTOR'
  AND dg.environment = 'DEFAULT'
GROUP BY dg.name
ORDER BY stock_count DESC;
```

---

## Performance Notes

- All JOIN queries use indexes for optimal performance (<5ms typical)
- Foreign key CASCADE ensures automatic cleanup of orphaned memberships
- UNIQUE constraints prevent duplicate memberships
- JSONB columns allow flexible metadata storage without schema changes
