name: "Sprint 68: Core Analysis Migration - Pattern Detection & Indicator Calculation"
description: |
  Migrate pattern detection (20+ patterns), indicator calculation (15 indicators),
  and analysis engines from TickStockPL to TickStockAppV2. Establishes foundation
  for automated daily pattern/indicator analysis in Sprint 69.

---

## Goal

**Feature Goal**: Migrate TickStockPL's core analysis capabilities (patterns, indicators, analysis engines) to TickStockAppV2 to enable unified analysis platform and eliminate duplicate pattern logic maintenance.

**Deliverable**:
- 15 technical indicators migrated and tested (RSI, SMA, EMA, MACD, ATR, ADX, OBV, Stochastic, VWAP, etc.)
- 20+ candlestick/technical patterns migrated and tested (Doji, Hammer, Engulfing, Head-Shoulders, Breakout, etc.)
- AnalysisService orchestration layer with analyze_symbol() and analyze_universe()
- Dynamic pattern/indicator loading system (NO FALLBACK policy)
- Pattern registry integration (Sprint 17 compatibility)
- Database storage for pattern detections and indicator results
- 100% regression testing vs TickStockPL baseline

**Success Definition**:
- All indicators produce identical values to TickStockPL (floating point tolerance: 2 decimal places)
- All patterns detect identically to TickStockPL (same detections on same data)
- Performance: <1s per symbol for full analysis (15 indicators + 20 patterns)
- Integration tests pass with zero regressions
- 50+ unit tests pass (indicators, patterns, services)

## User Persona (if applicable)

**Target User**: TickStock Development Team (internal migration)

**Use Case**: Consolidate pattern/indicator logic into single codebase to reduce maintenance overhead and enable automated daily analysis in Sprint 69.

**User Journey**:
1. Developer triggers analysis via AnalysisService.analyze_symbol("AAPL")
2. Service loads enabled patterns/indicators from database
3. Calculates indicators first (dependency resolution)
4. Detects patterns using indicator context
5. Stores results in database
6. Returns structured analysis results

**Pain Points Addressed**:
- Duplicate pattern logic maintenance (TickStockPL + AppV2 fallback patterns)
- No automated daily pattern detection (currently disabled)
- Pattern detection debugging complexity (cross-component Redis events)
- Missing indicator calculation in AppV2 (currently relies on TickStockPL)

## Why

- **Business Value**: Consolidate 24,333 lines of analysis logic into single maintainable codebase
- **Integration**: Enables Sprint 69 background jobs (automated daily pattern/indicator calculation)
- **Performance**: Sub-second analysis per symbol (TickStockPL proven: <1ms per pattern)
- **Architecture**: Simplifies Producer/Consumer separation (AppV2 becomes analysis platform)
- **User Impact**: Unlocks automated pattern detection alerts and indicator-based screening

**Problems Solved**:
- Pattern detection currently disabled in production (requires TickStockPL which is being deprecated)
- Developers maintain duplicate logic in two codebases (TickStockPL patterns + AppV2 fallback patterns)
- Cannot add new patterns without coordinating TickStockPL + AppV2 changes
- Debugging requires cross-component Redis pub-sub tracing

## What

### Technical Requirements

**Indicators (15 total)**:
1. **Momentum**: RSI (14), Stochastic (14,3,3), ADX (14)
2. **Trend**: SMA (20,50,200), EMA (12,26), MACD (12,26,9)
3. **Volatility**: Bollinger Bands (20,2), ATR (14)
4. **Volume**: OBV, VWAP, Volume Spike Detection
5. **Custom**: RelativeStrength vs Benchmark

**Patterns (20+ total)**:
1. **Single-Bar Candlestick**: Doji, Hammer, Shooting Star, Hanging Man, Spinning Top
2. **Multi-Bar Candlestick**: Bullish/Bearish Engulfing, Morning/Evening Star, Three White Soldiers, Three Black Crows
3. **Daily Patterns**: Multi-Day Breakout, Consolidation, Double Top/Bottom, Head-Shoulders, Cup-Handle
4. **Advanced**: Weekly Breakout, Monthly Breakout, Trend Reversal

**Analysis Services**:
- `BaseIndicator` abstract class with calculate(), validate_data(), get_minimum_periods()
- `BasePattern` abstract class with detect(), validate_data(), get_minimum_bars()
- `IndicatorService` with calculate_indicator(), calculate_all_indicators()
- `PatternService` with detect_pattern(), detect_all_patterns()
- `AnalysisService` with analyze_symbol(), analyze_universe()
- Dynamic loader with importlib-based NO FALLBACK policy

**Database Integration**:
- `indicator_results` table storage (JSONB value_data field)
- `daily_patterns` table storage (pattern detections with confidence)
- `pattern_definitions` table integration (Sprint 17 registry)
- `indicator_definitions` table integration (configuration management)

### Success Criteria

- [ ] All 15 indicators calculate identically to TickStockPL baseline (±0.01 tolerance for floats)
- [ ] All 20+ patterns detect identically to TickStockPL baseline (same detection timestamps)
- [ ] Performance target: analyze_symbol() completes in <1s for 250 bars (15 indicators + 20 patterns)
- [ ] Performance target: analyze_universe() processes 500 symbols in <10 minutes (parallel processing)
- [ ] Integration tests pass: `python run_tests.py` (zero regressions)
- [ ] 50+ unit tests pass (pytest)
- [ ] Code coverage: >80% for src/analysis/ directory
- [ ] No linting errors: `ruff check src/analysis/`
- [ ] Dynamic loading works: patterns/indicators loaded from database definitions
- [ ] NO FALLBACK policy enforced: ImportError raised if pattern/indicator class not found

## All Needed Context

### Context Completeness Check

✅ **"No Prior Knowledge" Test Passed**: This PRP contains complete TickStockPL analysis architecture, exact file paths with line numbers, working code examples, database schemas, testing patterns, and critical gotchas. An implementer with no prior TickStockPL knowledge can succeed using only this PRP and codebase access.

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: TickStockAppV2
  role: Consumer + Analyzer (NEW ROLE - was Consumer-only pre-Sprint 68)

  migration_scope:
    source: C:\Users\McDude\TickStockPL\src\
    target: C:\Users\McDude\TickStockAppV2\src\analysis\
    lines_migrated: 24333 (patterns 7287 + indicators 3771 + engines 6427 + infrastructure 6848)

  redis_channels:
    # POST-MIGRATION: AppV2 will PUBLISH pattern events (reverses flow)
    - channel: "tickstock.events.patterns"
      purpose: "AppV2 publishes detected patterns (Sprint 69)"
      message_format: "{pattern_name, symbol, timeframe, confidence, detected_at, metadata}"
      direction: "AppV2 → Consumers (WebSocket clients)"

    - channel: "tickstock.events.indicators"
      purpose: "AppV2 publishes calculated indicators (Sprint 69)"
      message_format: "{indicator_type, symbol, timeframe, value, value_data, calculated_at}"
      direction: "AppV2 → Consumers"

    # Data flow remains same (TickStockPL owns historical data loading)
    - channel: "tickstock.jobs.data_load"
      purpose: "TickStockPL historical import completion events"
      message_format: "{event_type: 'data_load_complete', symbols, timeframe, run_analysis}"
      direction: "TickStockPL → AppV2 (triggers post-import analysis in Sprint 69)"

  database_access:
    mode: read-write (NEW - analysis results storage)
    tables_read:
      - ohlcv_daily (historical OHLCV data for analysis)
      - pattern_definitions (Sprint 17 registry - enabled patterns)
      - indicator_definitions (enabled indicators configuration)
      - definition_groups (universe symbols for analyze_universe)
    tables_write:
      - daily_patterns (pattern detection results)
      - indicator_results (indicator calculation results)
      - job_executions (background job tracking - Sprint 69)
    queries:
      - "SELECT * FROM ohlcv_daily WHERE symbol = %s AND timestamp >= %s ORDER BY timestamp"
      - "SELECT * FROM pattern_definitions WHERE enabled = true AND applicable_timeframes @> ARRAY[%s]"
      - "INSERT INTO daily_patterns (symbol, pattern_id, detected_at, confidence, metadata) VALUES ..."

  websocket_integration:
    broadcast_to: N/A (Sprint 68 only - WebSocket broadcasting in Sprint 69)
    message_format: N/A
    latency_target: "<100ms (Sprint 69)"

  tickstockpl_api:
    endpoints: N/A (no TickStockPL API calls in Sprint 68)
    format: N/A

  performance_targets:
    - metric: "Indicator calculation per symbol"
      target: "<500ms for 15 indicators on 250 bars"
      critical: true

    - metric: "Pattern detection per symbol"
      target: "<500ms for 20 patterns on 250 bars"
      critical: true

    - metric: "Full analysis (indicators + patterns)"
      target: "<1s per symbol"
      critical: true

    - metric: "Universe analysis (500 symbols parallel)"
      target: "<10 minutes with 10 workers"
      critical: false

    - metric: "Database write (pattern detection)"
      target: "<50ms per insert"
      critical: false

    - metric: "Dynamic module loading"
      target: "<100ms for 35 patterns/indicators"
      critical: false

  architecture_constraints:
    - "AppV2 becomes ANALYZER (new role) - calculates patterns/indicators"
    - "TickStockPL remains DATA PRODUCER - loads historical OHLCV only"
    - "NO FALLBACK policy: Missing pattern/indicator = ImportError (system fails explicitly)"
    - "Read-only OHLCV access: AppV2 reads from ohlcv_daily but NEVER writes"
    - "Pattern results storage: AppV2 writes to daily_patterns (NEW permission)"
    - "Indicator results storage: AppV2 writes to indicator_results (NEW permission)"
    - "Regression requirement: 100% identical results vs TickStockPL baseline"
```

### Documentation & References

```yaml
# CRITICAL: Read these TickStockPL files for implementation patterns

# === PATTERN DETECTION ===
- file: C:\Users\McDude\TickStockPL\src\patterns\base.py
  lines: 1-270
  why: "BasePattern abstract class - EXACT contract to implement"
  pattern: "__init__(params), detect(data), get_minimum_bars(), validate_data_format()"
  gotcha: "detect() MUST return pd.Series (boolean), NOT dict or custom object"
  critical: |
    Sprint 17 integration: set_pattern_registry_info(), calculate_confidence(),
    filter_by_confidence() - MUST implement for database integration

- file: C:\Users\McDude\TickStockPL\src\patterns\candlestick\single_bar.py
  lines: 90-166
  why: "DojiPattern implementation - simple pattern reference"
  pattern: "Vectorized detection with body_size/candle_range calculations"
  gotcha: "Use calculate_body_size(), calculate_candle_range() utility functions"
  critical: "Avoid division by zero: check candle_range >= min_range (0.01)"

- file: C:\Users\McDude\TickStockPL\src\patterns\candlestick\multi_bar.py
  lines: 62-158
  why: "BullishEngulfingPattern - multi-bar pattern with shift()"
  pattern: "Use data.shift(1) for previous bar access, NOT manual indexing"
  gotcha: "First bar always False (no previous bar for comparison)"
  critical: "Validate body sizes >= min_body (0.01) to avoid noise"

- file: C:\Users\McDude\TickStockPL\src\patterns\daily\multi_day_breakout_pattern.py
  lines: 1-437
  why: "Complex pattern with multi-phase detection"
  pattern: "Break detection into private helper methods (_detect_consolidation, _detect_breakouts)"
  gotcha: "get_minimum_bars() returns 30+ for multi-day patterns"
  critical: "Always return pd.Series even if detection fails (empty series with False)"

# === INDICATOR CALCULATION ===
- file: C:\Users\McDude\TickStockPL\src\indicators\base_indicator.py
  lines: 44-306
  why: "BaseIndicator abstract class - EXACT contract to implement"
  pattern: "calculate(data, symbol, timeframe) returns dict with 'value', 'value_data', 'metadata'"
  gotcha: "_safe_divide() utility REQUIRED for all ratio calculations (prevents div by zero)"
  critical: |
    CONVENTION: value = primary metric, value_data = all calculated values
    Example RSI: value=65.2, value_data={'rsi_14':65.2, 'signal':'neutral', 'overbought':False}

- file: C:\Users\McDude\TickStockPL\src\indicators\sma.py
  lines: 95-200
  why: "SMA implementation - simple indicator reference"
  pattern: "Use rolling(window=period, min_periods=period).mean()"
  gotcha: "Multi-period support: calculate SMA_20, SMA_50, SMA_200 in one pass"
  critical: "Detect golden/death cross if both SMA_50 and SMA_200 exist"

- file: C:\Users\McDude\TickStockPL\src\indicators\rsi.py
  lines: 103-261
  why: "RSI implementation with Wilder's smoothing"
  pattern: "ewm(alpha=1/period, adjust=False) for Wilder's smoothing (NOT span=period)"
  gotcha: "Separate gains and losses: gains = delta.clip(lower=0), losses = -delta.clip(upper=0)"
  critical: "Handle div by zero: rsi.fillna(100.0) if all losses are 0"

