# Cache Entries Deprecation Plan
## Sprint 59 Migration

**Current Status**: Both systems operational (parallel mode)

---

## Timeline

### Week 1-2: Parallel Operation (CURRENT)
**Status**: ✅ Active
**Start Date**: December 21, 2025

**Actions**:
- Both cache_entries and new tables contain same data
- All scripts use new tables
- Old cache_entries preserved for rollback

**Monitoring**:
- Query performance metrics
- Error rates
- Integration test results

---

### Week 3: Validation Period
**Target Date**: Week of January 6, 2026

**Actions**:
- [ ] Run comprehensive performance benchmarks
- [ ] Verify zero regression in functionality
- [ ] Monitor error logs for any issues
- [ ] Get stakeholder approval to proceed

**Go/No-Go Decision**: End of Week 3

---

### Week 4+: Archive Old Data (If Approved)
**Target Date**: Week of January 13, 2026

**Actions**:
- [ ] Create final backup of cache_entries
- [ ] Archive old entries (optional: move to archive table)
- [ ] Update documentation to remove cache_entries references
- [ ] Remove rollback instructions (if confident)

**Optional Archival Query**:
```sql
-- Create archive table
CREATE TABLE cache_entries_archive AS
SELECT * FROM cache_entries
WHERE type IN ('etf_holdings', 'theme_definition', 'sector_industry_map');

-- Delete archived data from cache_entries
DELETE FROM cache_entries
WHERE type IN ('etf_holdings', 'theme_definition', 'sector_industry_map');
```

---

## Rollback Window

- **Week 1-2**: Immediate rollback possible (no data change)
- **Week 3**: Same-day rollback possible
- **Week 4+**: Requires backup restore

---

## Decision Criteria

**Proceed with Deprecation if**:
- ✅ Zero production errors for 2 weeks
- ✅ Query performance equal or better
- ✅ All integration tests passing
- ✅ Stakeholder approval obtained

**Delay Deprecation if**:
- ❌ Any production errors related to new tables
- ❌ Performance degradation observed
- ❌ Integration test failures
- ❌ Stakeholder concerns raised

---

**Status**: Week 1 (Parallel Operation)
**Next Review**: January 6, 2026
