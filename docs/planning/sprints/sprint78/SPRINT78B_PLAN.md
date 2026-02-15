# Sprint 78B: Implement Final Table 1 Indicators

**Created**: February 15, 2026
**Parent Sprint**: Sprint 78 (split into 78A and 78B)
**Prerequisite**: Sprint 78A (Documentation & Cleanup) must be complete
**Sprint Goal**: Implement final 4 indicators from Table 1 to achieve 100% coverage
**Status**: 📋 PLANNING (Blocked by Sprint 78A)
**Estimated Effort**: 8-10 hours (2-3 hours per indicator)
**Estimated Completion**: February 16-17, 2026

---

## Overview

Sprint 78B is the **implementation phase** that completes Table 1 indicator coverage. This sprint builds on the clean foundation established by Sprint 78A:
- ✅ All existing indicators documented (Sprint 78A Phase 0A)
- ✅ Database cleaned of legacy definitions (Sprint 78A Phase 0B)
- ✅ 18 enabled indicators in clean state

**Sprint 78B adds 4 new indicators**:
1. **Volume** - Relative volume confirmation indicator
2. **VWAP** - Volume Weighted Average Price with daily reset
3. **Pivot Points (Standard)** - Traditional S/R levels
4. **Pivot Points (Fibonacci)** - Fibonacci-based S/R levels

**Post-Sprint 78B State**: 22 enabled indicators (100% Table 1 coverage + 2 bonus: ADX, Fibonacci Pivots)

---

## Prerequisites (Must Complete Sprint 78A First)

### Required from Sprint 78A:
- [x] 8 existing indicator documentation files created
- [ ] 16 legacy indicators deleted from database
- [ ] Verification: 18 enabled indicators (clean state)
- [ ] Pattern flow tests passing (zero regressions)
- [ ] SPRINT78A_COMPLETE.md written

**Do NOT start Sprint 78B until Sprint 78A is complete and verified.**

---

## Sprint 78B Scope

### Phase 1: Volume Indicator (2-3 hours)

**Implementation**: `src/analysis/indicators/volume/volume.py`
**Documentation**: `docs/patterns and indicators/indicators/volume.md` (already created)
**Database**: INSERT into indicator_definitions (display_order: 60)

**Calculation Logic**:
```
Relative Volume = Current Volume / SMA(Volume, period)
Signal Classification:
  - High Volume: Relative Volume > 1.5x
  - Normal Volume: 0.5x ≤ Relative Volume ≤ 1.5x
  - Low Volume: Relative Volume < 0.5x
```

**Implementation Steps**:
1. Create `src/analysis/indicators/volume/` directory
2. Create `volume.py` with VolumeIndicator class
3. Implement `@dataclass VolumeParams` with period, threshold_high, threshold_low
4. Implement `calculate()` method:
   - Calculate volume SMA baseline
   - Calculate relative volume ratio
   - Classify signal (high/normal/low)
   - Return {indicator_type, value_data, metadata}

**Return Format**:
```python
{
    "indicator_type": "volume",
    "value_data": {
        "volume": float,
        "volume_sma": float,
        "relative_volume": float,
        "signal": "high|normal|low"
    },
    "metadata": {
        "period": 20,
        "threshold_high": 1.5,
        "threshold_low": 0.5
    }
}
```

**Database Definition**:
```sql
INSERT INTO indicator_definitions
(name, display_order, category, class_name, method_name,
 instantiation_params, min_bars_required, enabled,
 short_description, display_name)
VALUES
('volume', 60, 'volume', 'VolumeIndicator', 'calculate',
 '{"period": 20, "threshold_high": 1.5, "threshold_low": 0.5}', 20, true,
 'Volume confirmation indicator with relative volume signals', 'Volume');
```

**Testing**: 15+ unit tests
- Basic relative volume calculation
- High/normal/low volume signal detection
- Insufficient data handling
- Custom threshold parameters
- Different period values

**Performance Target**: <5ms calculation time

---

### Phase 2: VWAP Indicator (2-3 hours)

**Implementation**: `src/analysis/indicators/volume/vwap.py`
**Documentation**: `docs/patterns and indicators/indicators/vwap.md` (already created)
**Database**: INSERT into indicator_definitions (display_order: 61)

