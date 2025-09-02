# Database Scripts

This folder contains **ACTIVE** database scripts and utilities for TickStock database management.

## Purpose
These scripts manage database schema, migrations, and utilities for the TickStock PostgreSQL/TimescaleDB database.

## Script Categories

## Folder Structure

```
scripts/database/
├── README.md                  # This file
├── utilities/                 # Active utility scripts
│   ├── clear_symbols_table.sql
│   ├── symbols_table_enhancement.sql
│   └── etf_database_methods.py
├── migrations/                # Completed migrations (historical)
│   ├── 01_create_symbols_related_tickers_table.sql
│   ├── 02_add_sic_fields_to_symbols.sql
│   ├── 03_create_complete_sic_mapping.sql
│   ├── cache_entries_universe_expansion.sql
│   ├── data_quality_enhancement.sql
│   ├── equity_types_enhancement.sql
│   └── etf_integration_migration.sql
└── documentation/             # Reference documentation
    ├── etf_integration_testing_strategy.md
    └── etf_performance_optimization_analysis.md
```

### 🔧 Active Utility Scripts (`utilities/`)

#### `clear_symbols_table.sql`
**Status**: ✅ **ACTIVELY USED**  
**Purpose**: Utility to clear symbols table for fresh data loads  
**Usage**: Execute when needing to reset symbol data
```sql
-- Use with caution - removes all symbol data
psql -d tickstock -f utilities/clear_symbols_table.sql
```

#### `symbols_table_enhancement.sql`
**Status**: ✅ **REFERENCE SCHEMA**  
**Purpose**: Current symbols table structure with all enhancements  
**Contains**: 
- Core symbol fields
- SIC classification fields (sic_code, sic_description, sector, industry)
- ETF-specific fields
- Market data fields
- Metadata tracking fields

#### `etf_database_methods.py`
**Status**: ✅ **UTILITY FUNCTIONS**  
**Purpose**: Python methods for ETF database operations

### 📚 Completed Migrations (`migrations/`)

These scripts have been **APPLIED** and are kept for historical reference:

#### SIC Implementation (Sprint 14)
- `01_create_symbols_related_tickers_table.sql` - ✅ Applied
- `02_add_sic_fields_to_symbols.sql` - ✅ Applied
- `03_create_complete_sic_mapping.sql` - ✅ Applied

#### ETF Integration (Sprint 12)
- `etf_integration_migration.sql` - ✅ Applied
- `equity_types_enhancement.sql` - ✅ Applied
- `data_quality_enhancement.sql` - ✅ Applied
- `cache_entries_universe_expansion.sql` - ✅ Applied

### 📖 Documentation (`documentation/`)
- `etf_integration_testing_strategy.md` - Testing documentation
- `etf_performance_optimization_analysis.md` - Performance analysis

## Database Schema Overview

### Primary Tables
- **symbols** - Master table for all stocks and ETFs
- **cache_entries** - Organized groupings and configurations
- **historical_data** - Time-series price/volume data
- **analytics_data** - Computed analytics and indicators

### Key Fields Added
```sql
-- SIC Classification (Added Sprint 14)
sic_code VARCHAR(10)
sic_description VARCHAR(255)
sector VARCHAR(100)
industry VARCHAR(100)
country VARCHAR(100)
total_employees INTEGER
list_date DATE

-- ETF Fields (Added Sprint 12)
etf_type VARCHAR(50)
aum_millions DECIMAL(15,2)
expense_ratio DECIMAL(6,4)
inception_date DATE
issuer VARCHAR(255)
```

## Usage Guidelines

### Running Scripts
```bash
# Connect to database and run script
psql -U app_readwrite -d tickstock -f script_name.sql

# Or via Python database connection
python -c "exec(open('script_name.sql').read())"
```

### Before Running Utilities
⚠️ **CAUTION**: 
- `clear_symbols_table.sql` removes ALL symbol data
- Always backup before running destructive operations
- Check current data status first

### Integration with Historical Loader
The symbols table is populated/updated by:
- `src/data/historical_loader.py` - Fetches from Polygon.io
- Automatically creates/updates symbols with SIC mappings
- Run cache synchronization after loading

## Important Notes

⚠️ **DO NOT DELETE** completed migration scripts - they document schema evolution

📝 **Schema Changes**: New changes should create numbered migration scripts

🔄 **Current State**: All migrations through Sprint 14 have been applied

## Related Components
- `/src/data/historical_loader.py` - Populates symbols table
- `/src/core/services/cache_entries_synchronizer.py` - Uses symbols for cache organization
- `/web/templates/admin/historical_data_dashboard.html` - UI for data loading