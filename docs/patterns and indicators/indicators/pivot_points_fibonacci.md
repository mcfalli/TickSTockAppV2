### Pivot Points (Fibonacci) Calculation Instructions for TickStock.ai

**Created**: February 15, 2026
**Category**: directional
**Display Order**: 71
**Implementation**: `src/analysis/indicators/directional/pivot_points_fibonacci.py`
**Variant**: Fibonacci Pivots (for Standard variant, see `pivot_points.md`)

---

## Overview

**Description**: Fibonacci Pivot Points are support and resistance levels calculated from the prior trading day's OHLC data using Fibonacci ratios (38.2%, 61.8%, 100%). They provide intra-day price targets based on natural retracement levels.

**Formula**:
```
PP (Pivot Point) = (High + Low + Close) / 3
Range = High - Low

R1 (Resistance 1) = PP + (0.382 × Range)
R2 (Resistance 2) = PP + (0.618 × Range)
R3 (Resistance 3) = PP + (1.000 × Range)

S1 (Support 1) = PP - (0.382 × Range)
S2 (Support 2) = PP - (0.618 × Range)
S3 (Support 3) = PP - (1.000 × Range)

All calculations use prior trading day's OHLC data.
```

**Interpretation**:
- **PP (Pivot Point)**: Central equilibrium level (same as Standard Pivots)
- **R1 (38.2%)**: First Fibonacci retracement resistance
- **R2 (61.8%)**: Golden ratio resistance (most significant)
- **R3 (100%)**: Full range extension resistance
- **S1 (38.2%)**: First Fibonacci retracement support
- **S2 (61.8%)**: Golden ratio support (most significant)
- **S3 (100%)**: Full range extension support
- **Golden Ratio**: R2/S2 levels (61.8%) are most respected in trending markets

**Typical Range**: Same scale as price (e.g., $148-$152 for a $150 stock)

**Parameters**:
- None - Fibonacci ratios are fixed (0.382, 0.618, 1.000)

**Usage Context**:
- Calculate once per day using prior day's OHLC
- Use throughout current trading day for intra-day targets
- More effective in trending markets than Standard Pivots
- 61.8% levels (R2/S2) are most reliable
- Combine with Fibonacci retracements for confluence zones

---

## Storage Schema

**Table**: `daily_indicators`

**Columns**:
- `symbol` — ticker (text)
- `indicator_type` — lowercase with underscore: 'pivot_points_fibonacci'
- `calculation_timestamp` — timestamp when calculated (typically market open)
- `timeframe` — 'daily' (calculated from prior day data, used for intra-day reference)
- `value_data` — JSONB with calculation results:
  ```json
  {
    "pp": 150.00,
    "r1": 151.53,
    "r2": 152.47,
    "r3": 154.00,
    "s1": 148.47,
    "s2": 147.53,
    "s3": 146.00
  }
  ```
- `metadata` — JSONB with context:
  ```json
  {
    "source": "batch_eod",
    "prior_date": "2026-02-14",
    "prior_high": 152.00,
    "prior_low": 148.00,
    "prior_close": 150.00,
    "range": 4.00
  }
  ```
- `expiration_date` — timestamp when data becomes stale (next day market open)

**Persistence Pattern** (Sprint 74 - TimescaleDB Hypertables):
```sql
-- DELETE existing entry (daily refresh)
DELETE FROM daily_indicators
WHERE symbol = :symbol
  AND indicator_type = 'pivot_points_fibonacci'
  AND timeframe = 'daily';

-- INSERT new entry
INSERT INTO daily_indicators
(symbol, indicator_type, value_data, calculation_timestamp,
 expiration_date, timeframe, metadata)
VALUES (:symbol, 'pivot_points_fibonacci', :value_data, NOW(),
        :expiration_date, 'daily', :metadata);
```

---

## Calculation Details

### Data Requirements

**Minimum Bars Required**: 2 bars (current + prior day)

**Data Validation**:
- If `len(data) < 2`, return `None` and skip storage
- Required columns: `['high', 'low', 'close', 'date']`
- Check for NaN values in required columns
- Verify prior day is a trading day (not weekend/holiday)

### Step-by-Step Calculation

**Step 1**: Extract prior day's OHLC data
```python
# Assuming data is sorted by date ascending
prior_day = data.iloc[-2]  # Second-to-last row
prior_high = prior_day['high']
prior_low = prior_day['low']
prior_close = prior_day['close']
prior_date = prior_day['date']
```

**Step 2**: Calculate Pivot Point (PP) and Range
```python
pp = (prior_high + prior_low + prior_close) / 3
range_hl = prior_high - prior_low
```

**Step 3**: Calculate Fibonacci Resistance Levels
```python
r1 = pp + (0.382 * range_hl)  # 38.2% Fibonacci
r2 = pp + (0.618 * range_hl)  # 61.8% Golden Ratio
r3 = pp + (1.000 * range_hl)  # 100% Range Extension
```

