# Sprint 78: Complete Table 1 Indicators - Documentation, Cleanup, Implementation

**Created**: February 15, 2026
**Sprint Goal**: Document all existing indicators, clean up legacy definitions, and implement final 4 indicators from Table 1
**Status**: 🔀 **SPLIT INTO SUB-SPRINTS** (See SPRINT78A and SPRINT78B)
**Estimated Effort**: 16-20 hours total (Sprint 78A: 10-13 hours, Sprint 78B: 8-10 hours)

---

## ⚠️ IMPORTANT: This Sprint Has Been Split

Due to the large scope (16-20 hours), Sprint 78 has been divided into two sequential sub-sprints:

### 📋 Sprint 78A: Documentation & Cleanup (10-13 hours)
**Plan**: `SPRINT78A_PLAN.md`
**Status**: 📋 READY FOR EXECUTION
**Goal**: Document 8 existing indicators, delete 16 legacy indicators
**Deliverables**:
- 8 indicator documentation files (~4,160 lines)
- Clean database (18 enabled indicators, 0 disabled)
- SPRINT78A_COMPLETE.md

**Start Here**: Execute Sprint 78A first before proceeding to 78B

### 🔧 Sprint 78B: Implementation (8-10 hours)
**Plan**: `SPRINT78B_PLAN.md`
**Status**: 📋 READY (Blocked by Sprint 78A)
**Prerequisite**: Sprint 78A must be complete
**Goal**: Implement 4 new indicators (Volume, VWAP, Pivot Points, Pivot Points Fibonacci)
**Deliverables**:
- 4 indicator implementations with 73+ tests
- Final state: 22 enabled indicators
- SPRINT78B_COMPLETE.md

**Important**: Do NOT start Sprint 78B until Sprint 78A is complete and verified

---

## Why Split?

**Original Scope**: 16-20 hours in a single sprint
**Challenge**: Large scope makes progress tracking difficult
**Solution**: Split into logical phases with clear completion criteria

**Benefits**:
- ✅ Clear milestones (documentation → cleanup → implementation)
- ✅ Easier progress tracking
- ✅ Can pause between sub-sprints if needed
- ✅ Separate completion summaries for each phase

---

## Overview

This sprint has THREE major components to ensure complete documentation coverage and database hygiene:

### Part 1: Document Existing Indicators (Phase 0A)
Create comprehensive documentation for 8 already-implemented indicators (Sprints 68-70, 74) that lack formal docs:
- ❌ SMA (Simple Moving Average) - 6 variants documented in one file
- ❌ EMA (Exponential Moving Average) - 6 variants documented in one file
- ❌ RSI (Relative Strength Index)
- ❌ MACD (Moving Average Convergence Divergence)
- ❌ Bollinger Bands
- ❌ Stochastic Oscillator
- ❌ ATR (Average True Range)
- ❌ ADX (Average Directional Index) - Bonus indicator

### Part 2: Database Cleanup (Phase 0B)
Remove 16 legacy/test indicator definitions NOT in Table 1:
- Legacy: ATR, Stochastic, Williams_R, CCI, OBV, VWAP, Relative_Strength_SPY/QQQ, Volume_SMA, SMA5, sma, ema (old capitalization)
- Test: RSI_hourly, RSI_intraday, SMA_5, AlwaysTrue

### Part 3: Implement New Indicators (Phases 1-4)
Add final 4 indicators from Table 1:
- ❌ Volume - Price move confirmation (Priority 5, Swing)
- ❌ VWAP - Volume Weighted Average Price (Priority 5, Intra-day, simplified daily reset)
- ❌ Pivot Points - Standard pivots for S/R levels (Priority 8, Swing)
- ❌ Pivot Points (Fibonacci) - Fibonacci pivots for S/R levels (Priority 9, Swing)

---

## Success Criteria

### Functional Requirements
1. **Volume Indicator**
   - ✅ Calculate relative volume vs moving average
   - ✅ Identify high/low volume signals
   - ✅ Support daily timeframe
   - ✅ Store in daily_indicators table

