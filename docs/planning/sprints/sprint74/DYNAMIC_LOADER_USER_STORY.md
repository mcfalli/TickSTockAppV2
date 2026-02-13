# Sprint 74 - Dynamic Pattern/Indicator Loader (Port from TickStockPL)

**Created**: 2026-02-12
**Status**: Planning
**Priority**: High
**Complexity**: Medium-High

---

## Executive Summary

Port the table-driven dynamic pattern/indicator loading architecture from TickStockPL to TickStockAppV2, enabling database-driven configuration of which patterns and indicators are active, eliminating hardcoded registries and providing centralized control over technical analysis capabilities.

---

## User Story

**As a** system administrator
**I want** patterns and indicators to be loaded dynamically from database tables
**So that** I can enable/disable analysis features without code changes, maintain consistent configuration between TickStockPL and TickStockAppV2, and have centralized control over which technical analysis capabilities are active.

---

## Background & Context

### Current State (TickStockAppV2)

**Hardcoded Registries**:
- `src/analysis/patterns/loader.py`: 8 patterns hardcoded in `CANDLESTICK_PATTERNS` set
- `src/analysis/indicators/loader.py`: 8 indicators hardcoded in `AVAILABLE_INDICATORS` set

**Issues**:
1. ❌ Patterns/indicators require code changes to enable/disable
2. ❌ No runtime configuration capability
3. ❌ Mismatch with database `pattern_definitions` and `indicator_definitions` tables
4. ❌ Admin UI shows all hardcoded patterns (can't filter by enabled status)
5. ❌ Inconsistent with TickStockPL architecture

### Target State (TickStockPL Architecture - PROVEN)

**Dynamic Loading System** (`src/analysis/dynamic_loader.py` - 680 lines):

```python
class DynamicPatternIndicatorLoader:
    """
    Queries database for enabled patterns/indicators by timeframe.
    Uses importlib for dynamic class instantiation.
    NO FALLBACK - Raises exceptions if loading fails.
    """

    def load_patterns_for_timeframe(self, timeframe: str):
        # Query: SELECT * FROM pattern_definitions
        #        WHERE enabled=true AND timeframe IN applicable_timeframes
        # Dynamic import: importlib.import_module(code_reference)
        # Instantiation: pattern_class(**instantiation_params)
        # Cache: patterns_<timeframe> in-memory cache

    def load_indicators_for_timeframe(self, timeframe: str):
        # Same pattern for indicators
```

**Database Tables** (Already Exist in TickStockAppV2):
- `pattern_definitions`: 25 rows (5 enabled, 20 disabled)
- `indicator_definitions`: 17 rows (8 enabled, 9 disabled)

**Key Columns**:
- `name`: Pattern/indicator name (e.g., "Doji", "RSI")
- `code_reference`: Module path (e.g., "src.analysis.patterns.candlestick.doji")
- `class_name`: Class name for importlib (e.g., "Doji", "RSI")
- `method_name`: Method to call (default: "detect" for patterns, "calculate" for indicators)
- `instantiation_params`: JSON parameters for class constructor
- `enabled`: Boolean flag (controls which are loaded)
- `applicable_timeframes`: Array of timeframes (e.g., ['daily', 'hourly'])
- `min_bars_required`: Minimum data points needed
- `display_order`: UI sorting

---

## Benefits

### 1. Configuration Flexibility ✅
- Enable/disable patterns/indicators via database UPDATE (no code deployment)
- Test new patterns on subset of symbols by toggling `enabled` flag
- A/B testing: Enable different pattern sets for different universes

### 2. Consistency with TickStockPL ✅
- Same database schema and loading mechanism
- Shared pattern/indicator definitions across both systems
- Unified configuration management

### 3. Runtime Adaptability ✅
- Admin UI automatically reflects enabled patterns/indicators
- No hardcoded lists to maintain
- Cache clearing allows runtime updates without restart

### 4. Maintainability ✅
- Single source of truth (database, not code)
- Clear separation: Database defines "what", code defines "how"
- Easier to add new patterns (DB row + class file)

### 5. Operational Control ✅
- Disable problematic patterns immediately (UPDATE query, no deployment)
- Monitor pattern performance via database queries
- Track which patterns are actually being used

---

## Implementation Phases

### Phase 1: Port Dynamic Loader (Core Infrastructure)

**File**: `src/analysis/dynamic_loader.py` (new file, ~650 lines)

**Key Features**:
- `DynamicPatternIndicatorLoader` class
- `load_patterns_for_timeframe(timeframe)` method
- `load_indicators_for_timeframe(timeframe)` method
- In-memory caching by timeframe
- NO FALLBACK error handling

**Dependencies**:
- importlib (Python stdlib)
- TickStockDatabase for DB connection
- Existing pattern/indicator classes (Sprint 68-70)

**Testing**:
- Unit tests for dynamic loading
- Cache invalidation tests
- Error handling tests (missing class, import errors)

### Phase 2: Sync Database Definitions

**Current DB State** (from earlier query):
- `pattern_definitions`: Only 5 enabled (Doji, Hammer, HeadShoulders, PriceChange, AlwaysDetected)
- Missing: engulfing, shooting_star, hanging_man, harami, morning_star, evening_star (Sprint 68-69)

**Current DB State** (indicators):
- `indicator_definitions`: 8 enabled but different names
- Missing: ema, stochastic, bollinger_bands, atr, adx (Sprint 70)

**Actions**:
1. **Insert Missing Patterns** (6 rows):
   ```sql
   INSERT INTO pattern_definitions (name, display_name, class_name, code_reference, category, enabled, min_bars_required)
   VALUES
     ('engulfing', 'Engulfing', 'EngulfingPattern', 'src.analysis.patterns.candlestick.engulfing', 'candlestick', true, 2),
     ('shooting_star', 'Shooting Star', 'ShootingStarPattern', 'src.analysis.patterns.candlestick.shooting_star', 'candlestick', true, 1),
     ('hanging_man', 'Hanging Man', 'HangingManPattern', 'src.analysis.patterns.candlestick.hanging_man', 'candlestick', true, 1),
     ('harami', 'Harami', 'HaramiPattern', 'src.analysis.patterns.candlestick.harami', 'candlestick', true, 2),
     ('morning_star', 'Morning Star', 'MorningStarPattern', 'src.analysis.patterns.candlestick.morning_star', 'candlestick', true, 3),
     ('evening_star', 'Evening Star', 'EveningStarPattern', 'src.analysis.patterns.candlestick.evening_star', 'candlestick', true, 3);
   ```

2. **Insert Missing Indicators** (5 rows):
   ```sql
   INSERT INTO indicator_definitions (name, display_name, class_name, code_reference, category, enabled, min_bars_required)
   VALUES
     ('ema', 'EMA', 'EMAIndicator', 'src.analysis.indicators.trend.ema', 'trend', true, 20),
     ('stochastic', 'Stochastic', 'StochasticIndicator', 'src.analysis.indicators.momentum.stochastic', 'momentum', true, 14),
     ('bollinger_bands', 'Bollinger Bands', 'BollingerBandsIndicator', 'src.analysis.indicators.volatility.bollinger_bands', 'volatility', true, 20),
     ('atr', 'ATR', 'ATRIndicator', 'src.analysis.indicators.volatility.atr', 'volatility', true, 14),
     ('adx', 'ADX', 'ADXIndicator', 'src.analysis.indicators.directional.adx', 'directional', true, 14);
   ```

3. **Verify Code References Match Actual Paths**:
   - Check that `code_reference` values map to real Python modules
   - Update if current file structure differs

### Phase 3: Update Loaders

**Pattern Loader** (`src/analysis/patterns/loader.py`):

**Before** (Hardcoded):
```python
CANDLESTICK_PATTERNS = {
    "doji", "hammer", "engulfing", "shooting_star",
    "hanging_man", "harami", "morning_star", "evening_star"
}

def get_available_patterns():
    return {
        "candlestick": list(CANDLESTICK_PATTERNS),
        "daily": [],
        "combo": []
    }
```

**After** (Dynamic):
```python
from src.analysis.dynamic_loader import DynamicPatternIndicatorLoader

_loader = DynamicPatternIndicatorLoader()

def get_available_patterns(timeframe='daily'):
    """Get patterns from database for specified timeframe."""
    patterns = _loader.load_patterns_for_timeframe(timeframe)

    # Group by category
    result = {}
    for name, meta in patterns.items():
        category = meta.get('category', 'other')
        if category not in result:
            result[category] = []
        result[category].append(name)

    return result

def load_pattern(pattern_name, timeframe='daily'):
    """Load specific pattern instance."""
    pattern_meta = _loader.get_pattern(timeframe, pattern_name)
    if not pattern_meta:
        raise PatternLoadError(f"Pattern {pattern_name} not found for {timeframe}")
    return pattern_meta['instance']
```

**Indicator Loader** (`src/analysis/indicators/loader.py`):
- Similar transformation for indicators
- Update `get_available_indicators()` to query database
- Update `load_indicator()` to use dynamic loader

### Phase 4: Update Services

**AnalysisService** (`src/analysis/services/analysis_service.py`):
- Replace hardcoded pattern/indicator loading with dynamic loader
- Pass timeframe to loaders
- Handle NO FALLBACK errors gracefully

**PatternDetectionService** (`src/analysis/patterns/pattern_detection_service.py`):
- Update to use dynamic loader
- Remove pattern caching (dynamic loader handles caching)

**IndicatorLoader** (`src/analysis/indicators/loader.py`):
- Similar updates for indicators

### Phase 5: Update Admin UI

**Admin Process Analysis** (`web/templates/admin/process_analysis_dashboard.html`):
- Pattern/indicator dropdowns load from database (via API)
- Show enabled status
- Display count of enabled patterns/indicators

**New Admin Endpoint** (`src/api/rest/admin_patterns_indicators.py`):
```python
@admin_patterns_bp.route("/definitions")
def get_pattern_indicator_definitions():
    """Get all pattern/indicator definitions with enabled status."""
    # Query both tables
    # Return JSON for admin UI
```

### Phase 6: Testing & Validation

**Unit Tests**:
- `tests/unit/test_dynamic_loader.py` (30+ tests)
  - Load patterns for each timeframe
  - Load indicators for each timeframe
  - Cache hit/miss scenarios
  - Error handling (missing class, import errors)
  - Database connection failures

**Integration Tests**:
- `tests/integration/test_dynamic_analysis.py`
  - End-to-end analysis with dynamically loaded patterns/indicators
  - Verify results match hardcoded approach
  - Toggle enabled flag and verify behavior change

**Regression Tests**:
- Existing Sprint 68-73 tests MUST still pass
- Admin Process Analysis (Sprint 73) MUST work with dynamic loading

---

## Architecture Decisions

### ✅ Adopt: Dynamic Loading from Database
**Rationale**:
- Proven architecture in TickStockPL (production-tested)
- Centralized configuration
- Runtime flexibility

### ✅ Adopt: NO FALLBACK Policy
**Rationale**:
- Fail fast for misconfigured patterns/indicators
- Clear error messages for debugging
- Prevents silent failures

### ⚠️ Consider: Hybrid Approach
**Option**: Keep hardcoded registries as fallback if database is unavailable?
**Decision**: **NO** - Violates NO FALLBACK policy and creates dual maintenance burden

### ✅ Adopt: In-Memory Caching
**Rationale**:
- Performance: Avoid repeated DB queries
- Pattern: Cache per timeframe
- Invalidation: Provide cache clearing API

### ✅ Adopt: Timeframe-Specific Loading
**Rationale**:
- Different patterns applicable to different timeframes (e.g., intraday vs daily)
- Database `applicable_timeframes` column supports this
- Aligns with TickStockPL pattern

---

## Database Migration

**File**: `model_migrations/sprint74_dynamic_loader.py`

**Actions**:
1. Add missing pattern definitions (6 rows)
2. Add missing indicator definitions (5 rows)
3. Update `code_reference` paths if needed
4. Set `applicable_timeframes` for each pattern/indicator
5. Add indexes on `enabled` and `applicable_timeframes` for query performance

**Rollback Plan**:
- Keep hardcoded loaders in backup branch
- Database changes are additive (INSERTs), safe to rollback

---

## Success Criteria

### Functional ✅
- [ ] All Sprint 68-70 patterns/indicators load dynamically from database
- [ ] Admin UI shows only enabled patterns/indicators
- [ ] Analysis results identical to hardcoded approach
- [ ] Cache invalidation works correctly

### Performance ✅
- [ ] First load (cache miss): <100ms per timeframe
- [ ] Cached load: <1ms
- [ ] No regression in analysis performance

### Quality ✅
- [ ] 90%+ unit test coverage on dynamic loader
- [ ] All existing tests pass (zero regressions)
- [ ] Error messages are clear and actionable

### Operational ✅
- [ ] Database UPDATE can enable/disable patterns without restart
- [ ] Clear documentation on adding new patterns/indicators
- [ ] Admin UI for viewing/editing definitions

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Database schema mismatch** | High | Audit schema, sync with TickStockPL definitions |
| **Performance regression** | Medium | Benchmark, optimize caching strategy |
| **Breaking existing tests** | High | Run full test suite after each phase |
| **Missing code references** | Medium | Validate all DB paths map to real files |
| **Cache staleness** | Low | Provide cache clear API, monitor cache hits |

---

## Timeline Estimate

| Phase | Estimated Hours | Dependencies |
|-------|----------------|--------------|
| 1. Port Dynamic Loader | 6-8 hours | None |
| 2. Sync Database Definitions | 2-3 hours | Schema audit |
| 3. Update Loaders | 4-6 hours | Phase 1 complete |
| 4. Update Services | 3-4 hours | Phase 3 complete |
| 5. Update Admin UI | 2-3 hours | Phase 4 complete |
| 6. Testing & Validation | 4-6 hours | All phases complete |
| **Total** | **21-30 hours** | Sequential execution |

---

## Out of Scope (Future Sprints)

- ❌ Admin UI for editing pattern/indicator definitions (Sprint 75)
- ❌ Performance metrics dashboard for patterns (Sprint 76)
- ❌ Pattern backtesting framework (Sprint 77)
- ❌ Custom pattern creation wizard (Sprint 78)

---

## References

### TickStockPL Files (Reference Implementation)
- `C:\Users\McDude\TickStockPL\src\analysis\dynamic_loader.py` (680 lines)
- `C:\Users\McDude\TickStockPL\src\jobs\daily_pattern_job.py` (lines 125-200)
- `C:\Users\McDude\TickStockPL\src\jobs\daily_indicator_job.py` (lines 121-200)

### TickStockAppV2 Files (To Be Updated)
- `src/analysis/patterns/loader.py` (current: hardcoded)
- `src/analysis/indicators/loader.py` (current: hardcoded)
- `src/analysis/services/analysis_service.py` (uses loaders)

### Database Tables
- `pattern_definitions` (25 rows, 5 enabled)
- `indicator_definitions` (17 rows, 8 enabled)

---

## Approval & Sign-off

**Reviewed By**: _________________
**Approved By**: _________________
**Date**: _________________

---

**Status**: ✅ Ready for Sprint Planning
