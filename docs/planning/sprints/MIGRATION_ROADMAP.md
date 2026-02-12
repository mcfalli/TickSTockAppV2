# TickStockPL → TickStockAppV2 Migration Roadmap

**Migration Goal**: Consolidate TickStockPL and TickStockAppV2 into a unified system with clear architectural boundaries.

**Total Duration**: 8 weeks (40 working days)
**Total Lines Migrated**: ~30,401 lines
**Sprints**: 68, 69, 70

---

## Executive Summary

### Problem Statement
TickStockPL and TickStockAppV2 exist as separate applications, causing:
- **Development Overhead**: HIGH - Maintaining two codebases, duplicate logic
- **Redis Complexity**: MEDIUM - Cross-component debugging challenges
- **Pattern Detection**: DISABLED - Critical feature unavailable

### Solution
**Partial Consolidation Strategy**:
- Migrate analysis capabilities to AppV2 (36% of PL)
- Keep data loading infrastructure in TickStockPL (64% of PL)
- Establish single source of truth for each domain

### Expected Benefits
1. ✅ Single codebase for pattern/indicator logic
2. ✅ Simplified debugging (single process for analysis)
3. ✅ Pattern detection re-enabled and automated
4. ✅ Clear architectural boundaries (Producer/Consumer)
5. ✅ Reduced deployment complexity

---

## Migration Architecture

### Before Migration
```
TickStockPL (67,588 lines)
├── Pattern Detection (7,287 lines)      ← DISABLED
├── Indicator Calculation (3,771 lines)  ← DISABLED
├── Analysis Engines (6,427 lines)
├── Background Jobs (4,848 lines)
├── Historical Data Loading (13,099 lines)
└── Supporting Infrastructure

TickStockAppV2
├── UI/Dashboards
├── WebSocket Streaming
├── Basic Pattern Detection (3 patterns only - fallback)
└── Duplicate Historical Loader (1,220 lines - architectural violation)
```

### After Migration (Post-Sprint 70)
```
TickStockPL (Data Loading Microservice - 13,795 lines)
├── Historical Data Loading (13,099 lines) ✅ KEPT
├── Job Queue Processing (696 lines)       ✅ KEPT
└── Data Producer Role                     ✅ SINGLE SOURCE OF TRUTH

TickStockAppV2 (UI & Analysis Platform - 30,401 lines added)
├── Pattern Detection (7,287 lines)        ✅ MIGRATED
├── Indicator Calculation (3,771 lines)    ✅ MIGRATED
├── Analysis Engines (6,427 lines)         ✅ MIGRATED
├── Background Jobs (4,848 lines)          ✅ MIGRATED
├── UI/Dashboards                          ✅ ENHANCED
├── WebSocket Streaming                    ✅ EXISTING
└── Admin UI                               ✅ WIRED TO PL VIA REDIS
```

### Communication Flow
```
User → AppV2 Admin UI
         ↓
    Redis Job Queue (tickstock.jobs.data_load)
         ↓
    TickStockPL → Load Data → Store in TimescaleDB
         ↓
    Redis Completion Event
         ↓
    AppV2 Post-Import Analysis → Calculate Indicators → Detect Patterns
         ↓
    Redis Pub-Sub (tickstock.events.patterns)
         ↓
    WebSocket → Browser
```

---

## Sprint Breakdown

### Sprint 68: Core Analysis Migration (3 weeks)
**Goal**: Migrate pattern detection, indicator calculation, and analysis engines from TickStockPL to AppV2.

**Week 1: Indicators (3,771 lines)**
- Days 1-2: BaseIndicator class + 5 core indicators (RSI, SMA, EMA, MACD, BB)
- Days 3-4: 5 advanced indicators (ATR, ADX, OBV, Stochastic, VWAP)
- Day 5: 5 additional indicators + Week 1 validation

**Week 2: Patterns (7,287 lines)**
- Days 6-7: BasePattern class + 7 basic patterns (Doji, Hammer, Shooting Star, etc.)
- Days 8-9: 7 advanced patterns (Head-Shoulders, Double Top/Bottom, etc.)
- Day 10: 6 final patterns + Week 2 validation

**Week 3: Analysis Engines (6,427 lines)**
- Days 11-12: AnalysisService, IndicatorService, PatternService
- Days 13-14: Dynamic loaders (NO FALLBACK policy), regression testing
- Day 15: Final validation, documentation, Sprint 68 closure

**Deliverables**:
- 15 indicators migrated and tested
- 20+ patterns migrated and tested
- AnalysisService with analyze_symbol() and analyze_universe()
- 50+ unit tests, 15+ integration tests
- Regression tests proving 100% accuracy match

