
# Database Integrity Fix Report
Generated: 2025-09-06 06:40:56
Failed Checks: 2 / 14

## Issues Found


### 1. Cache Table Indexes

**Problem**: Expected `8`, got `11`

**Fix**:
```sql
-- Recreate cache indexes from sprint23_phase1_performance_indexes.sql
```

### 2. Hypertables Created

**Problem**: Expected `3`, got `0`

**Fix**:
```sql
-- Run TimescaleDB sections from sprint23_phase1_script2_fixes.sql
```

## Recommended Actions

1. Review each failed check above
2. Execute the suggested SQL fixes in PGAdmin
3. Re-run this integrity checker to verify fixes
4. For TimescaleDB checks, ensure extension is installed

## Re-run Command
```bash
python scripts/dev_tools/util_test_db_integrity.py --sprint 23
```