**Step 4**: Calculate Fibonacci Support Levels
```python
s1 = pp - (0.382 * range_hl)  # 38.2% Fibonacci
s2 = pp - (0.618 * range_hl)  # 61.8% Golden Ratio
s3 = pp - (1.000 * range_hl)  # 100% Range Extension
```

### Pandas Implementation

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class FibonacciPivotPointsParams:
    """Fibonacci Pivot Points indicator parameters."""
    # No parameters - Fibonacci ratios are fixed
    pass

class FibonacciPivotPointsIndicator:
    """
    Fibonacci Pivot Points support and resistance indicator.

    Calculates intra-day price targets from prior trading day's OHLC data
    using Fibonacci ratios. Provides 7 levels: PP (pivot), R1/R2/R3 (resistance),
    S1/S2/S3 (support) based on 38.2%, 61.8%, and 100% retracements.

    Calculation:
    - PP = (High + Low + Close) / 3
    - Range = High - Low
    - R1 = PP + (0.382 × Range)
    - R2 = PP + (0.618 × Range)
    - R3 = PP + (1.000 × Range)
    - S1 = PP - (0.382 × Range)
    - S2 = PP - (0.618 × Range)
    - S3 = PP - (1.000 × Range)
    """

    def __init__(self, params: Optional[dict] = None):
        """Initialize Fibonacci Pivot Points indicator."""
        self.params = FibonacciPivotPointsParams()
        self.name = "pivot_points_fibonacci"
        self.category = "directional"

    def calculate(self, data: pd.DataFrame) -> Optional[dict]:
        """
        Calculate Fibonacci Pivot Points indicator.

        Args:
            data: DataFrame with OHLC columns, sorted by date ascending

        Returns:
            Dictionary with indicator_type, value_data, metadata
        """
        # Validate data
        if len(data) < 2:
            return None

        required_cols = ['high', 'low', 'close']
        if not all(col in data.columns for col in required_cols):
            return None

        # Check for NaN values
        if data[required_cols].isna().any().any():
            return None

        # Extract prior day's OHLC (second-to-last row)
        prior_day = data.iloc[-2]
        prior_high = float(prior_day['high'])
        prior_low = float(prior_day['low'])
        prior_close = float(prior_day['close'])

        # Get prior date if available
        if 'date' in data.columns:
            prior_date = str(prior_day['date'])
        else:
            prior_date = None

        # Skip if any prior day values are NaN
        if any(pd.isna(val) for val in [prior_high, prior_low, prior_close]):
            return None

        # Calculate Fibonacci pivots
        # Pivot Point (same as standard)
        pp = (prior_high + prior_low + prior_close) / 3
        range_hl = prior_high - prior_low

        # Fibonacci Resistance Levels
        r1 = pp + (0.382 * range_hl)
        r2 = pp + (0.618 * range_hl)
        r3 = pp + (1.000 * range_hl)

        # Fibonacci Support Levels
        s1 = pp - (0.382 * range_hl)
        s2 = pp - (0.618 * range_hl)
        s3 = pp - (1.000 * range_hl)

        # Return formatted result
        return {
            "indicator_type": "pivot_points_fibonacci",
            "value_data": {
                "pp": round(pp, 2),
                "r1": round(r1, 2),
                "r2": round(r2, 2),
                "r3": round(r3, 2),
                "s1": round(s1, 2),
                "s2": round(s2, 2),
                "s3": round(s3, 2)
            },
            "metadata": {
                "prior_date": prior_date,
                "prior_high": prior_high,
                "prior_low": prior_low,
                "prior_close": prior_close,
                "range": round(range_hl, 2)
            }
        }
```

---

## Dependencies

**Requires** (Processing Order):
- Prior day's OHLC data (requires 2+ days of history)
- Sprint 72 OHLCVDataService for fetching historical data

**Used By** (Downstream Dependencies):
- Fibonacci-based trading strategies
- Confluence zone analysis (with Fibonacci retracements)
- Trend following with natural retracement levels

**Database Definition**:
```sql
-- indicator_definitions table entry
INSERT INTO indicator_definitions
(name, display_order, category, class_name, method_name,
 instantiation_params, min_bars_required, enabled,
 short_description, display_name)
VALUES
('pivot_points_fibonacci', 71, 'directional', 'FibonacciPivotPointsIndicator', 'calculate',
 '{}', 2, true,
 'Fibonacci pivot points for intra-day support/resistance levels', 'Pivot Points (Fibonacci)');
