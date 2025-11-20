# Master CSV Universe Registry

**Created**: 2025-09-12  
**Purpose**: Central registry of all CSV universe files for controlled symbol loading  
**Strategy**: CSV defines symbols → Massive API provides details → Database stores both symbols + OHLCV data  

## Overview

This registry tracks all CSV files used for universe loading in TickStock. Each CSV contains curated symbol lists that control which stocks/ETFs are loaded from Massive.com API into the database.

**Key Principle**: CSV files control WHICH symbols to load, Massive API provides WHAT data for those symbols.

## Stock Universe Files

### **Major US Indexes**

#### `sp_500.csv`
- **Purpose**: S&P 500 Index constituent stocks
- **Symbol Count**: ~500 
- **Schema**: `symbol` (minimal)
- **Source**: Official S&P 500 constituent list
- **Update Frequency**: Quarterly (index changes)
- **Usage**: Most liquid large-cap US stocks
- **Admin Label**: "S&P 500 Index (500 stocks)"

#### `nasdaq_100.csv` 
- **Purpose**: NASDAQ 100 Index technology-focused stocks
- **Symbol Count**: ~100
- **Schema**: `symbol` (minimal)
- **Source**: NASDAQ official constituent list
- **Update Frequency**: Annually (rare changes)
- **Usage**: Large-cap technology and growth stocks
- **Admin Label**: "NASDAQ 100 Technology (100 stocks)"

#### `dow_30.csv`
- **Purpose**: Dow Jones Industrial Average blue-chip stocks
- **Symbol Count**: 30
- **Schema**: `symbol` (minimal) 
- **Source**: S&P Dow Jones Indices official list
- **Update Frequency**: Rarely (very stable)
- **Usage**: Traditional blue-chip large-cap stocks
- **Admin Label**: "Dow Jones 30 Industrial (30 stocks)"

### **Russell 3000 Index (Split into 6 Parts)**

#### `russell_3000_part1.csv`
- **Purpose**: Russell 3000 Index Part 1 (Largest companies)
- **Symbol Count**: 500
- **Schema**: `symbol` (minimal)
- **Source**: Russell 3000 constituent list (sorted by market cap)
- **Range**: Symbols 1-500 (largest market caps)
- **Admin Label**: "Russell 3000 Part 1 (500 largest)"

#### `russell_3000_part2.csv`
- **Purpose**: Russell 3000 Index Part 2
- **Symbol Count**: 500
- **Schema**: `symbol` (minimal)
- **Range**: Symbols 501-1000
- **Admin Label**: "Russell 3000 Part 2 (501-1000)"

#### `russell_3000_part3.csv`
- **Purpose**: Russell 3000 Index Part 3
- **Symbol Count**: 500
- **Schema**: `symbol` (minimal)
- **Range**: Symbols 1001-1500
- **Admin Label**: "Russell 3000 Part 3 (1001-1500)"

#### `russell_3000_part4.csv`
- **Purpose**: Russell 3000 Index Part 4
- **Symbol Count**: 500
- **Schema**: `symbol` (minimal)
- **Range**: Symbols 1501-2000
- **Admin Label**: "Russell 3000 Part 4 (1501-2000)"

#### `russell_3000_part5.csv`
- **Purpose**: Russell 3000 Index Part 5
- **Symbol Count**: 500
- **Schema**: `symbol` (minimal)
- **Range**: Symbols 2001-2500
- **Admin Label**: "Russell 3000 Part 5 (2001-2500)"

#### `russell_3000_part6.csv`
- **Purpose**: Russell 3000 Index Part 6 (Remainder)
- **Symbol Count**: ~500+ (includes remainder)
- **Schema**: `symbol` (minimal)
- **Range**: Symbols 2501-3000+ (plus any remainder)
- **Admin Label**: "Russell 3000 Part 6 (2501-end)"

## ETF Universe Files

### **Essential ETFs**

