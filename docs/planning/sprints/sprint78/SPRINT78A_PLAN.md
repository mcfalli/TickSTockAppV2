# Sprint 78A: Indicator Documentation & Database Cleanup

**Created**: February 15, 2026
**Parent Sprint**: Sprint 78 (split into 78A and 78B)
**Sprint Goal**: Document all existing indicators and clean up legacy database definitions
**Status**: 📋 PLANNING
**Estimated Effort**: 10-13 hours (8-10 hours documentation + 2-3 hours cleanup)
**Estimated Completion**: February 15-16, 2026

---

## Overview

Sprint 78A is the **foundation phase** of the complete Table 1 indicator implementation. This sprint ensures:
1. **Complete Documentation Coverage**: All existing indicators have comprehensive technical documentation
2. **Database Hygiene**: Remove 16 legacy/test indicators not in Table 1
3. **Clean Foundation**: Sprint 78B can build on a clean, well-documented codebase

**Why This Matters**:
- Documentation enables future maintainers to understand existing implementations
- Database cleanup prevents confusion and reduces query overhead
- Establishes documentation standards for future indicators

---

## Sprint 78A Scope

### Phase 0A: Document Existing Indicators (8-10 hours)

**Goal**: Create comprehensive documentation for 8 already-implemented indicators

**Indicators to Document**:

1. **SMA (Simple Moving Average)** - `docs/patterns and indicators/indicators/sma.md`
   - **Implemented**: Sprint 68, 74
   - **Variants**: 6 periods (5, 10, 20, 50, 100, 200)
   - **Category**: trend
   - **Display Orders**: 10-15
   - **Key Topics**: Calculation formula, crossover strategies, support/resistance identification
   - **Estimated Time**: 1-1.5 hours

2. **EMA (Exponential Moving Average)** - `docs/patterns and indicators/indicators/ema.md`
   - **Implemented**: Sprint 70
   - **Variants**: 6 periods (5, 10, 20, 50, 100, 200)
   - **Category**: trend
   - **Display Orders**: 20-25
   - **Key Topics**: Wilder's smoothing, comparison to SMA, faster response to price changes
   - **Estimated Time**: 1-1.5 hours

3. **RSI (Relative Strength Index)** - `docs/patterns and indicators/indicators/rsi.md`
   - **Implemented**: Sprint 68
   - **Variants**: 1 (14-period default)
   - **Category**: momentum
   - **Display Order**: 40
   - **Key Topics**: Overbought/oversold levels (70/30), divergence detection, momentum shifts
   - **Estimated Time**: 1-1.5 hours

4. **MACD (Moving Average Convergence Divergence)** - `docs/patterns and indicators/indicators/macd.md`
   - **Implemented**: Sprint 68
   - **Variants**: 1 (12/26/9 default)
   - **Category**: indicator
   - **Display Order**: 50
   - **Key Topics**: Signal line, histogram, crossover signals, trend strength
   - **Estimated Time**: 1-1.5 hours

5. **Bollinger Bands** - `docs/patterns and indicators/indicators/bollinger_bands.md`
   - **Implemented**: Sprint 70
   - **Variants**: 1 (20-period, 2 SD default)
   - **Category**: volatility
   - **Display Order**: 31
   - **Key Topics**: Squeeze/expansion, %B calculation, bandwidth, mean reversion
   - **Estimated Time**: 1-1.5 hours

6. **Stochastic Oscillator** - `docs/patterns and indicators/indicators/stochastic.md`
   - **Implemented**: Sprint 70
   - **Variants**: 1 (14-period default)
   - **Category**: momentum
   - **Display Order**: 41
   - **Key Topics**: %K/%D lines, overbought/oversold (80/20), crossover signals
   - **Estimated Time**: 1-1.5 hours

7. **ATR (Average True Range)** - `docs/patterns and indicators/indicators/atr.md`
   - **Implemented**: Sprint 70
   - **Variants**: 1 (14-period default)
   - **Category**: volatility
   - **Display Order**: 30
   - **Key Topics**: True range calculation, Wilder's smoothing, stop-loss placement, position sizing
   - **Estimated Time**: 1-1.5 hours

