### Pivot Points Calculation Instructions for TickStock.ai

**Created**: February 15, 2026
**Category**: directional
**Display Order**: 70
**Implementation**: `src/analysis/indicators/directional/pivot_points.py`
**Variant**: Standard Pivots (for Fibonacci variant, see `pivot_points_fibonacci.md`)

---

## Overview

**Description**: Standard Pivot Points are support and resistance levels calculated from the prior trading day's OHLC data using traditional formulas. They provide intra-day price targets and reversal zones for swing and day traders.

**Formula**:
```
PP (Pivot Point) = (High + Low + Close) / 3
R1 (Resistance 1) = (2 × PP) - Low
R2 (Resistance 2) = PP + (High - Low)
R3 (Resistance 3) = High + 2 × (PP - Low)
S1 (Support 1) = (2 × PP) - High
S2 (Support 2) = PP - (High - Low)
S3 (Support 3) = Low - 2 × (High - PP)

All calculations use prior trading day's OHLC data.
```

**Interpretation**:
- **PP (Pivot Point)**: Central equilibrium level, price tends to gravitate toward PP
- **R1/R2/R3**: Resistance levels above PP, potential reversal or profit-taking zones
- **S1/S2/S3**: Support levels below PP, potential bounce or entry zones
- **Breakouts**: Close above R1 suggests bullish momentum; close below S1 suggests bearish momentum
- **Range Trading**: PP as midpoint, trade bounces between S1-R1

**Typical Range**: Same scale as price (e.g., $148-$152 for a $150 stock)

**Parameters**:
- None - Standard formula is fixed

**Usage Context**:
- Calculate once per day using prior day's OHLC
- Use throughout current trading day for intra-day targets
- Most effective in ranging markets
- Combine with volume for confirmation

---

## Storage Schema

**Table**: `daily_indicators`

**Columns**:
- `symbol` — ticker (text)
- `indicator_type` — lowercase with underscore: 'pivot_points'
- `calculation_timestamp` — timestamp when calculated (typically market open)
- `timeframe` — 'daily' (calculated from prior day data, used for intra-day reference)
- `value_data` — JSONB with calculation results:
  ```json
  {
    "pp": 150.00,
    "r1": 151.20,
    "r2": 152.40,
    "r3": 153.60,
    "s1": 148.80,
    "s2": 147.60,
    "s3": 146.40
  }
  ```
- `metadata` — JSONB with context:
  ```json
  {
    "source": "batch_eod",
    "prior_date": "2026-02-14",
    "prior_high": 152.00,
    "prior_low": 148.00,
    "prior_close": 150.00
  }
  ```
- `expiration_date` — timestamp when data becomes stale (next day market open)

**Persistence Pattern** (Sprint 74 - TimescaleDB Hypertables):
```sql
-- DELETE existing entry (daily refresh)
DELETE FROM daily_indicators
WHERE symbol = :symbol
  AND indicator_type = 'pivot_points'
  AND timeframe = 'daily';

-- INSERT new entry
INSERT INTO daily_indicators
(symbol, indicator_type, value_data, calculation_timestamp,
 expiration_date, timeframe, metadata)
VALUES (:symbol, 'pivot_points', :value_data, NOW(),
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

**Step 2**: Calculate Pivot Point (PP)
```python
pp = (prior_high + prior_low + prior_close) / 3
```

**Step 3**: Calculate Resistance Levels (R1, R2, R3)
```python
r1 = (2 * pp) - prior_low
r2 = pp + (prior_high - prior_low)
r3 = prior_high + 2 * (pp - prior_low)
```

**Step 4**: Calculate Support Levels (S1, S2, S3)
```python
s1 = (2 * pp) - prior_high
s2 = pp - (prior_high - prior_low)
s3 = prior_low - 2 * (prior_high - pp)
```

### Pandas Implementation

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class PivotPointsParams:
    """Pivot Points indicator parameters."""
    # No parameters - Standard formula is fixed
    pass

class PivotPointsIndicator:
    """
    Standard Pivot Points support and resistance indicator.

    Calculates intra-day price targets from prior trading day's OHLC data.
    Provides 7 levels: PP (pivot), R1/R2/R3 (resistance), S1/S2/S3 (support).

    Calculation:
    - PP = (High + Low + Close) / 3
    - R1 = (2 × PP) - Low
    - R2 = PP + (High - Low)
    - R3 = High + 2 × (PP - Low)
    - S1 = (2 × PP) - High
    - S2 = PP - (High - Low)
    - S3 = Low - 2 × (High - PP)
    """

    def __init__(self, params: Optional[dict] = None):
        """Initialize Pivot Points indicator."""
        self.params = PivotPointsParams()
        self.name = "pivot_points"
        self.category = "directional"

    def calculate(self, data: pd.DataFrame) -> Optional[dict]:
        """
        Calculate Pivot Points indicator.

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

        # Calculate standard pivots
        # Pivot Point
        pp = (prior_high + prior_low + prior_close) / 3

        # Resistance Levels
        r1 = (2 * pp) - prior_low
        r2 = pp + (prior_high - prior_low)
        r3 = prior_high + 2 * (pp - prior_low)

        # Support Levels
        s1 = (2 * pp) - prior_high
        s2 = pp - (prior_high - prior_low)
        s3 = prior_low - 2 * (prior_high - pp)

        # Return formatted result
        return {
            "indicator_type": "pivot_points",
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
                "prior_close": prior_close
            }
        }
```