2. **VWAP Indicator**
   - ✅ Calculate fair-value benchmark
   - ✅ Daily reset (first bar of new day, no market hours restriction)
   - ✅ Deviation bands (1σ, 2σ)
   - ✅ Support 1min timeframe
   - ✅ Includes pre-market, regular hours, after-hours data

3. **Pivot Points Indicator (Standard)**
   - ✅ Calculate standard pivots (PP, R1, R2, R3, S1, S2, S3)
   - ✅ Use prior day's OHLC
   - ✅ Support daily calculation (intra-day reference)
   - ✅ Store in daily_indicators table

4. **Pivot Points Indicator (Fibonacci)**
   - ✅ Calculate Fibonacci pivots using 38.2%, 61.8%, 100% ratios
   - ✅ Separate indicator from Standard Pivots
   - ✅ Use prior day's OHLC
   - ✅ Support daily calculation (intra-day reference)
   - ✅ Store in daily_indicators table

### Technical Requirements
- ✅ All indicators follow TickStockAppV2 conventions (Sprint 68)
- ✅ @dataclass parameter validation
- ✅ Returns {value, value_data, indicator_type} format
- ✅ Vectorized pandas operations
- ✅ <10ms calculation performance
- ✅ Database definitions in indicator_definitions table
- ✅ DELETE + INSERT persistence strategy
- ✅ Comprehensive unit tests (15+ per indicator)

### Documentation Requirements
- ✅ Create volume.md with calculation instructions
- ✅ Create vwap.md with session-based logic
- ✅ Create pivot_points.md with S/R level formulas
- ✅ Update SPRINT78_COMPLETE.md with results

---

## Implementation Plan

### Phase 0A: Document Existing Indicators (8-10 hours)

**Goal**: Create comprehensive documentation for all 8 already-implemented indicators

**Indicators to Document**:
1. **SMA (Simple Moving Average)** - `docs/patterns and indicators/indicators/sma.md`
   - Cover all 6 variants (5, 10, 20, 50, 100, 200 periods)
   - Calculation formula, use cases, crossover strategies
   - Sprint 68/74 implementation reference

2. **EMA (Exponential Moving Average)** - `docs/patterns and indicators/indicators/ema.md`
   - Cover all 6 variants (5, 10, 20, 50, 100, 200 periods)
   - Wilder's smoothing method, comparison to SMA
   - Sprint 70 implementation reference

3. **RSI (Relative Strength Index)** - `docs/patterns and indicators/indicators/rsi.md`
   - 14-period default, overbought/oversold levels (70/30)
   - Divergence detection, calculation steps
   - Sprint 68 implementation reference

4. **MACD (Moving Average Convergence Divergence)** - `docs/patterns and indicators/indicators/macd.md`
   - 12/26/9 parameters, signal line, histogram
   - Crossover signals, trend strength interpretation
   - Sprint 68 implementation reference

5. **Bollinger Bands** - `docs/patterns and indicators/indicators/bollinger_bands.md`
   - 20-period SMA, 2 standard deviation bands
   - Squeeze/expansion, %B calculation, bandwidth
   - Sprint 70 implementation reference

6. **Stochastic Oscillator** - `docs/patterns and indicators/indicators/stochastic.md`
   - %K and %D lines, 14-period default
   - Overbought/oversold (80/20), crossover signals
   - Sprint 70 implementation reference

7. **ATR (Average True Range)** - `docs/patterns and indicators/indicators/atr.md`
   - 14-period default, Wilder's smoothing
   - Volatility measurement, stop-loss placement
   - Sprint 70 implementation reference

8. **ADX (Average Directional Index)** - `docs/patterns and indicators/indicators/adx.md`
   - ADX, +DI, -DI lines, 14-period default
   - Trend strength classification, directional movement
   - Sprint 70 implementation reference

**Documentation Template**: Follow `TEMPLATE_INDICATOR.md` structure (520 lines each)
- Overview (formula, interpretation, parameters)
- Storage Schema (daily_indicators table, DELETE + INSERT)
- Calculation Details (step-by-step, pandas implementation)
- Dependencies (processing order)
- Validation Rules (data quality, calculation validation)
- Error Handling & Logging
- Performance Targets
- Testing (unit tests, integration tests)
- References (technical documentation, code references)