```

---

## Validation Rules

**Data Quality**:
- ✅ No gaps > 5 consecutive trading days
- ✅ No duplicate timestamps
- ✅ All OHLC values positive
- ✅ High ≥ Low (valid OHLC relationship)

**Calculation Validation**:
- ✅ R3 > R2 > R1 > PP > S1 > S2 > S3 (levels properly ordered)
- ✅ PP near prior day's price range
- ✅ R2 and S2 (61.8%) between R1/R3 and S1/S3
- ✅ No NaN values unless insufficient data
- ✅ Precision: 2 decimal places (standard for stock prices)

**Regression Testing**:
- Compare against TradingView Fibonacci Pivot Points indicator
- Tolerance: ±$0.01 for pivot levels

---

## Error Handling & Logging

```python
import logging
logger = logging.getLogger(__name__)

# Insufficient data
if len(data) < 2:
    logger.warning(f"Fibonacci Pivots: Insufficient data for {symbol} - need 2 days, have {len(data)}")
    return None

# Missing columns
required_cols = ['high', 'low', 'close']
if not all(col in data.columns for col in required_cols):
    logger.error(f"Fibonacci Pivots: Missing required columns for {symbol}")
    return None

# NaN values in prior day
if any(pd.isna(val) for val in [prior_high, prior_low, prior_close]):
    logger.warning(f"Fibonacci Pivots: NaN values in prior day data for {symbol}")
    return None

# Invalid OHLC relationship
if prior_high < prior_low:
    logger.warning(f"Fibonacci Pivots: Invalid OHLC data for {symbol} - high < low")
    return None

# Calculation error
try:
    pp = (prior_high + prior_low + prior_close) / 3
    range_hl = prior_high - prior_low
    r1 = pp + (0.382 * range_hl)
except Exception as e:
    logger.error(f"Fibonacci Pivots: Calculation failed for {symbol}: {e}", exc_info=True)
    return None

# Data gap warning (weekend/holiday)
if 'date' in data.columns:
    current_date = data.iloc[-1]['date']
    days_diff = (current_date - prior_date).days
    if days_diff > 3:  # More than weekend
        logger.warning(f"Fibonacci Pivots: Large date gap for {symbol} - {days_diff} days")
        metadata['data_gap_warning'] = True
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Calculation | <5ms | 10 arithmetic operations (3 more than Standard) |
| Prior day data fetch | <20ms | Database query for 2 days |
| Persistence (DELETE + INSERT) | <20ms | Two SQL operations |
| **Total: Indicator update** | **<50ms** | End-to-end latency |

---

## Testing