---

## Dependencies

**Requires** (Processing Order):
- Prior day's OHLC data (requires 2+ days of history)
- Sprint 72 OHLCVDataService for fetching historical data

**Used By** (Downstream Dependencies):
- Intra-day support/resistance strategies
- Range trading setups
- Breakout confirmation

**Database Definition**:
```sql
-- indicator_definitions table entry
INSERT INTO indicator_definitions
(name, display_order, category, class_name, method_name,
 instantiation_params, min_bars_required, enabled,
 short_description, display_name)
VALUES
('pivot_points', 70, 'directional', 'PivotPointsIndicator', 'calculate',
 '{}', 2, true,
 'Standard pivot points for intra-day support/resistance levels', 'Pivot Points');
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
- ✅ No NaN values unless insufficient data
- ✅ Precision: 2 decimal places (standard for stock prices)

**Regression Testing**:
- Compare against TradingView Pivot Points indicator
- Tolerance: ±$0.01 for pivot levels

---

## Error Handling & Logging

```python
import logging
logger = logging.getLogger(__name__)

# Insufficient data
if len(data) < 2:
    logger.warning(f"Pivot Points: Insufficient data for {symbol} - need 2 days, have {len(data)}")
    return None

# Missing columns
required_cols = ['high', 'low', 'close']
if not all(col in data.columns for col in required_cols):
    logger.error(f"Pivot Points: Missing required columns for {symbol}")
    return None

# NaN values in prior day
if any(pd.isna(val) for val in [prior_high, prior_low, prior_close]):
    logger.warning(f"Pivot Points: NaN values in prior day data for {symbol}")
    return None

# Invalid OHLC relationship
if prior_high < prior_low:
    logger.warning(f"Pivot Points: Invalid OHLC data for {symbol} - high < low")
    return None

# Calculation error
try:
    pp = (prior_high + prior_low + prior_close) / 3
    r1 = (2 * pp) - prior_low
except Exception as e:
    logger.error(f"Pivot Points: Calculation failed for {symbol}: {e}", exc_info=True)
    return None

# Data gap warning (weekend/holiday)
if 'date' in data.columns:
    current_date = data.iloc[-1]['date']
    days_diff = (current_date - prior_date).days
    if days_diff > 3:  # More than weekend
        logger.warning(f"Pivot Points: Large date gap for {symbol} - {days_diff} days")
        metadata['data_gap_warning'] = True
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Calculation | <5ms | 7 arithmetic operations |
| Prior day data fetch | <20ms | Database query for 2 days |
| Persistence (DELETE + INSERT) | <20ms | Two SQL operations |
| **Total: Indicator update** | **<50ms** | End-to-end latency |

---

## Testing