**Success Criteria**:
- ✅ All indicators calculate identically to TickStockPL
- ✅ All patterns detect identically to TickStockPL
- ✅ Performance: <1s per symbol (15 indicators + 20 patterns)
- ✅ Dynamic loading working (NO FALLBACK)
- ✅ Integration tests pass

---

### Sprint 69: Background Jobs & Integration (3 weeks)
**Goal**: Integrate migrated analysis with background job infrastructure, enable pattern detection automation, and remove TickStockPL analysis dependencies.

**Week 1: Background Job Infrastructure (4,848 lines)**
- Day 1: APScheduler setup, SchedulerManager singleton, BaseJob class
- Day 2: DailyIndicatorJob (runs 6:10 PM ET)
- Day 3: DailyPatternJob (runs 6:20 PM ET, publishes to Redis)
- Day 4: Post-import analysis integration (DataLoadListener)
- Day 5: Job monitoring API endpoints + Admin UI

**Week 2: TickStockPL Dependency Removal**
- Day 6: Redis channel consolidation (AppV2 publishes patterns)
- Days 7-8: Migrate remaining jobs (CacheMaintenanceJob, DatabaseCleanupJob)
- Day 9: TickStockPL deprecation plan documentation
- Day 10: Week 2 validation, standalone AppV2 testing

**Week 3: Final Integration & Documentation**
- Days 11-12: Admin UI enhancements (Analysis Control Panel, job dashboard)
- Days 13-14: Documentation & knowledge transfer
- Day 15: Final validation, Sprint 69 closure

**Deliverables**:
- 6 background jobs operational (APScheduler)
- Daily pattern/indicator automation (6:10 PM, 6:20 PM ET)
- Post-import analysis triggers automatically
- Redis channels consolidated (AppV2 publishes)
- Admin UI Analysis Control Panel
- TickStockPL deprecation plan

**Success Criteria**:
- ✅ Background jobs run successfully (>99% success rate)
- ✅ Pattern detection automated (daily after market close)
- ✅ Post-import analysis working (triggered by TickStockPL)
- ✅ AppV2 runs standalone (analysis features)
- ✅ 50+ unit tests, 15+ integration tests

---

### Sprint 70: Historical Import Consolidation (2 weeks)
**Goal**: Remove AppV2's duplicate historical loader, wire Admin UI to TickStockPL's Redis job queue, and establish single source of truth for data loading.

**Week 1: Historical Import Consolidation**
- Day 1: Audit and remove duplicate historical_loader.py (1,220 lines)
- Day 2: Create TickStockPLClient for Redis job queue
- Day 3: Update Admin UI for async job workflow (polling, progress bar)
- Day 4: Validate single source of truth (TickStockPL owns data loading)
- Day 5: Week 1 validation, integration tests

**Week 2: TickStockPL Archival & Monitoring**
- Days 6-7: TickStockPL archival plan (NOTE: Keep deployed for data loading)
- Days 8-9: 30-day monitoring dashboard, automated alerts
- Day 10: Sprint 70 closure, migration summary documentation

**Deliverables**:
- historical_loader.py removed (1,220 lines)
- TickStockPLClient for Redis job submission
- Admin UI async job workflow (polling, progress bar)
- Data flow architecture documentation
- 30-day monitoring dashboard
- Migration summary

**Success Criteria**:
- ✅ Duplicate historical loader removed
- ✅ Admin UI wired to TickStockPL via Redis
- ✅ Job submission/polling working (<100ms, <50ms)
- ✅ Single source of truth established (TickStockPL)
- ✅ Monitoring dashboard operational

---

## Migration Metrics

### Lines of Code

| Component | Lines | Sprint | Status |
|-----------|-------|--------|--------|
| **Pattern Detection** | 7,287 | 68 | ✅ Migrate to AppV2 |
| **Indicator Calculation** | 3,771 | 68 | ✅ Migrate to AppV2 |
| **Analysis Engines** | 6,427 | 68 | ✅ Migrate to AppV2 |
| **Background Jobs** | 4,848 | 69 | ✅ Migrate to AppV2 |
| **Duplicate Loader** | 1,220 | 70 | ✅ Remove from AppV2 |
| **Historical Data Loading** | 13,099 | - | ❌ KEEP in TickStockPL |
| **Job Queue Processing** | 696 | - | ❌ KEEP in TickStockPL |

**Total Migrated**: 24,333 lines (36% of TickStockPL)
**Total Removed**: 1,220 lines (duplicates)
**Total Remaining in PL**: 13,795 lines (20% of TickStockPL)

### Testing Coverage