**Calculation Logic**:
```
Typical Price = (High + Low + Close) / 3
VWAP = Σ(Typical Price × Volume) / Σ(Volume)
Daily reset: First bar of new day (date change)
Deviation Bands:
  Upper 1σ = VWAP + (1 × Standard Deviation)
  Upper 2σ = VWAP + (2 × Standard Deviation)
  Lower 1σ = VWAP - (1 × Standard Deviation)
  Lower 2σ = VWAP - (2 × Standard Deviation)
Includes all trading hours (pre-market, regular, after-hours)
```

**Implementation Steps**:
1. Create `vwap.py` with VWAPIndicator class
2. Implement daily grouping (no market hours restriction):
   - Use `date` column if available, else extract from `timestamp`
   - Group by date for cumulative calculations
3. Implement `calculate()` method:
   - Calculate typical price
   - Calculate cumulative VWAP per day
   - Calculate deviation bands (standard deviation)
   - Determine price position (above/at/below VWAP)
   - Return {indicator_type, value_data, metadata}

**Return Format**:
```python
{
    "indicator_type": "vwap",
    "value_data": {
        "vwap": float,
        "vwap_upper_1sd": float,
        "vwap_upper_2sd": float,
        "vwap_lower_1sd": float,
        "vwap_lower_2sd": float,
        "position": "above|at|below"
    },
    "metadata": {
        "calculation_date": str,
        "bars_in_day": int
    }
}
```

**Database Definition**:
```sql
INSERT INTO indicator_definitions
(name, display_order, category, class_name, method_name,
 instantiation_params, min_bars_required, enabled,
 short_description, display_name)
VALUES
('vwap', 61, 'volume', 'VWAPIndicator', 'calculate',
 '{}', 1, true,
 'Volume Weighted Average Price with deviation bands', 'VWAP');
```

**Testing**: 18+ unit tests
- Daily VWAP calculation
- Cumulative sum accuracy
- Deviation band calculation
- Daily reset (date change)
- Multi-day data handling
- Position relative to VWAP

**Performance Target**: <10ms calculation time

---

### Phase 3: Pivot Points (Standard) Indicator (2-3 hours)

**Implementation**: `src/analysis/indicators/directional/pivot_points.py`
**Documentation**: `docs/patterns and indicators/indicators/pivot_points.md` (already created)
**Database**: INSERT into indicator_definitions (display_order: 70)

**Calculation Logic**:
```
Standard Pivots (from prior day OHLC):
  PP = (High + Low + Close) / 3
  R1 = (2 × PP) - Low
  R2 = PP + (High - Low)
  R3 = High + 2 × (PP - Low)
  S1 = (2 × PP) - High
  S2 = PP - (High - Low)
  S3 = Low - 2 × (High - PP)
```

**Implementation Steps**:
1. Create `src/analysis/indicators/directional/` directory
2. Create `pivot_points.py` with PivotPointsIndicator class
3. Implement `calculate()` method:
   - Extract prior day's OHLC (second-to-last row)
   - Calculate PP (pivot point)
   - Calculate R1, R2, R3 (resistance levels)
   - Calculate S1, S2, S3 (support levels)
   - Return {indicator_type, value_data, metadata}

**Return Format**:
```python
{
    "indicator_type": "pivot_points",
    "value_data": {
        "pp": float,
        "r1": float,
        "r2": float,
        "r3": float,
        "s1": float,
        "s2": float,
        "s3": float
    },
    "metadata": {
        "prior_date": str,
        "prior_high": float,
        "prior_low": float,
        "prior_close": float
    }
}
```

**Database Definition**:
```sql
INSERT INTO indicator_definitions
(name, display_order, category, class_name, method_name,
 instantiation_params, min_bars_required, enabled,
 short_description, display_name)
VALUES
('pivot_points', 70, 'directional', 'PivotPointsIndicator', 'calculate',
 '{}', 2, true,
 'Standard pivot points for intra-day support/resistance levels', 'Pivot Points');
```

**Testing**: 20+ unit tests
- Standard pivot calculation
- Level ordering (R3 > R2 > R1 > PP > S1 > S2 > S3)
- Prior day data fetching
- Insufficient data handling
- Edge case: identical OHLC values

**Performance Target**: <5ms calculation time

---

### Phase 4: Pivot Points (Fibonacci) Indicator (2-3 hours)

**Implementation**: `src/analysis/indicators/directional/pivot_points_fibonacci.py`
**Documentation**: `docs/patterns and indicators/indicators/pivot_points_fibonacci.md` (already created)
**Database**: INSERT into indicator_definitions (display_order: 71)