**Unit Tests** (`tests/unit/indicators/test_pivot_points.py`):
```python
import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.analysis.indicators.directional.pivot_points import PivotPointsIndicator

def test_pivot_points_calculation():
    """Test pivot points calculation with known data."""
    # Prior day: H=152, L=148, C=150
    # PP = (152 + 148 + 150) / 3 = 150.0
    # R1 = (2 × 150) - 148 = 152.0
    # R2 = 150 + (152 - 148) = 154.0
    # R3 = 152 + 2 × (150 - 148) = 156.0
    # S1 = (2 × 150) - 152 = 148.0
    # S2 = 150 - (152 - 148) = 146.0
    # S3 = 148 - 2 × (152 - 150) = 144.0

    data = pd.DataFrame({
        'date': [datetime(2026, 2, 14), datetime(2026, 2, 15)],
        'high': [152.0, 155.0],
        'low': [148.0, 149.0],
        'close': [150.0, 153.0]
    })

    indicator = PivotPointsIndicator()
    result = indicator.calculate(data)

    # Assert
    assert result is not None
    assert result['value_data']['pp'] == 150.0
    assert result['value_data']['r1'] == 152.0
    assert result['value_data']['r2'] == 154.0
    assert result['value_data']['r3'] == 156.0
    assert result['value_data']['s1'] == 148.0
    assert result['value_data']['s2'] == 146.0
    assert result['value_data']['s3'] == 144.0

def test_pivot_points_level_ordering():
    """Test that pivot levels are properly ordered."""
    data = pd.DataFrame({
        'high': [100.0, 105.0],
        'low': [95.0, 98.0],
        'close': [98.0, 102.0]
    })

    indicator = PivotPointsIndicator()
    result = indicator.calculate(data)

    # Assert proper ordering: R3 > R2 > R1 > PP > S1 > S2 > S3
    assert result['value_data']['r3'] > result['value_data']['r2']
    assert result['value_data']['r2'] > result['value_data']['r1']
    assert result['value_data']['r1'] > result['value_data']['pp']
    assert result['value_data']['pp'] > result['value_data']['s1']
    assert result['value_data']['s1'] > result['value_data']['s2']
    assert result['value_data']['s2'] > result['value_data']['s3']

def test_pivot_points_insufficient_data():
    """Test handling of insufficient data (only 1 day)."""
    data = pd.DataFrame({
        'high': [100.0],
        'low': [95.0],
        'close': [98.0]
    })

    indicator = PivotPointsIndicator()
    result = indicator.calculate(data)

    assert result is None

def test_pivot_points_missing_columns():
    """Test handling of missing required columns."""
    data = pd.DataFrame({
        'close': [100, 101]
    })

    indicator = PivotPointsIndicator()
    result = indicator.calculate(data)

    assert result is None

def test_pivot_points_nan_values():
    """Test handling of NaN values in prior day."""
    data = pd.DataFrame({
        'high': [None, 105.0],  # NaN in prior day
        'low': [95.0, 98.0],
        'close': [98.0, 102.0]
    })

    indicator = PivotPointsIndicator()
    result = indicator.calculate(data)

    assert result is None

def test_pivot_points_metadata():
    """Test metadata includes prior day OHLC."""
    data = pd.DataFrame({
        'date': [datetime(2026, 2, 14), datetime(2026, 2, 15)],
        'high': [152.0, 155.0],
        'low': [148.0, 149.0],
        'close': [150.0, 153.0]
    })

    indicator = PivotPointsIndicator()
    result = indicator.calculate(data)

    # Assert metadata
    assert result['metadata']['prior_high'] == 152.0
    assert result['metadata']['prior_low'] == 148.0
    assert result['metadata']['prior_close'] == 150.0
    assert '2026-02-14' in result['metadata']['prior_date']

def test_pivot_points_edge_case_identical_ohlc():
    """Test edge case where prior day OHLC are identical."""
    # If H=L=C, all pivots should equal that value
    data = pd.DataFrame({
        'high': [100.0, 105.0],
        'low': [100.0, 98.0],
        'close': [100.0, 102.0]
    })

    indicator = PivotPointsIndicator()
    result = indicator.calculate(data)

    # When H=L=C=100, PP=100, R1=100, R2=100, etc.
    assert result['value_data']['pp'] == 100.0
    assert result['value_data']['r1'] == 100.0
    assert result['value_data']['s1'] == 100.0
    # Range is 0, so R2=PP, S2=PP
    assert result['value_data']['r2'] == 100.0
    assert result['value_data']['s2'] == 100.0
```

**Integration Tests**:
- Verify DELETE + INSERT prevents duplicates
- Verify daily timeframe storage
- Verify metadata tracking (prior day OHLC)
- Verify integration with OHLCVDataService for historical data

---

## References

**Technical Documentation**:
- [Investopedia: Pivot Points](https://www.investopedia.com/terms/p/pivotpoint.asp)
- [TradingView: Pivot Points Standard](https://www.tradingview.com/support/solutions/43000521824-pivot-points-standard/)
- [Fibonacci Pivot Points](https://www.investopedia.com/articles/technical/04/092204.asp)

**Code References**:
- `src/analysis/indicators/directional/pivot_points.py` - Implementation
- `src/analysis/indicators/base_indicator.py` - Base class
- `src/api/services/ohlcv_data_service.py` - Historical data fetching (Sprint 72)

---

## Document Status

**Version**: 1.0
**Last Updated**: February 15, 2026
**Status**: ✅ **READY FOR IMPLEMENTATION**
**Sprint**: Sprint 78 - Complete Table 1 Indicators
