### [Pattern Name] Detection Instructions for TickStock.ai

**Created**: [Date]
**Category**: [candlestick|multi_bar|streaming|daily|breakout]
**Display Order**: [Number 100-199]
**Implementation**: `src/analysis/patterns/[category]/[pattern_name].py`
**Pattern Type**: [Single-bar|Two-bar|Three-bar|Multi-bar]

---

## Overview

**Description**: [Brief 1-2 sentence description of the pattern]

**Signal**: [Bullish|Bearish|Reversal|Continuation]

**Reliability**: [High|Medium|Low]

**Typical Success Rate**: [Percentage, if known]

**Risk Level**: [Low|Medium|High]

**Confirmation**: [What confirms the pattern - e.g., volume, next candle close above/below, etc.]

---

## Storage Schema

**Table**: `daily_patterns`

**Columns**:
- `symbol` — ticker (text)
- `pattern_type` — lowercase with underscore: '[pattern_name]'
- `confidence` — float 0-100 (from Sprint 17 confidence scoring)
- `pattern_data` — JSONB with detection details
- `detection_timestamp` — when pattern was detected
- `expiration_date` — 48-hour retention (Sprint 74)
- `timeframe` — 'daily' (or '1min' for streaming patterns)
- `metadata` — JSONB with context

**Persistence Pattern** (Sprint 76 - Aligned with Indicators):
```sql
-- DELETE existing entry (prevent duplicates)
DELETE FROM daily_patterns
WHERE symbol = :symbol
  AND pattern_type = :pattern_type
  AND timeframe = :timeframe
  AND detection_timestamp::date = CURRENT_DATE;

-- INSERT new entry
INSERT INTO daily_patterns
(symbol, pattern_type, confidence, pattern_data,
 detection_timestamp, expiration_date, timeframe, metadata)
VALUES (:symbol, :pattern_type, :confidence, :pattern_data,
        NOW(), :expiration_date, :timeframe, :metadata);
```

---

## Pattern Recognition Rules

### Minimum Bars Required

**Bars Needed**: [N bars]

**Validation**:
```python
def get_minimum_bars(self) -> int:
    """Return minimum bars required for detection."""
    return [N]
```

### Visual Characteristics

**Diagram**:
```
[ASCII diagram showing pattern structure]

Example for Hammer:
    |
    |
  --|--
    |
    |
    |
    |
========  (long lower shadow, small body, little/no upper shadow)
```

**Key Features**:
1. [Feature 1 - e.g., "Long lower shadow (≥2x body length)"]
2. [Feature 2 - e.g., "Small real body"]
3. [Feature 3 - e.g., "Little or no upper shadow"]
4. [Feature 4 - additional characteristics]

### Detection Logic

**Required Conditions** (ALL must be true):
1. **[Condition 1]**: [Description and formula]
   ```python
   condition_1 = [boolean expression]
   ```

2. **[Condition 2]**: [Description and formula]
   ```python
   condition_2 = [boolean expression]
   ```

3. **[Condition 3]**: [Description and formula]
   ```python
   condition_3 = [boolean expression]
   ```

**Optional Enhancements** (increase confidence):
- [Enhancement 1] → +10% confidence
- [Enhancement 2] → +15% confidence
- [Enhancement 3] → +5% confidence

### Pandas Implementation

```python
import pandas as pd
import numpy as np

class [PatternName](BasePattern):
    """
    [Pattern Name] pattern detection.

    [Brief description of pattern characteristics]

    Detection Criteria:
    - [Criterion 1]
    - [Criterion 2]
    - [Criterion 3]
    """

    def __init__(self, params: dict = None):
        """Initialize [Pattern Name] detector."""
        super().__init__(params)
        self.name = "[pattern_name]"
        self.category = "[category]"

    def detect(
        self,
        data: pd.DataFrame,
        symbol: str = None,
        timeframe: str = "daily"
    ) -> pd.Series:
        """
        Detect [Pattern Name] pattern in OHLCV data.

        Args:
            data: DataFrame with OHLCV columns
            symbol: Stock symbol (optional)
            timeframe: Timeframe for detection

        Returns:
            Boolean Series indicating pattern detection at each index
        """
        # Validate data
        if len(data) < self.get_minimum_bars():
            return pd.Series([False] * len(data), index=data.index)

        # Required columns
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in data.columns for col in required_cols):
            return pd.Series([False] * len(data), index=data.index)

        # Calculate body and shadow sizes (vectorized)
        body = abs(data['close'] - data['open'])
        upper_shadow = data['high'] - data[['close', 'open']].max(axis=1)
        lower_shadow = data[['close', 'open']].min(axis=1) - data['low']
        total_range = data['high'] - data['low']

        # Detection conditions (vectorized boolean operations)
        condition_1 = [boolean_expression]
        condition_2 = [boolean_expression]
        condition_3 = [boolean_expression]

        # Combine conditions (ALL must be True)
        pattern_detected = condition_1 & condition_2 & condition_3

        return pattern_detected

    def get_minimum_bars(self) -> int:
        """Return minimum bars required."""
        return [N]

    def calculate_confidence(
        self,
        data: pd.DataFrame,
        index: int
    ) -> float:
        """
        Calculate confidence score for detected pattern.

        Args:
            data: OHLCV DataFrame
            index: Index where pattern detected

        Returns:
            Confidence score 0-100
        """
        base_confidence = 60.0  # Base confidence for meeting all conditions

        # Enhancement 1: [Description]
        if [enhancement_condition]:
            base_confidence += 10.0

        # Enhancement 2: [Description]
        if [enhancement_condition]:
            base_confidence += 15.0

        # Enhancement 3: [Description]
        if [enhancement_condition]:
            base_confidence += 5.0

        return min(base_confidence, 100.0)  # Cap at 100%
```