**Calculation Logic**:
```
Fibonacci Pivots (from prior day OHLC):
  PP = (High + Low + Close) / 3
  Range = High - Low
  R1 = PP + (0.382 × Range)  # 38.2% Fibonacci
  R2 = PP + (0.618 × Range)  # 61.8% Golden Ratio
  R3 = PP + (1.000 × Range)  # 100% Extension
  S1 = PP - (0.382 × Range)  # 38.2% Fibonacci
  S2 = PP - (0.618 × Range)  # 61.8% Golden Ratio
  S3 = PP - (1.000 × Range)  # 100% Extension
```

**Implementation Steps**:
1. Create `pivot_points_fibonacci.py` with FibonacciPivotPointsIndicator class
2. Implement `calculate()` method:
   - Extract prior day's OHLC (second-to-last row)
   - Calculate PP (pivot point) - same as standard
   - Calculate Range (High - Low)
   - Calculate Fibonacci resistance levels (38.2%, 61.8%, 100%)
   - Calculate Fibonacci support levels (38.2%, 61.8%, 100%)
   - Return {indicator_type, value_data, metadata}

**Return Format**:
```python
{
    "indicator_type": "pivot_points_fibonacci",
    "value_data": {
        "pp": float,
        "r1": float,  # 38.2%
        "r2": float,  # 61.8% Golden Ratio
        "r3": float,  # 100%
        "s1": float,  # 38.2%
        "s2": float,  # 61.8% Golden Ratio
        "s3": float   # 100%
    },
    "metadata": {
        "prior_date": str,
        "prior_high": float,
        "prior_low": float,
        "prior_close": float,
        "range": float
    }
}
```

**Database Definition**:
```sql
INSERT INTO indicator_definitions
(name, display_order, category, class_name, method_name,
 instantiation_params, min_bars_required, enabled,
 short_description, display_name)
VALUES
('pivot_points_fibonacci', 71, 'directional', 'FibonacciPivotPointsIndicator', 'calculate',
 '{}', 2, true,
 'Fibonacci pivot points for intra-day support/resistance levels', 'Pivot Points (Fibonacci)');
```

**Testing**: 20+ unit tests
- Fibonacci pivot calculation
- Fibonacci ratio validation (38.2%, 61.8%, 100%)
- Golden ratio levels (R2/S2 at 61.8%)
- Level ordering
- Edge case: zero range (H=L=C)

**Performance Target**: <5ms calculation time

---

## Technical Requirements

### Architecture Compliance
All 4 indicators follow TickStockAppV2 conventions (Sprint 68):
- ✅ @dataclass parameter validation
- ✅ Returns {value, value_data, indicator_type} format
- ✅ Vectorized pandas operations
- ✅ DELETE + INSERT persistence (Sprint 74)
- ✅ <10ms calculation performance
- ✅ Comprehensive error handling
- ✅ NO FALLBACK policy

### Code Quality
- ✅ Files: Max 500 lines per file
- ✅ Functions: Max 50 lines per function
- ✅ Complexity: Cyclomatic complexity <10
- ✅ Naming: snake_case for functions/variables, PascalCase for classes

---

## Testing Strategy

### Unit Tests (73+ total)

**Volume Tests** (`tests/unit/indicators/test_volume.py`): 15+
- Basic relative volume calculation
- High volume signal detection
- Low volume signal detection
- Insufficient data handling
- Zero volume edge case
- NaN value handling
- Custom threshold parameters
- Different period values (10, 20, 50)

**VWAP Tests** (`tests/unit/indicators/test_vwap.py`): 18+
- Daily VWAP calculation
- Cumulative sum accuracy
- Deviation band calculation (1σ, 2σ)
- Daily reset (date change)
- Multi-day data handling
- Position relative to VWAP (above/at/below)
- Missing volume data

**Pivot Points Tests** (`tests/unit/indicators/test_pivot_points.py`): 20+
- Standard pivot calculation (PP, R1, R2, R3, S1, S2, S3)
- Level ordering (R3 > R2 > R1 > PP > S1 > S2 > S3)
- Prior day data fetching
- Gap handling
- Holiday/weekend handling
- Missing prior day data
- Edge case: identical OHLC values

**Fibonacci Pivot Points Tests** (`tests/unit/indicators/test_pivot_points_fibonacci.py`): 20+
- Fibonacci pivot calculation
- Fibonacci ratio validation (38.2%, 61.8%, 100%)
- Golden ratio levels (R2/S2 at 61.8%)
- Level ordering
- Range calculation
- Prior day data fetching
- Edge case: zero range (H=L=C)

