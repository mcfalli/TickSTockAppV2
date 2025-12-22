# Sprint 59 Rollback Plan

## Quick Rollback (Keep Both Systems)

**Current State**: Both old (cache_entries) and new (definition_groups) systems exist

**To Rollback Scripts Only**:
```bash
# 1. Revert all scripts to Sprint 58 versions
git checkout feature/sprint58-etf-stock-relationships -- scripts/cache_maintenance/

# 2. Restart services
# No database changes needed - cache_entries data still intact
```

**Impact**: Immediate (scripts use cache_entries again)
**Data Loss**: None
**Risk**: Very Low

---

## Full Database Rollback

**If New Tables Need Removal**:

```sql
-- WARNING: This deletes new tables and all data
DROP TABLE IF EXISTS group_memberships CASCADE;
DROP TABLE IF EXISTS definition_groups CASCADE;
```

**Restore from Backup**:
```bash
# Restore entire database
psql -d tickstock < backup_before_sprint59_20251220_170204.sql
```

**Impact**: Full database restore (30-60 minutes)
**Data Loss**: All changes since backup
**Risk**: Medium

---

## Partial Rollback (Delete New Data Only)

**Keep Tables, Delete Data**:
```sql
-- Delete all Sprint 59 data (keeps table structure)
DELETE FROM group_memberships;
DELETE FROM definition_groups;

-- Reset sequences
ALTER SEQUENCE definition_groups_id_seq RESTART WITH 1;
ALTER SEQUENCE group_memberships_id_seq RESTART WITH 1;
```

**Impact**: Immediate
**Data Loss**: Only new table data
**Risk**: Low

---

## Verification After Rollback

```bash
# 1. Test scripts work
python scripts/cache_maintenance/query_relationships.py --etf SPY

# 2. Run validation
python scripts/cache_maintenance/validate_relationships.py

# 3. Check database
psql -d tickstock -c "SELECT type, COUNT(*) FROM cache_entries GROUP BY type;"
```

---

## Emergency Contact

If rollback needed:
1. Stop all services
2. Execute appropriate rollback (above)
3. Test validation
4. Restart services
