# TickStockPL - Remove 5-Minute Pattern Detection Delay

## Issue Summary
Pattern detections are delayed 5-8 minutes after TickStockPL startup because `StreamingPatternJob` enforces a minimum 5-bar buffer requirement before detecting patterns. This causes TickStockAppV2 to fall back to database polling until Redis pattern channels start flowing.

## Root Cause Analysis

### File: `src/jobs/streaming_pattern_job.py`

**Lines 155-160** - Hard-coded minimum bar requirement:
```python
if len(historical_bars) < 5:
    # Not enough history yet
    logger.warning(
        f"PATTERN-JOB: Insufficient history for {symbol}: {len(historical_bars)} < 5"
    )
    return
```

**Impact**: This blocks ALL pattern detection for the first 5 minutes of streaming, regardless of whether individual patterns actually need 5 bars of history.

## The Problem

1. **Blanket Enforcement**: All patterns are blocked until 5 bars accumulate
2. **Inconsistent with Indicators**: Indicators can detect from bar 1-2
3. **Poor User Experience**: 5-8 minute wait after system starts
4. **Pattern-Agnostic**: Some patterns (Doji, PriceChange, AlwaysDetected) only need 1 bar

## Recommended Solution

### Option 1: Pattern-Specific Bar Requirements (BEST)

Allow each pattern class to declare its own minimum bar requirement and only enforce that requirement for that specific pattern.

**Implementation Steps:**

1. **Add `min_bars_required` property to pattern base class** (`src/patterns/base.py`):
```python
class BasePattern:
    """Base class for all pattern detectors."""

    @property
    def min_bars_required(self) -> int:
        """
        Minimum bars required for reliable pattern detection.

        Override in subclasses:
        - Single-bar patterns (Doji, Hammer): return 1
        - Multi-bar patterns (Engulfing): return 2
        - Trend-based patterns: return self.params.trend_period or 20

        Returns:
            Minimum number of bars needed
        """
        return 1  # Default: most patterns work with 1 bar
```

2. **Update pattern classes to declare requirements**:

```python
# Single-bar patterns - only need 1 bar
class DojiPattern(BasePattern):
    @property
    def min_bars_required(self) -> int:
        return 1

class PriceChangePattern(BasePattern):
    @property
    def min_bars_required(self) -> int:
        return 1

# Multi-bar patterns - need 2+ bars
class BullishEngulfingPattern(BasePattern):
    @property
    def min_bars_required(self) -> int:
        return 2

# Trend patterns - need configurable period
class MinuteTrendPattern(BasePattern):
    @property
    def min_bars_required(self) -> int:
        return self.params.trend_period + 1  # Need period + 1 for rolling window
```

3. **Modify `StreamingPatternJob._detect_patterns()` (lines 155-160)**:

**REMOVE** this block:
```python
if len(historical_bars) < 5:
    # Not enough history yet
    logger.warning(
        f"PATTERN-JOB: Insufficient history for {symbol}: {len(historical_bars)} < 5"
    )
    return
```

**REPLACE** with per-pattern validation (around line 172):
```python
for pattern_name, pattern_metadata in self.patterns.items():
    try:
        # Get pattern instance
        pattern_instance = pattern_metadata.get("instance")

        # Check if pattern has enough bars
        min_bars = getattr(pattern_instance, 'min_bars_required', 1)
        if len(historical_bars) < min_bars:
            logger.debug(
                f"PATTERN-JOB: Skipping {pattern_name} for {symbol}: "
                f"need {min_bars} bars, have {len(historical_bars)}"
            )
            continue  # Skip this pattern, try next one

        logger.info(f"PATTERN-JOB: Calling {pattern_name}.detect() for {symbol}")

        # ... rest of detection logic ...
```

**Benefits:**
- ✅ Single-bar patterns detect immediately (1 minute)
- ✅ Multi-bar patterns detect when ready (2 minutes)
- ✅ Trend patterns wait for required history (20+ minutes)
- ✅ Matches indicator behavior (early detection)
- ✅ Preserves pattern quality (no false positives)

---

### Option 2: Reduce Global Minimum (SIMPLER BUT LESS OPTIMAL)

Simply reduce the hard-coded minimum from 5 to 2 bars.

**Change line 155:**
```python
# OLD
if len(historical_bars) < 5:

# NEW
if len(historical_bars) < 2:
```

**Benefits:**
- ✅ Quick fix (1 line change)
- ✅ Reduces delay from 5-8 minutes to 2-3 minutes

**Drawbacks:**
- ❌ Still delays single-bar patterns unnecessarily
- ❌ Doesn't account for pattern-specific needs
- ❌ Arbitrary threshold

---

### Option 3: Remove Global Check Entirely (RISKY)

Remove the bar count check completely and let pandas handle insufficient data.