- file: C:\Users\McDude\TickStockPL\src\indicators\macd.py
  lines: 119-218
  why: "MACD implementation with EMA"
  pattern: "ewm(span=period, adjust=False).mean() for standard EMA"
  gotcha: "PRIMARY VALUE = MACD line (NOT histogram!) for database storage"
  critical: "Detect crossovers: histogram crosses 0 (bullish/bearish signals)"

# === ANALYSIS SERVICES ===
- file: C:\Users\McDude\TickStockPL\src\services\pattern_detection_service.py
  lines: 673-715
  why: "Orchestration pattern: indicators FIRST, then patterns"
  pattern: "process_single_symbol() calls calculate_indicators() then detect_patterns(indicators)"
  gotcha: "Patterns access indicator results via context dict for confidence adjustment"
  critical: "Cache indicator results per symbol to avoid recalculation"

- file: C:\Users\McDude\TickStockPL\src\analysis\dynamic_loader.py
  lines: 1-680
  why: "Dynamic loading system with NO FALLBACK policy"
  pattern: "importlib.import_module(code_reference) then getattr(module, class_name)"
  gotcha: "If ImportError or AttributeError, RAISE immediately (no fallback processing)"
  critical: |
    Database-driven loading:
    SELECT name, code_reference, class_name FROM pattern_definitions WHERE enabled=true
    Then: module = importlib.import_module(code_reference); cls = getattr(module, class_name)

# === DATABASE SCHEMAS ===
- file: C:\Users\McDude\TickStockPL\docs\planning\sprint_history\sprint17\implemented_sql.md
  lines: 1-200
  why: "Pattern registry schema (Sprint 17)"
  pattern: "pattern_definitions table with enabled, confidence_threshold, risk_level"
  gotcha: "applicable_timeframes is ARRAY type (use @> operator for containment checks)"
  critical: |
    CREATE TABLE pattern_definitions (
      id SERIAL PRIMARY KEY,
      name VARCHAR(100) UNIQUE,
      code_reference VARCHAR(255),  -- 'src.patterns.candlestick.doji'
      class_name VARCHAR(100),       -- 'DojiPattern'
      instantiation_params JSONB,
      confidence_threshold DECIMAL(3,2),
      enabled BOOLEAN DEFAULT true,
      applicable_timeframes VARCHAR(20)[]
    );

# === TESTING PATTERNS ===
- file: C:\Users\McDude\TickStockPL\tests\unit\patterns\test_base.py
  lines: 1-262
  why: "Base test class with OHLCV data generators"
  pattern: "create_bullish_data(), create_bearish_data(), create_specific_pattern()"
  gotcha: "CRITICAL: Ensure OHLC consistency (high = max, low = min)"
  critical: |
    self.bullish_data['high'] = self.bullish_data[['open','high','low','close']].max(axis=1)
    self.bullish_data['low'] = self.bullish_data[['open','high','low','close']].min(axis=1)

- file: C:\Users\McDude\TickStockPL\tests\unit\indicators\test_all_indicators.py
  lines: 18-93
  why: "Indicator testing patterns with validation"
  pattern: "assertAlmostEqual(result['value'], expected, places=2) for float comparison"
  gotcha: "Always validate return structure: assertIn('value', result), assertIn('value_data', result)"
  critical: "Test RSI range: assertGreaterEqual(rsi, 0), assertLessEqual(rsi, 100)"

# === EXCEPTION HANDLING ===
- file: C:\Users\McDude\TickStockPL\src\exceptions.py
  lines: 1-94
  why: "Custom exception hierarchy for analysis errors"
  pattern: "PatternDetectionError, IndicatorError, DataValidationError"
  gotcha: "Include context in exceptions: pattern_name, reason, data_info"
  critical: |
    raise PatternDetectionError(
      pattern_name=self.pattern_name,
      reason=f"Detection failed: {str(e)}",
      data_info=f"Rows: {len(data)}, Cols: {list(data.columns)}"
    )

# === EXTERNAL LIBRARIES ===
# Technical Analysis Formulas (NO library wrappers - use formulas directly)

- url: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html
  why: "Rolling window calculations for SMA, Bollinger Bands, ATR"
  critical: |
    ALWAYS use min_periods=period for strict window requirements
    Example: df['close'].rolling(window=20, min_periods=20).mean()
    Gotcha: Default min_periods=window for int, min_periods=1 for time offsets

- url: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html
  why: "Exponential weighted moving average for EMA, MACD, RSI"
  critical: |
    ALWAYS use adjust=False for standard EMA formula
    Example: df['close'].ewm(span=20, adjust=False).mean()
    Gotcha: adjust=True (default) gives weighted average, NOT standard EMA
    For Wilder's smoothing: ewm(alpha=1/period, adjust=False) NOT ewm(span=period)

- url: https://blog.quantinsti.com/rsi-indicator/
  why: "RSI calculation formula with Wilder's smoothing"
  critical: |
    Wilder's Smoothing Formula:
    avg_gain = gains.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    Gotcha: First 14 bars use simple average, then exponential smoothing

- url: https://pandas.pydata.org/docs/user_guide/enhancingperf.html
  why: "Performance optimization: vectorization vs loops"
  critical: |
    Vectorized operations: 50-100x faster than .apply()
    NEVER use .iterrows() or .apply(axis=1) in production
    Use NumPy array operations: df['close'].to_numpy() for heavy math
    Gotcha: Vectorization uses more memory (trade-off: speed vs memory)

- url: https://docs.python.org/3/library/importlib.html
  why: "Dynamic module loading with importlib"
  critical: |
    Pattern: importlib.import_module('package.module')
    Gotcha: Call importlib.invalidate_caches() for runtime-created modules
    NO FALLBACK: Raise ImportError if module not found (never silently skip)
```

### Current Codebase Tree

```bash
C:\Users\McDude\TickStockAppV2\
├── src\
│   ├── core\
│   │   └── services\
│   │       ├── breadth_metrics_service.py      # Uses rolling/ewm patterns
│   │       ├── relationship_cache.py           # Universe symbol loading
│   │       └── tickstock_database.py           # Database access layer
│   ├── data\
│   │   └── historical_loader.py                # DUPLICATE (remove in Sprint 70)
│   └── api\
│       └── routes\
│           └── admin.py                        # Admin endpoints
├── tests\
│   ├── unit\
│   │   └── (create test directories here)
│   └── integration\
│       └── run_integration_tests.py            # Integration test runner
├── docs\
│   ├── PRPs\
│   │   └── templates\
│   │       └── prp-new.md                      # This template
│   └── planning\
│       └── sprints\
│           └── sprint68\
│               ├── SPRINT68_PLAN.md            # Sprint plan reference
│               └── core-analysis-migration.md  # This PRP
└── CLAUDE.md                                    # Development guide
```

### Desired Codebase Tree

```bash
C:\Users\McDude\TickStockAppV2\
├── src\
│   ├── analysis\                                # NEW: Analysis module
│   │   ├── __init__.py
│   │   ├── exceptions.py                        # PatternDetectionError, IndicatorError
│   │   │
│   │   ├── indicators\                          # Indicator implementations
│   │   │   ├── __init__.py
│   │   │   ├── base_indicator.py                # BaseIndicator abstract class
│   │   │   ├── sma.py                           # Simple Moving Average
│   │   │   ├── ema.py                           # Exponential Moving Average
│   │   │   ├── rsi.py                           # Relative Strength Index
│   │   │   ├── macd.py                          # MACD
│   │   │   ├── bollinger_bands.py               # Bollinger Bands
│   │   │   ├── atr.py                           # Average True Range
│   │   │   ├── adx.py                           # Average Directional Index
│   │   │   ├── obv.py                           # On-Balance Volume
│   │   │   ├── stochastic.py                    # Stochastic Oscillator
│   │   │   ├── vwap.py                          # Volume Weighted Average Price
│   │   │   └── (5 more indicators)
│   │   │
│   │   ├── patterns\                            # Pattern implementations
│   │   │   ├── __init__.py
│   │   │   ├── base_pattern.py                  # BasePattern abstract class
│   │   │   │
│   │   │   ├── candlestick\                     # Candlestick patterns
│   │   │   │   ├── __init__.py
│   │   │   │   ├── single_bar.py                # Doji, Hammer, Shooting Star, Hanging Man
│   │   │   │   └── multi_bar.py                 # Engulfing, Morning/Evening Star, Three Soldiers
│   │   │   │
│   │   │   └── daily\                           # Daily/multi-day patterns
│   │   │       ├── __init__.py
│   │   │       ├── multi_day_breakout.py        # Multi-day breakout pattern
│   │   │       ├── consolidation.py             # Consolidation pattern
│   │   │       ├── double_top_bottom.py         # Double top/bottom
│   │   │       ├── head_shoulders.py            # Head and shoulders
│   │   │       └── (6 more patterns)
│   │   │
│   │   └── services\                            # Analysis orchestration
│   │       ├── __init__.py
│   │       ├── indicator_service.py             # IndicatorService
│   │       ├── pattern_service.py               # PatternService
│   │       ├── analysis_service.py              # AnalysisService (unified)
│   │       ├── dynamic_loader.py                # Dynamic pattern/indicator loading
│   │       └── pattern_registry_service.py      # Sprint 17 registry integration
│   │
│   └── core\
│       └── services\
│           └── (existing services unchanged)
│
├── tests\
│   ├── unit\
│   │   ├── analysis\                            # NEW: Analysis unit tests
│   │   │   ├── indicators\
│   │   │   │   ├── test_base_indicator.py
│   │   │   │   ├── test_sma.py
│   │   │   │   ├── test_rsi.py
│   │   │   │   └── (13 more indicator tests)
│   │   │   │
│   │   │   ├── patterns\
│   │   │   │   ├── test_base_pattern.py
│   │   │   │   ├── test_candlestick_single.py
│   │   │   │   ├── test_candlestick_multi.py
│   │   │   │   └── (18 more pattern tests)
│   │   │   │
│   │   │   └── services\
│   │   │       ├── test_indicator_service.py
│   │   │       ├── test_pattern_service.py
│   │   │       └── test_analysis_service.py
│   │   │
│   │   └── (existing unit tests unchanged)
│   │
│   └── integration\
│       ├── test_analysis_integration.py         # NEW: End-to-end analysis tests
│       ├── test_regression_vs_tickstockpl.py    # NEW: Regression validation
│       └── (existing integration tests unchanged)
│
└── docs\
    └── planning\
        └── sprints\
            └── sprint68\
                ├── SPRINT68_PLAN.md
                ├── core-analysis-migration.md       # This PRP
                ├── core-analysis-migration-RESULTS.md    # Post-execution
                └── core-analysis-migration-AMENDMENT.md  # If PRP gaps found
```

### Known Gotchas & Library Quirks

```python
# === CRITICAL: TickStock Architecture Constraints ===

# GOTCHA 1: NO FALLBACK Policy (TickStock Architecture)
# If a pattern/indicator class cannot be loaded, system FAILS explicitly
# NEVER silently skip or use fallback logic

# WRONG - Fallback pattern
try:
    pattern_class = importlib.import_module(f'src.analysis.patterns.{pattern_name}')
except ImportError:
    logger.warning(f"Pattern {pattern_name} not found, skipping...")
    return None  # WRONG: Silent failure

# CORRECT - Fail fast
try:
    pattern_module = importlib.import_module(f'src.analysis.patterns.{pattern_name}')
    pattern_class = getattr(pattern_module, class_name)
except (ImportError, AttributeError) as e:
    raise ImportError(f"Pattern '{pattern_name}' failed to load: {e}") from e

# === CRITICAL: Pandas EMA Calculation ===

# GOTCHA 2: adjust=False REQUIRED for Standard EMA
# adjust=True (default) gives weighted average, NOT standard EMA

# WRONG - Incorrect EMA (uses weighted average)
ema = df['close'].ewm(span=20).mean()  # adjust=True by default

# CORRECT - Standard EMA formula
ema = df['close'].ewm(span=20, adjust=False).mean()

# === CRITICAL: RSI Wilder's Smoothing ===

# GOTCHA 3: Wilder's Smoothing uses alpha=1/period, NOT span=period

# WRONG - Incorrect Wilder's smoothing
avg_gain = gains.ewm(span=14, adjust=False).mean()  # NOT Wilder's method

# CORRECT - Wilder's smoothing formula
avg_gain = gains.ewm(alpha=1/14, adjust=False, min_periods=14).mean()

# === CRITICAL: Division by Zero Protection ===

# GOTCHA 4: ALWAYS protect division operations

# WRONG - Will crash if avg_volume == 0
relative_volume = current_volume / avg_volume