**Expected Output**: 8 files, ~4,160 total lines

**Estimated Time**: 8-10 hours (1-1.5 hours per indicator)

---

### Phase 0B: Database Cleanup (2-3 hours)

**Goal**: Remove legacy/test indicator definitions NOT in Table 1

**Legacy Indicators to DELETE** (16 total):
```sql
-- Delete legacy indicators (old capitalization, duplicates)
DELETE FROM indicator_definitions
WHERE name IN (
  'ATR',              -- Old capitalization (we have 'atr')
  'Stochastic',       -- Old capitalization (we have 'stochastic')
  'Williams_R',       -- Not in Table 1
  'CCI',              -- Not in Table 1
  'OBV',              -- Not in Table 1
  'VWAP',             -- Old capitalization (we'll add 'vwap' in Phase 2)
  'Relative_Strength_SPY',  -- Not in Table 1
  'Relative_Strength_QQQ',  -- Not in Table 1
  'SMA5',             -- Old naming (we have 'sma_5')
  'ema',              -- Incomplete variant (we have 'ema_5', etc.)
  'sma',              -- Incomplete variant (we have 'sma_5', etc.)
  'Volume_SMA',       -- Not in Table 1 (we'll add 'volume' in Phase 1)
  'RSI_hourly',       -- Timeframe-specific (use timeframe column instead)
  'RSI_intraday',     -- Timeframe-specific (use timeframe column instead)
  'SMA_5',            -- Old naming with underscore
  'AlwaysTrue'        -- Test indicator
);
```

**Verification**:
```sql
-- Verify only Table 1 indicators remain
SELECT name, category, display_order, enabled
FROM indicator_definitions
WHERE enabled = true
ORDER BY display_order;

-- Expected: 18 enabled indicators
--   12 SMA/EMA variants
--   1 RSI
--   1 MACD
--   1 Bollinger Bands
--   1 Stochastic
--   1 ATR
--   1 ADX (bonus, not in Table 1 but keep)
```

**Data Cleanup**:
```sql
-- Check if any indicator data exists for deleted indicators
SELECT DISTINCT indicator_type
FROM daily_indicators
WHERE indicator_type IN (
  'Williams_R', 'CCI', 'OBV', 'VWAP', 'Relative_Strength_SPY',
  'Relative_Strength_QQQ', 'SMA5', 'Volume_SMA', 'AlwaysTrue'
)
LIMIT 100;

-- If data exists, document in SPRINT78_COMPLETE.md
-- Do NOT delete indicator data (preserve historical records)
```

**Expected Outcome**: 18 enabled indicators (clean state before adding 4 new)

**Estimated Time**: 2-3 hours (includes verification and documentation)

---

### Phase 1: Volume Indicator (2-3 hours)

**Calculation Logic**:
```
Relative Volume = Current Volume / SMA(Volume, period)
High Volume = Relative Volume > threshold (default 1.5x)
Low Volume = Relative Volume < threshold (default 0.5x)
```

**Implementation Steps**:
1. Create `src/analysis/indicators/volume/volume.py`
2. Add VolumeIndicator class with @dataclass params
3. Implement calculate() method
   - Calculate volume SMA baseline
   - Calculate relative volume ratio
   - Identify high/low volume signals
4. Return format:
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
           "period": int,
           "threshold_high": float,
           "threshold_low": float
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

**Testing**:
- 15+ unit tests
- High volume detection
- Low volume detection
- Insufficient data handling
- Edge cases (zero volume, NaN values)

---

### Phase 2: VWAP Indicator (2-3 hours)

**Calculation Logic**:
```
VWAP = Σ(Price × Volume) / Σ(Volume)
Price = (High + Low + Close) / 3  (typical price)
Daily reset: First bar of new day (date change)
Deviation Bands:
  VWAP + 1σ, VWAP + 2σ (upper bands)
  VWAP - 1σ, VWAP - 2σ (lower bands)
Includes all trading hours (pre-market, regular, after-hours)
```