**REMOVE** lines 155-160 entirely.

**Benefits:**
- ✅ Patterns detect as soon as possible
- ✅ No artificial delays

**Drawbacks:**
- ⚠️ Pandas `.rolling()` calls may fail on insufficient data
- ⚠️ Need to ensure all pattern classes handle edge cases
- ⚠️ Potential runtime errors

---

## Additional Considerations

### Pattern-Specific Data Requirements

Based on code review, here are patterns and their actual data needs:

| Pattern | File | Actual Bars Needed | Current Block |
|---------|------|-------------------|---------------|
| AlwaysDetected | `candlestick/always_detected.py` | 1 | ❌ 5 bars |
| PriceChange | `candlestick/price_change.py` | 1 | ❌ 5 bars |
| Doji | `candlestick/doji.py` | 1 | ❌ 5 bars |
| Hammer | `candlestick/hammer.py` | 1 | ❌ 5 bars |
| BullishEngulfing | `candlestick/bullish_engulfing.py` | 2 | ❌ 5 bars |
| BearishEngulfing | `candlestick/bearish_engulfing.py` | 2 | ❌ 5 bars |
| MinuteTrend | `streaming.py` | trend_period + 1 (usually 21) | ✅ Needs 5+ |

### Rolling Window Patterns

Some patterns use `.rolling(window=N, min_periods=N)` which REQUIRES N bars. These patterns will naturally fail gracefully if insufficient data:

```python
# From streaming.py line 78
volume_avg = data["volume"].rolling(window=20, min_periods=20).mean()
```

This pattern **correctly requires 20 bars** - it should wait. But blocking ALL patterns for this one is wrong.

---

## Recommendation

**Implement Option 1** (Pattern-Specific Bar Requirements).

**Why:**
1. Most patterns (Doji, Hammer, PriceChange, AlwaysDetected) only need 1 bar
2. Allows immediate pattern detection (matching indicator behavior)
3. Preserves data quality for patterns that genuinely need history
4. Follows Single Responsibility Principle (each pattern declares its needs)
5. Easy to maintain (new patterns declare their requirements)

**Timeline:**
- **Phase 1**: Add `min_bars_required` property to `BasePattern` (5 minutes)
- **Phase 2**: Update single-bar patterns to return `1` (10 minutes)
- **Phase 3**: Modify `StreamingPatternJob` to check per pattern (15 minutes)
- **Phase 4**: Test with TickStockAppV2 streaming (10 minutes)

**Total Estimated Effort**: 40 minutes

---

## Testing Verification

After implementing the fix, verify:

1. **TickStockPL Logs** - Patterns should detect within 1-2 minutes:
```bash
# Should see this after 1-2 minutes, not 5-8 minutes
grep "PATTERN-JOB: Successfully detected" logs/tickstockpl.log
```

2. **TickStockAppV2 Logs** - Redis channels should receive immediately:
```bash
# Should see pattern messages within 1-2 minutes
grep "REDIS-SUBSCRIBER DEBUG: Received message on channel: 'tickstock:patterns:streaming'" logs/tickstock.log
```

3. **Live Streaming Dashboard** - Patterns should appear within 1-2 minutes of startup

---

## Configuration Option (BONUS)

Add configuration to override minimum bars globally:

**In `config/tickstockpl_config.py`:**
```python
# Minimum bars for pattern detection (0 = use pattern-specific requirements)
STREAMING_PATTERN_MIN_BARS = 0
```

**In `StreamingPatternJob._detect_patterns()`:**
```python
global_min = self.config.get("STREAMING_PATTERN_MIN_BARS", 0)
if global_min > 0 and len(historical_bars) < global_min:
    return  # Respect global override

# Otherwise use pattern-specific requirements...
```

---

## Files to Modify

1. `src/patterns/base.py` - Add `min_bars_required` property
2. `src/patterns/candlestick/*.py` - Override for single-bar patterns
3. `src/patterns/streaming.py` - Override for trend patterns
4. `src/jobs/streaming_pattern_job.py` - Modify detection logic (lines 155-175)
5. (Optional) `config/tickstockpl_config.py` - Add configuration option

---

## Expected Outcome

**Before Fix:**
- Patterns start detecting after 5-8 minutes
- TickStockAppV2 uses database polling fallback
- Poor user experience

**After Fix:**
- Single-bar patterns detect at 1 minute (bar 1)
- Multi-bar patterns detect at 2 minutes (bar 2)
- Trend patterns detect when sufficient history available
- TickStockAppV2 receives Redis events immediately
- User sees patterns within 1-2 minutes of startup

---

## Contact

For questions about this fix, contact the TickStockAppV2 team or reference:
- Sprint 43 diagnostics: `docs/planning/sprints/sprint43/`
- Redis channel monitoring: `scripts/diagnostics/monitor_redis_channels.py`