#### `curated_etfs.csv` ✅ **COMPLETE**
- **Purpose**: Essential ETFs for market analysis (hand-curated)
- **Symbol Count**: 46
- **Schema**: `symbol,name,category,description`
- **Source**: TickStock curation (broad market, sectors, factors, crypto, bonds)
- **Update Frequency**: Quarterly review
- **Usage**: High-quality, liquid ETF universe for pattern analysis
- **Admin Label**: "Curated Essential ETFs (46 funds)"

## CSV File Schema Standards

### **Minimal Schema** (Most Files)
```csv
symbol
AAPL
MSFT
GOOGL
```

### **Enhanced Schema** (When Needed)
```csv
symbol,name
AAPL,Apple Inc
MSFT,Microsoft Corp
GOOGL,Alphabet Inc
```

### **Rich Schema** (ETFs Only)
```csv
symbol,name,category,description
SPY,SPDR S&P 500 ETF Trust,broad_market,Largest S&P 500 ETF
QQQ,Invesco QQQ Trust,broad_market,NASDAQ-100 Technology Focus
```

## Load Tracking System

### **Database Table**: `symbol_load_log`
```sql
CREATE TABLE symbol_load_log (
    id SERIAL PRIMARY KEY,
    csv_filename VARCHAR(255) NOT NULL,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    symbol_count INTEGER NOT NULL,
    symbols_loaded INTEGER DEFAULT 0,
    symbols_updated INTEGER DEFAULT 0,
    symbols_skipped INTEGER DEFAULT 0,
    ohlcv_records_loaded INTEGER DEFAULT 0,
    load_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    load_duration_seconds FLOAT
);
```

### **Load Status Values**
- `pending` - Load initiated
- `in_progress` - Currently loading
- `completed` - Successfully completed
- `failed` - Failed with errors
- `partial` - Completed with some errors

## File Maintenance Guidelines

### **Update Schedule**
- **S&P 500**: Quarterly (March, June, September, December)
- **NASDAQ 100**: Annually (December)
- **Dow 30**: As needed (rare changes)
- **Russell 3000**: Annually (June reconstitution)
- **Curated ETFs**: Quarterly review

### **File Validation**
Before updating any CSV file:
1. Verify symbol count matches expectations
2. Check for duplicate symbols
3. Validate symbols exist on exchanges
4. Test load with small sample

### **Git Workflow**
```bash
# Update CSV files
git add data/sp_500.csv
git commit -m "Update S&P 500 constituents - Q3 2025 changes"

# Tag quarterly updates
git tag csv-update-2025-q3
```

## Admin Interface Integration

### **CSV Loading Flow**
1. **Admin selects CSV** from dropdown
2. **System reads CSV** symbols list
3. **Massive API called** for each symbol to get full details
4. **Database updated** with both `symbols` and `ohlcv_daily` data
5. **Load tracked** in `symbol_load_log` table

### **Performance Considerations**
- **Batch processing**: Load symbols in batches of 100
- **Rate limiting**: Respect Massive API limits
- **Progress tracking**: Show admin load progress
- **Error handling**: Continue on individual symbol failures

## File Status Summary

| CSV File | Status | Symbol Count | Last Updated |
|----------|--------|--------------|--------------|
| curated_etfs.csv | ✅ Complete | 46 | 2025-09-12 |
| sp_500.csv | 📝 Pending | ~500 | TBD |
| nasdaq_100.csv | 📝 Pending | ~100 | TBD |
| dow_30.csv | 📝 Pending | 30 | TBD |
| russell_3000_part1.csv | 📝 Pending | 500 | TBD |
| russell_3000_part2.csv | 📝 Pending | 500 | TBD |
| russell_3000_part3.csv | 📝 Pending | 500 | TBD |
| russell_3000_part4.csv | 📝 Pending | 500 | TBD |
| russell_3000_part5.csv | 📝 Pending | 500 | TBD |
| russell_3000_part6.csv | 📝 Pending | ~500+ | TBD |

## Next Steps

1. **Create database table**: `symbol_load_log`
2. **Generate CSV files**: Populate with actual symbol lists
3. **Update admin interface**: Add CSV dropdown selection
4. **Implement CSV loading**: Enhance bulk loader for CSV → Massive → Database flow
5. **Testing**: Validate full loading workflow