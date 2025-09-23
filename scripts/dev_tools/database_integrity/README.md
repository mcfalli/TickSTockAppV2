# Database Integrity Validation System
**TickStockAppV2 Quality Assurance Framework**

## Overview
Comprehensive database validation system that ensures 100% accuracy across all sprints and database migrations. Automatically detects issues and generates corrective SQL.

## Quick Start
```bash
# Navigate to directory
cd scripts/dev_tools/database_integrity

# Install dependencies
pip install -r requirements.txt

# Run Sprint 23 validation
python run_integrity_check.py

# Or run detailed checks
python util_test_db_integrity.py --sprint 23 --generate-fixes
```

## Current Capabilities

### Sprint 23 Validation (14 Checks)
✅ **Tables**: market_conditions, 3 cache tables  
✅ **Functions**: 6 analytics + 4 cache management functions  
✅ **Views**: Materialized views with refresh capability  
✅ **Indexes**: Performance optimization validation  
✅ **TimescaleDB**: Hypertable setup and optimization  
✅ **Permissions**: app_readwrite user access validation  

### Architecture
- **`util_test_db_integrity.py`** - Core integrity checker with extensible check framework
- **`db_config.py`** - Database configuration and test patterns
- **`run_integrity_check.py`** - Simple guided runner
- **Check Results** - Automatic fix report generation with specific SQL commands

## Extending for Future Sprints

### Adding Sprint 24 Checks
```python
# In util_test_db_integrity.py, add to _register_sprint24_checks():
self.checks.extend([
    IntegrityCheck(
        name="new_feature_table_exists",
        category="tables", 
        sprint="24",
        sql_query="SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'new_feature');",
        expected_result=True,
        fix_sql="-- Run: docs/planning/sprints/sprint24/sql/create_new_feature.sql",
        description="New feature table must exist"
    ),
])
```

### TimescaleDB Previous Sprints
The system can be extended to validate:
- **Pattern Detection Tables** - Convert to hypertables for better performance
- **Market Data Tables** - Time-series optimization
- **Analytics Result Tables** - Compression and retention policies

## Usage Patterns

### Daily Development
```bash
# Quick health check
python run_integrity_check.py

# After major changes
python util_test_db_integrity.py --all --generate-fixes
```

### Pre-Deployment Validation
```bash
# Full system validation
python util_test_db_integrity.py --all --timescaledb --generate-fixes
```

### Sprint Completion
```bash
# Sprint-specific validation
python util_test_db_integrity.py --sprint 24 --generate-fixes
```

## Configuration

### Database Connection
Edit `db_config.py` or set environment variables:
```python
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tickstock  
DB_USER=app_readwrite
DB_PASSWORD=your_password
```

### Test Patterns
Add expected objects in `get_test_patterns()` for new sprints.

## Output Format
- **Console**: Real-time check status with ✅/❌ indicators
- **Reports**: Detailed markdown reports with fix instructions
- **Return Codes**: 0 for success, 1 for failures (CI/CD friendly)

## Future Enhancements
- **Performance Benchmarking** - Query execution time validation
- **Data Quality Checks** - Content validation beyond schema
- **Migration Testing** - Before/after validation for schema changes
- **Integration with CI/CD** - Automated validation in deployment pipeline

---
**Built for Sprint 23 - Ready for unlimited expansion**