# CORRECT - Safe division
relative_volume = current_volume / avg_volume if avg_volume > 0 else 1.0

# OR use utility method (BaseIndicator._safe_divide)
relative_volume = self._safe_divide(current_volume, avg_volume, default=1.0)

# === CRITICAL: Rolling Window min_periods ===

# GOTCHA 5: Always specify min_periods to prevent partial windows

# WRONG - First 19 values are partial averages
sma = df['close'].rolling(window=20).mean()  # min_periods defaults to 1 for offsets

# CORRECT - Only full windows calculated
sma = df['close'].rolling(window=20, min_periods=20).mean()

# === CRITICAL: DataFrame Index for Time Operations ===

# GOTCHA 6: Data MUST have DatetimeIndex for time-based operations

# WRONG - No index set
data = pd.DataFrame({"timestamp": [...], "close": [...]})
result = calculate(data)  # Fails on data.index[-1]

# CORRECT - Set DatetimeIndex
data.index = pd.to_datetime(data["timestamp"])
result = calculate(data)

# === CRITICAL: Indicator Return Convention ===

# GOTCHA 7: 'value' field MUST be PRIMARY metric, 'value_data' contains ALL values

# WRONG for MACD - Using histogram as primary
return {
    "value": histogram,  # WRONG: Histogram is derivative metric
    "value_data": {"macd": macd_line, "signal": signal_line}
}

# CORRECT - MACD line is primary metric
return {
    "value": macd_line,  # CORRECT: MACD line is primary
    "value_data": {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    }
}

# === CRITICAL: Pattern Detection Return Type ===

# GOTCHA 8: detect() MUST return pd.Series (boolean), NOT dict

# WRONG - Returns dict
def detect(self, data: pd.DataFrame) -> dict:
    return {"detected": True, "confidence": 0.85}

# CORRECT - Returns pd.Series
def detect(self, data: pd.DataFrame) -> pd.Series:
    # Vectorized detection
    detected = (body_size < threshold * candle_range)
    return detected.fillna(False).astype(bool)

# === CRITICAL: OHLC Consistency in Test Data ===

# GOTCHA 9: Test data MUST enforce OHLC consistency (high=max, low=min)

# WRONG - Inconsistent OHLC (high might be lower than close)
df = pd.DataFrame({
    'open': [100, 101],
    'high': [102, 103],  # Could be < close if random
    'low': [99, 100],
    'close': [101, 102]
})

# CORRECT - Enforce consistency
df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)

# === CRITICAL: Float Comparison in Tests ===

# GOTCHA 10: Use assertAlmostEqual for float comparisons (precision limits)

# WRONG - Exact equality check
assert result['value'] == expected_value  # May fail due to float precision

# CORRECT - Tolerance-based comparison
self.assertAlmostEqual(result['value'], expected_value, places=2)

# === CRITICAL: Vectorization Performance ===

# GOTCHA 11: NEVER use .iterrows() or .apply(axis=1) in production

# WRONG - Row-by-row iteration (740x slower)
for idx, row in df.iterrows():
    result.append(row['a'] * row['b'])

# WRONG - Apply with row-wise lambda (60x slower)
df['result'] = df.apply(lambda row: row['a'] * row['b'], axis=1)

# CORRECT - Vectorized operation
df['result'] = df['a'] * df['b']

# === CRITICAL: Multi-Bar Pattern shift() Usage ===

# GOTCHA 12: Use shift() for previous bar access, NOT manual indexing

# WRONG - Manual indexing (error-prone, non-vectorized)
for i in range(1, len(df)):
    if df['close'].iloc[i] > df['close'].iloc[i-1]:
        detected.append(True)

# CORRECT - Vectorized shift()
current_close = df['close']
prev_close = df['close'].shift(1)
detected = current_close > prev_close

# === CRITICAL: NaN Handling in Indicator Results ===

# GOTCHA 13: Check for NaN before returning indicator value

# WRONG - May return NaN to database
latest_value = sma_series.iloc[-1]
return {"value": latest_value}  # Could be NaN

# CORRECT - Validate and convert
latest_value = sma_series.iloc[-1]
return {
    "value": float(latest_value) if not pd.isna(latest_value) else None
}

# === CRITICAL: Database JSONB Field Structure ===

# GOTCHA 14: value_data stored as JSONB in database (PostgreSQL)

# Pattern definitions table uses JSONB for instantiation_params
# Indicator results use JSONB for value_data (all calculated values)
# Pattern detections use JSONB for metadata (detection context)

# Ensure value_data is JSON-serializable (NO NumPy types)
value_data = {
    "rsi_14": float(rsi_value),  # CORRECT: Convert np.float64 to Python float
    "signal": "overbought"       # CORRECT: Python str
}

# WRONG - NumPy types not JSON-serializable
value_data = {
    "rsi_14": np.float64(rsi_value),  # WRONG: Will fail JSON serialization
}

# === CRITICAL: Dynamic Module Loading Cache Invalidation ===

# GOTCHA 15: Call importlib.invalidate_caches() for runtime-created modules

# If creating modules dynamically at runtime
import importlib

# After creating/modifying a module file
importlib.invalidate_caches()

# Now import the new module
new_module = importlib.import_module('dynamically_created_pattern')

# === CRITICAL: Worker Boundary Event Type Mixing ===

# GOTCHA 16: Convert typed events to dicts before Redis pub-sub (Sprint 69)

# WRONG - Publishing typed event
pattern_event = PatternEvent(symbol="AAPL", pattern_name="Doji")
redis_client.publish("tickstock.events.patterns", pattern_event)  # Fails serialization

# CORRECT - Convert to dict before publishing
pattern_event_dict = {
    "symbol": "AAPL",
    "pattern_name": "Doji",
    "confidence": 0.85,
    "detected_at": datetime.now().isoformat()
}
redis_client.publish("tickstock.events.patterns", json.dumps(pattern_event_dict))

# === CRITICAL: Sprint 17 Pattern Registry Integration ===

# GOTCHA 17: Patterns MUST call set_pattern_registry_info() for database integration

# In BasePattern implementation:
def set_pattern_registry_info(
    self,
    pattern_id: int,
    confidence_threshold: float,
    metadata: dict[str, Any]
):
    """Link pattern to database registry (Sprint 17)."""
    self._pattern_id = pattern_id
    self._confidence_threshold = confidence_threshold
    self._registry_metadata = metadata

# Dynamic loader calls this after instantiation:
pattern_instance = pattern_class(params)
pattern_instance.set_pattern_registry_info(
    pattern_id=row['id'],
    confidence_threshold=row['confidence_threshold'],
    metadata={'risk_level': row['risk_level'], ...}
)
```

## Implementation Blueprint

### Data Models and Structure

```python
# === Indicator Parameter Dataclasses ===

from dataclasses import dataclass
from typing import Any

@dataclass
class IndicatorParams:
    """Base parameter configuration for all indicators."""
    period: int
    source: str = "close"  # OHLCV column to use

    def __post_init__(self):
        """Validate parameters after initialization."""
        if self.period <= 0:
            raise ValueError("Period must be positive")

        valid_sources = ["open", "high", "low", "close", "volume"]
        if self.source not in valid_sources:
            raise ValueError(f"Source must be one of: {valid_sources}")

@dataclass
class SMAParams(IndicatorParams):
    """SMA-specific parameters with multi-period support."""
    periods: list[int] | None = None  # Calculate multiple SMAs simultaneously

    def __post_init__(self):
        super().__post_init__()
        if self.periods:
            if not isinstance(self.periods, list):
                self.periods = [self.periods]
            for p in self.periods:
                if not isinstance(p, int) or p <= 0:
                    raise ValueError(f"All periods must be positive integers, got {p}")

@dataclass
class RSIParams(IndicatorParams):
    """RSI-specific parameters with overbought/oversold thresholds."""
    overbought: float = 70.0
    oversold: float = 30.0
    use_sma: bool = False  # Use SMA instead of EMA for smoothing

    def __post_init__(self):
        super().__post_init__()
        if not 0 < self.overbought <= 100:
            raise ValueError("Overbought must be between 0 and 100")
        if not 0 <= self.oversold < 100:
            raise ValueError("Oversold must be between 0 and 100")
        if self.oversold >= self.overbought:
            raise ValueError("Oversold must be less than overbought")

@dataclass
class MACDParams(IndicatorParams):
    """MACD-specific parameters."""
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9

    def __post_init__(self):
        super().__post_init__()
        if self.fast_period >= self.slow_period:
            raise ValueError(
                f"Fast period ({self.fast_period}) must be < slow period ({self.slow_period})"
            )

# === Pattern Parameter Dataclasses ===

from pydantic import BaseModel, Field, field_validator

class PatternParams(BaseModel):
    """Base parameters for all patterns (Pydantic v2)."""
    timeframe: str = Field(default="daily")

    model_config = {"from_attributes": True}

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value):
        valid_timeframes = ["1min", "5min", "15min", "30min", "1H", "4H", "daily", "weekly", "monthly"]
        if value not in valid_timeframes:
            raise ValueError(f"Timeframe must be one of: {valid_timeframes}")
        return value

class DojiParams(PatternParams):
    """Doji pattern-specific parameters."""
    tolerance: float = Field(default=0.01, ge=0.001, le=0.1)

    @field_validator("tolerance")
    @classmethod
    def validate_tolerance(cls, value):
        if not 0.001 <= value <= 0.1:
            raise ValueError("Tolerance must be between 0.001 and 0.1")
        return value

class BullishEngulfingParams(PatternParams):
    """Bullish Engulfing pattern parameters."""
    min_engulf_ratio: float = Field(default=1.0, ge=0.8, le=2.0)

    @field_validator("min_engulf_ratio")
    @classmethod
    def validate_ratio(cls, value):
        if not 0.8 <= value <= 2.0:
            raise ValueError("Engulf ratio must be between 0.8 and 2.0")
        return value

# === Database Models (SQLAlchemy ORM) ===

from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, Boolean, ARRAY, JSON as JSONB, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, UTC

Base = declarative_base()

class PatternDefinition(Base):
    """Pattern definitions table (Sprint 17 registry)."""
    __tablename__ = "pattern_definitions"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    short_description = Column(String(255), nullable=False)
    long_description = Column(Text)
    code_reference = Column(String(255))  # 'src.analysis.patterns.candlestick.single_bar'
    class_name = Column(String(100))       # 'DojiPattern'
    category = Column(String(50), default='pattern')
    enabled = Column(Boolean, default=True, nullable=False)
    confidence_threshold = Column(DECIMAL(3, 2), default=0.50)
    risk_level = Column(String(20), default='medium')
    applicable_timeframes = Column(ARRAY(String(20)))  # ['daily', 'hourly', 'intraday']
    instantiation_params = Column(JSONB)  # {"tolerance": 0.02}
    created_date = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_date = Column(DateTime, default=lambda: datetime.now(UTC))

class IndicatorDefinition(Base):
    """Indicator definitions table."""
    __tablename__ = "indicator_definitions"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    code_reference = Column(String(255))  # 'src.analysis.indicators.rsi'
    class_name = Column(String(100))       # 'RSI'
    category = Column(String(50), default='indicator')
    enabled = Column(Boolean, default=True, nullable=False)
    default_params = Column(JSONB)         # {"period": 14, "overbought": 70}
    created_date = Column(DateTime, default=lambda: datetime.now(UTC))

class DailyPattern(Base):
    """Pattern detection results storage."""
    __tablename__ = "daily_patterns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_id = Column(Integer, nullable=False)  # FK to pattern_definitions
    symbol = Column(String(10), nullable=False, index=True)
    detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    confidence = Column(DECIMAL(4, 3), nullable=False)
    price_at_detection = Column(DECIMAL(10, 4))
    volume_at_detection = Column(Integer)
    pattern_data = Column(JSONB)  # Pattern-specific metadata

class IndicatorResult(Base):
    """Indicator calculation results storage."""
    __tablename__ = "indicator_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    indicator_id = Column(Integer, nullable=False)  # FK to indicator_definitions
    symbol = Column(String(10), nullable=False, index=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, index=True)
    value = Column(DECIMAL(12, 4))  # Primary value
    value_data = Column(JSONB, nullable=False)  # All calculated values
    metadata = Column(JSONB)  # Calculation metadata

# === Exception Classes ===

class TickStockAnalysisError(Exception):
    """Base exception for analysis errors."""
    pass

class IndicatorError(TickStockAnalysisError):
    """Raised when indicator calculation fails."""
    def __init__(self, indicator_name: str = "", reason: str = "", data_info: str = ""):
        self.indicator_name = indicator_name
        self.reason = reason
        self.data_info = data_info
        super().__init__(
            f"Indicator error [{indicator_name}]: {reason} {data_info}"
        )