### Integration Tests

**Pattern Flow Test** (existing):
```bash
python run_tests.py
# Expected: All tests pass (zero regressions)
```

**API Tests** (`tests/unit/api/test_analysis_routes.py`):
- ✅ Volume indicator in analysis response
- ✅ VWAP indicator in 1min timeframe
- ✅ Pivot Points in daily timeframe
- ✅ Fibonacci Pivot Points in daily timeframe
- ✅ All 22 indicators discoverable via /api/indicators/available

### Manual Validation

**Database Persistence**:
```sql
-- Verify Volume storage
SELECT symbol, timeframe, value_data, metadata
FROM daily_indicators
WHERE indicator_type = 'volume'
ORDER BY calculation_timestamp DESC
LIMIT 5;

-- Verify VWAP storage (1min bars)
SELECT symbol, timeframe, value_data, metadata
FROM daily_indicators
WHERE indicator_type = 'vwap' AND timeframe = '1min'
ORDER BY calculation_timestamp DESC
LIMIT 10;

-- Verify Pivot Points storage
SELECT symbol, timeframe, value_data, metadata
FROM daily_indicators
WHERE indicator_type = 'pivot_points'
ORDER BY calculation_timestamp DESC
LIMIT 5;

-- Verify Fibonacci Pivot Points storage
SELECT symbol, timeframe, value_data, metadata
FROM daily_indicators
WHERE indicator_type = 'pivot_points_fibonacci'
ORDER BY calculation_timestamp DESC
LIMIT 5;
```

**Performance Testing**:
```bash
# Time indicator calculations (should all be <10ms)
import time
from src.analysis.indicators.loader import load_indicator

indicators = ['volume', 'vwap', 'pivot_points', 'pivot_points_fibonacci']
for name in indicators:
    start = time.time()
    ind = load_indicator(name)
    result = ind.calculate(data)
    elapsed = (time.time() - start) * 1000
    print(f"{name}: {elapsed:.2f}ms")
```

---

## Success Criteria

### Functional Completeness
- ✅ 22/21 Table 1 indicators implemented (105% coverage - includes bonus ADX and Fibonacci Pivots)
- ✅ All 4 new indicators discoverable via API
- ✅ All 4 new indicators persist to database
- ✅ Real-time updates working (VWAP)

### Testing
- ✅ 73+ unit tests passing (100%)
- ✅ Pattern flow tests pass (zero regressions)
- ✅ All performance targets achieved (<10ms calculations)

### Code Quality
- ✅ All files <500 lines
- ✅ All functions <50 lines
- ✅ Cyclomatic complexity <10
- ✅ NO FALLBACK policy enforced

### Documentation
- ✅ 4 indicator documentation files (already created in preparation)
- ✅ SPRINT78B_COMPLETE.md written
- ✅ CLAUDE.md updated with Sprint 78B status

---

## Performance Targets

| Indicator | Calculation Target | Data Fetch Target | Total Target |
|-----------|-------------------|-------------------|--------------|
| Volume | <5ms | <50ms | <100ms |
| VWAP | <10ms | <50ms | <100ms |
| Pivot Points | <5ms | <20ms (2 days) | <50ms |
| Pivot Points (Fib) | <5ms | <20ms (2 days) | <50ms |

---

## Dependencies

### Sprint 78A (Prerequisite):
- ✅ 8 existing indicator documentation files created
- ✅ 16 legacy indicators deleted
- ✅ Database in clean state (18 enabled indicators)
- ✅ Pattern flow tests passing

### Code Dependencies:
- ✅ Sprint 68: AnalysisService, IndicatorLoader pattern
- ✅ Sprint 72: OHLCVDataService for prior day data (Pivot Points)
- ✅ Sprint 74: Dynamic loader infrastructure
- ✅ Sprint 74: DELETE + INSERT persistence strategy

### Data Dependencies:
- ✅ OHLCV data with volume column (daily, 1min)
- ✅ Prior day OHLC data (for Pivot Points)

---

## Database State Flow

```
Sprint 78A Complete:  18 enabled indicators (clean state)
Phase 1 (Volume):     19 enabled indicators
Phase 2 (VWAP):       20 enabled indicators
Phase 3 (Pivot Pts):  21 enabled indicators
Phase 4 (Fib Pivots): 22 enabled indicators (FINAL)
```