| Sprint | Unit Tests | Integration Tests | Total |
|--------|-----------|-------------------|-------|
| 68 | 50+ | 15+ | 65+ |
| 69 | 50+ | 15+ | 65+ |
| 70 | 10+ | 10+ | 20+ |
| **Total** | **110+** | **40+** | **150+** |

### Performance Targets

| Metric | Target | Sprint | Priority |
|--------|--------|--------|----------|
| Indicator Calculation | <1s per symbol | 68 | HIGH |
| Pattern Detection | <1s per symbol | 68 | HIGH |
| Background Jobs | <10 min for 500 symbols | 69 | MEDIUM |
| Job Submission | <100ms | 70 | MEDIUM |
| Status Polling | <50ms | 70 | LOW |
| Redis Operations | <10ms | All | HIGH |

---

## Risk Management

### High Risks

**Risk 1: Pattern Detection Accuracy Regression**
- **Impact**: HIGH - Core feature accuracy loss
- **Probability**: LOW - Regression tests validate 100% match
- **Mitigation**:
  - Comprehensive regression testing (Sprint 68 Day 14)
  - 30-day monitoring with automated alerts
  - Rollback plan if accuracy <99%

**Risk 2: Performance Degradation**
- **Impact**: MEDIUM - User experience degradation
- **Probability**: LOW - Parallel processing with 10 workers
- **Mitigation**:
  - Performance benchmarking (Sprint 68 Day 15)
  - Database query optimization
  - Connection pooling

**Risk 3: Background Job Failures**
- **Impact**: MEDIUM - Pattern detection unavailable
- **Probability**: LOW - Robust error handling, retry logic
- **Mitigation**:
  - Job monitoring dashboard (Sprint 69 Day 5)
  - Automated alerts on job failures
  - Manual trigger capability via Admin UI

### Medium Risks

**Risk 4: Redis Communication Issues**
- **Impact**: MEDIUM - Cross-component events lost
- **Probability**: MEDIUM - Network/Redis instability
- **Mitigation**:
  - Redis connection pooling
  - Retry logic with exponential backoff
  - Health monitoring (Sprint 69 Day 10)

**Risk 5: Data Inconsistency**
- **Impact**: LOW - UI shows stale data
- **Probability**: LOW - Database constraints, transactions
- **Mitigation**:
  - Database integrity constraints
  - Transaction isolation
  - Data validation gates

---

## Success Criteria (Overall)

### Technical Quality
- ✅ All 150+ tests passing (unit + integration)
- ✅ Code coverage >80% for migrated components
- ✅ Zero linting errors (ruff)
- ✅ No security vulnerabilities (hardcoded credentials)
- ✅ Performance targets met (<1s per symbol)

### Functional Requirements
- ✅ Pattern detection working identically to TickStockPL
- ✅ Indicator calculation matching TickStockPL values
- ✅ Background jobs automated (daily 6:10 PM, 6:20 PM ET)
- ✅ Post-import analysis triggered automatically
- ✅ Admin UI fully functional (job control, monitoring)

### Architecture Compliance
- ✅ AppV2 is Consumer + Analyzer (no data fetching)
- ✅ TickStockPL is Data Producer (historical import only)
- ✅ Redis pub-sub for cross-component events
- ✅ Single source of truth (TickStockPL for data, AppV2 for analysis)
- ✅ Clear separation of concerns

### Documentation
- ✅ Sprint completion documents (3 sprints)
- ✅ Architecture documentation updated
- ✅ Migration summary created
- ✅ Troubleshooting guides tested
- ✅ CLAUDE.md updated with latest status

### Stability (30-day monitoring)
- ✅ System uptime >99.9%
- ✅ Job success rate >99%
- ✅ Error rate <0.1%
- ✅ Zero critical incidents
- ✅ Pattern accuracy >99% vs baseline

---

## Decision Points

### Sprint 68 Completion Gate
**Criteria**:
- All indicators/patterns migrated and tested
- Regression tests prove 100% accuracy match
- Performance targets met (<1s per symbol)
- Integration tests passing

**Decision**: Proceed to Sprint 69 if all criteria met

### Sprint 69 Completion Gate
**Criteria**:
- Background jobs operational (>99% success rate)
- AppV2 standalone validated (analysis features)
- Redis channels consolidated
- Admin UI functional

**Decision**: Proceed to Sprint 70 if all criteria met

### Sprint 70 Completion Gate
**Criteria**:
- Duplicate historical loader removed
- Admin UI wired to TickStockPL via Redis
- Single source of truth validated
- Monitoring dashboard operational

**Decision**: Begin 30-day monitoring period