class PatternDetectionError(TickStockAnalysisError):
    """Raised when pattern detection logic fails."""
    def __init__(self, pattern_name: str, reason: str, data_info: str = ""):
        self.pattern_name = pattern_name
        self.reason = reason
        self.data_info = data_info
        super().__init__(
            f"Pattern detection failed for {pattern_name}: {reason} {data_info}"
        )

class DataValidationError(TickStockAnalysisError):
    """Raised when OHLCV data validation fails."""
    pass
```

### Implementation Tasks (Dependency-Ordered)

```yaml
# === WEEK 1: INDICATOR MIGRATION (Days 1-5) ===

# Day 1: Foundation Setup
Task 1.1: CREATE src/analysis/__init__.py
  - IMPLEMENT: Package initialization
  - PLACEMENT: Root of analysis module
  - DEPENDENCIES: None

Task 1.2: CREATE src/analysis/exceptions.py
  - IMPLEMENT: TickStockAnalysisError, IndicatorError, PatternDetectionError, DataValidationError
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\exceptions.py (lines 1-94)
  - NAMING: Exception classes end with "Error"
  - GOTCHA: Include context fields (indicator_name, reason, data_info)
  - VALIDATION: Import exceptions in __init__.py

Task 1.3: CREATE src/analysis/indicators/__init__.py + base_indicator.py
  - IMPLEMENT: BaseIndicator abstract class
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\indicators\base_indicator.py (lines 44-306)
  - CRITICAL METHODS:
    - calculate(data, symbol, timeframe) -> dict[str, Any]
    - _validate_params(params) -> IndicatorParams
    - get_minimum_periods() -> int
    - can_calculate(data) -> bool
    - _validate_data_format(data) -> None
    - _get_source_values(data) -> pd.Series
    - _safe_divide(numerator, denominator, default=0.0)
    - _rolling_calculation(data, window, func_name)
    - _exponential_smoothing(data, alpha)
    - _true_range(data) -> pd.Series
  - NAMING: BaseIndicator (PascalCase), methods with _ prefix are protected
  - GOTCHA: Return convention {"value": primary, "value_data": {...}, "metadata": {...}}
  - VALIDATION: Can instantiate BaseIndicator subclass, abstractmethod enforcement works

Task 1.4: CREATE src/analysis/indicators/sma.py
  - IMPLEMENT: SMA (Simple Moving Average) indicator
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\indicators\sma.py (lines 95-200)
  - PARAMETERS: SMAParams with periods=[20, 50, 200] multi-period support
  - CALCULATION: df['close'].rolling(window=period, min_periods=period).mean()
  - FEATURES: Golden cross / death cross detection (SMA_50 vs SMA_200)
  - GOTCHA: Primary value = first calculated period's value
  - VALIDATION: Test on 250 bars, verify SMA_20 matches pandas reference

Task 1.5: CREATE src/analysis/indicators/ema.py
  - IMPLEMENT: EMA (Exponential Moving Average) indicator
  - PARAMETERS: EMAParams with period, span support
  - CALCULATION: df['close'].ewm(span=period, adjust=False, min_periods=period).mean()
  - CRITICAL: adjust=False for standard EMA formula
  - GOTCHA: EMA initialization uses first SMA value
  - VALIDATION: Compare vs manual EMA calculation (α = 2/(span+1))