8. **ADX (Average Directional Index)** - `docs/patterns and indicators/indicators/adx.md`
   - **Implemented**: Sprint 70
   - **Variants**: 1 (14-period default)
   - **Category**: directional
   - **Display Order**: 51
   - **Key Topics**: ADX/+DI/-DI lines, trend strength classification, directional movement
   - **Estimated Time**: 1-1.5 hours

---

### Phase 0B: Database Cleanup (2-3 hours)

**Goal**: Remove legacy/test indicator definitions NOT in Table 1

**Legacy Indicators to DELETE** (16 total):

| Name | Reason | Status |
|------|--------|--------|
| ATR | Old capitalization (we have 'atr') | Disabled |
| Stochastic | Old capitalization (we have 'stochastic') | Disabled |
| Williams_R | Not in Table 1 | Disabled |
| CCI | Not in Table 1 | Disabled |
| OBV | Not in Table 1 | Disabled |
| VWAP | Old capitalization (adding 'vwap' in Sprint 78B) | Disabled |
| Relative_Strength_SPY | Not in Table 1 | Disabled |
| Relative_Strength_QQQ | Not in Table 1 | Disabled |
| SMA5 | Old naming (we have 'sma_5') | Disabled |
| ema | Incomplete variant (we have 'ema_5', etc.) | Disabled |
| sma | Incomplete variant (we have 'sma_5', etc.) | Disabled |
| Volume_SMA | Not in Table 1 (adding 'volume' in Sprint 78B) | Disabled |
| RSI_hourly | Timeframe-specific (use timeframe column) | Disabled |
| RSI_intraday | Timeframe-specific (use timeframe column) | Disabled |
| SMA_5 | Old naming with underscore | Disabled |
| AlwaysTrue | Test indicator | Disabled |

**Cleanup Steps**:

1. **Verify Current State**:
```sql
-- List all indicator definitions
SELECT name, category, display_order, enabled, class_name
FROM indicator_definitions
ORDER BY enabled DESC, display_order;

-- Expected: 18 enabled + 16 disabled
```

2. **Delete Legacy Indicators**:
```sql
-- Delete legacy indicators (PERMANENT - cannot be undone)
DELETE FROM indicator_definitions
WHERE name IN (
  'ATR', 'Stochastic', 'Williams_R', 'CCI', 'OBV', 'VWAP',
  'Relative_Strength_SPY', 'Relative_Strength_QQQ',
  'SMA5', 'ema', 'sma', 'Volume_SMA',
  'RSI_hourly', 'RSI_intraday', 'SMA_5', 'AlwaysTrue'
);

-- Expected: 16 rows deleted
```

3. **Verify Clean State**:
```sql
-- Verify only Table 1 indicators remain
SELECT name, category, display_order, enabled
FROM indicator_definitions
WHERE enabled = true
ORDER BY display_order;

-- Expected: 18 enabled indicators
--   sma_5, sma_10, sma_20, sma_50, sma_100, sma_200 (6)
--   ema_5, ema_10, ema_20, ema_50, ema_100, ema_200 (6)
--   atr, bollinger_bands (2)
--   rsi, stochastic (2)
--   macd (1)
--   adx (1 - bonus)
```

4. **Check for Orphaned Data** (informational only):
```sql
-- Check if any indicator data exists for deleted indicators
SELECT DISTINCT indicator_type, COUNT(*) as record_count
FROM daily_indicators
WHERE indicator_type IN (
  'Williams_R', 'CCI', 'OBV', 'VWAP', 'Relative_Strength_SPY',
  'Relative_Strength_QQQ', 'SMA5', 'Volume_SMA', 'AlwaysTrue'
)
GROUP BY indicator_type
ORDER BY record_count DESC;

-- Do NOT delete indicator data - preserve historical records
-- Document findings in SPRINT78A_COMPLETE.md
```

5. **Document Cleanup**:
   - List of deleted indicators in SPRINT78A_COMPLETE.md
   - Reason for each deletion
   - Any orphaned data discovered (but not deleted)

