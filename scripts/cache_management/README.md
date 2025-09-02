# Cache Management Scripts

This folder contains **ACTIVE** scripts for managing and maintaining the TickStock cache entries system.

## Purpose
These scripts are essential for the ongoing operation of TickStock's cache organization system, which groups stocks and ETFs into logical categories for efficient processing and user filtering.

## Active Scripts

### 1. `run_cache_synchronization.py`
**Status**: ✅ **ACTIVELY USED**  
**Purpose**: Rebuilds and organizes cache entries from the symbols table  
**Usage**: 
```bash
python scripts/cache_management/run_cache_synchronization.py [--no-delete] [--verbose]
```

**What it does**:
- Organizes stocks into market cap categories (mega_cap, large_cap, mid_cap, small_cap, micro_cap)
- Creates sector leaders (top 10 per sector using real SIC data)
- Builds market leaders lists (top 10/50/100/250/500)
- Groups stocks by themes (AI, Biotech, Cloud, Crypto, etc.)
- Organizes by industry groups
- Creates ETF universes and categories
- **PRESERVES** app_settings and configuration entries

**When to run**:
- After loading new symbols via historical data loader
- After updating SIC mappings
- When cache entries need reorganization
- Can be triggered from Admin Dashboard

### 2. `create_sic_mapping_config.sql`
**Status**: ✅ **REFERENCE/SETUP SCRIPT**  
**Purpose**: SQL script for creating/updating SIC code mappings in cache_entries  
**Usage**: Applied to database when adding new SIC mappings

**What it contains**:
- SIC code to sector/industry mappings
- Range-based sector classifications
- Configuration entries for cache organization

## Integration Points

### Admin Dashboard
The cache synchronization can be triggered from:
- Admin Historical Data Dashboard (`/admin/historical-data`)
- "Update and Organize Cache" button after data loads

### Core Service
The synchronizer is implemented in:
- `src/core/services/cache_entries_synchronizer.py`

### Database Tables
Works with:
- `cache_entries` - Target table for organized data
- `symbols` - Source of stock/ETF data with SIC codes

## Important Notes

⚠️ **DO NOT DELETE THIS FOLDER** - These scripts are actively used in production

✅ **Renamed**: This folder has been renamed from `maintenance` to `cache_management` for clarity

🔄 **Regular Usage**: The cache synchronization is run regularly as part of data maintenance

## Related Documentation
- `/docs/planning/sprint14/cache_entries_directions.md` - Design specifications
- `/docs/operations/cache-synchronization-guide.md` - Operational guide