# Day 2: Core Indicators (Momentum & Trend)
Task 2.1: CREATE src/analysis/indicators/rsi.py
  - IMPLEMENT: RSI (Relative Strength Index) indicator
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\indicators\rsi.py (lines 103-261)
  - PARAMETERS: RSIParams with period=14, overbought=70, oversold=30, use_sma=False
  - CALCULATION (Wilder's smoothing):
    ```python
    delta = prices.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gains = gains.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_losses = losses.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    ```
  - CRITICAL: alpha=1/period for Wilder's smoothing (NOT span=period)
  - FEATURES: Overbought/oversold signals, divergence detection
  - GOTCHA: Handle div by zero: rsi.fillna(100.0) if all losses are 0
  - VALIDATION: RSI range 0-100, test overbought/oversold detection

Task 2.2: CREATE src/analysis/indicators/macd.py
  - IMPLEMENT: MACD (Moving Average Convergence Divergence) indicator
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\indicators\macd.py (lines 119-218)
  - PARAMETERS: MACDParams with fast=12, slow=26, signal=9
  - CALCULATION:
    ```python
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    ```
  - CRITICAL: Primary value = MACD line (NOT histogram)
  - FEATURES: Crossover detection (bullish/bearish signals)
  - GOTCHA: Minimum bars = slow + signal (26 + 9 = 35)
  - VALIDATION: Test crossover detection logic

# Day 3: Volatility & Volume Indicators
Task 3.1: CREATE src/analysis/indicators/bollinger_bands.py
  - IMPLEMENT: Bollinger Bands indicator
  - PARAMETERS: BollingerBandsParams with period=20, num_std=2.0
  - CALCULATION:
    ```python
    middle_band = prices.rolling(window=period, min_periods=period).mean()
    std_dev = prices.rolling(window=period, min_periods=period).std()
    upper_band = middle_band + (num_std * std_dev)
    lower_band = middle_band - (num_std * std_dev)
    ```
  - FEATURES: %B calculation, bandwidth, squeeze detection
  - GOTCHA: value_data contains all 3 bands (upper, middle, lower)
  - VALIDATION: Test squeeze detection (bandwidth < threshold)

Task 3.2: CREATE src/analysis/indicators/atr.py
  - IMPLEMENT: ATR (Average True Range) indicator
  - PARAMETERS: ATRParams with period=14
  - CALCULATION:
    ```python
    true_range = pd.DataFrame({
        'hl': data['high'] - data['low'],
        'hc': abs(data['high'] - data['close'].shift(1)),
        'lc': abs(data['low'] - data['close'].shift(1))
    }).max(axis=1)
    atr = true_range.ewm(span=period, adjust=False).mean()
    ```
  - CRITICAL: Use _true_range() utility from BaseIndicator
  - GOTCHA: First bar has no previous close (use high - low only)
  - VALIDATION: Test on volatile vs stable data

Task 3.3: CREATE src/analysis/indicators/obv.py
  - IMPLEMENT: OBV (On-Balance Volume) indicator
  - PARAMETERS: OBVParams (no period required)
  - CALCULATION:
    ```python
    obv = (np.sign(prices.diff()) * volume).fillna(0).cumsum()
    ```
  - FEATURES: OBV divergence from price
  - GOTCHA: Cumulative sum (absolute value meaningless, only trend matters)
  - VALIDATION: Test cumulative sum correctness

Task 3.4: CREATE src/analysis/indicators/vwap.py
  - IMPLEMENT: VWAP (Volume Weighted Average Price) indicator
  - PARAMETERS: VWAPParams (intraday only)
  - CALCULATION:
    ```python
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    ```
  - CRITICAL: Reset at start of trading day
  - GOTCHA: Only valid for intraday timeframes (1min, 5min, etc.)
  - VALIDATION: Test reset logic on multi-day data

# Day 4: Advanced Indicators
Task 4.1: CREATE src/analysis/indicators/adx.py
  - IMPLEMENT: ADX (Average Directional Index) indicator
  - PARAMETERS: ADXParams with period=14
  - CALCULATION: Complex (requires +DI, -DI, DX calculations)
  - CRITICAL: Use Wilder's smoothing for all EMAs
  - GOTCHA: Minimum 2×period bars required (28 for period=14)
  - VALIDATION: Test trend strength interpretation

Task 4.2: CREATE src/analysis/indicators/stochastic.py
  - IMPLEMENT: Stochastic Oscillator indicator
  - PARAMETERS: StochasticParams with k_period=14, d_period=3, smooth_k=3
  - CALCULATION:
    ```python
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    k_smoothed = k.rolling(window=smooth_k).mean()
    d = k_smoothed.rolling(window=d_period).mean()
    ```
  - FEATURES: %K and %D crossovers, overbought/oversold (80/20)
  - GOTCHA: Handle div by zero if highest_high == lowest_low
  - VALIDATION: Test crossover detection

Task 4.3: CREATE remaining 3 indicators (adp choice)
  - OPTIONS: CCI, Williams %R, Momentum, ROC, Donchian Channels, Ichimoku Cloud
  - FOLLOW BaseIndicator pattern
  - VALIDATION: Full test coverage

# Day 5: Indicator Service & Testing
Task 5.1: CREATE src/analysis/services/__init__.py + indicator_service.py
  - IMPLEMENT: IndicatorService class
  - CRITICAL METHODS:
    - calculate_indicator(symbol, indicator_name, data, config) -> dict
    - calculate_all_indicators(symbol, data) -> dict[str, dict]
    - _load_indicator_class(indicator_name) -> Type[BaseIndicator]
    - _store_result(symbol, indicator_name, result) -> None
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\services\pattern_detection_service.py (lines 355-481)
  - DEPENDENCIES: TickStockDatabase, dynamic loader
  - GOTCHA: Load enabled indicators from indicator_definitions table
  - VALIDATION: Test calculate_all_indicators() with 5+ indicators

Task 5.2: CREATE tests/unit/analysis/indicators/test_base_indicator.py
  - IMPLEMENT: Base test class for indicator testing
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\tests\unit\indicators\test_all_indicators.py (lines 18-55)
  - FIXTURES: create_test_data() with OHLC consistency enforcement
  - UTILITIES: assertAlmostEqual helpers for float comparison
  - VALIDATION: Base test class importable, fixtures work

Task 5.3: CREATE indicator unit tests (15 tests total)
  - FILES: test_sma.py, test_ema.py, test_rsi.py, test_macd.py, etc.
  - COVERAGE: Test calculation accuracy, edge cases, invalid data handling
  - ASSERTIONS: Return structure, value ranges, NaN handling
  - PERFORMANCE: Test <10ms for 1000 bars
  - VALIDATION: All indicator tests pass

# === WEEK 2: PATTERN MIGRATION (Days 6-10) ===

# Day 6: Pattern Foundation
Task 6.1: CREATE src/analysis/patterns/__init__.py + base_pattern.py
  - IMPLEMENT: BasePattern abstract class
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\patterns\base.py (lines 1-270)
  - CRITICAL METHODS:
    - detect(data) -> pd.Series (MUST return boolean Series)
    - get_minimum_bars() -> int
    - _validate_data_format(data) -> None
    - set_pattern_registry_info(pattern_id, confidence_threshold, metadata)
    - calculate_confidence(data, detection_indices) -> dict[Index, float]
    - filter_by_confidence(detections, data) -> pd.Series
    - enable_confidence_scoring() -> None
  - PARAMETERS: PatternParams with timeframe validation
  - GOTCHA: Sprint 17 integration methods REQUIRED for database storage
  - VALIDATION: Can subclass BasePattern, abstractmethod enforcement works

Task 6.2: CREATE pattern utility functions
  - FILE: src/analysis/patterns/utils.py
  - FUNCTIONS:
    - calculate_body_size(data) -> pd.Series
    - calculate_candle_range(data) -> pd.Series
    - calculate_upper_shadow(data) -> pd.Series
    - calculate_lower_shadow(data) -> pd.Series
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\patterns\candlestick\single_bar.py (utility functions)
  - CRITICAL: All functions must be vectorized (no loops)
  - VALIDATION: Test utility functions with 1000 bars

Task 6.3: CREATE src/analysis/patterns/candlestick/__init__.py + single_bar.py
  - IMPLEMENT: Single-bar candlestick patterns
  - PATTERNS: DojiPattern, HammerPattern, ShootingStarPattern, HangingManPattern, SpinningTopPattern
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\patterns\candlestick\single_bar.py (lines 90-166 for Doji)
  - CRITICAL: Vectorized detection (NO loops)
  - EXAMPLE (DojiPattern):
    ```python
    body_size = calculate_body_size(data)
    candle_range = calculate_candle_range(data)
    valid_candles = candle_range >= 0.01  # Avoid div by zero
    doji_detected = (body_size <= tolerance * candle_range) & valid_candles
    return doji_detected.fillna(False).astype(bool)
    ```
  - GOTCHA: get_minimum_bars() returns 1 for single-bar patterns
  - VALIDATION: Test on created test data with known Doji patterns

# Day 7: Multi-Bar Candlestick Patterns
Task 7.1: CREATE src/analysis/patterns/candlestick/multi_bar.py
  - IMPLEMENT: Multi-bar candlestick patterns
  - PATTERNS: BullishEngulfingPattern, BearishEngulfingPattern, MorningStarPattern, EveningStarPattern, ThreeWhiteSoldiersPattern, ThreeBlackCrowsPattern
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\patterns\candlestick\multi_bar.py (lines 62-158 for BullishEngulfing)
  - CRITICAL: Use shift() for previous bar access
  - EXAMPLE (BullishEngulfing):
    ```python
    current_close = data["close"]
    prev_close = data["close"].shift(1)
    current_open = data["open"]
    prev_open = data["open"].shift(1)

    prev_bearish = prev_close < prev_open
    current_bullish = current_close > current_open
    body_engulfed = (current_open <= prev_close) & (current_close >= prev_open)

    bullish_engulfing = prev_bearish & current_bullish & body_engulfed
    return bullish_engulfing.fillna(False).astype(bool)
    ```
  - GOTCHA: First bar always False (no previous bar for shift)
  - VALIDATION: Test with 2-bar sequences

# Day 8: Daily/Multi-Day Patterns
Task 8.1: CREATE src/analysis/patterns/daily/__init__.py + multi_day_breakout.py
  - IMPLEMENT: MultiDayBreakoutPattern
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\patterns\daily\multi_day_breakout_pattern.py (lines 1-437)
  - CRITICAL METHODS:
    - _detect_consolidation(data) -> pd.Series
    - _detect_upward_breakouts(data, consolidation_periods) -> pd.Series
    - _detect_downward_breakouts(data, consolidation_periods) -> pd.Series
    - _volume_surge_confirmation(data) -> pd.Series
  - PARAMETERS: MultiDayBreakoutPatternParams with consolidation_period, breakout_strength, volume_surge_multiplier
  - GOTCHA: get_minimum_bars() returns 30+ (needs historical context)
  - VALIDATION: Test on 60-bar dataset with consolidation → breakout sequence

Task 8.2: CREATE src/analysis/patterns/daily/consolidation.py
  - IMPLEMENT: ConsolidationPattern
  - DETECTION: Price range compression (std dev / mean < threshold)
  - CALCULATION:
    ```python
    rolling_std = prices.rolling(window=period).std()
    rolling_mean = prices.rolling(window=period).mean()
    range_compression = rolling_std / rolling_mean
    consolidation = range_compression < max_range_compression
    ```
  - VALIDATION: Test on sideways market data

Task 8.3: CREATE src/analysis/patterns/daily/double_top_bottom.py
  - IMPLEMENT: DoubleTopPattern, DoubleBottomPattern
  - DETECTION: Two peaks/troughs at similar price levels
  - CRITICAL: Use scipy.signal.find_peaks for peak detection
  - GOTCHA: Validate symmetry in time between peaks
  - VALIDATION: Test with synthetic double top data

Task 8.4: CREATE src/analysis/patterns/daily/head_shoulders.py
  - IMPLEMENT: HeadShouldersPattern
  - DETECTION: Three peaks (left shoulder, head, right shoulder)
  - VALIDATION CRITERIA:
    - Head is highest peak
    - Shoulders roughly equal height (within 10%)
    - Time symmetry between shoulders and head
  - GOTCHA: Requires scipy.signal.find_peaks for peak detection
  - VALIDATION: Test with synthetic H&S pattern

# Day 9: Pattern Service & Dynamic Loading
Task 9.1: CREATE src/analysis/services/pattern_service.py
  - IMPLEMENT: PatternService class
  - CRITICAL METHODS:
    - detect_pattern(symbol, pattern_name, data, indicators, config) -> dict | None
    - detect_all_patterns(symbol, data, indicators) -> list[dict]
    - _load_pattern_class(pattern_name) -> Type[BasePattern]
    - _adjust_confidence_with_indicators(pattern_name, base_confidence, indicators) -> float
    - _store_result(symbol, pattern_name, result) -> None
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\services\pattern_detection_service.py (lines 482-560)
  - DEPENDENCIES: IndicatorService (patterns use indicator results for confidence)
  - GOTCHA: Patterns detect AFTER indicators calculated (dependency resolution)
  - VALIDATION: Test detect_all_patterns() with 5+ patterns

Task 9.2: CREATE src/analysis/services/dynamic_loader.py
  - IMPLEMENT: DynamicPatternIndicatorLoader class
  - CRITICAL METHODS:
    - load_patterns_for_timeframe(timeframe) -> dict[str, Any]
    - load_indicators_for_timeframe(timeframe) -> dict[str, Any]
    - _import_class(code_reference, class_name) -> Type
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\analysis\dynamic_loader.py (lines 1-680)
  - DATABASE QUERIES:
    - "SELECT name, code_reference, class_name FROM pattern_definitions WHERE enabled=true AND %s = ANY(applicable_timeframes)"
    - "SELECT name, code_reference, class_name FROM indicator_definitions WHERE enabled=true"
  - CRITICAL: NO FALLBACK policy
    ```python
    try:
        module = importlib.import_module(code_reference)
        cls = getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Failed to load {class_name}: {e}") from e
    ```
  - GOTCHA: Call importlib.invalidate_caches() for runtime-created modules
  - VALIDATION: Test loading all patterns/indicators from database

# Day 10: Pattern Testing & Regression
Task 10.1: CREATE tests/unit/analysis/patterns/test_base_pattern.py
  - IMPLEMENT: Base test class for pattern testing
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\tests\unit\patterns\test_base.py (lines 1-262)
  - FIXTURES:
    - create_bullish_data() with upward trend
    - create_bearish_data() with downward trend
    - create_sideways_data() with consolidation
    - create_specific_pattern(pattern_type) with embedded patterns
  - UTILITIES: OHLC consistency enforcement
  - GOTCHA: Ensure high=max(O,H,L,C), low=min(O,H,L,C)
  - VALIDATION: Base test class importable, fixtures generate valid data

Task 10.2: CREATE pattern unit tests (20+ tests total)
  - FILES: test_candlestick_single.py, test_candlestick_multi.py, test_daily_patterns.py
  - COVERAGE: Test detection accuracy, edge cases, insufficient data handling
  - ASSERTIONS: Return type (pd.Series), boolean values, index alignment
  - PERFORMANCE: Test <10ms for 1000 bars
  - VALIDATION: All pattern tests pass

Task 10.3: CREATE tests/integration/test_regression_vs_tickstockpl.py
  - IMPLEMENT: Regression validation vs TickStockPL baseline
  - APPROACH:
    1. Load 10 test symbols with 250 bars each (from ohlcv_daily)
    2. Run AppV2 analysis (calculate indicators + detect patterns)
    3. Load TickStockPL baseline results (from indicator_results, daily_patterns)
    4. Compare: assertAlmostEqual(appv2_value, tickstockpl_value, places=2)
  - CRITICAL: 100% match requirement for production migration
  - GOTCHA: Handle floating point precision (2 decimal places tolerance)
  - VALIDATION: Zero regressions detected

# === WEEK 3: ANALYSIS ENGINES & INTEGRATION (Days 11-15) ===

# Day 11: Unified Analysis Service
Task 11.1: CREATE src/analysis/services/analysis_service.py
  - IMPLEMENT: AnalysisService class (unified orchestration)
  - CRITICAL METHODS:
    - analyze_symbol(symbol, calculate_indicators, detect_patterns) -> dict[str, Any]
    - analyze_universe(universe, parallel, max_workers) -> dict[str, Any]
    - _load_ohlcv_data(symbol, timeframe, start_date, end_date) -> pd.DataFrame
    - _analyze_universe_parallel(symbols, max_workers) -> dict
    - _analyze_universe_sequential(symbols) -> dict
  - DEPENDENCIES: IndicatorService, PatternService, TickStockDatabase, RelationshipCache
  - EXAMPLE (analyze_symbol):
    ```python
    def analyze_symbol(
        self,
        symbol: str,
        calculate_indicators: bool = True,
        detect_patterns: bool = True,
        timeframe: str = "daily"
    ) -> dict[str, Any]:
        # 1. Load OHLCV data
        df = self._load_ohlcv_data(symbol, timeframe)

        results = {
            'symbol': symbol,
            'timeframe': timeframe,
            'indicators': {},
            'patterns': {}
        }

        # 2. Calculate indicators (if requested)
        if calculate_indicators:
            results['indicators'] = self.indicator_service.calculate_all_indicators(
                symbol, df
            )

        # 3. Detect patterns (if requested)
        if detect_patterns:
            results['patterns'] = self.pattern_service.detect_all_patterns(
                symbol, df, indicators=results['indicators']
            )

        return results
    ```
  - GOTCHA: Indicators MUST be calculated before patterns (dependency)
  - VALIDATION: Test analyze_symbol() end-to-end with 1 symbol

Task 11.2: Implement parallel processing for analyze_universe()
  - IMPLEMENTATION: ThreadPoolExecutor with max_workers=10
  - EXAMPLE:
    ```python
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _analyze_universe_parallel(self, symbols: list[str], max_workers: int = 10):
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.analyze_symbol, symbol): symbol
                for symbol in symbols
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result(timeout=30)
                    results[symbol] = result
                except Exception as e:
                    logger.error(f"Failed to analyze {symbol}: {e}")
                    results[symbol] = {'error': str(e)}

        return results
    ```
  - GOTCHA: Handle timeouts (30s per symbol)
  - VALIDATION: Test with 50 symbols, verify parallel speedup

# Day 12: Pattern Registry Integration (Sprint 17)
Task 12.1: CREATE src/analysis/services/pattern_registry_service.py
  - IMPLEMENT: PatternRegistryService class (Sprint 17 compatibility)
  - FOLLOW pattern: C:\Users\McDude\TickStockPL\src\data\database\pattern_registry_service.py (lines 1-593)
  - CRITICAL METHODS:
    - get_enabled_patterns() -> list[PatternSummaryModel]
    - get_pattern_by_id(pattern_id) -> PatternSummaryModel | None
    - get_pattern_by_name(pattern_name) -> PatternSummaryModel | None
    - update_pattern_enabled_status(pattern_id, enabled) -> bool
    - _initialize_cache() -> None
    - _ensure_cache_fresh() -> None
  - CACHING: Thread-safe caching with RLock, 5-minute TTL
  - PERFORMANCE: <5ms access time (cache hit)
  - GOTCHA: Cache refresh every 5 minutes or on update
  - VALIDATION: Test cache performance (<5ms), test enable/disable pattern

Task 12.2: Seed database with pattern/indicator definitions
  - CREATE: scripts/seed_analysis_definitions.py
  - IMPLEMENTATION:
    ```python
    # Seed pattern_definitions table
    patterns_to_seed = [
        {
            'name': 'Doji',
            'code_reference': 'src.analysis.patterns.candlestick.single_bar',
            'class_name': 'DojiPattern',
            'short_description': 'Doji candlestick pattern',
            'confidence_threshold': 0.70,
            'applicable_timeframes': ['daily', 'hourly', 'intraday'],
            'instantiation_params': {'tolerance': 0.01}
        },
        # ... 19 more patterns
    ]

    # Seed indicator_definitions table
    indicators_to_seed = [
        {
            'name': 'RSI',
            'code_reference': 'src.analysis.indicators.rsi',
            'class_name': 'RSI',
            'default_params': {'period': 14, 'overbought': 70, 'oversold': 30}
        },
        # ... 14 more indicators
    ]
    ```
  - VALIDATION: Run script, verify 20 patterns + 15 indicators in database

# Day 13: Database Integration & Storage
Task 13.1: Implement database storage for indicator results
  - UPDATE: src/analysis/services/indicator_service.py
  - METHOD: _store_result(symbol, indicator_name, result)
  - IMPLEMENTATION:
    ```python
    def _store_result(self, symbol: str, indicator_name: str, result: dict):
        query = """
            INSERT INTO indicator_results
            (indicator_id, symbol, calculated_at, value, value_data, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        # Lookup indicator_id from indicator_definitions
        indicator_id = self._get_indicator_id(indicator_name)

        self.db.execute_write(
            query,
            (
                indicator_id,
                symbol,
                result['calculation_timestamp'],
                result['value'],
                json.dumps(result['value_data']),
                json.dumps(result['metadata'])
            )
        )
    ```
  - GOTCHA: value_data is JSONB (PostgreSQL) - must serialize to JSON
  - VALIDATION: Test insert, verify data in indicator_results table

Task 13.2: Implement database storage for pattern detections
  - UPDATE: src/analysis/services/pattern_service.py
  - METHOD: _store_result(symbol, pattern_name, result)
  - IMPLEMENTATION:
    ```python
    def _store_result(self, symbol: str, pattern_name: str, result: dict):
        query = """
            INSERT INTO daily_patterns
            (pattern_id, symbol, detected_at, confidence, price_at_detection,
             volume_at_detection, pattern_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        pattern_id = self._get_pattern_id(pattern_name)

        self.db.execute_write(
            query,
            (
                pattern_id,
                symbol,
                result['detected_at'],
                result['confidence'],
                result.get('price_at_detection'),
                result.get('volume_at_detection'),
                json.dumps(result.get('metadata', {}))
            )
        )
    ```
  - VALIDATION: Test insert, verify data in daily_patterns table

# Day 14: Integration Testing
Task 14.1: CREATE tests/integration/test_analysis_integration.py
  - IMPLEMENT: End-to-end integration tests
  - TEST CASES:
    - test_analyze_symbol_with_indicators() - Full indicator calculation
    - test_analyze_symbol_with_patterns() - Full pattern detection
    - test_analyze_symbol_full() - Indicators + patterns together
    - test_analyze_universe_parallel() - Universe-wide analysis
    - test_dynamic_loader_database_integration() - Load from database
    - test_pattern_registry_caching() - Cache performance
    - test_database_storage_indicators() - Indicator results storage
    - test_database_storage_patterns() - Pattern results storage
  - ASSERTIONS:
    - Response structure validation
    - Database writes verification
    - Performance targets (<1s per symbol)
  - VALIDATION: All integration tests pass

Task 14.2: Run regression validation
  - EXECUTE: tests/integration/test_regression_vs_tickstockpl.py
  - APPROACH:
    1. Select 10 diverse test symbols (trending, volatile, sideways)
    2. Load 250 bars of historical data per symbol
    3. Run AppV2 AnalysisService.analyze_symbol() for each
    4. Compare results vs TickStockPL baseline:
       - Indicator values: assertAlmostEqual(appv2, tickstockpl, places=2)
       - Pattern detections: assertEqual(appv2_detections, tickstockpl_detections)
  - CRITICAL: 100% match requirement
  - VALIDATION: Zero regressions, all comparisons pass

# Day 15: Final Validation & Sprint Closure
Task 15.1: Run all validation levels (4 levels)
  - LEVEL 1: Syntax & style - `ruff check src/analysis/` (expect zero errors)
  - LEVEL 2: Unit tests - `pytest tests/unit/analysis/ -v` (expect 50+ tests passing)
  - LEVEL 3: Integration tests - `python run_tests.py` (expect MANDATORY tests passing)
  - LEVEL 4: Regression tests - Zero regressions vs TickStockPL baseline
  - VALIDATION: All levels pass

Task 15.2: Performance validation
  - TEST analyze_symbol() performance:
    ```bash
    python -m timeit -s "from src.analysis.services.analysis_service import AnalysisService; service = AnalysisService()" "service.analyze_symbol('AAPL')"
    ```
    - TARGET: <1s per symbol (15 indicators + 20 patterns on 250 bars)
  - TEST analyze_universe() performance:
    - Run with 500 symbols, max_workers=10
    - TARGET: <10 minutes total
  - VALIDATION: Performance targets met

Task 15.3: Documentation & sprint closure
  - CREATE: docs/planning/sprints/sprint68/core-analysis-migration-RESULTS.md
  - CONTENT:
    - Success criteria verification (all checkboxes)
    - Performance metrics achieved
    - Regression test results (zero regressions)
    - Files created/modified (count)
    - Lines migrated (24,333)
  - UPDATE: CLAUDE.md with Sprint 68 completion
  - VALIDATION: Sprint documentation complete
```

### Implementation Patterns & Key Details

```python
# === PATTERN 1: BaseIndicator Implementation ===
# File: src/analysis/indicators/base_indicator.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
from src.analysis.exceptions import IndicatorError

class BaseIndicator(ABC):
    """Abstract base class for all indicator implementations."""

    def __init__(self, params: dict[str, Any]):
        try:
            self.params = self._validate_params(params)
            self.indicator_name = self.__class__.__name__
        except Exception as e:
            raise IndicatorError(f"Parameter validation failed for {self.__class__.__name__}: {e}")

    @abstractmethod
    def calculate(self, data: pd.DataFrame, symbol: str = None, timeframe: str = "daily") -> dict[str, Any]:
        """
        Calculate indicator values.

        MUST return dict with:
        - 'indicator_type': str (e.g., 'rsi', 'sma')
        - 'symbol': str
        - 'timeframe': str
        - 'value': float | None (PRIMARY VALUE)
        - 'value_data': dict (ALL calculated values)
        - 'calculation_timestamp': pd.Timestamp
        - 'metadata': dict (calculation details)
        """
        pass

    @abstractmethod
    def _validate_params(self, params: dict[str, Any]) -> IndicatorParams:
        """Validate and parse indicator parameters."""
        pass

    def get_minimum_periods(self) -> int:
        """Get minimum periods required for calculation."""
        return getattr(self.params, "period", 1)

    def can_calculate(self, data: pd.DataFrame) -> bool:
        """Check if indicator can be calculated with given data."""
        try:
            self._validate_data_format(data)
            return len(data) >= self.get_minimum_periods()
        except Exception:
            return False

    def _validate_data_format(self, data: pd.DataFrame) -> None:
        """Validate OHLCV data format."""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            raise IndicatorError(
                indicator_name=self.indicator_name,
                reason=f"Missing required columns: {missing_columns}",
                data_info=f"Available columns: {list(data.columns)}"
            )

        min_periods = self.get_minimum_periods()
        if len(data) < min_periods:
            raise IndicatorError(
                indicator_name=self.indicator_name,
                reason=f"Insufficient data: {len(data)} rows, need {min_periods}",
                data_info=f"Minimum periods: {min_periods}"
            )

    def _get_source_values(self, data: pd.DataFrame) -> pd.Series:
        """Extract source column values (close, open, high, low, volume)."""
        source = self.params.source
        if source not in data.columns:
            raise IndicatorError(
                indicator_name=self.indicator_name,
                reason=f"Source column '{source}' not found",
                data_info=f"Available columns: {list(data.columns)}"
            )
        return data[source]

    def _safe_divide(self, numerator, denominator, default=0.0):
        """Safe division with default value for div by zero."""
        return np.where(denominator != 0, numerator / denominator, default)

    def _rolling_calculation(self, data: pd.Series, window: int, func_name: str) -> pd.Series:
        """Generic rolling window calculation with error handling."""
        try:
            rolling = data.rolling(window=window, min_periods=window)

            if func_name == 'mean':
                return rolling.mean()
            elif func_name == 'sum':
                return rolling.sum()
            elif func_name == 'std':
                return rolling.std()
            elif func_name == 'var':
                return rolling.var()
            elif func_name == 'min':
                return rolling.min()
            elif func_name == 'max':
                return rolling.max()
            else:
                raise ValueError(f"Unsupported function: {func_name}")
        except Exception as e:
            raise IndicatorError(
                indicator_name=self.indicator_name,
                reason=f"Rolling calculation failed: {e}",
                data_info=f"Window: {window}, Function: {func_name}"
            )

    def _exponential_smoothing(self, data: pd.Series, alpha: float) -> pd.Series:
        """EMA calculation with validation."""
        if not 0 < alpha <= 1:
            raise IndicatorError(
                indicator_name=self.indicator_name,
                reason=f"Invalid alpha: {alpha} (must be 0 < alpha <= 1)"
            )

        return data.ewm(alpha=alpha, adjust=False).mean()

    def _true_range(self, data: pd.DataFrame) -> pd.Series:
        """Calculate True Range for ATR."""
        hl = data['high'] - data['low']
        hc = abs(data['high'] - data['close'].shift(1))
        lc = abs(data['low'] - data['close'].shift(1))

        true_range = pd.DataFrame({'hl': hl, 'hc': hc, 'lc': lc}).max(axis=1)
        return true_range


# === PATTERN 2: RSI Indicator Implementation ===
# File: src/analysis/indicators/rsi.py

from dataclasses import dataclass
import pandas as pd
import numpy as np
from src.analysis.indicators.base_indicator import BaseIndicator, IndicatorParams

@dataclass
class RSIParams(IndicatorParams):
    """RSI-specific parameters."""
    overbought: float = 70.0
    oversold: float = 30.0
    use_sma: bool = False

    def __post_init__(self):
        super().__post_init__()
        if not 0 < self.overbought <= 100:
            raise ValueError("Overbought must be between 0 and 100")
        if not 0 <= self.oversold < 100:
            raise ValueError("Oversold must be between 0 and 100")
        if self.oversold >= self.overbought:
            raise ValueError("Oversold must be less than overbought")

class RSI(BaseIndicator):
    """Relative Strength Index indicator with Wilder's smoothing."""

    def _validate_params(self, params: dict) -> RSIParams:
        return RSIParams(**params)

    def calculate(self, data: pd.DataFrame, symbol: str = None, timeframe: str = "daily") -> dict:
        """Calculate RSI using Wilder's smoothing method."""
        # Validate data
        self._validate_data_format(data)

        # Get source values
        prices = self._get_source_values(data)

        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)

        # Wilder's smoothing (alpha = 1/period, adjust=False)
        avg_gains = gains.ewm(alpha=1/self.params.period, min_periods=self.params.period, adjust=False).mean()
        avg_losses = losses.ewm(alpha=1/self.params.period, min_periods=self.params.period, adjust=False).mean()

        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))

        # Handle division by zero
        rsi = rsi.fillna(100.0)  # If all losses are 0, RSI is 100
        rsi[avg_gains == 0] = 0.0  # If all gains are 0, RSI is 0

        # Get latest value
        latest_rsi = rsi.iloc[-1]

        # Determine signal
        if latest_rsi >= self.params.overbought:
            signal = "overbought"
        elif latest_rsi <= self.params.oversold:
            signal = "oversold"
        else:
            signal = "neutral"

        # Calculate confidence (higher at extremes)
        if latest_rsi >= self.params.overbought or latest_rsi <= self.params.oversold:
            confidence = 0.85
        elif 50 <= latest_rsi <= 70 or 30 <= latest_rsi <= 50:
            confidence = 0.70
        else:
            confidence = 0.60

        # CONVENTION-COMPLIANT return
        return {
            "indicator_type": "rsi",
            "symbol": symbol or "UNKNOWN",
            "timeframe": timeframe,
            "value": float(latest_rsi) if not pd.isna(latest_rsi) else None,
            "value_data": {
                f"rsi_{self.params.period}": float(latest_rsi) if not pd.isna(latest_rsi) else None,
                "signal": signal,
                "overbought": latest_rsi >= self.params.overbought,
                "oversold": latest_rsi <= self.params.oversold,
                "confidence": confidence,
                "avg_gain": float(avg_gains.iloc[-1]) if not pd.isna(avg_gains.iloc[-1]) else None,
                "avg_loss": float(avg_losses.iloc[-1]) if not pd.isna(avg_losses.iloc[-1]) else None
            },
            "calculation_timestamp": data.index[-1] if len(data) > 0 else pd.Timestamp.now(),
            "metadata": {
                "period": self.params.period,
                "overbought_threshold": self.params.overbought,
                "oversold_threshold": self.params.oversold,
                "method": "sma" if self.params.use_sma else "wilder",
                "min_periods": self.params.period
            }
        }