### Final Archival Decision (Post-30 days)
**Criteria**:
- All success criteria met
- 30 days of stable operation
- Zero critical regressions
- Team aligned on strategy

**Decision**:
- ✅ **KEEP TickStockPL DEPLOYED** (data loading microservice)
- ✅ Archive TickStockPL repository (read-only, reference only)
- ✅ Update deployment documentation

---

## Rollback Plan

### Scenario: Critical Regression Detected

**Step 1: Assess Impact**
- Determine affected component (patterns, indicators, jobs)
- Check monitoring dashboard for metrics
- Review error logs and alerts

**Step 2: Immediate Mitigation**
- Pause affected background jobs (via Admin UI)
- Enable verbose logging
- Notify team

**Step 3: Determine Rollback Scope**
- **If Sprint 68 issue**: Pattern/indicator calculation error
  - No rollback available (TickStockPL analysis disabled)
  - Fix forward, deploy hotfix
- **If Sprint 69 issue**: Background job failure
  - Pause jobs, manual analysis via Admin UI
  - Fix forward
- **If Sprint 70 issue**: Historical import workflow broken
  - Re-enable AppV2 historical loader (revert commit)
  - Fix TickStockPL client, redeploy

**Step 4: Root Cause Analysis**
- Identify regression source
- Create fix plan with tests
- Deploy to staging, re-test

**Step 5: Re-Deploy**
- Deploy fix to production
- Resume normal operations
- Monitor for 7 days

**Rollback Trigger**: >5% accuracy regression OR >3 consecutive critical job failures

---

## Post-Migration Operations

### 30-Day Monitoring Period

**Daily Activities**:
1. Generate migration monitoring report
2. Review automated alerts
3. Check job success rates
4. Validate pattern accuracy
5. Monitor system health

**Weekly Activities**:
1. Performance analysis (compare to baseline)
2. Error log review
3. User feedback collection
4. Documentation updates
5. Team standup (migration status)

**Monthly Activities**:
1. Comprehensive system health report
2. Pattern accuracy regression analysis
3. Performance benchmarking
4. Decision on TickStockPL archival

### Success Metrics (30-day period)

| Metric | Target | Measurement |
|--------|--------|-------------|
| System Uptime | >99.9% | Job execution logs |
| Job Success Rate | >99% | job_executions table |
| Pattern Accuracy | >99% vs baseline | Regression tests |
| Error Rate | <0.1% | error_logs table |
| Average Analysis Time | <1s per symbol | Performance logs |

### Final Decision

**If all metrics met after 30 days**:
- ✅ TickStockPL archival approved (keep deployed for data loading)
- ✅ Repository marked read-only
- ✅ Migration declared successful
- ✅ Lessons learned documented

**If metrics not met**:
- ⚠️ Extend monitoring period (additional 30 days)
- ⚠️ Address identified issues
- ⚠️ Re-evaluate migration strategy

---

## Timeline

```
Week 1-3  : Sprint 68 (Indicators, Patterns, Analysis Engines)
Week 4-6  : Sprint 69 (Background Jobs, Integration, Deprecation)
Week 7-8  : Sprint 70 (Historical Import Consolidation, Monitoring)
Week 9-12 : 30-day monitoring period
Week 13   : Final decision & archival (if criteria met)
```

**Total Duration**: 13 weeks (3 months)
**Active Development**: 8 weeks (Sprints 68-70)
**Monitoring**: 4 weeks (validation period)
**Final Decision**: Week 13

---

## Next Steps

1. **Review This Roadmap**: Team alignment on migration strategy
2. **Create PRPs**: Generate Product Requirement Prompts for Sprint 68, 69, 70
3. **Sprint 68 Kickoff**: Begin indicator/pattern migration
4. **Establish Baselines**: Capture TickStockPL pattern/indicator accuracy for comparison
5. **Setup Monitoring**: Prepare infrastructure for 30-day monitoring period

---

## Related Documentation

- **Sprint 68 Plan**: `docs/planning/sprints/sprint68/SPRINT68_PLAN.md`
- **Sprint 69 Plan**: `docs/planning/sprints/sprint69/SPRINT69_PLAN.md`
- **Sprint 70 Plan**: `docs/planning/sprints/sprint70/SPRINT70_PLAN.md`
- **Migration Assessment**: `docs/planning/sprints/TICKSTOCKPL_MIGRATION_ASSESSMENT.md`
- **PRP Template**: `docs/PRPs/templates/prp-new.md`

---

**Status**: Planning Complete, Ready for PRP Generation
**Owner**: TickStock Development Team
**Start Date**: TBD (after PRP creation)
**Target Completion**: 13 weeks from start date
