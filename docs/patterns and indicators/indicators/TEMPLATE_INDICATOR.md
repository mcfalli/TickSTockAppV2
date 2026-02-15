### [Indicator Name] Calculation Instructions for TickStock.ai

**Created**: [Date]
**Category**: [trend|momentum|volatility|volume|directional]
**Display Order**: [Number 10-99]
**Implementation**: `src/analysis/indicators/[indicator_name].py`

---

## Overview

**Description**: [Brief 1-2 sentence description of what this indicator measures]

**Formula**: [Mathematical formula or calculation method]

**Interpretation**: [How to interpret values - bullish/bearish signals, overbought/oversold levels, etc.]

**Typical Range**: [e.g., 0-100 for RSI, unbounded for MACD, etc.]

**Parameters**:
- `period`: [Default value] - [Description]
- `[param2]`: [Default value] - [Description]

---

## Storage Schema

**Table**: `daily_indicators`

**Columns**:
- `symbol` — ticker (text)
- `indicator_type` — lowercase with underscore: '[indicator_name]'
- `calculation_timestamp` — exact minute (intraday) or day-end timestamp (EOD)
- `timeframe` — '1min' or 'daily'
- `value_data` — JSONB with calculation results: `{"[indicator_name]": [value], "[sub_value]": [value]}`
- `metadata` — JSONB with context: `{"source": "batch_eod", "periods_used": N, "[additional_context]": value}`
- `expiration_date` — timestamp when data becomes stale (next day at market close)

**Persistence Pattern** (Sprint 74 - TimescaleDB Hypertables):
```sql
-- DELETE existing entry
DELETE FROM daily_indicators
WHERE symbol = :symbol
  AND indicator_type = :indicator_type
  AND timeframe = :timeframe;

-- INSERT new entry
INSERT INTO daily_indicators
(symbol, indicator_type, value_data, calculation_timestamp,
 expiration_date, timeframe, metadata)
VALUES (:symbol, :indicator_type, :value_data, NOW(),
        :expiration_date, :timeframe, :metadata);
```

---

## Calculation Details

### Data Requirements

**Minimum Bars Required**: [N bars]

**Data Validation**:
- If `len(data) < [N]`, return `None` and skip storage
- Required columns: `['open', 'high', 'low', 'close', 'volume']` (or subset)
- Check for NaN values in required columns

### Step-by-Step Calculation

**Step 1**: [First calculation step]
```python
# Code example
```

**Step 2**: [Second calculation step]
```python
# Code example
```

**Step 3**: [Final calculation step]
```python
# Code example
```

### Pandas Implementation

```python
import pandas as pd
import numpy as np

def calculate_[indicator_name](data: pd.DataFrame, period: int = [default]) -> dict:
    """
    Calculate [Indicator Name] indicator.

    Args:
        data: DataFrame with OHLCV columns
        period: Lookback period (default: [default])

    Returns:
        Dictionary with indicator_type, value_data, metadata
    """
    # Validate data
    if len(data) < period:
        return None

    # Calculation logic here
    [calculation_code]

    # Extract latest value
    latest_value = [indicator_series].iloc[-1]

    # Return formatted result
    return {
        "indicator_type": "[indicator_name]",
        "value_data": {
            "[indicator_name]": float(latest_value) if not pd.isna(latest_value) else None,
            # Additional sub-values if needed
        },
        "metadata": {
            "periods_used": period,
            # Additional context
        }
    }
```

---

## Dependencies

**Requires** (Processing Order):
- [List indicators that must be calculated FIRST, if any]
- If no dependencies: "None - uses only OHLCV data"

**Used By** (Downstream Dependencies):
- [List indicators that may reference this indicator, if known]

**Database Definition**:
```sql
-- indicator_definitions table entry
INSERT INTO indicator_definitions
(name, display_order, category, class_name, method_name,
 instantiation_params, min_bars_required, enabled,
 short_description, display_name)
VALUES
('[indicator_name]', [display_order], '[category]', '[ClassName]', 'calculate',
 '{"period": [default]}', [min_bars], true,
 '[Brief description]', '[Display Name]');
```

---

## Validation Rules

**Data Quality**:
- ✅ No gaps > 5 consecutive trading days
- ✅ No duplicate timestamps
- ✅ All OHLC values positive
- ✅ Volume ≥ 0

**Calculation Validation**:
- ✅ Output value in expected range: [range]
- ✅ No NaN values unless insufficient data
- ✅ Precision: float64

**Regression Testing**:
- Compare against [reference source - e.g., TradingView, Yahoo Finance]
- Tolerance: ±[acceptable_variance]

---

## Error Handling & Logging

```python
import logging
logger = logging.getLogger(__name__)

# Insufficient data
if len(data) < period:
    logger.warning(f"[INDICATOR_NAME]: Insufficient data for {symbol} - need {period}, have {len(data)}")
    return None

# Calculation error
try:
    result = [calculation]
except Exception as e:
    logger.error(f"[INDICATOR_NAME]: Calculation failed for {symbol}: {e}", exc_info=True)
    return None

# Data gap warning
if has_gap(data, threshold_days=5):
    logger.warning(f"[INDICATOR_NAME]: Data gap detected for {symbol} - {gap_days} days missing")
    metadata['data_gap_warning'] = True
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Calculation (single period) | <10ms | Vectorized pandas operation |
| Data fetch | <50ms | Database query |
| Persistence (DELETE + INSERT) | <20ms | Two SQL operations |
| **Total: Indicator update** | **<100ms** | End-to-end latency |

---

## Testing

**Unit Tests** (`tests/unit/test_[indicator_name].py`):
```python
def test_[indicator_name]_calculation():
    """Test [Indicator Name] calculation with known data."""
    # Test data
    data = pd.DataFrame({
        'close': [expected_values],
        # Other columns
    })

    # Calculate
    result = calculate_[indicator_name](data, period=[period])

    # Assert
    assert result['value_data']['[indicator_name]'] == pytest.approx([expected], rel=1e-2)

def test_[indicator_name]_insufficient_data():
    """Test handling of insufficient data."""
    data = pd.DataFrame({'close': [1, 2, 3]})  # Only 3 bars
    result = calculate_[indicator_name](data, period=10)
    assert result is None
```

**Integration Tests**:
- Verify DELETE + INSERT prevents duplicates
- Verify timeframe separation (1min vs daily)
- Verify metadata tracking

---

## References

**Technical Documentation**:
- [Link to authoritative source - e.g., Investopedia, technical analysis books]
- [Link to formula reference]

**Code References**:
- `src/analysis/indicators/[indicator_name].py` - Implementation
- `src/analysis/indicators/base_indicator.py` - Base class
- `docs/patterns and indicators/indicators/sma_ema_calculations.md` - Similar indicator example

---

## Document Status

**Version**: 1.0
**Last Updated**: [Date]
**Status**: ⚠️ **TEMPLATE** - Replace bracketed placeholders with actual values
**Sprint**: [Sprint number when implemented]