# === PATTERN 3: BasePattern Implementation ===
# File: src/analysis/patterns/base_pattern.py

from abc import ABC, abstractmethod
from typing import Any
import pandas as pd
from pydantic import BaseModel, Field, field_validator
from src.analysis.exceptions import PatternDetectionError

class PatternParams(BaseModel):
    """Base parameters for all patterns (Pydantic v2)."""
    timeframe: str = Field(default="daily")

    model_config = {"from_attributes": True}

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value):
        valid_timeframes = ["1min", "5min", "15min", "30min", "1H", "4H", "daily", "weekly", "monthly"]
        if value not in valid_timeframes:
            raise ValueError(f"Timeframe must be one of: {valid_timeframes}")
        return value

class BasePattern(ABC):
    """Abstract base class for all pattern implementations."""

    def __init__(self, params: dict[str, Any] | None = None):
        self.params = self._validate_and_parse_params(params or {})
        self.pattern_name = self.__class__.__name__
        self.timeframe = self.params.timeframe

        # Sprint 17: Pattern registry integration
        self._pattern_id: int | None = None
        self._confidence_threshold: float | None = None
        self._registry_metadata: dict[str, Any] | None = None
        self._supports_confidence_scoring: bool = False

    @abstractmethod
    def detect(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect pattern in OHLCV data.

        MUST return pd.Series (boolean) indexed by timestamp.
        Use vectorized operations (NO loops for performance).
        """
        pass

    @abstractmethod
    def _validate_and_parse_params(self, params: dict[str, Any]) -> PatternParams:
        """Validate and parse pattern parameters."""
        pass

    def get_minimum_bars(self) -> int:
        """Get minimum bars required for detection."""
        return 1  # Override in subclasses (e.g., 2 for BullishEngulfing, 30 for MultiDayBreakout)

    def _validate_data_format(self, data: pd.DataFrame) -> None:
        """Validate OHLCV data format."""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            raise PatternDetectionError(
                pattern_name=self.pattern_name,
                reason=f"Missing required columns: {missing_columns}",
                data_info=f"Available columns: {list(data.columns)}"
            )

        min_bars = self.get_minimum_bars()
        if len(data) < min_bars:
            raise PatternDetectionError(
                pattern_name=self.pattern_name,
                reason=f"Insufficient data: {len(data)} rows, need {min_bars}",
                data_info=f"Minimum bars: {min_bars}"
            )

    # === Sprint 17 Pattern Registry Integration ===

    def set_pattern_registry_info(
        self,
        pattern_id: int,
        confidence_threshold: float,
        metadata: dict[str, Any]
    ):
        """Link pattern to database registry (Sprint 17)."""
        self._pattern_id = pattern_id
        self._confidence_threshold = confidence_threshold
        self._registry_metadata = metadata

    def calculate_confidence(
        self,
        data: pd.DataFrame,
        detection_indices: pd.Index
    ) -> dict[pd.Timestamp, float]:
        """
        Calculate confidence scores for detected patterns.
        Override in subclasses for custom confidence scoring.
        """
        # Default: Use registry confidence threshold
        return {idx: self._confidence_threshold for idx in detection_indices}

    def filter_by_confidence(
        self,
        detections: pd.Series,
        data: pd.DataFrame
    ) -> pd.Series:
        """Filter detections by confidence threshold."""
        if not self._supports_confidence_scoring:
            return detections

        detection_indices = detections[detections].index
        confidences = self.calculate_confidence(data, detection_indices)

        # Filter by threshold
        filtered = detections.copy()
        for idx in detection_indices:
            if confidences.get(idx, 0.0) < self._confidence_threshold:
                filtered.loc[idx] = False

        return filtered

    def enable_confidence_scoring(self):
        """Opt-in for confidence scoring (Sprint 17)."""
        self._supports_confidence_scoring = True


# === PATTERN 4: Doji Pattern Implementation ===
# File: src/analysis/patterns/candlestick/single_bar.py

import pandas as pd
from pydantic import Field, field_validator
from src.analysis.patterns.base_pattern import BasePattern, PatternParams
from src.analysis.patterns.utils import calculate_body_size, calculate_candle_range

class DojiParams(PatternParams):
    """Doji pattern-specific parameters."""
    tolerance: float = Field(default=0.01, ge=0.001, le=0.1)

    @field_validator("tolerance")
    @classmethod
    def validate_tolerance(cls, value):
        if not 0.001 <= value <= 0.1:
            raise ValueError("Tolerance must be between 0.001 and 0.1")
        return value

class DojiPattern(BasePattern):
    """Doji candlestick pattern detector."""

    def _validate_and_parse_params(self, params: dict) -> DojiParams:
        return DojiParams(**params)

    def detect(self, data: pd.DataFrame) -> pd.Series:
        """Vectorized Doji detection."""
        try:
            self._validate_data_format(data)

            if data.empty:
                return pd.Series([], dtype=bool, name="doji_detected")

            # Vectorized calculations (NO LOOPS)
            body_size = calculate_body_size(data)  # abs(close - open)
            candle_range = calculate_candle_range(data)  # high - low

            # Avoid division by zero
            min_range = 0.01  # Minimum $0.01 range
            valid_candles = candle_range >= min_range

            # Doji criteria: body <= tolerance * range
            doji_detected = (body_size <= self.params.tolerance * candle_range) & valid_candles

            return doji_detected.fillna(False).astype(bool)

        except Exception as e:
            raise PatternDetectionError(
                pattern_name="DojiPattern",
                reason=f"Detection failed: {str(e)}",
                data_info=f"Rows: {len(data)}, Cols: {list(data.columns)}"
            )


# === PATTERN 5: AnalysisService Orchestration ===
# File: src/analysis/services/analysis_service.py

from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from src.analysis.services.indicator_service import IndicatorService
from src.analysis.services.pattern_service import PatternService
from src.core.services.tickstock_database import TickStockDatabase
from src.core.services.relationship_cache import get_relationship_cache

logger = logging.getLogger(__name__)

class AnalysisService:
    """Unified service for all pattern/indicator analysis."""

    def __init__(self):
        self.indicator_service = IndicatorService()
        self.pattern_service = PatternService()
        self.db = TickStockDatabase()
        self.cache = get_relationship_cache()

    def analyze_symbol(
        self,
        symbol: str,
        calculate_indicators: bool = True,
        detect_patterns: bool = True,
        timeframe: str = "daily",
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        Run full analysis for symbol (indicators + patterns).
        This is the main entry point for analysis operations.
        """
        # 1. Load OHLCV data
        df = self._load_ohlcv_data(symbol, timeframe, start_date, end_date)

        if df.empty:
            return {
                'success': False,
                'symbol': symbol,
                'error': 'No OHLCV data available'
            }

        results = {
            'success': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'bars_analyzed': len(df),
            'indicators': {},
            'patterns': {}
        }

        # 2. Calculate indicators (if requested)
        if calculate_indicators:
            logger.info(f"Calculating indicators for {symbol}")
            results['indicators'] = self.indicator_service.calculate_all_indicators(
                symbol, df, timeframe
            )

        # 3. Detect patterns (if requested)
        if detect_patterns:
            logger.info(f"Detecting patterns for {symbol}")
            results['patterns'] = self.pattern_service.detect_all_patterns(
                symbol, df, indicators=results['indicators'], timeframe=timeframe
            )

        return results

    def analyze_universe(
        self,
        universe: str,
        parallel: bool = True,
        max_workers: int = 10,
        timeframe: str = "daily"
    ) -> Dict[str, Any]:
        """Run full analysis for all symbols in universe with parallel processing."""
        # Get universe symbols
        symbols = self.cache.get_universe_symbols(universe)

        if not symbols:
            return {
                'success': False,
                'universe': universe,
                'error': 'No symbols found in universe'
            }

        logger.info(f"Analyzing {len(symbols)} symbols in {universe} universe")

        if parallel:
            return self._analyze_universe_parallel(symbols, max_workers, timeframe)
        else:
            return self._analyze_universe_sequential(symbols, timeframe)

    def _analyze_universe_parallel(
        self,
        symbols: List[str],
        max_workers: int,
        timeframe: str
    ) -> Dict[str, Any]:
        """Parallel universe analysis with ThreadPoolExecutor."""
        results = {
            'success': True,
            'total_symbols': len(symbols),
            'successful': 0,
            'failed': 0,
            'symbol_results': {}
        }

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.analyze_symbol,
                    symbol,
                    calculate_indicators=True,
                    detect_patterns=True,
                    timeframe=timeframe
                ): symbol
                for symbol in symbols
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result(timeout=30)  # 30s timeout per symbol

                    if result.get('success'):
                        results['successful'] += 1
                    else:
                        results['failed'] += 1

                    results['symbol_results'][symbol] = result

                except Exception as e:
                    logger.error(f"Failed to analyze {symbol}: {e}")
                    results['failed'] += 1
                    results['symbol_results'][symbol] = {
                        'success': False,
                        'symbol': symbol,
                        'error': str(e)
                    }

        return results

    def _analyze_universe_sequential(
        self,
        symbols: List[str],
        timeframe: str
    ) -> Dict[str, Any]:
        """Sequential universe analysis (for debugging)."""
        results = {
            'success': True,
            'total_symbols': len(symbols),
            'successful': 0,
            'failed': 0,
            'symbol_results': {}
        }

        for symbol in symbols:
            try:
                result = self.analyze_symbol(
                    symbol,
                    calculate_indicators=True,
                    detect_patterns=True,
                    timeframe=timeframe
                )

                if result.get('success'):
                    results['successful'] += 1
                else:
                    results['failed'] += 1

                results['symbol_results'][symbol] = result

            except Exception as e:
                logger.error(f"Failed to analyze {symbol}: {e}")
                results['failed'] += 1
                results['symbol_results'][symbol] = {
                    'success': False,
                    'symbol': symbol,
                    'error': str(e)
                }

        return results

    def _load_ohlcv_data(
        self,
        symbol: str,
        timeframe: str = "daily",
        start_date: str = None,
        end_date: str = None
    ) -> pd.DataFrame:
        """Load OHLCV data for analysis."""
        import pandas as pd

        # Map timeframe to table name
        table_mapping = {
            "daily": "ohlcv_daily",
            "hourly": "ohlcv_hourly",
            "weekly": "ohlcv_weekly",
            "monthly": "ohlcv_monthly"
        }

        table_name = table_mapping.get(timeframe, "ohlcv_daily")

        # Build query
        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM {table_name}
            WHERE symbol = %s
        """
        params = [symbol]

        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)

        query += " ORDER BY timestamp ASC"

        # Execute query
        rows = self.db.execute_read(query, tuple(params))

        if not rows:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df.index = pd.to_datetime(df['timestamp'])

        return df
```

### Integration Points

```yaml
# === DATABASE ===

# Migration: Create indicator_results table (if not exists)
migration_file: src/infrastructure/database/migrations/migration_068_indicator_results.sql
migration_content: |
  -- UP
  CREATE TABLE IF NOT EXISTS indicator_results (
      id BIGSERIAL PRIMARY KEY,
      indicator_id INTEGER NOT NULL REFERENCES indicator_definitions(id),
      symbol VARCHAR(10) NOT NULL,
      calculated_at TIMESTAMP WITH TIME ZONE NOT NULL,
      value DECIMAL(12,4),
      value_data JSONB NOT NULL,
      metadata JSONB,

      -- Indexes
      INDEX idx_indicator_results_symbol_time (symbol, calculated_at),
      INDEX idx_indicator_results_indicator (indicator_id)
  );

  -- DOWN
  DROP TABLE IF EXISTS indicator_results CASCADE;

# Query patterns to add
query_location: src/analysis/services/indicator_service.py
query_example_select: |
  SELECT name, code_reference, class_name, default_params
  FROM indicator_definitions
  WHERE enabled = true
query_example_insert: |
  INSERT INTO indicator_results
  (indicator_id, symbol, calculated_at, value, value_data, metadata)
  VALUES (%s, %s, %s, %s, %s, %s)
performance: "<50ms query time (verify with EXPLAIN ANALYZE)"

# === REDIS CHANNELS ===

# Note: Sprint 68 does NOT publish to Redis (that's Sprint 69)
# Sprint 68 focuses on calculation logic only, storage in database

subscribe_in: N/A (Sprint 69 - background jobs publish after calculation)
channel_pattern: N/A
message_format: N/A

# === WEBSOCKET ===

# Note: Sprint 68 does NOT broadcast via WebSocket (that's Sprint 69)
# Sprint 68 establishes analysis capability, Sprint 69 adds real-time broadcasting

event_handler: N/A (Sprint 69)
event_name: N/A
broadcast_method: N/A

# === FLASK BLUEPRINTS ===

# Note: Sprint 68 does NOT add REST API routes
# Analysis accessible programmatically via AnalysisService
# Sprint 69 will add API endpoints if needed

blueprint_file: N/A
blueprint_name: N/A

# === CONFIG ===

# Add to .env
add_to: .env
variables: |
  # Analysis Configuration
  ANALYSIS_ENABLED=true
  ANALYSIS_MAX_WORKERS=10
  ANALYSIS_TIMEOUT_SECONDS=30

  # Pattern Registry Cache
  PATTERN_REGISTRY_CACHE_TTL_SECONDS=300

  # Dynamic Loading
  DYNAMIC_LOADER_INVALIDATE_CACHES=true

# === STARTUP ===

# Service initialization (Sprint 69 - background jobs)
startup_file: N/A (Sprint 69)
initialization: N/A
health_check: N/A
```

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# TickStock Standard: Ruff for linting and formatting
# Run after each file creation - fix before proceeding

# File-specific validation
ruff check src/analysis/ --fix     # Auto-format and fix linting issues
ruff format src/analysis/          # Ensure consistent formatting

# Project-wide validation (final check)
ruff check src/ --fix
ruff format src/

# Expected: Zero errors. If errors exist, READ output and fix before proceeding.
# Note: TickStock does not use mypy - rely on runtime type checking and tests
```

### Level 2: Unit Tests (Component Validation)

```bash
# TickStock Standard: pytest for all testing
# Test each component as it's created

# Indicator unit tests
python -m pytest tests/unit/analysis/indicators/ -v

# Pattern unit tests
python -m pytest tests/unit/analysis/patterns/ -v

# Service unit tests
python -m pytest tests/unit/analysis/services/ -v

# All analysis unit tests
python -m pytest tests/unit/analysis/ -v

# Coverage validation
python -m pytest tests/unit/analysis/ --cov=src/analysis --cov-report=term-missing

# Expected: 50+ tests pass, >80% coverage on business logic
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
# CRITICAL: Must run before ANY commit

# Primary integration test runner
python run_tests.py

# Alternative detailed runner
python tests/integration/run_integration_tests.py

# Expected Output:
# - 2+ tests passing
# - ~30 second runtime
# - Pattern flow tests passing
# - Core integration may fail if services not running (acceptable in dev)

# NOTE: RLock warning can be ignored (known asyncio quirk)

# Analysis-specific integration tests
python -m pytest tests/integration/test_analysis_integration.py -v
python -m pytest tests/integration/test_regression_vs_tickstockpl.py -v

# Database integration validation
PGPASSWORD=your_password psql -U app_readwrite -d tickstock -c "SELECT COUNT(*) FROM indicator_results;"
PGPASSWORD=your_password psql -U app_readwrite -d tickstock -c "SELECT COUNT(*) FROM daily_patterns;"

# Expected: Database writes successful, data retrievable
```

### Level 4: TickStock-Specific Validation

```bash
# === REGRESSION VALIDATION (CRITICAL) ===

# Run regression tests vs TickStockPL baseline
python -m pytest tests/integration/test_regression_vs_tickstockpl.py -v

# Expected: Zero regressions
# - All indicator values match TickStockPL (±0.01 tolerance)
# - All pattern detections match TickStockPL (identical timestamps)

# === PERFORMANCE BENCHMARKING ===

# Test analyze_symbol() performance
python -c "
from src.analysis.services.analysis_service import AnalysisService
import time

service = AnalysisService()
start = time.time()
result = service.analyze_symbol('AAPL')
elapsed = time.time() - start
print(f'analyze_symbol() took {elapsed:.2f}s')
assert elapsed < 1.0, f'Performance target missed: {elapsed:.2f}s > 1.0s'
"

# Target: <1s per symbol
# Measure: Add timing logs and verify in output

# Test analyze_universe() performance
python -c "
from src.analysis.services.analysis_service import AnalysisService
import time

service = AnalysisService()
start = time.time()
result = service.analyze_universe('nasdaq100', parallel=True, max_workers=10)
elapsed = time.time() - start
print(f'analyze_universe(nasdaq100) took {elapsed:.2f}s')
assert result['total_symbols'] > 0
print(f\"Analyzed {result['successful']}/{result['total_symbols']} symbols\")
"

# Target: <10 minutes for 500 symbols
# Measure: Verify parallel speedup vs sequential

# === DATABASE WRITE VALIDATION ===

# Verify indicator results storage
PGPASSWORD=your_password psql -U app_readwrite -d tickstock -c "
SELECT symbol, indicator_id, calculated_at, value
FROM indicator_results
ORDER BY calculated_at DESC
LIMIT 10;
"

# Verify pattern detection storage
PGPASSWORD=your_password psql -U app_readwrite -d tickstock -c "
SELECT symbol, pattern_id, detected_at, confidence
FROM daily_patterns
ORDER BY detected_at DESC
LIMIT 10;
"

# Expected: Recent analysis results stored correctly

# === DYNAMIC LOADING VALIDATION ===

# Verify all patterns/indicators loadable from database
python -c "
from src.analysis.services.dynamic_loader import DynamicPatternIndicatorLoader

loader = DynamicPatternIndicatorLoader()

# Load patterns for daily timeframe
patterns = loader.load_patterns_for_timeframe('daily')
print(f'Loaded {len(patterns)} patterns')
assert len(patterns) >= 20, 'Should load 20+ patterns'

# Load indicators
indicators = loader.load_indicators_for_timeframe('daily')
print(f'Loaded {len(indicators)} indicators')
assert len(indicators) >= 15, 'Should load 15+ indicators'
"

# Expected: All patterns/indicators loaded successfully, NO ImportError

# === NO FALLBACK ENFORCEMENT ===

# Verify ImportError raised for missing pattern
python -c "
from src.analysis.services.dynamic_loader import DynamicPatternIndicatorLoader

loader = DynamicPatternIndicatorLoader()

try:
    # Attempt to load non-existent pattern
    loader._import_class('src.analysis.patterns.nonexistent', 'NonExistent')
    assert False, 'Should have raised ImportError'
except ImportError as e:
    print(f'CORRECT: ImportError raised - {e}')
"

# Expected: ImportError raised (NO silent fallback)

# === ARCHITECTURE COMPLIANCE ===

# Verify NO writes to ohlcv_* tables (read-only constraint)
grep -r "INSERT INTO ohlcv" src/analysis/
grep -r "UPDATE ohlcv" src/analysis/
grep -r "DELETE FROM ohlcv" src/analysis/

# Expected: No matches (analysis is read-only for OHLCV)

# Verify writes ONLY to indicator_results and daily_patterns
grep -r "INSERT INTO" src/analysis/

# Expected: Only indicator_results and daily_patterns inserts

# === CODE QUALITY CHECKS ===

# Verify no .iterrows() or .apply(axis=1) in production code
grep -r "\.iterrows()" src/analysis/
grep -r "\.apply.*axis=1" src/analysis/

# Expected: No matches (all vectorized operations)

# Verify all indicators return convention-compliant dict
python -m pytest tests/unit/analysis/indicators/ -k "test_return_structure" -v

# Expected: All tests pass (value, value_data, metadata fields present)

# Verify all patterns return pd.Series (boolean)
python -m pytest tests/unit/analysis/patterns/ -k "test_return_type" -v

# Expected: All tests pass (returns pd.Series with dtype bool)
```

## Final Validation Checklist

### Technical Validation

- [ ] All 4 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] No linting errors: `ruff check src/analysis/`
- [ ] No formatting issues: `ruff format src/analysis/ --check`
- [ ] Unit tests pass: `python -m pytest tests/unit/analysis/ -v` (50+ tests)
- [ ] Regression tests pass: Zero regressions vs TickStockPL baseline

### Feature Validation

- [ ] All 15 indicators calculate identically to TickStockPL (±0.01 tolerance)
- [ ] All 20+ patterns detect identically to TickStockPL (same timestamps)
- [ ] analyze_symbol() completes in <1s for 250 bars
- [ ] analyze_universe() processes 500 symbols in <10 minutes (parallel)
- [ ] Dynamic loading works: all patterns/indicators loaded from database
- [ ] Database storage works: indicator_results and daily_patterns populated
- [ ] Error cases handled gracefully: insufficient data, invalid params, missing patterns

### TickStock Architecture Validation

- [ ] Component role respected: AppV2 becomes Analyzer (NEW ROLE)
- [ ] Read-only OHLCV access: NO writes to ohlcv_* tables
- [ ] Database writes limited: ONLY indicator_results and daily_patterns
- [ ] NO FALLBACK policy enforced: ImportError raised if pattern/indicator not found
- [ ] Performance targets met: <1s per symbol, <10 min for 500 symbols
- [ ] Regression requirement met: 100% identical results vs TickStockPL baseline
- [ ] Sprint 17 integration: Pattern registry info set, confidence filtering works

### Code Quality Validation

- [ ] Follows existing codebase patterns and naming conventions
- [ ] File placement matches desired codebase tree structure
- [ ] Anti-patterns avoided: NO .iterrows(), NO .apply(axis=1), NO loops in detection
- [ ] Dependencies properly managed and imported
- [ ] Configuration properly integrated (pattern/indicator definitions in database)
- [ ] Code structure limits followed: max 500 lines/file, 50 lines/function
- [ ] Naming conventions: snake_case functions, PascalCase classes, UPPER_SNAKE_CASE constants
- [ ] All utility methods reused: _safe_divide(), calculate_body_size(), etc.
- [ ] Vectorized operations: All indicator/pattern calculations use pandas/NumPy vectorization

### Documentation & Deployment

- [ ] Code is self-documenting with clear variable/function names
- [ ] Logs are informative but not verbose
- [ ] Database migrations created and tested
- [ ] Environment variables documented (.env)
- [ ] No "Generated by Claude" comments in code or commits
- [ ] Sprint completion document created: core-analysis-migration-RESULTS.md

---

## Anti-Patterns to Avoid

### Generic Anti-Patterns
- ❌ Don't create new patterns when existing ones work
- ❌ Don't skip validation because "it should work"
- ❌ Don't ignore failing tests - fix them
- ❌ Don't use sync functions in async context
- ❌ Don't hardcode values that should be config
- ❌ Don't catch all exceptions - be specific

### TickStock-Specific Anti-Patterns (CRITICAL)

#### Architecture Violations
- ❌ **Don't violate read-only OHLCV constraint**
  - AppV2 reads ohlcv_daily but NEVER writes
  - Violation: Adding INSERT/UPDATE/DELETE for ohlcv_* tables

- ❌ **Don't create OHLCV aggregation in TickStockAppV2**
  - OHLCV aggregation belongs exclusively in TickStockPL (TickAggregator)
  - Sprint 42 removed this code - don't re-introduce it
  - AppV2 analyzes existing OHLCV data, does NOT create it

- ❌ **Don't use fallback logic for missing patterns/indicators**
  - NO FALLBACK policy: Missing class = ImportError (system fails explicitly)
  - Violation: Catching ImportError and silently skipping pattern
  - Correct: Raise ImportError, log error, halt processing

#### Data Handling Anti-Patterns
- ❌ **Don't return dict from BasePattern.detect()**
  - MUST return pd.Series (boolean), NOT dict or custom object
  - Violation: `return {"detected": True, "confidence": 0.85}`
  - Correct: `return pd.Series([True, False, ...], index=data.index)`

- ❌ **Don't violate indicator return convention**
  - MUST return dict with "value" (primary), "value_data" (all values), "metadata"
  - Violation: Using "histogram" as primary value for MACD (should be "macd_line")
  - Correct: value=macd_line, value_data={macd, signal, histogram}

- ❌ **Don't store NumPy types in JSONB fields**
  - Database JSONB requires Python types (float, int, str)
  - Violation: `value_data = {"rsi": np.float64(65.2)}`
  - Correct: `value_data = {"rsi": float(65.2)}`

#### Performance Anti-Patterns
- ❌ **Don't use loops for indicator/pattern calculations**
  - Use pandas/NumPy vectorized operations (50-100x faster)
  - Violation: `for i in range(len(df)): result.append(df['a'][i] * df['b'][i])`
  - Correct: `result = df['a'] * df['b']`

- ❌ **Don't use .iterrows() or .apply(axis=1) in production**
  - These are 60-740x slower than vectorized operations
  - Violation: `df.apply(lambda row: row['a'] * row['b'], axis=1)`
  - Correct: `df['a'] * df['b']`

- ❌ **Don't skip min_periods in rolling calculations**
  - Prevent partial windows (first N-1 values are NaN)
  - Violation: `df['close'].rolling(window=20).mean()` (partial windows)
  - Correct: `df['close'].rolling(window=20, min_periods=20).mean()`

#### Testing Anti-Patterns
- ❌ **Don't use exact equality for float comparisons**
  - Floating point precision issues require tolerance
  - Violation: `assert result['value'] == expected`
  - Correct: `self.assertAlmostEqual(result['value'], expected, places=2)`

- ❌ **Don't skip OHLC consistency in test data**
  - high MUST be >= all OHLC, low MUST be <= all OHLC
  - Violation: Creating random OHLC without consistency checks
  - Correct: `df['high'] = df[['open','high','low','close']].max(axis=1)`

- ❌ **Don't skip regression validation**
  - Sprint 68 REQUIRES 100% match with TickStockPL baseline
  - Violation: Skipping regression tests because "close enough"
  - Correct: Run test_regression_vs_tickstockpl.py, fix ALL discrepancies

#### EMA/RSI Calculation Anti-Patterns
- ❌ **Don't use adjust=True for standard EMA**
  - adjust=True gives weighted average, NOT standard EMA
  - Violation: `df['close'].ewm(span=20).mean()` (adjust=True by default)
  - Correct: `df['close'].ewm(span=20, adjust=False).mean()`

- ❌ **Don't use ewm(span=period) for Wilder's smoothing**
  - Wilder's smoothing uses alpha=1/period, NOT span=period
  - Violation: `gains.ewm(span=14, adjust=False).mean()` (incorrect for RSI)
  - Correct: `gains.ewm(alpha=1/14, adjust=False).mean()`

#### Database Anti-Patterns
- ❌ **Don't skip pattern_id lookup**
  - Patterns stored with FK to pattern_definitions
  - Violation: Hardcoding pattern_id=1 for all Doji patterns
  - Correct: Query pattern_definitions by name to get pattern_id

- ❌ **Don't skip indicator_id lookup**
  - Indicators stored with FK to indicator_definitions
  - Violation: Hardcoding indicator_id=5 for RSI
  - Correct: Query indicator_definitions by name to get indicator_id

#### Sprint 17 Integration Anti-Patterns
- ❌ **Don't skip set_pattern_registry_info() call**
  - Patterns MUST be linked to database registry
  - Violation: Instantiating pattern without calling set_pattern_registry_info()
  - Correct: Call after instantiation to link pattern_id, confidence_threshold

- ❌ **Don't skip confidence scoring for registry-enabled patterns**
  - Patterns with _supports_confidence_scoring=True MUST filter by threshold
  - Violation: Returning all detections without confidence filtering
  - Correct: Call filter_by_confidence() before storing results