**Unit Tests** (`tests/unit/indicators/test_pivot_points_fibonacci.py`):
```python
import pytest
import pandas as pd
from datetime import datetime
from src.analysis.indicators.directional.pivot_points_fibonacci import FibonacciPivotPointsIndicator

def test_fibonacci_pivots_calculation():
    """Test Fibonacci pivot points calculation with known data."""
    # Prior day: H=110, L=100, C=105
    # Range = 110 - 100 = 10
    # PP = (110 + 100 + 105) / 3 = 105.0
    # R1 = 105 + (0.382 × 10) = 108.82
    # R2 = 105 + (0.618 × 10) = 111.18
    # R3 = 105 + (1.000 × 10) = 115.0
    # S1 = 105 - (0.382 × 10) = 101.18
    # S2 = 105 - (0.618 × 10) = 98.82
    # S3 = 105 - (1.000 × 10) = 95.0

    data = pd.DataFrame({
        'date': [datetime(2026, 2, 14), datetime(2026, 2, 15)],
        'high': [110.0, 112.0],
        'low': [100.0, 102.0],
        'close': [105.0, 108.0]
    })

    indicator = FibonacciPivotPointsIndicator()
    result = indicator.calculate(data)

    # Assert (with rounding tolerance)
    assert result is not None
    assert result['value_data']['pp'] == 105.0
    assert result['value_data']['r1'] == pytest.approx(108.82, abs=0.01)
    assert result['value_data']['r2'] == pytest.approx(111.18, abs=0.01)
    assert result['value_data']['r3'] == 115.0
    assert result['value_data']['s1'] == pytest.approx(101.18, abs=0.01)
    assert result['value_data']['s2'] == pytest.approx(98.82, abs=0.01)
    assert result['value_data']['s3'] == 95.0
    assert result['metadata']['range'] == 10.0

def test_fibonacci_pivots_level_ordering():
    """Test that Fibonacci pivot levels are properly ordered."""
    data = pd.DataFrame({
        'high': [100.0, 105.0],
        'low': [95.0, 98.0],
        'close': [98.0, 102.0]
    })

    indicator = FibonacciPivotPointsIndicator()
    result = indicator.calculate(data)

    # Assert proper ordering: R3 > R2 > R1 > PP > S1 > S2 > S3
    assert result['value_data']['r3'] > result['value_data']['r2']
    assert result['value_data']['r2'] > result['value_data']['r1']
    assert result['value_data']['r1'] > result['value_data']['pp']
    assert result['value_data']['pp'] > result['value_data']['s1']
    assert result['value_data']['s1'] > result['value_data']['s2']
    assert result['value_data']['s2'] > result['value_data']['s3']

def test_fibonacci_pivots_golden_ratio():
    """Test that R2/S2 use 61.8% golden ratio."""
    data = pd.DataFrame({
        'high': [110.0, 112.0],
        'low': [100.0, 102.0],
        'close': [105.0, 108.0]
    })

    indicator = FibonacciPivotPointsIndicator()
    result = indicator.calculate(data)

    pp = result['value_data']['pp']
    range_val = result['metadata']['range']

    # R2 should be PP + 0.618 * range
    expected_r2 = pp + (0.618 * range_val)
    assert result['value_data']['r2'] == pytest.approx(expected_r2, abs=0.01)

    # S2 should be PP - 0.618 * range
    expected_s2 = pp - (0.618 * range_val)
    assert result['value_data']['s2'] == pytest.approx(expected_s2, abs=0.01)

def test_fibonacci_pivots_insufficient_data():
    """Test handling of insufficient data (only 1 day)."""
    data = pd.DataFrame({
        'high': [100.0],
        'low': [95.0],
        'close': [98.0]
    })

    indicator = FibonacciPivotPointsIndicator()
    result = indicator.calculate(data)

    assert result is None

def test_fibonacci_pivots_missing_columns():
    """Test handling of missing required columns."""
    data = pd.DataFrame({
        'close': [100, 101]
    })

    indicator = FibonacciPivotPointsIndicator()
    result = indicator.calculate(data)

    assert result is None

def test_fibonacci_pivots_nan_values():
    """Test handling of NaN values in prior day."""
    data = pd.DataFrame({
        'high': [None, 105.0],  # NaN in prior day
        'low': [95.0, 98.0],
        'close': [98.0, 102.0]
    })

    indicator = FibonacciPivotPointsIndicator()
    result = indicator.calculate(data)

    assert result is None

def test_fibonacci_pivots_metadata():
    """Test metadata includes prior day OHLC and range."""
    data = pd.DataFrame({
        'date': [datetime(2026, 2, 14), datetime(2026, 2, 15)],
        'high': [152.0, 155.0],
        'low': [148.0, 149.0],
        'close': [150.0, 153.0]
    })

    indicator = FibonacciPivotPointsIndicator()
    result = indicator.calculate(data)

    # Assert metadata
    assert result['metadata']['prior_high'] == 152.0
    assert result['metadata']['prior_low'] == 148.0
    assert result['metadata']['prior_close'] == 150.0
    assert result['metadata']['range'] == 4.0
    assert '2026-02-14' in result['metadata']['prior_date']

def test_fibonacci_pivots_edge_case_zero_range():
    """Test edge case where prior day has zero range (H=L=C)."""
    # If H=L=C, range is 0, all pivots should equal PP
    data = pd.DataFrame({
        'high': [100.0, 105.0],
        'low': [100.0, 98.0],
        'close': [100.0, 102.0]
    })

    indicator = FibonacciPivotPointsIndicator()
    result = indicator.calculate(data)

    # When range=0, all levels collapse to PP
    assert result['value_data']['pp'] == 100.0
    assert result['value_data']['r1'] == 100.0
    assert result['value_data']['r2'] == 100.0
    assert result['value_data']['r3'] == 100.0
    assert result['value_data']['s1'] == 100.0
    assert result['value_data']['s2'] == 100.0
    assert result['value_data']['s3'] == 100.0
    assert result['metadata']['range'] == 0.0
```

**Integration Tests**:
- Verify DELETE + INSERT prevents duplicates
- Verify daily timeframe storage
- Verify metadata tracking (prior day OHLC + range)
- Verify integration with OHLCVDataService for historical data

---

## References

**Technical Documentation**:
- [Investopedia: Fibonacci Pivot Points](https://www.investopedia.com/articles/technical/04/092204.asp)
- [TradingView: Fibonacci Pivot Points](https://www.tradingview.com/support/solutions/43000502098-pivot-points-high-low/)
- [Fibonacci Ratios in Trading](https://www.investopedia.com/terms/f/fibonacciretracement.asp)

**Code References**:
- `src/analysis/indicators/directional/pivot_points_fibonacci.py` - Implementation
- `src/analysis/indicators/directional/pivot_points.py` - Standard Pivots (comparison)
- `src/api/services/ohlcv_data_service.py` - Historical data fetching (Sprint 72)

---

## Document Status

**Version**: 1.0
**Last Updated**: February 15, 2026
**Status**: ✅ **READY FOR IMPLEMENTATION**
**Sprint**: Sprint 78 - Complete Table 1 Indicators