**Final Enabled Indicators** (22 total):
- SMA variants: sma_5, sma_10, sma_20, sma_50, sma_100, sma_200 (6)
- EMA variants: ema_5, ema_10, ema_20, ema_50, ema_100, ema_200 (6)
- Volatility: atr, bollinger_bands (2)
- Momentum: rsi, stochastic (2)
- Trend: macd, adx (2)
- Volume: volume, vwap (2)
- Directional: pivot_points, pivot_points_fibonacci (2)

---

## Validation Checklist

### Pre-Sprint
- [ ] Sprint 78A complete and verified
- [ ] Database in clean state (18 enabled indicators)
- [ ] Pattern flow tests passing
- [ ] SPRINT78A_COMPLETE.md reviewed

### During Phase 1 (Volume)
- [ ] VolumeIndicator class created
- [ ] calculate() method implemented
- [ ] Database definition inserted
- [ ] 15+ unit tests written and passing
- [ ] Performance <5ms verified

### During Phase 2 (VWAP)
- [ ] VWAPIndicator class created
- [ ] Daily reset logic implemented (no market hours)
- [ ] Deviation bands calculated correctly
- [ ] Database definition inserted
- [ ] 18+ unit tests written and passing
- [ ] Performance <10ms verified

### During Phase 3 (Pivot Points)
- [ ] PivotPointsIndicator class created
- [ ] Standard pivot formulas implemented
- [ ] Prior day data fetching working
- [ ] Database definition inserted
- [ ] 20+ unit tests written and passing
- [ ] Performance <5ms verified

### During Phase 4 (Fibonacci Pivot Points)
- [ ] FibonacciPivotPointsIndicator class created
- [ ] Fibonacci ratios (38.2%, 61.8%, 100%) implemented
- [ ] Database definition inserted
- [ ] 20+ unit tests written and passing
- [ ] Performance <5ms verified

### Post-Sprint
- [ ] Pattern flow tests pass (zero regressions)
- [ ] 73+ total tests passing
- [ ] All performance targets achieved
- [ ] Database: 22 enabled indicators verified
- [ ] All 4 indicators load via dynamic loader
- [ ] API returns all 22 indicators via /api/indicators/available
- [ ] SPRINT78B_COMPLETE.md written
- [ ] CLAUDE.md updated
- [ ] Git commits with proper messages (no AI attributions)

---

## Deliverables

### Code:
1. `src/analysis/indicators/volume/volume.py` (~200 lines)
2. `src/analysis/indicators/volume/vwap.py` (~250 lines)
3. `src/analysis/indicators/directional/pivot_points.py` (~200 lines)
4. `src/analysis/indicators/directional/pivot_points_fibonacci.py` (~200 lines)

### Tests:
1. `tests/unit/indicators/test_volume.py` (~150 lines, 15+ tests)
2. `tests/unit/indicators/test_vwap.py` (~180 lines, 18+ tests)
3. `tests/unit/indicators/test_pivot_points.py` (~200 lines, 20+ tests)
4. `tests/unit/indicators/test_pivot_points_fibonacci.py` (~200 lines, 20+ tests)

### Database:
- 4 new entries in indicator_definitions table
- Clean state: 22 enabled indicators (no disabled)

### Documentation:
- `docs/planning/sprints/sprint78/SPRINT78B_COMPLETE.md` (comprehensive summary)

---

## Next Steps After Sprint 78B

**Sprint 78 Complete!** 🎉

**Achievements**:
- 22 enabled indicators (100% Table 1 coverage + 2 bonus)
- 12 comprehensive documentation files (6,310 lines)
- Clean database (0 legacy indicators)
- 73+ unit tests passing
- All performance targets achieved

**Future Work** (Table 2 Patterns):
- Head and Shoulders (+ Inverse)
- Double Top / Double Bottom
- Triangles (Ascending, Descending, Symmetrical)
- Flags / Pennants
- Cup and Handle
- Wedges (Rising, Falling)
- Range Breakout
- V-Top / V-Bottom
- Pin Bar

---

## Document Status

**Version**: 1.0
**Last Updated**: February 15, 2026
**Status**: 📋 **READY FOR EXECUTION** (after Sprint 78A)
**Parent Sprint**: Sprint 78 (Complete Table 1 Indicators)
**Prerequisite**: Sprint 78A (Documentation & Cleanup)

**Next Action**: Wait for Sprint 78A completion, then begin Phase 1 - Volume indicator