---

## Documentation Template

All indicator documentation must follow `TEMPLATE_INDICATOR.md` structure:

### Required Sections (520 lines typical):

1. **Header** (Lines 1-10)
   - Indicator name, creation date, category, display order, implementation path

2. **Overview** (Lines 10-30)
   - Description, formula, interpretation, typical range, parameters

3. **Storage Schema** (Lines 30-60)
   - Table: daily_indicators
   - Columns: symbol, indicator_type, value_data, calculation_timestamp, timeframe, metadata
   - Persistence Pattern: DELETE + INSERT (Sprint 74)

4. **Calculation Details** (Lines 60-130)
   - Data requirements (minimum bars)
   - Step-by-step calculation
   - Pandas implementation with full code example

5. **Dependencies** (Lines 130-160)
   - Requires: Processing order dependencies
   - Used By: Downstream dependencies
   - Database Definition: INSERT statement for indicator_definitions table

6. **Validation Rules** (Lines 160-180)
   - Data quality checks
   - Calculation validation
   - Regression testing approach

7. **Error Handling & Logging** (Lines 180-210)
   - Insufficient data handling
   - Calculation error handling
   - Data gap warnings

8. **Performance Targets** (Lines 210-220)
   - Calculation time (<10ms target)
   - Data fetch time (<50ms)
   - Total update time (<100ms)

9. **Testing** (Lines 220-250)
   - Unit test examples (pytest format)
   - Integration test approach
   - Edge cases to test

10. **References** (Lines 250-260)
    - Technical documentation links
    - Code reference paths
    - Related indicator documentation

11. **Document Status** (Lines 260-270)
    - Version, last updated, status, sprint reference

---

## Success Criteria

### Phase 0A Completion:
- ✅ 8 indicator documentation files created (following template structure)
- ✅ Total: ~4,160 lines of documentation
- ✅ All existing implementations documented with:
  - Complete calculation formulas
  - Code examples from actual implementations
  - Database definitions matching current state
  - Performance targets and testing approaches

### Phase 0B Completion:
- ✅ 16 legacy/test indicators deleted from indicator_definitions table
- ✅ Verification query shows 18 enabled indicators (clean state)
- ✅ No indicator data deleted (historical preservation)
- ✅ Cleanup documented in SPRINT78A_COMPLETE.md
- ✅ Zero regressions (pattern flow tests still pass)

### Overall Sprint 78A:
- ✅ Clean, well-documented codebase
- ✅ Foundation ready for Sprint 78B (implement 4 new indicators)
- ✅ Documentation standards established for future work

---

## Dependencies

### Prerequisites (Before Starting Sprint 78A):
- ✅ Table 1 master document updated (Fibonacci Pivots added)
- ✅ TEMPLATE_INDICATOR.md template reviewed
- ✅ Access to Sprint 68, 70, 74 implementation code for reference

### Blockers:
- None - Phase 0A and 0B are independent of Sprint 78B

### Enables:
- **Sprint 78B**: Clean foundation for implementing Volume, VWAP, Pivot Points (Standard), Pivot Points (Fibonacci)

---

## Testing Strategy

### Phase 0A Testing:
- **Documentation Review**: Each file reviewed for completeness (checklist-based)
- **Code Cross-Reference**: Verify formulas match actual implementation
- **Link Validation**: All code path references are valid

### Phase 0B Testing:
- **Pre-Cleanup Verification**:
  ```bash
  # Count indicators before cleanup
  python -c "from src.analysis.indicators.loader import get_available_indicators; print(len(get_available_indicators()))"
  # Expected: 18 enabled indicators loaded
  ```

- **Post-Cleanup Verification**:
  ```sql
  -- Verify 16 deleted, 18 remain
  SELECT COUNT(*) FROM indicator_definitions WHERE enabled = true;
  -- Expected: 18

  SELECT COUNT(*) FROM indicator_definitions WHERE enabled = false;
  -- Expected: 0
  ```

- **Integration Tests**:
  ```bash
  # Run pattern flow tests to ensure no regressions
  python run_tests.py
  # Expected: All tests pass (zero regressions)
  ```