**Implementation Steps**:
1. Create `src/analysis/indicators/volume/vwap.py`
2. Add VWAPIndicator class with daily reset logic
3. Implement calculate() method
   - Extract date for daily grouping (no market hours restriction)
   - Calculate cumulative VWAP per day
   - Calculate deviation bands
4. Handle real-time updates (1min bars)
5. Return format:
   ```python
   {
       "indicator_type": "vwap",
       "value_data": {
           "vwap": float,
           "vwap_upper_1sd": float,
           "vwap_upper_2sd": float,
           "vwap_lower_1sd": float,
           "vwap_lower_2sd": float,
           "position": "above|at|below"  # Price relative to VWAP
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

**Testing**:
- 18+ unit tests
- Session boundary detection
- Cumulative calculation
- Deviation band accuracy
- Real-time update scenarios
- Market open/close handling

---

### Phase 3: Pivot Points Indicator (2-3 hours)

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

Fibonacci Pivots (optional):
  R1 = PP + 0.382 × (High - Low)
  R2 = PP + 0.618 × (High - Low)
  R3 = PP + 1.000 × (High - Low)
  S1 = PP - 0.382 × (High - Low)
  S2 = PP - 0.618 × (High - Low)
  S3 = PP - 1.000 × (High - Low)
```

**Implementation Steps**:
1. Create `src/analysis/indicators/directional/pivot_points.py`
2. Add PivotPointsIndicator class
3. Implement calculate() method
   - Fetch prior day's OHLC
   - Calculate standard pivots
   - Optional: Calculate Fibonacci pivots
4. Return format:
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
           "s3": float,
           "variant": "standard|fibonacci"
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
 '{"variant": "standard"}', 2, true,
 'Daily support/resistance levels for intra-day trading', 'Pivot Points');
```

**Testing**:
- 20+ unit tests
- Standard pivot calculation
- Prior day data fetching
- Edge cases (gaps, holidays, missing data)

---

### Phase 4: Pivot Points (Fibonacci) Indicator (2-3 hours)

**Calculation Logic**:
```
Fibonacci Pivots (from prior day OHLC):
  PP = (High + Low + Close) / 3
  Range = High - Low
  R1 = PP + (0.382 × Range)
  R2 = PP + (0.618 × Range)  # Golden Ratio
  R3 = PP + (1.000 × Range)
  S1 = PP - (0.382 × Range)
  S2 = PP - (0.618 × Range)  # Golden Ratio
  S3 = PP - (1.000 × Range)
```

**Implementation Steps**:
1. Create `src/analysis/indicators/directional/pivot_points_fibonacci.py`
2. Add FibonacciPivotPointsIndicator class
3. Implement calculate() method
   - Fetch prior day's OHLC
   - Calculate Fibonacci pivots using ratios
4. Return format:
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

**Testing**:
- 20+ unit tests
- Fibonacci ratio validation (38.2%, 61.8%, 100%)
- Golden ratio levels (R2/S2)
- Prior day data fetching
- Edge cases (zero range, gaps, missing data)

---

## Database Updates

### 1. Clean Up Old Definitions

**Disable/Remove Redundant Entries**:
```sql
-- Check for any old/test volume indicators
SELECT name, enabled, class_name FROM indicator_definitions
WHERE name LIKE '%volume%' OR name LIKE '%vwap%' OR name LIKE '%pivot%';

-- Disable any legacy entries
UPDATE indicator_definitions
SET enabled = false
WHERE name IN ('old_volume', 'test_vwap', 'legacy_pivot')
  AND enabled = true;
```

### 2. Insert New Definitions

Execute SQL from Phase 1-4 implementation steps to add:
- `volume` (display_order: 60, category: volume)
- `vwap` (display_order: 61, category: volume)
- `pivot_points` (display_order: 70, category: directional)
- `pivot_points_fibonacci` (display_order: 71, category: directional)

### 3. Verify Definitions

```sql
-- Verify all Table 1 indicators are present
SELECT name, category, display_order, enabled
FROM indicator_definitions
WHERE enabled = true
ORDER BY display_order;