---

## Context & Market Conditions

**Best Used When**:
- [Market condition 1 - e.g., "After sustained downtrend"]
- [Market condition 2 - e.g., "At support level"]
- [Market condition 3 - e.g., "With high volume"]

**Avoid Using When**:
- [Condition 1 - e.g., "In choppy/sideways market"]
- [Condition 2 - e.g., "During low volume periods"]

**Confirmation Signals**:
1. [Signal 1 - e.g., "Next candle closes above pattern high"]
2. [Signal 2 - e.g., "Volume increases on confirmation"]
3. [Signal 3 - e.g., "RSI shows bullish divergence"]

---

## Dependencies

**Requires** (Processing Order):
- Patterns are independent (no dependencies on other patterns)
- **Indicators**: [List if pattern uses indicator values - e.g., "None" or "RSI for divergence check"]

**Database Definition**:
```sql
-- pattern_definitions table entry
INSERT INTO pattern_definitions
(name, display_order, category, class_name, method_name,
 instantiation_params, min_bars_required, enabled,
 short_description, display_name, confidence_threshold,
 risk_level, typical_success_rate)
VALUES
('[pattern_name]', [display_order], '[category]', '[ClassName]', 'detect',
 '{}', [min_bars], true,
 '[Brief description]', '[Display Name]', 60.0,
 '[Low|Medium|High]', [success_rate_decimal]);
```

---

## Validation Rules

**Data Quality**:
- ✅ OHLC values: 0 < L ≤ O,C ≤ H
- ✅ Volume ≥ 0
- ✅ No duplicate timestamps
- ✅ No NaN values in required columns

**Pattern Validation**:
- ✅ Returns boolean pd.Series (NOT dict)
- ✅ Series length matches input data length
- ✅ Confidence score: 0 ≤ confidence ≤ 100
- ✅ Minimum bars check enforced

**Edge Cases**:
- **Doji candle** (O ≈ C): [How pattern handles this]
- **Gap up/down**: [How pattern handles gaps]
- **Extreme volatility**: [How pattern handles outliers]

---

## Error Handling & Logging

```python
import logging
logger = logging.getLogger(__name__)

# Insufficient data
if len(data) < self.get_minimum_bars():
    logger.debug(f"[PATTERN_NAME]: Insufficient data for {symbol} - need {self.get_minimum_bars()}, have {len(data)}")
    return pd.Series([False] * len(data), index=data.index)

# Missing columns
required_cols = ['open', 'high', 'low', 'close']
if not all(col in data.columns for col in required_cols):
    logger.error(f"[PATTERN_NAME]: Missing required columns for {symbol}")
    return pd.Series([False] * len(data), index=data.index)

# Invalid OHLC values
if (data['low'] > data['high']).any():
    logger.warning(f"[PATTERN_NAME]: Invalid OHLC values detected for {symbol}")
    return pd.Series([False] * len(data), index=data.index)
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Detection (vectorized) | <10ms | Boolean operations on pandas Series |
| Confidence calculation | <5ms | Per detected instance |
| **Total: Pattern detection** | **<20ms** | For 200-bar dataset |

---

## Testing

**Unit Tests** (`tests/unit/patterns/test_[pattern_name].py`):
```python
import pytest
import pandas as pd
from src.analysis.patterns.[category].[pattern_name] import [PatternName]

def test_[pattern_name]_basic_detection():
    """Test basic pattern detection with known data."""
    # Construct test data with clear pattern
    data = pd.DataFrame({
        'open': [values],
        'high': [values],
        'low': [values],
        'close': [values],
    })

    detector = [PatternName]()
    result = detector.detect(data)

    # Assert pattern detected at expected index
    assert result.iloc[-1] == True

def test_[pattern_name]_no_detection():
    """Test that pattern is NOT detected when conditions not met."""
    data = pd.DataFrame({
        'open': [values_not_matching_pattern],
        'high': [values],
        'low': [values],
        'close': [values],
    })

    detector = [PatternName]()
    result = detector.detect(data)

    assert result.iloc[-1] == False

def test_[pattern_name]_insufficient_data():
    """Test handling of insufficient data."""
    data = pd.DataFrame({
        'open': [1],
        'high': [2],
        'low': [0.5],
        'close': [1.5],
    })

    detector = [PatternName]()
    result = detector.detect(data)

    assert len(result) == 1
    assert result.iloc[0] == False

def test_[pattern_name]_confidence_scoring():
    """Test confidence score calculation."""
    # [Setup test data]
    detector = [PatternName]()
    confidence = detector.calculate_confidence(data, index=0)

    assert 0 <= confidence <= 100
```

**Integration Tests**:
- Verify DELETE + INSERT prevents duplicates
- Verify 48-hour expiration cleanup
- Verify pattern flow integration test passes

---

## References

**Technical Documentation**:
- [Link to authoritative source - e.g., Bulkowski's Encyclopedia, Investopedia]
- [Link to visual examples]

**Statistical Studies**:
- [Success rate studies, if available]
- [Reliability research]

**Code References**:
- `src/analysis/patterns/[category]/[pattern_name].py` - Implementation
- `src/analysis/patterns/base_pattern.py` - Base class
- `docs/patterns and indicators/patterns/[similar_pattern].md` - Similar pattern example

---

## Document Status

**Version**: 1.0
**Last Updated**: [Date]
**Status**: ⚠️ **TEMPLATE** - Replace bracketed placeholders with actual values
**Sprint**: [Sprint number when implemented]