---

## Risk Assessment

### Low Risk:
- Documentation creation (no code changes)
- Database cleanup of disabled indicators (already not in use)

### Medium Risk:
- Time estimation (8-10 hours for documentation may vary)
- Undiscovered dependencies on deleted indicators

### Mitigation:
- Start with Phase 0B verification queries before deletion
- Run integration tests after cleanup to catch regressions
- Keep detailed cleanup log for potential rollback

---

## Deliverables

### Documentation (Phase 0A):
1. `docs/patterns and indicators/indicators/sma.md` (~520 lines)
2. `docs/patterns and indicators/indicators/ema.md` (~520 lines)
3. `docs/patterns and indicators/indicators/rsi.md` (~520 lines)
4. `docs/patterns and indicators/indicators/macd.md` (~520 lines)
5. `docs/patterns and indicators/indicators/bollinger_bands.md` (~520 lines)
6. `docs/patterns and indicators/indicators/stochastic.md` (~520 lines)
7. `docs/patterns and indicators/indicators/atr.md` (~520 lines)
8. `docs/patterns and indicators/indicators/adx.md` (~520 lines)

**Total**: 8 files, ~4,160 lines

### Database Changes (Phase 0B):
- 16 legacy indicators deleted from indicator_definitions table
- Clean state: 18 enabled indicators

### Completion Summary:
- `docs/planning/sprints/sprint78/SPRINT78A_COMPLETE.md`
  - Documentation created
  - Database cleanup performed
  - Verification results
  - Any issues encountered
  - Readiness for Sprint 78B

---

## Validation Checklist

### Pre-Sprint
- [ ] Sprint 78A plan reviewed and approved
- [ ] TEMPLATE_INDICATOR.md structure understood
- [ ] Sprint 68, 70, 74 implementation code accessible
- [ ] Database access confirmed for cleanup queries

### During Phase 0A (Documentation)
- [ ] SMA documentation complete and reviewed
- [ ] EMA documentation complete and reviewed
- [ ] RSI documentation complete and reviewed
- [ ] MACD documentation complete and reviewed
- [ ] Bollinger Bands documentation complete and reviewed
- [ ] Stochastic documentation complete and reviewed
- [ ] ATR documentation complete and reviewed
- [ ] ADX documentation complete and reviewed
- [ ] All 8 files follow template structure
- [ ] Code examples match actual implementations
- [ ] Database definitions match current state

### During Phase 0B (Cleanup)
- [ ] Pre-cleanup verification completed (18 enabled + 16 disabled)
- [ ] DELETE query executed (16 rows deleted)
- [ ] Post-cleanup verification completed (18 enabled, 0 disabled)
- [ ] Orphaned data check completed (documented, not deleted)
- [ ] Cleanup documented in SPRINT78A_COMPLETE.md

### Post-Sprint
- [ ] Pattern flow tests pass (zero regressions)
- [ ] All 8 documentation files complete (~4,160 lines)
- [ ] Database clean (18 enabled indicators)
- [ ] SPRINT78A_COMPLETE.md written
- [ ] CLAUDE.md updated with Sprint 78A status
- [ ] Ready to proceed with Sprint 78B

---

## Next Steps After Sprint 78A

**Sprint 78B** will implement 4 new indicators on this clean foundation:
1. Volume indicator (Priority 5, Swing)
2. VWAP indicator (Priority 5, Intra-day, simplified daily reset)
3. Pivot Points (Standard) (Priority 8, Swing)
4. Pivot Points (Fibonacci) (Priority 9, Swing)

**Estimated Effort for Sprint 78B**: 8-10 hours
**Total Sprint 78 Effort**: 16-20 hours (78A + 78B)

---

## Document Status

**Version**: 1.0
**Last Updated**: February 15, 2026
**Status**: 📋 **READY FOR EXECUTION**
**Parent Sprint**: Sprint 78 (Complete Table 1 Indicators)
**Successor**: Sprint 78B (Implementation)

**Next Action**: Begin Phase 0A - Document SMA indicator