-- Expected count: 22 indicators
--   12 SMA/EMA variants
--   1 RSI
--   1 MACD
--   1 Bollinger Bands
--   1 Stochastic
--   1 ATR
--   1 ADX (bonus from Sprint 70)
--   4 new (Volume, VWAP, Pivot Points, Pivot Points Fibonacci)
```

---

## Processing Logic Updates

### 1. AnalysisService Integration

**File**: `src/api/services/analysis_service.py`

No changes required - dynamic loader will automatically pick up new indicators from database definitions.

**Verification**:
```python
# Test that new indicators are loaded
from src.analysis.indicators.loader import get_available_indicators

indicators = get_available_indicators()
assert 'volume' in indicators
assert 'vwap' in indicators
assert 'pivot_points' in indicators
```

### 2. Real-Time Updates (VWAP Session Handling)

**File**: `src/redis/redis_event_subscriber.py`

Add session boundary detection for VWAP:
```python
def _is_market_open_event(self, bar_data):
    """Detect market open (9:30 AM ET) for VWAP session reset."""
    timestamp = bar_data.get('timestamp')
    if timestamp:
        market_time = timestamp.astimezone(pytz.timezone('America/New_York'))
        return market_time.hour == 9 and market_time.minute == 30
    return False
```

**Integration**:
- VWAP recalculates on every 1min bar
- Session state maintained in metadata
- Cumulative sums reset at market open

### 3. Timeframe Support

**Volume**: Daily only (matches Table 1)
**VWAP**: 1min only (intra-day session-based)
**Pivot Points**: Daily calculation (used for intra-day reference)

---

## Testing Strategy

### Unit Tests (73+ total)

**Volume Tests** (`tests/unit/indicators/test_volume.py`):
- ✅ Basic relative volume calculation
- ✅ High volume signal detection
- ✅ Low volume signal detection
- ✅ Insufficient data handling
- ✅ Zero volume edge case
- ✅ NaN value handling
- ✅ Custom threshold parameters
- ✅ Different period values (10, 20, 50)

**VWAP Tests** (`tests/unit/indicators/test_vwap.py`):
- ✅ Daily VWAP calculation
- ✅ Cumulative sum accuracy
- ✅ Deviation band calculation (1σ, 2σ)
- ✅ Daily reset (date change)
- ✅ Multi-day data handling
- ✅ Intra-day updates
- ✅ Position relative to VWAP (above/at/below)
- ✅ Missing volume data

**Pivot Points Tests** (`tests/unit/indicators/test_pivot_points.py`):
- ✅ Standard pivot calculation (PP, R1, R2, R3, S1, S2, S3)
- ✅ Prior day data fetching
- ✅ Gap handling
- ✅ Holiday/weekend handling
- ✅ Missing prior day data
- ✅ Edge case: identical OHLC values

**Fibonacci Pivot Points Tests** (`tests/unit/indicators/test_pivot_points_fibonacci.py`):
- ✅ Fibonacci pivot calculation (PP, R1, R2, R3, S1, S2, S3)
- ✅ Fibonacci ratio validation (38.2%, 61.8%, 100%)
- ✅ Golden ratio levels (R2/S2 at 61.8%)
- ✅ Prior day data fetching
- ✅ Range calculation
- ✅ Gap handling
- ✅ Missing prior day data
- ✅ Edge case: zero range (H=L=C)

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
# Time indicator calculations
import time
from src.analysis.indicators.loader import load_indicator

# Volume (should be <10ms)
start = time.time()
volume_ind = load_indicator('volume')
result = volume_ind.calculate(data)
print(f"Volume: {(time.time() - start) * 1000:.2f}ms")

# VWAP (should be <10ms)
start = time.time()
vwap_ind = load_indicator('vwap')
result = vwap_ind.calculate(data)
print(f"VWAP: {(time.time() - start) * 1000:.2f}ms")

# Pivot Points (should be <10ms)
start = time.time()
pivot_ind = load_indicator('pivot_points')
result = pivot_ind.calculate(data)
print(f"Pivot Points: {(time.time() - start) * 1000:.2f}ms")

# Fibonacci Pivot Points (should be <10ms)
start = time.time()
fib_pivot_ind = load_indicator('pivot_points_fibonacci')
result = fib_pivot_ind.calculate(data)
print(f"Fibonacci Pivot Points: {(time.time() - start) * 1000:.2f}ms")
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Volume calculation | <5ms | Simple SMA + ratio |
| VWAP calculation | <10ms | Cumulative sum with deviation bands |
| Pivot Points calculation | <5ms | 7 arithmetic operations |
| Database fetch (prior day) | <20ms | For Pivot Points |
| DELETE + INSERT | <20ms | Persistence operation |

---

## Dependencies

### Code Dependencies
- ✅ Sprint 68: AnalysisService, IndicatorLoader pattern
- ✅ Sprint 72: OHLCVDataService for prior day data (Pivot Points)
- ✅ Sprint 74: Dynamic loader infrastructure
- ✅ Sprint 74: DELETE + INSERT persistence strategy

### Data Dependencies
- ✅ OHLCV data with volume column (daily, 1min)
- ✅ Prior day OHLC data (for Pivot Points)
- ✅ Session timestamps (for VWAP reset)

### External Libraries
- pandas (existing)
- numpy (existing)
- pytz (for timezone handling in VWAP)

---

## Documentation Updates

### Create New Indicator Documentation

**Files to Create**:
1. `docs/patterns and indicators/indicators/volume.md` (520 lines, following TEMPLATE_INDICATOR.md)
2. `docs/patterns and indicators/indicators/vwap.md` (550 lines, daily reset logic)
3. `docs/patterns and indicators/indicators/pivot_points.md` (540 lines, standard S/R levels)
4. `docs/patterns and indicators/indicators/pivot_points_fibonacci.md` (540 lines, Fibonacci S/R levels)

**Content Structure** (per TEMPLATE_INDICATOR.md):
- Overview (description, formula, interpretation, parameters)
- Storage Schema (daily_indicators table, DELETE + INSERT pattern)
- Calculation Details (step-by-step, pandas implementation)
- Dependencies (requires only OHLCV data)
- Validation Rules (data quality, calculation validation)
- Error Handling & Logging
- Performance Targets
- Testing (unit tests, integration tests)
- References (technical documentation, code references)

### Update Sprint Documentation

**File**: `docs/planning/sprints/sprint78/SPRINT78_COMPLETE.md`

Include:
- Implementation results (3 indicators added)
- Test results (53+ tests, 100% passing)
- Performance metrics (actual vs targets)
- Database state (21 enabled indicators)
- Lessons learned
- Next steps (Table 2 patterns in future sprint)

### Update CLAUDE.md

Add Sprint 78 section with:
- Status: COMPLETE ✅
- Date: February 15, 2026
- Summary: Completed Table 1 indicators (Volume, VWAP, Pivot Points)
- Testing: 53+ tests passing
- Performance: All targets achieved

---

## Risk Assessment

### Low Risk
- Volume indicator - Simple calculation, well-documented
- Pivot Points - Standard formulas, no edge cases

### Medium Risk
- VWAP session handling - Market open detection, timezone handling
- Mitigation: Comprehensive session boundary tests, pytz for timezone

### Technical Debt
- None introduced - follows established patterns from Sprints 68-74

---

## Success Metrics

### Code Quality
- ✅ 100% test coverage on new indicators
- ✅ <10ms calculation performance
- ✅ Zero regressions on pattern flow tests
- ✅ All indicators follow TickStockAppV2 conventions

### Functional Completeness
- ✅ 22/21 Table 1 indicators implemented (105% coverage - includes bonus Fibonacci Pivots)
- ✅ All indicators discoverable via API
- ✅ All indicators persist to database
- ✅ Real-time updates working (VWAP)

### Documentation
- ✅ 8 existing indicator documentation files (4,160 lines) - Phase 0A
- ✅ 4 new indicator documentation files (2,150 lines) - Phases 1-4
- ✅ Total: 12 documentation files (6,310 lines)
- ✅ Sprint completion summary
- ✅ CLAUDE.md updated with Sprint 78 status

### Database Hygiene
- ✅ 16 legacy/test indicators deleted - Phase 0B
- ✅ Clean state: 18 enabled indicators before new additions
- ✅ Final state: 22 enabled indicators after Sprint 78

---

## Next Steps (Post-Sprint 78)

### Table 2 Patterns (Future Sprint)
Table 2 has 14 chart patterns for swing and intra-day traders:
- Head and Shoulders (+ Inverse)
- Double Top / Double Bottom
- Triangles (Ascending, Descending, Symmetrical)
- Flags / Pennants
- Cup and Handle
- Wedges (Rising, Falling)
- Range Breakout
- V-Top / V-Bottom
- Pin Bar

Currently implemented: 8 patterns (Sprints 68-69)
Remaining: 6+ pattern families

### Performance Optimization (If Needed)
- VWAP caching for intra-day bars
- Pivot Points daily cache (recalculate once per day)

### Advanced Features
- Fibonacci Pivot Points variant
- Woodie's Pivot Points variant
- Camarilla Pivot Points variant

---

## Validation Checklist

### Pre-Implementation
- [ ] Sprint 78 plan reviewed and approved
- [ ] Documentation templates reviewed
- [ ] Database cleanup strategy confirmed
- [ ] Master document updated (Fibonacci Pivots added to Table 1)

### During Phase 0A (Documentation)
- [ ] SMA documentation complete (~520 lines)
- [ ] EMA documentation complete (~520 lines)
- [ ] RSI documentation complete (~520 lines)
- [ ] MACD documentation complete (~520 lines)
- [ ] Bollinger Bands documentation complete (~520 lines)
- [ ] Stochastic documentation complete (~520 lines)
- [ ] ATR documentation complete (~520 lines)
- [ ] ADX documentation complete (~520 lines)
- [ ] Total: 8 files, ~4,160 lines

### During Phase 0B (Cleanup)
- [ ] 16 legacy/test indicators deleted from database
- [ ] Verification query confirms 18 enabled indicators
- [ ] No indicator data deleted (historical preservation)
- [ ] Cleanup documented in SPRINT78_COMPLETE.md

### During Phases 1-4 (Implementation)
- [ ] Phase 1: Volume indicator complete, 15+ tests passing
- [ ] Phase 2: VWAP indicator complete, 18+ tests passing
- [ ] Phase 3: Pivot Points complete, 20+ tests passing
- [ ] Phase 4: Fibonacci Pivot Points complete, 20+ tests passing
- [ ] Database definitions inserted (4 indicators)
- [ ] All indicators load via dynamic loader

### Post-Implementation
- [ ] Pattern flow tests pass (zero regressions)
- [ ] 73+ total tests passing
- [ ] Performance targets achieved
- [ ] Documentation complete (12 files total: 8 existing + 4 new)
- [ ] Database clean: 22 enabled indicators
- [ ] SPRINT78_COMPLETE.md written
- [ ] CLAUDE.md updated
- [ ] Git commits with proper messages (no AI attributions)

---

## Document Status

**Version**: 1.2
**Last Updated**: February 15, 2026
**Status**: 📋 **READY FOR REVIEW** (Major Expansion: Documentation + Cleanup + Implementation)
**Estimated Effort**: 16-20 hours
  - Phase 0A (Documentation): 8-10 hours (8 files, 4,160 lines)
  - Phase 0B (Cleanup): 2-3 hours (16 legacy indicators deleted)
  - Phases 1-4 (Implementation): 8-10 hours (4 new indicators, 73 tests)
**Estimated Completion**: February 15-17, 2026

**Changes from v1.1**:
- **Added Phase 0A**: Document all 8 existing indicators (SMA, EMA, RSI, MACD, Bollinger Bands, Stochastic, ATR, ADX)
- **Added Phase 0B**: Database cleanup - delete 16 legacy/test indicators
- **Updated Table 1**: Added Fibonacci Pivots to master document
- **Total Documentation**: 12 files (8 existing + 4 new), 6,310 lines
- **Database Hygiene**: 18 enabled indicators → clean state → 22 after implementation

**Changes from v1.0**:
- VWAP: Removed market hours restriction, simplified to daily reset
- Pivot Points: Split into two separate indicators (Standard + Fibonacci)
- Scope expanded from implementation-only to documentation + cleanup + implementation

**Next Action**: User review and approval to proceed with Phase 0A (documentation)
